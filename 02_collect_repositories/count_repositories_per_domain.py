"""
Utility - count collected repositories per domain.

Usage:  python 02_collect_repositories/count_repositories_per_domain.py
"""
import pandas as pd
import os

def count_domains(input_file):
    """
    Reads a CSV, counts repositories per Domain, and saves to a text file.
    """
    if not os.path.exists(input_file):
        # Try looking in the parent directory if not found in current
        parent_file = os.path.join("..", input_file)
        if os.path.exists(parent_file):
            print(f"   -> Found file in parent directory: {parent_file}")
            input_file = parent_file
        else:
            print(f"❌ File not found: {input_file}")
            return

    try:
        # Load the dataset
        df = pd.read_csv(input_file, low_memory=False)
        
        if 'Domain' not in df.columns:
            print("❌ Error: Column 'Domain' not found in CSV.")
            print("   Available columns:", list(df.columns))
            return

        # Count occurrences of each domain
        domain_counts = df['Domain'].value_counts()
        
        # Prepare output filename: (filename)_record.txt
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_file = f"{base_name}_record.txt"
        
        # Prepare content
        output_lines = []
        output_lines.append("=" * 50)
        output_lines.append("📊 DOMAIN STATISTICS RECORD")
        output_lines.append("=" * 50)
        output_lines.append(f"File Processed: {os.path.basename(input_file)}")
        output_lines.append(f"Total Repositories: {len(df)}")
        output_lines.append("-" * 50)
        output_lines.append(f"{'Domain':<25} | {'Count':<8} | {'%':<6}")
        output_lines.append("-" * 50)
        
        for domain, count in domain_counts.items():
            percent = (count / len(df)) * 100
            output_lines.append(f"{domain:<25} | {count:<8} | {percent:5.1f}%")
        
        output_lines.append("-" * 50)
            
        output_content = "\n".join(output_lines)
        
        # Write to file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(output_content)
            
        print(output_content)
        print(f"\n✅ Saved record to: {output_file}")

    except Exception as e:
        print(f"❌ Error processing file: {e}")

if __name__ == "__main__":
    print("--- Domain Counter ---")
    user_input = input("Enter CSV filename: ").strip()
    
    # Remove quotes if user dragged and dropped file path
    user_input = user_input.replace('"', '').replace("'", "")
    
    if user_input:
        # Auto-add extension if missing
        if not os.path.exists(user_input) and not user_input.lower().endswith(".csv"):
             user_input += ".csv"
             
        count_domains(user_input)
    else:
        print("❌ No file entered.")
