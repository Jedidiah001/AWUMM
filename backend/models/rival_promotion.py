"""
Rival Promotion Model
STEP 126: Rival Promotion Interest Generation

Models competing promotions that bid for free agents,
compete for talent, and react to your signings.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum
import random


class RivalPromotionTier(Enum):
    """Size/prestige tier of rival promotion"""
    MAJOR = "major"          # WWE/AEW level - huge budget, global reach
    REGIONAL = "regional"    # ROH/NXT level - solid mid-tier
    INDIE = "indie"          # Small indie - low budget, niche appeal


class RivalBrandIdentity(Enum):
    """What kind of wrestling does this promotion run"""
    SPORTS_ENTERTAINMENT = "sports_entertainment"   # Spectacle, character-driven
    PURE_WRESTLING = "pure_wrestling"               # Technical, match-focused
    HARDCORE = "hardcore"                           # Extreme, violent
    LUCHA = "lucha"                                 # High-flying, lucha style
    STRONG_STYLE = "strong_style"                   # Hard-hitting, Japanese style
    MIXED = "mixed"                                 # Diverse styles


@dataclass
class RivalPromotion:
    """
    A competing wrestling promotion that signs free agents
    and competes for talent.

    Budget and roster needs determine which free agents they
    pursue and how aggressively they bid.
    """
    promotion_id: str
    name: str
    abbreviation: str           # e.g. "GWF", "APW"
    tier: RivalPromotionTier
    brand_identity: RivalBrandIdentity

    # Financials
    budget_per_year: int        # Annual talent budget
    remaining_budget: int       # What's left to spend
    avg_salary_per_show: int    # Their typical offer

    # Roster profile
    roster_size: int            # Current roster headcount
    max_roster_size: int        # Won't sign beyond this
    roster_needs: List[str]     # Roles they're actively recruiting: 'Main Event', etc.
    gender_focus: str           # 'male', 'female', 'both'

    # Personality/strategy
    aggression: int             # 0-100: how hard they pursue targets
    loyalty_to_talent: int      # 0-100: how well they treat signed talent
    prestige: int               # 0-100: how attractive they are to sign with
    relationship_with_player: int  # 0-100: diplomatic standing

    # Tracking
    active_pursuits: List[str] = field(default_factory=list)   # fa_ids currently pursuing
    signed_this_year: int = 0
    lost_bidding_wars: int = 0
    won_bidding_wars: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'promotion_id': self.promotion_id,
            'name': self.name,
            'abbreviation': self.abbreviation,
            'tier': self.tier.value,
            'brand_identity': self.brand_identity.value,
            'budget_per_year': self.budget_per_year,
            'remaining_budget': self.remaining_budget,
            'avg_salary_per_show': self.avg_salary_per_show,
            'roster_size': self.roster_size,
            'max_roster_size': self.max_roster_size,
            'roster_needs': self.roster_needs,
            'gender_focus': self.gender_focus,
            'aggression': self.aggression,
            'loyalty_to_talent': self.loyalty_to_talent,
            'prestige': self.prestige,
            'relationship_with_player': self.relationship_with_player,
            'active_pursuits': self.active_pursuits,
            'signed_this_year': self.signed_this_year,
            'lost_bidding_wars': self.lost_bidding_wars,
            'won_bidding_wars': self.won_bidding_wars
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'RivalPromotion':
        return RivalPromotion(
            promotion_id=data['promotion_id'],
            name=data['name'],
            abbreviation=data['abbreviation'],
            tier=RivalPromotionTier(data['tier']),
            brand_identity=RivalBrandIdentity(data['brand_identity']),
            budget_per_year=data['budget_per_year'],
            remaining_budget=data['remaining_budget'],
            avg_salary_per_show=data['avg_salary_per_show'],
            roster_size=data['roster_size'],
            max_roster_size=data['max_roster_size'],
            roster_needs=data.get('roster_needs', []),
            gender_focus=data.get('gender_focus', 'both'),
            aggression=data.get('aggression', 50),
            loyalty_to_talent=data.get('loyalty_to_talent', 50),
            prestige=data.get('prestige', 50),
            relationship_with_player=data.get('relationship_with_player', 50),
            active_pursuits=data.get('active_pursuits', []),
            signed_this_year=data.get('signed_this_year', 0),
            lost_bidding_wars=data.get('lost_bidding_wars', 0),
            won_bidding_wars=data.get('won_bidding_wars', 0)
        )

    def can_afford(self, salary_per_show: int, contract_weeks: int = 52) -> bool:
        """Check if promotion can afford a contract"""
        shows_per_week = 3  # Estimate
        annual_cost = salary_per_show * shows_per_week * 52
        return annual_cost <= self.remaining_budget

    def calculate_interest_level(self, free_agent) -> int:
        """
        Calculate 0-100 interest level in a specific free agent.

        Factors:
        - Roster need for their role
        - Gender alignment
        - Budget fit
        - Brand identity match
        - Promotion prestige vs wrestler popularity
        """
        interest = 0

        # Role need (biggest factor)
        if free_agent.role in self.roster_needs:
            interest += 40
        elif 'Midcard' in self.roster_needs and free_agent.role in ['Midcard', 'Lower Midcard']:
            interest += 20
        else:
            interest += 10

        # Gender alignment
        if self.gender_focus == 'both':
            interest += 15
        elif self.gender_focus == free_agent.gender.lower():
            interest += 20
        else:
            interest += 0  # Wrong gender focus

        # Budget fit
        estimated_ask = free_agent.demands.asking_salary
        if self.can_afford(estimated_ask):
            interest += 20
        elif self.can_afford(int(estimated_ask * 0.8)):
            interest += 10
        else:
            interest -= 20  # Can't afford them

        # Popularity/prestige fit
        pop_diff = free_agent.popularity - self.prestige
        if abs(pop_diff) <= 20:
            interest += 15  # Good fit
        elif pop_diff > 40:
            interest -= 10  # Too big a star for them
        else:
            interest += 5

        # Roster size limit
        if self.roster_size >= self.max_roster_size:
            interest -= 50  # Roster full

        # Aggression modifier
        interest = int(interest * (0.5 + self.aggression / 200))

        return max(0, min(100, interest))

    def generate_offer_salary(self, free_agent, interest_level: int) -> int:
        """
        Generate the salary this promotion would offer.

        Higher interest = closer to wrestler's asking price.
        Budget constraints cap the maximum.
        """
        asking = free_agent.demands.asking_salary

        if interest_level >= 80:
            offer_pct = random.uniform(0.90, 1.05)  # 90-105% of asking
        elif interest_level >= 60:
            offer_pct = random.uniform(0.75, 0.92)  # 75-92%
        elif interest_level >= 40:
            offer_pct = random.uniform(0.60, 0.80)  # 60-80%
        else:
            offer_pct = random.uniform(0.50, 0.70)  # 50-70% (lowball)

        # Prestige adjustment - lower prestige promotions pay more to compensate
        if self.prestige < 40:
            offer_pct *= 1.10

        raw_offer = int(asking * offer_pct)

        # Round to nearest $500
        raw_offer = round(raw_offer / 500) * 500

        return max(3000, raw_offer)


# ============================================================
# DEFAULT RIVAL PROMOTIONS
# ============================================================

DEFAULT_RIVAL_PROMOTIONS = [
    RivalPromotion(
        promotion_id="rival_gwf",
        name="Global Wrestling Federation",
        abbreviation="GWF",
        tier=RivalPromotionTier.MAJOR,
        brand_identity=RivalBrandIdentity.SPORTS_ENTERTAINMENT,
        budget_per_year=5_000_000,
        remaining_budget=5_000_000,
        avg_salary_per_show=15000,
        roster_size=60,
        max_roster_size=80,
        roster_needs=["Main Event", "Upper Midcard"],
        gender_focus="both",
        aggression=80,
        loyalty_to_talent=55,
        prestige=85,
        relationship_with_player=40
    ),
    RivalPromotion(
        promotion_id="rival_apw",
        name="All-Pro Wrestling",
        abbreviation="APW",
        tier=RivalPromotionTier.REGIONAL,
        brand_identity=RivalBrandIdentity.PURE_WRESTLING,
        budget_per_year=1_500_000,
        remaining_budget=1_500_000,
        avg_salary_per_show=7000,
        roster_size=30,
        max_roster_size=45,
        roster_needs=["Midcard", "Upper Midcard", "Main Event"],
        gender_focus="both",
        aggression=60,
        loyalty_to_talent=75,
        prestige=60,
        relationship_with_player=55
    ),
    RivalPromotion(
        promotion_id="rival_dynasty",
        name="Dynasty Pro Wrestling",
        abbreviation="DPW",
        tier=RivalPromotionTier.REGIONAL,
        brand_identity=RivalBrandIdentity.MIXED,
        budget_per_year=800_000,
        remaining_budget=800_000,
        avg_salary_per_show=5000,
        roster_size=25,
        max_roster_size=35,
        roster_needs=["Midcard", "Lower Midcard", "Upper Midcard"],
        gender_focus="male",
        aggression=45,
        loyalty_to_talent=65,
        prestige=45,
        relationship_with_player=60
    ),
    RivalPromotion(
        promotion_id="rival_lucha_elite",
        name="Lucha Elite",
        abbreviation="LE",
        tier=RivalPromotionTier.REGIONAL,
        brand_identity=RivalBrandIdentity.LUCHA,
        budget_per_year=600_000,
        remaining_budget=600_000,
        avg_salary_per_show=4000,
        roster_size=20,
        max_roster_size=30,
        roster_needs=["Midcard", "Lower Midcard"],
        gender_focus="both",
        aggression=40,
        loyalty_to_talent=70,
        prestige=40,
        relationship_with_player=65
    ),
]