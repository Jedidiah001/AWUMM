"""
Loyalty System — Steps 208-223

Step 208: Loyalty Score Calculation for active roster members
Step 209: Loyalty Tiers and their effects on renewal negotiations
Step 210: Holdout Mechanics — unhappy wrestlers refusing to work
Step 211: Contract Dispute Escalation
Step 212: Tampering Mechanics — rival promotions illegally approaching your talent
Step 213: Tampering detection and counter-measures
Step 214: Loyalty bonuses — rewarding tenure
Step 215: Failed Negotiation Consequences
Step 216: Public fallout from failed negotiations
Step 217: Second chance / re-approach windows
Step 218: Wrestler-initiated free agency (opting out)
Step 219: Exclusive negotiating windows for re-signing
Step 220: Multi-year loyalty incentives
Step 221: Historical relationship modifier for returning wrestlers
Step 222: Free agency bidding war loyalty exception
Step 223: Surprise return mechanics for wrestlers who previously left
"""

import random
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


# ============================================================================
# STEP 208: Loyalty Score
# ============================================================================

def calculate_loyalty_score(
    years_with_promotion: float,
    morale: int,
    was_champion: bool,
    was_pushed_consistently: bool,
    had_contract_dispute: bool,
    had_wellness_strike: bool,
    paid_above_market: bool,
) -> int:
    """
    Step 208: 0-100 loyalty score for a current roster member.
    Feeds into renewal probability, holdout risk, and tampering vulnerability.
    """
    score = 40  # Neutral baseline

    # Tenure (capped at 10 years for scoring purposes)
    score += min(20, int(years_with_promotion * 2))

    # Morale: strong driver of loyalty
    score += int((morale - 50) * 0.4)

    # Positive career experiences
    if was_champion:           score += 10
    if was_pushed_consistently: score += 8
    if paid_above_market:       score += 8

    # Negative history
    if had_contract_dispute:   score -= 15
    if had_wellness_strike:    score -= 8

    return max(0, min(100, score))


# ============================================================================
# STEP 209: Loyalty Tiers
# ============================================================================

class LoyaltyTier(Enum):
    DISGRUNTLED  = "disgruntled"    # 0-20:  actively looking to leave
    INDIFFERENT  = "indifferent"    # 21-40: open to leaving if the offer is right
    CONTENT      = "content"        # 41-60: happy but not resistant to offers
    LOYAL        = "loyal"          # 61-80: prefers to stay, needs incentive to leave
    DEVOTED      = "devoted"        # 81-100: would take below-market to stay

    @property
    def label(self) -> str:
        return self.value.title()

    @property
    def renewal_discount(self) -> float:
        """
        How far below market they'll accept for a renewal offer.
        Positive = discount possible, negative = premium required.
        """
        discounts = {
            "disgruntled":  -0.20,   # Needs 20% above market to stay
            "indifferent":  -0.10,
            "content":       0.00,
            "loyal":         0.08,   # Will accept 8% below market
            "devoted":       0.18,   # Will accept 18% below market
        }
        return discounts[self.value]

    @property
    def tampering_vulnerability(self) -> int:
        """0-100: how susceptible to rival poaching."""
        vulns = {
            "disgruntled":  90,
            "indifferent":  65,
            "content":      40,
            "loyal":        20,
            "devoted":      5,
        }
        return vulns[self.value]

    @property
    def holdout_risk(self) -> int:
        """0-100: probability of refusing to work during contract dispute."""
        risks = {
            "disgruntled":  70,
            "indifferent":  40,
            "content":      15,
            "loyal":        5,
            "devoted":      0,
        }
        return risks[self.value]

    @property
    def description(self) -> str:
        descs = {
            "disgruntled": "Actively unhappy. Looking for an exit. Every rival offer is a temptation.",
            "indifferent": "No strong emotional connection to the promotion. Will leave if the money is right.",
            "content":     "Happy with their situation but hasn't built deep loyalty. Standard market offers required.",
            "loyal":       "Prefers to stay. A modest below-market offer may be accepted to avoid disruption.",
            "devoted":     "Deep roots here. Would take a meaningful pay cut to stay rather than start over.",
        }
        return descs[self.value]

    @staticmethod
    def from_score(score: int) -> "LoyaltyTier":
        if score >= 81: return LoyaltyTier.DEVOTED
        if score >= 61: return LoyaltyTier.LOYAL
        if score >= 41: return LoyaltyTier.CONTENT
        if score >= 21: return LoyaltyTier.INDIFFERENT
        return LoyaltyTier.DISGRUNTLED


# ============================================================================
# STEP 210-211: Holdout Mechanics
# ============================================================================

class HoldoutStatus(Enum):
    NONE       = "none"       # Not in a holdout
    THREATENED = "threatened" # Wrestler has mentioned the possibility
    ACTIVE     = "active"     # Actively refusing scheduled appearances
    RESOLVED   = "resolved"   # Holdout ended (positively or with release)

    @property
    def label(self) -> str:
        return self.value.title()


@dataclass
class HoldoutSituation:
    """
    Step 210: A wrestler refusing to work during a contract dispute.
    Resolved by meeting demands, releasing the wrestler, or mediation.
    """
    wrestler_id:       str  = ""
    wrestler_name:     str  = ""
    status:            HoldoutStatus = HoldoutStatus.NONE
    weeks_in_holdout:  int  = 0
    original_demand:   int  = 0    # Salary they want (per show)
    current_offer:     int  = 0    # Your current offer
    minimum_to_end:    int  = 0    # Minimum that would end the holdout

    # Step 211: Escalation tracking
    media_leaks:       int  = 0    # How many times the dispute hit the press
    fan_reaction:      str  = "mixed"
    locker_room_aware: bool = False

    def weekly_cost_to_promotion(self) -> int:
        """Shows missed × estimated gate + merchandise impact."""
        return random.randint(8000, 25000)

    def escalation_risk_per_week(self) -> int:
        """0-100: chance of the dispute escalating further each week."""
        base = 20 + self.weeks_in_holdout * 5
        if self.media_leaks >= 2: base += 20
        return min(90, base)

    def advance_week(self) -> Dict[str, Any]:
        self.weeks_in_holdout += 1
        events = []

        # Random escalation
        if random.randint(1, 100) <= self.escalation_risk_per_week():
            event = random.choice([
                "Story leaked to wrestling press — fan debate intensifying.",
                "Wrestler skipped live event — noticed by fans.",
                "Agent issued statement demanding resolution.",
                "Social media cryptic post by wrestler fuels speculation.",
            ])
            events.append(event)
            self.media_leaks += 1
            if not self.locker_room_aware:
                self.locker_room_aware = True

        return {
            "weeks_in_holdout": self.weeks_in_holdout,
            "cost_this_week":   self.weekly_cost_to_promotion(),
            "events":           events,
            "escalation_risk":  self.escalation_risk_per_week(),
        }

    def resolve_with_deal(self, agreed_salary: int) -> Dict[str, Any]:
        self.status = HoldoutStatus.RESOLVED
        fan_sentiment = "positive" if agreed_salary >= self.minimum_to_end else "mixed"
        return {
            "resolved":       True,
            "agreed_salary":  agreed_salary,
            "fan_sentiment":  fan_sentiment,
            "morale_change":  10 if agreed_salary >= self.original_demand else -5,
            "message": (
                f"{self.wrestler_name} ends holdout — agreed at ${agreed_salary:,}/show. "
                + ("Both sides satisfied." if agreed_salary >= self.minimum_to_end
                   else "Wrestler accepted reluctantly.")
            ),
        }

    def resolve_with_release(self) -> Dict[str, Any]:
        self.status = HoldoutStatus.RESOLVED
        return {
            "resolved":      True,
            "released":      True,
            "morale_change": -15,   # Rest of roster demoralised
            "message":       f"{self.wrestler_name} released after holdout could not be resolved.",
            "pr_damage":     self.media_leaks * 5,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "wrestler_id":        self.wrestler_id,
            "wrestler_name":      self.wrestler_name,
            "status":             self.status.value,
            "status_label":       self.status.label,
            "weeks_in_holdout":   self.weeks_in_holdout,
            "original_demand":    self.original_demand,
            "current_offer":      self.current_offer,
            "minimum_to_end":     self.minimum_to_end,
            "gap":                max(0, self.minimum_to_end - self.current_offer),
            "media_leaks":        self.media_leaks,
            "fan_reaction":       self.fan_reaction,
            "locker_room_aware":  self.locker_room_aware,
            "weekly_cost":        self.weekly_cost_to_promotion(),
            "escalation_risk":    self.escalation_risk_per_week(),
        }


# ============================================================================
# STEP 212-213: Tampering Mechanics
# ============================================================================

class TamperingIntensity(Enum):
    FEELERS    = "feelers"      # Casual indirect interest
    CONTACT    = "contact"      # Direct contact with wrestler's agent
    OFFER      = "offer"        # Formal (illegal) offer made
    AGGRESSIVE = "aggressive"   # Repeated approaches, pressure campaign

    @property
    def label(self) -> str:
        return self.value.title()

    @property
    def detection_difficulty(self) -> int:
        """0-100; higher = harder to catch."""
        difficulties = {"feelers": 80, "contact": 60, "offer": 40, "aggressive": 20}
        return difficulties[self.value]

    @property
    def loyalty_erosion_per_week(self) -> int:
        """How many loyalty score points are lost per week of this activity."""
        erosion = {"feelers": 1, "contact": 3, "offer": 6, "aggressive": 10}
        return erosion[self.value]


@dataclass
class TamperingIncident:
    """
    Step 212: A rival promotion illegally approaching one of your wrestlers.
    """
    promotion_id:     str              = ""
    promotion_name:   str              = ""
    wrestler_id:      str              = ""
    wrestler_name:    str              = ""
    intensity:        TamperingIntensity = TamperingIntensity.FEELERS
    detected:         bool             = False
    reported_to_board: bool            = False
    weeks_ongoing:    int              = 0

    # Step 213: Counter-measures applied
    counter_measure_applied: Optional[str] = None   # "loyalty_bonus"|"meeting"|"media_statement"

    def detection_roll(self) -> bool:
        """Step 213: Roll to see if tampering is detected this week."""
        roll = random.randint(1, 100)
        base_chance = 100 - self.intensity.detection_difficulty
        detected = roll <= base_chance
        if detected:
            self.detected = True
        return detected

    def apply_counter_measure(self, measure: str, loyalty_score: int) -> Dict[str, Any]:
        """Step 213: Apply a counter-measure to resist tampering."""
        self.counter_measure_applied = measure

        effects = {
            "loyalty_bonus": {
                "loyalty_change":  10,
                "tampering_effectiveness_reduction": 30,
                "cost":           15000,
                "message":        f"Loyalty bonus paid to {self.wrestler_name} — rival approach less effective.",
            },
            "meeting": {
                "loyalty_change":  5,
                "tampering_effectiveness_reduction": 20,
                "cost":           0,
                "message":        f"Personal meeting with {self.wrestler_name} reinforced commitment.",
            },
            "media_statement": {
                "loyalty_change":  0,
                "tampering_effectiveness_reduction": 15,
                "cost":           5000,
                "message":        f"Public statement deterred {self.promotion_name} from further approaches.",
            },
            "legal_threat": {
                "loyalty_change":  -3,
                "tampering_effectiveness_reduction": 50,
                "cost":           10000,
                "message":        f"Legal threat sent to {self.promotion_name}. Aggressive but effective.",
            },
        }

        return effects.get(measure, {
            "loyalty_change": 0,
            "tampering_effectiveness_reduction": 0,
            "cost": 0,
            "message": "Counter-measure applied.",
        })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "promotion_id":     self.promotion_id,
            "promotion_name":   self.promotion_name,
            "wrestler_id":      self.wrestler_id,
            "wrestler_name":    self.wrestler_name,
            "intensity":        self.intensity.value,
            "intensity_label":  self.intensity.label,
            "detected":         self.detected,
            "reported_to_board": self.reported_to_board,
            "weeks_ongoing":    self.weeks_ongoing,
            "loyalty_erosion_per_week": self.intensity.loyalty_erosion_per_week,
            "counter_measure_applied":  self.counter_measure_applied,
        }


# ============================================================================
# STEP 214: Loyalty Bonus Rewards
# ============================================================================

@dataclass
class LoyaltyBonus:
    """
    Step 214: Reward long-tenured roster members to build goodwill.
    Can be monetary, creative, or tenure milestone-based.
    """
    wrestler_id:   str = ""
    wrestler_name: str = ""
    bonus_type:    str = "monetary"   # "monetary"|"creative"|"title_push"|"tenure_award"
    amount:        int = 0            # For monetary bonuses
    loyalty_gain:  int = 0            # Loyalty score points gained
    morale_gain:   int = 0            # Morale points gained
    description:   str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "wrestler_id":   self.wrestler_id,
            "wrestler_name": self.wrestler_name,
            "bonus_type":    self.bonus_type,
            "amount":        self.amount,
            "loyalty_gain":  self.loyalty_gain,
            "morale_gain":   self.morale_gain,
            "description":   self.description,
        }

    @staticmethod
    def generate_tenure_award(
        wrestler_id: str,
        wrestler_name: str,
        years_with_promotion: float,
    ) -> "LoyaltyBonus":
        """Step 214: Milestone rewards at 1, 2, 5, 10 year marks."""
        if years_with_promotion >= 10:
            return LoyaltyBonus(
                wrestler_id=wrestler_id, wrestler_name=wrestler_name,
                bonus_type="tenure_award", amount=100_000,
                loyalty_gain=15, morale_gain=20,
                description=f"10-Year Loyalty Award — {wrestler_name} is a cornerstone of this promotion.",
            )
        if years_with_promotion >= 5:
            return LoyaltyBonus(
                wrestler_id=wrestler_id, wrestler_name=wrestler_name,
                bonus_type="tenure_award", amount=50_000,
                loyalty_gain=10, morale_gain=15,
                description=f"5-Year Loyalty Award — {wrestler_name} has proven their commitment.",
            )
        if years_with_promotion >= 2:
            return LoyaltyBonus(
                wrestler_id=wrestler_id, wrestler_name=wrestler_name,
                bonus_type="tenure_award", amount=20_000,
                loyalty_gain=5, morale_gain=8,
                description=f"2-Year Loyalty Award — {wrestler_name} is becoming a fixture on the roster.",
            )
        return LoyaltyBonus(
            wrestler_id=wrestler_id, wrestler_name=wrestler_name,
            bonus_type="tenure_award", amount=5_000,
            loyalty_gain=3, morale_gain=5,
            description=f"1-Year Recognition — {wrestler_name} has completed their first year.",
        )


# ============================================================================
# STEP 215-216: Failed Negotiation Consequences
# ============================================================================

class FailedNegotiationConsequence(Enum):
    WALKS_TO_RIVAL        = "walks_to_rival"         # Signs with competing promotion
    ENTERS_HOLDOUT        = "enters_holdout"          # Refuses to work
    DEMANDS_PUBLIC_TRADE  = "demands_public_trade"    # Publicly requests to move
    ACCEPTS_GRUDGINGLY    = "accepts_grudgingly"      # Signs but morale tanks
    RETIRES_PREMATURELY   = "retires_prematurely"     # Walks away from the business

    @property
    def label(self) -> str:
        return self.value.replace("_", " ").title()

    @property
    def severity(self) -> str:
        sev = {
            "walks_to_rival":       "critical",
            "enters_holdout":       "high",
            "demands_public_trade": "high",
            "accepts_grudgingly":   "moderate",
            "retires_prematurely":  "critical",
        }
        return sev[self.value]


def determine_failed_negotiation_consequence(
    loyalty_tier: LoyaltyTier,
    morale: int,
    age: int,
    rival_offers_exist: bool,
    weeks_until_contract_expires: int,
) -> FailedNegotiationConsequence:
    """
    Step 215: What happens when a contract negotiation breaks down?
    """
    # Weighted random by situation
    if loyalty_tier == LoyaltyTier.DISGRUNTLED:
        if rival_offers_exist:
            return FailedNegotiationConsequence.WALKS_TO_RIVAL
        if morale < 20:
            return FailedNegotiationConsequence.ENTERS_HOLDOUT
        return random.choice([
            FailedNegotiationConsequence.DEMANDS_PUBLIC_TRADE,
            FailedNegotiationConsequence.ENTERS_HOLDOUT,
        ])

    if loyalty_tier == LoyaltyTier.INDIFFERENT:
        if rival_offers_exist and random.random() < 0.6:
            return FailedNegotiationConsequence.WALKS_TO_RIVAL
        return random.choice([
            FailedNegotiationConsequence.ACCEPTS_GRUDGINGLY,
            FailedNegotiationConsequence.DEMANDS_PUBLIC_TRADE,
        ])

    if loyalty_tier in (LoyaltyTier.CONTENT, LoyaltyTier.LOYAL):
        if age >= 40 and weeks_until_contract_expires <= 4:
            # Older, contract almost up — may retire rather than fight
            return FailedNegotiationConsequence.RETIRES_PREMATURELY
        return FailedNegotiationConsequence.ACCEPTS_GRUDGINGLY

    # Devoted — very unlikely to do anything drastic
    return FailedNegotiationConsequence.ACCEPTS_GRUDGINGLY


def generate_public_fallout_narrative(
    consequence: FailedNegotiationConsequence,
    wrestler_name: str,
    promotion_name: str = "Ring of Champions",
) -> Dict[str, Any]:
    """Step 216: Generate the PR / narrative consequences of a failed negotiation."""
    narratives = {
        FailedNegotiationConsequence.WALKS_TO_RIVAL: {
            "headline":        f"BREAKING: {wrestler_name} signs with rival promotion",
            "fan_reaction":    "shocked",
            "media_heat":      "high",
            "morale_impact":   -12,
            "pr_response_options": [
                "Wish them well publicly (costs nothing, minimal fallout)",
                "No comment (safe but looks weak)",
                "Dispute their version of events (risky but may salvage narrative)",
            ],
        },
        FailedNegotiationConsequence.ENTERS_HOLDOUT: {
            "headline":        f"Reports: {wrestler_name} in dispute with {promotion_name}",
            "fan_reaction":    "mixed",
            "media_heat":      "high",
            "morale_impact":   -8,
            "pr_response_options": [
                "Issue joint statement promising resolution",
                "Book them off TV with kayfabe injury",
                "Remove them from advertising immediately",
            ],
        },
        FailedNegotiationConsequence.DEMANDS_PUBLIC_TRADE: {
            "headline":        f"{wrestler_name} reportedly requests release from {promotion_name}",
            "fan_reaction":    "concerned",
            "media_heat":      "moderate",
            "morale_impact":   -5,
            "pr_response_options": [
                "Grant request quietly (minimal damage)",
                "Deny request publicly (escalates tension)",
                "Offer trade to another brand as compromise",
            ],
        },
        FailedNegotiationConsequence.ACCEPTS_GRUDGINGLY: {
            "headline":        f"{wrestler_name} re-signs with {promotion_name}",
            "fan_reaction":    "positive",
            "media_heat":      "low",
            "morale_impact":   -5,   # Signed but unhappy
            "pr_response_options": [
                "Announce signing with positive spin (recommended)",
                "No announcement — let it develop organically",
            ],
        },
        FailedNegotiationConsequence.RETIRES_PREMATURELY: {
            "headline":        f"{wrestler_name} announces sudden retirement",
            "fan_reaction":    "saddened",
            "media_heat":      "moderate",
            "morale_impact":   -8,
            "pr_response_options": [
                "Organise farewell appearance (goodwill with fans)",
                "Issue statement thanking their contributions",
            ],
        },
    }
    return narratives.get(consequence, {
        "headline": f"Contract dispute with {wrestler_name} resolved",
        "fan_reaction": "neutral",
        "media_heat": "low",
        "morale_impact": 0,
        "pr_response_options": [],
    })


# ============================================================================
# STEP 217-219: Re-approach Windows and Exclusive Signing Windows
# ============================================================================

@dataclass
class ReApproachWindow:
    """
    Step 217: After a failed negotiation, when can you try again?
    """
    wrestler_id:     str = ""
    wrestler_name:   str = ""
    blocked_until_week:  int = 0
    blocked_until_year:  int = 1
    cooldown_reason: str = ""   # Why the window is closed
    goodwill_actions_taken: List[str] = field(default_factory=list)

    def is_open(self, current_year: int, current_week: int) -> bool:
        if current_year > self.blocked_until_year:
            return True
        if current_year == self.blocked_until_year:
            return current_week >= self.blocked_until_week
        return False

    def weeks_until_open(self, current_year: int, current_week: int) -> int:
        if self.is_open(current_year, current_week):
            return 0
        year_diff = self.blocked_until_year - current_year
        return max(0, year_diff * 52 + self.blocked_until_week - current_week)

    def take_goodwill_action(self, action: str) -> Dict[str, Any]:
        """
        Step 217: Rebuild goodwill to re-open the window sooner.
        """
        self.goodwill_actions_taken.append(action)
        weeks_reduced = 0
        effects = {
            "public_apology":    4,
            "tribute_video":     2,
            "mutual_friend":     3,
            "public_praise":     2,
            "hall_of_fame_hint": 6,
        }
        weeks_reduced = effects.get(action, 1)
        self.blocked_until_week = max(0, self.blocked_until_week - weeks_reduced)
        return {
            "action":        action,
            "weeks_reduced": weeks_reduced,
            "new_open_week": self.blocked_until_week,
            "new_open_year": self.blocked_until_year,
            "message": f"Goodwill action '{action}' shortens re-approach window by {weeks_reduced} week(s).",
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "wrestler_id":          self.wrestler_id,
            "wrestler_name":        self.wrestler_name,
            "blocked_until_week":   self.blocked_until_week,
            "blocked_until_year":   self.blocked_until_year,
            "cooldown_reason":      self.cooldown_reason,
            "goodwill_actions":     self.goodwill_actions_taken,
        }


@dataclass
class ExclusiveNegotiatingWindow:
    """
    Step 219: A time-limited window where you and a wrestler negotiate
    without rival promotions making offers.
    Typically 8 weeks — granted for contract extensions with 12 weeks remaining.
    """
    wrestler_id:      str  = ""
    wrestler_name:    str  = ""
    opens_week:       int  = 0
    opens_year:       int  = 1
    expires_week:     int  = 0
    expires_year:     int  = 1
    window_weeks:     int  = 8
    offer_made:       bool = False
    offer_accepted:   bool = False

    def is_active(self, current_year: int, current_week: int) -> bool:
        if current_year < self.opens_year:
            return False
        if current_year == self.opens_year and current_week < self.opens_week:
            return False
        if current_year > self.expires_year:
            return False
        if current_year == self.expires_year and current_week > self.expires_week:
            return False
        return True

    def weeks_remaining(self, current_year: int, current_week: int) -> int:
        if not self.is_active(current_year, current_week):
            return 0
        year_diff  = self.expires_year - current_year
        return max(0, year_diff * 52 + self.expires_week - current_week)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "wrestler_id":   self.wrestler_id,
            "wrestler_name": self.wrestler_name,
            "opens_week":    self.opens_week,
            "opens_year":    self.opens_year,
            "expires_week":  self.expires_week,
            "expires_year":  self.expires_year,
            "window_weeks":  self.window_weeks,
            "offer_made":    self.offer_made,
            "offer_accepted": self.offer_accepted,
        }


# ============================================================================
# STEP 220: Multi-Year Loyalty Incentives
# ============================================================================

@dataclass
class MultiYearLoyaltyIncentive:
    """
    Step 220: Contractual incentives that unlock after N years of service.
    Encourages wrestlers to stay long-term.
    """
    years_required:  int = 3
    bonus_amount:    int = 0          # One-time cash bonus
    salary_bump_pct: float = 0.0     # Percentage salary increase
    creative_perk:   str = ""        # "title_guarantee"|"no_job_clause"|"creative_input"
    description:     str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "years_required":  self.years_required,
            "bonus_amount":    self.bonus_amount,
            "salary_bump_pct": self.salary_bump_pct,
            "creative_perk":   self.creative_perk,
            "description":     self.description,
        }

    @staticmethod
    def standard_package(current_salary: int) -> List["MultiYearLoyaltyIncentive"]:
        """Step 220: Standard multi-year incentive package."""
        return [
            MultiYearLoyaltyIncentive(
                years_required=1, bonus_amount=int(current_salary * 5),
                salary_bump_pct=0.0,
                description="1-year milestone bonus",
            ),
            MultiYearLoyaltyIncentive(
                years_required=3, bonus_amount=int(current_salary * 15),
                salary_bump_pct=0.05,
                creative_perk="creative_input",
                description="3-year loyalty bonus + 5% salary bump + creative input rights",
            ),
            MultiYearLoyaltyIncentive(
                years_required=5, bonus_amount=int(current_salary * 30),
                salary_bump_pct=0.10,
                creative_perk="no_job_clause",
                description="5-year veteran bonus + 10% salary bump + no-job clause",
            ),
        ]


# ============================================================================
# STEP 221: Historical Relationship Modifier (for returning wrestlers)
# ============================================================================

@dataclass
class HistoricalRelationship:
    """
    Step 221: Tracks relationship history with wrestlers who have left.
    Affects difficulty and cost of bringing them back.
    """
    wrestler_id:              str   = ""
    wrestler_name:            str   = ""
    years_worked_together:    float = 0.0
    was_champion:             bool  = False
    departure_reason:         str   = "contract_expired"   # "released"|"mutual"|"walkout"|"retired"
    departed_on_good_terms:   bool  = True
    had_public_dispute:       bool  = False
    return_interest_modifier: int   = 0   # -50 to +50 adjustment to comeback likelihood
    events: List[str]               = field(default_factory=list)

    def relationship_score(self) -> int:
        """0-100: overall relationship quality. Feeds into return negotiations."""
        score = 50  # Neutral
        score += min(20, int(self.years_worked_together * 3))
        if self.was_champion:             score += 10
        if self.departed_on_good_terms:   score += 15
        if self.had_public_dispute:       score -= 20
        reason_mods = {
            "contract_expired": 5,
            "mutual":           10,
            "released":         -5,
            "walkout":          -20,
            "retired":          0,
        }
        score += reason_mods.get(self.departure_reason, 0)
        return max(0, min(100, score))

    def negotiation_difficulty_modifier(self) -> int:
        """
        Step 221: Adjustment to negotiation difficulty for returning wrestlers.
        Positive = easier to sign. Negative = harder (more expensive, more clauses).
        """
        score = self.relationship_score()
        if score >= 75: return 15     # History makes them more receptive
        if score >= 55: return 5
        if score >= 35: return -10
        return -25                     # Bad blood makes return very difficult

    def return_salary_premium(self) -> float:
        """
        How much more (or less) they expect vs. market rate upon return.
        Negative = discount (they want to come home). Positive = premium.
        """
        score = self.relationship_score()
        if score >= 75: return -0.05  # 5% discount — happy to return
        if score >= 55: return 0.00
        if score >= 35: return 0.10   # 10% premium — need convincing
        return 0.20                    # 20% premium — significant bad blood

    def label(self) -> str:
        score = self.relationship_score()
        if score >= 75: return "Warm"
        if score >= 55: return "Neutral"
        if score >= 35: return "Strained"
        return "Hostile"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "wrestler_id":              self.wrestler_id,
            "wrestler_name":            self.wrestler_name,
            "years_worked_together":    self.years_worked_together,
            "was_champion":             self.was_champion,
            "departure_reason":         self.departure_reason,
            "departed_on_good_terms":   self.departed_on_good_terms,
            "had_public_dispute":       self.had_public_dispute,
            "return_interest_modifier": self.return_interest_modifier,
            "events":                   self.events,
            "relationship_score":       self.relationship_score(),
            "relationship_label":       self.label(),
            "negotiation_difficulty_modifier": self.negotiation_difficulty_modifier(),
            "return_salary_premium":    self.return_salary_premium(),
        }


# ============================================================================
# STEP 222: Loyalty Exception in Bidding Wars
# ============================================================================

def calculate_loyalty_bidding_war_exception(
    loyalty_tier: LoyaltyTier,
    years_with_promotion: float,
    was_champion: bool,
) -> Dict[str, Any]:
    """
    Step 222: In a re-signing bidding war, loyal wrestlers give you
    a right-of-first-refusal and a matching window before they sign elsewhere.
    """
    if loyalty_tier == LoyaltyTier.DEVOTED:
        return {
            "exception_applies":      True,
            "matching_window_weeks":  4,
            "automatic_right_of_first_refusal": True,
            "salary_cap_exception":   0.15,  # Can go 15% over normal cap
            "description": "Devoted wrestlers give you first right of refusal and a generous matching window.",
        }
    if loyalty_tier == LoyaltyTier.LOYAL:
        return {
            "exception_applies":      True,
            "matching_window_weeks":  2,
            "automatic_right_of_first_refusal": True,
            "salary_cap_exception":   0.08,
            "description": "Loyal wrestlers give you a 2-week window to match any rival offer.",
        }
    if loyalty_tier == LoyaltyTier.CONTENT and years_with_promotion >= 3:
        return {
            "exception_applies":      True,
            "matching_window_weeks":  1,
            "automatic_right_of_first_refusal": False,
            "salary_cap_exception":   0.0,
            "description": "Long-tenured wrestlers give you a brief window to improve your offer.",
        }
    return {
        "exception_applies":      False,
        "matching_window_weeks":  0,
        "automatic_right_of_first_refusal": False,
        "salary_cap_exception":   0.0,
        "description": "No loyalty exception — standard bidding war rules apply.",
    }


# ============================================================================
# STEP 223: Surprise Return Mechanics
# ============================================================================

class SurpriseReturnType(Enum):
    CROWD_POP_DEBUT      = "crowd_pop_debut"       # Shock return at major show
    SLOW_BUILD_TEASE     = "slow_build_tease"      # Weeks of vignettes first
    FORBIDDEN_DOOR       = "forbidden_door"        # Cross-promotional appearance
    EMERGENCY_RETURN     = "emergency_return"      # Brought back due to injury crisis
    HEEL_RETURN          = "heel_return"           # Returns as a villain
    FACE_RETURN          = "face_return"           # Returns as a beloved babyface

    @property
    def label(self) -> str:
        return self.value.replace("_", " ").title()

    @property
    def fan_pop_modifier(self) -> int:
        """Bonus to initial crowd reaction / pop event."""
        mods = {
            "crowd_pop_debut":   30,
            "slow_build_tease":  20,
            "forbidden_door":    25,
            "emergency_return":  10,
            "heel_return":       -10,
            "face_return":       25,
        }
        return mods[self.value]

    @property
    def popularity_gain(self) -> int:
        """Immediate popularity gain for the returning wrestler."""
        gains = {
            "crowd_pop_debut":  15,
            "slow_build_tease": 10,
            "forbidden_door":   12,
            "emergency_return":  5,
            "heel_return":       8,
            "face_return":      18,
        }
        return gains[self.value]


@dataclass
class SurpriseReturnPlan:
    """
    Step 223: Plan for bringing back a wrestler who previously left.
    Integrates with HistoricalRelationship and the legend/prospect systems.
    """
    wrestler_id:      str  = ""
    wrestler_name:    str  = ""
    return_type:      SurpriseReturnType = SurpriseReturnType.FACE_RETURN
    planned_show:     str  = ""
    planned_year:     int  = 1
    planned_week:     int  = 1
    secret_until_week: int = 0  # 0 = announce immediately; >0 = kept secret until then
    requires_contract_signed: bool = True
    estimated_cost:   int  = 0   # Total cost including signing bonus & any appearance fees
    historical_relationship: Optional[HistoricalRelationship] = None

    # Execution tracking
    tease_videos_count: int  = 0
    is_revealed:        bool = False
    executed:           bool = False

    def expected_pop_score(self) -> int:
        """0-100: how big the crowd moment will be."""
        base = 50
        base += self.return_type.fan_pop_modifier
        if self.historical_relationship:
            rel_score = self.historical_relationship.relationship_score()
            if rel_score >= 75: base += 15
            elif rel_score >= 55: base += 5
            elif rel_score < 35: base -= 10
        # Secret reveals pop bigger
        if self.secret_until_week > 0:
            base += 10
        # Tease videos build anticipation
        base += min(10, self.tease_videos_count * 3)
        return max(0, min(100, base))

    def add_tease_video(self) -> Dict[str, Any]:
        self.tease_videos_count += 1
        fan_excitement = min(100, 40 + self.tease_videos_count * 15)
        return {
            "tease_number":  self.tease_videos_count,
            "fan_excitement": fan_excitement,
            "message": (
                f"Tease #{self.tease_videos_count} aired. "
                f"Fan speculation at {fan_excitement}%. "
                + ("Fans are LOUD about who this could be!" if fan_excitement > 75
                   else "Buzz is building steadily.")
            ),
        }

    def execute_return(self, actual_show: str) -> Dict[str, Any]:
        self.executed = True
        self.is_revealed = True
        pop = self.expected_pop_score()
        popularity_gain = self.return_type.popularity_gain
        return {
            "executed":        True,
            "show":            actual_show,
            "return_type":     self.return_type.label,
            "pop_score":       pop,
            "popularity_gain": popularity_gain,
            "tease_count":     self.tease_videos_count,
            "message": (
                f"{self.wrestler_name} returns at {actual_show}! "
                f"{'The roof nearly comes off the building!' if pop >= 75 else 'A solid reaction from the crowd.'} "
                f"+{popularity_gain} popularity."
            ),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "wrestler_id":      self.wrestler_id,
            "wrestler_name":    self.wrestler_name,
            "return_type":      self.return_type.value,
            "return_type_label": self.return_type.label,
            "planned_show":     self.planned_show,
            "planned_year":     self.planned_year,
            "planned_week":     self.planned_week,
            "secret_until_week": self.secret_until_week,
            "requires_contract_signed": self.requires_contract_signed,
            "estimated_cost":   self.estimated_cost,
            "tease_videos_count": self.tease_videos_count,
            "is_revealed":      self.is_revealed,
            "executed":         self.executed,
            "expected_pop_score": self.expected_pop_score(),
            "popularity_gain":  self.return_type.popularity_gain,
            "historical_relationship": (
                self.historical_relationship.to_dict()
                if self.historical_relationship else None
            ),
        }