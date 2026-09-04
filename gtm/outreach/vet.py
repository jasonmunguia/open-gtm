"""The gates, in the order they run. All machine-checked, before any send.

  1. ledger dedupe      — already attempted → skip (never re-source)
  2. protected          — on your no-touch list → skip, and never even visit
  3. employment (API)   — no CURRENT position → skip. The headline is never
                          consulted: it is self-written and stale.
  4. employer deny-list — substring on the API-returned company name
  5. title deny-list    — substring on the API-returned title

Gates 1-2 run on search-card data (cheap, no profile visit). Gates 3-5 need
the profile open. `vet()` is pure so every gate is testable offline.
"""


def current_position(positions):
    """First position with no end date, or None. `positions` is the parsed
    output of js/current_role.js: [{co, t, end: 'current'|'ended'}]."""
    if not isinstance(positions, list):
        return None
    for p in positions:
        if isinstance(p, dict) and p.get("end") == "current":
            return p
    return None


def precheck(cand, cfg, attempted):
    """Gates 1-2, from the search card alone. Returns a reason or None."""
    url = cand["url"].rstrip("/")
    if url in attempted:
        return "already attempted"
    if cfg.is_protected(url, cand.get("name", "")):
        return "protected"
    return None


def vet(cand, positions, cfg):
    """Gates 3-5. `positions` None means the API call itself failed — that is
    an infrastructure verdict, not a candidate verdict, and the caller counts
    it separately (three in a row = session problem, abort the run)."""
    if positions is None or (isinstance(positions, dict) and positions.get("err")):
        return "position API failed"
    cur = current_position(positions)
    if not cur:
        return "no current position (job seeker / stale headline)"
    co, title = str(cur.get("co") or ""), str(cur.get("t") or "")
    if any(b in co.lower() for b in cfg.deny_employers):
        return f"excluded employer: {co}"
    if any(b in title.lower() for b in cfg.deny_titles):
        return f"excluded title: {title}"
    cand["company"], cand["title"] = co, title
    return None
