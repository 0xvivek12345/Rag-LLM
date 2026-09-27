# Implementation Plan: Mutual Fund FAQ RAG Chatbot

**Version:** 1.0 · **Date:** 2026-09-27
**Guides implementation against:** `doc/architecture.md` · requirements in `PRD.md`

Each phase below is a self-contained instruction block you can hand to Cursor (or any agent) one at a time. Do not start phase N+1 until phase N's "Done criteria" pass.

---

## Phase 1 — Project Setup & Scaffolding (done)

**Goal:** Repo skeleton + installed dependencies + central config.

**Create files:**
- `requirements.txt` — `requests`, `beautifulsoup4`, `lxml`, `sentence-transformers`, `chromadb`
- `.gitignore` — `.venv/`, `__pycache__/`, `data/chroma/`
- `config.py` — scheme registry (5 HDFC schemes + Groww URLs from PRD §4.1), paths (`data/raw/text`, `data/chunks`, `data/chroma`), `EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"`, `CHROMA_COLLECTION = "mf_faq"`, chunk params (`CHUNK_MIN_CHARS=120`, `CHUNK_MAX_CHARS=400`, `CHUNK_OVERLAP_SENTENCES=1`), fetch settings
- `src/__init__.py` — empty package marker
- Directories: `src/`, `scripts/`, `data/raw/text/`, `data/chunks/`, `data/chroma/`

**Done criteria / verification:**
```
pip install -r requirements.txt
python -c "import config, src, requests, bs4, chromadb"
```

---

## Phase 2 — Data Ingestion I: Loading & Chunking (done)

**Goal:** Official pages → cleaned text snapshots → section-aware chunks with metadata.

**Create files:**
- `src/loader.py` — stage [1] Loading:
  - Source resolution order per scheme: local snapshot `data/raw/text/<scheme_key>.txt` (default, offline-reproducible) → live fetch (opt-in `--live`)
  - `fetch_url(url)` with browser-like UA + 30s timeout
  - `extract_text_from_html(html)` via BeautifulSoup: remove `script/style/nav/footer/header`, collapse whitespace
  - `load_corpus()` → list of scheme dicts `{scheme_key, scheme_name, category, source_url, source_type, fetched_at, text}`
  - Saves snapshot text to `data/raw/text/<scheme_key>.txt` for traceability
- `src/chunker.py` — stage [2] Chunking:
  - Sentence split (regex on `.!?`), best-effort `section` label via keyword detection (expense ratio, exit load, SIP, lock-in, riskometer, benchmark, download/statement, tax, returns, general)
  - Greedy sentence packing: 120–400 chars, 1-sentence overlap; hard-split overlong sentences; never split a fact across chunks
  - `chunk_scheme()` → chunk dicts with `chunk_id = "<scheme_key>_<idx:03d>"` + metadata
  - Writes `data/chunks/chunks.jsonl` **and** human-readable `data/chunks/chunks.txt`
- `scripts/run_ingest.py` — orchestrates loader + chunker, `--live` flag, prints per-scheme stats

**Done criteria / verification:**
```
python scripts/run_ingest.py
```
- `data/raw/text/*.txt` exists (5 files), `data/chunks/chunks.jsonl` + `chunks.txt` exist
- Every chunk has all metadata fields; spot-check 2–3 chunks read as complete facts
- Re-running is idempotent (no duplicates)

---

## Phase 3 — Data Ingestion II: Embedding & Vector Store (done)

**Goal:** chunks.jsonl → all-MiniLM-L6-v2 embeddings → persistent ChromaDB collection.

**Create files:**
- `src/embedder.py` — stage [3]: wraps `SentenceTransformer(config.EMBEDDING_MODEL)`; `encode(texts)` batch, `normalize_embeddings=True` (L2-normalized 384-dim); `encode_query(text)`
- `src/vector_store.py` — stage [4]: `chromadb.PersistentClient(path=config.CHROMA_DIR)`, collection `mf_faq` with `{"hnsw:space": "cosine"}`; `rebuild(chunks, embeddings)` (delete-all + deterministic-id add, idempotent), `count()`, `query(embedding, k, where)`, `peek(n)`
- `scripts/run_build_index.py` — reads chunks.jsonl, embeds all, **writes human-readable `data/chunks/embeddings.txt`** (chunk_id + full 384-dim vector per line), rebuilds Chroma, verifies count == chunk count, runs sample similarity queries against a freshly reopened client to prove persistence

**Done criteria / verification:**
```
python scripts/run_build_index.py
```
- `data/chunks/embeddings.txt` exists (one 384-float vector per chunk)
- Chroma count == number of chunks; `data/chroma/` populated on disk
- Re-running the script does not duplicate vectors (deterministic IDs)
- Sample query returns relevant chunks from a fresh process → **persistence proven**

---

## Phase 4 — Retrieval & Guardrails (done)

**Goal:** Query-time top-k retrieval + PRD guardrails.
- `src/retriever.py` — embeds query via Embedder → `vector_store.query(k, where)`; optional scheme filter
- `src/guardrails.py` — advice refusal (buy/sell/should-I/recommend/portfolio) with SEBI investor-education link; PII regex rejection (PAN/Aadhaar/account/OTP/email/phone) never stored; performance-claim intent → AMFI factsheet link instead
- `scripts/test_retrieval.py` — runs the 6 expected query types + 3 guardrail cases
**Verification (passed):** all 6 query types retrieve the correct scheme chunks; refusal/PII/performance cases blocked before retrieval.

---

## Phase 5 — Answer Generation & Tiny UI (done)

**Goal:** Final answers + UI per PRD §6.
- `src/answer_generator.py` — **Groq LLM generation** (`config.GROQ_MODEL`, API key in `.env`): retrieved chunks passed as context with a strict facts-only system prompt (≤3 sentences, no advice/opinions, no return computation, exact figures from context only). **Extractive fallback** keeps the demo working if the API is unavailable. Citation link + "Last updated from sources:" always come from chunk metadata — never LLM-generated.
- `scripts/run_chat.py` — CLI app: welcome line, 3 example questions, "Facts-only. No investment advice."; `--demo` runs a fixed set incl. advice-refusal, PII-rejection and performance-redirect cases
- `app.py` — Streamlit tiny UI (welcome, 3 example-question buttons, answer card with citation + last-updated)
- `.env` — holds `GROQ_API_KEY`; gitignored secret — never commit or share it
**Verification:** `python scripts/run_chat.py --demo` produces PRD-compliant answers; `streamlit run app.py` serves the UI.

---

## Phase 6 — Evaluation & Deliverables (done)

**Goal:** PRD §9 deliverables + PRD §10 demo checklist.

**Create files:**
- `src/demo_cases.py` — canonical 6 expected query types (PRD §4.2) + 3 out-of-scope cases (PRD §4.3) with their expected action / section / scheme, shared by the two scripts below
- `scripts/export_sources.py` — writes `doc/sources.csv` + `doc/sources.md` (5 URLs, category, last-updated, chunk counts, section breakdown) straight from `config.SCHEMES` + `chunks.jsonl`
- `scripts/build_sample_qa.py` — runs guardrails → retrieval → generation over the 10 demo cases, writes `doc/sample_qa.md` + `doc/sample_qa.csv` (answer, citation, last-updated, supporting chunk ids, generator + grounding score)
- `scripts/run_evaluation.py` — executes the PRD §10 checklist (SC-1…SC-6) and writes `doc/evaluation_report.md`; **exits non-zero on any failure** so it doubles as a regression test
- `README.md` — setup, build, run, scope, deliverables table, disclaimer, known limits
- `config.DISCLAIMER` / `config.DISCLAIMER_LONG` — the UI disclaimer snippet, now the single source of truth for `app.py` and `run_chat.py` (with `config.LAST_UPDATED_LABEL` for the last-updated note)

**Fixes made while validating the demo:**
- `config.GROQ_MODEL` pointed at the retired `llama-3.1-8b-instant`; now `openai/gpt-oss-20b` (Groq failures are no longer silent — a `[warn]` line is printed)
- `ANSWER_MAX_TOKENS` 150 → 400 plus a post-processor that strips markdown, drops a sentence cut off by the token cap, and caps output at 3 sentences
- new **grounding gate** (`MIN_ANSWER_GROUNDING = 0.7`): an LLM answer whose content words aren't supported by the retrieved context is rejected and regenerated extractively
- `src/retriever.py` now returns `chunk_id` with each hit, so answers can cite their supporting chunks

**Done criteria / verification:**
```
python scripts/run_evaluation.py     # 16/16 checks pass, exit 0
```
- `doc/sources.md` + `.csv`, `doc/sample_qa.md` + `.csv`, `doc/evaluation_report.md`, `README.md` all present and generated from live pipeline output
- PRD §10 checklist green: 6 query types answered with a valid citation · advice/PII/performance blocked · ≤3 sentences + "Last updated from sources:" on every answer · stage artifacts present (5 snapshots, 39 chunks, 39 × 384-dim vectors, Chroma count == 39) · every answer figure traceable to the retrieved context
- `python scripts/run_chat.py --demo` and `streamlit run app.py` still work
