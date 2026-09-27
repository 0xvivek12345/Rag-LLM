import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_TEXT_DIR = DATA_DIR / "raw" / "text"
CHUNKS_DIR = DATA_DIR / "chunks"
CHROMA_DIR = DATA_DIR / "chroma"

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHROMA_COLLECTION = "mf_faq_onnx"
TOP_K = 4
ANSWER_MAX_SENTENCES = 3
ANSWER_MAX_TOKENS = 400
MIN_ANSWER_GROUNDING = 0.7

EDU_LINK_ADVICE = "https://investor.sebi.gov.in/"
FACTSHEET_LINK = "https://www.amfiindia.com/interactive-report/fact-sheet"

LAST_UPDATED_LABEL = "Last updated from sources:"

DISCLAIMER = "Facts-only. No investment advice."
DISCLAIMER_LONG = (
    "This assistant answers factual questions using only official public pages. "
    "It does not give investment, buy/sell, portfolio or tax advice, and it does not "
    "compute or compare returns. Every answer carries a source link - please verify the "
    "details there before acting. Mutual fund investments are subject to market risks; "
    "read all scheme related documents carefully."
)

CHUNK_MIN_CHARS = 120
CHUNK_MAX_CHARS = 400
CHUNK_OVERLAP_SENTENCES = 1

FETCH_TIMEOUT_SECS = 30
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    )
}

SCHEMES = {
    "large_cap": {
        "name": "HDFC Large Cap Fund Direct Growth",
        "category": "Large Cap",
        "url": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
    },
    "flexi_cap": {
        "name": "HDFC Flexi Cap Direct Plan Growth",
        "category": "Flexi Cap",
        "url": "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth",
    },
    "elss": {
        "name": "HDFC ELSS Tax Saver Fund Direct Plan Growth",
        "category": "ELSS",
        "url": "https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth",
    },
    "small_cap": {
        "name": "HDFC Small Cap Fund Direct Growth",
        "category": "Small Cap",
        "url": "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
    },
    "balanced_advantage": {
        "name": "HDFC Balanced Advantage Fund Direct Growth",
        "category": "Balanced Advantage (Hybrid)",
        "url": "https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth",
    },
}

SECTION_KEYWORDS = {
    "fees": ["expense ratio", "fee", "management fee", "stamp duty"],
    "exit_load": ["exit load", "redemption"],
    "sip": ["sip", "minimum investment", "lumpsum"],
    "lock_in": ["lock-in", "lock in"],
    "riskometer": ["riskometer", "very high risk", "risk level"],
    "benchmark": ["benchmark", "nifty", "index"],
    "download": ["download", "statement", "capital gains", "cams"],
    "tax": ["tax", "80c"],
    "returns": ["returns", "cagr", "performance"],
    "fund_info": ["fund manager", "aum", "inception", "launch", "objective", "fund type"],
}


def _load_env():
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


_load_env()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = "openai/gpt-oss-20b"


def groq_api_key():
    """Resolve the Groq key: environment/.env first, Streamlit secrets second.

    Streamlit Cloud injects secrets through `st.secrets` instead of a .env file,
    and that value is only readable after `set_page_config`, hence the lazy lookup.
    """
    key = os.environ.get("GROQ_API_KEY", "")
    if key:
        return key
    try:
        import streamlit as st

        return str(st.secrets.get("GROQ_API_KEY", ""))
    except Exception:
        return ""
