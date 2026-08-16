# Per-lead call angle

For each lead, write the `angle` field: the ONE specific thing the caller
says in the first ten seconds that proves this isn't a spray-and-pray dial.

Rules:
- Grounded in a verifiable fact about the company (registry data you already
  have: activities, size class, NAICS, location; or their site). Never
  invented, never "I saw you're growing".
- ≤ 20 words. It's a call opener, not a paragraph.
- In the USER'S register — derived from their writing samples during the
  interview, not from any default voice. If no samples exist, plain and
  direct beats clever.
- Phone-first framing: this line is spoken aloud. Read it aloud; if it
  sounds like an email, rewrite it.

Batch task, small model, ~20 rows per call. Output JSON only:
`[{"i": 0, "angle": "..."}]`
