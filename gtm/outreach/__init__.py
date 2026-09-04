"""LinkedIn outreach — the first-touch stage after the lead CSV.

BYOK: you bring a LinkedIn account (Premium — Basic caps connection notes at
a handful per month, which makes this whole stage pointless) and a Chromium
browser. The repo brings sourcing, vetting, pacing, a ledger, and API-verified
sending. Your context lives in ONE file, icps/<name>/outreach.yaml, written by
prompts/outreach-interview.md. Nothing here knows your product.

Two phases, one gate:
  Phase A (read-only)  search → vet → queue.  `run.py outreach --icp X`
  Phase B (sends)      queue → paced sends.   `run.py outreach --icp X --send`
The gate exists because a connection request is not reversible in any way
that matters: LinkedIn restrictions are behaviour-based, take ~a week to
lift, Support will not lift them early, and withdrawing invites does not
help. You look at the queue before anything goes out.
"""
