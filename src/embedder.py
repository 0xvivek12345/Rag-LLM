import config
from sentence_transformers import SentenceTransformer


class Embedder:
    def __init__(self, model_name=config.EMBEDDING_MODEL):
        self.model = SentenceTransformer(model_name)

    def encode(self, texts, batch_size=32):
        embeddings = self.model.encode(
            list(texts),
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [e.tolist() for e in embeddings]

    def encode_query(self, text):
        return self.encode([text])[0]
