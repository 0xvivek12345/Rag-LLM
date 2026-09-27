# Architecture: Mutual Fund FAQ RAG Chatbot

**Version:** 1.0
**Date:** 2026-09-27
**Derived from:** `PRD.md` (repo root)
**Reference problem statement:** `doc/Problem Statement.txt`

---

## 1. System Overview

A single-AMC (HDFC), five-scheme RAG chatbot. Offline ingestion pipeline turns official public pages into chunked, embedded vectors stored in ChromaDB. At query time, a user question is embedded, similar chunks are retrieved, guardrails filter advice/PII/performance intents, and a ≤3-sentence factual answer is returned with exactly one citation link.

```
                        ┌──────────────────────────────┐
                        │      OFFICIAL PUBLIC PAGES   │
                        │  5 Groww scheme pages +      │
                        │  AMC/SEBI/AMFI references    │
                        └──────────────┬───────────────┘
                                       │
              DATA INGESTION (offline, Phase 2 + 3)
                                       │
        ┌──────────────────────────────▼──────────────────────────────┐
        │  [1] LOADER   src/loader.py                                 │
        │      live fetch (opt-in) or local snapshots in data/raw/    │
        │      → cleaned plain text per scheme                        │
        ├─────────────────────────────────────────────────────────────┤
        │  [2] CHUNKER  src/chunker.py                                │
        │      section-aware sentence packing, 120–400 chars,         │
        │      1-sentence overlap → chunks.jsonl + metadata           │
        ├─────────────────────────────────────────────────────────────┤
        │  [3] EMBEDDER src/embedder.py                               │
        │      sentence-transformers/all-MiniLM-L6-v2,                │
        │      L2-normalized 384-dim vectors                          │
        ├─────────────────────────────────────────────────────────────┤
        │  [4] VECTOR STORE src/vector_store.py                       │
        │      ChromaDB PersistentClient → data/chroma,               │
        │      collection "mf_faq", cosine space                      │
        └─────────────────────────────────────────────────────────────┘

              QUERY TIME (Phase 4 + 5, planned)
                                       │
        ┌──────────────────────────────▼──────────────────────────────┐
        │  [5] RETRIEVER  src/retriever.py                            │
        │      embed query → Chroma top-k (+ optional metadata filter)│
        ├─────────────────────────────────────────────────────────────┤
        │  [6] GUARDRAILS src/guardrails.py                           │
        │      advice refusal · PII rejection · no performance claims │
        ├─────────────────────────────────────────────────────────────┤
        │  [7] ANSWER GENERATOR src/answer_generator.py               │
        │      Groq LLM (facts-only system prompt) with extractive    │
        │      fallback; ≤3 sentences + 1 citation + "Last updated"   │
        ├─────────────────────────────────────────────────────────────┤
        │  [8] TINY UI  app surface (CLI/Streamlit)                   │
        │      welcome line · 3 example questions · facts-only note   │
        └─────────────────────────────────────────────────────────────┘
```

---

## 2. Tech Stack

| Component | Choice | Notes |
|---|---|---|
| Language | Python 3.14 | Standard library + the packages below |
| HTTP fetching | `requests` | Opt-in live fetch; default is offline snapshots for reproducibility |
| HTML parsing | `beautifulsoup4` + `lxml` | Strip script/style/nav, extract visible text |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` | 384-dim, fast, good for short factual chunks (per PRD) |
| Vector DB | **ChromaDB** (persistent, local) | Zero-infra, cosine similarity, metadata filtering (per PRD) |
| App surface | CLI first (Phase 5), Streamlit optional | Class-demo friendly; demo video acceptable |

---

## 3. Repository Layout

```
D:\New folder\
├── PRD.md                      # product requirements (repo root)
├── README.md                   # setup, scope, deliverables, known limits (Phase 6)
├── app.py                      # Streamlit UI (Phase 5)
├── doc\
│   ├── Problem Statement.txt   # milestone brief (input)
│   ├── architecture.md         # this file
│   ├── implementation.md       # phase-wise build plan
│   ├── sources.md / .csv       # source list (Phase 6, generated)
│   ├── sample_qa.md / .csv     # sample Q&A (Phase 6, generated)
│   └── evaluation_report.md    # PRD §10 checklist result (Phase 6, generated)
├── config.py                   # all constants: URLs, paths, model, chunk params, disclaimer
├── requirements.txt
├── .gitignore
├── src\                        # importable package
│   ├── __init__.py
│   ├── loader.py               # Phase 2 — stage [1]
│   ├── chunker.py              # Phase 2 — stage [2]
│   ├── embedder.py             # Phase 3 — stage [3]
│   ├── vector_store.py         # Phase 3 — stage [4]
│   ├── retriever.py            # Phase 4 — stage [5]
│   ├── guardrails.py           # Phase 4 — stage [6]
│   ├── answer_generator.py     # Phase 5 — stage [7]
│   └── demo_cases.py           # Phase 6 — canonical query cases + expectations
├── scripts\
│   ├── run_ingest.py           # Phase 2 — loader + chunker → chunks.jsonl
│   ├── run_build_index.py      # Phase 3 — chunks.jsonl → ChromaDB + verify
│   ├── test_retrieval.py       # Phase 4 — 6 query types + 3 guardrail cases
│   ├── run_chat.py             # Phase 5 — CLI app
│   ├── run_evaluation.py       # Phase 6 — PRD §10 checklist → evaluation_report.md
│   ├── build_sample_qa.py      # Phase 6 — sample_qa.md / .csv
│   └── export_sources.py       # Phase 6 — sources.md / .csv
└── data\
    ├── raw\
    │   └── text\               # source snapshots (<scheme_key>.txt), kept in repo
    ├── chunks\                 # chunks.jsonl, chunks.txt, embeddings.txt (build artifacts)
    └── chroma\                 # ChromaDB persistence (build artifact)
```

---

## 4. Pipeline Stage → Module Mapping

| RAG stage | Module | Script | Input | Output |
|---|---|---|---|---|
| Loading | `src/loader.py` | `scripts/run_ingest.py` | scheme URLs / snapshots | cleaned text per scheme |
| Chunking | `src/chunker.py` | `scripts/run_ingest.py` | cleaned text | `data/chunks/chunks.jsonl` |
| Embedding | `src/embedder.py` | `scripts/run_build_index.py` | chunk texts | 384-dim vectors |
| Vector store | `src/vector_store.py` | `scripts/run_build_index.py` | chunks + vectors | `data/chroma/` (mf_faq) |
| Retrieval | `src/retriever.py` | `scripts/run_chat.py`, `app.py` | query embedding | top-k chunks |
| Guardrails | `src/guardrails.py` | all query-time entry points | raw query | allow / refuse + reason |
| Answer generation | `src/answer_generator.py` | all query-time entry points | query + top-k chunks | final answer + citation |
| UI | CLI/Streamlit | `scripts/run_chat.py`, `app.py` | user input | answer card |
| Evaluation | `scripts/run_evaluation.py` | `scripts/run_evaluation.py` | demo cases + artifacts | PRD §10 pass/fail report |

---

## 5. Module Specifications

### 5.1 `src/loader.py` — Loading (Phase 2)

- **Responsibility:** produce clean plain text for each of the 5 schemes, with provenance.
- **Source resolution order (per scheme):**
  1. Local snapshot `data/raw/text/<scheme_key>.txt` (default; deterministic, demo-reproducible)
  2. Live fetch of the official URL (opt-in via `--live` flag on `run_ingest.py`)
- **Cleaning:** drop `<script>`, `<style>`, `<nav>`, `<footer>`, `<header>`; collapse whitespace; keep factual sentence text. Live-fetched HTML uses the same cleaner before saving as a snapshot.
- **Output per scheme:** `{scheme_key, scheme_name, category, source_url, source_type, fetched_at, text}`
- **Snapshot flag:** snapshot files are the canonical corpus for the demo; if a scheme has neither snapshot nor successful live fetch, ingestion fails loudly for that scheme with instructions.

### 5.2 `src/chunker.py` — Chunking (Phase 2)

- **Strategy (per PRD, decided from data structure):** scheme pages are semi-structured fact sheets → **section-aware chunking**: sentences are packed greedily into chunks of **120–400 chars** with **1-sentence overlap**, and a best-effort `section` label is assigned from keyword detection (expense ratio, exit load, SIP, lock-in, riskometer, benchmark, download/statement, tax, returns, general).
- **Rules:**
  - Never split a single fact (label + figure) across chunks; hard-split only sentences longer than `CHUNK_MAX_CHARS`.
  - Every chunk carries full metadata (see §6) so a single retrieval hit can produce a complete cited answer.
- **Output:** JSONL, one chunk per line, ordered per scheme.

### 5.3 `src/embedder.py` — Embedding (Phase 3)

- **Model:** `sentence-transformers/all-MiniLM-L6-v2` (per PRD).
- **Behavior:** batch-encode chunk texts and queries with `normalize_embeddings=True` (L2-normalized) so cosine similarity ≈ dot product; 384-dim output.
- **Interface:** `encode(texts) -> list[list[float]]`, `encode_query(text) -> list[float]`.

### 5.4 `src/vector_store.py` — Vector Store (Phase 3)

- **ChromaDB:** `PersistentClient(path="data/chroma")`, collection `mf_faq` with `metadata={"hnsw:space": "cosine"}`.
- **Write path:** full rebuild semantics — delete existing collection contents, then `add(ids, documents, metadatas, embeddings)`. Deterministic IDs `<scheme_key>_<idx:03d>` make rebuilds idempotent.
- **Read path (used by Phase 4):** `query(embedding, k, where=None)` with optional Chroma `where` metadata filter (e.g., `{"scheme_key": "elss"}`).
- **Interface:** `rebuild(chunks, embeddings)`, `count()`, `query(...)`, `peek(n)`.

### 5.5 `src/retriever.py` — Retrieval (Phase 4)

- **Responsibility:** embed the query, run cosine top-k against Chroma, return hits carrying `chunk_id` + full chunk metadata + `text` + `distance`.
- **Interface:** `retrieve(query, scheme_key=None)`; `scheme_key` adds a metadata filter.

### 5.6 `src/guardrails.py` — Guardrails (Phase 4)

- **Responsibility:** classify the raw query as `allow` / `refuse_advice` / `redirect_performance` / `reject_pii` *before* retrieval, and never persist the input.
- **Interface:** `check_query(query) -> {action, message, link}`; pattern tables `PII_PATTERNS`, `ADVICE_PATTERNS`, `PERFORMANCE_PATTERNS`.

### 5.7 `src/answer_generator.py` — Answer Generation (Phase 5)

- **Responsibility:** turn query + top-k chunks into a ≤3-sentence factual answer, then attach citation + last-updated **from chunk metadata** (never model-generated).
- **LLM path:** Groq chat completion with a strict facts-only system prompt (`GROQ_MODEL`, key from `.env`).
- **Post-processing:** strip markdown emphasis, flatten whitespace, drop a trailing sentence if the model hit the token cap, and cap at `ANSWER_MAX_SENTENCES`.
- **Grounding gate:** `grounding_score(answer, context)` = share of the answer's content words present in the retrieved context; below `MIN_ANSWER_GROUNDING` the LLM answer is rejected and regenerated extractively.
- **Fallback:** `_extractive_answer` picks the keyword-matching sentences of the top chunk — deterministic, offline, and always traceable to a cited chunk.

### 5.8 `src/demo_cases.py` — Demo Cases (Phase 6)

- **Responsibility:** single source of truth for the 6 expected query types (PRD §4.2) and the out-of-scope cases (PRD §4.3), each with its expected action/section/scheme.
- **Used by:** `scripts/build_sample_qa.py` (published sample answers) and `scripts/run_evaluation.py` (PRD §10 checklist) so the two can't drift apart.

---

## 6. Data Schemas

### 6.1 Chunk record (`data/chunks/chunks.jsonl`)

```json
{
  "chunk_id": "large_cap_000",
  "text": "The expense ratio of HDFC Large Cap Fund Direct Growth is ...",
  "scheme_key": "large_cap",
  "scheme_name": "HDFC Large Cap Fund - Direct Growth",
  "category": "Large Cap",
  "section": "fees",
  "source_url": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
  "source_type": "snapshot",
  "last_updated": "2026-09-27",
  "char_count": 312
}
```

### 6.2 Chroma collection `mf_faq`

| Field | Value |
|---|---|
| ids | `<scheme_key>_<idx:03d>` (same as `chunk_id`) |
| documents | chunk `text` |
| embeddings | 384-dim L2-normalized float vectors |
| metadatas | `scheme_key`, `scheme_name`, `category`, `section`, `source_url`, `source_type`, `last_updated`, `char_count` (all scalar — Chroma-compatible) |
| space | cosine |

### 6.3 Scheme registry (`config.py`)

Five schemes exactly as scoped in the PRD: large_cap, flexi_cap, elss, small_cap, balanced_advantage (HDFC AMC, Groww URLs).

---

## 7. Guardrails Architecture (Phase 4)

| Guardrail | Detection | Response |
|---|---|---|
| Advice refusal | intent keywords (buy, sell, recommend, should I, allocate, switch) | polite facts-only message + 1 SEBI/AMFI investor-education link |
| No PII | regex for PAN, Aadhaar, account no., OTP, email, phone | reject input; never store it |
| No performance claims | return/NAV-comparison/CAGR intent | no computation; link to official factsheet |
| Citation mandatory | answer path only | no answer emitted without ≥1 retrieved chunk; exactly 1 source link shown |
| Grounding gate (Phase 5) | answer words not supported by retrieved context | reject LLM answer, regenerate extractively |

Guardrails run **before** retrieval (input filtering) and **before** UI display (answer filtering). They never persist user input.

---

## 8. Configuration Reference (`config.py`)

| Constant | Value | Used by |
|---|---|---|
| `SCHEMES` | 5-scheme registry (key, name, category, url) | loader |
| `RAW_TEXT_DIR` | `data/raw/text` | loader |
| `CHUNKS_DIR` | `data/chunks` | chunker |
| `CHROMA_DIR` | `data/chroma` | vector store |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | embedder, retriever |
| `CHROMA_COLLECTION` | `mf_faq` | vector store |
| `TOP_K` | 4 | retriever |
| `ANSWER_MAX_SENTENCES` / `ANSWER_MAX_TOKENS` | 3 / 400 | answer generator |
| `MIN_ANSWER_GROUNDING` | 0.7 | answer generator grounding gate |
| `CHUNK_MIN_CHARS` / `CHUNK_MAX_CHARS` | 120 / 400 | chunker |
| `CHUNK_OVERLAP_SENTENCES` | 1 | chunker |
| `FETCH_TIMEOUT_SECS`, `REQUEST_HEADERS` | 30, browser-like UA | loader (live mode) |
| `EDU_LINK_ADVICE`, `FACTSHEET_LINK` | SEBI investor education, AMFI factsheet | guardrails |
| `LAST_UPDATED_LABEL` | `Last updated from sources:` | both UIs, deliverables |
| `DISCLAIMER`, `DISCLAIMER_LONG` | short note + full disclaimer text | both UIs, README, sample Q&A |
| `GROQ_API_KEY`, `GROQ_MODEL` | from `.env`; `openai/gpt-oss-20b` | answer generator |

---

## 9. Architecture Decisions Log

| # | Decision | Rationale |
|---|---|---|
| AD-1 | Offline snapshots are the default corpus; live fetch is opt-in | Reproducible demo, immune to bot-protection/403s and page drift mid-demo; snapshots kept in `data/raw/text/` for traceability |
| AD-2 | Section-aware chunking over fixed-size windows | Scheme pages are fact-sheet-like; keeping a fact group intact means one hit = one complete answer (PRD requirement) |
| AD-3 | Deterministic chunk IDs + full-rebuild writes | Idempotent re-ingestion; no duplicate-vector bugs during demo prep |
| AD-4 | Cosine space + normalized embeddings | Standard for MiniLM retrieval; dot product ≡ cosine |
| AD-5 | LLM answer generation via Groq API with strict facts-only system prompt + extractive fallback | Fluent grounded answers for the demo; figures/names must come from retrieved chunks; fallback keeps demo working if API is unavailable (PRD: no advice, no performance claims) |
| AD-6 | Metadata on every chunk | Enables per-scheme filtering (Phase 4) and guarantees the citation link requirement |
| AD-7 | Grounding gate on generated answers (`MIN_ANSWER_GROUNDING`) | The LLM sometimes elaborated steps the chunk never stated; rejecting weakly-grounded answers keeps the demo inside PRD §10's "no hallucinated facts" criterion without disabling the LLM path |
| AD-8 | Deliverables are generated by scripts from live pipeline output | `sources.*`, `sample_qa.*` and `evaluation_report.md` can't drift from the actual build; `run_evaluation.py` doubles as a regression test (non-zero exit on failure) |
| AD-9 | Demo cases live in `src/demo_cases.py` | One definition of "expected query type" and its expectations, shared by the sample Q&A and the evaluation script |

---

## 10. Evaluation & Deliverables (Phase 6)

`scripts/run_evaluation.py` executes the PRD §10 demo checklist and writes
`doc/evaluation_report.md`; it exits non-zero on any failure.

| Criterion | How it is checked |
|---|---|
| SC-1 expected query types answered + cited | per query: non-empty answer, citation ∈ corpus URLs, last-updated present, ≤3 sentences, expected scheme and section present in the retrieved top-k |
| SC-2 opinionated queries refused | `check_query` returns `refuse_advice` / `redirect_performance` with the expected link; retrieval and generation are never invoked |
| SC-3 PII rejected and never stored | `reject_pii` action + a PII regex scan over `chunks.jsonl`, `chunks.txt` and every stored Chroma document |
| SC-4 answer shape | sentence count per answer + both UIs render `LAST_UPDATED_LABEL` |
| SC-5 stages demonstrable | 5 snapshots, populated `chunks.jsonl`, `embeddings.txt` = 39 × 384-dim, Chroma count == chunk count, all stage scripts present |
| SC-6 no hallucinated facts | every figure in an answer must appear in the retrieved context, and answer wording must clear `MIN_ANSWER_GROUNDING` |

Generated deliverables: `doc/sources.md` / `.csv` (`export_sources.py`),
`doc/sample_qa.md` / `.csv` (`build_sample_qa.py`), `doc/evaluation_report.md`
(`run_evaluation.py`), `README.md` + `config.DISCLAIMER*` (the UI disclaimer snippet).
