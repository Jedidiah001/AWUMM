"""
Business logic for booking, storyline, ratings, media, and business simulation.

Controllers call this service; this service calls the repository. Calculations are
kept here so they can be unit tested without Flask.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Any

from repositories.phase_expansion_repository import PhaseExpansionRepository, new_id


RUNTIME_BY_SHOW_TYPE = {
    "weekly_tv": 120,
    "minor_ppv": 180,
    "major_ppv": 240,
    "premium_live_event": 210,
}

MANDATORY_BREAKS_BY_SHOW_TYPE = {
    "weekly_tv": 8,
    "minor_ppv": 0,
    "major_ppv": 0,
    "premium_live_event": 0,
}

SEGMENT_DURATION_RANGES = {
    "promo": (4, 10),
    "promo_battle": (7, 14),
    "interview": (3, 7),
    "announcement": (4, 8),
    "backstage": (3, 8),
    "backstage_attack": (3, 6),
    "in_ring_attack": (3, 8),
    "run_in": (2, 6),
    "brawl": (4, 9),
    "contract_signing": (8, 15),
    "vignette": (2, 5),
    "confrontation": (5, 10),
    "debut": (4, 10),
    "return": (4, 10),
    "match": (7, 16),
    "singles": (8, 14),
    "tag": (10, 16),
    "trios_tag": (11, 18),
    "triple_threat": (11, 17),
    "fatal_4way": (12, 18),
    "battle_royal": (14, 24),
    "rumble": (45, 65),
    "elimination_chamber": (28, 42),
    "main_event_title_match": (18, 32),
}

ACTION_BASE_HEAT = {
    "in_ring_brawl": 7,
    "locker_room_attack": 8,
    "parking_lot_ambush": 10,
    "post_match_beatdown": 9,
    "promo_challenge": 5,
    "response_promo": 4,
    "in_ring_confrontation": 5,
    "contract_signing": 9,
    "video_package": 3,
    "rival_match_interference": 8,
    "title_sabotage": 10,
    "milestone_interference": 9,
    "ally_attack": 8,
    "personal_property": 12,
    "family_involvement": 14,
    "public_humiliation": 13,
    "secret_revelation": 15,
    "career_threat": 16,
}

PERSONAL_ESCALATION_ACTIONS = {
    "personal_property",
    "family_involvement",
    "public_humiliation",
    "secret_revelation",
    "career_threat",
}

DEMO_SPLIT = {
    "male_18_49": (0.38, 1.55),
    "adult_female": (0.20, 1.05),
    "teenage": (0.16, 0.90),
    "family_children": (0.14, 0.80),
    "casual_viewer": (0.12, 1.25),
}

STORY_ARC_TEMPLATE_SEEDS = [
    ("classic_babyface_chase", "Classic Babyface Chase", "tier_1_main_event", 10, 14, 2, 3, "medium", "very_high"),
    ("heel_authority_corruption", "Heel Authority Corruption", "tier_1_main_event", 16, 24, 5, 8, "very_high", "high"),
    ("tournament_of_destiny", "Tournament of Destiny", "tier_2_midcard", 6, 8, 8, 16, "high", "high"),
    ("betrayal_and_revenge", "Betrayal and Revenge", "tier_1_main_event", 12, 18, 2, 4, "medium", "very_high"),
    ("unlikely_tag_alliance", "Unlikely Tag Alliance", "tier_3_undercard", 8, 12, 2, 3, "low_medium", "high"),
    ("generational_warfare", "Generational Warfare", "tier_4_background", 20, 30, 6, 10, "very_high", "medium_high"),
    ("underdog_redemption", "Underdog Redemption", "tier_2_midcard", 8, 12, 2, 3, "low", "very_high"),
    ("faction_civil_war", "Faction Civil War", "tier_4_background", 16, 20, 6, 12, "very_high", "medium"),
    ("mystery_attacker", "Mystery Attacker Whodunit", "tier_4_background", 8, 16, 4, 8, "high", "medium_high"),
    ("champion_vs_monster", "Champion vs. Monster", "tier_1_main_event", 8, 10, 2, 3, "low_medium", "high"),
    ("passing_torch", "Passing of the Torch", "tier_2_midcard", 12, 16, 2, 4, "high", "very_high"),
    ("love_triangle", "Love Triangle Complication", "tier_3_undercard", 10, 14, 3, 4, "medium", "medium"),
]

MILESTONE_SCHEMA = [
    ("seed", "Seed Moment", 0, "low"),
    ("inciting_incident", "Inciting Incident", 2, "maximum"),
    ("escalation", "Escalation Beat", 4, "high"),
    ("flashpoint", "Flashpoint Event", 7, "maximum"),
    ("crisis_peak", "Crisis Peak", 10, "high"),
    ("payoff", "Payoff Moment", 12, "maximum"),
    ("aftermath", "Aftermath Thread", 13, "medium"),
]

ANNUAL_STORY_CALENDAR = [
    (1, "New Year Reset", "television_special", "tier_d", "Launch fresh feuds and reset character direction."),
    (5, "Rumble Direction Event", "premium_live_event", "tier_b", "Set first major yearly championship direction."),
    (12, "Spring Spectacular", "signature_event", "tier_a", "Deliver the year's first major payoff."),
    (18, "Mid-Spring Showcase", "premium_live_event", "tier_b", "Elevate mid-card and secondary title stories."),
    (26, "Summer Spectacular", "signature_event", "tier_a", "Second peak event for major title and faction arcs."),
    (35, "Fall Premiere", "television_special", "tier_d", "Reset television season and plant autumn stories."),
    (43, "Halloween Special", "special_event", "tier_c", "Exploit darker character and mystery storytelling."),
    (47, "Survival Tournament", "premium_live_event", "tier_b", "Multi-person and faction conflict payoff anchor."),
    (52, "Season Finale", "signature_event", "tier_a", "Conclude annual arcs and seed the next year."),
]


@dataclass
class FormulaContext:
    year: int = 1
    week: int = 1
    show_id: str | None = None
    show_name: str | None = None


class ValidationError(ValueError):
    pass


class BookingStoryMediaService:
    def __init__(self, database):
        self.database = database
        self.repo = PhaseExpansionRepository(database)

    # ------------------------------------------------------------------
    # Utility and validation
    # ------------------------------------------------------------------

    def clamp(self, value: float, low: float = 0.0, high: float = 100.0) -> float:
        return max(low, min(high, value))

    def _stable_variance(self, token: str, spread: int = 4) -> int:
        if not token:
            return 0
        return (sum(ord(ch) for ch in token) % ((spread * 2) + 1)) - spread

    def _total_week(self, year: int, week: int) -> int:
        return (int(year) * 52) + int(week)

    def heat_level(self, heat: float) -> str:
        if heat <= 15:
            return "cold"
        if heat <= 30:
            return "lukewarm"
        if heat <= 50:
            return "warm"
        if heat <= 70:
            return "hot"
        if heat <= 85:
            return "very_hot"
        return "nuclear"

    def network_break_count(self, show_type: str, relationship_score: float = 65.0) -> int:
        base = MANDATORY_BREAKS_BY_SHOW_TYPE.get(show_type, 6)
        if show_type in {"minor_ppv", "major_ppv", "premium_live_event"}:
            return 0
        if relationship_score >= 85:
            return max(4, base - 2)
        if relationship_score <= 35:
            return base + 2
        return base

    def get_config(self) -> dict:
        return {
            "lookups": self.repo.get_lookup_values(),
            "duration_ranges": SEGMENT_DURATION_RANGES,
            "theme_templates": self.repo.list_theme_templates(),
            "network": self.repo.get_primary_network(),
            "social_platforms": self.repo.get_social_metrics(),
        }

    def _row_or_attr(self, source: Any, key: str, default: Any = None) -> Any:
        if source is None:
            return default
        if isinstance(source, dict):
            return source.get(key, default)
        return getattr(source, key, default)

    def _wrestler_by_id(self, wrestler_id: str, universe=None) -> Any:
        if not wrestler_id:
            return None
        if universe and hasattr(universe, "get_wrestler_by_id"):
            wrestler = universe.get_wrestler_by_id(wrestler_id)
            if wrestler:
                return wrestler
        if hasattr(self.database, "get_wrestler_by_id"):
            return self.database.get_wrestler_by_id(wrestler_id)
        return None

    def _wrestler_name(self, wrestler_id: str, universe=None) -> str:
        wrestler = self._wrestler_by_id(wrestler_id, universe)
        return self._row_or_attr(wrestler, "name", wrestler_id)

    def _wrestler_metric(self, wrestler_id: str, metric: str, universe=None, default: float = 50.0) -> float:
        wrestler = self._wrestler_by_id(wrestler_id, universe)
        if wrestler is None:
            return default
        value = self._row_or_attr(wrestler, metric, default)
        if value is None and metric == "charisma":
            value = self._row_or_attr(wrestler, "mic", default)
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _participant_ids_from_match(self, match: Any) -> list[str]:
        side_a = self._row_or_attr(match, "side_a")
        side_b = self._row_or_attr(match, "side_b")
        ids: list[str] = []
        for side in (side_a, side_b):
            if isinstance(side, dict):
                ids.extend(side.get("wrestler_ids") or [])
            elif side is not None:
                ids.extend(getattr(side, "wrestler_ids", []) or [])
        return [wrestler_id for wrestler_id in ids if wrestler_id]

    def _participant_ids_from_segment(self, segment: Any) -> list[str]:
        ids: list[str] = []
        participants = self._row_or_attr(segment, "participants", []) or []
        for participant in participants:
            if isinstance(participant, dict):
                ids.append(participant.get("wrestler_id") or participant.get("id"))
            else:
                ids.append(getattr(participant, "wrestler_id", None) or getattr(participant, "id", None))
        return [wrestler_id for wrestler_id in ids if wrestler_id and wrestler_id not in {"interviewer", "authority"}]

    def _expected_range_for_item(self, item_type: str, segment_type: str, payload: Any) -> tuple[int, int]:
        if item_type == "match":
            match_type = self._row_or_attr(payload, "match_type", segment_type) or "match"
            is_title = bool(self._row_or_attr(payload, "is_title_match", False))
            importance = self._row_or_attr(payload, "importance", "normal")
            if is_title and importance in {"high_drama", "major"}:
                return SEGMENT_DURATION_RANGES["main_event_title_match"]
            return SEGMENT_DURATION_RANGES.get(match_type, SEGMENT_DURATION_RANGES["match"])
        return SEGMENT_DURATION_RANGES.get(segment_type, (3, 8))

    def _planned_duration_for_item(self, item_type: str, segment_type: str, payload: Any) -> int:
        explicit = self._row_or_attr(payload, "planned_duration_minutes")
        if explicit is not None:
            try:
                return max(1, int(explicit))
            except (TypeError, ValueError):
                pass
        if item_type == "segment":
            return int(self._row_or_attr(payload, "duration_minutes", self._row_or_attr(payload, "duration", 5)) or 5)
        low, high = self._expected_range_for_item(item_type, segment_type, payload)
        importance = self._row_or_attr(payload, "importance", "normal")
        position = int(self._row_or_attr(payload, "card_position", self._row_or_attr(payload, "position", 1)) or 1)
        bonus = 4 if importance == "high_drama" else 0
        if position >= 90:
            bonus += 3
        return min(high, max(low, int((low + high) / 2) + bonus))

    def _actual_duration_for_item(self, item_type: str, segment_type: str, payload: Any, universe=None) -> int:
        planned = self._planned_duration_for_item(item_type, segment_type, payload)
        if item_type == "segment":
            ids = self._participant_ids_from_segment(payload)
            metric = "mic"
        else:
            ids = self._participant_ids_from_match(payload)
            metric = "psychology"
        if not ids:
            return planned
        avg = sum(self._wrestler_metric(wid, metric, universe) for wid in ids) / len(ids)
        experience = sum(self._wrestler_metric(wid, "years_experience", universe, 5) for wid in ids) / len(ids)
        control = ((avg - 50) / 25.0) + ((experience - 5) / 20.0)
        variance = self._stable_variance("|".join(ids) + segment_type, 3)
        if control >= 1.2:
            variance = int(variance / 2)
        elif control <= -0.8 and variance < 0:
            variance -= 1
        return max(1, planned + variance)

    # ------------------------------------------------------------------
    # Booking plan and time allocation (#64, #68-72)
    # ------------------------------------------------------------------

    def build_show_plan_from_draft(
        self,
        show_draft,
        production_plan: dict | None = None,
        universe=None,
        actuals: dict | None = None,
        accept_overrun: bool = False,
        commercial_breaks: list[dict] | None = None,
    ) -> tuple[dict, list[dict]]:
        show_type = self._row_or_attr(show_draft, "show_type", "weekly_tv")
        total_runtime = int(
            (production_plan or {}).get("total_runtime_minutes")
            or self._row_or_attr(show_draft, "total_runtime_minutes", RUNTIME_BY_SHOW_TYPE.get(show_type, 120))
            or 120
        )
        network = self.repo.get_primary_network()
        break_count = self.network_break_count(show_type, float(network.get("relationship_score", 65)))
        show_id = self._row_or_attr(show_draft, "show_id")
        if not show_id:
            raise ValidationError("show_id is required")

        raw_items: list[tuple[int, str, Any]] = []
        for index, match in enumerate(self._row_or_attr(show_draft, "matches", []) or []):
            raw_items.append((int(self._row_or_attr(match, "card_position", index + 1) or index + 1), "match", match))
        for index, segment in enumerate(self._row_or_attr(show_draft, "segments", []) or []):
            raw_items.append((int(self._row_or_attr(segment, "card_position", (index * 100) + 50) or ((index * 100) + 50)), "segment", segment))
        raw_items.sort(key=lambda item: item[0])

        warnings: list[str] = []
        segments: list[dict] = []
        elapsed = 0
        actual_elapsed = 0
        main_index = len(raw_items) - 1
        for idx, (position, item_type, item) in enumerate(raw_items):
            source_id = self._row_or_attr(item, "match_id") if item_type == "match" else self._row_or_attr(item, "segment_id")
            source_id = source_id or f"{item_type}_{idx + 1}"
            segment_type = self._row_or_attr(item, "match_type") if item_type == "match" else self._row_or_attr(item, "segment_type", "promo")
            segment_type = segment_type or item_type
            low, high = self._expected_range_for_item(item_type, segment_type, item)
            planned = self._planned_duration_for_item(item_type, segment_type, item)
            actual_duration = None
            if actuals and source_id in actuals:
                actual_duration = actuals[source_id].get("actual_duration_minutes")
            elif actuals is not None:
                actual_duration = self._actual_duration_for_item(item_type, segment_type, item, universe)

            suspicious = planned < low
            overrun = max(0, (actual_duration or planned) - planned)
            dead_air = max(0, planned - (actual_duration or planned))
            status = "within_budget"
            if elapsed + planned > total_runtime:
                status = "over_allocated"
            elif suspicious:
                status = "suspiciously_short"
            if suspicious:
                warnings.append(f"{segment_type} at position {position} is short for its type.")
            if status == "over_allocated":
                warnings.append(f"Position {position} exceeds the show runtime allocation.")

            quality_score = 0.0
            crowd_heat = 0.0
            if actuals and source_id in actuals:
                quality_score = actuals[source_id].get("quality_score", 0)
                crowd_heat = actuals[source_id].get("crowd_heat_score", 0)

            segments.append(
                {
                    "id": f"{show_id}_{item_type}_{source_id}",
                    "show_id": show_id,
                    "source_item_id": source_id,
                    "item_type": item_type,
                    "segment_type": segment_type,
                    "card_position": position,
                    "planned_start_minute": elapsed,
                    "planned_duration_minutes": planned,
                    "actual_duration_minutes": actual_duration,
                    "allocation_status": status,
                    "expected_min_minutes": low,
                    "expected_max_minutes": high,
                    "suspiciously_short": suspicious,
                    "overrun_minutes": overrun,
                    "dead_air_minutes": dead_air,
                    "is_opening": idx == 0 or bool(self._row_or_attr(item, "is_opening", False)),
                    "is_main_event": idx == main_index or bool(self._row_or_attr(item, "is_main_event", False)),
                    "is_dark_match": bool(self._row_or_attr(item, "is_dark_match", False)),
                    "dark_match_phase": self._row_or_attr(item, "dark_match_phase"),
                    "feud_id": self._row_or_attr(item, "feud_id"),
                    "title_id": self._row_or_attr(item, "title_id"),
                    "quality_score": quality_score,
                    "crowd_heat_score": crowd_heat,
                    "payload_json": self._safe_to_dict(item),
                }
            )
            elapsed += planned
            actual_elapsed += actual_duration or planned

        overrun_minutes = max(0, elapsed - total_runtime)
        actual_overrun = max(0, actual_elapsed - total_runtime)
        dead_air_minutes = sum(segment["dead_air_minutes"] for segment in segments)
        if overrun_minutes and not accept_overrun:
            warnings.append(f"Planned card is {overrun_minutes} minutes over the contracted runtime.")
        if actual_overrun:
            warnings.append(f"Simulated runtime ran {actual_overrun} minutes long.")
        if dead_air_minutes:
            warnings.append(f"{dead_air_minutes} minutes of dead-air risk detected from short segments.")

        commercials = [
            self.calculate_commercial_break(show_id, idx, commercial)
            for idx, commercial in enumerate(commercial_breaks or [], start=1)
        ]

        plan = {
            "show_id": show_id,
            "show_name": self._row_or_attr(show_draft, "show_name", "Untitled Show"),
            "brand": self._row_or_attr(show_draft, "brand", "Cross-Brand"),
            "show_type": show_type,
            "year": int(self._row_or_attr(show_draft, "year", 1) or 1),
            "week": int(self._row_or_attr(show_draft, "week", 1) or 1),
            "total_runtime_minutes": total_runtime,
            "network_break_count": break_count,
            "accept_overrun": accept_overrun,
            "booking_credibility_delta": -min(10, overrun_minutes / 2) if overrun_minutes and accept_overrun else 0,
            "planned_rating_impact": -0.02 * dead_air_minutes - 0.03 * overrun_minutes,
            "actual_runtime_minutes": actual_elapsed if actuals is not None else None,
            "dead_air_risk_minutes": dead_air_minutes,
            "overrun_minutes": max(overrun_minutes, actual_overrun),
            "warnings": warnings,
            "commercial_breaks": commercials,
        }
        return plan, segments

    def _safe_to_dict(self, item: Any) -> dict:
        if isinstance(item, dict):
            return item
        if hasattr(item, "to_dict"):
            return item.to_dict()
        return dict(getattr(item, "__dict__", {}))

    def save_show_plan(self, payload: dict, universe=None) -> dict:
        show_draft = payload.get("show_draft") or payload
        accept_overrun = bool(payload.get("accept_overrun", False))
        plan, segments = self.build_show_plan_from_draft(
            show_draft,
            production_plan=payload.get("production_plan"),
            universe=universe,
            accept_overrun=accept_overrun,
            commercial_breaks=payload.get("commercial_breaks") or [],
        )
        if plan["overrun_minutes"] > 0 and not accept_overrun:
            raise ValidationError("Show allocation exceeds runtime. Trim segments or set accept_overrun=true.")
        return self.repo.replace_show_plan(plan, segments)

    def calculate_commercial_break(self, show_id: str, position_index: int, data: dict) -> dict:
        strategy = data.get("strategy", "neutral_reset")
        placement = data.get("placement_type", "between_segments")
        score = 55.0
        if strategy == "cliffhanger":
            score += 25
        elif strategy == "bad_cut":
            score -= 30
        elif placement == "mid_match" and strategy != "match_midpoint":
            score -= 15
        elif strategy == "match_midpoint":
            score += 5
        score = self.clamp(score)
        return {
            "id": data.get("id") or new_id("commercial"),
            "show_id": show_id,
            "position_index": position_index,
            "placement_type": placement,
            "after_segment_id": data.get("after_segment_id"),
            "during_match_id": data.get("during_match_id"),
            "minute_marker": int(data.get("minute_marker", 0) or 0),
            "strategy": strategy,
            "quality_score": score,
            "viewer_return_modifier": round((score - 50) / 500, 4),
            "satisfaction_modifier": round((score - 50) / 300, 4),
        }

    # ------------------------------------------------------------------
    # Interference, debuts, returns
    # ------------------------------------------------------------------

    def project_interference(self, data: dict, universe=None) -> dict:
        required = ["interfering_wrestler_id", "show_id", "match_id", "year", "week", "purpose"]
        for key in required:
            if key not in data or data[key] in (None, ""):
                raise ValidationError(f"{key} is required")
        year = int(data["year"])
        week = int(data["week"])
        wrestler_id = data["interfering_wrestler_id"]
        feud_id = data.get("feud_id")
        recent = self.repo.count_recent_interferences(wrestler_id, year, week)
        feud_count = self.repo.count_feud_interferences(feud_id)
        spacing_factor = 1.25 if recent == 0 else max(0.35, 1.0 - (recent * 0.22))
        feud_decay = 1.0 if feud_count == 0 else max(-0.40, 1.0 - (feud_count * 0.28))
        heat = self._linked_feud_heat(feud_id)
        heat_factor = 0.85 + (heat / 200.0)
        significance = float(data.get("match_significance", 50)) / 50.0
        base = 38.0
        impact = base * spacing_factor * feud_decay * heat_factor * significance
        overuse = recent >= 2
        credibility_penalty = 0.0
        heat_delta = impact / 10.0
        if overuse:
            credibility_penalty = min(10.0, 2 + recent * 1.5)
            heat_delta -= credibility_penalty
        if feud_count >= 4:
            heat_delta -= 8
        return {
            "impact_score": round(self.clamp(impact, -25, 100), 2),
            "heat_delta": round(heat_delta, 2),
            "recent_count_4_weeks": recent,
            "feud_interference_count": feud_count,
            "overuse_warning": overuse,
            "credibility_penalty": round(credibility_penalty, 2),
            "warning": "Interference overuse will reduce crowd heat and booking credibility." if overuse else None,
        }

    def record_interference(self, data: dict, universe=None) -> dict:
        projection = self.project_interference(data, universe)
        row = {
            **data,
            **projection,
            "interfering_wrestler_name": data.get("interfering_wrestler_name")
            or self._wrestler_name(data["interfering_wrestler_id"], universe),
            "outcome": data.get("outcome", "planned"),
            "override_warning": bool(data.get("override_warning", False)),
        }
        saved = self.repo.record_interference(row)
        if row.get("feud_id") and row.get("heat_delta"):
            self.apply_heat_delta(row["feud_id"], row["heat_delta"], int(row["year"]), int(row["week"]), "interference")
        return saved

    def schedule_debut_vignette(self, data: dict, universe=None) -> dict:
        wrestler_id = data["wrestler_id"]
        quality = self.clamp(float(data.get("quality_score", 60)))
        row = {
            "id": new_id("debut_vignette"),
            "wrestler_id": wrestler_id,
            "wrestler_name": data.get("wrestler_name") or self._wrestler_name(wrestler_id, universe),
            "show_id": data.get("show_id"),
            "year": int(data["year"]),
            "week": int(data["week"]),
            "quality_score": quality,
            "anticipation_delta": round(quality / 8, 2),
            "notes": data.get("notes"),
        }
        return self.repo.insert_simple("debut_vignettes", row)

    def create_debut(self, data: dict, universe=None) -> dict:
        wrestler_id = data["wrestler_id"]
        method = data.get("method", "surprise")
        year = int(data["year"])
        week = int(data["week"])
        rows = self.repo.fetch_all(
            "SELECT * FROM debut_vignettes WHERE wrestler_id = ? AND deleted_at IS NULL",
            (wrestler_id,),
        )
        vignette_count = len(rows)
        anticipation = sum(float(row["anticipation_delta"]) for row in rows)
        weeks_hidden = int(data.get("weeks_hidden", max(0, 12 - vignette_count)))
        if method == "surprise":
            surprise = 100 if weeks_hidden <= 1 else max(0, 100 - weeks_hidden * 8)
            anticipation_score = surprise
        else:
            anticipation_score = self.clamp(anticipation + min(20, vignette_count * 4))
        performance = (
            self._wrestler_metric(wrestler_id, "mic", universe)
            + self._wrestler_metric(wrestler_id, "popularity", universe)
            + self._wrestler_metric(wrestler_id, "psychology", universe)
        ) / 3
        debut_pop = self.clamp((anticipation_score * 0.55) + (performance * 0.45))
        momentum = round((debut_pop - 50) / 2, 2)
        if method == "teased" and anticipation_score > 75 and performance < 55:
            momentum -= 12
        row = {
            "id": new_id("debut"),
            "wrestler_id": wrestler_id,
            "wrestler_name": data.get("wrestler_name") or self._wrestler_name(wrestler_id, universe),
            "show_id": data["show_id"],
            "method": method,
            "weeks_hidden": weeks_hidden,
            "vignette_count": vignette_count,
            "anticipation_score": round(anticipation_score, 2),
            "debut_pop_rating": round(debut_pop, 2),
            "post_debut_momentum": momentum,
            "performance_score": round(performance, 2),
            "year": year,
            "week": week,
        }
        saved = self.repo.insert_simple("debut_records", row)
        self.repo.add_social_spike(
            {
                "show_id": data["show_id"],
                "source_type": "debut",
                "source_id": saved["id"],
                "description": f"Debut of {saved['wrestler_name']}",
                "spike_score": debut_pop,
                "follower_gain": int(debut_pop * 120),
                "engagement_delta": min(0.04, debut_pop / 3000),
                "year": year,
                "week": week,
            }
        )
        return saved

    def schedule_return_anticipation(self, data: dict, universe=None) -> dict:
        wrestler_id = data["wrestler_id"]
        quality = self.clamp(float(data.get("quality_score", 60)))
        row = {
            "id": new_id("return_anticipation"),
            "wrestler_id": wrestler_id,
            "wrestler_name": data.get("wrestler_name") or self._wrestler_name(wrestler_id, universe),
            "show_id": data.get("show_id"),
            "year": int(data["year"]),
            "week": int(data["week"]),
            "quality_score": quality,
            "anticipation_delta": round(quality / 7, 2),
            "notes": data.get("notes"),
        }
        return self.repo.insert_simple("return_anticipation_segments", row)

    def create_return(self, data: dict, universe=None) -> dict:
        wrestler_id = data["wrestler_id"]
        return_type = data.get("return_type", "cold")
        absence = int(data.get("absence_weeks", 0))
        rows = self.repo.fetch_all(
            "SELECT * FROM return_anticipation_segments WHERE wrestler_id = ? AND deleted_at IS NULL",
            (wrestler_id,),
        )
        anticipation = sum(float(row["anticipation_delta"]) for row in rows)
        overness = self._wrestler_metric(wrestler_id, "popularity", universe)
        absence_factor = 5 if absence < 4 else 20 if absence < 12 else 35 if absence < 26 else 50
        if return_type == "announced":
            pop = self.clamp((overness * 0.45) + anticipation + absence_factor)
        else:
            pop = self.clamp((overness * 0.65) + absence_factor)
        credibility_penalty = 0.0
        if return_type == "announced" and data.get("slipped_return_date"):
            credibility_penalty = 12.0
            pop -= 8
        row = {
            "id": new_id("return"),
            "wrestler_id": wrestler_id,
            "wrestler_name": data.get("wrestler_name") or self._wrestler_name(wrestler_id, universe),
            "show_id": data["show_id"],
            "return_type": return_type,
            "context_type": data.get("context_type", "babyface_comeback"),
            "absence_weeks": absence,
            "anticipation_score": round(anticipation, 2),
            "return_pop_rating": round(self.clamp(pop), 2),
            "credibility_penalty": credibility_penalty,
            "momentum_delta": round((pop - 50) / 2 - credibility_penalty, 2),
            "year": int(data["year"]),
            "week": int(data["week"]),
        }
        return self.repo.insert_simple("return_records", row)

    # ------------------------------------------------------------------
    # Storylines and feuds (#88-100)
    # ------------------------------------------------------------------

    def create_story_feud(self, data: dict, universe=None) -> dict:
        participants = data.get("participants") or []
        if len(participants) < 2:
            raise ValidationError("At least two feud participants are required")
        year = int(data.get("year", 1))
        week = int(data.get("week", 1))
        participant_rows = []
        names = []
        for index, participant in enumerate(participants):
            participant_id = participant.get("participant_id") or participant.get("id")
            if not participant_id:
                raise ValidationError("Each participant needs participant_id")
            name = participant.get("participant_name") or participant.get("name") or self._wrestler_name(participant_id, universe)
            names.append(name)
            participant_rows.append(
                {
                    "participant_type": participant.get("participant_type", "wrestler"),
                    "participant_id": participant_id,
                    "participant_name": name,
                    "side_label": participant.get("side_label", chr(65 + index)),
                    "role": participant.get("role", "primary"),
                }
            )
        initial_heat = self.clamp(float(data.get("initial_heat", 25)))
        feud = {
            "legacy_feud_id": data.get("legacy_feud_id"),
            "name": data.get("name") or " vs ".join(names),
            "basis": data.get("basis", "personal_grudge"),
            "status": "active",
            "heat_score": initial_heat,
            "heat_level": self.heat_level(initial_heat),
            "trajectory": "stable",
            "intended_conclusion_match_type": data.get("intended_conclusion_match_type", "singles"),
            "duration_target_weeks": int(data.get("duration_target_weeks", 8)),
            "start_year": year,
            "start_week": week,
            "planned_climax_year": data.get("planned_climax_year"),
            "planned_climax_week": data.get("planned_climax_week"),
            "metadata_json": data.get("metadata", {}),
        }
        return self.repo.create_story_feud(feud, participant_rows)

    def add_heat_action(self, feud_id: str, data: dict) -> dict:
        feud = self.repo.get_story_feud(feud_id)
        if not feud:
            raise ValidationError("Feud not found")
        action_type = data.get("action_type", "promo_challenge")
        current_heat = float(feud["heat_score"])
        if action_type in PERSONAL_ESCALATION_ACTIONS and current_heat < 45:
            raise ValidationError("Personal escalation requires at least warm feud heat")
        base = ACTION_BASE_HEAT.get(action_type, 4)
        recent_same = [
            action for action in feud.get("actions", [])[-4:]
            if action.get("action_type") == action_type
        ]
        repetition_penalty = len(recent_same) * 2.5
        quality = self.clamp(float(data.get("quality_score", 60)))
        overness_factor = 1.0 + ((quality - 50) / 200)
        heat_change = (base * overness_factor) - repetition_penalty
        if current_heat >= 85 and action_type not in {"career_threat", "secret_revelation", "contract_signing"}:
            heat_change *= 0.45
        heat_after = self.clamp(current_heat + heat_change)
        action = {
            "feud_id": feud_id,
            "action_category": data.get("action_category", self._action_category(action_type)),
            "action_type": action_type,
            "participants_json": data.get("participants", []),
            "description": data.get("description", action_type.replace("_", " ").title()),
            "heat_change": round(heat_after - current_heat, 2),
            "heat_after": round(heat_after, 2),
            "heat_level": self.heat_level(heat_after),
            "trajectory": "rising" if heat_after > current_heat else "declining" if heat_after < current_heat else "stable",
            "credibility_effect": -repetition_penalty / 3,
            "quality_score": quality,
            "show_id": data.get("show_id"),
            "year": int(data.get("year", feud.get("last_action_year") or feud["start_year"])),
            "week": int(data.get("week", feud.get("last_action_week") or feud["start_week"])),
        }
        saved = self.repo.record_storyline_action(action)
        if heat_after >= 75:
            self.repo.add_social_spike(
                {
                    "show_id": data.get("show_id"),
                    "source_type": "hot_feud_action",
                    "source_id": saved["id"],
                    "description": f"{feud['name']} escalated with {action_type.replace('_', ' ')}",
                    "spike_score": heat_after,
                    "follower_gain": int(heat_after * 45),
                    "engagement_delta": min(0.025, heat_after / 5000),
                    "year": saved["year"],
                    "week": saved["week"],
                }
            )
        return saved

    def _action_category(self, action_type: str) -> str:
        if action_type in {"in_ring_brawl", "locker_room_attack", "parking_lot_ambush", "post_match_beatdown"}:
            return "physical"
        if action_type in {"promo_challenge", "response_promo", "in_ring_confrontation", "contract_signing", "video_package"}:
            return "verbal"
        if action_type in {"rival_match_interference", "title_sabotage", "milestone_interference", "ally_attack"}:
            return "interference"
        return "personal_escalation"

    def apply_heat_delta(self, feud_id: str, delta: float, year: int, week: int, reason: str) -> None:
        feud = self.repo.get_story_feud(feud_id)
        if not feud:
            return
        current = float(feud["heat_score"])
        after = self.clamp(current + delta)
        self.repo.update_story_feud_heat(
            feud_id,
            after,
            self.heat_level(after),
            "rising" if delta > 0 else "declining" if delta < 0 else "stable",
            year,
            week,
            extra_updates={"booking_credibility_delta": float(feud.get("booking_credibility_delta", 0) or 0) + min(0, delta / 5)},
        )

    def create_payoff(self, data: dict) -> dict:
        feud_id = data.get("feud_id")
        feud = self.repo.get_story_feud(feud_id) if feud_id else None
        heat = float(feud["heat_score"]) if feud else float(data.get("heat_at_booking", 30))
        timing = "optimal" if heat >= 70 else "cold" if heat <= 30 else "early"
        match_quality = float(data.get("match_quality", 3.0)) * 20
        finish = data.get("finish_type", "clean_pin")
        decisiveness = 90 if finish in {"clean_pin", "submission"} else 55 if finish in {"cheating", "rollup"} else 25
        closure = self.clamp(float(data.get("closure_score", 60)))
        payoff = self.clamp((match_quality * 0.35) + (heat * 0.30) + (decisiveness * 0.20) + (closure * 0.15))
        if timing != "optimal":
            payoff -= 12
        row = {
            "id": new_id("payoff"),
            "feud_id": feud_id,
            "program_id": data.get("program_id"),
            "show_id": data["show_id"],
            "match_id": data["match_id"],
            "heat_at_booking": heat,
            "timing_quality": timing,
            "finish_decisiveness": decisiveness,
            "crowd_investment": heat,
            "closure_score": closure,
            "match_quality": match_quality,
            "payoff_score": round(self.clamp(payoff), 2),
            "booking_legacy_effect": round((payoff - 50) / 5, 2),
        }
        saved = self.repo.insert_simple("storyline_payoffs", row)
        if feud_id:
            self.repo.update_story_feud_heat(
                feud_id,
                max(0, heat - 35),
                self.heat_level(max(0, heat - 35)),
                "declining",
                extra_updates={"status": "resolved", "payoff_score": saved["payoff_score"]},
            )
        return saved

    def create_swerve(self, data: dict) -> dict:
        feud_id = data.get("feud_id")
        actor_id = data.get("actor_id")
        history_rows = self.repo.fetch_all(
            """
            SELECT COUNT(*) AS total
            FROM storyline_actions
            WHERE participants_json LIKE ? AND deleted_at IS NULL
            """,
            (f"%{actor_id}%",),
        )
        telegraphing = min(40, int(history_rows[0]["total"]) * 6) if history_rows else 0
        unpredictability = self.clamp(float(data.get("unpredictability_score", 80 - telegraphing)))
        motivation = (data.get("motivation") or "").strip()
        logic = self.clamp(float(data.get("narrative_logic_score", 75 if len(motivation) >= 20 else 38)))
        placement = data.get("placement", "mid_card")
        placement_bonus = 12 if placement in {"main_event", "premium_closing"} else 0
        impact = self.clamp((unpredictability * 0.40) + (logic * 0.45) + placement_bonus)
        credibility = round((logic - 50) / 4, 2)
        social = self.clamp((unpredictability * 0.60) + (impact * 0.40))
        row = {
            "id": new_id("swerve"),
            "feud_id": feud_id,
            "show_id": data.get("show_id"),
            "swerve_type": data.get("swerve_type", "betrayal"),
            "actor_id": actor_id,
            "target_id": data.get("target_id"),
            "motivation": motivation or "No stated motivation",
            "unpredictability_score": round(unpredictability, 2),
            "narrative_logic_score": round(logic, 2),
            "impact_score": round(impact, 2),
            "credibility_effect": credibility,
            "social_buzz_score": round(social, 2),
            "year": int(data["year"]),
            "week": int(data["week"]),
        }
        saved = self.repo.insert_simple("story_swerves", row)
        if feud_id:
            self.apply_heat_delta(feud_id, (impact - 50) / 4, row["year"], row["week"], "swerve")
        self.repo.add_social_spike(
            {
                "show_id": row.get("show_id"),
                "source_type": "swerve",
                "source_id": saved["id"],
                "description": f"{row['swerve_type'].replace('_', ' ').title()} swerve",
                "spike_score": social,
                "follower_gain": int(social * 100),
                "engagement_delta": min(0.04, social / 2800),
                "year": row["year"],
                "week": row["week"],
            }
        )
        return saved

    def record_promo(self, data: dict, universe=None) -> dict:
        speaker = data["speaker_id"]
        mic = self._wrestler_metric(speaker, "mic", universe)
        script = data.get("script_content") or ""
        script_quality = self.clamp(float(data.get("script_quality", min(90, 40 + len(script) / 8))))
        delivery_modifier = (mic - 50) / 2
        quality = self.clamp(script_quality + delivery_modifier)
        heat_change = 0.0
        if data.get("feud_id"):
            heat_change = round((quality - 45) / 8, 2)
            self.apply_heat_delta(data["feud_id"], heat_change, int(data["year"]), int(data["week"]), "promo")
        row = {
            "id": new_id("promo"),
            "show_id": data.get("show_id"),
            "segment_id": data.get("segment_id"),
            "feud_id": data.get("feud_id"),
            "speaker_id": speaker,
            "target_id": data.get("target_id"),
            "tone": data.get("tone", "aggressive_confrontation"),
            "duration_minutes": int(data.get("duration_minutes", 5)),
            "script_content": script,
            "script_quality": round(script_quality, 2),
            "delivery_modifier": round(delivery_modifier, 2),
            "promo_quality": round(quality, 2),
            "heat_change": heat_change,
            "character_momentum_delta": round((quality - 50) / 10, 2),
            "year": int(data["year"]),
            "week": int(data["week"]),
        }
        return self.repo.insert_simple("promo_segments", row)

    def record_backstage_segment(self, data: dict, universe=None) -> dict:
        participants = data.get("participants", [])
        ids = [p.get("wrestler_id") or p.get("id") for p in participants if isinstance(p, dict)]
        acting = sum(self._wrestler_metric(wid, "mic", universe) for wid in ids) / max(1, len(ids))
        charisma = sum(self._wrestler_metric(wid, "popularity", universe) for wid in ids) / max(1, len(ids))
        quality = self.clamp((acting * 0.55) + (charisma * 0.45))
        heat_change = round((quality - 45) / 12, 2) if data.get("feud_id") else 0
        if data.get("feud_id"):
            self.apply_heat_delta(data["feud_id"], heat_change, int(data["year"]), int(data["week"]), "backstage")
        row = {
            "id": new_id("backstage"),
            "show_id": data.get("show_id"),
            "segment_id": data.get("segment_id"),
            "feud_id": data.get("feud_id"),
            "segment_type": data.get("segment_type", "confrontation"),
            "location": data.get("location", "locker_room_hallway"),
            "participants_json": self.repo.to_json(participants),
            "acting_quality": round(acting, 2),
            "charisma_quality": round(charisma, 2),
            "segment_quality": round(quality, 2),
            "heat_change": heat_change,
            "year": int(data["year"]),
            "week": int(data["week"]),
        }
        return self.repo.insert_simple("backstage_segments", row)

    def create_tournament(self, data: dict, universe=None) -> dict:
        participants = data.get("participants", [])
        count = int(data.get("participant_count", len(participants)))
        if count not in {4, 8, 16, 32} and data.get("format", "single_elimination") in {"single_elimination", "double_elimination"}:
            raise ValidationError("Elimination tournaments require 4, 8, 16, or 32 participants")
        bracket = self._build_single_elim_bracket(participants)
        row = {
            "id": new_id("tournament"),
            "name": data["name"],
            "prize_type": data.get("prize_type", "championship_opportunity"),
            "prize_description": data.get("prize_description", "Championship match opportunity"),
            "format": data.get("format", "single_elimination"),
            "participant_count": count,
            "status": "active",
            "duration_shows": int(data.get("duration_shows", 1)),
            "seeding_logic": data.get("seeding_logic", "ranking"),
            "narrative_arc_score": 40,
            "bracket_json": self.repo.to_json(bracket),
            "start_year": int(data["year"]),
            "start_week": int(data["week"]),
        }
        saved = self.repo.insert_simple("tournaments", row)
        for seed, participant in enumerate(participants, start=1):
            wrestler_id = participant.get("wrestler_id") or participant.get("id")
            self.repo.insert_simple(
                "tournament_entries",
                {
                    "id": new_id("tournament_entry"),
                    "tournament_id": saved["id"],
                    "wrestler_id": wrestler_id,
                    "wrestler_name": participant.get("wrestler_name") or self._wrestler_name(wrestler_id, universe),
                    "seed": seed,
                },
            )
        return saved

    def _build_single_elim_bracket(self, participants: list[dict]) -> dict:
        seeds = [p.get("wrestler_id") or p.get("id") for p in participants]
        matches = []
        for index in range(0, len(seeds), 2):
            matches.append({"round": 1, "position": int(index / 2) + 1, "wrestler_a_id": seeds[index], "wrestler_b_id": seeds[index + 1] if index + 1 < len(seeds) else None})
        return {"rounds": [{"round": 1, "matches": matches}]}

    def create_romantic_angle(self, data: dict, universe=None) -> dict:
        participants = data.get("participants", [])
        ids = [p.get("wrestler_id") or p.get("id") for p in participants if isinstance(p, dict)]
        charisma = sum(self._wrestler_metric(wid, "mic", universe) for wid in ids) / max(1, len(ids))
        alignment_mix = {self._row_or_attr(self._wrestler_by_id(wid, universe), "alignment", "Tweener") for wid in ids}
        risk = 35
        if "Heel" in alignment_mix and "Face" in alignment_mix:
            risk += 18
        if data.get("relationship_type") in {"jealousy_triangle", "betrayal_romance", "forbidden_romance"}:
            risk += 12
        risk -= (charisma - 50) / 3
        risk = self.clamp(risk)
        row = {
            "id": new_id("romance"),
            "name": data.get("name", "Romantic Angle"),
            "relationship_type": data.get("relationship_type", "genuine_partnership"),
            "status": "active",
            "participants_json": self.repo.to_json(participants),
            "linked_feud_id": data.get("linked_feud_id"),
            "reception_risk_score": round(risk, 2),
            "crowd_support_score": round(self.clamp(100 - risk + (charisma - 50) / 2), 2),
            "backlash_score": round(risk, 2),
            "history_json": "[]",
            "start_year": int(data["year"]),
            "start_week": int(data["week"]),
        }
        return self.repo.insert_simple("romantic_angles", row)

    def record_legacy_relationship(self, data: dict, universe=None) -> dict:
        a = data["wrestler_a_id"]
        b = data["wrestler_b_id"]
        row = {
            "id": new_id("legacy_rel"),
            "wrestler_a_id": a,
            "wrestler_a_name": data.get("wrestler_a_name") or self._wrestler_name(a, universe),
            "wrestler_b_id": b,
            "wrestler_b_name": data.get("wrestler_b_name") or self._wrestler_name(b, universe),
            "relationship_type": data.get("relationship_type", "chosen_family"),
            "relationship_strength": self.clamp(float(data.get("relationship_strength", 60))),
            "biological": 1 if data.get("biological") else 0,
            "notes": data.get("notes"),
        }
        return self.repo.insert_simple("legacy_relationships", row)

    def record_torch_pass(self, data: dict, universe=None) -> dict:
        legend_id = data["legend_id"]
        star_id = data["rising_star_id"]
        legend_over = self._wrestler_metric(legend_id, "popularity", universe)
        star_over = self._wrestler_metric(star_id, "popularity", universe)
        climax = self.clamp(float(data.get("climax_quality", 70)))
        structure = self.clamp(float(data.get("structure_score", 65)))
        transfer = self.clamp((legend_over - star_over) * 0.35 + (climax - 50) * 0.45 + (structure - 50) * 0.20)
        row = {
            "id": new_id("torch_pass"),
            "legend_id": legend_id,
            "legend_name": data.get("legend_name") or self._wrestler_name(legend_id, universe),
            "rising_star_id": star_id,
            "rising_star_name": data.get("rising_star_name") or self._wrestler_name(star_id, universe),
            "show_id": data.get("show_id"),
            "match_id": data.get("match_id"),
            "structure_score": structure,
            "climax_quality": climax,
            "overness_transfer": round(transfer, 2),
            "legacy_impact_score": round(self.clamp(transfer + structure / 3), 2),
            "status": "completed",
            "year": int(data["year"]),
            "week": int(data["week"]),
        }
        return self.repo.insert_simple("torch_passes", row)

    # ------------------------------------------------------------------
    # Media/business (#126-137)
    # ------------------------------------------------------------------

    def calculate_tv_ratings(self, show_draft, show_result, show_plan: dict | None = None) -> dict:
        year = int(self._row_or_attr(show_draft, "year", 1))
        week = int(self._row_or_attr(show_draft, "week", 1))
        show_id = self._row_or_attr(show_draft, "show_id")
        recent = self.repo.get_recent_ratings(12)
        historical_average = int(sum(row["total_viewership"] for row in recent) / len(recent)) if recent else 850000
        quality = float(self._row_or_attr(show_result, "overall_rating", 3.0)) * 20
        trend = self._ratings_trend_modifier(recent)
        competition = self._competition_modifier(year, week, show_id)
        opening_modifier = self._opening_modifier(show_plan)
        main_event_modifier = self._main_event_modifier(show_plan, show_result)
        commercial_modifier = self._commercial_modifier(show_plan)
        total_modifier = 1 + trend + ((quality - 60) / 250) + competition + opening_modifier + main_event_modifier + commercial_modifier
        total_viewers = max(10000, int(historical_average * total_modifier))
        rating_score = round(total_viewers / 1000000, 3)
        demographics = self._demographic_breakdown(total_viewers, quality, show_plan)
        ad_revenue = int(sum(d["revenue_contribution"] for d in demographics))
        rating = {
            "show_id": show_id,
            "show_name": self._row_or_attr(show_draft, "show_name", "Untitled Show"),
            "brand": self._row_or_attr(show_draft, "brand", "Cross-Brand"),
            "year": year,
            "week": week,
            "base_viewership": historical_average,
            "total_viewership": total_viewers,
            "rating_score": rating_score,
            "booking_quality_score": round(quality, 2),
            "momentum_modifier": round(trend, 4),
            "competition_modifier": round(competition, 4),
            "opening_modifier": round(opening_modifier, 4),
            "main_event_modifier": round(main_event_modifier, 4),
            "commercial_modifier": round(commercial_modifier, 4),
            "demographic_value_index": round(ad_revenue / max(1, total_viewers), 4),
            "advertising_revenue": ad_revenue,
        }
        quarters = self._quarter_hour_breakdown(total_viewers, rating_score, show_plan, show_result)
        insights = self._ratings_insights(rating, quarters, recent)
        return {
            "rating": rating,
            "quarters": quarters,
            "demographics": demographics,
            "insights": insights,
        }

    def _ratings_trend_modifier(self, recent: list[dict]) -> float:
        if len(recent) < 3:
            return 0.0
        ordered = list(reversed(recent[:6]))
        first = ordered[: max(1, len(ordered) // 2)]
        second = ordered[max(1, len(ordered) // 2):]
        first_avg = sum(row["total_viewership"] for row in first) / len(first)
        second_avg = sum(row["total_viewership"] for row in second) / max(1, len(second))
        return max(-0.12, min(0.12, (second_avg - first_avg) / max(1, first_avg)))

    def _competition_modifier(self, year: int, week: int, show_id: str | None = None) -> float:
        events = self.repo.get_competition_for_week(year, week)
        modifier = sum(float(event["impact_modifier"]) for event in events)
        if events and show_id:
            for event in events:
                self.repo.insert_simple(
                    "competing_impact_history",
                    {
                        "id": new_id("competition_impact"),
                        "show_id": show_id,
                        "competing_event_id": event["id"],
                        "impact_modifier": event["impact_modifier"],
                        "lost_viewers_estimate": int(abs(float(event["impact_modifier"])) * 850000),
                        "analysis_note": f"{event['event_name']} reduced available audience.",
                        "year": year,
                        "week": week,
                    },
                )
        return max(-0.35, min(0.10, modifier))

    def _opening_modifier(self, show_plan: dict | None) -> float:
        if not show_plan:
            return 0.0
        opener = next((segment for segment in show_plan.get("segments", []) if segment.get("is_opening")), None)
        if not opener:
            return 0.0
        quality = float(opener.get("quality_score") or 55)
        status_penalty = -0.03 if opener.get("allocation_status") == "suspiciously_short" else 0
        return max(-0.08, min(0.10, (quality - 55) / 500 + status_penalty))

    def _main_event_modifier(self, show_plan: dict | None, show_result=None) -> float:
        if not show_plan:
            return 0.0
        main = next((segment for segment in show_plan.get("segments", []) if segment.get("is_main_event")), None)
        if not main:
            return 0.0
        quality = float(main.get("quality_score") or (float(self._row_or_attr(show_result, "overall_rating", 3)) * 20))
        if quality < 45:
            return -0.10
        if quality > 85:
            return 0.09
        return (quality - 60) / 700

    def _commercial_modifier(self, show_plan: dict | None) -> float:
        if not show_plan:
            return 0.0
        breaks = show_plan.get("commercial_breaks") or []
        if not breaks:
            return 0.025 if show_plan.get("show_type") in {"minor_ppv", "major_ppv", "premium_live_event"} else 0
        return max(-0.08, min(0.08, sum(float(b["viewer_return_modifier"]) for b in breaks)))

    def _demographic_breakdown(self, total_viewers: int, quality: float, show_plan: dict | None) -> list[dict]:
        title_match_bonus = 0.03 if any(segment.get("title_id") for segment in (show_plan or {}).get("segments", [])) else 0
        rows = []
        for demographic, (share, ad_multiplier) in DEMO_SPLIT.items():
            adjusted_share = share
            if demographic == "male_18_49":
                adjusted_share += title_match_bonus + max(0, quality - 70) / 1000
            if demographic == "casual_viewer":
                adjusted_share += max(0, quality - 80) / 1200
            viewers = int(total_viewers * adjusted_share)
            rating_score = round(viewers / 1000000, 3)
            rows.append(
                {
                    "demographic": demographic,
                    "viewership": viewers,
                    "rating_score": rating_score,
                    "ad_rate_multiplier": ad_multiplier,
                    "revenue_contribution": int(viewers * 0.018 * ad_multiplier),
                }
            )
        return rows

    def _quarter_hour_breakdown(self, total_viewers: int, rating_score: float, show_plan: dict | None, show_result=None) -> list[dict]:
        runtime = int((show_plan or {}).get("total_runtime_minutes", 120))
        quarters_count = max(1, ceil(runtime / 15))
        segments = (show_plan or {}).get("segments", [])
        quarters = []
        prior_viewers = total_viewers
        for index in range(quarters_count):
            start = index * 15
            end = min(runtime, start + 15)
            segment = next((s for s in segments if int(s.get("planned_start_minute", 0)) <= start < int(s.get("planned_start_minute", 0)) + int(s.get("planned_duration_minutes", 0))), None)
            quality = float((segment or {}).get("quality_score") or 55)
            dead_air = float((segment or {}).get("dead_air_minutes") or 0)
            opening_bonus = 0.05 if index == 0 and (segment or {}).get("is_opening") else 0
            viewer_factor = 1 + ((quality - 55) / 600) + opening_bonus - (dead_air * 0.01)
            viewers = max(10000, int(prior_viewers * viewer_factor))
            delta = viewers - prior_viewers if index > 0 else viewers - total_viewers
            note = "gained viewers" if delta > 0 else "lost viewers" if delta < 0 else "held steady"
            quarters.append(
                {
                    "quarter_index": index + 1,
                    "start_minute": start,
                    "end_minute": end,
                    "segment_id": (segment or {}).get("source_item_id"),
                    "content_summary": (segment or {}).get("segment_type", "Show flow"),
                    "rating_score": round(rating_score * (viewers / max(1, total_viewers)), 3),
                    "viewership": viewers,
                    "viewer_delta": delta,
                    "analysis_note": note,
                }
            )
            prior_viewers = viewers
        return quarters

    def _ratings_insights(self, rating: dict, quarters: list[dict], recent: list[dict]) -> list[dict]:
        insights = []
        if quarters:
            best = max(quarters, key=lambda q: q["viewer_delta"])
            worst = min(quarters, key=lambda q: q["viewer_delta"])
            insights.append(
                {
                    "insight_type": "quarter_hour",
                    "title": "Strongest quarter-hour",
                    "body": f"Quarter {best['quarter_index']} around {best['content_summary']} gained {best['viewer_delta']} viewers versus the prior quarter.",
                    "metric_value": best["viewer_delta"],
                    "confidence": 0.82,
                }
            )
            insights.append(
                {
                    "insight_type": "quarter_hour",
                    "title": "Weakest quarter-hour",
                    "body": f"Quarter {worst['quarter_index']} around {worst['content_summary']} changed by {worst['viewer_delta']} viewers.",
                    "metric_value": worst["viewer_delta"],
                    "confidence": 0.78,
                }
            )
        if recent:
            average = sum(row["total_viewership"] for row in recent) / len(recent)
            diff = rating["total_viewership"] - average
            insights.append(
                {
                    "insight_type": "historical_comparison",
                    "title": "Historical comparison",
                    "body": f"This show was {int(diff)} viewers versus the recent average.",
                    "metric_value": diff,
                    "confidence": 0.75,
                }
            )
        return insights

    def save_media_appearance(self, data: dict, universe=None) -> dict:
        wrestler_id = data["wrestler_id"]
        outlet_type = data.get("outlet_type", "wrestling_podcast")
        reach = {"wrestling_podcast": 35, "sports_show": 60, "entertainment_tv": 80, "influencer_collaboration": 55}.get(outlet_type, 45)
        performance = self.clamp((self._wrestler_metric(wrestler_id, "mic", universe) * 0.55) + (self._wrestler_metric(wrestler_id, "popularity", universe) * 0.45))
        coverage = self.clamp((reach * 0.45) + (performance * 0.55))
        row = {
            "id": new_id("media_appearance"),
            "wrestler_id": wrestler_id,
            "wrestler_name": data.get("wrestler_name") or self._wrestler_name(wrestler_id, universe),
            "outlet_type": outlet_type,
            "outlet_name": data.get("outlet_name", "Unnamed Outlet"),
            "talking_points": data.get("talking_points", ""),
            "restrictions": data.get("restrictions"),
            "reach_score": reach,
            "performance_score": round(performance, 2),
            "coverage_score": round(coverage, 2),
            "mainstream_awareness_delta": round(coverage / 20, 2),
            "year": int(data["year"]),
            "week": int(data["week"]),
        }
        saved = self.repo.insert_simple("media_appearances", row)
        self._update_snapshot_awareness(saved["year"], saved["week"], saved["mainstream_awareness_delta"])
        return saved

    def create_digital_content(self, data: dict, universe=None) -> dict:
        content_type = data.get("content_type", "highlight_reel")
        hot_feud_bonus = 12 if data.get("associated_storylines") else 0
        quality = self.clamp(float(data.get("quality_score", 60)) + hot_feud_bonus)
        row = {
            "id": new_id("digital_content"),
            "content_type": content_type,
            "title": data.get("title", content_type.replace("_", " ").title()),
            "production_cost": int(data.get("production_cost", 25000)),
            "time_investment_hours": int(data.get("time_investment_hours", 8)),
            "featured_wrestlers_json": self.repo.to_json(data.get("featured_wrestlers", [])),
            "associated_storylines_json": self.repo.to_json(data.get("associated_storylines", [])),
            "engagement_score": round(quality, 2),
            "follower_gain": int(quality * 60),
            "ip_asset_value": int(quality * 1500),
            "produced_year": int(data["year"]),
            "produced_week": int(data["week"]),
        }
        saved = self.repo.insert_simple("digital_content_library", row)
        self.repo.add_social_spike(
            {
                "source_type": "digital_content",
                "source_id": saved["id"],
                "description": saved["title"],
                "spike_score": quality,
                "follower_gain": saved["follower_gain"],
                "engagement_delta": min(0.025, quality / 4500),
                "year": saved["produced_year"],
                "week": saved["produced_week"],
            }
        )
        return saved

    def negotiate_streaming_deal(self, data: dict) -> dict:
        dashboard = self.media_business_dashboard()
        attractiveness = dashboard["business_metrics"]["streaming_attractiveness"]
        platform_type = data.get("platform_type", "general_entertainment")
        model = data.get("revenue_model", "flat_rights_fee")
        base_value = int(attractiveness * 18000)
        if platform_type == "general_entertainment":
            base_value = int(base_value * 1.4)
        if model == "self_distribution":
            base_value = int(base_value * 0.65)
        row = {
            "id": new_id("streaming_deal"),
            "platform_type": platform_type,
            "partner_name": data.get("partner_name", "Streaming Partner"),
            "status": "active",
            "revenue_model": model,
            "annual_value": int(data.get("annual_value", base_value)),
            "revenue_share_pct": float(data.get("revenue_share_pct", 0.0)),
            "attractiveness_score": round(attractiveness, 2),
            "terms_json": self.repo.to_json(data.get("terms", {})),
            "start_year": int(data.get("year", 1)),
            "start_week": int(data.get("week", 1)),
            "duration_months": int(data.get("duration_months", 24)),
        }
        return self.repo.insert_simple("streaming_deals", row)

    def create_documentary(self, data: dict, universe=None) -> dict:
        budget = int(data.get("budget", 100000))
        subject_score = self._wrestler_metric(data.get("subject_id"), "popularity", universe, 55) if data.get("subject_id") else 60
        production = self.clamp(35 + budget / 8000)
        resonance = self.clamp(float(data.get("emotional_resonance", subject_score)))
        relevance = self.clamp(float(data.get("current_storyline_relevance", 0)))
        reception = self.clamp(subject_score * 0.35 + production * 0.30 + resonance * 0.25 + relevance * 0.10)
        row = {
            "id": new_id("documentary"),
            "documentary_type": data.get("documentary_type", "career_retrospective"),
            "title": data.get("title", "Untitled Documentary"),
            "subject_id": data.get("subject_id"),
            "subject_name": data.get("subject_name") or (self._wrestler_name(data.get("subject_id"), universe) if data.get("subject_id") else None),
            "status": data.get("status", "released"),
            "budget": budget,
            "timeline_weeks": int(data.get("timeline_weeks", 8)),
            "production_quality": round(production, 2),
            "emotional_resonance": round(resonance, 2),
            "current_storyline_relevance": round(relevance, 2),
            "reception_score": round(reception, 2),
            "distribution_plan": data.get("distribution_plan", "streaming"),
            "release_year": data.get("release_year", data.get("year")),
            "release_week": data.get("release_week", data.get("week")),
        }
        return self.repo.insert_simple("documentary_projects", row)

    def create_video_game_license(self, data: dict) -> dict:
        profile = self.media_business_dashboard()
        awareness = profile["business_metrics"]["mainstream_awareness"]
        game_type = data.get("game_type", "indie_sim")
        fee_multiplier = {"aaa_wrestling": 3.5, "indie_sim": 1.0, "mobile": 1.6}.get(game_type, 1.0)
        row = {
            "id": new_id("game_license"),
            "developer_name": data.get("developer_name", "Game Studio"),
            "game_type": game_type,
            "status": "active",
            "duration_months": int(data.get("duration_months", 36)),
            "upfront_fee": int(data.get("upfront_fee", max(50000, awareness * 10000 * fee_multiplier))),
            "royalty_pct": float(data.get("royalty_pct", 3.0 if game_type != "mobile" else 1.5)),
            "exclusivity": data.get("exclusivity", "none"),
            "roster_requirement": int(data.get("roster_requirement", 20)),
            "belts_included_json": self.repo.to_json(data.get("belts_included", [])),
            "game_quality_score": self.clamp(float(data.get("game_quality_score", 65))),
            "brand_awareness_delta": round(float(data.get("game_quality_score", 65)) / 20, 2),
        }
        return self.repo.insert_simple("video_game_licenses", row)

    def stage_press_conference(self, data: dict, universe=None) -> dict:
        spokesperson = data.get("spokesperson_id")
        charisma = self._wrestler_metric(spokesperson, "mic", universe, 60) if spokesperson else 60
        significance = self.clamp(float(data.get("significance_score", 60)))
        network = self.repo.get_primary_network()
        media_relationship = float(network.get("relationship_score", 60))
        execution = self.clamp((charisma * 0.45) + (significance * 0.35) + (media_relationship * 0.20))
        row = {
            "id": new_id("press_conference"),
            "conference_type": data.get("conference_type", "major_match_announcement"),
            "announcement": data.get("announcement", ""),
            "spokesperson_id": spokesperson,
            "spokesperson_name": data.get("spokesperson_name") or (self._wrestler_name(spokesperson, universe) if spokesperson else None),
            "participants_json": self.repo.to_json(data.get("participants", [])),
            "significance_score": significance,
            "execution_quality": round(execution, 2),
            "media_coverage_score": round(self.clamp(execution + significance / 4), 2),
            "downstream_impact_json": self.repo.to_json({"awareness_delta": round(execution / 25, 2), "event_interest_delta": round(significance / 20, 2)}),
            "year": int(data["year"]),
            "week": int(data["week"]),
        }
        saved = self.repo.insert_simple("press_conferences", row)
        self._update_snapshot_awareness(saved["year"], saved["week"], saved["media_coverage_score"] / 25)
        return saved

    def respond_to_controversy(self, data: dict, universe=None) -> dict:
        severity = self.clamp(float(data.get("severity_score", 50)))
        response = data.get("response_type", "formal_apology")
        response_effects = {
            "formal_apology": (-severity * 0.10, -severity * 0.05, -severity * 0.02),
            "suspend": (-severity * 0.15, severity * 0.05, severity * 0.02),
            "terminate": (-severity * 0.25, severity * 0.08, severity * 0.05),
            "do_nothing": (-severity * 0.05, -severity * 0.12, -severity * 0.10),
            "lean_in_heel": (severity * 0.08, -severity * 0.07, -severity * 0.06),
            "storyline_launch": (severity * 0.05, -severity * 0.02, -severity * 0.01),
        }
        wrestler_delta, brand_delta, network_delta = response_effects.get(response, response_effects["formal_apology"])
        row = {
            "id": data.get("id") or new_id("controversy"),
            "wrestler_id": data["wrestler_id"],
            "wrestler_name": data.get("wrestler_name") or self._wrestler_name(data["wrestler_id"], universe),
            "controversy_type": data.get("controversy_type", "divisive_personal_opinion"),
            "description": data.get("description", ""),
            "severity_score": severity,
            "response_type": response,
            "response_effect_json": self.repo.to_json({"response": response}),
            "wrestler_reputation_delta": round(wrestler_delta, 2),
            "brand_image_delta": round(brand_delta, 2),
            "network_delta": round(network_delta, 2),
            "sponsor_delta": round(brand_delta * 1.2, 2),
            "status": "resolved",
            "year": int(data["year"]),
            "week": int(data["week"]),
        }
        saved = self.repo.insert_simple("wrestler_social_controversies", row)
        self.repo.update_network_relationship(network_delta, f"Controversy response: {response}", row["year"], row["week"])
        return saved

    def _update_snapshot_awareness(self, year: int, week: int, awareness_delta: float) -> None:
        snapshot = self.repo.get_business_snapshot(year, week) or {
            "year": year,
            "week": week,
            "mainstream_awareness": 30,
            "sponsorship_attractiveness": 40,
            "streaming_attractiveness": 40,
            "booking_credibility": 70,
            "promotion_momentum": 50,
            "valuation_estimate": 10000000,
        }
        snapshot["mainstream_awareness"] = self.clamp(float(snapshot.get("mainstream_awareness", 30)) + awareness_delta)
        snapshot["sponsorship_attractiveness"] = self.clamp(float(snapshot.get("sponsorship_attractiveness", 40)) + awareness_delta / 2)
        snapshot["streaming_attractiveness"] = self.clamp(float(snapshot.get("streaming_attractiveness", 40)) + awareness_delta / 2)
        self.repo.upsert_business_snapshot(snapshot)

    # ------------------------------------------------------------------
    # Internal calendar jobs and simulation integration
    # ------------------------------------------------------------------

    def run_weekly_jobs(self, year: int, week: int) -> dict:
        existing = self.repo.fetch_one(
            """
            SELECT result_json
            FROM internal_simulation_jobs
            WHERE job_type = 'weekly_internal_simulation'
              AND trigger_year = ?
              AND trigger_week = ?
              AND status = 'completed'
              AND deleted_at IS NULL
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (year, week),
        )
        if existing:
            return {"already_ran": True, "previous_result": self.repo.from_json(existing.get("result_json"), {})}

        result = {
            "heat_decay": self._apply_heat_decay(year, week),
            "social_growth": self._apply_social_growth(year, week),
            "network_trend": self._apply_network_trend(year, week),
            "business_snapshot": self._recalculate_business_snapshot(year, week),
            "story_arc_ai": self.run_story_arc_ai_week(year, week, auto=True),
        }
        self.repo.log_job(
            "weekly_internal_simulation",
            year,
            week,
            "completed",
            ["story_feuds", "tv_ratings", "social_platform_metrics", "network_relationships"],
            ["story_feuds", "social_metric_history", "network_relationship_history", "business_metric_snapshots"],
            result,
        )
        return result

    # ------------------------------------------------------------------
    # Story arc planning AI and event calendar
    # ------------------------------------------------------------------

    def ensure_story_arc_foundation(self, year: int | None = None) -> dict:
        state = self.database.get_game_state() if hasattr(self.database, "get_game_state") else {}
        year = int(year or state.get("current_year", 1))
        now = self.repo.now()
        seeded_templates = 0
        seeded_calendar = 0
        seeded_vision = 0
        with self.repo.transaction():
            for template_id, name, tier, min_weeks, max_weeks, roster_min, roster_max, complexity, success_rate in STORY_ARC_TEMPLATE_SEEDS:
                before = self.repo.fetch_one("SELECT id FROM story_arc_templates WHERE id = ?", (template_id,))
                self.repo.conn.execute(
                    """
                    INSERT OR IGNORE INTO story_arc_templates (
                        id, template_name, tier, duration_min_weeks, duration_max_weeks,
                        roster_min, roster_max, complexity, success_rate,
                        milestone_schema_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        template_id,
                        name,
                        tier,
                        min_weeks,
                        max_weeks,
                        roster_min,
                        roster_max,
                        complexity,
                        success_rate,
                        self.repo.to_json(MILESTONE_SCHEMA),
                        now,
                        now,
                    ),
                )
                if not before:
                    seeded_templates += 1

            for week, name, event_type, tier, purpose in ANNUAL_STORY_CALENDAR:
                pressure = self._calendar_competition_pressure(year, week)
                before = self.repo.fetch_one(
                    "SELECT id FROM story_calendar_events WHERE event_name = ? AND year = ? AND week = ?",
                    (name, year, week),
                )
                self.repo.conn.execute(
                    """
                    INSERT OR IGNORE INTO story_calendar_events (
                        id, event_name, event_type, tier, year, week, brand,
                        venue_market, venue_capacity, strategic_purpose,
                        competition_pressure_score, seasonal_notes,
                        booking_strategy_json, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'planned', ?, ?)
                    """,
                    (
                        f"story_calendar_{year}_{week}_{event_type}",
                        name,
                        event_type,
                        tier,
                        year,
                        week,
                        "Cross-Brand" if tier in {"tier_a", "tier_b"} else "ROC Alpha",
                        self._suggest_market_for_event(tier, week),
                        15000 if tier == "tier_a" else 8000 if tier == "tier_b" else 4500,
                        purpose,
                        pressure,
                        self._seasonal_note(week),
                        self.repo.to_json({"recommended_arc_tier": "tier_1_main_event" if tier == "tier_a" else "tier_2_midcard"}),
                        now,
                        now,
                    ),
                )
                if not before:
                    seeded_calendar += 1

            for vision_year, category, objective in self._vision_seed_rows():
                before = self.repo.fetch_one(
                    """
                    SELECT id FROM story_vision_goals
                    WHERE vision_year = ? AND category = ? AND objective = ? AND deleted_at IS NULL
                    """,
                    (vision_year, category, objective),
                )
                self.repo.conn.execute(
                    """
                    INSERT OR IGNORE INTO story_vision_goals (
                        id, vision_year, category, objective, target_json,
                        current_progress, status, evidence_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, 0, 'planned', '{}', ?, ?)
                    """,
                    (
                        f"vision_{vision_year}_{category}_{sum(ord(c) for c in objective)}",
                        vision_year,
                        category,
                        objective,
                        self.repo.to_json({"source": "ai_foundation"}),
                        now,
                        now,
                    ),
                )
                if not before:
                    seeded_vision += 1

        return {"templates": seeded_templates, "calendar_events": seeded_calendar, "vision_goals": seeded_vision}

    def run_story_arc_ai_week(self, year: int, week: int, seed: int | None = None, auto: bool = False, force: bool = False) -> dict:
        existing = self.repo.fetch_one(
            """
            SELECT result_json
            FROM internal_simulation_jobs
            WHERE job_type = 'story_arc_ai_weekly'
              AND trigger_year = ?
              AND trigger_week = ?
              AND status = 'completed'
              AND deleted_at IS NULL
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (year, week),
        )
        if existing and not force:
            return {"already_ran": True, "previous_result": self.repo.from_json(existing.get("result_json"), {})}

        foundation = self.ensure_story_arc_foundation(year)
        created_from_feuds = self._ensure_story_arcs_for_active_feuds(year, week)
        drafted = self._draft_ai_story_if_needed(year, week)
        health = self._scan_story_arc_health(year, week)
        due_reviews = self._create_due_milestone_reviews(year, week)
        disruption_reviews = self._scan_dynamic_event_disruptions(year, week)
        vision = self._update_story_vision_progress(year, week)
        result = {
            "already_ran": False,
            "foundation": foundation,
            "created_from_feuds": created_from_feuds,
            "drafted": drafted,
            "health": health,
            "due_reviews": due_reviews,
            "disruption_reviews": disruption_reviews,
            "vision": vision,
            "pending_reviews": len(self.pending_story_arc_reviews()),
            "auto": bool(auto),
        }
        self.repo.log_job(
            "story_arc_ai_weekly",
            year,
            week,
            "completed",
            ["story_feuds", "story_arcs", "dynamic_event_records", "wrestlers", "show_history"],
            ["story_arcs", "story_arc_milestones", "story_arc_reviews", "story_arc_health_snapshots", "story_calendar_events"],
            result,
        )
        return result

    def story_arc_ai_dashboard(self) -> dict:
        state = self.database.get_game_state() if hasattr(self.database, "get_game_state") else {"current_year": 1, "current_week": 1}
        year = int(state.get("current_year", 1))
        week = int(state.get("current_week", 1))
        self.ensure_story_arc_foundation(year)
        arcs = self.repo.fetch_all(
            """
            SELECT a.*, p.tier, p.priority_score, p.investment_score, p.fatigue_score,
                   p.continuity_risk_score, p.retcon_risk_score, p.ai_strategy_json
            FROM story_arcs a
            LEFT JOIN story_arc_planning_profiles p ON p.arc_id = a.id AND p.deleted_at IS NULL
            WHERE a.deleted_at IS NULL
            ORDER BY CASE a.status WHEN 'pending_review' THEN 0 WHEN 'active' THEN 1 ELSE 2 END,
                     p.priority_score DESC, a.updated_at DESC
            LIMIT 30
            """
        )
        for arc in arcs:
            arc["cast_json"] = self.repo.from_json(arc.get("cast_json"), [])
            arc["ai_strategy_json"] = self.repo.from_json(arc.get("ai_strategy_json"), {})
            arc["milestones"] = self._arc_milestones(arc["id"])
            arc["health"] = self._latest_arc_health(arc["id"])
        calendar = self.repo.fetch_all(
            """
            SELECT *
            FROM story_calendar_events
            WHERE deleted_at IS NULL
              AND ((year * 52) + week) >= ?
            ORDER BY year, week
            LIMIT 16
            """,
            (self._total_week(year, week),),
        )
        for event in calendar:
            event["booking_strategy_json"] = self.repo.from_json(event.get("booking_strategy_json"), {})
        return {
            "summary": {
                "active_arcs": len([arc for arc in arcs if arc.get("status") == "active"]),
                "draft_arcs": len([arc for arc in arcs if arc.get("status") == "pending_review"]),
                "pending_reviews": len(self.pending_story_arc_reviews()),
                "next_calendar_events": len(calendar),
            },
            "arcs": arcs,
            "pending_reviews": self.pending_story_arc_reviews(20),
            "calendar": calendar,
            "vision": self.repo.fetch_all("SELECT * FROM story_vision_goals WHERE deleted_at IS NULL ORDER BY vision_year, category LIMIT 30"),
        }

    def pending_story_arc_reviews(self, limit: int = 8) -> list[dict]:
        rows = self.repo.fetch_all(
            """
            SELECT *
            FROM story_arc_reviews
            WHERE status = 'pending' AND deleted_at IS NULL
            ORDER BY CASE severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                     created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        for row in rows:
            row["options_json"] = self.repo.from_json(row.get("options_json"), [])
            row["payload_json"] = self.repo.from_json(row.get("payload_json"), {})
        return rows

    def story_arc_ai_pulse(self, data: dict | None = None) -> dict:
        data = data or {}
        state = self.database.get_game_state() if hasattr(self.database, "get_game_state") else {}
        year = int(data.get("year") or state.get("current_year", 1))
        week = int(data.get("week") or state.get("current_week", 1))
        if data.get("run_ai", True):
            self.run_story_arc_ai_week(year, week, data.get("seed"), auto=True)
        reviews = self.pending_story_arc_reviews(int(data.get("limit", 5)))
        return {
            "needs_review": bool(reviews),
            "reviews": reviews,
            "pending_count": len(self.pending_story_arc_reviews(50)),
        }

    def decide_story_arc_review(self, review_id: str, data: dict) -> dict:
        review = self.repo.fetch_one(
            "SELECT * FROM story_arc_reviews WHERE id = ? AND deleted_at IS NULL",
            (review_id,),
        )
        if not review:
            raise ValidationError("Story arc review not found")
        if review["status"] != "pending":
            raise ValidationError("Story arc review is already resolved")
        decision = data.get("decision", "approve")
        selected_option = data.get("selected_option") or decision
        now = self.repo.now()
        with self.repo.transaction():
            self.repo.conn.execute(
                """
                UPDATE story_arc_reviews
                SET status = ?, selected_option = ?, decision_notes = ?,
                    updated_at = ?, resolved_at = ?
                WHERE id = ?
                """,
                (
                    "approved" if decision in {"approve", "approved"} else "rejected" if decision in {"reject", "rejected"} else "deferred",
                    selected_option,
                    data.get("notes"),
                    now,
                    now,
                    review_id,
                ),
            )
            if decision in {"approve", "approved"}:
                if review.get("arc_id"):
                    self.repo.conn.execute(
                        """
                        UPDATE story_arcs
                        SET status = CASE WHEN status = 'pending_review' THEN 'active' ELSE status END,
                            updated_at = ?
                        WHERE id = ?
                        """,
                        (now, review["arc_id"]),
                    )
                if review.get("milestone_id"):
                    self.repo.conn.execute(
                        """
                        UPDATE story_arc_milestones
                        SET status = CASE WHEN status = 'planned' THEN 'approved' ELSE status END,
                            health_status = 'locked',
                            approved_at = COALESCE(approved_at, ?),
                            updated_at = ?
                        WHERE id = ?
                        """,
                        (now, now, review["milestone_id"]),
                    )
        return self.repo.fetch_one("SELECT * FROM story_arc_reviews WHERE id = ?", (review_id,))

    def handle_story_disruption_event(self, event: dict) -> dict | None:
        if not event:
            return None
        event_id = event.get("id")
        if not event_id:
            return None
        existing = self.repo.fetch_one(
            """
            SELECT id FROM story_arc_reviews
            WHERE source_type = 'dynamic_event' AND source_id = ? AND deleted_at IS NULL
            """,
            (event_id,),
        )
        if existing:
            return existing
        event_type = event.get("event_type", "dynamic_event")
        severity_score = float(event.get("severity_score", 50) or 50)
        severity = "critical" if severity_score >= 78 else "high" if severity_score >= 62 else "medium"
        arc = self._best_arc_for_event(event)
        options = self._rebooking_options_for_event(event_type)
        return self._create_story_review(
            review_type="dynamic_rebooking",
            severity=severity,
            source_type="dynamic_event",
            source_id=event_id,
            arc_id=arc.get("id") if arc else None,
            milestone_id=None,
            title=f"Review disruption: {event.get('title', event_type.replace('_', ' '))}",
            summary=f"The simulation generated a {event_type.replace('_', ' ')} that may disrupt active storyline plans.",
            recommendation=options[0]["label"],
            options=options,
            due_year=event.get("year"),
            due_week=event.get("week"),
            payload={"dynamic_event": event},
        )

    def process_story_arc_show_result(self, show_draft, show_result, universe=None) -> dict:
        year = int(self._row_or_attr(show_draft, "year", 1))
        week = int(self._row_or_attr(show_draft, "week", 1))
        show_id = self._row_or_attr(show_draft, "show_id")
        completed = []
        due = self.repo.fetch_all(
            """
            SELECT *
            FROM story_arc_milestones
            WHERE planned_year = ? AND planned_week = ?
              AND status IN ('planned', 'approved')
              AND deleted_at IS NULL
            """,
            (year, week),
        )
        quality = self._show_quality_estimate(show_result)
        now = self.repo.now()
        with self.repo.transaction():
            for milestone in due:
                score = self.clamp(quality + (8 if milestone["status"] == "approved" else -6))
                self.repo.conn.execute(
                    """
                    UPDATE story_arc_milestones
                    SET status = 'completed', health_status = 'completed',
                        completed_at = ?, success_score = ?,
                        impact_scores_json = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        now,
                        round(score, 2),
                        self.repo.to_json({
                            "execution_quality": round(score, 2),
                            "show_id": show_id,
                            "crowd_response": round(quality, 2),
                        }),
                        now,
                        milestone["id"],
                    ),
                )
                completed.append({"milestone_id": milestone["id"], "score": round(score, 2)})
        return {"completed_milestones": completed, "count": len(completed)}

    def _calendar_competition_pressure(self, year: int, week: int) -> float:
        rows = self.repo.fetch_all(
            """
            SELECT audience_overlap_score, impact_modifier
            FROM competing_events
            WHERE (year IS NULL OR year = ?) AND week = ? AND deleted_at IS NULL
            """,
            (year, week),
        )
        if rows:
            return self.clamp(sum(float(row["audience_overlap_score"]) * float(row["impact_modifier"]) for row in rows) / max(1, len(rows)))
        if week in {5, 6}:
            return 85.0
        if 35 <= week <= 47:
            return 55.0
        return 25.0

    def _suggest_market_for_event(self, tier: str, week: int) -> str:
        if tier == "tier_a":
            return "New York" if week in {12, 52} else "Los Angeles"
        if tier == "tier_b":
            return "Chicago"
        if week == 43:
            return "Philadelphia"
        return "Atlanta"

    def _seasonal_note(self, week: int) -> str:
        if week <= 5:
            return "New year and football playoff competition require clear hooks."
        if 10 <= week <= 13:
            return "Spring spectacular window favors major payoffs."
        if 25 <= week <= 31:
            return "Summer audience availability supports major events and tours."
        if 35 <= week <= 39:
            return "Television season reset; plant autumn directions."
        if week >= 48:
            return "Holiday/year-end emotional resonance and finale booking."
        return "Standard calendar window."

    def _vision_seed_rows(self) -> list[tuple[int, str, str]]:
        return [
            (1, "business", "Establish promotion identity and reliable audience baseline"),
            (1, "creative", "Launch two signature characters and one defining championship arc"),
            (1, "roster", "Identify three cornerstone five-year performers"),
            (2, "business", "Grow audience 25 percent and improve media terms"),
            (2, "creative", "Complete first legendary long-form storyline"),
            (3, "business", "Run first major arena or stadium-scale event"),
            (3, "roster", "Graduate first developmental talent into a main event trajectory"),
            (4, "creative", "Establish second generation stars beside founding generation"),
            (5, "legacy", "Stage fifth anniversary as a historical milestone"),
        ]

    def _arc_tier_for_feud(self, feud: dict) -> str:
        heat = float(feud.get("heat_score", 0) or 0)
        duration = int(feud.get("duration_target_weeks", 8) or 8)
        if heat >= 70 or duration >= 14:
            return "tier_1_main_event"
        if heat >= 45 or duration >= 8:
            return "tier_2_midcard"
        return "tier_3_undercard"

    def _template_for_tier(self, tier: str, feud: dict | None = None) -> str:
        basis = (feud or {}).get("basis", "")
        if "betray" in basis:
            return "betrayal_and_revenge"
        if tier == "tier_1_main_event":
            return "classic_babyface_chase"
        if tier == "tier_2_midcard":
            return "underdog_redemption"
        if tier == "tier_4_background":
            return "mystery_attacker"
        return "unlikely_tag_alliance"

    def _offset_year_week(self, year: int, week: int, offset: int) -> tuple[int, int]:
        total = self._total_week(year, week) + int(offset)
        new_year = max(1, (total - 1) // 52)
        new_week = ((total - 1) % 52) + 1
        return new_year, new_week

    def _scaled_milestone_offsets(self, duration: int) -> list[int]:
        duration = max(4, int(duration))
        ratios = [0, 0.18, 0.34, 0.52, 0.72, 0.92, 1.0]
        return [min(duration, max(0, round(duration * ratio))) for ratio in ratios]

    def _milestone_description(self, milestone_type: str, arc_name: str) -> str:
        descriptions = {
            "seed": "Plant a subtle clue that rewards attentive viewers later.",
            "inciting_incident": "Make the story unmistakable to the audience.",
            "escalation": "Raise the stakes in a visibly larger way.",
            "flashpoint": "Create the mid-arc moment that redefines the conflict.",
            "crisis_peak": "Put the protagonist at their lowest emotional point.",
            "payoff": "Deliver the promised emotional resolution.",
            "aftermath": "Turn the ending into the next chapter.",
        }
        return f"{descriptions.get(milestone_type, 'Advance the story.')} Arc: {arc_name}."

    def _emotion_target(self, milestone_type: str) -> str:
        return {
            "seed": "curiosity",
            "inciting_incident": "shock",
            "escalation": "anticipation",
            "flashpoint": "discussion",
            "crisis_peak": "sympathy_and_anger",
            "payoff": "catharsis",
            "aftermath": "forward_momentum",
        }.get(milestone_type, "engagement")

    def _production_notes(self, milestone_type: str) -> str:
        return {
            "seed": "Subtle camera linger or background placement.",
            "inciting_incident": "Full production value and clipped for social media.",
            "flashpoint": "Protect surprise while keeping motivation logical.",
            "crisis_peak": "Emphasize emotional consequence and crowd sympathy.",
            "payoff": "Premium event presentation and post-show replay package.",
        }.get(milestone_type, "Standard television execution.")

    def _arc_milestones(self, arc_id: str) -> list[dict]:
        rows = self.repo.fetch_all(
            """
            SELECT *
            FROM story_arc_milestones
            WHERE arc_id = ? AND deleted_at IS NULL
            ORDER BY planned_year, planned_week, created_at
            """,
            (arc_id,),
        )
        for row in rows:
            row["required_participants_json"] = self.repo.from_json(row.get("required_participants_json"), [])
            row["dependency_ids_json"] = self.repo.from_json(row.get("dependency_ids_json"), [])
            row["impact_scores_json"] = self.repo.from_json(row.get("impact_scores_json"), {})
        return rows

    def _latest_arc_health(self, arc_id: str) -> dict | None:
        row = self.repo.fetch_one(
            """
            SELECT *
            FROM story_arc_health_snapshots
            WHERE arc_id = ? AND deleted_at IS NULL
            ORDER BY year DESC, week DESC, created_at DESC
            LIMIT 1
            """,
            (arc_id,),
        )
        if row:
            row["metrics_json"] = self.repo.from_json(row.get("metrics_json"), {})
        return row

    def _story_lifecycle(self, age_weeks: int) -> str:
        if age_weeks <= 3:
            return "establishment"
        if age_weeks <= 7:
            return "momentum_building"
        if age_weeks <= 12:
            return "peak_investment"
        if age_weeks <= 18:
            return "diminishing_returns"
        return "fatigue"

    def _ensure_story_arcs_for_active_feuds(self, year: int, week: int) -> dict:
        created = []
        for feud in self.repo.list_story_feuds(active_only=True):
            existing = self.repo.fetch_one(
                """
                SELECT p.arc_id
                FROM story_arc_planning_profiles p
                WHERE p.source_type = 'story_feud' AND p.source_id = ? AND p.deleted_at IS NULL
                """,
                (feud["id"],),
            )
            if existing:
                continue
            participants = feud.get("participants") or []
            tier = self._arc_tier_for_feud(feud)
            template_id = self._template_for_tier(tier, feud)
            duration = max(int(feud.get("duration_target_weeks", 8) or 8), 6)
            arc = self.repo.insert_simple(
                "story_arcs",
                {
                    "id": new_id("story_arc"),
                    "name": feud["name"],
                    "premise": f"{feud['basis'].replace('_', ' ').title()} program tracked by the storyline arc AI.",
                    "status": "active",
                    "planned_duration_weeks": duration,
                    "start_year": int(feud.get("start_year") or year),
                    "start_week": int(feud.get("start_week") or week),
                    "cast_json": self.repo.to_json(participants),
                },
            )
            self._create_arc_profile(arc["id"], tier, template_id, "story_feud", feud["id"], feud, year, week)
            self._ensure_milestones_for_arc(arc, tier, template_id, participants, feud.get("id"))
            created.append(arc["id"])
        return {"created": len(created), "arc_ids": created}

    def _draft_ai_story_if_needed(self, year: int, week: int) -> dict:
        pending = self.repo.fetch_one(
            "SELECT COUNT(*) AS total FROM story_arc_reviews WHERE status = 'pending' AND review_type = 'new_arc_approval' AND deleted_at IS NULL"
        )
        active = self.repo.fetch_one("SELECT COUNT(*) AS total FROM story_arcs WHERE status = 'active' AND deleted_at IS NULL")
        if int((pending or {}).get("total") or 0) > 0 or int((active or {}).get("total") or 0) >= 3:
            return {"created": 0}
        wrestlers = self.repo.fetch_all(
            """
            SELECT id, name, popularity, momentum, role, primary_brand, age
            FROM wrestlers
            WHERE is_retired = 0
            ORDER BY popularity DESC, momentum DESC
            LIMIT 6
            """
        )
        if len(wrestlers) < 2:
            return {"created": 0, "reason": "not_enough_wrestlers"}
        first, second = wrestlers[0], wrestlers[1]
        tier = "tier_1_main_event" if int(first.get("popularity") or 0) >= 80 else "tier_2_midcard"
        template_id = "classic_babyface_chase" if tier == "tier_1_main_event" else "underdog_redemption"
        cast = [
            {"participant_id": first["id"], "participant_name": first["name"], "role": "protagonist"},
            {"participant_id": second["id"], "participant_name": second["name"], "role": "antagonist"},
        ]
        arc = self.repo.insert_simple(
            "story_arcs",
            {
                "id": new_id("story_arc"),
                "name": f"{first['name']} vs {second['name']}: AI Vision",
                "premise": "AI-drafted long-range program awaiting creative approval.",
                "status": "pending_review",
                "planned_duration_weeks": 12 if tier == "tier_1_main_event" else 8,
                "start_year": year,
                "start_week": week,
                "cast_json": self.repo.to_json(cast),
            },
        )
        self._create_arc_profile(arc["id"], tier, template_id, "ai_draft", None, {"heat_score": 50, "participants": cast}, year, week)
        self._ensure_milestones_for_arc(arc, tier, template_id, cast, None)
        review = self._create_story_review(
            review_type="new_arc_approval",
            severity="medium",
            source_type="story_arc_ai",
            source_id=arc["id"],
            arc_id=arc["id"],
            milestone_id=None,
            title=f"Approve new AI storyline: {arc['name']}",
            summary="The creative AI found available talent and drafted a connected long-range storyline.",
            recommendation="Approve the arc and allow milestone reviews to enter the weekly booking flow.",
            options=[
                {"key": "approve", "label": "Approve arc"},
                {"key": "revise", "label": "Request revision"},
                {"key": "reject", "label": "Reject arc"},
            ],
            due_year=year,
            due_week=week,
            payload={"cast": cast, "template_id": template_id, "tier": tier},
        )
        return {"created": 1, "arc_id": arc["id"], "review_id": review["id"]}

    def _create_arc_profile(self, arc_id: str, tier: str, template_id: str, source_type: str, source_id: str | None, feud: dict, year: int, week: int) -> dict:
        heat = float(feud.get("heat_score", 45) or 45)
        priority = self.clamp(heat + (15 if tier == "tier_1_main_event" else 5))
        return self.repo.insert_simple(
            "story_arc_planning_profiles",
            {
                "id": new_id("arc_profile"),
                "arc_id": arc_id,
                "tier": tier,
                "template_id": template_id,
                "source_type": source_type,
                "source_id": source_id,
                "planning_mode": "campaign" if tier in {"tier_1_main_event", "tier_2_midcard"} else "vision",
                "priority_score": round(priority, 2),
                "investment_score": round(self.clamp(heat), 2),
                "fatigue_score": 0,
                "continuity_risk_score": 10,
                "retcon_risk_score": 5,
                "payoff_window_start_year": year,
                "payoff_window_start_week": min(52, week + 8),
                "payoff_window_end_year": year + ((week + 14) // 53),
                "payoff_window_end_week": ((week + 14 - 1) % 52) + 1,
                "ai_strategy_json": self.repo.to_json({
                    "rule_of_three_escalations": True,
                    "two_week_stagnation_watch": True,
                    "protected_priority": tier,
                    "review_required_before_major_payoff": True,
                }),
            },
        )

    def _ensure_milestones_for_arc(self, arc: dict, tier: str, template_id: str, cast: list, feud_id: str | None) -> None:
        existing = self.repo.fetch_one("SELECT COUNT(*) AS total FROM story_arc_milestones WHERE arc_id = ? AND deleted_at IS NULL", (arc["id"],))
        if int((existing or {}).get("total") or 0) > 0:
            return
        start_year = int(arc["start_year"])
        start_week = int(arc["start_week"])
        offsets = self._scaled_milestone_offsets(int(arc["planned_duration_weeks"]))
        for index, (milestone_type, label, _, visibility) in enumerate(MILESTONE_SCHEMA):
            year, week = self._offset_year_week(start_year, start_week, offsets[index])
            self.repo.insert_simple(
                "story_arc_milestones",
                {
                    "id": new_id("arc_milestone"),
                    "arc_id": arc["id"],
                    "feud_id": feud_id,
                    "milestone_type": milestone_type,
                    "title": f"{label}: {arc['name']}",
                    "description": self._milestone_description(milestone_type, arc["name"]),
                    "planned_year": year,
                    "planned_week": week,
                    "status": "planned",
                    "health_status": "flexible",
                    "visibility": visibility,
                    "crowd_emotion_target": self._emotion_target(milestone_type),
                    "required_participants_json": self.repo.to_json(cast),
                    "dependency_ids_json": self.repo.to_json([]),
                    "production_notes": self._production_notes(milestone_type),
                    "impact_scores_json": self.repo.to_json({}),
                    "ai_generated": 1,
                    "requires_approval": 1 if milestone_type in {"inciting_incident", "flashpoint", "crisis_peak", "payoff"} else 0,
                },
            )

    def _scan_story_arc_health(self, year: int, week: int) -> dict:
        arcs = self.repo.fetch_all(
            """
            SELECT a.*, p.id AS profile_id, p.tier, p.priority_score, p.source_type, p.source_id
            FROM story_arcs a
            LEFT JOIN story_arc_planning_profiles p ON p.arc_id = a.id AND p.deleted_at IS NULL
            WHERE a.status IN ('active', 'pending_review') AND a.deleted_at IS NULL
            """
        )
        current_week = self._total_week(year, week)
        snapshots = []
        reviews = 0
        now = self.repo.now()
        for arc in arcs:
            start_total = self._total_week(int(arc["start_year"]), int(arc["start_week"]))
            age = max(0, current_week - start_total)
            milestones = self._arc_milestones(arc["id"])
            completed = len([m for m in milestones if m["status"] == "completed"])
            overdue = [
                m for m in milestones
                if m["status"] in {"planned", "approved"}
                and self._total_week(int(m["planned_year"]), int(m["planned_week"])) < current_week
            ]
            due = [
                m for m in milestones
                if m["status"] in {"planned", "approved"}
                and self._total_week(int(m["planned_year"]), int(m["planned_week"])) == current_week
            ]
            duration = max(1, int(arc.get("planned_duration_weeks") or 8))
            expected_completion = self.clamp((age / duration) * max(1, len(milestones)))
            stagnation_weeks = max(0, int(round(expected_completion - completed)))
            lifecycle = self._story_lifecycle(age)
            fatigue = self.clamp((age / duration) * 45 + len(overdue) * 12 - completed * 3)
            investment = self.clamp((completed * 14) + len(due) * 6 + float(arc.get("priority_score") or 45) * 0.35 - fatigue * 0.25)
            payoff_status = "not_due"
            if age >= duration:
                payoff_status = "overdue"
            elif age >= max(1, duration - 3):
                payoff_status = "approaching"
            recommended = "continue"
            if overdue:
                recommended = "repair_overdue_milestones"
            if fatigue >= 70:
                recommended = "payoff_or_mercy_rule"
            elif stagnation_weeks >= 3:
                recommended = "inject_escalation"

            snapshot = self.repo.insert_simple(
                "story_arc_health_snapshots",
                {
                    "id": new_id("arc_health"),
                    "arc_id": arc["id"],
                    "year": year,
                    "week": week,
                    "investment_score": round(investment, 2),
                    "fatigue_score": round(fatigue, 2),
                    "stagnation_weeks": stagnation_weeks,
                    "lifecycle_stage": lifecycle,
                    "payoff_window_status": payoff_status,
                    "recommended_action": recommended,
                    "metrics_json": self.repo.to_json({
                        "age_weeks": age,
                        "completed_milestones": completed,
                        "total_milestones": len(milestones),
                        "due_milestones": len(due),
                        "overdue_milestones": len(overdue),
                    }),
                    "created_at": now,
                    "updated_at": now,
                },
            )
            snapshots.append(snapshot["id"])
            self._update_arc_profile_health(arc["id"], investment, fatigue, len(overdue) * 18, len(overdue) * 12)
            if recommended in {"inject_escalation", "payoff_or_mercy_rule", "repair_overdue_milestones"}:
                review = self._create_unique_arc_review(
                    review_type="arc_health",
                    severity="high" if fatigue >= 70 or overdue else "medium",
                    source_type="story_arc_ai",
                    source_id=f"health_{arc['id']}_{year}_{week}",
                    arc_id=arc["id"],
                    milestone_id=None,
                    title=f"Storyline health review: {arc['name']}",
                    summary=f"{arc['name']} is in {lifecycle.replace('_', ' ')} with {stagnation_weeks} stagnation week(s).",
                    recommendation=recommended.replace("_", " ").title(),
                    options=[
                        {"key": "continue", "label": "Continue current plan"},
                        {"key": "escalate", "label": "Add escalation beat"},
                        {"key": "payoff", "label": "Move toward payoff"},
                        {"key": "abandon", "label": "Abandon quietly"},
                    ],
                    due_year=year,
                    due_week=week,
                    payload={"snapshot_id": snapshot["id"], "recommended_action": recommended},
                )
                if review:
                    reviews += 1
        return {"snapshots": len(snapshots), "reviews": reviews}

    def _create_due_milestone_reviews(self, year: int, week: int) -> dict:
        milestones = self.repo.fetch_all(
            """
            SELECT m.*, a.name AS arc_name
            FROM story_arc_milestones m
            JOIN story_arcs a ON a.id = m.arc_id
            WHERE m.planned_year = ? AND m.planned_week = ?
              AND m.status = 'planned'
              AND m.requires_approval = 1
              AND m.deleted_at IS NULL
              AND a.deleted_at IS NULL
            """,
            (year, week),
        )
        created = []
        for milestone in milestones:
            review = self._create_unique_arc_review(
                review_type="milestone_approval",
                severity="high" if milestone["milestone_type"] in {"flashpoint", "payoff"} else "medium",
                source_type="story_arc_milestone",
                source_id=milestone["id"],
                arc_id=milestone["arc_id"],
                milestone_id=milestone["id"],
                title=f"Approve milestone: {milestone['title']}",
                summary=milestone["description"],
                recommendation="Approve this milestone for the current booking week or request a pivot.",
                options=[
                    {"key": "approve", "label": "Approve milestone"},
                    {"key": "delay", "label": "Delay one week"},
                    {"key": "pivot", "label": "Request a pivot"},
                ],
                due_year=year,
                due_week=week,
                payload={
                    "arc_name": milestone["arc_name"],
                    "milestone_type": milestone["milestone_type"],
                    "participants": self.repo.from_json(milestone.get("required_participants_json"), []),
                },
            )
            if review:
                created.append(review["id"])
        return {"created": len(created), "review_ids": created}

    def _scan_dynamic_event_disruptions(self, year: int, week: int) -> dict:
        events = self.repo.fetch_all(
            """
            SELECT *
            FROM dynamic_event_records
            WHERE year = ? AND week = ?
              AND status = 'open'
              AND deleted_at IS NULL
            ORDER BY severity_score DESC, created_at DESC
            LIMIT 10
            """,
            (year, week),
        )
        created = []
        for event in events:
            review = self.handle_story_disruption_event(event)
            if review and review.get("id"):
                created.append(review["id"])
        return {"created": len(created), "event_count": len(events), "review_ids": created}

    def _update_story_vision_progress(self, year: int, week: int) -> dict:
        active = self.repo.fetch_one("SELECT COUNT(*) AS total FROM story_arcs WHERE status = 'active' AND deleted_at IS NULL")
        payoffs = self.repo.fetch_one("SELECT AVG(success_score) AS avg_score FROM story_arc_milestones WHERE milestone_type = 'payoff' AND status = 'completed' AND deleted_at IS NULL")
        calendar = self.repo.fetch_one("SELECT COUNT(*) AS total FROM story_calendar_events WHERE year = ? AND deleted_at IS NULL", (year,))
        active_total = int((active or {}).get("total") or 0)
        avg_payoff = float((payoffs or {}).get("avg_score") or 0)
        calendar_total = int((calendar or {}).get("total") or 0)
        updated = 0
        now = self.repo.now()
        goals = self.repo.fetch_all("SELECT * FROM story_vision_goals WHERE deleted_at IS NULL")
        with self.repo.transaction():
            for goal in goals:
                category = goal["category"]
                if category == "creative":
                    progress = self.clamp(active_total * 18 + avg_payoff * 0.45)
                elif category == "legacy":
                    progress = self.clamp(avg_payoff + active_total * 8)
                elif category == "business":
                    progress = self.clamp(calendar_total * 6 + active_total * 8)
                else:
                    progress = self.clamp(active_total * 10)
                status = "achieved" if progress >= 100 else "active" if progress > 0 else goal.get("status", "planned")
                self.repo.conn.execute(
                    """
                    UPDATE story_vision_goals
                    SET current_progress = ?, status = ?, evidence_json = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        round(progress, 2),
                        status,
                        self.repo.to_json({
                            "active_arcs": active_total,
                            "avg_payoff_score": round(avg_payoff, 2),
                            "calendar_events": calendar_total,
                            "as_of": {"year": year, "week": week},
                        }),
                        now,
                        goal["id"],
                    ),
                )
                updated += 1
        return {"updated": updated, "active_arcs": active_total, "avg_payoff_score": round(avg_payoff, 2)}

    def _create_story_review(
        self,
        review_type: str,
        severity: str,
        source_type: str,
        source_id: str | None,
        arc_id: str | None,
        milestone_id: str | None,
        title: str,
        summary: str,
        recommendation: str,
        options: list[dict],
        due_year: int | None,
        due_week: int | None,
        payload: dict | None = None,
    ) -> dict:
        return self.repo.insert_simple(
            "story_arc_reviews",
            {
                "id": new_id("arc_review"),
                "review_type": review_type,
                "severity": severity,
                "status": "pending",
                "source_type": source_type,
                "source_id": source_id,
                "arc_id": arc_id,
                "milestone_id": milestone_id,
                "title": title,
                "summary": summary,
                "ai_recommendation": recommendation,
                "options_json": self.repo.to_json(options),
                "due_year": due_year,
                "due_week": due_week,
                "payload_json": self.repo.to_json(payload or {}),
            },
        )

    def _create_unique_arc_review(self, **kwargs) -> dict | None:
        existing = self.repo.fetch_one(
            """
            SELECT *
            FROM story_arc_reviews
            WHERE review_type = ?
              AND source_type = ?
              AND COALESCE(source_id, '') = COALESCE(?, '')
              AND status = 'pending'
              AND deleted_at IS NULL
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (kwargs.get("review_type"), kwargs.get("source_type"), kwargs.get("source_id")),
        )
        if existing:
            return None
        return self._create_story_review(**kwargs)

    def _update_arc_profile_health(self, arc_id: str, investment: float, fatigue: float, continuity: float, retcon: float) -> None:
        self.repo.conn.execute(
            """
            UPDATE story_arc_planning_profiles
            SET investment_score = ?, fatigue_score = ?,
                continuity_risk_score = ?, retcon_risk_score = ?,
                updated_at = ?
            WHERE arc_id = ? AND deleted_at IS NULL
            """,
            (
                round(self.clamp(investment), 2),
                round(self.clamp(fatigue), 2),
                round(self.clamp(continuity), 2),
                round(self.clamp(retcon), 2),
                self.repo.now(),
                arc_id,
            ),
        )
        self.repo.conn.commit()

    def _best_arc_for_event(self, event: dict) -> dict | None:
        wrestler_ids = {
            event.get("primary_wrestler_id"),
            event.get("secondary_wrestler_id"),
        } - {None, ""}
        arcs = self.repo.fetch_all(
            """
            SELECT a.*, p.priority_score
            FROM story_arcs a
            LEFT JOIN story_arc_planning_profiles p ON p.arc_id = a.id AND p.deleted_at IS NULL
            WHERE a.status IN ('active', 'pending_review') AND a.deleted_at IS NULL
            ORDER BY p.priority_score DESC, a.updated_at DESC
            LIMIT 20
            """
        )
        for arc in arcs:
            cast = self.repo.from_json(arc.get("cast_json"), [])
            cast_ids = {
                item.get("participant_id") or item.get("wrestler_id") or item.get("id")
                for item in cast
                if isinstance(item, dict)
            }
            if wrestler_ids & cast_ids:
                return arc
        return arcs[0] if arcs else None

    def _rebooking_options_for_event(self, event_type: str) -> list[dict]:
        base = [
            {"key": "approve_pivot", "label": "Approve AI pivot"},
            {"key": "manual_review", "label": "Hold for manual booking"},
            {"key": "protect_continuity", "label": "Protect existing continuity"},
        ]
        additions = {
            "match_injury_rebooking": [
                {"key": "emergency_substitute", "label": "Book emergency substitute"},
                {"key": "vacate_or_delay", "label": "Delay affected payoff"},
            ],
            "wrestler_no_show": [
                {"key": "discipline_and_rebook", "label": "Discipline and rebook segment"},
                {"key": "turn_absence_into_angle", "label": "Turn absence into storyline"},
            ],
            "storyline_leak": [
                {"key": "swerve_finish", "label": "Create controlled swerve"},
                {"key": "lean_into_leak", "label": "Make leak part of canon"},
            ],
            "network_interference": [
                {"key": "adjust_for_network", "label": "Adjust for network demands"},
                {"key": "push_back", "label": "Push back creatively"},
            ],
            "organic_alignment_turn": [
                {"key": "follow_crowd", "label": "Follow organic crowd reaction"},
                {"key": "slow_burn_turn", "label": "Slow-burn alignment shift"},
            ],
        }
        return additions.get(event_type, []) + base

    def _show_quality_estimate(self, show_result) -> float:
        values = []
        for match in getattr(show_result, "match_results", []) or []:
            values.append(float(getattr(match, "star_rating", 2.5) or 2.5) * 20)
        for segment in getattr(show_result, "segment_results", []) or []:
            values.append(float(getattr(segment, "segment_rating", 2.5) or 2.5) * 20)
        return self.clamp(sum(values) / len(values)) if values else 55.0

    def _apply_heat_decay(self, year: int, week: int) -> dict:
        feuds = self.repo.list_story_feuds(active_only=True)
        updates = []
        current_week = self._total_week(year, week)
        for feud in feuds:
            heat = float(feud["heat_score"])
            last_year = feud.get("last_action_year") or feud["start_year"]
            last_week = feud.get("last_action_week") or feud["start_week"]
            idle = max(0, current_week - self._total_week(last_year, last_week))
            if idle <= 0:
                continue
            decay = 1.5 + min(5.0, idle * 0.45)
            if heat >= 70:
                decay *= 0.75
            if heat <= 30:
                decay *= 1.25
            after = self.clamp(heat - decay)
            weeks_at_nuclear = int(feud.get("weeks_at_nuclear", 0) or 0)
            if after >= 86:
                weeks_at_nuclear += 1
            else:
                weeks_at_nuclear = 0
            fatigue = float(feud.get("fatigue_penalty", 0) or 0)
            if weeks_at_nuclear > 3:
                fatigue += 2
                after = self.clamp(after - 2)
            self.repo.update_story_feud_heat(
                feud["id"],
                after,
                self.heat_level(after),
                "declining" if after < heat else "stable",
                extra_updates={"weeks_at_nuclear": weeks_at_nuclear, "fatigue_penalty": fatigue},
            )
            updates.append({"feud_id": feud["id"], "before": heat, "after": after, "decay": round(decay, 2)})
        return {"updated": len(updates), "feuds": updates}

    def _apply_social_growth(self, year: int, week: int) -> dict:
        rows = self.repo.get_social_metrics()
        total_gain = 0
        for platform in rows:
            quality_factor = float(platform["engagement_rate"]) * 100
            gain = int(max(25, float(platform["follower_count"]) * (0.001 + quality_factor / 100000)))
            self.repo.add_social_spike(
                {
                    "source_type": "organic_growth",
                    "description": f"Organic weekly growth on {platform['platform']}",
                    "spike_score": quality_factor,
                    "follower_gain": gain,
                    "engagement_delta": 0.0005,
                    "platforms_json": [platform["platform"]],
                    "year": year,
                    "week": week,
                }
            )
            total_gain += gain
        return {"platforms": len(rows), "estimated_total_gain": total_gain}

    def _apply_network_trend(self, year: int, week: int) -> dict:
        recent = self.repo.get_recent_ratings(12)
        if len(recent) < 6:
            return {"change": 0, "reason": "Insufficient ratings history"}
        ordered = list(reversed(recent[:12]))
        first = ordered[: len(ordered) // 2]
        second = ordered[len(ordered) // 2:]
        first_avg = sum(row["total_viewership"] for row in first) / len(first)
        second_avg = sum(row["total_viewership"] for row in second) / len(second)
        pct = (second_avg - first_avg) / max(1, first_avg)
        change = 0
        if pct > 0.04:
            change = 2.5
        elif pct < -0.04:
            change = -3.0
        if change:
            self.repo.update_network_relationship(change, "Three-month ratings trend adjustment", year, week)
        return {"change": change, "trend_pct": round(pct, 4)}

    def _recalculate_business_snapshot(self, year: int, week: int) -> dict:
        social = self.repo.get_social_metrics()
        followers = sum(int(row["follower_count"]) for row in social)
        engagement = sum(float(row["engagement_rate"]) for row in social) / max(1, len(social))
        recent = self.repo.get_recent_ratings(6)
        avg_viewers = sum(row["total_viewership"] for row in recent) / max(1, len(recent)) if recent else 850000
        network = self.repo.get_primary_network()
        awareness = self.clamp((followers / 50000) + (avg_viewers / 50000))
        sponsorship = self.clamp(awareness * 0.40 + float(network["relationship_score"]) * 0.35 + engagement * 250)
        streaming = self.clamp(awareness * 0.50 + len(self.repo.fetch_all("SELECT id FROM digital_content_library WHERE deleted_at IS NULL")) * 0.8)
        snapshot = {
            "year": year,
            "week": week,
            "mainstream_awareness": round(awareness, 2),
            "sponsorship_attractiveness": round(sponsorship, 2),
            "streaming_attractiveness": round(streaming, 2),
            "booking_credibility": round(float(network["relationship_score"]), 2),
            "promotion_momentum": round(self.clamp((avg_viewers / 20000) + float(network["relationship_score"]) / 2), 2),
            "valuation_estimate": int((avg_viewers * 8) + (followers * 2.5) + (sponsorship * 100000)),
            "metadata_json": {"followers": followers, "avg_viewers": avg_viewers},
        }
        return self.repo.upsert_business_snapshot(snapshot)

    def process_show_result(self, show_draft, show_result, universe=None, production_plan: dict | None = None) -> dict:
        actuals: dict[str, dict] = {}
        for match in getattr(show_result, "match_results", []) or []:
            actuals[match.match_id] = {
                "actual_duration_minutes": getattr(match, "duration_minutes", None),
                "quality_score": float(getattr(match, "star_rating", 0) or 0) * 20,
                "crowd_heat_score": getattr(match, "crowd_energy", 50),
            }
        for segment in getattr(show_result, "segment_results", []) or []:
            actuals[segment.segment_id] = {
                "actual_duration_minutes": getattr(segment, "duration_minutes", None),
                "quality_score": float(getattr(segment, "segment_rating", 0) or 0) * 20,
                "crowd_heat_score": getattr(segment, "crowd_heat", 50),
            }

        plan, segments = self.build_show_plan_from_draft(
            show_draft,
            production_plan=production_plan,
            universe=universe,
            actuals=actuals,
            accept_overrun=True,
        )
        saved_plan = self.repo.replace_show_plan(plan, segments)
        self._record_opening_and_main_event_assessments(saved_plan)
        self._apply_show_to_storylines(show_draft, show_result, universe)
        story_arc_result = self.process_story_arc_show_result(show_draft, show_result, universe)
        ratings = self.calculate_tv_ratings(show_draft, show_result, saved_plan)
        saved_rating = self.repo.save_ratings_bundle(
            ratings["rating"],
            ratings["quarters"],
            ratings["demographics"],
            ratings["insights"],
        )
        network_change = self._network_change_from_show(ratings["rating"], saved_plan)
        network = self.repo.update_network_relationship(
            network_change,
            f"Show rating impact for {ratings['rating']['show_name']}",
            ratings["rating"]["year"],
            ratings["rating"]["week"],
            ratings["rating"]["show_id"],
        )
        self._social_spikes_from_show(show_draft, show_result, ratings["rating"])
        jobs = self.run_weekly_jobs(ratings["rating"]["year"], ratings["rating"]["week"])
        result = {
            "booking_plan": saved_plan,
            "story_arc_ai": story_arc_result,
            "ratings": saved_rating,
            "network": network,
            "jobs": jobs,
        }
        setattr(show_result, "media_business_result", result)
        if hasattr(show_result, "add_event"):
            show_result.add_event(
                "media_business",
                f"TV rating {ratings['rating']['rating_score']:.3f} with {ratings['rating']['total_viewership']:,} viewers"
            )
        return result

    def _record_opening_and_main_event_assessments(self, plan: dict) -> None:
        opener = next((segment for segment in plan.get("segments", []) if segment.get("is_opening")), None)
        main = next((segment for segment in plan.get("segments", []) if segment.get("is_main_event")), None)
        self.repo.conn.execute("DELETE FROM opening_segment_assessments WHERE show_id = ?", (plan["show_id"],))
        self.repo.conn.execute("DELETE FROM main_event_assessments WHERE show_id = ?", (plan["show_id"],))
        self.repo.conn.commit()
        if opener:
            planned = self.clamp((float(opener.get("expected_max_minutes", 10)) / max(1, opener.get("planned_duration_minutes", 5))) * 45 + 20)
            actual = float(opener.get("quality_score") or planned)
            self.repo.insert_simple(
                "opening_segment_assessments",
                {
                    "id": new_id("opening"),
                    "show_id": plan["show_id"],
                    "segment_id": opener["source_item_id"],
                    "planned_quality_score": round(planned, 2),
                    "actual_performance_score": round(actual, 2),
                    "ratings_impact": round((actual - 50) / 500, 4),
                    "viewer_retention_effect": round((actual - 50) / 300, 4),
                    "inputs_json": self.repo.to_json(opener),
                },
            )
        if main:
            actual = float(main.get("quality_score") or 55)
            expected = self.clamp(55 + (10 if main.get("title_id") else 0) + (10 if main.get("feud_id") else 0))
            effect = -0.12 if actual < 45 else 0.10 if actual > 85 else (actual - expected) / 500
            self.repo.insert_simple(
                "main_event_assessments",
                {
                    "id": new_id("main_event"),
                    "show_id": plan["show_id"],
                    "segment_id": main["source_item_id"],
                    "expected_quality_score": round(expected, 2),
                    "actual_quality_score": round(actual, 2),
                    "overall_rating_effect": round(effect, 4),
                    "network_effect": round(effect * 20, 2),
                    "social_reaction_score": round(self.clamp(actual), 2),
                    "failure_recorded": 1 if actual < 45 else 0,
                    "inputs_json": self.repo.to_json(main),
                },
            )

    def _apply_show_to_storylines(self, show_draft, show_result, universe=None) -> None:
        year = int(self._row_or_attr(show_draft, "year", 1))
        week = int(self._row_or_attr(show_draft, "week", 1))
        match_lookup = {self._row_or_attr(match, "match_id"): match for match in self._row_or_attr(show_draft, "matches", []) or []}
        for match_result in getattr(show_result, "match_results", []) or []:
            match = match_lookup.get(match_result.match_id)
            feud_id = self._row_or_attr(match, "feud_id") if match else None
            story_feud_id = self._ensure_story_feud_from_legacy(feud_id, match, universe, year, week) if feud_id else None
            participant_ids = self._participant_ids_from_match(match) if match else []
            if not story_feud_id:
                active = self.repo.get_active_story_feuds_for_wrestlers(participant_ids)
                story_feud_id = active[0]["id"] if active else None
            if story_feud_id:
                quality = float(getattr(match_result, "star_rating", 3.0)) * 20
                heat_delta = round((quality - 50) / 8 + (4 if getattr(match_result, "is_title_match", False) else 0), 2)
                self.add_heat_action(
                    story_feud_id,
                    {
                        "action_type": "match",
                        "action_category": "match",
                        "description": getattr(match_result, "match_summary", "Feud match"),
                        "participants": participant_ids,
                        "quality_score": quality,
                        "year": year,
                        "week": week,
                        "show_id": self._row_or_attr(show_draft, "show_id"),
                    },
                )
                self.apply_heat_delta(story_feud_id, heat_delta, year, week, "match_quality")
                if self._row_or_attr(match, "importance") == "high_drama" and quality >= 65:
                    self.create_payoff(
                        {
                            "feud_id": story_feud_id,
                            "show_id": self._row_or_attr(show_draft, "show_id"),
                            "match_id": match_result.match_id,
                            "heat_at_booking": self._linked_feud_heat(story_feud_id),
                            "match_quality": getattr(match_result, "star_rating", 3.0),
                            "finish_type": getattr(getattr(match_result, "finish_type", None), "value", "clean_pin"),
                            "closure_score": quality,
                        }
                    )

    def _ensure_story_feud_from_legacy(self, legacy_feud_id: str, match: Any, universe=None, year: int = 1, week: int = 1) -> str | None:
        existing = self.repo.fetch_one(
            "SELECT id FROM story_feuds WHERE legacy_feud_id = ? AND deleted_at IS NULL",
            (legacy_feud_id,),
        )
        if existing:
            return existing["id"]
        participant_ids = self._participant_ids_from_match(match)
        if len(participant_ids) < 2:
            return None
        participants = [{"participant_id": pid, "participant_name": self._wrestler_name(pid, universe)} for pid in participant_ids[:2]]
        created = self.create_story_feud(
            {
                "legacy_feud_id": legacy_feud_id,
                "participants": participants,
                "basis": "personal_grudge",
                "initial_heat": 35,
                "duration_target_weeks": 8,
                "intended_conclusion_match_type": self._row_or_attr(match, "match_type", "singles"),
                "year": year,
                "week": week,
            },
            universe,
        )
        return created["id"]

    def _network_change_from_show(self, rating: dict, plan: dict) -> float:
        change = 0.0
        if rating["booking_quality_score"] >= 75:
            change += 2.0
        elif rating["booking_quality_score"] < 45:
            change -= 2.5
        if rating["total_viewership"] > rating["base_viewership"] * 1.05:
            change += 1.5
        elif rating["total_viewership"] < rating["base_viewership"] * 0.92:
            change -= 2.0
        if plan.get("overrun_minutes", 0) > 0:
            change -= min(4.0, plan["overrun_minutes"] * 0.4)
        return round(change, 2)

    def _social_spikes_from_show(self, show_draft, show_result, rating: dict) -> None:
        year = rating["year"]
        week = rating["week"]
        show_id = rating["show_id"]
        for match_result in getattr(show_result, "match_results", []) or []:
            if getattr(match_result, "title_changed_hands", False):
                score = 82
                self.repo.add_social_spike(
                    {
                        "show_id": show_id,
                        "source_type": "title_change",
                        "source_id": match_result.match_id,
                        "description": f"Title change: {getattr(match_result, 'new_champion_name', 'New champion')}",
                        "spike_score": score,
                        "follower_gain": int(score * 90),
                        "engagement_delta": 0.025,
                        "year": year,
                        "week": week,
                    }
                )
            if getattr(match_result, "is_upset", False):
                score = 70
                self.repo.add_social_spike(
                    {
                        "show_id": show_id,
                        "source_type": "upset",
                        "source_id": match_result.match_id,
                        "description": "Tournament or match upset generated conversation",
                        "spike_score": score,
                        "follower_gain": int(score * 55),
                        "engagement_delta": 0.018,
                        "year": year,
                        "week": week,
                    }
                )

    def _linked_feud_heat(self, feud_id: str | None) -> float:
        if not feud_id:
            return 30.0
        story = self.repo.get_story_feud(feud_id)
        if story:
            return float(story["heat_score"])
        legacy = self.repo.fetch_one("SELECT intensity FROM feuds WHERE id = ?", (feud_id,))
        return float(legacy["intensity"]) if legacy else 30.0

    def media_business_dashboard(self) -> dict:
        recent = self.repo.get_recent_ratings(10)
        network = self.repo.get_primary_network()
        social = self.repo.get_social_metrics()
        latest_state = self.database.get_game_state() if hasattr(self.database, "get_game_state") else {"current_year": 1, "current_week": 1}
        year = int(latest_state.get("current_year", 1))
        week = int(latest_state.get("current_week", 1))
        snapshot = self.repo.get_business_snapshot(year, week) or self._recalculate_business_snapshot(year, week)
        return {
            "ratings": recent,
            "network": network,
            "social_platforms": social,
            "business_metrics": snapshot,
            "open_controversies": self.repo.fetch_all(
                """
                SELECT *
                FROM wrestler_social_controversies
                WHERE status = 'open' AND deleted_at IS NULL
                ORDER BY severity_score DESC
                """
            ),
            "streaming_deals": self.repo.fetch_all("SELECT * FROM streaming_deals WHERE deleted_at IS NULL ORDER BY created_at DESC"),
            "content_library_count": self.repo.fetch_one("SELECT COUNT(*) AS total FROM digital_content_library WHERE deleted_at IS NULL")["total"],
            "press_history": self.repo.fetch_all("SELECT * FROM press_conferences WHERE deleted_at IS NULL ORDER BY year DESC, week DESC LIMIT 10"),
        }

    def story_dashboard(self) -> dict:
        feuds = self.repo.list_story_feuds(active_only=False)
        active = [feud for feud in feuds if feud["status"] == "active"]
        return {
            "feuds": feuds,
            "summary": {
                "total": len(feuds),
                "active": len(active),
                "hot_or_better": len([f for f in active if float(f["heat_score"]) >= 51]),
                "nuclear": len([f for f in active if float(f["heat_score"]) >= 86]),
                "declining": len([f for f in active if f.get("trajectory") == "declining"]),
            },
            "recent_actions": self.repo.fetch_all(
                """
                SELECT sa.*, sf.name AS feud_name
                FROM storyline_actions sa
                JOIN story_feuds sf ON sf.id = sa.feud_id
                WHERE sa.deleted_at IS NULL
                ORDER BY sa.year DESC, sa.week DESC, sa.created_at DESC
                LIMIT 25
                """
            ),
        }
