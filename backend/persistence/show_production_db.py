"""
Show Production Database Tables (Steps 58-72)
Handles show templates, pacing, segments, and production elements
"""

import sqlite3
from typing import Dict, Any
import json
from datetime import datetime


def create_show_production_tables(database):
    """Create all show production tables (Steps 58-72)"""
    cursor = database.conn.cursor()
    
    # ========================================================================
    # STEP 58-61: Show Templates & Types
    # ========================================================================
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS show_templates (
            template_id TEXT PRIMARY KEY,
            show_type TEXT NOT NULL,
            template_name TEXT NOT NULL,
            brand TEXT NOT NULL,
            default_duration_minutes INTEGER NOT NULL,
            default_match_count INTEGER NOT NULL,
            default_segment_count INTEGER NOT NULL,
            has_intermission INTEGER DEFAULT 0,
            intermission_minutes INTEGER DEFAULT 0,
            allows_commercials INTEGER DEFAULT 1,
            commercial_break_count INTEGER DEFAULT 0,
            ticket_price_base INTEGER DEFAULT 50,
            production_cost_base INTEGER DEFAULT 10000,
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
    ''')
    
    # Show types: weekly_tv, house_show, minor_ppv, major_ppv, supercard
    cursor.execute('''
        INSERT OR IGNORE INTO show_templates (
            template_id,
            show_type,
            template_name,
            brand,
            default_duration_minutes,
            default_match_count,
            default_segment_count,
            has_intermission,
            intermission_minutes,
            allows_commercials,
            commercial_break_count,
            ticket_price_base,
            production_cost_base,
            is_active,
            created_at
        ) VALUES
        ('tpl_weekly_alpha', 'weekly_tv', 'ROC Alpha Weekly', 'ROC Alpha', 120, 5, 3, 0, 0, 1, 3, 30, 5000, 1, datetime('now')),
        ('tpl_weekly_velocity', 'weekly_tv', 'ROC Velocity Weekly', 'ROC Velocity', 120, 5, 3, 0, 0, 1, 3, 30, 5000, 1, datetime('now')),
        ('tpl_weekly_vanguard', 'weekly_tv', 'ROC Vanguard Weekly', 'ROC Vanguard', 120, 5, 3, 0, 0, 1, 3, 30, 5000, 1, datetime('now')),
        ('tpl_house_show', 'house_show', 'House Show Tour', 'Cross-Brand', 150, 7, 0, 1, 15, 0, 0, 25, 3000, 1, datetime('now')),
        ('tpl_minor_ppv', 'minor_ppv', 'Minor PPV Template', 'Cross-Brand', 180, 6, 4, 1, 15, 0, 0, 75, 25000, 1, datetime('now')),
        ('tpl_major_ppv', 'major_ppv', 'Major PPV Template', 'Cross-Brand', 240, 8, 5, 1, 20, 0, 0, 150, 50000, 1, datetime('now')),
        ('tpl_supercard', 'supercard', 'Supercard Event', 'Cross-Brand', 300, 10, 6, 1, 20, 0, 0, 200, 100000, 1, datetime('now'))
    ''')
    
    # ========================================================================
    # STEP 63: Show Pacing & Crowd Energy
    # ========================================================================
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS show_pacing_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            show_id TEXT NOT NULL,
            show_name TEXT NOT NULL,
            year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            total_runtime_minutes INTEGER NOT NULL,
            planned_runtime_minutes INTEGER NOT NULL,
            is_overrunning INTEGER DEFAULT 0,
            overrun_minutes INTEGER DEFAULT 0,
            pacing_grade TEXT NOT NULL,
            opening_energy INTEGER DEFAULT 50,
            peak_energy INTEGER DEFAULT 0,
            final_energy INTEGER DEFAULT 50,
            energy_curve TEXT NOT NULL,
            dead_spots INTEGER DEFAULT 0,
            hot_stretches INTEGER DEFAULT 0,
            commercial_breaks_actual INTEGER DEFAULT 0,
            notes TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (show_id) REFERENCES show_history(show_id)
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_pacing_logs_show ON show_pacing_logs(show_id)')
    
    # ========================================================================
    # STEP 64: Time Slot Management
    # ========================================================================
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS time_slots (
            slot_id INTEGER PRIMARY KEY AUTOINCREMENT,
            show_id TEXT NOT NULL,
            slot_type TEXT NOT NULL,
            scheduled_minutes INTEGER NOT NULL,
            actual_minutes INTEGER DEFAULT 0,
            slot_position INTEGER NOT NULL,
            content_type TEXT NOT NULL,
            content_id TEXT,
            is_commercial INTEGER DEFAULT 0,
            is_dark_match INTEGER DEFAULT 0,
            notes TEXT,
            FOREIGN KEY (show_id) REFERENCES show_history(show_id)
        )
    ''')
    
    # ========================================================================
    # STEP 65-67: Run-Ins, Interference, Returns
    # ========================================================================
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS show_interference_log (
            interference_id TEXT PRIMARY KEY,
            show_id TEXT NOT NULL,
            show_name TEXT NOT NULL,
            year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            match_id TEXT,
            segment_id TEXT,
            interference_type TEXT NOT NULL,
            interferer_id TEXT NOT NULL,
            interferer_name TEXT NOT NULL,
            target_id TEXT,
            target_name TEXT,
            was_planned INTEGER DEFAULT 1,
            was_surprise INTEGER DEFAULT 0,
            crowd_reaction TEXT,
            feud_id TEXT,
            description TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_interference_show ON show_interference_log(show_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_interference_wrestler ON show_interference_log(interferer_id)')
    
    # ========================================================================
    # STEP 71: Dark Matches
    # ========================================================================
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dark_matches (
            dark_match_id TEXT PRIMARY KEY,
            show_id TEXT NOT NULL,
            show_name TEXT NOT NULL,
            year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            match_type TEXT NOT NULL,
            side_a_ids TEXT NOT NULL,
            side_a_names TEXT NOT NULL,
            side_b_ids TEXT NOT NULL,
            side_b_names TEXT NOT NULL,
            winner TEXT NOT NULL,
            duration_minutes INTEGER DEFAULT 10,
            purpose TEXT NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (show_id) REFERENCES show_history(show_id)
        )
    ''')

    # Forward-compatible columns for dark matches (routes send richer payloads).
    # SQLite: no IF NOT EXISTS for ADD COLUMN, so try/except.
    for ddl in [
        "ALTER TABLE dark_matches ADD COLUMN notes TEXT",
        "ALTER TABLE dark_matches ADD COLUMN brand TEXT",
        "ALTER TABLE dark_matches ADD COLUMN finish_type TEXT",
        "ALTER TABLE dark_matches ADD COLUMN star_rating REAL DEFAULT 0.0",
        "ALTER TABLE dark_matches ADD COLUMN is_tryout INTEGER DEFAULT 0",
        "ALTER TABLE dark_matches ADD COLUMN is_developmental INTEGER DEFAULT 0",
        "ALTER TABLE dark_matches ADD COLUMN is_pre_show INTEGER DEFAULT 1",
        "ALTER TABLE dark_matches ADD COLUMN is_post_show INTEGER DEFAULT 0",
        "ALTER TABLE dark_matches ADD COLUMN match_summary TEXT",
        "ALTER TABLE dark_matches ADD COLUMN highlights TEXT DEFAULT '[]'",
    ]:
        try:
            cursor.execute(ddl)
        except Exception:
            pass

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dark_matches_show ON dark_matches(show_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dark_matches_year_week ON dark_matches(year, week)')
    
    # ========================================================================
    # STEP 72: Show Themes
    # ========================================================================
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS show_themes (
            theme_id TEXT PRIMARY KEY,
            theme_name TEXT NOT NULL,
            theme_type TEXT NOT NULL,
            description TEXT NOT NULL,
            trigger_condition TEXT,
            bonus_match_quality REAL DEFAULT 0.0,
            bonus_attendance_pct REAL DEFAULT 0.0,
            bonus_revenue_pct REAL DEFAULT 0.0,
            special_stipulation TEXT,
            extra_event_log_prefix TEXT,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    cursor.execute('''
        INSERT OR IGNORE INTO show_themes VALUES
        ('theme_anniversary', 'Anniversary Special', 'celebration', 'Celebrating promotion anniversary with nostalgia and legends', 'year_milestone', 0.25, 0.10, 0.15, NULL, '🎉 ANNIVERSARY', 1),
        ('theme_tribute', 'Tribute Night', 'memorial', 'Honoring a retired or deceased wrestler', 'special_occasion', 0.15, 0.05, 0.05, NULL, '🕊️ TRIBUTE', 1),
        ('theme_wildcard', 'Wildcard Night', 'variety', 'Cross-brand chaos with unexpected matchups', 'special_booking', 0.10, 0.08, 0.10, 'No DQ', '🎲 WILDCARD', 1),
        ('theme_extreme', 'Extreme Rules', 'hardcore', 'All matches have relaxed rules', 'ppv_only', 0.20, 0.12, 0.18, 'No Disqualification', '⚡ EXTREME', 1),
        ('theme_pride', 'Pride Month Special', 'social', 'Celebrating diversity and inclusion', 'june_only', 0.05, 0.15, 0.10, NULL, '🏳️‍🌈 PRIDE', 1),
        ('theme_draft', 'Draft Night', 'roster', 'Annual draft with surprise picks', 'draft_week', 0.10, 0.20, 0.15, NULL, '📋 DRAFT', 1)
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS show_theme_assignments (
            assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            show_id TEXT NOT NULL,
            theme_id TEXT NOT NULL,
            applied_bonuses TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (show_id) REFERENCES show_history(show_id),
            FOREIGN KEY (theme_id) REFERENCES show_themes(theme_id)
        )
    ''')
    
    database.conn.commit()
    print("✅ Show production tables created (Steps 58-72)")


def save_dark_match(database, dark_match: Dict[str, Any]) -> None:
    """
    Persist a single dark match (Step 71).

    List fields are stored as JSON strings.
    Unknown keys are ignored so callers can send richer payloads safely.
    """
    cursor = database.conn.cursor()

    # Self-heal schema drift for older saves that may not have run startup
    # table creation/migrations yet.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dark_matches (
            dark_match_id TEXT PRIMARY KEY,
            show_id TEXT NOT NULL,
            show_name TEXT NOT NULL,
            year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            match_type TEXT NOT NULL,
            side_a_ids TEXT NOT NULL,
            side_a_names TEXT NOT NULL,
            side_b_ids TEXT NOT NULL,
            side_b_names TEXT NOT NULL,
            winner TEXT NOT NULL,
            duration_minutes INTEGER DEFAULT 10,
            purpose TEXT NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL,
            brand TEXT,
            finish_type TEXT,
            star_rating REAL DEFAULT 0.0,
            is_tryout INTEGER DEFAULT 0,
            is_developmental INTEGER DEFAULT 0,
            is_pre_show INTEGER DEFAULT 1,
            is_post_show INTEGER DEFAULT 0,
            match_summary TEXT,
            highlights TEXT DEFAULT '[]',
            FOREIGN KEY (show_id) REFERENCES show_history(show_id)
        )
    ''')

    cursor.execute("PRAGMA table_info(dark_matches)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    for ddl, col_name in [
        ("ALTER TABLE dark_matches ADD COLUMN notes TEXT", "notes"),
        ("ALTER TABLE dark_matches ADD COLUMN brand TEXT", "brand"),
        ("ALTER TABLE dark_matches ADD COLUMN finish_type TEXT", "finish_type"),
        ("ALTER TABLE dark_matches ADD COLUMN star_rating REAL DEFAULT 0.0", "star_rating"),
        ("ALTER TABLE dark_matches ADD COLUMN is_tryout INTEGER DEFAULT 0", "is_tryout"),
        ("ALTER TABLE dark_matches ADD COLUMN is_developmental INTEGER DEFAULT 0", "is_developmental"),
        ("ALTER TABLE dark_matches ADD COLUMN is_pre_show INTEGER DEFAULT 1", "is_pre_show"),
        ("ALTER TABLE dark_matches ADD COLUMN is_post_show INTEGER DEFAULT 0", "is_post_show"),
        ("ALTER TABLE dark_matches ADD COLUMN match_summary TEXT", "match_summary"),
        ("ALTER TABLE dark_matches ADD COLUMN highlights TEXT DEFAULT '[]'", "highlights"),
    ]:
        if col_name not in existing_columns:
            cursor.execute(ddl)

    def _json(value, default):
        if value is None:
            value = default
        if isinstance(value, str):
            return value
        return json.dumps(value)

    now = datetime.now().isoformat()

    cursor.execute(
        '''
        INSERT OR REPLACE INTO dark_matches (
            dark_match_id, show_id, show_name, year, week,
            match_type,
            side_a_ids, side_a_names, side_b_ids, side_b_names,
            winner, duration_minutes, purpose, notes, created_at,
            brand, finish_type, star_rating,
            is_tryout, is_developmental, is_pre_show, is_post_show,
            match_summary, highlights
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''',
        (
            dark_match.get("dark_match_id"),
            dark_match.get("show_id"),
            dark_match.get("show_name"),
            int(dark_match.get("year", 1)),
            int(dark_match.get("week", 1)),
            str(dark_match.get("match_type", "pre_show")),
            _json(dark_match.get("side_a_ids"), []),
            _json(dark_match.get("side_a_names"), []),
            _json(dark_match.get("side_b_ids"), []),
            _json(dark_match.get("side_b_names"), []),
            str(dark_match.get("winner", "pending")),
            int(dark_match.get("duration_minutes", 8)),
            str(dark_match.get("purpose", "crowd_warmup")),
            dark_match.get("notes"),
            dark_match.get("created_at") or now,
            dark_match.get("brand"),
            dark_match.get("finish_type"),
            float(dark_match.get("star_rating", 0.0) or 0.0),
            1 if dark_match.get("is_tryout") else 0,
            1 if dark_match.get("is_developmental") else 0,
            1 if dark_match.get("is_pre_show", True) else 0,
            1 if dark_match.get("is_post_show", False) else 0,
            dark_match.get("match_summary"),
            _json(dark_match.get("highlights"), []),
        ),
    )


def get_show_template(database, show_type: str, brand: str) -> Dict[str, Any]:
    """Get show template for a specific type and brand"""
    cursor = database.conn.cursor()
    
    cursor.execute('''
        SELECT * FROM show_templates
        WHERE show_type = ? AND (brand = ? OR brand = 'Cross-Brand')
        AND is_active = 1
        LIMIT 1
    ''', (show_type, brand))
    
    row = cursor.fetchone()
    return dict(row) if row else None


def log_show_pacing(database, pacing_data: Dict[str, Any]):
    """Log show pacing metrics (Step 63)"""
    cursor = database.conn.cursor()
    
    from datetime import datetime
    now = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT INTO show_pacing_logs (
            show_id, show_name, year, week,
            total_runtime_minutes, planned_runtime_minutes,
            is_overrunning, overrun_minutes,
            pacing_grade, opening_energy, peak_energy, final_energy,
            energy_curve, dead_spots, hot_stretches,
            commercial_breaks_actual, notes, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        pacing_data['show_id'],
        pacing_data['show_name'],
        pacing_data['year'],
        pacing_data['week'],
        pacing_data['total_runtime_minutes'],
        pacing_data['planned_runtime_minutes'],
        1 if pacing_data.get('is_overrunning', False) else 0,
        pacing_data.get('overrun_minutes', 0),
        pacing_data['pacing_grade'],
        pacing_data.get('opening_energy', 50),
        pacing_data.get('peak_energy', 0),
        pacing_data.get('final_energy', 50),
        pacing_data.get('energy_curve', '[]'),
        pacing_data.get('dead_spots', 0),
        pacing_data.get('hot_stretches', 0),
        pacing_data.get('commercial_breaks_actual', 0),
        pacing_data.get('notes'),
        now
    ))
    
    database.conn.commit()


def log_interference(database, interference_data: Dict[str, Any]):
    """Log run-in/interference event (Steps 65-67)"""
    cursor = database.conn.cursor()
    
    from datetime import datetime
    now = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT INTO show_interference_log (
            interference_id, show_id, show_name, year, week,
            match_id, segment_id, interference_type,
            interferer_id, interferer_name, target_id, target_name,
            was_planned, was_surprise, crowd_reaction,
            feud_id, description, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        interference_data['interference_id'],
        interference_data['show_id'],
        interference_data['show_name'],
        interference_data['year'],
        interference_data['week'],
        interference_data.get('match_id'),
        interference_data.get('segment_id'),
        interference_data['interference_type'],
        interference_data['interferer_id'],
        interference_data['interferer_name'],
        interference_data.get('target_id'),
        interference_data.get('target_name'),
        1 if interference_data.get('was_planned', True) else 0,
        1 if interference_data.get('was_surprise', False) else 0,
        interference_data.get('crowd_reaction'),
        interference_data.get('feud_id'),
        interference_data['description'],
        now
    ))
    
    database.conn.commit()
