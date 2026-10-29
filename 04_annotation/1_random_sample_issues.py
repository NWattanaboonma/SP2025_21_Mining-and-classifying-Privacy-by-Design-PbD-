"""
Step 04.1 - Randomly sample issues for manual annotation (report 4.3.3, Steps 3.1-3.2).
Interactive: asks for a single total or a per-domain array (e.g. [50, 50, 20]).

Usage:  python 04_annotation/1_random_sample_issues.py
"""
import pandas as pd
import os
import glob
import sys
import ast

def main():
    print("--- 🎲 Random Issue Sampler ---")
    
    # 1. Locate Files
    # We prioritize the fully filtered files (English + No Empty Body)
    # This ensures you are sampling from your best quality data.
    search_pattern = "*_Only_E_No_Empty.csv"
    files = glob.glob(search_pattern)
    
    # Fallback: If no cleaned files exist, look for any issue files
    if not files:
        print(f"⚠️  No '{search_pattern}' files found.")
        print("   Looking for generic 'issues_*.csv' files...")
        files = glob.glob("issues_*.csv")
        # Exclude stats files or previous random samples to avoid duplicates
        files = [f for f in files if "_stats" not in f and "random_sample" not in f]

    if not files:
        print("❌ No issue CSV files found in the current directory.")
        return

    # Sort files to ensure consistent order for array input
    files.sort()

    print(f"📂 Found {len(files)} files:")
    
    # 2. Load Data
    print("⏳ Loading data to check row counts...")
    all_dfs = []
    for i, f in enumerate(files):
        try:
            df = pd.read_csv(f, low_memory=False)
            df['Source_File'] = os.path.basename(f)
            
            # Ensure Domain column exists (infer from filename if missing)
            if 'Domain' not in df.columns:
                if "Health" in f: df['Domain'] = "Health"
                elif "Iot" in f: df['Domain'] = "Iot"
                elif "Government" in f: df['Domain'] = "Government"
                else:
                    # Fallback: Extract domain from filename instead of "Unknown"
                    clean_name = os.path.basename(f).replace("issues_", "")
                    clean_name = clean_name.split("_Only_E")[0].split(".")[0]
                    df['Domain'] = clean_name

            all_dfs.append(df)
            print(f"   [{i}] {os.path.basename(f)} ({len(df)} rows)")
        except Exception as e:
            print(f"   ❌ Error reading {f}: {e}")
            all_dfs.append(pd.DataFrame())

    if not any(len(df) > 0 for df in all_dfs):
        print("❌ No valid data loaded.")
        return

    # --- NEW: Exclude Previous Samples ---
    print("\n🚫 Exclusion Step (Optional)")
    print("   If you want to ensure new samples do NOT duplicate previous work, enter the old filename here.")
    exclude_file = input("   📄 Enter filename to exclude (e.g. 'old_sample.csv') or press Enter to skip: ").strip()
    
    if exclude_file:
        # Handle quotes if user dragged file path
        exclude_file = exclude_file.replace('"', '').replace("'", "")
        if os.path.exists(exclude_file):
            try:
                ex_df = pd.read_csv(exclude_file, low_memory=False)
                
                # Determine key to use for exclusion (Prioritize Issue_ID)
                exclude_key = None
                if 'Issue_ID' in ex_df.columns:
                    exclude_key = 'Issue_ID'
                elif 'URL' in ex_df.columns:
                    exclude_key = 'URL'

                if exclude_key:
                    excluded_ids = set(ex_df[exclude_key].astype(str).unique())
                    print(f"   👀 Found {len(excluded_ids)} rows in exclusion file (using '{exclude_key}').")
                    
                    total_removed = 0
                    for i in range(len(all_dfs)):
                        initial_count = len(all_dfs[i])
                        if exclude_key in all_dfs[i].columns:
                            # Ensure types match for comparison
                            all_dfs[i] = all_dfs[i][~all_dfs[i][exclude_key].astype(str).isin(excluded_ids)]
                        removed = initial_count - len(all_dfs[i])
                        total_removed += removed
                    
                    print(f"   ✅ Removed {total_removed} duplicate rows from the pool. (Remaining pool: {sum(len(d) for d in all_dfs)})")
                else:
                    print("   ⚠️ The exclusion file does not have 'Issue_ID' or 'URL'. Cannot filter duplicates.")
            except Exception as e:
                print(f"   ❌ Error reading exclusion file: {e}")
        else:
            print(f"   ❌ File '{exclude_file}' not found. Proceeding without exclusion.")

    # 3. Get User Input
    sample_mode = "total"
    sample_values = []

    while True:
        print(f"\nOPTIONS:")
        print(f"   - Enter a SINGLE number (e.g. 100) to sample randomly from all files combined.")
        print(f"   - Enter an ARRAY (e.g. [50, 50, 20]) to sample specific amounts from files [0], [1], [2]...")
        user_input = input("🔢 Input: ").strip()

        # Try parsing as array
        if user_input.startswith("[") and user_input.endswith("]"):
            try:
                parsed = ast.literal_eval(user_input)
                if isinstance(parsed, list) and all(isinstance(x, int) for x in parsed):
                    if len(parsed) != len(files):
                        print(f"   ❌ Error: Array length ({len(parsed)}) must match number of files ({len(files)}).")
                        continue
                    sample_values = parsed
                    sample_mode = "array"
                    break
            except:
                pass 
        
        # Try parsing as integer
        elif user_input.isdigit():
            val = int(user_input)
            if val > 0:
                sample_values = [val]
                sample_mode = "total"
                break
        
        print("   ❌ Invalid input. Please enter a number or an array like [10, 20].")

    # 4. Get Output Filename
    default_name = "random_sample_output.csv"
    out_name = input(f"💾 Enter output filename (default: {default_name}): ").strip()
    if not out_name:
        out_name = default_name
    if not out_name.lower().endswith(".csv"):
        out_name += ".csv"

    # 5. Perform Sampling
    sampled_dfs = []
    
    if sample_mode == "array":
        print("\n🎲 Sampling per file...")
        for i, count in enumerate(sample_values):
            df = all_dfs[i]
            if df.empty: continue
            
            if count > len(df):
                print(f"   ⚠️ File [{i}] has {len(df)} rows, requested {count}. Taking all.")
                count = len(df)
            
            if count > 0:
                sampled = df.sample(n=count)
                sampled_dfs.append(sampled)
                print(f"   ✅ File [{i}]: Took {count} rows.")
    
    else: # Total mode
        print(f"\n🎲 Sampling {sample_values[0]} issues from combined pool...")
        full_df = pd.concat(all_dfs, ignore_index=True)
        total_rows = len(full_df)
        count = sample_values[0]
        
        if count > total_rows:
            print(f"   ⚠️ Requested {count}, but only {total_rows} available. Taking all.")
            count = total_rows
            
        sampled_dfs.append(full_df.sample(n=count))

    # 6. Save
    if sampled_dfs:
        final_df = pd.concat(sampled_dfs, ignore_index=True)
        
        print("\n📈 Final Sample Composition:")
        print(final_df['Source_File'].value_counts().to_string())
        
        final_df.to_csv(out_name, index=False, encoding='utf-8-sig')
        print(f"\n✅ Success! Saved CSV to: {out_name}")

        # Save Excel
        xlsx_name = out_name.replace(".csv", ".xlsx")
        try:
            final_df.to_excel(xlsx_name, index=False)
            print(f"✅ Success! Saved Excel to: {xlsx_name}")
        except Exception as e:
            print(f"⚠️  Could not save Excel file (missing openpyxl?): {e}")
    else:
        print("\n⚠️ No rows selected.")

if __name__ == "__main__":
    main()
