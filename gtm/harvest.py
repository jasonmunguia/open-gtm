"""SearXNG harvest — find LinkedIn profiles for (title, company) pairs.

This module encodes the hardest-won operational knowledge in the repo. The
constants are not tunables; each carries the incident that set it.

Run it as a long-lived process (it paces itself); parallelism is one worker
PER INSTANCE, never many workers per instance.
"""
import html as H
import json
import random
import re
import time
import urllib.parse

# 7–12s between requests, per instance. This pacing is why the original runs
# were never banned across ~49k URLs harvested. Public SearXNG instances are
# VOLUNTEER-RUN infrastructure: the pacing is an ethical floor, not a knob.
# If you need more throughput, add instances (one worker each) or self-host —
# never shorten the delay.  [recovered: PIPELINE_V2_SPEC §3 + run logs]
PACING_S = (7, 12)

# Consecutive blocked/errored responses before an instance is rested. A tripped
# instance stays hot for hours; hammering it converts a cooloff into a ban.
BLOCK_STREAK_LIMIT = 3
COOLOFF_S = 1800

_LINK = re.compile(
    r'<a[^>]+href="(https://[a-z]{0,3}\.?linkedin\.com/in/[^"?#]+)[^"]*"[^>]*>(.*?)</a>', re.DOTALL
)
_BLOCK_MARKERS = ("captcha", "unusual traffic", "are you a robot")


def extract(body):
    """Pull linkedin.com/in/ links + anchor text + trailing context from a
    results page. The 700-char context window after the anchor is what the
    joiner mines for title/company confirmation."""
    hits, seen = [], set()
    for m in _LINK.finditer(body):
        url = m.group(1).rstrip("/")
        if url in seen:
            continue
        seen.add(url)
        anchor = re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", " ", m.group(2)))).strip()
        ctx = re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", " ", body[m.end():m.end() + 700]))).strip()
        hits.append({"url": url, "anchor": anchor[:200], "ctx": ctx[:350]})
    return hits


def classify(status, body, hits):
    """Return (hits, ok). THE invariant of this whole module:

        ok=False means the ENGINE failed — the caller must NOT mark the
        company done. Without this, a ban silently converts to "we searched
        everyone and found nothing," which is unrecoverable after the fact.

    False-positive guard: SearXNG pages contain 'captcha_pass' in benign URLs
    after auto-passing a challenge. Naive marker matching reads that as a
    block and halts a healthy run — so a marker only counts as a real block
    when there are NO results alongside it.  [recovered: harvester_syn.py]
    """
    blocked = status != 200 or any(m in body.lower() for m in _BLOCK_MARKERS)
    if hits:
        return hits, True
    if blocked:
        return [], False
    return [], True


class Engine:
    """One search instance with its own pacing clock and block streak."""

    def __init__(self, name, base_url):
        self.name = name
        self.base = base_url  # e.g. "https://priv.au/search?q="
        self.streak = 0
        self.rest_until = 0.0

    def available(self, now=None):
        return (now or time.time()) >= self.rest_until

    def search(self, query, fetch):
        """fetch(url) -> (status:int, body:str). Injected so tests run offline
        and callers choose their client (scrapling stealth vs urllib)."""
        status, body = fetch(self.base + urllib.parse.quote(query))
        hits, ok = classify(status, body, extract(body))
        if ok:
            self.streak = 0
        else:
            self.streak += 1
            if self.streak >= BLOCK_STREAK_LIMIT:
                self.rest_until = time.time() + COOLOFF_S
                self.streak = 0
        return hits, ok

    def pace(self):
        time.sleep(random.uniform(*PACING_S))


def harvest(companies, engines, fetch, ledger, out_path, query_fn):
    """Walk companies round-robin across available engines. Appends JSONL to
    out_path (append-mode + the ledger = crash-resumable: a rerun continues,
    and person-level dedup downstream makes overlap harmless).

    ledger: gtm.ledger.Ledger — a company is marked done ONLY on ok=True.
    query_fn(company) -> the search query string.
    """
    done = 0
    with open(out_path, "a") as out:
        for c in companies:
            if ledger.is_done("harvest", c["company"]):
                continue
            eng = next((e for e in engines if e.available()), None)
            if eng is None:
                break  # every instance resting — stop cleanly, resume later
            hits, ok = eng.search(query_fn(c), fetch)
            if ok:
                for h in hits:
                    h["company"] = c["company"]
                    h["lane"] = c.get("lane", "call")
                    h["icp"] = c.get("icp", "?")
                    out.write(json.dumps(h) + "\n")
                out.flush()
                ledger.mark_done("harvest", c["company"])
                done += 1
            # ok=False: engine trouble — company stays pending, streak counted.
            eng.pace()
    return done
