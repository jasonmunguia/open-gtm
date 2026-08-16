"""Coverage ledger — which (stage, key) cells are already swept.

Two jobs:
1. Crash-resume: a rerun skips finished work instead of repeating it.
2. Honest exhaustion: "the mine is empty" is only a true statement if you can
   prove which cells were swept. Loop-until-dry stops on consecutive
   near-zero cells — without a ledger you can't tell an exhausted universe
   from a repeated search.

Resetting a stage is SAFE by design: downstream dedup is person-level, so a
rescan can only re-find, never duplicate. (This is what made "regex changed →
reset harvest_joined_lines to 0 and rescan" a routine move, not a migration.)
"""
import json
from pathlib import Path


class Ledger:
    def __init__(self, path):
        self.path = Path(path)
        self._d = json.loads(self.path.read_text()) if self.path.is_file() else {}

    def _cell(self, stage, key):
        return f"{stage}::{key}"

    def is_done(self, stage, key):
        return self._cell(stage, key) in self._d

    def mark_done(self, stage, key, meta=None):
        self._d[self._cell(stage, key)] = meta or True
        self._save()

    def reset_stage(self, stage):
        prefix = stage + "::"
        self._d = {k: v for k, v in self._d.items() if not k.startswith(prefix)}
        self._save()

    def count(self, stage):
        prefix = stage + "::"
        return sum(1 for k in self._d if k.startswith(prefix))

    def _save(self):
        self.path.write_text(json.dumps(self._d, indent=0))
