Primordium Evolv Swarm
=======================

Overview
- A local, Ollama‑backed research + synthesis stack with routing, verification and judging.
- Includes an evolving prompt mutator and an experiment runner to evaluate mutated system prompts against a small gold set.

Prerequisites
- Python 3.11+ (3.12 recommended)
- Local Ollama server running with models (suggested):
  - llama3.2:1b (judge primary), qwen2.5:0.5b-instruct (judge secondary)
  - gemma3:1b (synthesizer), qwen3:0.6b (planner/verifier alt)
  - embeddinggemma:300m (health checks)
  - Optional for mutator: deepseek-r1:1.5b

Quick Start
- Health: `PYTHONPATH=. python app/scripts/run_health.py`
- Smoke HRM: `PYTHONPATH=. python -m app.scripts.smoke_hrm "summarize today’s AI news with exactly two citations"`
- Web search only: `PYTHONPATH=. python - <<'PY'\nfrom app.operators.searcher import search_web; print(search_web('today AI research news', k=3))\nPY`

Gold Set Eval
- Evaluate: `PYTHONPATH=. python app/gold/eval.py`
- Summarize: `PYTHONPATH=. python app/gold/summary.py`

Mutator + Experiment
- Generate prompt variants (DeepSeek, can take minutes):
  - `PYTHONPATH=. python - <<'PY'\nfrom app.evolve.mutator import propose_variants\nbase = ("You are a precise synthesizer. Write 160–190 words.\n"
        "Structure: intro; three bullets starting with '• '; wrap.\n"
        "Use exactly TWO citations [1](URL) and [2](URL) at the END of the FIRST and LAST bullet.\n"
        "Plain prose only.")\nprint(propose_variants(base, k=2, model='deepseek-r1:1.5b', temperature=0.45))\nPY`
- Full experiment (mutate k variants, run over gold set, judge, save results):
  - `PYTHONPATH=. python app/evolve/experiment.py`
  - Results: `data/evolve/<timestamp>/{results.jsonl, best.system.txt, summary.json}` and `data/evolve/latest` symlink

Routing
- Use `from app.config import get_models` to select models per goal:
  - `from app.config import get_models; print(get_models('plan steps for AI citations'))`

Notes
- The mutator uses progress logs and timeouts; DeepSeek generations are long and may need retries. Fallback to qwen3:0.6b is enabled for resilience.
- The synthesizer enforces two inline citations pinned to the first and last bullet and strips extra URLs.

