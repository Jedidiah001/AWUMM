"""
Morale Simulation Engine
Steps 224-244: Morale fundamentals + positive & negative influences

Covers:
- Step 224: Individual morale tracking (0-100)
- Step 225: Morale score visibility & categories
- Step 226: Morale component breakdown
- Step 227: Hidden morale factors
- Step 228: Morale momentum
- Step 229: Push satisfaction
- Step 230: Win-loss ratio impact
- Step 231: Championship opportunities
- Step 232: Quality match experiences
- Step 233: Promo time allocation
- Step 234: Merchandise success
- Step 235: Peer respect
- Step 236: Management appreciation
- Step 237: Being Buried (burial detection)
- Step 238: Creative Frustration (stale booking)
- Step 239: Underutilization (too few appearances)
- Step 240: Overwork Burnout (too many appearances, travel fatigue)
- Step 241: Pay Grievances (underpaid vs market value)
- Step 242: Promise Breaking (broken creative commitments)
- Step 243: Disrespectful Treatment (public embarrassment, humiliation angles)
- Step 244: Personal Conflicts (locker room feuds with specific wrestlers)
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


# ============================================================================
# Step 225: Morale Categories
# ============================================================================

class MoraleCategory(Enum):
    ECSTATIC  = "Ecstatic"    # 90-100
    HAPPY     = "Happy"       # 70-89
    CONTENT   = "Content"     # 50-69
    UNHAPPY   = "Unhappy"     # 30-49
    MISERABLE = "Miserable"   # 0-29

    @staticmethod
    def from_score(score: int) -> 'MoraleCategory':
        if score >= 90:   return MoraleCategory.ECSTATIC
        elif score >= 70: return MoraleCategory.HAPPY
        elif score >= 50: return MoraleCategory.CONTENT
        elif score >= 30: return MoraleCategory.UNHAPPY
        else:             return MoraleCategory.MISERABLE

    @property
    def color(self) -> str:
        return {
            "Ecstatic":  "#00c851",
            "Happy":     "#33b5e5",
            "Content":   "#ffbb33",
            "Unhappy":   "#ff8800",
            "Miserable": "#ff4444",
        }[self.value]

    @property
    def emoji(self) -> str:
        return {
            "Ecstatic":  "😄",
            "Happy":     "🙂",
            "Content":   "😐",
            "Unhappy":   "😞",
            "Miserable": "😡",
        }[self.value]


# ============================================================================
# Step 226: Morale Component Breakdown
# ============================================================================

@dataclass
class MoraleComponents:
    """
    Eight weighted factors that produce the final morale score.
    Weights sum to 1.0.
    """
    push_satisfaction:          float = 50.0   # 25%
    win_loss_satisfaction:      float = 50.0   # 15%
    championship_satisfaction:  float = 50.0   # 20%
    match_quality_satisfaction: float = 50.0   # 10%
    promo_satisfaction:         float = 50.0   # 10%
    merch_satisfaction:         float = 50.0   #  5%
    peer_respect:               float = 50.0   #  5%
    management_appreciation:    float = 50.0   # 10%

    WEIGHTS = {
        'push_satisfaction':          0.25,
        'win_loss_satisfaction':      0.15,
        'championship_satisfaction':  0.20,
        'match_quality_satisfaction': 0.10,
        'promo_satisfaction':         0.10,
        'merch_satisfaction':         0.05,
        'peer_respect':               0.05,
        'management_appreciation':    0.10,
    }

    def compute_weighted_score(self) -> float:
        score = (
            self.push_satisfaction          * self.WEIGHTS['push_satisfaction'] +
            self.win_loss_satisfaction       * self.WEIGHTS['win_loss_satisfaction'] +
            self.championship_satisfaction   * self.WEIGHTS['championship_satisfaction'] +
            self.match_quality_satisfaction  * self.WEIGHTS['match_quality_satisfaction'] +
            self.promo_satisfaction          * self.WEIGHTS['promo_satisfaction'] +
            self.merch_satisfaction          * self.WEIGHTS['merch_satisfaction'] +
            self.peer_respect                * self.WEIGHTS['peer_respect'] +
            self.management_appreciation     * self.WEIGHTS['management_appreciation']
        )
        return max(0.0, min(100.0, score))

    def to_dict(self) -> dict:
        return {
            'push_satisfaction':          round(self.push_satisfaction, 1),
            'win_loss_satisfaction':      round(self.win_loss_satisfaction, 1),
            'championship_satisfaction':  round(self.championship_satisfaction, 1),
            'match_quality_satisfaction': round(self.match_quality_satisfaction, 1),
            'promo_satisfaction':         round(self.promo_satisfaction, 1),
            'merch_satisfaction':         round(self.merch_satisfaction, 1),
            'peer_respect':               round(self.peer_respect, 1),
            'management_appreciation':    round(self.management_appreciation, 1),
            'weighted_total':             round(self.compute_weighted_score(), 1),
        }


# ============================================================================
# Step 228: Morale Momentum
# ============================================================================

@dataclass
class MoraleMomentum:
    """
    Tracks the direction morale is trending.
    Positive momentum buffers against single bad events.
    Negative momentum amplifies bad experiences.
    """
    value:                float = 0.0    # -50 to +50
    consecutive_positive: int   = 0
    consecutive_negative: int   = 0

    def update(self, morale_delta: float):
        if morale_delta > 0:
            self.consecutive_positive += 1
            self.consecutive_negative  = 0
            self.value = min(50.0, self.value + morale_delta * 0.3)
        elif morale_delta < 0:
            self.consecutive_negative += 1
            self.consecutive_positive  = 0
            self.value = max(-50.0, self.value + morale_delta * 0.3)
        self.value *= 0.95   # Decay toward zero each week

    def get_buffer(self) -> float:
        """
        Multiplier applied to negative deltas.
        < 1.0 = buffer (positive momentum softens blows)
        > 1.0 = amplifier (negative momentum makes things worse)
        """
        if   self.value >= 30:  return 0.50
        elif self.value >= 10:  return 0.75
        elif self.value >= -10: return 1.00
        elif self.value >= -30: return 1.25
        else:                   return 1.50

    def to_dict(self) -> dict:
        return {
            'value':                round(self.value, 1),
            'consecutive_positive': self.consecutive_positive,
            'consecutive_negative': self.consecutive_negative,
            'buffer_multiplier':    self.get_buffer(),
            'trend': 'Rising' if self.value > 5 else 'Falling' if self.value < -5 else 'Stable',
        }


# ============================================================================
# Step 227: Hidden Morale Factors
# ============================================================================

@dataclass
class HiddenMoraleFactors:
    """
    Factors not directly visible to the player.
    Revealed only through events or hint messages.
    """
    personal_life_stress:  float = 0.0   # -20 to  0
    culture_fit:           float = 0.0   # -15 to +15
    unspoken_expectations: float = 0.0   # -25 to  0
    career_anxiety:        float = 0.0   # -20 to  0

    def total_hidden_effect(self) -> float:
        return (
            self.personal_life_stress +
            self.culture_fit +
            self.unspoken_expectations +
            self.career_anxiety
        )

    def to_dict(self) -> dict:
        total = self.total_hidden_effect()
        return {
            'total_hidden_effect': round(total, 1),
            'hint': self._get_hint(),
        }

    def _get_hint(self) -> str:
        t = self.total_hidden_effect()
        if   t <= -40: return "Something significant is troubling them beyond work matters."
        elif t <= -20: return "There may be personal factors affecting their happiness."
        elif t <=  -5: return "Minor off-screen factors slightly affecting mood."
        elif t >=  10: return "They seem particularly well-suited to this environment."
        else:          return "No unusual hidden factors detected."


# ============================================================================
# Main Morale Record — one per wrestler
# ============================================================================

@dataclass
class WrestlerMoraleRecord:
    """Complete morale tracking for one wrestler, persisted to DB."""
    wrestler_id:   str
    wrestler_name: str
    morale_score:  float = 50.0

    components:     MoraleComponents    = field(default_factory=MoraleComponents)
    momentum:       MoraleMomentum      = field(default_factory=MoraleMomentum)
    hidden_factors: HiddenMoraleFactors = field(default_factory=HiddenMoraleFactors)

    recent_events:       List[dict] = field(default_factory=list)
    last_processed_week: int        = 0
    last_processed_year: int        = 1

    # Step 236 appreciation events stored on record
    _appreciation_events: List = field(default_factory=list)

    @property
    def category(self) -> MoraleCategory:
        return MoraleCategory.from_score(int(self.morale_score))

    def add_morale_event(self, event_type: str, description: str, delta: float,
                         component: Optional[str] = None):
        """Record a morale event, apply momentum buffer, update score."""
        if delta < 0:
            delta = delta * self.momentum.get_buffer()
        self.momentum.update(delta)
        self.morale_score = max(0.0, min(100.0, self.morale_score + delta))
        self.recent_events.insert(0, {
            'type':            event_type,
            'description':     description,
            'delta':           round(delta, 1),
            'component':       component,
            'resulting_score': round(self.morale_score, 1),
        })
        if len(self.recent_events) > 10:
            self.recent_events.pop()

    def recalculate_from_components(self):
        """Recalculate morale_score from components + hidden factors."""
        base   = self.components.compute_weighted_score()
        hidden = self.hidden_factors.total_hidden_effect()
        self.morale_score = max(0.0, min(100.0, base + hidden))

    def to_dict(self) -> dict:
        cat = self.category
        return {
            'wrestler_id':    self.wrestler_id,
            'wrestler_name':  self.wrestler_name,
            'morale_score':   round(self.morale_score, 1),
            'category':       cat.value,
            'category_color': cat.color,
            'category_emoji': cat.emoji,
            'components':     self.components.to_dict(),
            'momentum':       self.momentum.to_dict(),
            'hidden_factors': self.hidden_factors.to_dict(),
            'recent_events':  self.recent_events[:5],
        }


# ============================================================================
# Step 229: Push Satisfaction Engine
# ============================================================================

class PushSatisfactionEngine:
    """
    Wrestlers want pushes appropriate to their career stage.
    Main eventers expect world title pictures.
    Midcarders want meaningful secondary feuds.
    Newcomers appreciate development opportunities.
    """

    ROLE_PUSH_EXPECTATIONS = {
        'Main Event':    {'min_card_position': 0.70, 'expected_win_rate': 0.85, 'title_freq_weeks': 12},
        'Upper Midcard': {'min_card_position': 0.50, 'expected_win_rate': 0.75, 'title_freq_weeks': 24},
        'Midcard':       {'min_card_position': 0.30, 'expected_win_rate': 0.60, 'title_freq_weeks': 52},
        'Lower Midcard': {'min_card_position': 0.10, 'expected_win_rate': 0.50, 'title_freq_weeks': 999},
        'Jobber':        {'min_card_position': 0.00, 'expected_win_rate': 0.30, 'title_freq_weeks': 999},
    }

    @staticmethod
    def calculate(
        wrestler_role: str,
        recent_card_positions: List[float],       # 0.0=opener, 1.0=main event
        recent_wins: int,
        recent_losses: int,
        weeks_since_last_title_shot: Optional[int],
        weeks_since_last_appearance: int,
    ) -> Tuple[float, str]:

        exp   = PushSatisfactionEngine.ROLE_PUSH_EXPECTATIONS.get(
            wrestler_role,
            PushSatisfactionEngine.ROLE_PUSH_EXPECTATIONS['Jobber']
        )
        score   = 50.0
        reasons = []

        # Card position
        if recent_card_positions:
            avg_pos = sum(recent_card_positions) / len(recent_card_positions)
            min_pos = exp['min_card_position']
            if   avg_pos >= min_pos + 0.20: score += 15; reasons.append("Above expected card position")
            elif avg_pos >= min_pos:        score +=  5; reasons.append("Meeting card position expectations")
            elif avg_pos >= min_pos - 0.15: score -= 10; reasons.append("Slightly below expected position")
            else:                           score -= 25; reasons.append("Significantly underused on cards")
        elif weeks_since_last_appearance > 4:
            score -= 30
            reasons.append(f"No appearances in {weeks_since_last_appearance} weeks")

        # Win rate
        total = recent_wins + recent_losses
        if total > 0:
            win_rate = recent_wins / total
            exp_rate = exp['expected_win_rate']
            if   win_rate >= exp_rate + 0.15: score += 10; reasons.append("Winning more than expected")
            elif win_rate >= exp_rate - 0.10: score +=  3; reasons.append("Win rate on target")
            elif win_rate >= exp_rate - 0.25: score -= 12; reasons.append("Losing more than role warrants")
            else:                             score -= 22; reasons.append("Being buried in win/loss record")

        # Title shot frequency
        if wrestler_role in ['Main Event', 'Upper Midcard']:
            freq = exp['title_freq_weeks']
            if weeks_since_last_title_shot is None or weeks_since_last_title_shot > freq * 1.5:
                penalty = -20 if wrestler_role == 'Main Event' else -10
                score  += penalty
                reasons.append("No title opportunity for too long")
            elif weeks_since_last_title_shot <= freq:
                score += 10
                reasons.append("Regular title opportunities")

        return max(0.0, min(100.0, score)), "; ".join(reasons) or "Push level acceptable"


# ============================================================================
# Step 230: Win/Loss Ratio Impact
# ============================================================================

class WinLossImpactEngine:
    """
    Context-sensitive win/loss satisfaction.
    Meaningful wins over worthy opponents matter more than squash wins.
    Losses to bigger stars hurt less than losses to nobodies.
    """

    ROLE_HIERARCHY = ['Jobber', 'Lower Midcard', 'Midcard', 'Upper Midcard', 'Main Event']

    @staticmethod
    def calculate(
        recent_results: List[dict],   # Each: {won, opponent_role, match_importance, was_title_match}
        wrestler_role: str,
    ) -> Tuple[float, str]:

        if not recent_results:
            return 50.0, "No recent match data"

        hier    = WinLossImpactEngine.ROLE_HIERARCHY
        my_rank = hier.index(wrestler_role) if wrestler_role in hier else 2

        score               = 50.0
        meaningful_wins     = 0
        demoralizing_losses = 0
        acceptable_losses   = 0

        for result in recent_results[-8:]:
            won       = result.get('won', False)
            opp_role  = result.get('opponent_role', 'Midcard')
            importance= result.get('match_importance', 'Normal')
            is_title  = result.get('was_title_match', False)
            opp_rank  = hier.index(opp_role) if opp_role in hier else 2
            rank_diff = opp_rank - my_rank   # positive = opponent is higher-ranked

            if won:
                if rank_diff > 0:
                    meaningful_wins += 1
                    score += 8 + rank_diff * 3
                elif rank_diff == 0:
                    score += 4
                else:
                    score += 1
                if is_title:
                    score += 5
            else:
                if rank_diff < 0:
                    demoralizing_losses += 1
                    score -= 15 + abs(rank_diff) * 5
                elif rank_diff == 0:
                    score -= 6
                else:
                    acceptable_losses += 1
                    score -= 3 if importance in ['High Drama', 'High Stakes'] else 7

        score = max(0.0, min(100.0, score))

        if   demoralizing_losses > 2: reason = f"Being fed to lower-tier talent ({demoralizing_losses} demoralizing losses)"
        elif meaningful_wins     > 2: reason = f"Strong wins over worthy opponents ({meaningful_wins} meaningful wins)"
        elif acceptable_losses   > 3: reason = "Losing competitive matches to top talent — acceptable"
        else:                         reason = "Mixed win/loss record"

        return score, reason


# ============================================================================
# Step 231: Championship Opportunity Satisfaction
# ============================================================================

class ChampionshipOpportunitySatisfaction:
    """
    Title reigns and shots boost morale significantly.
    Even failed challenges show the wrestler is valued.
    Long periods without title consideration cause decay.
    """

    @staticmethod
    def calculate(
        wrestler_role: str,
        is_current_champion: bool,
        weeks_as_champion: int,
        weeks_since_last_title_shot: Optional[int],
        total_title_reigns: int,
        years_experience: int,
    ) -> Tuple[float, str]:

        if is_current_champion:
            if   weeks_as_champion <=  4: return 90.0, "Recently won championship — elated"
            elif weeks_as_champion <= 12: return 85.0, "Active title reign"
            elif weeks_as_champion <= 26: return 80.0, "Established champion"
            else:                         return 75.0, "Long reign — comfortable but wanting fresh challenges"

        score   = 50.0
        reasons = []

        if wrestler_role in ['Main Event', 'Upper Midcard']:
            if weeks_since_last_title_shot is None:
                if years_experience < 2:
                    score = 60.0; reasons.append("Still building toward title opportunities")
                else:
                    score = 25.0; reasons.append("Never given a title opportunity despite experience")
            elif weeks_since_last_title_shot <=  8: score = 75.0; reasons.append("Recent title shot — feeling valued")
            elif weeks_since_last_title_shot <= 20: score = 60.0; reasons.append("In title picture — adequate")
            elif weeks_since_last_title_shot <= 36: score = 40.0; reasons.append("Overdue for title consideration")
            else:                                   score = 20.0; reasons.append("Completely ignored in title picture")

        elif wrestler_role == 'Midcard':
            if weeks_since_last_title_shot and weeks_since_last_title_shot <= 52:
                score = 70.0; reasons.append("Given title consideration above midcard expectations")
            else:
                score = 50.0; reasons.append("Not expecting title shots at current position")

        else:
            score = 55.0; reasons.append("Title competition not expected yet")

        if total_title_reigns > 0:
            score = min(score + min(total_title_reigns * 3, 15), 100.0)
            reasons.append(f"{total_title_reigns} career reign(s)")

        return max(0.0, min(100.0, score)), "; ".join(reasons) or "Title situation neutral"


# ============================================================================
# Step 232: Quality Match Experience Satisfaction
# ============================================================================

class MatchQualitySatisfaction:
    """Good matches make wrestlers happy; stinkers hurt professional pride."""

    @staticmethod
    def calculate(
        recent_star_ratings: List[float],
        had_moty_candidate: bool = False,
    ) -> Tuple[float, str]:

        if not recent_star_ratings:
            return 50.0, "No recent match data"

        avg  = sum(recent_star_ratings) / len(recent_star_ratings)
        best = max(recent_star_ratings)

        if   avg >= 4.0: score = 90.0; reason = f"Consistently excellent matches (avg {avg:.1f}★)"
        elif avg >= 3.5: score = 78.0; reason = f"Strong match quality (avg {avg:.1f}★)"
        elif avg >= 3.0: score = 65.0; reason = f"Good matches (avg {avg:.1f}★)"
        elif avg >= 2.5: score = 52.0; reason = f"Average match quality (avg {avg:.1f}★)"
        elif avg >= 2.0: score = 38.0; reason = f"Below-average quality (avg {avg:.1f}★)"
        else:            score = 25.0; reason = f"Poor quality — hurting professional pride (avg {avg:.1f}★)"

        if best >= 4.5:
            score  = min(100.0, score + 10)
            reason += "; had a standout classic"
        if had_moty_candidate:
            score  = min(100.0, score + 8)
            reason += "; match of the year candidate"

        return score, reason


# ============================================================================
# Step 233: Promo Time Allocation Satisfaction
# ============================================================================

class PromoTimeSatisfaction:
    """Wrestlers want mic time proportional to their position."""

    EXPECTED = {
        'Main Event':    {'min': 5, 'ideal': 10},
        'Upper Midcard': {'min': 2, 'ideal':  5},
        'Midcard':       {'min': 1, 'ideal':  3},
        'Lower Midcard': {'min': 0, 'ideal':  1},
        'Jobber':        {'min': 0, 'ideal':  0},
    }

    @staticmethod
    def calculate(
        wrestler_role: str,
        avg_promo_minutes_recent: float,
        weeks_since_last_promo: int,
    ) -> Tuple[float, str]:

        exp   = PromoTimeSatisfaction.EXPECTED.get(wrestler_role, PromoTimeSatisfaction.EXPECTED['Jobber'])
        ideal = exp['ideal']
        minimum = exp['min']

        if ideal == 0:
            return 55.0, "No promo expectations at current role"

        if weeks_since_last_promo > 6 and wrestler_role in ['Main Event', 'Upper Midcard']:
            return 20.0, f"No mic time in {weeks_since_last_promo} weeks"
        if weeks_since_last_promo > 10 and wrestler_role == 'Midcard':
            return 35.0, "Rarely given promo opportunities"

        if   avg_promo_minutes_recent >= ideal:   return 80.0, f"Good mic time ({avg_promo_minutes_recent:.1f} min avg)"
        elif avg_promo_minutes_recent >= minimum:  return 60.0, f"Adequate promo time ({avg_promo_minutes_recent:.1f} min avg)"
        elif avg_promo_minutes_recent >  0:        return 40.0, "Limited promo opportunities"
        else:                                      return 25.0, "No microphone time given"


# ============================================================================
# Step 234: Merchandise Success Satisfaction
# ============================================================================

class MerchandiseSatisfaction:
    """Strong merch sales validate the wrestler's connection with fans."""

    @staticmethod
    def calculate(
        merch_sales_rank: int,
        total_roster_size: int,
        merch_revenue_monthly: float,
    ) -> Tuple[float, str]:

        if total_roster_size == 0:
            return 50.0, "No merch data"

        pct = 1.0 - (merch_sales_rank / total_roster_size)

        if   pct >= 0.90: score = 90.0; reason = f"Top merch seller — fans love you (#{merch_sales_rank})"
        elif pct >= 0.70: score = 75.0; reason = f"Strong merch performer (#{merch_sales_rank})"
        elif pct >= 0.50: score = 60.0; reason = f"Average merch sales (#{merch_sales_rank})"
        elif pct >= 0.30: score = 45.0; reason = f"Below-average merch (#{merch_sales_rank})"
        else:             score = 30.0; reason = "Merchandise not connecting with fans"

        if   merch_revenue_monthly > 50000: score = min(100.0, score + 10); reason += f" | ${merch_revenue_monthly:,.0f}/mo"
        elif merch_revenue_monthly > 10000: score = min(100.0, score +  4)

        return score, reason


# ============================================================================
# Step 235: Peer Respect Satisfaction
# ============================================================================

class PeerRespectEngine:
    """Locker room respect provides social validation and morale."""

    REP_SCORES = {
        'Backstage Leader': 90.0,
        'Respected':        75.0,
        'Neutral':          55.0,
        'Disliked':         25.0,
        'Unknown':          50.0,
    }

    @staticmethod
    def calculate(
        years_experience: int,
        is_major_superstar: bool,
        recent_avg_star_rating: float,
        locker_room_rep: str,
        is_faction_leader: bool = False,
    ) -> Tuple[float, str]:

        score   = PeerRespectEngine.REP_SCORES.get(locker_room_rep, 50.0)
        reasons = [f"Locker room status: {locker_room_rep}"]

        if   years_experience >= 15: score = min(100.0, score + 8); reasons.append("Veteran status earns natural respect")
        elif years_experience >=  8: score = min(100.0, score + 3)

        if recent_avg_star_rating >= 3.5:
            score = min(100.0, score + 8)
            reasons.append("Known as a quality worker")

        if is_major_superstar: score = min(100.0, score + 5)
        if is_faction_leader:  score = min(100.0, score + 10); reasons.append("Respected as faction leader")

        return score, "; ".join(reasons)


# ============================================================================
# Step 236: Management Appreciation Engine
# ============================================================================

@dataclass
class ManagementAppreciationEvent:
    event_type:   str
    description:  str
    morale_boost: float
    week:         int
    year:         int


class ManagementAppreciationEngine:
    """
    Direct management communication and appreciation gestures boost morale.
    Each event has a boost that decays over time (Step 228 interaction).
    """

    APPRECIATION_EVENTS = {
        'verbal_praise':      {'boost': 8.0,   'decay_weeks': 4, 'description': 'Management personally praised your recent work'},
        'performance_bonus':  {'boost': 15.0,  'decay_weeks': 6, 'description': 'Received unexpected performance bonus'},
        'featured_in_promo':  {'boost': 10.0,  'decay_weeks': 3, 'description': 'Featured in major promotional material'},
        'promised_push':      {'boost': 20.0,  'decay_weeks': 8, 'description': 'Management promised an upcoming push'},
        'public_recognition': {'boost': 12.0,  'decay_weeks': 4, 'description': 'Publicly recognized on-show for achievements'},
        'creative_meeting':   {'boost': 8.0,   'decay_weeks': 5, 'description': 'Had a direct meeting about creative direction — feel heard'},
        'ignored':            {'boost': -15.0, 'decay_weeks': 0, 'description': 'Management has not communicated in weeks'},
    }

    @staticmethod
    def calculate(
        recent_appreciation_events: List[ManagementAppreciationEvent],
        weeks_since_any_contact: int,
        current_week: int,
        current_year: int,
    ) -> Tuple[float, str]:

        if weeks_since_any_contact > 8:
            score = max(0.0, 50.0 - (weeks_since_any_contact - 8) * 3)
            return score, f"Management has been silent for {weeks_since_any_contact} weeks"

        if not recent_appreciation_events:
            return 50.0, "No notable management interactions"

        score        = 50.0
        active_boosts = []

        for event in recent_appreciation_events:
            ev_def      = ManagementAppreciationEngine.APPRECIATION_EVENTS.get(event.event_type, {})
            decay_weeks = ev_def.get('decay_weeks', 4)
            boost       = event.morale_boost
            age_weeks   = (current_year - event.year) * 52 + (current_week - event.week)

            if age_weeks <= decay_weeks:
                decay_factor    = 1.0 - (age_weeks / max(decay_weeks, 1))
                effective_boost = boost * decay_factor
                score          += effective_boost
                active_boosts.append(f"{event.event_type} ({effective_boost:+.1f})")

        score  = max(0.0, min(100.0, score))
        reason = "Recent: " + ", ".join(active_boosts) if active_boosts else "No recent management contact"
        return score, reason

    @staticmethod
    def create_event(event_type: str, current_week: int, current_year: int) -> ManagementAppreciationEvent:
        ev_def = ManagementAppreciationEngine.APPRECIATION_EVENTS.get(event_type, {})
        return ManagementAppreciationEvent(
            event_type=event_type,
            description=ev_def.get('description', 'Management interaction'),
            morale_boost=ev_def.get('boost', 5.0),
            week=current_week,
            year=current_year,
        )


# ============================================================================
# Step 237: Being Buried Engine
# ============================================================================

class BurialDetectionEngine:
    """
    Step 237: Detects systematic burial patterns that devastate morale.

    Burial is distinct from a simple bad win/loss record — it is a pattern
    of booking that actively signals to the locker room that the company
    has no faith in the wrestler. Consecutive clean losses to lower-ranked
    opponents, removal from PPV cards, and sudden card-position drops are
    the hallmarks.

    This feeds into push_satisfaction (primary) and win_loss_satisfaction
    (secondary) as severe negative modifiers.
    """

    # Weeks of burial pattern before it compounds
    BURIAL_THRESHOLDS = {
        'Main Event':    {'consecutive_losses_to_lower': 2, 'ppv_miss_weeks': 6},
        'Upper Midcard': {'consecutive_losses_to_lower': 3, 'ppv_miss_weeks': 10},
        'Midcard':       {'consecutive_losses_to_lower': 4, 'ppv_miss_weeks': 16},
        'Lower Midcard': {'consecutive_losses_to_lower': 5, 'ppv_miss_weeks': 999},
        'Jobber':        {'consecutive_losses_to_lower': 999, 'ppv_miss_weeks': 999},
    }

    @staticmethod
    def calculate(
        wrestler_role: str,
        recent_results: List[dict],          # [{won, opponent_role, match_importance, finish_type}]
        weeks_since_ppv_match: Optional[int],# None = never
        previous_role: Optional[str],        # Role 8 weeks ago (detect demotions)
        weeks_at_current_role: int,          # How long at this role
    ) -> Tuple[float, str, bool]:
        """
        Returns (score_modifier, reason, is_buried).
        score_modifier is applied directly on top of push_satisfaction.
        is_buried flag triggers event logging.
        """
        thresholds = BurialDetectionEngine.BURIAL_THRESHOLDS.get(
            wrestler_role,
            BurialDetectionEngine.BURIAL_THRESHOLDS['Jobber']
        )

        hier = ['Jobber', 'Lower Midcard', 'Midcard', 'Upper Midcard', 'Main Event']
        my_rank = hier.index(wrestler_role) if wrestler_role in hier else 2

        modifier    = 0.0
        reasons     = []
        is_buried   = False

        if not recent_results:
            return 0.0, "No match data", False

        # -- Detect consecutive clean losses to lower-ranked opponents --
        consecutive_burial_losses = 0
        for result in recent_results[-6:]:
            if result.get('won', True):
                consecutive_burial_losses = 0  # Reset on any win
                continue
            opp_role = result.get('opponent_role', 'Midcard')
            opp_rank = hier.index(opp_role) if opp_role in hier else 2
            finish   = result.get('finish_type', 'clean')

            # Only clean losses to lower-ranked opponents count as burial
            if opp_rank < my_rank and finish in ('clean_pin', 'submission', 'clean'):
                consecutive_burial_losses += 1
            else:
                consecutive_burial_losses = 0

        burial_threshold = thresholds['consecutive_losses_to_lower']
        if consecutive_burial_losses >= burial_threshold:
            severity = consecutive_burial_losses - burial_threshold
            modifier -= 20 + (severity * 8)
            reasons.append(
                f"Being systematically buried — {consecutive_burial_losses} clean losses to lower-ranked talent"
            )
            is_buried = True

        # -- Detect PPV exile (for Main Eventers and Upper Midcarders) --
        ppv_miss_limit = thresholds['ppv_miss_weeks']
        if (weeks_since_ppv_match is not None and
                wrestler_role in ['Main Event', 'Upper Midcard'] and
                weeks_since_ppv_match > ppv_miss_limit):
            weeks_over = weeks_since_ppv_match - ppv_miss_limit
            modifier  -= 12 + (weeks_over * 2)
            reasons.append(
                f"Absent from PPV cards for {weeks_since_ppv_match} weeks — feels exiled"
            )
            is_buried = True

        # -- Detect sudden role demotion --
        if previous_role and previous_role in hier and wrestler_role in hier:
            prev_rank = hier.index(previous_role)
            if my_rank < prev_rank and weeks_at_current_role <= 8:
                demotion_gap = prev_rank - my_rank
                modifier -= 15 * demotion_gap
                reasons.append(
                    f"Recently demoted from {previous_role} — still processing the drop"
                )

        modifier = max(-45.0, modifier)  # Cap burial penalty
        reason   = "; ".join(reasons) if reasons else "No burial pattern detected"
        return modifier, reason, is_buried


# ============================================================================
# Step 238: Creative Frustration Engine
# ============================================================================

class CreativeFrustrationEngine:
    """
    Step 238: Measures frustration from stale, repetitive, or contradictory booking.

    Even a well-pushed wrestler becomes frustrated if:
    - Their character hasn't evolved in months
    - They keep working the same opponent(s)
    - Their gimmick/alignment has been changed without consultation
    - They have high creative_control but aren't being consulted
    """

    @staticmethod
    def calculate(
        weeks_in_same_feud: int,               # Weeks against same opponent
        total_distinct_feuds_12w: int,          # Different opponents in last 12 weeks
        gimmick_changed_without_consent: bool,  # Alignment/character forced change
        has_creative_control: bool,             # Contract has creative control clause
        creative_control_respected: bool,       # Was it actually respected?
        weeks_same_character_arc: int,          # Weeks without story progression
        wrestler_role: str,
    ) -> Tuple[float, str]:
        """
        Returns (promo_satisfaction_modifier, reason).
        Applied as a modifier on top of promo_satisfaction.
        """
        modifier = 0.0
        reasons  = []

        # -- Feud staleness --
        if wrestler_role in ['Main Event', 'Upper Midcard']:
            if weeks_in_same_feud > 16:
                modifier -= 18
                reasons.append(f"Same feud for {weeks_in_same_feud} weeks — feels like creative has run out of ideas")
            elif weeks_in_same_feud > 10:
                modifier -= 8
                reasons.append("Feud is running long — getting repetitive")
        elif wrestler_role == 'Midcard':
            if weeks_in_same_feud > 20:
                modifier -= 12
                reasons.append(f"Stuck in same midcard feud for {weeks_in_same_feud} weeks")

        # -- Lack of variety --
        if total_distinct_feuds_12w <= 1 and wrestler_role in ['Main Event', 'Upper Midcard']:
            modifier -= 10
            reasons.append("Booking has been one-dimensional — same story week after week")

        # -- Character arc stagnation --
        if wrestler_role in ['Main Event', 'Upper Midcard']:
            if weeks_same_character_arc > 20:
                modifier -= 15
                reasons.append(f"Character hasn't evolved in {weeks_same_character_arc} weeks")
            elif weeks_same_character_arc > 12:
                modifier -= 7
                reasons.append("Story arc feels stale — needs a new direction")

        # -- Forced creative changes --
        if gimmick_changed_without_consent:
            modifier -= 20
            reasons.append("Gimmick/character changed without consultation — feels disrespected")

        # -- Creative control violation --
        if has_creative_control and not creative_control_respected:
            modifier -= 25
            reasons.append("Creative control clause in contract is being ignored — major grievance")

        modifier = max(-40.0, modifier)
        reason   = "; ".join(reasons) if reasons else "Creative direction feels fresh"
        return modifier, reason


# ============================================================================
# Step 239: Underutilization Engine
# ============================================================================

class UnderutilizationEngine:
    """
    Step 239: Wrestlers who don't appear frequently enough lose morale.

    A Main Eventer expects to be on every show. A Midcarder expects
    at least every other week. Prolonged absences feel like a message
    from management: "We don't see you as valuable."

    This is distinct from injury absences — those use a separate buffer.
    """

    # (expected_appearances_per_4w, minimum_acceptable_per_4w)
    ROLE_APPEARANCE_EXPECTATIONS = {
        'Main Event':    (4, 3),   # On every show; miss 1 max
        'Upper Midcard': (3, 2),   # 3 of 4 shows minimum
        'Midcard':       (2, 1),   # Every other show
        'Lower Midcard': (1, 0),   # At least once a month
        'Jobber':        (1, 0),   # No expectation
    }

    @staticmethod
    def calculate(
        wrestler_role: str,
        appearances_last_4_weeks: int,
        is_injured: bool,
        weeks_since_last_appearance: int,
    ) -> Tuple[float, str]:
        """
        Returns (push_satisfaction_modifier, reason).
        Injured wrestlers get a much smaller penalty.
        """
        if is_injured:
            # Injured wrestlers understand non-appearance; minor longing
            penalty = min(5.0, weeks_since_last_appearance * 0.5)
            return -penalty, "Out injured — eager to return" if penalty > 0 else ""

        expected, minimum = UnderutilizationEngine.ROLE_APPEARANCE_EXPECTATIONS.get(
            wrestler_role, (1, 0)
        )

        if wrestler_role == 'Jobber':
            # Jobbers have low expectations — slight bonus if used
            if appearances_last_4_weeks >= 2:
                return 5.0, "Getting regular work — appreciated"
            return 0.0, "Appearance rate typical for role"

        modifier = 0.0
        reasons  = []

        if appearances_last_4_weeks >= expected:
            modifier = 5.0
            reasons.append("Regular bookings — feeling valued")
        elif appearances_last_4_weeks >= minimum:
            modifier = 0.0
            reasons.append("Appearance rate acceptable")
        elif appearances_last_4_weeks == 0:
            # Total absence is severe
            severity = min(weeks_since_last_appearance, 12)
            modifier = -(15 + severity * 2.5)
            reasons.append(
                f"Not booked in {weeks_since_last_appearance} weeks — feels forgotten"
            )
        else:
            gap      = minimum - appearances_last_4_weeks
            modifier = -(8 * gap)
            reasons.append(
                f"Only {appearances_last_4_weeks} appearance(s) in 4 weeks — underutilised"
            )

        modifier = max(-40.0, modifier)
        return modifier, "; ".join(reasons) if reasons else "Booking frequency acceptable"


# ============================================================================
# Step 240: Overwork Burnout Engine
# ============================================================================

class OverworkBurnoutEngine:
    """
    Step 240: Excessive bookings, travel fatigue, and injury risks from
    being overworked all drain morale over time.

    The irony: Main Eventers can also have too much. A wrestler booked
    on every single show for 20 straight weeks begins to break down
    physically and mentally, especially without a meaningful story.

    This feeds into fatigue (existing field) and reduces satisfaction
    with the overall push (counterintuitively: too much = less rewarding).
    """

    @staticmethod
    def calculate(
        appearances_last_4_weeks: int,
        current_fatigue: int,              # 0-100 from wrestler.fatigue
        wrestler_role: str,
        weeks_without_rest: int,           # Consecutive weeks booked
        injury_prone: bool,                # Has had 2+ injuries this contract
    ) -> Tuple[float, str]:
        """
        Returns (management_appreciation_modifier, reason).
        High fatigue + no rest suggests management doesn't care about wellbeing.
        """
        modifier = 0.0
        reasons  = []

        # Role-based overwork thresholds
        overwork_threshold = {
            'Main Event':    5,   # >5 per 4w is overwork
            'Upper Midcard': 5,
            'Midcard':       6,
            'Lower Midcard': 7,
            'Jobber':        8,
        }.get(wrestler_role, 6)

        if appearances_last_4_weeks > overwork_threshold:
            excess    = appearances_last_4_weeks - overwork_threshold
            modifier -= 5 + (excess * 4)
            reasons.append(
                f"Overbooked — {appearances_last_4_weeks} appearances in 4 weeks feels unsustainable"
            )

        # Fatigue factor
        if current_fatigue >= 80:
            modifier -= 18
            reasons.append(f"Running on empty — fatigue at {current_fatigue}%")
        elif current_fatigue >= 60:
            modifier -= 10
            reasons.append(f"Physically worn down — fatigue at {current_fatigue}%")
        elif current_fatigue >= 40:
            modifier -= 4
            reasons.append("Feeling the grind — minor fatigue building")

        # Consecutive weeks without meaningful rest
        if weeks_without_rest >= 16:
            modifier -= 15
            reasons.append(f"No break in {weeks_without_rest} weeks — burning out")
        elif weeks_without_rest >= 10:
            modifier -= 7
            reasons.append("Long stretch without rest — fatigue compounding")

        # Injury-prone wrestlers feel unsafe when overbooked
        if injury_prone and appearances_last_4_weeks > 4:
            modifier -= 10
            reasons.append("History of injuries makes heavy schedule feel reckless")

        modifier = max(-35.0, modifier)
        return modifier, "; ".join(reasons) if reasons else "Workload feels manageable"


# ============================================================================
# Step 241: Pay Grievances Engine
# ============================================================================

class PayGrievancesEngine:
    """
    Step 241: Wrestlers compare their pay to peers and market rates.

    A wrestler who has risen in card position but not in pay feels
    exploited. Conversely, an overpaid talent who underperforms feels
    guilty but not unhappy.

    Uses contract.salary_per_show compared against role market rates
    and compares against perceived peer salaries.
    """

    # Market rate salary_per_show by role (approximate)
    MARKET_RATES = {
        'Main Event':    {'min': 15000, 'fair': 25000, 'premium': 50000},
        'Upper Midcard': {'min':  8000, 'fair': 14000, 'premium': 25000},
        'Midcard':       {'min':  4000, 'fair':  7000, 'premium': 12000},
        'Lower Midcard': {'min':  2000, 'fair':  3500, 'premium':  6000},
        'Jobber':        {'min':   800, 'fair':  1500, 'premium':  3000},
    }

    @staticmethod
    def calculate(
        wrestler_role: str,
        current_salary: int,              # salary_per_show
        years_experience: int,
        total_title_reigns: int,
        popularity: int,                  # 0-100
        weeks_since_raise: Optional[int], # None = never had raise
        peer_avg_salary: Optional[float], # Average salary of same-role wrestlers
    ) -> Tuple[float, str]:
        """
        Returns (management_appreciation_modifier, reason).
        Pay dissatisfaction hits management_appreciation hardest.
        """
        rates    = PayGrievancesEngine.MARKET_RATES.get(
            wrestler_role,
            PayGrievancesEngine.MARKET_RATES['Midcard']
        )
        modifier = 0.0
        reasons  = []

        fair_rate = rates['fair']

        # Adjust fair rate upward for experienced veterans
        if years_experience >= 15:
            fair_rate = int(fair_rate * 1.4)
        elif years_experience >= 8:
            fair_rate = int(fair_rate * 1.2)

        # Adjust fair rate upward for popular wrestlers
        if popularity >= 80:
            fair_rate = int(fair_rate * 1.3)
        elif popularity >= 65:
            fair_rate = int(fair_rate * 1.15)

        # Adjust for title prestige
        if total_title_reigns >= 3:
            fair_rate = int(fair_rate * 1.2)
        elif total_title_reigns >= 1:
            fair_rate = int(fair_rate * 1.1)

        pay_ratio = current_salary / max(fair_rate, 1)

        if pay_ratio >= 1.4:
            modifier += 12
            reasons.append(f"Well compensated — earning above market (${current_salary:,}/show)")
        elif pay_ratio >= 1.1:
            modifier += 5
            reasons.append("Pay is fair — no financial grievances")
        elif pay_ratio >= 0.85:
            modifier = 0.0
            reasons.append("Pay is slightly below expectation — tolerable")
        elif pay_ratio >= 0.65:
            modifier -= 14
            reasons.append(
                f"Underpaid relative to role — earning ${current_salary:,}/show vs ~${fair_rate:,} fair rate"
            )
        else:
            modifier -= 28
            reasons.append(
                f"Significantly underpaid — ${current_salary:,}/show vs ${fair_rate:,} market rate. Feels exploited."
            )

        # Peer comparison penalty
        if peer_avg_salary and current_salary < peer_avg_salary * 0.7:
            modifier -= 10
            reasons.append(
                f"Earning {int((1 - current_salary/peer_avg_salary)*100)}% less than peers — aware of disparity"
            )

        # Raise neglect
        if weeks_since_raise is not None and weeks_since_raise > 52 and wrestler_role in ['Main Event', 'Upper Midcard']:
            modifier -= 8
            reasons.append(f"No raise in {weeks_since_raise} weeks despite sustained performance")

        modifier = max(-35.0, min(15.0, modifier))
        return modifier, "; ".join(reasons) if reasons else "Compensation feels appropriate"


# ============================================================================
# Step 242: Promise Breaking Engine
# ============================================================================

class PromiseBreakingEngine:
    """
    Step 242: Broken creative promises devastate trust and morale.

    When management promises a push, a title shot, a storyline, or a
    specific booking outcome and then doesn't deliver, morale crashes
    in proportion to how much the wrestler invested in the promise.

    Uses the contract_promises table data (broken, promise_type).
    """

    # Morale impact per broken promise type
    PROMISE_IMPACTS = {
        'title_shot':           -25,
        'main_event_push':      -30,
        'championship_run':     -35,
        'feud_with_star':       -18,
        'ppv_match':            -20,
        'storyline_spotlight':  -15,
        'creative_direction':   -12,
        'promo_time':           -10,
        'pay_raise':            -22,
        'brand_move':           -12,
        'time_off':             -18,
        'general':              -10,
    }

    @staticmethod
    def calculate(
        broken_promises: List[dict],    # [{promise_type, broken_reason, weeks_ago}]
        fulfilled_promises: List[dict], # [{promise_type}] — kept promises soften the impact
        total_promises_made: int,
    ) -> Tuple[float, str]:
        """
        Returns (management_appreciation_modifier, reason).
        Recent breaks hurt more; older ones fade over time.
        """
        if not broken_promises:
            # Bonus for consistent promise-keeping
            if fulfilled_promises and len(fulfilled_promises) >= 3:
                return 8.0, "Management consistently delivers on commitments — trust is high"
            return 0.0, "No broken promises on record"

        modifier       = 0.0
        reasons        = []
        recent_breaks  = 0

        for promise in broken_promises:
            promise_type = promise.get('promise_type', 'general')
            weeks_ago    = promise.get('weeks_ago', 0)
            base_impact  = PromiseBreakingEngine.PROMISE_IMPACTS.get(promise_type, -10)

            # Recency weighting: full impact within 8 weeks, halved by 24 weeks
            if weeks_ago <= 4:
                multiplier  = 1.0
                recent_breaks += 1
            elif weeks_ago <= 12:
                multiplier = 0.75
            elif weeks_ago <= 24:
                multiplier = 0.5
            else:
                multiplier = 0.25  # Old wounds still sting a little

            modifier += base_impact * multiplier

        # Serial promise-breaking compounds distrust
        if recent_breaks >= 3:
            modifier -= 15
            reasons.append(f"Management has broken {recent_breaks} promises recently — no longer trusts their word")
        elif recent_breaks == 2:
            modifier -= 8
            reasons.append("Back-to-back broken promises — trust is eroding")
        elif recent_breaks == 1:
            reasons.append(f"Recent broken promise — still processing the disappointment")

        # Kept promises partially offset broken ones
        keep_ratio = len(fulfilled_promises) / max(total_promises_made, 1)
        if keep_ratio >= 0.8 and len(fulfilled_promises) >= 2:
            modifier = modifier * 0.7  # Track record softens current break
            reasons.append("Strong track record of kept promises softens current disappointment")

        modifier = max(-50.0, modifier)
        return modifier, "; ".join(reasons) if reasons else "Promise history is mixed"


# ============================================================================
# Step 243: Disrespectful Treatment Engine
# ============================================================================

class DisrespectfulTreatmentEngine:
    """
    Step 243: Public humiliation, embarrassing angles, and being made to
    look foolish on-screen destroys morale and locker room standing.

    Categories:
    - Public embarrassment (comedy squash, humiliation segments)
    - Being called out/berated in front of roster
    - Being made to lose in humiliating fashion
    - Being pulled from advertised matches without explanation
    - Gimmick mockery / being paired with degrading character work
    """

    INCIDENT_IMPACTS = {
        'humiliation_segment':          -30,  # On-screen mockery/degradation
        'squash_by_non_threat':         -20,  # Fast loss to someone with no story reason
        'pulled_from_advertised_match': -22,  # Advertised, then removed
        'public_dressing_down':         -25,  # Berated backstage in front of others
        'degrading_gimmick_forced':     -28,  # Made to perform embarrassing character
        'no_entrance_music_stripped':   -15,  # Symbols of status removed
        'entrance_gear_degraded':       -12,  # Forced to look weak visually
        'verbal_disrespect_by_booker':  -20,  # Told you're "just a body" etc.
    }

    @staticmethod
    def calculate(
        disrespect_incidents: List[dict],  # [{incident_type, weeks_ago, severity_note}]
        is_veteran: bool,                  # Veterans are more sensitive to loss of respect
        wrestler_role: str,
    ) -> Tuple[float, str]:
        """
        Returns (management_appreciation_modifier, reason).
        Also bleeds into peer_respect.
        """
        if not disrespect_incidents:
            return 0.0, "No disrespect incidents on record"

        modifier = 0.0
        reasons  = []
        acute    = []   # Incidents within last 4 weeks

        for incident in disrespect_incidents:
            incident_type = incident.get('incident_type', 'humiliation_segment')
            weeks_ago     = incident.get('weeks_ago', 0)
            base_impact   = DisrespectfulTreatmentEngine.INCIDENT_IMPACTS.get(incident_type, -15)

            # Veterans take these harder (pride and established status)
            if is_veteran:
                base_impact = base_impact * 1.3

            # Recency weighting
            if weeks_ago <= 2:
                multiplier = 1.0
                acute.append(incident_type)
            elif weeks_ago <= 6:
                multiplier = 0.8
            elif weeks_ago <= 14:
                multiplier = 0.5
            else:
                multiplier = 0.25  # Old scars

            modifier += base_impact * multiplier

        if acute:
            clean_names = [t.replace('_', ' ') for t in acute[:2]]
            reasons.append(
                f"Recent disrespectful treatment: {', '.join(clean_names)} — still raw"
            )
        if len(disrespect_incidents) >= 3:
            reasons.append("Pattern of disrespectful treatment — feels targeted")

        modifier = max(-45.0, modifier)
        return modifier, "; ".join(reasons) if reasons else "No recent disrespect"


# ============================================================================
# Step 244: Personal Conflicts Engine
# ============================================================================

class PersonalConflictsEngine:
    """
    Step 244: Real locker room feuds with specific colleagues damage morale.

    Unlike poor peer_respect (which is a general standing), personal
    conflicts are targeted — they involve specific individuals who either:
    - Have heat with the wrestler backstage
    - Are political rivals fighting for the same spot
    - Have had physical/verbal altercations
    - Are spreading negative talk about them

    Active conflicts with upper-card wrestlers are more damaging because
    those wrestlers have more political power.
    """

    CONFLICT_SEVERITY = {
        'heated_rivalry':     -12,   # Ongoing backstage tension
        'verbal_altercation': -18,   # Argument that others witnessed
        'political_rivalry':  -15,   # Both competing for same push
        'spreading_rumors':   -20,   # Colleague actively undermining them
        'physical_incident':  -30,   # Physical altercation (very rare)
        'power_play':         -22,   # Higher-card star using influence to bury them
        'clique_exclusion':   -14,   # Being excluded from dominant locker room faction
    }

    ROLE_HIERARCHY = ['Jobber', 'Lower Midcard', 'Midcard', 'Upper Midcard', 'Main Event']

    @staticmethod
    def calculate(
        active_conflicts: List[dict],    # [{conflict_type, opponent_role, weeks_active, is_public}]
        wrestler_role: str,
    ) -> Tuple[float, str]:
        """
        Returns (peer_respect_modifier, reason).
        Active conflicts affect both peer_respect and management_appreciation.
        """
        if not active_conflicts:
            return 0.0, "No notable personal conflicts"

        hier     = PersonalConflictsEngine.ROLE_HIERARCHY
        my_rank  = hier.index(wrestler_role) if wrestler_role in hier else 2

        modifier = 0.0
        reasons  = []

        for conflict in active_conflicts:
            conflict_type  = conflict.get('conflict_type', 'heated_rivalry')
            opponent_role  = conflict.get('opponent_role', 'Midcard')
            weeks_active   = conflict.get('weeks_active', 1)
            is_public      = conflict.get('is_public', False)
            opp_rank       = hier.index(opponent_role) if opponent_role in hier else 2
            base_impact    = PersonalConflictsEngine.CONFLICT_SEVERITY.get(conflict_type, -12)

            # More powerful opponents are more damaging politically
            if opp_rank > my_rank:
                base_impact = base_impact * 1.4  # Political disadvantage
            elif opp_rank == my_rank:
                base_impact = base_impact * 1.0

            # Duration amplifies
            if weeks_active >= 12:
                base_impact *= 1.3
            elif weeks_active >= 6:
                base_impact *= 1.15

            # Public conflicts are extra damaging (everyone sees)
            if is_public:
                base_impact *= 1.25

            modifier += base_impact

        if len(active_conflicts) >= 3:
            modifier -= 10
            reasons.append(f"Multiple ongoing conflicts — toxic locker room experience for this individual")
        elif active_conflicts:
            top = active_conflicts[0]
            ctype = top.get('conflict_type', 'heated_rivalry').replace('_', ' ')
            oname = top.get('opponent_name', 'a colleague')
            reasons.append(f"Personal conflict ({ctype}) with {oname} affecting daily environment")

        modifier = max(-40.0, modifier)
        return modifier, "; ".join(reasons) if reasons else "Locker room relationships manageable"


# ============================================================================
# Master Morale Engine (updated for Steps 237-244)
# ============================================================================

class MoraleEngine:
    """
    Orchestrates all morale components for a wrestler after each show week.
    Steps 237-244 add negative influence engines that modify component scores
    on top of the positive base scores calculated in Steps 229-236.
    """

    def process_weekly_morale(
        self,
        record: WrestlerMoraleRecord,
        wrestler_data: dict,
        show_data: dict,
        universe_data: dict,
    ) -> WrestlerMoraleRecord:
        """
        Recalculate all morale components and update the record.

        wrestler_data keys:
            role, years_experience, is_major_superstar, total_title_reigns,
            locker_room_rep, is_faction_leader, current_salary, popularity,
            fatigue, is_injured, injury_prone, previous_role,
            weeks_at_current_role, peer_avg_salary, weeks_since_raise

        show_data keys:
            recent_card_positions, recent_wins, recent_losses,
            weeks_since_last_title_shot, weeks_since_last_appearance,
            recent_results, is_current_champion, weeks_as_champion,
            recent_star_ratings, had_moty_candidate,
            avg_promo_minutes, weeks_since_last_promo,
            avg_star_rating, appreciation_events,
            weeks_since_management_contact,
            appearances_last_4_weeks, weeks_without_rest,
            weeks_since_ppv_match,
            weeks_in_same_feud, total_distinct_feuds_12w,
            gimmick_changed_without_consent, has_creative_control,
            creative_control_respected, weeks_same_character_arc,
            broken_promises, fulfilled_promises, total_promises_made,
            disrespect_incidents, active_conflicts

        universe_data keys:
            merch_rank, roster_size, merch_revenue_monthly,
            current_week, current_year
        """
        role = wrestler_data.get('role', 'Midcard')

        # ── Positive Influences (Steps 229-236) ──────────────────────────────

        record.components.push_satisfaction, _ = PushSatisfactionEngine.calculate(
            wrestler_role=role,
            recent_card_positions=show_data.get('recent_card_positions', []),
            recent_wins=show_data.get('recent_wins', 0),
            recent_losses=show_data.get('recent_losses', 0),
            weeks_since_last_title_shot=show_data.get('weeks_since_last_title_shot'),
            weeks_since_last_appearance=show_data.get('weeks_since_last_appearance', 0),
        )

        record.components.win_loss_satisfaction, _ = WinLossImpactEngine.calculate(
            recent_results=show_data.get('recent_results', []),
            wrestler_role=role,
        )

        record.components.championship_satisfaction, _ = ChampionshipOpportunitySatisfaction.calculate(
            wrestler_role=role,
            is_current_champion=show_data.get('is_current_champion', False),
            weeks_as_champion=show_data.get('weeks_as_champion', 0),
            weeks_since_last_title_shot=show_data.get('weeks_since_last_title_shot'),
            total_title_reigns=wrestler_data.get('total_title_reigns', 0),
            years_experience=wrestler_data.get('years_experience', 1),
        )

        record.components.match_quality_satisfaction, _ = MatchQualitySatisfaction.calculate(
            recent_star_ratings=show_data.get('recent_star_ratings', []),
            had_moty_candidate=show_data.get('had_moty_candidate', False),
        )

        record.components.promo_satisfaction, _ = PromoTimeSatisfaction.calculate(
            wrestler_role=role,
            avg_promo_minutes_recent=show_data.get('avg_promo_minutes', 0.0),
            weeks_since_last_promo=show_data.get('weeks_since_last_promo', 4),
        )

        record.components.merch_satisfaction, _ = MerchandiseSatisfaction.calculate(
            merch_sales_rank=universe_data.get('merch_rank', 20),
            total_roster_size=universe_data.get('roster_size', 45),
            merch_revenue_monthly=universe_data.get('merch_revenue_monthly', 0.0),
        )

        record.components.peer_respect, _ = PeerRespectEngine.calculate(
            years_experience=wrestler_data.get('years_experience', 1),
            is_major_superstar=wrestler_data.get('is_major_superstar', False),
            recent_avg_star_rating=show_data.get('avg_star_rating', 2.5),
            locker_room_rep=wrestler_data.get('locker_room_rep', 'Neutral'),
            is_faction_leader=wrestler_data.get('is_faction_leader', False),
        )

        record.components.management_appreciation, _ = ManagementAppreciationEngine.calculate(
            recent_appreciation_events=show_data.get('appreciation_events', []),
            weeks_since_any_contact=show_data.get('weeks_since_management_contact', 2),
            current_week=universe_data.get('current_week', 1),
            current_year=universe_data.get('current_year', 1),
        )

        # ── Negative Influences (Steps 237-244) ──────────────────────────────

        # Step 237: Burial detection → push_satisfaction modifier
        burial_mod, burial_reason, is_buried = BurialDetectionEngine.calculate(
            wrestler_role=role,
            recent_results=show_data.get('recent_results', []),
            weeks_since_ppv_match=show_data.get('weeks_since_ppv_match'),
            previous_role=wrestler_data.get('previous_role'),
            weeks_at_current_role=wrestler_data.get('weeks_at_current_role', 0),
        )
        record.components.push_satisfaction = max(0.0, min(100.0,
            record.components.push_satisfaction + burial_mod
        ))
        if is_buried:
            record.add_morale_event(
                event_type='burial_detected',
                description=burial_reason,
                delta=burial_mod * 0.5,  # Partial immediate hit; rest via component
                component='push_satisfaction',
            )

        # Step 238: Creative frustration → promo_satisfaction modifier
        creative_mod, creative_reason = CreativeFrustrationEngine.calculate(
            weeks_in_same_feud=show_data.get('weeks_in_same_feud', 0),
            total_distinct_feuds_12w=show_data.get('total_distinct_feuds_12w', 1),
            gimmick_changed_without_consent=show_data.get('gimmick_changed_without_consent', False),
            has_creative_control=wrestler_data.get('has_creative_control', False),
            creative_control_respected=show_data.get('creative_control_respected', True),
            weeks_same_character_arc=show_data.get('weeks_same_character_arc', 0),
            wrestler_role=role,
        )
        record.components.promo_satisfaction = max(0.0, min(100.0,
            record.components.promo_satisfaction + creative_mod
        ))

        # Step 239: Underutilization → push_satisfaction modifier
        util_mod, util_reason = UnderutilizationEngine.calculate(
            wrestler_role=role,
            appearances_last_4_weeks=show_data.get('appearances_last_4_weeks', 2),
            is_injured=wrestler_data.get('is_injured', False),
            weeks_since_last_appearance=show_data.get('weeks_since_last_appearance', 0),
        )
        record.components.push_satisfaction = max(0.0, min(100.0,
            record.components.push_satisfaction + util_mod
        ))

        # Step 240: Overwork burnout → management_appreciation modifier
        burnout_mod, burnout_reason = OverworkBurnoutEngine.calculate(
            appearances_last_4_weeks=show_data.get('appearances_last_4_weeks', 2),
            current_fatigue=wrestler_data.get('fatigue', 0),
            wrestler_role=role,
            weeks_without_rest=show_data.get('weeks_without_rest', 0),
            injury_prone=wrestler_data.get('injury_prone', False),
        )
        record.components.management_appreciation = max(0.0, min(100.0,
            record.components.management_appreciation + burnout_mod
        ))

        # Step 241: Pay grievances → management_appreciation modifier
        pay_mod, pay_reason = PayGrievancesEngine.calculate(
            wrestler_role=role,
            current_salary=wrestler_data.get('current_salary', 5000),
            years_experience=wrestler_data.get('years_experience', 1),
            total_title_reigns=wrestler_data.get('total_title_reigns', 0),
            popularity=wrestler_data.get('popularity', 50),
            weeks_since_raise=wrestler_data.get('weeks_since_raise'),
            peer_avg_salary=wrestler_data.get('peer_avg_salary'),
        )
        record.components.management_appreciation = max(0.0, min(100.0,
            record.components.management_appreciation + pay_mod
        ))

        # Step 242: Promise breaking → management_appreciation modifier
        promise_mod, promise_reason = PromiseBreakingEngine.calculate(
            broken_promises=show_data.get('broken_promises', []),
            fulfilled_promises=show_data.get('fulfilled_promises', []),
            total_promises_made=show_data.get('total_promises_made', 0),
        )
        record.components.management_appreciation = max(0.0, min(100.0,
            record.components.management_appreciation + promise_mod
        ))
        if promise_mod < -10:
            record.add_morale_event(
                event_type='broken_promise',
                description=promise_reason,
                delta=promise_mod * 0.4,
                component='management_appreciation',
            )

        # Step 243: Disrespectful treatment → management_appreciation + peer_respect
        disrespect_mod, disrespect_reason = DisrespectfulTreatmentEngine.calculate(
            disrespect_incidents=show_data.get('disrespect_incidents', []),
            is_veteran=wrestler_data.get('years_experience', 1) >= 10,
            wrestler_role=role,
        )
        record.components.management_appreciation = max(0.0, min(100.0,
            record.components.management_appreciation + disrespect_mod * 0.6
        ))
        record.components.peer_respect = max(0.0, min(100.0,
            record.components.peer_respect + disrespect_mod * 0.4
        ))
        if disrespect_mod < -10:
            record.add_morale_event(
                event_type='disrespectful_treatment',
                description=disrespect_reason,
                delta=disrespect_mod * 0.3,
                component='management_appreciation',
            )

        # Step 244: Personal conflicts → peer_respect modifier
        conflict_mod, conflict_reason = PersonalConflictsEngine.calculate(
            active_conflicts=show_data.get('active_conflicts', []),
            wrestler_role=role,
        )
        record.components.peer_respect = max(0.0, min(100.0,
            record.components.peer_respect + conflict_mod
        ))

        # ── Recalculate final morale score ────────────────────────────────────

        old_score = record.morale_score
        record.recalculate_from_components()
        delta = record.morale_score - old_score

        if abs(delta) >= 3:
            # Find the dominant driver
            c = record.components
            all_drivers = [
                (abs(c.push_satisfaction         - 50), 'push_satisfaction',         "Push situation changed"),
                (abs(c.championship_satisfaction - 50), 'championship_satisfaction', "Championship picture changed"),
                (abs(c.win_loss_satisfaction     - 50), 'win_loss_satisfaction',     "Win/loss record impact"),
                (abs(c.management_appreciation   - 50), 'management_appreciation',   "Management relationship"),
                (abs(c.promo_satisfaction        - 50), 'promo_satisfaction',         "Creative direction"),
                (abs(c.peer_respect              - 50), 'peer_respect',              "Locker room dynamics"),
            ]
            dominant = max(all_drivers, key=lambda x: x[0])
            record.add_morale_event(
                event_type='weekly_recalculation',
                description=dominant[2],
                delta=delta,
                component=dominant[1],
            )

        return record

    def apply_management_appreciation(
        self,
        record: WrestlerMoraleRecord,
        event_type: str,
        current_week: int,
        current_year: int,
    ) -> Tuple[WrestlerMoraleRecord, float]:
        """Apply an immediate management appreciation gesture."""
        event = ManagementAppreciationEngine.create_event(event_type, current_week, current_year)
        boost = event.morale_boost
        record._appreciation_events.append(event)
        record.add_morale_event(
            event_type=f'management_{event_type}',
            description=event.description,
            delta=boost,
            component='management_appreciation',
        )
        return record, boost

    def apply_negative_event(
        self,
        record: WrestlerMoraleRecord,
        event_type: str,
        description: str,
        delta: float,
        component: str = 'management_appreciation',
    ) -> Tuple[WrestlerMoraleRecord, float]:
        """
        Apply an immediate negative morale event (Steps 237-244 triggers).
        Used by routes when the player takes an action that causes harm.
        delta should be negative.
        """
        record.add_morale_event(
            event_type=event_type,
            description=description,
            delta=delta,
            component=component,
        )
        return record, delta

    def get_negative_factors_summary(self, record: WrestlerMoraleRecord) -> dict:
        """
        Returns a structured summary of which negative factors are
        most impacting this wrestler's morale (Steps 237-244).
        Used by the frontend breakdown panel.
        """
        c = record.components
        negatives = []

        checks = [
            (c.push_satisfaction,        'push_satisfaction',        'Being buried / underutilised'),
            (c.win_loss_satisfaction,     'win_loss_satisfaction',    'Losing record impacting morale'),
            (c.championship_satisfaction, 'championship_satisfaction','Lack of title opportunities'),
            (c.promo_satisfaction,        'promo_satisfaction',       'Creative frustration / no mic time'),
            (c.management_appreciation,   'management_appreciation',  'Management issues / pay grievances'),
            (c.peer_respect,              'peer_respect',             'Locker room conflicts'),
        ]

        for score, key, label in checks:
            if score < 35:
                severity = 'critical' if score < 20 else 'high'
                negatives.append({
                    'component': key,
                    'label':     label,
                    'score':     round(score, 1),
                    'severity':  severity,
                })

        negatives.sort(key=lambda x: x['score'])
        return {
            'negative_factors': negatives,
            'total_negative_components': len(negatives),
            'most_critical': negatives[0] if negatives else None,
        }

    def get_morale_summary(self, record: WrestlerMoraleRecord) -> dict:
        cat = record.category
        return {
            **record.to_dict(),
            'summary': {
                'score':            round(record.morale_score, 1),
                'category':         cat.value,
                'emoji':            cat.emoji,
                'color':            cat.color,
                'trend':            record.momentum.to_dict()['trend'],
                'top_positive':     self._get_top_positives(record),
                'top_concerns':     self._get_top_concerns(record),
                'negative_factors': self.get_negative_factors_summary(record)['negative_factors'],
            },
        }

    def _get_top_positives(self, record: WrestlerMoraleRecord) -> List[str]:
        c = record.components
        return [label for score, label in [
            (c.push_satisfaction,          "Strong push"),
            (c.championship_satisfaction,  "Championship opportunities"),
            (c.win_loss_satisfaction,      "Winning consistently"),
            (c.match_quality_satisfaction, "Quality match experiences"),
            (c.management_appreciation,    "Management appreciation"),
            (c.peer_respect,               "Locker room respect"),
        ] if score >= 70][:3]

    def _get_top_concerns(self, record: WrestlerMoraleRecord) -> List[str]:
        c = record.components
        return [label for score, label in [
            (c.push_satisfaction,         "Unsatisfied with push"),
            (c.championship_satisfaction, "Lacking title opportunities"),
            (c.win_loss_satisfaction,     "Poor win/loss record"),
            (c.promo_satisfaction,        "Insufficient mic time / creative frustration"),
            (c.management_appreciation,   "Pay/management grievances"),
            (c.peer_respect,              "Locker room conflicts"),
        ] if score < 40][:3]


# Module-level singleton
morale_engine = MoraleEngine()