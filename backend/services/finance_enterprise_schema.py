"""Schema helpers for finance-integrated sponsorship, venue, and tour systems."""

from __future__ import annotations

from datetime import datetime
import sqlite3
import threading


VENUE_COLUMNS = {
    "venue_type": "TEXT NOT NULL DEFAULT 'Arena'",
    "city": "TEXT NOT NULL DEFAULT ''",
    "state": "TEXT NOT NULL DEFAULT ''",
    "country": "TEXT NOT NULL DEFAULT 'United States'",
    "wrestling_capacity": "INTEGER NOT NULL DEFAULT 12000",
    "ownership": "TEXT NOT NULL DEFAULT 'third-party'",
    "latitude": "REAL",
    "longitude": "REAL",
    "prestige_score": "INTEGER NOT NULL DEFAULT 70",
    "historical_attendance": "INTEGER NOT NULL DEFAULT 0",
    "historical_revenue": "INTEGER NOT NULL DEFAULT 0",
    "updated_at": "TEXT",
    "deleted_at": "TEXT",
}


NAMED_VENUES = [
    ("venue_msg", "city_001", "Madison Square Garden", "Arena", 19812, 185000, "Arena", "New York", "NY", "United States", 19000, "third-party", 40.7505, -73.9934, 98),
    ("venue_td_garden", "city_020", "TD Garden", "Arena", 19580, 145000, "Arena", "Boston", "MA", "United States", 17800, "third-party", 42.3662, -71.0621, 92),
    ("venue_wells_fargo", "city_006", "Wells Fargo Center", "Arena", 19500, 132000, "Arena", "Philadelphia", "PA", "United States", 17600, "third-party", 39.9012, -75.1720, 90),
    ("venue_united_center", "city_003", "United Center", "Arena", 20917, 150000, "Arena", "Chicago", "IL", "United States", 19000, "third-party", 41.8807, -87.6742, 93),
    ("venue_tmobile_arena", "city_023", "T-Mobile Arena", "Arena", 20000, 165000, "Arena", "Las Vegas", "NV", "United States", 18500, "third-party", 36.1028, -115.1785, 94),
]

_schema_lock = threading.Lock()


def ensure_finance_enterprise_tables(database) -> None:
    """Create tables, compatibility columns, indexes, and lightweight seed data."""
    if getattr(database, "_finance_enterprise_schema_ready", False):
        return

    with _schema_lock:
        if getattr(database, "_finance_enterprise_schema_ready", False):
            return

        cursor = database.conn.cursor()
        now = datetime.now().isoformat()
        _create_tables(cursor)
        _ensure_venue_columns(cursor)
        _create_indexes(cursor)
        _seed_accounts(cursor, now)
        _seed_named_venues(cursor, now)
        _seed_budgets(cursor, now)
        database.conn.commit()
        database._finance_enterprise_schema_ready = True


def _create_tables(cursor) -> None:
    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS finance_accounts (
            account_code TEXT PRIMARY KEY,
            account_name TEXT NOT NULL,
            account_type TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS finance_transactions (
            id TEXT PRIMARY KEY,
            transaction_date TEXT NOT NULL,
            posting_date TEXT NOT NULL,
            amount INTEGER NOT NULL,
            type TEXT NOT NULL,
            category TEXT NOT NULL,
            source_module TEXT NOT NULL,
            source_id TEXT,
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            account_code TEXT NOT NULL,
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (account_code) REFERENCES finance_accounts(account_code)
        );
        CREATE TABLE IF NOT EXISTS finance_budgets (
            id TEXT PRIMARY KEY,
            period TEXT NOT NULL,
            category TEXT NOT NULL,
            baseline_amount INTEGER NOT NULL,
            stretch_amount INTEGER NOT NULL,
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS finance_settlements (
            id TEXT PRIMARY KEY,
            settlement_type TEXT NOT NULL,
            source_id TEXT NOT NULL,
            period TEXT NOT NULL,
            revenue_total INTEGER NOT NULL,
            expense_total INTEGER NOT NULL,
            profit INTEGER NOT NULL,
            margin_pct REAL NOT NULL,
            status TEXT NOT NULL,
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS finance_reports (
            id TEXT PRIMARY KEY,
            report_type TEXT NOT NULL,
            period TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sponsors (
            sponsor_id TEXT PRIMARY KEY,
            company_name TEXT NOT NULL,
            logo_url TEXT DEFAULT '',
            industry_category TEXT NOT NULL,
            tier_level TEXT NOT NULL,
            brand_value INTEGER NOT NULL DEFAULT 50,
            market_reputation_score INTEGER NOT NULL DEFAULT 50,
            contact_name TEXT DEFAULT '',
            contact_email TEXT DEFAULT '',
            contact_phone TEXT DEFAULT '',
            satisfaction_score INTEGER NOT NULL DEFAULT 75,
            historical_partnerships TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            deleted_at TEXT
        );
        CREATE TABLE IF NOT EXISTS sponsorship_contracts (
            contract_id TEXT PRIMARY KEY,
            sponsor_id TEXT NOT NULL,
            contract_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Active',
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            duration_months INTEGER NOT NULL,
            total_value INTEGER NOT NULL,
            payment_schedule TEXT NOT NULL,
            exclusivity_clause TEXT DEFAULT '',
            territory TEXT DEFAULT 'Global',
            renewal_option TEXT DEFAULT '',
            performance_bonus INTEGER NOT NULL DEFAULT 0,
            termination_penalty INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            deleted_at TEXT,
            FOREIGN KEY (sponsor_id) REFERENCES sponsors(sponsor_id)
        );
        CREATE TABLE IF NOT EXISTS sponsorship_requirements (
            requirement_id TEXT PRIMARY KEY,
            contract_id TEXT NOT NULL,
            requirement_type TEXT NOT NULL,
            description TEXT NOT NULL,
            target_value REAL NOT NULL,
            unit TEXT NOT NULL,
            cadence TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            deleted_at TEXT,
            FOREIGN KEY (contract_id) REFERENCES sponsorship_contracts(contract_id)
        );
        CREATE TABLE IF NOT EXISTS sponsorship_deliverable_tracking (
            tracking_id TEXT PRIMARY KEY,
            requirement_id TEXT NOT NULL,
            event_id TEXT,
            event_name TEXT,
            delivered_value REAL NOT NULL,
            notes TEXT DEFAULT '',
            delivered_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (requirement_id) REFERENCES sponsorship_requirements(requirement_id)
        );
        CREATE TABLE IF NOT EXISTS sponsorship_controversies (
            controversy_id TEXT PRIMARY KEY,
            sponsor_id TEXT NOT NULL,
            contract_id TEXT,
            incident_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            description TEXT NOT NULL,
            impact_score INTEGER NOT NULL,
            threat_level TEXT NOT NULL,
            response_required TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            resolved_at TEXT,
            FOREIGN KEY (sponsor_id) REFERENCES sponsors(sponsor_id)
        );
        CREATE TABLE IF NOT EXISTS sponsorship_transactions (
            sponsorship_transaction_id TEXT PRIMARY KEY,
            contract_id TEXT NOT NULL,
            finance_transaction_id TEXT NOT NULL,
            transaction_kind TEXT NOT NULL,
            amount INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (contract_id) REFERENCES sponsorship_contracts(contract_id),
            FOREIGN KEY (finance_transaction_id) REFERENCES finance_transactions(id)
        );
        CREATE TABLE IF NOT EXISTS sponsorship_communications (
            communication_id TEXT PRIMARY KEY,
            sponsor_id TEXT NOT NULL,
            communication_type TEXT NOT NULL,
            summary TEXT NOT NULL,
            owner TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (sponsor_id) REFERENCES sponsors(sponsor_id)
        );
        CREATE TABLE IF NOT EXISTS venue_facilities (
            facility_id TEXT PRIMARY KEY,
            venue_id TEXT NOT NULL,
            facility_type TEXT NOT NULL,
            quality_score INTEGER NOT NULL,
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS venue_upgrades (
            upgrade_id TEXT PRIMARY KEY,
            venue_id TEXT NOT NULL,
            upgrade_category TEXT NOT NULL,
            upgrade_name TEXT NOT NULL,
            upfront_cost INTEGER NOT NULL,
            maintenance_cost INTEGER NOT NULL,
            expected_revenue_increase INTEGER NOT NULL,
            capacity_increase INTEGER NOT NULL DEFAULT 0,
            premium_revenue_boost INTEGER NOT NULL DEFAULT 0,
            roi_events INTEGER NOT NULL,
            purchased_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tours (
            tour_id TEXT PRIMARY KEY,
            tour_name TEXT NOT NULL,
            theme TEXT DEFAULT '',
            tour_type TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            roster_assignment TEXT DEFAULT '',
            budget_allocation INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'Planning',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            deleted_at TEXT
        );
        CREATE TABLE IF NOT EXISTS tour_events (
            event_id TEXT PRIMARY KEY,
            tour_id TEXT,
            venue_id TEXT NOT NULL,
            event_name TEXT NOT NULL,
            event_type TEXT NOT NULL,
            event_date TEXT NOT NULL,
            sequence_no INTEGER NOT NULL,
            projected_revenue INTEGER NOT NULL,
            projected_expenses INTEGER NOT NULL,
            projected_profit INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Scheduled',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tour_routing (
            route_id TEXT PRIMARY KEY,
            tour_id TEXT NOT NULL,
            from_event_id TEXT,
            to_event_id TEXT NOT NULL,
            distance_miles REAL NOT NULL,
            travel_cost INTEGER NOT NULL,
            travel_mode TEXT NOT NULL,
            rest_day_required INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS venue_performance_history (
            history_id TEXT PRIMARY KEY,
            venue_id TEXT NOT NULL,
            event_id TEXT,
            attendance INTEGER NOT NULL,
            revenue INTEGER NOT NULL,
            expenses INTEGER NOT NULL,
            profit INTEGER NOT NULL,
            sell_through_pct REAL NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS event_financials (
            financial_id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL UNIQUE,
            ticket_sales INTEGER NOT NULL,
            merchandise_sales INTEGER NOT NULL,
            concession_revenue INTEGER NOT NULL,
            parking_vip_revenue INTEGER NOT NULL DEFAULT 0,
            local_sponsorship_revenue INTEGER NOT NULL DEFAULT 0,
            venue_rental INTEGER NOT NULL,
            production_costs INTEGER NOT NULL,
            talent_costs INTEGER NOT NULL,
            travel_costs INTEGER NOT NULL,
            marketing_costs INTEGER NOT NULL,
            total_revenue INTEGER NOT NULL,
            total_expenses INTEGER NOT NULL,
            profit INTEGER NOT NULL,
            margin_pct REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'Settled',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS travel_logistics (
            logistics_id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            logistics_type TEXT NOT NULL,
            description TEXT NOT NULL,
            cost INTEGER NOT NULL DEFAULT 0,
            starts_at TEXT,
            ends_at TEXT,
            status TEXT NOT NULL DEFAULT 'Planned',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )
def _create_indexes(cursor) -> None:
    cursor.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_finance_transactions_date ON finance_transactions(posting_date, status);
        CREATE INDEX IF NOT EXISTS idx_finance_transactions_source ON finance_transactions(source_module, source_id);
        CREATE INDEX IF NOT EXISTS idx_sponsors_tier ON sponsors(tier_level, deleted_at);
        CREATE INDEX IF NOT EXISTS idx_contracts_sponsor_status ON sponsorship_contracts(sponsor_id, status, deleted_at);
        CREATE INDEX IF NOT EXISTS idx_requirements_contract ON sponsorship_requirements(contract_id, deleted_at);
        CREATE INDEX IF NOT EXISTS idx_deliverables_requirement ON sponsorship_deliverable_tracking(requirement_id, delivered_at);
        CREATE INDEX IF NOT EXISTS idx_controversies_sponsor ON sponsorship_controversies(sponsor_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_venues_location ON venues(country, city, deleted_at);
        CREATE INDEX IF NOT EXISTS idx_venues_geo ON venues(latitude, longitude);
        CREATE INDEX IF NOT EXISTS idx_tours_dates ON tours(start_date, end_date, status);
        CREATE INDEX IF NOT EXISTS idx_tour_events_tour_date ON tour_events(tour_id, event_date, status);
        CREATE INDEX IF NOT EXISTS idx_event_financials_profit ON event_financials(event_id, profit, margin_pct);
        """
    )


def _ensure_venue_columns(cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS venues (
            venue_id TEXT PRIMARY KEY,
            city_id TEXT,
            name TEXT NOT NULL,
            venue_tier TEXT NOT NULL DEFAULT 'arena',
            capacity INTEGER NOT NULL DEFAULT 12000,
            cost INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
        """
    )
    existing = {row[1] for row in cursor.execute("PRAGMA table_info(venues)").fetchall()}
    for name, ddl in VENUE_COLUMNS.items():
        if name not in existing:
            try:
                cursor.execute(f"ALTER TABLE venues ADD COLUMN {name} {ddl}")
            except sqlite3.OperationalError as exc:
                if "duplicate column name" not in str(exc).lower():
                    raise
            existing.add(name)


def _seed_accounts(cursor, now: str) -> None:
    accounts = [
        ("4000", "Sponsorship Revenue", "Revenue"),
        ("4100", "Event Revenue", "Revenue"),
        ("4200", "Merchandise Revenue", "Revenue"),
        ("5000", "Venue Costs", "Expense"),
        ("5100", "Travel Expenses", "Expense"),
        ("5200", "Production Costs", "Expense"),
        ("5300", "Talent Costs", "Expense"),
        ("5400", "Marketing Expenses", "Expense"),
        ("1500", "Venue Improvements", "Asset"),
        ("2100", "Accounts Payable", "Liability"),
        ("1200", "Accounts Receivable", "Asset"),
    ]
    cursor.executemany(
        """
        INSERT OR IGNORE INTO finance_accounts
        (account_code, account_name, account_type, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        [(code, name, typ, now, now) for code, name, typ in accounts],
    )


def _seed_named_venues(cursor, now: str) -> None:
    cursor.executemany(
        """
        INSERT OR IGNORE INTO venues
        (venue_id, city_id, name, venue_tier, capacity, cost, venue_type, city,
         state, country, wrestling_capacity, ownership, latitude, longitude,
         prestige_score, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [(*venue, now, now) for venue in NAMED_VENUES],
    )
    cursor.execute(
        """
        UPDATE venues
        SET city = COALESCE(NULLIF(city, ''), name),
            wrestling_capacity = CASE WHEN wrestling_capacity <= 0 THEN capacity ELSE wrestling_capacity END,
            updated_at = COALESCE(updated_at, ?)
        """,
        (now,),
    )


def _seed_budgets(cursor, now: str) -> None:
    budgets = [
        ("budget_sponsorship_q", "current_quarter", "Sponsorship Revenue", 1_500_000, 2_200_000),
        ("budget_event_q", "current_quarter", "Event Revenue", 2_000_000, 3_100_000),
        ("budget_venue_q", "current_quarter", "Venue Costs", 550_000, 475_000),
        ("budget_tour_q", "current_quarter", "Tour Expenses", 850_000, 760_000),
    ]
    cursor.executemany(
        """
        INSERT OR IGNORE INTO finance_budgets
        (id, period, category, baseline_amount, stretch_amount, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [(bid, period, cat, base, stretch, now, now) for bid, period, cat, base, stretch in budgets],
    )
