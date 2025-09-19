# (use your existing heuristic; minimal example shown)
import urllib.parse, httpx


def score_heuristic(output, snippets):
    text = output.get("answer", "")
    cites = output.get("citations", [])
    words = len(text.split())
    doms = {urllib.parse.urlparse(s.get("url", "")).netloc for s in snippets if s.get("url")}

    s = 0.0
    # length
    s += 0.25 if 120 <= words <= 220 else 0.10
    # citations: exactly 2 and domain check
    ok2 = len(cites) == 2
    okdom = all(urllib.parse.urlparse(u).netloc in doms for u in cites) if cites else False
    s += 0.45 if (ok2 and okdom) else 0.15
    # structure (very light)
    struct = ("• " in text) or (text.count("\n") >= 2)
    s += 0.20 if struct else 0.05

    # soft dead-link penalty
    pen = 0.0
    for u in cites:
        try:
            r = httpx.head(u, timeout=3.0, follow_redirects=True)
            if r.status_code >= 400:
                pen += 0.05
        except Exception:
            pen += 0.05

    s = max(0.0, min(1.0, s - pen))
    return {
        "score": s,
        "length_ok": 120 <= words <= 220,
        "citation_ok": ok2 and okdom,
        "notes": f"heur pen={pen:.2f}",
    }

