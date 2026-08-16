"""USDA FSIS Meat, Poultry & Egg Product Inspection Directory.

THE meat-processing universe: every federally inspected US plant. ~7,200 rows
with name, street/city/state/zip, PHONE (a phone-first pipeline's dream —
the registry hands you switchboard numbers for free), grant date, activities,
size class, and lat/lon (so no geocoding needed for visit-radius checks).

Access (verified 2026-08-16): the site 403s plain curl (Akamai). The CSV is
fetched from INSIDE a stealth browser page, where the bot-check cookies apply.
Requires `scrapling` (imported lazily so the rest of the pipeline runs
without it).

    from registries import fsis
    rows = fsis.fetch()          # list[dict], keys = CSV header
"""
import csv
import io

PAGE = "https://www.fsis.usda.gov/inspection/establishments/meat-poultry-and-egg-product-inspection-directory"
CSV_PATH = "/sites/default/files/media_file/documents/MPI_Directory_by_Establishment_Name.csv"

# Verified header (2026-08-16):
# establishment_id, establishment_number, establishment_name, duns_number,
# street, city, state, zip, phone, grant_date, activities, dbas, district,
# circuit, size, latitude, longitude, county, fips_code


def fetch():
    from scrapling.fetchers import StealthyFetcher  # lazy: only this registry needs it

    captured = {}

    def grab(page):
        captured["csv"] = page.evaluate(
            f"async () => {{ const r = await fetch('{CSV_PATH}'); return await r.text(); }}"
        )

    StealthyFetcher.fetch(PAGE, page_action=grab)
    text = captured.get("csv", "")
    if not text or text.lstrip().startswith("<"):
        raise RuntimeError("FSIS fetch returned no CSV — bot wall changed; re-derive via the page")
    return list(csv.DictReader(io.StringIO(text)))


def to_companies(rows, activities_filter=None):
    """Registry rows -> pipeline company dicts. activities_filter: substring
    match on the `activities` field (e.g. 'Meat Processing')."""
    out = []
    for r in rows:
        if activities_filter and activities_filter.lower() not in (r.get("activities") or "").lower():
            continue
        out.append({
            "company": r.get("establishment_name", "").strip(),
            "address": f"{r.get('street','').strip()}, {r.get('city','')}, {r.get('state','')} {r.get('zip','')}",
            "company_phone": r.get("phone", "").strip(),
            "lat": r.get("latitude"), "lon": r.get("longitude"),
            "size": r.get("size", ""),
            "source": "fsis",
        })
    return out
