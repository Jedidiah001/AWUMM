"""
History Tracking System
Wrapper for stats tracking functionality.
"""

from typing import List, Dict, Any, Optional
from models.stats import WrestlerStats, PromotionRecords, Milestone, MilestoneType
from models.show import ShowResult
from models.match import MatchResult


class StatsTracker:
    """
    Central stats tracking system.
    Wraps database stats functionality for easy access.
    """
    
    def __init__(self, database):
        self.db = database
    
    def get_wrestler_stats(self, wrestler_id: str) -> Optional[WrestlerStats]:
        """Get complete stats for a wrestler"""
        stats_dict = self.db.calculate_wrestler_stats(wrestler_id)
        
        if not stats_dict:
            return None
        
        # Convert dict to WrestlerStats object
        stats = WrestlerStats(
            wrestler_id=wrestler_id,
            wrestler_name=stats_dict['wrestler_name']
        )
        
        # Populate from dict
        record = stats_dict['record']
        stats.total_matches = record['total_matches']
        stats.wins = record['wins']
        stats.losses = record['losses']
        stats.draws = record['draws']
        stats.win_percentage = record['win_percentage']
        
        quality = stats_dict['match_quality']
        stats.average_star_rating = quality['average_star_rating']
        stats.highest_star_rating = quality['highest_star_rating']
        stats.five_star_matches = quality['five_star_matches']
        stats.four_star_plus_matches = quality['four_star_plus_matches']
        
        titles = stats_dict['title_history']
        stats.total_title_reigns = titles['total_reigns']
        stats.total_days_as_champion = titles['total_days']
        stats.longest_reign_days = titles['longest_reign_days']
        stats.current_title_reign_days = titles.get('current_reign_days', 0)
        
        achievements = stats_dict['achievements']
        stats.main_events = achievements['main_events']
        stats.ppv_matches = achievements['ppv_matches']
        stats.upsets_caused = achievements['upsets_caused']
        stats.upset_losses = achievements['upset_losses']
        
        finishes = stats_dict['finish_breakdown']
        stats.clean_wins = finishes['clean_wins']
        stats.cheating_wins = finishes['cheating_wins']
        stats.dq_countout_wins = finishes['dq_countout_wins']
        stats.submission_wins = finishes['submission_wins']
        
        streaks = stats_dict['streaks']
        stats.current_win_streak = streaks['current_win_streak']
        stats.current_loss_streak = streaks['current_loss_streak']
        stats.longest_win_streak = streaks['longest_win_streak']
        stats.longest_loss_streak = streaks['longest_loss_streak']
        
        return stats
    
    def update_wrestler_stats(self, wrestler_id: str):
        """Update cached stats for a wrestler"""
        self.db.update_wrestler_stats_cache(wrestler_id)
    
    def get_wrestler_milestones(self, wrestler_id: str) -> List[Milestone]:
        """Get all milestones for a wrestler"""
        milestone_dicts = self.db.get_wrestler_milestones(wrestler_id)
        
        milestones = []
        for m_dict in milestone_dicts:
            milestone = Milestone(
                milestone_id=m_dict['id'],
                wrestler_id=m_dict['wrestler_id'],
                wrestler_name=m_dict.get('wrestler_name', ''),
                milestone_type=m_dict['milestone_type'],
                description=m_dict['description'],
                achieved_at_show_id=m_dict['achieved_at_show_id'],
                achieved_at_show_name=m_dict['achieved_at_show_name'],
                year=m_dict['year'],
                week=m_dict['week']
            )
            milestones.append(milestone)
        
        return milestones
    
    def get_recent_milestones(self, limit: int = 10) -> List[Milestone]:
        """Get recent milestones across all wrestlers"""
        milestone_dicts = self.db.get_recent_milestones(limit)
        
        milestones = []
        for m_dict in milestone_dicts:
            milestone = Milestone(
                milestone_id=m_dict['id'],
                wrestler_id=m_dict['wrestler_id'],
                wrestler_name=m_dict.get('wrestler_name', ''),
                milestone_type=m_dict['milestone_type'],
                description=m_dict['description'],
                achieved_at_show_id=m_dict['achieved_at_show_id'],
                achieved_at_show_name=m_dict['achieved_at_show_name'],
                year=m_dict['year'],
                week=m_dict['week']
            )
            milestones.append(milestone)
        
        return milestones
    
    def get_promotion_records(self) -> PromotionRecords:
        """Get all promotion-wide records"""
        records_dict = self.db.get_promotion_records()
        
        records = PromotionRecords()
        
        # Populate from dict
        if 'match_records' in records_dict:
            match_records = records_dict['match_records']
            records.highest_rated_match = match_records.get('highest_rated')
            records.lowest_rated_match = match_records.get('lowest_rated')
            records.longest_match = match_records.get('longest')
            records.shortest_match = match_records.get('shortest')
        
        if 'wrestler_records' in records_dict:
            wrestler_records = records_dict['wrestler_records']
            records.most_wins = wrestler_records.get('most_wins')
            records.best_win_percentage = wrestler_records.get('best_win_percentage')
            records.most_title_reigns = wrestler_records.get('most_title_reigns')
            records.longest_title_reign = wrestler_records.get('longest_title_reign')
        
        if 'streak_records' in records_dict:
            streak_records = records_dict['streak_records']
            records.longest_winning_streak = streak_records.get('longest_winning')
            records.longest_losing_streak = streak_records.get('longest_losing')
        
        if 'show_records' in records_dict:
            show_records = records_dict['show_records']
            records.highest_rated_show = show_records.get('highest_rated')
            records.highest_attendance = show_records.get('highest_attendance')
            records.highest_revenue = show_records.get('highest_revenue')
        
        if 'milestone_records' in records_dict:
            milestone_records = records_dict['milestone_records']
            records.most_five_star_matches = milestone_records.get('most_five_star_matches')
            records.most_main_events = milestone_records.get('most_main_events')
            records.most_ppv_wins = milestone_records.get('most_ppv_wins')
        
        return records
    
    def record_milestone(
        self,
        wrestler_id: str,
        wrestler_name: str,
        milestone_type: str,
        description: str,
        show_id: str,
        show_name: str,
        year: int,
        week: int
    ):
        """Record a new milestone achievement"""
        self.db.record_milestone(            wrestler_id=wrestler_id,
            wrestler_name=wrestler_name,
            milestone_type=milestone_type,
            description=description,
            show_id=show_id,
            show_name=show_name,
            year=year,
            week=week
        )
    
    def check_for_milestones(self, wrestler_id: str, stats: WrestlerStats, show_result: ShowResult):
        """Check if a wrestler has achieved any milestones"""
        milestones_achieved = []
        
        # Check match count milestones
        if stats.total_matches == 1:
            milestones_achieved.append((
                MilestoneType.DEBUT,
                f"{stats.wrestler_name} made their in-ring debut!"
            ))
        elif stats.total_matches == 100:
            milestones_achieved.append((
                MilestoneType.MATCH_100,
                f"{stats.wrestler_name} competed in their 100th match!"
            ))
        elif stats.total_matches == 250:
            milestones_achieved.append((
                MilestoneType.MATCH_250,
                f"{stats.wrestler_name} competed in their 250th match!"
            ))
        elif stats.total_matches == 500:
            milestones_achieved.append((
                MilestoneType.MATCH_500,
                f"{stats.wrestler_name} competed in their 500th match!"
            ))
        
        # Check win milestones
        if stats.wins == 1:
            milestones_achieved.append((
                MilestoneType.FIRST_WIN,
                f"{stats.wrestler_name} earned their first victory!"
            ))
        elif stats.wins == 100:
            milestones_achieved.append((
                MilestoneType.WIN_100,
                f"{stats.wrestler_name} earned their 100th victory!"
            ))
        elif stats.wins == 250:
            milestones_achieved.append((
                MilestoneType.WIN_250,
                f"{stats.wrestler_name} earned their 250th victory!"
            ))
        
        # Check streak milestones
        if stats.current_win_streak == 10:
            milestones_achieved.append((
                MilestoneType.STREAK_10,
                f"{stats.wrestler_name} is on a 10-match winning streak!"
            ))
        elif stats.current_win_streak == 25:
            milestones_achieved.append((
                MilestoneType.STREAK_25,
                f"{stats.wrestler_name} is on an incredible 25-match winning streak!"
            ))
        
        # Check title milestones
        if stats.total_title_reigns == 1 and stats.current_title_reign_days > 0:
            milestones_achieved.append((
                MilestoneType.FIRST_TITLE,
                f"{stats.wrestler_name} won their first championship!"
            ))
        
        # Check main event milestones
        if stats.main_events == 50:
            milestones_achieved.append((
                MilestoneType.MAIN_EVENT_50,
                f"{stats.wrestler_name} has main evented 50 shows!"
            ))
        
        # Check PPV milestones
        if stats.ppv_matches == 50:
            milestones_achieved.append((
                MilestoneType.PPV_50,
                f"{stats.wrestler_name} has competed in 50 PPV matches!"
            ))
        
        # Record all achieved milestones
        for milestone_type, description in milestones_achieved:
            self.record_milestone(
                wrestler_id=wrestler_id,
                wrestler_name=stats.wrestler_name,
                milestone_type=milestone_type,
                description=description,
                show_id=show_result.show_id,
                show_name=show_result.show_name,
                year=show_result.year,
                week=show_result.week
            )
        
        return milestones_achieved