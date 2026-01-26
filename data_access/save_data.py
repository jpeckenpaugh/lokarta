import json
from typing import Any, Dict


class SaveData:
    def __init__(self, path: str):
        self._path = path

    def load(self) -> Dict[str, Any]:
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(data, dict):
            return {}
        data.setdefault("version", 1)
        data.setdefault("player", {})
        data.setdefault("quests", {})
        data.setdefault("flags", {})
        return data

    def save(self, data: Dict[str, Any]):
        payload = {
            "version": int(data.get("version", 1)),
            "player": data.get("player", {}),
            "quests": data.get("quests", {}),
            "flags": data.get("flags", {}),
        }
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def exists(self) -> bool:
        try:
            with open(self._path, "r", encoding="utf-8"):
                return True
        except OSError:
            return False

    def delete(self):
        try:
            import os
            os.remove(self._path)
        except OSError:
            pass
