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
    """provider: an adapter exposing .estimate(rows) -> credits and
    .enrich(rows) -> rows-with-contact-fields (e.g. a FullEnrich client, built
    against your own account per SETUP.md).

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
