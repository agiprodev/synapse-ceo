import uuid
from datetime import datetime
from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer

# الاتصال بـ Qdrant (تأكد من تشغيله على بورت 6333)
try:
    qdrant = QdrantClient(host="localhost", port=6333)
    encoder = SentenceTransformer('all-MiniLM-L6-v2')
    COLLECTION_NAME = "incidents_memory"
except:
    print("⚠️ Qdrant connection skipped in memory module.")

class ExperienceSaver:
    @staticmethod
    def save_success(incident_log: str, action_taken: str, impact_score: float):
        """
        حفظ التجربة الناجحة في الذاكرة طويلة الأمد
        """
        try:
            # تحويل النص لمتجه (Embedding)
            vector = encoder.encode(incident_log).tolist()
            
            # تخزين في Qdrant
            qdrant.upsert(
                collection_name=COLLECTION_NAME,
                points=[
                    models.PointStruct(
                        id=str(uuid.uuid4()),
                        vector=vector,
                        payload={
                            "issue": incident_log,
                            "action": action_taken,
                            "score": impact_score,
                            "timestamp": datetime.utcnow().isoformat(),
                            "verified": True
                        }
                    )
                ]
            )
            print(f"🧠 [MEMORY] Knowledge optimized and saved for: {action_taken}")
        except Exception as e:
            print(f"❌ [MEMORY] Failed to save experience: {e}")
