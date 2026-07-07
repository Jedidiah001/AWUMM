"""
Anti-Bidding War Tactics
STEP 133: Strategies to avoid escalation and retain talent without expensive bidding wars.

Four core tactics:
1. Pre-emptive Signings     — Lock up wrestlers BEFORE they hit free agency
2. Long-Term Contract Locks — Extended deals with loyalty discounts
3. Loyalty Bonuses          — Financial incentives that make leaving costly
4. Relationship Building    — Non-monetary investment that makes money secondary
"""

import random
from typing import Dict, Any, List, Optional
from datetime import datetime

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────

PREEMPTIVE_WINDOW_WEEKS = 26  # 6 months — window for pre-emptive offer

LOYALTY_BONUS_PCTS = {
    'small':  0.10,
    'medium': 0.20,
    'large':  0.35,
}

RELATIONSHIP_TIERS = {
    (90, 100): 'Devoted',
    (70, 89):  'Loyal',
    (50, 69):  'Content',
    (30, 49):  'Restless',
    (0,  29):  'Disgruntled',
}


def _relationship_tier(score: int) -> str:
    for (lo, hi), label in RELATIONSHIP_TIERS.items():
        if lo <= score <= hi:
            return label
    return 'Unknown'


def _weeks_to_expiry(wrestler) -> int:
    if hasattr(wrestler, 'contract') and wrestler.contract:
        return getattr(wrestler.contract, 'weeks_remaining', 0)
    return getattr(wrestler, 'weeks_remaining', 0)


# ─────────────────────────────────────────────
# Tactic Result
# ─────────────────────────────────────────────

class TacticResult:
    def __init__(self, tactic, success, message, cost=0, relationship_change=0,
                 weeks_added=0, details=None, warnings=None):
        self.tactic = tactic
        self.success = success
        self.message = message
        self.cost = cost
        self.relationship_change = relationship_change
        self.weeks_added = weeks_added
        self.details = details or {}
        self.warnings = warnings or []
        self.timestamp = datetime.now().isoformat()

    def to_dict(self):
        return {
            'tactic': self.tactic,
            'success': self.success,
            'message': self.message,
            'cost': self.cost,
            'relationship_change': self.relationship_change,
            'weeks_added': self.weeks_added,
            'details': self.details,
            'warnings': self.warnings,
            'timestamp': self.timestamp,
        }


# ─────────────────────────────────────────────
# Engine
# ─────────────────────────────────────────────

class AntiBiddingTactics:
    """STEP 133: Anti-Bidding War Tactics Engine."""

    # ── Tactic 1: Pre-emptive Signing ─────────────────────────

    def attempt_preemptive_signing(self, wrestler, offered_salary, offered_weeks,
                                   promotion_balance):
        """
        Offer a contract extension BEFORE wrestler reaches free agency.
        Best window: 4–26 weeks remaining.
        """
        warnings = []
        weeks_left = _weeks_to_expiry(wrestler)

        if weeks_left > PREEMPTIVE_WINDOW_WEEKS:
            return TacticResult(
                'preemptive_signing', False,
                f"{wrestler.name} has {weeks_left} weeks left — too early. "
                f"Approach within {PREEMPTIVE_WINDOW_WEEKS} weeks of expiry.",
                warnings=['Not in pre-emptive window yet.']
            )

        if weeks_left <= 0:
            return TacticResult(
                'preemptive_signing', False,
                f"{wrestler.name}'s contract already expired — use Free Agent system.",
                warnings=['Contract already expired.']
            )

        morale = getattr(wrestler, 'morale', 50)
        popularity = getattr(wrestler, 'popularity', 50)
        base_prob = morale / 100.0

        current_salary = self._get_current_salary(wrestler)
        ratio = offered_salary / max(current_salary, 500)
        if ratio >= 1.2:
            salary_bonus = 0.20
        elif ratio >= 1.1:
            salary_bonus = 0.12
        elif ratio >= 1.0:
            salary_bonus = 0.05
        else:
            salary_bonus = -0.10
            warnings.append('Salary below current pay — may insult wrestler.')

        pop_penalty = -0.10 if popularity >= 80 else -0.05 if popularity >= 60 else 0.0
        if popularity >= 80:
            warnings.append('High-profile star may prefer to test open market.')

        length_bonus = 0.12 if offered_weeks >= 104 else 0.06 if offered_weeks >= 52 else 0.0
        if offered_weeks < 52:
            warnings.append('Short-term offer provides little security incentive.')

        final_prob = min(0.95, max(0.05, base_prob + salary_bonus + pop_penalty + length_bonus))
        accepted = random.random() <= final_prob

        if accepted:
            return TacticResult(
                'preemptive_signing', True,
                f"✅ {wrestler.name} accepted the pre-emptive extension! "
                f"${offered_salary:,}/wk for {offered_weeks} weeks. No bidding war necessary.",
                relationship_change=random.randint(5, 12),
                weeks_added=offered_weeks,
                details={
                    'accepted_salary': offered_salary,
                    'accepted_weeks': offered_weeks,
                    'acceptance_probability': round(final_prob * 100, 1),
                    'rival_interest_blocked': True,
                },
                warnings=warnings
            )
        else:
            return TacticResult(
                'preemptive_signing', False,
                f"❌ {wrestler.name} declined the pre-emptive offer. "
                f"They want to test the open market. Prepare for potential bidding war.",
                relationship_change=random.randint(-3, 0),
                details={
                    'offered_salary': offered_salary,
                    'offered_weeks': offered_weeks,
                    'acceptance_probability': round(final_prob * 100, 1),
                    'rival_interest_blocked': False,
                },
                warnings=warnings
            )

    # ── Tactic 2: Long-Term Contract Lock ─────────────────────

    def offer_long_term_lock(self, wrestler, years, lock_salary, promotion_balance):
        """
        Multi-year deal at fair-to-generous rate.
        Wrestler trades open-market potential for guaranteed security.
        Best for mid-career wrestlers aged 25–33.
        """
        warnings = []

        if years < 1 or years > 5:
            return TacticResult('long_term_lock', False,
                                'Lock-in period must be 1–5 years.',
                                warnings=['Invalid years parameter.'])

        weeks = years * 52
        total_commitment = lock_salary * weeks

        if total_commitment > promotion_balance * 3:
            warnings.append(
                f'${total_commitment:,} commitment is large vs ${promotion_balance:,} balance.')

        morale = getattr(wrestler, 'morale', 50)
        age = getattr(wrestler, 'age', 30)

        if age < 25:
            age_mod = -0.10
            warnings.append('Young wrestlers prefer shorter deals to re-evaluate faster.')
        elif age <= 33:
            age_mod = 0.08
        elif age <= 38:
            age_mod = 0.15
        else:
            age_mod = 0.05
            if years >= 3:
                warnings.append('Older wrestlers may resist committing 3+ years.')

        market = self._estimate_market_salary(wrestler)
        ratio = lock_salary / max(market, 500)
        if ratio < 0.90:
            sal_mod = -0.20
            warnings.append('Salary significantly below market.')
        elif ratio < 1.00:
            sal_mod = -0.05
        elif ratio <= 1.10:
            sal_mod = 0.10
        else:
            sal_mod = 0.18

        base_prob = (morale / 100.0) * 0.6 + 0.2
        len_pen = -0.10 if years >= 4 else -0.04 if years == 3 else 0.0
        if years >= 4:
            warnings.append('4–5 year deals are hard sells.')

        final_prob = min(0.92, max(0.05, base_prob + age_mod + sal_mod + len_pen))
        accepted = random.random() <= final_prob

        if accepted:
            return TacticResult(
                'long_term_lock', True,
                f"🔒 {wrestler.name} signed a {years}-year lock! "
                f"${lock_salary:,}/wk for {weeks} weeks. Off the market.",
                relationship_change=random.randint(8, 15),
                weeks_added=weeks,
                details={
                    'years': years, 'weeks': weeks,
                    'locked_salary': lock_salary,
                    'market_salary_estimate': market,
                    'total_commitment': total_commitment,
                    'acceptance_probability': round(final_prob * 100, 1),
                    'rival_interest_blocked': True,
                },
                warnings=warnings
            )
        else:
            return TacticResult(
                'long_term_lock', False,
                f"❌ {wrestler.name} rejected the long-term lock. "
                f"They prefer shorter commitments or better terms.",
                relationship_change=random.randint(-5, -1),
                details={
                    'offered_years': years, 'offered_salary': lock_salary,
                    'market_salary_estimate': market,
                    'acceptance_probability': round(final_prob * 100, 1),
                },
                warnings=warnings
            )

    # ── Tactic 3: Loyalty Bonus ────────────────────────────────

    def award_loyalty_bonus(self, wrestler, bonus_tier, promotion_balance):
        """
        Upfront cash bonus tied to retention commitment.
        Immediately improves morale and reduces free agency exploration.
        Tiers: 'small' (10%), 'medium' (20%), 'large' (35%) of annual salary.
        """
        warnings = []

        if bonus_tier not in LOYALTY_BONUS_PCTS:
            return TacticResult('loyalty_bonus', False,
                                f"Invalid tier '{bonus_tier}'. Choose: small, medium, large.",
                                warnings=['Invalid tier.'])

        annual_salary = self._get_current_salary(wrestler) * 52
        bonus_amount = int(annual_salary * LOYALTY_BONUS_PCTS[bonus_tier])

        if bonus_amount <= 0:
            return TacticResult('loyalty_bonus', False,
                                'Cannot calculate bonus — no salary on record.',
                                warnings=['No salary data.'])

        if bonus_amount > promotion_balance:
            return TacticResult('loyalty_bonus', False,
                                f"Insufficient funds. ${bonus_amount:,} needed, "
                                f"${promotion_balance:,} available.",
                                cost=bonus_amount, warnings=['Insufficient budget.'])

        morale = getattr(wrestler, 'morale', 50)
        if morale >= 80:
            morale_boost = random.randint(2, 6)
            warnings.append('Already happy — diminished morale returns.')
        elif morale >= 60:
            morale_boost = random.randint(6, 12)
        elif morale >= 40:
            morale_boost = random.randint(10, 18)
        else:
            morale_boost = random.randint(15, 25)

        deterrence = {'small': 0.40, 'medium': 0.65, 'large': 0.85}
        deterred = random.random() < deterrence[bonus_tier]
        tier_labels = {'small': '10%', 'medium': '20%', 'large': '35%'}

        return TacticResult(
            'loyalty_bonus', True,
            f"💰 ${bonus_amount:,} loyalty bonus awarded to {wrestler.name}! "
            f"({tier_labels[bonus_tier]} of annual salary). "
            + ("Committed to staying." if deterred else "Appreciated but still exploring options."),
            cost=bonus_amount,
            relationship_change=random.randint(5, 10),
            details={
                'bonus_tier': bonus_tier,
                'bonus_amount': bonus_amount,
                'morale_boost': morale_boost,
                'free_agency_deterred': deterred,
                'deterrence_probability': deterrence[bonus_tier] * 100,
            },
            warnings=warnings
        )

    # ── Tactic 4: Relationship Building ───────────────────────

    def invest_in_relationship(self, wrestler, investment_type, promotion_balance):
        """
        Non-monetary investments making money secondary in contract talks.

        investment_type:
          personal_call, creative_meeting, public_praise,
          merchandise_push ($15k), mentorship_role,
          title_conversation, schedule_relief
        """
        TYPES = {
            'personal_call': {
                'label': '📞 Personal Call from Management', 'cost': 0,
                'rel_range': (6, 14), 'morale_range': (4, 10),
                'description': 'Direct conversation showing the wrestler matters to leadership.',
                'rival_deterrence': 0.15,
            },
            'creative_meeting': {
                'label': '🎭 Collaborative Creative Meeting', 'cost': 0,
                'rel_range': (5, 12), 'morale_range': (8, 16),
                'description': 'Co-develop their storylines and character direction.',
                'rival_deterrence': 0.20,
            },
            'public_praise': {
                'label': '📣 Public Management Praise', 'cost': 0,
                'rel_range': (4, 9), 'morale_range': (5, 12),
                'description': 'Publicly validate their contributions via interviews or on-air.',
                'rival_deterrence': 0.12,
            },
            'merchandise_push': {
                'label': '👕 Priority Merchandise Push', 'cost': 15000,
                'rel_range': (8, 16), 'morale_range': (10, 18),
                'description': 'Priority merch production with larger revenue share.',
                'rival_deterrence': 0.35,
            },
            'mentorship_role': {
                'label': '🎓 Mentorship / Leadership Role', 'cost': 0,
                'rel_range': (7, 15), 'morale_range': (8, 16),
                'description': 'Give veterans coaching responsibility — purpose beyond matches.',
                'rival_deterrence': 0.28,
            },
            'title_conversation': {
                'label': '🏆 Honest Title Picture Discussion', 'cost': 0,
                'rel_range': (5, 18), 'morale_range': (6, 20),
                'description': 'Candid title trajectory talk. Honesty builds more trust than vague promises.',
                'rival_deterrence': 0.30,
            },
            'schedule_relief': {
                'label': '🏖 Schedule Relief', 'cost': 0,
                'rel_range': (6, 12), 'morale_range': (10, 20),
                'description': 'Reduce road schedule — shows you value their wellbeing.',
                'rival_deterrence': 0.22,
            },
        }

        if investment_type not in TYPES:
            return TacticResult(
                'relationship_building', False,
                f"Unknown type '{investment_type}'. Valid: {', '.join(TYPES.keys())}",
                warnings=['Invalid investment type.']
            )

        cfg = TYPES[investment_type]
        warnings = []
        cost = cfg['cost']

        if cost > promotion_balance:
            return TacticResult('relationship_building', False,
                                f"Cannot afford '{cfg['label']}'. "
                                f"Cost: ${cost:,} | Balance: ${promotion_balance:,}.",
                                cost=cost, warnings=['Insufficient budget.'])

        morale = getattr(wrestler, 'morale', 50)
        rlo, rhi = cfg['rel_range']
        mlo, mhi = cfg['morale_range']

        if morale >= 80:
            rel_change = random.randint(max(1, rlo - 4), max(2, rhi - 5))
            morale_boost = random.randint(max(1, mlo - 4), max(2, mhi - 5))
            warnings.append('Already happy — diminished returns.')
        else:
            rel_change = random.randint(rlo, rhi)
            morale_boost = random.randint(mlo, mhi)

        deterred = random.random() < cfg['rival_deterrence']

        return TacticResult(
            'relationship_building', True,
            f"{cfg['label']} completed for {wrestler.name}. "
            f"Relationship +{rel_change}, Morale +{morale_boost}. "
            + ("Reduced interest in rival offers." if deterred else
               "Appreciated, but not enough alone to deter rival interest."),
            cost=cost,
            relationship_change=rel_change,
            details={
                'investment_type': investment_type,
                'label': cfg['label'],
                'description': cfg['description'],
                'morale_boost': morale_boost,
                'rival_interest_deterred': deterred,
                'deterrence_probability': round(cfg['rival_deterrence'] * 100, 1),
            },
            warnings=warnings
        )

    # ── Advisor ───────────────────────────────────────────────

    def recommend_tactics(self, wrestler) -> dict:
        """Analyse wrestler situation and return ranked tactic recommendations."""
        morale = getattr(wrestler, 'morale', 50)
        age = getattr(wrestler, 'age', 30)
        popularity = getattr(wrestler, 'popularity', 50)
        weeks_left = _weeks_to_expiry(wrestler)
        recs = []

        if 4 <= weeks_left <= PREEMPTIVE_WINDOW_WEEKS:
            recs.append({
                'tactic': 'preemptive_signing',
                'priority': 'HIGH' if weeks_left <= 13 else 'MEDIUM',
                'reason': f"Contract expires in {weeks_left} weeks. Pre-emptive offer prevents bidding war.",
                'urgency_weeks': weeks_left,
            })

        if morale >= 55 and 25 <= age <= 35 and weeks_left <= 26:
            recs.append({
                'tactic': 'long_term_lock',
                'priority': 'HIGH' if morale >= 70 else 'MEDIUM',
                'reason': f"Age {age}, morale {morale} — prime window for multi-year security deal.",
            })

        if weeks_left <= 12 and morale < 70:
            tier = 'large' if morale < 40 else 'medium' if morale < 60 else 'small'
            recs.append({
                'tactic': 'loyalty_bonus',
                'priority': 'HIGH',
                'reason': f"Morale {morale} with {weeks_left} weeks left. {tier.title()} bonus deters exploration.",
                'suggested_tier': tier,
            })

        if morale < 60:
            recs.append({
                'tactic': 'relationship_building',
                'priority': 'HIGH' if morale < 40 else 'MEDIUM',
                'reason': f"Morale {morale} — address root cause. Try: personal_call + creative_meeting.",
                'suggested_types': ['personal_call', 'creative_meeting'],
            })
        elif popularity >= 70:
            recs.append({
                'tactic': 'relationship_building',
                'priority': 'MEDIUM',
                'reason': f"High-profile (pop {popularity}) — public_praise + title_conversation maintains loyalty.",
                'suggested_types': ['public_praise', 'title_conversation'],
            })

        if not recs:
            recs.append({
                'tactic': 'none_needed',
                'priority': 'LOW',
                'reason': f"{wrestler.name} stable (morale: {morale}, {weeks_left} weeks left). No action needed.",
            })

        recs.sort(key=lambda r: {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}.get(r.get('priority', 'LOW'), 2))

        return {
            'wrestler_id': getattr(wrestler, 'id', ''),
            'wrestler_name': getattr(wrestler, 'name', ''),
            'current_morale': morale,
            'current_age': age,
            'current_popularity': popularity,
            'weeks_to_expiry': weeks_left,
            'relationship_tier': _relationship_tier(morale),
            'risk_level': (
                'CRITICAL' if weeks_left <= 4 and morale < 50 else
                'HIGH' if weeks_left <= 12 or morale < 40 else
                'MEDIUM' if weeks_left <= 26 or morale < 60 else 'LOW'
            ),
            'recommendations': recs,
        }

    def get_at_risk_wrestlers(self, wrestlers: list) -> list:
        """Scan roster for wrestlers likely to trigger bidding wars."""
        at_risk = []
        for w in wrestlers:
            weeks_left = _weeks_to_expiry(w)
            morale = getattr(w, 'morale', 50)
            popularity = getattr(w, 'popularity', 50)

            if (weeks_left <= PREEMPTIVE_WINDOW_WEEKS or morale < 60) and popularity >= 50:
                score = (
                    max(0, PREEMPTIVE_WINDOW_WEEKS - weeks_left) * 2 +
                    max(0, 60 - morale) +
                    popularity // 10
                )
                at_risk.append({
                    'wrestler_id': getattr(w, 'id', ''),
                    'wrestler_name': getattr(w, 'name', ''),
                    'weeks_to_expiry': weeks_left,
                    'morale': morale,
                    'popularity': popularity,
                    'risk_score': score,
                    'risk_level': 'CRITICAL' if score >= 80 else 'HIGH' if score >= 50 else 'MEDIUM',
                    'primary_concern': (
                        'Contract expiring' if weeks_left <= 12 else
                        'Low morale' if morale < 40 else 'Expiring + unhappy'
                    ),
                })

        at_risk.sort(key=lambda x: x['risk_score'], reverse=True)
        return at_risk

    # ── Helpers ───────────────────────────────────────────────

    def _get_current_salary(self, wrestler) -> int:
        try:
            if hasattr(wrestler, 'contract') and wrestler.contract:
                return getattr(wrestler.contract, 'salary_per_show', 0)
        except Exception:
            pass
        return getattr(wrestler, 'salary_per_show', 500)

    def _estimate_market_salary(self, wrestler) -> int:
        popularity = getattr(wrestler, 'popularity', 50)
        role = getattr(wrestler, 'role', 'midcard').lower()
        base = {'main event': 8000, 'upper midcard': 5000, 'midcard': 3000,
                'lower midcard': 1800, 'jobber': 800}.get(role, 3000)
        return max(500, int(base * (1 + ((popularity - 50) / 50) * 0.40)))


# Global singleton
anti_bidding_tactics = AntiBiddingTactics()