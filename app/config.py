"""
Repository configuration.

Centralizes static limits and routed model picks.
Use:
  from app.config import get_models, get_config

get_models(goal) -> {
  'planner_model', 'synthesizer_model', 'verifier_model',
  'judge_primary', 'judge_secondary'
}

get_config() -> {
  'embed_model', 'judge_weights', 'limits'
}
"""

from __future__ import annotations

from app.router import choose_models

# Static settings that do NOT depend on the goal
embed_model = "embeddinggemma:300m"
judge_weights = {"llm": 0.7, "heur": 0.3}  # 70/30 as agreed
limits = dict(max_concurrent_models=2, max_answer_words=200)

def get_models(goal: str) -> dict:
    """
    Return routed model selections for a given goal.
    Keys: planner_model, synthesizer_model, verifier_model, judge_primary, judge_secondary
    """
    return choose_models(goal)

def get_config() -> dict:
    """
    Return static configuration (no routing).
    """
    return {
        "embed_model": embed_model,
        "judge_weights": judge_weights,
        "limits": limits,
    }
