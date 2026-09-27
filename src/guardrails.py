import re

import config

PII_PATTERNS = [
    r"\b[A-Z]{5}\d{4}[A-Z]\b",
    r"\b\d{12}\b",
    r"\b\d{9,18}\b",
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    r"\b(?:\+91[-\s]?|0)?[6-9]\d{9}\b",
    r"\botp\b",
    r"\bone time password\b",
    r"\baadhaar\b",
    r"\bpan\b",
]

ADVICE_PATTERNS = [
    r"\bshould i\b",
    r"\bbuy\b",
    r"\bsell\b",
    r"\bswitch\b",
    r"\brecommend\w*\b",
    r"\bbetter (fund|option|scheme)\b",
    r"\bworth (investing|buying)\b",
    r"\ballocate\b",
    r"\bportfolio\b",
]

PERFORMANCE_PATTERNS = [
    r"\breturns?\b",
    r"\bcagr\b",
    r"\bperformance\b",
    r"\bnav (history|trend)\b",
]


def _matches(text, patterns):
    lowered = text.lower()
    return any(re.search(p, text) or re.search(p, lowered) for p in patterns)


def check_query(query):
    if _matches(query, PII_PATTERNS):
        return {
            "action": "reject_pii",
            "message": (
                "I can't accept personal details like PAN, Aadhaar, account numbers, "
                "OTPs, emails, or phone numbers. Please ask a factual question about the "
                "schemes without any personal information."
            ),
            "link": None,
        }
    if _matches(query, ADVICE_PATTERNS):
        return {
            "action": "refuse_advice",
            "message": (
                "I'm a facts-only assistant and can't provide buy/sell or investment "
                "advice. You can learn more from SEBI's investor education portal:"
            ),
            "link": config.EDU_LINK_ADVICE,
        }
    if _matches(query, PERFORMANCE_PATTERNS):
        return {
            "action": "redirect_performance",
            "message": (
                "I don't compute or compare fund returns. Please check the official "
                "factsheet for returns data:"
            ),
            "link": config.FACTSHEET_LINK,
        }
    return {"action": "allow", "message": "", "link": None}
