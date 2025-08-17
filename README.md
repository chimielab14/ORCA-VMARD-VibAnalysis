# ORCA Vibrational Mode Analysis & IR Intensity Re-mapping Tool

![Python](https://img.shields.io/badge/Python-3.x-blue.svg)
![Pandas](https://img.shields.io/badge/Pandas-lightgreen.svg)
![Scikit-learn](https://img.shields.io/badge/Scikit--learn-orange.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 💡 What is this project?

This project provides a Python-based tool designed to enhance and streamline the analysis of vibrational modes calculated by **ORCA** quantum chemistry software, specifically by integrating it with the capabilities of the external **`vibAnalysis` (VMARD)** script.

Quantum chemistry calculations yield vibrational frequencies and IR intensities, crucial for comparing with experimental IR spectra. While `vibAnalysis` excels at decomposing these vibrations into contributions from internal coordinates (bonds, angles, torsions), its IR intensities may not always match the higher precision values directly from the ORCA output. This tool bridges that gap.

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
### Step 2: Clone vibAnalysis and Patch va.py

This step will clone the vibAnalysis repository and apply a necessary patch to va.py for compatibility with modern scikit-learn versions (specifically, replacing n_iter with max_iter in ARDRegression calls).

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
