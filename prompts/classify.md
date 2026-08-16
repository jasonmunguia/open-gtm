# Company classification — FIT / MISFIT

Batch task for a SMALL/fast model (see llm.py's model-routing doctrine —
this is fixed-schema mechanical judgment, and a frontier model in this loop
once ran slower than its own timeout and silently never classified 1,313
rows). Batches of ~20 companies per call, maximum.

## Input
The ICP's `fit` and `misfit` paragraphs (from icp.yaml), plus a JSON array of
companies: `[{"i": 0, "company": "...", "context": "..."}]`.

## Task
For each company return FIT or MISFIT with the reason category:

- FIT → assign the segment key from the ICP's `segments`
- MISFIT → one of: end-user | distributor | transport | sub-scale |
  software | staffing | competitor | parse-error | defunct | other

Judgment guidance recovered from the original runs:
- **The economic test beats the keyword test.** For a product sold to
  servicers: a hospital's "service manager" is a cost center (MISFIT
  end-user); an equipment servicer's is billable (FIT). Same title,
  opposite verdicts.
- **Parse-errors exist.** Harvest reconstructs names from URL slugs and
  sometimes attaches people to the wrong company (car dealership managers,
  college robotics clubs). A company that doesn't look like a company is a
  parse-error, not "other".
- **CPG brand owners are MISFIT unless the visible titles are
  production/assembly** — then they're a manufacturer wearing a brand.

## Output
ONLY a JSON array: `[{"i": 0, "verdict": "FIT", "segment": "...", "why": "<=12 words"}]`
or `[{"i": 0, "verdict": "MISFIT", "reason": "distributor", "why": "..."}]`.
No prose. MISFIT rows are moved to a recoverable sidecar, never deleted.
