from typing import List
from ollama import chat

PLANNER_SYS = (
    "You are a hierarchical planner. Decompose the GOAL into 2–5 numbered steps. "
    "Prefer short, tool-aware steps like: search, select top-2 URLs, draft, verify, finalize. "
    "Output plain text only (numbered lines)."
)

def plan(goal: str, model: str = "llama3.2:1b") -> List[str]:
    resp = chat(
        model=model,
        messages=[
            {"role": "system", "content": PLANNER_SYS},
            {"role": "user", "content": f"GOAL: {goal}"},
        ],
        options={"temperature": 0.2, "num_predict": 256},
    )
    text = (resp.get("message") or {}).get("content", "").strip()
    steps = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        # accept formats like "1. do X" or "1) do X"
        if ln[0].isdigit():
            parts = ln.split(".", 1) if "." in ln else ln.split(")", 1)
            if len(parts) == 2:
                steps.append(parts[1].strip())
                continue
        steps.append(ln)
    return steps[:5]
