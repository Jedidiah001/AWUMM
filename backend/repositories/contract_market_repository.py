"""Repository for contract market persistence."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import json
import uuid


JSON_COLUMNS = {
    "clauses_json",
    "demands_json",
    "response_json",
    "promised_terms_json",
    "consequence_json",
    "details_json",
    "roster_needs",
    "active_pursuits",
}


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


class ContractMarketRepository:
    def __init__(self, database):
        self.database = database
        self.conn = database.conn

    @contextmanager
    def transaction(self):
        try:
            yield
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def now(self) -> str:
        return datetime.now().isoformat()

    def to_json(self, value) -> str:
        return json.dumps(value or {})

    def from_json(self, value, default):
        if value in (None, ""):
            return default
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return default

    def decode(self, row):
        if not row:
            return None
        data = dict(row)
        for key in list(data.keys()):
            if key in JSON_COLUMNS:
                data[key] = self.from_json(data[key], {})
        return data

    def fetch_one(self, sql: str, params: tuple = ()):
        return self.decode(self.conn.execute(sql, params).fetchone())

    def fetch_all(self, sql: str, params: tuple = ()):
        return [self.decode(row) for row in self.conn.execute(sql, params).fetchall()]

    def game_week(self) -> tuple[int, int]:
        row = self.fetch_one("SELECT current_year, current_week FROM game_state WHERE id = 1")
        if not row:
            return 1, 1
        return int(row["current_year"]), int(row["current_week"])

    def reputation(self) -> dict:
        row = self.fetch_one("SELECT * FROM contract_market_reputation WHERE id = 1")
        if row:
            return row
        now = self.now()
        self.conn.execute(
            """
            INSERT INTO contract_market_reputation (
                id, reputation_score, trust_score, last_reason, updated_at
            ) VALUES (1, 62, 62, 'Initial market reputation', ?)
            """,
            (now,),
        )
        self.conn.commit()
        return self.fetch_one("SELECT * FROM contract_market_reputation WHERE id = 1")

    def adjust_reputation(self, reputation_delta: float, trust_delta: float, reason: str) -> dict:
        now = self.now()
        self.conn.execute(
            """
            UPDATE contract_market_reputation
            SET reputation_score = MAX(0, MIN(100, reputation_score + ?)),
                trust_score = MAX(0, MIN(100, trust_score + ?)),
                last_reason = ?,
                updated_at = ?
            WHERE id = 1
            """,
            (reputation_delta, trust_delta, reason, now),
        )
        return self.reputation()

    def get_wrestler(self, wrestler_id: str) -> dict | None:
        return self.fetch_one("SELECT * FROM wrestlers WHERE id = ?", (wrestler_id,))

    def update_wrestler_contract(self, wrestler_id: str, updates: dict) -> None:
        allowed = {
            "contract_salary",
            "contract_total_weeks",
            "contract_weeks_remaining",
            "contract_signing_year",
            "contract_signing_week",
            "morale",
            "is_retired",
            "contract_type",
            "release_clause_amount",
            "no_compete_weeks",
            "creative_control_clause",
            "base_salary",
            "current_escalated_salary",
            "creative_control_level",
            "buy_out_penalty",
            "max_appearances_per_year",
        }
        data = {key: value for key, value in updates.items() if key in allowed}
        if not data:
            return
        data["updated_at"] = self.now()
        assignments = ", ".join(f"{key} = ?" for key in data)
        self.conn.execute(
            f"UPDATE wrestlers SET {assignments} WHERE id = ?",
            tuple(data.values()) + (wrestler_id,),
        )

    def insert_negotiation(self, row: dict) -> dict:
        now = self.now()
        row = dict(row)
        row.setdefault("id", new_id("neg"))
        row.setdefault("created_at", now)
        row.setdefault("updated_at", now)
        row["clauses_json"] = self.to_json(row.get("clauses_json"))
        row["demands_json"] = self.to_json(row.get("demands_json"))
        row["response_json"] = self.to_json(row.get("response_json"))
        columns = list(row.keys())
        self.conn.execute(
            f"INSERT INTO contract_market_negotiations ({', '.join(columns)}) VALUES ({', '.join(['?'] * len(columns))})",
            tuple(row[column] for column in columns),
        )
        return self.fetch_one("SELECT * FROM contract_market_negotiations WHERE id = ?", (row["id"],))

    def insert_deal(self, row: dict) -> dict:
        now = self.now()
        row = dict(row)
        row.setdefault("id", new_id("deal"))
        row.setdefault("created_at", now)
        row.setdefault("updated_at", now)
        row["clauses_json"] = self.to_json(row.get("clauses_json"))
        columns = list(row.keys())
        self.conn.execute(
            f"INSERT INTO contract_market_deals ({', '.join(columns)}) VALUES ({', '.join(['?'] * len(columns))})",
            tuple(row[column] for column in columns),
        )
        return self.fetch_one("SELECT * FROM contract_market_deals WHERE id = ?", (row["id"],))

    def insert_handshake(self, row: dict) -> dict:
        now = self.now()
        row = dict(row)
        row.setdefault("id", new_id("handshake"))
        row.setdefault("created_at", now)
        row.setdefault("updated_at", now)
        row["promised_terms_json"] = self.to_json(row.get("promised_terms_json"))
        row["consequence_json"] = self.to_json(row.get("consequence_json"))
        columns = list(row.keys())
        self.conn.execute(
            f"INSERT INTO contract_market_handshake_deals ({', '.join(columns)}) VALUES ({', '.join(['?'] * len(columns))})",
            tuple(row[column] for column in columns),
        )
        return self.fetch_one("SELECT * FROM contract_market_handshake_deals WHERE id = ?", (row["id"],))

    def update_handshake(self, handshake_id: str, updates: dict) -> dict | None:
        data = dict(updates)
        if "consequence_json" in data:
            data["consequence_json"] = self.to_json(data["consequence_json"])
        data["updated_at"] = self.now()
        assignments = ", ".join(f"{key} = ?" for key in data)
        self.conn.execute(
            f"UPDATE contract_market_handshake_deals SET {assignments} WHERE id = ?",
            tuple(data.values()) + (handshake_id,),
        )
        return self.fetch_one("SELECT * FROM contract_market_handshake_deals WHERE id = ?", (handshake_id,))

    def insert_rival_event(self, row: dict) -> dict:
        row = dict(row)
        row.setdefault("id", new_id("rival_evt"))
        row.setdefault("created_at", self.now())
        row["details_json"] = self.to_json(row.get("details_json"))
        columns = list(row.keys())
        self.conn.execute(
            f"INSERT INTO rival_strategy_events ({', '.join(columns)}) VALUES ({', '.join(['?'] * len(columns))})",
            tuple(row[column] for column in columns),
        )
        return self.fetch_one("SELECT * FROM rival_strategy_events WHERE id = ?", (row["id"],))

