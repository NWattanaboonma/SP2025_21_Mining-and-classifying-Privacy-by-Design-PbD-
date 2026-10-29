"""
Utility - convert an Excel file to CSV.

Usage:  python tools/convert_xlsx_to_csv.py
"""
import pandas as pd
import os
import sys

def convert_xlsx_to_csv(input_file):
    """
    Converts an Excel file (.xlsx) to CSV format.
    If multiple sheets exist, saves them as separate CSV files.
    """
    if not os.path.exists(input_file):
        print(f"❌ File not found: {input_file}")
        return

    print(f"📂 Processing: {input_file} ...")

    try:
        # Read all sheets
        # sheet_name=None returns a dictionary {sheet_name: dataframe}
        # engine='openpyxl' is required for .xlsx files
        xls = pd.read_excel(input_file, sheet_name=None, engine='openpyxl')
        
        base_dir = os.path.dirname(input_file)
        base_name = os.path.splitext(os.path.basename(input_file))[0]

        for sheet_name, df in xls.items():
            # Construct output filename
            if len(xls) > 1:
                # Clean sheet name for filename compatibility
                safe_sheet_name = "".join([c if c.isalnum() else "_" for c in sheet_name])
                output_file = os.path.join(base_dir, f"{base_name}_{safe_sheet_name}.csv")
            else:
                output_file = os.path.join(base_dir, f"{base_name}.csv")

            # Save to CSV
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"   ✅ Saved sheet '{sheet_name}' to: {output_file}")

    except ImportError:
        print("   ❌ Error: 'openpyxl' library is missing. Install it via: pip install openpyxl")
    except Exception as e:
        print(f"   ❌ Error converting file: {e}")

if __name__ == "__main__":
    print("--- Excel to CSV Converter ---")
    
    if len(sys.argv) > 1:
        # Support command line arguments
        input_path = sys.argv[1]
        convert_xlsx_to_csv(input_path)
    else:
        user_input = input("Enter Excel filename (or press Enter to scan directory): ").strip()
        user_input = user_input.replace('"', '').replace("'", "")

        if user_input:
            convert_xlsx_to_csv(user_input)
        else:
            # Batch process current directory
            print("Scanning for .xlsx files in current directory...")
            found = False
            for file in os.listdir("."):
                if file.endswith(".xlsx") and not file.startswith("~$"):
                    convert_xlsx_to_csv(file)
                    found = True
            
            if not found:
                print("⚠️ No .xlsx files found.")