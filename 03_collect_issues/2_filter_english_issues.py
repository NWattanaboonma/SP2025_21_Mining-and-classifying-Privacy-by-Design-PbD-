"""
Step 03.2 - Keep English issues only (langdetect, code blocks and URLs are stripped first).
Output: issues_<Domain>_Only_E.csv

Usage:  python 03_collect_issues/2_filter_english_issues.py
"""
import pandas as pd
import os
import sys
import re

# Try to import langdetect
try:
    from langdetect import detect, LangDetectException, DetectorFactory
    # Set seed for deterministic results
    DetectorFactory.seed = 0
except ImportError:
    print("❌ Error: The 'langdetect' library is required.")
    print("   Please install it by running: pip install langdetect")
    sys.exit(1)

def filter_english_issues(input_file):
    """
    Reads a CSV, checks Title and Body for English content,
    and saves a new file with only English rows.
    """
    # Normalize path to handle relative paths correctly
    input_file = os.path.abspath(input_file)

    # 1. Validate Input File
    if not os.path.exists(input_file):
        print(f"❌ File not found: {input_file}")
        return

    print(f"📂 Processing: {input_file}...", flush=True)
    try:
        df = pd.read_csv(input_file, low_memory=False)
    except PermissionError:
        print(f"❌ Error: Permission denied. Please close the file if it is open in Excel.")
        return
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return

    # 2. Validate Columns
    required_cols = ['Title', 'Body']
    for col in required_cols:
        if col not in df.columns:
            print(f"⚠️  Skipping {input_file}: Column '{col}' not found.")
            return

    # Fill NaNs
    df['Title'] = df['Title'].fillna('')
    df['Body'] = df['Body'].fillna('')

    total_rows = len(df)
    
    # Progress Counter
    processed_count = 0
    
    # 3. Define Detection Logic
    def clean_text(text):
        """Remove code blocks, inline code, and URLs to focus on human language."""
        # Remove code blocks (```...```)
        text = re.sub(r'```[\s\S]*?```', '', text)
        # Remove inline code (`...`)
        text = re.sub(r'`[^`]+`', '', text)
        # Remove URLs
        text = re.sub(r'http\S+', '', text)
        return text.strip()

    def is_english(row):
        nonlocal processed_count
        processed_count += 1
        if processed_count % 50 == 0:
            sys.stdout.write(f"\r   ⏳ Analyzing: {processed_count}/{total_rows} ({(processed_count/total_rows)*100:.1f}%)")
            sys.stdout.flush()

        title = str(row['Title']).strip()
        body = str(row['Body']).strip()

        if not title:
            return False

        # Strict check: If CJK characters are present in Title, reject immediately.
        if re.search(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]', title):
            return False

        # Strict check: If CJK characters are present in Body, reject immediately.
        if re.search(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]', body):
            return False

        try:
            # Check Title and Body separately to ensure both are English
            if detect(title) != 'en':
                return False

            # Clean body to remove code/logs that look like English
            cleaned_body = clean_text(body)
            
            # If body is empty after cleaning (e.g. only code), treat as English
            if not cleaned_body:
                return True

            # Run language detection on the cleaned human text
            if detect(cleaned_body[:2000]) != 'en':
                return False
                
            return True
        except LangDetectException:
            return False

    # 4. Apply Filter
    mask = df.apply(is_english, axis=1)
    print(f"\r   ✅ Analyzed {total_rows} rows.                  ") # Clear progress line
    df_english = df[mask]

    # 5. Save Output
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    dir_name = os.path.dirname(input_file)
    output_filename = f"{base_name}_Only_E.csv"
    output_path = os.path.join(dir_name, output_filename)

    kept_count = len(df_english)
    removed_count = total_rows - kept_count

    print(f"   ✅ Kept: {kept_count}, Removed: {removed_count}")
    
    df_english.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"   💾 Saved to: {output_path}\n")

def process_all_files(target_dir=None):
    """
    Scans the target directory and subdirectories for 'issues_*.csv' files
    and processes them.
    """
    if target_dir is None:
        target_dir = os.getcwd()

    print(f"🚀 Scanning directory: {target_dir}")
    print("-" * 40)
    
    found_any = False
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            # Target files starting with 'issues_' and ending with '.csv'
            # Avoid re-processing files that are already filtered (contain '_Only_E')
            if file.startswith("issues_") and file.endswith(".csv") and "_Only_E" not in file:
                file_path = os.path.join(root, file)
                filter_english_issues(file_path)
                found_any = True
    
    if not found_any:
        print("⚠️ No matching 'issues_*.csv' files found to process.")
    else:
        print("-" * 40)
        print("🎉 Batch processing complete!")

if __name__ == "__main__":
    print("--- English Issue Filter ---")
    print("Enter a specific CSV filename, a folder path, or press Enter to scan current directory.")
    user_input = input("Input: ").strip().replace('"', '').replace("'", "")

    try:
        if user_input:
            if os.path.isfile(user_input):
                filter_english_issues(user_input)
            elif os.path.isdir(user_input):
                process_all_files(user_input)
            elif not user_input.lower().endswith(".csv"):
                # Try appending extension if it looks like a file request
                if os.path.exists(user_input + ".csv"):
                    filter_english_issues(user_input + ".csv")
                else:
                    print(f"❌ Error: '{user_input}' not found.")
            else:
                print(f"❌ Error: '{user_input}' not found.")
        else:
            process_all_files()
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
    
    input("\nPress Enter to exit...")