"""
Step 04.2 - Check that the sampled issues contain no duplicates.

Usage:  python 04_annotation/2_check_sample_duplicates.py
"""
import pandas as pd
import os

def check_duplicates():
    print("--- 🕵️‍♀️ Duplicate Issue Checker ---")
    print("   This script compares two CSV files to see if they share any common issues.")
    
    # 1. Get File Paths
    file_a = input("📄 Enter path to FIRST CSV file (e.g. old_sample.csv): ").strip().replace('"', '').replace("'", "")
    file_b = input("📄 Enter path to SECOND CSV file (e.g. new_sample.csv): ").strip().replace('"', '').replace("'", "")

    if not os.path.exists(file_a) or not os.path.exists(file_b):
        print("❌ Error: One or both files not found.")
        return

    # 2. Load Data
    try:
        df_a = pd.read_csv(file_a, low_memory=False)
        df_b = pd.read_csv(file_b, low_memory=False)
        
        print(f"\n📊 Loaded File A: {len(df_a)} rows")
        print(f"📊 Loaded File B: {len(df_b)} rows")

        # 3. Identify Unique Column
        # We prefer 'Issue_ID' as it is the most robust identifier
        possible_keys = ['Issue_ID', 'URL', 'Issue_URL', 'html_url']
        key = None
        
        # Find a common key
        for k in possible_keys:
            if k in df_a.columns and k in df_b.columns:
                key = k
                break
        
        if not key:
            print("❌ Error: Could not find a common unique column (Issue_ID, URL, etc) in both files.")
            print(f"   File A columns: {list(df_a.columns)}")
            print(f"   File B columns: {list(df_b.columns)}")
            return

        print(f"🔑 Using column '{key}' as unique identifier.")

        # 4. Find Duplicates
        # Convert to string to ensure matching types
        set_a = set(df_a[key].astype(str))
        set_b = set(df_b[key].astype(str))
        
        intersection = set_a.intersection(set_b)
        count = len(intersection)

        if count == 0:
            print("\n✅ No duplicates found! These two files are completely distinct.")
        else:
            print(f"\n⚠️  Found {count} DUPLICATE issues between the files!")
            print("   Here are some examples:")
            for i, item in enumerate(list(intersection)[:5]):
                print(f"   - {item}")
            
            # Optional: Save duplicates
            save = input("\n💾 Save duplicates to 'duplicates.csv'? (y/n): ").lower().strip()
            if save == 'y':
                dupes_df = df_a[df_a[key].astype(str).isin(intersection)]
                dupes_df.to_csv("duplicates.csv", index=False, encoding='utf-8-sig')
                print("   ✅ Saved to duplicates.csv")

    except Exception as e:
        print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    check_duplicates()
