import os, sys, re, subprocess, shutil
import pandas as pd
from google.colab import files # For file uploads and downloads in Colab

def check_perm(path, is_file=True):
    """
    Checks if a file or directory exists and is readable.
    Raises an error if not (Colab-friendly alternative to sys.exit).
    """
    if is_file and not os.path.isfile(path):
        raise FileNotFoundError(f"File not found: {path}")
    elif not is_file and not os.path.isdir(path):
        raise FileNotFoundError(f"Directory not found: {path}")
        
    if not os.access(path, os.R_OK):
        raise PermissionError(f"Cannot access (read permission denied) {path}")

def parse_orca_ir(lines):
    """
    Parse ORCA output file to extract IR spectrum data.
    (Retained original user's working logic, adapted for Colab error handling)
    """
    start = next((i for i, ln in enumerate(lines) if ln.strip().startswith("IR SPECTRUM")), None)
    if start is None:
        raise ValueError("IR SPECTRUM section not found in ORCA output. Please check your ORCA .out file.")
        
    end = next((j for j in range(start, len(lines)) 
               if "Maximum memory used throughout the entire PROP-calculation" in lines[j]), None)
    if end is None:
        # Fallback for ORCA output files that might not have the exact "Maximum memory used" line
        # This is a common ORCA footer, but if it's missing, try to find a general end.
        # A more robust end might be the next major section header or end of file
        for k in range(start + 1, len(lines)):
            if (len(lines[k].strip()) == 0 and len(lines[k+1].strip()) > 0 if k+1 < len(lines) else False) or \
               lines[k].strip().startswith(("---", "**********")): # Look for next section separator
                end = k
                break
        if end is None: # If still no clear end, go to end of file
            end = len(lines)
        if end == len(lines):
            print("Warning: Could not find explicit end marker for 'IR SPECTRUM' section. Parsing until end of file or next major block.", file=sys.stderr)

    orca = {}
    # Original regex from user, designed to capture: Mode#: Freq Unit IR_Intensity
    pat = re.compile(r'\s*(\d+):\s*([\d.]+)\s+\S+\s+([\d.]+)')
    for ln in lines[start:end]:
        m = pat.match(ln)
        if m:
            idx = int(m.group(1))
            orca[idx] = {"freq": float(m.group(2)), "ir": float(m.group(3))}
    
    if not orca:
        raise ValueError("No IR modes found in the 'IR SPECTRUM' section matching the expected pattern. "
                         "Please check your ORCA output file's 'IR SPECTRUM' format.")
    return orca

def run_va(hfile, va_script):
    """
    Run the vibrational analysis script (va.py) using subprocess.
    Includes error handling and prints va.py's output for debugging.
    """
    print(f"Running va.py: {va_script} --vmard --mwd --autosel {hfile}")
    try:
        # Run va.py from its directory to ensure it finds any auxiliary files it might need
        # The hfile argument MUST be an absolute path here for va.py to find it.
        result = subprocess.run([sys.executable, va_script, "--vmard", "--mwd", "--autosel", hfile], 
                                check=True, capture_output=True, text=True,
                                cwd=os.path.dirname(va_script)) 
        print("va.py completed successfully.")
        # Print va.py's stdout/stderr for debugging even if it succeeds (e.g., warnings)
        if result.stdout:
            print("--- va.py STDOUT ---")
            print(result.stdout)
        if result.stderr:
            print("--- va.py STDERR ---")
            print(result.stderr)
            
    except FileNotFoundError:
        raise FileNotFoundError(f"Error: va.py script not found at '{va_script}'. Make sure it's cloned/uploaded and path is correct.")
    except subprocess.CalledProcessError as e:
        print(f"Error running va.py:\nSTDOUT:\n{e.stdout}\nSTDERR:\n{e.stderr}", file=sys.stderr)
        raise RuntimeError(f"va.py failed with exit code {e.returncode}. Check va.py output above for details.")
    except Exception as e:
        raise RuntimeError(f"An unexpected error occurred while running va.py: {e}")

def replace_vmard_ir(nma_path, orca_modes, backup=True):
    """
    Update NMA file with ORCA IR values.
    Matches modes by frequency. Uses 0.05 cm-1 tolerance for robust matching.
    """
    if backup:
        shutil.copy(nma_path, nma_path + ".orig")
        print(f"Backed up {nma_path} to {nma_path}.orig")

    try:
        with open(nma_path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        raise FileNotFoundError(f"NMA file not found: {nma_path}. Was va.py executed successfully and did it create the .nma file?")

    out = []
    # Pattern to match Mode X: Y.YY cm-1 (IR: Z.ZZ) in the NMA file
    pat_mode = re.compile(r'\s*Mode\s+(\d+):\s*([\d.]+)\s*cm-1\s*\(IR:\s*([\d.]+)\)')
    
    replacements_made = 0
    # Create a mutable copy of orca_modes to pop matched items
    remaining_orca_modes = orca_modes.copy() 

    for ln in lines:
        m = pat_mode.match(ln)
        if m:
            vm_mode = int(m.group(1))
            freq = float(m.group(2))
            
            # Find ORCA mode index with matching frequency from remaining modes
            match_key = None
            # Using a slightly larger tolerance for floating point comparisons
            for o_idx, v_data in list(remaining_orca_modes.items()): 
                if abs(v_data["freq"] - freq) < 0.05: # Changed from original 1e-4 for robustness
                    match_key = o_idx
                    break
            
            if match_key is not None:
                irv = remaining_orca_modes[match_key]["ir"]
                # Format to two decimal places for consistency
                new_ln = f"Mode {vm_mode}:  {freq:.2f} cm-1 (IR: {irv:.2f})"
                out.append(new_ln)
                replacements_made += 1
                # Remove matched ORCA mode to prevent re-matching
                del remaining_orca_modes[match_key] 
            else:
                out.append(ln) # Keep original line if no match
        else:
            out.append(ln)
    
    if replacements_made == 0:
        print("Warning: No IR intensities were updated in the NMA file. Check frequency matching or ORCA output format.", file=sys.stderr)
    elif len(remaining_orca_modes) > 0:
        print(f"Warning: {len(remaining_orca_modes)} ORCA IR modes were not matched to NMA modes. (Frequencies: {[v['freq'] for v in remaining_orca_modes.values()]})", file=sys.stderr)

    with open(nma_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    return nma_path

def parse_aligned_nma(nma_path):
    """
    Parse the NMA file to extract vibrational mode information.
    (Retained original user's regex for contribution lines)
    """
    check_perm(nma_path)
    modes = []
    with open(nma_path, encoding="utf-8") as f:
        for ln in f:
            # Header with Mode line
            m = re.match(r"\s*Mode\s+(\d+):\s*([\d.]+)\s*cm-1\s*\(IR:\s*([\d.]+)\)", ln)
            if m:
                idx = int(m.group(1))
                freq = float(m.group(2))
                ir = float(m.group(3))
                modes.append({'Mode': idx, 'Freq': freq, 'IR': ir, 'Contrib': []})
            elif ln.strip().startswith(("+", "-")) and modes:
                # Contribution line: +0.50 (50.0%) BOND C1-H2
                m2 = re.match(r"\s*[+-]?([\d.]+)\s+\(\s*([\d.]+)%\)\s+(\w+)\s+(.+)", ln)
                if m2:
                    weight = float(m2.group(2)) / 100.0
                    ctype = m2.group(3)
                    atoms = m2.group(4).split() # Original split() method
                    modes[-1]['Contrib'].append({'type': ctype, 'atoms': atoms, 'weight': weight})
    if not modes:
        raise ValueError("No vibrational modes found in the NMA file. Check NMA file format or va.py output.")
    return modes

def calc_counts_and_top(modes, topn=2):
    """
    Calculate contribution counts and top contributors for each mode.
    (Adjusted column names for clarity, improved atom list formatting in Top_Contributions)
    """
    rows = []
    for m in modes:
        cnt = {'BOND': 0, 'ANGLE': 0, 'OUT': 0, 'TORSION': 0}
        for c in m['Contrib']:
            key = 'TORSION' if c['type'].upper() == 'TORSION' else c['type'].upper() # Ensure consistent casing
            cnt[key] = cnt.get(key, 0) + 1 # Use .get() for safety
        
        top = sorted(m['Contrib'], key=lambda x: x['weight'], reverse=True)[:topn]
        # Using ' '.join for atoms for better readability, assuming va.py outputs space-separated atoms
        topstr = "; ".join(f"{c['type']}({' '.join(c['atoms'])}):{c['weight']:.2f}" for c in top)
        
        rows.append({
            'Mode': m['Mode'],
            'Freq_cm-1': f"{m['Freq']:.2f}",
            'IR_Intensity_km/mol': f"{m['IR']:.2f}", # Renamed for clarity
            'BOND_Contribs': cnt.get('BOND', 0),
            'ANGLE_Contribs': cnt.get('ANGLE', 0),
            'OUT_Contribs': cnt.get('OUT', 0),
            'TORSION_Contribs': cnt.get('TORSION', 0),
            'Top_Contributions': topstr
        })
    return pd.DataFrame(rows)

def prompt_filter(df):
    """
    Prompt user to filter the results.
    (Enhanced filtering options from previous iterations)
    """
    while True:
        choice = input("\nFilter by (a)toms/groups, (f)requencies, (n)one, or (e)xport current results? ").strip().lower()
        if choice == 'a':
            atoms_input = input("Enter atom pairs/groups comma-sep (e.g., C1 H2, N3 C4, C=O). Use exact atom numbers from NMA output: ").strip()
            if not atoms_input:
                print("No atoms/groups entered. Returning original DataFrame.")
                return df
            
            atoms_groups = [grp.strip() for grp in atoms_input.split(',') if grp.strip()]
            
            mask = pd.Series([False] * len(df)) # Initialize a boolean mask
            for grp in atoms_groups:
                # The pattern looks for the entered group within the parentheses part of the contribution string.
                # Example: If user enters "C1 H2", it will look for "(C1 H2)"
                # This ensures we match exact atom groups, not partial matches across types.
                search_pattern = r'\(' + re.escape(grp) + r'\)' 
                mask = mask | df['Top_Contributions'].str.contains(search_pattern, case=False, regex=True)
            
            if mask.any():
                print(f"Applying filter for: {', '.join(atoms_groups)}")
                return df[mask]
            else:
                print(f"No modes found matching the atoms/groups: {', '.join(atoms_groups)}. Showing original DataFrame.")
                return df # Return original if no matches
                
        elif choice == 'f':
            try:
                freq_input = input("Enter discrete frequencies (e.g., 100.0, 200.5) or a range (e.g., 100-200): ").strip()
                if not freq_input:
                    print("No frequencies entered. Returning original DataFrame.")
                    return df
                
                if '-' in freq_input:
                    # Handle frequency range
                    f_start_str, f_end_str = freq_input.split('-')
                    f_start = float(f_start_str.strip())
                    f_end = float(f_end_str.strip())
                    print(f"Applying filter for frequency range: {f_start:.2f}-{f_end:.2f} cm-1")
                    # Convert 'Freq_cm-1' to float for comparison
                    return df[ (df['Freq_cm-1'].astype(float) >= f_start) & (df['Freq_cm-1'].astype(float) <= f_end) ]
                else:
                    # Handle discrete frequencies
                    freqs = [float(x.strip()) for x in freq_input.split(',') if x.strip()]
                    print(f"Applying filter for discrete frequencies: {', '.join([f'{f:.2f}' for f in freqs])} cm-1")
                    return df[df['Freq_cm-1'].astype(float).isin(freqs)]
            except ValueError:
                print("Invalid frequency format. No filtering applied.")
                return df
        elif choice == 'n':
            print("No filtering applied. Displaying all modes.")
            return df
        elif choice == 'e':
            # User wants to export the currently displayed results
            return None # Special return to signal export
        else:
            print("Invalid choice. Please enter 'a', 'f', 'n', or 'e'.")
            
    return df # Should not be reached if loop breaks correctly

def export_results(df):
    """
    Export results to a file in the specified format.
    Includes Google Colab file download functionality.
    """
    while True:
        outpath = input("Enter output filename (with extension .txt, .xlsx, or .mc): ").strip()
        if not outpath:
            print("No filename provided. Please try again.")
            continue
            
        ext = os.path.splitext(outpath)[1].lower()
        try:
            if ext == '.xlsx':
                df.to_excel(outpath, index=False)
            elif ext == '.mc':
                # Custom markdown-like table format
                with open(outpath, 'w', encoding="utf-8") as f:
                    # Header
                    f.write("| " + " | ".join(df.columns) + " |\n")
                    # Separator
                    f.write("|" + " --- |" * len(df.columns) + "\n")
                    # Rows
                    for _, row in df.iterrows():
                        f.write("| " + " | ".join(str(row[c]) for c in df.columns) + " |\n")
            else:  # Default to tab-separated .txt
                df.to_csv(outpath, sep='\t', index=False)
            
            print(f"Results successfully saved to {os.path.abspath(outpath)}")
            # In Colab, you can download the file directly
            files.download(outpath)
            print(f"File '{outpath}' has been downloaded to your local machine.")
            return
        except Exception as e:
            print(f"Error saving file: {e}. Please try again.")

def main():
    print("=== ORCA IR Analysis Tool ===\n")
    
    # --- Input and Setup (Colab-specific file handling) ---
    
    # Automatically find uploaded ORCA files in the current Colab directory (/content/)
    orca_out_files = [f for f in os.listdir('.') if f.endswith('.out') or f.endswith('.orca')]
    orca_hess_files = [f for f in os.listdir('.') if f.endswith('.hess')]
    
    if not orca_out_files:
        raise FileNotFoundError("No ORCA output file (.out or .orca) found in the current directory. Please ensure you have uploaded it.")
    if not orca_hess_files:
        raise FileNotFoundError("No ORCA Hessian file (.hess) found in the current directory. Please ensure you have uploaded it.")

    # Get the filenames from the uploaded files (these are relative to /content/)
    outf_name = orca_out_files[0] 
    hfile_name = orca_hess_files[0] 

    # Construct the absolute paths for the input files
    # All uploaded files are in /content/
    full_outf_path = os.path.join("/content/", outf_name)
    full_hfile_path = os.path.join("/content/", hfile_name)

    # IMPORTANT: Use the path to va.py from the cloned and patched repository
    # This path assumes you cloned to /content/vibAnalysis-master/
    va_script = "/content/vibAnalysis-master/va.py" 
    
    if not os.path.exists(va_script):
        raise FileNotFoundError(f"The 'va.py' script was not found at {va_script}. Please ensure you have run Step 2 (Clone & Patch va.py) correctly.")
    
    print(f"Using ORCA output file: {full_outf_path}")
    print(f"Using ORCA Hessian file: {full_hfile_path}")
    print(f"Using vibAnalysis script: {va_script}")

    # Check permissions for the chosen files (using absolute paths)
    try:
        check_perm(full_outf_path)
        check_perm(full_hfile_path)
        check_perm(va_script)
    except (FileNotFoundError, PermissionError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1) 

    # Step 1: Process ORCA output and Hessian file
    print("\nStep 1: Processing ORCA output and running vibrational analysis...")
    print("-" * 50)
    
    # Parse ORCA output to get IR intensities
    print(f"Parsing ORCA output file: {full_outf_path}...")
    with open(full_outf_path, encoding="utf-8") as f:
        lines = f.readlines()
    orca_modes = parse_orca_ir(lines) 
    print(f"Found {len(orca_modes)} IR modes in {full_outf_path}.")
    
    # Run va.py, passing the ABSOLUTE path to the Hessian file
    run_va(full_hfile_path, va_script)
    
    # Determine the NMA file name. va.py typically creates the .nma file
    # in the same directory as the input .hess file.
    nma_path = full_hfile_path.replace(".hess", ".nma")
    if not os.path.exists(nma_path):
        # Fallback for some va.py versions that might append .nma directly
        if os.path.exists(full_hfile_path + ".nma"):
            nma_path = full_hfile_path + ".nma"
        else:
            raise FileNotFoundError(f"Expected NMA file '{nma_path}' or '{full_hfile_path}.nma' not found after running va.py. Check va.py output in the console above.")

    check_perm(nma_path) # Check if the NMA file was successfully created and is readable
    
    # Replace IR values in the NMA file
    print(f"\nUpdating NMA file with ORCA IR values: {nma_path}")
    updated_nma = replace_vmard_ir(nma_path, orca_modes.copy()) # Pass a copy as dict is modified
    print(f"Updated NMA file path: {os.path.abspath(updated_nma)}")
    
    # Step 2: Analyze the NMA file
    print("\nStep 2: Analyzing the NMA file")
    print("-" * 50)
    
    modes = parse_aligned_nma(updated_nma)
    df = calc_counts_and_top(modes, topn=2)
    
    # Display and filter results
    print("\nInitial Vibrational Modes Summary:")
    print("-" * 50)
    print(df.to_string(index=False))
    
    current_df = df # Start with the full DataFrame
    while True:
        # Pass the current_df to the filter function
        filtered_df_result = prompt_filter(current_df) 
        
        if filtered_df_result is None: # Signal to export current results
            export_results(current_df)
            break # Exit the loop after export
        else:
            current_df = filtered_df_result # Update current_df with filtered results
            print("\nFiltered Results:")
            print("-" * 30)
            if current_df.empty:
                print("No modes match the current filter criteria.")
            else:
                print(current_df.to_string(index=False))
            
            # Offer to filter again or export
            continue_action = input("\n(f)ilter again, (e)xport these results, or (q)uit? ").strip().lower()
            if continue_action == 'e':
                export_results(current_df)
                break
            elif continue_action == 'q':
                break
            elif continue_action == 'f':
                continue # Loop back to prompt_filter
            else:
                print("Invalid choice. Exiting.")
                break
    
    print("\nAnalysis complete!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except (FileNotFoundError, PermissionError, ValueError, RuntimeError) as e:
        print(f"\nAn error occurred: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)
