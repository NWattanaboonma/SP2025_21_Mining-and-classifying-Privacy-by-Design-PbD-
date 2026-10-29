"""
Step 06.2 - Average Recall@K per configuration -> Summary_Averages.txt and chart.
Run from inside 06_evaluation/.

Usage:  cd 06_evaluation && python summarize_recall.py
"""
import os
import pandas as pd
import glob
import matplotlib.pyplot as plt

# --- CONFIGURATION ---
RESULTS_FOLDER = 'EVA_RECALL'
OUTPUT_TEXT_FILE = 'Summary_Averages.txt'
OUTPUT_IMAGE_FILE = 'Summary_Averages_Chart.png'
# ---------------------

def summarize_results():
    # 1. Find all Excel files in the target folder
    file_pattern = os.path.join(RESULTS_FOLDER, '*.xlsx')
    excel_files = glob.glob(file_pattern)
    
    if not excel_files:
        print(f"❌ No Excel files found in '{RESULTS_FOLDER}'. Please check the folder name.")
        return

    print(f"🔍 Found {len(excel_files)} files. Calculating averages...\n")
    
    summary_rows = []

    # 2. Loop through each file and calculate averages
    for file_path in excel_files:
        filename = os.path.basename(file_path)
        file_id = os.path.splitext(filename)[0]
        
        # --- Format Model ID ---
        # Change from "Eval-ModelA_ModelB" to "Embedding_ModelA_Chat_ModelB"
        if file_id.startswith('Eval_'):
            models_str = file_id[5:]  # Remove the 'Eval-' prefix
            # Remove specific suffixes
            models_str = models_str.replace('_10_10', '').replace('_Recall', '')
            # Assuming the two models are separated by an underscore
            if '_' in models_str:
                emb_model, chat_model = models_str.split('_', 1)
                file_id = f"Embedding_{emb_model}_Chat_{chat_model}"
        # -----------------------

        try:
            df = pd.read_excel(file_path)
            
            # Exclude the 'Average' row injected by previous scripts so it doesn't double-count
            if 'IssueID' in df.columns:
                df = df[df['IssueID'] != 'Average']
                
            row_data = {'ID': file_id}
            
            # Find all columns starting with 'Recall@'
            recall_cols = [col for col in df.columns if str(col).startswith('Recall@')]
            
            if recall_cols:
                # Sort columns so they display in numerical order
                recall_cols.sort()
                
                for col in recall_cols:
                    row_data[col] = f"{df[col].mean():.4f}"
            else:
                print(f"   ⚠️ No 'Recall@X' columns found in {filename}.")
                
            summary_rows.append(row_data)
            
        except Exception as e:
            print(f"⚠️ Could not read {filename}: {e}")

    # 3. Format into a neat text table and save
    if summary_rows:
        all_recall_cols = set()
        for row in summary_rows:
            all_recall_cols.update(k for k in row.keys() if k != 'ID')
        all_recall_cols = sorted(list(all_recall_cols))
        
        header = f"{'ID':<45}"
        for col in all_recall_cols:
            header += f" | {col:<10}"
            
        separator = "=" * len(header)
        
        output_lines = [separator, header, separator]
        
        for row in summary_rows:
            line = f"{row['ID']:<45}"
            for col in all_recall_cols:
                val = row.get(col, "N/A")
                line += f" | {val:<10}"
            output_lines.append(line)
            
        output_lines.append(separator)
        
        print("\n" + "\n".join(output_lines))
        
        with open(OUTPUT_TEXT_FILE, 'w', encoding='utf-8') as f:
            f.write("\n".join(output_lines) + "\n")
            
        print(f"\n✅ All averages successfully calculated and saved to: {OUTPUT_TEXT_FILE}")
        
        # --- 4. Generate Graphic (Line Chart) ---
        try:
            df_plot = pd.DataFrame(summary_rows)
            df_plot.set_index('ID', inplace=True)
            
            # Ensure columns are safely converted to numbers for plotting
            for col in all_recall_cols:
                df_plot[col] = pd.to_numeric(df_plot[col], errors='coerce')
                
            # Transpose so Recall@K is on the X-axis
            df_plot = df_plot[all_recall_cols].T
            
            # Rename index from 'Recall@X' to just the number 'X' (e.g., '1', '2', etc.)
            df_plot.index = [str(idx).replace('Recall@', '') for idx in df_plot.index]
            
            # Use subplots so we have a distinct handle on the 'ax' object
            fig, ax = plt.subplots(figsize=(14, 8))
            
            for column in df_plot.columns:
                # Drop missing values so lines don't break if a model misses a metric
                valid_data = df_plot[column].dropna()
                ax.plot(valid_data.index, valid_data.values, marker='o', linewidth=2, label=column)
                
            # ax.set_title('Recall@K Performance Across Models', fontsize=16, fontweight='bold')
            ax.set_xlabel('Recall@K', fontsize=12)
            ax.set_ylabel('Average Score', fontsize=12)
            ax.grid(True, linestyle='--', alpha=0.7)
            
            # --- FIX: Match Legend Height to Plot Height ---
            # 'mode="expand"' forces the legend box to expand to fill the bounding box.
            # 'bbox_to_anchor=(1.02, 0, 1, 1)' sets: (start_x, start_y, width, height) relative to the axes.
            ax.legend(
                title='Model IDs', 
                bbox_to_anchor=(1.02, 0, 0.5, 1), # Increased width to 0.85 to fit larger font sizes safely
                loc='center left', 
                mode="expand",                     # Spreads the items out vertically to match the height
                borderaxespad=0., 
                fontsize=14
            )
            
            # Ensure everything fits nicely without cropping the right side
            plt.tight_layout()
            
            plt.savefig(OUTPUT_IMAGE_FILE, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"📊 Graphical chart successfully saved to: {OUTPUT_IMAGE_FILE}")
        except Exception as e:
            print(f"⚠️ Could not generate chart: {e}")
            print("   (If you see an error about 'matplotlib', run: pip install matplotlib)")

    else:
        print("⚠️ No data was processed.")

if __name__ == "__main__":
    summarize_results()
