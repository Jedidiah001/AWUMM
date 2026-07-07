"""
Championship Manager Database Extensions
Stores championship manager state (unifications, splits, transfers, lineages)
"""

import json
from datetime import datetime


def create_championship_manager_tables(database):
    """Create tables for championship manager state"""
    cursor = database.conn.cursor()
    
    # Manager state table (stores serialized state)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS championship_manager_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            state_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')
    
    # Unification history table (for querying)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS championship_unifications (
            unification_id TEXT PRIMARY KEY,
            primary_title_id TEXT NOT NULL,
            primary_title_name TEXT NOT NULL,
            secondary_title_id TEXT NOT NULL,
            secondary_title_name TEXT NOT NULL,
            resulting_title_id TEXT NOT NULL,
            resulting_title_name TEXT NOT NULL,
            unification_type TEXT NOT NULL,
            unified_by_wrestler_id TEXT NOT NULL,
            unified_by_wrestler_name TEXT NOT NULL,
            year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            show_id TEXT NOT NULL,
            show_name TEXT NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    
    # Split history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS championship_splits (
            split_id TEXT PRIMARY KEY,
            original_title_id TEXT NOT NULL,
            original_title_name TEXT NOT NULL,
            new_title_ids TEXT NOT NULL,
            new_title_names TEXT NOT NULL,
            reason TEXT NOT NULL,
            year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            show_id TEXT NOT NULL,
            show_name TEXT NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    
    # Transfer history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS championship_transfers (
            transfer_id TEXT PRIMARY KEY,
            title_id TEXT NOT NULL,
            title_name TEXT NOT NULL,
            transfer_type TEXT NOT NULL,
            from_value TEXT NOT NULL,
            to_value TEXT NOT NULL,
            year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            reason TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    
    # Lineage table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS championship_lineages (
            lineage_id TEXT PRIMARY KEY,
            title_id TEXT NOT NULL,
            title_name TEXT NOT NULL,
            lineage_number INTEGER NOT NULL,
            start_year INTEGER NOT NULL,
            start_week INTEGER NOT NULL,
            end_year INTEGER,
            end_week INTEGER,
            end_reason TEXT,
            total_reigns INTEGER NOT NULL DEFAULT 0,
            total_defenses INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    ''')
    
    # Add status column to championship_extended if not exists
    try:
        cursor.execute('ALTER TABLE championship_extended ADD COLUMN status TEXT DEFAULT "active"')
    except:
        pass  # Column already exists
    
    try:
        cursor.execute('ALTER TABLE championship_extended ADD COLUMN brand_exclusive INTEGER DEFAULT 1')
    except:
        pass
    
    try:
        cursor.execute('ALTER TABLE championship_extended ADD COLUMN deactivated_year INTEGER')
    except:
        pass
    
    try:
        cursor.execute('ALTER TABLE championship_extended ADD COLUMN deactivated_week INTEGER')
    except:
        pass
    
    try:
        cursor.execute('ALTER TABLE championship_extended ADD COLUMN deactivation_reason TEXT')
    except:
        pass
    
    try:
        cursor.execute('ALTER TABLE championship_extended ADD COLUMN split_from TEXT')
    except:
        pass
    
    try:
        cursor.execute('ALTER TABLE championship_extended ADD COLUMN unified_into TEXT')
    except:
        pass
    
    # Indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_unifications_primary ON championship_unifications(primary_title_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_unifications_secondary ON championship_unifications(secondary_title_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_splits_original ON championship_splits(original_title_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transfers_title ON championship_transfers(title_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_lineages_title ON championship_lineages(title_id)')
    
    database.conn.commit()
    print("✅ Championship manager tables created")


def save_unification_record(database, record: dict):
    """Save a unification record"""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT OR REPLACE INTO championship_unifications (
            unification_id, primary_title_id, primary_title_name,
            secondary_title_id, secondary_title_name,
            resulting_title_id, resulting_title_name,
            unification_type, unified_by_wrestler_id, unified_by_wrestler_name,
            year, week, show_id, show_name, notes, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        record['unification_id'],
        record['primary_title_id'],
        record['primary_title_name'],
        record['secondary_title_id'],
        record['secondary_title_name'],
        record['resulting_title_id'],
        record['resulting_title_name'],
        record['unification_type'],
        record['unified_by_wrestler_id'],
        record['unified_by_wrestler_name'],
        record['year'],
        record['week'],
        record['show_id'],
        record['show_name'],
        record.get('notes', ''),
        now
    ))
    
    database.conn.commit()


def save_split_record(database, record: dict):
    """Save a split record"""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT OR REPLACE INTO championship_splits (
            split_id, original_title_id, original_title_name,
            new_title_ids, new_title_names, reason,
            year, week, show_id, show_name, notes, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        record['split_id'],
        record['original_title_id'],
        record['original_title_name'],
        json.dumps(record['new_title_ids']),
        json.dumps(record['new_title_names']),
        record['reason'],
        record['year'],
        record['week'],
        record['show_id'],
        record['show_name'],
        record.get('notes', ''),
        now
    ))
    
    database.conn.commit()


def save_transfer_record(database, record: dict):
    """Save a transfer record"""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT OR REPLACE INTO championship_transfers (
            transfer_id, title_id, title_name, transfer_type,
            from_value, to_value, year, week, reason, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        record['transfer_id'],
        record['title_id'],
        record['title_name'],
        record['transfer_type'],
        record['from_value'],
        record['to_value'],
        record['year'],
        record['week'],
        record.get('reason', ''),
        now
    ))
    
    database.conn.commit()


def save_lineage_record(database, record: dict):
    """Save a lineage record"""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT OR REPLACE INTO championship_lineages (
            lineage_id, title_id, title_name, lineage_number,
            start_year, start_week, end_year, end_week, end_reason,
            total_reigns, total_defenses, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        record['lineage_id'],
        record['title_id'],
        record['title_name'],
        record['lineage_number'],
        record['start_year'],
        record['start_week'],
        record.get('end_year'),
        record.get('end_week'),
        record.get('end_reason'),
        record.get('total_reigns', 0),
        record.get('total_defenses', 0),
        now
    ))
    
    database.conn.commit()


def get_unification_history(database, title_id: str = None):
    """Get unification history"""
    cursor = database.conn.cursor()
    
    if title_id:
        cursor.execute('''
            SELECT * FROM championship_unifications
            WHERE primary_title_id = ? OR secondary_title_id = ? OR resulting_title_id = ?
            ORDER BY year DESC, week DESC
        ''', (title_id, title_id, title_id))
    else:
        cursor.execute('SELECT * FROM championship_unifications ORDER BY year DESC, week DESC')
    
    return [dict(row) for row in cursor.fetchall()]


def get_split_history(database, title_id: str = None):
    """Get split history"""
    cursor = database.conn.cursor()
    
    if title_id:
        cursor.execute('''
            SELECT * FROM championship_splits
            WHERE original_title_id = ? OR new_title_ids LIKE ?
            ORDER BY year DESC, week DESC
        ''', (title_id, f'%{title_id}%'))
    else:
        cursor.execute('SELECT * FROM championship_splits ORDER BY year DESC, week DESC')
    
    results = []
    for row in cursor.fetchall():
        record = dict(row)
        record['new_title_ids'] = json.loads(record['new_title_ids'])
        record['new_title_names'] = json.loads(record['new_title_names'])
        results.append(record)
    
    return results


def get_transfer_history(database, title_id: str = None):
    """Get transfer history"""
    cursor = database.conn.cursor()
    
    if title_id:
        cursor.execute('''
            SELECT * FROM championship_transfers
            WHERE title_id = ?
            ORDER BY year DESC, week DESC
        ''', (title_id,))
    else:
        cursor.execute('SELECT * FROM championship_transfers ORDER BY year DESC, week DESC')
    
    return [dict(row) for row in cursor.fetchall()]


def get_lineages(database, title_id: str):
    """Get all lineages for a championship"""
    cursor = database.conn.cursor()
    cursor.execute('''
        SELECT * FROM championship_lineages
        WHERE title_id = ?
        ORDER BY lineage_number
    ''', (title_id,))
    
    return [dict(row) for row in cursor.fetchall()]