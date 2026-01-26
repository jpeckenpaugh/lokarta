"""Load spell data from JSON."""

import json
from typing import Dict, Optional


class SpellsData:
    def __init__(self, path: str):
        self._path = path
        self._spells: Dict[str, dict] = {}
        self.load()

    def load(self):
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                self._spells = json.load(f)
        except (OSError, json.JSONDecodeError):
            self._spells = {}

    def all(self) -> Dict[str, dict]:
        return self._spells

    def get(self, key: str, default: Optional[dict] = None) -> dict:
        if default is None:
            default = {}
        return self._spells.get(key, default)
