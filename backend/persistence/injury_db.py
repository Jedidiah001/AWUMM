"""
Injury Database Operations
Handles all injury and rehabilitation data persistence.
"""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional


def create_injury_tables(database):
    """Create injury-related tables in the database"""
    cursor = database.conn.cursor()
    
    # Detailed Injury Tracking Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS injury_details (
            wrestler_id TEXT PRIMARY KEY,
            severity TEXT NOT NULL,
            body_part TEXT NOT NULL,
            description TEXT NOT NULL,
            weeks_out INTEGER NOT NULL,
            weeks_remaining INTEGER NOT NULL,
            requires_surgery INTEGER NOT NULL DEFAULT 0,
            surgery_completed INTEGER NOT NULL DEFAULT 0,
            can_appear_limited INTEGER NOT NULL DEFAULT 0,
            medical_costs INTEGER NOT NULL DEFAULT 0,
            rehab_progress REAL NOT NULL DEFAULT 0.0,
            rehab_milestones TEXT,
            occurred_year INTEGER NOT NULL,
            occurred_week INTEGER NOT NULL,
            occurred_show_id TEXT,
            estimated_return_year INTEGER,
            estimated_return_week INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
        )
    ''')
    
    # Injury History Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS injury_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wrestler_id TEXT NOT NULL,
            wrestler_name TEXT NOT NULL,
            severity TEXT NOT NULL,
            body_part TEXT NOT NULL,
            description TEXT NOT NULL,
            occurred_year INTEGER NOT NULL,
            occurred_week INTEGER NOT NULL,
            occurred_show_id TEXT,
            occurred_show_name TEXT,
            weeks_missed INTEGER NOT NULL,
            required_surgery INTEGER NOT NULL DEFAULT 0,
            medical_costs INTEGER NOT NULL DEFAULT 0,
            return_year INTEGER,
            return_week INTEGER,
            return_show_id TEXT,
            return_show_name TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
        )
    ''')
    
    # Injury Angles Table (for storyline write-offs)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS injury_angles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            injured_wrestler_id TEXT NOT NULL,
            injured_wrestler_name TEXT NOT NULL,
            attacker_id TEXT,
            attacker_name TEXT,
            angle_type TEXT NOT NULL,
            description TEXT NOT NULL,
            show_id TEXT NOT NULL,
            show_name TEXT NOT NULL,
            year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            heat_generated INTEGER NOT NULL DEFAULT 0,
            created_feud INTEGER NOT NULL DEFAULT 0,
            feud_id TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (injured_wrestler_id) REFERENCES wrestlers(id),
            FOREIGN KEY (attacker_id) REFERENCES wrestlers(id),
            FOREIGN KEY (feud_id) REFERENCES feuds(id)
        )
    ''')
    
    # Return Angles Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS return_angles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wrestler_id TEXT NOT NULL,
            wrestler_name TEXT NOT NULL,
            target_id TEXT,
            target_name TEXT,
            angle_type TEXT NOT NULL,
            description TEXT NOT NULL,
            is_surprise INTEGER NOT NULL DEFAULT 1,
            show_id TEXT NOT NULL,
            show_name TEXT NOT NULL,
            year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            momentum_boost INTEGER NOT NULL DEFAULT 0,
            popularity_boost INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id),
            FOREIGN KEY (target_id) REFERENCES wrestlers(id)
        )
    ''')
    
    # Medical Staff Configuration Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS medical_staff_config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            tier TEXT NOT NULL DEFAULT 'Standard',
            recovery_modifier REAL NOT NULL DEFAULT 1.0,
            cost_per_week INTEGER NOT NULL DEFAULT 10000,
            injury_prevention REAL NOT NULL DEFAULT 0.02,
            misdiagnosis_chance REAL NOT NULL DEFAULT 0.05,
            upgraded_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')
    
    # Rehab Sessions Table (for tracking recovery milestones)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rehab_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wrestler_id TEXT NOT NULL,
            session_week INTEGER NOT NULL,
            session_type TEXT NOT NULL,
            progress_made REAL NOT NULL,
            milestone_achieved TEXT,
            therapist_notes TEXT,
            year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
        )
    ''')
    
    # Injury Statistics Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS injury_stats (
            wrestler_id TEXT PRIMARY KEY,
            total_injuries INTEGER NOT NULL DEFAULT 0,
            minor_injuries INTEGER NOT NULL DEFAULT 0,
            moderate_injuries INTEGER NOT NULL DEFAULT 0,
            severe_injuries INTEGER NOT NULL DEFAULT 0,
            career_threatening_injuries INTEGER NOT NULL DEFAULT 0,
            total_weeks_missed INTEGER NOT NULL DEFAULT 0,
            total_medical_costs INTEGER NOT NULL DEFAULT 0,
            surgeries_undergone INTEGER NOT NULL DEFAULT 0,
            most_injured_body_part TEXT,
            injury_prone_rating REAL NOT NULL DEFAULT 0.0,
            last_updated TEXT NOT NULL,
            FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
        )
    ''')
    
    # Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_injury_details_wrestler ON injury_details(wrestler_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_injury_history_wrestler ON injury_history(wrestler_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_injury_angles_injured ON injury_angles(injured_wrestler_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_injury_angles_attacker ON injury_angles(attacker_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_return_angles_wrestler ON return_angles(wrestler_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_rehab_sessions_wrestler ON rehab_sessions(wrestler_id)')
    
    # Initialize medical staff config if not exists
    cursor.execute('SELECT COUNT(*) FROM medical_staff_config')
    if cursor.fetchone()[0] == 0:
        now = datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO medical_staff_config (
                id, tier, recovery_modifier, cost_per_week,
                injury_prevention, misdiagnosis_chance,
                created_at, updated_at
            ) VALUES (1, 'Standard', 0.95, 10000, 0.02, 0.05, ?, ?)
        ''', (now, now))
    
    database.conn.commit()
    print("✅ Injury tables created")


def save_injury_details(database, wrestler_id: str, injury_data: Dict[str, Any]):
    """Save detailed injury information"""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT OR REPLACE INTO injury_details (
            wrestler_id, severity, body_part, description,
            weeks_out, weeks_remaining, requires_surgery, surgery_completed,
            can_appear_limited, medical_costs, rehab_progress,
            rehab_milestones, occurred_year, occurred_week, occurred_show_id,
            estimated_return_year, estimated_return_week,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        wrestler_id,
        injury_data['severity'],
        injury_data['body_part'],
        injury_data['description'],
        injury_data['weeks_out'],
        injury_data['weeks_remaining'],
        1 if injury_data.get('requires_surgery', False) else 0,
        1 if injury_data.get('surgery_completed', False) else 0,
        1 if injury_data.get('can_appear_limited', False) else 0,
        injury_data.get('medical_costs', 0),
        injury_data.get('rehab_progress', 0.0),
        json.dumps(injury_data.get('rehab_milestones', [])),
        injury_data['occurred_year'],
        injury_data['occurred_week'],
        injury_data.get('occurred_show_id'),
        injury_data.get('estimated_return_year'),
        injury_data.get('estimated_return_week'),
        now, now
    ))


def get_injury_details(database, wrestler_id: str) -> Optional[Dict[str, Any]]:
    """Get detailed injury information for a wrestler"""
    cursor = database.conn.cursor()
    cursor.execute('SELECT * FROM injury_details WHERE wrestler_id = ?', (wrestler_id,))
    row = cursor.fetchone()
    
    if not row:
        return None
    
    injury_dict = dict(row)
    injury_dict['rehab_milestones'] = json.loads(injury_dict['rehab_milestones'] or '[]')
    
    return injury_dict


def update_injury_progress(database, wrestler_id: str, weeks_healed: int, new_progress: float):
    """Update injury recovery progress"""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute('''
        UPDATE injury_details
        SET weeks_remaining = weeks_remaining - ?,
            rehab_progress = ?,
            updated_at = ?
        WHERE wrestler_id = ?
    ''', (weeks_healed, new_progress, now, wrestler_id))


def delete_injury_details(database, wrestler_id: str):
    """Remove injury details when wrestler recovers"""
    cursor = database.conn.cursor()
    cursor.execute('DELETE FROM injury_details WHERE wrestler_id = ?', (wrestler_id,))


def save_to_injury_history(database, wrestler_id: str, injury_data: Dict[str, Any]):
    """Save completed injury to history"""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT INTO injury_history (
            wrestler_id, wrestler_name, severity, body_part, description,
            occurred_year, occurred_week, occurred_show_id, occurred_show_name,
            weeks_missed, required_surgery, medical_costs,
            return_year, return_week, return_show_id, return_show_name,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        wrestler_id,
        injury_data['wrestler_name'],
        injury_data['severity'],
        injury_data['body_part'],
        injury_data['description'],
        injury_data['occurred_year'],
        injury_data['occurred_week'],
        injury_data.get('occurred_show_id'),
        injury_data.get('occurred_show_name'),
        injury_data['weeks_missed'],
        1 if injury_data.get('required_surgery', False) else 0,
        injury_data.get('medical_costs', 0),
        injury_data.get('return_year'),
        injury_data.get('return_week'),
        injury_data.get('return_show_id'),
        injury_data.get('return_show_name'),
        now
    ))


def get_injury_history(database, wrestler_id: str = None) -> List[Dict[str, Any]]:
    """Get injury history, optionally filtered by wrestler"""
    cursor = database.conn.cursor()
    
    if wrestler_id:
        cursor.execute('''
            SELECT * FROM injury_history
            WHERE wrestler_id = ?
            ORDER BY occurred_year DESC, occurred_week DESC
        ''', (wrestler_id,))
    else:
        cursor.execute('''
            SELECT * FROM injury_history
            ORDER BY occurred_year DESC, occurred_week DESC
            LIMIT 50
        ''')
    
    return [dict(row) for row in cursor.fetchall()]


def save_injury_angle(database, angle_data: Dict[str, Any]) -> int:
    """Save an injury angle and return ID"""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT INTO injury_angles (
            injured_wrestler_id, injured_wrestler_name,
            attacker_id, attacker_name,
            angle_type, description,
            show_id, show_name, year, week,
            heat_generated, created_feud, feud_id,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        angle_data['injured_wrestler_id'],
        angle_data['injured_wrestler_name'],
        angle_data.get('attacker_id'),
        angle_data.get('attacker_name'),
        angle_data['type'],
        angle_data['description'],
        angle_data['show_id'],
        angle_data['show_name'],
        angle_data['year'],
        angle_data['week'],
        angle_data.get('heat_generated', 0),
        1 if angle_data.get('creates_feud', False) else 0,
        angle_data.get('feud_id'),
        now
    ))
    
    return cursor.lastrowid


def save_return_angle(database, angle_data: Dict[str, Any]) -> int:
    """Save a return angle and return ID"""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT INTO return_angles (
            wrestler_id, wrestler_name,
            target_id, target_name,
            angle_type, description, is_surprise,
            show_id, show_name, year, week,
            momentum_boost, popularity_boost,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        angle_data['wrestler_id'],
        angle_data['wrestler_name'],
        angle_data.get('target_id'),
        angle_data.get('target_name'),
        angle_data['type'],
        angle_data['description'],
        1 if angle_data.get('is_surprise', True) else 0,
        angle_data['show_id'],
        angle_data['show_name'],
        angle_data['year'],
        angle_data['week'],
        angle_data.get('momentum_boost', 0),
        angle_data.get('popularity_boost', 0),
        now
    ))
    
    return cursor.lastrowid


def get_medical_staff_config(database) -> Dict[str, Any]:
    """Get current medical staff configuration"""
    cursor = database.conn.cursor()
    cursor.execute('SELECT * FROM medical_staff_config WHERE id = 1')
    row = cursor.fetchone()
    return dict(row) if row else None


def update_medical_staff_tier(database, tier: str, config: Dict[str, Any]):
    """Update medical staff tier"""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute('''
        UPDATE medical_staff_config
        SET tier = ?,
            recovery_modifier = ?,
            cost_per_week = ?,
            injury_prevention = ?,
            misdiagnosis_chance = ?,
            upgraded_at = ?,
            updated_at = ?
        WHERE id = 1
    ''', (
        tier,
        config['recovery_modifier'],
        config['cost_per_week'],
        config['injury_prevention'],
        config['misdiagnosis_chance'],
        now, now
    ))


def save_rehab_session(database, session_data: Dict[str, Any]):
    """Save a rehab session record"""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT INTO rehab_sessions (
            wrestler_id, session_week, session_type,
            progress_made, milestone_achieved, therapist_notes,
            year, week, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        session_data['wrestler_id'],
        session_data['session_week'],
        session_data['session_type'],
        session_data['progress_made'],
        session_data.get('milestone_achieved'),
        session_data.get('therapist_notes'),
        session_data['year'],
        session_data['week'],
        now
    ))


def get_rehab_sessions(database, wrestler_id: str) -> List[Dict[str, Any]]:
    """Get all rehab sessions for a wrestler"""
    cursor = database.conn.cursor()
    cursor.execute('''
        SELECT * FROM rehab_sessions
        WHERE wrestler_id = ?
        ORDER BY year DESC, week DESC
    ''', (wrestler_id,))
    
    return [dict(row) for row in cursor.fetchall()]


def update_injury_stats(database, wrestler_id: str, injury_severity: str, weeks_missed: int, medical_costs: int, had_surgery: bool):
    """Update injury statistics for a wrestler"""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    # Get existing stats
    cursor.execute('SELECT * FROM injury_stats WHERE wrestler_id = ?', (wrestler_id,))
    existing = cursor.fetchone()
    
    if existing:
        # Update existing
        total_injuries = existing['total_injuries'] + 1
        minor = existing['minor_injuries'] + (1 if injury_severity == 'Minor' else 0)
        moderate = existing['moderate_injuries'] + (1 if injury_severity == 'Moderate' else 0)
        severe = existing['severe_injuries'] + (1 if injury_severity == 'Severe' else 0)
        career_threatening = existing['career_threatening_injuries'] + (1 if injury_severity == 'Career Threatening' else 0)
        total_weeks = existing['total_weeks_missed'] + weeks_missed
        total_costs = existing['total_medical_costs'] + medical_costs
        surgeries = existing['surgeries_undergone'] + (1 if had_surgery else 0)
        
        cursor.execute('''
            UPDATE injury_stats
            SET total_injuries = ?,
                minor_injuries = ?,
                moderate_injuries = ?,
                severe_injuries = ?,
                career_threatening_injuries = ?,
                total_weeks_missed = ?,
                total_medical_costs = ?,
                surgeries_undergone = ?,
                injury_prone_rating = ?,
                last_updated = ?
            WHERE wrestler_id = ?
        ''', (
            total_injuries, minor, moderate, severe, career_threatening,
            total_weeks, total_costs, surgeries,
            total_injuries / max(1, total_weeks / 52),  # Injuries per year
            now, wrestler_id
        ))
    else:
        # Create new
        cursor.execute('''
            INSERT INTO injury_stats (
                wrestler_id, total_injuries,
                minor_injuries, moderate_injuries, severe_injuries, career_threatening_injuries,
                total_weeks_missed, total_medical_costs, surgeries_undergone,
                injury_prone_rating, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            wrestler_id, 1,
            1 if injury_severity == 'Minor' else 0,
            1 if injury_severity == 'Moderate' else 0,
            1 if injury_severity == 'Severe' else 0,
            1 if injury_severity == 'Career Threatening' else 0,
            weeks_missed, medical_costs,
            1 if had_surgery else 0,
            1.0,  # First injury
            now
        ))


def get_injury_stats(database, wrestler_id: str = None) -> Optional[Dict[str, Any]]:
    """Get injury statistics for a wrestler or all wrestlers"""
    cursor = database.conn.cursor()
    
    if wrestler_id:
        cursor.execute('SELECT * FROM injury_stats WHERE wrestler_id = ?', (wrestler_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    else:
        cursor.execute('SELECT * FROM injury_stats ORDER BY total_injuries DESC LIMIT 20')
        return [dict(row) for row in cursor.fetchall()]


def get_all_injured_wrestlers(database) -> List[Dict[str, Any]]:
    """Get all currently injured wrestlers with full details"""
    cursor = database.conn.cursor()
    cursor.execute('''
        SELECT w.*, id.*
        FROM wrestlers w
        JOIN injury_details id ON w.id = id.wrestler_id
        WHERE w.injury_severity != 'None'
        ORDER BY id.severity DESC, id.weeks_remaining DESC
    ''')
    
    injured = []
    for row in cursor.fetchall():
        wrestler_dict = dict(row)
        if 'rehab_milestones' in wrestler_dict and wrestler_dict['rehab_milestones']:
            wrestler_dict['rehab_milestones'] = json.loads(wrestler_dict['rehab_milestones'])
        injured.append(wrestler_dict)
    
    return injured