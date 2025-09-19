from __future__ import annotations
from typing import List, Dict

# Five prompt variants; all preserve:
# exactly two citations at the END of the FIRST and LAST bullet.
PROMPT_VARIANTS: List[Dict[str, str]] = [
    {
        "id": "v1",
        "system": (
            "Write 160–190 words, plain prose.\n"
            "Structure exactly: one intro sentence; three bullets starting with '• '; one wrap sentence.\n"
            "Use exactly two inline citations as [1](URL) and [2](URL), placed at the END of the FIRST and LAST bullet."
        ),
        "notes": "baseline",
    },
    {
        "id": "v2",
        "system": (
            "Plain style; avoid lists except the three required bullets starting with '• '.\n"
            "Cite ONLY the provided two URLs. Use EXACTLY TWO citations [1](URL) and [2](URL) at the END of the FIRST and LAST bullet; do not place citations elsewhere."
        ),
        "notes": "strong cite instruction",
    },
    {
        "id": "v3",
        "system": (
            "Keep bullets tight: each bullet ≤ 22 words, starts with '• ', and is specific.\n"
            "Append exactly two citations [1](URL) and [2](URL) at the END of the FIRST and LAST bullet, respectively."
        ),
        "notes": "tighter bullets",
    },
    {
        "id": "v4",
        "system": (
            "Target length 160–190 words. Maintain flow: 1 intro line, 3 bullets ('• '), 1 wrap line.\n"
            "Use exactly two citations [1](URL) and [2](URL) at the END of the FIRST and LAST bullet."
        ),
        "notes": "explicit 160–190 hint",
    },
    {
        "id": "v5",
        "system": (
            "Prioritize brevity and clarity; cut filler.\n"
            "Structure: intro; three '• ' bullets; wrap. Place exactly two citations [1](URL) and [2](URL) at the END of the FIRST and LAST bullet."
        ),
        "notes": "brevity + clarity",
    },
]

def get_variants() -> List[Dict[str, str]]:
    return PROMPT_VARIANTS
