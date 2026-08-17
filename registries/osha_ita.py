"""OSHA ITA (Injury Tracking Application) establishment data.

Every establishment that files a 300A: name, street address, NAICS code, and
annual_average_employees — i.e., a free, authoritative company universe with
a built-in size floor for any manufacturing NAICS. Filter NAICS + employee
floor and you have your universe before touching a paid provider.

Access (verified 2026-08-16): plain HTTPS, no key, no bot wall.
Header confirmed: id, establishment_name, establishment_id, ein, company_name,
street_address, city, state, zip_code, naics_code, naics_year,
industry_description, establishment_type, size, annual_average_employees, ...

Index of yearly files: https://www.osha.gov/Establishment-Specific-Injury-and-Illness-Data
"""
import csv
import io
import urllib.request

from . import _net

# One in-process download per URL. The 2025 file is ~84MB; an ICP with three
# NAICS-backed segments would otherwise pull it three times in one run.
_CACHE = {}

# Newest full-coverage file at verification time. Check the index page yearly;
# OSHA posts current-year partials (suffix `_through_<date>`) and prior-year zips.
DEFAULT_URL = "https://www.osha.gov/sites/default/files/ITA_300A_Summary_Data_2025_through_03-15-2026_v2.csv"


def fetch(url=DEFAULT_URL, timeout=300):
    if url not in _CACHE:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (gtm-system registry pull)"})
        with _net.urlopen(req, timeout=timeout) as r:
            _CACHE[url] = r.read().decode("utf-8", "ignore")
    return csv.DictReader(io.StringIO(_CACHE[url]))


def to_companies(rows, naics_prefixes, min_employees=0, states=None):
    """Filter by NAICS prefix list + employee floor (+ optional state list).
    Dedup on establishment name happens downstream (normc) — one company files
    many establishments, and you usually WANT the per-plant rows for the visit
    lane."""
    out = []
    for r in rows:
        naics = (r.get("naics_code") or "").strip()
        if naics_prefixes and not any(naics.startswith(p) for p in naics_prefixes):
            continue
        try:
            emp = int(float(r.get("annual_average_employees") or 0))
        except ValueError:
            emp = 0
        if emp < min_employees:
            continue
        if states and (r.get("state") or "").strip().upper() not in states:
            continue
        out.append({
            "company": (r.get("establishment_name") or r.get("company_name") or "").strip(),
            "address": f"{r.get('street_address','').strip()}, {r.get('city','')}, {r.get('state','')} {r.get('zip_code','')}",
            "naics": naics,
            "employees": emp,
            "source": "osha_ita",
        })
    return out
