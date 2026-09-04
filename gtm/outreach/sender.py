"""Phase B: one profile → one API-verified send (or a ledgered skip).

The sequence per candidate, each step a scar:
  wait for render → employment gate (API) → find THIS person's Connect
  (top-card scoped, full-name match) → dialog opens in a shadow root →
  Add a note → fill via native setter → counter must read len/300 →
  Send by coordinates → verify against the sent-invitations API.
A wrong-recipient result withdraws the stray invite and ABORTS the run.
"""
import time

from . import js, vet, verify


class WrongRecipient(RuntimeError):
    """Our note landed on someone other than the intended profile."""


class Sender:
    def __init__(self, page, cfg, ledger, log=print, sleep=time.sleep):
        self.page, self.cfg, self.ledger, self.log, self.sleep = page, cfg, ledger, log, sleep
        self.note = cfg.note
        self._role_js = js.load("current_role")
        self._invs_js = js.load("sent_invitations", count=10)
        self._invs_7d_js = js.load("sent_invitations", count=100)
        self._note_js = js.load("note_fill", note=self.note)
        self._dialog_js = js.load("dialog_state")
        self._ready_js = js.load("ready")
        self._esc_js = js.load("escape")

    # ---- API reads ---------------------------------------------------------
    def sent_invitations(self, js_src=None):
        arr = self.page.jev(js_src or self._invs_js, await_promise=True, timeout=45)
        if not isinstance(arr, list):
            return []
        arr.sort(key=lambda x: -(x.get("sent") or 0))
        return arr

    def count_last_7d(self):
        now, wk = time.time() * 1000, 7 * 86400 * 1000
        return sum(1 for x in self.sent_invitations(self._invs_7d_js)
                   if x.get("sent") and now - x["sent"] < wk)

    def positions(self):
        return self.page.jev(self._role_js, await_promise=True, timeout=60)

    # ---- page mechanics ----------------------------------------------------
    def _log(self, cand, status, detail, company=""):
        self.ledger.append(cand["name"], company or cand.get("company", ""),
                           cand.get("title") or cand.get("headline", ""), cand.get("tier", ""),
                           status, detail, cand["url"])
        self.log(f"LOG {status}: {cand['name']} — {detail}")

    def wait_ready(self, tries=12):
        for _ in range(tries):
            r = self.page.jev(self._ready_js)
            if r.get("main") and r.get("acts"):
                return True
            self.sleep(4)
        return bool(self.page.jev(self._ready_js).get("main"))

    def _esc(self):
        self.page.ev(self._esc_js)

    def withdraw(self, slug):
        """Emergency: withdraw the invitation to `slug`. True if the API no
        longer lists it afterwards."""
        self.page.goto(f"https://www.linkedin.com/in/{slug}/", 7)
        self.page.jev(js.load("withdraw_open"))
        self.sleep(2)
        self.page.jev(js.load("withdraw_confirm"))
        self.sleep(3)
        return all((x.get("slug") or "").lower() != slug for x in self.sent_invitations())

    # ---- the attempt -------------------------------------------------------
    def attempt(self, cand):
        """Returns True iff a send was API-verified. Raises WrongRecipient."""
        url = cand["url"]
        self.page.goto(url, 6)
        if not self.wait_ready():
            self.page.goto(url, 6)  # one reload, then wait again
            if not self.wait_ready():
                self._log(cand, "error", "page never rendered (retry failed)")
                return False

        reason = vet.vet(cand, self.positions(), self.cfg)
        if reason:
            self._log(cand, "skipped", reason)
            return False

        toks = js.name_tokens(cand["name"])
        st = self.page.jev(js.load("find_connect", tokens=toks))
        state = st.get("state")
        if state == "pending":
            self._log(cand, "skipped", "already pending"); return False
        if state == "wrong_profile":
            self._log(cand, "skipped", f"profile heading '{st.get('h1')}' does not match candidate name"); return False
        if state == "not_rendered":
            self._log(cand, "error", "main missing after ready-check"); return False
        if state == "no_connect_no_more":
            self._log(cand, "skipped", "no connect path"); return False
        if state == "opened_more":
            self.sleep(1.5)
            m = self.page.jev(js.load("menu_connect", tokens=toks))
            if m.get("state") != "clicked_menu":
                self._esc(); self._log(cand, "skipped", "no Connect via More"); return False
        elif state != "clicked_direct":
            self._log(cand, "skipped", f"unexpected: {st}"); return False

        self.sleep(3)
        d = self.page.jev(self._dialog_js)
        if not d.get("open"):
            self.sleep(3); d = self.page.jev(self._dialog_js)
        if not d.get("open"):
            self._log(cand, "skipped", "invite dialog never opened"); return False
        if d.get("add"):
            self.page.click(d["add"]["x"], d["add"]["y"]); self.sleep(2)

        filled = self.page.jev(self._note_js)
        if filled.get("taLen") != len(self.note):
            self._esc(); self._esc()
            self._log(cand, "skipped", f"note fill failed: {filled}"); return False
        self.sleep(1.5)
        d2 = self.page.jev(self._dialog_js)
        want_counter = f"{len(self.note)}/300"
        if d2.get("counter") != want_counter or not d2.get("send"):
            self._esc(); self._esc()
            self._log(cand, "skipped", f"counter {d2.get('counter')} != {want_counter} — refusing to send"); return False

        before = self.sent_invitations()
        before_t = before[0]["sent"] if before else 0
        self.page.click(d2["send"]["x"], d2["send"]["y"])
        self.sleep(4)

        outcome, inv = verify.classify_send(self.sent_invitations(), verify.slug_of(url), self.note, before_t)
        if outcome == verify.SENT:
            self._log(cand, "sent", "recipient+note API-verified", cand.get("company", "")); return True
        if outcome == verify.SENT_NOTE_MISMATCH:
            self._log(cand, "sent-note-mismatch",
                      f"invite went out but note is {len(inv.get('msg', ''))} chars vs {len(self.note)} — "
                      f"counts as a send, investigate", cand.get("company", ""))
            return True   # it DID go out; consume a slot, never resend
        if outcome == verify.WRONG_RECIPIENT:
            got_slug = (inv.get("slug") or "").lower()
            stray = {"name": inv.get("to", "?"), "url": f"https://www.linkedin.com/in/{got_slug}/" if got_slug else url,
                     "tier": cand.get("tier", "")}
            self._log(stray, "error", f"WRONG RECIPIENT: intended {cand['name']} ({verify.slug_of(url)}), "
                                      f"our note went to {got_slug or 'UNRESOLVED'}")
            if got_slug:
                ok = self.withdraw(got_slug)
                self._log(stray, "withdrawn" if ok else "error",
                          f"emergency withdrawal {'succeeded' if ok else 'FAILED — withdraw manually NOW'}")
            raise WrongRecipient(f"intended {verify.slug_of(url)}, note landed on {got_slug or 'unknown'}. "
                                 f"Check linkedin.com/mynetwork/invitation-manager/sent/ before running again.")
        self._log(cand, "error", f"no confirmation from the API — not counted as a send")
        return False
