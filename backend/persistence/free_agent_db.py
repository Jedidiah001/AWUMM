"""
Free Agent Database Operations
Handles all persistence for the free agent pool system.
"""

import sqlite3
import json
from typing import List, Optional, Dict, Any
from datetime import datetime


def create_free_agent_tables(database):
    """Create all free agent related tables"""
    cursor = database.conn.cursor()
    
    # Main Free Agents Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS free_agents (
            id TEXT PRIMARY KEY,
            wrestler_id TEXT NOT NULL,
            wrestler_name TEXT NOT NULL,
            
            -- Wrestler snapshot
            age INTEGER NOT NULL,
            gender TEXT NOT NULL,
            alignment TEXT NOT NULL,
            role TEXT NOT NULL,
            
            -- Attributes
            brawling INTEGER NOT NULL,
            technical INTEGER NOT NULL,
            speed INTEGER NOT NULL,
            mic INTEGER NOT NULL,
            psychology INTEGER NOT NULL,
            stamina INTEGER NOT NULL,
            
            -- Career
            years_experience INTEGER NOT NULL,
            is_major_superstar INTEGER NOT NULL DEFAULT 0,
            popularity INTEGER NOT NULL DEFAULT 50,
            
            -- STEP 116: Enhanced market value tracking
            peak_popularity INTEGER DEFAULT 50,
            market_value_trend TEXT DEFAULT 'stable',
            last_value_calculation TEXT,
            average_match_rating REAL DEFAULT 3.0,
            recent_match_rating REAL DEFAULT 3.0,
            five_star_matches INTEGER DEFAULT 0,
            four_plus_matches INTEGER DEFAULT 0,
            injury_history_count INTEGER DEFAULT 0,
            months_since_last_injury INTEGER DEFAULT 12,
            has_chronic_issues INTEGER DEFAULT 0,
            backstage_reputation INTEGER DEFAULT 50,
            locker_room_leader INTEGER DEFAULT 0,
            known_difficult INTEGER DEFAULT 0,
            
            -- Free agency status
            source TEXT NOT NULL,
            visibility INTEGER NOT NULL DEFAULT 2,
            mood TEXT NOT NULL DEFAULT 'patient',
            market_value INTEGER NOT NULL DEFAULT 10000,
            weeks_unemployed INTEGER NOT NULL DEFAULT 0,
            
            -- Agent info (JSON)
            agent_data TEXT,
            
            -- Contract demands (JSON)
            demands_data TEXT,
            
            -- Controversy
            has_controversy INTEGER NOT NULL DEFAULT 0,
            controversy_type TEXT,
            controversy_severity INTEGER NOT NULL DEFAULT 0,
            time_since_incident_weeks INTEGER NOT NULL DEFAULT 0,
            
            -- Legend status
            is_legend INTEGER NOT NULL DEFAULT 0,
            retirement_status TEXT NOT NULL DEFAULT 'active',
            comeback_likelihood INTEGER NOT NULL DEFAULT 50,
            
            -- International
            origin_region TEXT NOT NULL DEFAULT 'domestic',
            requires_visa INTEGER NOT NULL DEFAULT 0,
            exclusive_willing INTEGER NOT NULL DEFAULT 1,
            
            -- Prospect
            is_prospect INTEGER NOT NULL DEFAULT 0,
            training_investment_needed INTEGER NOT NULL DEFAULT 0,
            ceiling_potential INTEGER NOT NULL DEFAULT 50,
            
            -- Availability timing
            available_from_year INTEGER NOT NULL DEFAULT 1,
            available_from_week INTEGER NOT NULL DEFAULT 1,
            no_compete_until_year INTEGER,
            no_compete_until_week INTEGER,
            
            -- STEP 124: Exclusive window tracking
            exclusive_window_active INTEGER DEFAULT 0,
            exclusive_window_holder TEXT,
            exclusive_window_holder_name TEXT,
            exclusive_window_cost_paid INTEGER DEFAULT 0,
            exclusive_window_duration INTEGER DEFAULT 0,
            exclusive_window_started_year INTEGER,
            exclusive_window_started_week INTEGER,
            exclusive_window_expires_year INTEGER,
            exclusive_window_expires_week INTEGER,
            exclusive_window_id TEXT,
            exclusive_window_resulted_in_signing INTEGER DEFAULT 0,
            
            -- Discovery
            discovered INTEGER NOT NULL DEFAULT 0,
            
            -- Status
            is_signed INTEGER NOT NULL DEFAULT 0,
            signed_to_promotion TEXT,
            signed_year INTEGER,
            signed_week INTEGER,
            
            -- Timestamps
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')
    
    # Rival Interest Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS free_agent_rival_interest (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            free_agent_id TEXT NOT NULL,
            promotion_name TEXT NOT NULL,
            interest_level INTEGER NOT NULL DEFAULT 50,
            offer_salary INTEGER NOT NULL DEFAULT 0,
            offer_made INTEGER NOT NULL DEFAULT 0,
            deadline_week INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY (free_agent_id) REFERENCES free_agents(id),
            UNIQUE(free_agent_id, promotion_name)
        )
    ''')
    
    # Contract History Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS free_agent_contract_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            free_agent_id TEXT NOT NULL,
            promotion_name TEXT NOT NULL,
            start_year INTEGER NOT NULL,
            end_year INTEGER NOT NULL,
            departure_reason TEXT NOT NULL,
            final_salary INTEGER NOT NULL DEFAULT 5000,
            was_champion INTEGER NOT NULL DEFAULT 0,
            relationship_on_departure INTEGER NOT NULL DEFAULT 50,
            created_at TEXT NOT NULL,
            FOREIGN KEY (free_agent_id) REFERENCES free_agents(id)
        )
    ''')
    
    # Negotiation History Table (for tracking past offers)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS negotiation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            free_agent_id TEXT NOT NULL,
            promotion_name TEXT NOT NULL,
            offer_salary INTEGER NOT NULL,
            offer_length_weeks INTEGER NOT NULL,
            offer_signing_bonus INTEGER NOT NULL DEFAULT 0,
            offer_accepted INTEGER NOT NULL DEFAULT 0,
            rejection_reason TEXT,
            negotiation_round INTEGER NOT NULL DEFAULT 1,
            year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (free_agent_id) REFERENCES free_agents(id)
        )
    ''')
    
    # Scouting Reports Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scouting_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            free_agent_id TEXT NOT NULL,
            scout_accuracy INTEGER NOT NULL DEFAULT 50,
            reported_potential TEXT,
            reported_concerns TEXT,
            scouting_cost INTEGER NOT NULL DEFAULT 0,
            year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (free_agent_id) REFERENCES free_agents(id)
        )
    ''')
    
    # Market Value History Table (STEP 116)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS free_agent_market_value_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            free_agent_id TEXT NOT NULL,
            year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            value INTEGER NOT NULL,
            reason TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (free_agent_id) REFERENCES free_agents(id)
        )
    ''')
    
    # Exclusive Windows Table (STEP 124)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exclusive_windows (
            window_id TEXT PRIMARY KEY,
            free_agent_id TEXT NOT NULL,
            promotion_id TEXT NOT NULL DEFAULT 'player',
            promotion_name TEXT NOT NULL,
            cost_paid INTEGER NOT NULL,
            duration_days INTEGER NOT NULL,
            started_year INTEGER NOT NULL,
            started_week INTEGER NOT NULL,
            expires_year INTEGER NOT NULL,
            expires_week INTEGER NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            resulted_in_signing INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            ended_at TEXT,
            FOREIGN KEY (free_agent_id) REFERENCES free_agents(id)
        )
    ''')
    
    # Indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_free_agents_wrestler ON free_agents(wrestler_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_free_agents_source ON free_agents(source)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_free_agents_visibility ON free_agents(visibility)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_free_agents_signed ON free_agents(is_signed)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_free_agents_discovered ON free_agents(discovered)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_rival_interest_fa ON free_agent_rival_interest(free_agent_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_contract_history_fa ON free_agent_contract_history(free_agent_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_market_value_history_fa ON free_agent_market_value_history(free_agent_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_exclusive_windows_fa ON exclusive_windows(free_agent_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_exclusive_windows_active ON exclusive_windows(is_active)')
    
    database.conn.commit()
    print("✅ Free agent tables created")


def _get_rival_field(rival, field_name, default=None):
    """
    Helper to get a field from a rival interest object or dict.
    Handles both object attributes and dictionary keys.
    """
    if isinstance(rival, dict):
        return rival.get(field_name, default)
    else:
        return getattr(rival, field_name, default)


def _get_history_field(history, field_name, default=None):
    """
    Helper to get a field from a contract history object or dict.
    Handles both object attributes and dictionary keys.
    """
    if isinstance(history, dict):
        return history.get(field_name, default)
    else:
        return getattr(history, field_name, default)


def save_free_agent(database, free_agent) -> None:
    """Save or update a free agent (ENHANCED for STEP 116-117 + 124)"""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    # Handle agent serialization - can be object, dict, or None
    agent_data = None
    if hasattr(free_agent, 'agent') and free_agent.agent is not None:
        if hasattr(free_agent.agent, 'to_dict'):
            agent_data = json.dumps(free_agent.agent.to_dict())
        elif isinstance(free_agent.agent, dict):
            agent_data = json.dumps(free_agent.agent)
        else:
            agent_data = json.dumps({})
    
    # Handle demands serialization - can be object, dict, or None
    demands_data = None
    if hasattr(free_agent, 'demands') and free_agent.demands is not None:
        if hasattr(free_agent.demands, 'to_dict'):
            demands_data = json.dumps(free_agent.demands.to_dict())
        elif isinstance(free_agent.demands, dict):
            demands_data = json.dumps(free_agent.demands)
        else:
            demands_data = json.dumps({})
    
    cursor.execute('''
        INSERT OR REPLACE INTO free_agents (
            id, wrestler_id, wrestler_name,
            age, gender, alignment, role,
            brawling, technical, speed, mic, psychology, stamina,
            years_experience, is_major_superstar, popularity,
            peak_popularity, market_value_trend, last_value_calculation,
            average_match_rating, recent_match_rating, five_star_matches, four_plus_matches,
            injury_history_count, months_since_last_injury, has_chronic_issues,
            backstage_reputation, locker_room_leader, known_difficult,
            source, visibility, mood, market_value, weeks_unemployed,
            agent_data, demands_data,
            has_controversy, controversy_type, controversy_severity, time_since_incident_weeks,
            is_legend, retirement_status, comeback_likelihood,
            origin_region, requires_visa, exclusive_willing,
            is_prospect, training_investment_needed, ceiling_potential,
            available_from_year, available_from_week,
            no_compete_until_year, no_compete_until_week,
            exclusive_window_active, exclusive_window_holder, exclusive_window_holder_name,
            exclusive_window_cost_paid, exclusive_window_duration,
            exclusive_window_started_year, exclusive_window_started_week,
            exclusive_window_expires_year, exclusive_window_expires_week,
            exclusive_window_id, exclusive_window_resulted_in_signing,
            discovered, is_signed, signed_to_promotion, signed_year, signed_week,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        free_agent.id,
        free_agent.wrestler_id,
        free_agent.wrestler_name,
        free_agent.age,
        free_agent.gender,
        free_agent.alignment,
        free_agent.role,
        free_agent.brawling,
        free_agent.technical,
        free_agent.speed,
        free_agent.mic,
        free_agent.psychology,
        free_agent.stamina,
        free_agent.years_experience,
        1 if free_agent.is_major_superstar else 0,
        free_agent.popularity,
        # STEP 116: New fields
        getattr(free_agent, 'peak_popularity', free_agent.popularity),
        getattr(free_agent, 'market_value_trend', 'stable'),
        getattr(free_agent, 'last_value_calculation', None),
        getattr(free_agent, 'average_match_rating', 3.0),
        getattr(free_agent, 'recent_match_rating', 3.0),
        getattr(free_agent, 'five_star_matches', 0),
        getattr(free_agent, 'four_plus_matches', 0),
        getattr(free_agent, 'injury_history_count', 0),
        getattr(free_agent, 'months_since_last_injury', 12),
        1 if getattr(free_agent, 'has_chronic_issues', False) else 0,
        getattr(free_agent, 'backstage_reputation', 50),
        1 if getattr(free_agent, 'locker_room_leader', False) else 0,
        1 if getattr(free_agent, 'known_difficult', False) else 0,
        # End STEP 116 fields
        free_agent.source.value if hasattr(free_agent.source, 'value') else free_agent.source,
        free_agent.visibility.value if hasattr(free_agent.visibility, 'value') else free_agent.visibility,
        free_agent.mood.value if hasattr(free_agent.mood, 'value') else free_agent.mood,
        free_agent.market_value,
        free_agent.weeks_unemployed,
        agent_data,
        demands_data,
        1 if free_agent.has_controversy else 0,
        free_agent.controversy_type,
        free_agent.controversy_severity,
        free_agent.time_since_incident_weeks,
        1 if free_agent.is_legend else 0,
        free_agent.retirement_status,
        free_agent.comeback_likelihood,
        free_agent.origin_region,
        1 if free_agent.requires_visa else 0,
        1 if free_agent.exclusive_willing else 0,
        1 if free_agent.is_prospect else 0,
        free_agent.training_investment_needed,
        free_agent.ceiling_potential,
        free_agent.available_from_year,
        free_agent.available_from_week,
        free_agent.no_compete_until_year,
        free_agent.no_compete_until_week,
        # STEP 124: Exclusive window fields
        1 if getattr(free_agent, 'exclusive_window_active', False) else 0,
        getattr(free_agent, 'exclusive_window_holder', None),
        getattr(free_agent, 'exclusive_window_holder_name', None),
        getattr(free_agent, 'exclusive_window_cost_paid', 0),
        getattr(free_agent, 'exclusive_window_duration', 0),
        getattr(free_agent, 'exclusive_window_started_year', None),
        getattr(free_agent, 'exclusive_window_started_week', None),
        getattr(free_agent, 'exclusive_window_expires_year', None),
        getattr(free_agent, 'exclusive_window_expires_week', None),
        getattr(free_agent, 'exclusive_window_id', None),
        1 if getattr(free_agent, 'exclusive_window_resulted_in_signing', False) else 0,
        # End STEP 124 fields
        1 if free_agent.discovered else 0,
        1 if getattr(free_agent, 'is_signed', False) else 0,
        getattr(free_agent, 'signed_to_promotion', None),
        getattr(free_agent, 'signed_year', None),
        getattr(free_agent, 'signed_week', None),
        getattr(free_agent, 'created_at', now),
        now
    ))
    
    # Save rival interest - handle both object and dict formats
    cursor.execute('DELETE FROM free_agent_rival_interest WHERE free_agent_id = ?', (free_agent.id,))
    rival_interest_list = getattr(free_agent, 'rival_interest', []) or []
    
    for rival in rival_interest_list:
        # Use helper function to handle both dict and object
        promotion_name = _get_rival_field(rival, 'promotion_name', 'Unknown')
        interest_level = _get_rival_field(rival, 'interest_level', 50)
        offer_salary = _get_rival_field(rival, 'offer_salary', 0)
        offer_made = _get_rival_field(rival, 'offer_made', False)
        deadline_week = _get_rival_field(rival, 'deadline_week', None)
        
        cursor.execute('''
            INSERT INTO free_agent_rival_interest (
                free_agent_id, promotion_name, interest_level,
                offer_salary, offer_made, deadline_week, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            free_agent.id,
            promotion_name,
            interest_level,
            offer_salary,
            1 if offer_made else 0,
            deadline_week,
            now
        ))
    
    # Save contract history - handle both object and dict formats
    cursor.execute('DELETE FROM free_agent_contract_history WHERE free_agent_id = ?', (free_agent.id,))
    contract_history_list = getattr(free_agent, 'contract_history', []) or []
    
    for history in contract_history_list:
        # Use helper function to handle both dict and object
        promotion_name = _get_history_field(history, 'promotion_name', 'Unknown')
        start_year = _get_history_field(history, 'start_year', 1)
        end_year = _get_history_field(history, 'end_year', 1)
        departure_reason = _get_history_field(history, 'departure_reason', 'released')
        final_salary = _get_history_field(history, 'final_salary', 5000)
        was_champion = _get_history_field(history, 'was_champion', False)
        relationship_on_departure = _get_history_field(history, 'relationship_on_departure', 50)
        
        cursor.execute('''
            INSERT INTO free_agent_contract_history (
                free_agent_id, promotion_name, start_year, end_year,
                departure_reason, final_salary, was_champion,
                relationship_on_departure, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            free_agent.id,
            promotion_name,
            start_year,
            end_year,
            departure_reason,
            final_salary,
            1 if was_champion else 0,
            relationship_on_departure,
            now
        ))
    
    # STEP 116: Save market value history if present
    market_value_history = getattr(free_agent, 'market_value_history', None)
    if market_value_history:
        # Keep only last 52 weeks
        for mv_entry in market_value_history[-52:]:
            # Handle both dict and object
            if isinstance(mv_entry, dict):
                mv_year = mv_entry.get('year', 1)
                mv_week = mv_entry.get('week', 1)
                mv_value = mv_entry.get('value', 0)
                mv_reason = mv_entry.get('reason', '')
            else:
                mv_year = getattr(mv_entry, 'year', 1)
                mv_week = getattr(mv_entry, 'week', 1)
                mv_value = getattr(mv_entry, 'value', 0)
                mv_reason = getattr(mv_entry, 'reason', '')
            
            cursor.execute('''
                INSERT OR IGNORE INTO free_agent_market_value_history (
                    free_agent_id, year, week, value, reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                free_agent.id,
                mv_year,
                mv_week,
                mv_value,
                mv_reason,
                now
            ))
    
    database.conn.commit()


def get_free_agent_by_id(database, free_agent_id: str) -> Optional[Dict[str, Any]]:
    """Get a free agent by ID"""
    cursor = database.conn.cursor()
    cursor.execute('SELECT * FROM free_agents WHERE id = ?', (free_agent_id,))
    row = cursor.fetchone()
    
    if not row:
        return None
    
    fa_dict = dict(row)
    
    # Parse JSON fields
    fa_dict['agent'] = json.loads(fa_dict['agent_data']) if fa_dict.get('agent_data') else {}
    fa_dict['demands'] = json.loads(fa_dict['demands_data']) if fa_dict.get('demands_data') else {}
    
    # Get rival interest
    cursor.execute('SELECT * FROM free_agent_rival_interest WHERE free_agent_id = ?', (free_agent_id,))
    fa_dict['rival_interest'] = [dict(r) for r in cursor.fetchall()]
    
    # Get contract history
    cursor.execute('SELECT * FROM free_agent_contract_history WHERE free_agent_id = ?', (free_agent_id,))
    fa_dict['contract_history'] = [dict(h) for h in cursor.fetchall()]
    
    # Get market value history
    cursor.execute('''
        SELECT * FROM free_agent_market_value_history 
        WHERE free_agent_id = ? 
        ORDER BY year DESC, week DESC 
        LIMIT 52
    ''', (free_agent_id,))
    fa_dict['market_value_history'] = [dict(h) for h in cursor.fetchall()]
    
    return fa_dict


def get_all_free_agents(database, available_only: bool = True, discovered_only: bool = False) -> List[Dict[str, Any]]:
    """Get all free agents with optional filters"""
    cursor = database.conn.cursor()
    
    conditions = []
    if available_only:
        conditions.append('is_signed = 0')
    if discovered_only:
        conditions.append('discovered = 1')
    
    sql = 'SELECT * FROM free_agents'
    if conditions:
        sql += ' WHERE ' + ' AND '.join(conditions)
    sql += ' ORDER BY market_value DESC'
    
    cursor.execute(sql)
    
    free_agents = []
    for row in cursor.fetchall():
        fa_dict = dict(row)
        fa_dict['agent'] = json.loads(fa_dict['agent_data']) if fa_dict.get('agent_data') else {}
        fa_dict['demands'] = json.loads(fa_dict['demands_data']) if fa_dict.get('demands_data') else {}
        
        # Get rival interest
        cursor.execute('SELECT * FROM free_agent_rival_interest WHERE free_agent_id = ?', (fa_dict['id'],))
        fa_dict['rival_interest'] = [dict(r) for r in cursor.fetchall()]
        
        # Get contract history
        cursor.execute('SELECT * FROM free_agent_contract_history WHERE free_agent_id = ?', (fa_dict['id'],))
        fa_dict['contract_history'] = [dict(h) for h in cursor.fetchall()]
        
        free_agents.append(fa_dict)
    
    return free_agents


def get_free_agents_by_visibility(database, max_visibility: int, discovered_only: bool = False) -> List[Dict[str, Any]]:
    """Get free agents up to a certain visibility tier"""
    cursor = database.conn.cursor()
    
    conditions = ['is_signed = 0', 'visibility <= ?']
    params = [max_visibility]
    
    if discovered_only:
        conditions.append('discovered = 1')
    
    sql = f'SELECT * FROM free_agents WHERE {" AND ".join(conditions)} ORDER BY market_value DESC'
    cursor.execute(sql, params)
    
    free_agents = []
    for row in cursor.fetchall():
        fa_dict = dict(row)
        fa_dict['agent'] = json.loads(fa_dict['agent_data']) if fa_dict.get('agent_data') else {}
        fa_dict['demands'] = json.loads(fa_dict['demands_data']) if fa_dict.get('demands_data') else {}
        free_agents.append(fa_dict)
    
    return free_agents


def get_free_agents_by_source(database, source: str) -> List[Dict[str, Any]]:
    """Get free agents by their source type"""
    cursor = database.conn.cursor()
    cursor.execute('''
        SELECT * FROM free_agents 
        WHERE source = ? AND is_signed = 0 
        ORDER BY market_value DESC
    ''', (source,))
    
    free_agents = []
    for row in cursor.fetchall():
        fa_dict = dict(row)
        fa_dict['agent'] = json.loads(fa_dict['agent_data']) if fa_dict.get('agent_data') else {}
        fa_dict['demands'] = json.loads(fa_dict['demands_data']) if fa_dict.get('demands_data') else {}
        free_agents.append(fa_dict)
    
    return free_agents


def mark_free_agent_discovered(database, free_agent_id: str) -> None:
    """Mark a free agent as discovered by the player"""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute('''
        UPDATE free_agents 
        SET discovered = 1, updated_at = ? 
        WHERE id = ?
    ''', (now, free_agent_id))
    
    database.conn.commit()


def mark_free_agent_signed(database, free_agent_id: str, promotion: str, year: int, week: int) -> None:
    """Mark a free agent as signed"""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute('''
        UPDATE free_agents 
        SET is_signed = 1, signed_to_promotion = ?, signed_year = ?, signed_week = ?, updated_at = ?
        WHERE id = ?
    ''', (promotion, year, week, now, free_agent_id))
    
    database.conn.commit()


def save_negotiation_attempt(
    database,
    free_agent_id: str,
    promotion_name: str,
    offer_salary: int,
    offer_length_weeks: int,
    offer_signing_bonus: int,
    accepted: bool,
    rejection_reason: Optional[str],
    negotiation_round: int,
    year: int,
    week: int
) -> None:
    """Record a negotiation attempt"""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT INTO negotiation_history (
            free_agent_id, promotion_name, offer_salary, offer_length_weeks,
            offer_signing_bonus, offer_accepted, rejection_reason,
            negotiation_round, year, week, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        free_agent_id, promotion_name, offer_salary, offer_length_weeks,
        offer_signing_bonus, 1 if accepted else 0, rejection_reason,
        negotiation_round, year, week, now
    ))
    
    database.conn.commit()


def get_negotiation_history(database, free_agent_id: str) -> List[Dict[str, Any]]:
    """Get negotiation history for a free agent"""
    cursor = database.conn.cursor()
    cursor.execute('''
        SELECT * FROM negotiation_history 
        WHERE free_agent_id = ? 
        ORDER BY year DESC, week DESC, negotiation_round DESC
    ''', (free_agent_id,))
    
    return [dict(row) for row in cursor.fetchall()]


def save_scouting_report(
    database,
    free_agent_id: str,
    accuracy: int,
    potential: str,
    concerns: str,
    cost: int,
    year: int,
    week: int
) -> None:
    """Save a scouting report"""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT INTO scouting_reports (
            free_agent_id, scout_accuracy, reported_potential,
            reported_concerns, scouting_cost, year, week, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        free_agent_id, accuracy, potential, concerns, cost, year, week, now
    ))
    
    database.conn.commit()


def get_free_agent_pool_summary(database) -> Dict[str, Any]:
    """Get summary statistics for the free agent pool"""
    cursor = database.conn.cursor()
    
    # Total counts
    cursor.execute('SELECT COUNT(*) as total FROM free_agents WHERE is_signed = 0')
    total = cursor.fetchone()['total']
    
    # By visibility
    cursor.execute('''
        SELECT visibility, COUNT(*) as count 
        FROM free_agents WHERE is_signed = 0 
        GROUP BY visibility
    ''')
    by_visibility = {row['visibility']: row['count'] for row in cursor.fetchall()}
    
    # By source
    cursor.execute('''
        SELECT source, COUNT(*) as count 
        FROM free_agents WHERE is_signed = 0 
        GROUP BY source
    ''')
    by_source = {row['source']: row['count'] for row in cursor.fetchall()}
    
    # Discovered vs undiscovered
    cursor.execute('SELECT COUNT(*) as count FROM free_agents WHERE is_signed = 0 AND discovered = 1')
    discovered = cursor.fetchone()['count']
    
    # Legends available
    cursor.execute('SELECT COUNT(*) as count FROM free_agents WHERE is_signed = 0 AND is_legend = 1')
    legends = cursor.fetchone()['count']
    
    # Controversy cases
    cursor.execute('SELECT COUNT(*) as count FROM free_agents WHERE is_signed = 0 AND has_controversy = 1')
    controversy = cursor.fetchone()['count']
    
    # Average market value
    cursor.execute('SELECT AVG(market_value) as avg FROM free_agents WHERE is_signed = 0')
    avg_value = cursor.fetchone()['avg'] or 0
    
    # Exclusive windows active
    cursor.execute('SELECT COUNT(*) as count FROM free_agents WHERE is_signed = 0 AND exclusive_window_active = 1')
    exclusive_windows = cursor.fetchone()['count']
    
    return {
        'total_available': total,
        'discovered': discovered,
        'undiscovered': total - discovered,
        'by_visibility': by_visibility,
        'by_source': by_source,
        'legends_available': legends,
        'controversy_cases': controversy,
        'average_market_value': int(avg_value),
        'exclusive_windows_active': exclusive_windows
    }


def upgrade_free_agent_tables_step_116_117(database):
    """
    Upgrade free agent tables with STEP 116-117 fields.
    Safe to run multiple times (ALTER TABLE IF NOT EXISTS).
    """
    cursor = database.conn.cursor()
    
    # STEP 116: Market value tracking columns
    new_columns = [
        ('peak_popularity', 'INTEGER DEFAULT 50'),
        ('market_value_trend', 'TEXT DEFAULT "stable"'),
        ('last_value_calculation', 'TEXT'),
        ('average_match_rating', 'REAL DEFAULT 3.0'),
        ('recent_match_rating', 'REAL DEFAULT 3.0'),
        ('five_star_matches', 'INTEGER DEFAULT 0'),
        ('four_plus_matches', 'INTEGER DEFAULT 0'),
        ('injury_history_count', 'INTEGER DEFAULT 0'),
        ('months_since_last_injury', 'INTEGER DEFAULT 12'),
        ('has_chronic_issues', 'INTEGER DEFAULT 0'),
        ('backstage_reputation', 'INTEGER DEFAULT 50'),
        ('locker_room_leader', 'INTEGER DEFAULT 0'),
        ('known_difficult', 'INTEGER DEFAULT 0'),
        # STEP 124: Exclusive window tracking
        ('exclusive_window_active', 'INTEGER DEFAULT 0'),
        ('exclusive_window_holder', 'TEXT'),
        ('exclusive_window_holder_name', 'TEXT'),
        ('exclusive_window_cost_paid', 'INTEGER DEFAULT 0'),
        ('exclusive_window_duration', 'INTEGER DEFAULT 0'),
        ('exclusive_window_started_year', 'INTEGER'),
        ('exclusive_window_started_week', 'INTEGER'),
        ('exclusive_window_expires_year', 'INTEGER'),
        ('exclusive_window_expires_week', 'INTEGER'),
        ('exclusive_window_id', 'TEXT'),
        ('exclusive_window_resulted_in_signing', 'INTEGER DEFAULT 0'),
    ]
    
    for column_name, column_def in new_columns:
        try:
            cursor.execute(f'ALTER TABLE free_agents ADD COLUMN {column_name} {column_def}')
            print(f"  ✅ Added column: {column_name}")
        except sqlite3.OperationalError:
            # Column already exists
            pass
    
    # Create market value history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS free_agent_market_value_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            free_agent_id TEXT NOT NULL,
            year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            value INTEGER NOT NULL,
            reason TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (free_agent_id) REFERENCES free_agents(id)
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_market_value_history_fa 
        ON free_agent_market_value_history(free_agent_id)
    ''')
    
    # STEP 124: Exclusive windows table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exclusive_windows (
            window_id TEXT PRIMARY KEY,
            free_agent_id TEXT NOT NULL,
            promotion_id TEXT NOT NULL DEFAULT 'player',
            promotion_name TEXT NOT NULL,
            cost_paid INTEGER NOT NULL,
            duration_days INTEGER NOT NULL,
            started_year INTEGER NOT NULL,
            started_week INTEGER NOT NULL,
            expires_year INTEGER NOT NULL,
            expires_week INTEGER NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            resulted_in_signing INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            ended_at TEXT,
            FOREIGN KEY (free_agent_id) REFERENCES free_agents(id)
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_exclusive_windows_fa 
        ON exclusive_windows(free_agent_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_exclusive_windows_active 
        ON exclusive_windows(is_active)
    ''')
    
    database.conn.commit()
    print("✅ Free agent tables upgraded (STEP 116-117 + 124)")


# ============================================================================
# STEP 116: Market Value History Helper Functions
# ============================================================================

def save_market_value_history_entry(database, free_agent_id: str, year: int, week: int, value: int, reason: str = "") -> None:
    """Save a market value history entry"""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT INTO free_agent_market_value_history (
            free_agent_id, year, week, value, reason, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
    ''', (free_agent_id, year, week, value, reason, now))
    
    # Keep only last 52 weeks for this free agent
    cursor.execute('''
        DELETE FROM free_agent_market_value_history
        WHERE free_agent_id = ? AND id NOT IN (
            SELECT id FROM free_agent_market_value_history
            WHERE free_agent_id = ?
            ORDER BY year DESC, week DESC
            LIMIT 52
        )
    ''', (free_agent_id, free_agent_id))
    
    database.conn.commit()


def get_market_value_history(database, free_agent_id: str, limit: int = 52) -> List[Dict[str, Any]]:
    """Get market value history for a free agent"""
    cursor = database.conn.cursor()
    cursor.execute('''
        SELECT * FROM free_agent_market_value_history
        WHERE free_agent_id = ?
        ORDER BY year DESC, week DESC
        LIMIT ?
    ''', (free_agent_id, limit))
    
    return [dict(row) for row in cursor.fetchall()]


# ============================================================================
# STEP 124: Exclusive Window Database Operations
# ============================================================================

def save_exclusive_window(database, window_data: Dict[str, Any]) -> None:
    """Save an exclusive negotiating window"""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT OR REPLACE INTO exclusive_windows (
            window_id, free_agent_id, promotion_id, promotion_name,
            cost_paid, duration_days, started_year, started_week,
            expires_year, expires_week, is_active, resulted_in_signing,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        window_data['window_id'],
        window_data['free_agent_id'],
        window_data.get('promotion_id', 'player'),
        window_data['promotion_name'],
        window_data['cost_paid'],
        window_data['duration_days'],
        window_data['started_year'],
        window_data['started_week'],
        window_data['expires_year'],
        window_data['expires_week'],
        1 if window_data.get('is_active', True) else 0,
        1 if window_data.get('resulted_in_signing', False) else 0,
        now
    ))
    
    database.conn.commit()


def end_exclusive_window(database, window_id: str, resulted_in_signing: bool = False) -> None:
    """Mark an exclusive window as ended"""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute('''
        UPDATE exclusive_windows
        SET is_active = 0, resulted_in_signing = ?, ended_at = ?
        WHERE window_id = ?
    ''', (1 if resulted_in_signing else 0, now, window_id))
    
    database.conn.commit()


def get_active_exclusive_windows(database) -> List[Dict[str, Any]]:
    """Get all active exclusive windows"""
    cursor = database.conn.cursor()
    cursor.execute('''
        SELECT * FROM exclusive_windows
        WHERE is_active = 1
        ORDER BY started_year DESC, started_week DESC
    ''')
    
    return [dict(row) for row in cursor.fetchall()]


def get_exclusive_window_by_free_agent(database, free_agent_id: str) -> Optional[Dict[str, Any]]:
    """Get active exclusive window for a specific free agent"""
    cursor = database.conn.cursor()
    cursor.execute('''
        SELECT * FROM exclusive_windows
        WHERE free_agent_id = ? AND is_active = 1
        LIMIT 1
    ''', (free_agent_id,))
    
    row = cursor.fetchone()
    return dict(row) if row else None


def delete_free_agent(database, free_agent_id: str) -> None:
    """Delete a free agent and all related data"""
    cursor = database.conn.cursor()
    
    # Delete related data first
    cursor.execute('DELETE FROM free_agent_rival_interest WHERE free_agent_id = ?', (free_agent_id,))
    cursor.execute('DELETE FROM free_agent_contract_history WHERE free_agent_id = ?', (free_agent_id,))
    cursor.execute('DELETE FROM free_agent_market_value_history WHERE free_agent_id = ?', (free_agent_id,))
    cursor.execute('DELETE FROM negotiation_history WHERE free_agent_id = ?', (free_agent_id,))
    cursor.execute('DELETE FROM scouting_reports WHERE free_agent_id = ?', (free_agent_id,))
    cursor.execute('DELETE FROM exclusive_windows WHERE free_agent_id = ?', (free_agent_id,))
    
    # Delete the free agent
    cursor.execute('DELETE FROM free_agents WHERE id = ?', (free_agent_id,))
    
    database.conn.commit()


def clear_all_free_agents(database) -> None:
    """Clear all free agent data (for testing/reset)"""
    cursor = database.conn.cursor()
    
    cursor.execute('DELETE FROM free_agent_rival_interest')
    cursor.execute('DELETE FROM free_agent_contract_history')
    cursor.execute('DELETE FROM free_agent_market_value_history')
    cursor.execute('DELETE FROM negotiation_history')
    cursor.execute('DELETE FROM scouting_reports')
    cursor.execute('DELETE FROM exclusive_windows')
    cursor.execute('DELETE FROM free_agents')
    
    database.conn.commit()
    print("✅ All free agent data cleared")