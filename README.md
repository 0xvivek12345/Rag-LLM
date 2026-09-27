# Mutual Fund FAQ RAG Chatbot

A facts-only RAG assistant for a scoped set of HDFC Mutual Fund schemes. It answers
factual questions (expense ratio, exit load, minimum SIP, ELSS lock-in, riskometer /
benchmark, statement downloads) **only** from collected public pages, and every answer
carries exactly one source link.

- **No investment advice.** Buy/sell, portfolio and "which fund is better" questions are
  politely refused with an investor-education link.
- **No PII.** Inputs containing PAN, Aadhaar, account numbers, OTPs, emails or phone
  numbers are rejected and never stored.
- **No performance claims.** Return/performance questions are redirected to the official
  AMFI factsheet instead of being computed or compared.
- Answers are capped at 3 sentences and always carry a "Last updated from sources:" note.

Built per [`PRD.md`](PRD.md); design in [`doc/architecture.md`](doc/architecture.md);
phase plan in [`doc/implementation.md`](doc/implementation.md).

---

## 1. Setup

Requires Python 3.11+ (developed on 3.14).

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Optional, for LLM phrasing of answers: put a Groq key in `.env`

```
GROQ_API_KEY=gsk_...
```

Without a key (or if the API is unreachable) the assistant falls back to **extractive
answers** built from the retrieved chunks, so the demo always works offline. The key is
gitignored — never commit it.

## 2. Build the index (once)

```bash
python scripts/run_ingest.py        # [1] Loading + [2] Chunking  -> data/chunks/chunks.jsonl
python scripts/run_build_index.py   # [3] Embedding + [4] Vector store -> data/chroma/
```

`run_ingest.py` reads the local page snapshots in `data/raw/text/` by default; pass
`--live` to re-fetch the URLs (needs network). `run_build_index.py` is idempotent —
re-running rebuilds the collection with deterministic chunk ids.

## 3. Run the app

```bash
python scripts/run_chat.py          # CLI
python scripts/run_chat.py --demo   # fixed demo set incl. refusals
streamlit run app.py                # Streamlit UI
```

`data/chroma/` is not committed (build artifact). The first query rebuilds the index
automatically from the committed page snapshots in `data/raw/text/` — that is why a
fresh clone or a cloud deploy works with no build step.

## 4. Deploy to the web

**Why the public URL can feel slow:** a Render free web service sleeps after ~15 minutes
idle. The next visitor waits for a cold start (allocate VM + start Streamlit) before
the page appears. After the instance is up, the UI loads first; the embedding model
warms in the background.

To keep [the Render demo](https://rag-llm-28lt.onrender.com/) from sleeping, this repo
includes `.github/workflows/keep-render-awake.yml` (pings `/_stcore/health` every 12
minutes). Enable GitHub Actions on the repo after you push. A paid Render instance, or
Streamlit Community Cloud, also avoids that sleep.

1. On Render: Python web service, start command
   `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`.
2. Optional: set `GROQ_API_KEY` in the host's environment / secrets.
3. After a fresh deploy, the first instance still downloads the MiniLM ONNX model once.

## 5. Verify the demo

```bash
python scripts/test_retrieval.py    # 6 expected query types + 3 guardrail cases
python scripts/run_evaluation.py    # PRD §10 checklist -> doc/evaluation_report.md
python scripts/test_ui.py           # headless Streamlit UI smoke test
python scripts/build_sample_qa.py   # regenerate doc/sample_qa.md / .csv
python scripts/export_sources.py    # regenerate doc/sources.md / .csv
```

`run_evaluation.py` and `test_ui.py` exit non-zero on failure, so they double as
regression tests.

## 6. Scope

**AMC:** HDFC Mutual Fund only. **5 schemes** (see [`doc/sources.md`](doc/sources.md)):

| Category | Scheme |
|---|---|
| Large Cap | HDFC Large Cap Fund Direct Growth |
| Flexi Cap | HDFC Flexi Cap Direct Plan Growth |
| ELSS | HDFC ELSS Tax Saver Fund Direct Plan Growth |
| Small Cap | HDFC Small Cap Fund Direct Growth |
| Balanced Advantage (Hybrid) | HDFC Balanced Advantage Fund Direct Growth |

Pipeline: Loading → Chunking → Embedding (`all-MiniLM-L6-v2` via fastembed/ONNX, 384-dim) → ChromaDB
(persistent, cosine) → Retrieval (top-4) → Guardrails → Answer generation (≤3 sentences
+ 1 citation). Stage-to-module mapping is in `doc/architecture.md` §4.

## 7. Deliverables (PRD §9)

| # | Deliverable | Where |
|---|---|---|
| 1 | Working prototype | `scripts/run_chat.py` (CLI) · `app.py` (Streamlit) |
| 2 | Source list of the 5 URLs | [`doc/sources.md`](doc/sources.md) · [`doc/sources.csv`](doc/sources.csv) |
| 3 | README (setup, scope, limits) | this file |
| 4 | Sample Q&A | [`doc/sample_qa.md`](doc/sample_qa.md) · [`doc/sample_qa.csv`](doc/sample_qa.csv) |
| 5 | Disclaimer snippet | `config.DISCLAIMER` / `config.DISCLAIMER_LONG`, rendered by both UIs |
| + | Evaluation report (PRD §10) | [`doc/evaluation_report.md`](doc/evaluation_report.md) |

## 8. Disclaimer (as shown in the UI)

> **Facts-only. No investment advice.** This assistant answers factual questions using
> only official public pages. It does not give investment, buy/sell, portfolio or tax
> advice, and it does not compute or compare returns. Every answer carries a source link —
> please verify the details there before acting. Mutual fund investments are subject to
> market risks; read all scheme related documents carefully.

## 9. Known limits

- One AMC, 5 schemes — nothing outside the corpus is answerable.
- "Last updated" reflects ingestion time, not the live state of the page.
- Semantic retrieval can miss paraphrases that differ strongly from page wording.
- Single-turn Q&A; no conversational memory.
- Answer generation is LLM-phrased from retrieved chunks, so wording varies between runs
  when the Groq model is available. A grounding gate rejects LLM answers whose content
  words are not supported by the retrieved context and regenerates them extractively.
- Grounding is a lexical heuristic — it catches invented figures, not subtle semantic drift.
- Groww scheme pages are used as the public source for figures; figures change over time,
  so always confirm on the linked page (or the AMC factsheet) before acting.
