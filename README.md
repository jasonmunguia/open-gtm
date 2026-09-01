# open-gtm

Built by [Jason Munguia](https://github.com/jasonmunguia). Apache-2.0 — free to use, fork and build on, **with credit**.

**Registry-first, phone-first lead generation. Self-hosted, BYOK/BYOM. The paid step runs last.**

Clone it, hand it to your coding agent, and be running in ~30 minutes. First
full CSV lands overnight — the harvest paces itself on purpose.

---

## The philosophy

Every GTM tool on the market gets you to the paid data as fast as possible, because the tool vendor **is** the paid data. Paste your domain, agents run, and you're renting a database by the credit — enriching thousands of contacts you'll never call, at companies that were never really your buyer.

This system inverts that, three times.

**Registry-first.** Your company universe comes from free federal registries before any paid provider sees a query. FSIS lists every federally inspected meat plant in America — with addresses, size classes, and switchboard phone numbers. OSHA's injury-tracking data lists every manufacturer that files a 300A, with NAICS codes and headcounts. openFDA lists every device establishment by state. A registry *is* the universe: free, authoritative, with a size floor built in. Paid keyword search guesses at the universe and eats vendor junk — the run this system is distilled from learned that the expensive way.

**Pay-last.** Six free stages — registry, hygiene, discovery, harvest, join, QA — run before one credit is spent. Enrichment happens only on rows that survived all six, only with an explicit human confirmation of the exact spend (`confirm='spend N'` — the awkwardness is the feature), and it optimizes for **phone numbers, not emails**. Inboxes are saturated and filtered. The dial is the undersupplied channel. The original run produced 3,228 QA'd leads for $0 in data costs before the first enrichment decision.

**The ICP interview argues back.** Hosted tools take your ICP as gospel, because questioning the customer doesn't convert. This one is *required* to challenge your ICP with independent research — job postings, competitor positioning, your own last three customers — before it writes a single line of config. A self-hosted tool has no revenue reason to flatter you. That's a structural advantage, and this repo spends it.

Every non-obvious constant in the code carries the incident that set it, inline, at the constant. Where a reason couldn't be recovered from the audit trail, it says **reason not recovered** rather than inventing one. A rule without its reason is cargo cult — someone "optimizes" the 7-12s pacing, gets an instance banned, and blames the tool.

## → For your AI agent

You're an agent and a human just handed you this repo. Your path:

1. Read `SETUP.md` top to bottom — it is addressed to you and is the setup
   procedure. Detect existing authenticated CLIs before writing any client.
2. Run the interview (`prompts/interview.md`). It is adversarial by design:
   you may not write the ICP until you've challenged it with research.
3. Follow `workflows/discovery-fanout.md` for anything parallel. Its limits
   (one fan-out level, ~10-20 rows per batch, small models for bulk, ledger
   in code) are scars, not suggestions.
4. `python3 run.py check` and `python3 -m pytest tests/ -q` must pass before
   you report anything as working. Report with commands and exit codes;
   anything you couldn't run is **unverified**, named as such.

## Quick start (human version)

```bash
git clone <this-repo> && cd open-gtm
pip install -r requirements.txt
python3 run.py check          # environment + ICP sanity
python3 -m pytest tests/ -q   # all offline, no keys needed
```

Then hand it to your agent (Claude Code, Codex, any CLI agent) and say:
*"set this up for me per SETUP.md."*

## What you bring (BYOK)

| | Why | Cost |
|---|---|---|
| A coding agent | the judgment joints: interview, classify, angles | your existing subscription |
| Apollo (free tier) | people discovery | $0 |
| FullEnrich | phones + emails, terminal stage only | credits, gated, explicit |
| SearXNG instances | LinkedIn-URL harvest | $0 (be polite — see pacing) |

No keys ship in this repo. `.env.example` is blank slots. The pipeline runs
end-to-end with `GTM_LLM=none` — deterministic only, keyword-gated.

Two pieces are deliberately yours to write, and both are fully specified
rather than shipped: the **harvest runner** (SETUP.md §6 — signature, query
template, client choice) and the **enrichment provider adapter** (SETUP.md §8
— endpoints, auth, contract). A shipped paid-vendor client rots against
whichever vendor you actually use; a spec doesn't.

## Architecture

```
deterministic spine (run.py)          agent joints (prompts/)
  registry → hygiene → join → export    interview · classify · angle
agent-orchestrated (workflows/)       paid terminal stage (gated)
  discovery fan-out · paced harvest     enrich: phone-first, confirm='spend N'
```

Per ICP: `data/<icp>/raw/` (immutable) → `derived/` (disposable — delete it
and the next run rebuilds identically) → `out/` (call + visit CSVs).

## License

Apache-2.0 — free to use, fork and build on, **with credit** (see NOTICE).
Built by [Jason Munguia](https://www.linkedin.com/in/jason-munguia/) —
distilled from real runs that produced 3,200+ QA'd, phone-ready leads at $0
in data costs.
