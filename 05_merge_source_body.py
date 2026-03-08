import json
import pandas as pd

# Loading the CSV 
df = pd.read_csv("Data/miniversion_issues1.csv")
# Clean up the URLs in the CSV to match the JSON 
df['issue_url'] = df['issue_url'].str.strip('"').str.strip("'")


body_lookup = dict(zip(df['issue_url'], df['body']))

#Loading the extracted JSON
input_file = "Data/cleaned_memory_final.json"
output_file = "Data/extracted_memory_complete.json"

with open(input_file, "r") as f:
    extracted_data = json.load(f)

print(f"Injecting bodies into {len(extracted_data)} issues...")

count = 0
for item in extracted_data:
    # Cleaning the URL 
    url = item['source_url'].strip('"').strip("'")
    
    if url in body_lookup:
        item['body'] = body_lookup[url]
        count += 1
    else:
        print(f"Warning: Could not find body for {url}")

with open(output_file, "w") as f:
    json.dump(extracted_data, f, indent=4)

print(f"Success! Injected {count} bodies. Use {output_file} for Phase 3.")