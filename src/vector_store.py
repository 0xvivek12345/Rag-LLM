import config

META_FIELDS = (
    "scheme_key",
    "scheme_name",
    "category",
    "section",
    "source_url",
    "source_type",
    "last_updated",
    "char_count",
)


class VectorStore:
    def __init__(self, persist_dir=config.CHROMA_DIR, collection_name=config.CHROMA_COLLECTION):
        import chromadb

        self.client = chromadb.PersistentClient(path=str(persist_dir))
        self.collection = self._get_collection(collection_name)

    def _get_collection(self, name):
        return self.client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})

    def rebuild(self, chunks, embeddings):
        try:
            self.client.delete_collection(config.CHROMA_COLLECTION)
        except Exception:
            pass
        self.collection = self._get_collection(config.CHROMA_COLLECTION)
        self.collection.add(
            ids=[c["chunk_id"] for c in chunks],
            documents=[c["text"] for c in chunks],
            metadatas=[{k: c[k] for k in META_FIELDS} for c in chunks],
            embeddings=embeddings,
        )

    def count(self):
        return self.collection.count()

    def query(self, embedding, k=5, where=None):
        return self.collection.query(
            query_embeddings=[embedding],
            n_results=k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

    def peek(self, n=3):
        return self.collection.peek(n)
