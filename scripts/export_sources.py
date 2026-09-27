"""Phase 6: export the source list (CSV + MD) used by the corpus.

Reads the scheme registry from config and the ingestion stats from
data/chunks/chunks.jsonl, so the exported list always matches the built index.
"""

import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config

CSV_PATH = config.PROJECT_ROOT / "doc" / "sources.csv"
MD_PATH = config.PROJECT_ROOT / "doc" / "sources.md"

CSV_FIELDS = [
    "scheme_key",
    "scheme_name",
    "category",
    "source_url",
    "source_type",
    "last_updated",
    "chunk_count",
    "sections",
    "snapshot_path",
]


def load_chunk_stats():
    stats = {}
    path = config.CHUNKS_DIR / "chunks.jsonl"
    if not path.exists():
        return stats
    sections = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            chunk = json.loads(line)
            key = chunk["scheme_key"]
            entry = stats.setdefault(
                key,
                {"chunk_count": 0, "sections": Counter(), "last_updated": chunk["last_updated"]},
            )
            entry["chunk_count"] += 1
            sections.setdefault(key, Counter())[chunk["section"]] += 1
    for key, counter in sections.items():
        stats[key]["sections"] = counter
    return stats


def build_rows():
    stats = load_chunk_stats()
    rows = []
    for key, scheme in config.SCHEMES.items():
        stat = stats.get(key, {})
        counter = stat.get("sections", Counter())
        rows.append(
            {
                "scheme_key": key,
                "scheme_name": scheme["name"],
                "category": scheme["category"],
                "source_url": scheme["url"],
                "source_type": "snapshot" if (config.RAW_TEXT_DIR / f"{key}.txt").exists() else "live",
                "last_updated": stat.get("last_updated", ""),
                "chunk_count": stat.get("chunk_count", 0),
                "sections": ", ".join(f"{s}({n})" for s, n in sorted(counter.items())),
                "snapshot_path": f"data/raw/text/{key}.txt",
            }
        )
    return rows


def write_csv(rows):
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_md(rows):
    total_chunks = sum(r["chunk_count"] for r in rows)
    last_updated = sorted({r["last_updated"] for r in rows if r["last_updated"]})
    lines = [
        "# Source List",
        "",
        "Every chunk in the vector store comes from one of the public pages below. "
        "No third-party blogs, no app back-end screenshots.",
        "",
        f"**Schemes:** {len(rows)} · **Total chunks indexed:** {total_chunks} · "
        f"**Last updated from sources:** {', '.join(last_updated) if last_updated else 'n/a'}",
        "",
        "| # | Scheme | Category | Source URL | Last updated | Chunks | Sections |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(rows, start=1):
        sections = r["sections"].replace(", ", "<br>") or "—"
        lines.append(
            f"| {i} | {r['scheme_name']} | {r['category']} | {r['source_url']} | "
            f"{r['last_updated'] or '—'} | {r['chunk_count']} | {sections} |"
        )
    lines += [
        "",
        "## Supplementary links (referenced, not ingested)",
        "",
        f"- SEBI investor education (advice-refusal redirect): {config.EDU_LINK_ADVICE}",
        f"- AMFI factsheet lookup (returns/performance redirect): {config.FACTSHEET_LINK}",
        "",
        "## Provenance",
        "",
        "- Raw page text snapshots: `data/raw/text/<scheme_key>.txt`",
        "- Chunk metadata: `data/chunks/chunks.jsonl` (`source_url`, `section`, `last_updated`)",
        "- Machine-readable copy: `doc/sources.csv` (regenerate with `python scripts/export_sources.py`)",
        "",
    ]
    MD_PATH.write_text("\n".join(lines), encoding="utf-8")


def main():
    rows = build_rows()
    if not rows:
        print("No schemes in config.SCHEMES")
        return
    write_csv(rows)
    write_md(rows)
    print(f"Wrote {CSV_PATH.relative_to(config.PROJECT_ROOT)}")
    print(f"Wrote {MD_PATH.relative_to(config.PROJECT_ROOT)}")
    for r in rows:
        print(f"  {r['scheme_key']:<20} {r['chunk_count']:>3} chunks  {r['source_url']}")


if __name__ == "__main__":
    main()
