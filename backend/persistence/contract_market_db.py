"""Persistent contract market tables for signing, releasing, and rival strategy."""

from __future__ import annotations


UP_SQL = """
CREATE TABLE IF NOT EXISTS contract_market_reputation (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    reputation_score REAL NOT NULL DEFAULT 62,
    trust_score REAL NOT NULL DEFAULT 62,
    last_reason TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS contract_market_negotiations (
    id TEXT PRIMARY KEY,
    target_type TEXT NOT NULL,
    wrestler_id TEXT,
    wrestler_name TEXT NOT NULL,
    free_agent_id TEXT,
    status TEXT NOT NULL,
    outcome TEXT,
    contract_type TEXT NOT NULL,
    offered_salary INTEGER NOT NULL DEFAULT 0,
    demanded_salary INTEGER NOT NULL DEFAULT 0,
    counter_salary INTEGER,
    contract_weeks INTEGER NOT NULL DEFAULT 52,
    signing_bonus INTEGER NOT NULL DEFAULT 0,
    market_value INTEGER NOT NULL DEFAULT 0,
    popularity INTEGER NOT NULL DEFAULT 50,
    morale INTEGER NOT NULL DEFAULT 50,
    agent_name TEXT,
    agent_leverage REAL NOT NULL DEFAULT 0,
    promotion_reputation REAL NOT NULL DEFAULT 50,
    acceptance_score REAL NOT NULL DEFAULT 0,
    refusal_reason TEXT,
    clauses_json TEXT NOT NULL DEFAULT '{}',
    demands_json TEXT NOT NULL DEFAULT '{}',
    response_json TEXT NOT NULL DEFAULT '{}',
    year INTEGER NOT NULL DEFAULT 1,
    week INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS contract_market_deals (
    id TEXT PRIMARY KEY,
    negotiation_id TEXT,
    wrestler_id TEXT,
    wrestler_name TEXT NOT NULL,
    free_agent_id TEXT,
    contract_type TEXT NOT NULL,
    salary_per_show INTEGER NOT NULL,
    contract_weeks INTEGER NOT NULL,
    weeks_remaining INTEGER NOT NULL,
    signing_bonus INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    release_reason TEXT,
    release_cost INTEGER NOT NULL DEFAULT 0,
    no_compete_until_year INTEGER,
    no_compete_until_week INTEGER,
    clauses_json TEXT NOT NULL DEFAULT '{}',
    signed_year INTEGER NOT NULL,
    signed_week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (negotiation_id) REFERENCES contract_market_negotiations(id)
);

CREATE TABLE IF NOT EXISTS contract_market_handshake_deals (
    id TEXT PRIMARY KEY,
    wrestler_id TEXT,
    wrestler_name TEXT NOT NULL,
    free_agent_id TEXT,
    promised_terms_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending',
    trust_delta REAL NOT NULL DEFAULT 0,
    morale_delta REAL NOT NULL DEFAULT 0,
    consequence_json TEXT NOT NULL DEFAULT '{}',
    year INTEGER NOT NULL DEFAULT 1,
    week INTEGER NOT NULL DEFAULT 1,
    resolved_year INTEGER,
    resolved_week INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rival_strategy_events (
    id TEXT PRIMARY KEY,
    promotion_id TEXT,
    promotion_name TEXT NOT NULL,
    event_type TEXT NOT NULL,
    target_type TEXT,
    target_id TEXT,
    target_name TEXT,
    details_json TEXT NOT NULL DEFAULT '{}',
    impact_score REAL NOT NULL DEFAULT 0,
    year INTEGER NOT NULL DEFAULT 1,
    week INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_contract_market_negotiations_target
    ON contract_market_negotiations(target_type, wrestler_id, free_agent_id);
CREATE INDEX IF NOT EXISTS idx_contract_market_negotiations_status
    ON contract_market_negotiations(status, year, week);
CREATE INDEX IF NOT EXISTS idx_contract_market_deals_wrestler
    ON contract_market_deals(wrestler_id, status);
CREATE INDEX IF NOT EXISTS idx_contract_market_handshakes_status
    ON contract_market_handshake_deals(status, year, week);
CREATE INDEX IF NOT EXISTS idx_rival_strategy_events_timeline
    ON rival_strategy_events(year DESC, week DESC);
"""


def create_contract_market_tables(database) -> None:
    cursor = database.conn.cursor()
    cursor.executescript(UP_SQL)

    for column, ddl in (
        ("contract_type", "TEXT NOT NULL DEFAULT 'full_time'"),
        ("release_clause_amount", "INTEGER NOT NULL DEFAULT 0"),
        ("no_compete_weeks", "INTEGER NOT NULL DEFAULT 0"),
        ("creative_control_clause", "TEXT NOT NULL DEFAULT 'none'"),
    ):
        try:
            cursor.execute(f"ALTER TABLE wrestlers ADD COLUMN {column} {ddl}")
        except Exception:
            pass

    cursor.execute(
        """
        INSERT OR IGNORE INTO contract_market_reputation (
            id, reputation_score, trust_score, last_reason, updated_at
        ) VALUES (1, 62, 62, 'Initial market reputation', datetime('now'))
        """
    )
    database.conn.commit()
    print("[OK] Contract market tables created")

