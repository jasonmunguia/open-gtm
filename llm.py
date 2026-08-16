"""LLM access — three backends, none of them ours.

BYOM (bring your own model): the pipeline is deterministic code with exactly
three judgment joints — classification (is this company really in the ICP),
the adversarial ICP interview, and per-lead call angles. Everything else is
plain code and must stay that way.

Backends, resolved in order unless GTM_LLM forces one:
  cli   any coding-agent CLI on PATH (claude, codex, gemini, ...) —
        no API key, uses the user's existing subscription. Headless-safe.
  api   any OpenAI-compatible or Anthropic endpoint via env vars.
  none  judgment joints are skipped; the deterministic pipeline still runs
        end-to-end (keyword-gated instead of judgment-gated).

Model-routing doctrine (a scar, not a preference): bulk classification is a
fixed-schema mechanical judgment → send it to a SMALL/fast model. The
original run defaulted a frontier model into a 1,313-row scoring job; it was
slower than its own timeout and the feature silently never ran. Frontier
models are for the interview and for nothing in a loop.
Batch ceiling: ~20 rows per call (20 rows at 300s blew the budget even on a
small model; 10-20 amortizes per-call overhead without tripping timeouts).
"""
import json
import os
import shutil
import subprocess
import urllib.request

CLI_CANDIDATES = ("claude", "codex", "gemini")
BATCH_MAX = 20


def detect_backend():
    forced = os.environ.get("GTM_LLM")
    if forced:
        return forced
    for c in CLI_CANDIDATES:
        if shutil.which(c):
            return "cli"
    if os.environ.get("LLM_API_KEY"):
        return "api"
    return "none"


def _run_cli(prompt, timeout=300):
    exe = os.environ.get("GTM_LLM_CLI") or next(c for c in CLI_CANDIDATES if shutil.which(c))
    # `-p` = headless one-shot prompt (claude & codex compatible flag)
    out = subprocess.run([exe, "-p", prompt], capture_output=True, text=True, timeout=timeout, check=False)
    if out.returncode != 0:
        raise RuntimeError(f"{exe} exited {out.returncode}: {out.stderr[:300]}")
    return out.stdout.strip()


def _run_api(prompt, timeout=120):
    """OpenAI-compatible chat endpoint (works for most providers incl. local
    servers). LLM_API_BASE, LLM_API_KEY, LLM_MODEL from env."""
    base = os.environ.get("LLM_API_BASE", "https://api.openai.com/v1")
    body = json.dumps({
        "model": os.environ.get("LLM_MODEL", "gpt-4o-mini"),
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        f"{base}/chat/completions", data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {os.environ['LLM_API_KEY']}"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)["choices"][0]["message"]["content"]


def ask(prompt, timeout=300):
    backend = detect_backend()
    if backend == "cli":
        return _run_cli(prompt, timeout)
    if backend == "api":
        return _run_api(prompt, timeout)
    return None  # backend 'none': caller must have a deterministic fallback


def ask_json(prompt, timeout=300):
    """ask(), then extract the first JSON array/object from the reply.
    Degrade gracefully: on ANY failure return None and let the keyword path
    stand — an LLM hiccup must never kill a pipeline run. [rerank.py pattern]"""
    try:
        txt = ask(prompt, timeout)
        if not txt:
            return None
        start = min(x for x in (txt.find("["), txt.find("{")) if x != -1)
        end = max(txt.rfind("]"), txt.rfind("}")) + 1
        return json.loads(txt[start:end])
    except Exception:  # noqa: BLE001 — deliberate: an LLM hiccup must never kill a run
        return None
