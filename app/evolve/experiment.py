from __future__ import annotations

import json, os, time
from statistics import mean
from typing import List, Dict

from app.evolve.mutator import propose_variants
from app.gold.io import load_gold
from app.operators.searcher import search_web
from app.operators.synthesizer import synthesize
from app.judge import score
from app.config import get_models

def run_experiment(base_system: str, k: int = 5, mut_model: str = "deepseek-r1:1.5b") -> Dict:
    variants = propose_variants(base_system, k=k, model=mut_model, temperature=0.45)
    if not variants:
        return {"ok": False, "error": "no_variants"}

    gold = load_gold()
    if not gold:
        return {"ok": False, "error": "no_gold_items"}

    results = []
    for v in variants:
        sys_prompt = v["system"]
        scores: List[float] = []
        for item in gold:
            q = item["query"]
            sn = search_web(q, k=4)
            models = get_models(q)
            out = synthesize(sn, model=models.get("synthesizer_model"), system_override=sys_prompt)
            j = score(out, sn)
            scores.append(float(j.get("score", 0.0)))
        results.append({
            "id": v.get("id",""),
            "notes": v.get("notes",""),
            "avg_score": round(mean(scores), 4),
            "n": len(scores),
            "system": sys_prompt,
        })

    results.sort(key=lambda x: x["avg_score"], reverse=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    outdir = f"data/evolve/{ts}"
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "results.jsonl"), "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(os.path.join(outdir, "best.system.txt"), "w", encoding="utf-8") as f:
        f.write(results[0]["system"])
    with open(os.path.join(outdir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump({"ok": True, "best": results[0], "all": results}, f, ensure_ascii=False, indent=2)
    latest = "data/evolve/latest"
    try:
        if os.path.islink(latest) or os.path.exists(latest):
            try: os.unlink(latest)
            except Exception: pass
        os.symlink(outdir, latest)
    except Exception:
        pass
    return {"ok": True, "dir": outdir, "best": results[0]}

if __name__ == "__main__":
    base = (
        "You are a precise synthesizer. Write 160–190 words.\n"
        "Structure: intro; three bullets starting with '• '; wrap.\n"
        "Use exactly TWO citations [1](URL) and [2](URL) at the END of the FIRST and LAST bullet.\n"
        "Plain prose only."
    )
    out = run_experiment(base, k=5, mut_model="deepseek-r1:1.5b")
    print(json.dumps(out, indent=2, ensure_ascii=False))
