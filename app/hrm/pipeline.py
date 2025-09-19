from typing import Any, Dict
from app.hrm.planner import plan
from app.operators.searcher import search_web
from app.operators.synthesizer import synthesize
from app.hrm.verifier import check, suggest_edit
from app.judge import score

def run(goal: str) -> Dict[str, Any]:
    steps = plan(goal)
    # Researcher: your existing web searcher
    sn = search_web(goal, k=4)
    # Synthesizer: uses first two URLs and clamps citations
    out = synthesize(sn)
    allowed = out.get("citations", [])[:2]
    # Verifier pass
    rep = check(out["answer"], allowed)
    if not all([rep["word_count_ok"], rep["bullets_ok"], rep["citation_ok"]]) and len(allowed) == 2:
        out["answer"] = suggest_edit(out["answer"], rep, allowed[0], allowed[1])
    # Judge
    j = score(out, sn)
    return {"steps": steps, "out": out, "report": rep, "judge": j}
