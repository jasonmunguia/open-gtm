"""Enrichment — the ONLY paid stage, and it runs LAST, on survivors only.

Pay-last architecture: six free stages (registry, hygiene, discovery, harvest,
join, QA) run before a single credit is spent. Every row reaching this stage
has already survived a registry check, a title gate, a LinkedIn join, and QA.
Enriching earlier burns credits on rows that die downstream — which is the
default behavior of every commercial tool in this category, because the tool
vendor IS the paid step.

Phone-first: the success metric is mobile > direct dial > switchboard.
Email is the secondary field, not the point.

HARD GATE: this module never runs implicitly. It refuses without an explicit
confirm string, and the caller is expected to have shown the row count and
credit estimate to the human first. Credits are money; "the pipeline spent my
credits while I slept" must be impossible.
"""


class SpendNotConfirmed(RuntimeError):
    pass


def request_enrichment(leads, provider, confirm=None):
    """provider: the BYOK adapter you build against your own account (see
    SETUP.md §8 for where it lives and how it is invoked). Two methods:

        estimate(n: int) -> credits
            n is a ROW COUNT, not the rows. Called before the gate, on every
            call, so it must not spend anything or hit a metered endpoint.

        enrich(rows: list[dict]) -> list[dict]
            Returns the same rows with contact fields merged in. Recognised
            keys, in the order rank_contactability prefers them:
                mobile          direct mobile   — the goal
                phone           direct dial
                company_phone   switchboard     — often already on the row
                                                  from the registry
                email           secondary, not the point
            Return every input row, enriched or not, in input order. Dropping
            misses breaks the join with the pre-enrichment sheet; a miss is a
            row whose contact keys are simply absent.

    `confirm` must be the exact string 'spend <N>' where N == len(leads).
    Anything else raises. The awkwardness is the feature: no default, no
    boolean, nothing an agent can pass by habit.
    """
    n = len(leads)
    est = provider.estimate(n)
    expected = f"spend {n}"
    if confirm != expected:
        raise SpendNotConfirmed(
            f"Enrichment gate: {n} rows, estimated {est} credits. "
            f"Nothing was spent. To proceed, call again with confirm='{expected}' "
            f"after the human has approved the spend."
        )
    return provider.enrich(leads)


def rank_contactability(row):
    """Sort key for the call sheet: mobile beats direct dial beats switchboard
    beats email-only. The dial is the product."""
    if row.get("mobile"):
        return 0
    if row.get("phone"):
        return 1
    if row.get("company_phone"):
        return 2
    return 3
