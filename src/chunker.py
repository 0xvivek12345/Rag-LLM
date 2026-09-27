import json
import re

import config

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def split_sentences(text):
    sentences = []
    for para in text.split("\n"):
        para = para.strip()
        if not para:
            continue
        sentences.extend(p.strip() for p in SENTENCE_SPLIT_RE.split(para) if p.strip())
    return sentences


def detect_section(chunk_text):
    lowered = chunk_text.lower()
    for section, keywords in config.SECTION_KEYWORDS.items():
        for kw in keywords:
            if re.search(rf"\b{re.escape(kw)}\b", lowered):
                return section
    return "general"


def chunk_sentences(sentences):
    chunks = []
    current = []
    for sent in sentences:
        if len(sent) > config.CHUNK_MAX_CHARS:
            if current:
                chunks.append(" ".join(current))
                current = []
            for i in range(0, len(sent), config.CHUNK_MAX_CHARS):
                chunks.append(sent[i : i + config.CHUNK_MAX_CHARS])
            continue
        if current and len(" ".join(current)) + len(sent) + 1 > config.CHUNK_MAX_CHARS:
            chunks.append(" ".join(current))
            current = current[-config.CHUNK_OVERLAP_SENTENCES :]
        current.append(sent)
    if current:
        chunks.append(" ".join(current))
    return chunks


def chunk_scheme(scheme):
    sentences = split_sentences(scheme["text"])
    chunks = []
    for idx, chunk_text in enumerate(chunk_sentences(sentences)):
        chunks.append(
            {
                "chunk_id": f"{scheme['scheme_key']}_{idx:03d}",
                "text": chunk_text,
                "scheme_key": scheme["scheme_key"],
                "scheme_name": scheme["scheme_name"],
                "category": scheme["category"],
                "section": detect_section(chunk_text),
                "source_url": scheme["source_url"],
                "source_type": scheme["source_type"],
                "last_updated": scheme["fetched_at"],
                "char_count": len(chunk_text),
            }
        )
    return chunks


def write_chunks(chunks):
    config.CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
    jsonl_path = config.CHUNKS_DIR / "chunks.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    txt_path = config.CHUNKS_DIR / "chunks.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(
                f"[{c['chunk_id']}] scheme={c['scheme_name']} | section={c['section']} "
                f"| {c['char_count']} chars\n{c['text']}\n\n"
            )
    return jsonl_path, txt_path
