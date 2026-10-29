"""
Step 04.3 - Inter-rater reliability: percent agreement between the two coders (report 4.3.3, Step 3.4).
Each issue = binary vector over taxonomy subcategories (1 = assigned).

Usage:  python 04_annotation/3_percent_agreement.py
"""
import csv
import os
from itertools import combinations

# --- CONFIGURATION ---
# Set the row number that contains the header.
# The first row is 0, the second is 1, and so on.
# Data reading will start on the line AFTER this row.
HEADER_ROW_INDEX = 4
# --- END CONFIGURATION ---

def get_data_as_vectors(filepath):
    """Helper function to read the CSV and convert it into a matrix of vectors."""
    matrix = {}
    num_labels = 0
    
    if not os.path.exists(filepath):
        return matrix, 0

    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.reader(f)
        try:
            # Skip rows before the header
            for _ in range(HEADER_ROW_INDEX):
                next(reader)
            header = next(reader) # Read the specified header row
            num_labels = len(header) - 2
        except StopIteration:
            return matrix, 0 # Empty file

        for row in reader:
            if not row: continue # Skip empty rows
            coder = row[0].strip()
            issue = row[1].strip()
            
            # Skip rows with missing coder or issue ID (e.g. empty lines or metadata rows)
            if not coder or not issue:
                continue
            
            label_vector = []
            # Start from the 3rd column (index 2)
            for i in range(2, len(row)):
                try:
                    if int(float(row[i])) == 1:
                        label_vector.append(1)
                    else:
                        label_vector.append(0)
                except (ValueError, TypeError):
                    label_vector.append(0)
            
            # Pad the vector if the row was shorter than the header
            while len(label_vector) < num_labels:
                label_vector.append(0)
            
            if issue not in matrix:
                matrix[issue] = {}
            matrix[issue][coder] = label_vector
            
    return matrix, num_labels

def calculate_positional_agreement(filepath):
    """
    Calculates agreement based on comparing label vectors position-by-position
    for every pair of coders on every issue.
    """
    matrix, num_labels = get_data_as_vectors(filepath)
    if not matrix:
        return 0.0, 0, 0

    total_agreed_positions = 0
    total_compared_positions = 0
    
    for issue, coders_data in matrix.items():
        coder_names = list(coders_data.keys())
        
        if len(coder_names) < 2:
            continue
            
        coder_pairs = combinations(coder_names, 2)
        
        for pair in coder_pairs:
            coder1, coder2 = pair
            vector1 = coders_data[coder1]
            vector2 = coders_data[coder2]
            
            # Ensure vectors are comparable
            if len(vector1) != num_labels or len(vector2) != num_labels:
                continue

            for i in range(num_labels):
                if vector1[i] == vector2[i]:
                    total_agreed_positions += 1
            
            total_compared_positions += num_labels

    agreement_percent = (total_agreed_positions / total_compared_positions) if total_compared_positions > 0 else 0.0
    
    return agreement_percent, total_agreed_positions, total_compared_positions

def show_scored_parts(filepath):
    output_lines = []
    output_lines.append("\n--- Detailed Score Breakdown (Labels Chosen) ---")

    matrix = {}
    all_coders = set()

    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.reader(f)
        rowcount = 0
        for row in reader:
            if rowcount > HEADER_ROW_INDEX:
                if not row: continue
                coder = row[0].strip()
                issue = row[1].strip()
                
                if not coder or not issue:
                    continue

                all_coders.add(coder)
                
                columncount = 0
                labels = []
                for e in row:
                    if columncount > 1:
                        try:
                            # Use int(float(e)) to handle "1" and "1.0"
                            if int(float(e)) == 1:
                                labels.append('R' + str(columncount-1))
                        except (ValueError, TypeError):
                            pass
                    columncount += 1
                
                if not labels:
                    labels.append('None')
                
                if issue not in matrix:
                    matrix[issue] = {}
                matrix[issue][coder] = labels
            rowcount += 1

    sorted_coders = sorted(list(all_coders))
    header = f"{'No.':<5} | {'Issue ID':<30} | " + " | ".join([f"{c:<15}" for c in sorted_coders])
    output_lines.append(header)
    output_lines.append("-" * len(header))

    for i, issue in enumerate(matrix, 1):
        row_str = f"{i:<5} | {issue:<30}"
        for coder in sorted_coders:
            lbls = matrix[issue].get(coder, ["N/A"])
            lbl_str = ", ".join(lbls)
            row_str += f" | {lbl_str:<15}"
        output_lines.append(row_str)
    output_lines.append("")
    return output_lines

def show_disagreements(filepath):
    output_lines = []
    output_lines.append("\n--- Issues with Disagreements ---")

    matrix = {}
    all_coders = set()

    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.reader(f)
        rowcount = 0
        for row in reader:
            if rowcount > HEADER_ROW_INDEX:
                if not row: continue
                coder = row[0].strip()
                issue = row[1].strip()
                
                if not coder or not issue:
                    continue

                all_coders.add(coder)
                
                columncount = 0
                labels = []
                for e in row:
                    if columncount > 1:
                        try:
                            if int(float(e)) == 1:
                                labels.append('R' + str(columncount-1))
                        except (ValueError, TypeError):
                            pass
                    columncount += 1
                
                if not labels:
                    labels.append('None')
                
                if issue not in matrix:
                    matrix[issue] = {}
                matrix[issue][coder] = labels
            rowcount += 1

    sorted_coders = sorted(list(all_coders))
    header = f"{'No.':<5} | {'Issue ID':<30} | " + " | ".join([f"{c:<15}" for c in sorted_coders])
    output_lines.append(header)
    output_lines.append("-" * len(header))

    for i, issue in enumerate(matrix, 1):
        # Check if all coders have the same labels for this issue
        coders_labels = [matrix[issue].get(c, ["N/A"]) for c in sorted_coders]
        if not all(l == coders_labels[0] for l in coders_labels[1:]):
            row_str = f"{i:<5} | {issue:<30}"
            for coder in sorted_coders:
                lbls = matrix[issue].get(coder, ["N/A"])
                lbl_str = ", ".join(lbls)
                row_str += f" | {lbl_str:<15}"
            output_lines.append(row_str)
    output_lines.append("")
    return output_lines

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    target_file = os.path.join(script_dir, 'Test_data_With_keyword_60.csv')
    output_filename = os.path.join(script_dir, 'agreement_results_Test_data_With_keyword_Final.txt')
    all_output = []

    if os.path.exists(target_file):
        all_output.extend(show_scored_parts(target_file))
        all_output.extend(show_disagreements(target_file))
        agreement, agreed_pos, total_pos = calculate_positional_agreement(target_file)
        all_output.append(f"\n--- Overall Summary ---")
        all_output.append(f"Total positions in agreement: {agreed_pos}")
        all_output.append(f"Total positions NOT in agreement: {total_pos - agreed_pos}")
        all_output.append(f"Total positions compared: {total_pos}")
        all_output.append(f"Overall Positional Percent Agreement: {agreement:.2%}")

        # Write to file and print to console
        output_string = "\n".join(all_output)
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(output_string)
        
        print(output_string)
        print(f"\n✅ Results also saved to: {output_filename}")
    else:
        print(f"File not found: {target_file}")