"""
Repository layer for booking, storyline, ratings, media, and business features.

All SQL for the #64-72, #88-100, and #126-137 phase lives here so controllers
and services stay thin and testable.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import json
import uuid


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


class PhaseExpansionRepository:
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
        return json.dumps(value if value is not None else {})

    def from_json(self, value, default):
        if value in (None, ""):
            return default
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return default

    def fetch_all(self, sql: str, params: tuple = ()) -> list[dict]:
        rows = self.conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def fetch_one(self, sql: str, params: tuple = ()) -> dict | None:
        row = self.conn.execute(sql, params).fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------
    # Post-show fallout
    # ------------------------------------------------------------------

    def save_post_show_fallout(self, report: dict, items: list[dict], job: dict | None = None) -> dict:
        """Persist a complete post-show fallout packet and any approval rows."""

        now = self.now()
        with self.transaction():
            self.conn.execute(
                """
                INSERT OR REPLACE INTO post_show_fallout_reports (
                    id, show_id, show_name, brand, show_type, year, week,
                    autonomy_level, overall_rating, urgency_score, summary,
                    headline_json, status, created_at, updated_at, deleted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(
                    (SELECT created_at FROM post_show_fallout_reports WHERE id = ?), ?
                ), ?, NULL)
                """,
                (
                    report["id"],
                    report["show_id"],
                    report["show_name"],
                    report["brand"],
                    report.get("show_type", "weekly_tv"),
                    report["year"],
                    report["week"],
                    report.get("autonomy_level", "balanced"),
                    report.get("overall_rating", 0),
                    report.get("urgency_score", 0),
                    report["summary"],
                    self.to_json(report.get("headlines", [])),
                    report.get("status", "open"),
                    report["id"],
                    now,
                    now,
                ),
            )
            self.conn.execute(
                "UPDATE post_show_fallout_items SET deleted_at = ?, updated_at = ? WHERE report_id = ? AND deleted_at IS NULL",
                (now, now, report["id"]),
            )
            for item in items:
                approval = item.get("approval")
                approval_id = None
                if approval:
                    approval_id = approval.get("id")
                    self.conn.execute(
                        """
                        INSERT OR REPLACE INTO booker_approval_queue (
                            id, source_type, source_id, category, priority, title, summary,
                            recommendation_json, deadline_year, deadline_week, status,
                            autonomy_policy, auto_execute_after_week, executed_at,
                            player_response_json, created_at, updated_at, deleted_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, '{}',
                            COALESCE((SELECT created_at FROM booker_approval_queue WHERE id = ?), ?), ?, NULL)
                        """,
                        (
                            approval_id,
                            approval.get("source_type", "post_show_fallout"),
                            item["id"],
                            item["item_type"],
                            approval.get("priority", item.get("urgency", "medium")),
                            item["title"],
                            item["summary"],
                            self.to_json(approval.get("recommendation", {})),
                            approval.get("deadline_year"),
                            approval.get("deadline_week"),
                            approval.get("status", "pending"),
                            approval.get("autonomy_policy", "ask"),
                            approval.get("auto_execute_after_week"),
                            approval_id,
                            now,
                            now,
                        ),
                    )

                self.conn.execute(
                    """
                    INSERT INTO post_show_fallout_items (
                        id, report_id, item_type, urgency, title, summary, details_json,
                        suggested_actions_json, mechanical_effects_json, requires_response,
                        auto_execute_allowed, status, approval_id, player_response_json,
                        created_at, updated_at, resolved_at, deleted_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '{}', ?, ?, NULL, NULL)
                    """,
                    (
                        item["id"],
                        report["id"],
                        item["item_type"],
                        item.get("urgency", "medium"),
                        item["title"],
                        item["summary"],
                        self.to_json(item.get("details", {})),
                        self.to_json(item.get("suggested_actions", [])),
                        self.to_json(item.get("mechanical_effects", [])),
                        1 if item.get("requires_response") else 0,
                        1 if item.get("auto_execute_allowed") else 0,
                        item.get("status", "open"),
                        approval_id,
                        now,
                        now,
                    ),
                )

            if job:
                self.conn.execute(
                    """
                    INSERT INTO internal_simulation_jobs (
                        id, job_type, trigger_year, trigger_week, status, reads_json,
                        writes_json, result_json, error_message, created_at, updated_at, deleted_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, NULL)
                    """,
                    (
                        job["id"],
                        job.get("job_type", "post_show_fallout"),
                        report["year"],
                        report["week"],
                        job.get("status", "completed"),
                        self.to_json(job.get("reads", [])),
                        self.to_json(job.get("writes", [])),
                        self.to_json(job.get("result", {})),
                        now,
                        now,
                    ),
                )
        return self.get_post_show_fallout(report["id"]) or {}

    def get_post_show_fallout(self, report_id: str) -> dict | None:
        report = self.fetch_one(
            "SELECT * FROM post_show_fallout_reports WHERE id = ? AND deleted_at IS NULL",
            (report_id,),
        )
        return self._decode_post_show_report(report) if report else None

    def get_post_show_fallout_by_show(self, show_id: str, year: int, week: int) -> dict | None:
        report = self.fetch_one(
            """
            SELECT * FROM post_show_fallout_reports
            WHERE show_id = ? AND year = ? AND week = ? AND deleted_at IS NULL
            ORDER BY created_at DESC LIMIT 1
            """,
            (show_id, year, week),
        )
        return self._decode_post_show_report(report) if report else None

    def latest_post_show_fallouts(self, limit: int = 8) -> list[dict]:
        rows = self.fetch_all(
            """
            SELECT * FROM post_show_fallout_reports
            WHERE deleted_at IS NULL
            ORDER BY year DESC, week DESC, created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [self._decode_post_show_report(row) for row in rows]

    def decide_post_show_fallout_item(self, item_id: str, status: str, response: dict) -> dict:
        now = self.now()
        self.conn.execute(
            """
            UPDATE post_show_fallout_items
            SET status = ?, player_response_json = ?, resolved_at = ?, updated_at = ?
            WHERE id = ? AND deleted_at IS NULL
            """,
            (status, self.to_json(response), now, now, item_id),
        )
        self.conn.commit()
        item = self.fetch_one("SELECT * FROM post_show_fallout_items WHERE id = ?", (item_id,))
        return self._decode_post_show_item(item) if item else {}

    def apply_post_show_effects(self, effects: list[dict]) -> list[dict]:
        """Apply small immediate stat/title effects generated by the fallout engine."""

        applied = []
        now = self.now()
        with self.transaction():
            for effect in effects:
                target_type = effect.get("target_type")
                impact_type = effect.get("impact_type")
                delta = float(effect.get("delta", 0))
                target_id = effect.get("target_id")
                target_name = effect.get("target_name")

                if target_type == "wrestler" and impact_type in {"morale", "momentum", "popularity", "fatigue"}:
                    column = impact_type
                    cursor = self.conn.execute(
                        f"""
                        UPDATE wrestlers
                        SET {column} = MAX(0, MIN(100, {column} + ?)), updated_at = ?
                        WHERE (? IS NOT NULL AND id = ?) OR (? IS NOT NULL AND name = ?)
                        """,
                        (delta, now, target_id, target_id, target_name, target_name),
                    )
                    if cursor.rowcount:
                        applied.append(effect)

                elif target_type == "championship" and impact_type == "prestige":
                    cursor = self.conn.execute(
                        """
                        UPDATE championships
                        SET prestige = MAX(0, MIN(100, prestige + ?)), updated_at = ?
                        WHERE (? IS NOT NULL AND id = ?) OR (? IS NOT NULL AND name = ?)
                        """,
                        (delta, now, target_id, target_id, target_name, target_name),
                    )
                    if cursor.rowcount:
                        applied.append(effect)
        return applied

    def _decode_post_show_report(self, report: dict) -> dict:
        report = dict(report)
        report["headlines"] = self.from_json(report.pop("headline_json", None), [])
        report["items"] = [
            self._decode_post_show_item(row)
            for row in self.fetch_all(
                """
                SELECT * FROM post_show_fallout_items
                WHERE report_id = ? AND deleted_at IS NULL
                ORDER BY
                    CASE urgency WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                    created_at ASC
                """,
                (report["id"],),
            )
        ]
        report["urgent_items"] = [item for item in report["items"] if item.get("urgency") in {"critical", "high"}]
        report["open_actions"] = [item for item in report["items"] if item.get("requires_response") and item.get("status") == "open"]
        return report

    def _decode_post_show_item(self, item: dict | None) -> dict:
        if not item:
            return {}
        item = dict(item)
        item["details"] = self.from_json(item.pop("details_json", None), {})
        item["suggested_actions"] = self.from_json(item.pop("suggested_actions_json", None), [])
        item["mechanical_effects"] = self.from_json(item.pop("mechanical_effects_json", None), [])
        item["player_response"] = self.from_json(item.pop("player_response_json", None), {})
        item["requires_response"] = bool(item.get("requires_response"))
        item["auto_execute_allowed"] = bool(item.get("auto_execute_allowed"))
        return item

    def get_lookup_values(self, category: str | None = None) -> dict | list:
        if category:
            return self.fetch_all(
                """
                SELECT value, label, metadata
                FROM phase_lookup_values
                WHERE category = ? AND deleted_at IS NULL
                ORDER BY sort_order, label
                """,
                (category,),
            )

        rows = self.fetch_all(
            """
            SELECT category, value, label, metadata
            FROM phase_lookup_values
            WHERE deleted_at IS NULL
            ORDER BY category, sort_order, label
            """
        )
        grouped: dict[str, list[dict]] = {}
        for row in rows:
            grouped.setdefault(row["category"], []).append(
                {"value": row["value"], "label": row["label"], "metadata": self.from_json(row["metadata"], {})}
            )
        return grouped

    # ------------------------------------------------------------------
    # Booking plans
    # ------------------------------------------------------------------

    def replace_show_plan(self, plan: dict, segments: list[dict]) -> dict:
        now = self.now()
        warnings = plan.get("warnings", [])
        with self.transaction():
            self.conn.execute("DELETE FROM booking_segments WHERE show_id = ?", (plan["show_id"],))
            self.conn.execute("DELETE FROM commercial_breaks WHERE show_id = ?", (plan["show_id"],))
            self.conn.execute(
                """
                INSERT OR REPLACE INTO booking_show_plans (
                    show_id, show_name, brand, show_type, year, week,
                    total_runtime_minutes, network_break_count, accept_overrun,
                    booking_credibility_delta, planned_rating_impact,
                    actual_runtime_minutes, dead_air_risk_minutes,
                    overrun_minutes, warnings, created_at, updated_at, deleted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(
                    (SELECT created_at FROM booking_show_plans WHERE show_id = ?), ?
                ), ?, NULL)
                """,
                (
                    plan["show_id"],
                    plan["show_name"],
                    plan["brand"],
                    plan["show_type"],
                    plan["year"],
                    plan["week"],
                    plan["total_runtime_minutes"],
                    plan.get("network_break_count", 0),
                    1 if plan.get("accept_overrun") else 0,
                    plan.get("booking_credibility_delta", 0),
                    plan.get("planned_rating_impact", 0),
                    plan.get("actual_runtime_minutes"),
                    plan.get("dead_air_risk_minutes", 0),
                    plan.get("overrun_minutes", 0),
                    self.to_json(warnings),
                    plan["show_id"],
                    now,
                    now,
                ),
            )
            for segment in segments:
                self.insert_booking_segment(segment, commit=False)
            for commercial in plan.get("commercial_breaks", []):
                self.insert_commercial_break(commercial, commit=False)
        return self.get_show_plan(plan["show_id"]) or {}

    def insert_booking_segment(self, segment: dict, commit: bool = True) -> None:
        now = self.now()
        self.conn.execute(
            """
            INSERT OR REPLACE INTO booking_segments (
                id, show_id, source_item_id, item_type, segment_type, card_position,
                planned_start_minute, planned_duration_minutes, actual_duration_minutes,
                allocation_status, expected_min_minutes, expected_max_minutes,
                suspiciously_short, overrun_minutes, dead_air_minutes,
                is_opening, is_main_event, is_dark_match, dark_match_phase,
                feud_id, title_id, quality_score, crowd_heat_score, payload_json,
                created_at, updated_at, deleted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(
                (SELECT created_at FROM booking_segments WHERE id = ?), ?
            ), ?, NULL)
            """,
            (
                segment["id"],
                segment["show_id"],
                segment["source_item_id"],
                segment["item_type"],
                segment["segment_type"],
                segment["card_position"],
                segment.get("planned_start_minute", 0),
                segment["planned_duration_minutes"],
                segment.get("actual_duration_minutes"),
                segment["allocation_status"],
                segment.get("expected_min_minutes", 1),
                segment.get("expected_max_minutes", 10),
                1 if segment.get("suspiciously_short") else 0,
                segment.get("overrun_minutes", 0),
                segment.get("dead_air_minutes", 0),
                1 if segment.get("is_opening") else 0,
                1 if segment.get("is_main_event") else 0,
                1 if segment.get("is_dark_match") else 0,
                segment.get("dark_match_phase"),
                segment.get("feud_id"),
                segment.get("title_id"),
                segment.get("quality_score", 0),
                segment.get("crowd_heat_score", 0),
                self.to_json(segment.get("payload_json", {})),
                segment["id"],
                now,
                now,
            ),
        )
        if commit:
            self.conn.commit()

    def insert_commercial_break(self, commercial: dict, commit: bool = True) -> None:
        now = self.now()
        self.conn.execute(
            """
            INSERT OR REPLACE INTO commercial_breaks (
                id, show_id, position_index, placement_type, after_segment_id,
                during_match_id, minute_marker, strategy, quality_score,
                viewer_return_modifier, satisfaction_modifier, created_at,
                updated_at, deleted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(
                (SELECT created_at FROM commercial_breaks WHERE id = ?), ?
            ), ?, NULL)
            """,
            (
                commercial["id"],
                commercial["show_id"],
                commercial.get("position_index", 0),
                commercial["placement_type"],
                commercial.get("after_segment_id"),
                commercial.get("during_match_id"),
                commercial.get("minute_marker", 0),
                commercial["strategy"],
                commercial["quality_score"],
                commercial["viewer_return_modifier"],
                commercial["satisfaction_modifier"],
                commercial["id"],
                now,
                now,
            ),
        )
        if commit:
            self.conn.commit()

    def get_show_plan(self, show_id: str) -> dict | None:
        plan = self.fetch_one("SELECT * FROM booking_show_plans WHERE show_id = ? AND deleted_at IS NULL", (show_id,))
        if not plan:
            return None
        plan["warnings"] = self.from_json(plan.get("warnings"), [])
        plan["segments"] = self.fetch_all(
            """
            SELECT * FROM booking_segments
            WHERE show_id = ? AND deleted_at IS NULL
            ORDER BY card_position, planned_start_minute
            """,
            (show_id,),
        )
        for segment in plan["segments"]:
            segment["payload_json"] = self.from_json(segment.get("payload_json"), {})
        plan["commercial_breaks"] = self.fetch_all(
            """
            SELECT * FROM commercial_breaks
            WHERE show_id = ? AND deleted_at IS NULL
            ORDER BY position_index
            """,
            (show_id,),
        )
        return plan

    def get_recent_booking_segments(self, limit: int = 200) -> list[dict]:
        return self.fetch_all(
            """
            SELECT bs.*, bsp.show_name, bsp.year, bsp.week
            FROM booking_segments bs
            JOIN booking_show_plans bsp ON bsp.show_id = bs.show_id
            WHERE bs.deleted_at IS NULL
            ORDER BY bsp.year DESC, bsp.week DESC, bs.card_position DESC
            LIMIT ?
            """,
            (limit,),
        )

    # ------------------------------------------------------------------
    # Interference, debuts, returns, themes
    # ------------------------------------------------------------------

    def count_recent_interferences(self, wrestler_id: str, year: int, week: int, window_weeks: int = 4) -> int:
        current_abs = (year * 52) + week
        rows = self.fetch_all(
            """
            SELECT year, week
            FROM interference_history
            WHERE interfering_wrestler_id = ? AND deleted_at IS NULL
            """,
            (wrestler_id,),
        )
        return sum(1 for row in rows if 0 <= current_abs - ((row["year"] * 52) + row["week"]) <= window_weeks)

    def count_feud_interferences(self, feud_id: str | None) -> int:
        if not feud_id:
            return 0
        row = self.fetch_one(
            """
            SELECT COUNT(*) AS total
            FROM interference_history
            WHERE feud_id = ? AND deleted_at IS NULL
            """,
            (feud_id,),
        )
        return int(row["total"]) if row else 0

    def record_interference(self, data: dict) -> dict:
        now = self.now()
        row = {
            "id": data.get("id") or new_id("interference"),
            **data,
            "created_at": now,
            "updated_at": now,
        }
        with self.transaction():
            self.conn.execute(
                """
                INSERT INTO interference_history (
                    id, show_id, match_id, feud_id, interfering_wrestler_id,
                    interfering_wrestler_name, purpose, outcome, impact_score,
                    heat_delta, recent_count_4_weeks, feud_interference_count,
                    overuse_warning, override_warning, credibility_penalty,
                    year, week, created_at, updated_at, deleted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                """,
                (
                    row["id"],
                    row["show_id"],
                    row["match_id"],
                    row.get("feud_id"),
                    row["interfering_wrestler_id"],
                    row["interfering_wrestler_name"],
                    row["purpose"],
                    row.get("outcome", "planned"),
                    row["impact_score"],
                    row.get("heat_delta", 0),
                    row.get("recent_count_4_weeks", 0),
                    row.get("feud_interference_count", 0),
                    1 if row.get("overuse_warning") else 0,
                    1 if row.get("override_warning") else 0,
                    row.get("credibility_penalty", 0),
                    row["year"],
                    row["week"],
                    now,
                    now,
                ),
            )
        return row

    def insert_simple(self, table: str, row: dict) -> dict:
        data = dict(row)
        data.setdefault("id", new_id(table))
        data.setdefault("created_at", self.now())
        data.setdefault("updated_at", data["created_at"])
        columns = list(data.keys())
        placeholders = ", ".join(["?"] * len(columns))
        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
        with self.transaction():
            self.conn.execute(sql, tuple(data[column] for column in columns))
        return data

    def list_theme_templates(self) -> list[dict]:
        rows = self.fetch_all(
            """
            SELECT *
            FROM show_theme_templates
            WHERE deleted_at IS NULL
            ORDER BY category, name
            """
        )
        for row in rows:
            row["requirements_json"] = self.from_json(row.get("requirements_json"), {})
        return rows

    def get_theme_template(self, theme_id: str) -> dict | None:
        row = self.fetch_one(
            "SELECT * FROM show_theme_templates WHERE id = ? AND deleted_at IS NULL",
            (theme_id,),
        )
        if row:
            row["requirements_json"] = self.from_json(row.get("requirements_json"), {})
        return row

    # ------------------------------------------------------------------
    # Story engine
    # ------------------------------------------------------------------

    def create_story_feud(self, feud: dict, participants: list[dict]) -> dict:
        now = self.now()
        feud_id = feud.get("id") or new_id("story_feud")
        with self.transaction():
            self.conn.execute(
                """
                INSERT INTO story_feuds (
                    id, legacy_feud_id, name, basis, status, heat_score,
                    heat_level, trajectory, intended_conclusion_match_type,
                    duration_target_weeks, start_year, start_week,
                    planned_climax_year, planned_climax_week, metadata_json,
                    created_at, updated_at, deleted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                """,
                (
                    feud_id,
                    feud.get("legacy_feud_id"),
                    feud["name"],
                    feud["basis"],
                    feud.get("status", "active"),
                    feud.get("heat_score", 20),
                    feud.get("heat_level", "lukewarm"),
                    feud.get("trajectory", "stable"),
                    feud["intended_conclusion_match_type"],
                    feud["duration_target_weeks"],
                    feud["start_year"],
                    feud["start_week"],
                    feud.get("planned_climax_year"),
                    feud.get("planned_climax_week"),
                    self.to_json(feud.get("metadata_json", {})),
                    now,
                    now,
                ),
            )
            for participant in participants:
                self.conn.execute(
                    """
                    INSERT INTO story_feud_participants (
                        id, feud_id, participant_type, participant_id,
                        participant_name, side_label, role, created_at,
                        updated_at, deleted_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                    """,
                    (
                        participant.get("id") or new_id("story_feud_participant"),
                        feud_id,
                        participant.get("participant_type", "wrestler"),
                        participant["participant_id"],
                        participant["participant_name"],
                        participant.get("side_label", "A"),
                        participant.get("role", "primary"),
                        now,
                        now,
                    ),
                )
        created = self.get_story_feud(feud_id)
        return created or {"id": feud_id}

    def update_story_feud_heat(
        self,
        feud_id: str,
        heat_score: float,
        heat_level: str,
        trajectory: str,
        year: int | None = None,
        week: int | None = None,
        extra_updates: dict | None = None,
        commit: bool = True,
    ) -> None:
        updates = [
            "heat_score = ?",
            "heat_level = ?",
            "trajectory = ?",
            "updated_at = ?",
        ]
        params: list = [heat_score, heat_level, trajectory, self.now()]
        if year is not None:
            updates.append("last_action_year = ?")
            params.append(year)
        if week is not None:
            updates.append("last_action_week = ?")
            params.append(week)
        for key, value in (extra_updates or {}).items():
            updates.append(f"{key} = ?")
            params.append(value)
        params.append(feud_id)
        self.conn.execute(f"UPDATE story_feuds SET {', '.join(updates)} WHERE id = ?", tuple(params))
        if commit:
            self.conn.commit()

    def record_storyline_action(self, action: dict) -> dict:
        now = self.now()
        action_id = action.get("id") or new_id("story_action")
        with self.transaction():
            self.conn.execute(
                """
                INSERT INTO storyline_actions (
                    id, feud_id, action_category, action_type, participants_json,
                    description, heat_change, heat_after, credibility_effect,
                    quality_score, show_id, year, week, created_at, updated_at,
                    deleted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                """,
                (
                    action_id,
                    action["feud_id"],
                    action["action_category"],
                    action["action_type"],
                    self.to_json(action.get("participants_json", [])),
                    action["description"],
                    action["heat_change"],
                    action["heat_after"],
                    action.get("credibility_effect", 0),
                    action.get("quality_score", 0),
                    action.get("show_id"),
                    action["year"],
                    action["week"],
                    now,
                    now,
                ),
            )
            self.update_story_feud_heat(
                action["feud_id"],
                action["heat_after"],
                action["heat_level"],
                action.get("trajectory", "rising"),
                action["year"],
                action["week"],
                commit=False,
            )
        action["id"] = action_id
        return action

    def get_story_feud(self, feud_id: str) -> dict | None:
        feud = self.fetch_one(
            "SELECT * FROM story_feuds WHERE id = ? AND deleted_at IS NULL",
            (feud_id,),
        )
        if not feud:
            return None
        feud["metadata_json"] = self.from_json(feud.get("metadata_json"), {})
        feud["participants"] = self.fetch_all(
            """
            SELECT *
            FROM story_feud_participants
            WHERE feud_id = ? AND deleted_at IS NULL
            ORDER BY side_label, role, participant_name
            """,
            (feud_id,),
        )
        feud["actions"] = self.fetch_all(
            """
            SELECT *
            FROM storyline_actions
            WHERE feud_id = ? AND deleted_at IS NULL
            ORDER BY year, week, created_at
            """,
            (feud_id,),
        )
        for action in feud["actions"]:
            action["participants_json"] = self.from_json(action.get("participants_json"), [])
        return feud

    def list_story_feuds(self, active_only: bool = True) -> list[dict]:
        where = "WHERE deleted_at IS NULL"
        if active_only:
            where += " AND status = 'active'"
        rows = self.fetch_all(
            f"""
            SELECT *
            FROM story_feuds
            {where}
            ORDER BY heat_score DESC, updated_at DESC
            """
        )
        for row in rows:
            row["metadata_json"] = self.from_json(row.get("metadata_json"), {})
            row["participants"] = self.fetch_all(
                """
                SELECT participant_id, participant_name, participant_type, side_label, role
                FROM story_feud_participants
                WHERE feud_id = ? AND deleted_at IS NULL
                ORDER BY side_label, participant_name
                """,
                (row["id"],),
            )
        return rows

    def get_active_story_feuds_for_wrestlers(self, wrestler_ids: list[str]) -> list[dict]:
        if not wrestler_ids:
            return []
        placeholders = ", ".join(["?"] * len(wrestler_ids))
        rows = self.fetch_all(
            f"""
            SELECT DISTINCT sf.*
            FROM story_feuds sf
            JOIN story_feud_participants sfp ON sfp.feud_id = sf.id
            WHERE sf.status = 'active'
              AND sf.deleted_at IS NULL
              AND sfp.deleted_at IS NULL
              AND sfp.participant_id IN ({placeholders})
            ORDER BY sf.heat_score DESC
            """,
            tuple(wrestler_ids),
        )
        return rows

    # ------------------------------------------------------------------
    # Ratings, network, social, business
    # ------------------------------------------------------------------

    def save_ratings_bundle(self, rating: dict, quarters: list[dict], demographics: list[dict], insights: list[dict]) -> dict:
        now = self.now()
        rating_id = rating.get("id") or new_id("tv_rating")
        with self.transaction():
            self.conn.execute("DELETE FROM tv_quarter_hour_ratings WHERE show_id = ?", (rating["show_id"],))
            old = self.fetch_one("SELECT id FROM tv_ratings WHERE show_id = ?", (rating["show_id"],))
            if old:
                self.conn.execute("DELETE FROM tv_demographic_ratings WHERE rating_id = ?", (old["id"],))
            self.conn.execute(
                """
                INSERT OR REPLACE INTO tv_ratings (
                    id, show_id, show_name, brand, year, week, base_viewership,
                    total_viewership, rating_score, booking_quality_score,
                    momentum_modifier, competition_modifier, opening_modifier,
                    main_event_modifier, commercial_modifier, demographic_value_index,
                    advertising_revenue, created_at, updated_at, deleted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(
                    (SELECT created_at FROM tv_ratings WHERE show_id = ?), ?
                ), ?, NULL)
                """,
                (
                    rating_id,
                    rating["show_id"],
                    rating["show_name"],
                    rating["brand"],
                    rating["year"],
                    rating["week"],
                    rating["base_viewership"],
                    rating["total_viewership"],
                    rating["rating_score"],
                    rating["booking_quality_score"],
                    rating["momentum_modifier"],
                    rating["competition_modifier"],
                    rating.get("opening_modifier", 0),
                    rating.get("main_event_modifier", 0),
                    rating.get("commercial_modifier", 0),
                    rating["demographic_value_index"],
                    rating["advertising_revenue"],
                    rating["show_id"],
                    now,
                    now,
                ),
            )
            for quarter in quarters:
                self.conn.execute(
                    """
                    INSERT INTO tv_quarter_hour_ratings (
                        id, rating_id, show_id, quarter_index, start_minute,
                        end_minute, segment_id, content_summary, rating_score,
                        viewership, viewer_delta, analysis_note, created_at,
                        updated_at, deleted_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                    """,
                    (
                        quarter.get("id") or new_id("quarter_rating"),
                        rating_id,
                        rating["show_id"],
                        quarter["quarter_index"],
                        quarter["start_minute"],
                        quarter["end_minute"],
                        quarter.get("segment_id"),
                        quarter["content_summary"],
                        quarter["rating_score"],
                        quarter["viewership"],
                        quarter["viewer_delta"],
                        quarter["analysis_note"],
                        now,
                        now,
                    ),
                )
            for demo in demographics:
                self.conn.execute(
                    """
                    INSERT INTO tv_demographic_ratings (
                        id, rating_id, demographic, viewership, rating_score,
                        ad_rate_multiplier, revenue_contribution, created_at,
                        updated_at, deleted_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                    """,
                    (
                        demo.get("id") or new_id("demo_rating"),
                        rating_id,
                        demo["demographic"],
                        demo["viewership"],
                        demo["rating_score"],
                        demo["ad_rate_multiplier"],
                        demo["revenue_contribution"],
                        now,
                        now,
                    ),
                )
            for insight in insights:
                self.conn.execute(
                    """
                    INSERT INTO ratings_insights (
                        id, show_id, insight_type, title, body, metric_value,
                        confidence, created_at, updated_at, deleted_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                    """,
                    (
                        insight.get("id") or new_id("ratings_insight"),
                        rating["show_id"],
                        insight["insight_type"],
                        insight["title"],
                        insight["body"],
                        insight.get("metric_value", 0),
                        insight.get("confidence", 0),
                        now,
                        now,
                    ),
                )
        saved = self.get_show_rating(rating["show_id"])
        return saved or {"id": rating_id}

    def get_show_rating(self, show_id: str) -> dict | None:
        rating = self.fetch_one("SELECT * FROM tv_ratings WHERE show_id = ? AND deleted_at IS NULL", (show_id,))
        if not rating:
            return None
        rating["quarter_hours"] = self.fetch_all(
            """
            SELECT *
            FROM tv_quarter_hour_ratings
            WHERE show_id = ? AND deleted_at IS NULL
            ORDER BY quarter_index
            """,
            (show_id,),
        )
        rating["demographics"] = self.fetch_all(
            """
            SELECT *
            FROM tv_demographic_ratings
            WHERE rating_id = ? AND deleted_at IS NULL
            ORDER BY revenue_contribution DESC
            """,
            (rating["id"],),
        )
        return rating

    def get_recent_ratings(self, limit: int = 20) -> list[dict]:
        return self.fetch_all(
            """
            SELECT *
            FROM tv_ratings
            WHERE deleted_at IS NULL
            ORDER BY year DESC, week DESC
            LIMIT ?
            """,
            (limit,),
        )

    def get_competition_for_week(self, year: int, week: int) -> list[dict]:
        return self.fetch_all(
            """
            SELECT *
            FROM competing_events
            WHERE deleted_at IS NULL
              AND (week = ? OR (year = ? AND week = ?))
            ORDER BY audience_overlap_score DESC
            """,
            (week, year, week),
        )

    def get_primary_network(self) -> dict:
        network = self.fetch_one(
            """
            SELECT *
            FROM network_relationships
            WHERE id = 'network_primary' AND deleted_at IS NULL
            """
        )
        if network:
            network["demands_json"] = self.from_json(network.get("demands_json"), [])
            return network
        now = self.now()
        self.conn.execute(
            """
            INSERT INTO network_relationships (
                id, network_name, relationship_score, relationship_level,
                content_profile, demands_json, promotional_support_score, updated_at
            ) VALUES ('network_primary', 'Prime Sports Network', 65, 'stable', 'balanced', '[]', 55, ?)
            """,
            (now,),
        )
        self.conn.commit()
        return self.get_primary_network()

    def update_network_relationship(self, change: float, reason: str, year: int, week: int, show_id: str | None = None) -> dict:
        network = self.get_primary_network()
        score_after = max(0.0, min(100.0, float(network["relationship_score"]) + change))
        level = self.relationship_level(score_after)
        now = self.now()
        with self.transaction():
            self.conn.execute(
                """
                UPDATE network_relationships
                SET relationship_score = ?, relationship_level = ?, updated_at = ?
                WHERE id = ?
                """,
                (score_after, level, now, network["id"]),
            )
            self.conn.execute(
                """
                INSERT INTO network_relationship_history (
                    id, network_id, show_id, change_amount, score_after,
                    reason, trend_window_json, year, week, created_at,
                    updated_at, deleted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                """,
                (
                    new_id("network_history"),
                    network["id"],
                    show_id,
                    change,
                    score_after,
                    reason,
                    "{}",
                    year,
                    week,
                    now,
                    now,
                ),
            )
        return self.get_primary_network()

    def relationship_level(self, score: float) -> str:
        if score >= 85:
            return "excellent"
        if score >= 70:
            return "strong"
        if score >= 50:
            return "stable"
        if score >= 30:
            return "strained"
        return "at_risk"

    def add_social_spike(self, spike: dict) -> dict:
        now = self.now()
        spike_id = spike.get("id") or new_id("social_spike")
        with self.transaction():
            self.conn.execute(
                """
                INSERT INTO social_spike_events (
                    id, show_id, source_type, source_id, description, spike_score,
                    follower_gain, engagement_delta, platforms_json, year, week,
                    created_at, updated_at, deleted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                """,
                (
                    spike_id,
                    spike.get("show_id"),
                    spike["source_type"],
                    spike.get("source_id"),
                    spike["description"],
                    spike["spike_score"],
                    spike["follower_gain"],
                    spike["engagement_delta"],
                    self.to_json(spike.get("platforms_json", [])),
                    spike["year"],
                    spike["week"],
                    now,
                    now,
                ),
            )
            platform_rows = self.fetch_all("SELECT * FROM social_platform_metrics WHERE deleted_at IS NULL")
            for platform in platform_rows:
                gain = max(1, int(spike["follower_gain"] / max(1, len(platform_rows))))
                engagement = min(0.25, float(platform["engagement_rate"]) + spike["engagement_delta"])
                followers = int(platform["follower_count"]) + gain
                self.conn.execute(
                    """
                    UPDATE social_platform_metrics
                    SET follower_count = ?, engagement_rate = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (followers, engagement, now, platform["id"]),
                )
                self.conn.execute(
                    """
                    INSERT INTO social_metric_history (
                        id, platform_id, follower_count, engagement_rate,
                        follower_delta, engagement_delta, reason, year, week,
                        created_at, updated_at, deleted_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                    """,
                    (
                        new_id("social_history"),
                        platform["id"],
                        followers,
                        engagement,
                        gain,
                        spike["engagement_delta"],
                        spike["description"],
                        spike["year"],
                        spike["week"],
                        now,
                        now,
                    ),
                )
        spike["id"] = spike_id
        return spike

    def get_social_metrics(self) -> list[dict]:
        return self.fetch_all(
            """
            SELECT *
            FROM social_platform_metrics
            WHERE deleted_at IS NULL
            ORDER BY platform_value_score DESC
            """
        )

    def get_business_snapshot(self, year: int, week: int) -> dict | None:
        return self.fetch_one(
            """
            SELECT *
            FROM business_metric_snapshots
            WHERE year = ? AND week = ? AND deleted_at IS NULL
            """,
            (year, week),
        )

    def upsert_business_snapshot(self, snapshot: dict) -> dict:
        now = self.now()
        snapshot_id = snapshot.get("id") or new_id("business_snapshot")
        with self.transaction():
            self.conn.execute(
                """
                INSERT OR REPLACE INTO business_metric_snapshots (
                    id, year, week, mainstream_awareness,
                    sponsorship_attractiveness, streaming_attractiveness,
                    booking_credibility, promotion_momentum, valuation_estimate,
                    metadata_json, created_at, updated_at, deleted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(
                    (SELECT created_at FROM business_metric_snapshots WHERE year = ? AND week = ?), ?
                ), ?, NULL)
                """,
                (
                    snapshot_id,
                    snapshot["year"],
                    snapshot["week"],
                    snapshot.get("mainstream_awareness", 0),
                    snapshot.get("sponsorship_attractiveness", 0),
                    snapshot.get("streaming_attractiveness", 0),
                    snapshot.get("booking_credibility", 70),
                    snapshot.get("promotion_momentum", 50),
                    snapshot.get("valuation_estimate", 0),
                    self.to_json(snapshot.get("metadata_json", {})),
                    snapshot["year"],
                    snapshot["week"],
                    now,
                    now,
                ),
            )
        return self.get_business_snapshot(snapshot["year"], snapshot["week"]) or snapshot

    def log_job(self, job_type: str, year: int, week: int, status: str, reads: list, writes: list, result: dict, error: str | None = None) -> dict:
        row = {
            "id": new_id("job"),
            "job_type": job_type,
            "trigger_year": year,
            "trigger_week": week,
            "status": status,
            "reads_json": self.to_json(reads),
            "writes_json": self.to_json(writes),
            "result_json": self.to_json(result),
            "error_message": error,
            "created_at": self.now(),
            "updated_at": self.now(),
        }
        self.insert_simple("internal_simulation_jobs", row)
        return row
