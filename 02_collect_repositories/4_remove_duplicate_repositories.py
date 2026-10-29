"""
Step 02.4 - Remove same-domain duplicate repositories and report cross-domain ones.
Output: <input>_deduped.csv

Usage:  python 02_collect_repositories/4_remove_duplicate_repositories.py
"""
import pandas as pd
import os

def process_duplicates(input_file):
    """
    Reads a CSV, removes duplicates within the same domain,
    and prints a report of duplicates found across different domains.
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
        print(f"📂 Loading data from {input_file}...")
        df = pd.read_csv(input_file, low_memory=False)
        
        if 'Repo_Name' not in df.columns or 'Domain' not in df.columns:
            print("❌ Error: 'Repo_Name' or 'Domain' column not found.")
            return

        initial_rows = len(df)

        # --- 1. Report on Cross-Domain Duplicates ---
        print("\n🔎 Checking for duplicates across different domains...")
        
        # Find all rows that are part of any name duplication
        df_dups = df[df.duplicated(subset=['Repo_Name'], keep=False)].copy()

        if not df_dups.empty:
            # Group by name and check if they span multiple domains
            grouped = df_dups.groupby('Repo_Name')
            cross_domain_dups = []

            for name, group in grouped:
                if group['Domain'].nunique() > 1:
                    domains = list(group['Domain'].unique())
                    cross_domain_dups.append((name, domains))
            
            if cross_domain_dups:
                print("⚠️ Found repositories present in multiple domains (kept for manual review):")
                for repo, domains in cross_domain_dups:
                    print(f"   🔸 {repo}")
                    print(f"      Found in domains: {', '.join(domains)}")
            else:
                print("✅ No cross-domain duplicates found.")
        else:
            print("✅ No duplicates of any kind found.")


        # --- 2. Remove Same-Domain Duplicates ---
        print("\n🗑️ Removing duplicates that are in the SAME domain...")
        
        # We keep the first occurrence of each (Repo_Name, Domain) pair
        df_cleaned = df.drop_duplicates(subset=['Repo_Name', 'Domain'], keep='first')
        
        final_rows = len(df_cleaned)
        rows_removed = initial_rows - final_rows

        print(f"   - Removed {rows_removed} same-domain duplicate rows.")
        print(f"📊 Final repository count: {final_rows} (Logical Data Rows)")

        # --- 3. Save the Cleaned File ---
        base_name, extension = os.path.splitext(input_file)
        output_file = f"{base_name}_deduped{extension}"
        
        df_cleaned.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n💾 Saved cleaned data to: {output_file}")

        # Verify physical lines for user clarity
        try:
            with open(output_file, 'r', encoding='utf-8-sig') as f:
                physical_lines = sum(1 for _ in f)
            print(f"   📝 Physical lines in file: {physical_lines} (Includes Header + Newlines in descriptions)")
            if physical_lines > final_rows + 1:
                print("      (Difference is likely due to descriptions containing newlines)")
        except Exception:
            pass

    except Exception as e:
        print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    print("--- Duplicate Processor ---")
    user_input = input("Enter CSV filename to process: ").strip().replace('"', '').replace("'", "")
    
    if user_input:
        if not os.path.exists(user_input) and not user_input.lower().endswith(".csv"):
             user_input += ".csv"
             
        process_duplicates(user_input)
    else:
        print("❌ No file entered.")
