"""
Step 02.1 - Search GitHub for repositories matching the domain keywords (report 4.3.2, Steps 2.1-2.2).
Uses recursive date slicing to get around the 1,000-results limit of the GitHub search API.
Criteria: stars >= MIN_STARS, updated since ACTIVE_SINCE (GDPR date, 2016-05-24).
Needs GITHUB_TOKEN. Output: found_repositories_<date>_final.csv

Usage:  python 02_collect_repositories/1_find_repositories.py
"""
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))   # project root, for project_env
from project_env import get_secret

import requests
import pandas as pd
import time
import os
import re
from datetime import datetime, timedelta
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ==========================================
# 1. CONFIGURATION & RESEARCH CRITERIA
# ==========================================
GITHUB_TOKEN = get_secret("GITHUB_TOKEN", required=False)   # from .env - never write the token here

# Criteria
MIN_STARS = 10                  
ACTIVE_SINCE = "2016-05-24"     # GDPR Enforcement Date
# 2016-05-24
# 2018-05-25
# Files
OUTPUT_FILE = f"found_repositories_{ACTIVE_SINCE}_final.csv"
KEYWORD_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "01_keywords", "Keyword_domain.md")

# Global Set to prevent duplicates across different time slices
SEEN_URLS = set()

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def get_session():
    """Creates a robust session with retry logic."""
    retry_strategy = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("https://", adapter)
    session.headers.update({
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    })
    return session

def load_keywords_from_md(filepath):
    """Parses the markdown file to extract Python lists of keywords."""
    if not os.path.exists(filepath):
        print(f"❌ Error: Keyword file '{filepath}' not found.")
        return {}
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    keywords = {}
    lists = re.findall(r'(\w+)\s*=\s*\[(.*?)\]', content, re.DOTALL)
    for var_name, list_body in lists:
        clean_name = var_name.replace("_keywords", "")
        domain_key = clean_name.capitalize()
        items = re.findall(r'["\']([^"\']+)["\']', list_body)
        if domain_key not in keywords:
            keywords[domain_key] = []
        keywords[domain_key].extend(items)
    for k in keywords:
        keywords[k] = list(set(keywords[k]))
    return keywords

def get_total_count(session, query):
    """Checks how many results exist for a query without downloading them."""
    url = f"https://api.github.com/search/repositories?q={query}&per_page=1"
    try:
        response = session.get(url)
        if response.status_code == 200:
            return response.json().get("total_count", 0)
        elif response.status_code == 403:
            print("      ⚠️ Rate Limit Hit during check! Sleeping 60s...")
            time.sleep(60)
            return get_total_count(session, query) # Retry
    except Exception as e:
        print(f"      ❌ Error checking count: {e}")
    return 0

# ==========================================
# 3. CORE LOGIC: RECURSIVE SEARCH
# ==========================================
def fetch_and_save(session, query, domain, keyword):
    """Fetches up to 1000 repos (Page 1-10) and saves immediately."""
    found_batch = []
    total_fetched = 0
    
    for page in range(1, 11): # Max 10 pages (1000 items)
        url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page=100&page={page}"
        try:
            response = session.get(url)
            
            if response.status_code == 200:
                items = response.json().get("items", [])
                if not items: break
                total_fetched += len(items)

                for item in items:
                    repo_name = item['full_name']
                    print(f"         > Found: {repo_name}")

                    # Filter: Must have Issues & Not seen before
                    if not item['has_issues']:
                        print(f"           - Skipped: Issues disabled")
                    elif item['html_url'] in SEEN_URLS:
                        print(f"           - Skipped: Duplicate")
                    else:
                        found_batch.append({
                            "Domain": domain,
                            "Keyword": keyword,
                            "Repo_Name": item['full_name'],
                            "URL": item['html_url'],
                            "Stars": item['stargazers_count'],
                            "Description": item['description'],
                            "Created_At": item['created_at'],
                            "Last_Update": item['pushed_at'],
                            "Total_Issues": item['open_issues_count']
                        })
                        SEEN_URLS.add(item['html_url'])
                        print(f"           + Recorded: {repo_name}")
            
            elif response.status_code == 403:
                print("      ⚠️ Rate Limit! Sleeping 60s...")
                time.sleep(60)
                # Note: In a complex loop, we skip the rest of this batch to be safe, 
                # or you could add a retry loop here.
                break 
            
            elif response.status_code == 422:
                break # Limit reached

        except Exception as e:
            print(f"      ❌ Error fetching page {page}: {e}")
            break
        
        time.sleep(1.0) # Politeness delay

    # AUTO-SAVE LOGIC
    if found_batch:
        df = pd.DataFrame(found_batch)
        # Append to CSV. If file doesn't exist, write header.
        header = not os.path.exists(OUTPUT_FILE)
        df.to_csv(OUTPUT_FILE, mode='a', header=header, index=False, encoding='utf-8-sig')
        print(f"      💾 Saved {len(found_batch)} repos to CSV.")
    
    return total_fetched, len(found_batch)

def recursive_search(session, keyword, domain, start_date, end_date):
    """
    The 'Smart' Function:
    Checks if a time range has > 1000 results.
    If YES -> Splits time in half and tries again (Recursive).
    If NO  -> Downloads the data.
    """
    date_str = f"{start_date.strftime('%Y-%m-%d')}..{end_date.strftime('%Y-%m-%d')}"
    
    # Construct Query with Filters
    query = (f'"{keyword}" in:name,description '
             f'stars:>{MIN_STARS} '
             f'pushed:>{ACTIVE_SINCE} '
             f'archived:false '
             f'created:{date_str}')
    
    # 1. Check Size
    count = get_total_count(session, query)
    
    # 2. Decision
    if count == 0:
        return 0, 0

    if count <= 1000:
        # Safe zone! Download it.
        print(f"   ✅ Range {date_str}: Found {count} (Safe). Downloading...")
        return fetch_and_save(session, query, domain, keyword)
    else:
        # Danger zone! Split it.
        print(f"   ✂️ Range {date_str}: Found {count} (>1000). Slicing...")
        
        # Calculate Midpoint
        time_diff = end_date - start_date
        if time_diff.days < 1:
            # Edge case: If 1 day has > 1000 repos, we can't slice further by date easily.
            # We just take the top 1000.
            print(f"   ⚠️ Daily limit exceeded on {date_str}. Taking top 1000.")
            return fetch_and_save(session, query, domain, keyword)

        mid_date = start_date + (time_diff / 2)

        # Recursive Calls (First Half, then Second Half)
        f1, s1 = recursive_search(session, keyword, domain, start_date, mid_date)
        f2, s2 = recursive_search(session, keyword, domain, mid_date, end_date)
        return f1 + f2, s1 + s2

# ==========================================
# 4. MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    if not GITHUB_TOKEN:
        print("❌ Error: GITHUB_TOKEN is missing.")
    else:
        print(f"📂 Loading keywords from {KEYWORD_FILE}...")
        
        # Load keywords
        if os.path.exists(KEYWORD_FILE):
            keywords = load_keywords_from_md(KEYWORD_FILE)
        else:
            print("⚠️ Warning: Keyword file not found. Using test set.")
            keywords = {"Test": ["privacy-by-design"]}

        # Setup Session
        session = get_session()
        
        # Define Global Time Range (2018 to Now)
        start_global = datetime.strptime(ACTIVE_SINCE, "%Y-%m-%d")
        end_global = datetime.now()

        print(f"🚀 Starting Smart Search (Auto-Slicing Mode)")
        print(f"   Time Range: {start_global.date()} to {end_global.date()}")
        print("------------------------------------------------")

        for domain, kw_list in keywords.items():
            print(f"\n📂 Domain: {domain}")
            for kw in kw_list:
                print(f"   🔎 Keyword: {kw}")
                try:
                    # Start the magic
                    # 1. Check Total Count First
                    date_str = f"{start_global.strftime('%Y-%m-%d')}..{end_global.strftime('%Y-%m-%d')}"
                    query = (f'"{kw}" in:name,description '
                             f'stars:>{MIN_STARS} '
                             f'pushed:>{ACTIVE_SINCE} '
                             f'archived:false '
                             f'created:{date_str}')
                    
                    print(f"      🔍 Query: {query}")
                    total_expected = get_total_count(session, query)
                    print(f"   📊 Total Repositories Found: {total_expected}")

                    total_retrieved, total_saved = recursive_search(session, kw, domain, start_global, end_global)
                    
                    print(f"   🏁 Search Finished for '{kw}'. Retrieved: {total_retrieved}/{total_expected} | Saved: {total_saved}")
                    
                    with open("search_summary_log_final.txt", "a", encoding="utf-8") as logf:
                        logf.write(f"Domain: {domain} | Keyword: {kw} | Found: {total_retrieved} | Saved: {total_saved} | Query: {query}\n")

                    if total_retrieved >= total_expected:
                        print("      ✅ All repositories retrieved.")
                    else:
                        print(f"      ⚠️ Warning: Missed {total_expected - total_retrieved} repositories.")
                except Exception as e:
                    print(f"   ❌ Critical Error on keyword {kw}: {e}")

        print("\n🎉 Search Complete. Check your CSV file.")