"""
Awards Database Persistence
Stores and retrieves year-end awards.
"""

from typing import List, Dict, Any, Optional
import json
from datetime import datetime


def save_awards_ceremony(database, ceremony) -> None:
    """Save an awards ceremony to the database"""
    
    cursor = database.conn.cursor()
    
    # Create awards table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS awards_ceremonies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER NOT NULL UNIQUE,
            ceremony_week INTEGER NOT NULL,
            total_awards INTEGER NOT NULL,
            awards_data TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')
    
    # Save ceremony
    cursor.execute('''
        INSERT OR REPLACE INTO awards_ceremonies
        (year, ceremony_week, total_awards, awards_data, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        ceremony.year,
        ceremony.ceremony_date_week,
        len(ceremony.awards),
        json.dumps(ceremony.to_dict()),
        datetime.now().isoformat()
    ))
    
    database.conn.commit()


def get_awards_ceremony(database, year: int) -> Optional[Dict[str, Any]]:
    """Get awards ceremony for a specific year"""
    
    cursor = database.conn.cursor()
    
    try:
        cursor.execute('''
            SELECT awards_data FROM awards_ceremonies
            WHERE year = ?
        ''', (year,))
        
        row = cursor.fetchone()
        
        if row:
            return json.loads(row[0])
        
        return None
        
    except:
        return None


def get_all_awards_ceremonies(database) -> List[Dict[str, Any]]:
    """Get all awards ceremonies"""
    
    cursor = database.conn.cursor()
    
    try:
        cursor.execute('''
            SELECT awards_data FROM awards_ceremonies
            ORDER BY year DESC
        ''')
        
        ceremonies = []
        for row in cursor.fetchall():
            ceremonies.append(json.loads(row[0]))
        
        return ceremonies
        
    except:
        return []


def get_wrestler_awards(database, wrestler_id: str) -> List[Dict[str, Any]]:
    """Get all awards won by a wrestler"""
    
    cursor = database.conn.cursor()
    
    try:
        cursor.execute('''
            SELECT year, awards_data FROM awards_ceremonies
            ORDER BY year
        ''')
        
        wrestler_awards = []
        
        for row in cursor.fetchall():
            year, awards_json = row
            ceremony = json.loads(awards_json)
            
            for award in ceremony['awards']:
                if award['winner_id'] == wrestler_id:
                    wrestler_awards.append({
                        'year': year,
                        'category': award['category'],
                        'category_display': award['category_display']
                    })
        
        return wrestler_awards
        
    except:
        return []