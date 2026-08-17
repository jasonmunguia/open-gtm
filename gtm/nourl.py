"""NO-URL promotion — ship champion-titled candidates that never matched a URL.

The harvest only converts a fraction of candidates to LinkedIn URLs. Run 1
left ~4,500 verified name+title+company rows unconverted and never ran this
pass; the v2 retro's verdict was "don't skip it." A verified person WITH a
gate-passing title and WITHOUT a URL is still a dialable lead — the URL is
evidence, not the product. Phone-first makes this stage bigger, not smaller.

Promoted rows are marked so the caller (or the human) knows the LinkedIn
column is a lookup task, not a verified link.
"""
import json

from .normalize import person_key


def promote(candidate_files, joined_keys, icp):
    """candidate_files: the same shards the joiner read.
    joined_keys: set of person_key() already shipped with URLs.
    Returns lead rows for gate-passing candidates the harvest never matched."""
    promoted, seen = [], set(joined_keys)
    for path in candidate_files:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                c = json.loads(line)
                k = person_key(c.get("first", ""), c.get("company", ""))
                if k in seen:
                    continue
                if not icp.title_ok(c.get("title", "")):
                    continue
                seen.add(k)
                promoted.append({
                    "name": c.get("first", ""),
                    "first": c.get("first", ""),
                    "title": c.get("title", ""),
                    "company": c.get("company", ""),
                    "linkedin": "",
                    "lane": "call",  # no URL -> no visit promotion, ever
                    "icp": c.get("icp", "?"),
                    "evidence": "NO-URL: candidate verified at discovery; LinkedIn is a manual lookup",
                })
    return promoted
