class GeminiEmbeddingProvider:
    def __init__(self, client, model: str = "text-embedding-004"):
        self.client = client
        self.model = model

    def embed(self, text: str):
        try:
            # استخدام الطريقة المباشرة لـ SDK الجديد
            result = self.client.models.embed_content(
                model=self.model,
                contents=text,
            )
            return result.embeddings[0].values
        except Exception as e:
            # لو فشل، جرب الموديل بكلمة models/
            try:
                result = self.client.models.embed_content(
                    model=f"models/{self.model}",
                    contents=text,
                )
                return result.embeddings[0].values
            except:
                print(f"❌ Critical Embedding Failure: {e}")
                return [0.0] * 768
