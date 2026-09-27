"""Build the vector index on first use when the collection is empty.

A fresh clone (or a Streamlit Community Cloud deploy, where build artifacts are
not committed) has `data/chroma/` empty, so retrieval would return nothing. The
committed page snapshots in `data/raw/text/` are enough to rebuild the exact same
index, so the app self-heals instead of failing.
"""

import config
from src.chunker import chunk_scheme
from src.embedder import Embedder
from src.loader import load_corpus
from src.vector_store import VectorStore


def build_index(store=None, live=False, embedder=None):
    """Chunk the corpus, embed it and load it into the vector store."""
    store = store or VectorStore()
    embedder = embedder or Embedder()
    chunks = [c for scheme in load_corpus(live=live) for c in chunk_scheme(scheme)]
    embeddings = embedder.encode([c["text"] for c in chunks])
    store.rebuild(chunks, embeddings)
    return chunks


def ensure_index(store=None, log=print, embedder=None):
    """Return a populated store, building the index first if it is empty."""
    store = store or VectorStore()
    count = store.count()
    if count:
        return store
    log(f"[setup] Empty vector store - building index from {len(config.SCHEMES)} scheme pages...")
    chunks = build_index(store, embedder=embedder)
    log(f"[setup] Indexed {len(chunks)} chunks into '{config.CHROMA_COLLECTION}'")
    return store
