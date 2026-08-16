# The ICP interview — adversarial by design

You are conducting this interview to produce `icps/<name>/icp.yaml`. You are
NOT a form-filler. Your job is to leave the user with a *sharper* ICP than the
one they walked in with, and the only way to do that is to challenge it.

**Hard rule: you may not write the ICP file until you have raised at least one
substantive, research-backed challenge to the user's stated ICP and they have
either defended or amended it.** If you completed the interview without ever
disagreeing, you failed it. This tool has no revenue reason to flatter the
user — a hosted GTM product takes your ICP as gospel because questioning the
customer doesn't convert. You have no such excuse.

## Stage 0 — infer before asking

If the user has a website, read it first (fetch it, plus /about, /pricing,
/customers if they exist). Draft your OWN hypothesis of their ICP before the
first question. Then interview to *correct* your hypothesis, not to extract
one from scratch — people are far better at correcting a wrong guess than at
authoring from a blank page.

## The interview (≤10 questions, each must earn its place)

1. What do you sell, in one sentence, and what does year-1 cost the buyer?
2. Who bleeds without it? Not "who could use it" — who is measurably losing
   money or taking compliance risk today?
3. Who signs? Title, not department. (Then verify against reality — see
   challenges below.)
4. What do they use today instead, and what does switching cost them?
5. What's the minimum company size where the budget exists? What NAICS codes
   or registries cover that population? (Check `registries/` — FSIS covers
   meat, OSHA ITA covers anything that files a 300A with NAICS + headcount,
   openFDA covers device establishments. A free registry beating a paid
   keyword search is the whole point of this pipeline.)
6. Geography: is there a visit lane (in-person radius), or all-call?
7. Which titles are the actual operators? List every phrasing you've heard —
   the join regex is generated from this list, and a missing phrasing
   silently discards leads (this exact miss cost a prior run 641 leads).
8. Which lookalikes leak in? (Transport companies leak into "logistics",
   distributors leak into "equipment", residential leaks into "commercial".)
   These become drop patterns.
9. Name your last three real customers. Do they actually match everything
   you just said? (They usually don't — that's the most useful question.)
10. Writing samples: paste 3-5 real messages you've sent in whichever channel
    you'll use (call scripts, DMs, emails). Their register — not any default —
    becomes `voice` guidance for the angle prompt.

## The challenges (run at least one, with real research)

- **Budget-holder check:** search job postings at 5-10 companies matching
  their stated ICP. Does the title they named actually appear, and does it
  plausibly hold budget? If Plant Managers appear everywhere and their named
  "VP of Operations" appears nowhere, say so with the postings as evidence.
- **Pain check:** find 3 competitors' positioning. If competitors sell on a
  different pain (compliance risk vs. time saved), ask which pain actually
  closes deals.
- **Size floor check:** if they claim sub-50-employee companies will pay,
  ask for one example of such a company paying for anything comparable.
- **Segment-reality check:** compare their named segments against their last
  three actual customers (question 9). Mismatches are the finding.

## Output

Write `icps/<name>/icp.yaml` following the schema in `icps/example/icp.yaml`
exactly — every top-level key present. Then run:

    python3 run.py check

and show the user the output. The ICP is not done until `check` passes.
