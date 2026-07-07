"""Historical & Legacy hub routes (Steps 203-211)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List

from flask import Blueprint, current_app, jsonify, request

history_hub_bp = Blueprint("history_hub", __name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _db():
    return current_app.config["DATABASE"]


def _cursor():
    return _db().conn.cursor()


def _now() -> str:
    return datetime.now().isoformat()


def _year_week() -> tuple[int, int]:
    gs = _db().get_game_state()
    return int(gs.get("current_year", 1)), int(gs.get("current_week", 1))


def _j(v: Any, default):
    if v is None:
        return default
    if isinstance(v, (dict, list)):
        return v
    try:
        return json.loads(v)
    except Exception:
        return default


def _s(v: Any) -> str:
    return json.dumps(v, ensure_ascii=False)


def _sig_level(score: float, crowd_reaction: float, tags: List[str]) -> int:
    tag_boost = 1 if any(t in {"title_match", "main_event", "grudge_match", "debut"} for t in tags) else 0
    raw = (score * 0.55) + (crowd_reaction * 0.35) + (tag_boost * 8)
    if raw >= 85:
        return 4
    if raw >= 70:
        return 3
    if raw >= 55:
        return 2
    return 1


def _upsert_legacy_stats(participants: List[Dict[str, Any]], winner_ids: List[str]) -> None:
    cur = _cursor()
    win_set = set(winner_ids)

    for p in participants:
        wid = p.get("wrestler_id")
        name = p.get("wrestler_name") or wid or "Unknown"
        if not wid:
            continue

        cur.execute("SELECT * FROM wrestler_legacy_stats WHERE wrestler_id=?", (wid,))
        row = cur.fetchone()
        wins = losses = draws = total = titles_won = defenses = hof = 0
        accolades: List[str] = []
        if row:
            d = dict(row)
            wins = int(d.get("wins", 0))
            losses = int(d.get("losses", 0))
            draws = int(d.get("draws", 0))
            total = int(d.get("total_matches", 0))
            titles_won = int(d.get("titles_won", 0))
            defenses = int(d.get("title_defenses", 0))
            hof = int(d.get("hall_of_fame_inducted", 0))
            accolades = _j(d.get("accolades_json"), [])

        total += 1
        if wid in win_set:
            wins += 1
        else:
            losses += 1

        win_pct = (wins / total) * 100 if total else 0

        cur.execute(
            """
            INSERT OR REPLACE INTO wrestler_legacy_stats (
                wrestler_id, wrestler_name, total_matches, wins, losses, draws,
                win_pct, titles_won, title_defenses, hall_of_fame_inducted,
                accolades_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                wid, name, total, wins, losses, draws,
                win_pct, titles_won, defenses, hof,
                _s(accolades), _now(),
            ),
        )


def _upsert_rivalry(participants: List[Dict[str, Any]], winner_ids: List[str], match_ref: Dict[str, Any]) -> None:
    if len(participants) < 2:
        return
    cur = _cursor()

    a = participants[0]
    b = participants[1]
    a_id, b_id = a.get("wrestler_id"), b.get("wrestler_id")
    if not a_id or not b_id:
        return

    rivalry_key = "|".join(sorted([a_id, b_id]))
    rid = f"riv_{rivalry_key.replace('|', '_')}"

    cur.execute("SELECT * FROM rivalry_history WHERE rivalry_id=?", (rid,))
    row = cur.fetchone()
    total = a_wins = b_wins = draws = 0
    peak = 0.0
    timeline: List[Dict[str, Any]] = []
    if row:
        d = dict(row)
        total = int(d.get("total_matches", 0))
        a_wins = int(d.get("a_wins", 0))
        b_wins = int(d.get("b_wins", 0))
        draws = int(d.get("draws", 0))
        peak = float(d.get("intensity_peak", 0.0))
        timeline = _j(d.get("timeline_json"), [])

    total += 1
    if a_id in winner_ids:
        a_wins += 1
    elif b_id in winner_ids:
        b_wins += 1
    else:
        draws += 1

    intensity = min(100.0, (total * 6.5) + (abs(a_wins - b_wins) * 2.0))
    peak = max(peak, intensity)

    year, week = int(match_ref.get("year", 1)), int(match_ref.get("week", 1))
    timeline.append(
        {
            "year": year,
            "week": week,
            "match_id": match_ref.get("history_match_id"),
            "winner_ids": winner_ids,
            "rating": match_ref.get("match_rating", 0),
        }
    )

    cur.execute(
        """
        INSERT OR REPLACE INTO rivalry_history (
            rivalry_id, wrestler_a_id, wrestler_b_id,
            total_matches, a_wins, b_wins, draws,
            intensity_peak, latest_update_year, latest_update_week,
            timeline_json, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM rivalry_history WHERE rivalry_id=?), ?), ?)
        """,
        (
            rid, a_id, b_id,
            total, a_wins, b_wins, draws,
            peak, year, week,
            _s(timeline), rid, _now(), _now(),
        ),
    )


def _update_records() -> None:
    cur = _cursor()

    # Fastest victory
    cur.execute("SELECT history_match_id, duration_minutes FROM history_matches WHERE duration_minutes > 0 ORDER BY duration_minutes ASC LIMIT 1")
    fv = cur.fetchone()
    if fv:
        cur.execute(
            """
            INSERT OR REPLACE INTO history_records (
                record_id, record_type, metric_name, holder_ref,
                value_numeric, value_text, context_json, set_year, set_week, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "rec_fastest_victory",
                "match",
                "Fastest Victory",
                fv["history_match_id"],
                float(fv["duration_minutes"]),
                f"{fv['duration_minutes']} min",
                _s({"history_match_id": fv["history_match_id"]}),
                *_year_week(),
                _now(),
            ),
        )

    # Most wins
    cur.execute("SELECT wrestler_id, wins FROM wrestler_legacy_stats ORDER BY wins DESC LIMIT 1")
    mw = cur.fetchone()
    if mw:
        cur.execute(
            """
            INSERT OR REPLACE INTO history_records (
                record_id, record_type, metric_name, holder_ref,
                value_numeric, value_text, context_json, set_year, set_week, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "rec_most_wins",
                "career",
                "Most Career Wins",
                mw["wrestler_id"],
                float(mw["wins"]),
                str(mw["wins"]),
                _s({}),
                *_year_week(),
                _now(),
            ),
        )


# ---------------------------------------------------------------------------
# Dashboard + timeline/search
# ---------------------------------------------------------------------------

@history_hub_bp.route("/api/history/dashboard", methods=["GET"])
def history_dashboard():
    cur = _cursor()

    def cnt(tbl):
        cur.execute(f"SELECT COUNT(*) c FROM {tbl}")
        return int(cur.fetchone()["c"])

    summary = {
        "matches": cnt("history_matches"),
        "storylines": cnt("history_storylines"),
        "lineages": cnt("history_championships"),
        "hall_of_fame": cnt("hall_of_fame"),
        "rivalries": cnt("rivalry_history"),
        "records": cnt("history_records"),
        "moments": cnt("historical_moments"),
        "eras": cnt("named_eras"),
    }

    cur.execute("SELECT * FROM historical_moments ORDER BY created_at DESC LIMIT 10")
    moments = [dict(r) for r in cur.fetchall()]

    return jsonify({"ok": True, "summary": summary, "latest_moments": moments})


@history_hub_bp.route("/api/history/matches", methods=["GET", "POST"])
def history_matches_api():
    cur = _cursor()

    if request.method == "GET":
        wrestler_a = request.args.get("wrestler_a", "").strip()
        wrestler_b = request.args.get("wrestler_b", "").strip()
        match_type = request.args.get("match_type", "").strip()
        limit = max(1, min(200, int(request.args.get("limit", 50))))

        where = []
        vals: List[Any] = []

        if wrestler_a:
            where.append("participants_json LIKE ?")
            vals.append(f"%{wrestler_a}%")
        if wrestler_b:
            where.append("participants_json LIKE ?")
            vals.append(f"%{wrestler_b}%")
        if match_type:
            where.append("details_json LIKE ?")
            vals.append(f"%{match_type}%")

        clause = f"WHERE {' AND '.join(where)}" if where else ""
        cur.execute(
            f"SELECT * FROM history_matches {clause} ORDER BY year DESC, week DESC, created_at DESC LIMIT ?",
            (*vals, limit),
        )
        rows = []
        for r in cur.fetchall():
            d = dict(r)
            d["participants"] = _j(d.get("participants_json"), [])
            d["winner_ids"] = _j(d.get("winner_ids_json"), [])
            rows.append(d)
        return jsonify({"ok": True, "matches": rows})

    data = request.get_json(force=True, silent=True) or {}
    year = int(data.get("year", _year_week()[0]))
    week = int(data.get("week", _year_week()[1]))

    participants = data.get("participants") or []
    winner_ids = data.get("winner_ids") or []
    tags = data.get("tags") or []

    if not participants:
        return jsonify({"ok": False, "error": "participants required"}), 400

    match_rating = float(data.get("match_rating", 60.0))
    crowd = float(data.get("crowd_reaction", 60.0))
    significance = _sig_level(match_rating, crowd, tags)

    history_match_id = f"hmatch_{uuid.uuid4().hex[:12]}"
    cur.execute(
        """
        INSERT INTO history_matches (
            history_match_id, match_id, show_id, show_name, year, week,
            participants_json, winner_ids_json, finish_type, duration_minutes,
            match_rating, significance, notes, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            history_match_id,
            data.get("match_id", ""),
            data.get("show_id", ""),
            data.get("show_name", "Unknown Show"),
            year,
            week,
            _s(participants),
            _s(winner_ids),
            data.get("finish_type", "pinfall"),
            int(data.get("duration_minutes", 10)),
            match_rating,
            significance,
            data.get("notes", ""),
            _now(),
        ),
    )

    match_ref = {
        "history_match_id": history_match_id,
        "year": year,
        "week": week,
        "match_rating": match_rating,
    }
    _upsert_legacy_stats(participants, winner_ids)
    _upsert_rivalry(participants, winner_ids, match_ref)
    _update_records()

    if significance >= 3:
        cur.execute(
            """
            INSERT INTO historical_moments (
                moment_id, year, week, show_id, title, description,
                significance_level, tags_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"moment_{uuid.uuid4().hex[:12]}",
                year,
                week,
                data.get("show_id", ""),
                data.get("headline", f"{data.get('show_name','Show')} standout match"),
                data.get("notes", "Auto-generated from match history entry."),
                significance,
                _s(tags),
                _now(),
            ),
        )

    # anniversary callbacks for debuts
    if "debut" in tags:
        cur.execute(
            """
            INSERT INTO history_anniversaries (
                anniversary_id, subject_type, subject_ref, original_date,
                reminder_window_weeks, callback_suggestions_json, is_active, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (
                f"ann_{uuid.uuid4().hex[:12]}",
                "match_debut",
                history_match_id,
                _now(),
                4,
                _s(["debut_callback", "video_package", "career_retrospective"]),
                _now(),
            ),
        )

    _db().conn.commit()
    return jsonify({"ok": True, "history_match_id": history_match_id, "significance": significance})


@history_hub_bp.route("/api/history/wrestler/<wrestler_id>/timeline", methods=["GET"])
def wrestler_timeline(wrestler_id: str):
    cur = _cursor()
    cur.execute(
        """
        SELECT * FROM history_matches
        WHERE participants_json LIKE ?
        ORDER BY year ASC, week ASC
        """,
        (f"%{wrestler_id}%",),
    )
    matches = [dict(r) for r in cur.fetchall()]

    cur.execute("SELECT * FROM wrestler_legacy_stats WHERE wrestler_id=?", (wrestler_id,))
    row = cur.fetchone()
    stats = dict(row) if row else None
    if stats and "accolades_json" in stats:
        stats["accolades"] = _j(stats.get("accolades_json"), [])

    return jsonify({"ok": True, "timeline": matches, "stats": stats})


# ---------------------------------------------------------------------------
# Storyline archive
# ---------------------------------------------------------------------------

@history_hub_bp.route("/api/history/storylines", methods=["GET", "POST"])
def storyline_archive_api():
    cur = _cursor()

    if request.method == "GET":
        cur.execute("SELECT * FROM history_storylines ORDER BY start_year DESC, start_week DESC")
        rows = []
        for r in cur.fetchall():
            d = dict(r)
            d["participants"] = _j(d.get("participants_json"), [])
            d["continuity_tags"] = _j(d.get("continuity_tags_json"), [])
            rows.append(d)
        return jsonify({"ok": True, "storylines": rows})

    data = request.get_json(force=True, silent=True) or {}
    sid = f"story_{uuid.uuid4().hex[:12]}"
    year, week = _year_week()
    cur.execute(
        """
        INSERT INTO history_storylines (
            storyline_id, feud_id, title, participants_json,
            start_year, start_week, end_year, end_week,
            climax_match_id, outcome_summary, continuity_tags_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            sid,
            data.get("feud_id", ""),
            data.get("title", "Untitled Storyline"),
            _s(data.get("participants", [])),
            int(data.get("start_year", year)),
            int(data.get("start_week", week)),
            data.get("end_year"),
            data.get("end_week"),
            data.get("climax_match_id", ""),
            data.get("outcome_summary", ""),
            _s(data.get("continuity_tags", [])),
            _now(),
        ),
    )
    _db().conn.commit()
    return jsonify({"ok": True, "storyline_id": sid})


# ---------------------------------------------------------------------------
# Championship history
# ---------------------------------------------------------------------------

@history_hub_bp.route("/api/history/championships", methods=["GET", "POST"])
def championship_history_api():
    cur = _cursor()

    if request.method == "GET":
        champ_id = request.args.get("championship_id", "").strip()
        if champ_id:
            cur.execute("SELECT * FROM history_championships WHERE championship_id=? ORDER BY reign_start_year, reign_start_week", (champ_id,))
        else:
            cur.execute("SELECT * FROM history_championships ORDER BY reign_start_year DESC, reign_start_week DESC")
        rows = []
        for r in cur.fetchall():
            d = dict(r)
            d["memorable_moments"] = _j(d.get("memorable_moments_json"), [])
            rows.append(d)
        return jsonify({"ok": True, "lineage": rows})

    data = request.get_json(force=True, silent=True) or {}
    lid = f"lin_{uuid.uuid4().hex[:12]}"
    year, week = _year_week()
    cur.execute(
        """
        INSERT INTO history_championships (
            lineage_id, championship_id, championship_name,
            champion_id, champion_name, reign_number,
            reign_start_year, reign_start_week,
            reign_end_year, reign_end_week,
            defenses, memorable_moments_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            lid,
            data.get("championship_id", "unknown_title"),
            data.get("championship_name", "Unknown Championship"),
            data.get("champion_id", ""),
            data.get("champion_name", "Unknown"),
            int(data.get("reign_number", 1)),
            int(data.get("reign_start_year", year)),
            int(data.get("reign_start_week", week)),
            data.get("reign_end_year"),
            data.get("reign_end_week"),
            int(data.get("defenses", 0)),
            _s(data.get("memorable_moments", [])),
            _now(),
        ),
    )
    _db().conn.commit()
    return jsonify({"ok": True, "lineage_id": lid})


# ---------------------------------------------------------------------------
# Hall of Fame
# ---------------------------------------------------------------------------

@history_hub_bp.route("/api/history/hof", methods=["GET", "POST"])
def hall_of_fame_api():
    cur = _cursor()

    if request.method == "GET":
        cur.execute("SELECT * FROM hall_of_fame ORDER BY induction_year DESC, induction_week DESC")
        return jsonify({"ok": True, "inductees": [dict(r) for r in cur.fetchall()]})

    data = request.get_json(force=True, silent=True) or {}
    iid = f"hof_{uuid.uuid4().hex[:12]}"
    year, week = _year_week()
    wid = data.get("wrestler_id")
    wname = data.get("wrestler_name", "Unknown")

    cur.execute(
        """
        INSERT INTO hall_of_fame (
            induction_id, wrestler_id, wrestler_name,
            induction_year, induction_week,
            induction_tier, speech_notes, legacy_score, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            iid, wid, wname,
            int(data.get("induction_year", year)),
            int(data.get("induction_week", week)),
            data.get("induction_tier", "standard"),
            data.get("speech_notes", ""),
            float(data.get("legacy_score", 75.0)),
            _now(),
        ),
    )

    if wid:
        cur.execute("UPDATE wrestler_legacy_stats SET hall_of_fame_inducted=1, updated_at=? WHERE wrestler_id=?", (_now(), wid))

    _db().conn.commit()
    return jsonify({"ok": True, "induction_id": iid})


@history_hub_bp.route("/api/history/hof/candidates", methods=["GET"])
def hall_of_fame_candidates():
    cur = _cursor()
    cur.execute(
        """
        SELECT * FROM wrestler_legacy_stats
        WHERE hall_of_fame_inducted = 0
        ORDER BY (wins * 0.6 + win_pct * 0.4 + titles_won * 5 + title_defenses * 2) DESC
        LIMIT 20
        """
    )
    return jsonify({"ok": True, "candidates": [dict(r) for r in cur.fetchall()]})


# ---------------------------------------------------------------------------
# Rivalries, anniversaries, records, moments, eras
# ---------------------------------------------------------------------------

@history_hub_bp.route("/api/history/rivalries", methods=["GET"])
def rivalry_list():
    cur = _cursor()
    cur.execute("SELECT * FROM rivalry_history ORDER BY intensity_peak DESC, total_matches DESC")
    rows = []
    for r in cur.fetchall():
        d = dict(r)
        d["timeline"] = _j(d.get("timeline_json"), [])
        rows.append(d)
    return jsonify({"ok": True, "rivalries": rows})


@history_hub_bp.route("/api/history/anniversaries/upcoming", methods=["GET"])
def upcoming_anniversaries():
    window_days = max(1, min(365, int(request.args.get("days", 60))))
    cur = _cursor()
    cur.execute("SELECT * FROM history_anniversaries WHERE is_active=1")

    today = datetime.now().date()
    horizon = today + timedelta(days=window_days)
    out = []
    for r in cur.fetchall():
        d = dict(r)
        try:
            original = datetime.fromisoformat(d.get("original_date")).date()
            this_year = original.replace(year=today.year)
            next_year = original.replace(year=today.year + 1)
            upcoming = this_year if this_year >= today else next_year
            if today <= upcoming <= horizon:
                d["upcoming_date"] = upcoming.isoformat()
                d["callback_suggestions"] = _j(d.get("callback_suggestions_json"), [])
                out.append(d)
        except Exception:
            continue

    out.sort(key=lambda x: x.get("upcoming_date", ""))
    return jsonify({"ok": True, "anniversaries": out})


@history_hub_bp.route("/api/history/records", methods=["GET"])
def records_api():
    cur = _cursor()
    cur.execute("SELECT * FROM history_records ORDER BY value_numeric DESC")
    records = [dict(r) for r in cur.fetchall()]

    alerts = []
    # Near-record alert: top 3 wins chasers
    cur.execute("SELECT wrestler_name, wins FROM wrestler_legacy_stats ORDER BY wins DESC LIMIT 3")
    top = [dict(r) for r in cur.fetchall()]
    if len(top) >= 2:
        leader, challenger = top[0], top[1]
        gap = int(leader["wins"] - challenger["wins"])
        if gap <= 3:
            alerts.append(f"{challenger['wrestler_name']} is within {gap} win(s) of {leader['wrestler_name']} for all-time wins.")

    return jsonify({"ok": True, "records": records, "near_record_alerts": alerts})


@history_hub_bp.route("/api/history/moments", methods=["GET"])
def moments_api():
    cur = _cursor()
    level = request.args.get("level", "").strip()
    if level:
        cur.execute("SELECT * FROM historical_moments WHERE significance_level=? ORDER BY year DESC, week DESC", (int(level),))
    else:
        cur.execute("SELECT * FROM historical_moments ORDER BY year DESC, week DESC, created_at DESC")
    rows = []
    for r in cur.fetchall():
        d = dict(r)
        d["tags"] = _j(d.get("tags_json"), [])
        rows.append(d)
    return jsonify({"ok": True, "moments": rows})


@history_hub_bp.route("/api/history/eras", methods=["GET", "POST"])
def eras_api():
    cur = _cursor()

    if request.method == "GET":
        detect = request.args.get("detect", "0") == "1"
        if detect:
            cur.execute("SELECT * FROM history_matches ORDER BY year DESC, week DESC LIMIT 120")
            recent = [dict(r) for r in cur.fetchall()]
            match_volume = len(recent)
            avg_sig = sum(float(r.get("significance", 1)) for r in recent) / match_volume if match_volume else 1

            tag_team_like = sum(1 for r in recent if "tag" in str(r.get("finish_type", "")).lower())
            hardcore_like = sum(1 for r in recent if any(k in str(r.get("notes", "")).lower() for k in ["hardcore", "extreme", "no dq", "street"]))

            if hardcore_like > tag_team_like and avg_sig >= 2.5:
                suggestion = "The Hardcore Revolution"
                style = ["hardcore", "high-risk", "chaotic"]
            elif tag_team_like >= hardcore_like and tag_team_like > 20:
                suggestion = "The Tag Team Renaissance"
                style = ["tag_team", "division_depth", "faction_wars"]
            else:
                suggestion = "The Dominance Era"
                style = ["title_focus", "star_power", "main_event_legacy"]

            return jsonify(
                {
                    "ok": True,
                    "suggested_era": {
                        "era_name": suggestion,
                        "defining_stars": [],
                        "style_markers": style,
                        "confidence": round(min(0.99, 0.4 + (avg_sig / 5.0)), 2),
                    },
                    "signals": {"match_volume": match_volume, "avg_significance": round(avg_sig, 2), "hardcore_like": hardcore_like, "tag_like": tag_team_like},
                }
            )

        cur.execute("SELECT * FROM named_eras ORDER BY start_year DESC, start_week DESC")
        rows = []
        for r in cur.fetchall():
            d = dict(r)
            d["defining_stars"] = _j(d.get("defining_stars_json"), [])
            d["style_markers"] = _j(d.get("style_markers_json"), [])
            rows.append(d)
        return jsonify({"ok": True, "eras": rows})

    data = request.get_json(force=True, silent=True) or {}
    eid = f"era_{uuid.uuid4().hex[:12]}"
    year, week = _year_week()
    cur.execute(
        """
        INSERT INTO named_eras (
            era_id, era_name, start_year, start_week,
            end_year, end_week, defining_stars_json, style_markers_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            eid,
            data.get("era_name", "Unnamed Era"),
            int(data.get("start_year", year)),
            int(data.get("start_week", week)),
            data.get("end_year"),
            data.get("end_week"),
            _s(data.get("defining_stars", [])),
            _s(data.get("style_markers", [])),
            _now(),
        ),
    )
    _db().conn.commit()
    return jsonify({"ok": True, "era_id": eid})
