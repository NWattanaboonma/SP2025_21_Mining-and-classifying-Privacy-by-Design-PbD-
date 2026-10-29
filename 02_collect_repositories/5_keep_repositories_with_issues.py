"""
Step 02.5 - Keep only repositories with Total_Issues > 0.
Output: <input>_has_issues.csv (this is the input of step 03.1)

Usage:  python 02_collect_repositories/5_keep_repositories_with_issues.py
"""
import pandas as pd
import os

def remove_empty_issues(input_file):
    """
    Reads a CSV, removes rows with 0 issues, empty issue counts, or completely empty rows.
    """
    # 1. Path Handling
    if not os.path.exists(input_file):
        # Try looking in the parent directory
        parent_file = os.path.join("..", input_file)
        if os.path.exists(parent_file):
            print(f"   -> Found file in parent directory: {parent_file}")
            input_file = parent_file
        else:
            print(f"❌ File not found: {input_file}")
            return

    try:
        print(f"📂 Loading data from {input_file}...")
        df = pd.read_csv(input_file, low_memory=False)
        
        initial_rows = len(df)
        
        # 2. Remove completely empty rows
        df.dropna(how='all', inplace=True)
        rows_after_empty_drop = len(df)
        if initial_rows - rows_after_empty_drop > 0:
            print(f"   🗑️ Removed {initial_rows - rows_after_empty_drop} completely empty rows.")

        # 3. Check for Total_Issues column
        if 'Total_Issues' not in df.columns:
            print("❌ Error: Column 'Total_Issues' not found.")
            print("   Available columns:", list(df.columns))
            return

        # 4. Filter Issues
        # Convert to numeric, turning errors (like strings) into NaN
        df['Total_Issues'] = pd.to_numeric(df['Total_Issues'], errors='coerce')
        
        # Keep rows where Total_Issues is not NaN AND > 0
        df_cleaned = df[df['Total_Issues'].notna() & (df['Total_Issues'] > 0)]
        
        final_rows = len(df_cleaned)
        removed_issues = rows_after_empty_drop - final_rows
        
        print(f"   🗑️ Removed {removed_issues} repositories with 0 or missing issues.")
        print(f"📊 Final repository count: {final_rows} (from {initial_rows})")

        # 5. Save
        base_name, extension = os.path.splitext(input_file)
        output_file = f"{base_name}_has_issues{extension}"
        
        df_cleaned.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n💾 Saved cleaned data to: {output_file}")

    except Exception as e:
        print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    print("--- Empty Issue Remover ---")
    user_input = input("Enter CSV filename: ").strip().replace('"', '').replace("'", "")
    
    if user_input:
        if not os.path.exists(user_input) and not user_input.lower().endswith(".csv"):
             user_input += ".csv"
             
        remove_empty_issues(user_input)
    else:
        print("❌ No file entered.")
