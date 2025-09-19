from __future__ import annotations

import json
from typing import List, Dict


def load_gold(path: str = "data/gold/items.jsonl") -> List[Dict]:
    """Load a JSONL gold set and perform tiny validation.

    Ensures each item has keys: id, query, allowed_urls, notes.
    Returns a list of dicts; silently skips malformed lines.
    """
    items: List[Dict] = []
    required = {"id", "query", "allowed_urls", "notes"}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if not isinstance(obj, dict):
                    continue
                if not required.issubset(obj.keys()):
                    continue
                if not isinstance(obj.get("allowed_urls"), list):
                    continue
                items.append(obj)
    except FileNotFoundError:
        return []
    return items

