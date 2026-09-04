"""Phase A sourcing: tiered searches → candidate cards. Read-only.

Round-robin by tier so no tier can starve the others: at most `per_search`
from each query, cycling tier 1→2→3→…, until the pool fills. Paging goes
deeper only when a page yields nothing new.
"""
import json
import time
import urllib.parse


def search_url(query, geo_urn, page=1):
    u = ("https://www.linkedin.com/search/results/people/?keywords="
         + urllib.parse.quote(query)
         + "&geoUrn=" + urllib.parse.quote(f'["{geo_urn}"]'))
    if page > 1:
        u += f"&page={page}"
    return u


def parse_cards(raw, tier, query):
    """js/extract_search_results.js output → candidates. Drops cards that are
    only a 'mutual connection' line and names under two tokens (a Connect
    button can only be targeted safely with a full name)."""
    try:
        cards = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError):
        return []
    out = []
    for c in cards or []:
        lines = c.get("lines") or []
        if not lines or "mutual connection" in " ".join(lines):
            continue
        name = lines[0].split("•")[0].strip()
        if len(name.split()) < 2:
            continue
        out.append({"name": name, "url": c["url"].rstrip("/"), "tier": tier,
                    "headline": " | ".join(lines[1:3])[:100], "query": query})
    return out


def round_robin(searches):
    by_tier = {}
    for tier, q in searches:
        by_tier.setdefault(tier, []).append(q)
    order = []
    for i in range(max(len(v) for v in by_tier.values())):
        for tier in sorted(by_tier):
            if i < len(by_tier[tier]):
                order.append((tier, by_tier[tier][i]))
    return order


def source(page, cfg, seen, want, start_page=1, log=print, sleep=time.sleep, extract_js=None):
    """Fill a pool of up to want*3 candidates not in `seen`. `page` is any
    object with goto(url, wait) and ev(js). Returns the pool."""
    from . import js
    extract_js = extract_js or js.load("extract_search_results")
    pool, seen = [], set(seen)
    order = round_robin(cfg.searches)
    pg, max_pg = start_page, start_page + 4
    while pg <= max_pg and len(pool) < want * 3:
        got_any = False
        for tier, q in order:
            if len(pool) >= want * 3:
                break
            page.goto(search_url(q, cfg.geo_urn, pg), 8)
            added = 0
            for c in parse_cards(page.ev(extract_js), tier, q):
                if c["url"] in seen or added >= cfg.per_search:
                    continue
                seen.add(c["url"])
                pool.append(c)
                added += 1
            if added:
                got_any = True
                log(f"[T{tier} p{pg}] '{q}' -> +{added} (pool {len(pool)})")
            sleep(3)
        if not got_any:
            log(f"page {pg} yielded nothing new — stopping search")
            break
        pg += 1
    return pool
