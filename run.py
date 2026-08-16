#!/usr/bin/env python3
"""gtm-system — registry-first, phone-first lead pipeline. BYOK/BYOM.

Usage:
  python3 run.py check                      # environment + ICP sanity, no network
  python3 run.py registry  --icp NAME       # pull free registries -> data/<icp>/raw/
  python3 run.py hygiene   --icp NAME       # apply drop rules -> companies.jsonl
  python3 run.py join      --icp NAME       # harvest hits + candidates -> leads
  python3 run.py export    --icp NAME       # write call/visit CSVs
  python3 run.py status    --icp NAME       # counts per stage, ledger coverage

Stages not in this CLI on purpose:
  discovery (Apollo cells) and harvest (SearXNG) are AGENT-ORCHESTRATED —
  see workflows/discovery-fanout.md. The judgment joints (interview,
  classify, angles) live in prompts/. This CLI is the deterministic spine.

Every write goes under data/<icp>/. --dry-run prints what would happen.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gtm import export as export_mod
from gtm import hygiene as hygiene_mod
from gtm import icp as icp_mod
from gtm import join as join_mod
from gtm.ledger import Ledger
from gtm.paths import data


def cmd_check(args):
    import llm
    print(f"llm backend: {llm.detect_backend()}")
    names = sorted(d.name for d in (Path(__file__).parent / "icps").iterdir()
                   if (d / "icp.yaml").is_file())
    for n in names:
        try:
            icp = icp_mod.load(n)
            print(f"icp {n}: OK ({len(icp.segments)} segments, "
                  f"{len(icp.raw['titles']['ops'])} ops titles, "
                  f"{len(icp.drop_named)} named drops)")
        except Exception as e:  # noqa: BLE001 — check reports every ICP failure, whatever it is
            print(f"icp {n}: FAIL — {e}")
            return 1
    return 0


def cmd_registry(args):
    icp = icp_mod.load(args.icp)
    d = data(icp.name)
    total = 0
    for seg, cfg in icp.segments.items():
        regs = cfg.get("registry")
        if not regs:
            continue
        for reg in regs if isinstance(regs, list) else [regs]:
            out = d / "raw" / f"registry_{reg}_{seg}.jsonl"
            if args.dry_run:
                print(f"would pull {reg} -> {out}")
                continue
            if reg == "fsis":
                from registries import fsis
                rows = fsis.to_companies(fsis.fetch())
            elif reg == "osha_ita":
                from registries import osha_ita
                rows = osha_ita.to_companies(
                    osha_ita.fetch(), cfg.get("naics", []), icp.min_employees)
            elif reg == "fda_devices":
                from registries import fda_devices
                states = cfg.get("states", ["CA"])
                rows = []
                for st in states:
                    rows += fda_devices.to_companies(fda_devices.fetch(st))
            else:
                print(f"unknown registry `{reg}` for segment {seg}")
                return 1
            for r in rows:
                r["icp"] = seg
                r["lane"] = "call"  # visit is CURATED later, never inherited
            with open(out, "w") as f:
                f.writelines(json.dumps(r) + "\n" for r in rows)
            print(f"{reg}/{seg}: {len(rows)} companies -> {out.name}")
            total += len(rows)
    print(f"registry total: {total}")
    return 0


def cmd_hygiene(args):
    icp = icp_mod.load(args.icp)
    d = data(icp.name)
    companies = []
    # registry_* shards ONLY — raw/ also holds candidates_* and harvest_hits
    # shards, which are people, not companies. (Caught by the first smoke test:
    # an unscoped glob fed people rows into company hygiene.)
    for shard in sorted((d / "raw").glob("registry_*.jsonl")):
        with open(shard) as f:
            companies += [json.loads(l) for l in f if l.strip()]
    kept, dropped = hygiene_mod.clean(companies, icp, d / "derived" / "dropped.jsonl")
    with open(d / "derived" / "companies.jsonl", "w") as f:
        f.writelines(json.dumps(c) + "\n" for c in kept)
    print(f"hygiene: {len(kept)} kept, {len(dropped)} dropped (recoverable in dropped.jsonl)")
    return 0


def cmd_join(args):
    icp = icp_mod.load(args.icp)
    d = data(icp.name)
    hits_file = d / "raw" / "harvest_hits.jsonl"
    if not hits_file.is_file():
        print(f"no harvest hits at {hits_file} — run the harvest first "
              f"(workflows/discovery-fanout.md)")
        return 1
    hits = [json.loads(l) for l in hits_file.read_text().splitlines() if l.strip()]
    cand_files = sorted((d / "raw").glob("candidates_*.jsonl"))
    tmap = join_mod.build_title_map(cand_files)
    curated = set()
    curated_file = d / "raw" / "visit_companies.json"
    if curated_file.is_file():
        curated = set(json.loads(curated_file.read_text()))
    leads = join_mod.join(hits, tmap, icp, curated)
    with open(d / "derived" / "leads.jsonl", "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in leads)
    print(f"join: {len(hits)} hits x {len(tmap)} candidates -> {len(leads)} leads")
    return 0


def cmd_export(args):
    icp = icp_mod.load(args.icp)
    d = data(icp.name)
    leads_file = d / "derived" / "leads.jsonl"
    if not leads_file.is_file():
        print("no leads yet — run join first")
        return 1
    leads = [json.loads(l) for l in leads_file.read_text().splitlines() if l.strip()]
    n_call, n_visit = export_mod.export(leads, d / "out")
    print(f"export: {n_call} call, {n_visit} visit -> {d/'out'}")
    return 0


def cmd_status(args):
    icp = icp_mod.load(args.icp)
    d = data(icp.name)
    led = Ledger(d / "derived" / "ledger.json")
    def count(p):
        return sum(1 for l in p.read_text().splitlines() if l.strip()) if p.is_file() else 0
    print(f"icp: {icp.name}")
    for label, p in [("raw registry rows", None),
                     ("companies (post-hygiene)", d / "derived" / "companies.jsonl"),
                     ("harvest hits", d / "raw" / "harvest_hits.jsonl"),
                     ("leads", d / "derived" / "leads.jsonl")]:
        if p is None:
            n = sum(count(s) for s in (d / "raw").glob("registry_*.jsonl"))
        else:
            n = count(p)
        print(f"  {label}: {n}")
    print(f"  harvest ledger: {led.count('harvest')} companies done")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("check", "registry", "hygiene", "join", "export", "status"):
        p = sub.add_parser(name)
        if name != "check":
            p.add_argument("--icp", required=True)
        p.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    return {"check": cmd_check, "registry": cmd_registry, "hygiene": cmd_hygiene,
            "join": cmd_join, "export": cmd_export, "status": cmd_status}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
