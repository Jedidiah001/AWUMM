"""
Championship Database Extensions
Handles persistence for championship hierarchy data.

Stores:
- Vacancy history
- Defense records
- Guaranteed title shots
- Title situation logs
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime


def create_championship_tables(database):
    """Create championship hierarchy tables"""
    cursor = database.conn.cursor()
    
    # Vacancy History Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS title_vacancies (
            vacancy_id TEXT PRIMARY KEY,
            title_id TEXT NOT NULL,
            title_name TEXT NOT NULL,
            reason TEXT NOT NULL,
            previous_champion_id TEXT,
            previous_champion_name TEXT,
            vacated_year INTEGER NOT NULL,
            vacated_week INTEGER NOT NULL,
            vacated_show_id TEXT,
            vacated_show_name TEXT,
            filled_year INTEGER,
            filled_week INTEGER,
            filled_show_id TEXT,
            filled_show_name TEXT,
            new_champion_id TEXT,
            new_champion_name TEXT,
            weeks_vacant INTEGER DEFAULT 0,
            resolution_method TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (title_id) REFERENCES championships(id)
        )
    ''')
    
    # Title Defense History Table
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
            is_ppv INTEGER NOT NULL,
            result TEXT NOT NULL,
            finish_type TEXT NOT NULL,
            star_rating REAL NOT NULL,
            duration_minutes INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (title_id) REFERENCES championships(id)
        )
    ''')
    
    # Guaranteed Title Shots Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS guaranteed_title_shots (
            shot_id TEXT PRIMARY KEY,
            wrestler_id TEXT NOT NULL,
            wrestler_name TEXT NOT NULL,
            title_id TEXT NOT NULL,
            title_name TEXT NOT NULL,
            reason TEXT NOT NULL,
            granted_year INTEGER NOT NULL,
            granted_week INTEGER NOT NULL,
            expires_year INTEGER,
            expires_week INTEGER,
            used INTEGER NOT NULL DEFAULT 0,
            used_year INTEGER,
            used_week INTEGER,
            used_show_id TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (title_id) REFERENCES championships(id),
            FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
        )
    ''')
    
    # Title Situation Log Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS title_situation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title_id TEXT NOT NULL,
            situation_type TEXT NOT NULL,
            description TEXT NOT NULL,
            decision_made TEXT,
            decision_result TEXT,
            year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (title_id) REFERENCES championships(id)
        )
    ''')
    
    # Indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_vacancies_title ON title_vacancies(title_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_defenses_title ON title_defenses(title_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_defenses_champion ON title_defenses(champion_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_shots_wrestler ON guaranteed_title_shots(wrestler_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_shots_title ON guaranteed_title_shots(title_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_shots_active ON guaranteed_title_shots(used)')
    
    database.conn.commit()
    print("✅ Championship hierarchy tables created")


def save_vacancy(database, vacancy_data: Dict[str, Any]):
    """Save a vacancy record"""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT OR REPLACE INTO title_vacancies (
            vacancy_id, title_id, title_name, reason,
            previous_champion_id, previous_champion_name,
            vacated_year, vacated_week, vacated_show_id, vacated_show_name,
            filled_year, filled_week, filled_show_id, filled_show_name,
            new_champion_id, new_champion_name,
            weeks_vacant, resolution_method, notes, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        vacancy_data['vacancy_id'],
        vacancy_data['title_id'],
        vacancy_data['title_name'],
        vacancy_data['reason'],
        vacancy_data.get('previous_champion_id'),
        vacancy_data.get('previous_champion_name'),
        vacancy_data['vacated_year'],
        vacancy_data['vacated_week'],
        vacancy_data.get('vacated_show_id'),
        vacancy_data.get('vacated_show_name'),
        vacancy_data.get('filled_year'),
        vacancy_data.get('filled_week'),
        vacancy_data.get('filled_show_id'),
        vacancy_data.get('filled_show_name'),
        vacancy_data.get('new_champion_id'),
        vacancy_data.get('new_champion_name'),
        vacancy_data.get('weeks_vacant', 0),
        vacancy_data.get('resolution_method'),
        vacancy_data.get('notes', ''),
        now
    ))
    
    database.conn.commit()


def get_vacancy(database, vacancy_id: str) -> Optional[Dict[str, Any]]:
    """Get a single vacancy record"""
    cursor = database.conn.cursor()
    cursor.execute('SELECT * FROM title_vacancies WHERE vacancy_id = ?', (vacancy_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_title_vacancies(database, title_id: str, active_only: bool = False) -> List[Dict[str, Any]]:
    """Get all vacancies for a title"""
    cursor = database.conn.cursor()
    
    if active_only:
        cursor.execute(
            'SELECT * FROM title_vacancies WHERE title_id = ? AND filled_year IS NULL ORDER BY vacated_year DESC, vacated_week DESC',
            (title_id,)
        )
    else:
        cursor.execute(
            'SELECT * FROM title_vacancies WHERE title_id = ? ORDER BY vacated_year DESC, vacated_week DESC',
            (title_id,)
        )
    
    return [dict(row) for row in cursor.fetchall()]


def get_all_active_vacancies(database) -> List[Dict[str, Any]]:
    """Get all currently active vacancies"""
    cursor = database.conn.cursor()
    cursor.execute('SELECT * FROM title_vacancies WHERE filled_year IS NULL ORDER BY vacated_year, vacated_week')
    return [dict(row) for row in cursor.fetchall()]


def fill_vacancy(database, vacancy_id: str, fill_data: Dict[str, Any]):
    """Update a vacancy record when filled"""
    cursor = database.conn.cursor()
    
    cursor.execute('''
        UPDATE title_vacancies SET
            filled_year = ?,
            filled_week = ?,
            filled_show_id = ?,
            filled_show_name = ?,
            new_champion_id = ?,
            new_champion_name = ?,
            weeks_vacant = ?,
            resolution_method = ?
        WHERE vacancy_id = ?
    ''', (
        fill_data['filled_year'],
        fill_data['filled_week'],
        fill_data.get('filled_show_id'),
        fill_data.get('filled_show_name'),
        fill_data['new_champion_id'],
        fill_data['new_champion_name'],
        fill_data.get('weeks_vacant', 0),
        fill_data.get('resolution_method', 'match'),
        vacancy_id
    ))
    
    database.conn.commit()


def save_defense(database, defense_data: Dict[str, Any]):
    """Save a title defense record"""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    # Use INSERT OR REPLACE to handle duplicates gracefully
    cursor.execute('''
        INSERT OR REPLACE INTO title_defenses (
            defense_id, title_id, champion_id, champion_name,
            challenger_id, challenger_name, show_id, show_name,
            year, week, is_ppv, result, finish_type,
            star_rating, duration_minutes, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        defense_data['defense_id'],
        defense_data['title_id'],
        defense_data['champion_id'],
        defense_data['champion_name'],
        defense_data['challenger_id'],
        defense_data['challenger_name'],
        defense_data['show_id'],
        defense_data['show_name'],
        defense_data['year'],
        defense_data['week'],
        1 if defense_data.get('is_ppv') else 0,
        defense_data['result'],
        defense_data['finish_type'],
        defense_data['star_rating'],
        defense_data['duration_minutes'],
        now
    ))
    
    database.conn.commit()


def get_title_defenses(database, title_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent defenses for a title"""
    cursor = database.conn.cursor()
    cursor.execute('''
        SELECT * FROM title_defenses 
        WHERE title_id = ? 
        ORDER BY year DESC, week DESC 
        LIMIT ?
    ''', (title_id, limit))
    return [dict(row) for row in cursor.fetchall()]


def get_champion_defenses(database, champion_id: str, title_id: str = None) -> List[Dict[str, Any]]:
    """Get all defenses by a champion"""
    cursor = database.conn.cursor()
    
    if title_id:
        cursor.execute('''
            SELECT * FROM title_defenses 
            WHERE champion_id = ? AND title_id = ?
            ORDER BY year DESC, week DESC
        ''', (champion_id, title_id))
    else:
        cursor.execute('''
            SELECT * FROM title_defenses 
            WHERE champion_id = ?
            ORDER BY year DESC, week DESC
        ''', (champion_id,))
    
    return [dict(row) for row in cursor.fetchall()]


def get_last_defense(database, title_id: str) -> Optional[Dict[str, Any]]:
    """Get the most recent defense for a title"""
    cursor = database.conn.cursor()
    cursor.execute('''
        SELECT * FROM title_defenses 
        WHERE title_id = ? 
        ORDER BY year DESC, week DESC 
        LIMIT 1
    ''', (title_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def save_guaranteed_shot(database, shot_data: Dict[str, Any]):
    """Save a guaranteed title shot"""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT OR REPLACE INTO guaranteed_title_shots (
            shot_id, wrestler_id, wrestler_name, title_id, title_name,
            reason, granted_year, granted_week, expires_year, expires_week,
            used, used_year, used_week, used_show_id, notes, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        shot_data['shot_id'],
        shot_data['wrestler_id'],
        shot_data['wrestler_name'],
        shot_data['title_id'],
        shot_data['title_name'],
        shot_data['reason'],
        shot_data['granted_year'],
        shot_data['granted_week'],
        shot_data.get('expires_year'),
        shot_data.get('expires_week'),
        1 if shot_data.get('used', False) else 0,
        shot_data.get('used_year'),
        shot_data.get('used_week'),
        shot_data.get('used_show_id'),
        shot_data.get('notes', ''),
        now
    ))
    
    database.conn.commit()


def get_guaranteed_shot(database, shot_id: str) -> Optional[Dict[str, Any]]:
    """Get a single guaranteed shot"""
    cursor = database.conn.cursor()
    cursor.execute('SELECT * FROM guaranteed_title_shots WHERE shot_id = ?', (shot_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_active_shots_for_title(database, title_id: str, current_year: int, current_week: int) -> List[Dict[str, Any]]:
    """Get all active (unused, unexpired) shots for a title"""
    cursor = database.conn.cursor()
    cursor.execute('''
        SELECT * FROM guaranteed_title_shots 
        WHERE title_id = ? 
          AND used = 0
          AND (expires_year IS NULL OR expires_year > ? OR (expires_year = ? AND expires_week >= ?))
        ORDER BY granted_year, granted_week
    ''', (title_id, current_year, current_year, current_week))
    return [dict(row) for row in cursor.fetchall()]


def get_wrestler_shots(database, wrestler_id: str, active_only: bool = True) -> List[Dict[str, Any]]:
    """Get all guaranteed shots for a wrestler"""
    cursor = database.conn.cursor()
    
    if active_only:
        cursor.execute('''
            SELECT * FROM guaranteed_title_shots 
            WHERE wrestler_id = ? AND used = 0
            ORDER BY granted_year DESC, granted_week DESC
        ''', (wrestler_id,))
    else:
        cursor.execute('''
            SELECT * FROM guaranteed_title_shots 
            WHERE wrestler_id = ?
            ORDER BY granted_year DESC, granted_week DESC
        ''', (wrestler_id,))
    
    return [dict(row) for row in cursor.fetchall()]


def use_guaranteed_shot(database, shot_id: str, year: int, week: int, show_id: str):
    """Mark a guaranteed shot as used"""
    cursor = database.conn.cursor()
    
    cursor.execute('''
        UPDATE guaranteed_title_shots SET
            used = 1,
            used_year = ?,
            used_week = ?,
            used_show_id = ?
        WHERE shot_id = ?
    ''', (year, week, show_id, shot_id))
    
    database.conn.commit()


def log_title_situation(
    database,
    title_id: str,
    situation_type: str,
    description: str,
    year: int,
    week: int,
    decision_made: str = None,
    decision_result: str = None
):
    """Log a title situation for history"""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT INTO title_situation_log (
            title_id, situation_type, description,
            decision_made, decision_result,
            year, week, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        title_id, situation_type, description,
        decision_made, decision_result,
        year, week, now
    ))
    
    database.conn.commit()


def get_title_situation_log(database, title_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Get situation log for a title"""
    cursor = database.conn.cursor()
    cursor.execute('''
        SELECT * FROM title_situation_log 
        WHERE title_id = ? 
        ORDER BY year DESC, week DESC, id DESC
        LIMIT ?
    ''', (title_id, limit))
    return [dict(row) for row in cursor.fetchall()]


def get_defense_stats(database, title_id: str) -> Dict[str, Any]:
    """Get defense statistics for a title"""
    cursor = database.conn.cursor()
    
    # Total defenses
    cursor.execute('SELECT COUNT(*) FROM title_defenses WHERE title_id = ?', (title_id,))
    row = cursor.fetchone()
    total = row[0] if row else 0
    
    # Successful defenses (retained)
    cursor.execute('SELECT COUNT(*) FROM title_defenses WHERE title_id = ? AND result = ?', (title_id, 'retained'))
    row = cursor.fetchone()
    retained = row[0] if row else 0
    
    # Average star rating
    cursor.execute('SELECT AVG(star_rating) FROM title_defenses WHERE title_id = ?', (title_id,))
    row = cursor.fetchone()
    avg_rating = row[0] if row and row[0] else 0
    
    # PPV defenses
    cursor.execute('SELECT COUNT(*) FROM title_defenses WHERE title_id = ? AND is_ppv = 1', (title_id,))
    row = cursor.fetchone()
    ppv_defenses = row[0] if row else 0
    
    # Highest rated defense
    cursor.execute('''
        SELECT * FROM title_defenses 
        WHERE title_id = ? 
        ORDER BY star_rating DESC 
        LIMIT 1
    ''', (title_id,))
    best_defense_row = cursor.fetchone()
    best_defense = dict(best_defense_row) if best_defense_row else None
    
    return {
        'total_defenses': total,
        'successful_defenses': retained,
        'title_changes': total - retained,
        'retention_rate': (retained / total * 100) if total > 0 else 0,
        'average_star_rating': round(avg_rating, 2) if avg_rating else 0,
        'ppv_defenses': ppv_defenses,
        'best_defense': best_defense
    }


def load_championship_hierarchy_state(database) -> Dict[str, Any]:
    """Load complete championship hierarchy state from database"""
    
    # Get all vacancies
    cursor = database.conn.cursor()
    cursor.execute('SELECT * FROM title_vacancies ORDER BY vacated_year, vacated_week')
    vacancies = [dict(row) for row in cursor.fetchall()]
    
    # Get all defenses
    cursor.execute('SELECT * FROM title_defenses ORDER BY year, week')
    defenses = [dict(row) for row in cursor.fetchall()]
    
    # Get all guaranteed shots
    cursor.execute('SELECT * FROM guaranteed_title_shots ORDER BY granted_year, granted_week')
    shots = [dict(row) for row in cursor.fetchall()]
    
    # Calculate next IDs safely
    next_vacancy_id = 1
    if vacancies:
        try:
            ids = []
            for v in vacancies:
                vid = v['vacancy_id']
                if vid and vid.startswith('vacancy_'):
                    ids.append(int(vid.replace('vacancy_', '')))
            if ids:
                next_vacancy_id = max(ids) + 1
        except (ValueError, TypeError):
            next_vacancy_id = len(vacancies) + 1
    
    next_defense_id = 1
    if defenses:
        try:
            ids = []
            for d in defenses:
                did = d['defense_id']
                if did and did.startswith('defense_'):
                    ids.append(int(did.replace('defense_', '')))
            if ids:
                next_defense_id = max(ids) + 1
        except (ValueError, TypeError):
            next_defense_id = len(defenses) + 1
    
    next_shot_id = 1
    if shots:
        try:
            ids = []
            for s in shots:
                sid = s['shot_id']
                if sid and sid.startswith('shot_'):
                    ids.append(int(sid.replace('shot_', '')))
            if ids:
                next_shot_id = max(ids) + 1
        except (ValueError, TypeError):
            next_shot_id = len(shots) + 1
    
    return {
        'vacancy_history': vacancies,
        'defense_history': defenses,
        'guaranteed_shots': shots,
        '_next_vacancy_id': next_vacancy_id,
        '_next_defense_id': next_defense_id,
        '_next_shot_id': next_shot_id
    }


def save_championship_hierarchy_state(database, hierarchy):
    """Save complete championship hierarchy state to database"""
    
    # Save all vacancies
    for vacancy in hierarchy.vacancy_history:
        save_vacancy(database, vacancy.to_dict())
    
    # Save all defenses
    for defense in hierarchy.defense_history:
        save_defense(database, defense.to_dict())
    
    # Save all guaranteed shots
    for shot in hierarchy.guaranteed_shots:
        save_guaranteed_shot(database, shot.to_dict())
    
    database.conn.commit()