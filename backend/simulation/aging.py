"""
Aging System
Handles wrestler aging, attribute degradation, and retirement decisions.
"""

from typing import List, Dict, Tuple
from models.wrestler import Wrestler
import random


class AgingSystem:
    """
    Manages the yearly aging process for all wrestlers.
    
    Features:
    - Age progression at year-end
    - Attribute degradation based on age thresholds
    - Retirement probability calculations
    - Career longevity tracking
    """
    
    def __init__(self):
        pass
    
    def process_year_end_aging(self, wrestlers: List[Wrestler]) -> Dict:
        """
        Process aging for all active wrestlers at year-end (Week 52).
        
        Returns:
            {
                'aged_count': int,
                'retirements': List[Wrestler],
                'degradation_report': List[Dict]
            }
        """
        aged_count = 0
        retirements = []
        degradation_report = []
        
        for wrestler in wrestlers:
            if wrestler.is_retired:
                continue
            
            # Store pre-aging stats for comparison
            pre_age = wrestler.age
            pre_attrs = {
                'brawling': wrestler.brawling,
                'technical': wrestler.technical,
                'speed': wrestler.speed,
                'stamina': wrestler.stamina,
                'mic': wrestler.mic,
                'psychology': wrestler.psychology
            }
            
            # AGE THE WRESTLER
            wrestler.age_one_year()
            aged_count += 1
            
            # Check for attribute changes
            changes = {}
            if wrestler.brawling < pre_attrs['brawling']:
                changes['brawling'] = wrestler.brawling - pre_attrs['brawling']
            if wrestler.technical < pre_attrs['technical']:
                changes['technical'] = wrestler.technical - pre_attrs['technical']
            if wrestler.speed < pre_attrs['speed']:
                changes['speed'] = wrestler.speed - pre_attrs['speed']
            if wrestler.stamina < pre_attrs['stamina']:
                changes['stamina'] = wrestler.stamina - pre_attrs['stamina']
            if wrestler.mic < pre_attrs['mic']:
                changes['mic'] = wrestler.mic - pre_attrs['mic']
            if wrestler.psychology < pre_attrs['psychology']:
                changes['psychology'] = wrestler.psychology - pre_attrs['psychology']
            
            if changes:
                degradation_report.append({
                    'wrestler_id': wrestler.id,
                    'wrestler_name': wrestler.name,
                    'age': wrestler.age,
                    'changes': changes
                })
            
            # CHECK FOR RETIREMENT
            if wrestler.should_retire():
                wrestler.is_retired = True
                retirements.append(wrestler)
        
        return {
            'aged_count': aged_count,
            'retirements': retirements,
            'degradation_report': degradation_report
        }
    
    def calculate_retirement_probability(self, wrestler: Wrestler) -> float:
        """
        Calculate the probability (0.0 - 1.0) that a wrestler will retire.
        
        Factors:
        - Age (primary factor)
        - Injury history
        - Morale
        - Attribute decline
        - Years of experience
        """
        if wrestler.age < 40:
            return 0.0  # No retirement before 40
        
        base_prob = 0.0
        
        # Age-based probability
        if wrestler.age >= 50:
            base_prob = 0.9  # 90% chance at 50+
        elif wrestler.age >= 48:
            base_prob = 0.6  # 60% chance at 48-49
        elif wrestler.age >= 45:
            base_prob = 0.3  # 30% chance at 45-47
        elif wrestler.age >= 42:
            base_prob = 0.1  # 10% chance at 42-44
        else:  # 40-41
            base_prob = 0.02  # 2% chance at 40-41
        
        # Injury modifier (major injury = +20% chance)
        if wrestler.injury.severity == 'Major':
            base_prob += 0.2
        elif wrestler.injury.severity == 'Moderate':
            base_prob += 0.1
        
        # Morale modifier (unhappy veterans retire easier)
        if wrestler.morale < -50:
            base_prob += 0.15
        elif wrestler.morale < 0:
            base_prob += 0.05
        
        # Attribute decline modifier
        avg_attributes = (
            wrestler.brawling + wrestler.technical + wrestler.speed +
            wrestler.mic + wrestler.psychology + wrestler.stamina
        ) / 6
        
        if avg_attributes < 40:
            base_prob += 0.25  # Severely declined
        elif avg_attributes < 50:
            base_prob += 0.15  # Noticeably declined
        elif avg_attributes < 60:
            base_prob += 0.05  # Slight decline
        
        # Years of experience (30+ year veterans more likely to retire)
        if wrestler.years_experience >= 30:
            base_prob += 0.1
        elif wrestler.years_experience >= 25:
            base_prob += 0.05
        
        return min(1.0, base_prob)  # Cap at 100%
    
    def force_retirement(self, wrestler: Wrestler, reason: str = "career_end") -> Dict:
        """
        Force a wrestler to retire immediately.
        
        Args:
            wrestler: The wrestler to retire
            reason: Reason code ('career_end', 'injury', 'contract', 'request')
        
        Returns:
            Retirement event details
        """
        wrestler.is_retired = True
        
        # If they're a notable wrestler, add to departed pool for potential return
        if wrestler.is_major_superstar or wrestler.popularity >= 65:
            from simulation.events import events_manager
            events_manager.add_departed_wrestler(wrestler)
        
        return {
            'wrestler_id': wrestler.id,
            'wrestler_name': wrestler.name,
            'age': wrestler.age,
            'years_experience': wrestler.years_experience,
            'reason': reason,
            'is_major_superstar': wrestler.is_major_superstar,
            'final_popularity': wrestler.popularity
        }
    
    def check_for_comebacks(self, retired_wrestlers: List[Wrestler], current_year: int) -> List[Wrestler]:
        """
        Check if any retired wrestlers are eligible for surprise returns.
        
        Eligibility criteria:
        - Must be marked as major superstar or high popularity
        - Retired for at least 1 year (52 weeks)
        - Not returned in the past 2 years
        - Under age 55
        """
        eligible = []
        
        for wrestler in retired_wrestlers:
            if not (wrestler.is_major_superstar or wrestler.popularity >= 65):
                continue
            
            if wrestler.age > 55:
                continue
            
            # NOTE: In full implementation, track retirement_year
            # For now, all retired notable wrestlers are eligible
            eligible.append(wrestler)
        
        return eligible


# Global aging system instance
aging_system = AgingSystem()