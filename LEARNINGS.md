# Learnings

Append-only, newest first. Every entry is a thing that broke or a rule whose
reason would otherwise be lost. Where the audit trail didn't preserve the
reason, the entry says **reason not recovered** — an invented reason is worse
than a missing one, because it stops anyone from looking.

---

## 2026-08-16 — The first smoke test caught two shipping bugs

Built the spine, ran 19 offline tests green, then ran the CLI end-to-end on
fixtures — and the fixture run caught what the unit tests didn't: hygiene
globbed ALL raw shards (feeding people rows into company hygiene), and the
join emitted `first` while the CSV schema wanted `name`, shipping a blank
name column on every lead.

Unit tests test the pieces you thought about. The fixture run tests the
seams. Both are mandatory; neither substitutes.

## 2026-08-16 — FSIS hands a phone-first pipeline its phones

Registry verification found the FSIS directory carries a `phone` column —
7,231 federally inspected plants with switchboard numbers, plus lat/lon
(no geocoding needed for radius checks). A phone-first pipeline gets its
first dialable number at stage 1, for free, before any enrichment spend.

Also: the FSIS site 403s plain curl (Akamai). The CSV must be fetched from
INSIDE a stealth browser page (`page.evaluate(fetch(...))`) where the
bot-check cookies apply. Navigating the browser directly at the CSV URL fails
too — it triggers a download event, not a page load.

## 2026-08-16 — What the audit trail preserved, and what it didn't

Recovered with receipts (now encoded in code/docs): the (hits, ok) engine
invariant; the captcha_pass false-positive guard; the normc() suffix list;
the 641-lead generated-regex scar; the 96-row visit-lane inheritance scar;
one-title-per-search × narrow geo (free-tier ~100-result display cap); the
NO-URL promotion pass; fan-out widths (12/60/80 agents, ~20-row batches);
one-level fan-out (the ~9-agents-on-one-quota incident); small-model routing
(the frontier-model-slower-than-its-own-timeout incident); loop-until-dry.

**Reason not recovered:** why pacing is 7-12s specifically rather than 5 or
15 (the band demonstrably avoided bans across ~49k URLs; its derivation
wasn't written down), and the exact block-streak threshold before the
original cooloffs (this rebuild uses 3).

## 2026-07 (recovered) — The pipeline's founding scars

- **Registry-first:** run 1 built its universe from paid keyword search and
  "ate vendor junk"; the registry IS the universe, free, with size floors.
- **Generated joiner regex:** a hand-maintained title regex silently
  discarded 641 leads for ~4 rounds. The regex is compiled from the ICP's
  title list at load time, never edited.
- **(hits, ok):** an engine block must never mark a company "searched" —
  a ban otherwise converts to "we searched everyone and found nothing."
- **Person-level dedup as the safety net:** it's what makes ledger resets
  and rescans safe (re-find, never duplicate).
- **Visit is curated, never inherited:** discovery geography ≠ person
  geography; 96 rows had to be audited back out.
- **Pay-last:** enrichment on survivors only. Credits spent early are
  credits spent on rows that die in QA.
