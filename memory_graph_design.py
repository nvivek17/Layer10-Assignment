from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime

@dataclass
class Evidence:
    quote: str
    source: str  
    timestamp: str

@dataclass
class Claim:
    text: str
    status: str = "CURRENT"
    confidence: float = 0.9
    evidence: List[Evidence] = field(default_factory=list)
    merge_history: List[dict] = field(default_factory=list)

@dataclass
class Entity:
    name: str
    entity_type: str
    aliases: List[str]
    mentions_log: List[dict]
    is_active: bool = True # For Soft Deletes/Redactions

class MemoryGraph:
    def __init__(self):
        self.nodes: Dict[str, Entity] = {}
        self.claims: List[Claim] = []
        self.observability_log = [] # Log ingestion errors or conflicts

    def add_claim(self, claim: Claim):
        self.claims.append(claim)
        self.observability_log.append({
            "timestamp": datetime.now().isoformat(),
            "action": "INGEST",
            "status": "SUCCESS"
        })

    def redact_source(self, source_url: str):
        # Conceptual design for privacy compliance
        for claim in self.claims:
            claim.evidence = [e for e in claim.evidence if e.source_url != source_url]
        print(f"Redacted source {source_url} from all claims.")


