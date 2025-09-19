#!/usr/bin/env python3
"""End-to-end demo: search → synthesize → score.

Prints 6 lines:
1) GOAL
2) MODEL
3) SCORE
4) NOTES
5) PREVIEW (first 200 chars)
6) CITATIONS (comma-separated)
"""

from __future__ import annotations

import sys

from app.config import get_config
from app.operators.searcher import search_web
from app.operators.synthesizer import synthesize
from app.judge import score


def main() -> int:
    goal = "Summarize today’s AI news with 2 sources"

    cfg = get_config()
    model = cfg.get("synthesizer_model")

    snippets = search_web(goal, k=4)
    out = synthesize(snippets, model=model)
    answer = out.get("answer", "")
    j = score(out, snippets)
    sc = float(j.get("score", 0.0))

    # Prepare outputs (exactly 6 lines)
    preview = (answer or "").replace("\n", " ")[:200]
    citations = ", ".join(out.get("citations", []))

    print(f"GOAL: {goal}")
    print(f"MODEL: {model}")
    print(f"SCORE: {sc:.2f}")
    print(f"NOTES: {j.get('rubric_notes','')}")
    print(f"PREVIEW: {preview}")
    print(f"CITATIONS: {citations}")

    return 0 if sc >= 0.6 else 1


if __name__ == "__main__":
    sys.exit(main())
