"""
Free Agent Mood States (STEP 117)
Defines mood states and their effects on negotiations.
"""

from enum import Enum
from typing import Dict, Tuple, Optional
from dataclasses import dataclass


class FreeAgentMood(Enum):
    """
    Free agent mood states affecting negotiation behavior.
    
    Moods are determined by:
    - Time unemployed
    - Rejection count
    - Rival interest level
    - Departure circumstances
    - Age and career stage
    """
    PATIENT = "patient"          # Waiting for right offer, will negotiate hard
    HUNGRY = "hungry"            # Wants to sign soon, more flexible
    BITTER = "bitter"            # Bad departure, demands premium
    DESPERATE = "desperate"      # Unemployed too long, very flexible
    ARROGANT = "arrogant"       # Overvalues self despite reality


@dataclass
class MoodModifiers:
    """
    Modifiers applied based on mood state.
    """
    # Price modifiers (multiplier to base asking price)
    asking_price_multiplier: float
    minimum_price_multiplier: float
    
    # Negotiation behavior
    acceptance_threshold: float  # % of asking price they'll accept (0.0-1.0)
    negotiation_stubbornness: int  # How many rounds they'll hold out (1-10)
    counteroffer_aggression: float  # How much they push back (0.5-2.0)
    
    # Decision factors
    money_weight: float  # How much they prioritize money vs other factors
    creative_weight: float  # How much they value creative control
    prestige_weight: float  # How much promotion prestige matters
    
    # Special behaviors
    will_accept_lowball: bool  # Accept offers significantly below asking
    demands_extras: bool  # Requires sweeteners beyond base salary
    prone_to_leverage: bool  # Uses rival offers to drive up price
    
    def to_dict(self) -> Dict:
        return {
            'asking_price_multiplier': self.asking_price_multiplier,
            'minimum_price_multiplier': self.minimum_price_multiplier,
            'acceptance_threshold': self.acceptance_threshold,
            'negotiation_stubbornness': self.negotiation_stubbornness,
            'counteroffer_aggression': self.counteroffer_aggression,
            'money_weight': self.money_weight,
            'creative_weight': self.creative_weight,
            'prestige_weight': self.prestige_weight,
            'will_accept_lowball': self.will_accept_lowball,
            'demands_extras': self.demands_extras,
            'prone_to_leverage': self.prone_to_leverage
        }


class MoodEffects:
    """
    Static definitions of how each mood affects behavior.
    """
    
    MOOD_MODIFIERS: Dict[FreeAgentMood, MoodModifiers] = {
        FreeAgentMood.PATIENT: MoodModifiers(
            asking_price_multiplier=1.10,      # +10% asking price
            minimum_price_multiplier=0.95,     # Will go 5% below base
            acceptance_threshold=0.95,         # Accepts 95%+ of asking
            negotiation_stubbornness=7,        # Very stubborn
            counteroffer_aggression=1.5,       # Pushes back hard
            money_weight=0.5,                  # Balanced priorities
            creative_weight=0.3,
            prestige_weight=0.2,
            will_accept_lowball=False,
            demands_extras=False,
            prone_to_leverage=True             # Will shop around
        ),
        
        FreeAgentMood.HUNGRY: MoodModifiers(
            asking_price_multiplier=0.95,      # -5% asking price
            minimum_price_multiplier=0.80,     # Will go 20% below base
            acceptance_threshold=0.80,         # Accepts 80%+ of asking
            negotiation_stubbornness=3,        # Not very stubborn
            counteroffer_aggression=0.8,       # Pushes back lightly
            money_weight=0.6,                  # Money important but flexible
            creative_weight=0.2,
            prestige_weight=0.2,
            will_accept_lowball=False,
            demands_extras=False,
            prone_to_leverage=False            # Wants deal done
        ),
        
        FreeAgentMood.BITTER: MoodModifiers(
            asking_price_multiplier=1.25,      # +25% asking price (revenge pricing)
            minimum_price_multiplier=1.05,     # Won't go below base
            acceptance_threshold=0.98,         # Accepts 98%+ only
            negotiation_stubbornness=9,        # Extremely stubborn
            counteroffer_aggression=2.0,       # Maximum pushback
            money_weight=0.7,                  # Money is validation
            creative_weight=0.2,
            prestige_weight=0.1,
            will_accept_lowball=False,
            demands_extras=True,               # Wants sweeteners
            prone_to_leverage=True             # Will use any leverage
        ),
        
        FreeAgentMood.DESPERATE: MoodModifiers(
            asking_price_multiplier=0.75,      # -25% asking price
            minimum_price_multiplier=0.60,     # Will go 40% below base
            acceptance_threshold=0.60,         # Accepts 60%+ of asking
            negotiation_stubbornness=1,        # Not stubborn at all
            counteroffer_aggression=0.5,       # Barely pushes back
            money_weight=0.8,                  # Just needs income
            creative_weight=0.1,
            prestige_weight=0.1,
            will_accept_lowball=True,          # Will take almost anything
            demands_extras=False,
            prone_to_leverage=False            # No position to leverage
        ),
        
        FreeAgentMood.ARROGANT: MoodModifiers(
            asking_price_multiplier=1.40,      # +40% asking price (delusional)
            minimum_price_multiplier=1.15,     # Won't negotiate down
            acceptance_threshold=1.0,          # Only accepts asking or higher
            negotiation_stubbornness=10,       # Maximum stubbornness
            counteroffer_aggression=2.0,       # Aggressive counteroffers
            money_weight=0.6,
            creative_weight=0.3,               # Wants control
            prestige_weight=0.1,
            will_accept_lowball=False,
            demands_extras=True,               # Expects premium treatment
            prone_to_leverage=True             # Overplays their hand
        )
    }
    
    @classmethod
    def get_modifiers(cls, mood: FreeAgentMood) -> MoodModifiers:
        """Get modifiers for a specific mood"""
        return cls.MOOD_MODIFIERS[mood]
    
    @classmethod
    def get_mood_description(cls, mood: FreeAgentMood) -> str:
        """Get human-readable description of mood"""
        descriptions = {
            FreeAgentMood.PATIENT: "Waiting for the right opportunity. Will negotiate carefully and isn't desperate to sign.",
            FreeAgentMood.HUNGRY: "Ready to make a deal. More flexible on terms and eager to get back in the ring.",
            FreeAgentMood.BITTER: "Resentful about their departure. Demands premium compensation and may be difficult to work with.",
            FreeAgentMood.DESPERATE: "Needs to sign quickly. Very flexible on terms and willing to accept lower offers.",
            FreeAgentMood.ARROGANT: "Overvalues their worth. Demands top dollar despite market reality and refuses to budge."
        }
        return descriptions.get(mood, "Unknown mood state")
    
    @classmethod
    def get_negotiation_tips(cls, mood: FreeAgentMood) -> list:
        """Get tips for negotiating with this mood"""
        tips = {
            FreeAgentMood.PATIENT: [
                "Be prepared for lengthy negotiations",
                "Offer fair market value or slightly above",
                "Emphasize creative opportunities",
                "Show long-term commitment to their career"
            ],
            FreeAgentMood.HUNGRY: [
                "Strike while they're motivated",
                "Fair offers will be accepted quickly",
                "Emphasize immediate opportunities",
                "Less need for extensive sweeteners"
            ],
            FreeAgentMood.BITTER: [
                "Expect difficult negotiations",
                "Premium salary required",
                "May need creative control guarantees",
                "Be prepared to walk away if unreasonable"
            ],
            FreeAgentMood.DESPERATE: [
                "Great opportunity for bargain signing",
                "Can offer below market value",
                "Focus on opportunity over money",
                "Move quickly before they become bitter"
            ],
            FreeAgentMood.ARROGANT: [
                "Extremely difficult to sign",
                "May demand more than they're worth",
                "Reality check may be needed",
                "Consider waiting for mood to change"
            ]
        }
        return tips.get(mood, [])


class MoodTransitionRules:
    """
    Rules for when and how moods transition.
    """
    
    # Weeks unemployed thresholds
    PATIENT_TO_HUNGRY_WEEKS = 8
    HUNGRY_TO_DESPERATE_WEEKS = 16
    DESPERATE_TO_BITTER_WEEKS = 24  # Desperation can turn to bitterness
    
    # Rejection count thresholds
    REJECTIONS_TO_BITTER = 3
    REJECTIONS_TO_DESPERATE = 5
    
    @classmethod
    def calculate_mood(
        cls,
        weeks_unemployed: int,
        rejection_count: int,
        departure_reason: str,
        rival_interest_count: int,
        is_legend: bool,
        is_major_superstar: bool,
        age: int,
        peak_popularity: int,
        current_popularity: int,
        has_controversy: bool
    ) -> FreeAgentMood:
        """
        Calculate appropriate mood based on multiple factors.
        
        Priority order:
        1. Controversy cases → Usually DESPERATE or BITTER
        2. Legends → Usually PATIENT or ARROGANT
        3. Departure reason → Can force BITTER
        4. Time + rejections → DESPERATE path
        5. Default path based on weeks unemployed
        """
        
        # CONTROVERSY: Depends on severity and time since incident
        if has_controversy:
            if weeks_unemployed >= 12:
                return FreeAgentMood.DESPERATE  # No one wants to touch them
            elif departure_reason == 'released':
                return FreeAgentMood.BITTER     # Angry about how they were treated
            else:
                return FreeAgentMood.HUNGRY     # Trying to prove themselves
        
        # LEGENDS: Tend toward patience or arrogance
        if is_legend:
            # Legends with high recent rejection count become bitter
            if rejection_count >= 2:
                return FreeAgentMood.BITTER
            # Legends who think they're still worth top dollar
            elif age < 45 and peak_popularity >= 80:
                return FreeAgentMood.ARROGANT
            # Legends taking their time
            elif weeks_unemployed < 12:
                return FreeAgentMood.PATIENT
            # Even legends get hungry eventually
            else:
                return FreeAgentMood.HUNGRY
        
        # MAJOR SUPERSTARS: Similar to legends but less extreme
        if is_major_superstar:
            if rejection_count >= cls.REJECTIONS_TO_BITTER:
                return FreeAgentMood.BITTER
            elif weeks_unemployed < 6 and rival_interest_count >= 2:
                return FreeAgentMood.ARROGANT  # In demand
            elif weeks_unemployed < 10:
                return FreeAgentMood.PATIENT
            else:
                return FreeAgentMood.HUNGRY
        
        # BITTER DEPARTURE: Forced by circumstances
        if departure_reason in ['released', 'fired']:
            # Recent releases are bitter
            if weeks_unemployed < 8:
                return FreeAgentMood.BITTER
            # But bitterness fades to desperation over time
            elif weeks_unemployed >= cls.DESPERATE_TO_BITTER_WEEKS:
                return FreeAgentMood.DESPERATE
            else:
                return FreeAgentMood.HUNGRY
        
        # HIGH REJECTION COUNT: Path to desperation or bitterness
        if rejection_count >= cls.REJECTIONS_TO_DESPERATE:
            return FreeAgentMood.DESPERATE
        elif rejection_count >= cls.REJECTIONS_TO_BITTER:
            # Younger wrestlers get bitter, older ones get desperate
            if age < 35:
                return FreeAgentMood.BITTER
            else:
                return FreeAgentMood.DESPERATE
        
        # TIME UNEMPLOYED: Standard progression
        if weeks_unemployed < cls.PATIENT_TO_HUNGRY_WEEKS:
            # Recently available, still selective
            if rival_interest_count >= 2:
                return FreeAgentMood.ARROGANT  # Multiple suitors
            else:
                return FreeAgentMood.PATIENT
        
        elif weeks_unemployed < cls.HUNGRY_TO_DESPERATE_WEEKS:
            # Getting eager to sign
            return FreeAgentMood.HUNGRY
        
        else:
            # Been out too long, getting desperate
            # But some turn bitter instead
            if departure_reason == 'mutual' or current_popularity < 40:
                return FreeAgentMood.DESPERATE
            else:
                # Still has pride, becomes bitter instead
                return FreeAgentMood.BITTER
    
    @classmethod
    def check_transition_trigger(
        cls,
        current_mood: FreeAgentMood,
        weeks_unemployed: int,
        rejection_count: int,
        new_rival_offers: int,
        popularity_change: int
    ) -> Tuple[bool, Optional[FreeAgentMood], str]:
        """
        Check if a mood transition should occur based on recent events.
        
        Returns:
            (should_transition, new_mood, reason)
        """
        
        # ARROGANT → PATIENT: Reality check
        if current_mood == FreeAgentMood.ARROGANT:
            if rejection_count >= 2 and new_rival_offers == 0:
                return True, FreeAgentMood.PATIENT, "Market reality check"
            elif weeks_unemployed >= 12:
                return True, FreeAgentMood.BITTER, "Still no takers despite high demands"
        
        # PATIENT → HUNGRY: Time passing
        if current_mood == FreeAgentMood.PATIENT:
            if weeks_unemployed >= cls.PATIENT_TO_HUNGRY_WEEKS:
                return True, FreeAgentMood.HUNGRY, "Ready to make a deal"
        
        # PATIENT → ARROGANT: New interest
        if current_mood == FreeAgentMood.PATIENT:
            if new_rival_offers >= 2:
                return True, FreeAgentMood.ARROGANT, "Multiple promotions interested"
        
        # HUNGRY → DESPERATE: Too long unemployed
        if current_mood == FreeAgentMood.HUNGRY:
            if weeks_unemployed >= cls.HUNGRY_TO_DESPERATE_WEEKS:
                return True, FreeAgentMood.DESPERATE, "Needs to sign soon"
        
        # HUNGRY → PATIENT: New opportunities
        if current_mood == FreeAgentMood.HUNGRY:
            if new_rival_offers >= 1 and popularity_change > 5:
                return True, FreeAgentMood.PATIENT, "Renewed interest allows selectivity"
        
        # DESPERATE → BITTER: Desperation curdles
        if current_mood == FreeAgentMood.DESPERATE:
            if weeks_unemployed >= cls.DESPERATE_TO_BITTER_WEEKS:
                return True, FreeAgentMood.BITTER, "Frustration turned to resentment"
        
        # BITTER → DESPERATE: Bitterness fades to necessity
        if current_mood == FreeAgentMood.BITTER:
            if weeks_unemployed >= 20 and rejection_count >= 4:
                return True, FreeAgentMood.DESPERATE, "Must swallow pride to get signed"
        
        return False, None, ""
    
    @classmethod
    def get_mood_label(cls, mood: FreeAgentMood) -> str:
        """Get display label for mood"""
        labels = {
            FreeAgentMood.PATIENT: "Patient",
            FreeAgentMood.HUNGRY: "Hungry",
            FreeAgentMood.BITTER: "Bitter",
            FreeAgentMood.DESPERATE: "Desperate",
            FreeAgentMood.ARROGANT: "Arrogant"
        }
        return labels.get(mood, "Unknown")
    
    @classmethod
    def get_mood_color(cls, mood: FreeAgentMood) -> str:
        """Get color code for UI display"""
        colors = {
            FreeAgentMood.PATIENT: "success",    # Green
            FreeAgentMood.HUNGRY: "warning",     # Yellow
            FreeAgentMood.BITTER: "danger",      # Red
            FreeAgentMood.DESPERATE: "secondary", # Gray
            FreeAgentMood.ARROGANT: "purple"     # Purple
        }
        return colors.get(mood, "secondary")


# Export commonly used functions at module level
def calculate_mood(**kwargs) -> FreeAgentMood:
    """Convenience function for mood calculation"""
    return MoodTransitionRules.calculate_mood(**kwargs)


def get_mood_modifiers(mood: FreeAgentMood) -> MoodModifiers:
    """Convenience function for getting modifiers"""
    return MoodEffects.get_modifiers(mood)


def check_mood_transition(**kwargs) -> Tuple[bool, Optional[FreeAgentMood], str]:
    """Convenience function for transition checks"""
    return MoodTransitionRules.check_transition_trigger(**kwargs)