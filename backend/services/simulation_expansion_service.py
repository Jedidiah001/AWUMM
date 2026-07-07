"""Business logic for locker room, developmental, and advanced simulation."""

from __future__ import annotations

import random
from statistics import mean
from typing import Any

from repositories.phase_expansion_repository import new_id
from repositories.simulation_expansion_repository import SimulationExpansionRepository


class ValidationError(ValueError):
    pass


ATTRIBUTES = ["brawling", "technical", "speed", "mic", "psychology", "stamina"]

CURRICULUM_KEYS = {
    "in_ring_fundamentals",
    "athletic_conditioning",
    "character_promo",
    "match_psychology",
    "move_set",
    "tag_faction",
    "sports_entertainment",
}


DYNAMIC_EVENT_AUDIT = [
    ("match_injury_rebooking", "Injury during a match forces last-minute rebooking", "partial", ["injury routes", "match simulation", "title situation system"], "Existing injury mechanics did not create a persistent emergency rebooking event."),
    ("wrestler_no_show", "Wrestler no-shows due to contract disputes or personal issues", "partial", ["loyalty system", "contract promises", "morale system"], "Existing systems model risk but not persistent show-day no-show crises."),
    ("viral_social_moment", "Viral social media moment boosts or hurts popularity", "partial", ["media business", "controversy system", "free agent news"], "Existing social metrics lacked roster event generation and resolution."),
    ("backstage_fight", "Backstage fight creates real heat and booking opportunities", "partial", ["locker shoot incidents", "disciplinary actions", "relationships"], "Existing incidents lacked investigation and dynamic booking hooks."),
    ("show_cancellation", "Natural disasters or world events force show cancellations", "missing", ["attendance factors", "finance settlements"], "No persistent world-event cancellation workflow existed."),
    ("organic_alignment_turn", "Crowd reaction turns planned heel into babyface", "partial", ["character system", "crowd energy", "merch/social signals"], "Existing character tools did not detect organic crowd turns."),
    ("retirement_announcement", "Veteran announces retirement mid-storyline", "partial", ["aging system", "veteran trainer transition"], "Retirement exists as career state but not as a dynamic storyline event."),
    ("drug_test_failure", "Drug test failure triggers suspension storyline", "partial", ["wellness/controversy", "substance issues", "discipline"], "Existing wellness risk lacked random test failure event flow."),
    ("media_scandal", "Media scandal requires immediate storyline adjustments", "partial", ["controversy system", "finance sponsors", "network relationships"], "Scandals existed but not as dynamic schedule-disrupting events."),
    ("network_interference", "TV network demands programming changes", "partial", ["media business", "network demands"], "Network demand persistence existed, but not random interference decisions."),
    ("power_clique", "Power cliques form in the locker room", "exists", ["locker clique formation", "backstage influence"], "Core clique mechanics exist; dynamic events now surface major clique escalation."),
    ("veteran_refuses_putover", "Veteran refuses to put over younger talent", "partial", ["creative disagreements", "ego management"], "Existing disagreement system did not target put-over refusal moments."),
    ("group_demands", "Wrestlers form alliances and make group demands", "partial", ["cliques", "meetings", "morale"], "No collective demand event record existed."),
    ("title_ultimatum", "Star threatens to leave without a title", "partial", ["contract market", "creative disagreements", "championships"], "No ultimatum decision flow existed."),
    ("style_friction", "Friction between wrestling styles", "partial", ["character style chemistry", "developmental training"], "Style chemistry existed but not locker room philosophy conflict events."),
    ("storyline_leak", "Storylines leak to rumor sites", "missing", ["media business", "storylines"], "No leak investigation or kayfabe integrity event existed."),
]


EVENT_DEFINITIONS = {
    "match_injury_rebooking": {
        "category": "booking_crisis",
        "severity_levels": ("minor_kayfabe", "moderate", "serious", "career_threatening"),
        "options": [
            {"key": "emergency_rebook", "label": "Emergency rebook", "effects": {"momentum_delta": 2, "crowd_delta": -4}},
            {"key": "kayfabe_injury_angle", "label": "Turn it into a storyline injury", "effects": {"popularity_delta": 2, "morale_delta": 1}},
            {"key": "vacate_title_tournament", "label": "Vacate title and create tournament", "effects": {"momentum_delta": -2, "legacy_delta": 3}},
        ],
    },
    "wrestler_no_show": {
        "category": "contract_crisis",
        "severity_levels": ("personal_issue", "contract_dispute", "deliberate_ghosting"),
        "options": [
            {"key": "private_support", "label": "Handle privately with support", "effects": {"morale_delta": 4, "trust_delta": 2}},
            {"key": "public_discipline", "label": "Public discipline", "effects": {"morale_delta": -8, "professionalism_delta": 2}},
            {"key": "reconcile_terms", "label": "Renegotiate and reconcile", "effects": {"morale_delta": 3, "finance_delta": -15000}},
        ],
    },
    "viral_social_moment": {
        "category": "media",
        "severity_levels": ("positive_breakout", "unexpected_hero", "negative_botch", "unscripted_controversy"),
        "options": [
            {"key": "amplify", "label": "Amplify the moment", "effects": {"popularity_delta": 5, "momentum_delta": 6, "finance_delta": -6000}},
            {"key": "protect_talent", "label": "Protect talent and control narrative", "effects": {"morale_delta": 3, "popularity_delta": 1}},
            {"key": "crisis_pr", "label": "Activate crisis PR", "effects": {"network_delta": 2, "sponsor_delta": 2, "finance_delta": -12000}},
        ],
    },
    "backstage_fight": {
        "category": "locker_room",
        "severity_levels": ("heated_argument", "physical_fight", "serious_altercation"),
        "options": [
            {"key": "investigate", "label": "Formal investigation", "effects": {"trust_delta": 2, "morale_delta": -1}},
            {"key": "mediate", "label": "Conflict mediation", "effects": {"morale_delta": 2, "atmosphere_delta": 2}},
            {"key": "suspend_aggressor", "label": "Suspend aggressor", "effects": {"morale_delta": -5, "professionalism_delta": 2}},
        ],
    },
    "show_cancellation": {
        "category": "operations",
        "severity_levels": ("local_disruption", "venue_unavailable", "regional_crisis"),
        "options": [
            {"key": "reschedule_same_city", "label": "Reschedule same city", "effects": {"finance_delta": -25000, "local_reputation_delta": 2}},
            {"key": "remote_special", "label": "Produce remote special content", "effects": {"finance_delta": -12000, "popularity_delta": 1}},
            {"key": "cancel_refund", "label": "Cancel and refund", "effects": {"finance_delta": -50000, "trust_delta": 1}},
        ],
    },
    "organic_alignment_turn": {
        "category": "creative",
        "severity_levels": ("early_signal", "clear_shift", "crowd_rejection_crisis"),
        "options": [
            {"key": "embrace_turn", "label": "Embrace the organic turn", "effects": {"popularity_delta": 5, "momentum_delta": 5}},
            {"key": "fight_turn", "label": "Fight the crowd reaction", "effects": {"popularity_delta": -3, "morale_delta": -2}},
            {"key": "slow_burn", "label": "Slow-burn acknowledgment", "effects": {"popularity_delta": 3, "momentum_delta": 2}},
        ],
    },
    "retirement_announcement": {
        "category": "career",
        "severity_levels": ("private_notice", "surprise_public", "health_forced"),
        "options": [
            {"key": "farewell_arc", "label": "Plan farewell arc", "effects": {"popularity_delta": 3, "legacy_delta": 5}},
            {"key": "trainer_transition", "label": "Transition to trainer role", "effects": {"development_delta": 3, "morale_delta": 2}},
            {"key": "immediate_writeoff", "label": "Immediate write-off", "effects": {"morale_delta": -3, "momentum_delta": -4}},
        ],
    },
    "drug_test_failure": {
        "category": "wellness",
        "severity_levels": ("policy_warning", "suspension", "rehab_required"),
        "options": [
            {"key": "support_rehab", "label": "Support rehab pathway", "effects": {"morale_delta": 2, "finance_delta": -18000}},
            {"key": "suspend", "label": "Suspend under wellness policy", "effects": {"morale_delta": -8, "professionalism_delta": 2}},
            {"key": "private_testing_plan", "label": "Private testing plan", "effects": {"trust_delta": 1, "sponsor_delta": -1}},
        ],
    },
    "media_scandal": {
        "category": "media_crisis",
        "severity_levels": ("social_backlash", "legal_issue", "major_allegation"),
        "options": [
            {"key": "transparent_response", "label": "Transparent response", "effects": {"network_delta": 2, "sponsor_delta": 1, "finance_delta": -10000}},
            {"key": "suspend_pending_investigation", "label": "Suspend pending investigation", "effects": {"morale_delta": -4, "sponsor_delta": 2}},
            {"key": "no_comment", "label": "No comment", "effects": {"network_delta": -3, "sponsor_delta": -3}},
        ],
    },
    "network_interference": {
        "category": "business_pressure",
        "severity_levels": ("note", "formal_demand", "contract_threat"),
        "options": [
            {"key": "comply", "label": "Comply with network demand", "effects": {"network_delta": 4, "morale_delta": -2}},
            {"key": "negotiate", "label": "Negotiate compromise", "effects": {"network_delta": 2, "finance_delta": -5000}},
            {"key": "push_back", "label": "Push back creatively", "effects": {"network_delta": -4, "morale_delta": 2}},
        ],
    },
    "power_clique": {
        "category": "locker_room",
        "severity_levels": ("minor_bloc", "power_center", "existential_threat"),
        "options": [
            {"key": "engage_leadership", "label": "Meet clique leadership", "effects": {"trust_delta": 2, "atmosphere_delta": 1}},
            {"key": "divide_and_address", "label": "Address individual grievances", "effects": {"morale_delta": 1, "atmosphere_delta": -1}},
            {"key": "restructure_environment", "label": "Restructure travel/training environment", "effects": {"finance_delta": -8000, "atmosphere_delta": 2}},
        ],
    },
    "veteran_refuses_putover": {
        "category": "creative",
        "severity_levels": ("negotiated_resistance", "subtle_sabotage", "outright_refusal"),
        "options": [
            {"key": "force_issue", "label": "Force the issue", "effects": {"morale_delta": -8, "professionalism_delta": 2}},
            {"key": "creative_workaround", "label": "Creative workaround", "effects": {"momentum_delta": -1, "trust_delta": 1}},
            {"key": "retirement_package", "label": "Offer retirement package", "effects": {"finance_delta": -30000, "legacy_delta": 4}},
        ],
    },
    "group_demands": {
        "category": "labor_pressure",
        "severity_levels": ("informal_request", "collective_demand", "union_drive"),
        "options": [
            {"key": "formal_negotiation", "label": "Formal negotiation", "effects": {"trust_delta": 3, "finance_delta": -25000}},
            {"key": "selective_concessions", "label": "Selective concessions", "effects": {"morale_delta": 1, "atmosphere_delta": -2}},
            {"key": "firm_boundary", "label": "Firm boundary", "effects": {"morale_delta": -5, "professionalism_delta": 1}},
        ],
    },
    "title_ultimatum": {
        "category": "contract_crisis",
        "severity_levels": ("implied", "agent_ultimatum", "walkout_threat"),
        "options": [
            {"key": "grant_title_plan", "label": "Grant title plan", "effects": {"morale_delta": 4, "trust_delta": -2}},
            {"key": "creative_compromise", "label": "Creative compromise", "effects": {"morale_delta": 2, "momentum_delta": 2}},
            {"key": "call_bluff", "label": "Call the bluff", "effects": {"morale_delta": -7, "trust_delta": 2}},
        ],
    },
    "style_friction": {
        "category": "locker_room",
        "severity_levels": ("philosophy_dispute", "training_conflict", "match_safety_concern"),
        "options": [
            {"key": "cross_style_workshop", "label": "Cross-style workshop", "effects": {"atmosphere_delta": 2, "development_delta": 2, "finance_delta": -5000}},
            {"key": "style_divisions", "label": "Create style-specific showcases", "effects": {"popularity_delta": 2, "momentum_delta": 1}},
            {"key": "ignore", "label": "Ignore as normal tension", "effects": {"atmosphere_delta": -3}},
        ],
    },
    "storyline_leak": {
        "category": "media_security",
        "severity_levels": ("rumor", "confirmed_spoiler", "source_compromised"),
        "options": [
            {"key": "investigate_leak", "label": "Investigate leak trail", "effects": {"finance_delta": -7000, "trust_delta": 1}},
            {"key": "change_finish", "label": "Change the creative finish", "effects": {"momentum_delta": -1, "kayfabe_delta": 2}},
            {"key": "plant_false_info", "label": "Plant false information", "effects": {"kayfabe_delta": 3, "trust_delta": -1}},
        ],
    },
}


class SimulationExpansionService:
    def __init__(self, database):
        self.database = database
        self.repo = SimulationExpansionRepository(database)

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def clamp(self, value: float, low: float = 0.0, high: float = 100.0) -> float:
        return max(low, min(high, float(value)))

    def _rng(self, seed: int | None, *tokens: Any) -> random.Random:
        base = int(seed if seed is not None else 0)
        for token in tokens:
            base += sum(ord(ch) for ch in str(token))
        return random.Random(base)

    def _state_week(self, data: dict | None = None) -> tuple[int, int]:
        data = data or {}
        if "year" in data and "week" in data:
            return int(data["year"]), int(data["week"])
        state = self.database.get_game_state() if hasattr(self.database, "get_game_state") else {}
        return int(state.get("current_year", 1)), int(state.get("current_week", 1))

    def _overall(self, wrestler: dict) -> float:
        return sum(float(wrestler.get(key, 50) or 50) for key in ATTRIBUTES) / len(ATTRIBUTES)

    def _level(self, score: float, scale: str) -> str:
        score = float(score)
        if scale == "morale":
            if score <= 15:
                return "deeply_unhappy"
            if score <= 30:
                return "dissatisfied"
            if score <= 50:
                return "neutral"
            if score <= 70:
                return "satisfied"
            if score <= 85:
                return "happy"
            return "elated"
        if scale == "atmosphere":
            if score <= 20:
                return "catastrophically_toxic"
            if score <= 40:
                return "troubled"
            if score <= 60:
                return "professional"
            if score <= 75:
                return "positive"
            if score <= 90:
                return "excellent"
            return "legendary"
        if scale == "ego":
            if score <= 20:
                return "humble"
            if score <= 40:
                return "confident"
            if score <= 60:
                return "noticeable"
            if score <= 80:
                return "significant"
            return "out_of_control"
        return "average"

    def _performance_modifier(self, morale: float, atmosphere: float = 50) -> float:
        morale_mod = 0.0
        if morale > 70:
            morale_mod += min(0.12, (morale - 70) / 250)
        elif morale < 30:
            morale_mod -= min(0.16, (30 - morale) / 180)
        if atmosphere > 60:
            morale_mod += min(0.06, (atmosphere - 60) / 500)
        elif atmosphere < 40:
            morale_mod -= min(0.08, (40 - atmosphere) / 350)
        return round(morale_mod, 4)

    def _market_value(self, wrestler: dict, champion_ids: set[str]) -> float:
        overall = self._overall(wrestler)
        overness = float(wrestler.get("popularity", 50) or 50)
        champion_bonus = 1.22 if wrestler["id"] in champion_ids else 1.0
        major_bonus = 1.15 if int(wrestler.get("is_major_superstar", 0) or 0) else 1.0
        return (35000 + (overall * 1150) + (overness * 950)) * champion_bonus * major_bonus

    def _champion_ids(self) -> set[str]:
        rows = self.repo.fetch_all("SELECT current_holder_id FROM championships WHERE current_holder_id IS NOT NULL")
        return {row["current_holder_id"] for row in rows if row.get("current_holder_id")}

    def _recent_match_counts(self, wrestler_id: str, year: int, week: int, window: int = 6) -> dict:
        current = (year * 52) + week
        rows = self.repo.fetch_all(
            """
            SELECT year, week, winner, side_a_ids, side_b_ids, is_title_match, star_rating
            FROM match_history
            WHERE (side_a_ids LIKE ? OR side_b_ids LIKE ?)
            ORDER BY year DESC, week DESC
            LIMIT 25
            """,
            (f"%{wrestler_id}%", f"%{wrestler_id}%"),
        )
        recent = []
        for row in rows:
            if 0 <= current - ((int(row["year"]) * 52) + int(row["week"])) <= window:
                recent.append(row)
        wins = 0
        losses = 0
        title_matches = 0
        quality = []
        for row in recent:
            side_a = self.repo.from_json(row.get("side_a_ids"), [])
            side_b = self.repo.from_json(row.get("side_b_ids"), [])
            winner = row.get("winner")
            if row.get("is_title_match"):
                title_matches += 1
            quality.append(float(row.get("star_rating", 3) or 3) * 20)
            if wrestler_id in side_a:
                wins += 1 if winner == "side_a" else 0
                losses += 1 if winner == "side_b" else 0
            if wrestler_id in side_b:
                wins += 1 if winner == "side_b" else 0
                losses += 1 if winner == "side_a" else 0
        return {
            "matches": len(recent),
            "wins": wins,
            "losses": losses,
            "title_matches": title_matches,
            "avg_quality": sum(quality) / len(quality) if quality else 50,
        }

    def _ensure_locker_states(self) -> list[dict]:
        wrestlers = self.repo.get_wrestlers()
        now = self.repo.now()
        states = []
        for wrestler in wrestlers:
            existing = self.repo.get_locker_state(wrestler["id"])
            if existing:
                states.append(existing)
                continue
            overall = self._overall(wrestler)
            preferences = self._default_preferences(wrestler)
            state = self.repo.upsert_locker_state(
                {
                    "wrestler_id": wrestler["id"],
                    "wrestler_name": wrestler["name"],
                    "brand": wrestler.get("primary_brand") or "ROC Alpha",
                    "roster_designation": "developmental_roster" if wrestler.get("primary_brand") == "ROC Vanguard" else "main_roster",
                    "morale_score": float(wrestler.get("morale", 50) or 50),
                    "morale_level": self._level(float(wrestler.get("morale", 50) or 50), "morale"),
                    "ego_level": self.clamp(20 + (overall - 50) * 0.35 + float(wrestler.get("popularity", 50)) * 0.15),
                    "professionalism": self.clamp(55 + float(wrestler.get("years_experience", 5) or 5) * 1.6 - float(wrestler.get("fatigue", 0) or 0) * 0.15),
                    "backstage_influence": self.clamp(10 + float(wrestler.get("years_experience", 5) or 5) * 2 + float(wrestler.get("popularity", 50) or 50) * 0.35),
                    "management_relationship": 50,
                    "creative_preferences_json": preferences,
                    "last_primary_factors_json": {},
                    "performance_modifier": 0,
                    "release_request_risk": 0,
                    "refusal_risk": 0,
                    "incident_risk": 0,
                    "updated_at": now,
                    "deleted_at": None,
                }
            )
            states.append(state)
        return states

    def _default_preferences(self, wrestler: dict) -> dict:
        overall = self._overall(wrestler)
        mic = float(wrestler.get("mic", 50) or 50)
        brawling = float(wrestler.get("brawling", 50) or 50)
        speed = float(wrestler.get("speed", 50) or 50)
        stamina = float(wrestler.get("stamina", 50) or 50)
        if overall >= 78 or int(wrestler.get("is_major_superstar", 0) or 0):
            preferred = "championship_competition"
        elif mic >= max(brawling, speed):
            preferred = "character_storyline"
        elif brawling >= 70:
            preferred = "physical_intensity"
        elif speed >= 70:
            preferred = "athletic_showcase"
        else:
            preferred = "steady_growth"
        return {
            "primary": preferred,
            "accepts_comedy": mic >= 65,
            "needs_protection": overall >= 82,
            "preferred_intensity": "high" if brawling + stamina >= 140 else "medium",
        }

    # ------------------------------------------------------------------
    # Locker room culture
    # ------------------------------------------------------------------

    def run_weekly_culture(self, year: int, week: int, seed: int | None = None) -> dict:
        existing = self.repo.get_job("weekly_locker_room_culture", year, week)
        if existing and existing["status"] == "completed":
            return {"already_ran": True, **(existing.get("result_json") or {})}

        rng = self._rng(seed, year, week, "culture")
        self._ensure_locker_states()
        champion_ids = self._champion_ids()
        wrestlers = {row["id"]: row for row in self.repo.get_wrestlers()}
        previous_states = {row["wrestler_id"]: row for row in self.repo.list_locker_states()}
        updated_states = []
        disagreement_count = 0
        bullying_count = 0
        substance_count = 0
        shoot_count = 0

        with self.repo.transaction():
            for wrestler_id, state in previous_states.items():
                wrestler = wrestlers.get(wrestler_id)
                if not wrestler:
                    continue
                match = self._recent_match_counts(wrestler_id, year, week)
                overall = self._overall(wrestler)
                market_value = self._market_value(wrestler, champion_ids)
                salary = float(wrestler.get("contract_salary", 0) or 0)
                pay_ratio = salary / max(1.0, market_value)
                booking_score = self.clamp(50 + (match["wins"] - match["losses"]) * 6 + match["title_matches"] * 7 + (match["matches"] - 1) * 2)
                if overall >= 80 and match["losses"] > match["wins"]:
                    booking_score -= 16
                pay_score = self.clamp(35 + pay_ratio * 45)
                contract_weeks = int(wrestler.get("contract_weeks_remaining", 52) or 52)
                contract_security = self.clamp(35 + min(65, contract_weeks * 1.25))
                creative_score = self._creative_satisfaction(state, match)
                injury_score = 35 if wrestler.get("injury_severity") and wrestler.get("injury_severity") != "None" else 55
                discipline_penalty = self._recent_discipline_penalty(wrestler_id, year, week)
                peer_score = self.clamp(50 + float(state.get("management_relationship", 50)) * 0.10)
                target = (
                    booking_score * 0.26
                    + pay_score * 0.18
                    + contract_security * 0.10
                    + creative_score * 0.18
                    + injury_score * 0.10
                    + peer_score * 0.10
                    + match["avg_quality"] * 0.08
                    - discipline_penalty
                )
                morale = self.clamp(float(state["morale_score"]) * 0.68 + target * 0.32 + rng.uniform(-2.2, 2.2))
                ego_delta = self._ego_delta(wrestler, state, match, champion_ids)
                ego = self.clamp(float(state["ego_level"]) + ego_delta)
                professionalism = self.clamp(float(state["professionalism"]) + self._professionalism_delta(state, morale, discipline_penalty, rng))
                influence = self._calculate_influence(wrestler, state, champion_ids)
                risks = {
                    "release_request": round(max(0, (30 - morale) / 100) + max(0, (pay_score < 40) * 0.04), 4),
                    "creative_refusal": round(max(0, (ego - 55) / 210) + max(0, (35 - morale) / 260), 4),
                    "backstage_incident": round(max(0, (35 - professionalism) / 180) + max(0, (25 - morale) / 220), 4),
                }
                performance_modifier = self._performance_modifier(morale)
                factors = {
                    "booking_satisfaction": round(booking_score, 2),
                    "pay_satisfaction": round(pay_score, 2),
                    "contract_security": round(contract_security, 2),
                    "creative_satisfaction": round(creative_score, 2),
                    "injury_pressure": round(injury_score, 2),
                    "discipline_penalty": round(discipline_penalty, 2),
                    "recent_match_summary": match,
                }
                next_state = {
                    **state,
                    "morale_score": round(morale, 2),
                    "morale_level": self._level(morale, "morale"),
                    "ego_level": round(ego, 2),
                    "professionalism": round(professionalism, 2),
                    "backstage_influence": round(influence, 2),
                    "last_primary_factors_json": factors,
                    "performance_modifier": performance_modifier,
                    "release_request_risk": risks["release_request"],
                    "refusal_risk": risks["creative_refusal"],
                    "incident_risk": risks["backstage_incident"],
                }
                self.repo.upsert_locker_state(next_state, commit=False)
                self.repo.insert_simple(
                    "locker_morale_history",
                    {
                        "id": f"morale_{wrestler_id}_{year}_{week}",
                        "wrestler_id": wrestler_id,
                        "wrestler_name": state["wrestler_name"],
                        "brand": next_state["brand"],
                        "year": year,
                        "week": week,
                        "morale_score": round(morale, 2),
                        "morale_level": next_state["morale_level"],
                        "factors_json": factors,
                        "performance_modifier": performance_modifier,
                        "event_risks_json": risks,
                    },
                    commit=False,
                )
                self.repo.insert_simple(
                    "locker_backstage_influence_history",
                    {
                        "id": f"influence_{wrestler_id}_{year}_{week}",
                        "wrestler_id": wrestler_id,
                        "wrestler_name": state["wrestler_name"],
                        "influence_score": round(influence, 2),
                        "factors_json": {
                            "tenure": wrestler.get("years_experience", 0),
                            "overness": wrestler.get("popularity", 50),
                            "ego": ego,
                            "clique_size": self._clique_size(wrestler_id),
                        },
                        "year": year,
                        "week": week,
                    },
                    commit=False,
                )
                if self._should_create_disagreement(next_state, creative_score, rng):
                    self._insert_creative_disagreement(next_state, creative_score, year, week, commit=False)
                    disagreement_count += 1
                if self._should_create_substance_issue(wrestler, next_state, rng):
                    self._insert_substance_issue(wrestler, next_state, year, week, rng, commit=False)
                    substance_count += 1
                updated_states.append(next_state)

            cliques = self._evaluate_cliques(updated_states, year, week, commit=False)
            atmosphere = self._calculate_and_store_atmosphere(updated_states, cliques, year, week, commit=False)
            bullying_count += self._maybe_bullying_incidents(updated_states, cliques, atmosphere, year, week, rng, commit=False)
            shoot_count += self._maybe_shoot_incident(updated_states, atmosphere, year, week, rng, commit=False)

        result = {
            "updated_wrestlers": len(updated_states),
            "brands": atmosphere,
            "creative_disagreements": disagreement_count,
            "cliques": len(cliques),
            "bullying_incidents": bullying_count,
            "substance_issues": substance_count,
            "shoot_incidents": shoot_count,
        }
        self.repo.upsert_job(
            {
                "job_type": "weekly_locker_room_culture",
                "year": year,
                "week": week,
                "status": "completed",
                "seed": seed,
                "reads": ["wrestlers", "match_history", "championships", "locker_wrestler_state"],
                "writes": ["locker_wrestler_state", "locker_morale_history", "locker_atmosphere_snapshots"],
                "result": result,
            }
        )
        return {"already_ran": False, **result}

    def _creative_satisfaction(self, state: dict, match: dict) -> float:
        prefs = state.get("creative_preferences_json") or {}
        primary = prefs.get("primary", "steady_growth")
        score = 50
        if primary == "championship_competition":
            score += match["title_matches"] * 14 + (match["wins"] - match["losses"]) * 5
            if match["matches"] == 0:
                score -= 10
        elif primary == "character_storyline":
            promos = self.repo.fetch_one(
                """
                SELECT COUNT(*) AS total FROM promo_segments
                WHERE speaker_id = ? AND deleted_at IS NULL
                """,
                (state["wrestler_id"],),
            )
            score += min(18, int(promos["total"]) * 2 if promos else 0)
        elif primary == "physical_intensity":
            score += match["matches"] * 5 + max(0, match["avg_quality"] - 55) * 0.25
        elif primary == "athletic_showcase":
            score += match["matches"] * 4 + max(0, match["avg_quality"] - 60) * 0.30
        else:
            score += match["matches"] * 3
        return self.clamp(score)

    def _ego_delta(self, wrestler: dict, state: dict, match: dict, champion_ids: set[str]) -> float:
        delta = 0.0
        if wrestler["id"] in champion_ids:
            delta += 1.4
        if int(wrestler.get("is_major_superstar", 0) or 0):
            delta += 0.5
        if match["wins"] > match["losses"]:
            delta += 0.4 * (match["wins"] - match["losses"])
        if match["losses"] > match["wins"]:
            delta -= 0.5 * (match["losses"] - match["wins"])
        if float(state.get("morale_score", 50)) < 30:
            delta += 0.3
        return delta

    def _professionalism_delta(self, state: dict, morale: float, discipline_penalty: float, rng: random.Random) -> float:
        delta = rng.uniform(-0.7, 0.9)
        if morale > 65:
            delta += 0.3
        if morale < 30:
            delta -= 0.6
        if discipline_penalty:
            delta -= 0.4
        return delta

    def _calculate_influence(self, wrestler: dict, state: dict, champion_ids: set[str]) -> float:
        tenure = float(wrestler.get("years_experience", 0) or 0)
        overness = float(wrestler.get("popularity", 50) or 50)
        age = float(wrestler.get("age", 30) or 30)
        champion = 10 if wrestler["id"] in champion_ids else 0
        clique_size = self._clique_size(wrestler["id"])
        return self.clamp(8 + tenure * 2.0 + overness * 0.35 + max(0, age - 30) * 0.6 + champion + clique_size * 4 + float(state.get("ego_level", 30)) * 0.08)

    def _recent_discipline_penalty(self, wrestler_id: str, year: int, week: int) -> float:
        current = year * 52 + week
        rows = self.repo.fetch_all(
            """
            SELECT year, week, morale_impact
            FROM locker_disciplinary_actions
            WHERE wrestler_id = ? AND deleted_at IS NULL
            """,
            (wrestler_id,),
        )
        return sum(abs(float(row["morale_impact"])) * 0.5 for row in rows if 0 <= current - (row["year"] * 52 + row["week"]) <= 8)

    def _clique_size(self, wrestler_id: str) -> int:
        row = self.repo.fetch_one(
            """
            SELECT COUNT(*) AS total FROM locker_clique_members
            WHERE wrestler_id = ? AND deleted_at IS NULL
            """,
            (wrestler_id,),
        )
        return int(row["total"]) if row else 0

    def _should_create_disagreement(self, state: dict, creative_score: float, rng: random.Random) -> bool:
        probability = max(0, (45 - creative_score) / 160) + max(0, (float(state["ego_level"]) - 60) / 260) + max(0, (35 - float(state["morale_score"])) / 220)
        return rng.random() < probability

    def _insert_creative_disagreement(self, state: dict, creative_score: float, year: int, week: int, commit: bool = True) -> dict:
        ego = float(state["ego_level"])
        morale = float(state["morale_score"])
        influence = float(state["backstage_influence"])
        severity = self.clamp((50 - creative_score) + max(0, ego - 45) * 0.5 + max(0, 45 - morale) * 0.35 + influence * 0.08)
        if severity >= 75:
            level = "complete_refusal"
        elif severity >= 60:
            level = "public_dissatisfaction"
        elif severity >= 45:
            level = "direct_communication"
        elif severity >= 30:
            level = "quiet_resistance"
        else:
            level = "private_discomfort"
        return self.repo.insert_simple(
            "locker_creative_disagreements",
            {
                "id": new_id("creative_disagreement"),
                "wrestler_id": state["wrestler_id"],
                "wrestler_name": state["wrestler_name"],
                "booking_object_ref": "weekly_direction",
                "direction_summary": "Current booking direction conflicts with stored creative preferences.",
                "preference_conflict_score": round(severity, 2),
                "escalation_level": level,
                "status": "open",
                "morale_impact": round(-severity / 12, 2),
                "ego_impact": round(severity / 30, 2),
                "atmosphere_impact": round(-severity / 40, 2),
                "aftermath_json": {"creative_score": creative_score, "state_morale": morale, "state_ego": ego},
                "year": year,
                "week": week,
                "updated_at": self.repo.now(),
            },
            commit=commit,
        )

    def _should_create_substance_issue(self, wrestler: dict, state: dict, rng: random.Random) -> bool:
        active = self.repo.fetch_one(
            """
            SELECT id FROM locker_substance_issues
            WHERE wrestler_id = ? AND status IN ('hidden', 'visible', 'rehab', 'recovery') AND deleted_at IS NULL
            """,
            (state["wrestler_id"],),
        )
        if active:
            return False
        injury = 0.035 if wrestler.get("injury_severity") and wrestler.get("injury_severity") != "None" else 0
        pressure = max(0, (35 - float(state["morale_score"])) / 900)
        fatigue = max(0, float(wrestler.get("fatigue", 0) or 0) / 2200)
        return rng.random() < injury + pressure + fatigue

    def _insert_substance_issue(self, wrestler: dict, state: dict, year: int, week: int, rng: random.Random, commit: bool = True) -> dict:
        severity = self.clamp(25 + max(0, 45 - float(state["morale_score"])) * 0.7 + rng.uniform(0, 20))
        return self.repo.insert_simple(
            "locker_substance_issues",
            {
                "id": new_id("substance"),
                "wrestler_id": state["wrestler_id"],
                "wrestler_name": state["wrestler_name"],
                "status": "hidden",
                "severity": round(severity, 2),
                "visible_signs_json": [],
                "recovery_progress": 0,
                "relapse_risk": round(severity / 140, 4),
                "history_json": [{"year": year, "week": week, "event": "risk pattern detected privately by simulation"}],
                "created_year": year,
                "created_week": week,
                "updated_at": self.repo.now(),
            },
            commit=commit,
        )

    def _evaluate_cliques(self, states: list[dict], year: int, week: int, commit: bool = True) -> list[dict]:
        by_brand: dict[str, list[dict]] = {}
        for state in states:
            by_brand.setdefault(state["brand"], []).append(state)
        created = []
        for brand, rows in by_brand.items():
            high_influence = [row for row in rows if float(row["backstage_influence"]) >= 58]
            if len(high_influence) < 2:
                continue
            high_influence.sort(key=lambda row: row["backstage_influence"], reverse=True)
            members = high_influence[: min(5, len(high_influence))]
            leader = members[0]
            avg_morale = sum(float(row["morale_score"]) for row in members) / len(members)
            solidarity = self.clamp(45 + len(members) * 5 + (avg_morale - 50) * 0.25)
            if avg_morale >= 65:
                behavior = "supportive"
            elif avg_morale <= 28:
                behavior = "predatory"
            elif avg_morale <= 42:
                behavior = "territorial"
            elif max(float(row["ego_level"]) for row in members) >= 70:
                behavior = "competitive"
            else:
                behavior = "neutral"
            clique_id = f"clique_{brand.lower().replace(' ', '_')}_{year}_{week}"
            self.repo.insert_simple(
                "locker_cliques",
                {
                    "id": clique_id,
                    "clique_name": f"{brand} power circle",
                    "brand": brand,
                    "leader_wrestler_id": leader["wrestler_id"],
                    "leader_wrestler_name": leader["wrestler_name"],
                    "solidarity": round(solidarity, 2),
                    "behavior_classification": behavior,
                    "political_power": round(sum(float(row["backstage_influence"]) for row in members) / len(members), 2),
                    "health_notes": f"Generated from affinity/influence evaluation for Y{year} W{week}.",
                    "updated_at": self.repo.now(),
                },
                commit=False,
            )
            for member in members:
                self.repo.insert_simple(
                    "locker_clique_members",
                    {
                        "id": f"{clique_id}_{member['wrestler_id']}",
                        "clique_id": clique_id,
                        "wrestler_id": member["wrestler_id"],
                        "wrestler_name": member["wrestler_name"],
                        "affinity_score": round(self.clamp(45 + member["backstage_influence"] * 0.35 + avg_morale * 0.25), 2),
                        "role": "leader" if member["wrestler_id"] == leader["wrestler_id"] else "member",
                        "joined_year": year,
                        "joined_week": week,
                    },
                    commit=False,
                )
            created.append({"id": clique_id, "brand": brand, "members": members, "behavior_classification": behavior, "solidarity": solidarity})
        if commit:
            self.repo.conn.commit()
        return created

    def _calculate_and_store_atmosphere(self, states: list[dict], cliques: list[dict], year: int, week: int, commit: bool = True) -> list[dict]:
        results = []
        brands = sorted({state["brand"] for state in states})
        for brand in brands:
            rows = [state for state in states if state["brand"] == brand]
            if not rows:
                continue
            avg_morale = sum(float(row["morale_score"]) for row in rows) / len(rows)
            low_drag = len([row for row in rows if float(row["morale_score"]) <= 25]) * 4.5
            veteran_anchor = sum(2.0 for row in rows if float(row["backstage_influence"]) >= 65 and float(row["morale_score"]) >= 70)
            brand_cliques = [clique for clique in cliques if clique["brand"] == brand]
            clique_penalty = sum(8 if c["behavior_classification"] == "predatory" else 5 if c["behavior_classification"] == "territorial" else 0 for c in brand_cliques)
            clique_bonus = sum(3 for c in brand_cliques if c["behavior_classification"] == "supportive")
            unresolved = self.repo.fetch_one(
                """
                SELECT COUNT(*) AS total FROM locker_creative_disagreements
                WHERE status = 'open' AND year >= ? AND deleted_at IS NULL
                """,
                (max(1, year - 1),),
            )
            score = self.clamp(avg_morale - low_drag + veteran_anchor + clique_bonus - clique_penalty - int(unresolved["total"]) * 0.5)
            result = {
                "id": f"atmosphere_{brand.lower().replace(' ', '_')}_{year}_{week}",
                "brand": brand,
                "year": year,
                "week": week,
                "atmosphere_score": round(score, 2),
                "atmosphere_level": self._level(score, "atmosphere"),
                "average_morale": round(avg_morale, 2),
                "match_quality_modifier": round((score - 50) / 300, 4),
                "developmental_modifier": round((score - 50) / 400, 4),
                "media_risk_modifier": round(max(0, (45 - score) / 120), 4),
                "recruitment_modifier": round((score - 50) / 250, 4),
                "inputs_json": {
                    "low_morale_drag": low_drag,
                    "veteran_anchor": veteran_anchor,
                    "clique_penalty": clique_penalty,
                    "clique_bonus": clique_bonus,
                    "unresolved_disagreements": int(unresolved["total"]) if unresolved else 0,
                },
            }
            self.repo.insert_simple("locker_atmosphere_snapshots", result, commit=False)
            self.repo.conn.execute(
                "UPDATE brand_entities SET atmosphere_score = ?, updated_at = ? WHERE brand_name = ?",
                (round(score, 2), self.repo.now(), brand),
            )
            results.append(result)
        if commit:
            self.repo.conn.commit()
        return results

    def _maybe_bullying_incidents(self, states: list[dict], cliques: list[dict], atmosphere: list[dict], year: int, week: int, rng: random.Random, commit: bool = True) -> int:
        count = 0
        atmosphere_by_brand = {row["brand"]: row for row in atmosphere}
        for clique in cliques:
            if clique["behavior_classification"] not in {"territorial", "predatory"}:
                continue
            score = float(atmosphere_by_brand.get(clique["brand"], {}).get("atmosphere_score", 50))
            probability = (0.05 if clique["behavior_classification"] == "territorial" else 0.11) + max(0, (40 - score) / 250)
            targets = [state for state in states if state["brand"] == clique["brand"] and state["wrestler_id"] not in {m["wrestler_id"] for m in clique["members"]}]
            if targets and rng.random() < probability:
                target = sorted(targets, key=lambda row: row["backstage_influence"])[0]
                perpetrators = clique["members"][:2]
                severity = self.clamp(35 + (50 - score) * 0.6 + (15 if clique["behavior_classification"] == "predatory" else 0))
                self.repo.insert_simple(
                    "locker_bullying_incidents",
                    {
                        "id": new_id("bullying"),
                        "perpetrator_ids_json": [p["wrestler_id"] for p in perpetrators],
                        "perpetrator_names_json": [p["wrestler_name"] for p in perpetrators],
                        "target_wrestler_id": target["wrestler_id"],
                        "target_wrestler_name": target["wrestler_name"],
                        "incident_type": "professional_undermining" if severity < 65 else "physical_intimidation",
                        "severity": round(severity, 2),
                        "witness_count": rng.randint(1, 8),
                        "reported_to_management": 1 if severity >= 60 else 0,
                        "morale_impact": round(-severity / 6, 2),
                        "atmosphere_impact": round(-severity / 9, 2),
                        "media_scandal_risk": round(severity / 140, 4),
                        "payload_json": {"clique_id": clique["id"], "brand_atmosphere": score},
                        "year": year,
                        "week": week,
                        "updated_at": self.repo.now(),
                    },
                    commit=False,
                )
                count += 1
        if commit:
            self.repo.conn.commit()
        return count

    def _maybe_shoot_incident(self, states: list[dict], atmosphere: list[dict], year: int, week: int, rng: random.Random, commit: bool = True) -> int:
        toxic = [row for row in atmosphere if float(row["atmosphere_score"]) <= 25]
        if not toxic:
            volatile = [row for row in states if float(row["morale_score"]) <= 18 and float(row["ego_level"]) >= 72]
        else:
            volatile = [row for row in states if row["brand"] == toxic[0]["brand"]]
        if len(volatile) < 2:
            return 0
        probability = 0.015 + len(toxic) * 0.05 + len([row for row in volatile if float(row["morale_score"]) <= 20]) * 0.006
        if rng.random() >= probability:
            return 0
        volatile.sort(key=lambda row: (row["morale_score"], -row["ego_level"]))
        participants = volatile[:2]
        severity = self.clamp(45 + max(0, 30 - min(float(p["morale_score"]) for p in participants)) + max(float(p["ego_level"]) for p in participants) * 0.2)
        self.repo.insert_simple(
            "locker_shoot_incidents",
            {
                "id": new_id("shoot"),
                "participant_ids_json": [p["wrestler_id"] for p in participants],
                "participant_names_json": [p["wrestler_name"] for p in participants],
                "trigger_context": "Low morale and high ego broke through the planned performance context.",
                "severity": round(severity, 2),
                "witness_count": rng.randint(3, 20),
                "captured_on_recording": 1 if rng.random() < 0.45 else 0,
                "crisis_management_score": 0,
                "credibility_impact": 0,
                "payload_json": {"requires_user_response": True},
                "year": year,
                "week": week,
                "updated_at": self.repo.now(),
            },
            commit=commit,
        )
        return 1

    def create_meeting(self, data: dict) -> dict:
        required = ["meeting_type", "purpose"]
        for key in required:
            if not data.get(key):
                raise ValidationError(f"{key} is required")
        year, week = self._state_week(data)
        self._ensure_locker_states()
        states = self.repo.list_locker_states(data.get("target_brand"))
        attendee_ids = set(data.get("attendee_ids") or [])
        if attendee_ids:
            states = [state for state in states if state["wrestler_id"] in attendee_ids]
        if data["meeting_type"] == "one_on_one" and len(states) != 1 and data.get("wrestler_id"):
            states = [self.repo.get_locker_state(data["wrestler_id"])]
        states = [state for state in states if state]
        if not states:
            raise ValidationError("No meeting attendees matched the request")
        atmosphere = self.repo.latest_atmosphere(data.get("target_brand"))
        atmosphere_score = float(atmosphere[0]["atmosphere_score"]) if atmosphere else 50
        communication = float(data.get("communication_skill", 65))
        credibility = float(data.get("credibility", 60))
        effectiveness = self.clamp(communication * 0.42 + credibility * 0.28 + atmosphere_score * 0.20 + min(10, len(states) * 0.2))
        purpose = data["purpose"]
        morale_delta = {
            "morale_boost": (effectiveness - 45) / 8,
            "policy_announcement": (effectiveness - 50) / 18,
            "creative_direction_briefing": (effectiveness - 48) / 12,
            "disciplinary_addressing": (effectiveness - 55) / 16,
            "conflict_resolution": (effectiveness - 50) / 10,
            "performance_feedback": (effectiveness - 52) / 14,
            "strategic_vision": (effectiveness - 46) / 11,
        }.get(purpose, (effectiveness - 50) / 15)
        meeting = self.repo.insert_simple(
            "locker_meetings",
            {
                "id": new_id("meeting"),
                "meeting_type": data["meeting_type"],
                "purpose": purpose,
                "conductor_name": data.get("conductor_name", "Promotion management"),
                "communication_skill": communication,
                "target_brand": data.get("target_brand"),
                "crisis_ref": data.get("crisis_ref"),
                "effectiveness_score": round(effectiveness, 2),
                "outcome_json": {
                    "attendee_count": len(states),
                    "morale_delta": round(morale_delta, 2),
                    "atmosphere_delta": round(morale_delta / 3, 2),
                },
                "year": year,
                "week": week,
            },
            commit=False,
        )
        with self.repo.transaction():
            for state in states:
                adjusted = self.clamp(float(state["morale_score"]) + morale_delta)
                ego_delta = -1.5 if purpose == "conflict_resolution" and effectiveness >= 65 else 0
                self.repo.upsert_locker_state(
                    {
                        **state,
                        "morale_score": round(adjusted, 2),
                        "morale_level": self._level(adjusted, "morale"),
                        "ego_level": round(self.clamp(float(state["ego_level"]) + ego_delta), 2),
                        "last_primary_factors_json": {
                            **(state.get("last_primary_factors_json") or {}),
                            "latest_meeting": {"purpose": purpose, "effectiveness": effectiveness},
                        },
                    },
                    commit=False,
                )
                self.repo.insert_simple(
                    "locker_meeting_attendees",
                    {
                        "id": new_id("meeting_attendee"),
                        "meeting_id": meeting["id"],
                        "wrestler_id": state["wrestler_id"],
                        "wrestler_name": state["wrestler_name"],
                        "morale_delta": round(morale_delta, 2),
                        "ego_delta": ego_delta,
                    },
                    commit=False,
                )
        return self.repo.fetch_one("SELECT * FROM locker_meetings WHERE id = ?", (meeting["id"],)) or meeting

    def create_disciplinary_action(self, data: dict) -> dict:
        required = ["wrestler_id", "violation_type", "action_type", "justification"]
        for key in required:
            if not data.get(key):
                raise ValidationError(f"{key} is required")
        year, week = self._state_week(data)
        self._ensure_locker_states()
        state = self.repo.get_locker_state(data["wrestler_id"])
        wrestler = self.repo.get_wrestler(data["wrestler_id"])
        if not state or not wrestler:
            raise ValidationError("Wrestler not found")
        severity = float(data.get("severity", 50))
        action = data["action_type"]
        expected = {"verbal_warning": 20, "written_warning": 38, "fine": 52, "suspension": 70, "termination": 90}.get(action, 45)
        proportionality = self.clamp(100 - abs(severity - expected))
        prior = self.repo.fetch_one(
            "SELECT COUNT(*) AS total FROM locker_disciplinary_actions WHERE wrestler_id = ? AND deleted_at IS NULL",
            (data["wrestler_id"],),
        )
        consistency = min(20, int(prior["total"]) * 5) if prior else 0
        perceived_fairness = self.clamp(proportionality * 0.75 + consistency)
        morale_impact = -max(2, severity / 8)
        if perceived_fairness >= 70:
            atmosphere_impact = 2.5
        elif perceived_fairness <= 45:
            atmosphere_impact = -5.5
        else:
            atmosphere_impact = -1
        legal = 0.0
        if action == "termination":
            legal = self.clamp((70 - proportionality) / 100 + (0 if prior and int(prior["total"]) else 0.25), 0, 0.85)
        salary = int(wrestler.get("contract_salary", 0) or 0)
        fine_amount = int(data.get("fine_amount") or (salary * float(data.get("fine_pct", 0.03)) if action == "fine" else 0))
        record = self.repo.insert_simple(
            "locker_disciplinary_actions",
            {
                "id": new_id("discipline"),
                "wrestler_id": state["wrestler_id"],
                "wrestler_name": state["wrestler_name"],
                "violation_type": data["violation_type"],
                "action_type": action,
                "fine_amount": fine_amount,
                "suspension_weeks": int(data.get("suspension_weeks", 0) or 0),
                "justification": data["justification"],
                "proportionality_score": round(proportionality, 2),
                "perceived_fairness": round(perceived_fairness, 2),
                "morale_impact": round(morale_impact, 2),
                "atmosphere_impact": round(atmosphere_impact, 2),
                "legal_challenge_probability": round(legal, 4),
                "related_incident_id": data.get("related_incident_id"),
                "year": year,
                "week": week,
            },
            commit=False,
        )
        with self.repo.transaction():
            adjusted = self.clamp(float(state["morale_score"]) + morale_impact)
            professionalism = self.clamp(float(state["professionalism"]) + (3 if perceived_fairness >= 70 else -2))
            self.repo.upsert_locker_state(
                {
                    **state,
                    "morale_score": round(adjusted, 2),
                    "morale_level": self._level(adjusted, "morale"),
                    "professionalism": round(professionalism, 2),
                    "last_primary_factors_json": {
                        **(state.get("last_primary_factors_json") or {}),
                        "latest_discipline": {"action_type": action, "fairness": perceived_fairness},
                    },
                },
                commit=False,
            )
        return self.repo.fetch_one("SELECT * FROM locker_disciplinary_actions WHERE id = ?", (record["id"],)) or record

    def resolve_creative_disagreement(self, disagreement_id: str, data: dict) -> dict:
        disagreement = self.repo.fetch_one(
            "SELECT * FROM locker_creative_disagreements WHERE id = ? AND deleted_at IS NULL",
            (disagreement_id,),
        )
        if not disagreement:
            raise ValidationError("Creative disagreement not found")
        choice = data.get("resolution_choice")
        if choice not in {"accommodation", "negotiation", "assertion", "compromise_timeline"}:
            raise ValidationError("Invalid resolution_choice")
        impacts = {
            "accommodation": (5, -1, 1.5),
            "negotiation": (3, -0.5, 1),
            "assertion": (-7, 2, -3),
            "compromise_timeline": (4, 0, 1.25),
        }[choice]
        state = self.repo.get_locker_state(disagreement["wrestler_id"])
        with self.repo.transaction():
            self.repo.conn.execute(
                """
                UPDATE locker_creative_disagreements
                SET status = 'resolved', resolution_choice = ?,
                    morale_impact = ?, ego_impact = ?, atmosphere_impact = ?,
                    aftermath_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    choice,
                    impacts[0],
                    impacts[1],
                    impacts[2],
                    self.repo.to_json({"resolution_notes": data.get("notes", ""), "choice": choice}),
                    self.repo.now(),
                    disagreement_id,
                ),
            )
            if state:
                morale = self.clamp(float(state["morale_score"]) + impacts[0])
                ego = self.clamp(float(state["ego_level"]) + impacts[1])
                self.repo.upsert_locker_state(
                    {**state, "morale_score": round(morale, 2), "morale_level": self._level(morale, "morale"), "ego_level": round(ego, 2)},
                    commit=False,
                )
        return self.repo.fetch_one("SELECT * FROM locker_creative_disagreements WHERE id = ?", (disagreement_id,))

    def locker_dashboard(self, brand: str | None = None) -> dict:
        self._ensure_locker_states()
        states = self.repo.list_locker_states(brand)
        atmospheres = self.repo.latest_atmosphere(brand)
        return {
            "summary": {
                "total_wrestlers": len(states),
                "low_morale": len([row for row in states if float(row["morale_score"]) < 31]),
                "high_ego": len([row for row in states if float(row["ego_level"]) > 60]),
                "low_professionalism": len([row for row in states if float(row["professionalism"]) < 41]),
                "average_morale": round(sum(float(row["morale_score"]) for row in states) / len(states), 2) if states else 0,
            },
            "atmosphere": atmospheres,
            "wrestlers": states,
            "cliques": self.repo.active_cliques(),
            "open_disagreements": self.repo.fetch_all(
                """
                SELECT * FROM locker_creative_disagreements
                WHERE status = 'open' AND deleted_at IS NULL
                ORDER BY preference_conflict_score DESC
                """
            ),
            "open_bullying_incidents": self.repo.fetch_all(
                """
                SELECT * FROM locker_bullying_incidents
                WHERE status = 'open' AND deleted_at IS NULL
                ORDER BY severity DESC
                """
            ),
            "recent_meetings": self.repo.recent_rows("locker_meetings", 10),
            "recent_discipline": self.repo.recent_rows("locker_disciplinary_actions", 10),
            "urgent_shoot_incidents": self.repo.fetch_all(
                """
                SELECT * FROM locker_shoot_incidents
                WHERE status = 'urgent' AND deleted_at IS NULL
                ORDER BY severity DESC
                """
            ),
        }

    def wrestler_culture_detail(self, wrestler_id: str) -> dict:
        self._ensure_locker_states()
        state = self.repo.get_locker_state(wrestler_id)
        if not state:
            raise ValidationError("Wrestler not found")
        return {
            "state": state,
            "morale_history": self.repo.recent_morale_history(wrestler_id, 16),
            "creative_disagreements": self.repo.fetch_all(
                """
                SELECT * FROM locker_creative_disagreements
                WHERE wrestler_id = ? AND deleted_at IS NULL
                ORDER BY year DESC, week DESC
                """,
                (wrestler_id,),
            ),
            "discipline": self.repo.fetch_all(
                """
                SELECT * FROM locker_disciplinary_actions
                WHERE wrestler_id = ? AND deleted_at IS NULL
                ORDER BY year DESC, week DESC
                """,
                (wrestler_id,),
            ),
            "substance_records": self.repo.fetch_all(
                """
                SELECT id, wrestler_id, wrestler_name, status, severity, discovered_year,
                       discovered_week, recovery_progress, relapse_risk,
                       confidentiality_level, created_year, created_week
                FROM locker_substance_issues
                WHERE wrestler_id = ? AND deleted_at IS NULL
                ORDER BY created_year DESC, created_week DESC
                """,
                (wrestler_id,),
            ),
        }

    # ------------------------------------------------------------------
    # Developmental pipeline
    # ------------------------------------------------------------------

    def developmental_dashboard(self) -> dict:
        center = self.repo.get_center() or {}
        trainees = self.repo.list_trainees()
        return {
            "center": center,
            "trainers": self.repo.list_trainers(),
            "curricula": self.repo.list_curricula(),
            "trainees": trainees,
            "ready_for_callup": [row for row in trainees if float(row["readiness_score"]) >= 75],
            "plateaus": [row for row in trainees if int(row["plateau_weeks"]) >= 4],
            "active_injuries": self.repo.fetch_all(
                """
                SELECT * FROM dev_training_injuries
                WHERE weeks_remaining > 0 AND deleted_at IS NULL
                ORDER BY weeks_remaining DESC
                """
            ),
            "active_excursions": self.repo.active_excursions(),
            "recent_progress": self.repo.recent_rows("dev_progress_snapshots", 20),
            "recent_tryouts": self.repo.recent_rows("dev_tryouts", 10),
        }

    def create_trainer(self, data: dict) -> dict:
        for key in ("trainer_name", "specialization"):
            if not data.get(key):
                raise ValidationError(f"{key} is required")
        return self.repo.insert_simple(
            "dev_trainers",
            {
                "id": data.get("id") or new_id("trainer"),
                "trainer_name": data["trainer_name"],
                "background": data.get("background", "wrestling_veteran"),
                "coaching_skill": self.clamp(data.get("coaching_skill", 60)),
                "specialization": data["specialization"],
                "preferred_methods_json": data.get("preferred_methods", {}),
                "reputation": self.clamp(data.get("reputation", 50)),
                "professionalism": self.clamp(data.get("professionalism", 70)),
                "salary": int(data.get("salary", 75000)),
                "active": 1,
                "performance_metrics_json": {},
                "relationship_json": {},
                "updated_at": self.repo.now(),
            },
        )

    def create_curriculum(self, data: dict) -> dict:
        allocation = data.get("allocation") or {}
        if not allocation:
            template = data.get("template_type", "raw_athlete")
            allocation = self._template_allocation(template)
        total = round(sum(float(value) for value in allocation.values()), 4)
        if abs(total - 100) > 0.01:
            raise ValidationError("Curriculum allocation must total 100")
        invalid = set(allocation.keys()) - CURRICULUM_KEYS
        if invalid:
            raise ValidationError(f"Invalid curriculum keys: {sorted(invalid)}")
        return self.repo.insert_simple(
            "dev_curricula",
            {
                "id": data.get("id") or new_id("curriculum"),
                "curriculum_name": data.get("curriculum_name", data.get("template_type", "Custom Curriculum").replace("_", " ").title()),
                "template_type": data.get("template_type", "custom"),
                "allocation_json": allocation,
                "intensity": float(data.get("intensity", 1.0)),
                "description": data.get("description", ""),
                "updated_at": self.repo.now(),
            },
        )

    def _template_allocation(self, template: str) -> dict:
        templates = {
            "raw_athlete": {
                "in_ring_fundamentals": 34,
                "athletic_conditioning": 18,
                "character_promo": 14,
                "match_psychology": 18,
                "move_set": 8,
                "tag_faction": 3,
                "sports_entertainment": 5,
            },
            "indie_veteran": {
                "in_ring_fundamentals": 12,
                "athletic_conditioning": 8,
                "character_promo": 30,
                "match_psychology": 18,
                "move_set": 8,
                "tag_faction": 8,
                "sports_entertainment": 16,
            },
            "former_athlete": {
                "in_ring_fundamentals": 28,
                "athletic_conditioning": 12,
                "character_promo": 20,
                "match_psychology": 18,
                "move_set": 8,
                "tag_faction": 4,
                "sports_entertainment": 10,
            },
        }
        return templates.get(template, templates["raw_athlete"])

    def add_trainee(self, data: dict) -> dict:
        if not data.get("wrestler_id") or not data.get("wrestler_name"):
            raise ValidationError("wrestler_id and wrestler_name are required")
        year, week = self._state_week(data)
        center_id = data.get("center_id", "pc_roc_vanguard")
        center = self.repo.get_center(center_id)
        if not center:
            raise ValidationError("Performance center not found")
        attrs = data.get("attributes") or {key: float(data.get(key, 45)) for key in ATTRIBUTES}
        trainee = self.repo.insert_simple(
            "dev_trainees",
            {
                "wrestler_id": data["wrestler_id"],
                "wrestler_name": data["wrestler_name"],
                "center_id": center_id,
                "status": "active",
                "developmental_overness": float(data.get("developmental_overness", 20)),
                "readiness_score": 0,
                "readiness_breakdown_json": {},
                "assigned_trainer_id": data.get("assigned_trainer_id"),
                "curriculum_id": data.get("curriculum_id"),
                "learning_rate": float(data.get("learning_rate", 1.0)),
                "physical_conditioning": float(data.get("physical_conditioning", attrs.get("stamina", 50))),
                "character_definition": float(data.get("character_definition", attrs.get("mic", 45))),
                "crowd_response": float(data.get("crowd_response", 40)),
                "initial_attributes_json": attrs,
                "current_attributes_json": attrs,
                "plateau_weeks": 0,
                "created_year": year,
                "created_week": week,
                "updated_at": self.repo.now(),
            },
        )
        readiness = self._readiness(trainee)
        self.repo.update_trainee(data["wrestler_id"], {"readiness_score": readiness["score"], "readiness_breakdown_json": readiness["breakdown"]})
        self.repo.update_center_count(center_id)
        return self.repo.get_trainee(data["wrestler_id"]) or trainee

    def _readiness(self, trainee: dict) -> dict:
        attrs = trainee.get("current_attributes_json") or {}
        in_ring = mean([float(attrs.get("brawling", 50)), float(attrs.get("technical", 50)), float(attrs.get("speed", 50)), float(attrs.get("stamina", 50)), float(attrs.get("psychology", 50))])
        promo = float(attrs.get("mic", 50))
        character = float(trainee.get("character_definition", 50))
        crowd = float(trainee.get("crowd_response", 50))
        professionalism = float((self.repo.get_locker_state(trainee["wrestler_id"]) or {}).get("professionalism", 60))
        conditioning = float(trainee.get("physical_conditioning", attrs.get("stamina", 50)))
        score = in_ring * 0.30 + promo * 0.18 + character * 0.18 + conditioning * 0.12 + professionalism * 0.10 + crowd * 0.12
        return {
            "score": round(self.clamp(score), 2),
            "breakdown": {
                "in_ring": round(in_ring, 2),
                "promo": round(promo, 2),
                "character": round(character, 2),
                "conditioning": round(conditioning, 2),
                "professionalism": round(professionalism, 2),
                "crowd_response": round(crowd, 2),
            },
        }

    def run_development_week(self, year: int, week: int, seed: int | None = None) -> dict:
        existing = self.repo.get_job("weekly_developmental_pipeline", year, week)
        if existing and existing["status"] == "completed":
            return {"already_ran": True, **(existing.get("result_json") or {})}
        rng = self._rng(seed, year, week, "development")
        center = self.repo.get_center()
        if not center:
            raise ValidationError("Performance center not found")
        trainees = self.repo.list_trainees()
        trainers = {row["id"]: row for row in self.repo.list_trainers()}
        curricula = {row["id"]: row for row in self.repo.list_curricula()}
        capacity_penalty = max(0, (len(trainees) - int(center["capacity"])) * 0.015)
        updated = 0
        injuries = 0
        breakthroughs = 0
        with self.repo.transaction():
            for trainee in trainees:
                if self._trainee_on_excursion(trainee["wrestler_id"]):
                    continue
                trainer = trainers.get(trainee.get("assigned_trainer_id"))
                curriculum = curricula.get(trainee.get("curriculum_id"))
                allocation = (curriculum or {}).get("allocation_json") or self._template_allocation("raw_athlete")
                trainer_effectiveness = self._trainer_effectiveness(trainer, allocation)
                facility = float(center.get("training_quality_modifier", 0) or 0) - capacity_penalty
                atmosphere_mod = self._developmental_atmosphere_modifier()
                curriculum_eff = self.clamp(50 + trainer_effectiveness * 20 + facility * 100 + atmosphere_mod * 100)
                attrs = dict(trainee.get("current_attributes_json") or {})
                before_total = sum(float(attrs.get(key, 50)) for key in ATTRIBUTES)
                learning = float(trainee.get("learning_rate", 1.0) or 1.0)
                intensity = float((curriculum or {}).get("intensity", 1.0) or 1.0)
                deltas = self._attribute_deltas(allocation, learning, trainer_effectiveness, facility, atmosphere_mod, rng)
                for key, delta in deltas.items():
                    attrs[key] = round(self.clamp(float(attrs.get(key, 50)) + delta), 2)
                character = self.clamp(float(trainee["character_definition"]) + deltas.get("mic", 0) * 0.35 + allocation.get("character_promo", 0) / 100)
                conditioning = self.clamp(float(trainee["physical_conditioning"]) + deltas.get("stamina", 0) * 0.50 + allocation.get("athletic_conditioning", 0) / 120)
                crowd = self.clamp(float(trainee["crowd_response"]) + rng.uniform(-0.2, 0.7))
                after_total = sum(float(attrs.get(key, 50)) for key in ATTRIBUTES)
                plateau = int(trainee["plateau_weeks"]) + 1 if after_total - before_total < 0.25 else 0
                event_type = "weekly_progress"
                notes = "Normal weekly progression."
                if self._breakthrough_chance(trainee, trainer, curriculum_eff, rng):
                    focus_key = max(deltas, key=lambda key: deltas[key])
                    attrs[focus_key] = round(self.clamp(float(attrs.get(focus_key, 50)) + rng.uniform(2.5, 5.0)), 2)
                    event_type = "breakthrough"
                    notes = f"Breakthrough moment in {focus_key}."
                    breakthroughs += 1
                    plateau = 0
                readiness_payload = self._readiness(
                    {
                        **trainee,
                        "current_attributes_json": attrs,
                        "character_definition": character,
                        "physical_conditioning": conditioning,
                        "crowd_response": crowd,
                    }
                )
                self.repo.update_trainee(
                    trainee["wrestler_id"],
                    {
                        "current_attributes_json": attrs,
                        "character_definition": round(character, 2),
                        "physical_conditioning": round(conditioning, 2),
                        "crowd_response": round(crowd, 2),
                        "readiness_score": readiness_payload["score"],
                        "readiness_breakdown_json": readiness_payload["breakdown"],
                        "plateau_weeks": plateau,
                    },
                    commit=False,
                )
                self.repo.insert_simple(
                    "dev_progress_snapshots",
                    {
                        "id": f"dev_progress_{trainee['wrestler_id']}_{year}_{week}",
                        "wrestler_id": trainee["wrestler_id"],
                        "wrestler_name": trainee["wrestler_name"],
                        "year": year,
                        "week": week,
                        "attributes_json": attrs,
                        "readiness_score": readiness_payload["score"],
                        "readiness_breakdown_json": readiness_payload["breakdown"],
                        "curriculum_effectiveness": round(curriculum_eff, 2),
                        "trainer_effectiveness": round(trainer_effectiveness, 4),
                        "facility_modifier": round(facility, 4),
                        "event_type": event_type,
                        "notes": notes,
                    },
                    commit=False,
                )
                if self._training_injury_chance(trainee, trainer, center, intensity, capacity_penalty, rng):
                    self._insert_training_injury(trainee, year, week, intensity, center, rng, commit=False)
                    injuries += 1
                updated += 1
        self.repo.update_center_count(center["id"])
        result = {"updated_trainees": updated, "injuries": injuries, "breakthroughs": breakthroughs}
        self.repo.upsert_job(
            {
                "job_type": "weekly_developmental_pipeline",
                "year": year,
                "week": week,
                "status": "completed",
                "seed": seed,
                "reads": ["dev_trainees", "dev_trainers", "dev_curricula", "dev_performance_centers"],
                "writes": ["dev_progress_snapshots", "dev_trainees", "dev_training_injuries"],
                "result": result,
            }
        )
        return {"already_ran": False, **result}

    def _trainer_effectiveness(self, trainer: dict | None, allocation: dict) -> float:
        if not trainer:
            return 0.0
        specialty = trainer.get("specialization")
        specialty_map = {
            "technical": "in_ring_fundamentals",
            "high_flying": "athletic_conditioning",
            "strength_conditioning": "athletic_conditioning",
            "promo_character": "character_promo",
            "psychology": "match_psychology",
            "tag_faction": "tag_faction",
        }
        match_pct = float(allocation.get(specialty_map.get(specialty, ""), 0)) / 100
        return ((float(trainer.get("coaching_skill", 60)) - 50) / 100) + match_pct * 0.45 + ((float(trainer.get("reputation", 50)) - 50) / 300)

    def _developmental_atmosphere_modifier(self) -> float:
        latest = self.repo.latest_atmosphere("ROC Vanguard") or self.repo.latest_atmosphere()
        if not latest:
            return 0.0
        avg = sum(float(row["atmosphere_score"]) for row in latest) / len(latest)
        return (avg - 50) / 400

    def _attribute_deltas(self, allocation: dict, learning: float, trainer_eff: float, facility: float, atmosphere_mod: float, rng: random.Random) -> dict:
        base = max(0.05, 0.45 * learning + trainer_eff + facility + atmosphere_mod)
        mapping = {
            "brawling": allocation.get("in_ring_fundamentals", 0) * 0.006 + allocation.get("move_set", 0) * 0.004,
            "technical": allocation.get("in_ring_fundamentals", 0) * 0.008 + allocation.get("match_psychology", 0) * 0.002,
            "speed": allocation.get("athletic_conditioning", 0) * 0.006 + allocation.get("move_set", 0) * 0.003,
            "mic": allocation.get("character_promo", 0) * 0.008 + allocation.get("sports_entertainment", 0) * 0.004,
            "psychology": allocation.get("match_psychology", 0) * 0.008 + allocation.get("tag_faction", 0) * 0.003,
            "stamina": allocation.get("athletic_conditioning", 0) * 0.008,
        }
        return {key: round(max(0, value * base + rng.uniform(-0.05, 0.18)), 3) for key, value in mapping.items()}

    def _breakthrough_chance(self, trainee: dict, trainer: dict | None, curriculum_eff: float, rng: random.Random) -> bool:
        probability = max(0, (curriculum_eff - 70) / 400) + (0.025 if trainer and float(trainer.get("coaching_skill", 0)) >= 80 else 0)
        if int(trainee.get("plateau_weeks", 0)) >= 3:
            probability += 0.025
        return rng.random() < probability

    def _training_injury_chance(self, trainee: dict, trainer: dict | None, center: dict, intensity: float, capacity_penalty: float, rng: random.Random) -> bool:
        conditioning = float(trainee.get("physical_conditioning", 50) or 50)
        trainer_prof = float((trainer or {}).get("professionalism", 60) or 60)
        facility_level = int(center.get("facility_level", 5) or 5)
        probability = 0.012 * intensity + max(0, (45 - conditioning) / 1000) + max(0, (55 - trainer_prof) / 1200) + max(0, (5 - facility_level) / 500) + capacity_penalty
        return rng.random() < probability

    def _insert_training_injury(self, trainee: dict, year: int, week: int, intensity: float, center: dict, rng: random.Random, commit: bool = True) -> dict:
        roll = rng.random()
        if roll < 0.55:
            severity, weeks, perm = "minor", rng.randint(1, 3), 0.01
        elif roll < 0.82:
            severity, weeks, perm = "moderate", rng.randint(3, 8), 0.04
        elif roll < 0.96:
            severity, weeks, perm = "significant", rng.randint(9, 13), 0.10
        else:
            severity, weeks, perm = "severe", rng.randint(14, 39), 0.22
        self.repo.update_trainee(trainee["wrestler_id"], {"status": "limited" if severity in {"minor", "moderate"} else "injured"}, commit=False)
        return self.repo.insert_simple(
            "dev_training_injuries",
            {
                "id": new_id("training_injury"),
                "wrestler_id": trainee["wrestler_id"],
                "wrestler_name": trainee["wrestler_name"],
                "injury_type": "training_load",
                "severity": severity,
                "weeks_remaining": weeks,
                "permanent_attribute_risk": perm,
                "cause_json": {"curriculum_intensity": intensity, "facility_level": center.get("facility_level")},
                "year": year,
                "week": week,
                "updated_at": self.repo.now(),
            },
            commit=commit,
        )

    def _trainee_on_excursion(self, wrestler_id: str) -> bool:
        row = self.repo.fetch_one(
            """
            SELECT id FROM dev_excursions
            WHERE wrestler_id = ? AND status = 'active' AND deleted_at IS NULL
            """,
            (wrestler_id,),
        )
        return bool(row)

    def schedule_tryout(self, data: dict) -> dict:
        year, week = self._state_week(data)
        count = int(data.get("candidate_count", 8))
        if count <= 0 or count > 100:
            raise ValidationError("candidate_count must be between 1 and 100")
        rng = self._rng(data.get("seed"), year, week, data.get("location", "tryout"))
        cost = int(7000 + count * 650 + int(data.get("duration_days", 2)) * 1800)
        tryout = self.repo.insert_simple(
            "dev_tryouts",
            {
                "id": data.get("id") or new_id("tryout"),
                "location": data.get("location", "Orlando"),
                "candidate_count": count,
                "scout_trainer_id": data.get("scout_trainer_id"),
                "duration_days": int(data.get("duration_days", 2)),
                "target_profile": data.get("target_profile", "general"),
                "cost": cost,
                "reputation_modifier": float(data.get("reputation_modifier", 0)),
                "status": "completed",
                "year": year,
                "week": week,
                "updated_at": self.repo.now(),
            },
            commit=False,
        )
        backgrounds = ["football", "martial_arts", "gymnastics", "indie_wrestling", "theater", "powerlifting", "dance"]
        with self.repo.transaction():
            for index in range(count):
                background = rng.choice(backgrounds)
                revealed, ceiling = self._candidate_attributes(background, rng)
                current = sum(revealed.values()) / len(revealed)
                potential = sum(ceiling.values()) / len(ceiling)
                self.repo.insert_simple(
                    "dev_tryout_candidates",
                    {
                        "id": new_id("candidate"),
                        "tryout_id": tryout["id"],
                        "candidate_name": f"{background.replace('_', ' ').title()} Prospect {index + 1}",
                        "background": background,
                        "revealed_attributes_json": revealed,
                        "potential_ceiling_json": ceiling,
                        "current_assessment": round(current, 2),
                        "potential_assessment": round(potential, 2),
                        "decision_status": "undecided",
                        "updated_at": self.repo.now(),
                    },
                    commit=False,
                )
        return self.get_tryout(tryout["id"])

    def _candidate_attributes(self, background: str, rng: random.Random) -> tuple[dict, dict]:
        base = {key: rng.randint(25, 55) for key in ATTRIBUTES}
        bonuses = {
            "football": {"brawling": 18, "stamina": 12},
            "martial_arts": {"technical": 16, "brawling": 10},
            "gymnastics": {"speed": 22, "stamina": 8},
            "indie_wrestling": {"technical": 18, "psychology": 12},
            "theater": {"mic": 20, "psychology": 8},
            "powerlifting": {"brawling": 20, "stamina": 5},
            "dance": {"speed": 16, "mic": 8},
        }.get(background, {})
        for key, value in bonuses.items():
            base[key] = self.clamp(base[key] + value)
        ceiling = {key: self.clamp(value + rng.randint(15, 38)) for key, value in base.items()}
        return base, ceiling

    def get_tryout(self, tryout_id: str) -> dict:
        tryout = self.repo.fetch_one("SELECT * FROM dev_tryouts WHERE id = ? AND deleted_at IS NULL", (tryout_id,))
        if not tryout:
            raise ValidationError("Tryout not found")
        tryout["candidates"] = self.repo.fetch_all(
            "SELECT * FROM dev_tryout_candidates WHERE tryout_id = ? AND deleted_at IS NULL ORDER BY potential_assessment DESC",
            (tryout_id,),
        )
        return tryout

    def sign_tryout_candidate(self, candidate_id: str, data: dict | None = None) -> dict:
        data = data or {}
        candidate = self.repo.fetch_one(
            "SELECT * FROM dev_tryout_candidates WHERE id = ? AND deleted_at IS NULL",
            (candidate_id,),
        )
        if not candidate:
            raise ValidationError("Candidate not found")
        wrestler_id = data.get("wrestler_id") or f"tryout_{candidate_id}"
        with self.repo.transaction():
            self.repo.conn.execute(
                "UPDATE dev_tryout_candidates SET decision_status = 'signed', signed_wrestler_id = ?, updated_at = ? WHERE id = ?",
                (wrestler_id, self.repo.now(), candidate_id),
            )
        return self.add_trainee(
            {
                "wrestler_id": wrestler_id,
                "wrestler_name": data.get("wrestler_name") or candidate["candidate_name"],
                "attributes": candidate["revealed_attributes_json"],
                "learning_rate": max(0.75, float(candidate["potential_assessment"]) / max(1, float(candidate["current_assessment"])) / 1.8),
                "physical_conditioning": candidate["revealed_attributes_json"].get("stamina", 50),
                "character_definition": candidate["revealed_attributes_json"].get("mic", 40),
                "created_year": data.get("year"),
                "created_week": data.get("week"),
            }
        )

    def create_callup(self, data: dict) -> dict:
        if not data.get("wrestler_id") or not data.get("destination_brand"):
            raise ValidationError("wrestler_id and destination_brand are required")
        year, week = self._state_week(data)
        trainee = self.repo.get_trainee(data["wrestler_id"])
        if not trainee:
            raise ValidationError("Trainee not found")
        readiness = float(trainee["readiness_score"])
        override = bool(data.get("readiness_override", False))
        if readiness < 65 and not override:
            raise ValidationError("Readiness below safe call-up threshold. Use readiness_override=true to accept the risk.")
        unreadiness = max(0, 75 - readiness) / 100
        callup = self.repo.insert_simple(
            "dev_callups",
            {
                "id": new_id("callup"),
                "wrestler_id": trainee["wrestler_id"],
                "wrestler_name": trainee["wrestler_name"],
                "source_brand": "ROC Vanguard",
                "destination_brand": data["destination_brand"],
                "readiness_score": readiness,
                "readiness_override": 1 if override else 0,
                "debut_plan": data.get("debut_plan", "announced_promotion"),
                "mentor_wrestler_id": data.get("mentor_wrestler_id"),
                "transition_score": round(60 - unreadiness * 35 + self._developmental_atmosphere_modifier() * 100, 2),
                "unreadiness_penalty": round(unreadiness, 4),
                "year": year,
                "week": week,
                "updated_at": self.repo.now(),
            },
            commit=False,
        )
        with self.repo.transaction():
            self.repo.update_trainee(trainee["wrestler_id"], {"status": "called_up"}, commit=False)
            state = self.repo.get_locker_state(trainee["wrestler_id"])
            if state:
                self.repo.upsert_locker_state({**state, "brand": data["destination_brand"], "roster_designation": "main_roster"}, commit=False)
        return callup

    def create_senddown(self, data: dict) -> dict:
        if not data.get("wrestler_id") or not data.get("reason"):
            raise ValidationError("wrestler_id and reason are required")
        year, week = self._state_week(data)
        state = self.repo.get_locker_state(data["wrestler_id"])
        wrestler = self.repo.get_wrestler(data["wrestler_id"])
        if not state and not wrestler:
            raise ValidationError("Wrestler not found")
        name = (state or wrestler)["wrestler_name" if state else "name"]
        ego = float((state or {}).get("ego_level", 35))
        tenure = float((wrestler or {}).get("years_experience", 4) or 4)
        meeting = bool(data.get("communicated_via_meeting", False))
        morale_impact = -(8 + ego / 12 + tenure / 4) + (5 if meeting else 0)
        record = self.repo.insert_simple(
            "dev_senddowns",
            {
                "id": new_id("senddown"),
                "wrestler_id": data["wrestler_id"],
                "wrestler_name": name,
                "source_brand": (state or {}).get("brand", (wrestler or {}).get("primary_brand", "ROC Alpha")),
                "reason": data["reason"],
                "communicated_via_meeting": 1 if meeting else 0,
                "morale_impact": round(morale_impact, 2),
                "improvement_plan_json": data.get("improvement_plan") or {"objectives": ["stabilize performance", "complete focused curriculum"]},
                "objective_status": "active",
                "year": year,
                "week": week,
                "updated_at": self.repo.now(),
            },
            commit=False,
        )
        with self.repo.transaction():
            if state:
                morale = self.clamp(float(state["morale_score"]) + morale_impact)
                self.repo.upsert_locker_state({**state, "brand": "ROC Vanguard", "roster_designation": "developmental_roster", "morale_score": round(morale, 2), "morale_level": self._level(morale, "morale")}, commit=False)
            if not self.repo.get_trainee(data["wrestler_id"]):
                attrs = {key: float((wrestler or {}).get(key, 55)) for key in ATTRIBUTES}
                self.add_trainee({"wrestler_id": data["wrestler_id"], "wrestler_name": name, "attributes": attrs, "year": year, "week": week})
        return record

    def start_excursion(self, data: dict) -> dict:
        if not data.get("wrestler_id") or not data.get("destination_id"):
            raise ValidationError("wrestler_id and destination_id are required")
        year, week = self._state_week(data)
        trainee = self.repo.get_trainee(data["wrestler_id"])
        dest = self.repo.fetch_one(
            "SELECT * FROM dev_excursion_destinations WHERE id = ? AND deleted_at IS NULL",
            (data["destination_id"],),
        )
        if not trainee or not dest:
            raise ValidationError("Trainee or destination not found")
        duration = int(data.get("duration_weeks", 24))
        adaptation = self.clamp(70 - float(dest["cultural_challenge"]) * 0.35 + float(trainee.get("learning_rate", 1)) * 12)
        self.repo.update_trainee(trainee["wrestler_id"], {"status": "excursion"}, commit=False)
        return self.repo.insert_simple(
            "dev_excursions",
            {
                "id": new_id("excursion"),
                "wrestler_id": trainee["wrestler_id"],
                "wrestler_name": trainee["wrestler_name"],
                "destination_id": dest["id"],
                "start_year": year,
                "start_week": week,
                "planned_duration_weeks": duration,
                "status": "active",
                "adaptation_score": round(adaptation, 2),
                "development_bonus_json": dest["specialty_json"],
                "progress_reports_json": [],
                "return_plan": data.get("return_plan"),
                "updated_at": self.repo.now(),
            },
        )

    def transition_veteran_to_trainer(self, data: dict) -> dict:
        if not data.get("wrestler_id"):
            raise ValidationError("wrestler_id is required")
        year, week = self._state_week(data)
        wrestler = self.repo.get_wrestler(data["wrestler_id"])
        state = self.repo.get_locker_state(data["wrestler_id"])
        if not wrestler:
            raise ValidationError("Wrestler not found")
        potential = {
            "technical": float(wrestler.get("technical", 50)),
            "psychology": float(wrestler.get("psychology", 50)),
            "promo_character": float(wrestler.get("mic", 50)),
            "authority": float((state or {}).get("backstage_influence", 40)),
        }
        legend = self.clamp(float(wrestler.get("popularity", 50)) * 0.45 + float(wrestler.get("years_experience", 0)) * 2.5)
        record = self.repo.insert_simple(
            "dev_veteran_trainer_transitions",
            {
                "id": new_id("veteran_transition"),
                "wrestler_id": wrestler["id"],
                "wrestler_name": wrestler["name"],
                "transition_reason": data.get("transition_reason", "career_transition"),
                "coaching_potential_json": potential,
                "legend_factor": round(legend, 2),
                "compensation": int(data.get("compensation", 90000 + legend * 1200)),
                "bridge_influence": round(float((state or {}).get("backstage_influence", 40)), 2),
                "status": data.get("status", "accepted"),
                "year": year,
                "week": week,
                "updated_at": self.repo.now(),
            },
            commit=False,
        )
        specialty = max(potential, key=potential.get)
        self.create_trainer(
            {
                "id": f"trainer_from_{wrestler['id']}",
                "trainer_name": wrestler["name"],
                "background": "veteran_transition",
                "coaching_skill": mean(potential.values()),
                "specialization": specialty,
                "reputation": legend,
                "salary": int(data.get("compensation", 90000 + legend * 1200)),
            }
        )
        return record

    # ------------------------------------------------------------------
    # Advanced simulation
    # ------------------------------------------------------------------

    def create_match_script(self, data: dict) -> dict:
        for key in ("show_id", "match_id"):
            if not data.get(key):
                raise ValidationError(f"{key} is required")
        beats = data.get("beats") or []
        if not beats:
            beats = [
                {"phase": "opening", "description": "Establish the competitive dynamic.", "required_skill": "psychology", "difficulty": 45, "intended_reaction": "engagement"},
                {"phase": "heat_building", "description": "Escalate conflict and control.", "required_skill": "brawling", "difficulty": 55, "intended_reaction": "heat"},
                {"phase": "hope_spot", "description": "Create a credible near comeback.", "required_skill": "speed", "difficulty": 58, "intended_reaction": "cheer"},
                {"phase": "finish", "description": "Execute the planned finish cleanly.", "required_skill": "psychology", "difficulty": 62, "intended_reaction": "shock"},
            ]
        script = self.repo.insert_simple(
            "advanced_match_scripts",
            {
                "id": data.get("id") or new_id("match_script"),
                "show_id": data["show_id"],
                "match_id": data["match_id"],
                "feud_id": data.get("feud_id"),
                "script_quality": self.clamp(data.get("script_quality", 60)),
                "intended_reaction": data.get("intended_reaction", "engagement"),
                "match_quality_modifier": 0,
                "feud_heat_delta": 0,
                "post_show_analysis_json": {},
                "updated_at": self.repo.now(),
            },
            commit=False,
        )
        with self.repo.transaction():
            for index, beat in enumerate(beats, start=1):
                self.repo.insert_simple(
                    "advanced_match_script_beats",
                    {
                        "id": new_id("script_beat"),
                        "script_id": script["id"],
                        "phase": beat.get("phase", "heat_building"),
                        "sequence_order": index,
                        "description": beat.get("description", "Scripted beat"),
                        "required_skill": beat.get("required_skill", "psychology"),
                        "difficulty": self.clamp(beat.get("difficulty", 50)),
                        "intended_reaction": beat.get("intended_reaction", data.get("intended_reaction", "engagement")),
                    },
                    commit=False,
                )
        return self.repo.get_match_script(script["id"]) or script

    def evaluate_match_script(self, script_id: str, data: dict) -> dict:
        script = self.repo.get_match_script(script_id)
        if not script:
            raise ValidationError("Match script not found")
        participants = data.get("participant_ids") or []
        wrestlers = [self.repo.get_wrestler(wid) for wid in participants]
        wrestlers = [row for row in wrestlers if row]
        crowd_investment = float(data.get("crowd_investment", 60))
        script_quality = float(script["script_quality"])
        beat_scores = []
        for beat in script["beats"]:
            skill = beat.get("required_skill", "psychology")
            performer_skill = mean([float(w.get(skill, 50) or 50) for w in wrestlers]) if wrestlers else 55
            difficulty = float(beat["difficulty"])
            execution = self.clamp(performer_skill * 0.50 + script_quality * 0.35 + crowd_investment * 0.15 - max(0, difficulty - performer_skill) * 0.25)
            crowd = self.clamp(execution * 0.55 + crowd_investment * 0.45)
            beat_scores.append((beat["id"], execution, crowd))
        execution_score = sum(score[1] for score in beat_scores) / max(1, len(beat_scores))
        crowd_score = sum(score[2] for score in beat_scores) / max(1, len(beat_scores))
        modifier = round((execution_score - 50) / 400 + (crowd_score - 50) / 500, 4)
        heat_delta = round((execution_score + crowd_score - 110) / 12, 2)
        with self.repo.transaction():
            for beat_id, execution, crowd in beat_scores:
                self.repo.conn.execute(
                    """
                    UPDATE advanced_match_script_beats
                    SET execution_score = ?, crowd_response_score = ?
                    WHERE id = ?
                    """,
                    (round(execution, 2), round(crowd, 2), beat_id),
                )
            self.repo.conn.execute(
                """
                UPDATE advanced_match_scripts
                SET execution_score = ?, crowd_connection_score = ?,
                    match_quality_modifier = ?, feud_heat_delta = ?,
                    post_show_analysis_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    round(execution_score, 2),
                    round(crowd_score, 2),
                    modifier,
                    heat_delta,
                    self.repo.to_json({"participant_ids": participants, "crowd_investment": crowd_investment}),
                    self.repo.now(),
                    script_id,
                ),
            )
            if script.get("feud_id"):
                self.repo.conn.execute(
                    """
                    UPDATE story_feuds
                    SET heat_score = MAX(0, MIN(100, heat_score + ?)), updated_at = ?
                    WHERE id = ?
                    """,
                    (heat_delta, self.repo.now(), script["feud_id"]),
                )
        return self.repo.get_match_script(script_id)

    def record_production_quality(self, data: dict) -> dict:
        for key in ("show_id", "brand"):
            if not data.get(key):
                raise ValidationError(f"{key} is required")
        year, week = self._state_week(data)
        profile = self.repo.fetch_one(
            "SELECT * FROM production_profiles WHERE brand = ? AND deleted_at IS NULL",
            (data["brand"],),
        )
        if not profile:
            profile = self.repo.insert_simple(
                "production_profiles",
                {
                    "id": f"production_{data['brand'].lower().replace(' ', '_')}",
                    "brand": data["brand"],
                    "camera_direction_quality": data.get("camera_score", 60),
                    "audio_mixing_quality": data.get("audio_score", 60),
                    "production_budget": data.get("production_budget", 0),
                    "crew_experience": data.get("crew_experience", 60),
                    "presentation_consistency": data.get("presentation_consistency", 60),
                    "updated_at": self.repo.now(),
                },
            )
        commentary = self.repo.fetch_one(
            "SELECT * FROM commentary_teams WHERE brand = ? AND deleted_at IS NULL",
            (data["brand"],),
        )
        commentary_score = float(data.get("commentary_score") or (mean([
            float((commentary or {}).get("play_by_play_accuracy", 60)),
            float((commentary or {}).get("color_insight", 60)),
            float((commentary or {}).get("chemistry", 60)),
            float((commentary or {}).get("storyline_knowledge", 60)),
        ])))
        camera = float(data.get("camera_score", profile["camera_direction_quality"]))
        audio = float(data.get("audio_score", profile["audio_mixing_quality"]))
        broadcast = self.clamp(camera * 0.32 + commentary_score * 0.30 + audio * 0.20 + float(profile.get("presentation_consistency", 60)) * 0.18)
        network_delta = round((broadcast - 60) / 18, 2)
        return self.repo.insert_simple(
            "production_quality_history",
            {
                "id": data.get("id") or new_id("production_quality"),
                "show_id": data["show_id"],
                "brand": data["brand"],
                "camera_score": round(camera, 2),
                "commentary_score": round(commentary_score, 2),
                "audio_score": round(audio, 2),
                "broadcast_score": round(broadcast, 2),
                "network_relationship_delta": network_delta,
                "inputs_json": data,
                "year": year,
                "week": week,
            },
        )

    def project_attendance(self, data: dict) -> dict:
        for key in ("show_id", "show_name", "market_id"):
            if not data.get(key):
                raise ValidationError(f"{key} is required")
        year, week = self._state_week(data)
        market = self.repo.fetch_one(
            "SELECT * FROM attendance_markets WHERE id = ? AND deleted_at IS NULL",
            (data["market_id"],),
        )
        if not market:
            raise ValidationError("Market not found")
        card_quality = float(data.get("card_quality", 55))
        marketing = int(data.get("marketing_spend", 0))
        special = data.get("special_event_status", "standard")
        base = int(float(market["market_size"]) * 0.0018)
        enthusiasm = float(market["wrestling_enthusiasm"]) / 50
        economy = float(market["economic_health"]) / 60
        competition = 1 - (float(market["competition_density"]) / 250)
        reputation = float(market["local_reputation"]) / 60
        card = 0.65 + card_quality / 100
        marketing_mod = min(0.35, marketing / 100000)
        special_mod = 1.28 if special in {"ppv", "anniversary", "themed"} else 1.0
        projection = base * enthusiasm * economy * competition * reputation * card * (1 + marketing_mod) * special_mod
        low = max(0, int(projection * 0.82))
        high = max(low + 1, int(projection * 1.18))
        actual = int(data["actual_attendance"]) if "actual_attendance" in data else None
        if actual is None and data.get("simulate_actual"):
            rng = self._rng(data.get("seed"), data["show_id"], data["market_id"], year, week)
            weather_hit = 1 - (float(market["weather_risk"]) / 500 if rng.random() < float(market["weather_risk"]) / 100 else 0)
            actual = int(projection * weather_hit * rng.uniform(0.91, 1.09))
        ticket_revenue = int((actual or int((low + high) / 2)) * int(data.get("average_ticket_price", 55)))
        record = self.repo.insert_simple(
            "attendance_records",
            {
                "id": data.get("id") or new_id("attendance"),
                "show_id": data["show_id"],
                "market_id": data["market_id"],
                "show_name": data["show_name"],
                "projected_low": low,
                "projected_high": high,
                "actual_attendance": actual,
                "ticket_revenue": ticket_revenue,
                "card_quality": card_quality,
                "marketing_spend": marketing,
                "special_event_status": special,
                "factors_json": {
                    "base": base,
                    "enthusiasm": enthusiasm,
                    "economy": economy,
                    "competition": competition,
                    "reputation": reputation,
                    "card": card,
                    "marketing_mod": marketing_mod,
                    "special_mod": special_mod,
                },
                "year": year,
                "week": week,
                "updated_at": self.repo.now(),
            },
        )
        return record

    def run_aging(self, year: int, week: int, seed: int | None = None) -> dict:
        existing = self.repo.get_job("annual_aging_effects", year, week)
        if existing and existing["status"] == "completed":
            return {"already_ran": True, **(existing.get("result_json") or {})}
        wrestlers = self.repo.get_wrestlers()
        snapshots = 0
        with self.repo.transaction():
            for wrestler in wrestlers:
                age = int(wrestler.get("age", 30) or 30)
                if age < 32:
                    continue
                style = wrestler.get("primary_wrestling_style") or ("high_flying" if float(wrestler.get("speed", 50)) >= 75 else "technical" if float(wrestler.get("technical", 50)) >= 75 else "hybrid")
                style_wear = 1.35 if style == "high_flying" else 1.10 if style == "brawling" else 0.85 if style == "technical" else 1.0
                injury_rows = self.repo.fetch_all(
                    "SELECT severity FROM dev_training_injuries WHERE wrestler_id = ? AND deleted_at IS NULL",
                    (wrestler["id"],),
                )
                injury_legacy = sum({"minor": 0.3, "moderate": 0.8, "significant": 1.6, "severe": 3.0}.get(row["severity"], 0.5) for row in injury_rows)
                over_35 = max(0, age - 35)
                physical_decline = round(-(over_35 * 0.18 * style_wear + injury_legacy * 0.08), 3)
                intangible_growth = round(max(0, min(1.2, (age - 32) * 0.06)), 3)
                graceful = self.clamp(float(wrestler.get("stamina", 50)) * 0.35 + float((self.repo.get_locker_state(wrestler["id"]) or {}).get("professionalism", 60)) * 0.45 - injury_legacy * 4)
                self.repo.insert_simple(
                    "aging_snapshots",
                    {
                        "id": f"aging_{wrestler['id']}_{year}_{week}",
                        "wrestler_id": wrestler["id"],
                        "wrestler_name": wrestler["name"],
                        "age": age,
                        "style_profile": style,
                        "physical_delta_json": {"speed": physical_decline, "stamina": physical_decline * 0.8, "brawling": physical_decline * 0.45},
                        "intangible_delta_json": {"psychology": intangible_growth, "mic": intangible_growth * 0.7},
                        "injury_legacy_modifier": round(injury_legacy, 2),
                        "career_wear_score": round(over_35 * style_wear + injury_legacy, 2),
                        "graceful_aging_score": round(graceful, 2),
                        "year": year,
                        "week": week,
                    },
                    commit=False,
                )
                snapshots += 1
        result = {"aging_snapshots": snapshots}
        self.repo.upsert_job({"job_type": "annual_aging_effects", "year": year, "week": week, "status": "completed", "seed": seed, "reads": ["wrestlers", "dev_training_injuries"], "writes": ["aging_snapshots"], "result": result})
        return {"already_ran": False, **result}

    def run_industry_evolution(self, year: int, week: int) -> dict:
        existing = self.repo.fetch_one(
            "SELECT * FROM industry_trend_snapshots WHERE year = ? AND week = ?",
            (year, week),
        )
        if existing:
            return existing
        eras = self.repo.fetch_all(
            "SELECT * FROM industry_eras WHERE deleted_at IS NULL ORDER BY start_year DESC, start_week DESC"
        )
        active = next((era for era in eras if (int(era["start_year"]) * 52 + int(era["start_week"])) <= (year * 52 + week)), eras[-1] if eras else None)
        if not active:
            raise ValidationError("No industry eras configured")
        taste = dict(active.get("audience_preferences_json") or {})
        pressure = self.clamp(45 + (year - 1) * 2.2)
        sensitivity = self.clamp(42 + (year - 1) * 2.5)
        record = self.repo.insert_simple(
            "industry_trend_snapshots",
            {
                "id": f"industry_trend_{year}_{week}",
                "year": year,
                "week": week,
                "active_era_id": active["id"],
                "audience_taste_json": taste,
                "competitor_pressure": round(pressure, 2),
                "technology_options_json": active.get("technology_json") or {},
                "cultural_sensitivity": round(sensitivity, 2),
            },
        )
        return record

    def assign_brand(self, data: dict) -> dict:
        if not data.get("wrestler_id") or not data.get("to_brand"):
            raise ValidationError("wrestler_id and to_brand are required")
        year, week = self._state_week(data)
        self._ensure_locker_states()
        state = self.repo.get_locker_state(data["wrestler_id"])
        wrestler = self.repo.get_wrestler(data["wrestler_id"])
        if not state and not wrestler:
            raise ValidationError("Wrestler not found")
        from_brand = (state or {}).get("brand", (wrestler or {}).get("primary_brand"))
        name = (state or {}).get("wrestler_name", (wrestler or {}).get("name", data["wrestler_id"]))
        with self.repo.transaction():
            if state:
                self.repo.upsert_locker_state({**state, "brand": data["to_brand"]}, commit=False)
            self.repo.conn.execute("UPDATE wrestlers SET primary_brand = ?, updated_at = ? WHERE id = ?", (data["to_brand"], self.repo.now(), data["wrestler_id"]))
            row = self.repo.insert_simple(
                "brand_assignment_history",
                {
                    "id": new_id("brand_assignment"),
                    "wrestler_id": data["wrestler_id"],
                    "wrestler_name": name,
                    "from_brand": from_brand,
                    "to_brand": data["to_brand"],
                    "transfer_reason": data.get("transfer_reason", "brand_management"),
                    "on_screen_justification": data.get("on_screen_justification", ""),
                    "year": year,
                    "week": week,
                },
                commit=False,
            )
        return row

    def update_endgame_progress(self, year: int, week: int) -> dict:
        objectives = self.repo.list_endgame_objectives()
        metrics = self._endgame_metrics()
        achieved = []
        with self.repo.transaction():
            for obj in objectives:
                current = float(metrics.get(obj["target_metric"], 0))
                target = float(obj["target_value"])
                progress = 100 if target <= 0 else self.clamp((current / target) * 100)
                status = obj["status"]
                if progress >= 100 and status != "achieved":
                    status = "achieved"
                    achieved.append(obj)
                    self.repo.insert_simple(
                        "endgame_recognition_events",
                        {
                            "id": new_id("endgame_recognition"),
                            "objective_id": obj["id"],
                            "title": f"Objective achieved: {obj['objective_name']}",
                            "description": f"{obj['objective_name']} reached {current:.0f} against a target of {target:.0f}.",
                            "legacy_score_delta": 10,
                            "year": year,
                            "week": week,
                        },
                        commit=False,
                    )
                self.repo.conn.execute(
                    """
                    UPDATE endgame_objectives
                    SET current_value = ?, progress_pct = ?, status = ?,
                        achieved_year = CASE WHEN ? = 'achieved' AND achieved_year IS NULL THEN ? ELSE achieved_year END,
                        achieved_week = CASE WHEN ? = 'achieved' AND achieved_week IS NULL THEN ? ELSE achieved_week END,
                        evidence_json = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (current, round(progress, 2), status, status, year, status, week, self.repo.to_json({"metrics": metrics}), self.repo.now(), obj["id"]),
                )
        return {"objectives": self.repo.list_endgame_objectives(), "newly_achieved": len(achieved)}

    def _endgame_metrics(self) -> dict:
        ratings = self.repo.fetch_one("SELECT AVG(total_viewership) AS avg_viewership FROM tv_ratings WHERE deleted_at IS NULL")
        revenue = self.repo.fetch_one("SELECT SUM(ticket_revenue) AS revenue FROM attendance_records WHERE deleted_at IS NULL")
        hof = self.repo.fetch_one("SELECT COUNT(*) AS total FROM hall_of_fame")
        legendary_heat = self.repo.fetch_one("SELECT COUNT(*) AS total FROM story_feuds WHERE heat_score >= 86 AND deleted_at IS NULL")
        return {
            "avg_viewership": float((ratings or {}).get("avg_viewership") or 0),
            "annual_revenue": float((revenue or {}).get("revenue") or 0),
            "hall_of_fame_count": float((hof or {}).get("total") or 0),
            "legendary_heat_count": float((legendary_heat or {}).get("total") or 0),
        }

    # ------------------------------------------------------------------
    # Dynamic event system
    # ------------------------------------------------------------------

    def sync_dynamic_event_audit(self) -> list[dict]:
        now = self.repo.now()
        with self.repo.transaction():
            for feature_key, name, status, systems, notes in DYNAMIC_EVENT_AUDIT:
                self.repo.conn.execute(
                    """
                    INSERT INTO dynamic_event_feature_audit (
                        id, feature_key, feature_name, overlap_status,
                        existing_systems_json, implemented_in_dynamic_events,
                        notes, updated_at
                    ) VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                    ON CONFLICT(feature_key) DO UPDATE SET
                        feature_name = excluded.feature_name,
                        overlap_status = excluded.overlap_status,
                        existing_systems_json = excluded.existing_systems_json,
                        implemented_in_dynamic_events = 1,
                        notes = excluded.notes,
                        updated_at = excluded.updated_at
                    """,
                    (
                        f"dyn_audit_{feature_key}",
                        feature_key,
                        name,
                        status,
                        self.repo.to_json(systems),
                        notes,
                        now,
                    ),
                )
        return self.repo.fetch_all("SELECT * FROM dynamic_event_feature_audit ORDER BY feature_key")

    def dynamic_event_dashboard(self) -> dict:
        self.sync_dynamic_event_audit()
        open_events = self.repo.fetch_all(
            """
            SELECT * FROM dynamic_event_records
            WHERE status = 'open' AND deleted_at IS NULL
            ORDER BY severity_score DESC, year DESC, week DESC
            LIMIT 25
            """
        )
        recent_events = self.repo.fetch_all(
            """
            SELECT * FROM dynamic_event_records
            WHERE deleted_at IS NULL
            ORDER BY year DESC, week DESC, created_at DESC
            LIMIT 30
            """
        )
        by_category = {}
        for event in recent_events:
            by_category[event["category"]] = by_category.get(event["category"], 0) + 1
        return {
            "audit": self.repo.fetch_all("SELECT * FROM dynamic_event_feature_audit ORDER BY feature_key"),
            "open_events": open_events,
            "recent_events": recent_events,
            "summary": {
                "open": len(open_events),
                "urgent": len([event for event in open_events if event["urgency"] == "urgent"]),
                "covered_features": len(EVENT_DEFINITIONS),
                "recent_by_category": by_category,
            },
        }

    def dynamic_event_pulse(self, data: dict | None = None) -> dict:
        """Occasionally create or surface a dynamic event outside the event hub."""

        data = data or {}
        year, week = self._state_week(data)
        context = data.get("context") or "global"
        force = bool(data.get("force"))
        chance = float(data.get("chance", 0.025 if context == "global" else 0.12))
        rng = random.Random(data.get("seed")) if data.get("seed") is not None else random.Random()

        open_events = self.repo.fetch_all(
            """
            SELECT * FROM dynamic_event_records
            WHERE status = 'open' AND deleted_at IS NULL
            ORDER BY urgency DESC, severity_score DESC, created_at DESC
            LIMIT 5
            """
        )
        if open_events and not force and not data.get("allow_multiple_open"):
            return {
                "triggered": False,
                "reason": "open_events_pending",
                "events": [],
                "open_events": open_events,
            }

        recent_context = self.repo.fetch_one(
            """
            SELECT COUNT(*) AS total
            FROM dynamic_event_records
            WHERE year = ? AND week = ? AND deleted_at IS NULL
              AND payload_json LIKE ?
            """,
            (year, week, f'%"pulse_context": "{context}"%'),
        )
        if recent_context and int(recent_context["total"] or 0) > 0 and not force:
            return {
                "triggered": False,
                "reason": "context_cooldown",
                "events": [],
                "open_events": open_events,
            }

        roll = rng.random()
        if not force and roll > chance:
            return {
                "triggered": False,
                "reason": "roll_missed",
                "roll": round(roll, 4),
                "chance": round(chance, 4),
                "events": [],
                "open_events": open_events,
            }

        event_type = data.get("event_type") or self._pulse_event_type(context, rng)
        run_data = {
            **data,
            "force": True,
            "event_type": event_type,
            "max_events": 1,
            "guarantee_event": True,
            "pulse_context": context,
            "origin": data.get("origin") or "dynamic_pulse",
        }
        result = self.run_dynamic_events(year, week, data.get("seed"), run_data)
        return {
            "triggered": bool(result.get("created")),
            "reason": "triggered" if result.get("created") else "not_created",
            "chance": round(chance, 4),
            "events": result.get("events", []),
            "open_events": self.dynamic_event_dashboard()["open_events"],
        }

    def _pulse_event_type(self, context: str, rng: random.Random) -> str:
        if context.startswith("show"):
            pool = [
                "match_injury_rebooking",
                "wrestler_no_show",
                "organic_alignment_turn",
                "backstage_fight",
                "storyline_leak",
                "network_interference",
                "viral_social_moment",
            ]
        elif context.startswith("booking"):
            pool = [
                "wrestler_no_show",
                "veteran_refuses_putover",
                "title_ultimatum",
                "storyline_leak",
                "network_interference",
            ]
        else:
            pool = list(EVENT_DEFINITIONS.keys())
        return rng.choice(pool)

    def run_dynamic_events(self, year: int, week: int, seed: int | None = None, data: dict | None = None) -> dict:
        data = data or {}
        existing = self.repo.get_job("weekly_dynamic_events", year, week)
        if existing and existing["status"] == "completed" and not data.get("force"):
            return {"already_ran": True, **(existing.get("result_json") or {})}

        self.sync_dynamic_event_audit()
        self._ensure_locker_states()
        rng = self._rng(seed, year, week, "dynamic-events")
        wrestlers = self.repo.get_wrestlers()
        states = {row["wrestler_id"]: row for row in self.repo.list_locker_states()}
        forced_type = data.get("event_type")
        events_to_insert = []

        if forced_type:
            if forced_type not in EVENT_DEFINITIONS:
                raise ValidationError("Unsupported dynamic event_type")
            events_to_insert.append(self._build_dynamic_event(forced_type, wrestlers, states, year, week, rng, data))
        else:
            scored = []
            for event_type in EVENT_DEFINITIONS:
                probability = self._dynamic_event_probability(event_type, wrestlers, states, year, week)
                roll = rng.random()
                if roll < probability:
                    scored.append((probability - roll, event_type))
            scored.sort(reverse=True)
            for _, event_type in scored[: int(data.get("max_events", 4) or 4)]:
                events_to_insert.append(self._build_dynamic_event(event_type, wrestlers, states, year, week, rng, data))
            if not events_to_insert and data.get("guarantee_event", True):
                weighted = sorted(
                    ((self._dynamic_event_probability(event_type, wrestlers, states, year, week), event_type) for event_type in EVENT_DEFINITIONS),
                    reverse=True,
                )
                top_pool = [event_type for _, event_type in weighted[:6]]
                events_to_insert.append(self._build_dynamic_event(rng.choice(top_pool), wrestlers, states, year, week, rng, data))

        created = []
        with self.repo.transaction():
            for event in events_to_insert:
                created.append(self.repo.insert_simple("dynamic_event_records", event, commit=False))

        story_reviews = []
        if created:
            try:
                from services.booking_story_media_service import BookingStoryMediaService

                story_service = BookingStoryMediaService(self.database)
                for event in created:
                    review = story_service.handle_story_disruption_event(event)
                    if review and review.get("id"):
                        story_reviews.append(review["id"])
            except Exception:
                story_reviews = []

        result = {
            "created": len(created),
            "events": created,
            "story_reviews": story_reviews,
            "open_total": len(self.dynamic_event_dashboard()["open_events"]),
        }
        self.repo.upsert_job(
            {
                "job_type": "weekly_dynamic_events",
                "year": year,
                "week": week,
                "status": "completed",
                "seed": seed,
                "reads": ["wrestlers", "locker_wrestler_state", "match_history", "network_relationships", "attendance_records", "story_arcs"],
                "writes": ["dynamic_event_records", "dynamic_event_feature_audit", "story_arc_reviews"],
                "result": {"created": result["created"], "event_ids": [event["id"] for event in created], "story_review_ids": story_reviews},
            }
        )
        return {"already_ran": False, **result}

    def _dynamic_event_probability(self, event_type: str, wrestlers: list[dict], states: dict, year: int, week: int) -> float:
        if not wrestlers:
            return 0.0
        avg_morale = mean(float(states.get(w["id"], {}).get("morale_score", w.get("morale", 50) or 50)) for w in wrestlers)
        high_fatigue = len([w for w in wrestlers if int(w.get("fatigue", 0) or 0) >= 45])
        older = len([w for w in wrestlers if int(w.get("age", 30) or 30) >= 38])
        expiring = len([w for w in wrestlers if int(w.get("contract_weeks_remaining", 52) or 52) <= 12])
        stars = len([w for w in wrestlers if int(w.get("is_major_superstar", 0) or 0) or int(w.get("popularity", 50) or 50) >= 82])
        high_ego = len([s for s in states.values() if float(s.get("ego_level", 0) or 0) >= 62])
        low_prof = len([s for s in states.values() if float(s.get("professionalism", 60) or 60) <= 42])
        base = 0.035
        modifiers = {
            "match_injury_rebooking": base + (high_fatigue + older) / max(1, len(wrestlers)) * 0.12,
            "wrestler_no_show": base + expiring / max(1, len(wrestlers)) * 0.14 + max(0, 45 - avg_morale) / 500,
            "viral_social_moment": 0.075,
            "backstage_fight": base + high_ego * 0.012 + low_prof * 0.015 + max(0, 45 - avg_morale) / 420,
            "show_cancellation": 0.025 + (week in {1, 13, 26, 39}) * 0.03,
            "organic_alignment_turn": 0.045 + stars * 0.006,
            "retirement_announcement": base + older / max(1, len(wrestlers)) * 0.12,
            "drug_test_failure": 0.025 + high_fatigue * 0.006 + max(0, 40 - avg_morale) / 650,
            "media_scandal": 0.035 + low_prof * 0.012,
            "network_interference": 0.04 + (week % 4 == 0) * 0.035,
            "power_clique": 0.035 + high_ego * 0.01,
            "veteran_refuses_putover": 0.03 + older * 0.008 + high_ego * 0.008,
            "group_demands": 0.025 + max(0, 48 - avg_morale) / 360,
            "title_ultimatum": 0.025 + stars * 0.012 + expiring * 0.01,
            "style_friction": 0.04,
            "storyline_leak": 0.035 + high_ego * 0.006,
        }
        return min(0.35, float(modifiers.get(event_type, base)))

    def _build_dynamic_event(self, event_type: str, wrestlers: list[dict], states: dict, year: int, week: int, rng: random.Random, data: dict) -> dict:
        definition = EVENT_DEFINITIONS[event_type]
        primary = self._pick_primary_for_event(event_type, wrestlers, states, rng, data)
        secondary = self._pick_secondary(primary, wrestlers, rng)
        severity_score = self._dynamic_severity(event_type, primary, secondary, states, rng)
        severity_level = self._severity_level(definition["severity_levels"], severity_score)
        brand = data.get("brand") or primary.get("primary_brand") or "ROC Alpha"
        show = self._latest_show_context(year, week)
        title = self._event_title(event_type, primary, secondary, severity_level)
        summary = self._event_summary(event_type, primary, secondary, severity_level)
        triggers = self._event_triggers(event_type, primary, secondary, states, severity_score)
        options = definition["options"]
        return {
            "id": new_id("dynamic_event"),
            "event_type": event_type,
            "category": definition["category"],
            "title": title,
            "summary": summary,
            "severity_level": severity_level,
            "severity_score": round(severity_score, 2),
            "urgency": "urgent" if severity_score >= 74 or event_type in {"match_injury_rebooking", "show_cancellation", "media_scandal"} else "normal",
            "status": "open",
            "brand": brand,
            "show_id": data.get("show_id") or show.get("show_id"),
            "show_name": data.get("show_name") or show.get("show_name"),
            "primary_wrestler_id": primary.get("id"),
            "primary_wrestler_name": primary.get("name"),
            "secondary_wrestler_id": secondary.get("id") if secondary else None,
            "secondary_wrestler_name": secondary.get("name") if secondary else None,
            "source_system": "dynamic_events",
            "trigger_conditions_json": triggers,
            "payload_json": {
                "existing_overlap": next((row[4] for row in DYNAMIC_EVENT_AUDIT if row[0] == event_type), ""),
                "pulse_context": data.get("pulse_context"),
                "origin": data.get("origin") or "weekly_dynamic_events",
                "requires_booking_response": event_type in {"match_injury_rebooking", "wrestler_no_show", "show_cancellation", "retirement_announcement", "network_interference"},
                "investigation_required": event_type in {"backstage_fight", "media_scandal", "storyline_leak", "drug_test_failure"},
            },
            "response_options_json": options,
            "mechanical_effects_json": {"pending": True, "available_options": [option["key"] for option in options]},
            "year": year,
            "week": week,
            "updated_at": self.repo.now(),
        }

    def _pick_primary_for_event(self, event_type: str, wrestlers: list[dict], states: dict, rng: random.Random, data: dict) -> dict:
        if data.get("wrestler_id"):
            wrestler = self.repo.get_wrestler(data["wrestler_id"])
            if wrestler:
                return wrestler
        candidates = list(wrestlers)
        if event_type in {"retirement_announcement", "veteran_refuses_putover"}:
            candidates = [w for w in wrestlers if int(w.get("age", 30) or 30) >= 36 or int(w.get("years_experience", 0) or 0) >= 12] or wrestlers
        elif event_type in {"title_ultimatum", "network_interference", "viral_social_moment"}:
            candidates = [w for w in wrestlers if int(w.get("popularity", 50) or 50) >= 70 or int(w.get("is_major_superstar", 0) or 0)] or wrestlers
        elif event_type in {"wrestler_no_show", "group_demands"}:
            candidates = [w for w in wrestlers if int(w.get("contract_weeks_remaining", 52) or 52) <= 16 or int(w.get("morale", 50) or 50) < 45] or wrestlers
        elif event_type in {"match_injury_rebooking", "drug_test_failure"}:
            candidates = [w for w in wrestlers if int(w.get("fatigue", 0) or 0) >= 25 or int(w.get("age", 30) or 30) >= 35] or wrestlers
        elif event_type in {"backstage_fight", "power_clique", "storyline_leak"}:
            candidates = [w for w in wrestlers if float(states.get(w["id"], {}).get("ego_level", 30) or 30) >= 50] or wrestlers
        return rng.choice(candidates)

    def _pick_secondary(self, primary: dict, wrestlers: list[dict], rng: random.Random) -> dict | None:
        others = [w for w in wrestlers if w.get("id") != primary.get("id")]
        return rng.choice(others) if others else None

    def _dynamic_severity(self, event_type: str, primary: dict, secondary: dict | None, states: dict, rng: random.Random) -> float:
        state = states.get(primary.get("id"), {})
        morale = float(state.get("morale_score", primary.get("morale", 50) or 50))
        ego = float(state.get("ego_level", 30) or 30)
        prof = float(state.get("professionalism", 60) or 60)
        fatigue = float(primary.get("fatigue", 0) or 0)
        age = float(primary.get("age", 30) or 30)
        popularity = float(primary.get("popularity", 50) or 50)
        score = 35 + rng.uniform(0, 25)
        score += max(0, 45 - morale) * 0.35
        score += max(0, ego - 55) * 0.25
        score += max(0, 45 - prof) * 0.35
        if event_type in {"match_injury_rebooking", "drug_test_failure"}:
            score += fatigue * 0.25 + max(0, age - 34) * 1.2
        if event_type in {"title_ultimatum", "network_interference", "viral_social_moment"}:
            score += max(0, popularity - 70) * 0.45
        if event_type in {"show_cancellation", "media_scandal", "storyline_leak"}:
            score += rng.uniform(8, 20)
        return self.clamp(score)

    def _severity_level(self, levels: tuple[str, ...], score: float) -> str:
        if score >= 82 and len(levels) >= 4:
            return levels[3]
        if score >= 68 and len(levels) >= 3:
            return levels[2]
        if score >= 50 and len(levels) >= 2:
            return levels[1]
        return levels[0]

    def _event_title(self, event_type: str, primary: dict, secondary: dict | None, severity_level: str) -> str:
        name = primary.get("name", "Unknown Talent")
        other = secondary.get("name", "another wrestler") if secondary else "another wrestler"
        titles = {
            "match_injury_rebooking": f"{name} injured during match: {severity_level.replace('_', ' ')}",
            "wrestler_no_show": f"{name} no-shows: {severity_level.replace('_', ' ')}",
            "viral_social_moment": f"{name} goes viral",
            "backstage_fight": f"Backstage fight: {name} and {other}",
            "show_cancellation": "World event threatens scheduled show",
            "organic_alignment_turn": f"Crowd organically shifts on {name}",
            "retirement_announcement": f"{name} signals retirement",
            "drug_test_failure": f"{name} fails wellness test",
            "media_scandal": f"Media scandal involving {name}",
            "network_interference": "Network partner demands creative changes",
            "power_clique": f"{name} becomes center of locker room power bloc",
            "veteran_refuses_putover": f"{name} resists putting over younger talent",
            "group_demands": f"{name} fronts collective roster demands",
            "title_ultimatum": f"{name} issues championship ultimatum",
            "style_friction": f"Style philosophy conflict around {name}",
            "storyline_leak": f"Storyline leak traced near {name}",
        }
        return titles.get(event_type, event_type.replace("_", " ").title())

    def _event_summary(self, event_type: str, primary: dict, secondary: dict | None, severity_level: str) -> str:
        return (
            f"{EVENT_DEFINITIONS[event_type]['category'].replace('_', ' ').title()} event generated at "
            f"{severity_level.replace('_', ' ')} severity. Management response is required and will persist "
            "with mechanical consequences."
        )

    def _event_triggers(self, event_type: str, primary: dict, secondary: dict | None, states: dict, severity_score: float) -> dict:
        state = states.get(primary.get("id"), {})
        return {
            "event_type": event_type,
            "severity_score": round(severity_score, 2),
            "primary_popularity": primary.get("popularity", 50),
            "primary_morale": state.get("morale_score", primary.get("morale", 50)),
            "primary_ego": state.get("ego_level", 30),
            "primary_professionalism": state.get("professionalism", 60),
            "contract_weeks_remaining": primary.get("contract_weeks_remaining", 0),
            "fatigue": primary.get("fatigue", 0),
            "secondary_wrestler": secondary.get("name") if secondary else None,
        }

    def _latest_show_context(self, year: int, week: int) -> dict:
        row = self.repo.fetch_one(
            """
            SELECT show_id, show_name
            FROM match_history
            WHERE year <= ? AND week <= ?
            ORDER BY year DESC, week DESC
            LIMIT 1
            """,
            (year, week),
        )
        return row or {"show_id": None, "show_name": "Upcoming Show"}

    def resolve_dynamic_event(self, event_id: str, data: dict) -> dict:
        event = self.repo.fetch_one(
            "SELECT * FROM dynamic_event_records WHERE id = ? AND deleted_at IS NULL",
            (event_id,),
        )
        if not event:
            raise ValidationError("Dynamic event not found")
        if event["status"] != "open":
            raise ValidationError("Dynamic event is already resolved")
        choice = data.get("choice")
        options = event.get("response_options_json") or []
        selected = next((option for option in options if option.get("key") == choice), None)
        if not selected:
            raise ValidationError("Invalid response choice")
        effects = dict(selected.get("effects") or {})
        effects["choice"] = choice
        impacts = []
        with self.repo.transaction():
            for wrestler_id, wrestler_name in (
                (event.get("primary_wrestler_id"), event.get("primary_wrestler_name")),
                (event.get("secondary_wrestler_id"), event.get("secondary_wrestler_name")),
            ):
                if wrestler_id:
                    impacts.extend(self._apply_dynamic_wrestler_effects(event, wrestler_id, wrestler_name, effects))
            for impact_type in ("finance_delta", "network_delta", "sponsor_delta", "trust_delta", "atmosphere_delta", "legacy_delta", "kayfabe_delta", "development_delta", "crowd_delta", "local_reputation_delta"):
                if effects.get(impact_type):
                    impacts.append(self._insert_dynamic_impact(event_id, "promotion", None, "Promotion", impact_type, effects[impact_type], {"choice": choice}))
            self.repo.conn.execute(
                """
                UPDATE dynamic_event_records
                SET status = 'resolved',
                    selected_response = ?,
                    resolution_summary = ?,
                    mechanical_effects_json = ?,
                    updated_at = ?,
                    resolved_at = ?
                WHERE id = ?
                """,
                (
                    choice,
                    data.get("notes") or selected.get("label") or choice,
                    self.repo.to_json(effects),
                    self.repo.now(),
                    self.repo.now(),
                    event_id,
                ),
            )
        return {
            "event": self.repo.fetch_one("SELECT * FROM dynamic_event_records WHERE id = ?", (event_id,)),
            "impacts": impacts,
        }

    def _apply_dynamic_wrestler_effects(self, event: dict, wrestler_id: str, wrestler_name: str, effects: dict) -> list[dict]:
        impacts = []
        wrestler = self.repo.get_wrestler(wrestler_id)
        if not wrestler:
            return impacts
        updates = {}
        for column, key in (("morale", "morale_delta"), ("popularity", "popularity_delta"), ("momentum", "momentum_delta"), ("fatigue", "fatigue_delta")):
            if effects.get(key):
                current = float(wrestler.get(column, 50 if column != "fatigue" else 0) or 0)
                updates[column] = int(self.clamp(current + float(effects[key]), 0, 100 if column != "momentum" else 999))
                impacts.append(self._insert_dynamic_impact(event["id"], "wrestler", wrestler_id, wrestler_name, key, effects[key], {"column": column}))
        if event["event_type"] == "match_injury_rebooking" and event["severity_level"] in {"moderate", "serious", "career_threatening"}:
            weeks = {"moderate": 6, "serious": 18, "career_threatening": 36}.get(event["severity_level"], 3)
            updates["injury_severity"] = "Serious" if weeks >= 18 else "Moderate"
            updates["injury_description"] = event["title"]
            updates["injury_weeks_remaining"] = weeks
            impacts.append(self._insert_dynamic_impact(event["id"], "wrestler", wrestler_id, wrestler_name, "injury_weeks", weeks, {"severity": event["severity_level"]}))
        if event["event_type"] == "retirement_announcement" and effects.get("choice") == "immediate_writeoff":
            updates["is_retired"] = 1
            impacts.append(self._insert_dynamic_impact(event["id"], "wrestler", wrestler_id, wrestler_name, "retired", 1, {"reason": "dynamic_event"}))
        if updates:
            updates["updated_at"] = self.repo.now()
            assignments = ", ".join(f"{key} = ?" for key in updates)
            self.repo.conn.execute(
                f"UPDATE wrestlers SET {assignments} WHERE id = ?",
                tuple(updates.values()) + (wrestler_id,),
            )
        state = self.repo.get_locker_state(wrestler_id)
        if state and (effects.get("morale_delta") or effects.get("professionalism_delta")):
            morale = self.clamp(float(state["morale_score"]) + float(effects.get("morale_delta", 0)))
            professionalism = self.clamp(float(state["professionalism"]) + float(effects.get("professionalism_delta", 0)))
            self.repo.upsert_locker_state(
                {
                    **state,
                    "morale_score": round(morale, 2),
                    "morale_level": self._level(morale, "morale"),
                    "professionalism": round(professionalism, 2),
                },
                commit=False,
            )
        return impacts

    def _insert_dynamic_impact(self, event_id: str, target_type: str, target_id: str | None, target_name: str | None, impact_type: str, value_delta: float, details: dict) -> dict:
        return self.repo.insert_simple(
            "dynamic_event_impacts",
            {
                "id": new_id("dynamic_impact"),
                "event_id": event_id,
                "target_type": target_type,
                "target_id": target_id,
                "target_name": target_name,
                "impact_type": impact_type,
                "value_delta": float(value_delta),
                "details_json": details,
            },
            commit=False,
        )

    def advanced_dashboard(self) -> dict:
        year, week = self._state_week()
        return {
            "match_scripts": self.repo.fetch_all("SELECT * FROM advanced_match_scripts WHERE deleted_at IS NULL ORDER BY created_at DESC LIMIT 20"),
            "production_history": self.repo.recent_rows("production_quality_history", 12),
            "attendance": self.repo.recent_rows("attendance_records", 12),
            "aging": self.repo.recent_rows("aging_snapshots", 12),
            "industry": self.repo.fetch_all("SELECT * FROM industry_trend_snapshots ORDER BY year DESC, week DESC LIMIT 8"),
            "brands": self.repo.fetch_all("SELECT * FROM brand_entities WHERE deleted_at IS NULL ORDER BY brand_name"),
            "endgame": self.update_endgame_progress(year, week)["objectives"],
        }

    def run_weekly_simulation(self, year: int, week: int, seed: int | None = None) -> dict:
        culture = self.run_weekly_culture(year, week, seed)
        development = self.run_development_week(year, week, seed)
        industry = self.run_industry_evolution(year, week)
        dynamic_events = self.run_dynamic_events(year, week, seed)
        endgame = self.update_endgame_progress(year, week)
        return {
            "culture": culture,
            "development": development,
            "industry": industry,
            "dynamic_events": dynamic_events,
            "endgame": endgame,
        }
