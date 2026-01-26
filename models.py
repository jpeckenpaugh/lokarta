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
