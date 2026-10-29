"""
Step 02.3 - Report repositories that appear more than once (e.g. in several domains).
Output: <input>_duplicate.csv

Usage:  python 02_collect_repositories/3_find_duplicate_repositories.py
"""
import pandas as pd
import os

def find_duplicate_repos(input_file):
    """
    Reads a CSV, identifies repositories with duplicate names, 
    lists their domains, and saves them to a separate file for review.
    """
    if not os.path.exists(input_file):
        # Try looking in the parent directory if not found in current
        parent_file = os.path.join("..", input_file)
        if os.path.exists(parent_file):
            print(f"   -> Found file in parent directory: {parent_file}")
            input_file = parent_file
        else:
            print(f"❌ File not found: {input_file}")
            return

    try:
        df = pd.read_csv(input_file, low_memory=False)
        
        if 'Repo_Name' not in df.columns:
            print("❌ Error: Column 'Repo_Name' not found.")
            return

        # Find duplicates (keep=False marks all occurrences as True, so we see every copy)
        dup_mask = df.duplicated(subset=['Repo_Name'], keep=False)
        df_dups = df[dup_mask].copy()

        if df_dups.empty:
            print("✅ No duplicate repositories found based on 'Repo_Name'.")
            return

        print(f"⚠️ Found {len(df_dups)} rows involved in duplication (sharing names).")
        print("-" * 50)
        
        # Group by Repo_Name to show where they come from
        if 'Keyword' in df_dups.columns:
            df_dups['Display_Loc'] = df_dups['Domain'].astype(str) + " (Key: " + df_dups['Keyword'].astype(str) + ")"
            grouped = df_dups.groupby('Repo_Name')['Display_Loc'].apply(list)
        else:
            grouped = df_dups.groupby('Repo_Name')['Domain'].apply(list)
        
        for repo, locations in grouped.items():
            # Filter out unique locations to show distinct sources
            unique_locs = list(set(locations))
            print(f"   🔸 {repo}")
            print(f"      Found in: {', '.join(str(l) for l in unique_locs)}")

        if 'Display_Loc' in df_dups.columns:
            df_dups.drop(columns=['Display_Loc'], inplace=True)

        print("-" * 50)

        # Save to (filename)_duplicate.csv
        base_name, extension = os.path.splitext(input_file)
        output_file = f"{base_name}_duplicate{extension}"
        
        # Sort by name so duplicates appear next to each other
        df_dups.sort_values(by=['Repo_Name', 'Domain'], inplace=True)
        
        df_dups.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n💾 Saved duplicate list to: {output_file}")
        print("   (You can open this file to manually review which ones to keep)")

    except Exception as e:
        print(f"❌ Error processing file: {e}")

if __name__ == "__main__":
    print("--- Duplicate Repository Finder ---")
    user_input = input("Enter CSV filename: ").strip()
    
    user_input = user_input.replace('"', '').replace("'", "")
    
    if user_input:
        if not os.path.exists(user_input) and not user_input.lower().endswith(".csv"):
             user_input += ".csv"
             
        find_duplicate_repos(user_input)
    else:
        print("❌ No file entered.")
