import json

input_file = "Data/extracted_memory_with_dates.json"
output_file = "Data/cleaned_memory_final.json"

with open(input_file, "r") as f:
    data = json.load(f)

cleaned_data = []

print(f"Initial samples: {len(data)}")

for item in data:
    ts = item.get('timestamp')
    
    if ts and ts != "None" and ts != "null":
        cleaned_data.append(item)
    else:
        print(f"Dropping ungrounded sample (No Timestamp): {item.get('source_url')}")

with open(output_file, "w") as f:
    json.dump(cleaned_data, f, indent=4)

print(f"Final high-quality samples: {len(cleaned_data)}")