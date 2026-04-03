import os
import json
from apps.api.learning.memory_store import MemoryStore, MEMORY_FILE

class MemoryRetrieval:
    def find_similar_successes(self, incident_text, limit=5):
        if not os.path.exists(MEMORY_FILE):
            return []
            
        try:
            with open(MEMORY_FILE, "r") as f:
                db = json.load(f)
        except:
            return []

        query_vec = MemoryStore.embed_text(incident_text)
        results = []
        
        for record in db:
            p = record.get("payload", {})
            if not p.get("success") or p.get("learning_tag") != "SUCCESS_STABLE":
                continue
            
            # حساب Cosine Similarity رياضياً
            score = sum(a * b for a, b in zip(query_vec, record["vector"]))
            results.append({"score": score, "payload": p})

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def get_success_count(self, incident_text, similarity_threshold=0.55) -> int:
        hits = self.find_similar_successes(incident_text)
        return sum(1 for h in hits if h["score"] >= similarity_threshold)

    def build_experience_context(self, incident_text, similarity_threshold=0.55) -> str:
        hits = self.find_similar_successes(incident_text)
        usable = [h for h in hits if h["score"] >= similarity_threshold]
        if not usable: return "No similar successful incidents found in memory."
        
        lines = []
        for h in usable[:3]:
            p = h["payload"]
            lines.append(f"- Similar past incident: action={p.get('action_taken')}, target={p.get('target')}, saved=${p.get('impact_dollars')}")
        return "\n".join(lines)
