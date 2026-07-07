"""
Roster Rotation System
Ensures all wrestlers get used regularly and fairly.

Tracks:
- Weeks since last match
- Total matches this month/year
- Overworked wrestlers (fatigue management)
- Underutilized talent
"""

from typing import List, Dict, Optional, Tuple
from models.wrestler import Wrestler
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class WrestlerUsageStats:
    """Tracks how often a wrestler is being used"""
    wrestler_id: str
    
    # Booking frequency
    weeks_since_last_match: int = 0
    matches_this_month: int = 0
    matches_this_year: int = 0
    
    # Overwork tracking
    consecutive_weeks_worked: int = 0
    total_fatigue_accumulated: int = 0
    
    # Match quality
    average_card_position: float = 5.0  # 1 = opener, 8 = main event
    
    # Last booked info
    last_match_year: int = 0
    last_match_week: int = 0
    
    def reset_monthly_stats(self):
        """Reset monthly counters"""
        self.matches_this_month = 0
    
    def reset_yearly_stats(self):
        """Reset yearly counters"""
        self.matches_this_year = 0
        self.matches_this_month = 0
    
    def to_dict(self):
        return {
            'wrestler_id': self.wrestler_id,
            'weeks_since_last_match': self.weeks_since_last_match,
            'matches_this_month': self.matches_this_month,
            'matches_this_year': self.matches_this_year,
            'consecutive_weeks_worked': self.consecutive_weeks_worked,
            'average_card_position': self.average_card_position
        }


class RotationManager:
    """Manages roster rotation and usage"""
    
    def __init__(self):
        self.usage_stats: Dict[str, WrestlerUsageStats] = {}
        self.current_year = 1
        self.current_week = 1
    
    def get_or_create_stats(self, wrestler_id: str) -> WrestlerUsageStats:
        """Get existing stats or create new"""
        if wrestler_id not in self.usage_stats:
            self.usage_stats[wrestler_id] = WrestlerUsageStats(wrestler_id=wrestler_id)
        return self.usage_stats[wrestler_id]
    
    def update_time(self, year: int, week: int):
        """
        Update current game time and increment weeks since last match.
        
        Call this BEFORE each show simulation.
        """
        
        weeks_passed = (year - self.current_year) * 52 + (week - self.current_week)
        
        # Increment weeks since last match for everyone
        for stats in self.usage_stats.values():
            stats.weeks_since_last_match += weeks_passed
        
        # Check for month/year rollover
        if week == 1 and year > self.current_year:
            # New year
            for stats in self.usage_stats.values():
                stats.reset_yearly_stats()
        elif week % 4 == 1:  # Rough monthly reset (every 4 weeks)
            for stats in self.usage_stats.values():
                stats.reset_monthly_stats()
        
        self.current_year = year
        self.current_week = week
    
    def record_match_appearance(
        self,
        wrestler_id: str,
        card_position: int,
        year: int,
        week: int
    ):
        """
        Record that a wrestler appeared on a show.
        
        Args:
            wrestler_id: ID of wrestler
            card_position: Position on card (1 = opener, 8 = main event)
            year: Year of show
            week: Week of show
        """
        
        stats = self.get_or_create_stats(wrestler_id)
        
        # Reset weeks since last match
        stats.weeks_since_last_match = 0
        
        # Increment counters
        stats.matches_this_month += 1
        stats.matches_this_year += 1
        
        # Update consecutive weeks
        if week == stats.last_match_week + 1 or (week == 1 and stats.last_match_week >= 50):
            stats.consecutive_weeks_worked += 1
        else:
            stats.consecutive_weeks_worked = 1
        
        # Update average card position (running average)
        if stats.matches_this_year == 1:
            stats.average_card_position = card_position
        else:
            # Weighted average (recent matches count more)
            stats.average_card_position = (stats.average_card_position * 0.7) + (card_position * 0.3)
        
        # Update last match info
        stats.last_match_year = year
        stats.last_match_week = week
    
    def get_underutilized_wrestlers(
        self,
        wrestlers: List[Wrestler],
        weeks_threshold: int = 3
    ) -> List[Tuple[Wrestler, WrestlerUsageStats]]:
        """
        Get wrestlers who haven't been used in a while.
        
        Args:
            wrestlers: All active wrestlers
            weeks_threshold: Weeks since last match to be considered underutilized
        
        Returns:
            List of (wrestler, stats) tuples
        """
        
        underutilized = []
        
        for wrestler in wrestlers:
            if wrestler.is_retired or not wrestler.can_compete:
                continue
            
            stats = self.get_or_create_stats(wrestler.id)
            
            if stats.weeks_since_last_match >= weeks_threshold:
                underutilized.append((wrestler, stats))
        
        # Sort by weeks since last match (most underutilized first)
        underutilized.sort(key=lambda x: x[1].weeks_since_last_match, reverse=True)
        
        return underutilized
    
    def get_overworked_wrestlers(
        self,
        wrestlers: List[Wrestler],
        fatigue_threshold: int = 70
    ) -> List[Tuple[Wrestler, WrestlerUsageStats]]:
        """
        Get wrestlers who are being overworked.
        
        Args:
            wrestlers: All active wrestlers
            fatigue_threshold: Fatigue level to be considered overworked
        
        Returns:
            List of (wrestler, stats) tuples
        """
        
        overworked = []
        
        for wrestler in wrestlers:
            if wrestler.is_retired:
                continue
            
            stats = self.get_or_create_stats(wrestler.id)
            
            # Check fatigue
            if wrestler.fatigue >= fatigue_threshold:
                overworked.append((wrestler, stats))
            
            # Check consecutive weeks
            elif stats.consecutive_weeks_worked >= 4:
                overworked.append((wrestler, stats))
        
        return overworked
    
    def should_rest_wrestler(self, wrestler: Wrestler) -> Tuple[bool, str]:
        """
        Determine if a wrestler should be rested.
        
        Returns:
            (should_rest, reason)
        """
        
        stats = self.get_or_create_stats(wrestler.id)
        
        # High fatigue
        if wrestler.fatigue >= 80:
            return (True, f"High fatigue ({wrestler.fatigue}/100)")
        
        # Worked too many consecutive weeks
        if stats.consecutive_weeks_worked >= 5:
            return (True, f"Worked {stats.consecutive_weeks_worked} weeks in a row")
        
        # Injured
        if wrestler.is_injured:
            return (True, f"Injured: {wrestler.injury.severity}")
        
        return (False, "Can compete")
    
    def prioritize_for_booking(
        self,
        wrestlers: List[Wrestler],
        max_count: int = 10
    ) -> List[Wrestler]:
        """
        Prioritize wrestlers for booking based on usage stats.
        
        Returns underutilized wrestlers who should get matches.
        
        Args:
            wrestlers: Available wrestlers
            max_count: Maximum wrestlers to return
        
        Returns:
            Prioritized list of wrestlers
        """
        
        scoreboard = []
        
        for wrestler in wrestlers:
            if not wrestler.can_compete or wrestler.is_retired:
                continue
            
            stats = self.get_or_create_stats(wrestler.id)
            
            # Calculate priority score
            score = 0
            
            # Weeks since last match (main factor)
            score += stats.weeks_since_last_match * 10
            
            # Underutilized this month
            if stats.matches_this_month == 0:
                score += 20
            
            # Role bonus (higher card should get more matches)
            role_bonuses = {
                'Main Event': 15,
                'Upper Midcard': 10,
                'Midcard': 5,
                'Lower Midcard': 2,
                'Jobber': 0
            }
            score += role_bonuses.get(wrestler.role, 0)
            
            # Momentum bonus (hot wrestlers should stay on TV)
            if wrestler.momentum > 20:
                score += 15
            elif wrestler.momentum > 10:
                score += 10
            
            # Popularity bonus
            score += wrestler.popularity * 0.1
            
            # Penalty for being overworked
            if stats.consecutive_weeks_worked >= 3:
                score -= 25
            
            # Penalty for high fatigue
            score -= wrestler.fatigue * 0.3
            
            scoreboard.append((wrestler, score, stats))
        
        # Sort by score
        scoreboard.sort(key=lambda x: x[1], reverse=True)
        
        return [w for w, score, stats in scoreboard[:max_count]]
    
    def get_rotation_summary(
        self,
        wrestlers: List[Wrestler]
    ) -> Dict[str, any]:
        """Get summary of roster rotation status"""
        
        underutilized = self.get_underutilized_wrestlers(wrestlers, weeks_threshold=2)
        overworked = self.get_overworked_wrestlers(wrestlers, fatigue_threshold=70)
        
        return {
            'total_active': len([w for w in wrestlers if not w.is_retired]),
            'underutilized_count': len(underutilized),
            'overworked_count': len(overworked),
            'underutilized': [
                {
                    'name': w.name,
                    'role': w.role,
                    'weeks_since_match': s.weeks_since_last_match,
                    'matches_this_month': s.matches_this_month
                }
                for w, s in underutilized[:10]
            ],
            'overworked': [
                {
                    'name': w.name,
                    'fatigue': w.fatigue,
                    'consecutive_weeks': s.consecutive_weeks_worked
                }
                for w, s in overworked[:10]
            ]
        }


# Global rotation manager instance
rotation_manager = RotationManager()