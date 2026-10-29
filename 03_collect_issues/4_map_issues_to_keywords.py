"""
Step 03.4 - Keep issues whose title/body match domain keywords (report 4.3.2, Step 2.5).
Keywords are read from 01_keywords/Keyword_domain.md.
Output: <name>_mapped.csv

Usage:  python 03_collect_issues/4_map_issues_to_keywords.py
"""
import os
import pandas as pd
import sys
import re
import warnings

# --- CONFIGURATION ---
# The file containing keywords (Python lists in Markdown)
KEYWORD_FILENAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "01_keywords", "Keyword_domain.md")
 
# The base name for the final output files (without extension)
OUTPUT_BASENAME = "mapped_issues_by_keyword"
# --- END CONFIGURATION ---

def resolve_file_path(filename):
    """
    Tries to locate the file in the current directory.
    If not found, checks the parent directory.
    """
    # 1. Check current directory
    if os.path.exists(filename):
        return filename
    
    # 2. Check parent directory (useful if running from a subdir)
    parent_dir = os.path.dirname(os.getcwd())
    parent_path = os.path.join(parent_dir, filename)
    if os.path.exists(parent_path):
        return parent_path
        
    # 3. Check script directory (if different from cwd)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, filename)
    if os.path.exists(script_path):
        return script_path

    return filename # Return original so error can be logged later

def load_keywords_from_md(filepath):
    """Parses the markdown file to extract all keywords from Python lists."""
    if not os.path.exists(filepath):
        print(f"⚠️  Warning: Keyword file '{filepath}' not found.")
        return []

    print(f"📖 Reading keywords from: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find all python list definitions: variable_name = [ ... ]
    lists = re.findall(r'(\w+)\s*=\s*\[(.*?)\]', content, re.DOTALL)
    
    all_keywords = set()
    for var_name, list_body in lists:
        # Extract items inside quotes
        items = re.findall(r'["\']([^"\']+)["\']', list_body)
        all_keywords.update(items)
    
    unique_keywords = list(all_keywords)
    print(f"   ✅ Loaded {len(unique_keywords)} unique keywords.")
    return unique_keywords

def find_csv_files(directory):
    """Scans a directory and its subdirectories for all .csv files."""
    csv_files = []
    output_csv_to_avoid = f"{OUTPUT_BASENAME}.csv"
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".csv"):
                # Avoid processing its own output file in subsequent runs
                if file == output_csv_to_avoid:
                    continue
                if file.endswith("_mapped.csv"):
                    continue
                csv_files.append(os.path.join(root, file))
    return csv_files

def map_keywords_in_file(filepath, keyword_pattern):
    """
    Reads a single CSV file and returns a DataFrame containing rows
    where keywords are found in the 'Title' or 'Body'.
    """
    print(f"📂 Processing: {os.path.basename(filepath)}...", end=" ", flush=True)
    
    try:
        df = pd.read_csv(filepath, low_memory=False)
    except Exception as e:
        print(f"❌ Error: {e}")
        return pd.DataFrame() # Return empty DataFrame on error

    # Validate that 'Title' and 'Body' columns exist
    if 'Title' not in df.columns or 'Body' not in df.columns:
        print(f"⚠️  Skipping (Missing columns)")
        return pd.DataFrame()

    # Fill empty cells to prevent errors during string operations
    df['Title'] = df['Title'].fillna('')
    df['Body'] = df['Body'].fillna('')

    # Create a boolean mask for rows that match the keyword pattern
    # The search is case-insensitive (case=False) and uses regex.
    # The '|' operator means OR, so it finds rows where the keyword is in the title OR the body.
    try:
        mask = df['Title'].str.contains(keyword_pattern, case=False, regex=True) | \
               df['Body'].str.contains(keyword_pattern, case=False, regex=True)
    except Exception as e:
        print(f"❌ Error applying regex: {e}")
        return pd.DataFrame()

    matching_rows = df[mask]
    
    print(f"✅ Found {len(matching_rows)}")
    return matching_rows

if __name__ == "__main__":
    print("--- Keyword Mapper for GitHub Issues ---")
    
    # 1. Set target directory to the script's location
    target_dir = os.path.dirname(os.path.abspath(__file__))

    # 2. Find all CSV files to process
    csv_files_to_process = find_csv_files(target_dir)
    if not csv_files_to_process:
        print("No CSV files to process. Exiting.")
        sys.exit(0)

    # 3. Prepare for search
    keyword_path = resolve_file_path(KEYWORD_FILENAME)
    keywords = load_keywords_from_md(keyword_path)
    
    if not keywords:
        print("❌ No keywords found to search. Exiting.")
        sys.exit(1)

    # Join keywords with '|' to create a regex OR pattern (e.g., "privacy|GDPR|PII")
    # We use re.escape to ensure special characters in keywords don't break the regex
    keyword_regex_pattern = "|".join([re.escape(k) for k in keywords])
    print(f"\n🔍 Processing {len(csv_files_to_process)} files...")
    
    # 4. Process each file
    for csv_file in csv_files_to_process:
        matches = map_keywords_in_file(csv_file, keyword_regex_pattern)
        if not matches.empty:
            # Generate output filename: original_mapped.csv
            base_name = os.path.splitext(os.path.basename(csv_file))[0]
            output_csv = f"{base_name}_mapped.csv"
            output_path = os.path.join(os.path.dirname(csv_file), output_csv)
            
            try:
                matches.to_csv(output_path, index=False, encoding='utf-8-sig')
                print(f"   💾 Saved {len(matches)} matches to: {output_csv}")
            except Exception as e:
                print(f"   ❌ Failed to save {output_csv}: {e}")

    print("\n🎉 Processing complete.")
    input("\nPress Enter to exit...")