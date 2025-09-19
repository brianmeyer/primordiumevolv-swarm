from app.config import get_models, judge_weights
from app.judge_llm import ask_llm_judge
from app.judge_heur import score_heuristic


def score(output, snippets):
    text = output.get("answer", "")
    # Router returns fixed judge models regardless of goal; empty goal is fine.
    models = get_models("")
    judge_primary = models.get("judge_primary", "llama3.2:1b")
    judge_tiebreak = models.get("judge_secondary", "qwen2.5:0.5b-instruct")
    judge_mismatch_delta = 0.25
    hh = score_heuristic(output, snippets)
    jp = ask_llm_judge(judge_primary, text, snippets, temperature=0.0)

    # If primary failed to produce JSON/any content, fall back to heuristic-only this run
    if (jp.get("notes", "") or "").startswith(("parse_error", "empty_output")):
        return {
            "score": hh["score"],
            "length_ok": hh.get("length_ok", True),
            "citation_ok": hh.get("citation_ok", True),
            "rubric_notes": f"fallback: llm_primary_{jp.get('notes','')}; heur={hh['score']:.2f}",
            "llm_primary_raw": jp.get("raw", ""),
            "llm_tiebreak_raw": "",
        }

    w = judge_weights  # e.g., {"llm":0.8,"heur":0.2}
    prim_score = float(jp.get("score", 0.0))
    heur_score = float(hh.get("score", 0.0))
    blended = w["llm"] * prim_score + w["heur"] * heur_score

    notes = f"blend only; prim={prim_score:.2f}; heur={heur_score:.2f}"
    length_ok = bool(jp.get("length_ok", True))
    citation_ok = bool(jp.get("citation_ok", True))
    llm_tie_raw = ""

    # If large discrepancy between primary LLM and heuristic, consult secondary and blend all 3
    try:
        gap = abs(prim_score - heur_score)
    except Exception:
        gap = 0.0
    if gap >= float(judge_mismatch_delta):
        js = ask_llm_judge(judge_tiebreak, text, snippets, temperature=0.0)
        tie_score = float(js.get("score", 0.0)) if not (js.get("notes", "").startswith(("parse_error", "empty_output"))) else None
        if tie_score is not None:
            llm_part = (prim_score + tie_score) / 2.0
            blended = w["llm"] * llm_part + w["heur"] * heur_score
            length_ok = bool(jp.get("length_ok", True)) and bool(js.get("length_ok", True))
            citation_ok = bool(jp.get("citation_ok", True)) and bool(js.get("citation_ok", True))
            notes = f"3-blend; prim={prim_score:.2f}; tie={tie_score:.2f}; heur={heur_score:.2f}"
            llm_tie_raw = js.get("raw", "")
        else:
            notes = f"blend only; prim={prim_score:.2f}; heur={heur_score:.2f} (tie_parse_error)"

    return {
        "score": max(0.0, min(1.0, blended)),
        "length_ok": length_ok,
        "citation_ok": citation_ok,
        "rubric_notes": notes,
        "llm_primary_raw": jp.get("raw", ""),
        "llm_tiebreak_raw": llm_tie_raw,
    }
