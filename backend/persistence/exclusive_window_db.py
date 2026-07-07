"""
Exclusive Window Database Management
Handles storage and retrieval of exclusive negotiating windows for free agents.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta


def create_exclusive_window_tables(database):
    """Create tables for exclusive negotiating windows"""
    cursor = database.conn.cursor()
    
    # Exclusive negotiating windows
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exclusive_windows (
            id TEXT PRIMARY KEY,
            free_agent_id TEXT NOT NULL,
            wrestler_name TEXT NOT NULL,
            promotion_id TEXT NOT NULL,
            promotion_name TEXT NOT NULL,
            
            -- Window terms
            cost_paid INTEGER NOT NULL,
            duration_days INTEGER NOT NULL,
            started_year INTEGER NOT NULL,
            started_week INTEGER NOT NULL,
            expires_year INTEGER NOT NULL,
            expires_week INTEGER NOT NULL,
            
            -- Status
            is_active BOOLEAN DEFAULT 1,
            resulted_in_signing BOOLEAN DEFAULT 0,
            refund_eligible BOOLEAN DEFAULT 0,
            refund_percentage REAL DEFAULT 0.0,
            
            -- Negotiation tracking
            offers_made INTEGER DEFAULT 0,
            last_offer_amount INTEGER DEFAULT 0,
            negotiation_status TEXT DEFAULT 'pending',
            
            -- Metadata
            created_at TEXT NOT NULL,
            completed_at TEXT,
            notes TEXT,
            
            FOREIGN KEY (free_agent_id) REFERENCES free_agents(id)
        )
    ''')
    
    # Window history and events
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exclusive_window_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            window_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            description TEXT,
            year INTEGER,
            week INTEGER,
            created_at TEXT NOT NULL,
            
            FOREIGN KEY (window_id) REFERENCES exclusive_windows(id)
        )
    ''')
    
    # Indexes
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_exclusive_windows_fa 
        ON exclusive_windows(free_agent_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_exclusive_windows_active 
        ON exclusive_windows(is_active, expires_year, expires_week)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_window_events_window 
        ON exclusive_window_events(window_id)
    ''')
    
    database.conn.commit()
    print("✅ Exclusive window tables created")


def save_exclusive_window(database, window_data: Dict[str, Any]) -> str:
    """Save an exclusive window to database"""
    cursor = database.conn.cursor()
    
    window_id = window_data.get('id', f"ew_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    
    cursor.execute('''
        INSERT OR REPLACE INTO exclusive_windows (
            id, free_agent_id, wrestler_name, promotion_id, promotion_name,
            cost_paid, duration_days, started_year, started_week,
            expires_year, expires_week, is_active, resulted_in_signing,
            refund_eligible, refund_percentage, offers_made, last_offer_amount,
            negotiation_status, created_at, completed_at, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        window_id,
        window_data['free_agent_id'],
        window_data['wrestler_name'],
        window_data['promotion_id'],
        window_data['promotion_name'],
        window_data['cost_paid'],
        window_data['duration_days'],
        window_data['started_year'],
        window_data['started_week'],
        window_data['expires_year'],
        window_data['expires_week'],
        window_data.get('is_active', True),
        window_data.get('resulted_in_signing', False),
        window_data.get('refund_eligible', False),
        window_data.get('refund_percentage', 0.0),
        window_data.get('offers_made', 0),
        window_data.get('last_offer_amount', 0),
        window_data.get('negotiation_status', 'pending'),
        window_data.get('created_at', datetime.now().isoformat()),
        window_data.get('completed_at'),
        window_data.get('notes')
    ))
    
    # Don't commit here - let caller batch commits
    return window_id


def get_active_exclusive_window(database, free_agent_id: str) -> Optional[Dict[str, Any]]:
    """Get active exclusive window for a free agent"""
    cursor = database.conn.cursor()
    
    cursor.execute('''
        SELECT * FROM exclusive_windows
        WHERE free_agent_id = ? AND is_active = 1
        ORDER BY created_at DESC
        LIMIT 1
    ''', (free_agent_id,))
    
    row = cursor.fetchone()
    return dict(row) if row else None


def get_promotion_exclusive_windows(
    database, 
    promotion_id: str, 
    active_only: bool = True
) -> List[Dict[str, Any]]:
    """Get all exclusive windows for a promotion"""
    cursor = database.conn.cursor()
    
    query = '''
        SELECT * FROM exclusive_windows
        WHERE promotion_id = ?
    '''
    
    if active_only:
        query += ' AND is_active = 1'
    
    query += ' ORDER BY created_at DESC'
    
    cursor.execute(query, (promotion_id,))
    
    return [dict(row) for row in cursor.fetchall()]


def expire_exclusive_window(
    database, 
    window_id: str, 
    resulted_in_signing: bool = False,
    refund_amount: int = 0
) -> bool:
    """Expire an exclusive window"""
    cursor = database.conn.cursor()
    
    cursor.execute('''
        UPDATE exclusive_windows
        SET is_active = 0,
            completed_at = ?,
            resulted_in_signing = ?,
            refund_percentage = ?
        WHERE id = ?
    ''', (
        datetime.now().isoformat(),
        resulted_in_signing,
        refund_amount,
        window_id
    ))
    
    # Record event
    cursor.execute('''
        INSERT INTO exclusive_window_events (
            window_id, event_type, description, created_at
        ) VALUES (?, ?, ?, ?)
    ''', (
        window_id,
        'expired',
        'Window expired' + (' - Signing completed' if resulted_in_signing else ''),
        datetime.now().isoformat()
    ))
    
    # Don't commit - let caller batch
    return cursor.rowcount > 0


def record_window_event(
    database,
    window_id: str,
    event_type: str,
    description: str,
    year: Optional[int] = None,
    week: Optional[int] = None
):
    """Record an event in exclusive window history"""
    cursor = database.conn.cursor()
    
    cursor.execute('''
        INSERT INTO exclusive_window_events (
            window_id, event_type, description, year, week, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        window_id,
        event_type,
        description,
        year,
        week,
        datetime.now().isoformat()
    ))


def get_window_events(database, window_id: str) -> List[Dict[str, Any]]:
    """Get all events for a window"""
    cursor = database.conn.cursor()
    
    cursor.execute('''
        SELECT * FROM exclusive_window_events
        WHERE window_id = ?
        ORDER BY created_at DESC
    ''', (window_id,))
    
    return [dict(row) for row in cursor.fetchall()]


def check_expired_windows(database, current_year: int, current_week: int) -> List[Dict[str, Any]]:
    """Check for windows that have expired"""
    cursor = database.conn.cursor()
    
    cursor.execute('''
        SELECT * FROM exclusive_windows
        WHERE is_active = 1
        AND (
            expires_year < ?
            OR (expires_year = ? AND expires_week <= ?)
        )
    ''', (current_year, current_year, current_week))
    
    return [dict(row) for row in cursor.fetchall()]