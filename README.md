# ORCA Vibrational Mode Analysis & IR Intensity Re-mapping Tool

![Python](https://img.shields.io/badge/Python-3.x-blue.svg)
![Pandas](https://img.shields.io/badge/Pandas-lightgreen.svg)
![Scikit-learn](https://img.shields.io/badge/Scikit--learn-orange.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 💡 What is this project?

This project provides a Python-based tool designed to enhance and streamline the analysis of vibrational modes calculated by **ORCA** quantum chemistry software, specifically by integrating it with the capabilities of the external **`vibAnalysis` (VMARD)** script.

Quantum chemistry calculations yield vibrational frequencies and IR intensities, crucial for comparing with experimental IR spectra. While `vibAnalysis` excels at decomposing these vibrations into contributions from internal coordinates (bonds, angles, torsions), its IR intensities may not always match the higher precision values directly from the ORCA output. This tool bridges that gap.
## 📝 How to Cite

If you use the ORCA Vibrational Mode Analysis & IR Intensity Re-mapping Tool in your research, please cite it using its Zenodo DOI. This ensures proper attribution and helps others find and reproduce your work.

*May, Abdelghani (2025). ORCA Vibrational Mode Analysis & IR Intensity Re-mapping Tool.*
<a href="https://doi.org/10.5281/zenodo.16891506"><img src="https://zenodo.org/badge/1039524480.svg" alt="DOI"></a>

---
**Note on vibAnalysis:** This tool utilizes the external `vibAnalysis` script. If its specific internal coordinate decomposition features are central to your work, consider acknowledging or citing the original `vibAnalysis` project as well.

## ✨ Key Features

*   **Accurate IR Intensity Extraction:** Parses your ORCA `.out` file to retrieve the precise IR intensities.
*   **`vibAnalysis` Integration:** Automatically runs the `vibAnalysis` script on your ORCA `.hess` file to generate detailed Normal Mode Analysis (`.nma`) data.
*   **IR Intensity Re-mapping:** Updates the `.nma` file with the accurate ORCA IR intensities, ensuring your vibrational analysis uses the most reliable data.
*   **Comprehensive Tabular Summary:** Processes the enriched `.nma` file to present a clear, exportable table for each vibrational mode, including:
    *   Mode number and frequency (cm⁻¹).
    *   **Original ORCA IR Intensity (km/mol).**
    *   Counts of contributing internal coordinate types (BOND, ANGLE, OUT, TORSION).
    *   Top 2 internal coordinate contributions by weight, indicating specific atomic motions.
*   **Interactive Filtering:** Allows users to filter results based on specific atom groups/pairs or frequency ranges.
*   **Flexible Export Options:** Export your analysis to `.txt`, `.xlsx` (Excel), or a custom markdown-like `.mc` format.

## 🚀 Getting Started (Google Colab Recommended)

The easiest way to use this tool is via Google Colab, which provides a ready-to-use Python environment.

**Open the Google Colab Notebook:**
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/chimielab14/ORCA-VMARD-VibAnalysis/blob/main/ORCA_VMARD_VibAnalysis_Colab.ipynb)

Follow the steps within the Colab notebook:

### Step 1: Install Dependencies
```python
!pip install scikit-learn pandas
```

### Step 2: Clone `vibAnalysis` and Patch `va.py`

This step will clone the `vibAnalysis` repository and apply a necessary patch to `va.py` for compatibility with modern `scikit-learn` versions (specifically, replacing `n_iter` with `max_iter` in `ARDRegression` calls).

```python
import os
import re

# Clone the repository
!git clone https://github.com/teixeirafilipe/vibAnalysis.git /content/vibAnalysis-master

# Define the path to va.py within the cloned directory
va_script_path = "/content/vibAnalysis-master/va.py"

print(f"Cloned vibAnalysis into /content/vibAnalysis-master/. Now patching '{va_script_path}' for scikit-learn compatibility...")

# Check if va.py exists at the expected path after cloning
if not os.path.exists(va_script_path):
    raise FileNotFoundError(f"Error: va.py not found at {va_script_path} after cloning. Check clone URL or path.")

# Read the content of va.py
with open(va_script_path, 'r', encoding='utf-8') as f:
    va_content = f.read()

# Replace 'n_iter' with 'max_iter' in the ARDRegression call
patched_content = re.sub(
    r'(sklm\.ARDRegression\([^)]*compute_score=True,)\s*n_iter=(\d+)',
    r'\1max_iter=\2',
    va_content
)

if patched_content == va_content:
    print("Warning: The 'n_iter' -> 'max_iter' patch did not find the expected line in va.py. It might already be patched or the format is different.")
else:
    print("Patch applied successfully: 'n_iter' replaced with 'max_iter' in ARDRegression call.")

# Write the patched content back to va.py
with open(va_script_path, 'w', encoding='utf-8') as f:
    f.write(patched_content)

print(f"Patched '{va_script_path}' saved.")
```

### Step 3: Upload Your ORCA Output and Hessian Files

You'll be prompted to upload your `.out` (ORCA output with IR spectrum) and `.hess` (ORCA Hessian) files directly to the Colab environment.

```python
from google.colab import files

print("Please upload your ORCA output file (.out):")
uploaded_out = files.upload()

print("\nPlease upload your ORCA Hessian file (.hess):")
uploaded_hess = files.upload()
```

### Step 4: Run the Analysis Script

Copy and paste the entire content of `orca_vib_analysis.py` (the main script in this repository) into a new Colab cell and execute it. Then, run `main()` in the next cell. The script will guide you through the analysis with interactive prompts.

```python
# Copy the entire content of orca_vib_analysis.py here
# ... (your Python code from orca_vib_analysis.py) ...

# Then, in a new cell, run:
main()
```

## 📊 Understanding the Output

The script generates a Pandas DataFrame with the following columns:

*   **Mode:** The vibrational mode number.
*   **Freq_cm-1:** The vibrational frequency in wavenumbers (cm⁻¹).
*   **IR_Intensity_km/mol:** The IR intensity in km/mol, directly taken from your ORCA `.out` file. This is the most accurate intensity value.
*   **BOND_Contribs, ANGLE_Contribs, OUT_Contribs, TORSION_Contribs:** These columns show the *number* of individual internal coordinates of that type contributing to the mode, as identified by `vibAnalysis`. This gives a quick overview of the nature of the vibration (e.g., is it predominantly bond stretches or angle bends?).
*   **Top_Contributions:** This is a string listing the top 2 (by default) internal coordinate contributions. Each entry is formatted as `TYPE(Atoms):Weight`, where:
    *   `TYPE`: The type of internal coordinate (e.g., BOND, ANGLE, TORSION, OUT).
    *   `Atoms`: The specific atoms involved in that coordinate (e.g., `C1 H2` for a bond between Carbon 1 and Hydrogen 2, or `H2 C1 H3` for an angle involving these atoms).
    *   `Weight`: The normalized contribution weight (from 0.00 to 1.00), indicating how much that specific coordinate contributes to the overall vibration.

By examining these columns, you can gain a deep understanding of your molecule's vibrational spectrum.

## ⚠️ Important Notes

*   **`vibAnalysis` Script (`va.py`):** This script relies on `va.py` from the `vibAnalysis` package. The provided setup includes cloning and patching it for compatibility.
*   **ORCA Output Format:** The parsing functions are designed for typical ORCA output. Minor variations in ORCA versions might require slight adjustments to the regular expressions, though the provided `parse_orca_ir` is robust based on your successful original.
*   **Frequency Matching Tolerance:** The script matches ORCA IR frequencies to `vibAnalysis` frequencies with a small tolerance (`0.05 cm-1`). This is generally robust, but very close frequencies (e.g., degenerate modes) might require careful inspection.
*   **Atom Naming:** Atom labels (e.g., `C1`, `H2`) come from your ORCA input. Ensure you know your atom numbering.
*   **Python Version:** Developed and tested with Python 3.x.

## 🎓 For Students

This tool can be incredibly useful for:

*   **Understanding Vibrations:** Moving beyond simple "stretch" or "bend" labels to see the exact atomic motions.
*   **IR Spectral Interpretation:** Assigning peaks in an experimental IR spectrum to specific vibrational modes and understanding their origin.
*   **Project Work:** Generating professional-looking tables for reports and presentations.

Experiment with different filtering options and output formats to see what works best for your analysis!

## 🤝 Contributing

Contributions are welcome! If you find a bug, have a feature request, or want to contribute code, please open an issue or submit a pull request.

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Credits

This script was adapted and enhanced from an original code provided by the user, aiming to make it more accessible and robust for educational purposes and Google Colab integration.
Special thanks to the developers of ORCA and vibAnalysis (VMARD) for their powerful tools.


