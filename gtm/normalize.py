"""Entity normalization — the unglamorous functions every lead tool gets wrong.

Every dedup failure in the original runs traced to an incomplete version of
normc()'s suffix list. The list below is the battle-tested one; extend it only
with suffixes, never with words that can start a real company name.
"""
import html
import re

_SUFFIXES = re.compile(
    r"\b(inc|llc|corp|corporation|co|ltd|company|group|usa|america|na|north america|the)\b\.?"
)


def normc(s):
    """Canonical company key: lowercase, suffixes stripped, alphanumeric only.

    'Godshall's Quality Meats, Inc.' and 'GODSHALLS QUALITY MEATS LLC' must
    collide — person-level dedup keys on normn(first) + '|' + normc(company),
    and a miss here means the same person ships twice.
    """
    if not s:
        return ""
    s = html.unescape(str(s)).lower().strip()
    s = _SUFFIXES.sub("", s)
    return re.sub(r"[^a-z0-9]", "", s)


def normn(s):
    """Canonical person-name key."""
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def person_key(first, company):
    """THE dedup key. Person-level, not row-level — this is what makes ledger
    resets and re-scans safe (rescanning can only re-find, never duplicate)."""
    return normn(first) + "|" + normc(company)
