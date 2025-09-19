#!/usr/bin/env python3
"""Run readiness checks and print a 1-line summary.

Example:
  READY: synth=✓ judge=✓ judge2=✓ embed=✓

Exits with code 0 if ready, else 1.
"""

from __future__ import annotations

import sys

from app.utils.health_check import readiness
from app.config import get_config


def main() -> int:
    cfg = get_config()
    report = readiness()
    ready = bool(report.get("ready", False))

    synth_ok = bool(report.get(cfg.get("synthesizer_model"), False))
    judge_ok = bool(report.get(cfg.get("judge_model_fast"), False))
    judge2_ok = bool(report.get(cfg.get("judge_model_backup"), False))
    embed_ok = bool(report.get(cfg.get("embed_model"), False))

    tick = lambda ok: "✓" if ok else "✗"
    summary = (
        f"READY: synth={tick(synth_ok)} "
        f"judge={tick(judge_ok)} "
        f"judge2={tick(judge2_ok)} "
        f"embed={tick(embed_ok)}"
    )
    print(summary)
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())

