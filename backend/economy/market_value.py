"""
Market Value Calculator
Step 116: Comprehensive market value calculation for free agents.

Calculates free agent asking prices from:
- Peak popularity rating
- Recent match quality averages
- Age and remaining career projection
- Injury history
- Backstage reputation
- Current demand from other promotions
- Desperation level based on time unemployed
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import math


class MarketTrend(Enum):
    """Current market conditions affecting all values"""
    BUYERS_MARKET = "buyers_market"      # More talent than demand
    BALANCED = "balanced"                 # Normal conditions
    SELLERS_MARKET = "sellers_market"     # High demand, low supply
    HOT_MARKET = "hot_market"            # Bidding wars common


class CareerPhase(Enum):
    """Career phase affects value trajectory"""
    RISING = "rising"           # Young, improving (under 28)
    PRIME = "prime"             # Peak years (28-34)
    VETERAN = "veteran"         # Experienced but declining (35-40)
    TWILIGHT = "twilight"       # Near retirement (41+)
    LEGEND = "legend"           # Special case - legends transcend age


@dataclass
class MarketValueFactors:
    """All factors that contribute to market value calculation"""
    # Base factors
    base_value: int = 5000
    
    # Popularity factors
    current_popularity: int = 50
    peak_popularity: int = 50
    popularity_trend: int = 0  # Positive = rising, negative = falling
    
    # Performance factors
    average_match_rating: float = 3.0
    recent_match_rating: float = 3.0  # Last 10 matches
    five_star_match_count: int = 0
    four_plus_match_count: int = 0
    
    # Career factors
    age: int = 30
    years_experience: int = 5
    career_phase: CareerPhase = CareerPhase.PRIME
    projected_years_remaining: int = 10
    
    # Role and status
    role: str = "Midcard"
    is_major_superstar: bool = False
    is_legend: bool = False
    
    # Injury factors
    current_injury_severity: int = 0  # 0 = healthy
    injury_history_count: int = 0
    months_since_last_injury: int = 12
    has_chronic_issues: bool = False
    
    # Reputation factors
    backstage_reputation: int = 50  # 0-100
    locker_room_leader: bool = False
    known_difficult: bool = False
    controversy_severity: int = 0
    
    # Demand factors
    rival_promotion_interest: int = 0  # Number of interested promotions
    highest_rival_offer: int = 0
    bidding_war_active: bool = False
    
    # Desperation factors
    weeks_unemployed: int = 0
    mood: str = "patient"  # patient, hungry, bitter, desperate, arrogant
    
    # Market conditions
    market_trend: MarketTrend = MarketTrend.BALANCED
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'base_value': self.base_value,
            'current_popularity': self.current_popularity,
            'peak_popularity': self.peak_popularity,
            'popularity_trend': self.popularity_trend,
            'average_match_rating': self.average_match_rating,
            'recent_match_rating': self.recent_match_rating,
            'five_star_match_count': self.five_star_match_count,
            'four_plus_match_count': self.four_plus_match_count,
            'age': self.age,
            'years_experience': self.years_experience,
            'career_phase': self.career_phase.value,
            'projected_years_remaining': self.projected_years_remaining,
            'role': self.role,
            'is_major_superstar': self.is_major_superstar,
            'is_legend': self.is_legend,
            'current_injury_severity': self.current_injury_severity,
            'injury_history_count': self.injury_history_count,
            'months_since_last_injury': self.months_since_last_injury,
            'has_chronic_issues': self.has_chronic_issues,
            'backstage_reputation': self.backstage_reputation,
            'locker_room_leader': self.locker_room_leader,
            'known_difficult': self.known_difficult,
            'controversy_severity': self.controversy_severity,
            'rival_promotion_interest': self.rival_promotion_interest,
            'highest_rival_offer': self.highest_rival_offer,
            'bidding_war_active': self.bidding_war_active,
            'weeks_unemployed': self.weeks_unemployed,
            'mood': self.mood,
            'market_trend': self.market_trend.value
        }


@dataclass
class MarketValueBreakdown:
    """Detailed breakdown of how market value was calculated"""
    final_value: int
    base_value: int
    
    # Component values
    popularity_value: int = 0
    performance_value: int = 0
    career_value: int = 0
    role_value: int = 0
    injury_adjustment: int = 0
    reputation_adjustment: int = 0
    demand_adjustment: int = 0
    desperation_adjustment: int = 0
    market_adjustment: int = 0
    
    # Multipliers applied
    multipliers: Dict[str, float] = field(default_factory=dict)
    
    # Explanations
    explanations: List[str] = field(default_factory=list)
    
    # Confidence level (how reliable is this estimate)
    confidence: str = "medium"  # low, medium, high
    
    # Range
    low_estimate: int = 0
    high_estimate: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'final_value': self.final_value,
            'base_value': self.base_value,
            'components': {
                'popularity': self.popularity_value,
                'performance': self.performance_value,
                'career': self.career_value,
                'role': self.role_value,
                'injury_adjustment': self.injury_adjustment,
                'reputation_adjustment': self.reputation_adjustment,
                'demand_adjustment': self.demand_adjustment,
                'desperation_adjustment': self.desperation_adjustment,
                'market_adjustment': self.market_adjustment
            },
            'multipliers': self.multipliers,
            'explanations': self.explanations,
            'confidence': self.confidence,
            'range': {
                'low': self.low_estimate,
                'high': self.high_estimate
            }
        }


class MarketValueCalculator:
    """
    Comprehensive market value calculation engine.
    
    Considers all factors specified in Step 116:
    - Peak popularity rating
    - Recent match quality averages
    - Age and remaining career projection
    - Injury history
    - Backstage reputation
    - Current demand from other promotions
    - Desperation level based on time unemployed
    """
    
    # Base value ranges by role
    ROLE_BASE_VALUES = {
        'Main Event': 25000,
        'Upper Midcard': 15000,
        'Midcard': 8000,
        'Lower Midcard': 5000,
        'Jobber': 3000
    }
    
    # Role multipliers
    ROLE_MULTIPLIERS = {
        'Main Event': 2.5,
        'Upper Midcard': 1.8,
        'Midcard': 1.3,
        'Lower Midcard': 1.0,
        'Jobber': 0.7
    }
    
    # Career phase multipliers
    CAREER_PHASE_MULTIPLIERS = {
        CareerPhase.RISING: 1.2,      # Premium for potential
        CareerPhase.PRIME: 1.0,       # Standard
        CareerPhase.VETERAN: 0.85,    # Slight discount
        CareerPhase.TWILIGHT: 0.6,    # Significant discount
        CareerPhase.LEGEND: 1.5       # Premium for star power
    }
    
    # Mood modifiers (percentage adjustment)
    MOOD_MODIFIERS = {
        'patient': 0,          # No change
        'hungry': -15,         # Will accept 15% less
        'bitter': 20,          # Demands 20% more
        'desperate': -30,      # Will accept 30% less
        'arrogant': 25         # Demands 25% more (may be unrealistic)
    }
    
    # Market trend modifiers
    MARKET_TREND_MODIFIERS = {
        MarketTrend.BUYERS_MARKET: -15,
        MarketTrend.BALANCED: 0,
        MarketTrend.SELLERS_MARKET: 15,
        MarketTrend.HOT_MARKET: 30
    }
    
    def __init__(self, database=None):
        self.database = database
        self._market_trend = MarketTrend.BALANCED
    
    def set_market_trend(self, trend: MarketTrend):
        """Set current market conditions"""
        self._market_trend = trend
    
    def calculate_market_value(
        self,
        factors: MarketValueFactors,
        include_breakdown: bool = True
    ) -> Tuple[int, Optional[MarketValueBreakdown]]:
        """
        Calculate comprehensive market value.
        
        Returns:
            Tuple of (final_value, breakdown) if include_breakdown=True
            Tuple of (final_value, None) if include_breakdown=False
        """
        breakdown = MarketValueBreakdown(
            final_value=0,
            base_value=factors.base_value
        )
        
        # Start with base value for role
        base = self.ROLE_BASE_VALUES.get(factors.role, 8000)
        breakdown.base_value = base
        
        # =====================================================================
        # 1. POPULARITY VALUE
        # Peak popularity matters most, but current matters too
        # =====================================================================
        peak_value = factors.peak_popularity * 150  # Up to 15,000
        current_value = factors.current_popularity * 100  # Up to 10,000
        
        # Weight: 60% peak, 40% current
        popularity_value = int(peak_value * 0.6 + current_value * 0.4)
        
        # Bonus for rising popularity
        if factors.popularity_trend > 0:
            popularity_value += factors.popularity_trend * 50
            breakdown.explanations.append(f"Rising popularity (+${factors.popularity_trend * 50:,})")
        elif factors.popularity_trend < 0:
            popularity_value += factors.popularity_trend * 30  # Smaller penalty
            breakdown.explanations.append(f"Declining popularity (${factors.popularity_trend * 30:,})")
        
        breakdown.popularity_value = popularity_value
        
        # =====================================================================
        # 2. PERFORMANCE VALUE (Match Quality)
        # Recent performance weighted more heavily
        # =====================================================================
        # Average match rating contribution
        avg_rating_value = int((factors.average_match_rating - 2.0) * 2000)  # 2.0 is baseline
        
        # Recent performance (last 10 matches) - weighted more
        recent_rating_value = int((factors.recent_match_rating - 2.0) * 3000)
        
        # Bonus for exceptional matches
        five_star_bonus = factors.five_star_match_count * 2000
        four_plus_bonus = factors.four_plus_match_count * 500
        
        performance_value = avg_rating_value + recent_rating_value + five_star_bonus + four_plus_bonus
        performance_value = max(0, performance_value)  # Don't go negative
        
        if factors.five_star_match_count > 0:
            breakdown.explanations.append(f"{factors.five_star_match_count} five-star matches (+${five_star_bonus:,})")
        
        if factors.recent_match_rating >= 4.0:
            breakdown.explanations.append(f"Excellent recent match quality ({factors.recent_match_rating:.2f}★)")
        elif factors.recent_match_rating < 2.5:
            breakdown.explanations.append(f"Poor recent match quality ({factors.recent_match_rating:.2f}★)")
        
        breakdown.performance_value = performance_value
        
        # =====================================================================
        # 3. CAREER VALUE (Age & Projection)
        # =====================================================================
        # Determine career phase
        career_phase = self._determine_career_phase(factors.age, factors.is_legend)
        factors.career_phase = career_phase
        
        # Calculate projected years remaining
        projected_years = self._calculate_projected_years(factors.age, factors.is_legend)
        factors.projected_years_remaining = projected_years
        
        # Base career value on experience
        experience_value = min(factors.years_experience * 300, 6000)  # Cap at 20 years
        
        # Adjust for career phase
        phase_multiplier = self.CAREER_PHASE_MULTIPLIERS.get(career_phase, 1.0)
        career_value = int(experience_value * phase_multiplier)
        
        # Longevity premium for projected years
        if projected_years >= 10:
            career_value += 3000
            breakdown.explanations.append("Long career projection (+$3,000)")
        elif projected_years <= 3:
            career_value -= 2000
            breakdown.explanations.append("Short career remaining (-$2,000)")
        
        breakdown.career_value = career_value
        breakdown.multipliers['career_phase'] = phase_multiplier
        
        # =====================================================================
        # 4. ROLE VALUE
        # =====================================================================
        role_multiplier = self.ROLE_MULTIPLIERS.get(factors.role, 1.0)
        role_value = int(base * (role_multiplier - 1))  # Additional value from role
        
        # Major superstar premium
        if factors.is_major_superstar:
            role_value += 15000
            breakdown.explanations.append("Major superstar premium (+$15,000)")
        
        # Legend premium
        if factors.is_legend:
            role_value += 20000
            breakdown.explanations.append("Legend status (+$20,000)")
        
        breakdown.role_value = role_value
        breakdown.multipliers['role'] = role_multiplier
        
        # =====================================================================
        # 5. INJURY ADJUSTMENT
        # =====================================================================
        injury_adjustment = 0
        
        # Current injury penalty
        if factors.current_injury_severity > 0:
            severity_penalty = factors.current_injury_severity * 100
            injury_adjustment -= severity_penalty
            breakdown.explanations.append(f"Current injury (-${severity_penalty:,})")
        
        # Injury history penalty
        if factors.injury_history_count > 3:
            history_penalty = (factors.injury_history_count - 3) * 500
            injury_adjustment -= history_penalty
            breakdown.explanations.append(f"Injury-prone history (-${history_penalty:,})")
        
        # Recent injury penalty
        if factors.months_since_last_injury < 6:
            recent_penalty = (6 - factors.months_since_last_injury) * 300
            injury_adjustment -= recent_penalty
            breakdown.explanations.append(f"Recent injury concern (-${recent_penalty:,})")
        
        # Chronic issues major penalty
        if factors.has_chronic_issues:
            injury_adjustment -= 5000
            breakdown.explanations.append("Chronic injury issues (-$5,000)")
        
        breakdown.injury_adjustment = injury_adjustment
        
        # =====================================================================
        # 6. REPUTATION ADJUSTMENT
        # =====================================================================
        reputation_adjustment = 0
        
        # Backstage reputation (50 is neutral)
        if factors.backstage_reputation >= 70:
            rep_bonus = (factors.backstage_reputation - 50) * 50
            reputation_adjustment += rep_bonus
            breakdown.explanations.append(f"Excellent backstage reputation (+${rep_bonus:,})")
        elif factors.backstage_reputation < 30:
            rep_penalty = (50 - factors.backstage_reputation) * 75
            reputation_adjustment -= rep_penalty
            breakdown.explanations.append(f"Poor backstage reputation (-${rep_penalty:,})")
        
        # Locker room leader bonus
        if factors.locker_room_leader:
            reputation_adjustment += 3000
            breakdown.explanations.append("Locker room leader (+$3,000)")
        
        # Difficult to work with penalty
        if factors.known_difficult:
            reputation_adjustment -= 4000
            breakdown.explanations.append("Known as difficult (-$4,000)")
        
        # Controversy penalty
        if factors.controversy_severity > 0:
            controversy_penalty = int(factors.controversy_severity * 100)
            reputation_adjustment -= controversy_penalty
            breakdown.explanations.append(f"Controversy concerns (-${controversy_penalty:,})")
        
        breakdown.reputation_adjustment = reputation_adjustment
        
        # =====================================================================
        # 7. DEMAND ADJUSTMENT (Rival Interest)
        # =====================================================================
        demand_adjustment = 0
        
        # Multiple promotions interested drives up price
        if factors.rival_promotion_interest > 0:
            interest_bonus = factors.rival_promotion_interest * 2000
            demand_adjustment += interest_bonus
            breakdown.explanations.append(f"{factors.rival_promotion_interest} rival promotions interested (+${interest_bonus:,})")
        
        # Active bidding war premium
        if factors.bidding_war_active:
            demand_adjustment += 5000
            breakdown.explanations.append("Active bidding war (+$5,000)")
        
        # Highest rival offer influences minimum
        if factors.highest_rival_offer > 0:
            # Value should be at least close to highest offer
            demand_adjustment += int(factors.highest_rival_offer * 0.1)
            breakdown.explanations.append(f"Competing offer of ${factors.highest_rival_offer:,}")
        
        breakdown.demand_adjustment = demand_adjustment
        
        # =====================================================================
        # 8. DESPERATION ADJUSTMENT
        # =====================================================================
        desperation_adjustment = 0
        
        # Weeks unemployed affects asking price
        if factors.weeks_unemployed > 0:
            # Every 4 weeks, 5% reduction (up to 40%)
            weeks_factor = min(factors.weeks_unemployed // 4, 8)
            desperation_reduction = weeks_factor * 0.05
            
            if weeks_factor > 0:
                breakdown.multipliers['unemployment'] = 1 - desperation_reduction
        
        # Mood modifier
        mood_modifier = self.MOOD_MODIFIERS.get(factors.mood, 0)
        if mood_modifier != 0:
            breakdown.multipliers['mood'] = 1 + (mood_modifier / 100)
            if mood_modifier > 0:
                breakdown.explanations.append(f"Mood: {factors.mood} (demands +{mood_modifier}%)")
            else:
                breakdown.explanations.append(f"Mood: {factors.mood} (will accept {abs(mood_modifier)}% less)")
        
        breakdown.desperation_adjustment = desperation_adjustment
        
        # =====================================================================
        # 9. MARKET ADJUSTMENT
        # =====================================================================
        market_modifier = self.MARKET_TREND_MODIFIERS.get(factors.market_trend, 0)
        breakdown.multipliers['market'] = 1 + (market_modifier / 100)
        
        if market_modifier != 0:
            breakdown.explanations.append(f"Market conditions: {factors.market_trend.value}")
        
        # =====================================================================
        # FINAL CALCULATION
        # =====================================================================
        
        # Sum all components
        subtotal = (
            base +
            popularity_value +
            performance_value +
            career_value +
            role_value +
            injury_adjustment +
            reputation_adjustment +
            demand_adjustment
        )
        
        # Apply multipliers
        final = float(subtotal)
        
        for name, mult in breakdown.multipliers.items():
            final *= mult
        
        # Apply desperation reduction based on weeks unemployed
        if factors.weeks_unemployed > 0:
            weeks_factor = min(factors.weeks_unemployed // 4, 8)
            desperation_multiplier = 1 - (weeks_factor * 0.05)
            final *= desperation_multiplier
            breakdown.multipliers['unemployment_weeks'] = desperation_multiplier
        
        # Round to nearest $500
        final = round(final / 500) * 500
        
        # Minimum floor based on role
        minimum_values = {
            'Main Event': 15000,
            'Upper Midcard': 8000,
            'Midcard': 5000,
            'Lower Midcard': 3000,
            'Jobber': 2000
        }
        min_value = minimum_values.get(factors.role, 3000)
        final = max(int(final), min_value)
        
        breakdown.final_value = final
        
        # Calculate range
        breakdown.low_estimate = int(final * 0.8)
        breakdown.high_estimate = int(final * 1.2)
        
        # Determine confidence
        breakdown.confidence = self._determine_confidence(factors)
        
        if include_breakdown:
            return final, breakdown
        return final, None
    
    def _determine_career_phase(self, age: int, is_legend: bool) -> CareerPhase:
        """Determine career phase based on age"""
        if is_legend:
            return CareerPhase.LEGEND
        elif age < 28:
            return CareerPhase.RISING
        elif age <= 34:
            return CareerPhase.PRIME
        elif age <= 40:
            return CareerPhase.VETERAN
        else:
            return CareerPhase.TWILIGHT
    
    def _calculate_projected_years(self, age: int, is_legend: bool) -> int:
        """Calculate projected years remaining in career"""
        if is_legend:
            return 5  # Legends can go longer
        
        # Assume average retirement at 42
        typical_retirement = 42
        projected = max(0, typical_retirement - age)
        
        # Add some variance
        return projected
    
    def _determine_confidence(self, factors: MarketValueFactors) -> str:
        """Determine confidence level of the estimate"""
        confidence_score = 50  # Start at medium
        
        # More data = higher confidence
        if factors.years_experience >= 5:
            confidence_score += 10
        
        # Active market interest = higher confidence
        if factors.rival_promotion_interest > 0:
            confidence_score += 15
        
        # Recent match data = higher confidence
        if factors.recent_match_rating > 0:
            confidence_score += 10
        
        # Controversy = lower confidence (unpredictable)
        if factors.controversy_severity > 30:
            confidence_score -= 20
        
        # Extreme moods = lower confidence
        if factors.mood in ['desperate', 'arrogant']:
            confidence_score -= 10
        
        if confidence_score >= 70:
            return "high"
        elif confidence_score >= 40:
            return "medium"
        else:
            return "low"
    
    def calculate_from_free_agent(
        self,
        free_agent,
        match_history: Optional[List[Dict]] = None
    ) -> Tuple[int, MarketValueBreakdown]:
        """
        Calculate market value from a FreeAgent object.
        
        Args:
            free_agent: FreeAgent instance
            match_history: Optional list of recent match data
            
        Returns:
            Tuple of (final_value, breakdown)
        """
        # Build factors from free agent
        factors = MarketValueFactors(
            base_value=5000,
            current_popularity=free_agent.popularity,
            peak_popularity=max(free_agent.popularity, getattr(free_agent, 'peak_popularity', free_agent.popularity)),
            popularity_trend=0,
            age=free_agent.age,
            years_experience=free_agent.years_experience,
            role=free_agent.role,
            is_major_superstar=free_agent.is_major_superstar,
            is_legend=free_agent.is_legend,
            weeks_unemployed=free_agent.weeks_unemployed,
            mood=free_agent.mood.value if hasattr(free_agent.mood, 'value') else free_agent.mood,
            rivalry_promotion_interest=len(free_agent.rival_interest),
            highest_rival_offer=free_agent.highest_rival_offer,
            bidding_war_active=any(r.offer_made for r in free_agent.rival_interest),
            controversy_severity=free_agent.controversy_severity if free_agent.has_controversy else 0,
            market_trend=self._market_trend
        )
        
        # Add match history data if provided
        if match_history:
            total_rating = sum(m.get('star_rating', 3.0) for m in match_history)
            factors.average_match_rating = total_rating / len(match_history)
            
            # Recent matches (last 10)
            recent = match_history[-10:] if len(match_history) > 10 else match_history
            factors.recent_match_rating = sum(m.get('star_rating', 3.0) for m in recent) / len(recent)
            
            # Count exceptional matches
            factors.five_star_match_count = sum(1 for m in match_history if m.get('star_rating', 0) >= 5.0)
            factors.four_plus_match_count = sum(1 for m in match_history if 4.0 <= m.get('star_rating', 0) < 5.0)
        
        return self.calculate_market_value(factors)
    
    def get_quick_estimate(
        self,
        popularity: int,
        role: str,
        age: int,
        is_major_superstar: bool = False
    ) -> int:
        """
        Get a quick market value estimate without full calculation.
        Useful for UI previews.
        """
        base = self.ROLE_BASE_VALUES.get(role, 8000)
        
        # Popularity contribution
        pop_value = popularity * 100
        
        # Role multiplier
        role_mult = self.ROLE_MULTIPLIERS.get(role, 1.0)
        
        # Age adjustment
        if age < 28:
            age_mult = 1.1
        elif age <= 34:
            age_mult = 1.0
        elif age <= 40:
            age_mult = 0.85
        else:
            age_mult = 0.6
        
        # Calculate
        value = (base + pop_value) * role_mult * age_mult
        
        # Major superstar premium
        if is_major_superstar:
            value *= 1.3
        
        return round(value / 500) * 500


# Global calculator instance
market_value_calculator = MarketValueCalculator()