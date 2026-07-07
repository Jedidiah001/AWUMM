"""
Prospect System - Steps 185-190
Handles fresh prospect discovery, evaluation, developmental contracts,
training investment decisions, competition, and breakthrough moments.
"""

import random
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


# ============================================================================
# STEP 185: Discovery Methods
# ============================================================================

class ProspectDiscoveryMethod(Enum):
    INDIE_SHOW_SCOUTING = "indie_show_scouting"
    TRAINING_SCHOOL_PARTNER = "training_school_partner"
    TRYOUT_CAMP = "tryout_camp"
    VIRAL_SOCIAL_MEDIA = "viral_social_media"
    FAN_RECOMMENDATION = "fan_recommendation"
    REFEREE_NETWORK = "referee_network"
    ROAD_AGENT_REFERRAL = "road_agent_referral"
    INTERNATIONAL_SCOUT = "international_scout"

    @property
    def label(self) -> str:
        labels = {
            "indie_show_scouting": "Indie Show Scouting",
            "training_school_partner": "Training School Partnership",
            "tryout_camp": "Tryout Camp",
            "viral_social_media": "Viral Social Media",
            "fan_recommendation": "Fan Recommendation",
            "referee_network": "Referee Network",
            "road_agent_referral": "Road Agent Referral",
            "international_scout": "International Scout",
        }
        return labels.get(self.value, self.value.replace("_", " ").title())

    @property
    def base_discovery_cost(self) -> int:
        """How much does this discovery method cost?"""
        costs = {
            "indie_show_scouting": 2000,
            "training_school_partner": 5000,
            "tryout_camp": 3000,
            "viral_social_media": 0,
            "fan_recommendation": 0,
            "referee_network": 1000,
            "road_agent_referral": 1500,
            "international_scout": 8000,
        }
        return costs.get(self.value, 1000)


# ============================================================================
# STEP 186: Prospect Evaluation Metrics
# ============================================================================

@dataclass
class ProspectEvaluation:
    """
    Step 186: Raw talent assessment for a prospect.
    Current stats may not reflect ceiling - hidden potential is key.
    """
    # Raw observable scores (0-100)
    athletic_ability: int = 50
    learning_speed: int = 50       # How fast they absorb coaching
    personality_presence: int = 50  # Camera presence, charisma potential
    physical_appearance: int = 50   # Look, size, marketability
    microphone_potential: int = 50  # Future promo ability
    work_ethic: int = 50           # Reliability, attitude

    # Hidden ceiling (player sees a range, not exact)
    true_ceiling: int = 60         # Actual maximum potential (hidden)
    ceiling_range_low: int = 50    # Shown to player: "50-75 ceiling"
    ceiling_range_high: int = 75

    # Evaluation confidence (how reliable are these scores?)
    evaluation_confidence: int = 70  # 0-100, higher = more accurate read

    def overall_raw_score(self) -> int:
        """Current raw talent score."""
        return int((
            self.athletic_ability * 0.25 +
            self.learning_speed * 0.20 +
            self.personality_presence * 0.20 +
            self.physical_appearance * 0.10 +
            self.microphone_potential * 0.15 +
            self.work_ethic * 0.10
        ))

    def ceiling_display(self) -> str:
        """Step 186: Show a range to the player, not the exact ceiling."""
        return f"{self.ceiling_range_low}–{self.ceiling_range_high}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "athletic_ability": self.athletic_ability,
            "learning_speed": self.learning_speed,
            "personality_presence": self.personality_presence,
            "physical_appearance": self.physical_appearance,
            "microphone_potential": self.microphone_potential,
            "work_ethic": self.work_ethic,
            "overall_raw_score": self.overall_raw_score(),
            "ceiling_display": self.ceiling_display(),
            "ceiling_range_low": self.ceiling_range_low,
            "ceiling_range_high": self.ceiling_range_high,
            "evaluation_confidence": self.evaluation_confidence,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ProspectEvaluation':
        pe = ProspectEvaluation()
        for key in ['athletic_ability', 'learning_speed', 'personality_presence',
                    'physical_appearance', 'microphone_potential', 'work_ethic',
                    'true_ceiling', 'ceiling_range_low', 'ceiling_range_high',
                    'evaluation_confidence']:
            if key in data:
                setattr(pe, key, data[key])
        return pe

    @staticmethod
    def generate_random(
        role_ceiling: str = "Midcard",
        scouting_accuracy: int = 70
    ) -> 'ProspectEvaluation':
        """
        Step 186: Generate a random prospect evaluation.
        scouting_accuracy affects how close ceiling_range is to true_ceiling.
        """
        # True ceiling based on role potential
        ceiling_by_role = {
            "Main Event": (75, 100),
            "Upper Midcard": (65, 85),
            "Midcard": (55, 75),
            "Lower Midcard": (45, 65),
            "Jobber": (35, 55),
        }
        ceiling_min, ceiling_max = ceiling_by_role.get(role_ceiling, (50, 75))
        true_ceiling = random.randint(ceiling_min, ceiling_max)

        # Raw scores are significantly below ceiling (they're raw!)
        raw_base = int(true_ceiling * random.uniform(0.45, 0.70))

        def rand_stat(base: int) -> int:
            return max(20, min(80, base + random.randint(-15, 15)))

        pe = ProspectEvaluation(
            athletic_ability=rand_stat(raw_base + 10),
            learning_speed=rand_stat(raw_base),
            personality_presence=rand_stat(raw_base - 5),
            physical_appearance=rand_stat(raw_base + 5),
            microphone_potential=rand_stat(raw_base - 10),
            work_ethic=rand_stat(raw_base + 5),
            true_ceiling=true_ceiling,
            evaluation_confidence=scouting_accuracy,
        )

        # Calculate ceiling range shown to player based on scouting accuracy
        # Better scouting = tighter range
        variance = int((100 - scouting_accuracy) * 0.3)
        pe.ceiling_range_low = max(30, true_ceiling - variance - random.randint(2, 8))
        pe.ceiling_range_high = min(100, true_ceiling + variance + random.randint(2, 8))

        return pe


# ============================================================================
# STEP 187: Developmental Contract Terms
# ============================================================================

@dataclass
class DevelopmentalContract:
    """
    Step 187: Prospects sign restrictive developmental deals.
    Lower pay, longer terms, performance milestones.
    """
    base_salary: int = 1500                 # Much lower than main roster
    contract_length_weeks: int = 104        # 2-year standard dev deal
    relocation_required: bool = True
    training_hours_per_week: int = 20

    # Performance milestones that affect continuation
    milestones: List[str] = field(default_factory=list)
    # e.g. ["reach_midcard_within_1_year", "maintain_70pct_match_quality"]

    # Player's control levels
    creative_control: str = "none"          # Dev talent does as told
    brand_placement: str = "any"            # Can be assigned anywhere
    release_clause_weeks: int = 4           # Short notice period

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_salary": self.base_salary,
            "contract_length_weeks": self.contract_length_weeks,
            "relocation_required": self.relocation_required,
            "training_hours_per_week": self.training_hours_per_week,
            "milestones": self.milestones,
            "creative_control": self.creative_control,
            "brand_placement": self.brand_placement,
            "release_clause_weeks": self.release_clause_weeks,
        }


# ============================================================================
# STEP 188: Training Investment
# ============================================================================

class TrainingInvestmentLevel(Enum):
    NONE = "none"
    BASIC = "basic"
    STANDARD = "standard"
    EXTENSIVE = "extensive"
    VETERAN_MENTORSHIP = "veteran_mentorship"
    OUTSIDE_SUPPLEMENTS = "outside_supplements"

    @property
    def weekly_cost(self) -> int:
        costs = {
            "none": 0,
            "basic": 500,
            "standard": 1500,
            "extensive": 3000,
            "veteran_mentorship": 2500,
            "outside_supplements": 2000,
        }
        return costs.get(self.value, 0)

    @property
    def development_speed_modifier(self) -> float:
        """Multiplier for how fast the prospect grows."""
        speeds = {
            "none": 0.5,
            "basic": 0.75,
            "standard": 1.0,
            "extensive": 1.5,
            "veteran_mentorship": 1.4,
            "outside_supplements": 1.2,
        }
        return speeds.get(self.value, 1.0)

    @property
    def label(self) -> str:
        return self.value.replace("_", " ").title()

    @property
    def description(self) -> str:
        descriptions = {
            "none": "No additional investment. Raw talent develops on its own, slowly.",
            "basic": "Cheap foundational training. Slow but steady development.",
            "standard": "Standard developmental program. Normal growth trajectory.",
            "extensive": "Intensive training regime. Fast development, higher cost.",
            "veteran_mentorship": "Pair with a veteran who coaches them. Faster growth, costs goodwill.",
            "outside_supplements": "Send them to outside training camps. Good speed, moderate cost.",
        }
        return descriptions.get(self.value, "")


# ============================================================================
# STEP 189: Prospect Competition Tracking
# ============================================================================

@dataclass
class ProspectCompetition:
    """
    Step 189: Tracks rival interest in the same prospect pool.
    """
    rival_promotions_scouting: List[str] = field(default_factory=list)
    has_competing_offer: bool = False
    competing_offer_salary: int = 0
    deadline_to_decide_week: Optional[int] = None
    deadline_to_decide_year: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rival_promotions_scouting": self.rival_promotions_scouting,
            "has_competing_offer": self.has_competing_offer,
            "competing_offer_salary": self.competing_offer_salary,
            "deadline_to_decide_week": self.deadline_to_decide_week,
            "deadline_to_decide_year": self.deadline_to_decide_year,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ProspectCompetition':
        pc = ProspectCompetition()
        pc.rival_promotions_scouting = data.get("rival_promotions_scouting", [])
        pc.has_competing_offer = data.get("has_competing_offer", False)
        pc.competing_offer_salary = data.get("competing_offer_salary", 0)
        pc.deadline_to_decide_week = data.get("deadline_to_decide_week")
        pc.deadline_to_decide_year = data.get("deadline_to_decide_year")
        return pc


# ============================================================================
# STEP 190: Breakthrough Moment Detection
# ============================================================================

class BreakthroughStatus(Enum):
    NOT_READY = "not_ready"         # Premature promotion = failure risk
    APPROACHING = "approaching"     # Getting close, one or two more months
    READY = "ready"                 # Perfect timing - organic breakthrough
    OVERDUE = "overdue"             # Too late - frustrated, wants out
    BREAKTHROUGH_HAPPENED = "breakthrough"  # Fully broke through

    @property
    def label(self) -> str:
        labels = {
            "not_ready": "Not Ready",
            "approaching": "Approaching Readiness",
            "ready": "Ready to Break Through",
            "overdue": "Overdue — Frustrated",
            "breakthrough": "Breakthrough Achieved",
        }
        return labels.get(self.value, self.value.title())

    @property
    def promotion_risk(self) -> str:
        risk = {
            "not_ready": "HIGH — Premature promotion likely to damage confidence",
            "approaching": "MODERATE — Could work with strong booking support",
            "ready": "LOW — Natural breakthrough window is now",
            "overdue": "MEDIUM — They need it now or they'll demand out",
            "breakthrough": "NONE — Already on main roster",
        }
        return risk.get(self.value, "Unknown")


@dataclass
class ProspectProfile:
    """
    Full prospect profile for a free agent tagged as is_prospect=True.
    Covers Steps 185-190.
    """
    # Step 185: How they were found
    discovery_method: ProspectDiscoveryMethod = ProspectDiscoveryMethod.INDIE_SHOW_SCOUTING
    discovery_cost: int = 0
    discovery_year: Optional[int] = None
    discovery_week: Optional[int] = None

    # Step 186: Evaluation
    evaluation: ProspectEvaluation = field(default_factory=ProspectEvaluation)

    # Step 187: Contract terms
    developmental_contract: DevelopmentalContract = field(default_factory=DevelopmentalContract)

    # Step 188: Training investment
    training_level: TrainingInvestmentLevel = TrainingInvestmentLevel.STANDARD
    weeks_in_development: int = 0
    total_training_invested: int = 0

    # Assigned mentor (Step 188: Veteran Mentorship)
    mentor_wrestler_id: Optional[str] = None
    mentor_wrestler_name: Optional[str] = None

    # Step 189: Competition
    competition: ProspectCompetition = field(default_factory=ProspectCompetition)
    was_first_to_sign: bool = False  # Did we beat rivals to this prospect?

    # Step 190: Breakthrough tracking
    breakthrough_status: BreakthroughStatus = BreakthroughStatus.NOT_READY
    weeks_until_ready: int = 26         # Estimated weeks until breakthrough window
    breakthrough_week: Optional[int] = None
    breakthrough_year: Optional[int] = None
    promoted_to_main_roster: bool = False
    promotion_timing: Optional[str] = None  # "early", "perfect", "late"
    morale_after_promotion: int = 70

    def calculate_development_progress(self) -> int:
        """
        Step 190: 0-100 progress towards being ready for main roster.
        Based on time in development adjusted for training intensity.
        """
        effective_weeks = int(
            self.weeks_in_development * self.training_level.development_speed_modifier
        )
        # Assume ~52 weeks standard development time
        standard_ready_at = 52
        progress = int((effective_weeks / standard_ready_at) * 100)
        return max(0, min(100, progress))

    def check_breakthrough_status(self, current_year: int, current_week: int) -> BreakthroughStatus:
        """
        Step 190: Assess whether it's the right time to promote this prospect.
        """
        progress = self.calculate_development_progress()

        if self.promoted_to_main_roster:
            return BreakthroughStatus.BREAKTHROUGH_HAPPENED

        if progress < 50:
            self.breakthrough_status = BreakthroughStatus.NOT_READY
        elif progress < 75:
            self.breakthrough_status = BreakthroughStatus.APPROACHING
        elif progress < 110:
            self.breakthrough_status = BreakthroughStatus.READY
        else:
            # They've been ready too long
            self.breakthrough_status = BreakthroughStatus.OVERDUE

        return self.breakthrough_status

    def promote_to_main_roster(
        self,
        current_year: int,
        current_week: int
    ) -> Dict[str, Any]:
        """
        Step 190: Promote prospect to main roster. Calculates timing quality.
        Returns result dict with morale and timing assessment.
        """
        progress = self.calculate_development_progress()

        if progress < 50:
            timing = "early"
            morale_impact = -20
            message = "Premature! They're not ready — expect struggles and confidence issues."
        elif progress < 75:
            timing = "slightly_early"
            morale_impact = -5
            message = "A bit early, but strong booking support can make it work."
        elif progress <= 100:
            timing = "perfect"
            morale_impact = +15
            message = "Perfect timing! They're at their peak readiness for this moment."
        else:
            timing = "late"
            morale_impact = -10
            message = "Overdue. They're relieved to finally be called up, but some frustration lingers."

        self.promoted_to_main_roster = True
        self.promotion_timing = timing
        self.breakthrough_week = current_week
        self.breakthrough_year = current_year
        self.breakthrough_status = BreakthroughStatus.BREAKTHROUGH_HAPPENED
        self.morale_after_promotion = max(30, min(100, 70 + morale_impact))

        return {
            "timing": timing,
            "morale_impact": morale_impact,
            "morale_after": self.morale_after_promotion,
            "message": message,
            "progress_at_promotion": progress,
        }

    def assign_mentor(self, wrestler_id: str, wrestler_name: str) -> Dict[str, Any]:
        """Step 188: Assign a veteran mentor to this prospect."""
        self.mentor_wrestler_id = wrestler_id
        self.mentor_wrestler_name = wrestler_name
        if self.training_level != TrainingInvestmentLevel.VETERAN_MENTORSHIP:
            self.training_level = TrainingInvestmentLevel.VETERAN_MENTORSHIP
        return {
            "mentor_assigned": True,
            "mentor_name": wrestler_name,
            "training_speed": self.training_level.development_speed_modifier,
            "weekly_cost": self.training_level.weekly_cost,
        }

    def get_status_summary(self) -> Dict[str, Any]:
        """Quick summary for the UI."""
        return {
            "discovery_method": self.discovery_method.label,
            "progress": self.calculate_development_progress(),
            "breakthrough_status": self.breakthrough_status.value,
            "breakthrough_label": self.breakthrough_status.label,
            "promotion_risk": self.breakthrough_status.promotion_risk,
            "training_level": self.training_level.label,
            "training_cost_weekly": self.training_level.weekly_cost,
            "weeks_in_development": self.weeks_in_development,
            "ceiling_display": self.evaluation.ceiling_display(),
            "has_mentor": self.mentor_wrestler_id is not None,
            "mentor_name": self.mentor_wrestler_name,
            "has_competing_offer": self.competition.has_competing_offer,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "discovery_method": self.discovery_method.value,
            "discovery_method_label": self.discovery_method.label,
            "discovery_cost": self.discovery_cost,
            "discovery_year": self.discovery_year,
            "discovery_week": self.discovery_week,
            "evaluation": self.evaluation.to_dict(),
            "developmental_contract": self.developmental_contract.to_dict(),
            "training_level": self.training_level.value,
            "training_level_label": self.training_level.label,
            "training_level_description": self.training_level.description,
            "training_level_weekly_cost": self.training_level.weekly_cost,
            "weeks_in_development": self.weeks_in_development,
            "total_training_invested": self.total_training_invested,
            "development_progress": self.calculate_development_progress(),
            "mentor_wrestler_id": self.mentor_wrestler_id,
            "mentor_wrestler_name": self.mentor_wrestler_name,
            "competition": self.competition.to_dict(),
            "was_first_to_sign": self.was_first_to_sign,
            "breakthrough_status": self.breakthrough_status.value,
            "breakthrough_status_label": self.breakthrough_status.label,
            "promotion_risk": self.breakthrough_status.promotion_risk,
            "breakthrough_week": self.breakthrough_week,
            "breakthrough_year": self.breakthrough_year,
            "promoted_to_main_roster": self.promoted_to_main_roster,
            "promotion_timing": self.promotion_timing,
            "morale_after_promotion": self.morale_after_promotion,
            "status_summary": self.get_status_summary(),
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ProspectProfile':
        pp = ProspectProfile()
        pp.discovery_method = ProspectDiscoveryMethod(
            data.get("discovery_method", "indie_show_scouting")
        )
        pp.discovery_cost = data.get("discovery_cost", 0)
        pp.discovery_year = data.get("discovery_year")
        pp.discovery_week = data.get("discovery_week")
        pp.training_level = TrainingInvestmentLevel(
            data.get("training_level", "standard")
        )
        pp.weeks_in_development = data.get("weeks_in_development", 0)
        pp.total_training_invested = data.get("total_training_invested", 0)
        pp.mentor_wrestler_id = data.get("mentor_wrestler_id")
        pp.mentor_wrestler_name = data.get("mentor_wrestler_name")
        pp.was_first_to_sign = data.get("was_first_to_sign", False)
        pp.breakthrough_status = BreakthroughStatus(
            data.get("breakthrough_status", "not_ready")
        )
        pp.breakthrough_week = data.get("breakthrough_week")
        pp.breakthrough_year = data.get("breakthrough_year")
        pp.promoted_to_main_roster = data.get("promoted_to_main_roster", False)
        pp.promotion_timing = data.get("promotion_timing")
        pp.morale_after_promotion = data.get("morale_after_promotion", 70)

        if "evaluation" in data:
            pp.evaluation = ProspectEvaluation.from_dict(data["evaluation"])
        if "developmental_contract" in data:
            dc = data["developmental_contract"]
            pp.developmental_contract = DevelopmentalContract(
                base_salary=dc.get("base_salary", 1500),
                contract_length_weeks=dc.get("contract_length_weeks", 104),
                relocation_required=dc.get("relocation_required", True),
                training_hours_per_week=dc.get("training_hours_per_week", 20),
                milestones=dc.get("milestones", []),
            )
        if "competition" in data:
            pp.competition = ProspectCompetition.from_dict(data["competition"])

        return pp

    @staticmethod
    def generate_new_prospect(
        discovery_method: ProspectDiscoveryMethod,
        current_year: int,
        current_week: int,
        potential_ceiling: str = "Midcard",
        scouting_accuracy: int = 70
    ) -> 'ProspectProfile':
        """
        Step 185-186: Generate a fresh prospect via a discovery method.
        """
        evaluation = ProspectEvaluation.generate_random(potential_ceiling, scouting_accuracy)

        # Add rival competition for standout prospects
        competition = ProspectCompetition()
        if evaluation.true_ceiling >= 75:
            # Hot prospect - rivals likely scouting too
            rivals = ["Dynasty Pro Wrestling", "Global Championship Wrestling",
                      "Apex Wrestling Federation", "Revolution Pro"]
            num_rivals = random.randint(1, 2)
            competition.rival_promotions_scouting = random.sample(rivals, num_rivals)

            # Chance of competing offer already
            if random.random() < 0.35 and evaluation.true_ceiling >= 80:
                competition.has_competing_offer = True
                competition.competing_offer_salary = random.randint(1000, 2500)
                competition.deadline_to_decide_week = current_week + random.randint(2, 6)
                competition.deadline_to_decide_year = current_year

        weeks_until_ready = int(52 / ProspectDiscoveryMethod.INDIE_SHOW_SCOUTING.base_discovery_cost * 2000)
        # Simpler: random based on ceiling
        if evaluation.true_ceiling >= 80:
            weeks_until_ready = random.randint(26, 52)
        elif evaluation.true_ceiling >= 65:
            weeks_until_ready = random.randint(52, 78)
        else:
            weeks_until_ready = random.randint(78, 104)

        pp = ProspectProfile(
            discovery_method=discovery_method,
            discovery_cost=discovery_method.base_discovery_cost,
            discovery_year=current_year,
            discovery_week=current_week,
            evaluation=evaluation,
            competition=competition,
            weeks_until_ready=weeks_until_ready,
        )

        return pp