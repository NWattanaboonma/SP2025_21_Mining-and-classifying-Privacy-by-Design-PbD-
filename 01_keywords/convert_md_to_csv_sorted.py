"""
Same as convert_md_to_csv.py, but sorted by domain/keyword.

Usage:  python 01_keywords/convert_md_to_csv_sorted.py
"""
import os
import re
import pandas as pd

# ==========================================
# CONFIGURATION
# ==========================================
# Path to the markdown file containing Python lists
# We look in the parent directory by default
INPUT_FILE = os.path.join("..", "G_Keyword_domain sealife.md")

# Output CSV file name
OUTPUT_FILE = "domain_keywords_sorted.csv"

def convert_md_keywords_to_csv(input_path, output_path):
    """
    Parses a Markdown/Python file for list definitions and exports them to CSV.
    Sorts keywords based on '(cite: number)' found in comments.
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
        
        # Rename Iot to Internet of Things (IoT)
        if domain_name == "Iot":
            domain_name = "Internet of Things (IoT)"
        
        # Extract items and sort by citation number in comments
        parsed_items = []
        
        # Process line by line to associate comments with keywords
        for line in list_body.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Split line into code and comment to avoid matching quotes in comments
            parts = line.split('#', 1)
            code_part = parts[0]
            
            # Extract keywords from the code part
            keywords_on_line = re.findall(r'["\']([^"\']+)["\']', code_part)
            
            if keywords_on_line:
                priority = 999999 # Low priority (high number) if no cite found
                
                # Search for (cite: number) in the whole line (usually the comment part)
                cite_match = re.search(r'\(cite:\s*(\d+)\)', line, re.IGNORECASE)
                if cite_match:
                    priority = int(cite_match.group(1))
                
                for kw in keywords_on_line:
                    parsed_items.append((priority, kw))
        
        # Sort by priority (citation number)
        parsed_items.sort(key=lambda x: x[0])
        items = [p[1] for p in parsed_items]
        
        print(f"   -> Found domain '{domain_name}' with {len(items)} keywords.")
        
        for item in items:
            data.append({
                "Domain": domain_name,
                "Keyword": item
            })

    # 4. Save to CSV
    if data:
        df = pd.DataFrame(data)
        # Remove duplicates
        df = df.drop_duplicates()
        
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"\n🎉 Success! Saved {len(df)} keywords to '{output_path}'.")
    else:
        print("\n⚠️ No data extracted.")

if __name__ == "__main__":
    convert_md_keywords_to_csv(INPUT_FILE, OUTPUT_FILE)