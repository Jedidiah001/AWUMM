"""
Free Agent Model
Represents an unsigned wrestler in the free agent pool with market dynamics.
Steps 113-223: Complete Free Agent System

STEP 116 UPDATE: Enhanced market value calculation integration
STEP 117 UPDATE: Mood system now imported from free_agent_moods.py
STEP 124 UPDATE: Exclusive negotiating window methods
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime, timedelta
import random
import json

# STEP 117: Import mood from separate module
from models.free_agent_moods import FreeAgentMood


class FreeAgentSource(Enum):
    """How the wrestler became a free agent"""
    RELEASED = "released"                    # Released from contract
    CONTRACT_EXPIRED = "contract_expired"    # Contract ran out
    RETIRED_COMEBACK = "retired_comeback"    # Legend returning
    INTERNATIONAL = "international"          # International talent
    PROSPECT = "prospect"                    # Fresh from training
    CONTROVERSY = "controversy"              # Released due to issues
    MUTUAL_AGREEMENT = "mutual_agreement"    # Amicable departure


class FreeAgentVisibility(Enum):
    """Discovery tier for free agents (Step 115)"""
    HEADLINE_NEWS = 1      # Major stars everyone knows
    INDUSTRY_BUZZ = 2      # Known within wrestling circles
    HIDDEN_GEM = 3         # Requires scouting to discover
    DEEP_CUT = 4           # Only through exceptional scouting


class AgentType(Enum):
    """Type of representation (Step 118)"""
    NONE = "none"                 # Negotiates directly
    STANDARD = "standard"         # Normal agent
    POWER_AGENT = "power_agent"   # High-profile agent with leverage
    PACKAGE_DEALER = "package_dealer"  # Represents multiple wrestlers


@dataclass
class AgentInfo:
    """Agent/Representative information"""
    agent_type: AgentType = AgentType.NONE
    agent_name: Optional[str] = None
    commission_rate: float = 0.0  # Percentage added to salary demands
    other_clients: List[str] = field(default_factory=list)  # Other wrestler IDs
    negotiation_difficulty: int = 0  # 0-100, higher = harder to deal with
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'agent_type': self.agent_type.value,
            'agent_name': self.agent_name,
            'commission_rate': self.commission_rate,
            'other_clients': self.other_clients,
            'negotiation_difficulty': self.negotiation_difficulty
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'AgentInfo':
        return AgentInfo(
            agent_type=AgentType(data.get('agent_type', 'none')),
            agent_name=data.get('agent_name'),
            commission_rate=data.get('commission_rate', 0.0),
            other_clients=data.get('other_clients', []),
            negotiation_difficulty=data.get('negotiation_difficulty', 0)
        )


@dataclass
class AgentBehavior:
    """STEP 118: Agent negotiation behavior patterns"""
    stubbornness: int = 50  # 0-100, how much they resist concessions
    greed: int = 50  # 0-100, how much they inflate demands
    patience: int = 50  # 0-100, how long they'll negotiate
    package_priority: bool = False  # Pushes for package deals
    publicity_seeking: bool = False  # Leaks negotiations to media
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'stubbornness': self.stubbornness,
            'greed': self.greed,
            'patience': self.patience,
            'package_priority': self.package_priority,
            'publicity_seeking': self.publicity_seeking
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'AgentBehavior':
        return AgentBehavior(
            stubbornness=data.get('stubbornness', 50),
            greed=data.get('greed', 50),
            patience=data.get('patience', 50),
            package_priority=data.get('package_priority', False),
            publicity_seeking=data.get('publicity_seeking', False)
        )


# STEP 118: Agent Name Generator
AGENT_FIRST_NAMES = [
    "Barry", "Richard", "David", "Michael", "Steven", "Paul",
    "Daniel", "Robert", "Jason", "Mark", "Tony", "Vincent",
    "Andrew", "Jonathan", "Samuel", "Nicholas", "Ethan", "Brian",
    "Chinedu", "Emeka", "Ifeanyi", "Nnamdi", "Chukwuemeka",
    "Obinna", "Uche", "Ibrahim", "Somto", "Chibuzo",
    "Onyekachi", "Ikenna"
]

AGENT_LAST_NAMES = [
    "Goldman", "Silver", "Diamond", "Sterling", "Powers", "Knight",
    "Russo", "Cohen", "Shapiro", "Brooks", "Mitchell", "Hayes",
    "Carter", "Reynolds", "Walker", "Stone", "Marshall", "Griffin",
    "Okafor", "Okoye", "Nwankwo", "Nnamdi", "Eze", "Onyekachi",
    "Chukwu", "Obi", "Uche", "Ike", "Maduka", "Anyanwu"
]


def generate_agent_name() -> str:
    """Generate a random agent name"""
    first = random.choice(AGENT_FIRST_NAMES)
    last = random.choice(AGENT_LAST_NAMES)
    return f"{first} {last}"


def assign_agent_to_free_agent(
    free_agent,
    force_type: Optional[AgentType] = None
) -> AgentInfo:
    """Assign an agent to a free agent based on their profile."""
    if force_type:
        agent_type = force_type
    else:
        if free_agent.is_legend:
            agent_chance = 0.90
            default_type = AgentType.POWER_AGENT
        elif free_agent.is_major_superstar:
            agent_chance = 0.80
            default_type = AgentType.POWER_AGENT
        elif free_agent.popularity >= 70:
            agent_chance = 0.60
            default_type = AgentType.STANDARD
        elif free_agent.origin_region != 'domestic':
            agent_chance = 0.50
            default_type = AgentType.STANDARD
        elif free_agent.is_prospect:
            agent_chance = 0.20
            default_type = AgentType.STANDARD
        else:
            agent_chance = 0.40
            default_type = AgentType.STANDARD
        
        if random.random() > agent_chance:
            return AgentInfo()
        
        agent_type = default_type
        
        if agent_type == AgentType.STANDARD and random.random() < 0.10:
            agent_type = AgentType.PACKAGE_DEALER
    
    agent_name = generate_agent_name()
    
    if agent_type == AgentType.POWER_AGENT:
        commission_rate = random.uniform(0.15, 0.20)
        base_difficulty = random.randint(70, 90)
    elif agent_type == AgentType.PACKAGE_DEALER:
        commission_rate = random.uniform(0.10, 0.15)
        base_difficulty = random.randint(60, 75)
    else:
        commission_rate = random.uniform(0.05, 0.10)
        base_difficulty = random.randint(40, 60)
    
    return AgentInfo(
        agent_type=agent_type,
        agent_name=agent_name,
        commission_rate=commission_rate,
        other_clients=[],
        negotiation_difficulty=base_difficulty
    )


@dataclass
class ContractDemands:
    """What the free agent wants in a contract (Steps 142-160)"""
    minimum_salary: int = 5000
    asking_salary: int = 10000
    signing_bonus_expected: int = 0
    merchandise_split: int = 30
    downside_guarantee: int = 0
    ppv_bonus_expected: int = 0
    preferred_length_weeks: int = 52
    minimum_length_weeks: int = 26
    maximum_length_weeks: int = 156
    creative_control_level: int = 0
    no_job_clauses: List[str] = field(default_factory=list)
    title_guarantee_weeks: int = 0
    brand_preference: Optional[str] = None
    finish_protection: bool = False
    promo_style: str = "any"
    max_appearances_per_year: int = 200
    travel_class: str = "standard"
    outside_projects_allowed: bool = True
    family_accommodation: bool = False
    injury_guarantee: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'minimum_salary': self.minimum_salary,
            'asking_salary': self.asking_salary,
            'signing_bonus_expected': self.signing_bonus_expected,
            'merchandise_split': self.merchandise_split,
            'downside_guarantee': self.downside_guarantee,
            'ppv_bonus_expected': self.ppv_bonus_expected,
            'preferred_length_weeks': self.preferred_length_weeks,
            'minimum_length_weeks': self.minimum_length_weeks,
            'maximum_length_weeks': self.maximum_length_weeks,
            'creative_control_level': self.creative_control_level,
            'no_job_clauses': self.no_job_clauses,
            'title_guarantee_weeks': self.title_guarantee_weeks,
            'brand_preference': self.brand_preference,
            'finish_protection': self.finish_protection,
            'promo_style': self.promo_style,
            'max_appearances_per_year': self.max_appearances_per_year,
            'travel_class': self.travel_class,
            'outside_projects_allowed': self.outside_projects_allowed,
            'family_accommodation': self.family_accommodation,
            'injury_guarantee': self.injury_guarantee
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ContractDemands':
        return ContractDemands(
            minimum_salary=data.get('minimum_salary', 5000),
            asking_salary=data.get('asking_salary', 10000),
            signing_bonus_expected=data.get('signing_bonus_expected', 0),
            merchandise_split=data.get('merchandise_split', 30),
            downside_guarantee=data.get('downside_guarantee', 0),
            ppv_bonus_expected=data.get('ppv_bonus_expected', 0),
            preferred_length_weeks=data.get('preferred_length_weeks', 52),
            minimum_length_weeks=data.get('minimum_length_weeks', 26),
            maximum_length_weeks=data.get('maximum_length_weeks', 156),
            creative_control_level=data.get('creative_control_level', 0),
            no_job_clauses=data.get('no_job_clauses', []),
            title_guarantee_weeks=data.get('title_guarantee_weeks', 0),
            brand_preference=data.get('brand_preference'),
            finish_protection=data.get('finish_protection', False),
            promo_style=data.get('promo_style', 'any'),
            max_appearances_per_year=data.get('max_appearances_per_year', 200),
            travel_class=data.get('travel_class', 'standard'),
            outside_projects_allowed=data.get('outside_projects_allowed', True),
            family_accommodation=data.get('family_accommodation', False),
            injury_guarantee=data.get('injury_guarantee', False)
        )


@dataclass
class RivalInterest:
    """Interest from a rival promotion"""
    promotion_name: str
    interest_level: int  # 0-100
    offer_salary: int = 0
    offer_made: bool = False
    deadline_week: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'promotion_name': self.promotion_name,
            'interest_level': self.interest_level,
            'offer_salary': self.offer_salary,
            'offer_made': self.offer_made,
            'deadline_week': self.deadline_week
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'RivalInterest':
        return RivalInterest(
            promotion_name=data['promotion_name'],
            interest_level=data.get('interest_level', 50),
            offer_salary=data.get('offer_salary', 0),
            offer_made=data.get('offer_made', False),
            deadline_week=data.get('deadline_week')
        )


@dataclass
class ContractHistory:
    """Previous contract information"""
    promotion_name: str
    start_year: int
    end_year: int
    departure_reason: str
    final_salary: int
    was_champion: bool = False
    relationship_on_departure: int = 50
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'promotion_name': self.promotion_name,
            'start_year': self.start_year,
            'end_year': self.end_year,
            'departure_reason': self.departure_reason,
            'final_salary': self.final_salary,
            'was_champion': self.was_champion,
            'relationship_on_departure': self.relationship_on_departure
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ContractHistory':
        return ContractHistory(
            promotion_name=data['promotion_name'],
            start_year=data['start_year'],
            end_year=data['end_year'],
            departure_reason=data['departure_reason'],
            final_salary=data.get('final_salary', 5000),
            was_champion=data.get('was_champion', False),
            relationship_on_departure=data.get('relationship_on_departure', 50)
        )


@dataclass
class MarketValueHistory:
    """STEP 116: Track market value history for trending"""
    week: int
    year: int
    value: int
    reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'week': self.week,
            'year': self.year,
            'value': self.value,
            'reason': self.reason
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'MarketValueHistory':
        return MarketValueHistory(
            week=data['week'],
            year=data['year'],
            value=data['value'],
            reason=data.get('reason', '')
        )


class FreeAgent:
    """
    Complete free agent model with all negotiation and market dynamics.
    """
    
    def __init__(
        self,
        free_agent_id: str,
        wrestler_id: str,
        wrestler_name: str,
        age: int,
        gender: str,
        alignment: str,
        role: str,
        brawling: int,
        technical: int,
        speed: int,
        mic: int,
        psychology: int,
        stamina: int,
        years_experience: int,
        is_major_superstar: bool = False,
        popularity: int = 50,
        peak_popularity: int = None,
        source: FreeAgentSource = FreeAgentSource.RELEASED,
        visibility: FreeAgentVisibility = FreeAgentVisibility.INDUSTRY_BUZZ,
        mood: FreeAgentMood = FreeAgentMood.PATIENT,
        market_value: int = 10000,
        weeks_unemployed: int = 0,
        market_value_history: Optional[List[MarketValueHistory]] = None,
        last_value_calculation: Optional[str] = None,
        average_match_rating: float = 3.0,
        recent_match_rating: float = 3.0,
        five_star_matches: int = 0,
        four_plus_matches: int = 0,
        injury_history_count: int = 0,
        months_since_last_injury: int = 12,
        has_chronic_issues: bool = False,
        backstage_reputation: int = 50,
        locker_room_leader: bool = False,
        known_difficult: bool = False,
        agent: Optional[AgentInfo] = None,
        demands: Optional[ContractDemands] = None,
        rival_interest: Optional[List] = None,  # Can be List[RivalInterest] or List[dict]
        contract_history: Optional[List[ContractHistory]] = None,
        has_controversy: bool = False,
        controversy_type: Optional[str] = None,
        controversy_severity: int = 0,
        time_since_incident_weeks: int = 0,
        is_legend: bool = False,
        retirement_status: str = "active",
        comeback_likelihood: int = 50,
        origin_region: str = "domestic",
        requires_visa: bool = False,
        exclusive_willing: bool = True,
        is_prospect: bool = False,
        training_investment_needed: int = 0,
        ceiling_potential: int = 50,
        available_from_year: int = 1,
        available_from_week: int = 1,
        no_compete_until_year: Optional[int] = None,
        no_compete_until_week: Optional[int] = None,
        exclusive_window_active: bool = False,
        exclusive_window_holder: Optional[str] = None,
        exclusive_window_holder_name: Optional[str] = None,
        exclusive_window_cost_paid: int = 0,
        exclusive_window_duration: int = 0,
        exclusive_window_started_year: Optional[int] = None,
        exclusive_window_started_week: Optional[int] = None,
        exclusive_window_expires_year: Optional[int] = None,
        exclusive_window_expires_week: Optional[int] = None,
        exclusive_window_id: Optional[str] = None,
        exclusive_window_resulted_in_signing: bool = False,
        discovered: bool = False,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None
    ):
        self.id = free_agent_id
        self.wrestler_id = wrestler_id
        self.wrestler_name = wrestler_name
        
        self.age = age
        self.gender = gender
        self.alignment = alignment
        self.role = role
        
        self.brawling = brawling
        self.technical = technical
        self.speed = speed
        self.mic = mic
        self.psychology = psychology
        self.stamina = stamina
        
        self.years_experience = years_experience
        self.is_major_superstar = is_major_superstar
        self.popularity = popularity
        self.peak_popularity = peak_popularity if peak_popularity is not None else popularity
        
        self.source = source
        self.visibility = visibility
        self.mood = mood
        self.market_value = market_value
        self.weeks_unemployed = weeks_unemployed
        
        self.market_value_history = market_value_history or []
        self.last_value_calculation = last_value_calculation
        
        self.average_match_rating = average_match_rating
        self.recent_match_rating = recent_match_rating
        self.five_star_matches = five_star_matches
        self.four_plus_matches = four_plus_matches
        
        self.injury_history_count = injury_history_count
        self.months_since_last_injury = months_since_last_injury
        self.has_chronic_issues = has_chronic_issues
        
        self.backstage_reputation = backstage_reputation
        self.locker_room_leader = locker_room_leader
        self.known_difficult = known_difficult
        
        self.agent = agent or AgentInfo()
        self.demands = demands or ContractDemands()
        self.rival_interest = rival_interest or []
        self.contract_history = contract_history or []
        
        self.has_controversy = has_controversy
        self.controversy_type = controversy_type
        self.controversy_severity = controversy_severity
        self.time_since_incident_weeks = time_since_incident_weeks
        
        self.is_legend = is_legend
        self.retirement_status = retirement_status
        self.comeback_likelihood = comeback_likelihood
        
        self.origin_region = origin_region
        self.requires_visa = requires_visa
        self.exclusive_willing = exclusive_willing
        
        self.is_prospect = is_prospect
        self.training_investment_needed = training_investment_needed
        self.ceiling_potential = ceiling_potential
        
        self.available_from_year = available_from_year
        self.available_from_week = available_from_week
        self.no_compete_until_year = no_compete_until_year
        self.no_compete_until_week = no_compete_until_week
        
        self.exclusive_window_active = exclusive_window_active
        self.exclusive_window_holder = exclusive_window_holder
        self.exclusive_window_holder_name = exclusive_window_holder_name
        self.exclusive_window_cost_paid = exclusive_window_cost_paid
        self.exclusive_window_duration = exclusive_window_duration
        self.exclusive_window_started_year = exclusive_window_started_year
        self.exclusive_window_started_week = exclusive_window_started_week
        self.exclusive_window_expires_year = exclusive_window_expires_year
        self.exclusive_window_expires_week = exclusive_window_expires_week
        self.exclusive_window_id = exclusive_window_id
        self.exclusive_window_resulted_in_signing = exclusive_window_resulted_in_signing
        
        self.discovered = discovered
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or datetime.now().isoformat()
    
    # ========================================================================
    # Computed Properties
    # ========================================================================
    
    @property
    def overall_rating(self) -> int:
        """Calculate overall wrestler rating"""
        return int((self.brawling + self.technical + self.speed + 
                   self.mic + self.psychology + self.stamina) / 6)
    
    @property
    def is_available(self) -> bool:
        """Check if free agent is currently available for signing"""
        return self.retirement_status not in ["full_retired", "injury_retired"]
    
    @property
    def has_no_compete(self) -> bool:
        """Check if under no-compete clause"""
        return self.no_compete_until_year is not None
    
    @property
    def highest_rival_offer(self) -> int:
        """Get the highest competing offer - handles both dict and object formats"""
        if not self.rival_interest:
            return 0
        
        offers = []
        for r in self.rival_interest:
            # Handle dict format (from rivals_routes)
            if isinstance(r, dict):
                if r.get('offer_made') and r.get('offer_salary'):
                    offers.append(r.get('offer_salary', 0))
            # Handle RivalInterest object format
            elif hasattr(r, 'offer_made') and hasattr(r, 'offer_salary'):
                if r.offer_made and r.offer_salary:
                    offers.append(r.offer_salary)
        
        return max(offers) if offers else 0
    
    @property
    def has_active_rival_offer(self) -> bool:
        """Check if any rival has made an active offer"""
        if not self.rival_interest:
            return False
        
        for r in self.rival_interest:
            if isinstance(r, dict):
                if r.get('offer_made'):
                    return True
            elif hasattr(r, 'offer_made') and r.offer_made:
                return True
        
        return False
    
    @property
    def negotiation_difficulty(self) -> int:
        """Calculate overall difficulty of negotiating (0-100)"""
        difficulty = 50
        
        # Mood affects difficulty
        if self.mood == FreeAgentMood.DESPERATE:
            difficulty -= 30
        elif self.mood == FreeAgentMood.HUNGRY:
            difficulty -= 15
        elif self.mood == FreeAgentMood.BITTER:
            difficulty += 20
        elif self.mood == FreeAgentMood.ARROGANT:
            difficulty += 25
        
        # Agent adds difficulty
        if self.agent and self.agent.agent_type != AgentType.NONE:
            difficulty += self.agent.negotiation_difficulty // 2
        
        # Star power adds difficulty
        if self.is_major_superstar:
            difficulty += 15
        
        # High popularity adds difficulty
        difficulty += (self.popularity - 50) // 5
        
        # Competition adds difficulty
        if self.rival_interest:
            rival_count = len(self.rival_interest)
            difficulty += rival_count * 5
            if self.highest_rival_offer > 0:
                difficulty += 10
        
        return max(0, min(100, difficulty))
    
    @property
    def visibility_label(self) -> str:
        """Human-readable visibility tier"""
        labels = {
            FreeAgentVisibility.HEADLINE_NEWS: "Headline News",
            FreeAgentVisibility.INDUSTRY_BUZZ: "Industry Buzz",
            FreeAgentVisibility.HIDDEN_GEM: "Hidden Gem",
            FreeAgentVisibility.DEEP_CUT: "Deep Cut"
        }
        return labels.get(self.visibility, "Unknown")
    
    @property
    def mood_label(self) -> str:
        """Human-readable mood"""
        labels = {
            FreeAgentMood.PATIENT: "Patient",
            FreeAgentMood.HUNGRY: "Hungry",
            FreeAgentMood.BITTER: "Bitter",
            FreeAgentMood.DESPERATE: "Desperate",
            FreeAgentMood.ARROGANT: "Arrogant"
        }
        return labels.get(self.mood, "Unknown")
    
    @property
    def source_label(self) -> str:
        """Human-readable source"""
        labels = {
            FreeAgentSource.RELEASED: "Released",
            FreeAgentSource.CONTRACT_EXPIRED: "Contract Expired",
            FreeAgentSource.RETIRED_COMEBACK: "Returning Legend",
            FreeAgentSource.INTERNATIONAL: "International Talent",
            FreeAgentSource.PROSPECT: "Fresh Prospect",
            FreeAgentSource.CONTROVERSY: "Controversy Case",
            FreeAgentSource.MUTUAL_AGREEMENT: "Mutual Agreement"
        }
        return labels.get(self.source, "Unknown")
    
    @property
    def popularity_trend(self) -> int:
        """STEP 116: Calculate popularity trend from peak"""
        return self.popularity - self.peak_popularity
    
    @property
    def market_value_trend(self) -> str:
        """STEP 116: Determine if market value is rising, falling, or stable"""
        if len(self.market_value_history) < 2:
            return "stable"
        
        recent = self.market_value_history[-1].value if self.market_value_history else self.market_value
        previous = self.market_value_history[-2].value if len(self.market_value_history) >= 2 else recent
        
        diff_percent = ((recent - previous) / max(previous, 1)) * 100
        
        if diff_percent > 5:
            return "rising"
        elif diff_percent < -5:
            return "falling"
        return "stable"
    
    # ========================================================================
    # State Modification Methods
    # ========================================================================
    
    def update_mood(self, current_year: int = 1, current_week: int = 1) -> dict:
        """STEP 117: Enhanced mood update using MoodTransitionRules."""
        from models.free_agent_moods import MoodTransitionRules
        
        old_mood = self.mood
        
        new_mood = MoodTransitionRules.calculate_mood(
            weeks_unemployed=self.weeks_unemployed,
            rejection_count=0,
            departure_reason=self.source.value if hasattr(self.source, 'value') else str(self.source),
            rival_interest_count=len(self.rival_interest),
            is_legend=self.is_legend,
            is_major_superstar=self.is_major_superstar,
            age=self.age,
            peak_popularity=self.peak_popularity,
            current_popularity=self.popularity,
            has_controversy=self.has_controversy
        )
        
        reason = ""
        
        if old_mood != new_mood:
            self.mood = new_mood
            self.updated_at = datetime.now().isoformat()
            
            if new_mood == FreeAgentMood.DESPERATE:
                reason = f"Unemployed for {self.weeks_unemployed} weeks"
            elif new_mood == FreeAgentMood.HUNGRY:
                reason = "Ready to make a deal"
            elif new_mood == FreeAgentMood.BITTER:
                reason = "Frustrated with unemployment"
            elif new_mood == FreeAgentMood.ARROGANT:
                reason = "Multiple promotions interested"
            elif new_mood == FreeAgentMood.PATIENT:
                reason = "Waiting for the right opportunity"
        
        self._adjust_demands_for_mood()
        
        return {
            'old_mood': old_mood.value if isinstance(old_mood, FreeAgentMood) else old_mood,
            'new_mood': self.mood.value if isinstance(self.mood, FreeAgentMood) else self.mood,
            'reason': reason,
            'changed': old_mood != new_mood,
            'weeks_unemployed': self.weeks_unemployed
        }

    def _adjust_demands_for_mood(self):
        """STEP 117: Adjust contract demands based on current mood"""
        mood_multipliers = {
            FreeAgentMood.DESPERATE: 0.70,
            FreeAgentMood.HUNGRY: 0.85,
            FreeAgentMood.PATIENT: 1.00,
            FreeAgentMood.BITTER: 1.25,
            FreeAgentMood.ARROGANT: 1.40
        }
        
        multiplier = mood_multipliers.get(self.mood, 1.0)
        base_asking = int(self.market_value * multiplier)
        self.demands.asking_salary = base_asking
        self.demands.minimum_salary = int(base_asking * 0.7)
        
        if self.mood == FreeAgentMood.DESPERATE:
            self.demands.signing_bonus_expected = 0
        elif self.mood == FreeAgentMood.HUNGRY:
            self.demands.signing_bonus_expected = int(base_asking * 0.25)
        elif self.mood == FreeAgentMood.BITTER:
            self.demands.signing_bonus_expected = int(base_asking * 0.75)
        elif self.mood == FreeAgentMood.ARROGANT:
            self.demands.signing_bonus_expected = int(base_asking * 1.0)
        
        if self.mood == FreeAgentMood.DESPERATE:
            self.demands.minimum_length_weeks = 26
            self.demands.preferred_length_weeks = 52
        elif self.mood == FreeAgentMood.ARROGANT:
            self.demands.minimum_length_weeks = 26
            self.demands.preferred_length_weeks = 52
            self.demands.maximum_length_weeks = 104

    def get_mood_description(self) -> str:
        """STEP 117: Get detailed mood description"""
        descriptions = {
            FreeAgentMood.DESPERATE: (
                f"{self.wrestler_name} has been unemployed for {self.weeks_unemployed} weeks and is "
                f"desperate for any opportunity. Will accept significantly reduced terms."
            ),
            FreeAgentMood.HUNGRY: (
                f"{self.wrestler_name} is eager to get back to work after {self.weeks_unemployed} weeks "
                f"on the shelf. Open to negotiation and willing to prove themselves."
            ),
            FreeAgentMood.PATIENT: (
                f"{self.wrestler_name} is patiently waiting for the right opportunity. "
                f"Not desperate, but open to fair offers."
            ),
            FreeAgentMood.BITTER: (
                f"{self.wrestler_name} is still bitter about their previous departure and "
                f"demands to be compensated properly. Negotiations will be difficult."
            ),
            FreeAgentMood.ARROGANT: (
                f"{self.wrestler_name} believes they're still a top-tier talent and "
                f"expects to be paid accordingly. Overvalues their current market worth."
            )
        }
        return descriptions.get(self.mood, "Unknown mood state")

    def get_negotiation_difficulty_explanation(self) -> str:
        """STEP 117: Explain why negotiation is at current difficulty"""
        difficulty = self.negotiation_difficulty
        factors = []
        
        if self.mood == FreeAgentMood.DESPERATE:
            factors.append("Very flexible due to desperation (-30)")
        elif self.mood == FreeAgentMood.HUNGRY:
            factors.append("Willing to negotiate (-15)")
        elif self.mood == FreeAgentMood.BITTER:
            factors.append("Bitter about past (+20)")
        elif self.mood == FreeAgentMood.ARROGANT:
            factors.append("Overvalues self (+25)")
        
        if self.agent and self.agent.agent_type != AgentType.NONE:
            factors.append(f"Agent representation (+{self.agent.negotiation_difficulty // 2})")
        
        if self.is_major_superstar:
            factors.append("Major superstar (+15)")
        
        pop_mod = (self.popularity - 50) // 5
        if pop_mod > 0:
            factors.append(f"High popularity (+{pop_mod})")
        elif pop_mod < 0:
            factors.append(f"Lower popularity ({pop_mod})")
        
        if self.rival_interest:
            factors.append(f"Rival interest (+{len(self.rival_interest) * 5})")
            if self.highest_rival_offer > 0:
                factors.append("Active competing offer (+10)")
        
        explanation = f"Difficulty: {difficulty}/100\n\nFactors:\n"
        explanation += "\n".join(f"  • {factor}" for factor in factors)
        
        return explanation
    
    def add_rival_interest(self, promotion_name: str, interest_level: int):
        """Add or update rival promotion interest"""
        for rival in self.rival_interest:
            if isinstance(rival, dict):
                if rival.get('promotion_name') == promotion_name:
                    rival['interest_level'] = interest_level
                    self.updated_at = datetime.now().isoformat()
                    return
            elif hasattr(rival, 'promotion_name') and rival.promotion_name == promotion_name:
                rival.interest_level = interest_level
                self.updated_at = datetime.now().isoformat()
                return
        
        self.rival_interest.append(RivalInterest(
            promotion_name=promotion_name,
            interest_level=interest_level
        ))
        self.updated_at = datetime.now().isoformat()
    
    def rival_makes_offer(self, promotion_name: str, salary: int, deadline_week: int):
        """A rival promotion makes an offer"""
        for rival in self.rival_interest:
            if isinstance(rival, dict):
                if rival.get('promotion_name') == promotion_name:
                    rival['offer_made'] = True
                    rival['offer_salary'] = salary
                    rival['deadline_week'] = deadline_week
                    self.updated_at = datetime.now().isoformat()
                    return True
            elif hasattr(rival, 'promotion_name') and rival.promotion_name == promotion_name:
                rival.offer_made = True
                rival.offer_salary = salary
                rival.deadline_week = deadline_week
                self.updated_at = datetime.now().isoformat()
                return True
        return False
    
    def advance_week(self):
        """Process weekly updates for this free agent"""
        self.weeks_unemployed += 1
        self.update_mood()
        
        if self.has_controversy:
            self.time_since_incident_weeks += 1
            if self.time_since_incident_weeks > 52:
                self.controversy_severity = max(0, self.controversy_severity - 5)
        
        if self.mood == FreeAgentMood.DESPERATE:
            self.demands.asking_salary = int(self.demands.asking_salary * 0.95)
            self.demands.asking_salary = max(
                self.demands.minimum_salary,
                self.demands.asking_salary
            )
        
        self.updated_at = datetime.now().isoformat()

    def recalculate_market_value(
        self, 
        match_history_rating: float = 3.0,
        year: int = 1,
        week: int = 1,
        use_calculator: bool = True
    ) -> int:
        """STEP 116: Recalculate market value using the comprehensive calculator."""
        if use_calculator:
            try:
                from economy.market_value import market_value_calculator, MarketValueFactors
                
                factors = MarketValueFactors(
                    current_popularity=self.popularity,
                    peak_popularity=self.peak_popularity,
                    popularity_trend=self.popularity_trend,
                    average_match_rating=self.average_match_rating,
                    recent_match_rating=self.recent_match_rating,
                    five_star_match_count=self.five_star_matches,
                    four_plus_match_count=self.four_plus_matches,
                    age=self.age,
                    years_experience=self.years_experience,
                    role=self.role,
                    is_major_superstar=self.is_major_superstar,
                    is_legend=self.is_legend,
                    injury_history_count=self.injury_history_count,
                    months_since_last_injury=self.months_since_last_injury,
                    has_chronic_issues=self.has_chronic_issues,
                    backstage_reputation=self.backstage_reputation,
                    locker_room_leader=self.locker_room_leader,
                    known_difficult=self.known_difficult,
                    controversy_severity=self.controversy_severity if self.has_controversy else 0,
                    rival_promotion_interest=len(self.rival_interest),
                    highest_rival_offer=self.highest_rival_offer,
                    bidding_war_active=self.has_active_rival_offer,
                    weeks_unemployed=self.weeks_unemployed,
                    mood=self.mood.value if isinstance(self.mood, FreeAgentMood) else self.mood
                )
                
                new_value, breakdown = market_value_calculator.calculate_market_value(factors)
                
                old_value = self.market_value
                self.market_value = new_value
                
                self.market_value_history.append(MarketValueHistory(
                    year=year,
                    week=week,
                    value=new_value,
                    reason=f"Recalculated (was ${old_value:,})"
                ))
                
                if len(self.market_value_history) > 52:
                    self.market_value_history = self.market_value_history[-52:]
                
                self.last_value_calculation = datetime.now().isoformat()
                self.updated_at = datetime.now().isoformat()
                self._update_demands_from_market_value()
                
                return new_value
                
            except ImportError:
                pass
        
        # Simple fallback calculation
        base_value = 5000
        base_value += self.popularity * 100
        avg_attrs = self.overall_rating
        base_value += avg_attrs * 50
        
        role_multipliers = {
            'Main Event': 2.0,
            'Upper Midcard': 1.5,
            'Midcard': 1.0,
            'Lower Midcard': 0.7,
            'Jobber': 0.5
        }
        base_value = int(base_value * role_multipliers.get(self.role, 1.0))
        
        if self.is_major_superstar:
            base_value = int(base_value * 1.5)
        
        if self.age > 35:
            base_value = int(base_value * (1 - (self.age - 35) * 0.03))
        
        if match_history_rating > 4.0:
            base_value = int(base_value * 1.2)
        elif match_history_rating < 2.5:
            base_value = int(base_value * 0.8)
        
        if self.has_controversy:
            discount = self.controversy_severity / 200
            base_value = int(base_value * (1 - discount))
        
        if self.rival_interest:
            base_value = int(base_value * (1 + len(self.rival_interest) * 0.05))
        
        if self.mood == FreeAgentMood.DESPERATE:
            base_value = int(base_value * 0.7)
        elif self.mood == FreeAgentMood.HUNGRY:
            base_value = int(base_value * 0.85)
        
        self.market_value = max(3000, base_value)
        self.updated_at = datetime.now().isoformat()
        
        return self.market_value
    
    def _update_demands_from_market_value(self):
        """STEP 116: Update contract demands based on market value"""
        mood_adjustments = {
            FreeAgentMood.PATIENT: 1.1,
            FreeAgentMood.HUNGRY: 0.95,
            FreeAgentMood.BITTER: 1.25,
            FreeAgentMood.DESPERATE: 0.8,
            FreeAgentMood.ARROGANT: 1.35
        }
        
        mood_mult = mood_adjustments.get(self.mood, 1.0)
        self.demands.asking_salary = int(self.market_value * mood_mult)
        self.demands.minimum_salary = int(self.demands.asking_salary * 0.7)
        
        if self.is_major_superstar:
            self.demands.signing_bonus_expected = self.market_value * 2
        elif self.role in ['Main Event', 'Upper Midcard']:
            self.demands.signing_bonus_expected = int(self.market_value * 0.5)
        else:
            self.demands.signing_bonus_expected = 0
    
    def update_match_stats(self, match_rating: float, year: int, week: int):
        """STEP 116: Update match statistics after a match"""
        if self.popularity > self.peak_popularity:
            self.peak_popularity = self.popularity
        
        if match_rating >= 5.0:
            self.five_star_matches += 1
        elif match_rating >= 4.0:
            self.four_plus_matches += 1
        
        self.recent_match_rating = (self.recent_match_rating * 0.8) + (match_rating * 0.2)
        self.average_match_rating = (self.average_match_rating * 0.95) + (match_rating * 0.05)
        self.updated_at = datetime.now().isoformat()
    
    def record_injury(self, severity: int = 1):
        """STEP 116: Record an injury for market value purposes"""
        self.injury_history_count += 1
        self.months_since_last_injury = 0
        
        if severity >= 3 and random.random() < 0.2:
            self.has_chronic_issues = True
        
        self.updated_at = datetime.now().isoformat()
    
    def update_reputation(self, change: int, reason: str = ""):
        """STEP 116: Update backstage reputation"""
        self.backstage_reputation = max(0, min(100, self.backstage_reputation + change))
        
        if self.backstage_reputation >= 85 and self.years_experience >= 10:
            self.locker_room_leader = True
        
        if self.backstage_reputation <= 25:
            self.known_difficult = True
        elif self.backstage_reputation >= 50:
            self.known_difficult = False
        
        self.updated_at = datetime.now().isoformat()
    
    def calculate_comprehensive_market_value(self, year: int, week: int, include_breakdown: bool = True) -> tuple:
        """STEP 116: Calculate comprehensive market value."""
        try:
            from economy.market_value import market_value_calculator, MarketValueFactors
            
            factors = MarketValueFactors(
                base_value=self.market_value,
                current_popularity=self.popularity,
                peak_popularity=self.peak_popularity,
                popularity_trend=self.popularity_trend,
                average_match_rating=self.average_match_rating,
                recent_match_rating=self.recent_match_rating,
                five_star_match_count=self.five_star_matches,
                four_plus_match_count=self.four_plus_matches,
                age=self.age,
                years_experience=self.years_experience,
                role=self.role,
                is_major_superstar=self.is_major_superstar,
                is_legend=self.is_legend,
                current_injury_severity=0,
                injury_history_count=self.injury_history_count,
                months_since_last_injury=self.months_since_last_injury,
                has_chronic_issues=self.has_chronic_issues,
                backstage_reputation=self.backstage_reputation,
                locker_room_leader=self.locker_room_leader,
                known_difficult=self.known_difficult,
                controversy_severity=self.controversy_severity if self.has_controversy else 0,
                rival_promotion_interest=len(self.rival_interest),
                highest_rival_offer=self.highest_rival_offer,
                bidding_war_active=self.has_active_rival_offer,
                weeks_unemployed=self.weeks_unemployed,
                mood=self.mood.value if isinstance(self.mood, FreeAgentMood) else self.mood
            )
            
            new_value, breakdown = market_value_calculator.calculate_market_value(
                factors, include_breakdown=include_breakdown
            )
            
            old_value = self.market_value
            self.market_value = new_value
            
            self.market_value_history.append(MarketValueHistory(
                year=year, week=week, value=new_value,
                reason=f"Comprehensive calculation (was ${old_value:,})"
            ))
            
            if len(self.market_value_history) > 52:
                self.market_value_history = self.market_value_history[-52:]
            
            self.last_value_calculation = datetime.now().isoformat()
            self.updated_at = datetime.now().isoformat()
            self._update_demands_from_market_value()
            
            return new_value, breakdown

        except ImportError as e:
            print(f"⚠️ MarketValueCalculator not available: {e}")
            return self.recalculate_market_value(year=year, week=week, use_calculator=False), None

    def get_market_value_breakdown(self) -> Optional[Dict[str, Any]]:
        """STEP 116: Get detailed breakdown of current market value"""
        try:
            from economy.market_value import market_value_calculator, MarketValueFactors
            
            factors = MarketValueFactors(
                current_popularity=self.popularity,
                peak_popularity=self.peak_popularity,
                popularity_trend=self.popularity_trend,
                average_match_rating=self.average_match_rating,
                recent_match_rating=self.recent_match_rating,
                five_star_match_count=self.five_star_matches,
                four_plus_match_count=self.four_plus_matches,
                age=self.age,
                years_experience=self.years_experience,
                role=self.role,
                is_major_superstar=self.is_major_superstar,
                is_legend=self.is_legend,
                injury_history_count=self.injury_history_count,
                months_since_last_injury=self.months_since_last_injury,
                has_chronic_issues=self.has_chronic_issues,
                backstage_reputation=self.backstage_reputation,
                locker_room_leader=self.locker_room_leader,
                known_difficult=self.known_difficult,
                controversy_severity=self.controversy_severity if self.has_controversy else 0,
                rival_promotion_interest=len(self.rival_interest),
                highest_rival_offer=self.highest_rival_offer,
                bidding_war_active=self.has_active_rival_offer,
                weeks_unemployed=self.weeks_unemployed,
                mood=self.mood.value if isinstance(self.mood, FreeAgentMood) else self.mood
            )
            
            value, breakdown = market_value_calculator.calculate_market_value(factors)
            return breakdown.to_dict()
            
        except ImportError:
            return None
    
    # ========================================================================
    # STEP 124: Exclusive Negotiating Window Methods
    # ========================================================================
    
    def has_active_exclusive_window(self) -> bool:
        """Check if free agent currently has an active exclusive window"""
        return getattr(self, 'exclusive_window_active', False)

    def get_exclusive_window_holder(self) -> Optional[str]:
        """Get the promotion ID holding exclusive rights"""
        return getattr(self, 'exclusive_window_holder', None) if self.has_active_exclusive_window() else None

    def get_exclusive_window_expires(self) -> Optional[dict]:
        """Get when exclusive window expires"""
        if not self.has_active_exclusive_window():
            return None
        
        return {
            'year': getattr(self, 'exclusive_window_expires_year', None),
            'week': getattr(self, 'exclusive_window_expires_week', None)
        }

    def calculate_exclusive_window_cost(
        self,
        relationship_quality: int = 50,
        current_year: int = 1,
        current_week: int = 1
    ) -> Dict[str, Any]:
        """STEP 124: Calculate cost and terms for exclusive negotiating window."""
        base_cost = int(self.market_value * 0.3)
        relationship_multiplier = 1.5 - (relationship_quality / 100)
        
        mood_modifiers = {
            'patient': {'cost_mult': 1.0, 'base_days': 14, 'refundable': False},
            'hungry': {'cost_mult': 0.8, 'base_days': 10, 'refundable': True},
            'bitter': {'cost_mult': 1.5, 'base_days': 7, 'refundable': False},
            'desperate': {'cost_mult': 0.5, 'base_days': 21, 'refundable': True},
            'arrogant': {'cost_mult': 2.0, 'base_days': 5, 'refundable': False}
        }
        
        mood_str = self.mood.value if hasattr(self.mood, 'value') else str(self.mood)
        mood_mod = mood_modifiers.get(mood_str, mood_modifiers['patient'])
        
        status_multiplier = 1.0
        if self.is_major_superstar:
            status_multiplier = 1.5
        elif self.is_legend:
            status_multiplier = 1.8
        elif self.role == 'Main Event':
            status_multiplier = 1.3
        
        agent_multiplier = 1.2 if self.agent and self.agent.agent_type != AgentType.NONE else 1.0
        agent_day_penalty = -3 if self.agent and self.agent.agent_type != AgentType.NONE else 0
        
        final_cost = int(
            base_cost * 
            relationship_multiplier * 
            mood_mod['cost_mult'] * 
            status_multiplier * 
            agent_multiplier
        )
        
        final_duration = max(3, mood_mod['base_days'] + agent_day_penalty)
        final_cost = max(1000, final_cost)
        
        return {
            'cost': final_cost,
            'duration_days': final_duration,
            'expires_year': current_year,
            'expires_week': current_week + (final_duration // 7) + (1 if final_duration % 7 else 0),
            'refund_eligible': mood_mod['refundable'],
            'refund_percentage': 50 if mood_mod['refundable'] else 0,
            'agent_involved': agent_multiplier > 1.0,
            'breakdown': {
                'base_cost': base_cost,
                'relationship_modifier': relationship_multiplier,
                'mood_modifier': mood_mod['cost_mult'],
                'status_modifier': status_multiplier,
                'agent_modifier': agent_multiplier
            }
        }

    def start_exclusive_window(
        self,
        promotion_id: str,
        promotion_name: str,
        cost_paid: int,
        duration_days: int,
        started_year: int,
        started_week: int,
        expires_year: int,
        expires_week: int
    ) -> str:
        """STEP 124: Start an exclusive negotiating window."""
        self.exclusive_window_active = True
        self.exclusive_window_holder = promotion_id
        self.exclusive_window_holder_name = promotion_name
        self.exclusive_window_cost_paid = cost_paid
        self.exclusive_window_duration = duration_days
        self.exclusive_window_started_year = started_year
        self.exclusive_window_started_week = started_week
        self.exclusive_window_expires_year = expires_year
        self.exclusive_window_expires_week = expires_week
        
        window_id = f"ew_{self.id}_{started_year}_{started_week}"
        self.exclusive_window_id = window_id
        
        self.updated_at = datetime.now().isoformat()
        
        return window_id

    def end_exclusive_window(self, resulted_in_signing: bool = False):
        """STEP 124: End the exclusive window"""
        self.exclusive_window_active = False
        self.exclusive_window_resulted_in_signing = resulted_in_signing
        self.updated_at = datetime.now().isoformat()

    def is_window_expired(self, current_year: int, current_week: int) -> bool:
        """STEP 124: Check if exclusive window has expired"""
        if not self.has_active_exclusive_window():
            return False
        
        expires_year = getattr(self, 'exclusive_window_expires_year', None)
        expires_week = getattr(self, 'exclusive_window_expires_week', None)
        
        if expires_year is None or expires_week is None:
            return False
        
        if current_year > expires_year:
            return True
        elif current_year == expires_year and current_week >= expires_week:
            return True
        
        return False

    def can_receive_offer_from(self, promotion_id: str) -> Dict[str, Any]:
        """STEP 124: Check if a promotion can make an offer to this free agent."""
        if self.has_active_exclusive_window():
            holder = self.get_exclusive_window_holder()
            
            if promotion_id == holder:
                return {
                    'can_offer': True,
                    'reason': 'exclusive_window_holder',
                    'message': 'You hold exclusive negotiating rights'
                }
            else:
                expires = self.get_exclusive_window_expires()
                return {
                    'can_offer': False,
                    'reason': 'exclusive_window_blocked',
                    'message': f"Exclusive window held by another promotion until Year {expires['year']}, Week {expires['week']}",
                    'holder': getattr(self, 'exclusive_window_holder_name', 'Unknown'),
                    'expires_year': expires['year'],
                    'expires_week': expires['week']
                }
        
        if self.has_no_compete:
            return {
                'can_offer': False,
                'reason': 'no_compete_active',
                'message': f"No-compete clause until Year {self.no_compete_until_year}, Week {self.no_compete_until_week}",
                'expires_year': self.no_compete_until_year,
                'expires_week': self.no_compete_until_week
            }
        
        return {
            'can_offer': True,
            'reason': 'open_market',
            'message': 'Free to negotiate'
        }
    
    # ========================================================================
    # Serialization
    # ========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON/database storage"""
        # Safely serialize rival_interest (handles both dict and object formats)
        rival_interest_list = []
        for r in self.rival_interest:
            if isinstance(r, dict):
                rival_interest_list.append(r)
            elif hasattr(r, 'to_dict'):
                rival_interest_list.append(r.to_dict())
            else:
                # Fallback
                rival_interest_list.append({
                    'promotion_name': getattr(r, 'promotion_name', 'Unknown'),
                    'interest_level': getattr(r, 'interest_level', 0),
                    'offer_salary': getattr(r, 'offer_salary', 0),
                    'offer_made': getattr(r, 'offer_made', False),
                    'deadline_week': getattr(r, 'deadline_week', None)
                })
        
        return {
            'id': self.id,
            'wrestler_id': self.wrestler_id,
            'wrestler_name': self.wrestler_name,
            
            'age': self.age,
            'gender': self.gender,
            'alignment': self.alignment,
            'role': self.role,
            
            'attributes': {
                'brawling': self.brawling,
                'technical': self.technical,
                'speed': self.speed,
                'mic': self.mic,
                'psychology': self.psychology,
                'stamina': self.stamina,
                'overall': self.overall_rating
            },
            
            'years_experience': self.years_experience,
            'is_major_superstar': self.is_major_superstar,
            'popularity': self.popularity,
            'peak_popularity': self.peak_popularity,
            
            'source': self.source.value if hasattr(self.source, 'value') else str(self.source),
            'source_label': self.source_label,
            'visibility': self.visibility.value if hasattr(self.visibility, 'value') else self.visibility,
            'visibility_label': self.visibility_label,
            'mood': self.mood.value if hasattr(self.mood, 'value') else str(self.mood),
            'mood_label': self.mood_label,
            'market_value': self.market_value,
            'weeks_unemployed': self.weeks_unemployed,
            
            'market_value_trend': self.market_value_trend,
            'popularity_trend': self.popularity_trend,
            'last_value_calculation': self.last_value_calculation,
            
            'average_match_rating': self.average_match_rating,
            'recent_match_rating': self.recent_match_rating,
            'five_star_matches': self.five_star_matches,
            'four_plus_matches': self.four_plus_matches,
            
            'injury_history_count': self.injury_history_count,
            'months_since_last_injury': self.months_since_last_injury,
            'has_chronic_issues': self.has_chronic_issues,
            
            'backstage_reputation': self.backstage_reputation,
            'locker_room_leader': self.locker_room_leader,
            'known_difficult': self.known_difficult,
            
            'negotiation_difficulty': self.negotiation_difficulty,
            'highest_rival_offer': self.highest_rival_offer,
            
            'agent': self.agent.to_dict() if self.agent else {},
            'demands': self.demands.to_dict() if self.demands else {},
            
            'rival_interest': rival_interest_list,
            'contract_history': [h.to_dict() for h in self.contract_history],
            'market_value_history': [h.to_dict() for h in self.market_value_history[-12:]],
            
            'has_controversy': self.has_controversy,
            'controversy_type': self.controversy_type,
            'controversy_severity': self.controversy_severity,
            'time_since_incident_weeks': self.time_since_incident_weeks,
            
            'is_legend': self.is_legend,
            'retirement_status': self.retirement_status,
            'comeback_likelihood': self.comeback_likelihood,
            
            'origin_region': self.origin_region,
            'requires_visa': self.requires_visa,
            'exclusive_willing': self.exclusive_willing,
            
            'is_prospect': self.is_prospect,
            'training_investment_needed': self.training_investment_needed,
            'ceiling_potential': self.ceiling_potential,
            
            'available_from_year': self.available_from_year,
            'available_from_week': self.available_from_week,
            'no_compete_until_year': self.no_compete_until_year,
            'no_compete_until_week': self.no_compete_until_week,
            'has_no_compete': self.has_no_compete,
            
            'exclusive_window': {
                'active': self.exclusive_window_active,
                'holder': self.exclusive_window_holder,
                'holder_name': self.exclusive_window_holder_name,
                'cost_paid': self.exclusive_window_cost_paid,
                'duration': self.exclusive_window_duration,
                'started_year': self.exclusive_window_started_year,
                'started_week': self.exclusive_window_started_week,
                'expires_year': self.exclusive_window_expires_year,
                'expires_week': self.exclusive_window_expires_week,
                'id': self.exclusive_window_id,
                'resulted_in_signing': self.exclusive_window_resulted_in_signing
            },
            
            'discovered': self.discovered,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'FreeAgent':
        """Create FreeAgent from dictionary"""
        attrs = data.get('attributes', {})
        
        mv_history = []
        for h in data.get('market_value_history', []):
            mv_history.append(MarketValueHistory.from_dict(h))
        
        # Parse rival interest - handle both formats
        rival_interest = []
        for r in data.get('rival_interest', []):
            if isinstance(r, dict):
                rival_interest.append(RivalInterest.from_dict(r))
            else:
                rival_interest.append(r)
        
        # Handle exclusive window data
        ew_data = data.get('exclusive_window', {})
        
        return FreeAgent(
            free_agent_id=data['id'],
            wrestler_id=data['wrestler_id'],
            wrestler_name=data['wrestler_name'],
            
            age=data['age'],
            gender=data['gender'],
            alignment=data['alignment'],
            role=data['role'],
            
            brawling=attrs.get('brawling', data.get('brawling', 50)),
            technical=attrs.get('technical', data.get('technical', 50)),
            speed=attrs.get('speed', data.get('speed', 50)),
            mic=attrs.get('mic', data.get('mic', 50)),
            psychology=attrs.get('psychology', data.get('psychology', 50)),
            stamina=attrs.get('stamina', data.get('stamina', 50)),
            
            years_experience=data.get('years_experience', 5),
            is_major_superstar=data.get('is_major_superstar', False),
            popularity=data.get('popularity', 50),
            peak_popularity=data.get('peak_popularity', data.get('popularity', 50)),
            
            source=FreeAgentSource(data.get('source', 'released')),
            visibility=FreeAgentVisibility(data.get('visibility', 2)),
            mood=FreeAgentMood(data.get('mood', 'patient')),
            market_value=data.get('market_value', 10000),
            weeks_unemployed=data.get('weeks_unemployed', 0),
            
            market_value_history=mv_history,
            last_value_calculation=data.get('last_value_calculation'),
            
            average_match_rating=data.get('average_match_rating', 3.0),
            recent_match_rating=data.get('recent_match_rating', 3.0),
            five_star_matches=data.get('five_star_matches', 0),
            four_plus_matches=data.get('four_plus_matches', 0),
            
            injury_history_count=data.get('injury_history_count', 0),
            months_since_last_injury=data.get('months_since_last_injury', 12),
            has_chronic_issues=data.get('has_chronic_issues', False),
            
            backstage_reputation=data.get('backstage_reputation', 50),
            locker_room_leader=data.get('locker_room_leader', False),
            known_difficult=data.get('known_difficult', False),
            
            agent=AgentInfo.from_dict(data['agent']) if data.get('agent') else None,
            demands=ContractDemands.from_dict(data['demands']) if data.get('demands') else None,
            rival_interest=rival_interest,
            contract_history=[ContractHistory.from_dict(h) for h in data.get('contract_history', [])],
            
            has_controversy=data.get('has_controversy', False),
            controversy_type=data.get('controversy_type'),
            controversy_severity=data.get('controversy_severity', 0),
            time_since_incident_weeks=data.get('time_since_incident_weeks', 0),
            
            is_legend=data.get('is_legend', False),
            retirement_status=data.get('retirement_status', 'active'),
            comeback_likelihood=data.get('comeback_likelihood', 50),
            
            origin_region=data.get('origin_region', 'domestic'),
            requires_visa=data.get('requires_visa', False),
            exclusive_willing=data.get('exclusive_willing', True),
            
            is_prospect=data.get('is_prospect', False),
            training_investment_needed=data.get('training_investment_needed', 0),
            ceiling_potential=data.get('ceiling_potential', 50),
            
            available_from_year=data.get('available_from_year', 1),
            available_from_week=data.get('available_from_week', 1),
            no_compete_until_year=data.get('no_compete_until_year'),
            no_compete_until_week=data.get('no_compete_until_week'),
            
            exclusive_window_active=ew_data.get('active', data.get('exclusive_window_active', False)),
            exclusive_window_holder=ew_data.get('holder', data.get('exclusive_window_holder')),
            exclusive_window_holder_name=ew_data.get('holder_name', data.get('exclusive_window_holder_name')),
            exclusive_window_cost_paid=ew_data.get('cost_paid', data.get('exclusive_window_cost_paid', 0)),
            exclusive_window_duration=ew_data.get('duration', data.get('exclusive_window_duration', 0)),
            exclusive_window_started_year=ew_data.get('started_year', data.get('exclusive_window_started_year')),
            exclusive_window_started_week=ew_data.get('started_week', data.get('exclusive_window_started_week')),
            exclusive_window_expires_year=ew_data.get('expires_year', data.get('exclusive_window_expires_year')),
            exclusive_window_expires_week=ew_data.get('expires_week', data.get('exclusive_window_expires_week')),
            exclusive_window_id=ew_data.get('id', data.get('exclusive_window_id')),
            exclusive_window_resulted_in_signing=ew_data.get('resulted_in_signing', data.get('exclusive_window_resulted_in_signing', False)),
            
            discovered=data.get('discovered', False),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )
    
    @staticmethod
    def from_wrestler(wrestler, source: FreeAgentSource, year: int, week: int) -> 'FreeAgent':
        """Create FreeAgent from an existing Wrestler object"""
        free_agent_id = f"fa_{wrestler.id}_{year}_{week}"
        
        if wrestler.is_major_superstar or wrestler.popularity >= 80:
            visibility = FreeAgentVisibility.HEADLINE_NEWS
        elif wrestler.popularity >= 60 or wrestler.role in ['Main Event', 'Upper Midcard']:
            visibility = FreeAgentVisibility.INDUSTRY_BUZZ
        elif wrestler.popularity >= 40:
            visibility = FreeAgentVisibility.HIDDEN_GEM
        else:
            visibility = FreeAgentVisibility.DEEP_CUT
        
        if source == FreeAgentSource.RELEASED:
            mood = FreeAgentMood.BITTER if random.random() < 0.4 else FreeAgentMood.HUNGRY
        elif source == FreeAgentSource.CONTRACT_EXPIRED:
            mood = FreeAgentMood.PATIENT
        else:
            mood = FreeAgentMood.PATIENT
        
        base_salary = 5000 + wrestler.popularity * 100 + wrestler.overall_rating * 50
        
        role_multipliers = {
            'Main Event': 2.0,
            'Upper Midcard': 1.5,
            'Midcard': 1.0,
            'Lower Midcard': 0.7,
            'Jobber': 0.5
        }
        base_salary = int(base_salary * role_multipliers.get(wrestler.role, 1.0))
        
        if wrestler.is_major_superstar:
            base_salary = int(base_salary * 1.5)
        
        demands = ContractDemands(
            minimum_salary=int(base_salary * 0.7),
            asking_salary=base_salary,
            preferred_length_weeks=52 if wrestler.age < 35 else 26,
            creative_control_level=2 if wrestler.is_major_superstar else 0,
            title_guarantee_weeks=26 if wrestler.role == 'Main Event' else 0
        )
        
        return FreeAgent(
            free_agent_id=free_agent_id,
            wrestler_id=wrestler.id,
            wrestler_name=wrestler.name,
            
            age=wrestler.age,
            gender=wrestler.gender,
            alignment=wrestler.alignment,
            role=wrestler.role,
            
            brawling=wrestler.brawling,
            technical=wrestler.technical,
            speed=wrestler.speed,
            mic=wrestler.mic,
            psychology=wrestler.psychology,
            stamina=wrestler.stamina,
            
            years_experience=wrestler.years_experience,
            is_major_superstar=wrestler.is_major_superstar,
            popularity=wrestler.popularity,
            peak_popularity=wrestler.popularity,
            
            source=source,
            visibility=visibility,
            mood=mood,
            market_value=base_salary,
            weeks_unemployed=0,
            
            average_match_rating=getattr(wrestler, 'average_match_rating', 3.0),
            recent_match_rating=getattr(wrestler, 'recent_match_rating', 3.0),
            five_star_matches=getattr(wrestler, 'five_star_matches', 0),
            four_plus_matches=getattr(wrestler, 'four_plus_matches', 0),
            
            injury_history_count=getattr(wrestler, 'injury_history_count', 0),
            months_since_last_injury=12 if not wrestler.is_injured else 0,
            has_chronic_issues=False,
            
            backstage_reputation=max(30, min(80, 50 + (wrestler.morale - 50) // 2)),
            locker_room_leader=wrestler.years_experience >= 15 and wrestler.morale >= 70,
            known_difficult=wrestler.morale < 30,
            
            demands=demands,
            
            is_legend=wrestler.is_major_superstar and wrestler.age >= 40,
            
            available_from_year=year,
            available_from_week=week
        )
    
    def __repr__(self):
        return f"<FreeAgent {self.wrestler_name} ({self.source_label}, {self.mood_label}, ${self.market_value:,})>"