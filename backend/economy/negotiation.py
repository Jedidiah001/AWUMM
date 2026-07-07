"""
Negotiation Engine - Steps 134-160
Handles all negotiation logic for free agent signings.

Covers:
  134 - Negotiation Interface Design
  135 - Opening Offer Strategy
  136 - Counter-Offer Mechanics
  137 - Negotiation Currency Points
  138 - Reading the Room
  139 - Walking Away and Returning
  140 - Deadline Pressure
  141 - Third-Party Intervention
  142 - Base Salary Structures
  143 - Contract Length Implications
  144 - Signing Bonus Calculations
  145 - Merchandise Split Negotiations
  146 - Downside Guarantee Structures
  147 - Pay-Per-View Bonus Tiers
  148 - Incentive Clause Creation
  149 - Creative Control Levels
  150 - No-Job Clause Specifics
  151 - Title Guarantee Demands
  152 - Brand Placement Preferences
  153 - Storyline Veto Rights
  154 - Finish Protection
  155 - Promo Style Preservation
  156 - Appearance Schedule Demands
  157 - Travel Accommodation Requirements
  158 - Outside Project Permissions
  159 - Family Accommodation Clauses
  160 - Injury Recovery Guarantees
"""

import random
import uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


# ─────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────

class NegotiationStatus(Enum):
    ACTIVE      = "active"
    ACCEPTED    = "accepted"
    REJECTED    = "rejected"
    COUNTERED   = "countered"
    PAUSED      = "paused"       # Step 139 – walked away
    EXPIRED     = "expired"      # Step 140 – deadline passed
    CANCELLED   = "cancelled"


class SalaryStructure(Enum):
    """Step 142 – Base Salary Structures"""
    PER_APPEARANCE = "per_appearance"   # Part-timers
    WEEKLY         = "weekly"           # Regular roster
    ANNUAL         = "annual"           # Top stars
    HYBRID         = "hybrid"           # Base + per-show bonus


class CreativeControlLevel(Enum):
    """Step 149 – Creative Control Levels"""
    NONE          = "none"
    CONSULTATION  = "consultation"
    APPROVAL      = "approval"
    PARTNERSHIP   = "partnership"
    FULL          = "full"


class NegotiationTell(Enum):
    """Step 138 – Reading the Room tells"""
    CREATIVE_FOCUS    = "creative_focus"
    MONEY_FOCUS       = "money_focus"
    LENGTH_FOCUS      = "length_focus"
    SCHEDULE_FOCUS    = "schedule_focus"
    CREATIVE_CONTROL  = "creative_control"
    TITLE_HUNGER      = "title_hunger"
    BRAND_SPECIFIC    = "brand_specific"
    LIFESTYLE         = "lifestyle"


class PaymentModel(Enum):
    """Step 142 sub-types"""
    DOWNSIDE_GUARANTEE = "downside_guarantee"
    PERFORMANCE_BONUS  = "performance_bonus"
    PPV_BONUS          = "ppv_bonus"
    MERCH_SPLIT        = "merch_split"


# ─────────────────────────────────────────────
# STEP 137 – Negotiation Currency (Flexibility Points)
# ─────────────────────────────────────────────

@dataclass
class NegotiationFlexibility:
    """
    How far each side will move. Stubborn wrestlers have few points;
    flexible ones have many. Each concession costs points.
    """
    total_points:      int = 10
    points_remaining:  int = 10

    # Track what has already been conceded
    salary_conceded:   bool = False
    length_conceded:   bool = False
    bonus_conceded:    bool = False
    creative_conceded: bool = False
    schedule_conceded: bool = False

    def spend(self, cost: int = 1) -> bool:
        if self.points_remaining >= cost:
            self.points_remaining -= cost
            return True
        return False

    @property
    def stubbornness_pct(self) -> float:
        used = self.total_points - self.points_remaining
        return (used / self.total_points) * 100 if self.total_points else 0

    @property
    def is_exhausted(self) -> bool:
        return self.points_remaining <= 0


# ─────────────────────────────────────────────
# STEP 140 – Deadline Pressure
# ─────────────────────────────────────────────

@dataclass
class NegotiationDeadline:
    """
    Some negotiations have hard deadlines:
      - Rival offer expiry
      - PPV booking window
    """
    has_deadline:      bool = False
    deadline_label:    str  = ""          # e.g. "Rumble Royale"
    deadline_week:     int  = 0
    deadline_year:     int  = 0
    rival_offer_rival: str  = ""          # Name of rival promotion
    rival_offer_value: int  = 0


# ─────────────────────────────────────────────
# STEP 148 / 147 – PPV Bonus Tiers & Incentive Clauses
# ─────────────────────────────────────────────

@dataclass
class PPVBonusTier:
    """Step 147"""
    base_appearance_bonus:  int = 0
    main_event_bonus:       int = 0
    championship_match_bonus: int = 0
    headliner_bonus:        int = 0
    guaranteed_ppv_minimum: int = 0   # Minimum PPV appearances guaranteed per year


@dataclass
class IncentiveClause:
    """Step 148 – Performance-based bonuses"""
    match_quality_bonus:    int = 0     # Triggered if avg star rating ≥ threshold
    match_quality_threshold: float = 3.5
    merch_sales_bonus:      int = 0
    attendance_bonus:       int = 0
    championship_bonus:     int = 0
    loyalty_bonus:          int = 0     # For completing contract without issues


# ─────────────────────────────────────────────
# STEP 145 / 146 – Merch Split & Downside Guarantee
# ─────────────────────────────────────────────

@dataclass
class MerchandiseDeal:
    """Step 145"""
    promotion_pct: int = 70   # Default 70/30
    wrestler_pct:  int = 30

    @classmethod
    def standard(cls):
        return cls(promotion_pct=70, wrestler_pct=30)

    @classmethod
    def star(cls):
        return cls(promotion_pct=60, wrestler_pct=40)

    @classmethod
    def superstar(cls):
        return cls(promotion_pct=55, wrestler_pct=45)


@dataclass
class DownsideGuarantee:
    """Step 146 – Minimum pay even if not used"""
    weekly_guarantee: int  = 0
    is_active:        bool = False


# ─────────────────────────────────────────────
# LIFESTYLE / CREATIVE CLAUSES (Steps 150-160)
# ─────────────────────────────────────────────

@dataclass
class CreativeClauses:
    """Steps 150-155"""
    creative_control:       CreativeControlLevel = CreativeControlLevel.NONE
    no_job_clauses:         List[str] = field(default_factory=list)  # Step 150
    title_guarantee:        str = ""       # e.g. "World title shot within 6 months" – Step 151
    brand_preference:       str = ""       # Step 152
    storyline_veto_rights:  bool = False   # Step 153
    finish_protection:      bool = False   # Step 154
    promo_style:            str = "none"   # "scripted"|"bullets"|"improv"|"none" – Step 155
    promo_time_minimum:     int = 0        # Minutes guaranteed on mic per show


@dataclass
class LifestyleClauses:
    """Steps 156-160"""
    max_appearances_per_year: int  = 0     # Step 156; 0 = no limit
    first_class_travel:      bool = False  # Step 157
    private_car_service:     bool = False
    minimum_hotel_tier:      str  = "standard"  # "standard"|"4-star"|"5-star"
    outside_projects_allowed: bool = True  # Step 158
    outside_projects_approval_required: bool = False
    family_time_off:         bool = False  # Step 159
    hometown_show_preference: bool = False
    injury_pay_protection:   bool = False  # Step 160 – continued pay during rehab
    injury_job_security:     bool = False  # No push loss due to injury


# ─────────────────────────────────────────────
# MAIN NEGOTIATION OFFER
# ─────────────────────────────────────────────

@dataclass
class NegotiationOffer:
    """A single offer in a negotiation (either side can make one)"""
    offer_id:          str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    from_promotion:    bool = True          # True = your offer; False = wrestler counter

    # Step 142 – Monetary
    salary_structure:  SalaryStructure = SalaryStructure.WEEKLY
    salary_per_show:   int = 0
    contract_weeks:    int = 52
    signing_bonus:     int = 0              # Step 144

    # Step 145-147
    merch_deal:        MerchandiseDeal = field(default_factory=MerchandiseDeal.standard)
    downside_guarantee: DownsideGuarantee = field(default_factory=DownsideGuarantee)
    ppv_bonuses:       PPVBonusTier = field(default_factory=PPVBonusTier)
    incentives:        IncentiveClause = field(default_factory=IncentiveClause)

    # Steps 149-155 – Creative
    creative_clauses:  CreativeClauses = field(default_factory=CreativeClauses)

    # Steps 156-160 – Lifestyle
    lifestyle_clauses: LifestyleClauses = field(default_factory=LifestyleClauses)

    # Meta
    round_number:      int = 1
    notes:             str = ""

    def total_value(self) -> int:
        """Estimated total value of offer over contract life"""
        base = self.salary_per_show * (self.contract_weeks // 7 * 3)  # ~3 shows/week
        return base + self.signing_bonus

    def to_dict(self) -> dict:
        return {
            "offer_id": self.offer_id,
            "from_promotion": self.from_promotion,
            "salary_structure": self.salary_structure.value,
            "salary_per_show": self.salary_per_show,
            "contract_weeks": self.contract_weeks,
            "signing_bonus": self.signing_bonus,
            "merch_deal": {
                "promotion_pct": self.merch_deal.promotion_pct,
                "wrestler_pct": self.merch_deal.wrestler_pct,
            },
            "downside_guarantee": {
                "weekly_guarantee": self.downside_guarantee.weekly_guarantee,
                "is_active": self.downside_guarantee.is_active,
            },
            "ppv_bonuses": {
                "base_appearance_bonus": self.ppv_bonuses.base_appearance_bonus,
                "main_event_bonus": self.ppv_bonuses.main_event_bonus,
                "championship_match_bonus": self.ppv_bonuses.championship_match_bonus,
                "headliner_bonus": self.ppv_bonuses.headliner_bonus,
                "guaranteed_ppv_minimum": self.ppv_bonuses.guaranteed_ppv_minimum,
            },
            "incentives": {
                "match_quality_bonus": self.incentives.match_quality_bonus,
                "match_quality_threshold": self.incentives.match_quality_threshold,
                "merch_sales_bonus": self.incentives.merch_sales_bonus,
                "championship_bonus": self.incentives.championship_bonus,
                "loyalty_bonus": self.incentives.loyalty_bonus,
            },
            "creative_clauses": {
                "creative_control": self.creative_clauses.creative_control.value,
                "no_job_clauses": self.creative_clauses.no_job_clauses,
                "title_guarantee": self.creative_clauses.title_guarantee,
                "brand_preference": self.creative_clauses.brand_preference,
                "storyline_veto_rights": self.creative_clauses.storyline_veto_rights,
                "finish_protection": self.creative_clauses.finish_protection,
                "promo_style": self.creative_clauses.promo_style,
                "promo_time_minimum": self.creative_clauses.promo_time_minimum,
            },
            "lifestyle_clauses": {
                "max_appearances_per_year": self.lifestyle_clauses.max_appearances_per_year,
                "first_class_travel": self.lifestyle_clauses.first_class_travel,
                "private_car_service": self.lifestyle_clauses.private_car_service,
                "minimum_hotel_tier": self.lifestyle_clauses.minimum_hotel_tier,
                "outside_projects_allowed": self.lifestyle_clauses.outside_projects_allowed,
                "outside_projects_approval_required": self.lifestyle_clauses.outside_projects_approval_required,
                "family_time_off": self.lifestyle_clauses.family_time_off,
                "hometown_show_preference": self.lifestyle_clauses.hometown_show_preference,
                "injury_pay_protection": self.lifestyle_clauses.injury_pay_protection,
                "injury_job_security": self.lifestyle_clauses.injury_job_security,
            },
            "round_number": self.round_number,
            "total_value": self.total_value(),
            "notes": self.notes,
        }


# ─────────────────────────────────────────────
# NEGOTIATION SESSION (the full state machine)
# ─────────────────────────────────────────────

@dataclass
class NegotiationSession:
    """
    Step 134 – The full negotiation session state.
    Tracks rounds, offers, tells, deadline, and flexibility.
    """
    session_id:     str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    fa_id:          str = ""
    wrestler_name:  str = ""
    wrestler_role:  str = "Midcard"
    asking_price:   int = 0
    market_value:   int = 0

    status:         NegotiationStatus = NegotiationStatus.ACTIVE
    round_number:   int = 1
    max_rounds:     int = 3              # Step 127 – bidding round structure

    offer_history:  List[NegotiationOffer] = field(default_factory=list)

    flexibility:    NegotiationFlexibility = field(default_factory=NegotiationFlexibility)
    deadline:       NegotiationDeadline = field(default_factory=NegotiationDeadline)

    # Step 138 – Reading the Room
    tells:          List[str] = field(default_factory=list)
    priority_focus: NegotiationTell = NegotiationTell.MONEY_FOCUS

    # Step 141 – Third-party intervention
    third_party_used: bool = False
    third_party_boost: int = 0

    # Step 139 – Walk-away state
    walk_away_count:    int = 0
    paused_since_week:  int = 0

    # Step 135 – Opening offer quality signal
    opening_offer_quality: str = "fair"  # "lowball"|"fair"|"generous"

    # Misc
    current_year:   int = 1
    current_week:   int = 1
    notes:          str = ""

    def latest_offer(self) -> Optional[NegotiationOffer]:
        return self.offer_history[-1] if self.offer_history else None

    def promotion_offers(self) -> List[NegotiationOffer]:
        return [o for o in self.offer_history if o.from_promotion]

    def wrestler_counters(self) -> List[NegotiationOffer]:
        return [o for o in self.offer_history if not o.from_promotion]

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "fa_id": self.fa_id,
            "wrestler_name": self.wrestler_name,
            "wrestler_role": self.wrestler_role,
            "asking_price": self.asking_price,
            "market_value": self.market_value,
            "status": self.status.value,
            "round_number": self.round_number,
            "max_rounds": self.max_rounds,
            "offer_history": [o.to_dict() for o in self.offer_history],
            "flexibility": {
                "total_points": self.flexibility.total_points,
                "points_remaining": self.flexibility.points_remaining,
                "stubbornness_pct": self.flexibility.stubbornness_pct,
                "is_exhausted": self.flexibility.is_exhausted,
            },
            "deadline": {
                "has_deadline": self.deadline.has_deadline,
                "deadline_label": self.deadline.deadline_label,
                "deadline_week": self.deadline.deadline_week,
                "rival_offer_rival": self.deadline.rival_offer_rival,
                "rival_offer_value": self.deadline.rival_offer_value,
            },
            "tells": self.tells,
            "priority_focus": self.priority_focus.value,
            "third_party_used": self.third_party_used,
            "third_party_boost": self.third_party_boost,
            "walk_away_count": self.walk_away_count,
            "opening_offer_quality": self.opening_offer_quality,
            "notes": self.notes,
        }


# ─────────────────────────────────────────────
# NEGOTIATION ENGINE
# ─────────────────────────────────────────────

class NegotiationEngine:
    """
    Central engine that manages negotiation sessions and calculates outcomes.
    All the logic for Steps 134-160 lives here.
    """

    # In-memory store of active sessions (keyed by session_id)
    _sessions: Dict[str, NegotiationSession] = {}

    # ── Step 134: Start a session ──────────────────────────────────────────

    def start_negotiation(
        self,
        fa: Any,                    # FreeAgent object or dict
        current_year: int = 1,
        current_week: int = 1,
    ) -> NegotiationSession:
        """
        Step 134 – Initialise a brand-new negotiation session for a free agent.
        Sets up flexibility points, reveals tells, checks for rival deadlines.
        """
        if hasattr(fa, 'to_dict'):
            fa_dict = fa.to_dict()
        else:
            fa_dict = fa

        wrestler_name = fa_dict.get('wrestler_name', fa_dict.get('name', 'Unknown'))
        market_value  = fa_dict.get('market_value', 50000)
        role          = fa_dict.get('role', 'Midcard')
        asking_price  = self._get_asking_price(fa_dict)

        # Flexibility points based on personality (Step 137)
        mood          = fa_dict.get('mood_state', 'patient')
        flex_points   = self._mood_to_flexibility(mood, role)

        # Priority tell (Step 138)
        tell, tells   = self._generate_tells(fa_dict)

        # Deadline (Step 140)
        deadline      = self._check_for_deadline(fa_dict, current_year, current_week)

        session = NegotiationSession(
            fa_id          = fa_dict.get('id', fa_dict.get('fa_id', '')),
            wrestler_name  = wrestler_name,
            wrestler_role  = role,
            asking_price   = asking_price,
            market_value   = market_value,
            flexibility    = NegotiationFlexibility(
                total_points=flex_points,
                points_remaining=flex_points
            ),
            deadline       = deadline,
            tells          = tells,
            priority_focus = tell,
            current_year   = current_year,
            current_week   = current_week,
        )

        self._sessions[session.session_id] = session
        return session

    # ── Step 135: Evaluate opening offer quality ───────────────────────────

    def evaluate_opening_offer(
        self,
        session: NegotiationSession,
        offer: NegotiationOffer,
    ) -> str:
        """
        Step 135 – Classify the first offer as lowball, fair, or generous.
        Returns a quality label and adds it to the session.
        """
        ratio = offer.salary_per_show / session.asking_price if session.asking_price else 1.0

        if ratio < 0.7:
            quality = "lowball"
            # Lowball can end negotiation immediately for proud wrestlers
        elif ratio < 0.95:
            quality = "fair"
        else:
            quality = "generous"

        session.opening_offer_quality = quality
        return quality

    # ── Step 136: Generate counter-offer ──────────────────────────────────

    def generate_counter_offer(
        self,
        session: NegotiationSession,
        your_offer: NegotiationOffer,
    ) -> Optional[NegotiationOffer]:
        """
        Step 136 – Wrestler counters with adjustments based on:
          - Gap between offer and asking price
          - Remaining flexibility points
          - Priority focus (tells)
        Returns None if wrestler rejects outright.
        """
        if session.flexibility.is_exhausted:
            return None  # No more movement – take it or leave it

        ratio = your_offer.salary_per_show / session.asking_price if session.asking_price else 1.0

        # Outright reject if insulting and no flexibility left
        if ratio < 0.6 and session.flexibility.points_remaining < 3:
            return None

        # Spend a flexibility point for each counter
        session.flexibility.spend(1)

        counter = NegotiationOffer(from_promotion=False)
        counter.round_number = session.round_number

        # Salary counter
        if ratio < 0.9:
            # Push back toward asking price proportionally
            gap_fill = 0.6 + (0.4 * (1 - session.flexibility.stubbornness_pct / 100))
            counter.salary_per_show = int(session.asking_price * gap_fill)
        else:
            counter.salary_per_show = your_offer.salary_per_show  # Acceptable

        # Contract length counter
        counter.contract_weeks = max(
            your_offer.contract_weeks,
            self._preferred_length(session.wrestler_role)
        )

        # Signing bonus counter
        if session.priority_focus == NegotiationTell.MONEY_FOCUS and your_offer.signing_bonus < 20000:
            counter.signing_bonus = max(your_offer.signing_bonus, 15000)
        else:
            counter.signing_bonus = your_offer.signing_bonus

        # Creative control push (if that's the tell)
        counter.creative_clauses = your_offer.creative_clauses
        if session.priority_focus == NegotiationTell.CREATIVE_CONTROL:
            if your_offer.creative_clauses.creative_control == CreativeControlLevel.NONE:
                counter.creative_clauses.creative_control = CreativeControlLevel.CONSULTATION

        # Title guarantee push (Step 151)
        if session.priority_focus == NegotiationTell.TITLE_HUNGER and not your_offer.creative_clauses.title_guarantee:
            counter.creative_clauses.title_guarantee = "Title shot within 12 months"

        # Lifestyle: appearance limit push (Step 156)
        counter.lifestyle_clauses = your_offer.lifestyle_clauses
        if session.priority_focus == NegotiationTell.SCHEDULE_FOCUS:
            if counter.lifestyle_clauses.max_appearances_per_year == 0:
                counter.lifestyle_clauses.max_appearances_per_year = 180

        counter.notes = self._generate_counter_note(session, ratio)
        return counter

    # ── Step 137: Evaluate acceptance probability ──────────────────────────

    def calculate_acceptance_probability(
        self,
        session: NegotiationSession,
        offer: NegotiationOffer,
    ) -> Dict[str, Any]:
        """
        Step 137 – Full probability calculation for an offer being accepted.
        Returns breakdown dict with final_probability and recommendation.
        """
        prob = 40  # Base
        breakdown = {}

        # ── Salary factor ──────────────────────────────────────
        ratio = offer.salary_per_show / session.asking_price if session.asking_price else 1.0
        if ratio >= 1.3:
            salary_mod = 35
        elif ratio >= 1.1:
            salary_mod = 25
        elif ratio >= 1.0:
            salary_mod = 15
        elif ratio >= 0.9:
            salary_mod = 5
        elif ratio >= 0.75:
            salary_mod = -10
        else:
            salary_mod = -30
        prob += salary_mod
        breakdown['salary'] = salary_mod

        # ── Signing bonus factor (Step 144) ───────────────────
        bonus_mod = 0
        if offer.signing_bonus >= 100_000:
            bonus_mod = 20
        elif offer.signing_bonus >= 50_000:
            bonus_mod = 14
        elif offer.signing_bonus >= 25_000:
            bonus_mod = 8
        elif offer.signing_bonus >= 10_000:
            bonus_mod = 4
        prob += bonus_mod
        breakdown['signing_bonus'] = bonus_mod

        # ── Merch split factor (Step 145) ─────────────────────
        merch_mod = 0
        wrestler_pct = offer.merch_deal.wrestler_pct
        if wrestler_pct >= 45:
            merch_mod = 12
        elif wrestler_pct >= 40:
            merch_mod = 8
        elif wrestler_pct >= 35:
            merch_mod = 4
        prob += merch_mod
        breakdown['merch_split'] = merch_mod

        # ── Downside guarantee factor (Step 146) ──────────────
        dg_mod = 0
        if offer.downside_guarantee.is_active:
            dg_mod = 8
        prob += dg_mod
        breakdown['downside_guarantee'] = dg_mod

        # ── PPV bonuses factor (Step 147) ─────────────────────
        ppv_mod = 0
        ppv_total = (offer.ppv_bonuses.base_appearance_bonus +
                     offer.ppv_bonuses.main_event_bonus +
                     offer.ppv_bonuses.championship_match_bonus)
        if ppv_total >= 50_000:
            ppv_mod = 10
        elif ppv_total >= 20_000:
            ppv_mod = 6
        elif ppv_total >= 5_000:
            ppv_mod = 3
        prob += ppv_mod
        breakdown['ppv_bonuses'] = ppv_mod

        # ── Creative control factor (Step 149) ────────────────
        cc_mods = {
            CreativeControlLevel.NONE:         0,
            CreativeControlLevel.CONSULTATION:  5,
            CreativeControlLevel.APPROVAL:     10,
            CreativeControlLevel.PARTNERSHIP:  15,
            CreativeControlLevel.FULL:         20,
        }
        cc_mod = cc_mods.get(offer.creative_clauses.creative_control, 0)
        # Extra weight if that's the priority
        if session.priority_focus == NegotiationTell.CREATIVE_CONTROL:
            cc_mod = int(cc_mod * 1.6)
        prob += cc_mod
        breakdown['creative_control'] = cc_mod

        # ── Title guarantee (Step 151) ─────────────────────────
        title_mod = 0
        if offer.creative_clauses.title_guarantee:
            title_mod = 12
            if session.priority_focus == NegotiationTell.TITLE_HUNGER:
                title_mod = 20
        prob += title_mod
        breakdown['title_guarantee'] = title_mod

        # ── Brand preference (Step 152) ────────────────────────
        brand_mod = 0
        if offer.creative_clauses.brand_preference:
            brand_mod = 6
            if session.priority_focus == NegotiationTell.BRAND_SPECIFIC:
                brand_mod = 14
        prob += brand_mod
        breakdown['brand_preference'] = brand_mod

        # ── Schedule/lifestyle (Steps 156-160) ────────────────
        lifestyle_mod = 0
        lc = offer.lifestyle_clauses
        if lc.max_appearances_per_year > 0 and lc.max_appearances_per_year <= 180:
            lifestyle_mod += 6
        if lc.first_class_travel:
            lifestyle_mod += 4
        if lc.outside_projects_allowed:
            lifestyle_mod += 5
        if lc.family_time_off:
            lifestyle_mod += 4
        if lc.injury_pay_protection:
            lifestyle_mod += 7
        if lc.injury_job_security:
            lifestyle_mod += 5
        if session.priority_focus == NegotiationTell.LIFESTYLE:
            lifestyle_mod = int(lifestyle_mod * 1.4)
        prob += lifestyle_mod
        breakdown['lifestyle'] = lifestyle_mod

        # ── Third-party boost (Step 141) ─────────────────────
        if session.third_party_used:
            prob += session.third_party_boost
            breakdown['third_party'] = session.third_party_boost

        # ── Deadline urgency can help you (Step 140) ──────────
        # If deadline is YOUR deadline (rival offer), wrestler knows you're serious
        if session.deadline.has_deadline and session.deadline.rival_offer_value > 0:
            # Rival offer pressure: if yours is clearly better it helps
            if offer.total_value() > session.deadline.rival_offer_value:
                prob += 8
                breakdown['deadline_pressure'] = 8

        # ── Walk-away penalty (Step 139) ──────────────────────
        if session.walk_away_count > 0:
            wa_penalty = -5 * session.walk_away_count
            prob += wa_penalty
            breakdown['walk_away_penalty'] = wa_penalty

        # ── Round bonus: final round slightly easier to close ──
        if session.round_number >= session.max_rounds:
            prob += 5
            breakdown['final_round_bonus'] = 5

        final = max(5, min(95, prob))
        breakdown['base'] = 40
        breakdown['final_probability'] = final

        recommendation = self._build_recommendation(session, offer, final, ratio)
        breakdown['recommendation'] = recommendation

        return breakdown

    # ── Step 138: Generate readable tells ─────────────────────────────────

    def get_negotiation_tells(self, session: NegotiationSession) -> List[str]:
        """
        Step 138 – Return human-readable tell strings for the UI.
        These hint at what the wrestler really cares about.
        """
        return session.tells

    # ── Step 139: Walk away and return ────────────────────────────────────

    def pause_negotiation(
        self,
        session: NegotiationSession,
        current_week: int,
    ) -> Dict[str, Any]:
        """Step 139 – Walk away from negotiation temporarily."""
        session.status       = NegotiationStatus.PAUSED
        session.walk_away_count += 1
        session.paused_since_week = current_week
        return {
            "success": True,
            "message": f"Negotiations paused. {session.wrestler_name} will wait, but patience is limited.",
            "walk_away_count": session.walk_away_count,
            "warning": "Returning too late or too many times will close the door permanently."
        }

    def resume_negotiation(
        self,
        session: NegotiationSession,
        current_week: int,
    ) -> Dict[str, Any]:
        """Step 139 – Return to paused negotiation."""
        weeks_away = current_week - session.paused_since_week

        # Wrestler patience: 1-4 weeks OK; beyond that risks closure
        if weeks_away > 4:
            # Random chance the door has closed
            if random.random() < (weeks_away - 4) * 0.15:
                session.status = NegotiationStatus.EXPIRED
                return {
                    "success": False,
                    "message": f"{session.wrestler_name} has lost patience and signed elsewhere.",
                    "session": session.to_dict()
                }

        session.status = NegotiationStatus.ACTIVE
        return {
            "success": True,
            "weeks_away": weeks_away,
            "message": f"Negotiations resumed after {weeks_away} week(s).",
            "note": f"{session.wrestler_name} has adjusted demands slightly." if weeks_away > 2 else "",
            "session": session.to_dict()
        }

    # ── Step 141: Third-party intervention ────────────────────────────────

    def apply_third_party_intervention(
        self,
        session: NegotiationSession,
        ally_name: str,
        ally_type: str,   # "roster_friend"|"legend"|"satisfied_signee"
    ) -> Dict[str, Any]:
        """Step 141 – A trusted party vouches for your promotion."""
        if session.third_party_used:
            return {"success": False, "message": "Third-party intervention already used this negotiation."}

        boost_map = {
            "roster_friend":    10,
            "legend":           15,
            "satisfied_signee": 8,
        }
        boost = boost_map.get(ally_type, 8)
        session.third_party_used  = True
        session.third_party_boost = boost

        return {
            "success": True,
            "ally_name": ally_name,
            "ally_type": ally_type,
            "probability_boost": boost,
            "message": f"{ally_name} has spoken highly of your promotion to {session.wrestler_name}. +{boost}% acceptance probability."
        }

    # ── Step 135: Submit final offer (resolve session) ────────────────────

    def submit_offer(
        self,
        session: NegotiationSession,
        offer: NegotiationOffer,
    ) -> Dict[str, Any]:
        """
        Step 135/136 – Submit an offer. Handles:
        - Round 1: classify opening quality, possibly get counter
        - Round 2/3: narrowing
        - Final: accept/reject with probability roll
        """
        if session.status not in (NegotiationStatus.ACTIVE, NegotiationStatus.COUNTERED):
            return {"success": False, "error": f"Session is {session.status.value}, not active."}

        offer.round_number = session.round_number
        session.offer_history.append(offer)

        # Evaluate opening quality on round 1
        if session.round_number == 1:
            quality = self.evaluate_opening_offer(session, offer)
            # Lowball from proud wrestler = immediate rejection risk
            if quality == "lowball" and session.flexibility.points_remaining < 2:
                session.status = NegotiationStatus.REJECTED
                return {
                    "success": True,
                    "outcome": "rejected",
                    "reason": "lowball_insult",
                    "message": f"{session.wrestler_name} is insulted by the low-ball offer and walks out.",
                    "session": session.to_dict()
                }

        # Check deadline (Step 140)
        if session.deadline.has_deadline:
            if session.current_week >= session.deadline.deadline_week:
                session.status = NegotiationStatus.EXPIRED
                return {
                    "success": True,
                    "outcome": "expired",
                    "message": f"Deadline passed! {session.wrestler_name} had to make a decision.",
                    "session": session.to_dict()
                }

        # Calculate probability
        prob_data = self.calculate_acceptance_probability(session, offer)
        final_prob = prob_data['final_probability']

        # On final round – roll for accept/reject
        if session.round_number >= session.max_rounds or final_prob >= 90:
            roll = random.uniform(0, 100)
            accepted = roll <= final_prob

            if accepted:
                session.status = NegotiationStatus.ACCEPTED
                return {
                    "success": True,
                    "outcome": "accepted",
                    "roll": round(roll, 1),
                    "probability": final_prob,
                    "probability_breakdown": prob_data,
                    "message": f"✅ {session.wrestler_name} ACCEPTS the offer!",
                    "session": session.to_dict(),
                    "final_offer": offer.to_dict()
                }
            else:
                session.status = NegotiationStatus.REJECTED
                return {
                    "success": True,
                    "outcome": "rejected",
                    "roll": round(roll, 1),
                    "probability": final_prob,
                    "probability_breakdown": prob_data,
                    "message": f"❌ {session.wrestler_name} REJECTS the final offer.",
                    "session": session.to_dict()
                }

        # Not final round – generate counter-offer
        counter = self.generate_counter_offer(session, offer)

        if counter is None:
            # No counter possible – reject
            session.status = NegotiationStatus.REJECTED
            return {
                "success": True,
                "outcome": "rejected",
                "reason": "no_flexibility",
                "message": f"❌ {session.wrestler_name} has no more flexibility and rejects.",
                "session": session.to_dict()
            }

        session.offer_history.append(counter)
        session.round_number += 1
        session.status = NegotiationStatus.COUNTERED

        return {
            "success": True,
            "outcome": "countered",
            "probability": final_prob,
            "probability_breakdown": prob_data,
            "counter_offer": counter.to_dict(),
            "tell": self._reveal_tell_from_counter(session, counter),
            "message": f"💬 {session.wrestler_name} counters (Round {session.round_number}/{session.max_rounds}): {counter.notes}",
            "session": session.to_dict()
        }

    # ── Session management ────────────────────────────────────────────────

    def get_session(self, session_id: str) -> Optional[NegotiationSession]:
        return self._sessions.get(session_id)

    def close_session(self, session_id: str):
        self._sessions.pop(session_id, None)

    def get_all_active_sessions(self) -> List[NegotiationSession]:
        return [s for s in self._sessions.values() if s.status == NegotiationStatus.ACTIVE]

    # ── Private helpers ───────────────────────────────────────────────────

    def _get_asking_price(self, fa_dict: dict) -> int:
        if fa_dict.get('demands') and isinstance(fa_dict['demands'], dict):
            return fa_dict['demands'].get('asking_salary', fa_dict.get('market_value', 50000))
        return fa_dict.get('asking_price', fa_dict.get('market_value', 50000))

    def _mood_to_flexibility(self, mood: str, role: str) -> int:
        """Step 137 – Map mood state to flexibility points"""
        base = {
            "patient":    8,
            "hungry":    12,
            "bitter":     5,
            "desperate": 14,
            "arrogant":   4,
        }.get(mood, 8)

        # Top stars are stubbornner
        if role in ("Main Event", "Upper Midcard"):
            base = max(3, base - 2)
        return base

    def _generate_tells(self, fa_dict: dict):
        """Step 138 – Generate tells revealing what the wrestler cares about"""
        tells_pool = []

        role = fa_dict.get('role', 'Midcard')
        age  = fa_dict.get('age', 28)
        mood = fa_dict.get('mood_state', 'patient')
        source = fa_dict.get('source', 'released')

        # Role-based tells
        if role in ('Main Event', 'Upper Midcard'):
            tells_pool.append(("She keeps mentioning creative direction", NegotiationTell.CREATIVE_CONTROL))
            tells_pool.append(("He emphasises championship opportunities", NegotiationTell.TITLE_HUNGER))
        else:
            tells_pool.append(("He seems focused on the numbers", NegotiationTell.MONEY_FOCUS))

        # Age-based tells
        if age >= 38:
            tells_pool.append(("She mentions needing a lighter schedule", NegotiationTell.SCHEDULE_FOCUS))
            tells_pool.append(("He asks about injury clause protection", NegotiationTell.LIFESTYLE))
        elif age <= 25:
            tells_pool.append(("She's excited about long-term opportunity", NegotiationTell.CREATIVE_FOCUS))

        # Source-based tells
        if source == 'rival_release':
            tells_pool.append(("He quickly accepted the salary but hesitated on length", NegotiationTell.LENGTH_FOCUS))
        if source == 'international':
            tells_pool.append(("She asks about family travel allowances", NegotiationTell.LIFESTYLE))

        # Mood tells
        if mood == 'bitter':
            tells_pool.append(("He keeps returning to how his last promotion treated him", NegotiationTell.CREATIVE_CONTROL))
        if mood == 'arrogant':
            tells_pool.append(("He seems dismissive of the offer so far", NegotiationTell.MONEY_FOCUS))

        if not tells_pool:
            tells_pool.append(("She seems open-minded about the offer", NegotiationTell.MONEY_FOCUS))

        chosen = random.choice(tells_pool)
        # Pick 1-2 extra tells
        extra = random.sample([t[0] for t in tells_pool if t[0] != chosen[0]], min(1, len(tells_pool) - 1))
        all_tells = [chosen[0]] + extra

        return chosen[1], all_tells

    def _check_for_deadline(self, fa_dict: dict, year: int, week: int) -> NegotiationDeadline:
        """Step 140 – Check if this negotiation has a hard deadline"""
        d = NegotiationDeadline()

        # 30% chance a rival promotion has an active offer
        if random.random() < 0.30:
            rivals = ["Dynasty Pro", "Pinnacle Wrestling", "Apex Federation"]
            rival  = random.choice(rivals)
            mv     = fa_dict.get('market_value', 50000)

            d.has_deadline      = True
            d.rival_offer_rival = rival
            d.rival_offer_value = int(mv * random.uniform(0.85, 1.15)) * 52 * 3
            d.deadline_week     = week + random.randint(2, 6)
            d.deadline_year     = year
            d.deadline_label    = f"{rival} offer expires"

        return d

    def _preferred_length(self, role: str) -> int:
        """Wrestlers prefer different contract lengths based on role"""
        return {
            "Main Event":     104,
            "Upper Midcard":   78,
            "Midcard":         52,
            "Lower Midcard":   52,
            "Jobber":          26,
        }.get(role, 52)

    def _generate_counter_note(self, session: NegotiationSession, ratio: float) -> str:
        """Step 136 – Generate a contextual counter-offer note"""
        if ratio < 0.75:
            notes = [
                f"That salary is nowhere near what I'm worth.",
                f"I expected a serious offer. This isn't it.",
                f"Come back when you're ready to be serious.",
            ]
        elif ratio < 0.95:
            notes = [
                f"I'm close, but I need something more.",
                f"We're in the same ballpark, let's work something out.",
                f"Almost there – but the salary needs to improve.",
            ]
        else:
            notes = [
                f"I appreciate the offer. I just need one or two things adjusted.",
                f"This is pretty close to what I'm looking for.",
            ]

        focus_notes = {
            NegotiationTell.CREATIVE_CONTROL: " I also need creative input – that's non-negotiable.",
            NegotiationTell.TITLE_HUNGER:     " And I need a clear path to a championship.",
            NegotiationTell.SCHEDULE_FOCUS:   " I also need a lighter schedule – my body needs it.",
            NegotiationTell.LIFESTYLE:        " The travel and lifestyle terms need improving too.",
        }

        note = random.choice(notes)
        note += focus_notes.get(session.priority_focus, "")
        return note

    def _reveal_tell_from_counter(self, session: NegotiationSession, counter: NegotiationOffer) -> str:
        """Step 138 – Reveal which area the wrestler pushed on"""
        tells = []
        latest_yours = session.promotion_offers()[-1] if session.promotion_offers() else None

        if latest_yours and counter.salary_per_show > latest_yours.salary_per_show:
            tells.append("💰 Salary is still the sticking point.")
        if counter.creative_clauses.creative_control != CreativeControlLevel.NONE:
            tells.append("🎬 Creative control is important to them.")
        if counter.creative_clauses.title_guarantee:
            tells.append("🏆 They want a clear title opportunity.")
        if counter.lifestyle_clauses.max_appearances_per_year > 0:
            tells.append("📅 They're asking for a limited schedule.")
        if counter.lifestyle_clauses.injury_pay_protection:
            tells.append("🏥 Injury protection is a priority.")

        return " | ".join(tells) if tells else "No clear priority revealed."

    def _build_recommendation(
        self,
        session: NegotiationSession,
        offer: NegotiationOffer,
        prob: float,
        ratio: float,
    ) -> str:
        if prob >= 80:
            return "Offer is strong – likely to be accepted."
        elif prob >= 60:
            return "Decent offer. Consider adding a signing bonus or creative incentive to improve odds."
        elif prob >= 40:
            if ratio < 0.9:
                return f"Salary needs to rise to at least ${int(session.asking_price * 0.95):,}/show."
            return "Add lifestyle clauses or title guarantees to sweeten the deal."
        else:
            return "Offer is too far below expectations. Significant salary increase required."


# ─────────────────────────────────────────────
# Singleton instance
# ─────────────────────────────────────────────
negotiation_engine = NegotiationEngine()