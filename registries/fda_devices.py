"""openFDA device establishment registrations.

The medical-device universe, per state, as a real JSON API — no key needed at
low volume (240 req/min, 1k/day unkeyed; a free key raises it). This registry
was run 1's visit-lane goldmine: 92 of 163 visit leads.

Access (verified 2026-08-16): 23,279 CA establishments.
    https://api.fda.gov/device/registrationlisting.json?search=registration.state_code:CA&limit=2
Fields: registration.{name, address_line_1, city, state_code, postal_code,
owner_operator, fei_number, ...}
"""
import json
import urllib.parse
import urllib.request

BASE = "https://api.fda.gov/device/registrationlisting.json"
PAGE_LIMIT = 100  # API max per request; paginate with skip (max skip 25k)


def fetch(state, max_rows=2000, timeout=60):
    rows, skip = [], 0
    while skip < max_rows:
        q = urllib.parse.urlencode({
            "search": f"registration.state_code:{state}",
            "limit": PAGE_LIMIT,
            "skip": skip,
        })
        req = urllib.request.Request(f"{BASE}?{q}", headers={"User-Agent": "gtm-system registry pull"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                d = json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                break  # past the last page
            raise
        results = d.get("results", [])
        if not results:
            break
        rows.extend(results)
        skip += PAGE_LIMIT
    return rows


def to_companies(rows):
    out, seen = [], set()
    for r in rows:
        reg = r.get("registration", {})
        name = (reg.get("name") or "").strip()
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        out.append({
            "company": name,
            "address": f"{reg.get('address_line_1','')}, {reg.get('city','')}, {reg.get('state_code','')} {reg.get('postal_code','')}",
            "source": "fda_devices",
        })
    return out
