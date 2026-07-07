"""Evolve development system routes (Steps 171-182)."""

from __future__ import annotations

import json
import random
import uuid
from datetime import datetime
from typing import Dict, Any

from flask import Blueprint, current_app, jsonify, request


evolve_bp = Blueprint("evolve", __name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _db():
    return current_app.config["DATABASE"]


def _cursor():
    return _db().conn.cursor()


def _now() -> str:
    return datetime.now().isoformat()


def _current_year_week() -> tuple[int, int]:
    gs = _db().get_game_state()
    return int(gs.get("current_year", 1)), int(gs.get("current_week", 1))


def _load_json(value: Any, default):
    if not value:
        return default
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return default


def _dump_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _ensure_center_exists() -> None:
    cur = _cursor()
    cur.execute("SELECT center_id FROM evolve_performance_center LIMIT 1")
    if cur.fetchone():
        return
    cur.execute(
        """
        INSERT INTO evolve_performance_center (
            center_id, brand_name, facility_level, monthly_cost,
            training_quality, medical_quality, scouting_quality,
            active_curriculum_id, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "evolve_center_main",
            "Evolve",
            1,
            15000,
            52.0,
            50.0,
            50.0,
            "",
            _now(),
        ),
    )
    _db().conn.commit()


def _record_event(event_type: str, payload: Dict[str, Any], prospect_id: str = "", wrestler_id: str = ""):
    year, week = _current_year_week()
    cur = _cursor()
    cur.execute(
        """
        INSERT INTO evolve_events (
            event_id, event_type, prospect_id, wrestler_id,
            year, week, payload_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"ev_{uuid.uuid4().hex[:12]}",
            event_type,
            prospect_id,
            wrestler_id,
            year,
            week,
            _dump_json(payload),
            _now(),
        ),
    )


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@evolve_bp.route("/api/evolve/dashboard", methods=["GET"])
def evolve_dashboard():
    _ensure_center_exists()
    cur = _cursor()

    cur.execute("SELECT * FROM evolve_performance_center LIMIT 1")
    center = dict(cur.fetchone())

    cur.execute("SELECT COUNT(*) c FROM evolve_roster")
    roster_count = int(cur.fetchone()["c"])

    cur.execute("SELECT COUNT(*) c FROM evolve_roster WHERE status='trainee'")
    trainee_count = int(cur.fetchone()["c"])

    cur.execute("SELECT COUNT(*) c FROM evolve_roster WHERE readiness_score >= 75")
    callup_ready = int(cur.fetchone()["c"])

    cur.execute("SELECT COUNT(*) c FROM evolve_trainers WHERE is_active=1")
    trainer_count = int(cur.fetchone()["c"])

    cur.execute(
        "SELECT * FROM evolve_events ORDER BY created_at DESC LIMIT 12"
    )
    recent_events = []
    for r in cur.fetchall():
        row = dict(r)
        row["payload"] = _load_json(row.get("payload_json"), {})
        recent_events.append(row)

    return jsonify(
        {
            "ok": True,
            "center": center,
            "summary": {
                "roster_count": roster_count,
                "trainee_count": trainee_count,
                "callup_ready": callup_ready,
                "trainer_count": trainer_count,
            },
            "recent_events": recent_events,
        }
    )


# ---------------------------------------------------------------------------
# 171: Performance Center
# ---------------------------------------------------------------------------

@evolve_bp.route("/api/evolve/performance-center", methods=["GET", "PUT"])
def performance_center():
    _ensure_center_exists()
    cur = _cursor()

    if request.method == "GET":
        cur.execute("SELECT * FROM evolve_performance_center LIMIT 1")
        return jsonify({"ok": True, "center": dict(cur.fetchone())})

    data = request.get_json(force=True, silent=True) or {}
    updates = {
        "brand_name": data.get("brand_name", "Evolve"),
        "facility_level": int(data.get("facility_level", 1)),
        "monthly_cost": int(data.get("monthly_cost", 15000)),
        "training_quality": float(data.get("training_quality", 50.0)),
        "medical_quality": float(data.get("medical_quality", 50.0)),
        "scouting_quality": float(data.get("scouting_quality", 50.0)),
        "updated_at": _now(),
    }
    cur.execute(
        """
        UPDATE evolve_performance_center
        SET brand_name=?, facility_level=?, monthly_cost=?,
            training_quality=?, medical_quality=?, scouting_quality=?,
            updated_at=?
        WHERE center_id='evolve_center_main'
        """,
        (
            updates["brand_name"],
            updates["facility_level"],
            updates["monthly_cost"],
            updates["training_quality"],
            updates["medical_quality"],
            updates["scouting_quality"],
            updates["updated_at"],
        ),
    )
    _record_event("center_update", updates)
    _db().conn.commit()
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# 172/175: Developmental Roster + progression state
# ---------------------------------------------------------------------------

@evolve_bp.route("/api/evolve/roster", methods=["GET", "POST"])
def evolve_roster():
    cur = _cursor()
    if request.method == "GET":
        cur.execute("SELECT * FROM evolve_roster ORDER BY readiness_score DESC, wrestler_name")
        rows = []
        for r in cur.fetchall():
            d = dict(r)
            d["progression"] = _load_json(d.get("progression_json"), {})
            rows.append(d)
        return jsonify({"ok": True, "roster": rows})

    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("wrestler_name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "wrestler_name is required"}), 400

    pid = f"pros_{uuid.uuid4().hex[:10]}"
    progression = data.get("progression") or {
        "athleticism": random.randint(35, 60),
        "psychology": random.randint(30, 58),
        "charisma": random.randint(30, 58),
        "technique": random.randint(32, 60),
    }
    cur.execute(
        """
        INSERT INTO evolve_roster (
            prospect_id, wrestler_id, wrestler_name, status, readiness_score,
            progression_json, assigned_trainer_id, contract_notes, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            pid,
            data.get("wrestler_id", ""),
            name,
            data.get("status", "trainee"),
            float(data.get("readiness_score", 35.0)),
            _dump_json(progression),
            data.get("assigned_trainer_id", ""),
            data.get("contract_notes", ""),
            _now(),
            _now(),
        ),
    )
    _record_event("roster_add", {"wrestler_name": name}, prospect_id=pid)
    _db().conn.commit()
    return jsonify({"ok": True, "prospect_id": pid})


# ---------------------------------------------------------------------------
# 173/182: Trainers
# ---------------------------------------------------------------------------

@evolve_bp.route("/api/evolve/trainers", methods=["GET", "POST"])
def evolve_trainers():
    cur = _cursor()
    if request.method == "GET":
        cur.execute("SELECT * FROM evolve_trainers ORDER BY coaching_rating DESC, name")
        return jsonify({"ok": True, "trainers": [dict(r) for r in cur.fetchall()]})

    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    specialty = (data.get("specialty") or "general").strip()
    if not name:
        return jsonify({"ok": False, "error": "name is required"}), 400
    tid = f"tr_{uuid.uuid4().hex[:10]}"
    cur.execute(
        """
        INSERT INTO evolve_trainers (
            trainer_id, name, specialty, coaching_rating,
            veteran_status, salary, is_active, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            tid,
            name,
            specialty,
            float(data.get("coaching_rating", 52.0)),
            1 if data.get("veteran_status") else 0,
            int(data.get("salary", 3500)),
            1,
            _now(),
        ),
    )
    _record_event("trainer_hired", {"name": name, "specialty": specialty})
    _db().conn.commit()
    return jsonify({"ok": True, "trainer_id": tid})


@evolve_bp.route("/api/evolve/trainers/transition-veteran", methods=["POST"])
def transition_veteran():
    data = request.get_json(force=True, silent=True) or {}
    trainer_id = data.get("trainer_id")
    if not trainer_id:
        return jsonify({"ok": False, "error": "trainer_id is required"}), 400

    cur = _cursor()
    cur.execute("UPDATE evolve_trainers SET veteran_status=1 WHERE trainer_id=?", (trainer_id,))
    _record_event("trainer_transition_veteran", {"trainer_id": trainer_id})
    _db().conn.commit()
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# 174: Curriculum
# ---------------------------------------------------------------------------

@evolve_bp.route("/api/evolve/curricula", methods=["GET", "POST"])
def evolve_curricula():
    cur = _cursor()
    if request.method == "GET":
        cur.execute("SELECT * FROM evolve_curricula ORDER BY updated_at DESC")
        rows = []
        for r in cur.fetchall():
            d = dict(r)
            d["focus"] = _load_json(d.get("focus_json"), {})
            rows.append(d)
        return jsonify({"ok": True, "curricula": rows})

    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("curriculum_name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "curriculum_name is required"}), 400

    cid = f"cur_{uuid.uuid4().hex[:10]}"
    cur.execute(
        """
        INSERT INTO evolve_curricula (
            curriculum_id, curriculum_name, focus_json,
            intensity, injury_risk_modifier, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            cid,
            name,
            _dump_json(data.get("focus") or {}),
            float(data.get("intensity", 1.0)),
            float(data.get("injury_risk_modifier", 1.0)),
            _now(),
            _now(),
        ),
    )
    _record_event("curriculum_created", {"curriculum_name": name})
    _db().conn.commit()
    return jsonify({"ok": True, "curriculum_id": cid})


@evolve_bp.route("/api/evolve/curricula/assign", methods=["POST"])
def assign_curriculum():
    _ensure_center_exists()
    data = request.get_json(force=True, silent=True) or {}
    cid = data.get("curriculum_id", "")
    cur = _cursor()
    cur.execute(
        "UPDATE evolve_performance_center SET active_curriculum_id=?, updated_at=? WHERE center_id='evolve_center_main'",
        (cid, _now()),
    )
    _record_event("curriculum_assigned", {"curriculum_id": cid})
    _db().conn.commit()
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# 175/180: Progression run + injury risk
# ---------------------------------------------------------------------------

@evolve_bp.route("/api/evolve/progression/run", methods=["POST"])
def run_progression():
    cur = _cursor()
    _ensure_center_exists()

    cur.execute("SELECT * FROM evolve_performance_center LIMIT 1")
    center = dict(cur.fetchone())

    cur.execute("SELECT * FROM evolve_curricula WHERE curriculum_id=?", (center.get("active_curriculum_id", ""),))
    curriculum_row = cur.fetchone()
    curriculum = dict(curriculum_row) if curriculum_row else {"focus_json": "{}", "intensity": 1.0, "injury_risk_modifier": 1.0}
    focus = _load_json(curriculum.get("focus_json"), {})

    cur.execute("SELECT * FROM evolve_trainers WHERE is_active=1")
    trainers = [dict(t) for t in cur.fetchall()]
    trainer_map = {t["trainer_id"]: t for t in trainers}

    cur.execute("SELECT * FROM evolve_roster WHERE status IN ('trainee', 'tryout', 'excursion')")
    prospects = [dict(r) for r in cur.fetchall()]

    updates = []
    injuries = []

    base_gain = max(0.4, (float(center.get("training_quality", 50.0)) - 35.0) / 35.0)
    intensity = float(curriculum.get("intensity", 1.0) or 1.0)
    injury_mod = float(curriculum.get("injury_risk_modifier", 1.0) or 1.0)

    for p in prospects:
        prog = _load_json(p.get("progression_json"), {})
        trainer_bonus = 0.0
        trainer = trainer_map.get(p.get("assigned_trainer_id", ""))
        if trainer:
            trainer_bonus = max(0.0, (float(trainer.get("coaching_rating", 50.0)) - 40.0) / 100.0)
            spec = trainer.get("specialty", "")
            if spec:
                prog[spec] = float(prog.get(spec, 40)) + random.uniform(0.3, 1.2)

        for attr in ["athleticism", "psychology", "charisma", "technique"]:
            attr_focus = float(focus.get(attr, 1.0) or 1.0)
            prog[attr] = float(prog.get(attr, 40)) + random.uniform(0.1, 0.9) * base_gain * intensity * attr_focus + trainer_bonus

        readiness_gain = random.uniform(0.6, 2.2) * base_gain * intensity + trainer_bonus
        new_readiness = min(100.0, float(p.get("readiness_score", 0)) + readiness_gain)

        # Injury risk (Step 180)
        injury_roll = random.random()
        injury_threshold = 0.03 * intensity * injury_mod * (1.08 - float(center.get("medical_quality", 50.0)) / 100.0)
        injured = injury_roll < injury_threshold
        status = p.get("status", "trainee")
        if injured:
            status = "injured"
            injury_weeks = random.randint(1, 6)
            injuries.append({"prospect_id": p["prospect_id"], "wrestler_name": p["wrestler_name"], "weeks": injury_weeks})
            _record_event(
                "training_injury",
                {"prospect_id": p["prospect_id"], "wrestler_name": p["wrestler_name"], "injury_weeks": injury_weeks},
                prospect_id=p["prospect_id"],
                wrestler_id=p.get("wrestler_id", ""),
            )

        updates.append((
            _dump_json(prog),
            new_readiness,
            status,
            _now(),
            p["prospect_id"],
        ))

    cur.executemany(
        "UPDATE evolve_roster SET progression_json=?, readiness_score=?, status=?, updated_at=? WHERE prospect_id=?",
        updates,
    )
    _record_event("progression_run", {"processed": len(prospects), "injuries": len(injuries), "curriculum_id": center.get("active_curriculum_id", "")})
    _db().conn.commit()
    return jsonify({"ok": True, "processed": len(prospects), "injuries": injuries})


# ---------------------------------------------------------------------------
# 176: Tryout System
# ---------------------------------------------------------------------------

@evolve_bp.route("/api/evolve/tryouts/hold", methods=["POST"])
def hold_tryouts():
    data = request.get_json(force=True, silent=True) or {}
    count = max(1, min(20, int(data.get("count", 5))))
    cur = _cursor()

    backgrounds = [
        "college_athlete", "mma", "gymnast", "powerlifter", "stunt_performer",
        "indie_referee", "bodybuilder", "parkour", "martial_arts", "actor",
    ]

    created = []
    for _ in range(count):
        name = f"Tryout {uuid.uuid4().hex[:4].upper()}"
        pid = f"pros_{uuid.uuid4().hex[:10]}"
        bg = random.choice(backgrounds)
        progression = {
            "athleticism": random.randint(35, 70),
            "psychology": random.randint(25, 55),
            "charisma": random.randint(25, 65),
            "technique": random.randint(20, 60),
            "background": bg,
        }
        readiness = round((progression["athleticism"] + progression["technique"]) / 3.0, 1)
        cur.execute(
            """
            INSERT INTO evolve_roster (
                prospect_id, wrestler_id, wrestler_name, status, readiness_score,
                progression_json, assigned_trainer_id, contract_notes, created_at, updated_at
            ) VALUES (?, '', ?, 'tryout', ?, ?, '', ?, ?, ?)
            """,
            (pid, name, readiness, _dump_json(progression), f"Background: {bg}", _now(), _now()),
        )
        created.append({"prospect_id": pid, "wrestler_name": name, "background": bg, "readiness": readiness})

    _record_event("tryout_held", {"count": count, "created": created[:5]})
    _db().conn.commit()
    return jsonify({"ok": True, "created": created})


# ---------------------------------------------------------------------------
# 177: Developmental Show
# ---------------------------------------------------------------------------

@evolve_bp.route("/api/evolve/shows/run", methods=["POST"])
def run_developmental_show():
    cur = _cursor()
    cur.execute("SELECT * FROM evolve_roster WHERE status IN ('trainee','tryout') ORDER BY readiness_score DESC LIMIT 12")
    wrestlers = [dict(r) for r in cur.fetchall()]
    if len(wrestlers) < 2:
        return jsonify({"ok": False, "error": "Need at least 2 active prospects"}), 400

    random.shuffle(wrestlers)
    matches = []
    for i in range(0, len(wrestlers) - 1, 2):
        a, b = wrestlers[i], wrestlers[i + 1]
        winner = random.choice([a, b])
        loser = b if winner is a else a
        matches.append({"a": a["wrestler_name"], "b": b["wrestler_name"], "winner": winner["wrestler_name"]})
        cur.execute(
            "UPDATE evolve_roster SET readiness_score=MIN(100, readiness_score + ?), updated_at=? WHERE prospect_id=?",
            (random.uniform(0.6, 2.0), _now(), winner["prospect_id"]),
        )
        cur.execute(
            "UPDATE evolve_roster SET readiness_score=MIN(100, readiness_score + ?), updated_at=? WHERE prospect_id=?",
            (random.uniform(0.3, 1.4), _now(), loser["prospect_id"]),
        )

    _record_event("developmental_show", {"brand": "Evolve", "matches": matches, "match_count": len(matches)})
    _db().conn.commit()
    return jsonify({"ok": True, "brand": "Evolve", "matches": matches})


# ---------------------------------------------------------------------------
# 178/179: Call-up and Send-down
# ---------------------------------------------------------------------------

@evolve_bp.route("/api/evolve/call-up", methods=["POST"])
def call_up():
    data = request.get_json(force=True, silent=True) or {}
    prospect_id = data.get("prospect_id")
    if not prospect_id:
        return jsonify({"ok": False, "error": "prospect_id is required"}), 400

    cur = _cursor()
    cur.execute("SELECT * FROM evolve_roster WHERE prospect_id=?", (prospect_id,))
    row = cur.fetchone()
    if not row:
        return jsonify({"ok": False, "error": "Prospect not found"}), 404

    prospect = dict(row)
    cur.execute(
        "UPDATE evolve_roster SET status='main_roster', updated_at=? WHERE prospect_id=?",
        (_now(), prospect_id),
    )
    _record_event("call_up", {"prospect_id": prospect_id, "wrestler_name": prospect["wrestler_name"], "debut_plan": data.get("debut_plan", "standard_debut")}, prospect_id=prospect_id, wrestler_id=prospect.get("wrestler_id", ""))
    _db().conn.commit()
    return jsonify({"ok": True})


@evolve_bp.route("/api/evolve/send-down", methods=["POST"])
def send_down():
    data = request.get_json(force=True, silent=True) or {}
    prospect_id = data.get("prospect_id")
    if not prospect_id:
        return jsonify({"ok": False, "error": "prospect_id is required"}), 400

    cur = _cursor()
    cur.execute("SELECT * FROM evolve_roster WHERE prospect_id=?", (prospect_id,))
    row = cur.fetchone()
    if not row:
        return jsonify({"ok": False, "error": "Prospect not found"}), 404

    cur.execute(
        "UPDATE evolve_roster SET status='trainee', readiness_score=MAX(25, readiness_score - 5), updated_at=? WHERE prospect_id=?",
        (_now(), prospect_id),
    )
    _record_event("send_down", {"prospect_id": prospect_id, "reason": data.get("reason", "development_reset")}, prospect_id=prospect_id)
    _db().conn.commit()
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# 181: Excursions
# ---------------------------------------------------------------------------

@evolve_bp.route("/api/evolve/excursions/send", methods=["POST"])
def send_excursion():
    data = request.get_json(force=True, silent=True) or {}
    prospect_id = data.get("prospect_id")
    destination = (data.get("destination") or "Japan").strip()
    weeks = max(1, min(52, int(data.get("weeks", 8))))

    if not prospect_id:
        return jsonify({"ok": False, "error": "prospect_id is required"}), 400

    cur = _cursor()
    cur.execute("SELECT * FROM evolve_roster WHERE prospect_id=?", (prospect_id,))
    row = cur.fetchone()
    if not row:
        return jsonify({"ok": False, "error": "Prospect not found"}), 404

    p = dict(row)
    cur.execute(
        "UPDATE evolve_roster SET status='excursion', readiness_score=MIN(100, readiness_score + 4), contract_notes=?, updated_at=? WHERE prospect_id=?",
        (f"Excursion: {destination} ({weeks} weeks)", _now(), prospect_id),
    )

    _record_event(
        "international_excursion",
        {
            "prospect_id": prospect_id,
            "wrestler_name": p.get("wrestler_name"),
            "destination": destination,
            "weeks": weeks,
        },
        prospect_id=prospect_id,
        wrestler_id=p.get("wrestler_id", ""),
    )
    _db().conn.commit()
    return jsonify({"ok": True})
