"""Volume and rhythm. Both numbers are guardrails, not throughput settings."""
import random


def allowance(daily_target, weekly_cap, weekly_buffer, sent_last_7d):
    """How many invites this run may send. Computed from LinkedIn's OWN
    sent-invitations list at run start, so hand-sent invites count against
    the week too — the cap is on the account, not on this tool."""
    return min(daily_target, max(0, weekly_cap - weekly_buffer - sent_last_7d))


def make_gaps(n_sends, lo, hi, rng=random):
    """One randomized gap AFTER each successful send except the last. No gap
    before the first. A skip consumes no gap — gaps pace sends, not attempts."""
    return [round(rng.uniform(lo, hi), 2) for _ in range(max(n_sends - 1, 0))]
