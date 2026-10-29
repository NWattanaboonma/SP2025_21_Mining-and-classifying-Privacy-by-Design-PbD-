"""
Step 06.1 - Compute Recall@K (K = 1..6) for each model configuration (report 4.4.4, Eq. 4.1).
Input : Recall_data_Excel/*.xlsx (pipeline outputs) + Testset.xlsx (ground truth)
Output: EVA_RECALL/Eval_*.xlsx
Run from inside 06_evaluation/.

Usage:  cd 06_evaluation && python recall_at_k.py
"""
import pandas as pd
import numpy as np
import os
import re
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.metrics import recall_score

# --- CONFIGURATION ---
INPUT_FOLDER = 'Recall_data_Excel'
OUTPUT_FOLDER = 'EVA_RECALL'
GROUND_TRUTH_FILE = 'Testset.xlsx'
PREDICTED_COL = 'Taxonomy ID'
ACTUAL_COL = 'Actual_Taxonomy'
# ---------------------

# Parse a cell such as "1.1, 6.4" into a list of taxonomy IDs
def extract_list(text):
    if pd.isna(text): 
        return []
    
    text_str = str(text).lower().strip()
    
    # Empty or "no data" values
    if text_str in ['', 'nan', 'none', '[]', '0']:
        return [] 
        
    # An AI error response counts as no prediction
    if 'error' in text_str or 'false' in text_str:
        return []
        
    # Strip brackets and quotes, then split on commas
    clean_text = str(text).replace('[', '').replace(']', '').replace("'", "").replace('"', '')
    return [item.strip() for item in clean_text.split(',') if item.strip()]

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

print(f"Loading Ground Truth data from: '{GROUND_TRUTH_FILE}'...")
try:
    # Load Ground Truth — skip the 6 empty header rows
    # Testset.xlsx has 6 rows above the header; use header=0 for a file without them
    gt_df = pd.read_excel(GROUND_TRUTH_FILE, header=6)
    gt_df['Issue_ID'] = gt_df['Issue_ID'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
    
    tax_cols = [c for c in gt_df.columns if re.match(r'^[1-6]\.', str(c))]
    
    def get_actual_labels(row):
        labels = [str(col) for col in tax_cols if pd.notna(row.get(col)) and str(row.get(col)).strip() in ['1', '1.0']]
        return ', '.join(labels)
        
    gt_df[ACTUAL_COL] = gt_df.apply(get_actual_labels, axis=1)
    
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
                if filename.endswith('.csv'):
                    df = pd.read_csv(file_path)
                else:
                    df = pd.read_excel(file_path)
                    
                if 'Issue_ID' not in df.columns:
                    print(f"   ⚠️ Skipping {filename}: Missing 'Issue_ID' column.")
                    continue
                
                df['Issue_ID'] = df['Issue_ID'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
                
                df_to_merge = df.copy()
                for col in ['Title', 'Body', 'Description']:
                    if col in df_to_merge.columns and col in gt_subset.columns:
                        df_to_merge = df_to_merge.drop(columns=[col])
                
                merged_df = pd.merge(df_to_merge, gt_subset, on='Issue_ID', how='right')
                
                if PREDICTED_COL not in merged_df.columns:
                    merged_df[PREDICTED_COL] = np.nan
                
                merged_df['actual_list'] = merged_df[ACTUAL_COL].apply(extract_list)
                merged_df['pred_list'] = merged_df[PREDICTED_COL].apply(extract_list)

                mlb = MultiLabelBinarizer()
                
                # Fit the binarizer on every label that appears in either column
                all_tags = merged_df['actual_list'].tolist() + merged_df['pred_list'].tolist()
                
                if not any(all_tags):
                    print(f"   ⚠️ Skipping this file: no taxonomy labels found (Actual and Pred are all empty - check the column names)")
                    continue
                
                mlb.fit(all_tags)

                y_true = mlb.transform(merged_df['actual_list'])
                is_error = merged_df[PREDICTED_COL].astype(str).str.lower().str.contains('error|false', na=False).values

                for k in range(1, 7):
                    preds_at_k = merged_df['pred_list'].apply(lambda x: x[:k])
                    y_pred = mlb.transform(preds_at_k)
                    
                    # Recall per issue (per sample)
                    recall_scores = np.array([
                        recall_score(t, p, zero_division=0) 
                        for t, p in zip(y_true, y_pred)
                    ], dtype=float)
                    
                    # True negative: no labels in both truth and prediction -> 1.0
                    is_true_negative = (y_true.sum(axis=1) == 0) & (y_pred.sum(axis=1) == 0)
                    recall_scores[is_true_negative] = 1.0
                    
                    # Rows with an AI error -> NaN (excluded from the mean)
                    recall_scores[is_error] = np.nan
                    
                    merged_df[f'Recall@{k}'] = recall_scores
                # ------------------------------------------------

                df_export = merged_df.rename(columns={
                    'Issue_ID': 'IssueID',
                    'Body': 'Description'
                })

                expected_columns = [
                    'IssueID', ACTUAL_COL, PREDICTED_COL,
                    'Recall@1', 'Recall@2', 'Recall@3', 
                    'Recall@4', 'Recall@5', 'Recall@6'
                ]
                
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