import json
import hashlib
import re
from rapidfuzz import fuzz

def clean_for_comparison(text):
    """
    Removes 'Noise' that prevents duplicates from being caught.
    This handles the 'email quoting/forwarding' requirement.
    """
    if not text: return ""
    #Removing common email headers/prefixes
    text = re.sub(r'^(re:|fwd:|\[.*?\])\s*', '', str(text), flags=re.IGNORECASE)
    # Removing 'Forwarded message' lines
    text = re.sub(r'-+ Forwarded message -+', '', text, flags=re.IGNORECASE)
    #Strip common signatures
    text = re.split(r'Sent from my|Best regards|Thanks,', text, flags=re.IGNORECASE)[0]
    text = re.sub(r"number of crashes: \d+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"impacted devices: \d+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"there's a lot more information about this crash on.*", "", text, flags=re.IGNORECASE)
    # 4. Standardize whitespace and lowercase

    return " ".join(text.lower().split())

def generate_hash(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

input_file = "Data/extracted_memory_complete.json"
output_file = "Data/deduped_artifacts.json"

with open(input_file, "r") as f:
    data = json.load(f)

print(f"Starting Artifact Deduplication on {len(data)} items...")

# The Logic: Cluster by Similarity
master_artifacts = [] # This will hold our 'Unique' messages
duplicates_count = 0

for item in data:
    body = item.get('body', '')
    cleaned_body = clean_for_comparison(body)
    
    is_duplicate = False
    reason=f""
    match_master=None
    # Check current item against our 'Master' list
    for master in master_artifacts:
        # Check Hash
        if generate_hash(cleaned_body) == generate_hash(master['_cleaned_body']):
            is_duplicate = True
            match_master = master
            reason = "Exact Hash Match"
            break
        
        #Check Fuzzy Similarity (Catches 'Near-Identical')
        similarity = fuzz.ratio(cleaned_body, master['_cleaned_body'])
        if similarity > 92:
            is_duplicate = True
            match_master = master
            reason = f"Fuzzy Match ({similarity:.1f}%)"
            break

    if is_duplicate and match_master is not None:
        # REVERSIBILITY: Don't delete. Add this URL to the master's record.
        match_master['duplicate_sources'].append({
            "url": item['source_url'],
            "reason": reason,
            "original_body_snippet": body[:100] + "..."
        })
        duplicates_count += 1
    else:
        # NEW UNIQUE ARTIFACT: We store the cleaned body temporarily for comparisons (deleted at end)
        item['_cleaned_body'] = cleaned_body 
        item['duplicate_sources'] = []
        master_artifacts.append(item)

#Clean up temporary fields and Save
for m in master_artifacts:
    if '_cleaned_body' in m:
        del m['_cleaned_body']

with open(output_file, "w") as f:
    json.dump(master_artifacts, f, indent=4)

print(f"\nSUCCESS: Artifact Deduplication Complete.")
print(f"Unique Artifacts Kept: {len(master_artifacts)}")
print(f"Near-Duplicates Linked: {duplicates_count}")