"""
Custom Championship Database Extensions
Handles persistence for custom championship creation features.

STEP 22: Adds tables and operations for:
- Extended championship fields (division, weight class, appearance)
- Custom defense requirements
- Championship creation/retirement tracking
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime


def create_custom_championship_tables(database):
    """Create tables for custom championship features"""
    cursor = database.conn.cursor()
    
    # Extended Championship Data Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS championship_extended (
            title_id TEXT PRIMARY KEY,
            division TEXT NOT NULL DEFAULT 'open',
            weight_class TEXT NOT NULL DEFAULT 'open',
            is_tag_team INTEGER NOT NULL DEFAULT 0,
            tag_team_size INTEGER NOT NULL DEFAULT 2,
            description TEXT,
            is_custom INTEGER NOT NULL DEFAULT 0,
            created_year INTEGER,
            created_week INTEGER,
            retired INTEGER NOT NULL DEFAULT 0,
            retired_year INTEGER,
            retired_week INTEGER,
            appearance_json TEXT,
            defense_requirements_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (title_id) REFERENCES championships(id)
        )
    ''')
    
    # Championship Creation Log
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS championship_creation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title_id TEXT NOT NULL,
            title_name TEXT NOT NULL,
            action TEXT NOT NULL,
            year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            details TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (title_id) REFERENCES championships(id)
        )
    ''')
    
    # Indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_champ_extended_custom ON championship_extended(is_custom)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_champ_extended_retired ON championship_extended(retired)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_champ_creation_log_title ON championship_creation_log(title_id)')
    
    database.conn.commit()
    print("✅ Custom championship tables created")


def save_championship_extended(database, title_id: str, extended_data: Dict[str, Any]):
    """Save extended championship data"""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    # Serialize JSON fields
    appearance_json = json.dumps(extended_data.get('appearance')) if extended_data.get('appearance') else None
    defense_json = json.dumps(extended_data.get('defense_requirements')) if extended_data.get('defense_requirements') else None
    
    cursor.execute('''
        INSERT OR REPLACE INTO championship_extended (
            title_id, division, weight_class, is_tag_team, tag_team_size,
            description, is_custom, created_year, created_week,
            retired, retired_year, retired_week,
            appearance_json, defense_requirements_json,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        title_id,
        extended_data.get('division', 'open'),
        extended_data.get('weight_class', 'open'),
        1 if extended_data.get('is_tag_team', False) else 0,
        extended_data.get('tag_team_size', 2),
        extended_data.get('description', ''),
        1 if extended_data.get('is_custom', False) else 0,
        extended_data.get('created_year'),
        extended_data.get('created_week'),
        1 if extended_data.get('retired', False) else 0,
        extended_data.get('retired_year'),
        extended_data.get('retired_week'),
        appearance_json,
        defense_json,
        now, now
    ))
    
    database.conn.commit()


def get_championship_extended(database, title_id: str) -> Optional[Dict[str, Any]]:
    """Get extended data for a championship"""
    cursor = database.conn.cursor()
    cursor.execute('SELECT * FROM championship_extended WHERE title_id = ?', (title_id,))
    row = cursor.fetchone()
    
    if not row:
        return None
    
    data = dict(row)
    
    # Parse JSON fields
    if data.get('appearance_json'):
        data['appearance'] = json.loads(data['appearance_json'])
    else:
        data['appearance'] = None
    
    if data.get('defense_requirements_json'):
        data['defense_requirements'] = json.loads(data['defense_requirements_json'])
    else:
        data['defense_requirements'] = None
    
    # Convert integer flags to boolean
    data['is_tag_team'] = bool(data.get('is_tag_team', 0))
    data['is_custom'] = bool(data.get('is_custom', 0))
    data['retired'] = bool(data.get('retired', 0))
    
    # Remove raw JSON fields
    data.pop('appearance_json', None)
    data.pop('defense_requirements_json', None)
    
    return data


def get_all_custom_championships(database, include_retired: bool = False) -> List[Dict[str, Any]]:
    """Get all custom (user-created) championships"""
    cursor = database.conn.cursor()
    
    if include_retired:
        cursor.execute('''
            SELECT ce.*, c.name, c.assigned_brand, c.title_type, c.prestige,
                   c.current_holder_id, c.current_holder_name
            FROM championship_extended ce
            JOIN championships c ON ce.title_id = c.id
            WHERE ce.is_custom = 1
            ORDER BY c.prestige DESC
        ''')
    else:
        cursor.execute('''
            SELECT ce.*, c.name, c.assigned_brand, c.title_type, c.prestige,
                   c.current_holder_id, c.current_holder_name
            FROM championship_extended ce
            JOIN championships c ON ce.title_id = c.id
            WHERE ce.is_custom = 1 AND ce.retired = 0
            ORDER BY c.prestige DESC
        ''')
    
    results = []
    for row in cursor.fetchall():
        data = dict(row)
        
        # Parse JSON fields
        if data.get('appearance_json'):
            data['appearance'] = json.loads(data['appearance_json'])
        if data.get('defense_requirements_json'):
            data['defense_requirements'] = json.loads(data['defense_requirements_json'])
        
        data['is_tag_team'] = bool(data.get('is_tag_team', 0))
        data['is_custom'] = bool(data.get('is_custom', 0))
        data['retired'] = bool(data.get('retired', 0))
        
        data.pop('appearance_json', None)
        data.pop('defense_requirements_json', None)
        
        results.append(data)
    
    return results


def get_championships_by_division(database, division: str) -> List[Dict[str, Any]]:
    """Get all championships for a specific division"""
    cursor = database.conn.cursor()
    cursor.execute('''
        SELECT ce.*, c.name, c.assigned_brand, c.title_type, c.prestige,
               c.current_holder_id, c.current_holder_name
        FROM championship_extended ce
        JOIN championships c ON ce.title_id = c.id
        WHERE ce.division = ? AND ce.retired = 0
        ORDER BY c.prestige DESC
    ''', (division,))
    
    results = []
    for row in cursor.fetchall():
        data = dict(row)
        if data.get('appearance_json'):
            data['appearance'] = json.loads(data['appearance_json'])
        if data.get('defense_requirements_json'):
            data['defense_requirements'] = json.loads(data['defense_requirements_json'])
        data['is_tag_team'] = bool(data.get('is_tag_team', 0))
        data['is_custom'] = bool(data.get('is_custom', 0))
        data['retired'] = bool(data.get('retired', 0))
        data.pop('appearance_json', None)
        data.pop('defense_requirements_json', None)
        results.append(data)
    
    return results


def retire_championship(database, title_id: str, year: int, week: int, reason: str = None):
    """Mark a championship as retired"""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute('''
        UPDATE championship_extended
        SET retired = 1, retired_year = ?, retired_week = ?, updated_at = ?
        WHERE title_id = ?
    ''', (year, week, now, title_id))
    if cursor.rowcount == 0:
        cursor.execute('''
            INSERT INTO championship_extended (
                title_id, division, weight_class, is_tag_team, tag_team_size,
                description, is_custom, created_year, created_week,
                retired, retired_year, retired_week,
                appearance_json, defense_requirements_json,
                created_at, updated_at
            ) VALUES (?, 'open', 'open', 0, 2, '', 0, NULL, NULL, 1, ?, ?, NULL, NULL, ?, ?)
        ''', (title_id, year, week, now, now))
    
    # Log the retirement
    log_championship_action(database, title_id, 'retired', year, week, reason)
    
    database.conn.commit()


def reactivate_championship(database, title_id: str, year: int, week: int):
    """Reactivate a retired championship"""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute('''
        UPDATE championship_extended
        SET retired = 0, retired_year = NULL, retired_week = NULL, updated_at = ?
        WHERE title_id = ?
    ''', (now, title_id))
    
    # Log the reactivation
    log_championship_action(database, title_id, 'reactivated', year, week, None)
    
    database.conn.commit()


def log_championship_action(
    database,
    title_id: str,
    action: str,
    year: int,
    week: int,
    details: str = None
):
    """Log a championship action (creation, retirement, etc.)"""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    # Get title name
    cursor.execute('SELECT name FROM championships WHERE id = ?', (title_id,))
    row = cursor.fetchone()
    title_name = row['name'] if row else 'Unknown'
    
    cursor.execute('''
        INSERT INTO championship_creation_log (
            title_id, title_name, action, year, week, details, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (title_id, title_name, action, year, week, details, now))
    
    database.conn.commit()


def get_championship_action_log(database, title_id: str = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Get championship action log"""
    cursor = database.conn.cursor()
    
    if title_id:
        cursor.execute('''
            SELECT * FROM championship_creation_log
            WHERE title_id = ?
            ORDER BY year DESC, week DESC, id DESC
            LIMIT ?
        ''', (title_id, limit))
    else:
        cursor.execute('''
            SELECT * FROM championship_creation_log
            ORDER BY year DESC, week DESC, id DESC
            LIMIT ?
        ''', (limit,))
    
    return [dict(row) for row in cursor.fetchall()]


def delete_championship(database, title_id: str):
    """
    Permanently delete a championship.
    WARNING: This removes all associated data.
    """
    cursor = database.conn.cursor()
    
    # Delete from extended table
    cursor.execute('DELETE FROM championship_extended WHERE title_id = ?', (title_id,))
    
    # Delete from creation log
    cursor.execute('DELETE FROM championship_creation_log WHERE title_id = ?', (title_id,))
    
    # Delete title reigns
    cursor.execute('DELETE FROM title_reigns WHERE title_id = ?', (title_id,))
    
    # Delete from defenses
    cursor.execute('DELETE FROM title_defenses WHERE title_id = ?', (title_id,))
    
    # Delete from vacancies
    cursor.execute('DELETE FROM title_vacancies WHERE title_id = ?', (title_id,))
    
    # Delete from guaranteed shots
    cursor.execute('DELETE FROM guaranteed_title_shots WHERE title_id = ?', (title_id,))
    
    # Delete from situation log
    cursor.execute('DELETE FROM title_situation_log WHERE title_id = ?', (title_id,))
    
    # Finally, delete from main championships table
    cursor.execute('DELETE FROM championships WHERE id = ?', (title_id,))
    
    database.conn.commit()


def get_championship_statistics(database, title_id: str) -> Dict[str, Any]:
    """Get comprehensive statistics for a championship"""
    cursor = database.conn.cursor()
    
    # Basic info
    cursor.execute('SELECT * FROM championships WHERE id = ?', (title_id,))
    champ_row = cursor.fetchone()
    
    if not champ_row:
        return None
    
    stats = {
        'title_id': title_id,
        'title_name': champ_row['name'],
        'prestige': champ_row['prestige']
    }
    
    # Total reigns
    cursor.execute('SELECT COUNT(*) as count FROM title_reigns WHERE title_id = ?', (title_id,))
    stats['total_reigns'] = cursor.fetchone()['count']
    
    # Unique champions
    cursor.execute('SELECT COUNT(DISTINCT wrestler_id) as count FROM title_reigns WHERE title_id = ?', (title_id,))
    stats['unique_champions'] = cursor.fetchone()['count']
    
    # Total defenses
    cursor.execute('SELECT COUNT(*) as count FROM title_defenses WHERE title_id = ?', (title_id,))
    stats['total_defenses'] = cursor.fetchone()['count']
    
    # Average match rating
    cursor.execute('SELECT AVG(star_rating) as avg FROM title_defenses WHERE title_id = ?', (title_id,))
    avg_row = cursor.fetchone()
    stats['average_match_rating'] = round(avg_row['avg'], 2) if avg_row['avg'] else 0
    
    # Longest reign
    cursor.execute('''
        SELECT wrestler_name, days_held 
        FROM title_reigns 
        WHERE title_id = ? AND days_held > 0
        ORDER BY days_held DESC
        LIMIT 1
    ''', (title_id,))
    longest = cursor.fetchone()
    if longest:
        stats['longest_reign'] = {
            'champion': longest['wrestler_name'],
            'days': longest['days_held']
        }
    else:
        stats['longest_reign'] = None
    
    # Most reigns
    cursor.execute('''
        SELECT wrestler_name, COUNT(*) as reign_count
        FROM title_reigns
        WHERE title_id = ?
        GROUP BY wrestler_id
        ORDER BY reign_count DESC
        LIMIT 1
    ''', (title_id,))
    most = cursor.fetchone()
    if most:
        stats['most_reigns'] = {
            'champion': most['wrestler_name'],
            'count': most['reign_count']
        }
    else:
        stats['most_reigns'] = None
    
    # Vacancy count
    cursor.execute('SELECT COUNT(*) as count FROM title_vacancies WHERE title_id = ?', (title_id,))
    stats['times_vacated'] = cursor.fetchone()['count']
    
    return stats
