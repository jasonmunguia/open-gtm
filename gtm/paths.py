"""Per-ICP data layout. Repo-relative always — nothing in this system may
reference an absolute path (the original hardcoded one user's Desktop into
all 10 scripts, so it ran for exactly one person on exactly one machine).

Layout per ICP:
  data/<icp>/raw/       immutable ingest shards (registries, apollo cells)
  data/<icp>/derived/   disposable — delete it and the next run rebuilds it
  data/<icp>/out/       deliverables (call/visit CSVs, outreach ledger)
  data/<icp>/outreach/  browser profile + window target for the outreach stage

raw is append-or-replace-whole-shard; the scorer/joiner never edits it.
derived being disposable is what makes every rule change a re-run instead of
a migration.
"""
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def data(icp_name):
    d = REPO / "data" / icp_name
    for sub in ("raw", "derived", "out"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    return d
