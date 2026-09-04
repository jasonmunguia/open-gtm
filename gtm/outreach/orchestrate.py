"""The run: window → allowance → Phase A → (gate) → Phase B → report.

Exit codes: 0 done · 1 config/infra problem, nothing sent · 2 WRONG-RECIPIENT
abort (something WAS sent; read the ledger before running again).
"""
import json
import time

from ..paths import data
from . import config as cfg_mod
from . import pacing, source, vet
from .ledger import OutreachLedger


def paths(icp_name):
    d = data(icp_name)
    o = d / "outreach"
    o.mkdir(exist_ok=True)
    return {"ledger": d / "out" / "linkedin_outreach.csv",
            "queue": d / "derived" / "outreach_queue.jsonl",
            "target": o / "window_target.txt",
            "profile": o / "profile"}


def phase_a(page, sender, cfg, ledger, want, start_page, log, sleep=time.sleep):
    """Source → precheck → vet → queue. Returns (vetted, rejected, pool_size)."""
    attempted = ledger.attempted()
    pool = source.source(page, cfg, attempted, want, start_page=start_page, log=log, sleep=sleep)
    vetted, rejected, infra_fails = [], [], 0
    for c in pool:
        if len(vetted) >= want:
            break
        pre = vet.precheck(c, cfg, attempted)
        if pre == "protected":
            ledger.append(c["name"], "", c.get("headline", ""), c["tier"], "protected",
                          "on the no-touch list — never visited", c["url"])
            log(f"  PROTECT {c['name'][:22]:22} never visited")
            continue
        if pre:
            continue
        page.goto(c["url"], 7)
        reason = vet.vet(c, sender.positions(), cfg)
        if reason == "position API failed":
            infra_fails += 1
            if infra_fails >= 3:
                raise RuntimeError("positions API failed 3x — a session or rate-limit problem, not a "
                                   "candidate problem. Nothing sent. Run `outreach --check`: if it "
                                   "shows logged in, wait an hour and re-run; if not, log in there.")
        if reason:
            rejected.append({**c, "reason": reason})
            log(f"  REJECT  {c['name'][:22]:22} {reason[:50]}")
        else:
            vetted.append(c)
            log(f"  VET OK  {c['name'][:22]:22} {c['company'][:30]:30} | {c['title'][:28]}")
        sleep(2)
    return vetted, rejected, len(pool)


def read_queue(path):
    """The reviewed queue. Lines the human deleted are gone — that is the veto."""
    if not path.is_file():
        return []
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def phase_b(sender, queue, need, cfg, log):
    from .sender import WrongRecipient
    gaps = pacing.make_gaps(need, *cfg.gap_minutes)
    log(f"Phase B: target {need}, {len(queue)} vetted, est {sum(gaps):.0f} min")
    sends, gi, owe_gap = 0, 0, False
    attempted = sender.ledger.attempted()
    for cand in queue:
        if sends >= need:
            break
        if cand["url"].rstrip("/") in attempted:
            continue          # ledgered since the queue was written (a hand-added skip, or a prior run)
        if owe_gap and gi < len(gaps):
            log(f"WAIT {gaps[gi]} min")
            time.sleep(gaps[gi] * 60)
            gi += 1
            owe_gap = False
        try:
            ok = sender.attempt(cand)
        except WrongRecipient:
            raise
        except Exception as e:  # noqa: BLE001 — any other failure is a ledger row, not a crash
            sender.ledger.append(cand["name"], "", cand.get("headline", ""), cand.get("tier", ""),
                                 "error", f"exception {type(e).__name__}: {str(e)[:120]}", cand["url"])
            ok = False
        if ok:
            sends += 1
            owe_gap = True
    return sends


def run(icp_name, send=False, check=False, log=print):
    from . import cdp
    from .sender import Sender, WrongRecipient
    cfg = cfg_mod.load(icp_name)
    p = paths(icp_name)
    ledger = OutreachLedger(p["ledger"])
    log(f"outreach config: {cfg.path.name} — {len(cfg.searches)} searches, note {len(cfg.note)}/300, "
        f"{len(cfg.protected)} protected")

    b = cfg.browser
    browser = cdp.Browser.attach(b["cdp_url"]) if b.get("cdp_url") else \
        cdp.Browser.launch(p["profile"], port=int(b.get("port", cdp.DEFAULT_PORT)), binary=b.get("binary"), log=log)
    page, tid = browser.page(p["target"])
    try:
        cdp.ensure_logged_in(browser, page, tid, log=log)
        if b.get("offscreen", True):
            browser.place_offscreen(page, tid, b.get("window_bounds"))
        sender = Sender(page, cfg, ledger, log=log)

        sent7d = sender.count_last_7d()
        allowance = pacing.allowance(cfg.daily_target, cfg.weekly_cap, cfg.weekly_buffer, sent7d)
        log(f"last 7 days: {sent7d} invites on the account -> this run's allowance: {allowance}")
        if check:
            log("check mode — stopping here (nothing sourced, nothing sent)")
            return 0
        if allowance == 0:
            log("weekly headroom exhausted — no run today")
            return 0

        if not send:
            want = int(round(allowance * (1 + cfg.bench)))
            log(f"Phase A only (no --send): sourcing + vetting up to {want}")
            vetted, rejected, n = phase_a(page, sender, cfg, ledger, want, 1, log)
            with open(p["queue"], "w") as f:
                for c in vetted:
                    f.write(json.dumps(c) + "\n")
            log(f"\n{len(vetted)} vetted, {len(rejected)} rejected, {n} sourced -> {p['queue']}")
            log("Review the queue: delete any line you don't want contacted. "
                "Then re-run with --send — it sends to THIS file first, and only "
                "sources more if the queue runs short of the allowance.")
            return 0

        # --send: the reviewed queue first. The gate is only real if what the
        # human saw is what gets contacted; re-sourcing first would make the
        # review advisory (caught by the audit before the first release).
        sent_total, rnd, pg = 0, 0, 1
        queued = read_queue(p["queue"])
        if queued:
            log(f"--- reviewed queue: {len(queued)} candidates ---")
            got = phase_b(sender, queued, allowance, cfg, log)
            sent_total += got
            p["queue"].unlink()          # consumed; a stale queue must never be re-sent
            log(f"queue: +{got} sent (total {sent_total}/{allowance})")
        else:
            log("no reviewed queue on disk — sourcing fresh (run without --send first to review)")
        while sent_total < allowance and rnd < cfg.max_rounds:
            rnd += 1
            need = allowance - sent_total
            log(f"--- round {rnd}: need {need} more (page {pg}) ---")
            want = int(round(need * (1 + cfg.bench)))
            vetted, _rej, _n = phase_a(page, sender, cfg, ledger, want, pg, log)
            if not vetted:
                pg += 2
                if pg > 9:
                    break
                continue
            got = phase_b(sender, vetted, need, cfg, log)
            sent_total += got
            log(f"round {rnd}: +{got} sent (total {sent_total}/{allowance})")
            if got < need:
                pg += 1
        if sent_total < allowance:
            log(f"SHORT: {sent_total}/{allowance} after {rnd} rounds — pool exhausted; widen `searches`")
        else:
            log(f"TARGET MET: {sent_total}/{allowance}")
        log(f"ledger: {p['ledger']}")
        return 0
    except WrongRecipient as e:
        log(f"ABORT: {e}")
        return 2
    except (cdp.NotLoggedIn, cdp.WindowGone, RuntimeError, ConnectionError) as e:
        log(f"ABORT: {e}")
        return 1
    finally:
        page.close()
