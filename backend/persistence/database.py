"""
SQLite Database Layer
Handles all persistence using SQLite with proper schema and relationships.
"""

import sqlite3
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import sys

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
except Exception:
    pass


class Database:
    """
    Main database interface for AWUM.
    Handles all SQLite operations with proper transactions and error handling.
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        self.stats_tracker = None
        
        # Establish persistent connection first
        self.connect()
        
        # Initialize database schema
        self.initialize_database()
        
        # Initialize stats tracker after database is ready
        from persistence.stats_tracker import StatsTracker
        self.stats_tracker = StatsTracker(self)
        
    def connect(self):
        """Establish database connection with row_factory"""
        if self.conn is None:
            self.conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            self.conn.row_factory = sqlite3.Row  # This allows dict(row) to work
            try:
                self.conn.execute('PRAGMA journal_mode=WAL')
            except sqlite3.OperationalError:
                pass
            try:
                self.conn.execute('PRAGMA busy_timeout = 30000')
            except sqlite3.OperationalError:
                pass
        return self.conn
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def initialize_database(self):
        """Create all tables and indexes"""
        cursor = self.conn.cursor()

        def _ensure_column(column_name: str, ddl_suffix: str) -> None:
            """Attempt to add a column for backward compatibility with older DB files."""
            try:
                cursor.execute(f'ALTER TABLE championships ADD COLUMN {column_name} {ddl_suffix}')
                print(f"[OK] Added {column_name} column")
            except sqlite3.OperationalError:
                # Column already exists or cannot be added on this schema version.
                pass
        
        # Game State Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                current_year INTEGER NOT NULL,
                current_week INTEGER NOT NULL,
                current_show_index INTEGER NOT NULL,
                balance INTEGER NOT NULL,
                show_count INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                last_saved TEXT NOT NULL
            );
        ''')
        
        # Wrestlers Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wrestlers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                gender TEXT NOT NULL,
                alignment TEXT NOT NULL,
                role TEXT NOT NULL,
                primary_brand TEXT NOT NULL,
                
                -- Attributes (0-100)
                brawling INTEGER NOT NULL,
                technical INTEGER NOT NULL,
                speed INTEGER NOT NULL,
                mic INTEGER NOT NULL,
                psychology INTEGER NOT NULL,
                stamina INTEGER NOT NULL,
                
                -- Career
                years_experience INTEGER NOT NULL,
                is_major_superstar INTEGER NOT NULL,
                
                -- Dynamic Stats
                popularity INTEGER NOT NULL,
                momentum INTEGER NOT NULL,
                morale INTEGER NOT NULL,
                fatigue INTEGER NOT NULL,
                
                -- Injury
                injury_severity TEXT NOT NULL,
                injury_description TEXT,
                injury_weeks_remaining INTEGER NOT NULL,
                
                -- Contract
                contract_salary INTEGER NOT NULL,
                contract_total_weeks INTEGER NOT NULL,
                contract_weeks_remaining INTEGER NOT NULL,
                contract_signing_year INTEGER NOT NULL,
                contract_signing_week INTEGER NOT NULL,
                
                -- Status
                is_retired INTEGER NOT NULL,
                
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        ''')
        
        # Championships Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS championships (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                assigned_brand TEXT NOT NULL,
                title_type TEXT NOT NULL,
                prestige INTEGER NOT NULL,
                current_holder_id TEXT,
                current_holder_name TEXT,
                interim_holder_id TEXT,
                interim_holder_name TEXT,
                defense_frequency_days INTEGER DEFAULT 30,
                min_annual_defenses INTEGER DEFAULT 12,
                last_defense_year INTEGER,
                last_defense_week INTEGER,
                last_defense_show_id TEXT,
                total_defenses INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (current_holder_id) REFERENCES wrestlers(id)
            );
        ''')

        # For existing databases, add columns if they don't exist
        _ensure_column('defense_frequency_days', 'INTEGER DEFAULT 30')
        _ensure_column('min_annual_defenses', 'INTEGER DEFAULT 12')
        _ensure_column('last_defense_year', 'INTEGER')
        _ensure_column('last_defense_week', 'INTEGER')
        _ensure_column('last_defense_show_id', 'TEXT')
        _ensure_column('total_defenses', 'INTEGER DEFAULT 0')
        
        # Title Reigns Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS title_reigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title_id TEXT NOT NULL,
                wrestler_id TEXT NOT NULL,
                wrestler_name TEXT NOT NULL,
                won_at_show_id TEXT,
                won_at_show_name TEXT NOT NULL,
                won_date_year INTEGER NOT NULL,
                won_date_week INTEGER NOT NULL,
                lost_at_show_id TEXT,
                lost_at_show_name TEXT,
                lost_date_year INTEGER,
                lost_date_week INTEGER,
                days_held INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (title_id) REFERENCES championships(id),
                FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
            );
        ''')
        
        # Feuds Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feuds (
                id TEXT PRIMARY KEY,
                feud_type TEXT NOT NULL,
                participant_ids TEXT NOT NULL,  -- JSON array
                participant_names TEXT NOT NULL,  -- JSON array
                title_id TEXT,
                title_name TEXT,
                intensity INTEGER NOT NULL,
                start_year INTEGER NOT NULL,
                start_week INTEGER NOT NULL,
                start_show_id TEXT,
                last_segment_show_id TEXT,
                last_segment_year INTEGER,
                last_segment_week INTEGER,
                planned_payoff_show_id TEXT,
                planned_payoff_event TEXT,
                status TEXT NOT NULL,
                match_count INTEGER NOT NULL DEFAULT 0,
                wins_by_participant TEXT NOT NULL,  -- JSON object
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (title_id) REFERENCES championships(id)
            );
        ''')
        
        # Feud Segments Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feud_segments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feud_id TEXT NOT NULL,
                show_id TEXT NOT NULL,
                show_name TEXT NOT NULL,
                year INTEGER NOT NULL,
                week INTEGER NOT NULL,
                segment_type TEXT NOT NULL,
                description TEXT NOT NULL,
                intensity_change INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (feud_id) REFERENCES feuds(id)
            );
        ''')
        
        # Match History Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS match_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id TEXT NOT NULL,
                show_id TEXT NOT NULL,
                show_name TEXT NOT NULL,
                year INTEGER NOT NULL,
                week INTEGER NOT NULL,
                
                side_a_ids TEXT NOT NULL,  -- JSON array
                side_a_names TEXT NOT NULL,  -- JSON array
                side_b_ids TEXT NOT NULL,  -- JSON array
                side_b_names TEXT NOT NULL,  -- JSON array
                
                winner TEXT NOT NULL,  -- 'side_a', 'side_b', 'draw'
                finish_type TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL,
                star_rating REAL NOT NULL,
                
                is_title_match INTEGER NOT NULL,
                title_id TEXT,
                title_changed_hands INTEGER NOT NULL,
                
                is_upset INTEGER NOT NULL,
                feud_id TEXT,
                
                match_summary TEXT NOT NULL,
                highlights TEXT NOT NULL,  -- JSON array
                
                created_at TEXT NOT NULL,
                FOREIGN KEY (title_id) REFERENCES championships(id),
                FOREIGN KEY (feud_id) REFERENCES feuds(id)
            );
        ''')
        
        # Show History Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS show_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                show_id TEXT NOT NULL,
                show_name TEXT NOT NULL,
                brand TEXT NOT NULL,
                show_type TEXT NOT NULL,
                year INTEGER NOT NULL,
                week INTEGER NOT NULL,
                
                match_count INTEGER NOT NULL,
                overall_rating REAL NOT NULL,
                total_attendance INTEGER NOT NULL,
                total_revenue INTEGER NOT NULL,
                total_payroll INTEGER NOT NULL,
                net_profit INTEGER NOT NULL,
                
                events TEXT NOT NULL,  -- JSON array
                created_at TEXT NOT NULL
            );
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_wrestlers_brand ON wrestlers(primary_brand)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_wrestlers_retired ON wrestlers(is_retired)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_title_reigns_title ON title_reigns(title_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_feuds_status ON feuds(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_feud_segments_feud ON feud_segments(feud_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_match_history_show ON match_history(show_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_show_history_year_week ON show_history(year, week)')
        
        # Initialize game state if it doesn't exist
        cursor.execute('SELECT COUNT(*) FROM game_state')
        if cursor.fetchone()[0] == 0:
            now = datetime.now().isoformat()
            cursor.execute('''
                INSERT INTO game_state (id, current_year, current_week, current_show_index, balance, show_count, created_at, last_saved)
                VALUES (1, 1, 1, 0, 1000000, 0, ?, ?)
            ''', (now, now))
        
        # Storylines Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS storylines (
                storyline_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                storyline_type TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL,
                triggered_year INTEGER,
                triggered_week INTEGER,
                cast_assignments TEXT,
                completed_beats TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        ''')
        
        # Create stats tracking tables
        self._create_stats_tables()
        self._create_tag_teams_table()
        self._create_factions_table()
        self._create_relationship_tables()
        self._create_wellness_tables()
        self._create_injury_tables()
        self._create_championship_hierarchy_tables()
        self._create_custom_championship_tables()
        self._create_championship_manager_tables()
        self._create_reign_goal_tables()
        self._create_free_agent_tables()
        # STEP 126: Rival Promotion Tables
        self._create_rival_promotion_tables()
        self._create_show_drafts_table()  # STEP 58-72: Booking system
        from persistence.phase_expansion_db import create_phase_expansion_tables
        create_phase_expansion_tables(self)

        # STEP 116-117: Upgrade free agent tables with new fields
        from persistence.free_agent_db import upgrade_free_agent_tables_step_116_117
        upgrade_free_agent_tables_step_116_117(self)
        
        self._create_contract_incentives_table()
        self._create_free_agency_declaration_tables()  # STEP 123
        self.create_contract_promises_table()  # STEP 121
        # ========================================================================
        # STEP 125: Contract Storyline Tables
        # ========================================================================
        
        self._create_character_system_tables()
        self._create_vanguard_development_tables()
        # ========================================================================
        # STEP 125: Contract Storyline Tables
        # ========================================================================

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contract_storylines (
                storyline_id TEXT PRIMARY KEY,
                storyline_type TEXT NOT NULL,
                wrestler_id TEXT NOT NULL,
                wrestler_name TEXT NOT NULL,
                status TEXT NOT NULL,
                trigger_year INTEGER NOT NULL,
                trigger_week INTEGER NOT NULL,
                planned_resolution_show TEXT,
                planned_resolution_week INTEGER,
                current_beat INTEGER DEFAULT 0,
                total_beats INTEGER DEFAULT 4,
                description TEXT,
                weekly_segments TEXT,
                outcome TEXT,
                resolution_details TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
            );
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_contract_storylines_wrestler ON contract_storylines(wrestler_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_contract_storylines_status ON contract_storylines(status)')

        # Update contract_promises table with missing columns if they don't exist
        try:
            cursor.execute('ALTER TABLE contract_promises ADD COLUMN broken INTEGER DEFAULT 0')
            print("[OK] Added 'broken' column to contract_promises")
        except:
            pass  # Column already exists

        try:
            cursor.execute('ALTER TABLE contract_promises ADD COLUMN broken_reason TEXT')
            print("[OK] Added 'broken_reason' column to contract_promises")
        except:
            pass  # Column already exists

        try:
            cursor.execute('ALTER TABLE contract_promises ADD COLUMN morale_penalty_applied INTEGER DEFAULT 0')
            print("[OK] Added 'morale_penalty_applied' column to contract_promises")
        except:
            pass  # Column already exists

        try:
            cursor.execute('ALTER TABLE contract_promises ADD COLUMN wrestler_name TEXT')
            print("[OK] Added 'wrestler_name' column to contract_promises")
        except:
            pass  # Column already exists

        try:
            cursor.execute('ALTER TABLE contract_promises ADD COLUMN fulfillment_details TEXT')
            print("[OK] Added 'fulfillment_details' column to contract_promises")
        except:
            pass  # Column already exists

        self.conn.commit()
        print("[OK] Contract storyline tables created/updated (STEP 125)")

        # ========================================================================
        # STEPS 224-236: Morale Records Table
        # ========================================================================

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS morale_records (
                wrestler_id TEXT PRIMARY KEY,
                wrestler_name TEXT NOT NULL,
                morale_score REAL NOT NULL DEFAULT 50.0,

                -- Component scores (Step 226)
                push_satisfaction REAL NOT NULL DEFAULT 50.0,
                win_loss_satisfaction REAL NOT NULL DEFAULT 50.0,
                championship_satisfaction REAL NOT NULL DEFAULT 50.0,
                match_quality_satisfaction REAL NOT NULL DEFAULT 50.0,
                promo_satisfaction REAL NOT NULL DEFAULT 50.0,
                merch_satisfaction REAL NOT NULL DEFAULT 50.0,
                peer_respect REAL NOT NULL DEFAULT 50.0,
                management_appreciation REAL NOT NULL DEFAULT 50.0,

                -- Momentum (Step 228)
                momentum_value REAL NOT NULL DEFAULT 0.0,
                consecutive_positive INTEGER NOT NULL DEFAULT 0,
                consecutive_negative INTEGER NOT NULL DEFAULT 0,

                -- Hidden factors (Step 227)
                personal_life_stress REAL NOT NULL DEFAULT 0.0,
                culture_fit REAL NOT NULL DEFAULT 0.0,
                unspoken_expectations REAL NOT NULL DEFAULT 0.0,
                career_anxiety REAL NOT NULL DEFAULT 0.0,

                -- Recent events JSON array
                recent_events TEXT NOT NULL DEFAULT '[]',

                -- Appreciation events JSON array (Step 236)
                appreciation_events TEXT NOT NULL DEFAULT '[]',

                -- Tracking
                last_processed_week INTEGER NOT NULL DEFAULT 0,
                last_processed_year INTEGER NOT NULL DEFAULT 1,

                updated_at TEXT NOT NULL DEFAULT (datetime('now')),

                FOREIGN KEY (wrestler_id) REFERENCES wrestlers (id) ON DELETE CASCADE
            );
        ''')

        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_morale_records_score ON morale_records(morale_score)'
        )

        self.conn.commit()
        print("[OK] Morale records table created (Steps 224-236)")

        # STEPS 245-253: Morale Behavior Tables
        self._create_morale_behavior_tables()

        # STEPS 254-259: Morale Recovery Tables
        self._create_recovery_tables()

        # STEPS 260-265: Morale Events Tables
        self._create_morale_events_tables()

        # STEPS 58-72: Show Production Tables
        try:
            from persistence.show_production_db import create_show_production_tables
            create_show_production_tables(self)
        except Exception as _spe:
            try:
                self.conn.rollback()
            except Exception:
                pass
            print(f"[WARN] Could not create show production tables: {_spe}")

        # STEPS 138-148: Venues / Cities (foundation)
        try:
            from persistence.venue_db import create_venue_tables
            create_venue_tables(self)
        except Exception as _vpe:
            try:
                self.conn.rollback()
            except Exception:
                pass
            print(f"[WARN] Could not create venue tables: {_vpe}")

        # STEPS 126-212: TV/media + marketing + staff + industry + ROC Evolve + legacy
        try:
            from persistence.legacy_expansion_db import create_legacy_expansion_tables
            create_legacy_expansion_tables(self)
        except Exception as _lee:
            try:
                self.conn.rollback()
            except Exception:
                pass
            print(f"[WARN] Could not create legacy expansion tables: {_lee}")

        # FEATURES 149-160, 171-182, 243-250: enterprise simulation expansion
        try:
            from persistence.simulation_expansion_db import create_simulation_expansion_tables
            create_simulation_expansion_tables(self)
        except Exception as _see:
            try:
                self.conn.rollback()
            except Exception:
                pass
            print(f"[WARN] Could not create simulation expansion tables: {_see}")
        try:
            from persistence.contract_market_db import create_contract_market_tables
            create_contract_market_tables(self)
        except Exception as _cme:
            try:
                self.conn.rollback()
            except Exception:
                pass
            print(f"[WARN] Could not create contract market tables: {_cme}")

        self.conn.commit()
        print("[OK] SQLite database initialized")
    
    # ========================================================================
    # Game State Operations
    # ========================================================================
    
    def get_game_state(self) -> Dict[str, Any]:
        """Get current game state"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM game_state WHERE id = 1')
        row = cursor.fetchone()
        
        if row is None:
            # Return default state if not found
            return {
                'current_year': 1,
                'current_week': 1,
                'current_show_index': 0,
                'balance': 1000000,
                'show_count': 0,
                'created_at': datetime.now().isoformat(),
                'last_saved': datetime.now().isoformat()
            }
        
        return {
            'current_year': row['current_year'],
            'current_week': row['current_week'],
            'current_show_index': row['current_show_index'],
            'balance': row['balance'],
            'show_count': row['show_count'],
            'current_brand': row['current_brand'] if 'current_brand' in row else 'ROC Alpha',
            'created_at': row['created_at'],
            'last_saved': row['last_saved']
        }
    
    def update_game_state(
        self,
        current_year: int = None,
        current_week: int = None,
        current_show_index: int = None,
        balance: int = None,
        show_count: int = None,
        current_brand: str = None
    ):
        """Update game state fields"""
        cursor = self.conn.cursor()
        
        updates = []
        values = []
        
        if current_year is not None:
            updates.append('current_year = ?')
            values.append(current_year)
        
        if current_week is not None:
            updates.append('current_week = ?')
            values.append(current_week)
        
        if current_show_index is not None:
            updates.append('current_show_index = ?')
            values.append(current_show_index)
        
        if balance is not None:
            updates.append('balance = ?')
            values.append(balance)
        
        if show_count is not None:
            updates.append('show_count = ?')
            values.append(show_count)
        
        if current_brand is not None:
            updates.append('current_brand = ?')
            values.append(current_brand)
        
        updates.append('last_saved = ?')
        values.append(datetime.now().isoformat())
        
        sql = f"UPDATE game_state SET {', '.join(updates)} WHERE id = 1"
        cursor.execute(sql, values)
        self.conn.commit()
    
    
    
    def _create_custom_championship_tables(self):
        """Create custom championship tables (STEP 22)"""
        from persistence.championship_custom_db import create_custom_championship_tables
        create_custom_championship_tables(self)
    
    # ========================================================================
    # Wrestler Operations
    # ========================================================================
    
    def save_wrestler(self, wrestler) -> None:
        """Save or update a wrestler (NO COMMIT - batched)"""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        character_columns = [
            'alignment_percentage', 'gimmick_effectiveness',
            'primary_wrestling_style', 'secondary_wrestling_style',
            'nationality', 'birth_city', 'birth_country',
            'kayfabe_hometown', 'ethnic_background',
        ]
        try:
            existing_character = cursor.execute(
                f"SELECT {', '.join(character_columns)} FROM wrestlers WHERE id = ?",
                (wrestler.id,)
            ).fetchone()
        except sqlite3.OperationalError:
            existing_character = None
        
        cursor.execute('''
            INSERT OR REPLACE INTO wrestlers (
                id, name, age, gender, alignment, role, primary_brand,
                brawling, technical, speed, mic, psychology, stamina,
                years_experience, is_major_superstar,
                popularity, momentum, morale, fatigue,
                injury_severity, injury_description, injury_weeks_remaining,
                contract_salary, contract_total_weeks, contract_weeks_remaining,
                contract_signing_year, contract_signing_week,
                base_salary, current_escalated_salary,
                merchandise_share_percentage, creative_control_level,
                guaranteed_ppv_appearances, has_no_trade_clause,
                has_injury_protection, injury_protection_percentage,
                option_years_remaining, buy_out_penalty,
                restricted_brands, max_appearances_per_year,
                ppv_appearances_this_year, title_reigns_this_contract,
                average_match_rating, total_matches_this_contract,
                is_retired, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            wrestler.id, wrestler.name, wrestler.age, wrestler.gender,
            wrestler.alignment, wrestler.role, wrestler.primary_brand,
            wrestler.brawling, wrestler.technical, wrestler.speed,
            wrestler.mic, wrestler.psychology, wrestler.stamina,
            wrestler.years_experience, 1 if wrestler.is_major_superstar else 0,
            wrestler.popularity, wrestler.momentum, wrestler.morale, wrestler.fatigue,
            wrestler.injury.severity, wrestler.injury.description, wrestler.injury.weeks_remaining,
            wrestler.contract.salary_per_show, wrestler.contract.total_length_weeks,
            wrestler.contract.weeks_remaining, wrestler.contract.signing_year,
            wrestler.contract.signing_week,
            getattr(wrestler.contract, 'base_salary', wrestler.contract.salary_per_show),
            getattr(wrestler.contract, 'current_escalated_salary', wrestler.contract.salary_per_show),
            getattr(wrestler.contract, 'merchandise_share_percentage', 30.0),
            getattr(wrestler.contract, 'creative_control_level', 'none') if isinstance(getattr(wrestler.contract, 'creative_control_level', 'none'), str) else getattr(wrestler.contract, 'creative_control_level').value,
            getattr(wrestler.contract, 'guaranteed_ppv_appearances', 0),
            1 if getattr(wrestler.contract, 'has_no_trade_clause', False) else 0,
            1 if getattr(wrestler.contract, 'has_injury_protection', False) else 0,
            getattr(wrestler.contract, 'injury_protection_percentage', 100.0),
            getattr(wrestler.contract, 'option_years_remaining', 0),
            getattr(wrestler.contract, 'buy_out_penalty', 0),
            json.dumps(getattr(wrestler.contract, 'restricted_brands', [])),
            getattr(wrestler.contract, 'max_appearances_per_year', None),
            getattr(wrestler.contract, 'ppv_appearances_this_year', 0),
            getattr(wrestler.contract, 'title_reigns_this_contract', 0),
            getattr(wrestler.contract, 'average_match_rating', 0.0),
            getattr(wrestler.contract, 'total_matches_this_contract', 0),
            1 if wrestler.is_retired else 0, now, now
        ))

        if existing_character:
            assignments = ', '.join([f'{column} = ?' for column in character_columns])
            cursor.execute(
                f'UPDATE wrestlers SET {assignments} WHERE id = ?',
                [existing_character[column] for column in character_columns] + [wrestler.id]
            )
        
        # STEP 122: Save contract incentives
        if hasattr(wrestler.contract, 'incentives'):
            self.save_contract_incentives(wrestler.id, wrestler.contract.incentives)
    
    def get_all_wrestlers(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all wrestlers as dictionaries"""
        cursor = self.conn.cursor()
        
        if active_only:
            cursor.execute('SELECT * FROM wrestlers WHERE is_retired = 0 ORDER BY name')
        else:
            cursor.execute('SELECT * FROM wrestlers ORDER BY name')
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def get_wrestler_by_id(self, wrestler_id: str) -> Optional[Dict[str, Any]]:
        """Get a single wrestler by ID"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM wrestlers WHERE id = ?', (wrestler_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_wrestlers_by_brand(self, brand: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all wrestlers for a specific brand"""
        cursor = self.conn.cursor()
        
        if active_only:
            cursor.execute(
                'SELECT * FROM wrestlers WHERE primary_brand = ? AND is_retired = 0 ORDER BY name',
                (brand,)
            )
        else:
            cursor.execute(
                'SELECT * FROM wrestlers WHERE primary_brand = ? ORDER BY name',
                (brand,)
            )
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def commit(self):
        """Commit current transaction"""
        if self.conn:
            self.conn.commit()

    # ========================================================================
    # Morale Operations (Steps 224-236)
    # ========================================================================

    def load_morale_record(self, wrestler_id: str):
        """
        Load a morale record from the database.
        Returns a dict suitable for _morale_record_from_dict(), or None if not found.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT * FROM morale_records WHERE wrestler_id = ?',
            (wrestler_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None

        row = dict(row)
        return {
            'wrestler_id':   row['wrestler_id'],
            'wrestler_name': row['wrestler_name'],
            'morale_score':  row['morale_score'],
            'components': {
                'push_satisfaction':          row['push_satisfaction'],
                'win_loss_satisfaction':      row['win_loss_satisfaction'],
                'championship_satisfaction':  row['championship_satisfaction'],
                'match_quality_satisfaction': row['match_quality_satisfaction'],
                'promo_satisfaction':         row['promo_satisfaction'],
                'merch_satisfaction':         row['merch_satisfaction'],
                'peer_respect':               row['peer_respect'],
                'management_appreciation':    row['management_appreciation'],
            },
            'momentum': {
                'value':                row['momentum_value'],
                'consecutive_positive': row['consecutive_positive'],
                'consecutive_negative': row['consecutive_negative'],
            },
            'hidden_factors': {
                'personal_life_stress':  row['personal_life_stress'],
                'culture_fit':           row['culture_fit'],
                'unspoken_expectations': row['unspoken_expectations'],
                'career_anxiety':        row['career_anxiety'],
            },
            'recent_events':       json.loads(row['recent_events']       or '[]'),
            'appreciation_events': json.loads(row['appreciation_events'] or '[]'),
            'last_processed_week': row['last_processed_week'],
            'last_processed_year': row['last_processed_year'],
        }

    def save_morale_record(self, record) -> bool:
        """
        Save or update a WrestlerMoraleRecord to the database.
        Accepts a WrestlerMoraleRecord object from simulation/morale.py.
        """
        now = datetime.now().isoformat()

        # Serialise appreciation events stored on record
        appreciation_data = []
        for e in getattr(record, '_appreciation_events', [])[-20:]:
            appreciation_data.append({
                'event_type':   e.event_type,
                'description':  e.description,
                'morale_boost': e.morale_boost,
                'week':         e.week,
                'year':         e.year,
            })

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO morale_records (
                wrestler_id, wrestler_name, morale_score,
                push_satisfaction, win_loss_satisfaction, championship_satisfaction,
                match_quality_satisfaction, promo_satisfaction, merch_satisfaction,
                peer_respect, management_appreciation,
                momentum_value, consecutive_positive, consecutive_negative,
                personal_life_stress, culture_fit, unspoken_expectations, career_anxiety,
                recent_events, appreciation_events,
                last_processed_week, last_processed_year, updated_at
            ) VALUES (
                ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?,
                ?, ?, ?
            )
            ON CONFLICT(wrestler_id) DO UPDATE SET
                wrestler_name              = excluded.wrestler_name,
                morale_score               = excluded.morale_score,
                push_satisfaction          = excluded.push_satisfaction,
                win_loss_satisfaction      = excluded.win_loss_satisfaction,
                championship_satisfaction  = excluded.championship_satisfaction,
                match_quality_satisfaction = excluded.match_quality_satisfaction,
                promo_satisfaction         = excluded.promo_satisfaction,
                merch_satisfaction         = excluded.merch_satisfaction,
                peer_respect               = excluded.peer_respect,
                management_appreciation    = excluded.management_appreciation,
                momentum_value             = excluded.momentum_value,
                consecutive_positive       = excluded.consecutive_positive,
                consecutive_negative       = excluded.consecutive_negative,
                personal_life_stress       = excluded.personal_life_stress,
                culture_fit                = excluded.culture_fit,
                unspoken_expectations      = excluded.unspoken_expectations,
                career_anxiety             = excluded.career_anxiety,
                recent_events              = excluded.recent_events,
                appreciation_events        = excluded.appreciation_events,
                last_processed_week        = excluded.last_processed_week,
                last_processed_year        = excluded.last_processed_year,
                updated_at                 = excluded.updated_at
        ''', (
            record.wrestler_id,
            record.wrestler_name,
            record.morale_score,
            record.components.push_satisfaction,
            record.components.win_loss_satisfaction,
            record.components.championship_satisfaction,
            record.components.match_quality_satisfaction,
            record.components.promo_satisfaction,
            record.components.merch_satisfaction,
            record.components.peer_respect,
            record.components.management_appreciation,
            record.momentum.value,
            record.momentum.consecutive_positive,
            record.momentum.consecutive_negative,
            record.hidden_factors.personal_life_stress,
            record.hidden_factors.culture_fit,
            record.hidden_factors.unspoken_expectations,
            record.hidden_factors.career_anxiety,
            json.dumps(record.recent_events),
            json.dumps(appreciation_data),
            record.last_processed_week,
            record.last_processed_year,
            now,
        ))
        self.conn.commit()
        return True

    def get_roster_morale_summary(self) -> List[Dict[str, Any]]:
        """
        Morale scores for all active wrestlers, joined from morale_records.
        Falls back to wrestlers.morale for wrestlers not yet in morale_records.
        Used by the morale dashboard.
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT
                w.id, w.name, w.role, w.primary_brand, w.alignment,
                COALESCE(m.morale_score, CAST(w.morale AS REAL)) AS morale_score,
                COALESCE(m.push_satisfaction, 50.0)  AS push_satisfaction,
                COALESCE(m.momentum_value,    0.0)   AS momentum_value
            FROM wrestlers w
            LEFT JOIN morale_records m ON w.id = m.wrestler_id
            WHERE w.is_retired = 0
            ORDER BY morale_score ASC
        ''')
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    
    
    # ========================================================================
    # Championship Operations
    # ========================================================================
    
    
    def save_championship(self, championship) -> None:
        """Save or update a championship - FIXED to save title reigns"""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()

        # Save championship record
        cursor.execute('''
            INSERT OR REPLACE INTO championships (
                id, name, assigned_brand, title_type, prestige,
                current_holder_id, current_holder_name,
                interim_holder_id, interim_holder_name,
                defense_frequency_days, min_annual_defenses,
                last_defense_year, last_defense_week, last_defense_show_id,
                total_defenses,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            championship.id, championship.name, championship.assigned_brand,
            championship.title_type, championship.prestige,
            championship.current_holder_id, championship.current_holder_name,
            getattr(championship, 'interim_holder_id', None),
            getattr(championship, 'interim_holder_name', None),
            getattr(championship, 'defense_frequency_days', 30),
            getattr(championship, 'min_annual_defenses', 12),
            getattr(championship, 'last_defense_year', None),
            getattr(championship, 'last_defense_week', None),
            getattr(championship, 'last_defense_show_id', None),
            getattr(championship, 'total_defenses', 0),
            now, now
        ))
    
        # CRITICAL FIX: Also save title reigns
        # First delete old reigns for this title
        cursor.execute('DELETE FROM title_reigns WHERE title_id = ?', (championship.id,))
    
        # Then insert all current reigns
        for reign in championship.history:
            cursor.execute('''
                INSERT INTO title_reigns (
                    title_id, wrestler_id, wrestler_name,
                    won_at_show_id, won_at_show_name,
                    won_date_year, won_date_week,
                    lost_at_show_id, lost_at_show_name,
                    lost_date_year, lost_date_week,
                    days_held, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                championship.id,
                reign.wrestler_id,
                reign.wrestler_name,
                reign.won_at_show_id,
                reign.won_at_show_name,
                reign.won_date_year,
                reign.won_date_week,
                reign.lost_at_show_id,
                reign.lost_at_show_name,
                reign.lost_date_year,
                reign.lost_date_week,
                reign.days_held,
                now
            ))
    
    
    def get_all_championships(self) -> List[Dict[str, Any]]:
        """Get all championships"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM championships ORDER BY prestige DESC')
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def get_championship_by_id(self, championship_id: str) -> Optional[Dict[str, Any]]:
        """Get a single championship by ID"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM championships WHERE id = ?', (championship_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_championships_by_brand(self, brand: str) -> List[Dict[str, Any]]:
        """Get all championships for a specific brand"""
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT * FROM championships WHERE assigned_brand = ? ORDER BY prestige DESC',
            (brand,)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    # ========================================================================
    # Title Reign Operations
    # ========================================================================
    
    def save_title_reign(self, reign_data: Dict[str, Any]) -> int:
        """Save a new title reign and return the ID"""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO title_reigns (
                title_id, wrestler_id, wrestler_name,
                won_at_show_id, won_at_show_name,
                won_date_year, won_date_week,
                lost_at_show_id, lost_at_show_name,
                lost_date_year, lost_date_week,
                days_held, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            reign_data['title_id'],
            reign_data['wrestler_id'],
            reign_data['wrestler_name'],
            reign_data.get('won_at_show_id'),
            reign_data['won_at_show_name'],
            reign_data['won_date_year'],
            reign_data['won_date_week'],
            reign_data.get('lost_at_show_id'),
            reign_data.get('lost_at_show_name'),
            reign_data.get('lost_date_year'),
            reign_data.get('lost_date_week'),
            reign_data.get('days_held', 0),
            now
        ))
        
        return cursor.lastrowid
    
    def update_title_reign(self, reign_id: int, updates: Dict[str, Any]) -> None:
        """Update an existing title reign"""
        cursor = self.conn.cursor()
        
        set_clauses = []
        values = []
        
        for key, value in updates.items():
            set_clauses.append(f'{key} = ?')
            values.append(value)
        
        values.append(reign_id)
        
        sql = f"UPDATE title_reigns SET {', '.join(set_clauses)} WHERE id = ?"
        cursor.execute(sql, values)
    
    def get_title_reigns(self, title_id: str = None, wrestler_id: str = None, current_only: bool = False) -> List[Dict[str, Any]]:
        """Get title reigns with optional filters"""
        cursor = self.conn.cursor()
        
        conditions = []
        values = []
        
        if title_id:
            conditions.append('title_id = ?')
            values.append(title_id)
        
        if wrestler_id:
            conditions.append('wrestler_id = ?')
            values.append(wrestler_id)
        
        if current_only:
            conditions.append('lost_at_show_id IS NULL')
        
        sql = 'SELECT * FROM title_reigns'
        if conditions:
            sql += ' WHERE ' + ' AND '.join(conditions)
        sql += ' ORDER BY won_date_year DESC, won_date_week DESC'
        
        cursor.execute(sql, values)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    # ========================================================================
    # Feud Operations
    # ========================================================================
    
    def save_feud(self, feud) -> None:
        """Save or update a feud (NO COMMIT - batched)"""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT OR REPLACE INTO feuds (
                id, feud_type, participant_ids, participant_names,
                title_id, title_name, intensity,
                start_year, start_week, start_show_id,
                last_segment_show_id, last_segment_year, last_segment_week,
                planned_payoff_show_id, planned_payoff_event,
                status, match_count, wins_by_participant,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            feud.id, feud.feud_type.value,
            json.dumps(feud.participant_ids), json.dumps(feud.participant_names),
            feud.title_id, feud.title_name, feud.intensity,
            feud.start_year, feud.start_week, feud.start_show_id,
            feud.last_segment_show_id, feud.last_segment_year, feud.last_segment_week,
            feud.planned_payoff_show_id, feud.planned_payoff_event,
            feud.status.value, feud.match_count,
            json.dumps(feud.wins_by_participant),
            now, now
        ))
        
        # Delete old segments and re-insert
        cursor.execute('DELETE FROM feud_segments WHERE feud_id = ?', (feud.id,))
        
        for segment in feud.segments:
            cursor.execute('''
                INSERT INTO feud_segments (
                    feud_id, show_id, show_name, year, week,
                    segment_type, description, intensity_change, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                feud.id, segment.show_id, segment.show_name,
                segment.year, segment.week, segment.segment_type,
                segment.description, segment.intensity_change, now
            ))
    
    def get_all_feuds(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all feuds"""
        cursor = self.conn.cursor()
        
        if active_only:
            cursor.execute('SELECT * FROM feuds WHERE status != "resolved" ORDER BY intensity DESC')
        else:
            cursor.execute('SELECT * FROM feuds ORDER BY created_at DESC')
        
        feuds = []
        for row in cursor.fetchall():
            feud_dict = dict(row)
            
            # Deserialize JSON fields
            feud_dict['participant_ids'] = json.loads(feud_dict['participant_ids'])
            feud_dict['participant_names'] = json.loads(feud_dict['participant_names'])
            feud_dict['wins_by_participant'] = json.loads(feud_dict['wins_by_participant'])
            
            # Get segments
            cursor.execute('SELECT * FROM feud_segments WHERE feud_id = ? ORDER BY created_at', (feud_dict['id'],))
            feud_dict['segments'] = [dict(seg) for seg in cursor.fetchall()]
            
            feuds.append(feud_dict)
        
        return feuds
    
    def get_feud_by_id(self, feud_id: str) -> Optional[Dict[str, Any]]:
        """Get a single feud by ID"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM feuds WHERE id = ?', (feud_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        feud_dict = dict(row)
        
        # Deserialize JSON fields
        feud_dict['participant_ids'] = json.loads(feud_dict['participant_ids'])
        feud_dict['participant_names'] = json.loads(feud_dict['participant_names'])
        feud_dict['wins_by_participant'] = json.loads(feud_dict['wins_by_participant'])
        
        # Get segments
        cursor.execute('SELECT * FROM feud_segments WHERE feud_id = ? ORDER BY created_at', (feud_id,))
        feud_dict['segments'] = [dict(seg) for seg in cursor.fetchall()]
        
        return feud_dict
    
    def delete_feud(self, feud_id: str) -> None:
        """Delete a feud and its segments"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM feud_segments WHERE feud_id = ?', (feud_id,))
        cursor.execute('DELETE FROM feuds WHERE id = ?', (feud_id,))
    
    # ========================================================================
    # Match History Operations
    # ========================================================================
    
    def save_match_result(self, match_result, show_id: str, show_name: str, year: int, week: int) -> None:
        """Save a match result to history (NO COMMIT - batched)"""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO match_history (
                match_id, show_id, show_name, year, week,
                side_a_ids, side_a_names, side_b_ids, side_b_names,
                winner, finish_type, duration_minutes, star_rating,
                is_title_match, title_id, title_changed_hands,
                is_upset, feud_id, match_summary, highlights, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            match_result.match_id, show_id, show_name, year, week,
            json.dumps(match_result.side_a.wrestler_ids),
            json.dumps(match_result.side_a.wrestler_names),
            json.dumps(match_result.side_b.wrestler_ids),
            json.dumps(match_result.side_b.wrestler_names),
            match_result.winner,
            match_result.finish_type.value,
            match_result.duration_minutes,
            match_result.star_rating,
            1 if match_result.is_title_match else 0,
            match_result.title_id if match_result.is_title_match else None,
            1 if match_result.title_changed_hands else 0,
            1 if match_result.is_upset else 0,
            None,
            match_result.match_summary,
            json.dumps([{
                'timestamp': h.timestamp,
                'description': h.description,
                'type': h.highlight_type
            } for h in match_result.highlights]),
            now
        ))
    
    def save_show_result(self, show_result) -> None:
        """Save a complete show result (NO COMMIT - batched)"""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        # Save show to history
        cursor.execute('''
            INSERT INTO show_history (
                show_id, show_name, brand, show_type, year, week,
                match_count, overall_rating,
                total_attendance, total_revenue, total_payroll, net_profit,
                events, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            show_result.show_id,
            show_result.show_name,
            show_result.brand,
            show_result.show_type,
            show_result.year,
            show_result.week,
            len(show_result.match_results),
            show_result.overall_rating,
            show_result.total_attendance,
            show_result.total_revenue,
            show_result.total_payroll,
            show_result.net_profit,
            json.dumps(show_result.events),
            now
        ))
        
        # Save all match results
        for match_result in show_result.match_results:
            self.save_match_result(
                match_result,
                show_result.show_id,
                show_result.show_name,
                show_result.year,
                show_result.week
            )
        
        # Commit everything at once
        self.conn.commit()
    
    def get_show_history(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """Get show history with pagination"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM show_history 
            ORDER BY id DESC 
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        
        shows = []
        for row in cursor.fetchall():
            show_dict = dict(row)
            # Deserialize events JSON
            try:
                show_dict['events'] = json.loads(show_dict['events'])
            except:
                show_dict['events'] = []
            shows.append(show_dict)
        
        return shows
    
    def get_show_by_id(self, show_id: str) -> Optional[Dict[str, Any]]:
        """Get a single show by ID"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM show_history WHERE show_id = ?', (show_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        show_dict = dict(row)
        try:
            show_dict['events'] = json.loads(show_dict['events'])
        except:
            show_dict['events'] = []
        
        return show_dict
    
    def get_match_history(self, wrestler_id: str = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Get match history, optionally filtered by wrestler"""
        cursor = self.conn.cursor()
        
        if wrestler_id:
            # Get matches involving specific wrestler
            cursor.execute('''
                SELECT * FROM match_history 
                WHERE side_a_ids LIKE ? OR side_b_ids LIKE ?
                ORDER BY year DESC, week DESC, id DESC
                LIMIT ?
            ''', (f'%{wrestler_id}%', f'%{wrestler_id}%', limit))
        else:
            cursor.execute('''
                SELECT * FROM match_history 
                ORDER BY year DESC, week DESC, id DESC
                LIMIT ?
            ''', (limit,))
        
        matches = []
        for row in cursor.fetchall():
            match_dict = dict(row)
            match_dict['side_a_ids'] = json.loads(match_dict['side_a_ids'])
            match_dict['side_a_names'] = json.loads(match_dict['side_a_names'])
            match_dict['side_b_ids'] = json.loads(match_dict['side_b_ids'])
            match_dict['side_b_names'] = json.loads(match_dict['side_b_names'])
            match_dict['highlights'] = json.loads(match_dict['highlights'])
            matches.append(match_dict)
        
        return matches
    
    def get_matches_for_show(self, show_id: str) -> List[Dict[str, Any]]:
        """Get all matches for a specific show"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM match_history 
            WHERE show_id = ?
            ORDER BY id
        ''', (show_id,))
        
        matches = []
        for row in cursor.fetchall():
            match_dict = dict(row)
            match_dict['side_a_ids'] = json.loads(match_dict['side_a_ids'])
            match_dict['side_a_names'] = json.loads(match_dict['side_a_names'])
            match_dict['side_b_ids'] = json.loads(match_dict['side_b_ids'])
            match_dict['side_b_names'] = json.loads(match_dict['side_b_names'])
            match_dict['highlights'] = json.loads(match_dict['highlights'])
            matches.append(match_dict)
        
        return matches
    
    # ========================================================================
    # STEP 11: Historical Stats & Milestones
    # ========================================================================
    
    def _create_stats_tables(self):
        """Create stats tracking tables (called during initialize_database)"""
        cursor = self.conn.cursor()
        
        # Wrestler Stats Cache Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wrestler_stats (
                wrestler_id TEXT PRIMARY KEY,
                
                total_matches INTEGER NOT NULL DEFAULT 0,
                wins INTEGER NOT NULL DEFAULT 0,
                losses INTEGER NOT NULL DEFAULT 0,
                draws INTEGER NOT NULL DEFAULT 0,
                
                total_star_rating REAL NOT NULL DEFAULT 0,
                highest_star_rating REAL NOT NULL DEFAULT 0,
                five_star_matches INTEGER NOT NULL DEFAULT 0,
                four_star_plus_matches INTEGER NOT NULL DEFAULT 0,
                
                total_title_reigns INTEGER NOT NULL DEFAULT 0,
                total_days_as_champion INTEGER NOT NULL DEFAULT 0,
                longest_reign_days INTEGER NOT NULL DEFAULT 0,
                
                total_main_events INTEGER NOT NULL DEFAULT 0,
                total_ppv_matches INTEGER NOT NULL DEFAULT 0,
                total_upsets INTEGER NOT NULL DEFAULT 0,
                total_upset_losses INTEGER NOT NULL DEFAULT 0,
                
                clean_wins INTEGER NOT NULL DEFAULT 0,
                cheating_wins INTEGER NOT NULL DEFAULT 0,
                dq_countout_wins INTEGER NOT NULL DEFAULT 0,
                submission_wins INTEGER NOT NULL DEFAULT 0,
                
                current_win_streak INTEGER NOT NULL DEFAULT 0,
                current_loss_streak INTEGER NOT NULL DEFAULT 0,
                longest_win_streak INTEGER NOT NULL DEFAULT 0,
                longest_loss_streak INTEGER NOT NULL DEFAULT 0,
                
                last_updated TEXT NOT NULL,
                
                FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
            );
        ''')
        
        # Milestones Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS milestones (
                id TEXT PRIMARY KEY,
                wrestler_id TEXT NOT NULL,
                milestone_type TEXT NOT NULL,
                description TEXT NOT NULL,
                achieved_at_show_id TEXT NOT NULL,
                achieved_at_show_name TEXT NOT NULL,
                year INTEGER NOT NULL,
                week INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
            );
        ''')
        
        # Indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_milestones_wrestler ON milestones(wrestler_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_milestones_type ON milestones(milestone_type)')
        
        self.conn.commit()
        print("[OK] Stats tracking tables created")
    
    def get_wrestler_stats(self, wrestler_id: str) -> Optional[Dict[str, Any]]:
        """Get cached stats for a wrestler"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM wrestler_stats WHERE wrestler_id = ?', (wrestler_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_all_wrestler_stats(self) -> List[Dict[str, Any]]:
        """Get cached stats for all wrestlers"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM wrestler_stats ORDER BY wins DESC')
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def calculate_wrestler_stats(self, wrestler_id: str) -> Dict[str, Any]:
        """
        Calculate complete statistics for a wrestler from match history.
        This is the source of truth - stats table is just a cache.
        """
        from models.stats import WrestlerStats
        
        cursor = self.conn.cursor()
        
        # Get wrestler name
        cursor.execute('SELECT name FROM wrestlers WHERE id = ?', (wrestler_id,))
        wrestler_row = cursor.fetchone()
        if not wrestler_row:
            return None
        
        wrestler_name = wrestler_row['name']
        stats = WrestlerStats(wrestler_id=wrestler_id, wrestler_name=wrestler_name)
        
        # Get all matches involving this wrestler
        cursor.execute('''
            SELECT * FROM match_history
            WHERE side_a_ids LIKE ? OR side_b_ids LIKE ?
            ORDER BY year, week, id
        ''', (f'%{wrestler_id}%', f'%{wrestler_id}%'))
        
        matches = cursor.fetchall()
        stats.total_matches = len(matches)
        
        if stats.total_matches == 0:
            return stats.to_dict()
        
        current_streak_type = None  # 'win' or 'loss'
        current_streak_count = 0
        
        for match in matches:
            match_dict = dict(match)
            
            # Determine if wrestler was on side A or B
            side_a_ids = json.loads(match_dict['side_a_ids'])
            side_b_ids = json.loads(match_dict['side_b_ids'])
            
            on_side_a = wrestler_id in side_a_ids
            on_side_b = wrestler_id in side_b_ids
            
            if not (on_side_a or on_side_b):
                continue  # Shouldn't happen, but safety check
            
            # Determine win/loss/draw
            winner = match_dict['winner']
            
            if winner == 'draw' or winner == 'no_contest':
                stats.draws += 1
                current_streak_type = None
                current_streak_count = 0
            elif (winner == 'side_a' and on_side_a) or (winner == 'side_b' and on_side_b):
                # WRESTLER WON
                stats.wins += 1
                
                # Finish type breakdown
                finish = match_dict['finish_type']
                if finish in ['clean_pin', 'submission']:
                    if finish == 'submission':
                        stats.submission_wins += 1
                    stats.clean_wins += 1
                elif finish == 'cheating':
                    stats.cheating_wins += 1
                elif finish in ['dq', 'countout']:
                    stats.dq_countout_wins += 1
                
                # Upsets caused
                if match_dict['is_upset']:
                    stats.total_upsets += 1
                
                # Win streak
                if current_streak_type == 'win':
                    current_streak_count += 1
                else:
                    current_streak_type = 'win'
                    current_streak_count = 1
                
                stats.current_win_streak = current_streak_count if current_streak_type == 'win' else 0
                stats.longest_win_streak = max(stats.longest_win_streak, current_streak_count)
                
            else:
                # WRESTLER LOST
                stats.losses += 1
                
                # Upset losses
                if match_dict['is_upset']:
                    stats.total_upset_losses += 1
                
                # Loss streak
                if current_streak_type == 'loss':
                    current_streak_count += 1
                else:
                    current_streak_type = 'loss'
                    current_streak_count = 1
                
                stats.current_loss_streak = current_streak_count if current_streak_type == 'loss' else 0
                stats.longest_loss_streak = max(stats.longest_loss_streak, current_streak_count)
            
            # Star rating stats
            star_rating = match_dict['star_rating']
            stats.total_star_rating += star_rating
            stats.highest_star_rating = max(stats.highest_star_rating, star_rating)
            
            if star_rating >= 5.0:
                stats.five_star_matches += 1
            if star_rating >= 4.0:
                stats.four_star_plus_matches += 1
            
            # Main event tracking (card_position would need to be added to match_history)
            # For now, assume title matches are main events
            if match_dict['is_title_match']:
                stats.total_main_events += 1
            
            # PPV tracking (show_type would need to be joined from show_history)
            cursor.execute('SELECT show_type FROM show_history WHERE show_id = ?', (match_dict['show_id'],))
            show_row = cursor.fetchone()
            if show_row and show_row['show_type'] in ['ppv', 'major_ppv']:
                stats.total_ppv_matches += 1
        
        # Calculate averages
        if stats.total_matches > 0:
            stats.win_percentage = (stats.wins / stats.total_matches) * 100
            stats.average_star_rating = stats.total_star_rating / stats.total_matches
        
        # Get title reign stats
        cursor.execute('''
            SELECT COUNT(*) as reign_count, 
                   SUM(days_held) as total_days,
                   MAX(days_held) as longest_reign
            FROM title_reigns
            WHERE wrestler_id = ?
        ''', (wrestler_id,))
        
        title_row = cursor.fetchone()
        if title_row:
            stats.total_title_reigns = title_row['reign_count'] or 0
            stats.total_days_as_champion = title_row['total_days'] or 0
            stats.longest_reign_days = title_row['longest_reign'] or 0
        
        # Check for current reign
        cursor.execute('''
            SELECT days_held FROM title_reigns
            WHERE wrestler_id = ? AND lost_at_show_id IS NULL
            ORDER BY won_date_year DESC, won_date_week DESC
            LIMIT 1
        ''', (wrestler_id,))
        
        current_reign = cursor.fetchone()
        if current_reign:
            stats.current_title_reign_days = current_reign['days_held']
        
        return stats.to_dict()
    
    def update_wrestler_stats_cache(self, wrestler_id: str):
        """Update the cached stats for a wrestler (NO COMMIT - batched)"""
        stats_dict = self.calculate_wrestler_stats(wrestler_id)
        
        if not stats_dict:
            return
        
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT OR REPLACE INTO wrestler_stats (
                wrestler_id, total_matches, wins, losses, draws,
                total_star_rating, highest_star_rating,
                five_star_matches, four_star_plus_matches,
                total_title_reigns, total_days_as_champion, longest_reign_days,
                total_main_events, total_ppv_matches,
                total_upsets, total_upset_losses,
                clean_wins, cheating_wins, dq_countout_wins, submission_wins,
                current_win_streak, current_loss_streak,
                longest_win_streak, longest_loss_streak,
                last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            wrestler_id,
            stats_dict['record']['total_matches'],
            stats_dict['record']['wins'],
            stats_dict['record']['losses'],
            stats_dict['record']['draws'],
            stats_dict['match_quality']['average_star_rating'] * stats_dict['record']['total_matches'],
            stats_dict['match_quality']['highest_star_rating'],
            stats_dict['match_quality']['five_star_matches'],
            stats_dict['match_quality']['four_star_plus_matches'],
            stats_dict['title_history']['total_reigns'],
            stats_dict['title_history']['total_days'],
            stats_dict['title_history']['longest_reign_days'],
            stats_dict['achievements']['main_events'],
            stats_dict['achievements']['ppv_matches'],
            stats_dict['achievements']['upsets_caused'],
            stats_dict['achievements']['upset_losses'],
            stats_dict['finish_breakdown']['clean_wins'],
            stats_dict['finish_breakdown']['cheating_wins'],
            stats_dict['finish_breakdown']['dq_countout_wins'],
            stats_dict['finish_breakdown']['submission_wins'],
            stats_dict['streaks']['current_win_streak'],
            stats_dict['streaks']['current_loss_streak'],
            stats_dict['streaks']['longest_win_streak'],
            stats_dict['streaks']['longest_loss_streak'],
            now
        ))
    
    def record_milestone(
        self,
        wrestler_id: str,
        wrestler_name: str,
        milestone_type: str,
        description: str,
        show_id: str,
        show_name: str,
        year: int,
        week: int
    ):
        """Record a milestone achievement (NO COMMIT - batched)"""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        milestone_id = f"milestone_{wrestler_id}_{milestone_type}_{year}_{week}"
        
        cursor.execute('''
            INSERT OR IGNORE INTO milestones (
                id, wrestler_id, milestone_type, description,
                achieved_at_show_id, achieved_at_show_name,
                year, week, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            milestone_id, wrestler_id, milestone_type, description,
            show_id, show_name, year, week, now
        ))
    
    def get_wrestler_milestones(self, wrestler_id: str) -> List[Dict[str, Any]]:
        """Get all milestones for a wrestler"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM milestones
            WHERE wrestler_id = ?
            ORDER BY year DESC, week DESC
        ''', (wrestler_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_recent_milestones(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent milestones across all wrestlers"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT m.*, w.name as wrestler_name
            FROM milestones m
            JOIN wrestlers w ON m.wrestler_id = w.id
            ORDER BY m.year DESC, m.week DESC
            LIMIT ?
        ''', (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_promotion_records(self) -> Dict[str, Any]:
        """Calculate promotion-wide records"""
        from models.stats import PromotionRecords
        
        cursor = self.conn.cursor()
        records = PromotionRecords()
        
        # Highest rated match
        cursor.execute('''
            SELECT m.*, w1.name as side_a_name, w2.name as side_b_name
            FROM match_history m
            LEFT JOIN wrestlers w1 ON json_extract(m.side_a_ids, '$[0]') = w1.id
            LEFT JOIN wrestlers w2 ON json_extract(m.side_b_ids, '$[0]') = w2.id
            ORDER BY star_rating DESC
            LIMIT 1
        ''')
        
        match_row = cursor.fetchone()
        if match_row:
            records.highest_rated_match = {
                'participants': f"{match_row['side_a_name']} vs {match_row['side_b_name']}",
                'star_rating': match_row['star_rating'],
                'show_name': match_row['show_name'],
                'year': match_row['year'],
                'week': match_row['week']
            }
        
        # Best win percentage (min 10 matches)
        cursor.execute('''
            SELECT ws.*, w.name
            FROM wrestler_stats ws
            JOIN wrestlers w ON ws.wrestler_id = w.id
            WHERE ws.total_matches >= 10
            ORDER BY (CAST(ws.wins AS FLOAT) / ws.total_matches) DESC
            LIMIT 1
        ''')
        
        win_pct_row = cursor.fetchone()
        if win_pct_row:
            win_pct = (win_pct_row['wins'] / win_pct_row['total_matches']) * 100
            records.best_win_percentage = {
                'wrestler_name': win_pct_row['name'],
                'win_percentage': round(win_pct, 1),
                'record': f"{win_pct_row['wins']}-{win_pct_row['losses']}"
            }
        
        # Longest title reign
        cursor.execute('''
            SELECT tr.*, w.name as wrestler_name, c.name as title_name
            FROM title_reigns tr
            JOIN wrestlers w ON tr.wrestler_id = w.id
            JOIN championships c ON tr.title_id = c.id
            ORDER BY days_held DESC
            LIMIT 1
        ''')
        
        reign_row = cursor.fetchone()
        if reign_row:
            records.longest_title_reign = {
                'wrestler_name': reign_row['wrestler_name'],
                'title_name': reign_row['title_name'],
                'days_held': reign_row['days_held']
            }
        
        # Most title reigns
        cursor.execute('''
            SELECT wrestler_id, COUNT(*) as reign_count, w.name
            FROM title_reigns tr
            JOIN wrestlers w ON tr.wrestler_id = w.id
            GROUP BY wrestler_id
            ORDER BY reign_count DESC
            LIMIT 1
        ''')
        
        reigns_row = cursor.fetchone()
        if reigns_row:
            records.most_title_reigns = {
                'wrestler_name': reigns_row['name'],
                'total_reigns': reigns_row['reign_count']
            }
        
        # Longest winning streak
        cursor.execute('''
            SELECT ws.*, w.name
            FROM wrestler_stats ws
            JOIN wrestlers w ON ws.wrestler_id = w.id
            ORDER BY longest_win_streak DESC
            LIMIT 1
        ''')
        
        streak_row = cursor.fetchone()
        if streak_row:
            records.longest_winning_streak = {
                'wrestler_name': streak_row['name'],
                'streak_length': streak_row['longest_win_streak']
            }
        
        # Highest rated show
        cursor.execute('''
            SELECT * FROM show_history
            ORDER BY overall_rating DESC
            LIMIT 1
        ''')
        
        show_row = cursor.fetchone()
        if show_row:
            records.highest_rated_show = {
                'show_name': show_row['show_name'],
                'rating': show_row['overall_rating'],
                'year': show_row['year'],
                'week': show_row['week']
            }
        
        # Highest attendance
        cursor.execute('''
            SELECT * FROM show_history
            ORDER BY total_attendance DESC
            LIMIT 1
        ''')
        
        attendance_row = cursor.fetchone()
        if attendance_row:
            records.highest_attendance = {
                'show_name': attendance_row['show_name'],
                'attendance': attendance_row['total_attendance'],
                'year': attendance_row['year'],
                'week': attendance_row['week']
            }
        
        return records.to_dict()
    
    # ========================================================================
    # Tag Teams
    # ========================================================================
    
    def _create_tag_teams_table(self):
        """Create tag teams table"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tag_teams (
                team_id TEXT PRIMARY KEY,
                team_name TEXT NOT NULL,
                member_ids TEXT NOT NULL,
                member_names TEXT NOT NULL,
                primary_brand TEXT NOT NULL,
                formation_date_year INTEGER NOT NULL,
                formation_date_week INTEGER NOT NULL,
                chemistry INTEGER NOT NULL DEFAULT 50,
                experience_weeks INTEGER NOT NULL DEFAULT 0,
                team_identity TEXT DEFAULT '',
                entrance_style TEXT DEFAULT 'standard',
                signature_double_team TEXT,
                manager_id TEXT,
                manager_name TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                is_disbanded INTEGER NOT NULL DEFAULT 0,
                total_title_reigns INTEGER NOT NULL DEFAULT 0,
                total_days_as_champions INTEGER NOT NULL DEFAULT 0,
                team_wins INTEGER NOT NULL DEFAULT 0,
                team_losses INTEGER NOT NULL DEFAULT 0,
                team_draws INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tag_teams_brand ON tag_teams(primary_brand)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tag_teams_active ON tag_teams(is_active)')

        for statement in [
            "ALTER TABLE tag_teams ADD COLUMN experience_weeks INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE tag_teams ADD COLUMN team_identity TEXT DEFAULT ''",
            "ALTER TABLE tag_teams ADD COLUMN entrance_style TEXT DEFAULT 'standard'",
            "ALTER TABLE tag_teams ADD COLUMN signature_double_team TEXT",
            "ALTER TABLE tag_teams ADD COLUMN manager_id TEXT",
            "ALTER TABLE tag_teams ADD COLUMN manager_name TEXT",
        ]:
            try:
                cursor.execute(statement)
            except:
                pass
        
        self.conn.commit()
        print("[OK] Tag teams table created")
    
    def save_tag_team(self, tag_team) -> None:
        """Save or update a tag team (NO COMMIT - batched)"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO tag_teams (
                team_id, team_name, member_ids, member_names,
                primary_brand, formation_date_year, formation_date_week,
                chemistry, experience_weeks, team_identity, entrance_style,
                signature_double_team, manager_id, manager_name,
                is_active, is_disbanded,
                total_title_reigns, total_days_as_champions,
                team_wins, team_losses, team_draws,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            tag_team.team_id,
            tag_team.team_name,
            json.dumps(tag_team.member_ids),
            json.dumps(tag_team.member_names),
            tag_team.primary_brand,
            tag_team.formation_date_year,
            tag_team.formation_date_week,
            tag_team.chemistry,
            getattr(tag_team, 'experience_weeks', 0),
            getattr(tag_team, 'team_identity', ''),
            getattr(tag_team, 'entrance_style', 'standard'),
            getattr(tag_team, 'signature_double_team', None),
            getattr(tag_team, 'manager_id', None),
            getattr(tag_team, 'manager_name', None),
            1 if tag_team.is_active else 0,
            1 if tag_team.is_disbanded else 0,
            tag_team.total_title_reigns,
            tag_team.total_days_as_champions,
            tag_team.team_wins,
            tag_team.team_losses,
            tag_team.team_draws,
            tag_team.created_at,
            tag_team.updated_at
        ))
    
    def get_all_tag_teams(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all tag teams"""
        cursor = self.conn.cursor()
        
        if active_only:
            cursor.execute('SELECT * FROM tag_teams WHERE is_active = 1 AND is_disbanded = 0 ORDER BY team_name')
        else:
            cursor.execute('SELECT * FROM tag_teams ORDER BY team_name')
        
        teams = []
        for row in cursor.fetchall():
            team_dict = dict(row)
            team_dict['member_ids'] = json.loads(team_dict['member_ids'])
            team_dict['member_names'] = json.loads(team_dict['member_names'])
            teams.append(team_dict)
        
        return teams
    
    def get_tag_team_by_id(self, team_id: str) -> Optional[Dict[str, Any]]:
        """Get tag team by ID"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM tag_teams WHERE team_id = ?', (team_id,))
        row = cursor.fetchone()
        
        if row:
            team_dict = dict(row)
            team_dict['member_ids'] = json.loads(team_dict['member_ids'])
            team_dict['member_names'] = json.loads(team_dict['member_names'])
            return team_dict
        
        return None
    
    def get_tag_teams_by_brand(self, brand: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all tag teams for a specific brand"""
        cursor = self.conn.cursor()
        
        if active_only:
            cursor.execute(
                'SELECT * FROM tag_teams WHERE primary_brand = ? AND is_active = 1 AND is_disbanded = 0 ORDER BY team_name',
                (brand,)
            )
        else:
            cursor.execute(
                'SELECT * FROM tag_teams WHERE primary_brand = ? ORDER BY team_name',
                (brand,)
            )
        
        teams = []
        for row in cursor.fetchall():
            team_dict = dict(row)
            team_dict['member_ids'] = json.loads(team_dict['member_ids'])
            team_dict['member_names'] = json.loads(team_dict['member_names'])
            teams.append(team_dict)
        
        return teams
    
    def delete_tag_team(self, team_id: str) -> None:
        """Delete a tag team"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM tag_teams WHERE team_id = ?', (team_id,))

    def _create_factions_table(self):
        """Create faction and stable table."""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS factions (
                faction_id TEXT PRIMARY KEY,
                faction_name TEXT NOT NULL,
                member_ids TEXT NOT NULL,
                member_names TEXT NOT NULL,
                leader_id TEXT NOT NULL,
                leader_name TEXT NOT NULL,
                primary_brand TEXT NOT NULL,
                identity TEXT DEFAULT '',
                goals TEXT NOT NULL DEFAULT '[]',
                hierarchy TEXT NOT NULL DEFAULT '[]',
                dynamics TEXT NOT NULL DEFAULT '{}',
                entrance_style TEXT DEFAULT 'standard',
                manager_id TEXT,
                manager_name TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                is_disbanded INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_factions_brand ON factions(primary_brand)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_factions_active ON factions(is_active)')
        self.conn.commit()

    def save_faction(self, faction) -> None:
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO factions (
                faction_id, faction_name, member_ids, member_names,
                leader_id, leader_name, primary_brand, identity,
                goals, hierarchy, dynamics, entrance_style,
                manager_id, manager_name, is_active, is_disbanded,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            faction.faction_id,
            faction.faction_name,
            json.dumps(faction.member_ids),
            json.dumps(faction.member_names),
            faction.leader_id,
            faction.leader_name,
            faction.primary_brand,
            faction.identity,
            json.dumps(faction.goals),
            json.dumps(faction.hierarchy),
            json.dumps(faction.dynamics),
            faction.entrance_style,
            faction.manager_id,
            faction.manager_name,
            1 if faction.is_active else 0,
            1 if faction.is_disbanded else 0,
            faction.created_at,
            faction.updated_at,
        ))

    def get_all_factions(self, active_only: bool = True) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        if active_only:
            cursor.execute('SELECT * FROM factions WHERE is_active = 1 AND is_disbanded = 0 ORDER BY faction_name')
        else:
            cursor.execute('SELECT * FROM factions ORDER BY faction_name')

        factions = []
        for row in cursor.fetchall():
            faction = dict(row)
            faction['member_ids'] = json.loads(faction['member_ids'] or '[]')
            faction['member_names'] = json.loads(faction['member_names'] or '[]')
            faction['goals'] = json.loads(faction['goals'] or '[]')
            faction['hierarchy'] = json.loads(faction['hierarchy'] or '[]')
            faction['dynamics'] = json.loads(faction['dynamics'] or '{}')
            factions.append(faction)
        return factions

    def get_faction_by_id(self, faction_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM factions WHERE faction_id = ?', (faction_id,))
        row = cursor.fetchone()
        if not row:
            return None
        faction = dict(row)
        faction['member_ids'] = json.loads(faction['member_ids'] or '[]')
        faction['member_names'] = json.loads(faction['member_names'] or '[]')
        faction['goals'] = json.loads(faction['goals'] or '[]')
        faction['hierarchy'] = json.loads(faction['hierarchy'] or '[]')
        faction['dynamics'] = json.loads(faction['dynamics'] or '{}')
        return faction

    def _create_relationship_tables(self):
        """Create locker-room relationship table."""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS locker_room_relationships (
                relationship_id TEXT PRIMARY KEY,
                wrestler_a_id TEXT NOT NULL,
                wrestler_a_name TEXT NOT NULL,
                wrestler_b_id TEXT NOT NULL,
                wrestler_b_name TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                strength INTEGER NOT NULL DEFAULT 50,
                metadata TEXT NOT NULL DEFAULT '{}',
                history TEXT NOT NULL DEFAULT '[]',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_relationships_a ON locker_room_relationships(wrestler_a_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_relationships_b ON locker_room_relationships(wrestler_b_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_relationships_type ON locker_room_relationships(relationship_type)')
        self.conn.commit()

    def save_relationship(self, relationship) -> None:
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO locker_room_relationships (
                relationship_id, wrestler_a_id, wrestler_a_name, wrestler_b_id, wrestler_b_name,
                relationship_type, strength, metadata, history, is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            relationship.relationship_id,
            relationship.wrestler_a_id,
            relationship.wrestler_a_name,
            relationship.wrestler_b_id,
            relationship.wrestler_b_name,
            relationship.relationship_type,
            relationship.strength,
            json.dumps(relationship.metadata),
            json.dumps(relationship.history),
            1 if relationship.is_active else 0,
            relationship.created_at,
            relationship.updated_at,
        ))

    def get_all_relationships(self, active_only: bool = True) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        if active_only:
            cursor.execute('SELECT * FROM locker_room_relationships WHERE is_active = 1 ORDER BY relationship_type, strength DESC')
        else:
            cursor.execute('SELECT * FROM locker_room_relationships ORDER BY relationship_type, strength DESC')

        relationships = []
        for row in cursor.fetchall():
            relationship = dict(row)
            relationship['metadata'] = json.loads(relationship['metadata'] or '{}')
            relationship['history'] = json.loads(relationship['history'] or '[]')
            relationships.append(relationship)
        return relationships

    def get_relationships_for_wrestler(self, wrestler_id: str, relationship_type: Optional[str] = None) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        if relationship_type:
            cursor.execute(
                '''
                SELECT * FROM locker_room_relationships
                WHERE is_active = 1 AND relationship_type = ?
                AND (wrestler_a_id = ? OR wrestler_b_id = ?)
                ORDER BY strength DESC
                ''',
                (relationship_type, wrestler_id, wrestler_id)
            )
        else:
            cursor.execute(
                '''
                SELECT * FROM locker_room_relationships
                WHERE is_active = 1 AND (wrestler_a_id = ? OR wrestler_b_id = ?)
                ORDER BY relationship_type, strength DESC
                ''',
                (wrestler_id, wrestler_id)
            )

        relationships = []
        for row in cursor.fetchall():
            relationship = dict(row)
            relationship['metadata'] = json.loads(relationship['metadata'] or '{}')
            relationship['history'] = json.loads(relationship['history'] or '[]')
            relationships.append(relationship)
        return relationships

    def _create_wellness_tables(self):
        """Create wellness policy and violation tables."""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wellness_policy (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                policy_name TEXT NOT NULL,
                testing_frequency_weeks INTEGER NOT NULL DEFAULT 4,
                strictness INTEGER NOT NULL DEFAULT 60,
                suspension_weeks_minor INTEGER NOT NULL DEFAULT 1,
                suspension_weeks_major INTEGER NOT NULL DEFAULT 4,
                rehab_focus INTEGER NOT NULL DEFAULT 60,
                notes TEXT DEFAULT '',
                updated_at TEXT NOT NULL
            );
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wellness_violations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wrestler_id TEXT NOT NULL,
                wrestler_name TEXT NOT NULL,
                violation_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                year INTEGER NOT NULL,
                week INTEGER NOT NULL,
                suspension_weeks INTEGER NOT NULL DEFAULT 0,
                notes TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );
        ''')
        cursor.execute('SELECT COUNT(*) FROM wellness_policy')
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                '''
                INSERT INTO wellness_policy (
                    id, policy_name, testing_frequency_weeks, strictness,
                    suspension_weeks_minor, suspension_weeks_major, rehab_focus,
                    notes, updated_at
                ) VALUES (1, ?, 4, 60, 1, 4, 60, ?, ?)
                ''',
                ("Standard Wellness Program", "Balanced testing and recovery support.", datetime.now().isoformat())
            )
        self.conn.commit()

    def get_wellness_policy(self) -> Dict[str, Any]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM wellness_policy WHERE id = 1')
        row = cursor.fetchone()
        return dict(row) if row else {}

    def save_wellness_policy(self, policy_data: Dict[str, Any]) -> None:
        current = self.get_wellness_policy()
        merged = {**current, **policy_data}
        merged['updated_at'] = datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute(
            '''
            INSERT OR REPLACE INTO wellness_policy (
                id, policy_name, testing_frequency_weeks, strictness,
                suspension_weeks_minor, suspension_weeks_major, rehab_focus,
                notes, updated_at
            ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                merged.get('policy_name', 'Standard Wellness Program'),
                merged.get('testing_frequency_weeks', 4),
                merged.get('strictness', 60),
                merged.get('suspension_weeks_minor', 1),
                merged.get('suspension_weeks_major', 4),
                merged.get('rehab_focus', 60),
                merged.get('notes', ''),
                merged['updated_at'],
            )
        )

    def record_wellness_violation(self, violation_data: Dict[str, Any]) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            '''
            INSERT INTO wellness_violations (
                wrestler_id, wrestler_name, violation_type, severity,
                year, week, suspension_weeks, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                violation_data['wrestler_id'],
                violation_data['wrestler_name'],
                violation_data.get('violation_type', 'wellness_violation'),
                violation_data.get('severity', 'minor'),
                violation_data['year'],
                violation_data['week'],
                violation_data.get('suspension_weeks', 0),
                violation_data.get('notes', ''),
                datetime.now().isoformat(),
            )
        )
        return cursor.lastrowid

    def get_wellness_violations(self, wrestler_id: Optional[str] = None) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        if wrestler_id:
            cursor.execute('SELECT * FROM wellness_violations WHERE wrestler_id = ? ORDER BY year DESC, week DESC, id DESC', (wrestler_id,))
        else:
            cursor.execute('SELECT * FROM wellness_violations ORDER BY year DESC, week DESC, id DESC')
        return [dict(row) for row in cursor.fetchall()]
    
    # ========================================================================
    # Storyline Operations (STEP 16)
    # ========================================================================
    
    def save_storyline_state(self, storyline_data: Dict[str, Any]):
        """Save storyline engine state"""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        # Clear existing storylines
        cursor.execute('DELETE FROM storylines')
        
        # Save active storylines
        for storyline in storyline_data.get('active_storylines', []):
            cursor.execute('''
                INSERT INTO storylines (
                    storyline_id, name, storyline_type, description,
                    status, triggered_year, triggered_week,
                    cast_assignments, completed_beats,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                storyline['storyline_id'],
                storyline['name'],
                storyline['storyline_type'],
                storyline['description'],
                storyline['status'],
                storyline.get('triggered_year'),
                storyline.get('triggered_week'),
                json.dumps(storyline.get('cast_assignments', {})),
                json.dumps(storyline.get('completed_beats', [])),
                now, now
            ))
        
        # Save completed storylines
        for storyline in storyline_data.get('completed_storylines', []):
            cursor.execute('''
                INSERT INTO storylines (
                    storyline_id, name, storyline_type, description,
                    status, triggered_year, triggered_week,
                    cast_assignments, completed_beats,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                storyline['storyline_id'],
                storyline['name'],
                storyline['storyline_type'],
                storyline['description'],
                'completed',
                storyline.get('triggered_year'),
                storyline.get('triggered_week'),
                json.dumps(storyline.get('cast_assignments', {})),
                json.dumps(storyline.get('completed_beats', [])),
                now, now
            ))
        
        self.conn.commit()
    
    def load_storyline_state(self) -> Dict[str, Any]:
        """Load storyline engine state"""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT * FROM storylines')
        rows = cursor.fetchall()
        
        active_storylines = []
        completed_storylines = []
        
        for row in rows:
            storyline_dict = dict(row)
            
            # Parse JSON fields
            storyline_dict['cast_assignments'] = json.loads(storyline_dict['cast_assignments'] or '{}')
            storyline_dict['completed_beats'] = json.loads(storyline_dict['completed_beats'] or '[]')
            
            # Remove database fields
            if 'created_at' in storyline_dict:
                del storyline_dict['created_at']
            if 'updated_at' in storyline_dict:
                del storyline_dict['updated_at']
            
            if storyline_dict['status'] == 'completed':
                completed_storylines.append(storyline_dict)
            else:
                active_storylines.append(storyline_dict)
        
        return {
            'active_storylines': active_storylines,
            'completed_storylines': completed_storylines
        }
    
    # ========================================================================
    # STEP 21: Championship Hierarchy Tables
    # ========================================================================
    
    def _create_championship_hierarchy_tables(self):
        """Create championship hierarchy tables (STEP 21 + STEP 25)"""
        from persistence.championship_db import create_championship_tables
        create_championship_tables(self)
    
        # STEP 25: Add defense frequency columns
        cursor = self.conn.cursor()
        try:
            cursor.execute('ALTER TABLE championships ADD COLUMN defense_frequency_days INTEGER DEFAULT 30')
            cursor.execute('ALTER TABLE championships ADD COLUMN min_annual_defenses INTEGER DEFAULT 12')
            # BUGFIX #3: Add defense tracking columns
            cursor.execute('ALTER TABLE championships ADD COLUMN last_defense_year INTEGER')
            cursor.execute('ALTER TABLE championships ADD COLUMN last_defense_week INTEGER')
            cursor.execute('ALTER TABLE championships ADD COLUMN last_defense_show_id TEXT')
            cursor.execute('ALTER TABLE championships ADD COLUMN total_defenses INTEGER DEFAULT 0')
            print("[OK] Added defense frequency and tracking columns to championships table")
        except:
            pass  # Columns already exist
    
        self.conn.commit()

    def _create_championship_manager_tables(self):
        """Create championship manager tables (STEP 22)"""
        from persistence.championship_manager_db import create_championship_manager_tables
        create_championship_manager_tables(self)
    

    def _create_reign_goal_tables(self):
        """Create reign goal tracking tables (STEP 30)"""
        from persistence.reign_goal_db import create_reign_goal_tables
        create_reign_goal_tables(self)
    
    # ========================================================================
    # Injury System Tables (STEP 20)
    # ========================================================================
    
    def _create_injury_tables(self):
        """Create injury and rehabilitation tables (STEP 20)"""
        from persistence.injury_db import create_injury_tables
        create_injury_tables(self)
    
    # ========================================================================
    # Free Agent Tables (STEP 113)
    # ========================================================================
    
    def _create_free_agent_tables(self):
        """Create free agent pool tables (STEP 113)"""
        from persistence.free_agent_db import create_free_agent_tables
        create_free_agent_tables(self)
    

    def _create_rival_promotion_tables(self):
        """Create rival promotion tables (STEP 126)"""
        from persistence.rival_promotion_db import create_rival_promotion_tables
        create_rival_promotion_tables(self)
        
    # ========================================================================
    # STEP 122: Contract Incentives Tables
    # ========================================================================
    
    def _create_contract_incentives_table(self):
        """Create contract incentives table (STEP 122)"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contract_incentives (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wrestler_id TEXT NOT NULL,
                incentive_type TEXT NOT NULL,
                description TEXT NOT NULL,
                value TEXT NOT NULL,
                conditions TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                triggered_count INTEGER NOT NULL DEFAULT 0,
                date_added TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
            );
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_contract_incentives_wrestler ON contract_incentives(wrestler_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_contract_incentives_type ON contract_incentives(incentive_type)')
        
        # ENHANCEMENT A: Contract History Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contract_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wrestler_id TEXT NOT NULL,
                wrestler_name TEXT NOT NULL,
                contract_type TEXT NOT NULL,
                salary_per_show INTEGER NOT NULL,
                contract_weeks INTEGER NOT NULL,
                signing_bonus INTEGER DEFAULT 0,
                total_incentives INTEGER DEFAULT 0,
                incentive_summary TEXT,
                signed_year INTEGER NOT NULL,
                signed_week INTEGER NOT NULL,
                expired_year INTEGER,
                expired_week INTEGER,
                termination_reason TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
            );
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_contract_history_wrestler ON contract_history(wrestler_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_contract_history_active ON contract_history(is_active)')
        
        # Add new columns to wrestlers table for STEP 122
        try:
            cursor.execute('ALTER TABLE wrestlers ADD COLUMN base_salary INTEGER DEFAULT NULL')
            cursor.execute('ALTER TABLE wrestlers ADD COLUMN current_escalated_salary INTEGER DEFAULT NULL')
            cursor.execute('ALTER TABLE wrestlers ADD COLUMN merchandise_share_percentage REAL DEFAULT 30.0')
            cursor.execute('ALTER TABLE wrestlers ADD COLUMN creative_control_level TEXT DEFAULT "none"')
            cursor.execute('ALTER TABLE wrestlers ADD COLUMN guaranteed_ppv_appearances INTEGER DEFAULT 0')
            cursor.execute('ALTER TABLE wrestlers ADD COLUMN has_no_trade_clause INTEGER DEFAULT 0')
            cursor.execute('ALTER TABLE wrestlers ADD COLUMN has_injury_protection INTEGER DEFAULT 0')
            cursor.execute('ALTER TABLE wrestlers ADD COLUMN injury_protection_percentage REAL DEFAULT 100.0')
            cursor.execute('ALTER TABLE wrestlers ADD COLUMN option_years_remaining INTEGER DEFAULT 0')
            cursor.execute('ALTER TABLE wrestlers ADD COLUMN buy_out_penalty INTEGER DEFAULT 0')
            cursor.execute('ALTER TABLE wrestlers ADD COLUMN restricted_brands TEXT DEFAULT NULL')
            cursor.execute('ALTER TABLE wrestlers ADD COLUMN max_appearances_per_year INTEGER DEFAULT NULL')
            cursor.execute('ALTER TABLE wrestlers ADD COLUMN ppv_appearances_this_year INTEGER DEFAULT 0')
            cursor.execute('ALTER TABLE wrestlers ADD COLUMN title_reigns_this_contract INTEGER DEFAULT 0')
            cursor.execute('ALTER TABLE wrestlers ADD COLUMN average_match_rating REAL DEFAULT 0.0')
            cursor.execute('ALTER TABLE wrestlers ADD COLUMN total_matches_this_contract INTEGER DEFAULT 0')
            print("[OK] Added STEP 122 contract incentive columns to wrestlers table")
        except:
            pass  # Columns already exist
        
        self.conn.commit()
        print("[OK] Contract incentives table created (STEP 122)")
        print("[OK] Contract history table created (Enhancement A)")
    
    # ========================================================================
    # STEP 122: Contract Incentive Operations
    # ========================================================================

    def save_contract_incentives(self, wrestler_id: str, incentives: List) -> None:
        """Save contract incentives for a wrestler (NO COMMIT - batched)"""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        # Delete existing incentives
        cursor.execute('DELETE FROM contract_incentives WHERE wrestler_id = ?', (wrestler_id,))
        
        # Insert current incentives
        for incentive in incentives:
            cursor.execute('''
                INSERT INTO contract_incentives (
                    wrestler_id, incentive_type, description, value,
                    conditions, is_active, triggered_count, date_added, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                wrestler_id,
                incentive.incentive_type.value,
                incentive.description,
                json.dumps(incentive.value),  # Store as JSON
                json.dumps(incentive.conditions) if incentive.conditions else None,
                1 if incentive.is_active else 0,
                incentive.triggered_count,
                now,
                now
            ))

    def load_contract_incentives(self, wrestler_id: str) -> List:
        """Load contract incentives for a wrestler"""
        from models.contract import ContractIncentive, IncentiveType

        read_conn = None

        try:
            # The office dashboard can fan out into several concurrent reads.
            # Using a short-lived read connection avoids sqlite cursor misuse on
            # the shared long-lived connection.
            read_conn = sqlite3.connect(self.db_path, timeout=30, check_same_thread=False)
            read_conn.row_factory = sqlite3.Row
            cursor = read_conn.cursor()
            cursor.execute('''
                SELECT incentive_type, description, value, conditions, is_active, triggered_count
                FROM contract_incentives 
                WHERE wrestler_id = ? AND is_active = 1
                ORDER BY id
            ''', (wrestler_id,))

            rows = [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[WARN] Database error loading incentives for {wrestler_id}: {e}")
            return []
        finally:
            if read_conn is not None:
                read_conn.close()

        incentives = []
        for row in rows:
            try:
                incentive_type_str = row.get('incentive_type') or None
                description = row.get('description') or ""
                value_str = row.get('value') if row.get('value') is not None else "0"
                conditions_str = row.get('conditions')
                is_active = bool(row.get('is_active')) if row.get('is_active') is not None else True
                triggered_count = row.get('triggered_count') if row.get('triggered_count') is not None else 0

                if not incentive_type_str:
                    print(f"[WARN] Skipping incentive with NULL type for {wrestler_id}")
                    continue

                try:
                    incentive_type = IncentiveType(incentive_type_str)
                except ValueError:
                    print(f"[WARN] Skipping invalid incentive type '{incentive_type_str}' for {wrestler_id}")
                    continue

                try:
                    if value_str is None:
                        value = 0
                    elif isinstance(value_str, (int, float)):
                        value = value_str
                    else:
                        value = json.loads(value_str)
                except (json.JSONDecodeError, TypeError):
                    value = value_str if value_str else 0

                try:
                    conditions = json.loads(conditions_str) if conditions_str else None
                except (json.JSONDecodeError, TypeError):
                    conditions = None

                incentive = ContractIncentive(
                    incentive_type=incentive_type,
                    description=description,
                    value=value,
                    conditions=conditions,
                    is_active=is_active,
                    triggered_count=triggered_count
                )
                incentives.append(incentive)

            except (ValueError, KeyError, IndexError, TypeError, AttributeError) as e:
                print(f"[WARN] Skipping invalid incentive for {wrestler_id}: {e}")
                continue

        return incentives

    def get_wrestlers_with_incentive(self, incentive_type: str) -> List[Dict[str, Any]]:
        """Get all wrestlers with a specific incentive type"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT DISTINCT w.*, ci.description, ci.value
            FROM wrestlers w
            JOIN contract_incentives ci ON w.id = ci.wrestler_id
            WHERE ci.incentive_type = ? AND ci.is_active = 1
        ''', (incentive_type,))
        
        return [dict(row) for row in cursor.fetchall()]

    def update_wrestler_contract_fields(self, wrestler_id: str, contract) -> None:
        """Update wrestler's contract fields including STEP 122 incentives (NO COMMIT)"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            UPDATE wrestlers SET
                contract_salary = ?,
                contract_total_weeks = ?,
                contract_weeks_remaining = ?,
                contract_signing_year = ?,
                contract_signing_week = ?,
                base_salary = ?,
                current_escalated_salary = ?,
                merchandise_share_percentage = ?,
                creative_control_level = ?,
                guaranteed_ppv_appearances = ?,
                has_no_trade_clause = ?,
                has_injury_protection = ?,
                injury_protection_percentage = ?,
                option_years_remaining = ?,
                buy_out_penalty = ?,
                restricted_brands = ?,
                max_appearances_per_year = ?,
                ppv_appearances_this_year = ?,
                title_reigns_this_contract = ?,
                average_match_rating = ?,
                total_matches_this_contract = ?
            WHERE id = ?
        ''', (
            contract.salary_per_show,
            contract.total_length_weeks,
            contract.weeks_remaining,
            contract.signing_year,
            contract.signing_week,
            contract.base_salary,
            contract.current_escalated_salary,
            contract.merchandise_share_percentage,
            contract.creative_control_level.value if hasattr(contract.creative_control_level, 'value') else contract.creative_control_level,
            contract.guaranteed_ppv_appearances,
            1 if contract.has_no_trade_clause else 0,
            1 if contract.has_injury_protection else 0,
            contract.injury_protection_percentage,
            contract.option_years_remaining,
            contract.buy_out_penalty,
            json.dumps(contract.restricted_brands) if contract.restricted_brands else None,
            contract.max_appearances_per_year,
            contract.ppv_appearances_this_year,
            contract.title_reigns_this_contract,
            contract.average_match_rating,
            contract.total_matches_this_contract,
            wrestler_id
        ))

    # ========================================================================
    # ENHANCEMENT A: Contract History Operations
    # ========================================================================

    def save_contract_to_history(
        self,
        wrestler_id: str,
        wrestler_name: str,
        contract_type: str,
        salary_per_show: int,
        contract_weeks: int,
        signing_bonus: int,
        total_incentives: int,
        incentive_summary: str,
        signed_year: int,
        signed_week: int
    ) -> int:
        """Record a new contract signing to history"""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO contract_history (
                wrestler_id, wrestler_name, contract_type,
                salary_per_show, contract_weeks, signing_bonus,
                total_incentives, incentive_summary,
                signed_year, signed_week,
                is_active, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            wrestler_id, wrestler_name, contract_type,
            salary_per_show, contract_weeks, signing_bonus,
            total_incentives, incentive_summary,
            signed_year, signed_week,
            1, now
        ))
        
        self.conn.commit()
        return cursor.lastrowid

    def expire_contract_in_history(
        self,
        wrestler_id: str,
        expired_year: int,
        expired_week: int,
        termination_reason: str = 'Expired'
    ):
        """Mark active contract as expired"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            UPDATE contract_history
            SET is_active = 0,
                expired_year = ?,
                expired_week = ?,
                termination_reason = ?
            WHERE wrestler_id = ? AND is_active = 1
        ''', (expired_year, expired_week, termination_reason, wrestler_id))
        
        self.conn.commit()

    def get_wrestler_contract_history(self, wrestler_id: str) -> List[Dict[str, Any]]:
        """Get all contracts for a wrestler, ordered newest to oldest"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT * FROM contract_history
            WHERE wrestler_id = ?
            ORDER BY signed_year DESC, signed_week DESC
        ''', (wrestler_id,))
        
        return [dict(row) for row in cursor.fetchall()]

    def get_contract_statistics(self, wrestler_id: str) -> Dict[str, Any]:
        """Get contract statistics for a wrestler"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total_contracts,
                AVG(salary_per_show) as avg_salary,
                MAX(salary_per_show) as highest_salary,
                MIN(salary_per_show) as lowest_salary,
                SUM(signing_bonus) as total_bonuses,
                AVG(total_incentives) as avg_incentives
            FROM contract_history
            WHERE wrestler_id = ?
        ''', (wrestler_id,))
        
        row = cursor.fetchone()
        return dict(row) if row else {}

    def get_all_active_contracts(self) -> List[Dict[str, Any]]:
        """Get all currently active contracts"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT * FROM contract_history
            WHERE is_active = 1
            ORDER BY wrestler_name
        ''')
        
        return [dict(row) for row in cursor.fetchall()]

    def get_contracts_expiring_soon(self, current_year: int, current_week: int, weeks_ahead: int = 4) -> List[Dict[str, Any]]:
        """Get contracts expiring within the specified number of weeks"""
        cursor = self.conn.cursor()
        
        # Calculate target week considering year rollover
        target_week = current_week + weeks_ahead
        target_year = current_year
        
        if target_week > 52:
            target_week = target_week - 52
            target_year += 1
        
        cursor.execute('''
            SELECT ch.*, w.contract_weeks_remaining
            FROM contract_history ch
            JOIN wrestlers w ON ch.wrestler_id = w.id
            WHERE ch.is_active = 1 
            AND w.contract_weeks_remaining <= ?
            AND w.contract_weeks_remaining > 0
            ORDER BY w.contract_weeks_remaining ASC
        ''', (weeks_ahead,))
        
        return [dict(row) for row in cursor.fetchall()]

    # ========================================================================
    # STEP 121: Contract Promise Tracking
    # ========================================================================

    def create_contract_promises_table(self):
        """Create contract promises tracking table"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contract_promises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                promise_type TEXT NOT NULL,
                wrestler_id TEXT NOT NULL,
                wrestler_name TEXT NOT NULL,
                promised_year INTEGER NOT NULL,
                promised_week INTEGER NOT NULL,
                deadline_weeks INTEGER NOT NULL,
                fulfilled INTEGER DEFAULT 0,
                fulfilled_year INTEGER,
                fulfilled_week INTEGER,
                fulfillment_details TEXT,
                broken INTEGER DEFAULT 0,
                broken_reason TEXT,
                morale_penalty_applied INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
            );
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_contract_promises_wrestler ON contract_promises(wrestler_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_contract_promises_fulfilled ON contract_promises(fulfilled)')
        
        self.conn.commit()
        print("[OK] Contract promises table created")

    def save_contract_promise(self, promise_data: Dict[str, Any]) -> int:
        """Save a contract promise"""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO contract_promises (
                promise_type, wrestler_id, wrestler_name,
                promised_year, promised_week, deadline_weeks,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            promise_data['promise_type'],
            promise_data['wrestler_id'],
            promise_data['wrestler_name'],
            promise_data['promised_year'],
            promise_data['promised_week'],
            promise_data['deadline_weeks'],
            now
        ))
        
        self.conn.commit()
        return cursor.lastrowid

    def get_active_promises(self, wrestler_id: str = None) -> List[Dict[str, Any]]:
        """Get active (unfulfilled, unbroken) promises"""
        cursor = self.conn.cursor()
        
        if wrestler_id:
            cursor.execute('''
                SELECT * FROM contract_promises
                WHERE wrestler_id = ? AND fulfilled = 0 AND broken = 0
                ORDER BY promised_year, promised_week
            ''', (wrestler_id,))
        else:
            cursor.execute('''
                SELECT * FROM contract_promises
                WHERE fulfilled = 0 AND broken = 0
                ORDER BY promised_year, promised_week
            ''')
        
        return [dict(row) for row in cursor.fetchall()]

    def fulfill_promise(
        self,
        promise_id: int,
        fulfilled_year: int,
        fulfilled_week: int,
        fulfillment_details: str
    ):
        """Mark a promise as fulfilled"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            UPDATE contract_promises
            SET fulfilled = 1,
                fulfilled_year = ?,
                fulfilled_week = ?,
                fulfillment_details = ?
            WHERE id = ?
        ''', (fulfilled_year, fulfilled_week, fulfillment_details, promise_id))
        
        self.conn.commit()

    def break_promise(
        self,
        promise_id: int,
        broken_reason: str,
        morale_penalty: int = 0
    ):
        """Mark a promise as broken"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            UPDATE contract_promises
            SET broken = 1,
                broken_reason = ?,
                morale_penalty_applied = ?
            WHERE id = ?
        ''', (broken_reason, morale_penalty, promise_id))
        
        self.conn.commit()

    def check_overdue_promises(self, current_year: int, current_week: int) -> List[Dict[str, Any]]:
        """Check for promises that are overdue"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT * FROM contract_promises
            WHERE fulfilled = 0 AND broken = 0
        ''')
        
        overdue = []
        for row in cursor.fetchall():
            promise = dict(row)
            
            # Calculate deadline
            deadline_year = promise['promised_year']
            deadline_week = promise['promised_week'] + promise['deadline_weeks']
            
            if deadline_week > 52:
                deadline_year += deadline_week // 52
                deadline_week = deadline_week % 52
            
            # Check if overdue
            if (current_year > deadline_year or 
                (current_year == deadline_year and current_week > deadline_week)):
                overdue.append(promise)
        
        return overdue

    def get_wrestler_promises(self, wrestler_id: str) -> Dict[str, List]:
        """Get all promises for a wrestler, categorized"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT * FROM contract_promises
            WHERE wrestler_id = ?
            ORDER BY promised_year DESC, promised_week DESC
        ''', (wrestler_id,))
        
        all_promises = [dict(row) for row in cursor.fetchall()]
        
        return {
            'active': [p for p in all_promises if not p['fulfilled'] and not p['broken']],
            'fulfilled': [p for p in all_promises if p['fulfilled']],
            'broken': [p for p in all_promises if p['broken']]
        }

    # ========================================================================
    # STEP 123: Free Agency Declaration Operations
    # ========================================================================

    def _create_free_agency_declaration_tables(self):
        """Create tables for free agency declarations (STEP 123)"""
        cursor = self.conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS free_agency_declarations (
                declaration_id TEXT PRIMARY KEY,
                wrestler_id TEXT NOT NULL,
                wrestler_name TEXT NOT NULL,
                declared_year INTEGER NOT NULL,
                declared_week INTEGER NOT NULL,
                declaration_type TEXT NOT NULL,
                status TEXT NOT NULL,
                weeks_remaining_at_declaration INTEGER NOT NULL,
                current_salary INTEGER NOT NULL,
                years_with_promotion INTEGER NOT NULL,
                reasons TEXT NOT NULL,
                public_statement TEXT NOT NULL,
                leverage_level INTEGER NOT NULL,
                media_attention INTEGER NOT NULL,
                rival_offers_count INTEGER DEFAULT 0,
                highest_rival_offer INTEGER DEFAULT 0,
                current_promotion_counter_offer INTEGER,
                resolved_year INTEGER,
                resolved_week INTEGER,
                resolution_details TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
            );
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_fa_declarations_wrestler ON free_agency_declarations(wrestler_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_fa_declarations_status ON free_agency_declarations(status)')

        self.conn.commit()
        print("[OK] Free agency declaration tables created (STEP 123)")

    def save_free_agency_declaration(self, declaration) -> None:
        """Save free agency declaration to database"""
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO free_agency_declarations (
                declaration_id, wrestler_id, wrestler_name,
                declared_year, declared_week, declaration_type, status,
                weeks_remaining_at_declaration, current_salary, years_with_promotion,
                reasons, public_statement, leverage_level, media_attention,
                rival_offers_count, highest_rival_offer, current_promotion_counter_offer,
                resolved_year, resolved_week, resolution_details, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            declaration.declaration_id,
            declaration.wrestler_id,
            declaration.wrestler_name,
            declaration.declared_year,
            declaration.declared_week,
            declaration.declaration_type.value,
            declaration.status.value,
            declaration.weeks_remaining_at_declaration,
            declaration.current_salary,
            declaration.years_with_promotion,
            json.dumps(declaration.reasons),
            declaration.public_statement,
            declaration.leverage_level,
            declaration.media_attention,
            declaration.rival_offers_count,
            declaration.highest_rival_offer,
            declaration.current_promotion_counter_offer,
            declaration.resolved_year,
            declaration.resolved_week,
            declaration.resolution_details,
            declaration.created_at
        ))

    def load_all_free_agency_declarations(self) -> List[dict]:
        """Load all free agency declarations from database"""
        cursor = self.conn.cursor()

        try:
            cursor.execute('SELECT * FROM free_agency_declarations ORDER BY declared_year DESC, declared_week DESC')
        except Exception as e:
            print(f"[WARN] Error loading declarations: {e}")
            print("Creating table...")
            self._create_free_agency_declaration_tables()
            cursor.execute('SELECT * FROM free_agency_declarations ORDER BY declared_year DESC, declared_week DESC')

        declarations = []
        for row in cursor.fetchall():
            decl_dict = dict(row)
            decl_dict['reasons'] = json.loads(decl_dict['reasons'])
            declarations.append(decl_dict)

        return declarations

    def get_active_free_agency_declarations(self) -> List[dict]:
        """Get only active declarations"""
        cursor = self.conn.cursor()

        try:
            cursor.execute('''
                SELECT * FROM free_agency_declarations 
                WHERE status = 'active'
                ORDER BY declared_year DESC, declared_week DESC
            ''')
        except Exception as e:
            print(f"[WARN] Error loading active declarations: {e}")
            print("Creating table...")
            self._create_free_agency_declaration_tables()
            cursor.execute('''
                SELECT * FROM free_agency_declarations 
                WHERE status = 'active'
                ORDER BY declared_year DESC, declared_week DESC
            ''')

        declarations = []
        for row in cursor.fetchall():
            decl_dict = dict(row)
            decl_dict['reasons'] = json.loads(decl_dict['reasons'])
            declarations.append(decl_dict)

        return declarations

    # ========================================================================
    # STEP 125: Contract Storyline Database Operations
    # ========================================================================

    def save_contract_storyline(self, storyline) -> None:
        """Save or update a contract storyline"""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT OR REPLACE INTO contract_storylines (
                storyline_id, storyline_type, wrestler_id, wrestler_name,
                status, trigger_year, trigger_week,
                planned_resolution_show, planned_resolution_week,
                current_beat, total_beats, description, weekly_segments,
                outcome, resolution_details, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            storyline.storyline_id,
            storyline.storyline_type.value,
            storyline.wrestler_id,
            storyline.wrestler_name,
            storyline.status.value,
            storyline.trigger_year,
            storyline.trigger_week,
            storyline.planned_resolution_show,
            storyline.planned_resolution_week,
            storyline.current_beat,
            storyline.total_beats,
            storyline.description,
            json.dumps(storyline.weekly_segments),
            storyline.outcome,
            storyline.resolution_details,
            now,
            now
        ))
        
        self.conn.commit()

    def load_contract_storylines(self) -> List[Dict[str, Any]]:
        """Load all contract storylines from database"""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM contract_storylines ORDER BY created_at DESC')
            rows = cursor.fetchall()
        except:
            # Table doesn't exist yet
            return []
        
        storylines = []
        
        for row in rows:
            storyline_dict = dict(row)
            storyline_dict['weekly_segments'] = json.loads(storyline_dict['weekly_segments'] or '[]')
            storylines.append(storyline_dict)
        
        return storylines

    def get_active_contract_storylines(self) -> List[Dict[str, Any]]:
        """Get only active contract storylines"""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute('''
                SELECT * FROM contract_storylines 
                WHERE status IN ('pending', 'active', 'progressing', 'climax')
                ORDER BY trigger_year DESC, trigger_week DESC
            ''')
            rows = cursor.fetchall()
        except:
            return []
        
        storylines = []
        
        for row in rows:
            storyline_dict = dict(row)
            storyline_dict['weekly_segments'] = json.loads(storyline_dict['weekly_segments'] or '[]')
            storylines.append(storyline_dict)
        
        return storylines

    def delete_contract_storyline(self, storyline_id: str) -> None:
        """Delete a contract storyline"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM contract_storylines WHERE storyline_id = ?', (storyline_id,))
        self.conn.commit()

    def update_contract_storyline_status(
        self, 
        storyline_id: str, 
        status: str, 
        current_beat: int = None,
        outcome: str = None,
        resolution_details: str = None
    ) -> None:
        """Update storyline status and progress"""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        updates = ['status = ?', 'updated_at = ?']
        values = [status, now]
        
        if current_beat is not None:
            updates.append('current_beat = ?')
            values.append(current_beat)
        
        if outcome is not None:
            updates.append('outcome = ?')
            values.append(outcome)
        
        if resolution_details is not None:
            updates.append('resolution_details = ?')
            values.append(resolution_details)
        
        values.append(storyline_id)
        
        sql = f"UPDATE contract_storylines SET {', '.join(updates)} WHERE storyline_id = ?"
        cursor.execute(sql, values)
        self.conn.commit()

    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def vacuum(self):
        """Optimize database"""
        self.conn.execute('VACUUM')
        print("[OK] Database optimized")
    
    def get_table_counts(self) -> Dict[str, int]:
        """Get row counts for all tables (useful for debugging)"""
        cursor = self.conn.cursor()
        
        tables = [
            'wrestlers', 'championships', 'title_reigns', 'feuds',
            'feud_segments', 'match_history', 'show_history',
            'wrestler_stats', 'milestones', 'tag_teams', 'storylines',
            'title_vacancies', 'title_defenses', 'guaranteed_title_shots',
            'free_agents', 'free_agent_rival_interest', 'free_agent_contract_history',
            'negotiation_history', 'scouting_reports',
            'contract_incentives', 'contract_history',
            'free_agency_declarations', 'contract_promises',
            'contract_storylines', 'morale_records',
            'wrestler_behavior_states', 'behavior_events',
            'recovery_events', 'recovery_cooldowns',
            'morale_storyline_seeds', 'office_alerts'
        ]
        
        counts = {}
        for table in tables:
            try:
                cursor.execute(f'SELECT COUNT(*) FROM {table}')
                counts[table] = cursor.fetchone()[0]
            except:
                counts[table] = 0
        
        return counts
    
    def reset_database(self):
        """Reset all data (dangerous - use with caution)"""
        cursor = self.conn.cursor()
        
        tables = [
            'milestones', 'wrestler_stats', 'feud_segments', 'feuds',
            'match_history', 'show_history', 'title_reigns',
            'championships', 'tag_teams', 'wrestlers', 'storylines', 'game_state',
            'title_vacancies', 'title_defenses', 'guaranteed_title_shots', 'title_situation_log',
            'free_agents', 'free_agent_rival_interest', 'free_agent_contract_history',
            'negotiation_history', 'scouting_reports',
            'contract_incentives', 'contract_history',
            'free_agency_declarations', 'contract_promises',
            'contract_storylines', 'morale_records',
            'wrestler_behavior_states', 'behavior_events',
            'recovery_events', 'recovery_cooldowns',
            'morale_storyline_seeds', 'office_alerts'
        ]
        
        for table in tables:
            try:
                cursor.execute(f'DELETE FROM {table}')
            except:
                pass
        
        # Re-initialize game state
        now = datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO game_state (id, current_year, current_week, current_show_index, balance, show_count, created_at, last_saved)
            VALUES (1, 1, 1, 0, 1000000, 0, ?, ?)
        ''', (now, now))
        
        self.conn.commit()
        print("[WARN] Database has been reset")
    

    # ========================================================================
    # STEPS 245-253: Morale Behavior Tables & Operations
    # ========================================================================

    def _create_morale_behavior_tables(self):
        """Create tables for morale behavior system (Steps 245-253)."""
        cursor = self.conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wrestler_behavior_states (
                wrestler_id TEXT PRIMARY KEY,
                has_requested_release INTEGER DEFAULT 0,
                release_demand_year INTEGER,
                release_demand_week INTEGER,
                release_demand_count INTEGER DEFAULT 0,
                has_gone_public INTEGER DEFAULT 0,
                public_demand_year INTEGER,
                public_demand_week INTEGER,
                public_statement TEXT,
                is_phoning_it_in INTEGER DEFAULT 0,
                phone_in_penalty REAL DEFAULT 0.0,
                is_sandbagging INTEGER DEFAULT 0,
                sandbagging_penalty REAL DEFAULT 0.0,
                refused_bookings TEXT DEFAULT '[]',
                refused_match_types TEXT DEFAULT '[]',
                cooperation_refusal_active INTEGER DEFAULT 0,
                is_leaking_info INTEGER DEFAULT 0,
                leaks_this_year INTEGER DEFAULT 0,
                last_leak_week INTEGER,
                is_venting_online INTEGER DEFAULT 0,
                social_media_incidents INTEGER DEFAULT 0,
                last_vent_week INTEGER,
                is_poisoning_locker_room INTEGER DEFAULT 0,
                poisoning_targets TEXT DEFAULT '[]',
                influence_radius INTEGER DEFAULT 0,
                is_running_down_contract INTEGER DEFAULT 0,
                lame_duck_start_week INTEGER,
                lame_duck_effort_penalty REAL DEFAULT 0.0,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
            );
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS behavior_events (
                event_id TEXT PRIMARY KEY,
                wrestler_id TEXT NOT NULL,
                wrestler_name TEXT NOT NULL,
                behavior_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                description TEXT NOT NULL,
                game_year INTEGER NOT NULL,
                game_week INTEGER NOT NULL,
                morale_at_time INTEGER NOT NULL,
                resolved INTEGER DEFAULT 0,
                resolution TEXT,
                match_quality_penalty REAL DEFAULT 0.0,
                affects_opponent INTEGER DEFAULT 0,
                leaked_info TEXT,
                social_post TEXT,
                influenced_wrestlers TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
            );
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_behavior_events_wrestler ON behavior_events(wrestler_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_behavior_events_type ON behavior_events(behavior_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_behavior_events_year_week ON behavior_events(game_year, game_week)')

        self.conn.commit()
        print("\u2705 Morale behavior tables created (Steps 245-253)")

    def get_behavior_state(self, wrestler_id: str):
        """Load behavior state dict for a wrestler, or None if not found."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM wrestler_behavior_states WHERE wrestler_id = ?', (wrestler_id,))
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        d['refused_bookings'] = json.loads(d.get('refused_bookings') or '[]')
        d['refused_match_types'] = json.loads(d.get('refused_match_types') or '[]')
        d['poisoning_targets'] = json.loads(d.get('poisoning_targets') or '[]')
        for bool_field in (
            'has_requested_release', 'has_gone_public', 'is_phoning_it_in',
            'is_sandbagging', 'cooperation_refusal_active', 'is_leaking_info',
            'is_venting_online', 'is_poisoning_locker_room', 'is_running_down_contract',
        ):
            d[bool_field] = bool(d.get(bool_field, 0))
        return d

    def save_behavior_state(self, state) -> None:
        """Save WrestlerBehaviorState to database (NO COMMIT — batched)."""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute('''
            INSERT OR REPLACE INTO wrestler_behavior_states (
                wrestler_id,
                has_requested_release, release_demand_year, release_demand_week, release_demand_count,
                has_gone_public, public_demand_year, public_demand_week, public_statement,
                is_phoning_it_in, phone_in_penalty,
                is_sandbagging, sandbagging_penalty,
                refused_bookings, refused_match_types, cooperation_refusal_active,
                is_leaking_info, leaks_this_year, last_leak_week,
                is_venting_online, social_media_incidents, last_vent_week,
                is_poisoning_locker_room, poisoning_targets, influence_radius,
                is_running_down_contract, lame_duck_start_week, lame_duck_effort_penalty,
                updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            state.wrestler_id,
            1 if state.has_requested_release else 0,
            state.release_demand_year, state.release_demand_week, state.release_demand_count,
            1 if state.has_gone_public else 0,
            state.public_demand_year, state.public_demand_week, state.public_statement,
            1 if state.is_phoning_it_in else 0, state.phone_in_penalty,
            1 if state.is_sandbagging else 0, state.sandbagging_penalty,
            json.dumps(state.refused_bookings), json.dumps(state.refused_match_types),
            1 if state.cooperation_refusal_active else 0,
            1 if state.is_leaking_info else 0, state.leaks_this_year, state.last_leak_week,
            1 if state.is_venting_online else 0, state.social_media_incidents, state.last_vent_week,
            1 if state.is_poisoning_locker_room else 0,
            json.dumps(state.poisoning_targets), state.influence_radius,
            1 if state.is_running_down_contract else 0,
            state.lame_duck_start_week, state.lame_duck_effort_penalty,
            now,
        ))

    def save_behavior_event(self, event) -> None:
        """Save a BehaviorEvent to database (NO COMMIT — batched)."""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute('''
            INSERT OR REPLACE INTO behavior_events (
                event_id, wrestler_id, wrestler_name,
                behavior_type, severity, description,
                game_year, game_week, morale_at_time,
                resolved, resolution,
                match_quality_penalty, affects_opponent,
                leaked_info, social_post, influenced_wrestlers,
                created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            event.event_id, event.wrestler_id, event.wrestler_name,
            event.behavior_type.value, event.severity.value, event.description,
            event.game_year, event.game_week, event.morale_at_time,
            1 if event.resolved else 0, event.resolution,
            event.match_quality_penalty, 1 if event.affects_opponent else 0,
            event.leaked_info, event.social_post,
            json.dumps(event.influenced_wrestlers), now,
        ))

    def get_behavior_events(self, wrestler_id: str = None, behavior_type: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch behavior event log, optionally filtered."""
        cursor = self.conn.cursor()
        conditions, params = [], []
        if wrestler_id:
            conditions.append('wrestler_id = ?')
            params.append(wrestler_id)
        if behavior_type:
            conditions.append('behavior_type = ?')
            params.append(behavior_type)
        where = ('WHERE ' + ' AND '.join(conditions)) if conditions else ''
        cursor.execute(f'SELECT * FROM behavior_events {where} ORDER BY game_year DESC, game_week DESC, created_at DESC LIMIT ?', params + [limit])
        result = []
        for row in cursor.fetchall():
            d = dict(row)
            d['resolved'] = bool(d.get('resolved', 0))
            d['affects_opponent'] = bool(d.get('affects_opponent', 0))
            d['influenced_wrestlers'] = json.loads(d.get('influenced_wrestlers') or '[]')
            result.append(d)
        return result

    def get_all_behavior_states_with_active_flags(self) -> List[Dict[str, Any]]:
        """Returns all wrestler behavior states with at least one active flag."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM wrestler_behavior_states
            WHERE has_requested_release = 1 OR has_gone_public = 1
               OR is_phoning_it_in = 1 OR is_sandbagging = 1
               OR cooperation_refusal_active = 1 OR is_leaking_info = 1
               OR is_venting_online = 1 OR is_poisoning_locker_room = 1
               OR is_running_down_contract = 1
            ORDER BY updated_at DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]

    # ========================================================================
    # STEPS 254-259: Morale Recovery Tables & Operations
    # ========================================================================

    def _create_recovery_tables(self):
        """Create tables for the morale recovery system (Steps 254-259)."""
        cursor = self.conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recovery_events (
                event_id TEXT PRIMARY KEY,
                wrestler_id TEXT NOT NULL,
                wrestler_name TEXT NOT NULL,
                recovery_type TEXT NOT NULL,
                outcome TEXT NOT NULL,
                morale_before INTEGER NOT NULL,
                morale_after INTEGER NOT NULL,
                morale_change INTEGER NOT NULL,
                details TEXT NOT NULL DEFAULT '{}',
                notes TEXT NOT NULL DEFAULT '[]',
                cost INTEGER NOT NULL DEFAULT 0,
                game_year INTEGER NOT NULL,
                game_week INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
            );
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_recovery_events_wrestler ON recovery_events(wrestler_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_recovery_events_type ON recovery_events(recovery_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_recovery_events_year ON recovery_events(game_year, game_week)')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recovery_cooldowns (
                wrestler_id TEXT PRIMARY KEY,
                last_used_json TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL,
                FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
            );
        ''')

        self.conn.commit()
        print("\u2705 Recovery tables created (Steps 254-259)")

    def save_recovery_event(self, event) -> None:
        """Persist a RecoveryEvent (NO COMMIT — batched)."""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute('''
            INSERT OR REPLACE INTO recovery_events (
                event_id, wrestler_id, wrestler_name,
                recovery_type, outcome,
                morale_before, morale_after, morale_change,
                details, notes, cost,
                game_year, game_week, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            event.event_id, event.wrestler_id, event.wrestler_name,
            event.recovery_type.value, event.outcome.value,
            event.morale_before, event.morale_after, event.morale_change,
            json.dumps(event.details), json.dumps(event.notes), event.cost,
            event.game_year, event.game_week, now,
        ))

    def get_recovery_events(self, wrestler_id: str = None, recovery_type: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch recovery events, optionally filtered."""
        cursor = self.conn.cursor()
        conditions, params = [], []
        if wrestler_id:
            conditions.append('wrestler_id = ?')
            params.append(wrestler_id)
        if recovery_type:
            conditions.append('recovery_type = ?')
            params.append(recovery_type)
        where = ('WHERE ' + ' AND '.join(conditions)) if conditions else ''
        cursor.execute(f'SELECT * FROM recovery_events {where} ORDER BY game_year DESC, game_week DESC, created_at DESC LIMIT ?', params + [limit])
        result = []
        for row in cursor.fetchall():
            d = dict(row)
            d['details'] = json.loads(d.get('details') or '{}')
            d['notes'] = json.loads(d.get('notes') or '[]')
            result.append(d)
        return result

    def save_recovery_cooldown(self, cooldown) -> None:
        """Persist a RecoveryCooldown (NO COMMIT — batched)."""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute('''
            INSERT OR REPLACE INTO recovery_cooldowns (wrestler_id, last_used_json, updated_at)
            VALUES (?, ?, ?)
        ''', (cooldown.wrestler_id, json.dumps(cooldown.last_used), now))

    def get_recovery_cooldown(self, wrestler_id: str):
        """Load recovery cooldown for a wrestler. Returns dict or None."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM recovery_cooldowns WHERE wrestler_id = ?', (wrestler_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    # ========================================================================
    # STEPS 260-265: Morale Events, Storyline Seeds, Office Alerts
    # ========================================================================

    def _create_show_drafts_table(self):
        """Create show drafts table for booking UI (STEP 58-72)"""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS show_drafts (
                show_id TEXT PRIMARY KEY,
                show_data TEXT NOT NULL,
                production_plan TEXT,
                created_at TEXT NOT NULL
            );
        ''')
        self.conn.commit()
        print("[OK] Show drafts table created")


    def _create_morale_events_tables(self):
        """Create tables for morale events system (Steps 260-265)."""
        cursor = self.conn.cursor()

        # Morale storyline seeds (Step 261)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS morale_storyline_seeds (
                seed_id TEXT PRIMARY KEY,
                storyline_type TEXT NOT NULL,
                title TEXT NOT NULL,
                logline TEXT NOT NULL,
                full_outline TEXT NOT NULL,
                primary_wrestler_id TEXT NOT NULL,
                primary_wrestler_name TEXT NOT NULL,
                supporting_cast TEXT NOT NULL DEFAULT '[]',
                morale_trigger INTEGER NOT NULL,
                urgency TEXT NOT NULL,
                suggested_duration_weeks INTEGER NOT NULL DEFAULT 8,
                status TEXT NOT NULL DEFAULT 'pending',
                year INTEGER NOT NULL,
                week INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (primary_wrestler_id) REFERENCES wrestlers(id)
            );
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_morale_seeds_wrestler ON morale_storyline_seeds(primary_wrestler_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_morale_seeds_status ON morale_storyline_seeds(status)')

        # Office alerts (Step 263)
        cursor.executescript('''
            CREATE TABLE IF NOT EXISTS office_alerts (
                alert_id TEXT PRIMARY KEY,
                priority TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                action_url TEXT,
                action_label TEXT,
                wrestler_id TEXT,
                wrestler_name TEXT,
                dismissed INTEGER NOT NULL DEFAULT 0,
                year INTEGER NOT NULL,
                week INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );
            
            -- Developmental Roster Tables
            CREATE TABLE IF NOT EXISTS developmental_roster (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wrestler_id TEXT UNIQUE NOT NULL,
                wrestler_name TEXT NOT NULL,
                join_date_year INTEGER NOT NULL,
                join_date_week INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'developmental',
                developmental_rating INTEGER NOT NULL DEFAULT 50,
                match_quality_avg REAL NOT NULL DEFAULT 0.0,
                crowd_reaction_avg REAL NOT NULL DEFAULT 0.0,
                coach_evaluation INTEGER NOT NULL DEFAULT 50,
                weeks_in_developmental INTEGER NOT NULL DEFAULT 0,
                call_up_eligible_week INTEGER NOT NULL DEFAULT 8,
                times_called_up INTEGER NOT NULL DEFAULT 0,
                last_call_up_year INTEGER,
                last_call_up_week INTEGER,
                last_call_up_brand TEXT,
                call_up_success_rate REAL NOT NULL DEFAULT 0.0,
                assigned_brand TEXT,
                assigned_brand_date_year INTEGER,
                assigned_brand_date_week INTEGER,
                achievements TEXT DEFAULT '[]',
                training_focus TEXT DEFAULT '[]',
                coaching_notes TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            
            -- Call-Up History Table
            CREATE TABLE IF NOT EXISTS call_up_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wrestler_id TEXT NOT NULL,
                wrestler_name TEXT NOT NULL,
                call_up_year INTEGER NOT NULL,
                call_up_week INTEGER NOT NULL,
                source_brand TEXT NOT NULL,
                destination_brand TEXT NOT NULL,
                reason TEXT NOT NULL,
                initiating_gm TEXT,
                success_outcome INTEGER,
                return_date_year INTEGER,
                return_date_week INTEGER,
                created_at TEXT NOT NULL
            );
            
            -- Nexus Championship Table
            CREATE TABLE IF NOT EXISTS nexus_championship (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                championship_id TEXT NOT NULL DEFAULT 'nexus_championship',
                name TEXT NOT NULL DEFAULT 'Nexus Championship',
                current_holder_id TEXT,
                current_holder_name TEXT,
                won_date_year INTEGER,
                won_date_week INTEGER,
                days_held INTEGER NOT NULL DEFAULT 0,
                defense_count INTEGER NOT NULL DEFAULT 0,
                history TEXT DEFAULT '[]',
                updated_at TEXT NOT NULL
            );
            
            -- Nexus Championship Matches Table
            CREATE TABLE IF NOT EXISTS nexus_championship_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_date_year INTEGER NOT NULL,
                match_date_week INTEGER NOT NULL,
                wrestler1_id TEXT NOT NULL,
                wrestler1_name TEXT NOT NULL,
                wrestler2_id TEXT NOT NULL,
                wrestler2_name TEXT NOT NULL,
                winner_id TEXT NOT NULL,
                winner_name TEXT NOT NULL,
                was_title_match INTEGER NOT NULL DEFAULT 0,
                title_changed INTEGER NOT NULL DEFAULT 0,
                match_quality INTEGER NOT NULL DEFAULT 50,
                notes TEXT,
                created_at TEXT NOT NULL
            );
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_office_alerts_dismissed ON office_alerts(dismissed)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_office_alerts_priority ON office_alerts(priority)')

        self.conn.commit()
        print("\u2705 Morale events tables created (Steps 260-265)")

    def save_morale_storyline_seed(self, seed) -> None:
        """Persist a MoraleStorylineSeed (NO COMMIT — batched)."""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute('''
            INSERT OR REPLACE INTO morale_storyline_seeds (
                seed_id, storyline_type, title, logline, full_outline,
                primary_wrestler_id, primary_wrestler_name,
                supporting_cast, morale_trigger, urgency,
                suggested_duration_weeks, status, year, week, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            seed.seed_id, seed.storyline_type.value, seed.title,
            seed.logline, seed.full_outline,
            seed.primary_wrestler_id, seed.primary_wrestler_name,
            json.dumps(seed.supporting_cast), seed.morale_trigger, seed.urgency,
            seed.suggested_duration_weeks,
            'accepted' if seed.accepted else ('rejected' if seed.rejected else 'pending'),
            seed.year, seed.week, now,
        ))

    def get_morale_storyline_seeds(
        self,
        wrestler_id: str = None,
        storyline_type: str = None,
        status: str = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Fetch morale storyline seeds, optionally filtered."""
        cursor = self.conn.cursor()
        conditions, params = [], []
        if wrestler_id:
            conditions.append('primary_wrestler_id = ?')
            params.append(wrestler_id)
        if storyline_type:
            conditions.append('storyline_type = ?')
            params.append(storyline_type)
        if status and status != 'all':
            conditions.append('status = ?')
            params.append(status)
        where = ('WHERE ' + ' AND '.join(conditions)) if conditions else ''
        cursor.execute(f'SELECT * FROM morale_storyline_seeds {where} ORDER BY created_at DESC LIMIT ?', params + [limit])
        result = []
        for row in cursor.fetchall():
            d = dict(row)
            d['supporting_cast'] = json.loads(d.get('supporting_cast') or '[]')
            result.append(d)
        return result

    def update_morale_storyline_seed_status(self, seed_id: str, status: str) -> None:
        """Update status of a storyline seed (accepted/rejected/pending)."""
        cursor = self.conn.cursor()
        cursor.execute('UPDATE morale_storyline_seeds SET status = ? WHERE seed_id = ?', (status, seed_id))

    def save_office_alert(self, alert) -> None:
        """Persist an OfficeAlert (NO COMMIT — batched)."""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute('''
            INSERT OR REPLACE INTO office_alerts (
                alert_id, priority, title, body,
                action_url, action_label, wrestler_id, wrestler_name,
                dismissed, year, week, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            alert.alert_id, alert.priority.value, alert.title, alert.body,
            alert.action_url, alert.action_label,
            alert.wrestler_id, alert.wrestler_name,
            1 if alert.dismissed else 0,
            alert.year, alert.week, now,
        ))

    def get_office_alerts(self, include_dismissed: bool = False, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch office alerts, sorted by priority."""
        cursor = self.conn.cursor()
        where = '' if include_dismissed else 'WHERE dismissed = 0'
        cursor.execute(
            f'SELECT * FROM office_alerts {where} ' +
            'ORDER BY CASE priority WHEN "critical" THEN 0 WHEN "urgent" THEN 1 WHEN "warning" THEN 2 ELSE 3 END, created_at DESC ' +
            'LIMIT ?',
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def dismiss_office_alert(self, alert_id: str) -> None:
        """Mark an office alert as dismissed."""
        cursor = self.conn.cursor()
        cursor.execute('UPDATE office_alerts SET dismissed = 1 WHERE alert_id = ?', (alert_id,))

    def backup_database(self, backup_path: str):
        """Create a backup of the database"""
        import shutil
        
        # Close connection temporarily
        self.close()
        
        # Copy the database file
        shutil.copy2(self.db_path, backup_path)
        
        # Reconnect
        self.connect()
        
        print(f"[OK] Database backed up to {backup_path}")
    
    def execute_raw(self, sql: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Execute raw SQL (use with caution)"""
        cursor = self.conn.cursor()
        
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        
        if sql.strip().upper().startswith('SELECT'):
            return [dict(row) for row in cursor.fetchall()]
        else:
            self.conn.commit()
            return []
    def save_show_draft(self, show_draft, production_plan=None):
        """Save show draft as JSON"""
        import json
        cursor = self.conn.cursor()
    
        # Create table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS show_drafts (
                show_id TEXT PRIMARY KEY,
                show_data TEXT NOT NULL,
                production_plan TEXT,
                created_at TEXT
            );
        ''')
    
        cursor.execute('''
            INSERT OR REPLACE INTO show_drafts 
            (show_id, show_data, production_plan, created_at)
            VALUES (?, ?, ?, ?)
        ''', (
            show_draft.show_id,
            json.dumps(show_draft.to_dict()),
            json.dumps(production_plan) if production_plan else None,
            datetime.now().isoformat()
        ))

        self.conn.commit()

    def get_show_draft(self, show_id):
        """Get show draft by ID"""
        import json
        cursor = self.conn.cursor()
        cursor.execute('SELECT show_data FROM show_drafts WHERE show_id = ?', (show_id,))
        row = cursor.fetchone()
    
        if row:
            return json.loads(row['show_data'])
        return None

    def get_current_show_draft(self, brand):
        """Get current show draft for a brand"""
        import json
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT show_data FROM show_drafts 
            WHERE json_extract(show_data, '$.brand') = ?
            ORDER BY created_at DESC LIMIT 1
        ''', (brand,))
        row = cursor.fetchone()
    
        if row:
            return json.loads(row['show_data'])
        return None

    def get_production_plan(self, show_id):
        """Get production plan for a show"""
        import json
        cursor = self.conn.cursor()
        cursor.execute('SELECT production_plan FROM show_drafts WHERE show_id = ?', (show_id,))
        row = cursor.fetchone()
    
        if row and row['production_plan']:
            return json.loads(row['production_plan'])
        return None

    def clear_show_draft(self, show_id):
        """Delete a show draft"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM show_drafts WHERE show_id = ?', (show_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    # ========================================================================
    # Vanguard Developmental Brand + GM Promotion Foundation
    # ========================================================================

    def _drop_alignment_turn_tables(self) -> None:
        """Remove deprecated wrestler turn/alignment tracking tables."""
        cursor = self.conn.cursor()
        cursor.execute('DROP TABLE IF EXISTS turn_segments')
        cursor.execute('DROP TABLE IF EXISTS wrestler_turns')
        self.conn.commit()

    def _create_character_system_tables(self) -> None:
        """Create persistent wrestler character system tables and columns."""
        cursor = self.conn.cursor()
        wrestler_columns = [
            ("alignment_percentage", "INTEGER DEFAULT 50"),
            ("gimmick_effectiveness", "INTEGER DEFAULT 50"),
            ("primary_wrestling_style", "TEXT DEFAULT 'hybrid'"),
            ("secondary_wrestling_style", "TEXT"),
            ("nationality", "TEXT DEFAULT 'United States'"),
            ("birth_city", "TEXT"),
            ("birth_country", "TEXT"),
            ("kayfabe_hometown", "TEXT"),
            ("ethnic_background", "TEXT"),
        ]
        for column_name, ddl in wrestler_columns:
            try:
                cursor.execute(f"ALTER TABLE wrestlers ADD COLUMN {column_name} {ddl}")
            except sqlite3.OperationalError:
                pass

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alignment_turns (
                id TEXT PRIMARY KEY,
                wrestler_id TEXT NOT NULL,
                old_alignment INTEGER NOT NULL,
                new_alignment INTEGER NOT NULL,
                turn_date TEXT NOT NULL,
                timing_score INTEGER NOT NULL,
                build_score INTEGER NOT NULL,
                surprise_factor INTEGER NOT NULL,
                impact_score INTEGER NOT NULL,
                overness_change INTEGER NOT NULL,
                notes TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
            );
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gimmick_templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                default_alignment TEXT NOT NULL,
                recommended_wrestling_style TEXT,
                base_popularity_modifier INTEGER DEFAULT 0,
                attributes_json TEXT NOT NULL,
                is_custom INTEGER DEFAULT 0,
                version INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wrestler_gimmicks (
                wrestler_id TEXT PRIMARY KEY,
                template_id TEXT NOT NULL,
                custom_name TEXT,
                effectiveness INTEGER NOT NULL,
                assigned_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id),
                FOREIGN KEY (template_id) REFERENCES gimmick_templates(id)
            );
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entrance_configurations (
                id TEXT PRIMARY KEY,
                wrestler_id TEXT NOT NULL,
                name TEXT NOT NULL,
                settings_json TEXT NOT NULL,
                weekly_cost INTEGER NOT NULL,
                presentation_boost INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
            );
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS catchphrases (
                id TEXT PRIMARY KEY,
                wrestler_id TEXT NOT NULL,
                phrase_text TEXT NOT NULL,
                popularity_score INTEGER DEFAULT 50,
                usage_count INTEGER DEFAULT 0,
                created_date TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
            );
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS finisher_moves (
                id TEXT PRIMARY KEY,
                wrestler_id TEXT NOT NULL,
                move_name TEXT NOT NULL,
                move_type TEXT NOT NULL,
                protection_rating INTEGER DEFAULT 100,
                kickout_count INTEGER DEFAULT 0,
                successful_pin_count INTEGER DEFAULT 0,
                debut_date TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
            );
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signature_moves (
                id TEXT PRIMARY KEY,
                wrestler_id TEXT NOT NULL,
                move_name TEXT NOT NULL,
                sequence_position INTEGER NOT NULL,
                crowd_anticipation_level INTEGER DEFAULT 50,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
            );
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS character_evolution_events (
                id TEXT PRIMARY KEY,
                wrestler_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                previous_state TEXT,
                new_state TEXT NOT NULL,
                trigger_reason TEXT,
                readiness_score INTEGER DEFAULT 50,
                event_date TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
            );
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entrance_companions (
                id TEXT PRIMARY KEY,
                wrestler_id TEXT NOT NULL,
                companion_id TEXT NOT NULL,
                role TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT,
                interference_tendency INTEGER DEFAULT 20,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id),
                FOREIGN KEY (companion_id) REFERENCES wrestlers(id)
            );
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rating_history (
                id TEXT PRIMARY KEY,
                wrestler_id TEXT NOT NULL,
                attribute_name TEXT NOT NULL,
                old_value INTEGER NOT NULL,
                new_value INTEGER NOT NULL,
                change_reason TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
            );
        ''')

        for ddl in [
            "CREATE INDEX IF NOT EXISTS idx_alignment_turns_wrestler_date ON alignment_turns(wrestler_id, turn_date)",
            "CREATE INDEX IF NOT EXISTS idx_catchphrases_wrestler ON catchphrases(wrestler_id)",
            "CREATE INDEX IF NOT EXISTS idx_finisher_moves_wrestler ON finisher_moves(wrestler_id)",
            "CREATE INDEX IF NOT EXISTS idx_signature_moves_wrestler_order ON signature_moves(wrestler_id, sequence_position)",
            "CREATE INDEX IF NOT EXISTS idx_rating_history_wrestler_date ON rating_history(wrestler_id, recorded_at)",
            "CREATE INDEX IF NOT EXISTS idx_wrestlers_character_filters ON wrestlers(primary_brand, primary_wrestling_style, alignment_percentage)",
        ]:
            cursor.execute(ddl)

        from services.character_system_service import default_gimmick_templates, now_iso
        for template in default_gimmick_templates():
            now = now_iso()
            cursor.execute('''
                INSERT OR IGNORE INTO gimmick_templates (
                    id, name, description, default_alignment,
                    recommended_wrestling_style, base_popularity_modifier,
                    attributes_json, is_custom, version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 1, ?, ?)
            ''', (
                template['template_key'],
                template['name'],
                template['description'],
                template['default_alignment'],
                template['recommended_wrestling_style'],
                template['base_popularity_modifier'],
                json.dumps(template['attributes_json']),
                now,
                now,
            ))

        self.conn.commit()

    def _create_vanguard_development_tables(self) -> None:
        """Create normalized tables for ROC Vanguard and GM progression systems."""
        cursor = self.conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS brand_metadata (
                brand_name TEXT PRIMARY KEY,
                brand_tier TEXT NOT NULL,
                prestige_level INTEGER NOT NULL DEFAULT 50,
                roster_capacity INTEGER NOT NULL DEFAULT 40,
                revenue_tier TEXT NOT NULL DEFAULT 'regional',
                audience_profile TEXT NOT NULL DEFAULT '{}',
                development_focus TEXT NOT NULL DEFAULT '[]',
                parent_brand TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wrestler_evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wrestler_id TEXT NOT NULL,
                brand_name TEXT NOT NULL DEFAULT 'ROC Vanguard',
                evaluation_year INTEGER NOT NULL,
                evaluation_week INTEGER NOT NULL,
                in_ring_score INTEGER NOT NULL,
                promo_score INTEGER NOT NULL,
                character_score INTEGER NOT NULL,
                crowd_reaction_score INTEGER NOT NULL,
                aggregate_readiness_score INTEGER NOT NULL,
                readiness_status TEXT NOT NULL,
                scout_notes TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
            );
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS call_up_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wrestler_id TEXT NOT NULL,
                destination_brand TEXT NOT NULL,
                decision_status TEXT NOT NULL,
                decision_score INTEGER NOT NULL,
                performance_score INTEGER NOT NULL,
                creative_fit_score INTEGER NOT NULL,
                timing_score INTEGER NOT NULL,
                brand_need_score INTEGER NOT NULL,
                buzz_score INTEGER NOT NULL,
                decision_reason TEXT,
                target_year INTEGER,
                target_week INTEGER,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
            );
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trial_appearances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wrestler_id TEXT NOT NULL,
                destination_brand TEXT NOT NULL,
                trial_type TEXT NOT NULL,
                start_year INTEGER NOT NULL,
                start_week INTEGER NOT NULL,
                planned_appearances INTEGER NOT NULL,
                completed_appearances INTEGER NOT NULL DEFAULT 0,
                crowd_reaction_score INTEGER DEFAULT 50,
                match_quality_score INTEGER DEFAULT 50,
                social_buzz_score INTEGER DEFAULT 50,
                outcome TEXT NOT NULL DEFAULT 'active',
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
            );
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS call_ups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wrestler_id TEXT NOT NULL,
                source_brand TEXT NOT NULL DEFAULT 'ROC Vanguard',
                destination_brand TEXT NOT NULL,
                call_up_type TEXT NOT NULL DEFAULT 'solo',
                announcement_method TEXT NOT NULL DEFAULT 'general_manager_announcement',
                debut_scenario TEXT NOT NULL DEFAULT 'planned_match_debut',
                debut_year INTEGER NOT NULL,
                debut_week INTEGER NOT NULL,
                first_feud_target_id TEXT,
                first_feud_title TEXT,
                trajectory_status TEXT NOT NULL DEFAULT 'test_run',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
            );
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS failed_call_ups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wrestler_id TEXT NOT NULL,
                original_call_up_id INTEGER,
                failure_reason TEXT NOT NULL,
                response_option TEXT NOT NULL,
                comeback_phase TEXT NOT NULL DEFAULT 'rock_bottom',
                reinvention_notes TEXT,
                second_call_up_ready INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id),
                FOREIGN KEY (original_call_up_id) REFERENCES call_ups(id)
            );
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS general_managers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gm_name TEXT NOT NULL UNIQUE,
                current_brand TEXT NOT NULL,
                gm_tier TEXT NOT NULL,
                background TEXT NOT NULL DEFAULT 'former_wrestler',
                character_type TEXT NOT NULL DEFAULT 'fair_but_firm',
                mic_skill INTEGER NOT NULL DEFAULT 60,
                screen_presence INTEGER NOT NULL DEFAULT 60,
                crisis_management INTEGER NOT NULL DEFAULT 60,
                political_navigation INTEGER NOT NULL DEFAULT 50,
                executive_satisfaction INTEGER NOT NULL DEFAULT 50,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gm_evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gm_id INTEGER NOT NULL,
                evaluation_year INTEGER NOT NULL,
                evaluation_week INTEGER NOT NULL,
                show_performance INTEGER NOT NULL,
                crisis_management INTEGER NOT NULL,
                authority_presence INTEGER NOT NULL,
                locker_room_control INTEGER NOT NULL,
                political_alignment INTEGER NOT NULL,
                aggregate_score INTEGER NOT NULL,
                promotion_eligible INTEGER NOT NULL DEFAULT 0,
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (gm_id) REFERENCES general_managers(id)
            );
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gm_promotions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gm_id INTEGER NOT NULL,
                from_brand TEXT NOT NULL,
                to_brand TEXT NOT NULL,
                promotion_status TEXT NOT NULL DEFAULT 'shadowing',
                shadow_start_year INTEGER,
                shadow_start_week INTEGER,
                shadow_duration_weeks INTEGER NOT NULL DEFAULT 6,
                decision_reason TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (gm_id) REFERENCES general_managers(id)
            );
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_eval_wrestler_week ON wrestler_evaluations(wrestler_id, evaluation_year, evaluation_week)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_eval_brand_status ON wrestler_evaluations(brand_name, readiness_status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_call_up_decisions_status ON call_up_decisions(decision_status, destination_brand)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trials_wrestler_outcome ON trial_appearances(wrestler_id, outcome)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_call_ups_destination ON call_ups(destination_brand, debut_year, debut_week)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_failed_callups_phase ON failed_call_ups(comeback_phase)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_gm_brand_tier ON general_managers(current_brand, gm_tier)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_gm_evals_gm_week ON gm_evaluations(gm_id, evaluation_year, evaluation_week)')

        now = datetime.now().isoformat()
        brands = [
            ('ROC Vanguard', 'developmental', 45, 42, 'developmental', '["in_ring", "promo", "character", "crowd_connection"]', None),
            ('ROC Alpha', 'main_roster', 90, 55, 'global', '["main_event", "media", "premium_sponsors"]', 'ROC Vanguard'),
            ('ROC Velocity', 'main_roster', 82, 50, 'national', '["workrate", "weekly_tv", "rising_stars"]', 'ROC Vanguard'),
        ]
        cursor.executemany('''
            INSERT OR IGNORE INTO brand_metadata (
                brand_name, brand_tier, prestige_level, roster_capacity,
                revenue_tier, development_focus, parent_brand, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', [(name, tier, prestige, cap, revenue, focus, parent, now, now) for name, tier, prestige, cap, revenue, focus, parent in brands])

        self.conn.commit()
        print("âœ… Vanguard developmental and GM promotion tables created")
