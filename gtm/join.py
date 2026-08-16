"""Join harvested LinkedIn hits against known (person, company, title) records.

Produces lead rows: name, title, company, linkedin, lane, icp. The title
gate (icp.title_ok) runs HERE, at join time, against the generated regex —
so an ICP title edit re-prices the whole corpus on the next run.
"""
import json
import re

from .normalize import normc, normn, person_key

_SLUG = re.compile(r"linkedin\.com/in/([a-z0-9-]+)")


def first_from_hit(hit):
    """Best-effort first name: prefer the anchor text, fall back to the URL slug.

    Slug parse-errors were a documented leak in run 2 (car-dealership managers
    and college robotics clubs attached to the wrong companies), so slug-derived
    names are marked low-confidence and must be confirmed by a title-map match —
    they are never shipped on their own.
    """
    a = (hit.get("anchor") or "").strip()
    if a and not a.lower().startswith("http"):
        word = a.split()[0] if a.split() else ""
        if word.isalpha():
            return word, "anchor"
    m = _SLUG.search(hit.get("url", ""))
    if m:
        return m.group(1).split("-")[0], "slug"
    return "", "none"


def build_title_map(candidate_files):
    """Union every discovery cell's candidates into person_key -> [(title, lane, icp)].
    The map is rebuilt from ALL cells every join — never incrementally patched."""
    tmap = {}
    for path in candidate_files:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                c = json.loads(line)
                k = person_key(c.get("first", ""), c.get("company", ""))
                tmap.setdefault(k, []).append(
                    (c.get("title", ""), c.get("lane", "call"), c.get("icp", "?"))
                )
    return tmap


def join(hits, tmap, icp, curated_visit_companies):
    """Match hits to candidates; gate titles; assign lanes.

    Lane rule (the 96-row-audit scar): a company is visit-lane ONLY if it was
    curated as local (`curated_visit_companies`, normc'd). Roster/harvest
    records carry no person location, so they can never PROMOTE a company
    into the visit lane — discovery geography is not people geography.
    """
    kept, seen = [], set()
    for h in hits:
        first, source = first_from_hit(h)
        if not first:
            continue
        k = normn(first) + "|" + normc(h.get("company", ""))
        matches = tmap.get(k, [])
        if not matches and source == "slug":
            continue  # slug-only identity with no candidate match = parse-error risk
        for title, lane, icp_seg in matches:
            if not icp.title_ok(title):
                continue
            if k in seen:
                break  # person-level dedup: one row per person, ever
            seen.add(k)
            if lane == "visit" and normc(h.get("company", "")) not in curated_visit_companies:
                lane = "call"
            anchor = (h.get("anchor") or "").strip()
            kept.append({
                "name": anchor if anchor and not anchor.lower().startswith("http") else first,
                "first": first,
                "title": title,
                "company": h.get("company", ""),
                "linkedin": h.get("url", ""),
                "lane": lane,
                "icp": icp_seg,
                "evidence": "LinkedIn URL search-verified; title from candidate record",
            })
            break
    return kept
