"""Company hygiene — apply the ICP's drop rules to a company universe.

Registry-first discovery makes this cheap: most junk never enters (the
registry IS the universe). Hygiene catches what keyword-tag discovery drags
in — run 1 "ate vendor junk" precisely because it guessed the universe via
Apollo keywords instead of pulling the registry first.

Never deletes: dropped rows go to a sidecar file, recoverable (the audit
pattern — 366 MISFIT rows in run 2 were saved to audit_removed_rows.csv,
and several were later re-adjudicated).
"""
import json


def clean(companies, icp, dropped_path=None):
    kept, dropped = [], []
    for c in companies:
        (dropped if icp.company_dropped(c.get("company", "")) else kept).append(c)
    if dropped_path and dropped:
        with open(dropped_path, "w") as f:
            for c in dropped:
                f.write(json.dumps(c) + "\n")
    return kept, dropped
