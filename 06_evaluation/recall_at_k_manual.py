"""
Variant of recall_at_k.py used for manual checks. Run from inside 06_evaluation/.

Usage:  cd 06_evaluation && python recall_at_k_manual.py
"""
import pandas as pd
import numpy as np
import os
import re

def compute_recall_at_k(actual_str, pred_str, k):
    # 1. Parse Actual Set
    actual_set = set()
    if pd.notna(actual_str) and str(actual_str).strip() not in ['', 'nan', 'none', '0']:
        actual_set = set([item.strip() for item in str(actual_str).split(',') if item.strip()])
        
    # 2. Check for AI Error messages
    if pd.notna(pred_str):
        lower_pred = str(pred_str).lower().strip()
        if 'error' in lower_pred or 'false' in lower_pred:
            return np.nan
            
    # 3. Parse Predicted List
    pred_list = []
    if pd.notna(pred_str):
        lower_pred = str(pred_str).lower().strip()
        if lower_pred not in ['nan', '', '[]', 'none', '0']:
            clean_pred = str(pred_str).replace('[', '').replace(']', '').replace("'", "").replace('"', '')
            pred_list = [item.strip() for item in clean_pred.split(',') if item.strip()][:k]
        
    # 4. Handle "No Privacy Issue" Cases (Empty Actual)
    if len(actual_set) == 0:
        if len(pred_list) == 0:
            return 1.0  # Correctly predicted NO privacy issues (True Negative)
        else:
            return 0.0  # Hallucinated a privacy issue when there was none (False Positive)
            
    # 5. Handle missing predictions when there ARE actual issues
    if len(pred_list) == 0:
        return 0.0  # AI missed the actual privacy issues
            
    # 6. Normal Recall (TP / (TP + FN))
    hits = set(pred_list).intersection(actual_set)
    return len(hits) / len(actual_set)

# --- CONFIGURATION ---
INPUT_FOLDER = 'Recall_data_Excel'
OUTPUT_FOLDER = 'EVA_RECALL'
GROUND_TRUTH_FILE = 'Testset.xlsx'
PREDICTED_COL = 'Taxonomy ID'
ACTUAL_COL = 'Actual_Taxonomy'
# ---------------------

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

print(f"Loading Ground Truth data from: '{GROUND_TRUTH_FILE}'...")
try:
    # Load Ground Truth — skip the 6 empty header rows
    gt_df = pd.read_excel(GROUND_TRUTH_FILE, header=6)
    gt_df['Issue_ID'] = gt_df['Issue_ID'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
    
    tax_cols = [c for c in gt_df.columns if re.match(r'^[1-6]\.', str(c))]
    
    def get_actual_labels(row):
        labels = [str(col) for col in tax_cols if pd.notna(row.get(col)) and str(row.get(col)).strip() in ['1', '1.0']]
        return ', '.join(labels)
        
    gt_df[ACTUAL_COL] = gt_df.apply(get_actual_labels, axis=1)
    
    # Keep descriptive columns from Ground Truth to ensure they are never missing
    gt_cols = ['Issue_ID', ACTUAL_COL]
    for col in ['Title', 'Body', 'Description']:
        if col in gt_df.columns:
            gt_cols.append(col)
            
    gt_subset = gt_df[gt_cols]
except Exception as e:
    print(f"❌ Error loading Ground Truth file: {e}")
    exit()

if not os.path.exists(INPUT_FOLDER):
    print(f"❌ Input folder '{INPUT_FOLDER}' not found.")
else:
    all_files = [f for f in os.listdir(INPUT_FOLDER) if f.endswith('.csv') or f.endswith('.xlsx')]
    
    if not all_files:
        print(f"⚠️ No CSV or Excel files found in '{INPUT_FOLDER}'.")
    else:
        print(f"🚀 Found {len(all_files)} files. Starting evaluation...\n")
        
        for filename in all_files:
            file_path = os.path.join(INPUT_FOLDER, filename)
            print(f"📂 Processing: {filename}...")
            
            try:
                # Handle both CSV and Excel formats
                if filename.endswith('.csv'):
                    df = pd.read_csv(file_path)
                else:
                    df = pd.read_excel(file_path)
                    
                if 'Issue_ID' not in df.columns:
                    print(f"   ⚠️ Skipping {filename}: Missing 'Issue_ID' column.")
                    continue
                
                df['Issue_ID'] = df['Issue_ID'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
                
                # Drop Title/Body from AI output if Ground Truth has them, to prevent collision
                df_to_merge = df.copy()
                for col in ['Title', 'Body', 'Description']:
                    if col in df_to_merge.columns and col in gt_subset.columns:
                        df_to_merge = df_to_merge.drop(columns=[col])
                
                # Merge with Ground Truth (RIGHT JOIN ensures all 77 GT issues are always shown)
                merged_df = pd.merge(df_to_merge, gt_subset, on='Issue_ID', how='right')
                
                if PREDICTED_COL not in merged_df.columns:
                    merged_df[PREDICTED_COL] = np.nan
                    
                for k in range(1, 7):
                    merged_df[f'Recall@{k}'] = merged_df.apply(
                        lambda row: compute_recall_at_k(row[ACTUAL_COL], row[PREDICTED_COL], k), 
                        axis=1
                    )

                df_export = merged_df.rename(columns={
                    'Issue_ID': 'IssueID',
                    'Body': 'Description'
                })

                expected_columns = [
                    'IssueID', ACTUAL_COL, PREDICTED_COL,
                    'Recall@1', 'Recall@2', 'Recall@3', 
                    'Recall@4', 'Recall@5', 'Recall@6'
                ]
                
                # Filter final_columns safely to prevent KeyError if the original dataset lacks a column (like Title)
                final_columns = [col for col in expected_columns if col in df_export.columns]

                df_final = df_export[final_columns].copy()

                print("   --- Average Performance ---")
                avg_row = {col: np.nan for col in df_final.columns}
                avg_row['IssueID'] = 'Average'
                
                for k in range(1, 7):
                    mean_score = df_final[f'Recall@{k}'].mean()
                    avg_row[f'Recall@{k}'] = mean_score
                    disp_score = "N/A" if pd.isna(mean_score) else f"{mean_score:.4f}"
                    print(f"   Recall@{k}: {disp_score}")
                
                # Append empty row and average row
                empty_row = {col: np.nan for col in df_final.columns}
                df_final = pd.concat([df_final, pd.DataFrame([empty_row, avg_row])], ignore_index=True)

                base_name = os.path.splitext(filename)[0]
                output_filename = os.path.join(OUTPUT_FOLDER, f'Eval_{base_name}.xlsx')
                df_final.to_excel(output_filename, index=False)

                print(f"   ✅ Saved to {output_filename}")
                print("-" * 40)
                
            except Exception as e:
                print(f"   ❌ Error processing {filename}: {e}")
                
        print("\n🎉 All files processed successfully!")