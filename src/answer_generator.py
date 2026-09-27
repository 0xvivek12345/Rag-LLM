import re

import config
from src.chunker import SENTENCE_SPLIT_RE

STOPWORDS = {
    "what", "is", "the", "of", "for", "a", "an", "in", "to", "how", "do",
    "i", "my", "me", "and", "are", "on", "does", "it",
}

SYSTEM_PROMPT = (
    "You are a facts-only mutual fund FAQ assistant. Answer ONLY from the provided "
    "context. Rules:\n"
    "- Maximum 3 sentences.\n"
    "- Do not give investment advice, opinions, buy/sell or fund recommendations.\n"
    "- Do not compute or compare returns or performance.\n"
    "- Use the exact figures, dates and fund names from the context.\n"
    "- Do not add steps, instructions, figures or details that the context does not "
    "state; if the context only names a source, say only that.\n"
    "- If the context does not contain the answer, say you don't have that information."
)


def _keywords(query):
    return {w for w in re.findall(r"[a-z0-9]+", query.lower()) if w not in STOPWORDS}


def _build_context(hits):
    parts = []
    for h in hits:
        parts.append(f"[{h['scheme_name']} | {h['section']}]\n{h['text']}")
    return "\n\n".join(parts)


def _extractive_answer(query, hits):
    top = hits[0]
    kw = _keywords(query)
    sentences = [s.strip() for s in SENTENCE_SPLIT_RE.split(top["text"]) if s.strip()]
    scored = []
    for idx, sent in enumerate(sentences):
        words = set(re.findall(r"[a-z0-9]+", sent.lower()))
        scored.append((len(kw & words), idx, sent))
    relevant = [s for s in scored if s[0] > 0] or scored
    relevant.sort(key=lambda t: (-t[0], t[1]))
    chosen = sorted(relevant[: config.ANSWER_MAX_SENTENCES], key=lambda t: t[1])
    return " ".join(t[2] for t in chosen)


def _enforce_limits(text, truncated):
    """Flatten markdown/whitespace and cap the answer at ANSWER_MAX_SENTENCES sentences.

    `truncated` drops a trailing cut-off sentence, which happens when the model
    hits the token cap mid-answer.
    """
    cleaned = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    cleaned = cleaned.replace("\u2011", "-").replace("\u2013", "-")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"\s+([%,])", r"\1", cleaned)
    sentences = [s.strip() for s in SENTENCE_SPLIT_RE.split(cleaned) if s.strip()]
    if truncated and len(sentences) > 1:
        sentences = sentences[:-1]
    return " ".join(sentences[: config.ANSWER_MAX_SENTENCES]).strip()


def grounding_score(answer, context):
    """Share of the answer's content words that also occur in the retrieved context.

    A cheap faithfulness proxy: an answer that invents steps or details usually
    drifts far from the wording of the chunks it was given.
    """
    def words(text):
        return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 3 and not w.isdigit()}

    answer_words = words(answer)
    if not answer_words:
        return 1.0
    context_words = words(context)
    grounded = {w for w in answer_words if w in context_words or w.rstrip("s") in context_words}
    return len(grounded) / len(answer_words)


def generate_answer(query, hits):
    top = hits[0]
    answer = None
    generator = "extractive"
    context = _build_context(hits)
    api_key = config.groq_api_key()

    if api_key:
        try:
            from groq import Groq

            client = Groq(api_key=api_key)
            completion = client.chat.completions.create(
                model=config.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"Context:\n{context}\n\n"
                            f"Question: {query}\n\n"
                            "Answer (max 3 sentences, facts only):"
                        ),
                    },
                ],
                temperature=0.1,
                max_tokens=config.ANSWER_MAX_TOKENS,
            )
            text = completion.choices[0].message.content
            if text and text.strip():
                answer = _enforce_limits(
                    text, completion.choices[0].finish_reason == "length"
                )
        except Exception as exc:
            print(f"[warn] Groq generation failed ({exc.__class__.__name__}); using extractive fallback")
            answer = None

    if answer:
        score = grounding_score(answer, context)
        if score < config.MIN_ANSWER_GROUNDING:
            print(
                f"[warn] LLM answer not grounded in context ({score:.0%}); "
                "using extractive fallback"
            )
            answer = None
        else:
            generator = "groq"

    if not answer:
        answer = _extractive_answer(query, hits)

    return {
        "answer": answer,
        "citation_url": top["source_url"],
        "last_updated": top["last_updated"],
        "scheme": top["scheme_name"],
        "generator": generator,
        "grounding": round(grounding_score(answer, context), 2),
    }
