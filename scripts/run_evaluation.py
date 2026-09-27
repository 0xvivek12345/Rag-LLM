"""Phase 6: run the PRD 10 demo checklist and write doc/evaluation_report.md.

Checks, per PRD 10:
  SC-1  the 6 expected query types are answered with a valid citation link
  SC-2  opinionated queries are refused politely (no advice given)
  SC-3  PII inputs are rejected (and never stored)
  SC-4  every answer is <= 3 sentences and carries the "Last updated" note
  SC-5  the ingestion + retrieval stages are demonstrable (artifacts present)
  SC-6  no hallucinated facts (figures traceable to retrieved context)

Exit code is non-zero if any check fails, so this doubles as a regression test.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from src.answer_generator import generate_answer, grounding_score
from src.chunker import SENTENCE_SPLIT_RE
from src.demo_cases import FACTUAL_CASES, GUARDRAIL_CASES
from src.embedder import Embedder
from src.guardrails import PII_PATTERNS, check_query
from src.retriever import Retriever
from src.vector_store import VectorStore

REPORT_PATH = config.PROJECT_ROOT / "doc" / "evaluation_report.md"
GROUNDING_MIN = config.MIN_ANSWER_GROUNDING
WORD_RE = re.compile(r"[a-z0-9]+")


class Checklist:
    def __init__(self):
        self.rows = []

    def add(self, criterion, name, passed, detail):
        self.rows.append(
            {"criterion": criterion, "name": name, "passed": bool(passed), "detail": detail}
        )
        return passed

    @property
    def failed(self):
        return [r for r in self.rows if not r["passed"]]


def _norm_number(token):
    return token.replace(",", "").rstrip(".")


def numbers_in(text):
    return {_norm_number(t) for t in re.findall(r"\d[\d,]*(?:\.\d+)?", text.lower())}


def run_factual_cases(retriever):
    """Retrieve + answer every factual case once; checks reuse the same result."""
    runs = {}
    for case in FACTUAL_CASES:
        query = case["query"]
        if check_query(query)["action"] != "allow":
            runs[query] = {"case": case, "hits": [], "result": None}
            continue
        hits = retriever.retrieve(query)
        result = generate_answer(query, hits) if hits else None
        runs[query] = {"case": case, "hits": hits, "result": result}
    return runs


def sc1_factual_answers(runs, checklist, details):
    corpus_urls = {s["url"] for s in config.SCHEMES.values()}
    for query, run in runs.items():
        case, hits, result = run["case"], run["hits"], run["result"]
        if not hits:
            checklist.add("SC-1", f"answered: {query}", False, "no hits retrieved")
            details.append(f"- `{query}` -> no hits")
            continue
        answer = result["answer"]
        sentences = [s for s in SENTENCE_SPLIT_RE.split(answer) if s.strip()]

        checks = {
            "answer non-empty": bool(answer.strip()),
            "citation is a corpus source": result["citation_url"] in corpus_urls,
            "last_updated present": bool(result["last_updated"]),
            "<= 3 sentences": len(sentences) <= config.ANSWER_MAX_SENTENCES,
        }
        if case["expect_scheme"]:
            top_scheme = hits[0]["scheme_key"]
            checks["expected scheme in top hits"] = any(
                h["scheme_key"] == case["expect_scheme"] for h in hits
            )
            details.append(f"- `{query}` -> top hit {top_scheme}, expected {case['expect_scheme']}")
        else:
            details.append(f"- `{query}` -> corpus-wide FAQ query")
        sections = {h["section"] for h in hits}
        checks["expected section in top hits"] = bool(set(case["expect_sections"]) & sections)

        failed = [k for k, v in checks.items() if not v]
        detail = "; ".join(f"{k}={v}" for k, v in checks.items()) if failed else "all sub-checks pass"
        checklist.add("SC-1", f"answered: {query}", not failed, detail)
        details[-1] += f" | sentences={len(sentences)}, sections={sorted(sections)}"
    return True


def sc2_refusals(checklist, details):
    for case in GUARDRAIL_CASES:
        query = case["query"]
        guard = check_query(query)
        ok_action = guard["action"] == case["expect_action"]
        ok_link = guard["link"] == case["expect_link"]
        ok_message = bool(guard["message"].strip())
        ok = ok_action and ok_link and ok_message
        checklist.add(
            "SC-2" if case["expect_action"] != "reject_pii" else "SC-3",
            f"blocked: {query}",
            ok,
            f"action={guard['action']}, link={'yes' if guard['link'] else 'no'}",
        )
        details.append(
            f"- `{query}` -> {guard['action']} (retrieval/generation skipped)"
        )
    return True


def sc3_no_stored_pii(checklist, details):
    leaked = []
    scanned = []
    for path in [config.CHUNKS_DIR / "chunks.jsonl", config.CHUNKS_DIR / "chunks.txt"]:
        if not path.exists():
            continue
        scanned.append(path.name)
        text = path.read_text(encoding="utf-8")
        for p in PII_PATTERNS:
            if re.search(p, text) or re.search(p, text.lower()):
                leaked.append(f"{path.name}:{p}")
    store = VectorStore()
    docs = store.peek(store.count()).get("documents") or []
    scanned.append(f"{len(docs)} chroma documents")
    for p in PII_PATTERNS:
        for doc in docs:
            if doc and (re.search(p, doc) or re.search(p, doc.lower())):
                leaked.append(f"chroma:{p}")
    details.append(f"- PII scan over {', '.join(scanned)} -> {len(leaked)} match(es)")
    return checklist.add(
        "SC-3", "no PII stored in corpus/vector store", not leaked, ", ".join(leaked) or "clean"
    )


def sc4_answer_shape(runs, checklist, details):
    ui_files = [config.PROJECT_ROOT / "app.py", config.PROJECT_ROOT / "scripts" / "run_chat.py"]
    missing_label = [
        f.name for f in ui_files if "LAST_UPDATED_LABEL" not in f.read_text(encoding="utf-8")
    ]
    details.append(
        f"- `{config.LAST_UPDATED_LABEL}` label rendered by: "
        f"{[f.name for f in ui_files if f.name not in missing_label]}"
    )
    checklist.add(
        "SC-4",
        f"'{config.LAST_UPDATED_LABEL}' rendered by both UIs",
        not missing_label,
        f"missing in {missing_label}" if missing_label else "app.py + run_chat.py",
    )

    over = []
    for query, run in runs.items():
        if not run["result"]:
            continue
        n = len([s for s in SENTENCE_SPLIT_RE.split(run["result"]["answer"]) if s.strip()])
        if n > config.ANSWER_MAX_SENTENCES:
            over.append(f"{query} ({n} sentences)")
    details.append(
        f"- sentence counts across {len(runs)} factual queries: "
        f"limit {config.ANSWER_MAX_SENTENCES} sentences"
    )
    return checklist.add(
        "SC-4", "every answer <= 3 sentences", not over, ", ".join(over) or "all within limit"
    )


def sc5_pipeline_artifacts(checklist, details):
    chunks = []
    chunks_path = config.CHUNKS_DIR / "chunks.jsonl"
    if chunks_path.exists():
        with open(chunks_path, encoding="utf-8") as f:
            chunks = [json.loads(line) for line in f if line.strip()]

    snapshots = sorted(config.RAW_TEXT_DIR.glob("*.txt"))
    store = VectorStore()
    emb_path = config.CHUNKS_DIR / "embeddings.txt"
    emb_lines = []
    if emb_path.exists():
        for line in emb_path.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#"):
                emb_lines.append(line)
    dim = len(emb_lines[0].split("\t")[1].split(",")) if emb_lines else 0
    stage_scripts = [
        "run_ingest.py",
        "run_build_index.py",
        "test_retrieval.py",
        "run_chat.py",
    ]
    missing_scripts = [s for s in stage_scripts if not (config.PROJECT_ROOT / "scripts" / s).exists()]

    items = {
        f"{len(snapshots)}/{len(config.SCHEMES)} source snapshots": len(snapshots) == len(config.SCHEMES),
        "chunks.jsonl populated": len(chunks) > 0,
        f"embeddings.txt: {len(emb_lines)} vectors x {dim}d": len(emb_lines) == len(chunks) and dim == 384,
        f"chroma count == chunk count ({store.count()})": store.count() == len(chunks),
        "stage scripts present": not missing_scripts,
    }
    details.append(
        "- artifacts: " + ", ".join(f"{k}={'ok' if v else 'FAIL'}" for k, v in items.items())
    )
    failed = [k for k, v in items.items() if not v]
    return checklist.add(
        "SC-5", "ingestion + retrieval stages demonstrable", not failed, ", ".join(failed) or "all artifacts present"
    )


def sc6_traceability(runs, checklist, details):
    unsupported_all = []
    low_grounding = []
    for query, run in runs.items():
        if not run["result"]:
            continue
        result = run["result"]
        context = " ".join(h["text"] for h in run["hits"])
        answer_nums = numbers_in(result["answer"])
        context_nums = numbers_in(context)
        unsupported = sorted(answer_nums - context_nums)
        if unsupported:
            unsupported_all.append(f"{query}: {unsupported}")
        ratio = grounding_score(result["answer"], context)
        if ratio < GROUNDING_MIN:
            low_grounding.append(f"{query}: {ratio:.0%}")
        details.append(
            f"- `{query}` -> generator={result['generator']}, "
            f"figures traceable={'yes' if not unsupported else 'no'}, "
            f"word grounding={ratio:.0%}"
        )
    checklist.add(
        "SC-6",
        "every figure in the answers appears in retrieved context",
        not unsupported_all,
        "; ".join(unsupported_all) or "no unsupported figures",
    )
    return checklist.add(
        "SC-6",
        f"answer wording grounded in context (>={GROUNDING_MIN:.0%} content words)",
        not low_grounding,
        "; ".join(low_grounding) or "all answers grounded",
    )


def write_report(checklist, details):
    passed = len(checklist.rows) - len(checklist.failed)
    lines = [
        "# Evaluation Report (PRD §10 demo checklist)",
        "",
        "Generated by `python scripts/run_evaluation.py`. "
        f"**{passed}/{len(checklist.rows)} checks passed.**",
        "",
        "| Criterion | Check | Result | Detail |",
        "|---|---|---|---|",
    ]
    for r in checklist.rows:
        mark = "PASS" if r["passed"] else "FAIL"
        lines.append(f"| {r['criterion']} | {r['name']} | {mark} | {r['detail']} |")
    lines += ["", "## Evidence", ""] + details + [
        "",
        "## Note",
        "",
        "- SC-6 grounding is a lexical heuristic (figures must appear verbatim in the "
        "retrieved context); it is a guard against fabricated numbers, not a proof of "
        "semantic equivalence.",
        "- Answer wording varies between runs when the Groq model is available; the "
        "extractive fallback is deterministic.",
        "",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main():
    retriever = Retriever(Embedder(), VectorStore())
    checklist = Checklist()
    details = []
    runs = run_factual_cases(retriever)

    sc1_factual_answers(runs, checklist, details)
    sc2_refusals(checklist, details)
    sc3_no_stored_pii(checklist, details)
    sc4_answer_shape(runs, checklist, details)
    sc5_pipeline_artifacts(checklist, details)
    sc6_traceability(runs, checklist, details)

    write_report(checklist, details)

    for r in checklist.rows:
        print(f"[{'PASS' if r['passed'] else 'FAIL'}] {r['criterion']}  {r['name']}")
    print(f"\n{len(checklist.rows) - len(checklist.failed)}/{len(checklist.rows)} checks passed")
    print(f"Report: {REPORT_PATH.relative_to(config.PROJECT_ROOT)}")
    return 1 if checklist.failed else 0


if __name__ == "__main__":
    sys.exit(main())
