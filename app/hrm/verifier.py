import re
from typing import List, Dict, Any

RULES = {
    "min_words": 120,
    "max_words": 220,
    "bullets_min": 3,
}

_CITE_RE = re.compile(r"\[(\d+)\]\((https?://[^)]+)\)")

def check(answer: str, allowed_urls: List[str]) -> Dict[str, Any]:
    wc = len(answer.split())
    bullets = sum(1 for ln in answer.splitlines() if ln.strip().startswith("• "))
    cites = _CITE_RE.findall(answer)
    cited_urls = [u for _, u in cites]
    cite_ok = (len(cites) == 2) and all(u in allowed_urls for u in cited_urls)
    return {
        "word_count_ok": RULES["min_words"] <= wc <= RULES["max_words"],
        "bullets_ok": bullets >= RULES["bullets_min"],
        "citation_ok": cite_ok,
        "details": {"wc": wc, "bullets": bullets, "cites": cited_urls},
    }

EDIT_SYS = (
    "You are a strict editor. Fix ONLY the reported issues while preserving meaning. "
    "If citations are missing or wrong, add exactly two inline citations using "
    "[1](URL1) and [2](URL2) at the ends of the first and last bullet. "
    "Output plain text only."
)

def suggest_edit(
    answer: str,
    issues: Dict[str, Any],
    url1: str,
    url2: str,
    model: str = "llama3.2:1b",
) -> str:
    if all([issues["word_count_ok"], issues["bullets_ok"], issues["citation_ok"]]):
        return answer
    needs = []
    if not issues["word_count_ok"]:
        needs.append("Make it 160–190 words.")
    if not issues["bullets_ok"]:
        needs.append("Ensure exactly 3 bullets starting with '• '.")
    if not issues["citation_ok"]:
        needs.append(
            f"Replace citations with exactly [1]({url1}) at end of first bullet and [2]({url2}) at end of last bullet."
        )
    prompt = "Fix the text:\n---\n" + answer + "\n---\n" + " ".join(needs)
    from ollama import chat
    resp = chat(
        model=model,
        messages=[{"role": "system", "content": EDIT_SYS}, {"role": "user", "content": prompt}],
        options={"temperature": 0.2, "num_predict": 512},
    )
    return (resp.get("message") or {}).get("content", "").strip() or answer
