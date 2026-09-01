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

`gtm/harvest.py` is a library with **no CLI on purpose** — it takes injected
`fetch` and `query_fn` so it stays testable offline, so you write the ~30-line
runner. Everything the runner must decide is specified here; none of it is
yours to invent.

```python
harvest(companies, engines, fetch, ledger, out_path, query_fn)
```

| Arg | What to pass |
|---|---|
| `companies` | rows from `data/<icp>/derived/companies.jsonl` (written by `run.py hygiene`) |
| `engines` | 3-4 `harvest.Engine(name, base_url)`; `base_url` ends at the query param, e.g. `"https://priv.au/search?q="` |
| `fetch` | `fetch(url) -> (status: int, body: str)`, body = raw HTML |
| `ledger` | `Ledger(data(icp) / "derived" / "ledger.json")` — same path `run.py status` reads |
| `out_path` | **must** be `data/<icp>/raw/harvest_hits.jsonl` — `run.py join` hardcodes it |
| `query_fn` | `query_fn(company_row) -> str` |

**The query template.** This one parameter decides whether the harvest yields
tens of thousands of URLs or nothing:

```python
query_fn = lambda c: f'site:linkedin.com/in "{c["company"]}"'
```

Return the query **unquoted** — `Engine.search` applies `urllib.parse.quote`
itself, and double-quoting is the failure that looks like a total block.
Add a title term only if a company over-returns; narrowing per-company costs
more requests than it saves, and the title gate runs at join time anyway.

**The fetch client.** Use plain `urllib` via `registries/_net.py` (the
certifi-patched opener). SearXNG instances are not bot-walled — scrapling is
for FSIS only, which is why `requirements.txt` keeps it commented out.
Reach for scrapling here **only** if an instance starts returning challenge
pages that `classify()` counts as blocks across several cool-offs; the
cheaper fix is dropping that instance for another from searx.space.

Run ONE worker per instance. Pacing is 7-12s per instance and is an ethical
floor — volunteer infrastructure, not a tunable. Schedule it (launchd/cron)
and let it run overnight; it is crash-resumable via the ledger, so a rerun
continues where it stopped.

## 7. Join → QA → export

```bash
python3 run.py join   --icp <name>
python3 run.py export --icp <name>   # data/<icp>/out/{call,visit}_leads.csv
```

Run classification (`prompts/classify.md`) over the company universe before
trusting the CSVs; MISFIT rows go to a recoverable sidecar.

## 8. Enrichment — ONLY on explicit human approval

**The provider client is yours to build — this section is its spec.** No
enrichment adapter ships here: the paid vendor is the one piece that must be
BYOK, and a shipped client would rot against whichever vendor you actually
use. Everything you need to write it is below.

**Where it goes.** Create `gtm/providers/<vendor>.py` exposing a class with
the two methods `gtm/enrich.py` calls — read that docstring for the exact
contract (`estimate(n: int)`, `enrich(rows) -> rows`, and the recognised
contact keys). There is deliberately no `run.py enrich` subcommand: money
does not belong behind a CLI flag someone can shell-history their way into.
Invoke it from a short script you write (`scripts/enrich_<icp>.py`) that
loads the QA'd rows, prints the count and the estimate, waits for the human,
then calls `request_enrichment(...)` with the confirm string.

**FullEnrich** (the vendor the original runs used):
- API docs: https://docs.fullenrich.com — read these before writing the client
- Base URL: `https://app.fullenrich.com/api/v1`
- Auth: `Authorization: Bearer $FULLENRICH_API_KEY` (slot in `.env.example`)
- Shape: bulk enrichment is **asynchronous** — POST a batch, receive an
  enrichment id, then poll for results. Budget for the poll loop; do not
  assume a synchronous response.
- Credits are per contact requested, not per contact found. That asymmetry is
  the whole reason this stage runs last.

**Apollo** is discovery, not enrichment, and has **no HTTP client in this
repo by design** — §0 and §4 route it through your own authenticated tooling
(an MCP server, a vendor CLI, or the web app). If you have none of those,
Apollo's own API docs are at https://docs.apollo.io and the same
build-your-own rules apply. Discovery cells can also be filled by hand from
the registry universe; the pipeline does not require Apollo.

**The gate.** `gtm/enrich.py` refuses to run without `confirm='spend <N>'`
where N is the exact row count. Show the human the count and the credit
estimate, get their yes, then run. Phone-first: sort the final sheet by
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
