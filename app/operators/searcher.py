"""Web search operator using DuckDuckGo + httpx + BeautifulSoup.

Returns a list of WebSnippet dicts: {"title", "url", "text"}.
Implements on-disk caching for 24h under `runs/cache/`.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from typing import List, TypedDict
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from ddgs import DDGS
import httpx


class WebSnippet(TypedDict):
    title: str
    url: str
    text: str


CACHE_DIR = os.path.join("runs", "cache")


def _cache_path(query: str) -> str:
    h = hashlib.sha1(query.encode("utf-8")).hexdigest()
    return os.path.join(CACHE_DIR, f"search_{h}.json")


def _read_cache(path: str, max_age_seconds: int = 24 * 3600) -> List[WebSnippet] | None:
    try:
        if not os.path.exists(path):
            return None
        age = time.time() - os.path.getmtime(path)
        if age > max_age_seconds:
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            # Basic schema validation
            out: List[WebSnippet] = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                t, u, x = item.get("title"), item.get("url"), item.get("text")
                if isinstance(t, str) and isinstance(u, str) and isinstance(x, str):
                    out.append({"title": t, "url": u, "text": x})
            return out
        return None
    except Exception:
        return None


def _write_cache(path: str, items: List[WebSnippet]) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False)
    except Exception:
        # Best-effort cache; ignore failures
        pass


def _normalize_domain(url: str) -> str:
    try:
        netloc = urlparse(url).netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return url


def _collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _fetch_and_extract(url: str, timeout_total: float = 5.0) -> str | None:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
        )
    }
    try:
        timeout = httpx.Timeout(timeout_total)
        with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
            r = client.get(url)
            ctype = r.headers.get("content-type", "").lower()
            if r.status_code >= 400 or "text/html" not in ctype:
                return None
            soup = BeautifulSoup(r.text, "html.parser")
            # Remove script/style/nav elements to reduce noise
            for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside"]):
                tag.decompose()
            text = soup.get_text(separator=" ", strip=True)
            text = _collapse_ws(text)
            return text[:800]
    except Exception:
        return None


def search_web(query: str, k: int = 4, lang: str = "en") -> List[WebSnippet]:
    """Search the web and return up to k deduplicated snippets.

    - Queries DuckDuckGo for candidates.
    - Fetches each URL, extracts visible text, truncates to 800 chars.
    - De-duplicates by domain and title; at most one per domain.
    - Caches results on disk for 24 hours.
    """
    k = max(0, int(k))
    cache_file = _cache_path(query)
    cached = _read_cache(cache_file)
    if cached is not None:
        return cached[:k]

    results: List[WebSnippet] = []
    seen_domains: set[str] = set()
    seen_titles: set[str] = set()

    try:
        ddgs = DDGS()
        candidates = ddgs.text(
            query,
            safesearch="moderate",
            timelimit="d",
            max_results=8,
            region="wt-wt",
        )
    except Exception:
        candidates = []

    for item in candidates:
        if len(results) >= k:
            break
        try:
            title = (item.get("title") or "").strip()
            url = (item.get("href") or item.get("link") or item.get("url") or "").strip()
            if not title or not url:
                continue
            domain = _normalize_domain(url)
            title_key = title.lower()
            if domain in seen_domains or title_key in seen_titles:
                continue

            text = _fetch_and_extract(url, timeout_total=5.0)
            if not text:
                continue

            results.append({"title": title, "url": url, "text": text})
            seen_domains.add(domain)
            seen_titles.add(title_key)
        except Exception:
            continue

    # Write to cache best-effort
    _write_cache(cache_file, results)
    return results[:k]
