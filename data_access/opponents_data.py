import json
import random
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

    def spawn(
        self,
        player_level: int,
        create_opponent
    ) -> List:
        if not self._opponents:
            return []
        candidates = list(self._opponents.values())
        total_level = 0
        spawned = []
        attempts = 0
        while len(spawned) < 3 and attempts < 10:
            attempts += 1
            remaining = max(1, player_level - total_level)
            choices = [
                m for m in candidates
                if int(m.get("level", 1)) <= remaining
            ]
            if not choices:
                break
            data = random.choice(choices)
            spawned.append(create_opponent(data))
            total_level += int(data.get("level", 1))
            if total_level >= player_level:
                break
        if not spawned:
            spawned.append(create_opponent(candidates[0]))
        return spawned
