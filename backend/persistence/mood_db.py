"""
Mood History Database Operations (STEP 117)
Tracks free agent mood changes over time for visualization and analysis.
"""

import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime


def create_mood_history_tables(database):
    """Create mood history tracking tables"""
    cursor = database.conn.cursor()
    
    # Mood History Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS free_agent_mood_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            free_agent_id TEXT NOT NULL,
            wrestler_name TEXT NOT NULL,
            
            -- Mood change details
            old_mood TEXT NOT NULL,
            new_mood TEXT NOT NULL,
            change_reason TEXT NOT NULL,
            trigger_event TEXT,
            
            -- Context at time of change
            weeks_unemployed INTEGER NOT NULL,
            rejection_count INTEGER NOT NULL,
            rival_offers INTEGER NOT NULL,
            market_value INTEGER NOT NULL,
            popularity INTEGER NOT NULL,
            
            -- When it happened
            year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            
            FOREIGN KEY (free_agent_id) REFERENCES free_agents(id)
        )
    ''')
    
    # Mood Transition Events Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mood_transition_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            free_agent_id TEXT NOT NULL,
            
            event_type TEXT NOT NULL,
            event_description TEXT NOT NULL,
            
            -- Impact
            mood_impact TEXT,
            mood_before TEXT,
            mood_after TEXT,
            
            -- When
            year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            
            FOREIGN KEY (free_agent_id) REFERENCES free_agents(id)
        )
    ''')
    
    # Negotiation Attempts Table (tracks rejections)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS negotiation_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            free_agent_id TEXT NOT NULL,
            wrestler_name TEXT NOT NULL,
            
            -- Offer details
            promotion_name TEXT NOT NULL,
            offered_salary INTEGER NOT NULL,
            offered_length_weeks INTEGER NOT NULL,
            offered_signing_bonus INTEGER NOT NULL,
            
            -- Wrestler state
            asking_salary INTEGER NOT NULL,
            minimum_salary INTEGER NOT NULL,
            mood TEXT NOT NULL,
            
            -- Result
            accepted INTEGER NOT NULL DEFAULT 0,
            rejection_reason TEXT,
            
            -- When
            year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            
            FOREIGN KEY (free_agent_id) REFERENCES free_agents(id)
        )
    ''')
    
    # Indexes for performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_mood_history_fa ON free_agent_mood_history(free_agent_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_mood_history_date ON free_agent_mood_history(year, week)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_mood_events_fa ON mood_transition_events(free_agent_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_negotiations_fa ON negotiation_attempts(free_agent_id)')
    
    database.conn.commit()
    print("✅ Mood history tables created")


def save_mood_change(
    database,
    free_agent_id: str,
    wrestler_name: str,
    old_mood: str,
    new_mood: str,
    change_reason: str,
    trigger_event: Optional[str],
    weeks_unemployed: int,
    rejection_count: int,
    rival_offers: int,
    market_value: int,
    popularity: int,
    year: int,
    week: int
) -> int:
    """Save a mood change to history"""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT INTO free_agent_mood_history (
            free_agent_id, wrestler_name, old_mood, new_mood, 
            change_reason, trigger_event, weeks_unemployed, 
            rejection_count, rival_offers, market_value, popularity,
            year, week, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        free_agent_id, wrestler_name, old_mood, new_mood,
        change_reason, trigger_event, weeks_unemployed,
        rejection_count, rival_offers, market_value, popularity,
        year, week, now
    ))
    
    return cursor.lastrowid


def get_mood_history(
    database,
    free_agent_id: str,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """Get mood change history for a free agent"""
    cursor = database.conn.cursor()
    
    cursor.execute('''
        SELECT * FROM free_agent_mood_history
        WHERE free_agent_id = ?
        ORDER BY year DESC, week DESC, id DESC
        LIMIT ?
    ''', (free_agent_id, limit))
    
    return [dict(row) for row in cursor.fetchall()]


def get_mood_timeline(
    database,
    free_agent_id: str
) -> List[Dict[str, Any]]:
    """Get complete mood timeline for visualization"""
    cursor = database.conn.cursor()
    
    cursor.execute('''
        SELECT 
            year, week, new_mood as mood, 
            change_reason, weeks_unemployed, 
            market_value, popularity
        FROM free_agent_mood_history
        WHERE free_agent_id = ?
        ORDER BY year ASC, week ASC
    ''', (free_agent_id,))
    
    return [dict(row) for row in cursor.fetchall()]


def save_mood_event(
    database,
    free_agent_id: str,
    event_type: str,
    event_description: str,
    mood_impact: Optional[str],
    mood_before: Optional[str],
    mood_after: Optional[str],
    year: int,
    week: int
) -> int:
    """Save a mood-impacting event"""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT INTO mood_transition_events (
            free_agent_id, event_type, event_description,
            mood_impact, mood_before, mood_after,
            year, week, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        free_agent_id, event_type, event_description,
        mood_impact, mood_before, mood_after,
        year, week, now
    ))
    
    return cursor.lastrowid


def get_mood_events(
    database,
    free_agent_id: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Get mood-impacting events"""
    cursor = database.conn.cursor()
    
    cursor.execute('''
        SELECT * FROM mood_transition_events
        WHERE free_agent_id = ?
        ORDER BY year DESC, week DESC, id DESC
        LIMIT ?
    ''', (free_agent_id, limit))
    
    return [dict(row) for row in cursor.fetchall()]


def save_negotiation_attempt(
    database,
    free_agent_id: str,
    wrestler_name: str,
    promotion_name: str,
    offered_salary: int,
    offered_length_weeks: int,
    offered_signing_bonus: int,
    asking_salary: int,
    minimum_salary: int,
    mood: str,
    accepted: bool,
    rejection_reason: Optional[str],
    year: int,
    week: int
) -> int:
    """Save a negotiation attempt"""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT INTO negotiation_attempts (
            free_agent_id, wrestler_name, promotion_name,
            offered_salary, offered_length_weeks, offered_signing_bonus,
            asking_salary, minimum_salary, mood,
            accepted, rejection_reason,
            year, week, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        free_agent_id, wrestler_name, promotion_name,
        offered_salary, offered_length_weeks, offered_signing_bonus,
        asking_salary, minimum_salary, mood,
        1 if accepted else 0, rejection_reason,
        year, week, now
    ))
    
    return cursor.lastrowid


def get_negotiation_history(
    database,
    free_agent_id: str,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """Get negotiation attempt history"""
    cursor = database.conn.cursor()
    
    cursor.execute('''
        SELECT * FROM negotiation_attempts
        WHERE free_agent_id = ?
        ORDER BY year DESC, week DESC, id DESC
        LIMIT ?
    ''', (free_agent_id, limit))
    
    return [dict(row) for row in cursor.fetchall()]


def get_rejection_count(
    database,
    free_agent_id: str
) -> int:
    """Get total rejection count for a free agent"""
    cursor = database.conn.cursor()
    
    cursor.execute('''
        SELECT COUNT(*) as count
        FROM negotiation_attempts
        WHERE free_agent_id = ? AND accepted = 0
    ''', (free_agent_id,))
    
    result = cursor.fetchone()
    return result['count'] if result else 0


def get_recent_rejections(
    database,
    free_agent_id: str,
    weeks: int = 8
) -> int:
    """Get rejection count in recent weeks"""
    cursor = database.conn.cursor()
    
    # This is simplified - in production would calculate actual week range
    cursor.execute('''
        SELECT COUNT(*) as count
        FROM negotiation_attempts
        WHERE free_agent_id = ? AND accepted = 0
        ORDER BY year DESC, week DESC
        LIMIT ?
    ''', (free_agent_id, weeks))
    
    result = cursor.fetchone()
    return result['count'] if result else 0


def get_mood_statistics(database, free_agent_id: str) -> Dict[str, Any]:
    """Get comprehensive mood statistics"""
    cursor = database.conn.cursor()
    
    # Time in each mood
    cursor.execute('''
        SELECT 
            new_mood, 
            COUNT(*) as transition_count,
            AVG(weeks_unemployed) as avg_weeks_when_entered
        FROM free_agent_mood_history
        WHERE free_agent_id = ?
        GROUP BY new_mood
    ''', (free_agent_id,))
    
    mood_distribution = [dict(row) for row in cursor.fetchall()]
    
    # Total negotiations
    cursor.execute('''
        SELECT 
            COUNT(*) as total_negotiations,
            SUM(CASE WHEN accepted = 1 THEN 1 ELSE 0 END) as accepted,
            SUM(CASE WHEN accepted = 0 THEN 1 ELSE 0 END) as rejected
        FROM negotiation_attempts
        WHERE free_agent_id = ?
    ''', (free_agent_id,))
    
    negotiation_stats = dict(cursor.fetchone()) if cursor.fetchone() else {}
    
    # Most recent mood
    cursor.execute('''
        SELECT new_mood, change_reason, year, week
        FROM free_agent_mood_history
        WHERE free_agent_id = ?
        ORDER BY year DESC, week DESC, id DESC
        LIMIT 1
    ''', (free_agent_id,))
    
    current_mood_row = cursor.fetchone()
    current_mood = dict(current_mood_row) if current_mood_row else None
    
    return {
        'mood_distribution': mood_distribution,
        'negotiation_stats': negotiation_stats,
        'current_mood': current_mood
    }


def clear_mood_history(database, free_agent_id: str):
    """Clear mood history for a free agent (when they sign)"""
    cursor = database.conn.cursor()
    
    cursor.execute('DELETE FROM free_agent_mood_history WHERE free_agent_id = ?', (free_agent_id,))
    cursor.execute('DELETE FROM mood_transition_events WHERE free_agent_id = ?', (free_agent_id,))
    cursor.execute('DELETE FROM negotiation_attempts WHERE free_agent_id = ?', (free_agent_id,))
    
    database.conn.commit()