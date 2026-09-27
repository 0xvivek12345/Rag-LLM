import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.chunker import chunk_scheme, write_chunks
from src.loader import load_corpus


def main():
    parser = argparse.ArgumentParser(description="Phase 2: load + chunk corpus")
    parser.add_argument("--live", action="store_true", help="live-fetch pages instead of using snapshots")
    args = parser.parse_args()

    corpus = load_corpus(live=args.live)
    all_chunks = []
    print(f"{'scheme':<20} {'source':<9} {'chars':>7}  chunks")
    for scheme in corpus:
        chunks = chunk_scheme(scheme)
        all_chunks.extend(chunks)
        print(f"{scheme['scheme_key']:<20} {scheme['source_type']:<9} {len(scheme['text']):>7}  {len(chunks)}")

    jsonl_path, txt_path = write_chunks(all_chunks)
    print(f"\nTotal chunks: {len(all_chunks)}")
    print(f"JSONL: {jsonl_path}")
    print(f"TXT:   {txt_path}")


if __name__ == "__main__":
    main()
