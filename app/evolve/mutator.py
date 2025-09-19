from __future__ import annotations

import json
import re
from typing import List, Dict, Any

# We prefer the Ollama Python client if available; otherwise fall back to HTTP.
try:
    import ollama  # type: ignore
    _HAVE_OLLAMA = True
except Exception:
    _HAVE_OLLAMA = False

def _http_chat(
    model: str,
    messages: List[Dict[str, str]],
    options: Dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> str:
    """
    Minimal HTTP fallback to Ollama /api/chat without external deps.
    """
    import urllib.request, urllib.error
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "stream": False,
        "options": options or {"temperature": 0.2, "num_predict": 400}
    }).encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            msg = (data.get("message") or {}).get("content", "")
            return msg or ""
    except urllib.error.URLError:
        return ""
    except Exception:
        return ""

_SANITIZE_FENCES = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)
_SANITIZE_THINK = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)

def _clean_text(text: str) -> str:
    if not text:
        return ""
    text = _SANITIZE_THINK.sub("", text)
    text = _SANITIZE_FENCES.sub("", text)
    return text.strip()


def _chat_with_timeout(model: str, messages: List[Dict[str, str]], options: Dict[str, Any], timeout: float) -> str:
    """Call ollama.chat with a hard timeout; return content string or ''."""
    if not _HAVE_OLLAMA:
        return _http_chat(model, messages, options, timeout=timeout)
    try:
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
        with ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(ollama.chat, model=model, messages=messages, options=options)  # type: ignore
            resp = fut.result(timeout=timeout)
        # Handle ChatResponse vs dict
        if isinstance(resp, dict):
            return ((resp.get("message") or {}).get("content") or "")
        return getattr(getattr(resp, "message", None), "content", "") or ""
    except Exception:
        return ""

_MUTATOR_SYS = (
    "You are the Mutator in a self-evolving swarm.\n"
    "Given a SYSTEM PROMPT template for a summarizer, propose SMALL, useful mutations while preserving invariants.\n"
    "Output JSON array of objects with keys exactly: id, system, notes.\n"
    "STRICT REQUIREMENTS FOR EACH OBJECT:\n"
    "• The 'system' field MUST explicitly contain ALL invariants below (not just in notes).\n"
    "• All 'system' values MUST be pairwise unique and differ from BASE by ≥15 characters (rewording is fine).\n"
    "• Keep mutations SMALL (tone, brevity, bullet tightness, cite clarity), no semantic drift.\n"
    "Invariants the 'system' must state explicitly:\n"
    "• 160–190 words\n"
    "• Structure: 1 intro sentence; exactly 3 bullets starting with '• '; 1 wrap sentence\n"
    "• Exactly TWO inline citations [1](URL) and [2](URL)\n"
    "• Citations appear ONLY at the END of the FIRST and LAST bullet\n"
    "• Plain prose only (no headings, no code fences)\n"
)

_MUTATOR_USER_TPL = (
    "BASE_SYSTEM_PROMPT:\n"
    "{base}\n\n"
    "TASK: Propose {k} SMALL mutations of the above system prompt.\n"
    "Return ONLY a JSON array (no prose, no <think>, no code fences)."
)

def propose_variant_one(
    base_system: str,
    model: str = "deepseek-r1:1.5b",
    temperature: float = 0.45,
) -> Dict[str, str] | None:
    """
    Ask for ONE mutation as a single JSON object: {"id","system","notes"}.
    Retries once if parsing fails or 'system' missing.
    """
    sys_msg = _MUTATOR_SYS
    user_tpl = (
        "BASE_SYSTEM_PROMPT:\n{base}\n\n"
        "TASK: Propose ONE SMALL mutation of the above system prompt.\n"
        "Return ONLY ONE JSON object with keys exactly: id, system, notes. No array, no prose, no <think>."
    )
    messages = [
        {"role": "system", "content": sys_msg},
        {"role": "user", "content": user_tpl.format(base=base_system)},
    ]
    options = {"temperature": temperature, "num_predict": 900, "num_ctx": 8192, "format": "json"}
    # call
    content = _chat_with_timeout(model, messages, options, timeout=30.0)
    content = _clean_text(content)
    # Extract first {...} block in case model wraps
    import re as _re
    m = _re.search(r"\{[\s\S]*\}", content)
    if m:
        content = m.group(0)
    def _parse_one(txt: str):
        try:
            obj = json.loads(txt)
            if isinstance(obj, dict) and obj.get("system"):
                return {"id": str(obj.get("id") or "m1"), "system": str(obj["system"]).strip(), "notes": str(obj.get("notes","")).strip()}
        except Exception:
            pass
        return None
    out = _parse_one(content)
    if out:
        return out
    # strict retry
    print("[mutator.one] strict retry", flush=True)
    strict_msgs = [
        {"role":"system","content": sys_msg + "\nReturn ONE JSON OBJECT ONLY."},
        {"role":"user","content": user_tpl.format(base=base_system)},
    ]
    strict_opts = {"temperature": max(temperature, 0.5), "num_predict": 1100, "num_ctx": 8192, "format":"json"}
    c2 = _chat_with_timeout(model, strict_msgs, strict_opts, timeout=32.0)
    c2 = _clean_text(c2)
    m2 = _re.search(r"\{[\s\S]*\}", c2)
    if m2:
        c2 = m2.group(0)
    out2 = _parse_one(c2)
    if out2:
        return out2
    # fallback to qwen3:0.6b if still no parse
    fallback_models = ["qwen3:0.6b"]
    for fb in fallback_models:
        fb_opts = {"temperature": 0.4, "num_predict": 800, "num_ctx": 8192, "format": "json"}
        c3 = _chat_with_timeout(fb, messages, fb_opts, timeout=20.0)
        c3 = _clean_text(c3)
        m3 = _re.search(r"\{[\s\S]*\}", c3)
        if m3:
            c3 = m3.group(0)
        out3 = _parse_one(c3)
        if out3:
            return out3
    return None

def propose_variants(
    base_system: str,
    k: int = 5,
    model: str = "deepseek-r1:1.5b",
    temperature: float = 0.45,
) -> List[Dict[str, str]]:
    """
    Generate k distinct mutations by invoking propose_variant_one k times.
    Enforces uniqueness and the invariants via existing cleaners.
    """
    from difflib import SequenceMatcher
    def sim(a,b): 
        return SequenceMatcher(None, a, b).ratio()
    outs: List[Dict[str,str]] = []
    attempts = 0
    # 2) give DeepSeek a bit more room
    max_attempts = k*4
    print(f"[mutator] target={k}, model={model}", flush=True)
    from concurrent.futures import ThreadPoolExecutor, as_completed
    concurrency = 3
    while len(outs) < k and attempts < max_attempts:
        batch = min(concurrency, max_attempts - attempts, k - len(outs))
        if batch <= 0:
            break
        print(f"[mutator] launch batch size={batch} (attempts {attempts+1}-{attempts+batch}/{max_attempts})", flush=True)
        with ThreadPoolExecutor(max_workers=batch) as ex:
            futs = [ex.submit(propose_variant_one, base_system, model, temperature) for _ in range(batch)]
            for fut in as_completed(futs):
                attempts += 1
                try:
                    one = fut.result()
                except Exception:
                    one = None
                if not one or not one.get("system"):
                    print("[mutator] skip: empty response", flush=True)
                    continue
                sys_s = _clean_text(one["system"])
                if not sys_s:
                    print("[mutator] skip: empty after clean", flush=True)
                    continue
                # 1) relaxed invariant check + 2) invariant tail if near-miss
                def _has_invariants(s: str) -> bool:
                    l = s.lower()
                    has_len = ("160–190" in l) or ("160-190" in l) or ("160 to 190" in l)
                    has_bullets = ("• " in s) or ("three bullets" in l) or ("3 bullets" in l)
                    has_cites = ("[1](" in s and "[2](" in s) or ("two citations" in l and "[1](" in s)
                    # accept common paraphrases of placement
                    pos_ok = (
                        ("first" in l and "last" in l) or
                        ("both" in l and "first" in l and "last" in l) or
                        ("end of the first" in l and "end of the last" in l) or
                        ("at the end of the first and last bullet" in l)
                    )
                    return has_len and has_bullets and has_cites and pos_ok

                def _enforce_invariant_tail(s: str) -> str:
                    tail = (
                        " Invariants: 160–190 words; structure = intro, three bullets starting with '• ', wrap; "
                        "exactly two citations [1](URL) at the end of the FIRST bullet and [2](URL) at the end of the LAST bullet; "
                        "plain prose only."
                    )
                    # append only if not already present
                    if "[1](" not in s or "[2](" not in s or "first" not in s.lower() or "last" not in s.lower():
                        return (s.rstrip() + tail).strip()
                    return s

                if not _has_invariants(sys_s):
                    sys_s = _enforce_invariant_tail(sys_s)
                if not _has_invariants(sys_s):
                    print("[mutator] skip: missing invariants", flush=True)
                    continue
                if any(sim(sys_s, o["system"]) >= 0.92 for o in outs):
                    print("[mutator] skip: too similar to existing", flush=True)
                    continue
                one["system"] = sys_s
                outs.append(one)
                print(f"[mutator] accepted {len(outs)}/{k}", flush=True)
    # 3) add qwen3:0.6b as a fallback if still short
    while len(outs) < k:
        print("[mutator] fallback → qwen3:0.6b", flush=True)
        fb = propose_variant_one(base_system, model="qwen3:0.6b", temperature=max(0.35, temperature))
        if not fb or not fb.get("system"):
            print("[mutator] fallback skip: empty response", flush=True)
            break
        sys_s = _clean_text(fb["system"])
        if not sys_s:
            print("[mutator] fallback skip: empty after clean", flush=True)
            break
        # try to enforce tail on fallback too
        if not _has_invariants(sys_s):
            sys_s = _enforce_invariant_tail(sys_s)
        if not _has_invariants(sys_s):
            print("[mutator] fallback skip: missing invariants", flush=True)
            break
        if any(sim(sys_s, o["system"]) >= 0.92 for o in outs):
            print("[mutator] fallback skip: too similar to existing", flush=True)
            break
        fb["system"] = sys_s
        outs.append(fb)
        print(f"[mutator] accepted {len(outs)}/{k}", flush=True)
    return outs

if __name__ == "__main__":
    import sys
    base = ""
    if not sys.stdin.isatty():
        base = sys.stdin.read().strip()
    if not base:
        base = (
            "You are a precise synthesizer. Write 160–190 words.\n"
            "Structure exactly: 1-sentence intro; three bullets starting with '• '; 1-sentence wrap.\n"
            "Use exactly TWO citations [1](URL) and [2](URL) at the END of the FIRST and LAST bullet.\n"
            "Plain prose only."
        )
    muts = propose_variants(base, k=5, model="deepseek-r1:1.5b")
    if not muts:
        print("[]", flush=True)
    else:
        print(json.dumps(muts, indent=2))
