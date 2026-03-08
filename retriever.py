import json
import time
from datetime import datetime
from rapidfuzz import fuzz
from groq import Groq
from config import GROQ_API_KEY
from memory_graph_design import MemoryGraph, Claim, Evidence

class Layer10EliteRetriever:
    def __init__(self, final_graph_path, api_key=GROQ_API_KEY):
        self.client = Groq(api_key=api_key)
        self.graph = []
        
        with open(final_graph_path, "r") as f:
            raw_data = json.load(f)
            for item in raw_data:
                evidences = []
                for ev in item['evidence']:
                    ev_obj = Evidence(
                        quote=ev.get('quote', 'No quote'),
                        source=ev.get('source') or ev.get('source_url') or 'Unknown Source',
                        timestamp=ev.get('timestamp', 'Unknown Time')
                    )
                    evidences.append(ev_obj)

                claim_obj = Claim(
                    text=item['text'],
                    status=item['status'],
                    evidence=evidences,
                    merge_history=item.get('merge_history', [])
                )
                # Attach primary entity for indexing
                claim_obj.primary_entity = item.get('entity', 'General')
                # Set a default confidence if missing
                claim_obj.confidence = item.get('confidence', 0.9)
                
                self.graph.append(claim_obj)

        # --- Indexing logic stays the same ---
        self.index = {}
        for claim in self.graph:
            key = claim.primary_entity.lower()
            if key not in self.index:
                self.index[key] = []
            self.index[key].append(claim)
            
    def get_intent(self, query):
        system_prompt = "You are a Query Parser. Extract the main software/tool/person from the user's question. Return ONLY the name."
        try:
            res = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                model="llama-3.1-8b-instant"
            )
            return res.choices[0].message.content.strip().lower()
        except:
            return None

    def retrieve(self, query):
        """Two-Stage Retrieval: Keyword Lookup -> AI Re-ranking."""
        target_subject = self.get_intent(query)
        
        # Stage 1: Filter by Index
        candidates = self.index.get(target_subject, self.graph)

        # Stage 2: Scoring (Keyword + Status)
        scored_candidates = []
        for c in candidates:
            # We use TokenSetRatio to handle word re-ordering
            text_score = fuzz.token_set_ratio(query.lower(), c.text.lower())
            
            # Recency Bonus: Prioritize 'CURRENT' information
            status_bonus = 30 if c.status == "CURRENT" else 0
            
            final_score = text_score + status_bonus
            if final_score > 50:
                scored_candidates.append((c, final_score))

        # Sort by best score
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        top_k = [pair[0] for pair in scored_candidates[:10]] # Take top 10

        if not top_k:
            return []

        # Semantic Re-Ranking & Conflict Handling
        # We ask the AI to pick the most relevant while checking for conflicts
        facts_list = "\n".join([f"- [{f.status}] {f.text}" for f in top_k])
        
        rerank_prompt = f"""
        User Question: {query}
        Available Facts in Memories:
        {facts_list}

        TASK:
        1. Select up to 3 facts that DIRECTLY answer the user's question.
        2. If NONE of the facts are relevant to the question (e.g. asking about cake when the data is about code), return ONLY the word 'NONE'.
        3. Prioritize CURRENT facts over HISTORICAL ones unless the user asks for history.

        Return ONLY the selected facts, one per line. No introduction.
        """
        
        try:
            res = self.client.chat.completions.create(
                messages=[{"role": "user", "content": rerank_prompt}],
                model="llama-3.3-70b-versatile" 
            )
            ai_response = res.choices[0].message.content.strip()

            if "NONE" in ai_response.upper():
                print(f"DEBUG: 70B rejected query '{query}' as out-of-bounds i.e corresponding information about this topic is not available.")
                return []

            ai_choices = ai_response.split('\n')
            final_selection = []
            for choice in ai_choices:
                for obj in top_k:
                    if obj.text.lower() in choice.lower() or choice.lower() in obj.text.lower():
                        if obj not in final_selection:
                            final_selection.append(obj)
            return final_selection[:3]
        except Exception as e:
            print(f"70B Error: {e}")
            return top_k[:3] # Fallback to top scored

    def query(self, user_query):
        results = self.retrieve(user_query)
        context_pack = {"query": user_query, "memories": []}

        for r in results:
            # Convert all evidence objects into a list of dictionaries
            all_grounding = [
                {
                    "quote": ev.quote,
                    "source_url": ev.source,
                    "timestamp": ev.timestamp
                } for ev in r.evidence
            ]
            
            context_pack["memories"].append({
                "fact": r.text,
                "status": r.status,
                "confidence": r.confidence,
                "all_grounding": all_grounding, # Now returning the WHOLE list
                "history_count": len(r.merge_history)
            })
        return context_pack

#TEST EXECUTION
if __name__ == "__main__":
    # Ensure your paths are correct!
    RETRIEVER = Layer10EliteRetriever("Data/final_memory_graph.json", "YOUR_GROQ_KEY")
    
    test_q = "What is the status of the React setup?"
    print(json.dumps(RETRIEVER.query(test_q), indent=4))