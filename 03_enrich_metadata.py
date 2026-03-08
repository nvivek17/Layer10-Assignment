import json
import requests
import time
from config import GITHUB_TOKEN
# 1. YOUR GITHUB TOKEN
GITHUB_TOKEN = GITHUB_TOKEN 
headers = {"Authorization": f"token {GITHUB_TOKEN}"}

def get_github_date(url):
    """Fetches the 'created_at' date from GitHub API."""
    try:
        clean_url = url.strip('"').strip("'")
        # Convert web URL to API URL
        api_url = clean_url.replace("https://github.com/","https://api.github.com/repos/")
        
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            return response.json().get('created_at')
        elif response.status_code == 403:
            print("Rate limit reached! Wait 60s...")
            return "RATE_LIMIT"
        else:
            print(f"Error {response.status_code} for {api_url}")
            return None
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return None

input_file = "Data/extracted_memory.json"
output_file = "Data/extracted_memory_with_dates.json"

with open(input_file, "r") as f:
    memory_data = json.load(f)

print(f"Starting enrichment for {len(memory_data)} extracted issues...")

# 3. Process each issue in the JSON
for i, item in enumerate(memory_data):
    # Check if we already have a timestamp 
    if 'timestamp' not in item or not item['timestamp']:
        url = item.get('source_url')
        if url:
            date = get_github_date(url)
            
            if date == "RATE_LIMIT":
                time.sleep(60) 
                date = get_github_date(url) # Try once more

            item['timestamp'] = date
            print(f"[{i+1}/{len(memory_data)}] Linked Date: {date} to {url}")
            time.sleep(0.5)

with open(output_file, "w") as f:
    json.dump(memory_data, f, indent=4)

print(f"\nSUCCESS! Enhanced memory saved to {output_file}")