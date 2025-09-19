import json, re, urllib.parse, os
from typing import List, Dict

SCHEMA = '{"score":0.0,"length_ok":false,"citation_ok":false,"notes":""}'


def _domains(snips: List[Dict]) -> list[str]:
    ds = []
    for s in snips:
        try:
            ds.append(urllib.parse.urlparse(s.get("url","" )).netloc)
        except Exception:
            pass
    # preserve order, drop empties
    out, seen = [], set()
    for d in ds:
        if d and d not in seen:
            out.append(d); seen.add(d)
    return out


def ask_llm_judge(model: str, answer: str, snippets: List[Dict], temperature: float = 0.0) -> Dict:
    # Prefer HTTP API first for robustness; fall back to python binding
    all_urls = [s.get("url","" ) for s in snippets if s.get("url")]
    urls = all_urls[:2]
    system = (
        "You are an evaluator. OUTPUT ONE JSON OBJECT ONLY with keys exactly: "
        '{"score":0.0,"length_ok":false,"citation_ok":false,"notes":""}. '
        "No prose, no code fences, no extra keys.\n"
        "How to set booleans:\n"
        "• length_ok: true iff the ANSWER has 120–220 words (inclusive).\n"
        "• citation_ok: true iff the ANSWER contains EXACTLY two inline citations in the form [n](URL) where n∈{1,2} and both URLs ∈ ALLOWED_URLS.\n"
        "How to set score (continuous quality rating, not pass/fail):\n"
        "• Start from 0.5 if length_ok and citation_ok are both true; else start from 0.3 if either is true; else start from 0.0.\n"
        "• Add up to +0.25 for clear structure (intro + ~3 concise bullets + wrap).\n"
        "• Add up to +0.15 for clarity and coherence.\n"
        "• Add up to +0.10 for relevance and specificity to the snippets (no generic filler).\n"
        "• Subtract up to −0.25 for factuality issues or citing non-allowed URLs.\n"
        "Clamp score to [0,1]. Do NOT default to 0.0 when basics pass.\n"
        'notes must be ≤ 120 characters and briefly justify the score (e.g., "good structure; two valid cites; minor generic wrap"). '
        "Do NOT repeat or quote the ANSWER text. Return JSON only."
    )

    answer_norm = " ".join(answer.split())
    user = (
        "ALLOWED_URLS=" + json.dumps(urls) + "\n\n"
        "ANSWER:\n" + answer_norm + "\n"
        "Return JSON only."
    )

    # HTTP first
    content = ""
    try:
        from urllib.request import Request, urlopen
        host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "options": {"temperature": 0.0, "num_predict": 700, "format": "json"},
            "stream": False,
        }
        req = Request(host + "/api/chat", data=json.dumps(payload).encode("utf-8"), method="POST")
        req.add_header("Content-Type", "application/json")
        with urlopen(req, timeout=60) as resp_http:
            body = resp_http.read().decode("utf-8")
            j = json.loads(body)
            content = ((j.get("message") or {}).get("content") or "")
    except Exception:
        content = ""
    
    if not content:
        # Fallback to python binding
        try:
            from ollama import chat
            resp = chat(
                model=model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                options={"temperature": 0.0, "num_predict": 700, "format": "json"},
            )
            content = (resp.get("message") or {}).get("content", "")
        except Exception:
            content = ""
    # sanitize preambles before parsing
    try:
        import re as _re
        # drop <think>...</think> blocks completely
        content = _re.sub(r"<think>.*?</think>", "", content, flags=_re.DOTALL | _re.IGNORECASE)
        # also trim any leading non-json chars before first "{"
        first_brace = content.find("{")
        if first_brace > 0:
            content = content[first_brace:]
    except Exception:
        pass

    def _parse_json(s: str):
        # fast path
        try:
            return json.loads(s)
        except Exception:
            pass
        # strip code fences if present
        s2 = s.strip().strip("`").strip()
        try:
            return json.loads(s2)
        except Exception:
            pass
        # grab first {...} span
        m = re.search(r"\{.*\}", s, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
        return None

    data = _parse_json(content)
    retry_note = ""
    def _snippet(s: str, n: int = 160) -> str:
        try:
            return re.sub(r"\s+", " ", s).strip()[:n]
        except Exception:
            return (s or "")[:n]

    content2 = ""
    if data is None:
        # one strict retry: shorter prompt that says "JSON ONLY"
        retry_system = 'Output ONE valid JSON object only. No prose. Schema: {"score":0.0,"length_ok":false,"citation_ok":false,"notes":""}'
        retry_user = "Return the JSON now."
        # Retry via HTTP first
        try:
            from urllib.request import Request, urlopen
            host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
            payload = {
                "model": model,
                "messages": [{"role": "system", "content": retry_system}, {"role": "user", "content": retry_user}],
                "options": {"temperature": 0.0, "num_predict": 200, "format": "json"},
                "stream": False,
            }
            req = Request(host + "/api/chat", data=json.dumps(payload).encode("utf-8"), method="POST")
            req.add_header("Content-Type", "application/json")
            with urlopen(req, timeout=60) as resp_http:
                body = resp_http.read().decode("utf-8")
                j = json.loads(body)
                content2 = ((j.get("message") or {}).get("content") or "")
        except Exception:
            content2 = ""
        if not content2:
            # Then try python binding
            try:
                from ollama import chat
                resp2 = chat(
                    model=model,
                    messages=[{"role": "system", "content": retry_system}, {"role": "user", "content": retry_user}],
                    options={"temperature": 0.0, "num_predict": 200, "format": "json"},
                )
                content2 = (resp2.get("message") or {}).get("content", "")
            except Exception:
                content2 = ""
        # sanitize preambles before parsing retry content
        try:
            import re as _re2
            content2 = _re2.sub(r"<think>.*?</think>", "", content2, flags=_re2.DOTALL | _re2.IGNORECASE)
            fb2 = content2.find("{")
            if fb2 > 0:
                content2 = content2[fb2:]
        except Exception:
            pass
        data = _parse_json(content2)
        if data:
            retry_note = " parse_error_retry"
        else:
            retry_note = " parse_error_nojson raw1='" + _snippet(content) + "' raw2='" + _snippet(content2) + "'"

    if not data:
        # include raw snippet from first attempt for diagnostics
        if not retry_note:
            retry_note = " raw='" + _snippet(content) + "'"
        data = {"score": 0.0, "length_ok": False, "citation_ok": False, "notes": ("parse_error" + retry_note)}
    sc = data.get("score", 0.0)
    try:
        sc = float(sc)
    except Exception:
        sc = 0.0
    sc = 0.0 if sc < 0 else 1.0 if sc > 1 else sc
    return {
        "score": sc,
        "length_ok": bool(data.get("length_ok", False)),
        "citation_ok": bool(data.get("citation_ok", False)),
        "notes": data.get("notes","" ),
        "raw": _snippet(content, 500),
        "raw_retry": _snippet(content2, 500) if content2 else "",
    }
