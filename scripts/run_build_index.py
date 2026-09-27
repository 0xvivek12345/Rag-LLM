import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config

from src.embedder import Embedder
from src.vector_store import VectorStore


def main():
    chunks_path = config.CHUNKS_DIR / "chunks.jsonl"
    chunks = [json.loads(line) for line in chunks_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    embedder = Embedder()
    embeddings = embedder.encode([c["text"] for c in chunks])
    dim = len(embeddings[0])

    emb_path = config.CHUNKS_DIR / "embeddings.txt"
    with open(emb_path, "w", encoding="utf-8") as f:
        f.write(
            f"# Embeddings | model={config.EMBEDDING_MODEL} | dim={dim} "
            f"| L2-normalized | vectors={len(embeddings)}\n\n"
        )
        for c, e in zip(chunks, embeddings):
            vec = ",".join(f"{v:.6f}" for v in e)
            f.write(f"{c['chunk_id']}\t{vec}\n")

    store = VectorStore()
    store.rebuild(chunks, embeddings)
    print(f"Embedded {len(chunks)} chunks (dim={dim})")
    print(f"Embeddings TXT: {emb_path}")
    print(f"Chroma collection '{config.CHROMA_COLLECTION}' count: {store.count()}")
    print(f"Persist dir: {config.CHROMA_DIR}")

    fresh = VectorStore()
    print(f"Fresh-client count (persistence proof): {fresh.count()}")

    for q in ["What is the expense ratio of HDFC Large Cap Fund?", "ELSS lock-in period?"]:
        res = fresh.query(embedder.encode_query(q), k=2)
        print(f"\nQ: {q}")
        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
            print(f"  [dist={dist:.4f}] {meta['scheme_name']} | {meta['section']} | {doc[:80]}...")


if __name__ == "__main__":
    main()
