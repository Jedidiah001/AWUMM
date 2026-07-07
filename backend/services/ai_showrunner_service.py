from __future__ import annotations

import json
import random
import re
from datetime import datetime
from typing import Any

from repositories.phase_expansion_repository import PhaseExpansionRepository, new_id


ANGLE_LIBRARY_SEEDS = [
    ("contract_signing_chaos", "Contract Signing Chaos", "feud_escalation", "contract_signing", "high", 8, 2, 6, ["feud_heat +10", "match_stipulation_pressure +8", "injury_risk +2"]),
    ("parking_lot_attack", "Parking Lot Attack", "shock_attack", "backstage_attack", "high", 6, 2, 4, ["feud_heat +12", "victim_morale -3", "attacker_heat +8"]),
    ("medical_update_interruption", "Medical Update Interrupted", "injury_story", "interview", "medium", 5, 1, 3, ["return_anticipation +8", "sympathy +6"]),
    ("gm_office_deal", "GM Office Deal", "authority", "backstage", "medium", 4, 2, 5, ["storyline_clarity +7", "authority_heat +5"]),
    ("mystery_attacker_clue", "Mystery Attacker Clue", "mystery", "vignette", "medium", 4, 1, 4, ["suspense +10", "social_buzz +6"]),
    ("faction_recruitment", "Faction Recruitment Pitch", "faction", "backstage", "medium", 5, 2, 6, ["faction_momentum +8", "turn_tease +6"]),
    ("fake_injury_swerve", "Fake Injury Swerve", "swerve", "in_ring_attack", "high", 8, 2, 4, ["shock +12", "trust_penalty_if_overused +5"]),
    ("champion_celebration_ruined", "Champion Celebration Ruined", "title_scene", "in_ring_attack", "high", 6, 2, 6, ["title_heat +10", "challenger_momentum +7"]),
    ("cash_in_tease", "Cash-In Tease", "money_in_bank", "run_in", "high", 3, 2, 4, ["briefcase_heat +9", "champion_anxiety +7"]),
    ("locker_room_pull_apart", "Locker Room Pull-Apart", "brawl", "backstage", "medium", 4, 4, 8, ["locker_room_tension +7", "feud_heat +8"]),
    ("betrayal_tease", "Betrayal Tease", "turn", "confrontation", "medium", 5, 2, 5, ["turn_suspicion +8", "team_chemistry_pressure +6"]),
    ("open_challenge_surprise", "Open Challenge Surprise", "opportunity", "match", "medium", 3, 2, 3, ["underused_visibility +10", "upset_probability +5"]),
]


class AIShowrunnerService:
    """Persistent AI booker, PLE roadmap, and approval queue coordinator."""

    def __init__(self, database):
        self.database = database
        self.repo = PhaseExpansionRepository(database)
        self.conn = database.conn
        self._tables_ready = False

    def now(self) -> str:
        return datetime.now().isoformat()

    def dashboard(self) -> dict:
        self._ensure_tables()
        pending = self._queue_rows("pending", 30)
        recent = self._queue_rows(None, 12)
        roadmaps = self._roadmaps(8)
        last_run = self.repo.fetch_one(
            """
            SELECT * FROM ai_showrunner_runs
            WHERE deleted_at IS NULL
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
        if last_run:
            self._decode_run(last_run)
        special = self._special_system_snapshot()
        return {
            "summary": {
                "pending_approvals": len(pending),
                "active_roadmaps": len(roadmaps),
                "angle_templates": special["angle_templates_count"],
                "active_mitb": len(special["mitb_briefcases"]),
                "active_war_games": len(special["war_games"]),
                "crown_payoffs": len(special["crown_payoffs"]),
                "dark_house_runs": len(special["dark_house_runs"]),
                "live_interruptions": len(special["live_interruptions"]),
                "promo_beats": len(special["promo_beats"]),
                "last_run_status": (last_run or {}).get("status", "not_run"),
            },
            "pending_approvals": pending,
            "recent_decisions": recent,
            "roadmaps": roadmaps,
            "special_systems": special,
            "last_run": last_run,
        }

    def run_weekly(self, year: int, week: int, universe=None, seed: int | None = None, force: bool = False, autonomy_level: str = "balanced") -> dict:
        self._ensure_tables()
        show = self._current_show(universe, year, week)
        existing = self.repo.fetch_one(
            """
            SELECT * FROM ai_showrunner_runs
            WHERE year = ? AND week = ? AND show_id = ? AND deleted_at IS NULL
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (year, week, show["show_id"]),
        )
        if existing and not force:
            self._decode_run(existing)
            return {"already_ran": True, "run": existing, "dashboard": self.dashboard()}

        rng = random.Random(seed if seed is not None else (year * 1000 + week * 17 + len(show["show_id"])))
        roster = self._active_roster(show["brand"])
        if len(roster) < 2:
            raise ValueError("AI Showrunner needs at least two active wrestlers to book a show.")

        risk = self._risk_from_autonomy(autonomy_level)
        opportunity = self._opportunity_rotation(roster)
        card = self._build_card(show, roster, opportunity, rng, risk)
        promo_beats = self._generate_promo_beats_for_card(year, week, show, card, rng, risk, source_type="ai_showrunner")
        special_systems = self._run_special_systems(year, week, show, roster, opportunity, card, universe, rng, risk, autonomy_level)
        special_systems["promo_beats"] = promo_beats
        special_systems["dark_house_autopilot"] = self._run_dark_house_autopilot(year, week, show, roster, opportunity, rng, risk, autonomy_level, force=force)
        roadmaps = self._refresh_ple_roadmap(year, week, roster, universe, rng)
        approvals, auto_executed = self._create_decisions(year, week, show, card, roadmaps, autonomy_level, risk, special_systems)
        saved_plan = self._persist_show_plan(show, card, year, week)

        run_id = new_id("showrunner")
        now = self.now()
        decisions = approvals + auto_executed
        with self.repo.transaction():
            self.conn.execute(
                """
                INSERT INTO ai_showrunner_runs (
                    id, year, week, show_id, show_name, brand, autonomy_level,
                    risk_tolerance, opportunity_rotation_json, generated_card_json,
                    decisions_json, auto_executed_json, status, created_at, updated_at, deleted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                """,
                (
                    run_id,
                    year,
                    week,
                    show["show_id"],
                    show["name"],
                    show["brand"],
                    autonomy_level,
                    risk,
                    json.dumps(opportunity[:12]),
                    json.dumps(card),
                    json.dumps(decisions),
                    json.dumps(auto_executed),
                    "auto_executed" if auto_executed else "drafted",
                    now,
                    now,
                ),
            )
            self.conn.execute(
                """
                INSERT INTO internal_simulation_jobs (
                    id, job_type, trigger_year, trigger_week, status, reads_json,
                    writes_json, result_json, created_at, updated_at, deleted_at
                ) VALUES (?, 'ai_showrunner_weekly', ?, ?, 'completed', ?, ?, ?, ?, ?, NULL)
                """,
                (
                    new_id("job"),
                    year,
                    week,
                    json.dumps(["wrestlers", "story_arcs", "story_calendar_events", "ple_roadmap_plans", "angle_library_templates"]),
                    json.dumps([
                        "ai_showrunner_runs", "booker_approval_queue", "booking_show_plans", "booking_segments",
                        "angle_executions", "money_in_bank_briefcases", "war_games_plans", "crown_tournament_payoffs",
                    ]),
                    json.dumps({"run_id": run_id, "approvals": len(approvals), "auto_executed": len(auto_executed)}),
                    now,
                    now,
                ),
            )

        return {
            "already_ran": False,
            "run_id": run_id,
            "show": show,
            "card": card,
            "saved_plan": saved_plan,
            "approvals_created": approvals,
            "auto_executed": auto_executed,
            "roadmaps": roadmaps,
            "special_systems": special_systems,
            "dashboard": self.dashboard(),
        }

    def decide_approval(self, approval_id: str, data: dict) -> dict:
        self._ensure_tables()
        action = str(data.get("decision") or data.get("action") or "").lower()
        status_map = {
            "approve": "approved",
            "approved": "approved",
            "counter": "countered",
            "modify": "countered",
            "reject": "rejected",
            "rejected": "rejected",
            "dismiss": "dismissed",
            "auto_execute": "auto_executed",
        }
        if action not in status_map:
            raise ValueError("Decision must be approve, counter, reject, dismiss, or auto_execute.")
        row = self.repo.fetch_one("SELECT * FROM booker_approval_queue WHERE id = ? AND deleted_at IS NULL", (approval_id,))
        if not row:
            raise ValueError("Booker approval item not found.")
        now = self.now()
        new_status = status_map[action]
        payload = {
            "decision": action,
            "notes": data.get("notes", ""),
            "counter_pitch": data.get("counter_pitch", ""),
            "decided_at": now,
        }
        self.conn.execute(
            """
            UPDATE booker_approval_queue
            SET status = ?, player_response_json = ?, executed_at = CASE WHEN ? IN ('approved', 'auto_executed') THEN ? ELSE executed_at END,
                updated_at = ?
            WHERE id = ?
            """,
            (new_status, json.dumps(payload), new_status, now, now, approval_id),
        )
        self.conn.commit()
        row = self.repo.fetch_one("SELECT * FROM booker_approval_queue WHERE id = ?", (approval_id,))
        return self._decode_queue(row)

    def auto_resolve_due(self, year: int, week: int) -> dict:
        self._ensure_tables()
        rows = self.repo.fetch_all(
            """
            SELECT * FROM booker_approval_queue
            WHERE status = 'pending'
              AND autonomy_policy = 'auto_if_unanswered'
              AND auto_execute_after_week IS NOT NULL
              AND auto_execute_after_week <= ?
              AND deleted_at IS NULL
            """,
            (week,),
        )
        resolved = []
        for row in rows:
            resolved.append(self.decide_approval(row["id"], {"decision": "auto_execute", "notes": f"Auto-resolved in Y{year} W{week}."}))
        return {"resolved": len(resolved), "items": resolved}

    def latest_booking_draft(self) -> dict:
        self._ensure_tables()
        run = self.repo.fetch_one(
            """
            SELECT *
            FROM ai_showrunner_runs
            WHERE deleted_at IS NULL
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
        if not run:
            return {"available": False, "message": "No AI Showrunner draft has been generated yet."}
        self._decode_run(run)
        card = run.get("generated_card_json") or {}
        draft = self._card_to_booking_draft(run, card)
        return {
            "available": True,
            "run": {
                "id": run["id"],
                "year": run["year"],
                "week": run["week"],
                "show_id": run["show_id"],
                "show_name": run["show_name"],
                "brand": run["brand"],
                "status": run["status"],
                "autonomy_level": run["autonomy_level"],
                "created_at": run["created_at"],
                "updated_at": run["updated_at"],
            },
            "show_draft": draft,
        }

    def run_dark_house_autopilot(self, year: int, week: int, universe=None, seed: int | None = None, force: bool = False, autonomy_level: str = "balanced") -> dict:
        self._ensure_tables()
        show = self._current_show(universe, year, week)
        roster = self._active_roster(show["brand"])
        if len(roster) < 2:
            raise ValueError("Dark/house autopilot needs at least two active wrestlers.")
        rng = random.Random(seed if seed is not None else (year * 3001 + week * 43 + 9))
        risk = self._risk_from_autonomy(autonomy_level)
        opportunity = self._opportunity_rotation(roster)
        return self._run_dark_house_autopilot(year, week, show, roster, opportunity, rng, risk, autonomy_level, force=force)

    def generate_promo_beats(self, year: int, week: int, show_draft: dict | None = None, seed: int | None = None, force: bool = False) -> dict:
        self._ensure_tables()
        rng = random.Random(seed if seed is not None else (year * 4001 + week * 59 + 13))
        if show_draft:
            show = {
                "show_id": show_draft.get("show_id", f"promo_y{year}_w{week}"),
                "name": show_draft.get("show_name") or show_draft.get("name") or f"Promo Beats Y{year} W{week}",
                "brand": show_draft.get("brand", "Cross-Brand"),
                "show_type": show_draft.get("show_type", "weekly_tv"),
            }
            card = {
                "show_id": show["show_id"],
                "show_name": show["name"],
                "brand": show["brand"],
                "segments": show_draft.get("segments", []),
            }
        else:
            show = {"show_id": f"promo_y{year}_w{week}", "name": f"Promo Beats Y{year} W{week}", "brand": "Cross-Brand", "show_type": "weekly_tv"}
            roster = self._active_roster("Cross-Brand")
            if len(roster) < 2:
                raise ValueError("Promo beat generator needs at least two wrestlers.")
            card = {"segments": [self._segment("standalone_promo", "promo", 1, 6, roster[:2], f"{roster[0]['name']} and {roster[1]['name']} trade verbal fire.")]}
        beats = self._generate_promo_beats_for_card(year, week, show, card, rng, 0.58, source_type="manual", force=force)
        return {"beats": beats, "total": len(beats)}

    def maybe_live_interruption(self, show_draft_data: dict, universe=None, seed: int | None = None, force: bool = False, autonomy_level: str = "balanced") -> dict:
        self._ensure_tables()
        if not show_draft_data:
            return {"inserted": False, "show_draft": show_draft_data, "reason": "No show draft provided."}
        year = int(show_draft_data.get("year") or 1)
        week = int(show_draft_data.get("week") or 1)
        show_id = show_draft_data.get("show_id") or f"live_y{year}_w{week}"
        existing = self.repo.fetch_one(
            """
            SELECT * FROM live_show_interruptions
            WHERE show_id = ? AND year = ? AND week = ? AND deleted_at IS NULL
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (show_id, year, week),
        )
        if existing and not force:
            return {"inserted": False, "show_draft": show_draft_data, "interruption": self._decode_live_interruption(existing), "reason": "A live interruption already exists for this show."}

        rng = random.Random(seed if seed is not None else (year * 5003 + week * 71 + len(show_id)))
        risk = self._risk_from_autonomy(autonomy_level)
        participant_ids = self._participant_ids_from_show_draft(show_draft_data)
        segment_pressure = len(show_draft_data.get("segments") or []) * 0.025
        title_pressure = 0.08 if any(m.get("is_title_match") for m in show_draft_data.get("matches", [])) else 0
        probability = min(0.72, 0.12 + (risk * 0.24) + segment_pressure + title_pressure)
        if not force and rng.random() > probability:
            return {"inserted": False, "show_draft": show_draft_data, "reason": "No live interruption triggered this time.", "probability": round(probability, 3)}

        brand = show_draft_data.get("brand", "Cross-Brand")
        roster = self._active_roster(brand)
        selected = self._select_interruption_participants(roster, participant_ids, rng)
        interruption_type = rng.choice(["surprise_run_in", "unscheduled_promo", "backstage_feed_cut", "authority_reversal", "rival_invasion_tease"])
        segment_type = {
            "surprise_run_in": "run_in",
            "unscheduled_promo": "promo",
            "backstage_feed_cut": "backstage_attack",
            "authority_reversal": "announcement",
            "rival_invasion_tease": "in_ring_attack",
        }.get(interruption_type, "run_in")
        max_position = max([int(s.get("card_position") or s.get("position") or 0) for s in show_draft_data.get("segments", [])] + [int(m.get("card_position") or m.get("position") or 0) for m in show_draft_data.get("matches", [])] + [0])
        inserted_position = max_position + 1
        description = self._interruption_description(interruption_type, selected, show_draft_data)
        payload = {
            "segment_id": new_id("live_segment"),
            "segment_type": segment_type,
            "display_name": "Live Interruption",
            "description": description,
            "participants": [{"id": p["id"], "name": p["name"], "role": "instigator"} for p in selected],
            "duration": 5,
            "duration_minutes": 5,
            "position": inserted_position,
            "card_position": inserted_position,
            "purpose": "start_feud" if len(selected) >= 2 else "shock",
            "advances_feud": True,
            "creates_heat": True,
            "creates_pop": interruption_type == "unscheduled_promo",
            "can_end_in_brawl": interruption_type in {"surprise_run_in", "backstage_feed_cut", "rival_invasion_tease"},
            "live_interruption": True,
        }
        effects = ["live_show_shock +12", "crowd_heat +8", "booking_volatility +6"]
        if interruption_type in {"surprise_run_in", "rival_invasion_tease"}:
            effects.append("feud_seed +10")
        row_id = new_id("live_intr")
        now = self.now()
        with self.repo.transaction():
            self.conn.execute(
                """
                INSERT INTO live_show_interruptions (
                    id, year, week, show_id, show_name, brand, trigger_context,
                    interruption_type, severity, status, participants_json,
                    segment_payload_json, mechanical_effects_json, inserted_card_position,
                    autonomy_policy, approval_id, resolved_at, created_at, updated_at, deleted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'inserted', ?, ?, ?, ?, ?, NULL, ?, ?, ?, NULL)
                """,
                (
                    row_id, year, week, show_id, show_draft_data.get("show_name", "Live Show"), brand,
                    "run_show", interruption_type, "high" if risk >= 0.7 else "medium",
                    json.dumps([{"id": p["id"], "name": p["name"]} for p in selected]),
                    json.dumps(payload), json.dumps(effects), inserted_position,
                    "auto", now, now, now,
                ),
            )
        show_draft_data.setdefault("segments", []).append(payload)
        interruption = self._decode_live_interruption(self.repo.fetch_one("SELECT * FROM live_show_interruptions WHERE id = ?", (row_id,)))
        return {"inserted": True, "show_draft": show_draft_data, "interruption": interruption, "probability": round(probability, 3)}

    def _ensure_tables(self) -> None:
        if self._tables_ready:
            return
        required = ("ai_showrunner_runs", "booker_approval_queue", "live_show_interruptions")
        placeholders = ",".join("?" for _ in required)
        rows = self.repo.fetch_all(
            f"SELECT name FROM sqlite_master WHERE type = 'table' AND name IN ({placeholders})",
            required,
        )
        if {row["name"] for row in rows} == set(required):
            self._tables_ready = True
            return

        from persistence.phase_expansion_db import create_phase_expansion_tables
        create_phase_expansion_tables(self.database)
        self._tables_ready = True

    def _current_show(self, universe, year: int, week: int) -> dict:
        show = None
        try:
            show = universe.calendar.get_current_show() if universe and getattr(universe, "calendar", None) else None
        except Exception:
            show = None
        if show:
            return show.to_dict() if hasattr(show, "to_dict") else dict(show)
        return {
            "show_id": f"ai_y{year}_w{week}_weekly",
            "name": f"AI Weekly Y{year} W{week}",
            "brand": "Cross-Brand",
            "show_type": "weekly_tv",
            "is_ppv": False,
            "tier": "weekly",
            "year": year,
            "week": week,
        }

    def _active_roster(self, brand: str) -> list[dict]:
        rows = self.repo.fetch_all(
            """
            SELECT id, name, age, gender, alignment, role, primary_brand, brawling,
                   technical, speed, mic, psychology, stamina, years_experience,
                   is_major_superstar, popularity, momentum, morale, fatigue,
                   injury_severity, injury_weeks_remaining
            FROM wrestlers
            WHERE COALESCE(is_retired, 0) = 0
            ORDER BY popularity DESC, momentum DESC, name
            """
        )
        healthy = []
        for row in rows:
            if int(row.get("injury_weeks_remaining") or 0) > 0:
                continue
            if brand not in {"Cross-Brand", "", None} and row.get("primary_brand") not in {brand, "Cross-Brand", None, ""}:
                continue
            row["overall"] = self._overall(row)
            healthy.append(row)
        return healthy or rows[:]

    def _overall(self, row: dict) -> float:
        keys = ["brawling", "technical", "speed", "mic", "psychology", "stamina", "popularity", "momentum"]
        values = [float(row.get(k) or 0) for k in keys]
        return round(sum(values) / max(1, len(values)), 2)

    def _opportunity_rotation(self, roster: list[dict]) -> list[dict]:
        recent_runs = self.repo.fetch_all(
            """
            SELECT generated_card_json
            FROM ai_showrunner_runs
            WHERE deleted_at IS NULL
            ORDER BY created_at DESC
            LIMIT 8
            """
        )
        usage = {w["id"]: 0 for w in roster}
        for run in recent_runs:
            card = self.repo.from_json(run.get("generated_card_json"), {})
            for segment in card.get("segments", []):
                for participant in segment.get("participants", []):
                    wid = participant.get("id")
                    if wid in usage:
                        usage[wid] += 1
        ranked = []
        for w in roster:
            base = 100 - min(95, float(w.get("popularity") or 0))
            morale_need = max(0, 55 - float(w.get("morale") or 50)) * 0.4
            gamble = max(0, 75 - float(w.get("overall") or 50)) * 0.15
            ranked.append({
                "id": w["id"],
                "name": w["name"],
                "usage_8_runs": usage.get(w["id"], 0),
                "opportunity_score": round(base + morale_need + gamble - (usage.get(w["id"], 0) * 12), 2),
            })
        return sorted(ranked, key=lambda item: item["opportunity_score"], reverse=True)

    def _build_card(self, show: dict, roster: list[dict], opportunity: list[dict], rng: random.Random, risk: float) -> dict:
        top = sorted(roster, key=lambda w: (w.get("overall", 0), w.get("popularity", 0)), reverse=True)
        underused_ids = [item["id"] for item in opportunity]
        underused = [w for wid in underused_ids for w in roster if w["id"] == wid]
        lead = top[0]
        challenger = self._pick_distinct(top[1:] + underused, {lead["id"]}, rng)
        gamble = self._pick_distinct(underused + top, {lead["id"], challenger["id"]}, rng)
        opponent = self._pick_distinct(top + underused, {lead["id"], challenger["id"], gamble["id"]}, rng)
        tag_a = self._pick_distinct(roster, {lead["id"], challenger["id"], gamble["id"], opponent["id"]}, rng)
        tag_b = self._pick_distinct(roster, {lead["id"], challenger["id"], gamble["id"], opponent["id"], tag_a["id"]}, rng)
        showcase_a = self._pick_distinct(roster, {lead["id"], challenger["id"], gamble["id"], opponent["id"], tag_a["id"], tag_b["id"]}, rng)
        showcase_b = self._pick_distinct(roster, {lead["id"], challenger["id"], gamble["id"], opponent["id"], tag_a["id"], tag_b["id"], showcase_a["id"]}, rng)
        main_winner = challenger if risk >= 0.68 and challenger.get("overall", 0) >= lead.get("overall", 0) - 18 else lead
        upset_winner = gamble if risk >= 0.5 else opponent
        segments = [
            self._segment("opening_promo", "promo", 1, 8, [lead, challenger], f"{lead['name']} opens with a PLE-level claim; {challenger['name']} interrupts."),
            self._segment("opportunity_match", "match", 2, 13, [gamble, opponent], f"Opportunity match designed to test {gamble['name']} above their usual slot.", winner=upset_winner),
            self._segment("backstage_attack", "backstage_attack", 3, 5, [challenger, lead], f"{challenger['name']} creates a backstage shock to raise urgency."),
            self._segment("tag_showcase", "tag", 4, 12, [tag_a, tag_b], "Fresh chemistry test for underused roster members."),
            self._segment("workrate_showcase", "match", 5, 10, [showcase_a, showcase_b], f"{showcase_a['name']} and {showcase_b['name']} get a main-card evaluation match.", winner=showcase_a),
            self._segment("character_interview", "interview", 6, 5, [gamble], f"{gamble['name']} gets a focused character interview after the opportunity match."),
            self._segment("main_event", "main_event_title_match", 7, 22, [lead, challenger], f"{lead['name']} vs {challenger['name']} anchors the night with a protected finish.", winner=main_winner),
        ]
        return {
            "show_id": show["show_id"],
            "show_name": show["name"],
            "brand": show["brand"],
            "show_type": show.get("show_type", "weekly_tv"),
            "risk_tolerance": risk,
            "creative_goal": "Rotate opportunities while keeping one strong PLE thread hot.",
            "segments": segments,
        }

    def _segment(self, sid: str, segment_type: str, position: int, minutes: int, wrestlers: list[dict], description: str, winner: dict | None = None) -> dict:
        return {
            "id": sid,
            "segment_type": segment_type,
            "position": position,
            "duration": minutes,
            "description": description,
            "participants": [{"id": w["id"], "name": w["name"], "role": w.get("role"), "overall": w.get("overall")} for w in wrestlers],
            "winner": {"id": winner["id"], "name": winner["name"]} if winner else None,
            "mechanical_effects": self._segment_effects(segment_type),
        }

    def _segment_effects(self, segment_type: str) -> list[str]:
        effects = {
            "promo": ["Raises feud heat if crowd response lands.", "Creates approval item for opening direction."],
            "match": ["Updates opportunity rotation.", "Can improve underused wrestler momentum."],
            "backstage_attack": ["Can trigger a dynamic event popup.", "Adds urgency to the PLE roadmap."],
            "tag": ["Tests chemistry for future booking."],
            "interview": ["Improves character clarity and promo visibility."],
            "contract_signing": ["Creates PLE-stakes pressure.", "Raises refusal/interference risk."],
            "run_in": ["Can trigger cash-in or interference consequences.", "Raises live shock value."],
            "vignette": ["Builds mystery and anticipation.", "Adds social discussion."],
            "confrontation": ["Clarifies character direction.", "Can tease turns or alliances."],
            "backstage": ["Moves story without using match time.", "Can alter locker-room relationships."],
            "in_ring_attack": ["Escalates feud heat.", "Can justify stipulation or injury write-off."],
            "main_event_title_match": ["Protects or changes title-track momentum.", "Requires approval before major title implications."],
        }
        return effects.get(segment_type, ["Adds weekly continuity."])

    def _pick_distinct(self, pool: list[dict], used: set[str], rng: random.Random) -> dict:
        choices = [w for w in pool if w["id"] not in used]
        if not choices:
            choices = pool
        return rng.choice(choices[: max(1, min(6, len(choices)))])

    def _run_dark_house_autopilot(self, year: int, week: int, show: dict, roster: list[dict], opportunity: list[dict], rng: random.Random, risk: float, autonomy: str, force: bool = False) -> dict:
        existing = self.repo.fetch_all(
            """
            SELECT * FROM dark_house_show_runs
            WHERE year = ? AND week = ? AND parent_show_id = ? AND deleted_at IS NULL
            ORDER BY created_at DESC
            """,
            (year, week, show["show_id"]),
        )
        if existing and not force:
            return {"created": [], "existing": [self._decode_dark_house(row) for row in existing], "total": len(existing)}

        underused_ids = [item["id"] for item in opportunity]
        focus = [w for wid in underused_ids for w in roster if w["id"] == wid]
        focus = (focus + roster)[: max(6, min(len(roster), 10))]
        plans = [
            ("dark_show", f"{show['name']} Dark", 650, 22),
            ("house_show", f"{show['brand']} House Loop", 2200, 38),
        ]
        created = []
        for mode, name, attendance_base, runtime in plans:
            show_id = f"{show['show_id']}_{mode}_y{year}_w{week}"
            selected = []
            used = set()
            for _ in range(min(6, len(focus))):
                pick = self._pick_distinct(focus, used, rng)
                selected.append(pick)
                used.add(pick["id"])
            if len(selected) < 2:
                continue
            first = selected[0]
            second = selected[1]
            third = selected[2] if len(selected) > 2 else self._pick_distinct(roster, {first["id"], second["id"]}, rng)
            fourth = selected[3] if len(selected) > 3 else self._pick_distinct(roster, {first["id"], second["id"], third["id"]}, rng)
            fifth = selected[4] if len(selected) > 4 else first
            sixth = selected[5] if len(selected) > 5 else second
            upset = first if risk >= 0.5 else second
            card = {
                "show_id": show_id,
                "show_name": name,
                "brand": show["brand"],
                "show_mode": mode,
                "segments": [
                    self._segment(f"{mode}_opener", "match", 1, 8, [first, second], f"{first['name']} gets live reps against {second['name']}.", winner=upset),
                    self._segment(f"{mode}_promo_lab", "promo", 2, 5, [third, fourth], f"{third['name']} and {fourth['name']} test crowd-facing character beats."),
                    self._segment(f"{mode}_main", "tag", 3, 9, [third, fourth, fifth, sixth], "Low-pressure chemistry and stamina test for the opportunity rotation.", winner=third),
                ],
            }
            impacts = self._dark_house_impacts(card, mode)
            results = {
                "match_count": 2,
                "promo_count": 1,
                "standout": first["name"],
                "crowd_response": round(54 + rng.random() * 18 + (risk * 6), 2),
                "notes": "Autopilot completed and fed opportunity rotation, morale, and fatigue.",
            }
            attendance = int(attendance_base + rng.randint(0, 350) + (sum(float(w.get("popularity") or 0) for w in selected) / max(1, len(selected))) * 8)
            revenue = attendance * (18 if mode == "dark_show" else 32)
            row_id = new_id("dhshow")
            now = self.now()
            with self.repo.transaction():
                self.conn.execute(
                    """
                    INSERT OR REPLACE INTO dark_house_show_runs (
                        id, year, week, parent_show_id, show_name, brand, show_mode,
                        autonomy_level, status, roster_focus_json, card_json, results_json,
                        opportunity_impacts_json, attendance, revenue, created_at, updated_at, deleted_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'completed', ?, ?, ?, ?, ?, ?, COALESCE(
                        (SELECT created_at FROM dark_house_show_runs WHERE id = ?), ?
                    ), ?, NULL)
                    """,
                    (
                        row_id, year, week, show["show_id"], name, show["brand"], mode, autonomy,
                        json.dumps([{"id": w["id"], "name": w["name"]} for w in selected]),
                        json.dumps(card), json.dumps(results), json.dumps(impacts),
                        attendance, revenue, row_id, now, now,
                    ),
                )
            self._persist_auxiliary_show_plan(show_id, name, show["brand"], mode, year, week, runtime, card["segments"])
            self._apply_dark_house_impacts(impacts)
            created.append(self._decode_dark_house(self.repo.fetch_one("SELECT * FROM dark_house_show_runs WHERE id = ?", (row_id,))))
        return {"created": created, "existing": [], "total": len(created)}

    def _persist_auxiliary_show_plan(self, show_id: str, show_name: str, brand: str, show_type: str, year: int, week: int, runtime: int, card_segments: list[dict]) -> None:
        planned_start = 0
        segments = []
        for item in card_segments:
            segments.append({
                "id": f"aux_{show_id}_{item['id']}",
                "show_id": show_id,
                "source_item_id": item["id"],
                "item_type": show_type,
                "segment_type": item["segment_type"],
                "card_position": item["position"],
                "planned_start_minute": planned_start,
                "planned_duration_minutes": item["duration"],
                "allocation_status": "autopilot_completed",
                "expected_min_minutes": max(1, item["duration"] - 2),
                "expected_max_minutes": item["duration"] + 4,
                "is_opening": item["position"] == 1,
                "is_main_event": item["position"] == len(card_segments),
                "is_dark_match": show_type == "dark_show",
                "dark_match_phase": show_type,
                "quality_score": 58,
                "crowd_heat_score": 50,
                "payload_json": item,
            })
            planned_start += item["duration"]
        self.repo.replace_show_plan({
            "show_id": show_id,
            "show_name": show_name,
            "brand": brand,
            "show_type": show_type,
            "year": year,
            "week": week,
            "total_runtime_minutes": runtime,
            "network_break_count": 0,
            "accept_overrun": True,
            "booking_credibility_delta": 0.7,
            "planned_rating_impact": 0.01,
            "dead_air_risk_minutes": max(0, runtime - planned_start),
            "overrun_minutes": max(0, planned_start - runtime),
            "warnings": ["AI autopilot auxiliary show: review opportunity and fatigue impacts."],
        }, segments)

    def _dark_house_impacts(self, card: dict, mode: str) -> list[dict]:
        seen = {}
        for segment in card.get("segments", []):
            for participant in segment.get("participants", []):
                wid = participant.get("id")
                if not wid:
                    continue
                entry = seen.setdefault(wid, {
                    "wrestler_id": wid,
                    "wrestler_name": participant.get("name", wid),
                    "appearances": 0,
                    "morale_delta": 0,
                    "momentum_delta": 0,
                    "fatigue_delta": 0,
                    "development_delta": 0,
                })
                entry["appearances"] += 1
                entry["morale_delta"] += 1 if mode == "dark_show" else 2
                entry["momentum_delta"] += 1
                entry["fatigue_delta"] += 2 if mode == "dark_show" else 4
                entry["development_delta"] += 2 if mode == "dark_show" else 1
        return list(seen.values())

    def _apply_dark_house_impacts(self, impacts: list[dict]) -> None:
        for impact in impacts:
            row = self.repo.fetch_one("SELECT morale, momentum, fatigue FROM wrestlers WHERE id = ?", (impact["wrestler_id"],))
            if not row:
                continue
            morale = max(0, min(100, float(row.get("morale") or 50) + impact.get("morale_delta", 0)))
            momentum = max(0, min(100, float(row.get("momentum") or 50) + impact.get("momentum_delta", 0)))
            fatigue = max(0, min(100, float(row.get("fatigue") or 0) + impact.get("fatigue_delta", 0)))
            self.conn.execute(
                "UPDATE wrestlers SET morale = ?, momentum = ?, fatigue = ?, updated_at = ? WHERE id = ?",
                (morale, momentum, fatigue, self.now(), impact["wrestler_id"]),
            )
        self.conn.commit()

    def _generate_promo_beats_for_card(self, year: int, week: int, show: dict, card: dict, rng: random.Random, risk: float, source_type: str, force: bool = False) -> list[dict]:
        roster = {row["id"]: row for row in self._active_roster(show.get("brand", "Cross-Brand"))}
        candidates = []
        for index, segment in enumerate(card.get("segments", []), start=1):
            segment_type = segment.get("segment_type", "promo")
            if segment_type in {"promo", "interview", "contract_signing", "confrontation", "announcement", "vignette"}:
                candidates.append((index, segment))
        if not candidates and card.get("segments"):
            candidates.append((1, card["segments"][0]))
        beats = []
        for index, segment in candidates[:4]:
            source_id = segment.get("segment_id") or segment.get("id") or f"segment_{index}"
            existing = self.repo.fetch_one(
                """
                SELECT * FROM promo_dialogue_beats
                WHERE year = ? AND week = ? AND show_id = ? AND source_id = ? AND deleted_at IS NULL
                LIMIT 1
                """,
                (year, week, show.get("show_id"), source_id),
            )
            if existing and not force:
                beats.append(self._decode_promo_beat(existing))
                continue
            participants = self._normalize_segment_participants(segment, roster)
            if not participants:
                continue
            beat = self._build_promo_beat(year, week, show, source_type, source_id, segment, participants, rng, risk)
            self._insert_promo_beat(beat)
            beats.append(beat)
        return beats

    def _build_promo_beat(self, year: int, week: int, show: dict, source_type: str, source_id: str, segment: dict, participants: list[dict], rng: random.Random, risk: float) -> dict:
        tone = rng.choice(["defiant", "wounded", "arrogant", "urgent", "cold"])
        beat_type = segment.get("segment_type", "promo")
        lead = participants[0]
        reply = participants[1] if len(participants) > 1 else None
        hook = segment.get("description") or f"{lead['name']} gets a microphone and forces the room to listen."
        lines = [
            {"speaker_id": lead["id"], "speaker_name": lead["name"], "line": f"I am done waiting for permission. Tonight, I make them react to me."},
        ]
        if reply:
            lines.append({"speaker_id": reply["id"], "speaker_name": reply["name"], "line": f"You wanted attention. Now you have mine, and that is a problem for you."})
        lines.append({"speaker_id": lead["id"], "speaker_name": lead["name"], "line": "Remember this moment, because after tonight nobody gets to call me optional."})
        crowd_goal = rng.choice(["cheers", "heat", "shock", "sustained engagement"])
        effects = ["promo_clarity +8", "crowd_investment +6"]
        if risk >= 0.6:
            effects.append("creative_volatility +4")
        return {
            "id": new_id("promo_beat"),
            "year": year,
            "week": week,
            "show_id": show.get("show_id"),
            "source_type": source_type,
            "source_id": source_id,
            "beat_type": beat_type,
            "tone": tone,
            "status": "drafted",
            "participants_json": participants,
            "hook_text": hook,
            "lines_json": lines,
            "crowd_goal": crowd_goal,
            "risk_level": "high" if risk >= 0.68 else "medium",
            "mechanical_effects_json": effects,
            "created_at": self.now(),
            "updated_at": self.now(),
        }

    def _insert_promo_beat(self, beat: dict) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO promo_dialogue_beats (
                id, year, week, show_id, source_type, source_id, beat_type, tone,
                status, participants_json, hook_text, lines_json, crowd_goal,
                risk_level, mechanical_effects_json, created_at, updated_at, deleted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(
                (SELECT created_at FROM promo_dialogue_beats WHERE id = ?), ?
            ), ?, NULL)
            """,
            (
                beat["id"], beat["year"], beat["week"], beat["show_id"], beat["source_type"], beat["source_id"],
                beat["beat_type"], beat["tone"], beat["status"], json.dumps(beat["participants_json"]),
                beat["hook_text"], json.dumps(beat["lines_json"]), beat["crowd_goal"], beat["risk_level"],
                json.dumps(beat["mechanical_effects_json"]), beat["id"], beat["created_at"], beat["updated_at"],
            ),
        )
        self.conn.commit()

    def _normalize_segment_participants(self, segment: dict, roster_by_id: dict[str, dict]) -> list[dict]:
        participants = []
        for raw in segment.get("participants", []):
            if isinstance(raw, str):
                wrestler = roster_by_id.get(raw, {})
                participants.append({"id": raw, "name": wrestler.get("name", raw)})
            elif isinstance(raw, dict):
                wid = raw.get("id") or raw.get("wrestler_id") or raw.get("participant_id")
                if wid:
                    wrestler = roster_by_id.get(wid, {})
                    participants.append({"id": wid, "name": raw.get("name") or raw.get("wrestler_name") or wrestler.get("name", wid)})
        return participants

    def _participant_ids_from_show_draft(self, show_draft_data: dict) -> list[str]:
        ids = []
        for match in show_draft_data.get("matches", []):
            for key in ("participants",):
                for item in match.get(key, []) or []:
                    if isinstance(item, str):
                        ids.append(item)
                    elif isinstance(item, list):
                        ids.extend([v for v in item if isinstance(v, str)])
            for side_key in ("side_a", "side_b"):
                side = match.get(side_key) or {}
                ids.extend(side.get("wrestler_ids") or [])
        for segment in show_draft_data.get("segments", []):
            for item in segment.get("participants", []) or []:
                if isinstance(item, str):
                    ids.append(item)
                elif isinstance(item, dict):
                    wid = item.get("id") or item.get("wrestler_id") or item.get("participant_id")
                    if wid:
                        ids.append(wid)
        return list(dict.fromkeys([wid for wid in ids if wid]))

    def _select_interruption_participants(self, roster: list[dict], current_ids: list[str], rng: random.Random) -> list[dict]:
        current = [w for w in roster if w["id"] in current_ids]
        outsiders = [w for w in roster if w["id"] not in current_ids]
        selected = []
        if current:
            selected.append(rng.choice(current[: max(1, min(8, len(current)))]))
        if outsiders:
            selected.append(rng.choice(outsiders[: max(1, min(10, len(outsiders)))]))
        elif len(current) > 1:
            selected.append(rng.choice([w for w in current if w["id"] != selected[0]["id"]]))
        return selected or roster[:2]

    def _interruption_description(self, interruption_type: str, participants: list[dict], show_draft_data: dict) -> str:
        names = [p.get("name", p.get("id", "Unknown")) for p in participants]
        first = names[0] if names else "Someone"
        second = names[1] if len(names) > 1 else "the locker room"
        templates = {
            "surprise_run_in": f"{first} storms the ring without clearance and targets {second}, forcing production to follow the chaos.",
            "unscheduled_promo": f"{first} takes a live microphone and changes the emotional direction of the show.",
            "backstage_feed_cut": f"The broadcast cuts backstage as {first} and {second} collide in an unscheduled fight.",
            "authority_reversal": f"Management interrupts the show to alter the stakes around {first}.",
            "rival_invasion_tease": f"{first} appears through the crowd and leaves {second} staring at a possible invasion.",
        }
        return templates.get(interruption_type, f"{first} interrupts {show_draft_data.get('show_name', 'the show')} without warning.")

    def _run_special_systems(self, year: int, week: int, show: dict, roster: list[dict], opportunity: list[dict], card: dict, universe, rng: random.Random, risk: float, autonomy: str) -> dict:
        self._seed_angle_library()
        angle = self._book_angle_execution(year, week, show, roster, opportunity, card, rng, risk)
        mitb = self._refresh_mitb_system(year, week, roster, opportunity, rng)
        war_games = self._refresh_war_games_system(year, week, roster, universe, rng)
        crown = self._refresh_crown_payoff_system(year, week, roster, universe, rng)
        return {
            "angle_execution": angle,
            "mitb": mitb,
            "war_games": war_games,
            "crown_payoffs": crown,
            "autonomy": autonomy,
        }

    def _seed_angle_library(self) -> None:
        now = self.now()
        for template_id, name, category, segment_type, risk_level, cooldown, min_p, max_p, effects in ANGLE_LIBRARY_SEEDS:
            self.conn.execute(
                """
                INSERT INTO angle_library_templates (
                    id, name, category, segment_type, risk_level, cooldown_weeks,
                    min_participants, max_participants, eligibility_json,
                    mechanical_effects_json, created_at, updated_at, deleted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                ON CONFLICT(id) DO UPDATE SET name = excluded.name,
                    category = excluded.category, segment_type = excluded.segment_type,
                    risk_level = excluded.risk_level, cooldown_weeks = excluded.cooldown_weeks,
                    min_participants = excluded.min_participants, max_participants = excluded.max_participants,
                    mechanical_effects_json = excluded.mechanical_effects_json,
                    updated_at = excluded.updated_at, deleted_at = NULL
                """,
                (template_id, name, category, segment_type, risk_level, cooldown, min_p, max_p, "{}", json.dumps(effects), now, now),
            )
        self.conn.commit()

    def _book_angle_execution(self, year: int, week: int, show: dict, roster: list[dict], opportunity: list[dict], card: dict, rng: random.Random, risk: float) -> dict:
        templates = self.repo.fetch_all(
            """
            SELECT t.*
            FROM angle_library_templates t
            WHERE t.deleted_at IS NULL
              AND NOT EXISTS (
                  SELECT 1 FROM angle_executions e
                  WHERE e.template_id = t.id
                    AND ((e.year * 52) + e.week) >= ?
                    AND e.deleted_at IS NULL
              )
            ORDER BY CASE t.risk_level WHEN 'high' THEN ? ELSE 0 END DESC, t.category, t.name
            """,
            (((year * 52) + week) - 4, 1 if risk >= 0.58 else 0),
        )
        if not templates:
            templates = self.repo.fetch_all("SELECT * FROM angle_library_templates WHERE deleted_at IS NULL ORDER BY name LIMIT 12")
        template = rng.choice(templates[: max(1, min(6, len(templates)))])
        participant_count = max(int(template.get("min_participants") or 2), 2)
        participant_count = min(participant_count, int(template.get("max_participants") or participant_count), len(roster))
        preferred_ids = [item["id"] for item in opportunity]
        preferred = [w for wid in preferred_ids for w in roster if w["id"] == wid]
        participants = []
        used = set()
        for pool in (preferred, roster):
            for wrestler in pool:
                if wrestler["id"] in used:
                    continue
                participants.append(wrestler)
                used.add(wrestler["id"])
                if len(participants) >= participant_count:
                    break
            if len(participants) >= participant_count:
                break
        impact = {
            "heat_delta": 12 if template["risk_level"] == "high" else 7,
            "opportunity_delta": 10 if template["category"] == "opportunity" else 4,
            "mechanical_effects": self.repo.from_json(template.get("mechanical_effects_json"), []),
        }
        execution_id = new_id("angle_exec")
        now = self.now()
        self.conn.execute(
            """
            INSERT INTO angle_executions (
                id, template_id, template_name, show_id, year, week,
                participants_json, autonomy_status, impact_json, created_at, updated_at, deleted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'drafted', ?, ?, ?, NULL)
            """,
            (
                execution_id,
                template["id"],
                template["name"],
                show["show_id"],
                year,
                week,
                json.dumps([{"id": w["id"], "name": w["name"]} for w in participants]),
                json.dumps(impact),
                now,
                now,
            ),
        )
        self.conn.commit()
        segment = self._segment(
            f"angle_{template['id']}",
            template["segment_type"],
            5,
            7 if template["risk_level"] == "high" else 5,
            participants,
            f"{template['name']}: {', '.join(w['name'] for w in participants)} drives a live, AI-selected angle.",
        )
        segment["angle_template_id"] = template["id"]
        segment["angle_execution_id"] = execution_id
        segment["mechanical_effects"] = impact["mechanical_effects"]
        card["segments"].insert(-1, segment)
        for index, item in enumerate(card["segments"], start=1):
            item["position"] = index
        return {
            "id": execution_id,
            "template_id": template["id"],
            "template_name": template["name"],
            "category": template["category"],
            "risk_level": template["risk_level"],
            "participants": segment["participants"],
            "impact": impact,
        }

    def _refresh_mitb_system(self, year: int, week: int, roster: list[dict], opportunity: list[dict], rng: random.Random) -> dict:
        active = self._mitb_rows("planned", 10) + self._mitb_rows("active", 10)
        created = []
        if not active:
            for division, gender in (("mens", "Male"), ("womens", "Female")):
                candidates = [w for w in roster if str(w.get("gender", "")).lower() == gender.lower()]
                if not candidates:
                    candidates = roster
                opp_ids = [item["id"] for item in opportunity]
                candidates = sorted(candidates, key=lambda w: (0 if w["id"] in opp_ids else 1, -float(w.get("momentum") or 0), w["name"]))
                holder = candidates[0]
                row_id = f"mitb_{division}_y{year}"
                now = self.now()
                self.conn.execute(
                    """
                    INSERT INTO money_in_bank_briefcases (
                        id, division, holder_id, holder_name, status, won_year, won_week,
                        target_title_id, target_title_name, cash_in_window_weeks,
                        cash_in_attempts_json, next_ai_check_year, next_ai_check_week,
                        created_at, updated_at, deleted_at
                    ) VALUES (?, ?, ?, ?, 'planned', ?, ?, NULL, ?, 52, '[]', ?, ?, ?, ?, NULL)
                    ON CONFLICT(id) DO UPDATE SET holder_id = excluded.holder_id,
                        holder_name = excluded.holder_name, status = excluded.status,
                        next_ai_check_year = excluded.next_ai_check_year,
                        next_ai_check_week = excluded.next_ai_check_week,
                        updated_at = excluded.updated_at, deleted_at = NULL
                    """,
                    (row_id, division, holder["id"], holder["name"], year, week, f"{division.title()} World Championship", year, week + 2, now, now),
                )
                created.append({"id": row_id, "division": division, "holder_id": holder["id"], "holder_name": holder["name"], "status": "planned"})
            self.conn.commit()
        rows = self._mitb_rows(None, 10)
        cash_in_tease = None
        if rows and rng.random() < 0.45:
            chosen = rows[0]
            cash_in_tease = {
                "briefcase_id": chosen["id"],
                "holder_name": chosen["holder_name"],
                "division": chosen["division"],
                "tease": f"{chosen['holder_name']} circles the champion with a possible cash-in window.",
                "risk": "high",
            }
        return {"created": created, "briefcases": rows, "cash_in_tease": cash_in_tease}

    def _refresh_war_games_system(self, year: int, week: int, roster: list[dict], universe, rng: random.Random) -> dict:
        target = self._target_event(universe, year, week, ["Autumn", "Night of Glory", "Survival"], fallback_name="War Games")
        target_name, target_year, target_week = target
        existing = self.repo.fetch_one(
            "SELECT * FROM war_games_plans WHERE target_event_name = ? AND target_year = ? AND target_week = ? AND deleted_at IS NULL",
            (target_name, target_year, target_week),
        )
        if existing:
            return self._decode_war_games(existing)
        ranked = sorted(roster, key=lambda w: (w.get("overall", 0), w.get("popularity", 0)), reverse=True)
        team_size = min(4, max(3, len(ranked) // 2))
        faction_a = ranked[:team_size]
        faction_b = ranked[team_size:team_size * 2] or ranked[-team_size:]
        advantage = rng.choice(faction_a + faction_b)
        beats = [
            "Week 1: locker-room pull-apart",
            "Week 2: advantage match",
            "Week 3: final team reveal",
            "PLE: War Games cage payoff",
        ]
        row_id = f"wargames_{target_year}_{target_week}_{self._slug(target_name)}"
        now = self.now()
        self.conn.execute(
            """
            INSERT INTO war_games_plans (
                id, year, week, target_event_name, target_year, target_week, status,
                faction_a_json, faction_b_json, advantage_holder_json, stakes_json,
                escalation_beats_json, created_at, updated_at, deleted_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'building', ?, ?, ?, ?, ?, ?, ?, NULL)
            """,
            (
                row_id, year, week, target_name, target_year, target_week,
                json.dumps([{"id": w["id"], "name": w["name"]} for w in faction_a]),
                json.dumps([{"id": w["id"], "name": w["name"]} for w in faction_b]),
                json.dumps({"id": advantage["id"], "name": advantage["name"]}),
                json.dumps({"prize": "brand control advantage", "risk": "faction fracture if mishandled"}),
                json.dumps(beats),
                now,
                now,
            ),
        )
        self.conn.commit()
        return self._decode_war_games(self.repo.fetch_one("SELECT * FROM war_games_plans WHERE id = ?", (row_id,)))

    def _refresh_crown_payoff_system(self, year: int, week: int, roster: list[dict], universe, rng: random.Random) -> list[dict]:
        target_name, target_year, target_week = self._target_event(universe, year, week, ["Summer", "Champions", "Clash"], fallback_name="Crown Tournament Payoff")
        created = []
        for tournament_type, division, gender in (("king", "mens", "Male"), ("queen", "womens", "Female")):
            existing = self.repo.fetch_one(
                "SELECT * FROM crown_tournament_payoffs WHERE tournament_type = ? AND division = ? AND won_year = ? AND deleted_at IS NULL",
                (tournament_type, division, year),
            )
            if existing:
                created.append(self._decode_crown(existing))
                continue
            candidates = [w for w in roster if str(w.get("gender", "")).lower() == gender.lower()] or roster
            candidates = sorted(candidates, key=lambda w: (float(w.get("popularity") or 0), -float(w.get("overall") or 0)))
            winner = candidates[0]
            row_id = f"crown_{tournament_type}_{year}"
            now = self.now()
            self.conn.execute(
                """
                INSERT INTO crown_tournament_payoffs (
                    id, tournament_type, division, winner_id, winner_name, status,
                    won_year, won_week, payoff_event_name, payoff_year, payoff_week,
                    title_shot_json, coronation_angle_json, created_at, updated_at, deleted_at
                ) VALUES (?, ?, ?, ?, ?, 'planned', ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                """,
                (
                    row_id, tournament_type, division, winner["id"], winner["name"], year, week,
                    target_name, target_year, target_week,
                    json.dumps({"guaranteed": True, "target": f"{division.title()} world title", "can_be_countered": True}),
                    json.dumps({"angle": "coronation promo interrupted", "risk": "crowd rejection if winner is over-pushed"}),
                    now, now,
                ),
            )
            created.append(self._decode_crown(self.repo.fetch_one("SELECT * FROM crown_tournament_payoffs WHERE id = ?", (row_id,))))
        self.conn.commit()
        return created

    def _refresh_ple_roadmap(self, year: int, week: int, roster: list[dict], universe, rng: random.Random) -> list[dict]:
        shows = []
        try:
            shows = [s.to_dict() if hasattr(s, "to_dict") else dict(s) for s in universe.calendar.get_upcoming_ppvs(4)]
        except Exception:
            shows = []
        if not shows:
            shows = [{"name": "Next Premium Event", "show_type": "major_ppv", "year": year, "week": min(52, week + 6), "tier": "major"}]
        created = []
        top = sorted(roster, key=lambda w: (w.get("overall", 0), w.get("popularity", 0)), reverse=True)
        risks = sorted(roster, key=lambda w: (w.get("popularity", 0), -w.get("overall", 0)))[:4]
        for show in shows:
            event_name = show.get("name", "Premium Event")
            target_year = int(show.get("year") or year)
            target_week = int(show.get("week") or week)
            if target_year < year or (target_year == year and target_week < week):
                continue
            main = {
                "recommended_winner": top[0]["name"],
                "challenger": (top[1] if len(top) > 1 else top[0])["name"],
                "finish": "protected star-making finish" if rng.random() < 0.55 else "clean decisive finish",
            }
            risk_bets = [{"wrestler_id": w["id"], "name": w["name"], "reason": "AI wants one calculated gamble on an underused act."} for w in risks[:2]]
            row = {
                "id": f"roadmap_{target_year}_{target_week}_{self._slug(event_name)}",
                "year": year,
                "week": week,
                "event_name": event_name,
                "event_type": show.get("show_type", "major_ppv"),
                "target_year": target_year,
                "target_week": target_week,
                "status": "active",
                "headline_plan": f"Build {main['challenger']} toward {main['recommended_winner']} while testing {risk_bets[0]['name']} as the surprise accelerator.",
                "main_event_json": json.dumps(main),
                "title_plans_json": json.dumps([main]),
                "risk_bets_json": json.dumps(risk_bets),
            }
            now = self.now()
            self.conn.execute(
                """
                INSERT INTO ple_roadmap_plans (
                    id, year, week, event_name, event_type, target_year, target_week,
                    status, headline_plan, main_event_json, title_plans_json,
                    risk_bets_json, created_at, updated_at, deleted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                ON CONFLICT(event_name, target_year, target_week) DO UPDATE SET
                    year = excluded.year, week = excluded.week, headline_plan = excluded.headline_plan,
                    main_event_json = excluded.main_event_json, title_plans_json = excluded.title_plans_json,
                    risk_bets_json = excluded.risk_bets_json, updated_at = excluded.updated_at,
                    deleted_at = NULL
                """,
                (
                    row["id"], row["year"], row["week"], row["event_name"], row["event_type"],
                    row["target_year"], row["target_week"], row["status"], row["headline_plan"],
                    row["main_event_json"], row["title_plans_json"], row["risk_bets_json"], now, now,
                ),
            )
            created.append(row)
        self.conn.commit()
        return self._roadmaps(8)

    def _create_decisions(self, year: int, week: int, show: dict, card: dict, roadmaps: list[dict], autonomy: str, risk: float, special_systems: dict | None = None) -> tuple[list[dict], list[dict]]:
        approvals = []
        auto_executed = []
        special_systems = special_systems or {}
        main = card["segments"][-1]
        approvals.append(self._queue_item(
            year,
            week,
            "ai_showrunner",
            card["show_id"],
            "weekly_card",
            "high",
            f"Approve AI draft for {show['name']}",
            f"The AI drafted {len(card['segments'])} segments with {main['winner']['name']} positioned in the main-event result.",
            {"card": card, "recommended_action": "approve_or_counter_card"},
            "ask",
            None,
        ))
        for roadmap in roadmaps[:2]:
            approvals.append(self._queue_item(
                year,
                week,
                "ple_roadmap",
                roadmap["id"],
                "ple_direction",
                "critical" if "LegacyMania" in roadmap["event_name"] else "high",
                f"PLE roadmap: {roadmap['event_name']}",
                roadmap["headline_plan"],
                {"roadmap": roadmap, "recommended_action": "approve_counter_or_reject_direction"},
                "ask",
                None,
            ))
        opportunity_segment = card["segments"][1]
        policy = "auto_if_unanswered" if risk >= 0.55 else "ask"
        item = self._queue_item(
            year,
            week,
            "ai_showrunner",
            f"{card['show_id']}:opportunity",
            "opportunity_gamble",
            "medium",
            f"Gamble on {opportunity_segment['participants'][0]['name']}",
            opportunity_segment["description"],
            {"segment": opportunity_segment, "recommended_action": "let_ai_test_underused_wrestler"},
            policy,
            week + 1 if policy == "auto_if_unanswered" else None,
        )
        if autonomy == "aggressive":
            self.decide_approval(item["id"], {"decision": "auto_execute", "notes": "Aggressive showrunner autonomy executed the low-risk opportunity."})
            auto_executed.append(self._decode_queue(self.repo.fetch_one("SELECT * FROM booker_approval_queue WHERE id = ?", (item["id"],))))
        else:
            approvals.append(item)
        angle = special_systems.get("angle_execution")
        if angle:
            angle_item = self._queue_item(
                year,
                week,
                "angle_library",
                angle["id"],
                "angle_library",
                "high" if angle.get("risk_level") == "high" else "medium",
                f"Run angle: {angle['template_name']}",
                f"AI selected {angle['template_name']} for {', '.join(p['name'] for p in angle.get('participants', []))}.",
                {"angle": angle, "recommended_action": "approve_counter_or_let_ai_run_angle"},
                "auto_if_unanswered" if risk >= 0.55 else "ask",
                week + 1 if risk >= 0.55 else None,
            )
            approvals.append(angle_item)
        mitb = special_systems.get("mitb", {})
        if mitb.get("cash_in_tease"):
            approvals.append(self._queue_item(
                year,
                week,
                "money_in_bank",
                mitb["cash_in_tease"]["briefcase_id"],
                "money_in_bank",
                "critical",
                f"MITB tease: {mitb['cash_in_tease']['holder_name']}",
                mitb["cash_in_tease"]["tease"],
                {"mitb": mitb["cash_in_tease"], "recommended_action": "approve_counter_or_delay_cash_in"},
                "ask",
                None,
            ))
        if mitb.get("created"):
            for briefcase in mitb["created"][:2]:
                approvals.append(self._queue_item(
                    year,
                    week,
                    "money_in_bank",
                    briefcase["id"],
                    "money_in_bank_setup",
                    "high",
                    f"MITB holder plan: {briefcase['holder_name']}",
                    f"AI wants {briefcase['holder_name']} to become the {briefcase['division']} briefcase threat.",
                    {"briefcase": briefcase, "recommended_action": "approve_counter_or_reassign_holder"},
                    "ask",
                    None,
                ))
        war_games = special_systems.get("war_games")
        if war_games:
            approvals.append(self._queue_item(
                year,
                week,
                "war_games",
                war_games["id"],
                "war_games",
                "high",
                f"War Games build: {war_games['target_event_name']}",
                f"AI formed two faction sides and an advantage-match road for Y{war_games['target_year']} W{war_games['target_week']}.",
                {"war_games": war_games, "recommended_action": "approve_counter_or_rebuild_teams"},
                "ask",
                None,
            ))
        for crown in (special_systems.get("crown_payoffs") or [])[:2]:
            crown_item = self._queue_item(
                year,
                week,
                "crown_tournament",
                crown["id"],
                "crown_tournament",
                "medium",
                f"{crown['tournament_type'].title()} payoff: {crown['winner_name']}",
                f"AI books {crown['winner_name']} as {crown['tournament_type']} winner with a future title-shot payoff.",
                {"crown": crown, "recommended_action": "approve_counter_or_reseed_tournament"},
                "auto_if_unanswered" if risk >= 0.58 else "ask",
                week + 2 if risk >= 0.58 else None,
            )
            if autonomy == "aggressive":
                self.decide_approval(crown_item["id"], {"decision": "auto_execute", "notes": "Aggressive autonomy locked the crown tournament direction."})
                auto_executed.append(self._decode_queue(self.repo.fetch_one("SELECT * FROM booker_approval_queue WHERE id = ?", (crown_item["id"],))))
            else:
                approvals.append(crown_item)
        dark_house = special_systems.get("dark_house_autopilot") or {}
        dark_created = dark_house.get("created") or []
        if dark_created:
            approvals.append(self._queue_item(
                year,
                week,
                "dark_house_autopilot",
                f"{show['show_id']}:dark_house:{year}:{week}",
                "dark_house_autopilot",
                "medium",
                "Review dark/house show autopilot",
                f"AI ran {len(dark_created)} auxiliary show(s), rotating {sum(len(r.get('roster_focus_json', [])) for r in dark_created)} total talent slots.",
                {"dark_house": dark_created, "recommended_action": "approve_adjust_or_reduce_future_autopilot"},
                "auto_if_unanswered",
                week + 1,
            ))
        promo_beats = special_systems.get("promo_beats") or []
        if promo_beats:
            approvals.append(self._queue_item(
                year,
                week,
                "promo_dialogue",
                f"{show['show_id']}:promo_beats:{year}:{week}",
                "promo_dialogue",
                "medium",
                "Review AI promo/dialogue beats",
                f"AI generated {len(promo_beats)} promo beat(s) for this card.",
                {"promo_beats": promo_beats, "recommended_action": "approve_counter_or_rewrite_dialogue"},
                "auto_if_unanswered" if risk >= 0.55 else "ask",
                week + 1 if risk >= 0.55 else None,
            ))
        return approvals, auto_executed

    def _queue_item(self, year: int, week: int, source_type: str, source_id: str, category: str, priority: str, title: str, summary: str, recommendation: dict, policy: str, auto_week: int | None) -> dict:
        existing = self.repo.fetch_one(
            """
            SELECT * FROM booker_approval_queue
            WHERE source_type = ? AND source_id = ? AND category = ? AND status = 'pending' AND deleted_at IS NULL
            LIMIT 1
            """,
            (source_type, source_id, category),
        )
        if existing:
            return self._decode_queue(existing)
        now = self.now()
        row_id = new_id("approval")
        self.conn.execute(
            """
            INSERT INTO booker_approval_queue (
                id, source_type, source_id, category, priority, title, summary,
                recommendation_json, deadline_year, deadline_week, status,
                autonomy_policy, auto_execute_after_week, created_at, updated_at, deleted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, NULL)
            """,
            (row_id, source_type, source_id, category, priority, title, summary, json.dumps(recommendation), year, week + 1, policy, auto_week, now, now),
        )
        self.conn.commit()
        return self._decode_queue(self.repo.fetch_one("SELECT * FROM booker_approval_queue WHERE id = ?", (row_id,)))

    def _persist_show_plan(self, show: dict, card: dict, year: int, week: int) -> dict:
        total_runtime = 180 if show.get("is_ppv") else 120
        planned_start = 0
        segments = []
        for item in card["segments"]:
            segment_id = f"ai_{show['show_id']}_{item['id']}"
            segments.append({
                "id": segment_id,
                "show_id": show["show_id"],
                "source_item_id": item["id"],
                "item_type": "ai_showrunner",
                "segment_type": item["segment_type"],
                "card_position": item["position"],
                "planned_start_minute": planned_start,
                "planned_duration_minutes": item["duration"],
                "allocation_status": "ai_draft",
                "expected_min_minutes": max(1, item["duration"] - 3),
                "expected_max_minutes": item["duration"] + 5,
                "is_opening": 1 if item["position"] == 1 else 0,
                "is_main_event": 1 if item["id"] == "main_event" else 0,
                "quality_score": 68,
                "crowd_heat_score": 62,
                "payload_json": item,
            })
            planned_start += item["duration"]
        plan = {
            "show_id": show["show_id"],
            "show_name": show["name"],
            "brand": show["brand"],
            "show_type": show.get("show_type", "weekly_tv"),
            "year": year,
            "week": week,
            "total_runtime_minutes": total_runtime,
            "network_break_count": 8 if show.get("show_type") == "weekly_tv" else 0,
            "accept_overrun": True,
            "booking_credibility_delta": 2.5,
            "planned_rating_impact": 0.08,
            "dead_air_risk_minutes": max(0, total_runtime - planned_start),
            "overrun_minutes": max(0, planned_start - total_runtime),
            "warnings": ["AI-generated card: review major/title implications before simulating."],
        }
        return self.repo.replace_show_plan(plan, segments)

    def _card_to_booking_draft(self, run: dict, card: dict) -> dict:
        matches = []
        segments = []
        for index, item in enumerate(card.get("segments", []), start=1):
            participants = item.get("participants") or []
            ids = [p.get("id") for p in participants if p.get("id")]
            names = [p.get("name") for p in participants if p.get("name")]
            segment_type = item.get("segment_type") or "promo"
            if segment_type in {"match", "tag", "main_event_title_match"} and len(ids) >= 2:
                side_a = ids[:1]
                side_b = ids[1:2]
                winner = (item.get("winner") or {}).get("id")
                matches.append({
                    "match_id": f"ai_match_{item.get('id', index)}",
                    "match_type": "singles",
                    "participants": [ids[0], ids[1]],
                    "side_a": {"wrestler_ids": side_a, "wrestler_names": names[:1], "is_tag_team": False},
                    "side_b": {"wrestler_ids": side_b, "wrestler_names": names[1:2], "is_tag_team": False},
                    "booked_winner": winner,
                    "booking_bias": "slight_a" if winner == ids[0] else "slight_b" if winner == ids[1] else "even",
                    "importance": "high_drama" if segment_type == "main_event_title_match" else "normal",
                    "planned_duration_minutes": item.get("duration", 10),
                    "duration": item.get("duration", 10),
                    "position": item.get("position", index),
                    "card_position": item.get("position", index),
                    "is_title_match": segment_type == "main_event_title_match",
                    "ai_description": item.get("description"),
                })
            else:
                segments.append({
                    "segment_id": f"ai_segment_{item.get('id', index)}",
                    "segment_type": segment_type,
                    "display_name": item.get("description") or segment_type.replace("_", " ").title(),
                    "description": item.get("description"),
                    "participants": ids,
                    "participant_name_map": {p.get("id"): p.get("name") for p in participants if p.get("id")},
                    "duration": item.get("duration", 5),
                    "duration_minutes": item.get("duration", 5),
                    "position": item.get("position", index),
                    "card_position": item.get("position", index),
                    "purpose": "ai_showrunner",
                    "advances_feud": True,
                    "creates_heat": True,
                    "creates_pop": segment_type in {"promo", "interview", "vignette"},
                    "ai_mechanical_effects": item.get("mechanical_effects", []),
                })
        return {
            "show_id": run["show_id"],
            "show_name": run["show_name"],
            "brand": run["brand"],
            "show_type": "weekly_tv",
            "is_ppv": False,
            "year": run["year"],
            "week": run["week"],
            "matches": matches,
            "segments": segments,
            "ai_showrunner_run_id": run["id"],
            "ai_source": "AI Showrunner",
            "ai_creative_goal": card.get("creative_goal", "AI-generated booking plan"),
        }

    def _roadmaps(self, limit: int) -> list[dict]:
        rows = self.repo.fetch_all(
            """
            SELECT * FROM ple_roadmap_plans
            WHERE deleted_at IS NULL
            ORDER BY target_year, target_week
            LIMIT ?
            """,
            (limit,),
        )
        for row in rows:
            row["main_event_json"] = self.repo.from_json(row.get("main_event_json"), {})
            row["title_plans_json"] = self.repo.from_json(row.get("title_plans_json"), [])
            row["risk_bets_json"] = self.repo.from_json(row.get("risk_bets_json"), [])
        return rows

    def _special_system_snapshot(self) -> dict:
        templates_count = self.repo.fetch_one("SELECT COUNT(*) AS total FROM angle_library_templates WHERE deleted_at IS NULL")
        recent_angles = self.repo.fetch_all(
            """
            SELECT * FROM angle_executions
            WHERE deleted_at IS NULL
            ORDER BY created_at DESC
            LIMIT 8
            """
        )
        for row in recent_angles:
            row["participants_json"] = self.repo.from_json(row.get("participants_json"), [])
            row["impact_json"] = self.repo.from_json(row.get("impact_json"), {})
        return {
            "angle_templates_count": int((templates_count or {}).get("total") or 0),
            "recent_angles": recent_angles,
            "mitb_briefcases": self._mitb_rows(None, 8),
            "war_games": [self._decode_war_games(row) for row in self.repo.fetch_all(
                "SELECT * FROM war_games_plans WHERE deleted_at IS NULL ORDER BY target_year, target_week LIMIT 5"
            )],
            "crown_payoffs": [self._decode_crown(row) for row in self.repo.fetch_all(
                "SELECT * FROM crown_tournament_payoffs WHERE deleted_at IS NULL ORDER BY payoff_year, payoff_week LIMIT 6"
            )],
            "dark_house_runs": [self._decode_dark_house(row) for row in self.repo.fetch_all(
                "SELECT * FROM dark_house_show_runs WHERE deleted_at IS NULL ORDER BY created_at DESC LIMIT 6"
            )],
            "live_interruptions": [self._decode_live_interruption(row) for row in self.repo.fetch_all(
                "SELECT * FROM live_show_interruptions WHERE deleted_at IS NULL ORDER BY created_at DESC LIMIT 6"
            )],
            "promo_beats": [self._decode_promo_beat(row) for row in self.repo.fetch_all(
                "SELECT * FROM promo_dialogue_beats WHERE deleted_at IS NULL ORDER BY created_at DESC LIMIT 8"
            )],
        }

    def _mitb_rows(self, status: str | None, limit: int) -> list[dict]:
        if status:
            rows = self.repo.fetch_all(
                """
                SELECT * FROM money_in_bank_briefcases
                WHERE status = ? AND deleted_at IS NULL
                ORDER BY won_year DESC, won_week DESC
                LIMIT ?
                """,
                (status, limit),
            )
        else:
            rows = self.repo.fetch_all(
                """
                SELECT * FROM money_in_bank_briefcases
                WHERE deleted_at IS NULL
                ORDER BY CASE status WHEN 'active' THEN 0 WHEN 'planned' THEN 1 ELSE 2 END,
                         won_year DESC, won_week DESC
                LIMIT ?
                """,
                (limit,),
            )
        for row in rows:
            row["cash_in_attempts_json"] = self.repo.from_json(row.get("cash_in_attempts_json"), [])
        return rows

    def _decode_war_games(self, row: dict | None) -> dict:
        if not row:
            return {}
        row = dict(row)
        row["faction_a_json"] = self.repo.from_json(row.get("faction_a_json"), [])
        row["faction_b_json"] = self.repo.from_json(row.get("faction_b_json"), [])
        row["advantage_holder_json"] = self.repo.from_json(row.get("advantage_holder_json"), {})
        row["stakes_json"] = self.repo.from_json(row.get("stakes_json"), {})
        row["escalation_beats_json"] = self.repo.from_json(row.get("escalation_beats_json"), [])
        return row

    def _decode_crown(self, row: dict | None) -> dict:
        if not row:
            return {}
        row = dict(row)
        row["title_shot_json"] = self.repo.from_json(row.get("title_shot_json"), {})
        row["coronation_angle_json"] = self.repo.from_json(row.get("coronation_angle_json"), {})
        return row

    def _decode_dark_house(self, row: dict | None) -> dict:
        if not row:
            return {}
        row = dict(row)
        row["roster_focus_json"] = self.repo.from_json(row.get("roster_focus_json"), [])
        row["card_json"] = self.repo.from_json(row.get("card_json"), {})
        row["results_json"] = self.repo.from_json(row.get("results_json"), {})
        row["opportunity_impacts_json"] = self.repo.from_json(row.get("opportunity_impacts_json"), [])
        return row

    def _decode_live_interruption(self, row: dict | None) -> dict:
        if not row:
            return {}
        row = dict(row)
        row["participants_json"] = self.repo.from_json(row.get("participants_json"), [])
        row["segment_payload_json"] = self.repo.from_json(row.get("segment_payload_json"), {})
        row["mechanical_effects_json"] = self.repo.from_json(row.get("mechanical_effects_json"), [])
        return row

    def _decode_promo_beat(self, row: dict | None) -> dict:
        if not row:
            return {}
        row = dict(row)
        row["participants_json"] = self.repo.from_json(row.get("participants_json"), [])
        row["lines_json"] = self.repo.from_json(row.get("lines_json"), [])
        row["mechanical_effects_json"] = self.repo.from_json(row.get("mechanical_effects_json"), [])
        return row

    def _target_event(self, universe, year: int, week: int, keywords: list[str], fallback_name: str) -> tuple[str, int, int]:
        try:
            events = [s.to_dict() if hasattr(s, "to_dict") else dict(s) for s in universe.calendar.get_upcoming_ppvs(8)]
        except Exception:
            events = []
        for event in events:
            name = event.get("name", "")
            if any(keyword.lower() in name.lower() for keyword in keywords):
                return name, int(event.get("year") or year), int(event.get("week") or week)
        if events:
            event = events[min(2, len(events) - 1)]
            return event.get("name", fallback_name), int(event.get("year") or year), int(event.get("week") or min(52, week + 8))
        return fallback_name, year, min(52, week + 8)

    def _queue_rows(self, status: str | None, limit: int) -> list[dict]:
        if status:
            rows = self.repo.fetch_all(
                """
                SELECT * FROM booker_approval_queue
                WHERE status = ? AND deleted_at IS NULL
                ORDER BY CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                         created_at DESC
                LIMIT ?
                """,
                (status, limit),
            )
        else:
            rows = self.repo.fetch_all(
                """
                SELECT * FROM booker_approval_queue
                WHERE deleted_at IS NULL
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
        return [self._decode_queue(row) for row in rows]

    def _decode_queue(self, row: dict | None) -> dict:
        if not row:
            return {}
        row = dict(row)
        row["recommendation_json"] = self.repo.from_json(row.get("recommendation_json"), {})
        row["player_response_json"] = self.repo.from_json(row.get("player_response_json"), {})
        return row

    def _decode_run(self, row: dict) -> None:
        row["opportunity_rotation_json"] = self.repo.from_json(row.get("opportunity_rotation_json"), [])
        row["generated_card_json"] = self.repo.from_json(row.get("generated_card_json"), {})
        row["decisions_json"] = self.repo.from_json(row.get("decisions_json"), [])
        row["auto_executed_json"] = self.repo.from_json(row.get("auto_executed_json"), [])

    def _risk_from_autonomy(self, autonomy: str) -> float:
        return {"cautious": 0.35, "balanced": 0.58, "aggressive": 0.78}.get(autonomy, 0.58)

    def _slug(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")[:40] or "event"
