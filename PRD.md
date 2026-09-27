# PRD: Mutual Fund FAQ RAG Chatbot

**Version:** 1.0
**Date:** 2026-09-27
**Type:** Class demo prototype
**End output:** RAG Chatbot

---

## 1. Problem Statement

Retail users and support/content teams repeatedly answer the same factual questions about mutual fund schemes — expense ratio, exit load, minimum SIP, lock-in (ELSS), riskometer, benchmark, statement downloads. Answers scattered across official public pages (factsheets, KIM/SID, FAQs) are hard to look up quickly, and generic chatbots often hallucinate or give investment advice.

**Solution:** A small RAG-based FAQ assistant that answers factual questions about a scoped set of mutual fund schemes **using only official public pages**, with a citation link on every answer, and zero investment advice.

---

## 2. Goals

- Build a working RAG chatbot prototype (app or notebook) for a class demo.
- Answer factual MF queries only, each with exactly **one source link**.
- Politely refuse opinionated/portfolio questions ("Should I buy/sell?") with a facts-only message + relevant educational link.
- Demonstrate the full RAG pipeline end-to-end: **Loading → Chunking → Embedding → Vector Storage → Retrieval → Answer**.
- Keep every answer ≤ 3 sentences, with a "Last updated from sources:" timestamp note.

### Non-Goals

- No investment/portfolio advice, buy/sell recommendations, or return comparisons.
- No performance computation (don't compute/compare returns; link to the official factsheet if asked).
- No PII handling: never accept/store PAN, Aadhaar, account numbers, OTPs, emails, phone numbers.
- No third-party blogs or app back-end screenshots as sources — public sources only.
- No production hosting/SLAs; a ≤ 3-min demo video is acceptable if hosting isn't possible.

---

## 3. Target Users

| User | Need |
|---|---|
| Retail investors comparing schemes | Fast, cited answers to factual scheme questions |
| Support/content teams | Deflect repetitive MF questions with a trusted source link |

---

## 4. Scope

### 4.1 Corpus

**AMC:** HDFC Mutual Fund (single AMC)
**Schemes (5):**

| Category | Source URL |
|---|---|
| Large Cap | https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth |
| Flexi Cap | https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth |
| ELSS | https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth |
| Small Cap | https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth |
| Balanced Advantage (Hybrid) | https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth |

Supplementary public pages (AMC/SEBI/AMFI): factsheets, KIM/SID, scheme FAQs, fee/charges pages, riskometer/benchmark notes, statement/tax-doc guides.

### 4.2 Expected Query Types

- "Expense ratio of [scheme]?"
- "ELSS lock-in?"
- "Minimum SIP?"
- "Exit load?"
- "Riskometer / benchmark?"
- "How to download capital-gains statement?"

### 4.3 Out-of-Scope Queries (must be refused)

- "Should I buy/sell [scheme]?"
- "Which fund will give better returns?"
- Portfolio allocation or tax-advice questions.

---

## 5. RAG Architecture

The system follows all standard RAG stages: **Data Ingestion** (Loading → Chunking → Embedding → Vector Store) and **Data Retrieval** (search → context assembly → answer generation).

```
┌─────────────────────────────────────────────────────────────┐
│                     DATA INGESTION                          │
│                                                             │
│  Public pages (5 scheme URLs + AMC/SEBI/AMFI pages)         │
│        │                                                    │
│        ▼                                                    │
│  [1] Loading    → fetch/extract raw text from pages         │
│        │                                                    │
│        ▼                                                    │
│  [2] Chunking   → split into retrieval-friendly chunks      │
│        │           (strategy decided from data structure —  │
│        │            see 5.2)                                │
│        ▼                                                    │
│  [3] Embedding  → sentence-transformers/all-MiniLM-L6-v2    │
│        │                                                    │
│        ▼                                                    │
│  [4] Vector Store → persist chunks + embeddings + metadata  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                     QUERY TIME (RETRIEVAL)                  │
│                                                             │
│  User question                                              │
│        │                                                    │
│        ▼                                                    │
│  [5] Embed query → similarity search in ChromaDB (top-k)    │
│        │                                                    │
│        ▼                                                    │
│  [6] Guardrail check → refuse opinionated/advice/PII input  │
│        │                                                    │
│        ▼                                                    │
│  [7] Answer generation → ≤3 sentence factual answer         │
│        │                  + 1 citation link                 │
│        │                  + "Last updated from sources:"    │
│        ▼                                                    │
│  Tiny UI response                                           │
└─────────────────────────────────────────────────────────────┘
```

### 5.1 Technology Choices

| Component | Choice | Rationale |
|---|---|---|
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` | Lightweight, fast, strong semantic similarity for short factual chunks |
| Vector DB | **ChromaDB** | Simple local persistence, easy metadata filtering, no infra overhead |
| App surface | App or notebook (or demo video) | Class-demo friendly |

### 5.2 Chunking Strategy

Chunking strategy is to be decided based on the collected data structure. Guiding rules:

- Scheme pages are semi-structured (sections for fees, loads, SIP, riskometer) → **section-aware chunking** is preferred: keep each section/fact-group as one chunk so a single retrieval hit contains a complete answer.
- Keep chunks small enough for `all-MiniLM-L6-v2` (max ~2–3 sentences of dense fact text; target 200–400 characters).
- Attach metadata to every chunk: `scheme_name`, `category`, `section`, `source_url`, `last_updated`.
- Never split a single fact (e.g., expense ratio figure + its label) across chunks.

### 5.3 Guardrails (enforced at query time)

1. **Advice refusal:** Detect buy/sell/recommend/allocation intents → reply with a polite facts-only message + one relevant educational link (e.g., SEBI/AMFI investor education page).
2. **No PII:** Detect and reject any input containing PAN, Aadhaar, account numbers, OTPs, emails, phone numbers; never store them.
3. **No performance claims:** If asked about returns, do not compute/compare — link to the official factsheet instead.
4. **Citation mandatory:** Every answer must include exactly one source link; no answer without retrieval backing.

---

## 6. User Interface (Tiny UI)

- Welcome line.
- 3 example questions (clickable/visible).
- Persistent note: **"Facts-only. No investment advice."**
- Answer card shows: answer text (≤3 sentences), one citation link, and "Last updated from sources: [date]".

---

## 7. Functional Requirements

| # | Requirement | Priority |
|---|---|---|
| FR-1 | Ingest the 5 scheme pages + supplementary official pages via the 4-stage pipeline | Must |
| FR-2 | Store chunks, embeddings, and metadata in ChromaDB | Must |
| FR-3 | Retrieve top-k relevant chunks for a user query | Must |
| FR-4 | Generate factual answers ≤3 sentences with exactly 1 citation link | Must |
| FR-5 | Refuse opinionated/portfolio questions politely with an educational link | Must |
| FR-6 | Reject PII input and never store it | Must |
| FR-7 | Append "Last updated from sources:" to every answer | Must |
| FR-8 | Tiny UI with welcome line, 3 example questions, facts-only note | Must |
| FR-9 | Link to official factsheet when asked about returns/performance | Should |

---

## 8. Key Constraints

- **Public sources only.** No app back-end screenshots as sources; no third-party blogs.
- **No PII.** Do not accept/store PAN, Aadhaar, account numbers, OTPs, emails, phone numbers.
- **No performance claims.** Don't compute/compare returns; link to the official factsheet if asked.
- **Clarity & transparency.** Answers ≤3 sentences; add "Last updated from sources: ".

---

## 9. Deliverables

1. **Working prototype** (app/notebook link) or a ≤3-min demo video if hosting isn't possible.
2. **Source list** (CSV/MD) of the 5 URLs used.
3. **README** with setup steps, scope (AMC + schemes), and known limits.
4. **Sample Q&A file** — 5–10 queries with the assistant's answers + links.
5. **Disclaimer snippet** used in the UI (facts-only, no advice).

---

## 10. Success Criteria (Demo)

- ✅ All 6 expected query types answered correctly with a valid citation link.
- ✅ Opinionated queries are refused politely (no advice given).
- ✅ PII inputs are rejected.
- ✅ Every answer ≤3 sentences with the "Last updated" note.
- ✅ RAG pipeline stages (ingestion + retrieval) are demonstrable/explainable in the demo.
- ✅ No hallucinated facts — every claim traceable to a collected public source.

---

## 11. Known Limits

- Scoped to one AMC (HDFC) and 5 schemes — no coverage outside the corpus.
- Answer quality depends on the freshness of collected pages; "Last updated" reflects ingestion time, not live page state.
- Semantic retrieval may miss paraphrased queries that differ strongly from page wording.
- No conversational memory across turns (single-turn Q&A for the demo).
