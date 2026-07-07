"""
Free Agent Mood States (STEP 117)
Mood logic separated from pool management.
"""

from enum import Enum
from typing import Dict, Tuple, Optional
from dataclasses import dataclass


class FreeAgentMood(Enum):
    """Free agent mood states affecting negotiation behavior."""
    PATIENT = "patient"
    HUNGRY = "hungry"
    BITTER = "bitter"
    DESPERATE = "desperate"
    ARROGANT = "arrogant"


@dataclass
class MoodModifiers:
    """Modifiers applied based on mood state."""
    asking_price_multiplier: float
    minimum_price_multiplier: float
    acceptance_threshold: float
    negotiation_stubbornness: int
    counteroffer_aggression: float
    money_weight: float
    creative_weight: float
    prestige_weight: float
    will_accept_lowball: bool
    demands_extras: bool
    prone_to_leverage: bool
    
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
    """Static definitions of how each mood affects behavior."""
    
    MOOD_MODIFIERS: Dict[FreeAgentMood, MoodModifiers] = {
        FreeAgentMood.PATIENT: MoodModifiers(
            asking_price_multiplier=1.10,
            minimum_price_multiplier=0.95,
            acceptance_threshold=0.95,
            negotiation_stubbornness=7,
            counteroffer_aggression=1.5,
            money_weight=0.5,
            creative_weight=0.3,
            prestige_weight=0.2,
            will_accept_lowball=False,
            demands_extras=False,
            prone_to_leverage=True
        ),
        
        FreeAgentMood.HUNGRY: MoodModifiers(
            asking_price_multiplier=0.95,
            minimum_price_multiplier=0.80,
            acceptance_threshold=0.80,
            negotiation_stubbornness=3,
            counteroffer_aggression=0.8,
            money_weight=0.6,
            creative_weight=0.2,
            prestige_weight=0.2,
            will_accept_lowball=False,
            demands_extras=False,
            prone_to_leverage=False
        ),
        
        FreeAgentMood.BITTER: MoodModifiers(
            asking_price_multiplier=1.25,
            minimum_price_multiplier=1.05,
            acceptance_threshold=0.98,
            negotiation_stubbornness=9,
            counteroffer_aggression=2.0,
            money_weight=0.7,
            creative_weight=0.2,
            prestige_weight=0.1,
            will_accept_lowball=False,
            demands_extras=True,
            prone_to_leverage=True
        ),
        
        FreeAgentMood.DESPERATE: MoodModifiers(
            asking_price_multiplier=0.75,
            minimum_price_multiplier=0.60,
            acceptance_threshold=0.60,
            negotiation_stubbornness=1,
            counteroffer_aggression=0.5,
            money_weight=0.8,
            creative_weight=0.1,
            prestige_weight=0.1,
            will_accept_lowball=True,
            demands_extras=False,
            prone_to_leverage=False
        ),
        
        FreeAgentMood.ARROGANT: MoodModifiers(
            asking_price_multiplier=1.40,
            minimum_price_multiplier=1.15,
            acceptance_threshold=1.0,
            negotiation_stubbornness=10,
            counteroffer_aggression=2.0,
            money_weight=0.6,
            creative_weight=0.3,
            prestige_weight=0.1,
            will_accept_lowball=False,
            demands_extras=True,
            prone_to_leverage=True
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
    """Rules for when and how moods transition."""
    
    PATIENT_TO_HUNGRY_WEEKS = 8
    HUNGRY_TO_DESPERATE_WEEKS = 16
    DESPERATE_TO_BITTER_WEEKS = 24
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
        """Calculate appropriate mood based on multiple factors."""
        
        if has_controversy:
            if weeks_unemployed >= 12:
                return FreeAgentMood.DESPERATE
            elif departure_reason == 'released':
                return FreeAgentMood.BITTER
            else:
                return FreeAgentMood.HUNGRY
        
        if is_legend:
            if rejection_count >= 2:
                return FreeAgentMood.BITTER
            elif age < 45 and peak_popularity >= 80:
                return FreeAgentMood.ARROGANT
            elif weeks_unemployed < 12:
                return FreeAgentMood.PATIENT
            else:
                return FreeAgentMood.HUNGRY
        
        if is_major_superstar:
            if rejection_count >= cls.REJECTIONS_TO_BITTER:
                return FreeAgentMood.BITTER
            elif weeks_unemployed < 6 and rival_interest_count >= 2:
                return FreeAgentMood.ARROGANT
            elif weeks_unemployed < 10:
                return FreeAgentMood.PATIENT
            else:
                return FreeAgentMood.HUNGRY
        
        if departure_reason in ['released', 'fired']:
            if weeks_unemployed < 8:
                return FreeAgentMood.BITTER
            elif weeks_unemployed >= cls.DESPERATE_TO_BITTER_WEEKS:
                return FreeAgentMood.DESPERATE
            else:
                return FreeAgentMood.HUNGRY
        
        if rejection_count >= cls.REJECTIONS_TO_DESPERATE:
            return FreeAgentMood.DESPERATE
        elif rejection_count >= cls.REJECTIONS_TO_BITTER:
            if age < 35:
                return FreeAgentMood.BITTER
            else:
                return FreeAgentMood.DESPERATE
        
        if weeks_unemployed < cls.PATIENT_TO_HUNGRY_WEEKS:
            if rival_interest_count >= 2:
                return FreeAgentMood.ARROGANT
            else:
                return FreeAgentMood.PATIENT
        
        elif weeks_unemployed < cls.HUNGRY_TO_DESPERATE_WEEKS:
            return FreeAgentMood.HUNGRY
        
        else:
            if departure_reason == 'mutual' or current_popularity < 40:
                return FreeAgentMood.DESPERATE
            else:
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
        """Check if a mood transition should occur."""
        
        if current_mood == FreeAgentMood.ARROGANT:
            if rejection_count >= 2 and new_rival_offers == 0:
                return True, FreeAgentMood.PATIENT, "Market reality check"
            elif weeks_unemployed >= 12:
                return True, FreeAgentMood.BITTER, "Still no takers despite high demands"
        
        if current_mood == FreeAgentMood.PATIENT:
            if weeks_unemployed >= cls.PATIENT_TO_HUNGRY_WEEKS:
                return True, FreeAgentMood.HUNGRY, "Ready to make a deal"
        
        if current_mood == FreeAgentMood.PATIENT:
            if new_rival_offers >= 2:
                return True, FreeAgentMood.ARROGANT, "Multiple promotions interested"
        
        if current_mood == FreeAgentMood.HUNGRY:
            if weeks_unemployed >= cls.HUNGRY_TO_DESPERATE_WEEKS:
                return True, FreeAgentMood.DESPERATE, "Needs to sign soon"
        
        if current_mood == FreeAgentMood.HUNGRY:
            if new_rival_offers >= 1 and popularity_change > 5:
                return True, FreeAgentMood.PATIENT, "Renewed interest allows selectivity"
        
        if current_mood == FreeAgentMood.DESPERATE:
            if weeks_unemployed >= cls.DESPERATE_TO_BITTER_WEEKS:
                return True, FreeAgentMood.BITTER, "Frustration turned to resentment"
        
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
            FreeAgentMood.PATIENT: "success",
            FreeAgentMood.HUNGRY: "warning",
            FreeAgentMood.BITTER: "danger",
            FreeAgentMood.DESPERATE: "secondary",
            FreeAgentMood.ARROGANT: "purple"
        }
        return colors.get(mood, "secondary")


# CRITICAL: Export at module level for direct import
def calculate_mood(**kwargs) -> FreeAgentMood:
    """Convenience function for mood calculation"""
    return MoodTransitionRules.calculate_mood(**kwargs)


def get_mood_modifiers(mood: FreeAgentMood) -> MoodModifiers:
    """Convenience function for getting modifiers"""
    return MoodEffects.get_modifiers(mood)


def check_mood_transition(**kwargs) -> Tuple[bool, Optional[FreeAgentMood], str]:
    """Convenience function for transition checks"""
    return MoodTransitionRules.check_transition_trigger(**kwargs)


# CRITICAL: Make FreeAgentMood available at module level
__all__ = [
    'FreeAgentMood',
    'MoodModifiers',
    'MoodEffects',
    'MoodTransitionRules',
    'calculate_mood',
    'get_mood_modifiers',
    'check_mood_transition'
]