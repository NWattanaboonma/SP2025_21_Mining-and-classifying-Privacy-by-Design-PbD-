"""
Convert Keyword_domain.md (Python lists per domain) into a flat CSV.

Usage:  python 01_keywords/convert_md_to_csv.py
"""
import os
import re
import pandas as pd

# ==========================================
# CONFIGURATION
# ==========================================
# Path to the markdown file containing Python lists
# We look in Data_Repo folder by default based on your project structure
INPUT_FILE = os.path.join("Keyword_domain.md")

# Output CSV file name
OUTPUT_FILE = "domain_keyword.csv"

def convert_md_keywords_to_csv(input_path, output_path):
    """
    Parses a Markdown/Python file for list definitions and exports them to CSV.
    """
    # 1. Check if input file exists
    if not os.path.exists(input_path):
        print(f"❌ Error: Input file '{input_path}' not found.")
        # Try looking in current directory as fallback
        if os.path.exists(os.path.basename(input_path)):
            input_path = os.path.basename(input_path)
            print(f"   -> Found it in current directory: {input_path}")
        else:
            return

    print(f"📂 Reading file: {input_path}")
    
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 2. Extract lists using Regex
    # Pattern matches: variable_name = [ ... ]
    # re.DOTALL allows matching across multiple lines
    lists = re.findall(r'(\w+)\s*=\s*\[(.*?)\]', content, re.DOTALL)

    if not lists:
        print("⚠️ No keyword lists found in the file.")
        return

    data = []

    # 3. Process each found list
    for var_name, list_body in lists:
        # Derive Domain Name from Variable (e.g., 'government_keywords' -> 'Government')
        domain_name = var_name.replace("_keywords", "").replace("_hyphenated", "").replace("_space", "").replace("_", " ").title()
        
        if domain_name == "Iot":
            domain_name = "Internet of Things (IoT)"
        
        # Extract items inside double quotes only (ignores apostrophes in comments)
        items = re.findall(r'"([^"]+)"', list_body)
        
        print(f"   -> Found domain '{domain_name}' with {len(items)} keywords.")
        
        for item in items:
            data.append({
                "Domain": domain_name,
                "Keyword": item
            })

    # 4. Save to CSV
    if data:
        df = pd.DataFrame(data)
        # Remove duplicates just in case
        df = df.drop_duplicates()
        
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"\n🎉 Success! Saved {len(df)} keywords to '{output_path}'.")
    else:
        print("\n⚠️ No data extracted.")

if __name__ == "__main__":
    convert_md_keywords_to_csv(INPUT_FILE, OUTPUT_FILE)
