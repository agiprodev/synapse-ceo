from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import hashlib

class MemoryService:
    def __init__(self, qdrant_url: str, embedding_provider):
        self.client = QdrantClient(url=qdrant_url)
        self.embedding_provider = embedding_provider
        self.collection = "incident_memory"
        self.vector_size = 768
        self._ensure_collection()

    def _ensure_collection(self):
        try:
            cols = self.client.get_collections().collections
            if not any(c.name == self.collection for c in cols):
                self.client.create_collection(
                    collection_name=self.collection,
                    vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE)
                )
        except: pass

    def _make_id(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]

    def upsert_incident(self, text: str, metadata: dict):
        vector = self.embedding_provider.embed(text)
        point_id = self._make_id(text + str(metadata.get("timestamp", "")))
        self.client.upsert(
            collection_name=self.collection,
            points=[PointStruct(id=point_id, vector=vector, payload={"text": text, **metadata})]
        )
        return point_id

    def search_similar(self, query_text: str, limit: int = 3):
        try:
            vector = self.embedding_provider.embed(query_text)
            results = self.client.search(collection_name=self.collection, query_vector=vector, limit=limit)
            return [{"text": r.payload["text"], "metadata": r.payload, "score": r.score} for r in results]
        except: return []
