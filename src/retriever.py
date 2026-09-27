import config


class Retriever:
    def __init__(self, embedder, vector_store, top_k=config.TOP_K):
        self.embedder = embedder
        self.vector_store = vector_store
        self.top_k = top_k

    def retrieve(self, query, scheme_key=None):
        embedding = self.embedder.encode_query(query)
        where = {"scheme_key": scheme_key} if scheme_key else None
        res = self.vector_store.query(embedding, k=self.top_k, where=where)
        hits = []
        ids = res.get("ids", [[]])[0]
        for chunk_id, doc, meta, dist in zip(ids, res["documents"][0], res["metadatas"][0], res["distances"][0]):
            hit = dict(meta)
            hit["chunk_id"] = chunk_id
            hit["text"] = doc
            hit["distance"] = dist
            hits.append(hit)
        return hits
