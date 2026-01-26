from dataclasses import dataclass
from typing import List


@dataclass
class Frame:
    title: str
    body_lines: List[str]
    action_lines: List[str]
    stat_lines: List[str]
    footer_hint: str  # shows available keys
    location: str
    art_lines: List[str]
    art_color: str
    status_lines: List[str]


@dataclass
class Player:
    name: str
    level: int
    xp: int
    stat_points: int
    gold: int
    battle_speed: str
    hp: int
    max_hp: int
    mp: int
    max_mp: int
    atk: int
    defense: int
    location: str
    inventory: dict

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "level": self.level,
            "xp": self.xp,
            "stat_points": self.stat_points,
            "gold": self.gold,
            "battle_speed": self.battle_speed,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "mp": self.mp,
            "max_mp": self.max_mp,
            "atk": self.atk,
            "defense": self.defense,
            "location": self.location,
            "inventory": self.inventory,
        }

    @staticmethod
    def from_dict(data: dict) -> "Player":
        return Player(
            name=data.get("name", "WARRIOR"),
            level=int(data.get("level", 1)),
            xp=int(data.get("xp", 0)),
            stat_points=int(data.get("stat_points", 0)),
            gold=int(data.get("gold", 10)),
            battle_speed=data.get("battle_speed", "normal"),
            hp=int(data.get("hp", 10)),
            max_hp=int(data.get("max_hp", 10)),
            mp=int(data.get("mp", 10)),
            max_mp=int(data.get("max_mp", 10)),
            atk=int(data.get("atk", 10)),
            defense=int(data.get("defense", 10)),
            location="Town",
            inventory=data.get("inventory", {}),
        )

    def add_item(self, key: str, amount: int = 1):
        self.inventory[key] = int(self.inventory.get(key, 0)) + amount

    def format_inventory(self, items_data) -> str:
        if not self.inventory:
            return "Inventory is empty."
        parts = []
        for key, count in self.inventory.items():
            item = items_data.get(key, {"name": key})
            parts.append(f"{item.get('name', key)} x{count}")
        return "Inventory: " + ", ".join(parts)

    def list_inventory_items(self, items_data) -> List[tuple[str, str]]:
        entries = []
        for key in sorted(self.inventory.keys()):
            count = int(self.inventory.get(key, 0))
            if count <= 0:
                continue
            item = items_data.get(key, {"name": key})
            name = item.get("name", key)
            hp = int(item.get("hp", 0))
            mp = int(item.get("mp", 0))
            entries.append((key, f"{name} x{count} (+{hp} HP/+{mp} MP)"))
        return entries

    def use_item(self, key: str, items_data) -> str:
        item = items_data.get(key)
        if not item:
            return "That item is not available."
        if int(self.inventory.get(key, 0)) <= 0:
            return "You do not have that item."
        if self.hp == self.max_hp and self.mp == self.max_mp:
            return "HP and MP are already full."
        hp_gain = int(item.get("hp", 0))
        mp_gain = int(item.get("mp", 0))
        self.hp = min(self.max_hp, self.hp + hp_gain)
        self.mp = min(self.max_mp, self.mp + mp_gain)
        self.inventory[key] = int(self.inventory.get(key, 0)) - 1
        if self.inventory[key] <= 0:
            self.inventory.pop(key, None)
        return f"Used {item.get('name', key)}."


@dataclass
class Opponent:
    name: str
    level: int
    hp: int
    max_hp: int
    atk: int
    defense: int
    stunned_turns: int
    action_chance: float
    melted: bool
    art_lines: List[str]
    art_color: str
    arrival: str
