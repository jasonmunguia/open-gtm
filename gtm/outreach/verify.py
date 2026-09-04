"""Was the invite actually sent, to the right person, with the right note?

Answered from LinkedIn's sent-invitations API, never from the UI. The toast
is not proof the note attached. "A new invitation exists" is not proof it went
to the intended person: in the original runs a sidebar mis-click pitched a
stranger, and a newest-invite check logged it as sent under the intended
name. So the rule is: OURS is the invite whose recipient slug matches the
intended profile AND whose message equals the note verbatim. Nothing else.
"""
SENT = "sent"
SENT_NOTE_MISMATCH = "sent-note-mismatch"
WRONG_RECIPIENT = "wrong-recipient"
UNCONFIRMED = "unconfirmed"


def slug_of(url):
    return url.rstrip("/").split("/")[-1].lower()


def classify_send(invitations, want_slug, note, before_newest_time):
    """invitations: parsed js/sent_invitations.js output [{to, slug, msg, sent}].
    Returns (outcome, invitation-or-None).

    The full recent list is searched, never just the newest entry: a manual
    invite sent from the account owner's phone can land between our click
    and this check, and a newest-only rule would have "corrected" it —
    withdrawing THEIR invite. Ours is identified by slug + note only.
    """
    want = want_slug.lower()
    mine = [x for x in invitations if (x.get("slug") or "").lower() == want]
    if mine:
        return (SENT, mine[0]) if mine[0].get("msg") == note else (SENT_NOTE_MISMATCH, mine[0])
    strays = [x for x in invitations
              if (x.get("sent") or 0) > (before_newest_time or 0) and x.get("msg") == note]
    if strays:
        return WRONG_RECIPIENT, strays[0]
    return UNCONFIRMED, None
