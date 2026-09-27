import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from src.answer_generator import generate_answer
from src.embedder import Embedder
from src.guardrails import check_query
from src.retriever import Retriever
from src.vector_store import VectorStore

WELCOME = "Welcome to the HDFC Mutual Fund FAQ Assistant."
EXAMPLES = [
    "What is the expense ratio of HDFC Large Cap Fund?",
    "What is the lock-in period of the ELSS fund?",
    "How do I download my capital gains statement?",
]

DEMO_QUERIES = [
    "What is the expense ratio of HDFC Large Cap Fund?",
    "What is the minimum SIP for HDFC Small Cap Fund?",
    "What is the lock-in period of the ELSS fund?",
    "Should I buy HDFC Small Cap Fund?",
    "My PAN is ABCDE1234F, which fund is best?",
    "What are the returns of HDFC Flexi Cap?",
]


def answer_card(result):
    print(f"\nAssistant: {result['answer']}")
    print(f"Source: {result['citation_url']}")
    print(f"{config.LAST_UPDATED_LABEL} {result['last_updated']}")


def handle(query, retriever):
    guard = check_query(query)
    if guard["action"] == "allow":
        hits = retriever.retrieve(query)
        if not hits:
            print("\nAssistant: Sorry, I could not find this in my sources. Please try another question.")
            return
        answer_card(generate_answer(query, hits))
    else:
        print(f"\nAssistant: {guard['message']}")
        if guard["link"]:
            print(f"Link: {guard['link']}")


def main():
    parser = argparse.ArgumentParser(description="HDFC MF FAQ RAG chatbot (CLI)")
    parser.add_argument("--demo", action="store_true", help="run a fixed set of demo questions and exit")
    args = parser.parse_args()

    print(WELCOME)
    print("Try:")
    for e in EXAMPLES:
        print(f"  - {e}")
    print(config.DISCLAIMER)
    print(config.DISCLAIMER_LONG)

    retriever = Retriever(Embedder(), VectorStore())

    if args.demo:
        for q in DEMO_QUERIES:
            print(f"\nYou: {q}")
            handle(q, retriever)
        return

    while True:
        try:
            query = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not query or query.lower() in ("quit", "exit"):
            break
        handle(query, retriever)


if __name__ == "__main__":
    main()
