import json
from datetime import datetime
from rapidfuzz import fuzz
from groq import Groq
import time
from config import GROQ_API_KEY
client = Groq(api_key=GROQ_API_KEY)
# 1. Setup
def judge_relationship(claim_a, claim_b):
    prompt = f"""
    You are a Senior Software Architect. Compare these two technical claims and determine their relationship.

    EXAMPLES:
    - SAME: "React setup failing" vs "React installation is broken" -> SAME
    - CONFLICT: "React setup fixed" vs "React setup failing" -> CONFLICT
    - DIFFERENT: "React setup failing" vs "Node version update" -> DIFFERENT

    CLAIMS TO EVALUATE:
    Claim A: "{claim_a}"
    Claim B: "{claim_b}"

    Instructions:
    - SAME: They report the same technical state/fact.
    - CONFLICT: They report opposite states of the same feature (Fixed vs Broken).
    - DIFFERENT: They describe unrelated technical events.

    Return ONLY: SAME, CONFLICT, or DIFFERENT.
    """
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile"
        )
        return response.choices[0].message.content.strip().upper()
    except Exception as e:
        print(f"API Error (Wait 60s): {e}")
        time.sleep(60) 
        return "DIFFERENT"

with open("Data/deduped_artifacts.json", "r") as f:
    data = json.load(f)
with open("Data/canonicalized_entities.json", "r") as f:
    entity_registry = json.load(f)

canonical_map = {alias.lower().strip(): official for official, details in entity_registry.items() for alias in details.get('aliases', [])}
knowledge_graph = {} 

STOP_WORDS = {"the", "a", "an", "is", "are", "was", "were", "to", "of", "in", "and", "or", "it", "this", "that", "with", "for", "on"}

print(f"Building Memory Graph with Llama-3.3-70B Logic...")

for issue in data:
    url = issue['source_url']
    ts_str = issue.get('timestamp') or '2000-01-01T00:00:00Z'
    current_ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))

    # Safe Entity Extraction
    issue_entities = []
    for ent in issue.get('entities', []):
        name = ent.get('name')
        if isinstance(name, str) and name.strip():
            official = canonical_map.get(name.strip().lower(), name.strip())
            if official not in issue_entities: issue_entities.append(official)
    
    if not issue_entities: issue_entities = ["General"]
    claims = issue.get('claims', issue.get('items', {}).get('claims', []))
    
    for c in claims:
        new_text = c.get('claim') or c.get('Claim') or "Unknown Claim"
        new_evidence = c.get('evidence_quote') or c.get('Evidence_quote') or "No quote"
        new_words = {w.lower() for w in new_text.split() if w.lower() not in STOP_WORDS and len(w) > 2}
        
        match_found = False

        for entity in issue_entities:
            if entity == "General": continue 
            if entity not in knowledge_graph: knowledge_graph[entity] = []
            
            for existing in knowledge_graph[entity]:
                # Idempotency
                if any(ev.get('source') == url for ev in existing['evidence']):
                    match_found = True
                    break

                # Keyword Filter
                existing_words = existing.get('keywords', set())
                if not (new_words & existing_words): continue 

                # Hybrid Check
                similarity = fuzz.token_set_ratio(new_text.lower(), existing['text'].lower())
                
                relation = "DIFFERENT"
                if similarity > 95:
                    relation = "SAME"
                elif similarity > 60: # trigger for the AI to judge
                    relation = judge_relationship(new_text, existing['text'])
                    print("AI JUDGE: ",new_text,"vs",existing['text'],relation)
                    time.sleep(1.0) 

                if "SAME" in relation:
                    existing['evidence'].append({"quote": new_evidence, "source": url, "timestamp": ts_str})
                    existing['merge_history'].append({"original_text": new_text, "source": url, "reason": "SAME","timestamp": ts_str })
                    if current_ts > existing['latest_ts_obj']:
                        existing['latest_ts_obj'] = current_ts
                        existing['text'] = new_text 
                    match_found = True
                    break

                elif "CONFLICT" in relation:
                    if current_ts > existing['latest_ts_obj']:
                        print(f"CONFLICT RESOLVED: {url} is the NEW Truth.")
                        existing['status'] = f"HISTORICAL (Superseded by {url})"
                        existing['is_current'] = False
                    # Allow the loop to finish so the new "Truth" is added as its own CURRENT node

        if not match_found:
            target_entity = issue_entities[0]
            if target_entity not in knowledge_graph: knowledge_graph[target_entity] = []
            knowledge_graph[target_entity].append({
                "text": new_text,
                "entity": target_entity,
                "keywords": new_words,
                "status": "CURRENT",
                "is_current": True,
                "latest_ts_obj": current_ts,
                "created_at": ts_str,
                "evidence": [{"quote": new_evidence, "source": url, "timestamp": ts_str}],
                "merge_history": []
            })

# Cleanup and Export
final_graph = []
for entity_claims in knowledge_graph.values():
    for fact in entity_claims:
        if 'latest_ts_obj' in fact: del fact['latest_ts_obj']
        if 'keywords' in fact: del fact['keywords']
        final_graph.append(fact)

with open("Data/final_memory_graph.json", "w") as f:
    json.dump(final_graph, f, indent=4)

print(f"SUCCESS! Logic-heavy Memory Graph built.")