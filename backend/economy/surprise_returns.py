"""
Surprise Returns Engine — Steps 198-207

Step 198: Secret Signing Mechanics
Step 199: Debut Engineering (timing, show selection, opponent selection)
Step 200: Surprise Debut Impact Calculation
Step 201: Forbidden Door Scenarios (cross-promotional appearances)
Step 202: Cross-Promotional Relationship Tracking
Step 203: Forbidden Door Negotiation
Step 204: Secret Keeping — rumour leak risk
Step 205: Failed Secret — managing premature reveals
Step 206: Post-Debut Booking Windows
Step 207: Surprise Return Booking Momentum
"""

import random
import uuid
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


# ============================================================================
# STEP 198: Secret Signing Status
# ============================================================================

class SecretSigningStatus(Enum):
    PLANNING     = "planning"      # Internally decided, no contract yet
    NEGOTIATING  = "negotiating"   # Actively in contract talks (secret)
    SIGNED       = "signed"        # Contract signed, identity hidden
    LEAKED       = "leaked"        # Secret got out early
    REVEALED     = "revealed"      # Official announcement made
    CANCELLED    = "cancelled"     # Signing fell through

    @property
    def label(self) -> str:
        return self.value.title()


class SecretLevel(Enum):
    PUBLIC       = "public"        # Not actually secret — announced signing
    LOOSE        = "loose"         # A few people know; leaks likely
    TIGHT        = "tight"         # Limited circle; manageable leak risk
    IRON_CLAD    = "iron_clad"     # Extreme NDA; very hard to leak

    @property
    def weekly_leak_chance(self) -> int:
        """0-100: chance per week of a leak occurring."""
        chances = {"public": 0, "loose": 45, "tight": 15, "iron_clad": 4}
        return chances[self.value]

    @property
    def label(self) -> str:
        return self.value.replace("_", " ").title()


# ============================================================================
# STEP 204: Secret Keeping — Rumour Leak Engine
# ============================================================================

LEAK_SOURCES = [
    "A crew member spotted them at the arena during a dark match rehearsal.",
    "Their agent was seen dining with your booker — wrestling press picked it up.",
    "Backstage photo emerged on social media before it was deleted.",
    "A fellow roster member accidentally mentioned the signing on a podcast.",
    "Arena staff in the city let it slip to a local reporter.",
    "A plane ticket in their name was spotted to your next TV taping city.",
    "Their merchandise was found in an internal inventory document that leaked.",
    "Old contract paperwork surfaced on a wrestling forum.",
]


@dataclass
class LeakEvent:
    """Step 204: A secret got out — partial or full."""
    source:         str  = ""
    is_confirmed:   bool = False   # False = rumour, True = confirmed leak
    fan_awareness:  int  = 0       # 0-100: how widely known is it?
    media_coverage: str  = "low"   # "low"|"moderate"|"high"
    week_occurred:  int  = 0
    year_occurred:  int  = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source":         self.source,
            "is_confirmed":   self.is_confirmed,
            "fan_awareness":  self.fan_awareness,
            "media_coverage": self.media_coverage,
            "week_occurred":  self.week_occurred,
            "year_occurred":  self.year_occurred,
        }


# ============================================================================
# STEP 198-200: Secret Signing
# ============================================================================

@dataclass
class SecretSigning:
    """
    Steps 198-200: Full lifecycle of a secret signing, from planning through debut.
    """
    signing_id:      str             = field(default_factory=lambda: str(uuid.uuid4())[:12])
    fa_id:           str             = ""
    wrestler_name:   str             = ""
    status:          SecretSigningStatus = SecretSigningStatus.PLANNING
    secret_level:    SecretLevel     = SecretLevel.TIGHT
    weeks_kept:      int             = 0

    # Debut planning (Step 199)
    planned_show:        str  = ""
    planned_week:        int  = 0
    planned_year:        int  = 1
    planned_opponent_id: str  = ""   # FA_id or wrestler_id of planned debut opponent
    planned_opponent_name: str = ""

    # Leak tracking (Step 204)
    leak_events:     List[LeakEvent] = field(default_factory=list)
    total_fan_awareness: int         = 0   # 0-100 cumulative

    # Contract details
    salary_per_show: int  = 0
    contract_weeks:  int  = 52
    signing_bonus:   int  = 0

    def advance_week(self, current_year: int, current_week: int) -> Dict[str, Any]:
        """Step 204: Process one week — check for leaks, advance countdown."""
        self.weeks_kept += 1
        events = []

        # Roll for leak
        leak_roll = random.randint(1, 100)
        if leak_roll <= self.secret_level.weekly_leak_chance:
            leak = LeakEvent(
                source       = random.choice(LEAK_SOURCES),
                is_confirmed = leak_roll <= self.secret_level.weekly_leak_chance // 3,
                fan_awareness = random.randint(15, 50),
                media_coverage = "high" if leak_roll <= 10 else "moderate",
                week_occurred  = current_week,
                year_occurred  = current_year,
            )
            self.leak_events.append(leak)
            self.total_fan_awareness = min(100, self.total_fan_awareness + leak.fan_awareness)

            if leak.is_confirmed:
                self.status = SecretSigningStatus.LEAKED
                events.append({
                    "type":    "CONFIRMED_LEAK",
                    "message": f"🚨 CONFIRMED LEAK: {self.wrestler_name}'s signing is now public knowledge. Source: {leak.source}",
                    "severity": "critical",
                })
            else:
                events.append({
                    "type":    "RUMOUR",
                    "message": f"📰 Rumour circulating about a mystery signing. {leak.source}",
                    "severity": "moderate",
                })

        return {
            "weeks_kept":      self.weeks_kept,
            "total_fan_awareness": self.total_fan_awareness,
            "status":          self.status.value,
            "events":          events,
        }

    def reveal(self, show_name: str, week: int, year: int) -> Dict[str, Any]:
        """Step 205: Official reveal / debut announcement."""
        self.status = SecretSigningStatus.REVEALED

        # Surprise value degrades with awareness
        surprise_value = max(0, 100 - self.total_fan_awareness)
        pop_modifier   = int(surprise_value * 0.3)  # Up to +30 to debut pop

        return {
            "revealed":       True,
            "show":           show_name,
            "surprise_value": surprise_value,
            "pop_modifier":   pop_modifier,
            "weeks_secret":   self.weeks_kept,
            "leak_count":     len(self.leak_events),
            "message": (
                f"🎉 {self.wrestler_name} OFFICIALLY REVEALED at {show_name}! "
                + (f"Surprise value: {surprise_value}% — fans are SHOCKED!"
                   if surprise_value >= 70
                   else f"Word had got out, but the live crowd still pops. Surprise value: {surprise_value}%.")
            ),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signing_id":     self.signing_id,
            "fa_id":          self.fa_id,
            "wrestler_name":  self.wrestler_name,
            "status":         self.status.value,
            "status_label":   self.status.label,
            "secret_level":   self.secret_level.value,
            "secret_level_label": self.secret_level.label,
            "weekly_leak_chance": self.secret_level.weekly_leak_chance,
            "weeks_kept":     self.weeks_kept,
            "planned_show":   self.planned_show,
            "planned_week":   self.planned_week,
            "planned_year":   self.planned_year,
            "planned_opponent_name": self.planned_opponent_name,
            "leak_events":    [l.to_dict() for l in self.leak_events],
            "total_fan_awareness": self.total_fan_awareness,
            "salary_per_show": self.salary_per_show,
            "contract_weeks":  self.contract_weeks,
            "signing_bonus":   self.signing_bonus,
        }


# ============================================================================
# STEP 199-200: Debut Engineering
# ============================================================================

class DebutQuality(Enum):
    CATASTROPHIC = "catastrophic"   # Everything went wrong
    POOR         = "poor"
    AVERAGE      = "average"
    GOOD         = "good"
    GREAT        = "great"
    LEGENDARY    = "legendary"      # All-time debut moment

    @property
    def label(self) -> str:
        return self.value.title()

    @property
    def popularity_gain(self) -> int:
        gains = {
            "catastrophic": -15,
            "poor":         -5,
            "average":       5,
            "good":         12,
            "great":        20,
            "legendary":    35,
        }
        return gains[self.value]

    @property
    def momentum_weeks(self) -> int:
        """How many weeks of booking momentum the debut generates."""
        weeks = {
            "catastrophic":  0,
            "poor":          2,
            "average":       4,
            "good":          8,
            "great":        14,
            "legendary":    26,
        }
        return weeks[self.value]


@dataclass
class DebutEngineering:
    """
    Step 199: Design and score a debut for maximum impact.
    Integrates with show type, opponent quality, and crowd size.
    """
    wrestler_name:    str  = ""
    show_type:        str  = "weekly_tv"  # "weekly_tv"|"ppv"|"special_event"|"stadium"
    opponent_role:    str  = "midcard"    # "curtain_jerker"|"midcard"|"upper_midcard"|"main_event"
    crowd_size:       int  = 5000
    is_surprise:      bool = True         # Unannounced = higher pop potential
    has_vignette_buildup: bool = False    # Pre-debut video packages
    planned_result:   str  = "win"        # "win"|"loss"|"draw"|"interrupted"
    mystery_partner:  bool = False        # Debut as part of a mystery team

    def calculate_debut_score(self, popularity: int) -> int:
        """0-100: quality score for this debut configuration."""
        score = 40  # Baseline

        # Show type bonuses
        show_bonus = {
            "weekly_tv":     0,
            "ppv":          15,
            "special_event": 10,
            "stadium":       20,
        }
        score += show_bonus.get(self.show_type, 0)

        # Opponent quality (better opponent = bigger debut)
        opp_bonus = {
            "curtain_jerker": -10,
            "midcard":          0,
            "upper_midcard":   10,
            "main_event":      20,
        }
        score += opp_bonus.get(self.opponent_role, 0)

        # Crowd size bonus
        if self.crowd_size >= 50000: score += 20
        elif self.crowd_size >= 15000: score += 12
        elif self.crowd_size >= 8000: score += 6

        # Surprise factor
        if self.is_surprise: score += 15

        # Pre-debut buildup
        if self.has_vignette_buildup: score += 10

        # Mystery partner teases
        if self.mystery_partner: score += 8

        # Result matters
        if self.planned_result == "win": score += 5
        elif self.planned_result == "interrupted": score += 5
        elif self.planned_result == "loss": score -= 10

        # Their personal popularity amplifies everything
        score += int((popularity - 50) * 0.2)

        return max(0, min(100, score))

    def determine_quality(self, popularity: int) -> DebutQuality:
        score = self.calculate_debut_score(popularity)
        if score >= 85: return DebutQuality.LEGENDARY
        if score >= 70: return DebutQuality.GREAT
        if score >= 55: return DebutQuality.GOOD
        if score >= 40: return DebutQuality.AVERAGE
        if score >= 25: return DebutQuality.POOR
        return DebutQuality.CATASTROPHIC

    def to_dict(self, popularity: int = 50) -> Dict[str, Any]:
        quality = self.determine_quality(popularity)
        return {
            "wrestler_name":      self.wrestler_name,
            "show_type":          self.show_type,
            "opponent_role":      self.opponent_role,
            "crowd_size":         self.crowd_size,
            "is_surprise":        self.is_surprise,
            "has_vignette_buildup": self.has_vignette_buildup,
            "planned_result":     self.planned_result,
            "mystery_partner":    self.mystery_partner,
            "debut_score":        self.calculate_debut_score(popularity),
            "quality":            quality.value,
            "quality_label":      quality.label,
            "popularity_gain":    quality.popularity_gain,
            "momentum_weeks":     quality.momentum_weeks,
        }


# ============================================================================
# STEP 201-203: Forbidden Door / Cross-Promotional Scenarios
# ============================================================================

class ForbiddenDoorType(Enum):
    TALENT_LOAN       = "talent_loan"         # Lend a wrestler for one show
    TALENT_BORROW     = "talent_borrow"       # Borrow a wrestler from rival
    CO_PROMOTED_EVENT = "co_promoted_event"   # Full joint event
    TITLE_UNIFICATION = "title_unification"   # Champions meet across promotions
    DREAM_MATCH       = "dream_match"         # Iconic match crossing promotions

    @property
    def label(self) -> str:
        return self.value.replace("_", " ").title()

    @property
    def relationship_required(self) -> int:
        """Minimum relationship score with rival promotion (0-100)."""
        reqs = {
            "talent_loan":        40,
            "talent_borrow":      40,
            "co_promoted_event":  60,
            "title_unification":  70,
            "dream_match":        55,
        }
        return reqs[self.value]

    @property
    def base_cost(self) -> int:
        """Minimum cost to arrange this type of cross-promotional event."""
        costs = {
            "talent_loan":        10_000,
            "talent_borrow":      10_000,
            "co_promoted_event":  75_000,
            "title_unification":  50_000,
            "dream_match":        35_000,
        }
        return costs[self.value]


@dataclass
class ForbiddenDoorProposal:
    """
    Steps 201-203: A cross-promotional scenario between two promotions.
    """
    proposal_id:       str  = field(default_factory=lambda: str(uuid.uuid4())[:10])
    door_type:         ForbiddenDoorType = ForbiddenDoorType.DREAM_MATCH
    our_promotion:     str  = "Ring of Champions"
    rival_promotion_id: str = ""
    rival_promotion_name: str = ""

    # What's being exchanged
    our_wrestlers:     List[str] = field(default_factory=list)  # Names of our talent offered
    their_wrestlers:   List[str] = field(default_factory=list)  # Names of their talent

    # Terms (Step 203: Negotiation)
    our_payment:       int  = 0     # We pay them
    their_payment:     int  = 0     # They pay us
    net_cost:          int  = 0     # = our_payment - their_payment
    revenue_split_pct: int  = 50    # Our share of co-promoted event revenue
    creative_rights:   str  = "mutual"  # "ours"|"theirs"|"mutual"

    # Status tracking
    status:            str  = "proposed"  # "proposed"|"negotiating"|"agreed"|"cancelled"
    relationship_change: int = 0          # Expected relationship change after event

    # Event details
    event_name:        str  = ""
    event_week:        int  = 0
    event_year:        int  = 1
    expected_buyrate:  str  = "normal"

    def is_feasible(self, current_relationship: int) -> bool:
        """Step 201: Can this even be proposed given current relationship?"""
        return current_relationship >= self.door_type.relationship_required

    def calculate_net_cost(self) -> int:
        self.net_cost = self.our_payment - self.their_payment
        return self.net_cost

    def estimated_revenue(self) -> int:
        """Rough estimate of extra revenue from this event."""
        base = {
            "talent_loan":        5_000,
            "talent_borrow":      8_000,
            "co_promoted_event": 150_000,
            "title_unification":  80_000,
            "dream_match":        50_000,
        }.get(self.door_type.value, 10_000)

        buyrate_mod = {"low": 0.7, "normal": 1.0, "high": 1.4, "blockbuster": 2.0}
        return int(base * buyrate_mod.get(self.expected_buyrate, 1.0))

    def relationship_impact(self) -> int:
        """
        Step 202: How does completing this event affect the relationship?
        Success strengthens ties; cancellation damages them.
        """
        impacts = {
            "talent_loan":        5,
            "talent_borrow":      5,
            "co_promoted_event": 15,
            "title_unification": 10,
            "dream_match":       10,
        }
        return impacts.get(self.door_type.value, 5)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id":         self.proposal_id,
            "door_type":           self.door_type.value,
            "door_type_label":     self.door_type.label,
            "our_promotion":       self.our_promotion,
            "rival_promotion_id":  self.rival_promotion_id,
            "rival_promotion_name": self.rival_promotion_name,
            "our_wrestlers":       self.our_wrestlers,
            "their_wrestlers":     self.their_wrestlers,
            "our_payment":         self.our_payment,
            "their_payment":       self.their_payment,
            "net_cost":            self.calculate_net_cost(),
            "revenue_split_pct":   self.revenue_split_pct,
            "creative_rights":     self.creative_rights,
            "status":              self.status,
            "relationship_required": self.door_type.relationship_required,
            "relationship_impact": self.relationship_impact(),
            "event_name":          self.event_name,
            "event_week":          self.event_week,
            "event_year":          self.event_year,
            "expected_buyrate":    self.expected_buyrate,
            "estimated_revenue":   self.estimated_revenue(),
            "base_cost_minimum":   self.door_type.base_cost,
        }


# ============================================================================
# STEP 205: Failed Secret / Premature Reveal Management
# ============================================================================

def handle_premature_reveal(
    signing: SecretSigning,
    reveal_week: int,
    reveal_year: int,
    weeks_until_planned_debut: int,
) -> Dict[str, Any]:
    """
    Step 205: The secret got out early. Evaluate damage and options.
    """
    fan_awareness = signing.total_fan_awareness
    leak_count    = len(signing.leak_events)

    # Damage assessment
    surprise_lost  = min(100, fan_awareness + leak_count * 10)
    pop_penalty    = int(surprise_lost * 0.25)  # Max 25 point debut pop penalty

    options = []
    if weeks_until_planned_debut > 4:
        options.append({
            "option":      "accelerate_debut",
            "description": "Rush the debut to beat further leaks. Lose some setup but limit damage.",
            "cost":        0,
            "pop_penalty": pop_penalty // 2,
        })
    options.append({
        "option":      "lean_into_it",
        "description": "Officially announce and build hype for the remaining weeks. Turn leak into a feature.",
        "cost":        10_000,
        "pop_penalty": 0,
    })
    options.append({
        "option":      "deny_and_delay",
        "description": "Publicly deny (risky if the leak is confirmed). Buy time for the planned debut.",
        "cost":        5_000,
        "pop_penalty": pop_penalty,
        "credibility_risk": "high",
    })
    options.append({
        "option":      "no_comment",
        "description": "Say nothing. Ambiguity builds its own hype.",
        "cost":        0,
        "pop_penalty": pop_penalty // 3,
    })

    return {
        "fan_awareness":   fan_awareness,
        "surprise_lost":   surprise_lost,
        "pop_penalty":     pop_penalty,
        "weeks_remaining": weeks_until_planned_debut,
        "management_options": options,
        "recommendation": (
            "lean_into_it" if surprise_lost >= 60
            else "no_comment" if weeks_until_planned_debut <= 2
            else "accelerate_debut"
        ),
    }


# ============================================================================
# STEP 206-207: Post-Debut Booking Windows & Momentum
# ============================================================================

@dataclass
class DebutMomentum:
    """
    Steps 206-207: Track the booking momentum window generated by a debut.
    Tells the game how long the hot streak should last.
    """
    wrestler_id:    str = ""
    wrestler_name:  str = ""
    quality:        DebutQuality = DebutQuality.GOOD
    weeks_remaining: int = 0
    momentum_score: int = 50   # 0-100

    # Step 207: What to book during the window
    booking_recommendations: List[str] = field(default_factory=list)

    def advance_week(self) -> Dict[str, Any]:
        self.weeks_remaining = max(0, self.weeks_remaining - 1)
        self.momentum_score  = max(0, self.momentum_score - 5)
        is_expired = self.weeks_remaining == 0
        return {
            "weeks_remaining": self.weeks_remaining,
            "momentum_score":  self.momentum_score,
            "expired":         is_expired,
            "warning": (
                f"⚠️ {self.wrestler_name}'s debut momentum expires in {self.weeks_remaining} week(s)! Book them now!"
                if 1 <= self.weeks_remaining <= 3 else None
            ),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "wrestler_id":    self.wrestler_id,
            "wrestler_name":  self.wrestler_name,
            "quality":        self.quality.value,
            "quality_label":  self.quality.label,
            "weeks_remaining": self.weeks_remaining,
            "momentum_score": self.momentum_score,
            "booking_recommendations": self.booking_recommendations,
        }

    @staticmethod
    def create_from_debut(
        wrestler_id: str,
        wrestler_name: str,
        quality: DebutQuality,
    ) -> "DebutMomentum":
        dm = DebutMomentum(
            wrestler_id    = wrestler_id,
            wrestler_name  = wrestler_name,
            quality        = quality,
            weeks_remaining = quality.momentum_weeks,
            momentum_score  = min(100, 50 + quality.popularity_gain),
        )
        # Step 207: Booking recommendations based on debut quality
        recs_by_quality = {
            DebutQuality.LEGENDARY: [
                "Book in a championship match within 4 weeks.",
                "Feature in the main event of next PPV.",
                "Build an immediate feud with the top heel.",
            ],
            DebutQuality.GREAT: [
                "Feature on PPV within 8 weeks.",
                "Begin building a rivalry with a credible opponent.",
                "Consider a title shot within 10 weeks.",
            ],
            DebutQuality.GOOD: [
                "Keep them winning strong for 6 weeks.",
                "Introduce them to a feud within 4 weeks.",
                "PPV spot within 12 weeks.",
            ],
            DebutQuality.AVERAGE: [
                "Build with wins over enhancement talent first.",
                "Feud development within 8 weeks.",
            ],
            DebutQuality.POOR: [
                "Reset booking approach — rebuild credibility.",
                "Avoid big losses for the next 8 weeks.",
            ],
            DebutQuality.CATASTROPHIC: [
                "Consider repackaging character entirely.",
                "Use to build an existing superstar over them.",
            ],
        }
        dm.booking_recommendations = recs_by_quality.get(quality, [])
        return dm


# ============================================================================
# In-memory store for active secret signings and forbidden door proposals
# ============================================================================

class SurpriseReturnsEngine:
    """
    Central manager for Steps 198-207.
    Tracks all active secret signings, forbidden door proposals,
    and debut momentum windows.
    """

    def __init__(self):
        self._secret_signings: Dict[str, SecretSigning]        = {}
        self._fd_proposals:    Dict[str, ForbiddenDoorProposal] = {}
        self._debut_momentum:  Dict[str, DebutMomentum]        = {}

    # ---------------------------------------------------------------- Signings
    def create_secret_signing(
        self,
        fa_id: str,
        wrestler_name: str,
        secret_level: str,
        salary: int,
        weeks: int,
        bonus: int,
        planned_show: str,
        planned_week: int,
        planned_year: int,
        planned_opponent_name: str = "",
    ) -> SecretSigning:
        try:
            level = SecretLevel(secret_level)
        except ValueError:
            level = SecretLevel.TIGHT

        signing = SecretSigning(
            fa_id                  = fa_id,
            wrestler_name          = wrestler_name,
            status                 = SecretSigningStatus.SIGNED,
            secret_level           = level,
            salary_per_show        = salary,
            contract_weeks         = weeks,
            signing_bonus          = bonus,
            planned_show           = planned_show,
            planned_week           = planned_week,
            planned_year           = planned_year,
            planned_opponent_name  = planned_opponent_name,
        )
        self._secret_signings[signing.signing_id] = signing
        return signing

    def get_signing(self, signing_id: str) -> Optional[SecretSigning]:
        return self._secret_signings.get(signing_id)

    def get_all_signings(self) -> List[SecretSigning]:
        return list(self._secret_signings.values())

    def advance_week_all_signings(self, year: int, week: int) -> List[Dict[str, Any]]:
        events = []
        for signing in self._secret_signings.values():
            if signing.status in (SecretSigningStatus.SIGNED, SecretSigningStatus.PLANNING):
                result = signing.advance_week(year, week)
                for e in result.get("events", []):
                    e["signing_id"]    = signing.signing_id
                    e["wrestler_name"] = signing.wrestler_name
                    events.append(e)
        return events

    def reveal_signing(
        self, signing_id: str, show_name: str, week: int, year: int
    ) -> Dict[str, Any]:
        signing = self.get_signing(signing_id)
        if not signing:
            return {"success": False, "error": "Signing not found"}
        result = signing.reveal(show_name, week, year)
        return {"success": True, **result, "signing": signing.to_dict()}

    # --------------------------------------------------------- Forbidden Door
    def create_fd_proposal(
        self,
        door_type: str,
        rival_promotion_id: str,
        rival_promotion_name: str,
        our_wrestlers: List[str],
        their_wrestlers: List[str],
        our_payment: int,
        their_payment: int,
        event_name: str,
        event_week: int,
        event_year: int,
        revenue_split_pct: int = 50,
    ) -> ForbiddenDoorProposal:
        try:
            dt = ForbiddenDoorType(door_type)
        except ValueError:
            dt = ForbiddenDoorType.DREAM_MATCH

        proposal = ForbiddenDoorProposal(
            door_type            = dt,
            rival_promotion_id   = rival_promotion_id,
            rival_promotion_name = rival_promotion_name,
            our_wrestlers        = our_wrestlers,
            their_wrestlers      = their_wrestlers,
            our_payment          = our_payment,
            their_payment        = their_payment,
            revenue_split_pct    = revenue_split_pct,
            event_name           = event_name,
            event_week           = event_week,
            event_year           = event_year,
            status               = "proposed",
        )
        self._fd_proposals[proposal.proposal_id] = proposal
        return proposal

    def get_fd_proposal(self, proposal_id: str) -> Optional[ForbiddenDoorProposal]:
        return self._fd_proposals.get(proposal_id)

    def get_all_fd_proposals(self) -> List[ForbiddenDoorProposal]:
        return list(self._fd_proposals.values())

    def agree_fd_proposal(self, proposal_id: str) -> Dict[str, Any]:
        proposal = self.get_fd_proposal(proposal_id)
        if not proposal:
            return {"success": False, "error": "Proposal not found"}
        proposal.status = "agreed"
        return {"success": True, "proposal": proposal.to_dict()}

    def cancel_fd_proposal(self, proposal_id: str) -> Dict[str, Any]:
        proposal = self.get_fd_proposal(proposal_id)
        if not proposal:
            return {"success": False, "error": "Proposal not found"}
        proposal.status = "cancelled"
        return {
            "success": True,
            "proposal": proposal.to_dict(),
            "relationship_impact": -proposal.relationship_impact(),  # Cancelling hurts
        }

    # -------------------------------------------------------- Debut Momentum
    def record_debut(
        self,
        wrestler_id: str,
        wrestler_name: str,
        debut_config: DebutEngineering,
        popularity: int,
    ) -> DebutMomentum:
        quality = debut_config.determine_quality(popularity)
        dm = DebutMomentum.create_from_debut(wrestler_id, wrestler_name, quality)
        self._debut_momentum[wrestler_id] = dm
        return dm

    def get_momentum(self, wrestler_id: str) -> Optional[DebutMomentum]:
        return self._debut_momentum.get(wrestler_id)

    def advance_week_momentum(self) -> List[Dict[str, Any]]:
        expired  = []
        warnings = []
        for wid, dm in list(self._debut_momentum.items()):
            result = dm.advance_week()
            if result["expired"]:
                expired.append({"wrestler_id": wid, "wrestler_name": dm.wrestler_name})
                del self._debut_momentum[wid]
            elif result.get("warning"):
                warnings.append({
                    "wrestler_id":   wid,
                    "wrestler_name": dm.wrestler_name,
                    "message":       result["warning"],
                })
        return expired + warnings

    def summary(self) -> Dict[str, Any]:
        return {
            "active_secret_signings": len([
                s for s in self._secret_signings.values()
                if s.status in (SecretSigningStatus.SIGNED, SecretSigningStatus.PLANNING)
            ]),
            "leaked_signings": len([
                s for s in self._secret_signings.values()
                if s.status == SecretSigningStatus.LEAKED
            ]),
            "active_fd_proposals": len([
                p for p in self._fd_proposals.values()
                if p.status in ("proposed", "negotiating", "agreed")
            ]),
            "active_debut_momentum": len(self._debut_momentum),
        }


# Module-level singleton
surprise_returns_engine = SurpriseReturnsEngine()