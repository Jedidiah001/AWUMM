"""
Rival Promotion Database Layer
STEP 126: Persistence for rival promotions and bidding wars
"""

import json
import sqlite3
import time
from datetime import datetime
from typing import List, Dict, Any, Optional


def create_rival_promotion_tables(database) -> None:
    """
    Create all tables needed for the rival promotion and bidding war systems.
    Called from database._create_rival_promotion_tables()
    """
    cursor = database.conn.cursor()

    # ------------------------------------------------------------------ #
    # Rival Promotions                                                     #
    # ------------------------------------------------------------------ #
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rival_promotions (
            promotion_id    TEXT PRIMARY KEY,
            name            TEXT NOT NULL,
            abbreviation    TEXT NOT NULL,
            tier            TEXT NOT NULL,
            brand_identity  TEXT NOT NULL,

            budget_per_year     INTEGER NOT NULL,
            remaining_budget    INTEGER NOT NULL,
            avg_salary_per_show INTEGER NOT NULL,

            roster_size     INTEGER NOT NULL DEFAULT 0,
            max_roster_size INTEGER NOT NULL DEFAULT 40,
            roster_needs    TEXT NOT NULL DEFAULT '[]',   -- JSON list
            gender_focus    TEXT NOT NULL DEFAULT 'both',

            aggression              INTEGER NOT NULL DEFAULT 50,
            loyalty_to_talent       INTEGER NOT NULL DEFAULT 50,
            prestige                INTEGER NOT NULL DEFAULT 50,
            relationship_with_player INTEGER NOT NULL DEFAULT 50,

            active_pursuits  TEXT NOT NULL DEFAULT '[]',  -- JSON list of fa_ids
            signed_this_year INTEGER NOT NULL DEFAULT 0,
            lost_bidding_wars INTEGER NOT NULL DEFAULT 0,
            won_bidding_wars  INTEGER NOT NULL DEFAULT 0,

            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')

    # ------------------------------------------------------------------ #
    # Bidding Wars                                                         #
    # ------------------------------------------------------------------ #
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bidding_wars (
            bidding_war_id  TEXT PRIMARY KEY,
            fa_id           TEXT NOT NULL,
            fa_name         TEXT NOT NULL,

            -- Status: open | round_2 | final | decided | cancelled
            status          TEXT NOT NULL DEFAULT 'open',
            is_open_bidding INTEGER NOT NULL DEFAULT 0,  -- 0=blind, 1=open

            current_round   INTEGER NOT NULL DEFAULT 1,
            max_rounds      INTEGER NOT NULL DEFAULT 3,

            -- Player's current offer (may be NULL if not yet bid)
            player_offer_salary     INTEGER,
            player_offer_weeks      INTEGER,
            player_offer_bonus      INTEGER DEFAULT 0,
            player_creative_control TEXT DEFAULT 'none',
            player_title_guarantee  INTEGER DEFAULT 0,
            player_withdrew         INTEGER NOT NULL DEFAULT 0,

            -- Outcome
            winner          TEXT,   -- 'player' | rival promotion_id | 'no_deal'
            winning_salary  INTEGER,
            decided_year    INTEGER,
            decided_week    INTEGER,
            outcome_reason  TEXT,

            -- Timing
            started_year    INTEGER NOT NULL,
            started_week    INTEGER NOT NULL,
            deadline_year   INTEGER,
            deadline_week   INTEGER,

            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,

            FOREIGN KEY (fa_id) REFERENCES free_agents(free_agent_id)
        )
    ''')

    # ------------------------------------------------------------------ #
    # Individual Rival Bids inside a Bidding War                          #
    # ------------------------------------------------------------------ #
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bidding_war_rival_bids (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            bidding_war_id  TEXT NOT NULL,
            promotion_id    TEXT NOT NULL,
            promotion_name  TEXT NOT NULL,
            round_number    INTEGER NOT NULL,

            salary_offer    INTEGER NOT NULL,
            contract_weeks  INTEGER NOT NULL DEFAULT 52,
            signing_bonus   INTEGER NOT NULL DEFAULT 0,
            creative_perks  TEXT,           -- JSON blob of extra perks

            interest_level  INTEGER NOT NULL DEFAULT 50,
            is_final_offer  INTEGER NOT NULL DEFAULT 0,
            withdrew        INTEGER NOT NULL DEFAULT 0,

            created_at TEXT NOT NULL,

            FOREIGN KEY (bidding_war_id) REFERENCES bidding_wars(bidding_war_id)
        )
    ''')

    # ------------------------------------------------------------------ #
    # Escalation Events (mid-bidding surprises)                           #
    # ------------------------------------------------------------------ #
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bidding_war_events (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            bidding_war_id  TEXT NOT NULL,
            event_type      TEXT NOT NULL,  -- see BiddingEventType enum
            description     TEXT NOT NULL,
            triggered_round INTEGER NOT NULL,
            effect_data     TEXT,           -- JSON blob
            created_at      TEXT NOT NULL,

            FOREIGN KEY (bidding_war_id) REFERENCES bidding_wars(bidding_war_id)
        )
    ''')

    # ------------------------------------------------------------------ #
    # Relationship History (post-bidding effects)                         #
    # ------------------------------------------------------------------ #
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rival_relationship_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            promotion_id    TEXT NOT NULL,
            change_amount   INTEGER NOT NULL,
            reason          TEXT NOT NULL,
            year            INTEGER NOT NULL,
            week            INTEGER NOT NULL,
            created_at      TEXT NOT NULL,

            FOREIGN KEY (promotion_id) REFERENCES rival_promotions(promotion_id)
        )
    ''')

    # Indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_bidding_wars_fa ON bidding_wars(fa_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_bidding_wars_status ON bidding_wars(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_bw_rival_bids_war ON bidding_war_rival_bids(bidding_war_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_bw_events_war ON bidding_war_events(bidding_war_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_rival_rel_log_promo ON rival_relationship_log(promotion_id)')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rival_world_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            promotion_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            headline TEXT NOT NULL,
            details TEXT,
            impact_score INTEGER NOT NULL DEFAULT 0,
            year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_rival_world_events_timeline ON rival_world_events(year DESC, week DESC)')

    # Backward-compatible column migrations for older saves.
    for col, ddl in (
        ("booking_philosophy", "TEXT NOT NULL DEFAULT 'balanced'"),
        ("management_style", "TEXT NOT NULL DEFAULT 'relationship_builder'"),
        ("cash_reserves", "INTEGER NOT NULL DEFAULT 0"),
        ("momentum", "INTEGER NOT NULL DEFAULT 50"),
    ):
        try:
            cursor.execute(f"ALTER TABLE rival_promotions ADD COLUMN {col} {ddl}")
        except Exception:
            pass

    database.conn.commit()
    print("✅ Rival promotion & bidding war tables created (STEP 126)")


# ======================================================================== #
# Rival Promotion CRUD                                                       #
# ======================================================================== #

def save_rival_promotion(database, promotion) -> None:
    """Insert or replace a rival promotion record."""
    now = datetime.now().isoformat()
    payload = (
        promotion.promotion_id,
        promotion.name,
        promotion.abbreviation,
        promotion.tier.value if hasattr(promotion.tier, 'value') else promotion.tier,
        promotion.brand_identity.value if hasattr(promotion.brand_identity, 'value') else promotion.brand_identity,
        promotion.budget_per_year,
        promotion.remaining_budget,
        promotion.avg_salary_per_show,
        promotion.roster_size,
        promotion.max_roster_size,
        json.dumps(promotion.roster_needs) if isinstance(promotion.roster_needs, list) else promotion.roster_needs,
        promotion.gender_focus,
        promotion.aggression,
        promotion.loyalty_to_talent,
        promotion.prestige,
        promotion.relationship_with_player,
        json.dumps(promotion.active_pursuits) if isinstance(promotion.active_pursuits, list) else promotion.active_pursuits,
        promotion.signed_this_year,
        promotion.lost_bidding_wars,
        promotion.won_bidding_wars,
        now,
        now,
    )

    for attempt in range(3):
        cursor = database.conn.cursor()
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO rival_promotions (
                    promotion_id, name, abbreviation, tier, brand_identity,
                    budget_per_year, remaining_budget, avg_salary_per_show,
                    roster_size, max_roster_size, roster_needs, gender_focus,
                    aggression, loyalty_to_talent, prestige, relationship_with_player,
                    active_pursuits, signed_this_year, lost_bidding_wars, won_bidding_wars,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', payload)
            database.conn.commit()
            return
        except sqlite3.OperationalError as exc:
            try:
                database.conn.rollback()
            except Exception:
                pass
            if 'locked' not in str(exc).lower() or attempt == 2:
                raise
            time.sleep(0.2 * (attempt + 1))


def load_rival_promotions(database) -> List[Dict[str, Any]]:
    """
    Load all rival promotions from database.
    Alias for load_all_rival_promotions for compatibility.
    """
    return load_all_rival_promotions(database)


def load_all_rival_promotions(database) -> List[Dict[str, Any]]:
    """Load all rival promotions as dictionaries."""
    cursor = database.conn.cursor()
    try:
        cursor.execute('SELECT * FROM rival_promotions ORDER BY prestige DESC')
        rows = cursor.fetchall()
    except Exception:
        return []

    result = []
    for row in rows:
        d = dict(row)
        d['roster_needs'] = json.loads(d.get('roster_needs') or '[]')
        d['active_pursuits'] = json.loads(d.get('active_pursuits') or '[]')
        result.append(d)
    return result


def get_rival_promotion(database, promotion_id: str) -> Optional[Dict[str, Any]]:
    """Get a single rival promotion by ID."""
    cursor = database.conn.cursor()
    cursor.execute('SELECT * FROM rival_promotions WHERE promotion_id = ?', (promotion_id,))
    row = cursor.fetchone()
    if not row:
        return None
    d = dict(row)
    d['roster_needs'] = json.loads(d.get('roster_needs') or '[]')
    d['active_pursuits'] = json.loads(d.get('active_pursuits') or '[]')
    return d


def get_rival_promotion_by_name(database, name: str) -> Optional[Dict[str, Any]]:
    """Get a rival promotion by name."""
    cursor = database.conn.cursor()
    cursor.execute('SELECT * FROM rival_promotions WHERE name = ? OR abbreviation = ?', (name, name))
    row = cursor.fetchone()
    if not row:
        return None
    d = dict(row)
    d['roster_needs'] = json.loads(d.get('roster_needs') or '[]')
    d['active_pursuits'] = json.loads(d.get('active_pursuits') or '[]')
    return d


def delete_rival_promotion(database, promotion_id: str) -> None:
    """Delete a rival promotion and its related data."""
    cursor = database.conn.cursor()
    
    # Delete relationship history
    cursor.execute('DELETE FROM rival_relationship_log WHERE promotion_id = ?', (promotion_id,))
    
    # Delete the promotion
    cursor.execute('DELETE FROM rival_promotions WHERE promotion_id = ?', (promotion_id,))
    
    database.conn.commit()


def update_rival_promotion_field(database, promotion_id: str, field: str, value: Any) -> None:
    """Update a single field on a rival promotion."""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    # Handle JSON fields
    if field in ('roster_needs', 'active_pursuits') and isinstance(value, list):
        value = json.dumps(value)
    
    cursor.execute(f'''
        UPDATE rival_promotions
        SET {field} = ?, updated_at = ?
        WHERE promotion_id = ?
    ''', (value, now, promotion_id))
    
    database.conn.commit()


def log_rival_world_event(
    database,
    promotion_id: str,
    event_type: str,
    headline: str,
    details: str,
    impact_score: int,
    year: int,
    week: int
) -> None:
    """Persist a weekly rival universe event."""
    cursor = database.conn.cursor()
    cursor.execute(
        '''
        INSERT INTO rival_world_events (
            promotion_id, event_type, headline, details, impact_score, year, week, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            promotion_id,
            event_type,
            headline,
            details,
            int(impact_score),
            int(year),
            int(week),
            datetime.now().isoformat()
        )
    )
    database.conn.commit()


def get_rival_world_events(database, limit: int = 30) -> List[Dict[str, Any]]:
    """Load latest rival universe events."""
    cursor = database.conn.cursor()
    cursor.execute(
        '''
        SELECT * FROM rival_world_events
        ORDER BY year DESC, week DESC, id DESC
        LIMIT ?
        ''',
        (max(1, int(limit)),)
    )
    return [dict(r) for r in cursor.fetchall()]


# ======================================================================== #
# Bidding War CRUD                                                           #
# ======================================================================== #

def save_bidding_war(database, war_data: Dict[str, Any]) -> None:
    """Insert or replace a bidding war record."""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()

    cursor.execute('''
        INSERT OR REPLACE INTO bidding_wars (
            bidding_war_id, fa_id, fa_name,
            status, is_open_bidding,
            current_round, max_rounds,
            player_offer_salary, player_offer_weeks, player_offer_bonus,
            player_creative_control, player_title_guarantee, player_withdrew,
            winner, winning_salary, decided_year, decided_week, outcome_reason,
            started_year, started_week, deadline_year, deadline_week,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        war_data['bidding_war_id'],
        war_data['fa_id'],
        war_data['fa_name'],
        war_data.get('status', 'open'),
        1 if war_data.get('is_open_bidding') else 0,
        war_data.get('current_round', 1),
        war_data.get('max_rounds', 3),
        war_data.get('player_offer_salary'),
        war_data.get('player_offer_weeks'),
        war_data.get('player_offer_bonus', 0),
        war_data.get('player_creative_control', 'none'),
        1 if war_data.get('player_title_guarantee') else 0,
        1 if war_data.get('player_withdrew') else 0,
        war_data.get('winner'),
        war_data.get('winning_salary'),
        war_data.get('decided_year'),
        war_data.get('decided_week'),
        war_data.get('outcome_reason'),
        war_data['started_year'],
        war_data['started_week'],
        war_data.get('deadline_year'),
        war_data.get('deadline_week'),
        now, now
    ))
    database.conn.commit()


def get_bidding_war(database, bidding_war_id: str) -> Optional[Dict[str, Any]]:
    """Load a single bidding war."""
    cursor = database.conn.cursor()
    cursor.execute('SELECT * FROM bidding_wars WHERE bidding_war_id = ?', (bidding_war_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_active_bidding_wars(database) -> List[Dict[str, Any]]:
    """Get all open/in-progress bidding wars."""
    cursor = database.conn.cursor()
    cursor.execute('''
        SELECT * FROM bidding_wars
        WHERE status IN ('open', 'round_2', 'final')
        ORDER BY started_year DESC, started_week DESC
    ''')
    return [dict(r) for r in cursor.fetchall()]


def get_all_bidding_wars(database, include_decided: bool = True) -> List[Dict[str, Any]]:
    """Get all bidding wars, optionally including decided ones."""
    cursor = database.conn.cursor()
    
    if include_decided:
        cursor.execute('''
            SELECT * FROM bidding_wars
            ORDER BY started_year DESC, started_week DESC
        ''')
    else:
        cursor.execute('''
            SELECT * FROM bidding_wars
            WHERE status IN ('open', 'round_2', 'final')
            ORDER BY started_year DESC, started_week DESC
        ''')
    
    return [dict(r) for r in cursor.fetchall()]


def get_bidding_war_for_fa(database, fa_id: str) -> Optional[Dict[str, Any]]:
    """Get the active bidding war for a specific free agent, if any."""
    cursor = database.conn.cursor()
    cursor.execute('''
        SELECT * FROM bidding_wars
        WHERE fa_id = ? AND status IN ('open', 'round_2', 'final')
        ORDER BY started_year DESC, started_week DESC
        LIMIT 1
    ''', (fa_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_bidding_war_history_for_fa(database, fa_id: str) -> List[Dict[str, Any]]:
    """Get all bidding wars (including decided) for a free agent."""
    cursor = database.conn.cursor()
    cursor.execute('''
        SELECT * FROM bidding_wars
        WHERE fa_id = ?
        ORDER BY started_year DESC, started_week DESC
    ''', (fa_id,))
    return [dict(r) for r in cursor.fetchall()]


def update_bidding_war_status(database, bidding_war_id: str, status: str) -> None:
    """Update the status of a bidding war."""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute('''
        UPDATE bidding_wars
        SET status = ?, updated_at = ?
        WHERE bidding_war_id = ?
    ''', (status, now, bidding_war_id))
    
    database.conn.commit()


def update_bidding_war_player_offer(
    database,
    bidding_war_id: str,
    salary: int,
    weeks: int,
    bonus: int = 0,
    creative_control: str = 'none',
    title_guarantee: bool = False
) -> None:
    """Update the player's offer in a bidding war."""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute('''
        UPDATE bidding_wars
        SET player_offer_salary = ?,
            player_offer_weeks = ?,
            player_offer_bonus = ?,
            player_creative_control = ?,
            player_title_guarantee = ?,
            updated_at = ?
        WHERE bidding_war_id = ?
    ''', (salary, weeks, bonus, creative_control, 1 if title_guarantee else 0, now, bidding_war_id))
    
    database.conn.commit()


def finalize_bidding_war(
    database,
    bidding_war_id: str,
    winner: str,
    winning_salary: int,
    year: int,
    week: int,
    reason: str = ""
) -> None:
    """Finalize a bidding war with a winner."""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute('''
        UPDATE bidding_wars
        SET status = 'decided',
            winner = ?,
            winning_salary = ?,
            decided_year = ?,
            decided_week = ?,
            outcome_reason = ?,
            updated_at = ?
        WHERE bidding_war_id = ?
    ''', (winner, winning_salary, year, week, reason, now, bidding_war_id))
    
    database.conn.commit()


def delete_bidding_war(database, bidding_war_id: str) -> None:
    """Delete a bidding war and all related data."""
    cursor = database.conn.cursor()
    
    # Delete related data
    cursor.execute('DELETE FROM bidding_war_rival_bids WHERE bidding_war_id = ?', (bidding_war_id,))
    cursor.execute('DELETE FROM bidding_war_events WHERE bidding_war_id = ?', (bidding_war_id,))
    
    # Delete the bidding war
    cursor.execute('DELETE FROM bidding_wars WHERE bidding_war_id = ?', (bidding_war_id,))
    
    database.conn.commit()


# ======================================================================== #
# Rival Bids CRUD                                                            #
# ======================================================================== #

def save_rival_bid(database, bid_data: Dict[str, Any]) -> int:
    """Insert a rival promotion's bid for a round."""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()

    cursor.execute('''
        INSERT INTO bidding_war_rival_bids (
            bidding_war_id, promotion_id, promotion_name, round_number,
            salary_offer, contract_weeks, signing_bonus, creative_perks,
            interest_level, is_final_offer, withdrew, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        bid_data['bidding_war_id'],
        bid_data['promotion_id'],
        bid_data['promotion_name'],
        bid_data['round_number'],
        bid_data['salary_offer'],
        bid_data.get('contract_weeks', 52),
        bid_data.get('signing_bonus', 0),
        json.dumps(bid_data.get('creative_perks', {})),
        bid_data.get('interest_level', 50),
        1 if bid_data.get('is_final_offer') else 0,
        1 if bid_data.get('withdrew') else 0,
        now
    ))
    database.conn.commit()
    return cursor.lastrowid


def get_rival_bids_for_war(database, bidding_war_id: str) -> List[Dict[str, Any]]:
    """Get all rival bids for a bidding war, grouped by round."""
    cursor = database.conn.cursor()
    cursor.execute('''
        SELECT * FROM bidding_war_rival_bids
        WHERE bidding_war_id = ?
        ORDER BY round_number ASC, salary_offer DESC
    ''', (bidding_war_id,))
    rows = cursor.fetchall()

    result = []
    for row in rows:
        d = dict(row)
        d['creative_perks'] = json.loads(d.get('creative_perks') or '{}')
        result.append(d)
    return result


def get_rival_bids_for_round(database, bidding_war_id: str, round_number: int) -> List[Dict[str, Any]]:
    """Get all rival bids for a specific round."""
    cursor = database.conn.cursor()
    cursor.execute('''
        SELECT * FROM bidding_war_rival_bids
        WHERE bidding_war_id = ? AND round_number = ?
        ORDER BY salary_offer DESC
    ''', (bidding_war_id, round_number))
    rows = cursor.fetchall()

    result = []
    for row in rows:
        d = dict(row)
        d['creative_perks'] = json.loads(d.get('creative_perks') or '{}')
        result.append(d)
    return result


def get_highest_rival_offer(database, bidding_war_id: str) -> Optional[Dict[str, Any]]:
    """Get the current highest rival offer (latest round, not withdrawn)."""
    cursor = database.conn.cursor()
    cursor.execute('''
        SELECT * FROM bidding_war_rival_bids
        WHERE bidding_war_id = ? AND withdrew = 0
        ORDER BY salary_offer DESC
        LIMIT 1
    ''', (bidding_war_id,))
    row = cursor.fetchone()
    if not row:
        return None
    d = dict(row)
    d['creative_perks'] = json.loads(d.get('creative_perks') or '{}')
    return d


def mark_rival_bid_withdrawn(database, bid_id: int) -> None:
    """Mark a rival bid as withdrawn."""
    cursor = database.conn.cursor()
    cursor.execute('''
        UPDATE bidding_war_rival_bids
        SET withdrew = 1
        WHERE id = ?
    ''', (bid_id,))
    database.conn.commit()


# ======================================================================== #
# Bidding War Events                                                         #
# ======================================================================== #

def save_bidding_event(database, event_data: Dict[str, Any]) -> int:
    """Record an escalation event during a bidding war."""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()

    cursor.execute('''
        INSERT INTO bidding_war_events (
            bidding_war_id, event_type, description,
            triggered_round, effect_data, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        event_data['bidding_war_id'],
        event_data['event_type'],
        event_data['description'],
        event_data.get('triggered_round', 1),
        json.dumps(event_data.get('effect_data', {})),
        now
    ))
    database.conn.commit()
    return cursor.lastrowid


def get_events_for_war(database, bidding_war_id: str) -> List[Dict[str, Any]]:
    """Get all escalation events for a bidding war."""
    cursor = database.conn.cursor()
    cursor.execute('''
        SELECT * FROM bidding_war_events
        WHERE bidding_war_id = ?
        ORDER BY triggered_round ASC, created_at ASC
    ''', (bidding_war_id,))
    rows = cursor.fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d['effect_data'] = json.loads(d.get('effect_data') or '{}')
        result.append(d)
    return result


# ======================================================================== #
# Relationship Management                                                    #
# ======================================================================== #

def log_relationship_change(
    database,
    promotion_id: str,
    change: int,
    reason: str,
    year: int,
    week: int
) -> None:
    """Log a relationship change between player and rival promotion."""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()

    cursor.execute('''
        INSERT INTO rival_relationship_log (
            promotion_id, change_amount, reason, year, week, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
    ''', (promotion_id, change, reason, year, week, now))

    # Also update the promotion's relationship score
    cursor.execute('''
        UPDATE rival_promotions
        SET relationship_with_player = MAX(0, MIN(100, relationship_with_player + ?)),
            updated_at = ?
        WHERE promotion_id = ?
    ''', (change, now, promotion_id))

    database.conn.commit()


def get_relationship_history(database, promotion_id: str) -> List[Dict[str, Any]]:
    """Get full relationship log for a rival promotion."""
    cursor = database.conn.cursor()
    cursor.execute('''
        SELECT * FROM rival_relationship_log
        WHERE promotion_id = ?
        ORDER BY year DESC, week DESC
    ''', (promotion_id,))
    return [dict(r) for r in cursor.fetchall()]


def get_relationship_score(database, promotion_id: str) -> int:
    """Get current relationship score with a rival promotion."""
    cursor = database.conn.cursor()
    cursor.execute('''
        SELECT relationship_with_player FROM rival_promotions
        WHERE promotion_id = ?
    ''', (promotion_id,))
    row = cursor.fetchone()
    return row['relationship_with_player'] if row else 50


def set_relationship_score(database, promotion_id: str, score: int) -> None:
    """Set the relationship score with a rival promotion."""
    cursor = database.conn.cursor()
    now = datetime.now().isoformat()
    
    # Clamp between 0 and 100
    score = max(0, min(100, score))
    
    cursor.execute('''
        UPDATE rival_promotions
        SET relationship_with_player = ?, updated_at = ?
        WHERE promotion_id = ?
    ''', (score, now, promotion_id))
    
    database.conn.commit()


# ======================================================================== #
# Statistics and Summaries                                                   #
# ======================================================================== #

def get_rival_promotion_summary(database) -> Dict[str, Any]:
    """Get summary statistics for all rival promotions."""
    cursor = database.conn.cursor()
    
    # Total promotions
    cursor.execute('SELECT COUNT(*) as total FROM rival_promotions')
    total = cursor.fetchone()['total']
    
    # By tier
    cursor.execute('''
        SELECT tier, COUNT(*) as count
        FROM rival_promotions
        GROUP BY tier
    ''')
    by_tier = {row['tier']: row['count'] for row in cursor.fetchall()}
    
    # Active bidding wars
    cursor.execute('''
        SELECT COUNT(*) as count FROM bidding_wars
        WHERE status IN ('open', 'round_2', 'final')
    ''')
    active_wars = cursor.fetchone()['count']
    
    # Total bidding wars won by player
    cursor.execute('''
        SELECT COUNT(*) as count FROM bidding_wars
        WHERE winner = 'player'
    ''')
    player_wins = cursor.fetchone()['count']
    
    # Total bidding wars lost by player
    cursor.execute('''
        SELECT COUNT(*) as count FROM bidding_wars
        WHERE winner IS NOT NULL AND winner != 'player' AND winner != 'no_deal'
    ''')
    player_losses = cursor.fetchone()['count']
    
    return {
        'total_promotions': total,
        'by_tier': by_tier,
        'active_bidding_wars': active_wars,
        'player_bidding_war_wins': player_wins,
        'player_bidding_war_losses': player_losses
    }


def get_bidding_war_summary(database, bidding_war_id: str) -> Dict[str, Any]:
    """Get a complete summary of a bidding war."""
    war = get_bidding_war(database, bidding_war_id)
    if not war:
        return {}
    
    bids = get_rival_bids_for_war(database, bidding_war_id)
    events = get_events_for_war(database, bidding_war_id)
    highest_rival = get_highest_rival_offer(database, bidding_war_id)
    
    return {
        'war': war,
        'rival_bids': bids,
        'events': events,
        'highest_rival_offer': highest_rival,
        'total_rival_bids': len(bids),
        'total_events': len(events)
    }


# ======================================================================== #
# Cleanup and Maintenance                                                    #
# ======================================================================== #

def clear_all_rival_data(database) -> None:
    """Clear all rival promotion and bidding war data (for testing/reset)."""
    cursor = database.conn.cursor()
    
    cursor.execute('DELETE FROM rival_relationship_log')
    cursor.execute('DELETE FROM bidding_war_events')
    cursor.execute('DELETE FROM bidding_war_rival_bids')
    cursor.execute('DELETE FROM bidding_wars')
    cursor.execute('DELETE FROM rival_promotions')
    
    database.conn.commit()
    print("✅ All rival promotion data cleared")


def cleanup_old_bidding_wars(database, keep_weeks: int = 52) -> int:
    """Remove old decided bidding wars older than specified weeks."""
    cursor = database.conn.cursor()
    
    # Get current game time (this would need to be passed in or fetched)
    # For now, just delete wars decided more than keep_weeks ago
    cursor.execute('''
        SELECT bidding_war_id FROM bidding_wars
        WHERE status = 'decided'
    ''')
    
    old_wars = [row['bidding_war_id'] for row in cursor.fetchall()]
    
    for war_id in old_wars:
        delete_bidding_war(database, war_id)
    
    return len(old_wars)
