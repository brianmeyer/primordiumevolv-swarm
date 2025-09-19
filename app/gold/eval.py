import json
from app.gold.io import load_gold
from app.operators.searcher import search_web
from app.operators.synthesizer import synthesize
from app.judge import score
from app.config import get_models

def run_eval(path="data/gold/items.jsonl", k=3, out="data/gold/results.jsonl"):
    items = load_gold(path)
    out_f = open(out, "w", encoding="utf-8")
    for it in items:
        q = it["query"]
        sn = search_web(q, k=k)
        models = get_models(q)
        ans = synthesize(sn, model=models.get("synthesizer_model"))
        j = score(ans, sn)
        rec = {"id": it["id"], "query": q, "score": j.get("score"), "length_ok": j.get("length_ok"), "citation_ok": j.get("citation_ok")}
        out_f.write(json.dumps(rec) + "\n")
    out_f.close()

if __name__ == "__main__":
    run_eval()
