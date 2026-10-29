"""
Utility - sum totals from issue-scraping log files.

Usage:  python tools/check_log_total.py
"""
import re
import os

# Get the directory where this script is located (Tools) and go up one level
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "..", "search_summary_log_final.txt")

def main():
    if not os.path.exists(LOG_FILE):
        print(f"❌ File '{LOG_FILE}' not found.")
        return

    total_saved = 0
    total_found = 0
    domain_stats = {}

    print(f"📂 Reading {LOG_FILE}...\n")

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            # Regex to extract Domain, Found, and Saved counts
            # Line format: Domain: Government | Keyword: public-housing | Found: 2 | Saved: 2 | ...
            match = re.search(r"Domain:\s*(.*?)\s*\|\s*Keyword:.*\|\s*Found:\s*(\d+)\s*\|\s*Saved:\s*(\d+)", line)
            if match:
                domain = match.group(1)
                found = int(match.group(2))
                saved = int(match.group(3))

                total_found += found
                total_saved += saved

                if domain not in domain_stats:
                    domain_stats[domain] = {"found": 0, "saved": 0}
                
                domain_stats[domain]["found"] += found
                domain_stats[domain]["saved"] += saved

    # Print Table
    print("-" * 45)
    print(f"{'Domain':<20} | {'Found':<10} | {'Saved':<10}")
    print("-" * 45)
    
    for domain, stats in domain_stats.items():
        print(f"{domain:<20} | {stats['found']:<10} | {stats['saved']:<10}")

    print("-" * 45)
    print(f"{'TOTAL':<20} | {total_found:<10} | {total_saved:<10}")
    print("-" * 45)

if __name__ == "__main__":
    main()