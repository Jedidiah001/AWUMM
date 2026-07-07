"""
Business logic for wrestler character systems.

This module keeps calculation rules out of Flask routes so the systems can be
tested directly and reused by booking, merchandise, and match simulation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, Tuple


TWEENER_MIN = 40
TWEENER_MAX = 60


GIMMICK_REQUIREMENTS: Dict[str, Dict[str, int]] = {
    "monster_heel": {"physical_presence": 85, "brawling": 75, "mic": 45},
    "underdog_babyface": {"speed": 65, "selling": 75, "charisma": 70},
    "cocky_champion": {"mic": 80, "psychology": 70, "charisma": 75},
    "mysterious_stranger": {"psychology": 75, "physical_presence": 65, "mic": 55},
    "comedy_act": {"mic": 70, "charisma": 80, "psychology": 55},
    "authority_figure": {"mic": 80, "charisma": 75, "psychology": 65},
    "technical_specialist": {"technical": 85, "psychology": 70, "stamina": 65},
    "high_flying_daredevil": {"speed": 85, "stamina": 70, "charisma": 60},
    "powerhouse": {"brawling": 80, "physical_presence": 80, "stamina": 60},
    "veteran_mentor": {"psychology": 85, "mic": 65, "technical": 60},
}


STYLE_CHEMISTRY: Dict[Tuple[str, str], int] = {
    ("technical", "technical"): 15,
    ("high_flyer", "high_flyer"): 10,
    ("technical", "brawler"): 5,
    ("powerhouse", "striker"): 5,
    ("hybrid", "technical"): 10,
    ("hybrid", "brawler"): 8,
    ("hybrid", "high_flyer"): 8,
    ("specialist", "specialist"): 6,
}


def clamp(value: int, minimum: int = 0, maximum: int = 100) -> int:
    return max(minimum, min(maximum, int(value)))


def alignment_label(percentage: int) -> str:
    percentage = clamp(percentage)
    if TWEENER_MIN <= percentage <= TWEENER_MAX:
        return "Tweener"
    return "Face" if percentage > TWEENER_MAX else "Heel"


def calculate_turn_impact(
    timing_score: int,
    build_score: int,
    surprise_factor: int,
) -> Dict[str, int]:
    timing = clamp(timing_score)
    build = clamp(build_score, 1, 10) * 10
    surprise = clamp(surprise_factor)
    impact = round((timing * 0.3) + (build * 0.4) + (surprise * 0.3))

    if impact >= 80:
        overness = 20
    elif impact >= 65:
        overness = 10
    elif impact >= 45:
        overness = 5
    elif impact >= 30:
        overness = -2
    else:
        overness = -10

    return {"impact_score": clamp(impact), "overness_change": overness}


def calculate_gimmick_effectiveness(wrestler: Dict, template_key: str) -> int:
    requirements = GIMMICK_REQUIREMENTS.get(template_key, {})
    if not requirements:
        return 60

    scores = []
    for stat, required in requirements.items():
        value = _wrestler_stat(wrestler, stat)
        scores.append(max(0, 100 - abs(required - value)))

    base = round(sum(scores) / len(scores))
    popularity_bonus = min(10, int(wrestler.get("popularity", 50)) // 10)
    return clamp(base + popularity_bonus)


def chemistry_modifier(style_a: str, style_b: str) -> int:
    a = (style_a or "").lower()
    b = (style_b or "").lower()
    if not a or not b:
        return 0
    return STYLE_CHEMISTRY.get((a, b), STYLE_CHEMISTRY.get((b, a), 0))


def calculate_finisher_protection(successful_pins: int, kickouts: int) -> int:
    total = max(0, successful_pins) + max(0, kickouts)
    if total == 0:
        return 100
    return clamp(round((max(0, successful_pins) / total) * 100))


def age_progression_delta(age: int, style: str = "") -> Dict[str, int]:
    if age <= 24:
        overall = 3
    elif age <= 30:
        overall = 2
    elif age <= 35:
        overall = 0
    elif age <= 40:
        overall = -1
    elif age <= 45:
        overall = -3
    else:
        overall = -5

    high_flyer_penalty = -1 if (style or "").lower() == "high_flyer" and age >= 36 else 0
    return {
        "brawling": overall,
        "technical": overall if age < 36 else max(overall, -1),
        "speed": overall + high_flyer_penalty,
        "mic": 1 if age >= 31 else 0,
        "psychology": 1 if age >= 31 else 0,
        "stamina": overall - (1 if age >= 36 else 0),
    }


def apply_attribute_delta(wrestler: Dict, deltas: Dict[str, int]) -> Dict[str, int]:
    return {
        key: clamp(int(wrestler.get(key, 50)) + delta)
        for key, delta in deltas.items()
    }


def default_gimmick_templates() -> Iterable[Dict]:
    for key, requirements in GIMMICK_REQUIREMENTS.items():
        yield {
            "template_key": key,
            "name": key.replace("_", " ").title(),
            "description": f"{key.replace('_', ' ').title()} character archetype.",
            "default_alignment": "Heel" if "heel" in key or key == "monster_heel" else "Face",
            "recommended_wrestling_style": _recommended_style(key),
            "base_popularity_modifier": 5 if key in {"cocky_champion", "monster_heel"} else 0,
            "attributes_json": requirements,
        }


def now_iso() -> str:
    return datetime.now().isoformat()


def _recommended_style(template_key: str) -> str:
    if "technical" in template_key:
        return "technical"
    if "high_flying" in template_key:
        return "high_flyer"
    if "powerhouse" in template_key or "monster" in template_key:
        return "powerhouse"
    return "hybrid"


def _wrestler_stat(wrestler: Dict, stat: str) -> int:
    aliases = {
        "charisma": "mic",
        "selling": "psychology",
        "physical_presence": "brawling",
    }
    return clamp(int(wrestler.get(stat) or wrestler.get(aliases.get(stat, stat), 50)))
