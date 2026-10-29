"""
Convert the annotated Excel file (Ground_data.xlsx) into JSON for indexing/n8n.
Taxonomy columns (names starting with a digit) become booleans.

Usage:  python 05_rag_pipeline/convert_xlsx_to_json.py 05_rag_pipeline/data/Ground_data.xlsx
"""
import pandas as pd
import argparse
import os
import sys
import re

def convert_xlsx_to_json(input_path: str, output_path: str = None) -> None:
    """
    Reads an Excel file and converts it to a JSON file.
    Uses orient='records' to create a list of dictionaries (one per row).
    """
    if not os.path.exists(input_path):
        print(f"Error: The file '{input_path}' does not exist.")
        sys.exit(1)

    # If output_path is missing, save as .json in the same location as input
    if output_path is None:
        base, _ = os.path.splitext(input_path)
        output_path = f"{base}.json"

    # Check if output_path is a directory or looks like one (ends with separator)
    is_dir_path = os.path.isdir(output_path) or output_path.endswith(os.sep)
    if os.altsep:
        is_dir_path = is_dir_path or output_path.endswith(os.altsep)

    if is_dir_path:
        # Ensure the directory exists
        if not os.path.exists(output_path):
            try:
                os.makedirs(output_path)
                print(f"Created output directory: {output_path}")
            except OSError as e:
                print(f"Error creating directory '{output_path}': {e}")
                sys.exit(1)
        
        # Construct the filename from input
        base_name = os.path.basename(input_path)
        name, _ = os.path.splitext(base_name)
        output_path = os.path.join(output_path, f"{name}.json")
    else:
        # It is a file path; ensure the parent directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
                print(f"Created output directory: {output_dir}")
            except OSError as e:
                print(f"Error creating directory '{output_dir}': {e}")
                sys.exit(1)

    try:
        print(f"Reading '{input_path}'...")
        # Read the Excel file. By default, this reads the first sheet.
        # To read a specific sheet, add sheet_name='Sheet1'
        # Header is on row 7 (index 6)
        df = pd.read_excel(input_path, engine='openpyxl', header=6)

        # Remove rows that are completely empty (fixes the issue with empty row 6)
        df = df.dropna(how='all')

        # Convert columns that look like requirement IDs (start with a digit) to boolean
        # 1 is True, 0 is False
        for col in df.columns:
            if re.match(r'^\d', str(col)):
                df[col] = df[col] == 1

        # Replace dots with underscores in column names to make them n8n friendly
        # df.columns = df.columns.astype(str).str.replace('.', '_', regex=False)

        # Convert to JSON string
        # orient='records' is best for ground truth (list of objects)
        # indent=4 makes it human-readable
        print("Converting to JSON...")
        df.to_json(output_path, orient='records', indent=4, force_ascii=False, date_format='iso')

        print(f"Success! Data saved to '{output_path}'")

    except Exception as e:
        if "openpyxl" in str(e):
            print("Error: Missing 'openpyxl' library. Please run: pip install openpyxl")
        print(f"An error occurred during conversion: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert XLSX to JSON for ground truth.")
    parser.add_argument("input_path", nargs='?', help="Path to the input Excel file")
    parser.add_argument("output_path", nargs='?', help="Path to the output JSON file or directory (optional)")
    
    args = parser.parse_args()

    # If no input file is provided, try to find one automatically
    if not args.input_path:
        xlsx_files = [f for f in os.listdir('.') if f.endswith('.xlsx') and not f.startswith('~$')]
        if len(xlsx_files) == 1:
            args.input_path = xlsx_files[0]
            print(f"No input file specified. Found '{args.input_path}', using it.")
        else:
            parser.print_help()
            sys.exit(1)

    convert_xlsx_to_json(args.input_path, args.output_path)