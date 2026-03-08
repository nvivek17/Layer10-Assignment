import json
import time
from rapidfuzz import process, fuzz
from groq import Groq
from config import GROQ_API_KEY
# 1. Setup
client = Groq(api_key=GROQ_API_KEY)

def get_canonical_ai(name_cluster, type_list):
    if len(name_cluster) <= 1: 
        return name_cluster[0], type_list[0]
    
    prompt = f"""
    Compare these variations of the same technical entity found in different documents:
    Names: {name_cluster}
    Suggested Types: {type_list}
    
    Rules:
    1. If they are the same entity (e.g., 'GitHub' and 'github'), merge them.
    2. Pick the MOST professional 'Official Name' (usually PascalCase).
    3. Pick the MOST accurate 'Official Type' from the suggested list.
    4. If they are truly different (e.g., 'iPhone 5s' vs 'iPhone 5c'), return 'SPLIT'.

    Return ONLY in this format: Name | Type (or 'SPLIT')
    """
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant"
        )
        res_text = response.choices[0].message.content.strip()
        if "SPLIT" in res_text.upper():
            return "SPLIT", "SPLIT"
        
        # Split the AI response into Name and Type
        parts = res_text.split("|")
        return parts[0].strip(), parts[1].strip()
    except:
        return name_cluster[0], type_list[0]

# GLOBAL NORMALIZATION (Ignoring Type Blocks)
with open("Data/deduped_artifacts.json", "r") as f:
    data = json.load(f)

# key: lowercase_name -> value: { 'original_names': set(), 'types': set(), 'count': int }
normalization_pool = {}

print("Normalizing global entity pool...")
for issue in data:
    for ent in issue.get('entities', []):
        raw_name = ent.get('name')
        if raw_name and isinstance(raw_name, str):
            name = raw_name.strip()
            low_name = name.lower()
            etype = ent.get('type', 'General')
            
            if low_name not in normalization_pool:
                normalization_pool[low_name] = {
                    "originals": {name},
                    "types": {etype},
                    "count": 1
                }
            else:
                normalization_pool[low_name]["originals"].add(name)
                normalization_pool[low_name]["types"].add(etype)
                normalization_pool[low_name]["count"] += 1

# CROSS-TYPE CANONICALIZATION 
canonical_map = {} # Original Name -> Official Name
master_type_map = {} # Official Name -> Official Type
processed_low_names = set()

# Sort by most frequent entities
sorted_keys = sorted(normalization_pool.keys(), key=lambda k: normalization_pool[k]['count'], reverse=True)

for low_name in sorted_keys:
    if low_name in processed_low_names: continue
    
    # Fuzzy match across the WHOLE pool (not blocked by type)
    matches = process.extract(
        low_name, 
        normalization_pool.keys(), 
        scorer=fuzz.ratio, 
        score_cutoff=90 
    )
    
    cluster_low_names = [m[0] for m in matches if m[0] not in processed_low_names]
    if not cluster_low_names: continue

    # Gather all original variations and types for the AI to judge
    all_originals = []
    all_types = []
    for ln in cluster_low_names:
        all_originals.extend(list(normalization_pool[ln]['originals']))
        all_types.extend(list(normalization_pool[ln]['types']))
        processed_low_names.add(ln)

    # AI decides Name AND Type
    official_name, official_type = get_canonical_ai(all_originals, all_types)
    
    if official_name == "SPLIT":
        # If split, keep original names as they were
        for orig in all_originals:
            canonical_map[orig] = orig
            master_type_map[orig] = normalization_pool[orig.lower()]['types'].pop()
    else:
        # Merge the whole cluster
        for orig in all_originals:
            canonical_map[orig] = official_name
            master_type_map[official_name] = official_type
    
    print(f"Merged {all_originals} -> {official_name} ({official_type})")
    time.sleep(0.4)

# BUILD REGISTRY
final_registry = {}
for issue in data:
    source = issue['source_url']
    for ent in issue.get('entities', []):
        raw_name = ent.get('name')
        if raw_name and isinstance(raw_name, str):
            orig_name = raw_name.strip()
            official = canonical_map.get(orig_name, orig_name)
            etype = master_type_map.get(official, ent.get('type'))
            
            if official not in final_registry:
                final_registry[official] = {
                    "type": etype,
                    "total_mentions": 0,
                    "aliases": set(),
                    "mentions_log": []
                }
            
            reg = final_registry[official]
            reg["total_mentions"] += 1
            reg["aliases"].add(orig_name)
            reg["mentions_log"].append({"original_name": orig_name, "source": source, "time": issue.get('timestamp')})

for official in final_registry:
    final_registry[official]["aliases"] = list(final_registry[official]["aliases"])

with open("Data/canonicalized_entities.json", "w") as f:
    json.dump(final_registry, f, indent=4)

print("\nSUCCESS! GitHub/Github and other cross-type duplicates are now merged.")