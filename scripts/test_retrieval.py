import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.embedder import Embedder
from src.guardrails import check_query
from src.index_bootstrap import ensure_index
from src.retriever import Retriever
from src.vector_store import VectorStore

QUERIES = [
    "What is the expense ratio of HDFC Large Cap Fund?",
    "What is the lock-in period of the ELSS fund?",
    "What is the minimum SIP for HDFC Small Cap Fund?",
    "What is the exit load of HDFC Flexi Cap?",
    "What is the riskometer and benchmark of HDFC Balanced Advantage Fund?",
    "How do I download my capital gains statement?",
]

GUARD_QUERIES = [
    "Should I buy HDFC Small Cap Fund?",
    "My PAN is ABCDE1234F, which fund is best?",
    "What are the returns of HDFC Large Cap Fund?",
]


def main():
    embedder = Embedder()
    store = ensure_index(VectorStore(), embedder=embedder)
    retriever = Retriever(embedder, store)
    print(f"Chroma count: {store.count()}\n")

    print("=== Retrieval tests ===")
    for q in QUERIES:
        print(f"Q: {q}")
        hits = retriever.retrieve(q)
        for h in hits[:2]:
            print(f"  [dist={h['distance']:.4f}] {h['scheme_name']} | {h['section']}")
            print(f"    {h['text'][:110]}...")
        print()

    print("=== Guardrail tests ===")
    for q in GUARD_QUERIES:
        g = check_query(q)
        link = f" -> {g['link']}" if g["link"] else ""
        print(f"Q: {q}\n  -> {g['action']}{link}")
        print(f"     {g['message'][:100]}")


if __name__ == "__main__":
    main()
