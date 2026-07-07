"""
Database operations for Championship Reign Goals

STEP 30: Reign goal tracking and satisfaction calculation
"""

import json
from typing import List, Dict, Any, Optional
from models.reign_goal import ReignGoal, ReignGoalType


def create_reign_goal_tables(db):
    """
    Create tables for reign goal tracking.
    Called during database initialization.
    """
    cursor = db.conn.cursor()
    
    # Reign Goals Table - tracks wrestler expectations
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reign_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wrestler_id TEXT NOT NULL,
            title_id TEXT NOT NULL,
            reign_start_year INTEGER NOT NULL,
            reign_start_week INTEGER NOT NULL,
            goal_type TEXT NOT NULL,
            target_value INTEGER NOT NULL,
            importance INTEGER NOT NULL,
            must_end_at_show TEXT,
            must_end_by_week INTEGER,
            minimum_match_rating REAL DEFAULT 3.0,
            is_met INTEGER DEFAULT 0,
            satisfaction_bonus INTEGER DEFAULT 0,
            satisfaction_penalty INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id),
            FOREIGN KEY (title_id) REFERENCES championships(id)
        )
    ''')
    
    # Reign Satisfaction History - records completed reigns
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reign_satisfaction_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wrestler_id TEXT NOT NULL,
            wrestler_name TEXT NOT NULL,
            title_id TEXT NOT NULL,
            title_name TEXT NOT NULL,
            reign_start_year INTEGER NOT NULL,
            reign_start_week INTEGER NOT NULL,
            reign_end_year INTEGER NOT NULL,
            reign_end_week INTEGER NOT NULL,
            days_held INTEGER NOT NULL,
            successful_defenses INTEGER NOT NULL,
            avg_star_rating REAL DEFAULT 0,
            loss_type TEXT,
            total_satisfaction INTEGER NOT NULL,
            morale_change INTEGER NOT NULL,
            goals_met INTEGER NOT NULL,
            goals_failed INTEGER NOT NULL,
            satisfaction_breakdown TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id),
            FOREIGN KEY (title_id) REFERENCES championships(id)
        )
    ''')
    
    # Contract Title Promises - track promised title runs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contract_title_promises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wrestler_id TEXT NOT NULL,
            title_id TEXT,
            title_tier TEXT,
            promised_min_days INTEGER NOT NULL,
            promised_min_defenses INTEGER NOT NULL,
            promise_year INTEGER NOT NULL,
            promise_week INTEGER NOT NULL,
            expires_year INTEGER,
            expires_week INTEGER,
            fulfilled INTEGER DEFAULT 0,
            fulfillment_year INTEGER,
            fulfillment_week INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
        )
    ''')
    
    # Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_reign_goals_wrestler ON reign_goals(wrestler_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_reign_goals_title ON reign_goals(title_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_reign_goals_active ON reign_goals(is_met)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_satisfaction_history_wrestler ON reign_satisfaction_history(wrestler_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_title_promises_wrestler ON contract_title_promises(wrestler_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_title_promises_unfulfilled ON contract_title_promises(fulfilled)')
    
    db.conn.commit()
    print("✅ Reign goal tables created")


def save_reign_goals(db, wrestler_id: str, title_id: str, reign_start_year: int, reign_start_week: int, goals: List[ReignGoal]):
    """Save reign goals for a new championship reign."""
    from datetime import datetime
    cursor = db.conn.cursor()
    now = datetime.now().isoformat()
    
    for goal in goals:
        cursor.execute('''
            INSERT INTO reign_goals (
                wrestler_id, title_id, reign_start_year, reign_start_week,
                goal_type, target_value, importance,
                must_end_at_show, must_end_by_week, minimum_match_rating,
                is_met, satisfaction_bonus, satisfaction_penalty,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            wrestler_id, title_id, reign_start_year, reign_start_week,
            goal.goal_type.value, goal.target_value, goal.importance,
            goal.must_end_at_show, goal.must_end_by_week, goal.minimum_match_rating,
            0, goal.satisfaction_bonus, goal.satisfaction_penalty,
            now
        ))
    
    # Don't commit here - batch with other operations


def get_reign_goals(db, wrestler_id: str, title_id: str, reign_start_year: int, reign_start_week: int) -> List[ReignGoal]:
    """Get reign goals for a specific championship reign."""
    cursor = db.conn.cursor()
    
    cursor.execute('''
        SELECT * FROM reign_goals
        WHERE wrestler_id = ? AND title_id = ? 
        AND reign_start_year = ? AND reign_start_week = ?
    ''', (wrestler_id, title_id, reign_start_year, reign_start_week))
    
    rows = cursor.fetchall()
    goals = []
    
    for row in rows:
        goal = ReignGoal(
            goal_type=ReignGoalType(row['goal_type']),
            target_value=row['target_value'],
            importance=row['importance'],
            must_end_at_show=row['must_end_at_show'],
            must_end_by_week=row['must_end_by_week'],
            minimum_match_rating=row['minimum_match_rating'],
            is_met=bool(row['is_met']),
            satisfaction_bonus=row['satisfaction_bonus'],
            satisfaction_penalty=row['satisfaction_penalty']
        )
        goals.append(goal)
    
    return goals


def get_active_reign_goals(db, wrestler_id: str) -> List[Dict[str, Any]]:
    """Get all active (unmet) reign goals for a wrestler."""
    cursor = db.conn.cursor()
    
    cursor.execute('''
        SELECT rg.*, c.name as title_name
        FROM reign_goals rg
        JOIN championships c ON rg.title_id = c.id
        WHERE rg.wrestler_id = ? AND rg.is_met = 0
        ORDER BY rg.importance DESC
    ''', (wrestler_id,))
    
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def save_reign_satisfaction(db, satisfaction_data: Dict[str, Any]):
    """Save completed reign satisfaction history."""
    from datetime import datetime
    cursor = db.conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT INTO reign_satisfaction_history (
            wrestler_id, wrestler_name, title_id, title_name,
            reign_start_year, reign_start_week,
            reign_end_year, reign_end_week,
            days_held, successful_defenses, avg_star_rating, loss_type,
            total_satisfaction, morale_change,
            goals_met, goals_failed,
            satisfaction_breakdown, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        satisfaction_data['wrestler_id'],
        satisfaction_data['wrestler_name'],
        satisfaction_data['title_id'],
        satisfaction_data['title_name'],
        satisfaction_data['reign_start_year'],
        satisfaction_data['reign_start_week'],
        satisfaction_data['reign_end_year'],
        satisfaction_data['reign_end_week'],
        satisfaction_data['days_held'],
        satisfaction_data['successful_defenses'],
        satisfaction_data.get('avg_star_rating', 0),
        satisfaction_data.get('loss_type'),
        satisfaction_data['total_satisfaction'],
        satisfaction_data['morale_change'],
        satisfaction_data['goals_met'],
        satisfaction_data['goals_failed'],
        json.dumps(satisfaction_data['satisfaction_breakdown']),
        now
    ))
    
    # Mark goals as met/failed
    cursor.execute('''
        UPDATE reign_goals
        SET is_met = ?
        WHERE wrestler_id = ? AND title_id = ?
        AND reign_start_year = ? AND reign_start_week = ?
    ''', (
        1,  # Mark as completed (not necessarily satisfied)
        satisfaction_data['wrestler_id'],
        satisfaction_data['title_id'],
        satisfaction_data['reign_start_year'],
        satisfaction_data['reign_start_week']
    ))


def get_wrestler_reign_history(db, wrestler_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get reign satisfaction history for a wrestler."""
    cursor = db.conn.cursor()
    
    cursor.execute('''
        SELECT * FROM reign_satisfaction_history
        WHERE wrestler_id = ?
        ORDER BY reign_end_year DESC, reign_end_week DESC
        LIMIT ?
    ''', (wrestler_id, limit))
    
    rows = cursor.fetchall()
    history = []
    
    for row in rows:
        record = dict(row)
        record['satisfaction_breakdown'] = json.loads(record['satisfaction_breakdown'])
        history.append(record)
    
    return history


def save_contract_title_promise(db, promise_data: Dict[str, Any]):
    """Save a contract title promise."""
    from datetime import datetime
    cursor = db.conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT INTO contract_title_promises (
            wrestler_id, title_id, title_tier,
            promised_min_days, promised_min_defenses,
            promise_year, promise_week,
            expires_year, expires_week,
            fulfilled, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        promise_data['wrestler_id'],
        promise_data.get('title_id'),
        promise_data.get('title_tier'),
        promise_data['promised_min_days'],
        promise_data['promised_min_defenses'],
        promise_data['promise_year'],
        promise_data['promise_week'],
        promise_data.get('expires_year'),
        promise_data.get('expires_week'),
        0,
        now
    ))


def get_unfulfilled_title_promises(db, wrestler_id: str = None) -> List[Dict[str, Any]]:
    """Get unfulfilled contract title promises."""
    cursor = db.conn.cursor()
    
    if wrestler_id:
        cursor.execute('''
            SELECT ctp.*, w.name as wrestler_name
            FROM contract_title_promises ctp
            JOIN wrestlers w ON ctp.wrestler_id = w.id
            WHERE ctp.wrestler_id = ? AND ctp.fulfilled = 0
            ORDER BY ctp.promise_year, ctp.promise_week
        ''', (wrestler_id,))
    else:
        cursor.execute('''
            SELECT ctp.*, w.name as wrestler_name
            FROM contract_title_promises ctp
            JOIN wrestlers w ON ctp.wrestler_id = w.id
            WHERE ctp.fulfilled = 0
            ORDER BY ctp.promise_year, ctp.promise_week
        ''')
    
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def fulfill_title_promise(db, promise_id: int, year: int, week: int):
    """Mark a title promise as fulfilled."""
    cursor = db.conn.cursor()
    
    cursor.execute('''
        UPDATE contract_title_promises
        SET fulfilled = 1, fulfillment_year = ?, fulfillment_week = ?
        WHERE id = ?
    ''', (year, week, promise_id))


def check_promise_expiration(db, current_year: int, current_week: int) -> List[Dict[str, Any]]:
    """Check for expired unfulfilled promises."""
    cursor = db.conn.cursor()
    
    cursor.execute('''
        SELECT ctp.*, w.name as wrestler_name
        FROM contract_title_promises ctp
        JOIN wrestlers w ON ctp.wrestler_id = w.id
        WHERE ctp.fulfilled = 0
        AND ctp.expires_year IS NOT NULL
        AND (ctp.expires_year < ? OR (ctp.expires_year = ? AND ctp.expires_week <= ?))
    ''', (current_year, current_year, current_week))
    
    rows = cursor.fetchall()
    return [dict(row) for row in rows]