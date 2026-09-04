# The outreach interview — adversarial by design

You are producing `icps/<name>/outreach.yaml` (schema: `icps/example/outreach.yaml`).
The ICP interview already decided WHO the buyer is; this one decides who gets
a cold connection request, what it says, and — the question everyone skips —
who must never receive one.

**Hard rule: you may not write the file until the note has survived the
stranger test (below) and the user has answered the protected-list question
with at least a considered "nobody".** A cold pitch reaching a customer, a
vendor, or an investor costs more than a hundred good sends earn.

## Stage 0 — start from the ICP

Read `icps/<name>/icp.yaml`. Its `segments` and `titles.ops` are your search
tiers; its `titles.bad` and `drop.patterns` are your first deny-lists. Draft
the whole config yourself, then interview to correct it.

## The interview (≤8 questions)

1. **The note, in their words.** Ask them to write it as a text message to a
   stranger who runs the exact team they sell to. Then run the stranger test:
   *Would this person accept a connection from someone they've never heard of
   on the strength of this text alone?* Three things that fail it: a link, a
   second ask, any sentence about the sender's company instead of the
   reader's problem. Cut until ≤300 characters. Read the final count aloud.
2. **The one ask.** Fifteen minutes? A live demo? A reply? Exactly one.
3. **Which segments get outreach at all.** Not every ICP segment deserves
   cold LinkedIn — some are reached better by the phone list this pipeline
   already produced. Tier the survivors 1→N by how fast they buy.
4. **Search strings per tier.** Pair every generic title with an industry
   keyword; bare "operations manager" returns noise. Aim for 8-15 total.
5. **Who structurally cannot buy.** Mega-corps whose staff can't sign,
   government, staffing agencies, competitors, the vendor's own orbit. These
   become `deny_employers` (substring on the API-returned employer).
6. **Who reads senior but owns nothing.** Sellers, recruiters, HR, IC
   technicians, consultants, students. `deny_titles`.
7. **The protected list.** *Name every person a cold pitch would embarrass
   you in front of: current customers, vendors you buy from, investors,
   partners, your co-founder's contacts, anyone you've already met.* Full
   names or profile URLs. Push once if they say "nobody" — everyone has a
   vendor.
8. **Geography and account.** Which country (→ `geo_urn`). Is the LinkedIn
   account Premium? If not, stop: Basic caps connection notes at a few per
   month and this stage cannot work.

## The challenges (run at least one)

- **Note check against reality:** search LinkedIn for three people matching
  tier 1. Read their headlines. Does the note name a problem those specific
  people plausibly have this quarter? If the note talks about "efficiency"
  and their headlines talk about "backlog", say so.
- **Deny-list check:** run one tier-1 search and look at the first ten
  employers. Any that should be denied and aren't? Any denied that shouldn't
  be?

## Output

Write `icps/<name>/outreach.yaml` with every key from the example present.
Then:

    python3 run.py check                       # must print "outreach: OK"
    python3 run.py outreach --icp <name> --check   # browser + login + allowance

Show the user the allowance line. The config is not done until both pass.
Then explain the gate: `outreach --icp <name>` sources and vets a queue and
sends nothing; only `--send` sends. They decide when.
