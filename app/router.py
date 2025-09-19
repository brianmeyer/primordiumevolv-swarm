from __future__ import annotations

import json
import re
import sys
from typing import Dict

_CITATION_KWS = [
    "cite",
    "citation",
    "url",
    "exactly two",
    "bullets",
    "format",
]

_CREATIVE_KWS = [
    "creative",
    "tone",
    "voice",
    "marketing",
]

_IMPERATIVE_STARTS = {"plan", "outline", "steps", "draft"}


def choose_models(goal: str) -> Dict[str, str]:
    """
    Return model choices based on a tiny rule-based router.
    Keys: planner_model, synthesizer_model, verifier_model, judge_primary, judge_secondary
    """
    g = (goal or "").strip()
    gl = g.lower()

    # Defaults
    models: Dict[str, str] = {
        "planner_model": "qwen3:0.6b",
        "synthesizer_model": "gemma3:1b",
        "verifier_model": "qwen2.5:0.5b-instruct",
        "judge_primary": "llama3.2:1b",
        "judge_secondary": "qwen2.5:0.5b-instruct",
    }

    # Rule 1: citation/format-heavy tasks → strict verifier from different family
    if any(kw in gl for kw in _CITATION_KWS):
        models["verifier_model"] = "qwen2.5:0.5b-instruct"
    # Rule 2: creative/tone/marketing → friendlier same-family polish
    elif any(kw in gl for kw in _CREATIVE_KWS):
        models["verifier_model"] = "gemma3:1b"

    # Rule 3: short imperative planning prompts → stronger planner-instruct
    tokens = [t for t in re.split(r"\s+", g) if t]
    if tokens and len(tokens) <= 12 and tokens[0].lower() in _IMPERATIVE_STARTS:
        models["planner_model"] = "qwen2.5:0.5b-instruct"

    # Rule 4: judges remain fixed
    models["judge_primary"] = "llama3.2:1b"
    models["judge_secondary"] = "qwen2.5:0.5b-instruct"
    return models


if __name__ == "__main__":
    goal_arg = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    print(json.dumps(choose_models(goal_arg), indent=2))
