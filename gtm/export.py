"""Deliverables: call-lane and visit-lane CSVs.

Phone-first on purpose. Inboxes are saturated and filtered; the dial is the
undersupplied channel. Every column exists to make the CALL easier: the
number to dial (post-enrichment), the opener angle, the evidence line that
lets the caller sound informed in the first ten seconds.
"""
import csv

COLUMNS = [
    "name", "title", "company", "phone", "mobile", "linkedin",
    "lane", "icp", "angle", "evidence", "address",
]


def write_csv(rows, path):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return len(rows)


def export(leads, out_dir):
    call = [r for r in leads if r.get("lane") != "visit"]
    visit = [r for r in leads if r.get("lane") == "visit"]
    n_call = write_csv(call, out_dir / "call_leads.csv")
    n_visit = write_csv(visit, out_dir / "visit_leads.csv")
    return n_call, n_visit
