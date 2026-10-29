"""
Utility - convert a CSV file to JSON.

Usage:  python tools/convert_csv_to_json.py
"""
import pandas as pd
import os
import sys

# ==========================================
# CONFIGURATION
# ==========================================
DEFAULT_INPUT_FILE = "github_issues_dataset.csv"

def convert_csv_to_json(csv_path):
    """
    Reads a CSV file and converts it to a JSON file.
    Output format: List of records (Array of Objects).
    """
    if not os.path.exists(csv_path):
        print(f"❌ Error: Input file '{csv_path}' not found.")
        return

    # Generate output filename
    json_path = os.path.splitext(csv_path)[0] + ".json"
    
    print(f"📂 Reading CSV: {csv_path}...")
    
    try:
        # Read CSV
        # low_memory=False helps with mixed types in large files
        df = pd.read_csv(csv_path, low_memory=False)
        print(f"   📊 Loaded {len(df)} rows.")

        print(f"🔄 Converting to JSON...")
        
        # Convert to JSON
        # orient='records' -> [{"col":"val"}, {"col":"val"}]
        # indent=4 -> Pretty print
        # force_ascii=False -> Preserve unicode (e.g. emojis, non-english)
        df.to_json(json_path, orient='records', indent=4, force_ascii=False)
        
        print(f"✅ Success! Saved to: {json_path}")

    except Exception as e:
        print(f"❌ Error converting file: {e}")

if __name__ == "__main__":
    # Handle command line argument: python convert_csv_to_json.py filename.csv
    if len(sys.argv) > 1:
        target_file = sys.argv[1]
    else:
        print(f"ℹ️ No file specified. Using default: {DEFAULT_INPUT_FILE}")
        target_file = DEFAULT_INPUT_FILE

    convert_csv_to_json(target_file)