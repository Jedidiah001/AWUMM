"""
Database operations for title lineage tracking
"""

from typing import List, Dict, Any, Optional
from datetime import datetime


def create_lineage_tables(database):
    """Create tables for title lineage tracking"""
    cursor = database.conn.cursor()
    
    # Title defenses table
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
    
    # Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_defenses_title ON title_defenses(title_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_defenses_champion ON title_defenses(champion_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_defenses_date ON title_defenses(year, week)')
    
    database.conn.commit()
    print("✅ Title lineage tables created")


def get_title_defenses(
    database,
    title_id: Optional[str] = None,
    champion_id: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Get title defense history with filters"""
    cursor = database.conn.cursor()
    
    query = 'SELECT * FROM title_defenses WHERE 1=1'
    params = []
    
    if title_id:
        query += ' AND title_id = ?'
        params.append(title_id)
    
    if champion_id:
        query += ' AND champion_id = ?'
        params.append(champion_id)
    
    query += ' ORDER BY year DESC, week DESC LIMIT ?'
    params.append(limit)
    
    cursor.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]


def get_wrestler_title_history(
    database,
    wrestler_id: str
) -> Dict[str, Any]:
    """Get complete title history for a wrestler"""
    cursor = database.conn.cursor()
    
    # Get all title reigns
    cursor.execute('''
        SELECT tr.*, c.name as title_name, c.title_type
        FROM title_reigns tr
        JOIN championships c ON tr.title_id = c.id
        WHERE tr.wrestler_id = ?
        ORDER BY tr.won_date_year DESC, tr.won_date_week DESC
    ''', (wrestler_id,))
    
    reigns = [dict(row) for row in cursor.fetchall()]
    
    # Get total stats
    cursor.execute('''
        SELECT 
            COUNT(*) as total_reigns,
            SUM(days_held) as total_days_as_champion,
            MAX(days_held) as longest_reign
        FROM title_reigns
        WHERE wrestler_id = ? AND days_held > 0
    ''', (wrestler_id,))
    
    stats = dict(cursor.fetchone())
    
    # Get defenses
    cursor.execute('''
        SELECT 
            COUNT(*) as total_defenses,
            SUM(CASE WHEN result = 'retained' THEN 1 ELSE 0 END) as successful_defenses,
            AVG(star_rating) as avg_defense_rating
        FROM title_defenses
        WHERE champion_id = ?
    ''', (wrestler_id,))
    
    defense_stats = dict(cursor.fetchone())
    
    return {
        'reigns': reigns,
        'total_reigns': stats['total_reigns'] or 0,
        'total_days_as_champion': stats['total_days_as_champion'] or 0,
        'longest_reign': stats['longest_reign'] or 0,
        'total_defenses': defense_stats['total_defenses'] or 0,
        'successful_defenses': defense_stats['successful_defenses'] or 0,
        'average_defense_rating': round(defense_stats['avg_defense_rating'] or 0, 2)
    }