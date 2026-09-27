import config


class Embedder:
    """ONNX MiniLM via fastembed — no PyTorch, so the UI can boot on small hosts."""

    def __init__(self, model_name=config.EMBEDDING_MODEL):
        from fastembed import TextEmbedding

        self.model = TextEmbedding(model_name=model_name)

    def encode(self, texts, batch_size=32):
        vectors = self.model.embed(list(texts), batch_size=batch_size)
        return [list(map(float, e)) for e in vectors]

    def encode_query(self, text):
        return self.encode([text])[0]
