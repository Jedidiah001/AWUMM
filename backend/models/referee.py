"""
Referee Personality System
Referees have personalities that affect DQ strictness and match flow.
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum
import random


class RefereeStyle(Enum):
    """Referee officiating style"""
    STRICT = "strict"              # Quick to call DQ, by-the-book
    LENIENT = "lenient"            # Lets things slide, allows brawling
    CHAOTIC = "chaotic"            # Unpredictable, can be distracted
    VETERAN = "veteran"            # Experienced, handles big matches well


@dataclass
class Referee:
    """
    Wrestling referee with personality traits.
    
    Attributes affect:
    - DQ probability
    - Count-out speed
    - Distraction vulnerability
    - Big match temperament
    """
    
    ref_id: str
    name: str
    style: RefereeStyle
    
    # Stats (0-100)
    strictness: int = 50           # Higher = more likely to DQ
    distraction_resistance: int = 50  # Higher = harder to distract
    big_match_experience: int = 50    # Higher = better for main events
    
    years_experience: int = 5
    
    def get_dq_probability(self, match_importance: str) -> float:
        """
        Calculate probability of calling a DQ in this match.
        
        Args:
            match_importance: 'normal', 'protect_both', or 'high_drama'
        
        Returns:
            Probability (0.0 - 1.0)
        """
        
        base_probability = self.strictness / 100
        
        # Style modifiers
        if self.style == RefereeStyle.STRICT:
            base_probability *= 1.5
        elif self.style == RefereeStyle.LENIENT:
            base_probability *= 0.5
        elif self.style == RefereeStyle.CHAOTIC:
            base_probability *= random.uniform(0.3, 1.7)  # Unpredictable
        
        # Match importance modifier (refs more lenient in big matches)
        if match_importance == 'high_drama':
            base_probability *= 0.7
        elif match_importance == 'protect_both':
            base_probability *= 1.3  # More likely to DQ to protect wrestlers
        
        return min(1.0, max(0.0, base_probability))
    
    def can_be_distracted(self) -> bool:
        """Check if referee can be distracted (for heel interference)"""
        
        resistance = self.distraction_resistance
        
        if self.style == RefereeStyle.STRICT:
            resistance += 20  # Harder to distract
        elif self.style == RefereeStyle.CHAOTIC:
            resistance -= 30  # Easily distracted
        
        # Roll against resistance
        roll = random.randint(0, 100)
        return roll > resistance
    
    def get_count_speed(self) -> str:
        """
        Get count-out/pinfall count speed.
        
        Returns:
            'fast', 'normal', or 'slow'
        """
        
        if self.style == RefereeStyle.STRICT:
            return 'fast'
        elif self.style == RefereeStyle.LENIENT:
            return 'slow'
        elif self.style == RefereeStyle.VETERAN:
            return 'normal'
        else:  # CHAOTIC
            return random.choice(['fast', 'normal', 'slow'])
    
    def is_suitable_for_main_event(self) -> bool:
        """Check if ref has experience for main event matches"""
        return self.big_match_experience >= 60 or self.style == RefereeStyle.VETERAN
    
    def to_dict(self):
        return {
            'ref_id': self.ref_id,
            'name': self.name,
            'style': self.style.value,
            'strictness': self.strictness,
            'distraction_resistance': self.distraction_resistance,
            'big_match_experience': self.big_match_experience,
            'years_experience': self.years_experience
        }


class RefereePool:
    """Manages all referees in the promotion"""
    
    def __init__(self):
        self.referees = self._generate_default_referees()
    
    def _generate_default_referees(self):
        """Create default referee roster"""
        
        return [
            Referee(
                ref_id='ref_001',
                name='Mike Chioda',
                style=RefereeStyle.VETERAN,
                strictness=60,
                distraction_resistance=75,
                big_match_experience=95,
                years_experience=25
            ),
            Referee(
                ref_id='ref_002',
                name='Charles Robinson',
                style=RefereeStyle.STRICT,
                strictness=80,
                distraction_resistance=70,
                big_match_experience=90,
                years_experience=20
            ),
            Referee(
                ref_id='ref_003',
                name='Earl Hebner',
                style=RefereeStyle.CHAOTIC,
                strictness=40,
                distraction_resistance=30,
                big_match_experience=85,
                years_experience=30
            ),
            Referee(
                ref_id='ref_004',
                name='Brian Hebner',
                style=RefereeStyle.LENIENT,
                strictness=35,
                distraction_resistance=50,
                big_match_experience=70,
                years_experience=15
            ),
            Referee(
                ref_id='ref_005',
                name='John Cone',
                style=RefereeStyle.VETERAN,
                strictness=55,
                distraction_resistance=80,
                big_match_experience=80,
                years_experience=18
            ),
            Referee(
                ref_id='ref_006',
                name='Jessika Carr',
                style=RefereeStyle.STRICT,
                strictness=75,
                distraction_resistance=85,
                big_match_experience=65,
                years_experience=8
            )
        ]
    
    def get_referee_for_match(self, match_importance: str, is_main_event: bool = False) -> Referee:
        """
        Select appropriate referee for a match.
        
        Args:
            match_importance: 'normal', 'protect_both', 'high_drama'
            is_main_event: True if this is the main event
        
        Returns:
            Selected Referee
        """
        
        if is_main_event:
            # Main events get veteran refs
            suitable = [r for r in self.referees if r.is_suitable_for_main_event()]
            return random.choice(suitable) if suitable else self.referees[0]
        
        elif match_importance == 'high_drama':
            # Important matches get experienced refs
            experienced = [r for r in self.referees if r.big_match_experience >= 70]
            return random.choice(experienced) if experienced else random.choice(self.referees)
        
        else:
            # Normal matches can have any ref
            return random.choice(self.referees)
    
    def get_random_referee(self) -> Referee:
        """Get a random referee"""
        return random.choice(self.referees)


# Global referee pool
referee_pool = RefereePool()