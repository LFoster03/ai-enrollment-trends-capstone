"""
inspect_file.py

Quick diagnostic to print the first N rows of an Excel file, and
list all sheet names, so we can see the real structure before
cleaning it.

Usage:
    python inspect_file.py "data\\raw\\ISU_Fall2025.xlsx"
    python inspect_file.py "data\\raw\\ISU_Fall2025.xlsx" UG
"""

import sys
import pandas as pd

filepath = sys.argv[1]
sheet = sys.argv[2] if len(sys.argv) > 2 else 0

# List all sheet names first, in case data isn't on the first sheet
xl = pd.ExcelFile(filepath)
print("Sheet names found:", xl.sheet_names)
print()

# Print the first 20 rows of the requested sheet, raw (no header assumed)
raw = pd.read_excel(filepath, sheet_name=sheet, header=None, nrows=20)
print(f"First 20 rows of sheet '{sheet}':")
print(raw.to_string())