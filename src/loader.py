import datetime

import requests
from bs4 import BeautifulSoup

import config


def fetch_url(url):
    resp = requests.get(url, headers=config.REQUEST_HEADERS, timeout=config.FETCH_TIMEOUT_SECS)
    resp.raise_for_status()
    return resp.text


def extract_text_from_html(html):
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    return clean_text(text)


def clean_text(text):
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def snapshot_path(scheme_key):
    return config.RAW_TEXT_DIR / f"{scheme_key}.txt"


def load_scheme(scheme_key, live=False):
    scheme = config.SCHEMES[scheme_key]
    if not live:
        path = snapshot_path(scheme_key)
        if path.exists():
            return _build(scheme_key, scheme, path.read_text(encoding="utf-8"), "snapshot")
        raise FileNotFoundError(
            f"No snapshot for '{scheme_key}'. Save the page text to {path} "
            f"or run with --live to fetch {scheme['url']}"
        )
    text = extract_text_from_html(fetch_url(scheme["url"]))
    live_path = config.RAW_TEXT_DIR / f"{scheme_key}.live.txt"
    live_path.write_text(text, encoding="utf-8")
    return _build(scheme_key, scheme, text, "live")


def _build(scheme_key, scheme, text, source_type):
    return {
        "scheme_key": scheme_key,
        "scheme_name": scheme["name"],
        "category": scheme["category"],
        "source_url": scheme["url"],
        "source_type": source_type,
        "fetched_at": datetime.date.today().isoformat(),
        "text": text,
    }


def load_corpus(live=False):
    return [load_scheme(key, live=live) for key in config.SCHEMES]
