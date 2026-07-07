"""
Legend System - Steps 167-172
Handles retired legend tracking, comeback approaches, match limitations,
legacy protection, physical limitations, and retirement announcements.
"""

import random
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


# ============================================================================
# STEP 167: Retirement Status Enum
# ============================================================================

class RetirementStatus(Enum):
    """
    How "retired" is a retired legend?
    Controls comeback likelihood and negotiation approach.
    """
    ACTIVE = "active"                   # Not retired - on a roster
    SOFT_RETIRED = "soft_retired"       # Probably coming back, just taking a break
    SEMI_RETIRED = "semi_retired"       # Occasional appearances possible
    FULLY_RETIRED = "fully_retired"     # Unlikely to return
    INJURY_RETIRED = "injury_retired"   # Retired due to injury - depends on recovery

    @property
    def comeback_modifier(self) -> float:
        """Multiplier applied to base comeback_likelihood."""
        modifiers = {
            "active": 1.0,
            "soft_retired": 1.4,
            "semi_retired": 1.0,
            "fully_retired": 0.3,
            "injury_retired": 0.5,
        }
        return modifiers.get(self.value, 1.0)

    @property
    def label(self) -> str:
        labels = {
            "active": "Active",
            "soft_retired": "Soft Retired",
            "semi_retired": "Semi-Retired",
            "fully_retired": "Fully Retired",
            "injury_retired": "Injury-Retired",
        }
        return labels.get(self.value, self.value.title())

    @property
    def negotiation_difficulty(self) -> str:
        """How hard is it to approach this legend?"""
        difficulty = {
            "active": "easy",
            "soft_retired": "easy",
            "semi_retired": "moderate",
            "fully_retired": "very_hard",
            "injury_retired": "hard",
        }
        return difficulty.get(self.value, "moderate")


# ============================================================================
# STEP 168: Comeback Approach Methods
# ============================================================================

class ComebackApproach(Enum):
    """Methods for contacting a retired legend."""
    COLD_CALL = "cold_call"                     # Rarely works
    MUTUAL_FRIEND = "mutual_friend"             # Moderate success
    TRIBUTE_EVENT = "tribute_event"             # Good for fully retired
    HALL_OF_FAME = "hall_of_fame"               # Best for legacy-focused legends
    DESPERATION_PITCH = "desperation_pitch"     # Only works when legend sees a need


COMEBACK_APPROACH_MODIFIERS = {
    "cold_call": -20,
    "mutual_friend": +15,
    "tribute_event": +25,
    "hall_of_fame": +35,
    "desperation_pitch": +10,
}


# ============================================================================
# STEP 169-171: Match Limitations & Physical Restrictions
# ============================================================================

@dataclass
class LegendMatchLimitations:
    """
    Step 169: What a returning legend will and won't do in the ring.
    """
    # Schedule limits
    max_appearances_per_year: int = 6          # Step 169
    max_consecutive_weeks: int = 2
    requires_rest_weeks_between: int = 4

    # Physical protection (Step 171)
    no_high_risk_moves: bool = False           # No top-rope dives, ladders, etc.
    no_hard_bumps: bool = False                # Must be protected in falls
    limited_match_length: bool = False         # Matches capped at 15 mins
    max_match_minutes: int = 20

    # Opponent requirements (Step 170: Legacy Protection)
    minimum_opponent_role: str = "Midcard"     # Won't face jobbers
    opponent_must_be_established: bool = True  # 2+ years experience
    refuse_comedy_angles: bool = True
    refuse_embarrassing_losses: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_appearances_per_year": self.max_appearances_per_year,
            "max_consecutive_weeks": self.max_consecutive_weeks,
            "requires_rest_weeks_between": self.requires_rest_weeks_between,
            "no_high_risk_moves": self.no_high_risk_moves,
            "no_hard_bumps": self.no_hard_bumps,
            "limited_match_length": self.limited_match_length,
            "max_match_minutes": self.max_match_minutes,
            "minimum_opponent_role": self.minimum_opponent_role,
            "opponent_must_be_established": self.opponent_must_be_established,
            "refuse_comedy_angles": self.refuse_comedy_angles,
            "refuse_embarrassing_losses": self.refuse_embarrassing_losses,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'LegendMatchLimitations':
        lml = LegendMatchLimitations()
        for k, v in data.items():
            if hasattr(lml, k):
                setattr(lml, k, v)
        return lml

    @staticmethod
    def for_age(age: int, retirement_status: RetirementStatus) -> 'LegendMatchLimitations':
        """Generate appropriate limitations based on age and retirement status."""
        lml = LegendMatchLimitations()

        if age >= 55:
            lml.max_appearances_per_year = 2
            lml.max_match_minutes = 10
            lml.no_high_risk_moves = True
            lml.no_hard_bumps = True
            lml.limited_match_length = True
            lml.requires_rest_weeks_between = 8
        elif age >= 50:
            lml.max_appearances_per_year = 4
            lml.max_match_minutes = 15
            lml.no_high_risk_moves = True
            lml.limited_match_length = True
            lml.requires_rest_weeks_between = 6
        elif age >= 45:
            lml.max_appearances_per_year = 8
            lml.max_match_minutes = 20
            lml.requires_rest_weeks_between = 3

        if retirement_status == RetirementStatus.INJURY_RETIRED:
            lml.no_hard_bumps = True
            lml.no_high_risk_moves = True
            lml.max_match_minutes = min(lml.max_match_minutes, 15)

        return lml


# ============================================================================
# STEP 172: Retirement Announcement (Farewell Tour Tracking)
# ============================================================================

class FarewellTourStatus(Enum):
    NONE = "none"               # No farewell tour planned
    ANNOUNCED = "announced"     # "One last run" announced
    IN_PROGRESS = "in_progress" # Tour underway
    FINAL_MATCH = "final_match" # Final match booked
    COMPLETED = "completed"     # Tour complete, fully retired


@dataclass
class FarewellTour:
    """Tracks a legend's farewell tour if they announce a final run."""
    status: FarewellTourStatus = FarewellTourStatus.NONE
    announced_week: Optional[int] = None
    announced_year: Optional[int] = None
    final_match_opponent: Optional[str] = None
    final_show_name: Optional[str] = None
    ceremony_planned: bool = False
    video_package_ready: bool = False
    total_farewell_matches: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "announced_week": self.announced_week,
            "announced_year": self.announced_year,
            "final_match_opponent": self.final_match_opponent,
            "final_show_name": self.final_show_name,
            "ceremony_planned": self.ceremony_planned,
            "video_package_ready": self.video_package_ready,
            "total_farewell_matches": self.total_farewell_matches,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'FarewellTour':
        ft = FarewellTour()
        ft.status = FarewellTourStatus(data.get("status", "none"))
        ft.announced_week = data.get("announced_week")
        ft.announced_year = data.get("announced_year")
        ft.final_match_opponent = data.get("final_match_opponent")
        ft.final_show_name = data.get("final_show_name")
        ft.ceremony_planned = data.get("ceremony_planned", False)
        ft.video_package_ready = data.get("video_package_ready", False)
        ft.total_farewell_matches = data.get("total_farewell_matches", 0)
        return ft


# ============================================================================
# STEP 167: Core Legend Profile (attached to FreeAgent when is_legend=True)
# ============================================================================

@dataclass
class LegendProfile:
    """
    Full legend profile attached to a free agent who is a retired/semi-retired star.
    Contains all the data needed for Steps 167-172.
    """
    # Step 167: Status tracking
    retirement_status: RetirementStatus = RetirementStatus.SEMI_RETIRED
    comeback_likelihood: int = 50           # 0-100, base chance they'd consider returning
    years_retired: int = 0
    career_peak_popularity: int = 75
    hall_of_fame_inducted: bool = False
    hall_of_fame_year: Optional[int] = None

    # Step 168: Approach history
    contact_attempts: int = 0
    last_contact_year: Optional[int] = None
    last_contact_week: Optional[int] = None
    best_approach_used: Optional[str] = None
    approach_history: List[Dict[str, Any]] = field(default_factory=list)

    # Step 169: Match limitations
    match_limitations: LegendMatchLimitations = field(default_factory=LegendMatchLimitations)

    # Step 170: Legacy demands
    legacy_demands: List[str] = field(default_factory=list)
    # e.g. ["no_job_to_newcomers", "marquee_placement", "meaningful_storyline", "no_comedy"]

    # Step 171: Physical condition
    physical_condition: str = "good"        # "excellent", "good", "limited", "poor"
    ring_rust_weeks: int = 0               # How long since last match
    injury_retirement_detail: Optional[str] = None  # What injury caused retirement

    # Step 172: Farewell tour
    farewell_tour: FarewellTour = field(default_factory=FarewellTour)
    announced_retirement_show: Optional[str] = None

    # Appearances this run (reset each new run)
    appearances_this_run: int = 0

    def calculate_effective_comeback_likelihood(self) -> int:
        """
        Step 167: Calculate actual comeback likelihood factoring in
        retirement status, years retired, and physical condition.
        """
        base = self.comeback_likelihood
        base = int(base * self.retirement_status.comeback_modifier)

        # Years retired penalty
        if self.years_retired >= 5:
            base -= 20
        elif self.years_retired >= 3:
            base -= 10
        elif self.years_retired >= 1:
            base -= 5

        # Physical condition modifier
        condition_mod = {
            "excellent": 10,
            "good": 0,
            "limited": -15,
            "poor": -30,
        }
        base += condition_mod.get(self.physical_condition, 0)

        # Hall of fame bump (they're already celebrated, less to prove)
        if self.hall_of_fame_inducted:
            base -= 5

        # Soft retirement = itching to come back
        if self.retirement_status == RetirementStatus.SOFT_RETIRED:
            base += 15

        return max(0, min(100, base))

    def approach_for_comeback(
        self,
        approach: ComebackApproach,
        current_year: int,
        current_week: int
    ) -> Dict[str, Any]:
        """
        Step 168: Attempt to approach the legend about a comeback.
        Returns result dict with success flag and message.
        """
        # Track attempt
        self.contact_attempts += 1
        self.last_contact_year = current_year
        self.last_contact_week = current_week

        modifier = COMEBACK_APPROACH_MODIFIERS.get(approach.value, 0)
        effective_likelihood = self.calculate_effective_comeback_likelihood()
        adjusted = effective_likelihood + modifier

        # Cold call barely works for fully retired
        if self.retirement_status == RetirementStatus.FULLY_RETIRED and approach == ComebackApproach.COLD_CALL:
            adjusted = min(adjusted, 10)

        roll = random.randint(1, 100)
        success = roll <= max(5, min(95, adjusted))

        result = {
            "approach": approach.value,
            "success": success,
            "roll": roll,
            "threshold": adjusted,
            "year": current_year,
            "week": current_week,
        }

        if success:
            result["message"] = self._success_message(approach)
            self.best_approach_used = approach.value
        else:
            result["message"] = self._failure_message(approach)

        # Store only safe scalar fields — never the full result dict,
        # which would create a circular reference when serialized.
        self.approach_history.append({
            'approach': result.get('approach'),
            'success': result.get('success'),
            'message': result.get('message'),
            'year': result.get('year'),
            'week': result.get('week'),
        })
        return result

    def _success_message(self, approach: ComebackApproach) -> str:
        messages = {
            ComebackApproach.COLD_CALL: "Against all odds, they picked up the phone and are interested!",
            ComebackApproach.MUTUAL_FRIEND: "Your mutual contact has opened the door — they're willing to talk.",
            ComebackApproach.TRIBUTE_EVENT: "The tribute show reminded them how much they miss the business. They're interested.",
            ComebackApproach.HALL_OF_FAME: "The Hall of Fame honor means the world to them. They want one more run to celebrate it properly.",
            ComebackApproach.DESPERATION_PITCH: "They can see you need them and appreciate the honesty. They're considering it.",
        }
        return messages.get(approach, "They're open to discussing a return.")

    def _failure_message(self, approach: ComebackApproach) -> str:
        messages = {
            ComebackApproach.COLD_CALL: "No answer. They're not interested in cold calls from promotions.",
            ComebackApproach.MUTUAL_FRIEND: "Your contact tried, but they politely declined for now.",
            ComebackApproach.TRIBUTE_EVENT: "They enjoyed the tribute but say their body isn't ready.",
            ComebackApproach.HALL_OF_FAME: "They're honoured by the offer but feel the Hall is the right ending to their story.",
            ComebackApproach.DESPERATION_PITCH: "They sympathise but aren't in a position to help right now.",
        }
        return messages.get(approach, "They're not interested at this time.")

    def get_appearance_limitations_summary(self) -> str:
        """Step 169: Human-readable limitations summary."""
        lml = self.match_limitations
        parts = [f"Max {lml.max_appearances_per_year} appearances/year"]
        if lml.limited_match_length:
            parts.append(f"Max {lml.max_match_minutes} min matches")
        if lml.no_high_risk_moves:
            parts.append("No high-risk moves")
        if lml.no_hard_bumps:
            parts.append("Protected style only")
        return " · ".join(parts)

    def get_legacy_demands_display(self) -> List[str]:
        """Step 170: Human-readable legacy demands."""
        demand_labels = {
            "no_job_to_newcomers": "Won't lose to wrestlers under 3 years experience",
            "marquee_placement": "Must be in main event or feature match position",
            "meaningful_storyline": "Requires a proper story arc, not filler",
            "no_comedy": "Refuses comedy or embarrassing segments",
            "no_stretcher_jobs": "Won't participate in injury angles",
            "win_guarantee": "Requires at least one clean win in the run",
        }
        return [demand_labels.get(d, d) for d in self.legacy_demands]

    def announce_farewell_tour(self, year: int, week: int, final_show: Optional[str] = None) -> Dict[str, Any]:
        """Step 172: Trigger farewell tour announcement."""
        self.farewell_tour.status = FarewellTourStatus.ANNOUNCED
        self.farewell_tour.announced_year = year
        self.farewell_tour.announced_week = week
        self.farewell_tour.final_show_name = final_show
        return {
            "announced": True,
            "year": year,
            "week": week,
            "final_show": final_show,
            "message": "Farewell tour announced! The fans will want to say goodbye properly.",
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "retirement_status": self.retirement_status.value,
            "comeback_likelihood": self.comeback_likelihood,
            "effective_comeback_likelihood": self.calculate_effective_comeback_likelihood(),
            "years_retired": self.years_retired,
            "career_peak_popularity": self.career_peak_popularity,
            "hall_of_fame_inducted": self.hall_of_fame_inducted,
            "hall_of_fame_year": self.hall_of_fame_year,
            "contact_attempts": self.contact_attempts,
            "last_contact_year": self.last_contact_year,
            "last_contact_week": self.last_contact_week,
            "best_approach_used": self.best_approach_used,
            "approach_history": self.approach_history,
            "match_limitations": self.match_limitations.to_dict(),
            "legacy_demands": self.legacy_demands,
            "legacy_demands_display": self.get_legacy_demands_display(),
            "physical_condition": self.physical_condition,
            "ring_rust_weeks": self.ring_rust_weeks,
            "injury_retirement_detail": self.injury_retirement_detail,
            "farewell_tour": self.farewell_tour.to_dict(),
            "announced_retirement_show": self.announced_retirement_show,
            "appearances_this_run": self.appearances_this_run,
            "limitations_summary": self.get_appearance_limitations_summary(),
            "negotiation_difficulty": self.retirement_status.negotiation_difficulty,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'LegendProfile':
        lp = LegendProfile()
        lp.retirement_status = RetirementStatus(data.get("retirement_status", "semi_retired"))
        lp.comeback_likelihood = data.get("comeback_likelihood", 50)
        lp.years_retired = data.get("years_retired", 0)
        lp.career_peak_popularity = data.get("career_peak_popularity", 75)
        lp.hall_of_fame_inducted = data.get("hall_of_fame_inducted", False)
        lp.hall_of_fame_year = data.get("hall_of_fame_year")
        lp.contact_attempts = data.get("contact_attempts", 0)
        lp.last_contact_year = data.get("last_contact_year")
        lp.last_contact_week = data.get("last_contact_week")
        lp.best_approach_used = data.get("best_approach_used")
        lp.approach_history = data.get("approach_history", [])
        lp.legacy_demands = data.get("legacy_demands", [])
        lp.physical_condition = data.get("physical_condition", "good")
        lp.ring_rust_weeks = data.get("ring_rust_weeks", 0)
        lp.injury_retirement_detail = data.get("injury_retirement_detail")
        lp.appearances_this_run = data.get("appearances_this_run", 0)
        lp.announced_retirement_show = data.get("announced_retirement_show")

        if "match_limitations" in data:
            lp.match_limitations = LegendMatchLimitations.from_dict(data["match_limitations"])

        if "farewell_tour" in data:
            lp.farewell_tour = FarewellTour.from_dict(data["farewell_tour"])

        return lp

    @staticmethod
    def generate_for_retired_wrestler(
        age: int,
        years_retired: int,
        is_major_superstar: bool,
        popularity: int,
        injury_retired: bool = False
    ) -> 'LegendProfile':
        """
        Step 167: Auto-generate a legend profile for a wrestler entering retirement.
        """
        if injury_retired:
            status = RetirementStatus.INJURY_RETIRED
        elif years_retired == 0:
            status = RetirementStatus.SOFT_RETIRED
        elif years_retired <= 2:
            status = RetirementStatus.SEMI_RETIRED
        else:
            status = RetirementStatus.FULLY_RETIRED

        # Base comeback likelihood
        if is_major_superstar:
            comeback_base = random.randint(40, 70)
        else:
            comeback_base = random.randint(20, 50)

        # Physical condition based on age
        if age >= 55:
            condition = random.choice(["limited", "limited", "poor"])
        elif age >= 50:
            condition = random.choice(["good", "limited", "limited"])
        elif age >= 45:
            condition = random.choice(["excellent", "good", "good", "limited"])
        else:
            condition = random.choice(["excellent", "excellent", "good"])

        # Legacy demands for major superstars
        demands = []
        if is_major_superstar:
            demands.append("marquee_placement")
            demands.append("meaningful_storyline")
        if age >= 50:
            demands.append("no_high_risk_moves")
        if popularity >= 75:
            demands.append("no_comedy")

        # Match limitations
        limitations = LegendMatchLimitations.for_age(age, status)

        lp = LegendProfile(
            retirement_status=status,
            comeback_likelihood=comeback_base,
            years_retired=years_retired,
            career_peak_popularity=popularity,
            physical_condition=condition,
            ring_rust_weeks=years_retired * 52,
            injury_retirement_detail="Undisclosed injury" if injury_retired else None,
            legacy_demands=demands,
            match_limitations=limitations,
        )
        return lp