"""
Step 03.3 - Remove issues with an empty body.
Output: issues_<Domain>_Only_E_No_Empty.csv

Usage:  python 03_collect_issues/3_filter_empty_body_issues.py
"""
import pandas as pd
import os
import sys

def filter_empty_body_issues(input_file):
    """
    Reads a CSV, removes rows where the Body is empty or NaN,
    and saves a new file.
    """
    # Normalize path to handle relative paths correctly
    input_file = os.path.abspath(input_file)

    # 1. Validate Input File
    if not os.path.exists(input_file):
        print(f"❌ File not found: {input_file}")
        return

    print(f"📂 Processing: {input_file}...", flush=True)
    try:
        df = pd.read_csv(input_file, low_memory=False)
    except PermissionError:
        print(f"❌ Error: Permission denied. Please close the file if it is open in Excel.")
        return
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return

    # 2. Validate Columns
    required_cols = ['Title', 'Body']
    for col in required_cols:
        if col not in df.columns:
            print(f"⚠️  Skipping {input_file}: Column '{col}' not found.")
            return

    total_rows = len(df)
    print(f"   📊 Total rows in input file: {total_rows}")
    
    # 3. Apply Filter
    # Check both Title and Body. 
    # We strip whitespace (spaces, tabs, newlines) and dashes ('-').
    # This removes rows that are just "---", " - ", "\n", or empty.
    chars_to_strip = ' \t\n\r-'
    
    # Process in chunks to show progress
    chunk_size = 10000
    chunks = []
    processed_count = 0

    for start in range(0, total_rows, chunk_size):
        end = min(start + chunk_size, total_rows)
        chunk = df.iloc[start:end]
        
        processed_count = end
        sys.stdout.write(f"\r   ⏳ Analyzing: {processed_count}/{total_rows} ({(processed_count/total_rows)*100:.1f}%)")
        sys.stdout.flush()

        mask = (chunk['Title'].fillna('').astype(str).str.strip(chars_to_strip) != '') & \
               (chunk['Body'].fillna('').astype(str).str.strip(chars_to_strip) != '')
        chunks.append(chunk[mask])

    print(f"\r   ✅ Analyzed {total_rows} rows.                  ")
    df_clean = pd.concat(chunks) if chunks else pd.DataFrame(columns=df.columns)

    # 4. Save Output
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    dir_name = os.path.dirname(input_file)
    output_filename = f"{base_name}_No_Empty.csv"
    output_path = os.path.join(dir_name, output_filename)

    kept_count = len(df_clean)
    removed_count = total_rows - kept_count

    print(f"   ✅ Kept: {kept_count}, Removed: {removed_count}")
    
    df_clean.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"   💾 Saved to: {output_path}\n")

    # # Optional: Save removed rows to inspect why they were dropped
    # if not df_removed.empty:
    #     debug_path = os.path.join(dir_name, f"{base_name}_removed_debug.csv")
    #     df_removed.to_csv(debug_path, index=False, encoding='utf-8-sig')
    #     print(f"   🕵️  Saved removed rows for inspection: {debug_path}")

def process_all_files(target_dir=None):
    """
    Scans the target directory and subdirectories for 'issues_*.csv' files
    and processes them.
    """
    if target_dir is None:
        target_dir = os.getcwd()

    print(f"🚀 Scanning directory: {target_dir}")
    print("-" * 40)
    
    found_any = False
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            # Target files starting with 'issues_' and ending with '.csv'
            # Avoid re-processing files that are already filtered (contain '_No_Empty')
            if file.startswith("issues_") and file.endswith(".csv") and "_No_Empty" not in file:
                file_path = os.path.join(root, file)
                filter_empty_body_issues(file_path)
                found_any = True
    
    if not found_any:
        print("⚠️ No matching 'issues_*.csv' files found to process.")
    else:
        print("-" * 40)
        print("🎉 Batch processing complete!")

if __name__ == "__main__":
    print("--- Empty Body Issue Filter ---")
    print("Enter a specific CSV filename, a folder path, or press Enter to scan current directory.")
    user_input = input("Input: ").strip().replace('"', '').replace("'", "")

    try:
        if user_input:
            if os.path.isfile(user_input):
                filter_empty_body_issues(user_input)
            elif os.path.isdir(user_input):
                process_all_files(user_input)
            elif not user_input.lower().endswith(".csv"):
                # Try appending extension if it looks like a file request
                if os.path.exists(user_input + ".csv"):
                    filter_empty_body_issues(user_input + ".csv")
                else:
                    print(f"❌ Error: '{user_input}' not found.")
            else:
                print(f"❌ Error: '{user_input}' not found.")
        else:
            process_all_files()
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
    
    input("\nPress Enter to exit...")