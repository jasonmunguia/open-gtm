"""ICP loading and validation.

The ICP file is the ONLY place strategy lives. Code in this repo is generic;
if you find yourself hardcoding a vertical, a title, or a company name in a
module, it belongs here instead. (The original system compiled the ICP into
8 of 10 scripts, which is why changing it meant reverse-engineering Python.)
"""
import re
from pathlib import Path

import yaml

from .normalize import normc

REPO = Path(__file__).resolve().parent.parent


class ICP:
    def __init__(self, raw, path):
        self.raw = raw
        self.path = path
        self.name = raw["name"]
        for req in ("fit", "misfit", "segments", "titles", "drop", "lanes"):
            if req not in raw:
                raise ValueError(f"{path}: missing required section `{req}`")
        if not raw["titles"].get("ops"):
            raise ValueError(f"{path}: titles.ops is empty — the joiner would keep nothing")

        # The joiner regex is GENERATED from the title list, never hand-edited.
        # Scar: a hand-maintained regex silently discarded 641 leads for ~4
        # rounds because newly discovered plant-floor titles didn't match it.
        # Generating from the union means adding a title phrase re-prices the
        # whole corpus on the next join (person-level dedup makes rescans safe).
        self.ops_re = re.compile("|".join(raw["titles"]["ops"]), re.IGNORECASE)
        self.bad_re = re.compile("|".join(raw["titles"]["bad"]), re.IGNORECASE) if raw["titles"].get("bad") else None
        self.drop_re = re.compile("|".join(raw["drop"]["patterns"]), re.IGNORECASE) if raw["drop"].get("patterns") else None
        self.drop_named = {normc(x) for x in raw["drop"].get("named", [])}
        self.min_employees = int(raw.get("min_employees", 0))
        self.segments = raw["segments"]

    def title_ok(self, title):
        """Keep a title only if it matches ops AND doesn't match bad.
        BAD wins over OPS: 'VP Sales & Operations' is a seller, not a buyer."""
        t = title or ""
        if self.bad_re and self.bad_re.search(t):
            return False
        return bool(self.ops_re.search(t))

    def company_dropped(self, name):
        """True if the company fails hygiene (pattern or named drop-list)."""
        if normc(name) in self.drop_named:
            return True
        return bool(self.drop_re and self.drop_re.search(name or ""))


def load(name_or_path):
    """Load an ICP by name (icps/<name>/icp.yaml) or explicit path."""
    p = Path(name_or_path)
    if not p.suffix:
        p = REPO / "icps" / str(name_or_path) / "icp.yaml"
    if not p.is_file():
        have = sorted(d.name for d in (REPO / "icps").iterdir() if (d / "icp.yaml").is_file())
        raise FileNotFoundError(f"no ICP at {p}. Available: {', '.join(have)}")
    with open(p) as f:
        return ICP(yaml.safe_load(f), p)
