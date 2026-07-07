"""
Stats Models
Data classes for wrestler statistics and promotion records.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class WrestlerStats:
    """Complete career statistics for a wrestler"""
    wrestler_id: str
    wrestler_name: str
    
    # Basic Record
    total_matches: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0
    win_percentage: float = 0.0
    
    # Match Quality
    average_star_rating: float = 0.0
    highest_star_rating: float = 0.0
    total_star_rating: float = 0.0
    five_star_matches: int = 0
    four_star_plus_matches: int = 0
    
    # Championships
    total_title_reigns: int = 0
    total_days_as_champion: int = 0
    longest_reign_days: int = 0
    current_title_reign_days: int = 0
    
    # Achievements
    total_main_events: int = 0  # FIXED: Changed from 'main_events'
    total_ppv_matches: int = 0  # FIXED: Changed from 'ppv_matches'
    total_upsets: int = 0       # FIXED: Changed from 'upsets_caused'
    total_upset_losses: int = 0  # FIXED: Changed from 'upset_losses'
    
    # Finish Breakdown
    clean_wins: int = 0
    cheating_wins: int = 0
    dq_countout_wins: int = 0
    submission_wins: int = 0
    
    # Streaks
    current_win_streak: int = 0
    current_loss_streak: int = 0
    longest_win_streak: int = 0
    longest_loss_streak: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'wrestler_id': self.wrestler_id,
            'wrestler_name': self.wrestler_name,
            'record': {
                'total_matches': self.total_matches,
                'wins': self.wins,
                'losses': self.losses,
                'draws': self.draws,
                'win_percentage': round(self.win_percentage, 1)
            },
            'match_quality': {
                'average_star_rating': round(self.average_star_rating, 2),
                'highest_star_rating': self.highest_star_rating,
                'five_star_matches': self.five_star_matches,
                'four_star_plus_matches': self.four_star_plus_matches
            },
            'title_history': {
                'total_reigns': self.total_title_reigns,
                'total_days': self.total_days_as_champion,
                'longest_reign_days': self.longest_reign_days,
                'current_reign_days': self.current_title_reign_days
            },
            'achievements': {
                'main_events': self.total_main_events,      # Maps to total_main_events
                'ppv_matches': self.total_ppv_matches,      # Maps to total_ppv_matches
                'upsets_caused': self.total_upsets,         # Maps to total_upsets
                'upset_losses': self.total_upset_losses     # Maps to total_upset_losses
            },
            'finish_breakdown': {
                'clean_wins': self.clean_wins,
                'cheating_wins': self.cheating_wins,
                'dq_countout_wins': self.dq_countout_wins,
                'submission_wins': self.submission_wins
            },
            'streaks': {
                'current_win_streak': self.current_win_streak,
                'current_loss_streak': self.current_loss_streak,
                'longest_win_streak': self.longest_win_streak,
                'longest_loss_streak': self.longest_loss_streak
            }
        }

@dataclass
class PromotionRecords:
    """Promotion-wide records and achievements"""
    
    # Match Records
    highest_rated_match: Optional[Dict[str, Any]] = None
    lowest_rated_match: Optional[Dict[str, Any]] = None
    longest_match: Optional[Dict[str, Any]] = None
    shortest_match: Optional[Dict[str, Any]] = None
    
    # Wrestler Records
    most_wins: Optional[Dict[str, Any]] = None
    best_win_percentage: Optional[Dict[str, Any]] = None
    most_title_reigns: Optional[Dict[str, Any]] = None
    longest_title_reign: Optional[Dict[str, Any]] = None
    
    # Streak Records
    longest_winning_streak: Optional[Dict[str, Any]] = None
    longest_losing_streak: Optional[Dict[str, Any]] = None
    
    # Show Records
    highest_rated_show: Optional[Dict[str, Any]] = None
    highest_attendance: Optional[Dict[str, Any]] = None
    highest_revenue: Optional[Dict[str, Any]] = None
    
    # Milestone Records
    most_five_star_matches: Optional[Dict[str, Any]] = None
    most_main_events: Optional[Dict[str, Any]] = None
    most_ppv_wins: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'match_records': {
                'highest_rated': self.highest_rated_match,
                'lowest_rated': self.lowest_rated_match,
                'longest': self.longest_match,
                'shortest': self.shortest_match
            },
            'wrestler_records': {
                'most_wins': self.most_wins,
                'best_win_percentage': self.best_win_percentage,
                'most_title_reigns': self.most_title_reigns,
                'longest_title_reign': self.longest_title_reign
            },
            'streak_records': {
                'longest_winning': self.longest_winning_streak,
                'longest_losing': self.longest_losing_streak
            },
            'show_records': {
                'highest_rated': self.highest_rated_show,
                'highest_attendance': self.highest_attendance,
                'highest_revenue': self.highest_revenue
            },
            'milestone_records': {
                'most_five_star_matches': self.most_five_star_matches,
                'most_main_events': self.most_main_events,
                'most_ppv_wins': self.most_ppv_wins
            }
        }


@dataclass
class Milestone:
    """A career milestone achievement"""
    milestone_id: str
    wrestler_id: str
    wrestler_name: str
    milestone_type: str
    description: str
    achieved_at_show_id: str
    achieved_at_show_name: str
    year: int
    week: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'milestone_id': self.milestone_id,
            'wrestler_id': self.wrestler_id,
            'wrestler_name': self.wrestler_name,
            'milestone_type': self.milestone_type,
            'description': self.description,
            'achieved_at_show_id': self.achieved_at_show_id,
            'achieved_at_show_name': self.achieved_at_show_name,
            'year': self.year,
            'week': self.week
        }


# Milestone type constants
class MilestoneType:
    """Types of milestones that can be achieved"""
    DEBUT = "debut"
    FIRST_WIN = "first_win"
    FIRST_TITLE = "first_title"
    MATCH_100 = "match_100"
    MATCH_250 = "match_250"
    MATCH_500 = "match_500"
    WIN_100 = "win_100"
    WIN_250 = "win_250"
    FIVE_STAR_MATCH = "five_star_match"
    GRAND_SLAM = "grand_slam"  # Won all major titles
    STREAK_10 = "streak_10"
    STREAK_25 = "streak_25"
    MAIN_EVENT_50 = "main_event_50"
    PPV_50 = "ppv_50"
    YEAR_UNDEFEATED = "year_undefeated"
    RETIREMENT = "retirement"