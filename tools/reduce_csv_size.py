"""
Utility - shrink big issue CSVs (e.g. keep only the columns needed).

Usage:  python tools/reduce_csv_size.py
"""
import pandas as pd
import os
import math

def reduce_csv_size(input_file):
    """
    Reads a CSV file, removes empty columns/rows, duplicates, and saves a smaller version.
    """
    if not os.path.exists(input_file):
        print(f"❌ File not found: {input_file}")
        return

    # Prepare paths
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    parent_dir = os.path.dirname(input_file)
    output_file = os.path.join(parent_dir, f"{base_name}_optimized.csv")
    print(f"📉 Optimizing: {input_file} ...")

    try:
        # Load the dataset
        # low_memory=False helps with mixed types in large files
        df = pd.read_csv(input_file, low_memory=False)
        
        original_rows, original_cols = df.shape
        original_size = os.path.getsize(input_file)

        # 1. Remove 'Unnamed' index columns (artifacts from previous saves)
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

        # 2. Drop columns that are completely empty (all NaN)
        df.dropna(axis=1, how='all', inplace=True)

        # 3. Drop rows that are completely empty (all NaN)
        df.dropna(axis=0, how='all', inplace=True)

        # 5. Strip whitespace from text columns (saves space and cleans data)
        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

        # 6. Check if file needs splitting
        # GitHub limit is 100MB. 25k rows is safe for text-heavy data (approx 50MB).
        MAX_ROWS = 25000
        
        if len(df) > MAX_ROWS:
            print(f"   ⚠️ File is large ({len(df)} rows). Splitting into parts (Limit: {MAX_ROWS})...")
            
            # Create a folder for the parts
            folder_name = f"{base_name}_parts"
            output_folder = os.path.join(parent_dir, folder_name)
            os.makedirs(output_folder, exist_ok=True)
            print(f"   📂 Created output folder: {output_folder}")

            num_parts = math.ceil(len(df) / MAX_ROWS)
            
            for i in range(num_parts):
                start_row = i * MAX_ROWS
                end_row = min((i + 1) * MAX_ROWS, len(df))
                chunk = df.iloc[start_row:end_row]
                
                part_filename = f"{base_name}_part{i+1}.csv"
                part_output = os.path.join(output_folder, part_filename)
                chunk.to_csv(part_output, index=False, encoding='utf-8-sig')
                print(f"      💾 Saved part {i+1}: {part_output} ({len(chunk)} rows)")
                
            print(f"   ✅ Success! Split into {num_parts} files inside '{folder_name}'.")
            
        else:
            # Save as single optimized file
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            
            # Statistics
            new_rows, new_cols = df.shape
            new_size = os.path.getsize(output_file)
            reduction = ((original_size - new_size) / original_size) * 100 if original_size > 0 else 0

            print(f"   ✅ Success!")
            print(f"   - Rows: {original_rows} -> {new_rows}")
            print(f"   - Columns: {original_cols} -> {new_cols}")
            print(f"   - Size: {original_size/1024/1024:.2f} MB -> {new_size/1024/1024:.2f} MB")
            print(f"   - Reduction: {reduction:.1f}%")
            print(f"   💾 Saved to: {output_file}\n")

    except Exception as e:
        print(f"   ❌ Error processing file: {e}")

if __name__ == "__main__":
    print("--- CSV Size Reducer ---")
    user_input = input("Enter CSV filename (or press Enter to process ALL .csv files in folder): ").strip()
    
    # Remove quotes if user dragged and dropped file path
    user_input = user_input.replace('"', '').replace("'", "")

    if user_input:
        # Check if file exists directly
        if os.path.exists(user_input):
            reduce_csv_size(user_input)
        # Check if user meant a file in the parent directory (Senior_project root)
        elif os.path.exists(os.path.join("..", user_input)):
            reduce_csv_size(os.path.join("..", user_input))
        # Check if user forgot extension
        elif not user_input.lower().endswith(".csv"):
             if os.path.exists(user_input + ".csv"):
                 reduce_csv_size(user_input + ".csv")
             elif os.path.exists(os.path.join("..", user_input + ".csv")):
                 reduce_csv_size(os.path.join("..", user_input + ".csv"))
             else:
                 print(f"❌ File not found: {user_input}")
        else:
            print(f"❌ File not found: {user_input}")
    else:
        # Batch process all CSVs in current directory AND parent directory
        print("Scanning for CSV files...")
        files_to_process = []

        # 1. Current Directory (Tools)
        for f in os.listdir('.'):
            if f.endswith('.csv') and '_optimized' not in f and 'part' not in f:
                files_to_process.append(f)
        
        # 2. Parent Directory (Senior_project)
        if os.path.exists(".."):
            for f in os.listdir(".."):
                if f.endswith('.csv') and '_optimized' not in f and 'part' not in f:
                    files_to_process.append(os.path.join("..", f))
        
        if not files_to_process:
            print("No CSV files found in current or parent directory.")
        else:
            print(f"Found {len(files_to_process)} CSV files. Processing all...")
            for f in files_to_process:
                reduce_csv_size(f)
