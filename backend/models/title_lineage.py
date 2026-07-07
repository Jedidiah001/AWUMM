"""
Title Lineage Recording System
Tracks complete championship history with detailed statistics
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class TitleDefense:
    """Record of a single title defense"""
    defense_id: str
    title_id: str
    champion_id: str
    champion_name: str
    challenger_id: str
    challenger_name: str
    show_id: str
    show_name: str
    year: int
    week: int
    result: str  # 'retained', 'lost'
    finish_type: str
    star_rating: float
    match_duration: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'defense_id': self.defense_id,
            'title_id': self.title_id,
            'champion_id': self.champion_id,
            'champion_name': self.champion_name,
            'challenger_id': self.challenger_id,
            'challenger_name': self.challenger_name,
            'show_id': self.show_id,
            'show_name': self.show_name,
            'year': self.year,
            'week': self.week,
            'result': self.result,
            'finish_type': self.finish_type,
            'star_rating': self.star_rating,
            'match_duration': self.match_duration
        }


@dataclass
class ReignStatistics:
    """Detailed statistics for a title reign"""
    total_defenses: int = 0
    successful_defenses: int = 0
    average_match_rating: float = 0.0
    highest_rated_defense: Optional[float] = None
    lowest_rated_defense: Optional[float] = None
    clean_wins: int = 0
    dirty_wins: int = 0
    total_match_time: int = 0
    notable_victories: List[str] = None
    
    def __post_init__(self):
        if self.notable_victories is None:
            self.notable_victories = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_defenses': self.total_defenses,
            'successful_defenses': self.successful_defenses,
            'average_match_rating': round(self.average_match_rating, 2),
            'highest_rated_defense': self.highest_rated_defense,
            'lowest_rated_defense': self.lowest_rated_defense,
            'clean_wins': self.clean_wins,
            'dirty_wins': self.dirty_wins,
            'total_match_time': self.total_match_time,
            'notable_victories': self.notable_victories
        }


class TitleLineageTracker:
    """Manages complete title lineage and statistics"""
    
    def __init__(self, database):
        self.db = database
    
    def record_title_change(
        self,
        title_id: str,
        new_champion_id: str,
        new_champion_name: str,
        show_id: str,
        show_name: str,
        year: int,
        week: int,
        previous_champion_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Record a title change in the lineage"""
        cursor = self.db.conn.cursor()
        
        # End previous reign if exists
        if previous_champion_id:
            cursor.execute('''
                UPDATE title_reigns 
                SET lost_at_show_id = ?, lost_at_show_name = ?, 
                    lost_date_year = ?, lost_date_week = ?,
                    days_held = ((? - won_date_year) * 52 + (? - won_date_week)) * 7
                WHERE title_id = ? AND wrestler_id = ? AND lost_at_show_id IS NULL
            ''', (show_id, show_name, year, week, year, week, title_id, previous_champion_id))
        
        # Create new reign
        cursor.execute('''
            INSERT INTO title_reigns (
                title_id, wrestler_id, wrestler_name,
                won_at_show_id, won_at_show_name,
                won_date_year, won_date_week,
                days_held, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
        ''', (
            title_id, new_champion_id, new_champion_name,
            show_id, show_name, year, week,
            datetime.now().isoformat()
        ))
        
        reign_id = cursor.lastrowid
        
        # Update championship current holder
        cursor.execute('''
            UPDATE championships 
            SET current_holder_id = ?, current_holder_name = ?, updated_at = ?
            WHERE id = ?
        ''', (new_champion_id, new_champion_name, datetime.now().isoformat(), title_id))
        
        self.db.conn.commit()
        
        return {
            'reign_id': reign_id,
            'title_id': title_id,
            'new_champion_id': new_champion_id,
            'new_champion_name': new_champion_name
        }
    
    def record_title_defense(
        self,
        defense_data: TitleDefense
    ) -> None:
        """Record a title defense"""
        cursor = self.db.conn.cursor()
        
        # Check if defenses table exists, create if not
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS title_defenses (
                defense_id TEXT PRIMARY KEY,
                title_id TEXT NOT NULL,
                champion_id TEXT NOT NULL,
                champion_name TEXT NOT NULL,
                challenger_id TEXT NOT NULL,
                challenger_name TEXT NOT NULL,
                show_id TEXT NOT NULL,
                show_name TEXT NOT NULL,
                year INTEGER NOT NULL,
                week INTEGER NOT NULL,
                result TEXT NOT NULL,
                finish_type TEXT NOT NULL,
                star_rating REAL NOT NULL,
                match_duration INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (title_id) REFERENCES championships(id),
                FOREIGN KEY (champion_id) REFERENCES wrestlers(id),
                FOREIGN KEY (challenger_id) REFERENCES wrestlers(id)
            )
        ''')
        
        cursor.execute('''
            INSERT INTO title_defenses (
                defense_id, title_id, champion_id, champion_name,
                challenger_id, challenger_name, show_id, show_name,
                year, week, result, finish_type, star_rating, match_duration,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            defense_data.defense_id,
            defense_data.title_id,
            defense_data.champion_id,
            defense_data.champion_name,
            defense_data.challenger_id,
            defense_data.challenger_name,
            defense_data.show_id,
            defense_data.show_name,
            defense_data.year,
            defense_data.week,
            defense_data.result,
            defense_data.finish_type,
            defense_data.star_rating,
            defense_data.match_duration,
            datetime.now().isoformat()
        ))
        
        self.db.conn.commit()
    
    def get_title_lineage(
        self,
        title_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get complete title lineage"""
        cursor = self.db.conn.cursor()
        
        query = '''
            SELECT tr.*, 
                   (SELECT COUNT(*) FROM title_defenses td 
                    WHERE td.title_id = tr.title_id 
                    AND td.champion_id = tr.wrestler_id 
                    AND td.year >= tr.won_date_year 
                    AND td.week >= tr.won_date_week
                    AND (tr.lost_date_year IS NULL OR 
                         (td.year < tr.lost_date_year OR 
                          (td.year = tr.lost_date_year AND td.week <= tr.lost_date_week)))
                    AND td.result = 'retained'
                   ) as successful_defenses
            FROM title_reigns tr
            WHERE tr.title_id = ?
            ORDER BY tr.won_date_year DESC, tr.won_date_week DESC
        '''
        
        if limit:
            query += f' LIMIT {limit}'
        
        cursor.execute(query, (title_id,))
        
        reigns = []
        for row in cursor.fetchall():
            reign = dict(row)
            
            # Calculate actual days held if ongoing
            if reign['lost_at_show_id'] is None:
                # Get current date from game state
                state = self.db.get_game_state()
                current_year = state['current_year']
                current_week = state['current_week']
                
                weeks_held = (current_year - reign['won_date_year']) * 52 + (current_week - reign['won_date_week'])
                reign['days_held'] = weeks_held * 7
                reign['is_current'] = True
            else:
                reign['is_current'] = False
            
            reigns.append(reign)
        
        return reigns
    
    def get_reign_statistics(
        self,
        title_id: str,
        wrestler_id: str,
        year: int,
        week: int
    ) -> ReignStatistics:
        """Get detailed statistics for a specific reign"""
        cursor = self.db.conn.cursor()
        
        # Get the specific reign
        cursor.execute('''
            SELECT * FROM title_reigns
            WHERE title_id = ? AND wrestler_id = ?
            AND won_date_year = ? AND won_date_week = ?
        ''', (title_id, wrestler_id, year, week))
        
        reign = cursor.fetchone()
        if not reign:
            return ReignStatistics()
        
        # Get all defenses for this reign
        cursor.execute('''
            SELECT * FROM title_defenses
            WHERE title_id = ? AND champion_id = ?
            AND year >= ? AND week >= ?
            ORDER BY year, week
        ''', (title_id, wrestler_id, year, week))
        
        defenses = cursor.fetchall()
        
        stats = ReignStatistics()
        stats.total_defenses = len(defenses)
        
        if defenses:
            ratings = []
            for defense in defenses:
                if defense['result'] == 'retained':
                    stats.successful_defenses += 1
                    
                    if defense['finish_type'] in ['clean_pin', 'submission']:
                        stats.clean_wins += 1
                    else:
                        stats.dirty_wins += 1
                
                ratings.append(defense['star_rating'])
                stats.total_match_time += defense['match_duration']
                
                # Track notable victories (4+ stars or against major stars)
                if defense['star_rating'] >= 4.0:
                    stats.notable_victories.append(
                        f"vs {defense['challenger_name']} ({defense['star_rating']}★)"
                    )
            
            stats.average_match_rating = sum(ratings) / len(ratings)
            stats.highest_rated_defense = max(ratings)
            stats.lowest_rated_defense = min(ratings)
        
        return stats
    
    def get_championship_statistics(self, title_id: str) -> Dict[str, Any]:
        """Get comprehensive statistics for a championship"""
        cursor = self.db.conn.cursor()
        
        # Total reigns
        cursor.execute('''
            SELECT COUNT(*) as total_reigns,
                   COUNT(DISTINCT wrestler_id) as unique_champions
            FROM title_reigns
            WHERE title_id = ?
        ''', (title_id,))
        
        basic_stats = dict(cursor.fetchone())
        
        # Longest reign
        cursor.execute('''
            SELECT wrestler_name, days_held
            FROM title_reigns
            WHERE title_id = ? AND days_held > 0
            ORDER BY days_held DESC
            LIMIT 1
        ''', (title_id,))
        
        longest_reign_row = cursor.fetchone()
        longest_reign = dict(longest_reign_row) if longest_reign_row else None
        
        # Most reigns
        cursor.execute('''
            SELECT wrestler_name, COUNT(*) as reign_count
            FROM title_reigns
            WHERE title_id = ?
            GROUP BY wrestler_id
            ORDER BY reign_count DESC
            LIMIT 1
        ''', (title_id,))
        
        most_reigns_row = cursor.fetchone()
        most_reigns = dict(most_reigns_row) if most_reigns_row else None
        
        # Total defenses
        cursor.execute('''
            SELECT COUNT(*) as total_defenses,
                   AVG(star_rating) as avg_match_rating
            FROM title_defenses
            WHERE title_id = ?
        ''', (title_id,))
        
        defense_stats = dict(cursor.fetchone())
        
        # Best defenses
        cursor.execute('''
            SELECT champion_name, challenger_name, star_rating, show_name
            FROM title_defenses
            WHERE title_id = ?
            ORDER BY star_rating DESC
            LIMIT 5
        ''', (title_id,))
        
        best_defenses = [dict(row) for row in cursor.fetchall()]
        
        return {
            'total_reigns': basic_stats['total_reigns'],
            'unique_champions': basic_stats['unique_champions'],
            'longest_reign': longest_reign,
            'most_reigns': most_reigns,
            'total_defenses': defense_stats['total_defenses'] or 0,
            'average_match_rating': round(defense_stats['avg_match_rating'] or 0, 2),
            'best_defenses': best_defenses
        }