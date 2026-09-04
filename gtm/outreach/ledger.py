"""The outreach ledger: one CSV, append-only, the dedupe source of truth AND
the deliverable (data/<icp>/out/linkedin_outreach.csv).

Every attempt gets a row — sent, skipped (with reason), protected, error.
Skips are permanent: a profile with no Connect path stays that way, so
re-sourcing it would stall a refill loop forever. A `sent` row is never
deleted; if you need to re-contact someone, that is a decision, not a rerun.
"""
import csv
from datetime import date
from pathlib import Path

COLUMNS = ["date", "name", "company", "title", "tier", "status", "detail", "url"]
ATTEMPTED_STATUSES = ("skipped", "protected")   # plus anything starting with "sent"


class OutreachLedger:
    def __init__(self, path):
        self.path = Path(path)
        if not self.path.is_file():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w", newline="") as f:
                csv.writer(f).writerow(COLUMNS)

    def append(self, name, company, title, tier, status, detail, url, when=None):
        with open(self.path, "a", newline="") as f:
            csv.writer(f).writerow([(when or date.today()).isoformat(), name, company,
                                    title, tier, status, detail, url.rstrip("/")])

    def rows(self):
        with open(self.path, newline="") as f:
            return [r for r in csv.DictReader(f)]

    def attempted(self):
        """URLs we must not source again: sent (any variant), skipped, protected."""
        out = set()
        for r in self.rows():
            st = r.get("status", "")
            if st.startswith("sent") or st in ATTEMPTED_STATUSES:
                out.add(r["url"].rstrip("/"))
        return out

    def sent(self):
        return [r for r in self.rows() if r.get("status", "").startswith("sent")]
