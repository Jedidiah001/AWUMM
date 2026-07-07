"""
Show Production Engine
Steps 58-72: Comprehensive show production management.

Step 58: Weekly TV Show Management
Step 59: Monthly PPV Event management
Step 60: House Show Tours
Step 61: Supercard Special Events
Step 62: Segment Type Variety
Step 63: Show Pacing Management
Step 64: Time Slot Allocation
Step 65: Run-In & Interference Booking
Step 66: Surprise Debut Booking
Step 67: Return Booking
Step 68: Commercial Break Strategy
Step 69: Opening Segment Priority
Step 70: Main Event Selection
Step 71: Dark Match Booking
Step 72: Show Theme Development
"""

import random
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field

from models.show_config import (
    ShowProductionConfig,
    ShowTheme,
    ShowThemeConfig,
    ShowCategory,
    OpeningSegmentType,
    CommercialBreakStrategy,
    PacingGrade,
    ShowPacingManager,
    BRAND_TIME_SLOTS,
    SHOW_TYPE_DURATIONS,
    TARGET_MATCH_COUNTS,
    SEGMENT_TYPE_CATALOGUE,
    SHOW_THEME_CONFIGS,
)


# ============================================================================
# HOUSE SHOW TOUR PLANNER  (Step 60)
# ============================================================================

@dataclass
class HouseShowSchedule:
    """A planned house show tour across multiple weeks."""
    tour_id: str
    tour_name: str
    brand: str
    start_year: int
    start_week: int
    end_week: int
    venues: List[str]
    scheduled_events: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tour_id": self.tour_id,
            "tour_name": self.tour_name,
            "brand": self.brand,
            "start_year": self.start_year,
            "start_week": self.start_week,
            "end_week": self.end_week,
            "venues": self.venues,
            "event_count": len(self.scheduled_events),
            "scheduled_events": self.scheduled_events,
        }


HOUSE_SHOW_VENUES = {
    "ROC Alpha": [
        "Madison Square Garden (House)", "Barclays Center", "TD Garden",
        "United Center", "Spectrum Center",
    ],
    "ROC Velocity": [
        "Staples Center (House)", "Chase Center", "Talking Stick Arena",
        "Vivint Arena", "Ball Arena",
    ],
    "ROC Vanguard": [
        "BOK Center", "Legacy Arena", "Von Braun Center",
        "Knoxville Civic Coliseum", "James Brown Arena",
    ],
}


class HouseShowTourManager:
    """Step 60: Manages non-televised house show tours."""

    def plan_tour(
        self,
        brand: str,
        start_year: int,
        start_week: int,
        duration_weeks: int = 4,
    ) -> HouseShowSchedule:
        venues = HOUSE_SHOW_VENUES.get(brand, ["Local Arena"])
        tour_id = f"tour_{brand.replace(' ', '_').lower()}_{start_year}w{start_week}"
        tour_name = f"{brand} House Show Tour"

        events = []
        for i in range(duration_weeks):
            week = start_week + i
            if week > 52:
                week -= 52
            venue = venues[i % len(venues)]
            events.append({
                "week": week,
                "venue": venue,
                "show_type": "house_show",
                "expected_attendance": random.randint(3_000, 8_000),
                "ticket_price": 35,
            })

        return HouseShowSchedule(
            tour_id=tour_id,
            tour_name=tour_name,
            brand=brand,
            start_year=start_year,
            start_week=start_week,
            end_week=start_week + duration_weeks - 1,
            venues=[e["venue"] for e in events],
            scheduled_events=events,
        )

    def calculate_tour_revenue(self, schedule: HouseShowSchedule) -> Dict[str, Any]:
        total_attendance = sum(e["expected_attendance"] for e in schedule.scheduled_events)
        avg_ticket = 35
        gross = total_attendance * avg_ticket
        # House shows have lower production cost
        production_cost = len(schedule.scheduled_events) * 15_000
        net = gross - production_cost
        return {
            "total_attendance": total_attendance,
            "gross_revenue": gross,
            "production_cost": production_cost,
            "net_profit": net,
        }


house_show_tour_manager = HouseShowTourManager()


# ============================================================================
# SUPERCARD PLANNER  (Step 61)
# ============================================================================

SUPERCARD_REQUIREMENTS = {
    "Victory Dome": {
        "min_matches": 9,
        "must_have_title_matches": 3,
        "celebrity_appearance_chance": 0.40,
        "must_have_world_title": True,
        "has_hall_of_fame": True,
        "special_intro_video": True,
    },
    "Summer Slamfest": {
        "min_matches": 8,
        "must_have_title_matches": 2,
        "celebrity_appearance_chance": 0.25,
        "must_have_world_title": True,
        "has_hall_of_fame": False,
        "special_intro_video": True,
    },
    "Rumble Royale": {
        "min_matches": 7,
        "must_have_title_matches": 1,
        "celebrity_appearance_chance": 0.10,
        "must_have_world_title": False,
        "has_hall_of_fame": False,
        "special_intro_video": True,
    },
    "Night of Glory": {
        "min_matches": 7,
        "must_have_title_matches": 2,
        "celebrity_appearance_chance": 0.15,
        "must_have_world_title": True,
        "has_hall_of_fame": False,
        "special_intro_video": True,
    },
}

def get_supercard_requirements(show_name: str) -> Dict[str, Any]:
    """Step 61: Get production requirements for a supercard."""
    return SUPERCARD_REQUIREMENTS.get(show_name, {
        "min_matches": 6,
        "must_have_title_matches": 1,
        "celebrity_appearance_chance": 0.0,
        "must_have_world_title": False,
        "has_hall_of_fame": False,
        "special_intro_video": False,
    })


# ============================================================================
# RUN-IN / INTERFERENCE MANAGER  (Step 65)
# ============================================================================

@dataclass
class RunInEvent:
    """A planned or spontaneous run-in during a show."""
    run_in_id: str
    interferer_id: str
    interferer_name: str
    target_match_id: str
    target_wrestler_id: str
    target_wrestler_name: str
    reason: str         # "feud_escalation", "heel_assistance", "face_save"
    effect: str         # "causes_dq", "costs_match", "saves_partner"
    feud_intensity_boost: int = 10
    creates_new_feud: bool = False
    is_planned: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__


class RunInManager:
    """Step 65: Books run-ins and interference angles."""

    # Overuse threshold — too many run-ins diminishes impact
    MAX_RUN_INS_PER_SHOW = {
        "weekly_tv": 1,
        "minor_ppv": 1,
        "major_ppv": 2,
        "supercard": 2,
        "house_show": 0,
    }

    def should_book_run_in(
        self,
        show_type: str,
        current_run_in_count: int,
        active_feuds: List,
        is_ppv: bool,
    ) -> bool:
        max_allowed = self.MAX_RUN_INS_PER_SHOW.get(show_type, 1)
        if current_run_in_count >= max_allowed:
            return False
        hot_feuds = [f for f in active_feuds if hasattr(f, 'intensity') and f.intensity >= 60]
        if not hot_feuds:
            return False
        # 40% base chance for weekly TV, 25% for PPV (saves them for match finishes)
        chance = 0.40 if not is_ppv else 0.25
        return random.random() < chance

    def book_run_in(
        self,
        feud,
        match_id: str,
        all_wrestlers: List,
    ) -> Optional[RunInEvent]:
        """Generate a run-in for a given feud and match."""
        if len(feud.participant_ids) < 2:
            return None

        interferer_id = feud.participant_ids[0]
        target_id = feud.participant_ids[1]
        interferer_name = feud.participant_names[0] if feud.participant_names else "Unknown"
        target_name = feud.participant_names[1] if len(feud.participant_names) > 1 else "Unknown"

        # Determine effect
        effect_choices = [
            ("causes_dq", "costs_match"),
            ("costs_match", "feud_escalation"),
            ("saves_partner", "heel_assistance"),
        ]
        effect, reason = random.choice(effect_choices)

        return RunInEvent(
            run_in_id=f"runin_{match_id}_{interferer_id}",
            interferer_id=interferer_id,
            interferer_name=interferer_name,
            target_match_id=match_id,
            target_wrestler_id=target_id,
            target_wrestler_name=target_name,
            reason=reason,
            effect=effect,
            feud_intensity_boost=random.randint(8, 15),
            creates_new_feud=False,
            is_planned=True,
        )


run_in_manager = RunInManager()


# ============================================================================
# SURPRISE DEBUT MANAGER  (Step 66)
# ============================================================================

@dataclass
class DebutAngle:
    debut_id: str
    wrestler_id: str
    wrestler_name: str
    debut_type: str       # "cold_debut", "vignette_debut", "attack_debut"
    target_id: Optional[str]
    target_name: Optional[str]
    momentum_boost: int
    popularity_boost: int
    creates_feud: bool
    crowd_reaction: str    # "massive_pop", "mixed", "heat"

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__


class SurpriseDebutManager:
    """Step 66: Plans and executes surprise debut angles."""

    def plan_debut(
        self,
        new_wrestler,
        show_type: str,
        existing_feuds: List,
        active_roster: List,
    ) -> DebutAngle:
        """Generate a debut angle for a new wrestler."""

        # Choose debut type based on alignment
        alignment = getattr(new_wrestler, 'alignment', 'Face')
        if alignment == 'Heel':
            debut_type = random.choice(["attack_debut", "cold_debut"])
            crowd_reaction = "heat"
            creates_feud = debut_type == "attack_debut"
        else:
            debut_type = random.choice(["cold_debut", "vignette_debut"])
            crowd_reaction = "massive_pop"
            creates_feud = False

        # Target — find someone to feud with on debut
        target = None
        if creates_feud and active_roster:
            candidates = [
                w for w in active_roster
                if w.alignment != alignment and w.role in ["Main Event", "Upper Midcard"]
            ]
            if candidates:
                target = max(candidates, key=lambda w: w.popularity)

        pop_boost = random.randint(15, 25)
        mom_boost = random.randint(20, 35)

        # PPV debut gets bigger boost
        if show_type in ("major_ppv", "supercard"):
            pop_boost += 10
            mom_boost += 15

        return DebutAngle(
            debut_id=f"debut_{new_wrestler.id}",
            wrestler_id=new_wrestler.id,
            wrestler_name=new_wrestler.name,
            debut_type=debut_type,
            target_id=target.id if target else None,
            target_name=target.name if target else None,
            momentum_boost=mom_boost,
            popularity_boost=pop_boost,
            creates_feud=creates_feud,
            crowd_reaction=crowd_reaction,
        )

    def should_debut_on_show(self, show_type: str, is_ppv: bool) -> bool:
        """Probability that a debut happens on this show."""
        if show_type == "house_show":
            return False
        chances = {
            "weekly_tv": 0.08,
            "minor_ppv": 0.20,
            "major_ppv": 0.35,
            "supercard": 0.50,
        }
        return random.random() < chances.get(show_type, 0.10)


surprise_debut_manager = SurpriseDebutManager()


# ============================================================================
# RETURN BOOKING MANAGER  (Step 67)
# ============================================================================

@dataclass
class ReturnAngle:
    return_id: str
    wrestler_id: str
    wrestler_name: str
    is_surprise: bool          # True = unannounced
    is_from_injury: bool
    is_from_retirement: bool
    absence_weeks: int
    return_type: str           # "saves_ally", "attacks_enemy", "championship_challenge"
    target_id: Optional[str]
    target_name: Optional[str]
    momentum_boost: int
    popularity_boost: int
    crowd_reaction: str

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__


class ReturnBookingManager:
    """Step 67: Plans return angles for injured/absent wrestlers."""

    def plan_return(
        self,
        returning_wrestler,
        absence_weeks: int,
        is_surprise: bool,
        active_roster: List,
        active_feuds: List,
        show_type: str,
    ) -> ReturnAngle:
        alignment = getattr(returning_wrestler, 'alignment', 'Face')

        # Determine return type
        if alignment == "Heel":
            return_type = random.choice(["attacks_enemy", "championship_challenge"])
            crowd_reaction = "heat"
        else:
            return_type = random.choice(["saves_ally", "championship_challenge"])
            crowd_reaction = "massive_pop" if absence_weeks > 12 else "pop"

        # Find target
        target = None
        if return_type in ("attacks_enemy", "saves_ally") and active_roster:
            if return_type == "attacks_enemy":
                candidates = [w for w in active_roster if w.alignment != alignment]
            else:
                candidates = [w for w in active_roster if w.alignment == alignment]
            if candidates:
                target = max(candidates, key=lambda w: w.popularity)

        # Boost scales with absence
        absence_multiplier = min(3.0, 1.0 + absence_weeks / 12)
        mom_boost = int(random.randint(15, 25) * absence_multiplier)
        pop_boost = int(random.randint(10, 20) * absence_multiplier)

        # Surprise returns get extra pop
        if is_surprise:
            mom_boost += 15
            pop_boost += 10
            crowd_reaction = "massive_pop" if alignment == "Face" else "massive_heat"

        return ReturnAngle(
            return_id=f"return_{returning_wrestler.id}",
            wrestler_id=returning_wrestler.id,
            wrestler_name=returning_wrestler.name,
            is_surprise=is_surprise,
            is_from_injury=getattr(returning_wrestler, 'is_injured', False),
            is_from_retirement=getattr(returning_wrestler, 'is_retired', False),
            absence_weeks=absence_weeks,
            return_type=return_type,
            target_id=target.id if target else None,
            target_name=target.name if target else None,
            momentum_boost=mom_boost,
            popularity_boost=pop_boost,
            crowd_reaction=crowd_reaction,
        )

    def find_return_candidates(
        self,
        all_wrestlers: List,
        show_name: str,
        is_major_ppv: bool,
    ) -> List:
        """Find wrestlers eligible for a surprise return."""
        candidates = []
        for w in all_wrestlers:
            # Must be injured or retired
            if getattr(w, 'is_retired', False) and getattr(w, 'is_major_superstar', False) and w.age < 52:
                if is_major_ppv:
                    candidates.append(w)
            elif getattr(w, 'is_injured', False):
                injury = getattr(w, 'injury', None)
                if injury and getattr(injury, 'weeks_remaining', 0) == 0:
                    candidates.append(w)
        return candidates


return_booking_manager = ReturnBookingManager()


# ============================================================================
# DARK MATCH MANAGER  (Step 71)
# ============================================================================

@dataclass
class DarkMatch:
    dark_match_id: str
    match_type: str         # "pre_show" or "post_show"
    side_a_ids: List[str]
    side_a_names: List[str]
    side_b_ids: List[str]
    side_b_names: List[str]
    purpose: str            # "talent_development", "crowd_warmup", "crowd_sendoff"
    duration_minutes: int = 8
    is_televised: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dark_match_id": self.dark_match_id,
            "match_type": self.match_type,
            "side_a": self.side_a_names,
            "side_b": self.side_b_names,
            "purpose": self.purpose,
            "duration_minutes": self.duration_minutes,
            "is_televised": self.is_televised,
        }


class DarkMatchManager:
    """Step 71: Books pre-show and post-show dark matches."""

    def book_dark_matches(
        self,
        available_wrestlers: List,
        show_type: str,
        booked_wrestler_ids: set,
        year: int,
        week: int,
        count: int = 1,
    ) -> List[DarkMatch]:
        dark_matches = []

        # Only for non-televised or house shows
        unbooked = [
            w for w in available_wrestlers
            if w.id not in booked_wrestler_ids
            and w.role in ["Lower Midcard", "Jobber", "Midcard"]
            and w.can_compete
            and w.fatigue < 70
        ]

        # Need at least 2 wrestlers
        if len(unbooked) < 2:
            return []

        for i in range(count):
            if len(unbooked) < 2:
                break

            match_type = "pre_show" if i == 0 else "post_show"
            purpose = "crowd_warmup" if match_type == "pre_show" else "talent_development"

            # Pick two wrestlers (prefer lower card)
            side_a_wrestler = unbooked.pop(random.randint(0, len(unbooked) - 1))
            side_b_wrestler = unbooked.pop(random.randint(0, len(unbooked) - 1))

            dark_match = DarkMatch(
                dark_match_id=f"dark_{year}w{week}_{i}",
                match_type=match_type,
                side_a_ids=[side_a_wrestler.id],
                side_a_names=[side_a_wrestler.name],
                side_b_ids=[side_b_wrestler.id],
                side_b_names=[side_b_wrestler.name],
                purpose=purpose,
                duration_minutes=random.randint(6, 10),
                is_televised=False,
            )
            dark_matches.append(dark_match)

        return dark_matches


dark_match_manager = DarkMatchManager()


# ============================================================================
# OPENING SEGMENT SELECTOR  (Step 69)
# ============================================================================

class OpeningSegmentSelector:
    """
    Step 69: Determines the best opening segment type for a show.
    The opener sets the tone — weak opens cost ratings.
    """

    OPENING_ENERGY_IMPACT = {
        OpeningSegmentType.HOT_MATCH: +15,
        OpeningSegmentType.PROMO_IN_RING: +8,
        OpeningSegmentType.AUTHORITY_OPENS: +3,
        OpeningSegmentType.COLD_OPEN_VIDEO: +5,
        OpeningSegmentType.DARK_RETURN: +20,
        OpeningSegmentType.CHAMPIONSHIP_ANNOUNCEMENT: +10,
    }

    def select_opening(
        self,
        show_type: str,
        is_ppv: bool,
        active_feuds: List,
        week: int,
        has_returning_star: bool = False,
        has_title_vacancy: bool = False,
    ) -> Tuple[OpeningSegmentType, str]:
        """
        Returns the recommended opening type and a description of why.
        """
        if has_returning_star:
            return (
                OpeningSegmentType.DARK_RETURN,
                "Surprise return opens the show for maximum impact.",
            )

        if has_title_vacancy and is_ppv:
            return (
                OpeningSegmentType.CHAMPIONSHIP_ANNOUNCEMENT,
                "Championship vacancy announcement sets major stakes.",
            )

        if is_ppv:
            return (
                OpeningSegmentType.COLD_OPEN_VIDEO,
                "PPV cold open video package builds anticipation.",
            )

        hot_feuds = [f for f in active_feuds if hasattr(f, 'intensity') and f.intensity >= 70]
        if hot_feuds:
            if show_type == "weekly_tv" and week % 2 == 0:
                return (
                    OpeningSegmentType.PROMO_IN_RING,
                    "Hot feud promo opens — feud intensity is boiling.",
                )
            return (
                OpeningSegmentType.HOT_MATCH,
                "Opening with a hot match from the hottest feud.",
            )

        # Premiere weeks
        if week in (1, 26):
            return (
                OpeningSegmentType.AUTHORITY_OPENS,
                "Season/mid-season premiere — authority sets the agenda.",
            )

        return (
            OpeningSegmentType.HOT_MATCH,
            "Standard hot-match opener to energise the crowd.",
        )

    def get_energy_impact(self, opening_type: OpeningSegmentType) -> int:
        return self.OPENING_ENERGY_IMPACT.get(opening_type, 5)


opening_segment_selector = OpeningSegmentSelector()


# ============================================================================
# MAIN EVENT SELECTOR  (Step 70)
# ============================================================================

class MainEventSelector:
    """
    Step 70: Selects the optimal main event for a show.
    Main events must send crowds home happy.
    """

    def select_main_event_criteria(
        self,
        show_type: str,
        is_ppv: bool,
        tier: str,
        active_feuds: List,
        brand_titles: List,
        show_name: str,
    ) -> Dict[str, Any]:
        """
        Returns a dict of criteria the AI Director should prioritise
        when booking the main event.
        """
        criteria = {
            "must_be_title_match": False,
            "preferred_feud_intensity_min": 50,
            "preferred_roles": ["Main Event"],
            "prefer_clean_finish": True,
            "allow_non_finish": False,
            "importance_level": "high_drama",
            "reason": "",
        }

        if show_name == "Victory Dome":
            criteria.update({
                "must_be_title_match": True,
                "prefer_world_title": True,
                "prefer_clean_finish": True,
                "reason": "Victory Dome: World Championship must main event.",
            })
        elif show_name == "Rumble Royale":
            criteria.update({
                "must_be_battle_royal": True,
                "must_be_title_match": False,
                "reason": "Rumble Royale: Battle Royal is the main event.",
            })
        elif show_name in ("Summer Slamfest", "Night of Glory"):
            criteria.update({
                "must_be_title_match": True,
                "preferred_feud_intensity_min": 70,
                "reason": f"{show_name}: Major PPV requires hottest feud as main event.",
            })
        elif is_ppv:
            criteria.update({
                "must_be_title_match": True,
                "reason": "PPV main event must involve a championship.",
            })
        else:
            # Weekly TV — most intense feud OR top title
            hot_feuds = sorted(
                [f for f in active_feuds if hasattr(f, 'intensity') and f.intensity >= 60],
                key=lambda f: f.intensity,
                reverse=True,
            )
            if hot_feuds:
                criteria.update({
                    "preferred_feud_id": hot_feuds[0].id,
                    "reason": f"Weekly TV: Hot feud ({hot_feuds[0].intensity} intensity) headlines.",
                })
            else:
                criteria.update({
                    "must_be_title_match": True,
                    "reason": "Weekly TV: No hot feud — title match main event.",
                })

        return criteria

    def evaluate_main_event_quality(self, match_result) -> Dict[str, Any]:
        """
        Step 70: After simulation, evaluate if the main event succeeded.
        A poor main event damages overall show perception.
        """
        rating = getattr(match_result, 'star_rating', 0.0)

        if rating >= 4.0:
            verdict = "Crowd sent home happy"
            show_perception_impact = +10
        elif rating >= 3.0:
            verdict = "Solid main event — crowd satisfied"
            show_perception_impact = +3
        elif rating >= 2.0:
            verdict = "Disappointing main event — mixed reaction"
            show_perception_impact = -5
        else:
            verdict = "Main event failed — crowd deflated"
            show_perception_impact = -15

        return {
            "rating": rating,
            "verdict": verdict,
            "show_perception_impact": show_perception_impact,
        }


main_event_selector = MainEventSelector()


# ============================================================================
# SHOW THEME MANAGER  (Step 72)
# ============================================================================

class ShowThemeManager:
    """
    Step 72: Assigns and applies show themes.
    Themes modify attendance, revenue, match quality, and required segments.
    """

    # Weeks at which automatic themed shows are triggered
    AUTO_THEME_TRIGGERS = {
        1: ShowTheme.SEASON_PREMIERE,
        26: ShowTheme.SEASON_PREMIERE,     # Mid-year premiere
        52: ShowTheme.SEASON_FINALE,
    }

    # PPV name → theme override
    PPV_THEMES = {
        "Victory Dome": ShowTheme.CHAMPIONSHIP_GALA,
        "Night of Glory": ShowTheme.LEGENDS_NIGHT,
        "Rumble Royale": ShowTheme.STANDARD,
        "Summer Slamfest": ShowTheme.GRUDGE_NIGHT,
        "Autumn Annihilation": ShowTheme.GRUDGE_NIGHT,
        "Champions' Ascent": ShowTheme.CHAMPIONSHIP_GALA,
    }

    def determine_show_theme(
        self,
        week: int,
        year: int,
        show_name: str,
        is_ppv: bool,
        brand: str,
        force_theme: Optional[ShowTheme] = None,
    ) -> ShowTheme:
        if force_theme:
            return force_theme

        # PPV themes
        if is_ppv and show_name in self.PPV_THEMES:
            return self.PPV_THEMES[show_name]

        # Auto weekly triggers
        if week in self.AUTO_THEME_TRIGGERS:
            return self.AUTO_THEME_TRIGGERS[week]

        # Anniversary shows (year milestones)
        if week == 1 and year % 5 == 0:
            return ShowTheme.ANNIVERSARY

        return ShowTheme.STANDARD

    def apply_theme_to_production(
        self,
        production_config: ShowProductionConfig,
        theme: ShowTheme,
    ) -> ShowProductionConfig:
        """Apply the chosen theme's modifications to the production config."""
        production_config.show_theme = theme
        cfg = SHOW_THEME_CONFIGS.get(theme, SHOW_THEME_CONFIGS[ShowTheme.STANDARD])

        # Themes may require specific opening segments
        if theme == ShowTheme.LEGENDS_NIGHT:
            production_config.has_surprise_return = True
            production_config.opening_segment_type = OpeningSegmentType.CHAMPIONSHIP_ANNOUNCEMENT
        elif theme == ShowTheme.ANNIVERSARY:
            production_config.has_surprise_return = True
        elif theme == ShowTheme.SEASON_PREMIERE:
            production_config.has_surprise_debut = True
        elif theme == ShowTheme.GRUDGE_NIGHT:
            production_config.has_run_ins = True
            production_config.run_in_count = 1

        return production_config

    def get_theme_description(self, theme: ShowTheme) -> str:
        cfg = SHOW_THEME_CONFIGS.get(theme)
        return cfg.description if cfg else "Standard show."

    def get_all_themes(self) -> List[Dict[str, Any]]:
        return [
            {
                "value": t.value,
                "display_name": cfg.display_name,
                "description": cfg.description,
                "bonus_match_quality": cfg.bonus_match_quality,
                "bonus_attendance_pct": cfg.bonus_attendance_pct,
                "bonus_revenue_pct": cfg.bonus_revenue_pct,
                "required_segments": cfg.required_segment_types,
            }
            for t, cfg in SHOW_THEME_CONFIGS.items()
        ]


show_theme_manager = ShowThemeManager()


# ============================================================================
# MASTER SHOW PRODUCTION MANAGER  (Steps 58-72 orchestrator)
# ============================================================================

class ShowProductionManager:
    """
    Master orchestrator for all show production features (Steps 58-72).
    Called before AI Director generates a card, providing enriched
    production context that guides booking decisions.
    """

    def build_production_plan(
        self,
        scheduled_show,
        universe_state,
        force_theme: Optional[ShowTheme] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point: Build a complete production plan for a show.

        Returns a production_plan dict that the booking route and AI Director
        can use to shape the card.
        """
        show_type = scheduled_show.show_type
        brand = scheduled_show.brand
        is_ppv = scheduled_show.is_ppv
        tier = scheduled_show.tier
        week = scheduled_show.week
        year = scheduled_show.year
        show_name = scheduled_show.name

        print(f"\n🎬 SHOW PRODUCTION PLAN: {show_name}")
        print(f"   Type: {show_type} | Brand: {brand} | Week {week}")

        # ── 1. Build base production config ──────────────────────────────
        config = ShowProductionConfig.from_scheduled_show(scheduled_show)

        # ── 2. Determine theme (Step 72) ──────────────────────────────────
        theme = show_theme_manager.determine_show_theme(
            week=week, year=year, show_name=show_name,
            is_ppv=is_ppv, brand=brand, force_theme=force_theme,
        )
        config = show_theme_manager.apply_theme_to_production(config, theme)
        theme_cfg = config.get_theme_config()
        print(f"   Theme: {theme_cfg.display_name}")

        # ── 3. Time slot & runtime planning (Steps 58/64) ────────────────
        time_slot = BRAND_TIME_SLOTS.get(brand)
        total_minutes = SHOW_TYPE_DURATIONS.get(show_type, 120)
        target = TARGET_MATCH_COUNTS.get(show_type, {"min": 4, "target": 5, "max": 6})
        print(f"   Runtime: {total_minutes} min | Target: {target['target']} matches")

        # ── 4. Opening segment (Step 69) ─────────────────────────────────
        active_feuds = []
        if universe_state:
            try:
                active_feuds = universe_state.feud_manager.get_active_feuds()
                if brand != "Cross-Brand":
                    active_feuds = [
                        f for f in active_feuds
                        if any(
                            universe_state.get_wrestler_by_id(pid) and
                            universe_state.get_wrestler_by_id(pid).primary_brand == brand
                            for pid in f.participant_ids
                        )
                    ]
            except Exception:
                pass

        has_returning = config.has_surprise_return
        has_vacancy = False
        if universe_state:
            try:
                has_vacancy = any(
                    c.is_vacant
                    for c in universe_state.championships
                    if c.assigned_brand == brand or c.assigned_brand == "Cross-Brand"
                )
            except Exception:
                pass

        opening_type, opening_reason = opening_segment_selector.select_opening(
            show_type=show_type,
            is_ppv=is_ppv,
            active_feuds=active_feuds,
            week=week,
            has_returning_star=has_returning,
            has_title_vacancy=has_vacancy,
        )
        config.opening_segment_type = opening_type
        opening_energy = opening_segment_selector.get_energy_impact(opening_type)
        print(f"   Opening: {opening_type.value} (+{opening_energy} energy) — {opening_reason}")

        # ── 5. Main event criteria (Step 70) ─────────────────────────────
        brand_titles = []
        if universe_state:
            try:
                brand_titles = [
                    c for c in universe_state.championships
                    if c.assigned_brand == brand or c.assigned_brand == "Cross-Brand"
                ]
            except Exception:
                pass

        main_event_criteria = main_event_selector.select_main_event_criteria(
            show_type=show_type,
            is_ppv=is_ppv,
            tier=tier,
            active_feuds=active_feuds,
            brand_titles=brand_titles,
            show_name=show_name,
        )
        print(f"   Main Event: {main_event_criteria['reason']}")

        # ── 6. Run-in planning (Step 65) ─────────────────────────────────
        run_in_planned = None
        if run_in_manager.should_book_run_in(
            show_type=show_type,
            current_run_in_count=0,
            active_feuds=active_feuds,
            is_ppv=is_ppv,
        ):
            hot_feuds = sorted(
                [f for f in active_feuds if hasattr(f, 'intensity') and f.intensity >= 60],
                key=lambda f: f.intensity, reverse=True,
            )
            if hot_feuds:
                run_in_planned = run_in_manager.book_run_in(
                    feud=hot_feuds[0],
                    match_id="main_event",
                    all_wrestlers=[],
                )
                config.has_run_ins = True
                config.run_in_count = 1
                print(f"   Run-In: {run_in_planned.interferer_name} interferes ({run_in_planned.reason})")

        # ── 7. Dark matches (Step 71) ─────────────────────────────────────
        dark_matches = []
        if config.has_dark_matches and universe_state:
            try:
                available = universe_state.get_wrestlers_by_brand(brand) if brand != "Cross-Brand" else universe_state.get_active_wrestlers()
                dark_matches = dark_match_manager.book_dark_matches(
                    available_wrestlers=available,
                    show_type=show_type,
                    booked_wrestler_ids=set(),
                    year=year,
                    week=week,
                    count=config.dark_match_count,
                )
                if dark_matches:
                    print(f"   Dark Matches: {len(dark_matches)} booked")
            except Exception:
                pass

        # ── 8. Supercard requirements (Step 61) ──────────────────────────
        supercard_reqs = None
        if is_ppv and tier == "major":
            supercard_reqs = get_supercard_requirements(show_name)
            print(f"   Supercard: min {supercard_reqs['min_matches']} matches, {supercard_reqs['must_have_title_matches']} title matches")

        # ── 9. PPV-specific (Step 59) ─────────────────────────────────────
        ppv_buildup_score = 0
        if is_ppv and universe_state:
            # Score based on how well weekly shows built up the PPV
            # (intensity of feuds, number of rematches, title defenses)
            try:
                ppv_buildup_score = min(100, sum(
                    f.intensity for f in active_feuds
                    if hasattr(f, 'intensity')
                ) // max(1, len(active_feuds)))
            except Exception:
                ppv_buildup_score = 50

        # ── 10. House show specifics (Step 60) ────────────────────────────
        house_show_info = None
        if show_type == "house_show":
            venue_list = HOUSE_SHOW_VENUES.get(brand, ["Local Arena"])
            house_show_info = {
                "venue": random.choice(venue_list),
                "expected_attendance": random.randint(3_000, 8_000),
                "ticket_price": 35,
                "no_title_changes": True,
                "no_major_angles": True,
            }

        # ── 11. Assemble production plan ─────────────────────────────────
        production_plan = {
            "show_type": show_type,
            "brand": brand,
            "show_name": show_name,
            "is_ppv": is_ppv,
            "tier": tier,
            "week": week,
            "year": year,

            # Theme (Step 72)
            "theme": theme.value,
            "theme_display_name": theme_cfg.display_name,
            "theme_description": theme_cfg.description,
            "theme_bonus_match_quality": theme_cfg.bonus_match_quality,
            "theme_bonus_attendance_pct": theme_cfg.bonus_attendance_pct,
            "theme_bonus_revenue_pct": theme_cfg.bonus_revenue_pct,
            "theme_required_segments": theme_cfg.required_segment_types,
            "theme_preferred_stipulations": theme_cfg.preferred_match_stipulations,
            "theme_event_prefix": theme_cfg.extra_event_log_prefix,

            # Time / pacing (Steps 58/63/64)
            "total_runtime_minutes": total_minutes,
            "target_matches": target["target"],
            "min_matches": target["min"],
            "max_matches": target["max"],
            "time_slot": time_slot.to_dict() if time_slot else None,

            # Commercial breaks (Step 68)
            "commercial_break_strategy": CommercialBreakStrategy.MINIMAL.value if is_ppv else CommercialBreakStrategy.STANDARD.value,
            "commercial_breaks_count": 3 if is_ppv else 8,

            # Opening segment (Step 69)
            "opening_segment_type": opening_type.value,
            "opening_segment_reason": opening_reason,
            "opening_energy_impact": opening_energy,

            # Main event (Step 70)
            "main_event_criteria": main_event_criteria,

            # Run-ins (Step 65)
            "run_in_planned": run_in_planned.to_dict() if run_in_planned else None,

            # Debuts / returns (Steps 66/67)
            "has_surprise_debut": config.has_surprise_debut,
            "has_surprise_return": config.has_surprise_return,

            # Dark matches (Step 71)
            "dark_matches": [d.to_dict() for d in dark_matches],

            # PPV (Step 59)
            "ppv_buildup_score": ppv_buildup_score,

            # Supercard (Step 61)
            "supercard_requirements": supercard_reqs,

            # House show (Step 60)
            "house_show_info": house_show_info,
        }

        print(f"✅ Production plan ready for {show_name}\n")
        return production_plan


show_production_manager = ShowProductionManager()