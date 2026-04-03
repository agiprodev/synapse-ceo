import os
import json
import math
import hashlib

MEMORY_FILE = "synapse_memory.json"
VECTOR_SIZE = 128

class MemoryStore:
    @staticmethod
    def embed_text(text: str) -> list:
        vec = [0.0] * VECTOR_SIZE
        words = (text or "").lower().split()
        if not words: return vec
        for word in words:
            h = hashlib.sha256(word.encode()).hexdigest()
            idx = int(h[:8], 16) % VECTOR_SIZE
            sign = 1.0 if int(h[8:10], 16) % 2 == 0 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def upsert_success_memory(self, action_id, incident_text, action_taken, target, confidence, impact_dollars, cpu_before, cpu_after, learning_tag="SUCCESS_STABLE"):
        vector = self.embed_text(incident_text)
        record = {
            "id": action_id,
            "vector": vector,
            "payload": {
                "action_taken": action_taken,
                "target": target,
                "confidence": confidence,
                "impact_dollars": impact_dollars,
                "learning_tag": learning_tag,
                "success": True
            }
        }
        
        db = []
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, "r") as f:
                    db = json.load(f)
            except:
                pass
                
        db.append(record)
        with open(MEMORY_FILE, "w") as f:
            json.dump(db, f)
            
        return {"status": "MEMORY_STORED"}
