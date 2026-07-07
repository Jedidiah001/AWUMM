"""
Crowd Heat Tracking
Real-time crowd reaction simulation during matches.

Tracks:
- Crowd energy level (0-100)
- Pop/heat for specific moments
- Match pacing feedback
"""

import random
from typing import List, Dict, Any
from models.wrestler import Wrestler


class CrowdHeatTracker:
    """Tracks crowd reactions during a match"""
    
    def __init__(self):
        self.base_energy = 50
        self.current_energy = 50
        self.reactions = []
    
    def initialize_for_match(
        self,
        wrestlers: List[Wrestler],
        match_importance: str,
        is_title_match: bool,
        card_position: int
    ):
        """
        Set initial crowd energy based on match context.
        
        Args:
            wrestlers: All wrestlers in the match
            match_importance: normal/protect_both/high_drama
            is_title_match: True if championship on the line
            card_position: Position on card (higher = more important)
        """
        
        # Base energy from wrestler popularity
        avg_popularity = sum(w.popularity for w in wrestlers) / len(wrestlers)
        self.base_energy = avg_popularity * 0.5  # 0-50 from popularity
        
        # Card position bonus
        if card_position >= 7:  # Main event area
            self.base_energy += 20
        elif card_position >= 5:
            self.base_energy += 10
        
        # Match importance
        if match_importance == 'high_drama':
            self.base_energy += 15
        
        # Title match bonus
        if is_title_match:
            self.base_energy += 10
        
        # Clamp to 0-100
        self.base_energy = max(20, min(100, self.base_energy))
        self.current_energy = self.base_energy
        
        self.reactions = []
    
    def react_to_moment(self, moment_type: str, participants: List[str] = None) -> Dict[str, Any]:
        """
        Generate crowd reaction to a specific moment.
        
        Args:
            moment_type: Type of moment (nearfall, big_move, finish, etc.)
            participants: Wrestler names involved
        
        Returns:
            Reaction dict with energy_change, volume, description
        """
        
        reaction = {
            'moment_type': moment_type,
            'participants': participants or [],
            'energy_before': self.current_energy,
            'energy_change': 0,
            'volume': 'medium',
            'description': ''
        }
        
        # Calculate energy change based on moment type
        if moment_type == 'opening_bell':
            change = random.randint(0, 5)
            reaction['description'] = "Crowd buzzes as the bell rings!"
            reaction['volume'] = 'medium'
        
        elif moment_type == 'big_move':
            change = random.randint(5, 15)
            reaction['description'] = f"BIG POP for that move!"
            reaction['volume'] = 'loud'
        
        elif moment_type == 'nearfall':
            change = random.randint(10, 25)
            reaction['description'] = "CROWD ON THEIR FEET for the near-fall!"
            reaction['volume'] = 'very_loud'
        
        elif moment_type == 'comeback':
            change = random.randint(8, 18)
            reaction['description'] = "Crowd rallying behind the comeback!"
            reaction['volume'] = 'loud'
        
        elif moment_type == 'heel_heat':
            change = random.randint(-15, -5)  # Negative for heel heat
            reaction['description'] = "Massive heat! Crowd BOOING!"
            reaction['volume'] = 'very_loud'
        
        elif moment_type == 'signature_spot':
            change = random.randint(12, 20)
            reaction['description'] = "HUGE reaction for the signature move!"
            reaction['volume'] = 'very_loud'
        
        elif moment_type == 'false_finish':
            change = random.randint(15, 30)
            reaction['description'] = "DID THEY JUST KICK OUT?! Crowd going INSANE!"
            reaction['volume'] = 'deafening'
        
        elif moment_type == 'finish':
            change = random.randint(20, 35)
            reaction['description'] = "HUGE POP for the finish!"
            reaction['volume'] = 'deafening'
        
        elif moment_type == 'rest_hold':
            change = random.randint(-10, -3)
            reaction['description'] = "Crowd getting restless..."
            reaction['volume'] = 'quiet'
        
        elif moment_type == 'slow_moment':
            change = random.randint(-5, 0)
            reaction['description'] = "Crowd settling down."
            reaction['volume'] = 'quiet'
        
        else:
            change = random.randint(-2, 5)
            reaction['description'] = "Crowd reacts."
            reaction['volume'] = 'medium'
        
        # Apply energy change
        self.current_energy += change
        self.current_energy = max(0, min(100, self.current_energy))
        
        reaction['energy_change'] = change
        reaction['energy_after'] = self.current_energy
        
        self.reactions.append(reaction)
        
        return reaction
    
    def get_match_pacing_grade(self) -> str:
        """
        Grade the match pacing based on crowd energy fluctuations.
        
        Returns:
            Grade: 'Excellent', 'Great', 'Good', 'Average', 'Poor'
        """
        
        if not self.reactions:
            return 'Average'
        
        # Check for energy peaks and valleys (good pacing has variation)
        energies = [r['energy_after'] for r in self.reactions]
        
        avg_energy = sum(energies) / len(energies)
        max_energy = max(energies)
        min_energy = min(energies)
        
        energy_range = max_energy - min_energy
        
        # Good matches have high average energy AND good variation
        if avg_energy >= 70 and energy_range >= 40:
            return 'Excellent'
        elif avg_energy >= 60 and energy_range >= 30:
            return 'Great'
        elif avg_energy >= 50 and energy_range >= 20:
            return 'Good'
        elif avg_energy >= 40:
            return 'Average'
        else:
            return 'Poor'
    
    def get_crowd_rating_modifier(self) -> float:
        """
        Get star rating modifier based on crowd reactions.
        
        Returns:
            Modifier to add to star rating (-0.5 to +0.5)
        """
        
        pacing_grade = self.get_match_pacing_grade()
        
        modifiers = {
            'Excellent': 0.5,
            'Great': 0.25,
            'Good': 0.0,
            'Average': -0.15,
            'Poor': -0.35
        }
        
        return modifiers.get(pacing_grade, 0.0)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get full crowd reaction summary"""
        
        return {
            'starting_energy': self.base_energy,
            'ending_energy': self.current_energy,
            'energy_delta': self.current_energy - self.base_energy,
            'pacing_grade': self.get_match_pacing_grade(),
            'total_reactions': len(self.reactions),
            'loudest_moments': sorted(
                self.reactions,
                key=lambda r: abs(r['energy_change']),
                reverse=True
            )[:3],
            'rating_modifier': self.get_crowd_rating_modifier()
        }


def create_crowd_tracker() -> CrowdHeatTracker:
    """Factory function to create a new crowd tracker"""
    return CrowdHeatTracker()