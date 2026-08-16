# SETUP — written for the AI agent

You are an AI agent setting this system up for a human. Read this whole file,
then execute it top to bottom. Ask the human only the questions in the
interview — everything mechanical is yours to do. Target: **running in ~30
minutes. First full CSV lands overnight, not in 30 minutes** — harvest pacing
is deliberately slow (see step 6), and honesty about that beats a broken
promise.

## 0. Detect what already exists — never reimplement an authenticated CLI

Check, in order: `claude`/`codex`/`gemini` (any = LLM backend `cli`, no API
key needed), `gh`, `composio`. If the human's tools already hold auth for a
provider, route through them instead of writing API clients. Then:

```bash
python3 --version         # need 3.10+
pip install -r requirements.txt
python3 run.py check      # must print an OK line per ICP and your llm backend
```

## 1. The interview → their ICP

Run `prompts/interview.md` with the human. It is adversarial by design — you
must challenge their ICP at least once with real research before writing
`icps/<their-name>/icp.yaml` (schema: `icps/example/icp.yaml`). Finish with
`python3 run.py check` passing.

## 2. Registries (free, no keys)

Map their segments to registries during the interview:
- Meat/poultry/egg processing → `fsis` (needs `pip install scrapling` +
  `scrapling install`; the site is bot-walled — the adapter fetches in-page)
- Anything manufacturing with NAICS + size floor → `osha_ita` (plain HTTPS)
- Medical devices → `fda_devices` (openFDA JSON API)

```bash
python3 run.py registry --icp <name>
python3 run.py hygiene  --icp <name>
```

If no registry covers their vertical, discovery cells carry the whole load —
the pipeline still works, it just loses the free-universe advantage.

## 3. Accounts the human must create (give them these exact links)

| Service | Why | Link | Cost |
|---|---|---|---|
| Apollo | people discovery (free tier) | https://www.apollo.io/sign-up | $0 |
| FullEnrich | phones + emails, LAST stage only | https://app.fullenrich.com/register | paid credits |
| SearXNG | LinkedIn-URL harvest | none — public instances at https://searx.space, or self-host | $0 |

Copy `.env.example` → `.env` for anything key-based. Keys never enter the
repo; `.env` is gitignored.

## 4. Discovery (agent fan-out — this is you)

Read `workflows/discovery-fanout.md` in full and follow its limits exactly
(one fan-out level, ~10-20 rows/batch, small models for bulk, ledger updated
in code). Output: `data/<icp>/raw/candidates_<cell>.jsonl` rows
`{first, company, title, lane, icp}`.

## 5. Curate the visit lane (human + you)

If their ICP has a visit lane: geocode-filter companies to the radius
(`registries/geocode.py`), then the human confirms the shortlist. Write the
normc'd names to `data/<icp>/raw/visit_companies.json`. Companies never
inherit visit from a discovery cell's geography.

## 6. Harvest (long-running, headless)

Use `gtm/harvest.py` with 3-4 instances from https://searx.space, ONE worker
per instance. Pacing is 7-12s per instance and is an ethical floor —
volunteer infrastructure, not a tunable. Schedule it (launchd/cron) and let
it run overnight; it is crash-resumable via the ledger.

## 7. Join → QA → export

```bash
python3 run.py join   --icp <name>
python3 run.py export --icp <name>   # data/<icp>/out/{call,visit}_leads.csv
```

Run classification (`prompts/classify.md`) over the company universe before
trusting the CSVs; MISFIT rows go to a recoverable sidecar.

## 8. Enrichment — ONLY on explicit human approval

`gtm/enrich.py` refuses to run without `confirm='spend <N>'` where N is the
exact row count. Show the human the count and the credit estimate, get their
yes, then run. Phone-first: sort the final sheet by
`rank_contactability` (mobile > direct > switchboard > email-only).

## Done means proven

- [ ] `python3 run.py check` exit 0
- [ ] `python3 -m pytest tests/ -q` all green
- [ ] registry pull produced non-empty shards (or documented: no registry fits)
- [ ] one end-to-end fixture run: hygiene → join → export produced a CSV
- [ ] harvest scheduled headless, ledger advancing
- [ ] human knows the enrichment gate exists and how to approve a spend

Report each with the command and its exit code. Anything you could not run:
say **unverified** and name the exact check the human must perform.
