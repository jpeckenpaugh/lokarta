import json
from typing import Dict, List, Optional


class OpponentsData:
    def __init__(self, path: str):
        self._path = path
        self._opponents: Dict[str, dict] = {}
        self.load()

    def load(self):
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                self._opponents = json.load(f)
        except (OSError, json.JSONDecodeError):
            self._opponents = {}

    def all(self) -> Dict[str, dict]:
        return self._opponents

    def get(self, key: str, default: Optional[dict] = None) -> dict:
        if default is None:
            default = {}
        return self._opponents.get(key, default)

    def list_descriptions(self) -> List[str]:
        lines = []
        for data in self._opponents.values():
            name = data.get("name", "Unknown")
            desc = data.get("desc", "")
            lines.append(f"{name}: {desc}")
        return lines
