"""Outreach config — icps/<name>/outreach.yaml, produced by the interview.

This is the ONLY place your note, your targets, and your no-touch list live.
Code in this package is generic; if you find yourself editing a Python file
to change who gets contacted, the thing you're changing belongs here.
"""
from pathlib import Path

import yaml

from ..icp import REPO

NOTE_MAX = 300   # LinkedIn's connection-note limit; the dialog counter reads N/300

# Defaults are practitioner consensus, not LinkedIn policy — LinkedIn publishes
# no numbers and enforces on behaviour. ~20/day for an aged account (10-15 for
# a new one), ~100/week widely reported. Penalty for crossing is asymmetric:
# a restriction of ~a week that Support will not lift early. Undershoot.
DEFAULTS = {
    "geo_urn": "103644278",       # United States. Others: SETUP.md §9
    "daily_target": 20,
    "weekly_cap": 100,
    "weekly_buffer": 10,          # headroom for invites you send by hand
    "gap_minutes": [1, 4],        # randomized per send; never identical intervals
    "per_search": 6,              # cap per query so one search cannot dominate the pool
    "bench": 0.5,                 # vet 50% more than you send: "no Connect path" is only
                                  # visible after opening a profile (20 vetted → 18 sent)
    "max_rounds": 6,              # refill rounds before admitting the pool is dry
    "deny_employers": [],
    "deny_titles": [],
    "protected": [],
    "browser": {},
}


class OutreachConfig:
    def __init__(self, raw, path):
        self.path = path
        merged = {**DEFAULTS, **(raw or {})}

        note = merged.get("note")
        if not isinstance(note, str) or not note.strip():
            raise ValueError(f"{path}: `note` is required — it is the only text typed into the dialog")
        note = note.strip()
        if len(note) > NOTE_MAX:
            raise ValueError(f"{path}: note is {len(note)} chars; LinkedIn allows {NOTE_MAX}. "
                             f"The runner refuses to send a truncated note.")
        self.note = note

        searches = merged.get("searches")
        if not isinstance(searches, list) or not searches:
            raise ValueError(f"{path}: `searches` must be a non-empty list of {{tier, query}}")
        self.searches = []
        for s in searches:
            if not isinstance(s, dict) or not s.get("query"):
                raise ValueError(f"{path}: every search needs a `query`: {s!r}")
            self.searches.append((str(s.get("tier", "1")), str(s["query"]).strip()))

        lo, hi = merged["gap_minutes"]
        if not (0 < lo <= hi):
            raise ValueError(f"{path}: gap_minutes must be [lo, hi] with 0 < lo <= hi")
        self.gap_minutes = (float(lo), float(hi))

        self.daily_target = int(merged["daily_target"])
        self.weekly_cap = int(merged["weekly_cap"])
        self.weekly_buffer = int(merged["weekly_buffer"])
        if self.daily_target <= 0 or self.weekly_cap <= self.weekly_buffer or self.weekly_buffer < 0:
            raise ValueError(f"{path}: need daily_target > 0 and weekly_cap > weekly_buffer >= 0")
        self.per_search = int(merged["per_search"])
        self.bench = float(merged["bench"])
        self.max_rounds = int(merged["max_rounds"])
        self.geo_urn = str(merged["geo_urn"])

        self.deny_employers = [str(x).lower() for x in merged["deny_employers"]]
        self.deny_titles = [str(x).lower() for x in merged["deny_titles"]]
        self.protected = {_protect_key(x) for x in merged["protected"]}
        self.browser = dict(merged["browser"] or {})

    def is_protected(self, url, name):
        """True if this profile is on the no-touch list — matched by slug OR by
        full name, so a vendor listed by name is caught even if their URL was
        never recorded. Protected profiles are never even visited."""
        return _protect_key(url) in self.protected or _protect_key(name) in self.protected


def _protect_key(entry):
    e = str(entry).strip().lower().rstrip("/")
    if "/in/" in e:
        e = e.split("/in/", 1)[1].split("/")[0].split("?")[0]
    return e


def load(name_or_path):
    p = Path(name_or_path)
    if not p.suffix:
        p = REPO / "icps" / str(name_or_path) / "outreach.yaml"
    if not p.is_file():
        raise FileNotFoundError(
            f"no outreach config at {p}. Run prompts/outreach-interview.md with your "
            f"agent to produce it (schema: icps/example/outreach.yaml)")
    with open(p) as f:
        return OutreachConfig(yaml.safe_load(f), p)
