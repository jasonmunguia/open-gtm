"""Load browser-side JS from ./js, substituting placeholders SAFELY.

Every placeholder is replaced with json.dumps() of the value, so a candidate
named O'Brien or a note containing quotes cannot break out of the string —
the scripts run inside a logged-in LinkedIn session, which makes this the one
place in the repo where string injection would matter.
"""
import json
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent / "js"


@lru_cache(maxsize=None)
def _raw(name):
    p = HERE / f"{name}.js"
    if not p.is_file():
        raise FileNotFoundError(f"no such browser script: {p}")
    return p.read_text(encoding="utf-8")


def load(name, **subs):
    src = _raw(name)
    for key, val in subs.items():
        marker = f"__{key.upper()}__"
        if marker not in src:
            raise KeyError(f"{name}.js has no placeholder {marker}")
        src = src.replace(marker, json.dumps(val))
    return src


def name_tokens(full_name):
    """Tokens the Connect-button match must ALL satisfy. Single characters
    are dropped (initials, punctuation) — but never below two tokens, so a
    first-name-only match is impossible by construction."""
    toks = [t.strip(".,'\"") for t in full_name.split()]
    toks = [t for t in toks if len(t) > 1]
    if len(toks) < 2:
        raise ValueError(f"need a full name (2+ tokens) to target a Connect button safely: {full_name!r}")
    return toks
