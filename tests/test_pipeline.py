"""Offline tests for the deterministic spine. Every test guards a specific
scar from the original runs — if one fails, a paid-for lesson has been
unlearned. All tests here run against the SHIPPED example ICP; ICP-specific
tests for private configs live in test_private_icps.py (not exported).
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gtm import harvest, hygiene, join
from gtm.icp import REPO
from gtm.icp import load as load_icp
from gtm.ledger import Ledger
from gtm.normalize import normc, person_key


class TestNormalize(unittest.TestCase):
    def test_company_suffix_collision(self):
        # The dedup key must collide across suffix/punctuation variants.
        self.assertEqual(normc("Godshall's Quality Meats, Inc."), normc("GODSHALLS QUALITY MEATS LLC"))

    def test_person_key(self):
        self.assertEqual(person_key("Maria", "Acme Corp."), person_key("maria", "ACME"))


class TestICPLoading(unittest.TestCase):
    def test_every_shipped_icp_loads(self):
        for d in sorted((REPO / "icps").iterdir()):
            if (d / "icp.yaml").is_file():
                icp = load_icp(d.name)
                self.assertTrue(icp.segments, f"{d.name}: no segments")

    def test_generated_regex_matches_listed_titles(self):
        # THE 641-lead scar: every phrasing in the ICP list must match the
        # generated regex — the regex is compiled from the list, never edited.
        icp = load_icp("example")
        for t in ("Service Coordinator", "Dispatch Manager", "Branch Manager",
                  "Director of Operations"):
            self.assertTrue(icp.title_ok(t), f"generated regex missed: {t}")

    def test_bad_beats_ops(self):
        # A title matching both lists is a seller wearing an ops word.
        icp = load_icp("example")
        self.assertFalse(icp.title_ok("VP Sales & Service Operations"))
        self.assertFalse(icp.title_ok("President / General Manager"))


class TestHygiene(unittest.TestCase):
    def test_pattern_and_named_drops(self):
        icp = load_icp("example")
        cos = [{"company": "Frostline Beverage Distribution"},  # named-only
               {"company": "Speedy Residential Heating"},       # pattern
               {"company": "Bay Mechanical Services Inc"}]      # keep
        kept, dropped = hygiene.clean(cos, icp)
        self.assertEqual([c["company"] for c in kept], ["Bay Mechanical Services Inc"])
        self.assertEqual(len(dropped), 2)

    def test_dropped_rows_are_recoverable(self):
        icp = load_icp("example")
        with tempfile.TemporaryDirectory() as td:
            side = Path(td) / "dropped.jsonl"
            hygiene.clean([{"company": "Sunset Residential HVAC"}], icp, side)
            self.assertEqual(json.loads(side.read_text())["company"], "Sunset Residential HVAC")


class TestHarvestInvariants(unittest.TestCase):
    def test_ok_false_on_block(self):
        # Engine failure must NOT read as "searched, found nothing".
        _hits, ok = harvest.classify(403, "<html>Access Denied</html>", [])
        self.assertFalse(ok)

    def test_captcha_pass_false_positive_guard(self):
        # 'captcha' marker + results present = healthy page, not a block.
        body = '<a href="https://www.linkedin.com/in/jane-doe-123">Jane Doe</a> captcha_pass'
        found = harvest.extract(body)
        hits, ok = harvest.classify(200, body, found)
        self.assertTrue(ok)
        self.assertEqual(len(hits), 1)

    def test_no_results_plus_marker_is_block(self):
        _hits, ok = harvest.classify(200, "please solve this captcha", [])
        self.assertFalse(ok)

    def test_blocked_company_stays_pending(self):
        with tempfile.TemporaryDirectory() as td:
            led = Ledger(Path(td) / "ledger.json")
            eng = harvest.Engine("test", "https://x/?q=")
            out = Path(td) / "hits.jsonl"
            harvest.PACING_S = (0, 0)  # tests must not sleep
            n = harvest.harvest(
                [{"company": "Blocked Co"}], [eng],
                fetch=lambda url: (403, "Access Denied"),
                ledger=led, out_path=out, query_fn=lambda c: c["company"])
            self.assertEqual(n, 0)
            self.assertFalse(led.is_done("harvest", "Blocked Co"))  # THE invariant

    def test_engine_cooloff_after_streak(self):
        eng = harvest.Engine("test", "https://x/?q=")
        for _ in range(harvest.BLOCK_STREAK_LIMIT):
            eng.search("q", lambda url: (403, ""))
        self.assertFalse(eng.available())


class TestJoin(unittest.TestCase):
    def _icp(self):
        return load_icp("example")

    def test_person_level_dedup(self):
        tmap = {person_key("Maria", "Acme"): [("Service Manager", "call", "commercial-hvac")]}
        hits = [{"url": "https://www.linkedin.com/in/maria-x", "anchor": "Maria Lopez", "company": "Acme"},
                {"url": "https://www.linkedin.com/in/maria-x2", "anchor": "Maria Lopez", "company": "Acme Inc."}]
        leads = join.join(hits, tmap, self._icp(), set())
        self.assertEqual(len(leads), 1)  # one row per person, ever

    def test_visit_never_inherited(self):
        # The 96-row-audit scar: candidate says visit, but the company was not
        # curated local -> lane must demote to call.
        tmap = {person_key("Joe", "FarCo"): [("Service Manager", "visit", "commercial-hvac")]}
        hits = [{"url": "https://www.linkedin.com/in/joe-y", "anchor": "Joe Smith", "company": "FarCo"}]
        leads = join.join(hits, tmap, self._icp(), curated_visit_companies=set())
        self.assertEqual(leads[0]["lane"], "call")
        # And curated companies DO keep visit:
        leads2 = join.join(hits, tmap, self._icp(), {normc("FarCo")})
        self.assertEqual(leads2[0]["lane"], "visit")

    def test_slug_only_identity_needs_candidate_match(self):
        # Slug parse-error scar: URL-derived names with no candidate match are dropped.
        hits = [{"url": "https://www.linkedin.com/in/bob-jones-99", "anchor": "http://x", "company": "NoMatch Co"}]
        self.assertEqual(join.join(hits, {}, self._icp(), set()), [])

    def test_title_gate_at_join_time(self):
        tmap = {person_key("Ann", "Acme"): [("Director of Sales", "call", "commercial-hvac")]}
        hits = [{"url": "https://www.linkedin.com/in/ann-z", "anchor": "Ann Chen", "company": "Acme"}]
        self.assertEqual(join.join(hits, tmap, self._icp(), set()), [])

    def test_lead_row_has_name(self):
        # Smoke-test scar: join once emitted `first` while the CSV wanted `name`.
        tmap = {person_key("Dana", "Bay Mechanical"): [("Service Manager", "call", "commercial-hvac")]}
        hits = [{"url": "https://www.linkedin.com/in/dana-r", "anchor": "Dana Reyes", "company": "Bay Mechanical"}]
        leads = join.join(hits, tmap, self._icp(), set())
        self.assertEqual(leads[0]["name"], "Dana Reyes")


class TestEnrichGate(unittest.TestCase):
    def test_refuses_without_exact_confirm(self):
        from gtm import enrich

        class FakeProvider:
            def estimate(self, n): return n
            def enrich(self, rows): return rows

        rows = [{"first": "a"}, {"first": "b"}]
        with self.assertRaises(enrich.SpendNotConfirmed):
            enrich.request_enrichment(rows, FakeProvider())
        with self.assertRaises(enrich.SpendNotConfirmed):
            enrich.request_enrichment(rows, FakeProvider(), confirm="yes")
        with self.assertRaises(enrich.SpendNotConfirmed):
            enrich.request_enrichment(rows, FakeProvider(), confirm="spend 3")  # wrong N
        out = enrich.request_enrichment(rows, FakeProvider(), confirm="spend 2")
        self.assertEqual(len(out), 2)

    def test_phone_first_ranking(self):
        from gtm.enrich import rank_contactability
        rows = [{"name": "email-only"}, {"name": "mobile", "mobile": "1"},
                {"name": "switchboard", "company_phone": "1"}, {"name": "direct", "phone": "1"}]
        ranked = sorted(rows, key=rank_contactability)
        self.assertEqual([r["name"] for r in ranked],
                         ["mobile", "direct", "switchboard", "email-only"])


class TestLedger(unittest.TestCase):
    def test_reset_stage_is_scoped(self):
        with tempfile.TemporaryDirectory() as td:
            led = Ledger(Path(td) / "l.json")
            led.mark_done("harvest", "A")
            led.mark_done("registry", "B")
            led.reset_stage("harvest")
            self.assertFalse(led.is_done("harvest", "A"))
            self.assertTrue(led.is_done("registry", "B"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
