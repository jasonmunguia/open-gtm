"""Offline tests for the outreach stage. Every test guards a scar from the
original runs; a browser is never needed — the page is faked, and every gate
is a pure function. Names and companies here are fictional.
"""
import csv
import io
import json
import random
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gtm.outreach import config as ocfg
from gtm.outreach import js, orchestrate, pacing, source, vet, verify
from gtm.outreach.ledger import OutreachLedger
from gtm.outreach.sender import Sender, WrongRecipient

EXAMPLE = Path(__file__).resolve().parent.parent / "icps" / "example" / "outreach.yaml"


def cfg_with(**over):
    raw = yaml.safe_load(EXAMPLE.read_text())
    raw.update(over)
    return ocfg.OutreachConfig(raw, EXAMPLE)


class TestConfig(unittest.TestCase):
    def test_example_loads(self):
        c = ocfg.load("example")
        self.assertLessEqual(len(c.note), ocfg.NOTE_MAX)
        self.assertGreaterEqual(len(c.searches), 3)

    def test_note_over_300_refused(self):
        # The runner refuses truncated notes; the config refuses them earlier.
        with self.assertRaises(ValueError):
            cfg_with(note="x" * 301)

    def test_note_required(self):
        with self.assertRaises(ValueError):
            cfg_with(note="   ")

    def test_searches_required(self):
        with self.assertRaises(ValueError):
            cfg_with(searches=[])

    def test_gap_and_volume_sanity(self):
        with self.assertRaises(ValueError):
            cfg_with(gap_minutes=[4, 1])
        with self.assertRaises(ValueError):
            cfg_with(weekly_cap=5, weekly_buffer=10)

    def test_protected_matches_url_slug_and_name(self):
        c = cfg_with(protected=["https://www.linkedin.com/in/vendor-contact-1/",
                                "Pat Vendor"])
        self.assertTrue(c.is_protected("https://www.linkedin.com/in/vendor-contact-1", "Someone Else"))
        self.assertTrue(c.is_protected("https://www.linkedin.com/in/other", "pat vendor"))
        self.assertFalse(c.is_protected("https://www.linkedin.com/in/other", "Other Person"))


class TestPacing(unittest.TestCase):
    def test_allowance_from_account_load(self):
        # cap 100, buffer 10, 75 already sent this week -> 15, not 20
        self.assertEqual(pacing.allowance(20, 100, 10, 75), 15)
        self.assertEqual(pacing.allowance(20, 100, 10, 0), 20)
        self.assertEqual(pacing.allowance(20, 100, 10, 95), 0)

    def test_gaps_count_and_bounds(self):
        rng = random.Random(1)
        gaps = pacing.make_gaps(20, 1, 4, rng)
        self.assertEqual(len(gaps), 19)          # none before the first send
        self.assertTrue(all(1 <= g <= 4 for g in gaps))
        self.assertEqual(pacing.make_gaps(1, 1, 4, rng), [])


class TestLedger(unittest.TestCase):
    def test_attempted_covers_sent_skipped_protected_not_error(self):
        with tempfile.TemporaryDirectory() as d:
            led = OutreachLedger(Path(d) / "l.csv")
            led.append("A One", "Co", "T", "1", "sent", "ok", "https://www.linkedin.com/in/a-one/")
            led.append("B Two", "Co", "T", "1", "skipped", "no connect path", "https://www.linkedin.com/in/b-two")
            led.append("C Three", "", "", "1", "protected", "", "https://www.linkedin.com/in/c-three")
            led.append("D Four", "Co", "T", "1", "error", "boom", "https://www.linkedin.com/in/d-four")
            att = led.attempted()
            self.assertEqual(att, {"https://www.linkedin.com/in/a-one", "https://www.linkedin.com/in/b-two",
                                   "https://www.linkedin.com/in/c-three"})
            self.assertEqual([r["name"] for r in led.sent()], ["A One"])


class TestVet(unittest.TestCase):
    def setUp(self):
        self.cfg = cfg_with(deny_employers=["staffing", "megacorp"], deny_titles=["recruiter", "technician"],
                            protected=["Pat Vendor"])

    def test_precheck_dedupe_and_protected(self):
        self.assertEqual(vet.precheck({"url": "https://www.linkedin.com/in/x/", "name": "X Y"}, self.cfg,
                                      {"https://www.linkedin.com/in/x"}), "already attempted")
        self.assertEqual(vet.precheck({"url": "https://www.linkedin.com/in/pv", "name": "Pat Vendor"}, self.cfg, set()),
                         "protected")
        self.assertIsNone(vet.precheck({"url": "https://www.linkedin.com/in/ok", "name": "O K"}, self.cfg, set()))

    def test_headline_never_consulted(self):
        # Headline says "Ops Manager at DreamCo"; API says no current position.
        c = {"url": "u", "name": "J Seeker", "headline": "Ops Manager at DreamCo"}
        self.assertIn("no current position", vet.vet(c, [{"co": "DreamCo", "t": "Ops Manager", "end": "ended"}], self.cfg))

    def test_api_failure_is_infra_not_verdict(self):
        self.assertEqual(vet.vet({"url": "u", "name": "A B"}, None, self.cfg), "position API failed")
        self.assertEqual(vet.vet({"url": "u", "name": "A B"}, {"err": "x"}, self.cfg), "position API failed")

    def test_deny_lists_on_api_values(self):
        c = {"url": "u", "name": "A B"}
        self.assertIn("excluded employer", vet.vet(c, [{"co": "MegaCorp Inc", "t": "Ops Mgr", "end": "current"}], self.cfg))
        self.assertIn("excluded title", vet.vet(c, [{"co": "Fine Co", "t": "Senior Technician", "end": "current"}], self.cfg))

    def test_ok_sets_company_and_title(self):
        c = {"url": "u", "name": "A B"}
        self.assertIsNone(vet.vet(c, [{"co": "Fine Co", "t": "Service Manager", "end": "current"}], self.cfg))
        self.assertEqual((c["company"], c["title"]), ("Fine Co", "Service Manager"))


class TestVerify(unittest.TestCase):
    NOTE = "hello there"

    def test_sent_requires_slug_and_verbatim_note(self):
        invs = [{"slug": "target-1", "msg": "hello there", "sent": 10}]
        self.assertEqual(verify.classify_send(invs, "target-1", self.NOTE, 5)[0], verify.SENT)
        invs = [{"slug": "target-1", "msg": "hello", "sent": 10}]
        self.assertEqual(verify.classify_send(invs, "target-1", self.NOTE, 5)[0], verify.SENT_NOTE_MISMATCH)

    def test_wrong_recipient_detected(self):
        # Our note landed on a stranger AFTER our click -> abort condition.
        invs = [{"slug": "stranger", "msg": "hello there", "sent": 10}]
        out, inv = verify.classify_send(invs, "target-1", self.NOTE, 5)
        self.assertEqual(out, verify.WRONG_RECIPIENT)
        self.assertEqual(inv["slug"], "stranger")

    def test_manual_invite_mid_run_is_left_alone(self):
        # A hand-sent invite (no note) newer than our click is NOT ours.
        invs = [{"slug": "friend", "msg": "", "sent": 10}]
        self.assertEqual(verify.classify_send(invs, "target-1", self.NOTE, 5)[0], verify.UNCONFIRMED)

    def test_old_stray_with_our_note_is_not_ours(self):
        invs = [{"slug": "someone", "msg": "hello there", "sent": 3}]   # older than before_t
        self.assertEqual(verify.classify_send(invs, "target-1", self.NOTE, 5)[0], verify.UNCONFIRMED)


class TestSource(unittest.TestCase):
    def test_search_url_carries_geo_and_page(self):
        u = source.search_url("service manager HVAC", "103644278", 3)
        self.assertIn("keywords=service%20manager%20HVAC", u)
        self.assertIn("geoUrn=%5B%22103644278%22%5D", u)
        self.assertTrue(u.endswith("&page=3"))
        self.assertNotIn("page=", source.search_url("x", "1", 1))

    def test_parse_cards_drops_unusable(self):
        raw = json.dumps([
            {"url": "https://www.linkedin.com/in/a-b/", "lines": ["Ada Bell • 2nd", "Service Manager", "Acme"]},
            {"url": "https://www.linkedin.com/in/c/", "lines": ["Cher", "Ops"]},              # one token
            {"url": "https://www.linkedin.com/in/d-e/", "lines": ["Dan Ell", "3 mutual connections"]},
            {"url": "https://www.linkedin.com/in/f/", "lines": []},
        ])
        out = source.parse_cards(raw, "1", "q")
        self.assertEqual([c["name"] for c in out], ["Ada Bell"])
        self.assertEqual(out[0]["url"], "https://www.linkedin.com/in/a-b")

    def test_round_robin_interleaves_tiers(self):
        order = source.round_robin([("1", "a"), ("1", "b"), ("2", "c"), ("3", "d")])
        self.assertEqual(order, [("1", "a"), ("2", "c"), ("3", "d"), ("1", "b")])


class TestJS(unittest.TestCase):
    def test_placeholders_are_json_safe(self):
        src = js.load("find_connect", tokens=['O"Brien', "D'Arcy"])
        self.assertIn(json.dumps(['O"Brien', "D'Arcy"]), src)
        self.assertNotIn("__TOKENS__", src)
        note = js.load("note_fill", note='say "hi"')
        self.assertIn('"say \\"hi\\""', note)

    def test_missing_placeholder_is_an_error(self):
        with self.assertRaises(KeyError):
            js.load("ready", tokens=["a"])

    def test_name_tokens_never_single(self):
        self.assertEqual(js.name_tokens("J. Ada Bell"), ["Ada", "Bell"])
        with self.assertRaises(ValueError):
            js.name_tokens("Cher")


class FakePage:
    """Drives Sender.attempt() offline. Keyed on distinctive substrings of the
    scripts; `script` maps step -> scripted responses (lists pop in order)."""

    def __init__(self, script):
        self.s = script
        self.visited, self.clicks = [], []

    def goto(self, url, wait=0):
        self.visited.append(url)

    def click(self, x, y):
        self.clicks.append((x, y))

    def ev(self, expr, await_promise=False, timeout=0):
        return 1

    def _pop(self, key):
        v = self.s[key]
        return v.pop(0) if isinstance(v, list) else v

    def jev(self, expr, await_promise=False, timeout=0):
        if "FullProfileWithEntities" in expr:
            return self.s["positions"]          # one response, returned as-is
        if "main [aria-label]" in expr or "/^withdraw$/i" in expr:
            return {"c": 1, "w": 1}          # withdraw_open / withdraw_confirm
        if "sentInvitationViewsV2" in expr:
            return self._pop("invitations")
        if "acts:" in expr:
            return {"main": True, "acts": True}
        if "main section h1" in expr:
            return self._pop("connect")
        if "includes('Add a note')" in expr:
            return self._pop("dialog")
        if "const NOTE =" in expr:
            return self._pop("fill")
        raise AssertionError("unscripted js: " + expr[:60])

    def close(self):
        pass


def _sender(page, **over):
    d = tempfile.mkdtemp()
    cfg = cfg_with(**over)
    led = OutreachLedger(Path(d) / "l.csv")
    return Sender(page, cfg, led, log=lambda *_: None, sleep=lambda *_: None), led


class TestSenderOffline(unittest.TestCase):
    CAND = {"name": "Ada Bell", "url": "https://www.linkedin.com/in/ada-bell", "tier": "1", "headline": "h"}

    def test_happy_path_is_api_verified(self):
        cfg = cfg_with()
        n = len(cfg.note)
        page = FakePage({
            "positions": [{"co": "Fine Co", "t": "Service Manager", "end": "current"}],
            "connect": {"state": "clicked_direct"},
            "dialog": [{"open": True, "add": {"x": 1, "y": 2}, "send": None, "counter": "0/300"},
                       {"open": True, "add": None, "send": {"x": 3, "y": 4}, "counter": f"{n}/300"}],
            "fill": {"len": n, "taLen": n},
            "invitations": [[],                                                   # before click
                            [{"slug": "ada-bell", "msg": cfg.note, "sent": 99}]],  # after click
        })
        s, led = _sender(page)
        self.assertTrue(s.attempt(dict(self.CAND)))
        rows = led.rows()
        self.assertEqual(rows[-1]["status"], "sent")
        self.assertEqual(rows[-1]["company"], "Fine Co")
        self.assertEqual(page.clicks, [(1, 2), (3, 4)])   # Add a note, then Send

    def test_counter_mismatch_never_clicks_send(self):
        cfg = cfg_with()
        n = len(cfg.note)
        page = FakePage({
            "positions": [{"co": "Fine Co", "t": "Service Manager", "end": "current"}],
            "connect": {"state": "clicked_direct"},
            "dialog": [{"open": True, "add": None, "send": {"x": 3, "y": 4}, "counter": "0/300"},
                       {"open": True, "add": None, "send": {"x": 3, "y": 4}, "counter": f"{n-1}/300"}],
            "fill": {"len": n, "taLen": n},
            "invitations": [],
        })
        s, led = _sender(page)
        self.assertFalse(s.attempt(dict(self.CAND)))
        self.assertEqual(page.clicks, [])                       # Send was never clicked
        self.assertIn("refusing to send", led.rows()[-1]["detail"])

    def test_employment_gate_skips_before_any_click(self):
        page = FakePage({"positions": [{"co": "X", "t": "Y", "end": "ended"}]})
        s, led = _sender(page)
        self.assertFalse(s.attempt(dict(self.CAND)))
        self.assertEqual(led.rows()[-1]["status"], "skipped")
        self.assertEqual(page.clicks, [])

    def test_wrong_recipient_withdraws_and_aborts(self):
        cfg = cfg_with()
        n = len(cfg.note)
        page = FakePage({
            "positions": [{"co": "Fine Co", "t": "Service Manager", "end": "current"}],
            "connect": {"state": "clicked_direct"},
            "dialog": [{"open": True, "add": None, "send": {"x": 3, "y": 4}, "counter": f"{n}/300"},
                       {"open": True, "add": None, "send": {"x": 3, "y": 4}, "counter": f"{n}/300"}],
            "fill": {"len": n, "taLen": n},
            "invitations": [[{"slug": "older", "msg": "", "sent": 1}],                  # before
                            [{"slug": "a-stranger", "msg": cfg.note, "sent": 50}],     # after: stray!
                            []],                                                        # post-withdraw
        })
        s, led = _sender(page)
        with self.assertRaises(WrongRecipient):
            s.attempt(dict(self.CAND))
        statuses = [r["status"] for r in led.rows()]
        self.assertIn("error", statuses)
        self.assertIn("withdrawn", statuses)
        self.assertIn("https://www.linkedin.com/in/a-stranger/", page.visited)


class TestPhaseA(unittest.TestCase):
    def test_protected_profile_is_never_visited(self):
        cfg = cfg_with(protected=["Pat Vendor"])
        cards = json.dumps([
            {"url": "https://www.linkedin.com/in/pat-vendor/", "lines": ["Pat Vendor", "Owner", "VendorCo"]},
            {"url": "https://www.linkedin.com/in/ada-bell/", "lines": ["Ada Bell", "Service Manager", "Acme"]},
        ])

        class Page:
            visited = []
            def goto(self, url, wait=0): self.visited.append(url)
            def ev(self, expr, **k): return cards
            def jev(self, expr, **k): return {}

        class S:
            def positions(self): return [{"co": "Acme", "t": "Service Manager", "end": "current"}]

        d = tempfile.mkdtemp()
        led = OutreachLedger(Path(d) / "l.csv")
        pg = Page()
        vetted, rejected, n = orchestrate.phase_a(pg, S(), cfg, led, want=1, start_page=1,
                                                  log=lambda *_: None, sleep=lambda *_: None)
        self.assertEqual([c["name"] for c in vetted], ["Ada Bell"])
        self.assertNotIn("https://www.linkedin.com/in/pat-vendor", pg.visited)
        self.assertEqual([r["status"] for r in led.rows()], ["protected"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
