# Agent orchestration — the fan-out doctrine

The deterministic spine (run.py) handles registry → hygiene → join → export.
Two stages are agent-orchestrated because they're embarrassingly parallel:
**discovery** (finding people at known-good companies) and **classification**
(FIT/MISFIT over the universe). This file is the doctrine for running them —
every number below was paid for in the original runs.

## The prime rule

> Orchestration stays on the main model; ALL bulk work fans out to small/fast
> subagents at low reasoning effort. List-building isn't a reasoning task —
> this cuts token burn ~5x per lead. Dedup runs in plain code between stages
> (zero tokens). Raw provider JSON stays QUARANTINED inside subagents; only
> clean rows come back.

That last sentence is what makes 60-80 parallel agents affordable: the
orchestrator's context never sees a raw API response.

## When to fan out

| Situation | Fan out? |
|---|---|
| Classify 1,500 companies against the ICP | ✅ one agent per ~20-company batch (real runs: 60 and 80 agents) |
| Sweep 12 verticals for people | ✅ one agent per discovery cell (vertical × geography) |
| Backfill addresses for 55 companies | ✅ but ONE agent — it's small enough |
| Registry pull, join, dedup, export | ❌ plain code, zero tokens |
| Nightly chain: ingest → score → deliver | ❌ dependent stages, not cells |
| QA (row counts, URL checks, dedup checks) | ❌ scripts — moved off agents mid-run in the original, deliberately |

**Pipelined, not phased:** resolution/classification agents start on cell 1's
output while cells 2-12 are still discovering. Never barrier unless a stage
truly needs ALL prior output (dedup across the full set is plain code anyway).

## Hard limits (each one is a scar)

1. **Fan-out is ONE level.** Subagents never spawn their own subagents against
   a shared quota — three agents once each spawned three more and ~9 hit a
   200-search budget simultaneously.
2. **Web-search budgets are for verification, never bulk sweeps** — bulk
   sweeps through a search budget killed two whole discovery rounds.
3. **Batch size ~10-20 rows per agent call.** 20 rows at 300s blew the budget
   even on a small model; below 10, per-call overhead dominates.
4. **A discovery cell's geography is not a person's geography.** Cells tagged
   by location must never promote their companies into the visit lane — only
   curated-local companies are visit (a 96-row audit taught this).
5. **A coverage ledger (gtm/ledger.py) records every swept cell** —
   geography × segment × title. Without it, "the universe is exhausted"
   and "we repeated ourselves" are indistinguishable.

## Stop condition — loop-until-dry

Do not stop at a lead count. Keep opening discovery cells until consecutive
cells come back zero or near-zero — that's exhaustion. The original run ended
exactly this way: "the last three discovery cells came back zero or
near-zero." Depth note: provider pagination is rarely exhausted (cells showed
2,000-23,000 matches while pulling 200-300) — depth is a lever before width.

## Provider discipline (Apollo free tier, recovered workarounds)

- Free-tier search DISPLAYS max ~100 results regardless of total_entries:
  batching 3-5 titles strands the tail behind the cap. **One title per
  search × narrow geography (state groups); paginate to page 4-6 while
  quality holds.** (Discovered at round 4 of run 1, the hard way.)
- Free people-search only in bulk; bulk_match/enrich are PAID and live behind
  the enrichment gate (gtm/enrich.py), never inside a discovery cell.

## Claude Code Workflow template

If your agent is Claude Code, discovery runs as a Workflow (deterministic
fan-out with resume caching — unchanged (prompt, opts) replay from cache, so
editing post-processing never re-runs 80 agents):

```js
export const meta = {
  name: 'discovery-cells',
  description: 'One agent per discovery cell; clean rows only come back',
  phases: [{ title: 'Discover' }, { title: 'Classify' }],
}
const CELLS = args.cells  // [{segment, geo, titles}, ...] from the ICP
const rows = await pipeline(
  CELLS,
  c => agent(
    `Discovery cell ${c.segment}/${c.geo}. Search the people provider ONE
     title per search, titles: ${c.titles.join('; ')}. Geography: ${c.geo}.
     Free tier only — no enrichment calls. Return ONLY clean JSON rows
     [{first,company,title}] — never raw API responses.`,
    { label: `cell:${c.segment}:${c.geo}`, phase: 'Discover', effort: 'low' }),
  (found, c) => agent(
    `Classify per prompts/classify.md against this ICP: <fit/misfit text>.
     Companies: ${JSON.stringify(found?.slice(0, 20))}. JSON only.`,
    { label: `classify:${c.segment}`, phase: 'Classify', effort: 'low' })
)
return rows.filter(Boolean).flat()
```

Any other agent framework: same shape — cells in, clean rows out, one level
deep, ledger updated by the orchestrator (plain code), never by the cells.
