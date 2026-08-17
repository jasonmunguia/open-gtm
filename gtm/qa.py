"""QA verdict application — the audit loop, as code.

Classification (prompts/classify.md) produces FIT/MISFIT verdicts per company.
This applies them: MISFIT leads move to a recoverable sidecar, never deleted
(run 2 deleted-and-saved 366 rows; several were later re-adjudicated).

Verdict file format (JSONL): {"company": ..., "verdict": "FIT"|"MISFIT",
"segment": ..., "reason": ..., "why": ...} — written by the agent running the
classify prompt, consumed here deterministically.
"""
import json

from .normalize import normc


def load_verdicts(path):
    v = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            v[normc(d.get("company", ""))] = d
    return v


def apply(leads, verdicts, removed_path=None):
    """Split leads by company verdict. Unclassified companies KEEP their leads
    (a missing verdict is a coverage gap to fix, not a silent drop)."""
    kept, removed = [], []
    for r in leads:
        v = verdicts.get(normc(r.get("company", "")))
        if v and v.get("verdict") == "MISFIT":
            r["misfit_reason"] = v.get("reason", "?")
            removed.append(r)
        else:
            if v and v.get("segment"):
                r["icp"] = v["segment"]
            kept.append(r)
    if removed_path and removed:
        with open(removed_path, "w") as f:
            f.writelines(json.dumps(r) + "\n" for r in removed)
    return kept, removed
