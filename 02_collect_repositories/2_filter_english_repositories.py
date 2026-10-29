"""
Step 02.2 - Drop repositories with empty fields and non-English name/description.
Output: <input>_r_n_E.csv

Usage:  python 02_collect_repositories/2_filter_english_repositories.py
"""
import pandas as pd
import os
import re
try:
    from langdetect import detect, LangDetectException
except ImportError:
    detect = None

# ==========================================
# CONFIGURATION
# ==========================================
def clean_repository_data(input_path):
    """
    Reads a CSV file, removes non-English repositories, and saves the cleaned dataset.
    """
    if detect is None:
        print("❌ Error: 'langdetect' library is missing. Please run: pip install langdetect")
        return

    if not os.path.exists(input_path):
        # Try looking in the parent directory if not found in current
        parent_path = os.path.join("..", input_path)
        if os.path.exists(parent_path):
            print(f"   -> Found file in parent directory: {parent_path}")
            input_path = parent_path
        else:
            print(f"❌ Error: Input file '{input_path}' not found.")
            return

    base_name, extension = os.path.splitext(input_path)
    output_path = f"{base_name}_r_n_E{extension}"

    print(f"📂 Reading file: {input_path}")
    try:
        df = pd.read_csv(input_path)
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return

    initial_count = len(df)
    print(f"   📊 Total Repositories (Before): {initial_count}")

    df_cleaned = df.copy()

    # Filter: Keep rows where Name + Description is English
    print("   🌍 Filtering non-English repositories (checking Name + Description)...")

    def is_english(row):
        try:
            name = str(row.get('Repo_Name', '')) if pd.notna(row.get('Repo_Name')) else ""
            desc = str(row.get('Description', '')) if pd.notna(row.get('Description')) else ""
            text = f"{name} {desc}".strip()

            # Strict check: Discard if text contains common non-English scripts
            # (Chinese, Japanese, Korean, Cyrillic, Thai, Arabic)
            if re.search(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af\u0400-\u04ff\u0e00-\u0e7f\u0600-\u06ff]', text):
                return False

            if not text:
                return False
            return detect(text) == 'en'
        except LangDetectException:
            return False

    df_cleaned = df_cleaned[df_cleaned.apply(is_english, axis=1)]

    final_count = len(df_cleaned)
    removed_lang = initial_count - final_count

    print(f"   🗑️ Removed (Language): {removed_lang} (Non-English or empty description)")
    print(f"   ✅ Total Repositories Left: {final_count}")

    df_cleaned.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"   💾 Saved cleaned data to: {output_path}")

if __name__ == "__main__":
    print("--- Non-English Repo Remover ---")
    user_input = input("Enter CSV filename: ").strip()
    
    user_input = user_input.replace('"', '').replace("'", "")
    
    if user_input:
        if not os.path.exists(user_input) and not user_input.lower().endswith(".csv"):
             user_input += ".csv"
             
        clean_repository_data(user_input)
    else:
        print("❌ No file entered.")
