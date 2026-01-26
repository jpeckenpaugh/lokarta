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
