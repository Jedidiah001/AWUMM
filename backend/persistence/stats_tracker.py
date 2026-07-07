"""
Stats Tracker
Wrapper class for stats functionality in the database.
"""

from typing import Optional
from persistence.database import Database


class StatsTracker:
    """
    Stats tracking functionality wrapper.
    Used by the Database class to provide stats methods.
    """
    
    def __init__(self, database: Database):
        self.db = database
    
    def get_wrestler_stats(self, wrestler_id: str) -> Optional[dict]:
        """Get cached stats for a wrestler"""
        return self.db.get_wrestler_stats(wrestler_id)
    
    def update_wrestler_stats(self, wrestler_id: str):
        """Update cached stats for a wrestler"""
        self.db.update_wrestler_stats_cache(wrestler_id)
    
    def get_all_wrestler_stats(self) -> list:
        """Get cached stats for all wrestlers"""
        return self.db.get_all_wrestler_stats()
    
    def calculate_wrestler_stats(self, wrestler_id: str) -> Optional[dict]:
        """Calculate complete statistics for a wrestler"""
        return self.db.calculate_wrestler_stats(wrestler_id)
    
    def get_wrestler_milestones(self, wrestler_id: str) -> list:
        """Get all milestones for a wrestler"""
        return self.db.get_wrestler_milestones(wrestler_id)
    
    def get_recent_milestones(self, limit: int = 10) -> list:
        """Get recent milestones across all wrestlers"""
        return self.db.get_recent_milestones(limit)
    
    def record_milestone(self, wrestler_id: str, wrestler_name: str, milestone_type: str, 
                        description: str, show_id: str, show_name: str, year: int, week: int):
        """Record a milestone achievement"""
        self.db.record_milestone(
            wrestler_id=wrestler_id,
            wrestler_name=wrestler_name,
            milestone_type=milestone_type,
            description=description,
            show_id=show_id,
            show_name=show_name,
            year=year,
            week=week
        )
    
    def get_promotion_records(self) -> dict:
        """Calculate promotion-wide records"""
        return self.db.get_promotion_records()