from __future__ import annotations

import random
from typing import Dict, List, Any

from persistence.rival_promotion_db import log_rival_world_event


PHILOSOPHY_MAP = {
    "sports_entertainment": "ratings_sensationalist",
    "pure_wrestling": "prestige_workrate",
    "hardcore": "shock_violence",
    "lucha": "athletic_showcase",
    "strong_style": "combat_authenticity",
    "mixed": "balanced",
}

STYLE_CHOICES = [
    "talent_raider",
    "relationship_builder",
    "youth_developer",
    "counter_programmer",
]


class CompetingPromotionAI:
    """Weekly simulation layer for rival promotions with persistent events."""

    def __init__(self, database, rival_manager):
        self.database = database
        self.rival_manager = rival_manager

    def initialize_metadata(self) -> None:
        for promo in self.rival_manager.get_all_promotions():
            if not getattr(promo, "booking_philosophy", None):
                promo.booking_philosophy = PHILOSOPHY_MAP.get(promo.brand_identity.value, "balanced")
            if not getattr(promo, "management_style", None):
                seed = sum(ord(c) for c in promo.promotion_id)
                promo.management_style = STYLE_CHOICES[seed % len(STYLE_CHOICES)]
            if getattr(promo, "cash_reserves", 0) <= 0:
                promo.cash_reserves = int(promo.budget_per_year * random.uniform(0.35, 0.8))
            if getattr(promo, "momentum", None) is None:
                promo.momentum = random.randint(45, 65)
            self.rival_manager.save_promotion(promo)

    def simulate_week(self, year: int, week: int, player_context: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        player_context = player_context or {}
        events: List[Dict[str, Any]] = []
        for promo in self.rival_manager.get_all_promotions():
            volatility = random.randint(-8, 11)
            if player_context.get("player_major_tournament"):
                volatility += 4 if promo.management_style == "counter_programmer" else 1
            if player_context.get("player_new_tv_deal"):
                volatility += 5 if promo.management_style in ("counter_programmer", "talent_raider") else 0

            promo.momentum = max(1, min(100, int(getattr(promo, "momentum", 50) + volatility)))
            purse_change = int((promo.prestige + promo.momentum - 100) * random.uniform(1800, 4000))
            promo.cash_reserves = max(0, int(getattr(promo, "cash_reserves", 0) + purse_change))

            event_type = "steady"
            if promo.momentum >= 75:
                event_type = "surge"
                headline = f"{promo.abbreviation} catches fire with a breakout cycle"
            elif promo.momentum <= 30:
                event_type = "slump"
                headline = f"{promo.abbreviation} enters a cold stretch amid creative criticism"
            else:
                reaction = "counter-books" if promo.management_style == "counter_programmer" else "doubles down"
                headline = f"{promo.abbreviation} {reaction} on its {promo.booking_philosophy.replace('_', ' ')} identity"

            details = (
                f"Momentum {promo.momentum}/100, reserves ${promo.cash_reserves:,}, "
                f"style={promo.management_style}, philosophy={promo.booking_philosophy}."
            )

            self.rival_manager.save_promotion(promo)
            log_rival_world_event(
                self.database,
                promo.promotion_id,
                event_type,
                headline,
                details,
                promo.momentum - 50,
                year,
                week,
            )
            events.append({
                "promotion_id": promo.promotion_id,
                "promotion_name": promo.name,
                "event_type": event_type,
                "headline": headline,
                "details": details,
                "momentum": promo.momentum,
                "cash_reserves": promo.cash_reserves,
            })
        return events
