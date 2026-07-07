"""Repository layer for the locker room, developmental, and advanced systems."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import json

from repositories.phase_expansion_repository import new_id


JSON_COLUMNS = {
    "creative_preferences_json",
    "last_primary_factors_json",
    "factors_json",
    "event_risks_json",
    "inputs_json",
    "aftermath_json",
    "perpetrator_ids_json",
    "perpetrator_names_json",
    "visible_signs_json",
    "history_json",
    "outcome_json",
    "payload_json",
    "performance_metrics_json",
    "relationship_json",
    "preferred_methods_json",
    "allocation_json",
    "readiness_breakdown_json",
    "attributes_json",
    "initial_attributes_json",
    "current_attributes_json",
    "revealed_attributes_json",
    "potential_ceiling_json",
    "cause_json",
    "specialty_json",
    "development_bonus_json",
    "progress_reports_json",
    "coaching_potential_json",
    "post_show_analysis_json",
    "subject_json",
    "physical_delta_json",
    "intangible_delta_json",
    "audience_preferences_json",
    "technology_json",
    "audience_taste_json",
    "technology_options_json",
    "factors_json",
    "rules_json",
    "selections_json",
    "evidence_json",
    "reads_json",
    "writes_json",
    "result_json",
    "trigger_conditions_json",
    "response_options_json",
    "mechanical_effects_json",
    "existing_systems_json",
    "details_json",
}


class SimulationExpansionRepository:
    def __init__(self, database):
        self.database = database
        self.conn = database.conn
        self._columns_cache: dict[str, set[str]] = {}

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
        if value is None:
            value = [] if isinstance(value, list) else {}
        return json.dumps(value)

    def from_json(self, value, default):
        if value in (None, ""):
            return default
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return default

    def _decode_row(self, row: dict) -> dict:
        decoded = dict(row)
        for key in list(decoded.keys()):
            if key in JSON_COLUMNS:
                default = [] if key.endswith("_ids_json") or key.endswith("_names_json") or key in {
                    "visible_signs_json",
                    "history_json",
                    "progress_reports_json",
                    "selections_json",
                    "reads_json",
                    "writes_json",
                    "response_options_json",
                    "existing_systems_json",
                } else {}
                decoded[key] = self.from_json(decoded[key], default)
        return decoded

    def fetch_one(self, sql: str, params: tuple = ()) -> dict | None:
        row = self.conn.execute(sql, params).fetchone()
        return self._decode_row(row) if row else None

    def fetch_all(self, sql: str, params: tuple = ()) -> list[dict]:
        return [self._decode_row(row) for row in self.conn.execute(sql, params).fetchall()]

    def insert_simple(self, table: str, row: dict, commit: bool = True) -> dict:
        data = dict(row)
        columns_available = self._table_columns(table)
        if "id" in columns_available:
            data.setdefault("id", new_id(table))
        if "created_at" in columns_available:
            data.setdefault("created_at", self.now())
        data = {key: value for key, value in data.items() if key in columns_available}
        encoded = {}
        for key, value in data.items():
            encoded[key] = self.to_json(value) if key in JSON_COLUMNS and not isinstance(value, str) else value
        columns = list(encoded.keys())
        placeholders = ", ".join(["?"] * len(columns))
        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
        self.conn.execute(sql, tuple(encoded[column] for column in columns))
        if commit:
            self.conn.commit()
        return self._decode_row(encoded)

    def _table_columns(self, table: str) -> set[str]:
        if table not in self._columns_cache:
            self._columns_cache[table] = {
                row["name"] for row in self.conn.execute(f"PRAGMA table_info({table})").fetchall()
            }
        return self._columns_cache[table]

    def upsert_job(self, job: dict) -> dict:
        now = self.now()
        data = {
            "id": job.get("id") or new_id("sim_job"),
            "job_type": job["job_type"],
            "year": int(job["year"]),
            "week": int(job["week"]),
            "status": job["status"],
            "seed": job.get("seed"),
            "reads_json": self.to_json(job.get("reads", [])),
            "writes_json": self.to_json(job.get("writes", [])),
            "result_json": self.to_json(job.get("result", {})),
            "error_message": job.get("error_message"),
            "created_at": now,
            "updated_at": now,
        }
        with self.transaction():
            self.conn.execute(
                """
                INSERT OR REPLACE INTO simulation_expansion_jobs (
                    id, job_type, year, week, status, seed, reads_json,
                    writes_json, result_json, error_message, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(
                    (SELECT created_at FROM simulation_expansion_jobs
                     WHERE job_type = ? AND year = ? AND week = ?), ?
                ), ?)
                """,
                (
                    data["id"],
                    data["job_type"],
                    data["year"],
                    data["week"],
                    data["status"],
                    data["seed"],
                    data["reads_json"],
                    data["writes_json"],
                    data["result_json"],
                    data["error_message"],
                    data["job_type"],
                    data["year"],
                    data["week"],
                    now,
                    now,
                ),
            )
        return self.get_job(job["job_type"], int(job["year"]), int(job["week"])) or data

    def get_job(self, job_type: str, year: int, week: int) -> dict | None:
        return self.fetch_one(
            """
            SELECT * FROM simulation_expansion_jobs
            WHERE job_type = ? AND year = ? AND week = ?
            """,
            (job_type, year, week),
        )

    def get_wrestlers(self) -> list[dict]:
        return self.fetch_all(
            """
            SELECT *
            FROM wrestlers
            WHERE is_retired = 0
            ORDER BY primary_brand, name
            """
        )

    def get_wrestler(self, wrestler_id: str) -> dict | None:
        return self.fetch_one("SELECT * FROM wrestlers WHERE id = ?", (wrestler_id,))

    def upsert_locker_state(self, state: dict, commit: bool = True) -> dict:
        now = self.now()
        state = dict(state)
        state["updated_at"] = now
        encoded = {
            key: self.to_json(value) if key in JSON_COLUMNS and not isinstance(value, str) else value
            for key, value in state.items()
        }
        columns = [
            "wrestler_id", "wrestler_name", "brand", "roster_designation",
            "morale_score", "morale_level", "ego_level", "professionalism",
            "backstage_influence", "management_relationship",
            "creative_preferences_json", "last_primary_factors_json",
            "performance_modifier", "release_request_risk", "refusal_risk",
            "incident_risk", "updated_at", "deleted_at",
        ]
        values = [encoded.get(column) for column in columns]
        self.conn.execute(
            f"""
            INSERT OR REPLACE INTO locker_wrestler_state ({', '.join(columns)})
            VALUES ({', '.join(['?'] * len(columns))})
            """,
            tuple(values),
        )
        if commit:
            self.conn.commit()
        return self.get_locker_state(state["wrestler_id"]) or state

    def get_locker_state(self, wrestler_id: str) -> dict | None:
        return self.fetch_one(
            "SELECT * FROM locker_wrestler_state WHERE wrestler_id = ? AND deleted_at IS NULL",
            (wrestler_id,),
        )

    def list_locker_states(self, brand: str | None = None) -> list[dict]:
        if brand:
            return self.fetch_all(
                """
                SELECT * FROM locker_wrestler_state
                WHERE brand = ? AND deleted_at IS NULL
                ORDER BY morale_score ASC
                """,
                (brand,),
            )
        return self.fetch_all(
            """
            SELECT * FROM locker_wrestler_state
            WHERE deleted_at IS NULL
            ORDER BY brand, morale_score ASC
            """
        )

    def latest_atmosphere(self, brand: str | None = None) -> list[dict]:
        params: tuple = ()
        where = "WHERE a.deleted_at IS NULL"
        if brand:
            where += " AND a.brand = ?"
            params = (brand,)
        return self.fetch_all(
            f"""
            SELECT a.*
            FROM locker_atmosphere_snapshots a
            JOIN (
                SELECT brand, MAX((year * 52) + week) AS week_key
                FROM locker_atmosphere_snapshots
                WHERE deleted_at IS NULL
                GROUP BY brand
            ) latest
              ON latest.brand = a.brand
             AND latest.week_key = ((a.year * 52) + a.week)
            {where}
            ORDER BY a.brand
            """,
            params,
        )

    def recent_morale_history(self, wrestler_id: str, limit: int = 12) -> list[dict]:
        rows = self.fetch_all(
            """
            SELECT * FROM locker_morale_history
            WHERE wrestler_id = ? AND deleted_at IS NULL
            ORDER BY year DESC, week DESC
            LIMIT ?
            """,
            (wrestler_id, limit),
        )
        return list(reversed(rows))

    def active_cliques(self) -> list[dict]:
        cliques = self.fetch_all(
            """
            SELECT * FROM locker_cliques
            WHERE deleted_at IS NULL
            ORDER BY political_power DESC
            """
        )
        for clique in cliques:
            clique["members"] = self.fetch_all(
                """
                SELECT * FROM locker_clique_members
                WHERE clique_id = ? AND deleted_at IS NULL
                ORDER BY role, wrestler_name
                """,
                (clique["id"],),
            )
        return cliques

    def recent_rows(self, table: str, limit: int = 20) -> list[dict]:
        order_col = "created_at"
        return self.fetch_all(
            f"""
            SELECT * FROM {table}
            WHERE deleted_at IS NULL
            ORDER BY {order_col} DESC
            LIMIT ?
            """,
            (limit,),
        )

    def get_center(self, center_id: str = "pc_roc_vanguard") -> dict | None:
        return self.fetch_one(
            "SELECT * FROM dev_performance_centers WHERE id = ? AND deleted_at IS NULL",
            (center_id,),
        )

    def update_center_count(self, center_id: str) -> None:
        row = self.fetch_one(
            """
            SELECT COUNT(*) AS total
            FROM dev_trainees
            WHERE center_id = ? AND status IN ('active', 'limited') AND deleted_at IS NULL
            """,
            (center_id,),
        )
        center = self.get_center(center_id)
        if not center:
            return
        level = int(center["facility_level"])
        weekly_cost = int(18000 + (level * 5400) + (int(row["total"]) * 850))
        modifier = round((level - 5) * 0.025, 4)
        self.conn.execute(
            """
            UPDATE dev_performance_centers
            SET trainee_count = ?, weekly_operational_cost = ?,
                training_quality_modifier = ?, capacity = ?, updated_at = ?
            WHERE id = ?
            """,
            (int(row["total"]), weekly_cost, modifier, max(8, level * 5), self.now(), center_id),
        )
        self.conn.commit()

    def list_trainers(self) -> list[dict]:
        return self.fetch_all(
            "SELECT * FROM dev_trainers WHERE deleted_at IS NULL ORDER BY active DESC, coaching_skill DESC"
        )

    def list_curricula(self) -> list[dict]:
        return self.fetch_all(
            "SELECT * FROM dev_curricula WHERE deleted_at IS NULL ORDER BY curriculum_name"
        )

    def list_trainees(self, include_inactive: bool = False) -> list[dict]:
        where = "WHERE deleted_at IS NULL"
        if not include_inactive:
            where += " AND status IN ('active', 'limited')"
        return self.fetch_all(
            f"""
            SELECT * FROM dev_trainees
            {where}
            ORDER BY readiness_score DESC, wrestler_name
            """
        )

    def get_trainee(self, wrestler_id: str) -> dict | None:
        return self.fetch_one(
            "SELECT * FROM dev_trainees WHERE wrestler_id = ? AND deleted_at IS NULL",
            (wrestler_id,),
        )

    def update_trainee(self, wrestler_id: str, updates: dict, commit: bool = True) -> None:
        data = dict(updates)
        data["updated_at"] = self.now()
        encoded = {
            key: self.to_json(value) if key in JSON_COLUMNS and not isinstance(value, str) else value
            for key, value in data.items()
        }
        assignments = ", ".join([f"{key} = ?" for key in encoded.keys()])
        params = list(encoded.values()) + [wrestler_id]
        self.conn.execute(f"UPDATE dev_trainees SET {assignments} WHERE wrestler_id = ?", tuple(params))
        if commit:
            self.conn.commit()

    def active_excursions(self) -> list[dict]:
        return self.fetch_all(
            """
            SELECT e.*, d.destination_name, d.wrestling_style, d.specialty_json, d.cultural_challenge
            FROM dev_excursions e
            JOIN dev_excursion_destinations d ON d.id = e.destination_id
            WHERE e.status = 'active' AND e.deleted_at IS NULL
            ORDER BY e.start_year, e.start_week
            """
        )

    def get_match_script(self, script_id: str) -> dict | None:
        script = self.fetch_one(
            "SELECT * FROM advanced_match_scripts WHERE id = ? AND deleted_at IS NULL",
            (script_id,),
        )
        if script:
            script["beats"] = self.fetch_all(
                """
                SELECT * FROM advanced_match_script_beats
                WHERE script_id = ? AND deleted_at IS NULL
                ORDER BY sequence_order
                """,
                (script_id,),
            )
        return script

    def list_endgame_objectives(self) -> list[dict]:
        return self.fetch_all(
            """
            SELECT * FROM endgame_objectives
            WHERE deleted_at IS NULL
            ORDER BY category, objective_name
            """
        )
