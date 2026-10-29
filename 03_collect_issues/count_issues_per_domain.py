"""
Utility - issue statistics per domain / repository / state. Output: <name>_stats.txt

Usage:  python 03_collect_issues/count_issues_per_domain.py
"""
import pandas as pd
import os

def count_issue_stats(input_file):
    """
    Reads an Issue CSV, counts issues per Domain and Repository, 
    including Open/Closed status breakdown.
    """
    # 1. Locate the file
    if not os.path.exists(input_file):
        # Search recursively starting from the project root (relative to this script)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up 2 levels from 'Record/issuess' to get to 'Senior_project'
        project_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
        
        print(f"🔍 '{input_file}' not found locally. Searching in project: {project_root}...")
        
        found = False
        target_name = os.path.basename(input_file)
        
        for root, dirs, files in os.walk(project_root):
            if target_name in files:
                input_file = os.path.join(root, target_name)
                found = True
                break
        
        if not found:
            print(f"❌ File not found: {input_file}")
            return

    try:
        print(f"📂 Loading {input_file}...")
        df = pd.read_csv(input_file, low_memory=False)
        
        required_cols = ['Repo_Name', 'State']
        if not all(col in df.columns for col in required_cols):
            print(f"❌ Error: CSV must contain columns: {required_cols}")
            return

        # Handle missing Domain column if applicable
        if 'Domain' not in df.columns:
            df['Domain'] = 'Uncategorized'

        # 2. Calculate Statistics
        total_issues = len(df)
        domain_counts = df['Domain'].value_counts()

        # Group by Domain -> Repo -> State
        # unstack() pivots the 'State' values (open/closed) into columns
        repo_stats = df.groupby(['Domain', 'Repo_Name', 'State']).size().unstack(fill_value=0)
        
        # Ensure 'open' and 'closed' columns exist (fill with 0 if missing)
        for status in ['open', 'closed']:
            if status not in repo_stats.columns:
                repo_stats[status] = 0
            
        repo_stats['Total'] = repo_stats['open'] + repo_stats['closed']
        
        # Sort by Total issues descending
        repo_stats = repo_stats.sort_values(by='Total', ascending=False)

        # 3. Generate Report
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_file = f"{base_name}_stats.txt"
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("=" * 85 + "\n")
            f.write(f"📊 ISSUE STATISTICS REPORT: {base_name}\n")
            f.write("=" * 85 + "\n")
            f.write(f"Total Issues Scraped: {total_issues}\n")
            f.write("-" * 85 + "\n\n")
            
            f.write(f"{'Domain':<15} | {'Repository':<40} | {'Total':<6} | {'Open':<6} | {'Closed':<6}\n")
            f.write("-" * 85 + "\n")

            # Iterate through the grouped dataframe
            for (domain, repo), row in repo_stats.iterrows():
                f.write(f"{str(domain)[:15]:<15} | {str(repo)[:40]:<40} | {row['Total']:<6} | {row['open']:<6} | {row['closed']:<6}\n")
            
            f.write("-" * 85 + "\n")

        print(f"✅ Statistics saved to: {output_file}")
        print(f"   (Contains breakdown of Open vs Closed issues per repo)")

    except Exception as e:
        print(f"❌ Error processing file: {e}")

if __name__ == "__main__":
    print("--- Issue Statistics Generator ---")
    user_input = input("Enter Issue CSV filename (e.g., issues_Government.csv): ").strip()
    
    user_input = user_input.replace('"', '').replace("'", "")
    
    if user_input:
        if not os.path.exists(user_input) and not user_input.lower().endswith(".csv"):
             user_input += ".csv"
        count_issue_stats(user_input)
    else:
        print("❌ No file entered.")