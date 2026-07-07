"""Real-time world feed routes (Phase A)."""

from __future__ import annotations

import json
import random
import uuid
from datetime import datetime
from flask import Blueprint, current_app, jsonify, request

world_feed_bp = Blueprint("world_feed", __name__)


def _db():
    return current_app.config["DATABASE"]


def _cursor():
    return _db().conn.cursor()


def _now():
    return datetime.now().isoformat()


def _year_week():
    gs = _db().get_game_state()
    return int(gs.get("current_year", 1)), int(gs.get("current_week", 1))


def _jloads(v, default):
    try:
        return json.loads(v) if isinstance(v, str) else (v if v is not None else default)
    except Exception:
        return default


def _jdumps(v):
    return json.dumps(v, ensure_ascii=False)


def _future_year_week(year: int, week: int, add_weeks: int) -> tuple[int, int]:
    total_weeks = (year - 1) * 52 + week + add_weeks
    future_year = ((total_weeks - 1) // 52) + 1
    future_week = ((total_weeks - 1) % 52) + 1
    return future_year, future_week


def _is_expired(cur_year: int, cur_week: int, exp_year: int, exp_week: int) -> bool:
    return (cur_year, cur_week) > (exp_year, exp_week)


def _apply_consequences(feed_id: str, headline: str, impact: dict, significance: int, year: int, week: int):
    """
    Phase B consequence engine:
    - mirrors story into media/sentiment logs
    - creates persistent timed world modifiers (buzz multipliers and deltas)
    """
    cur = _cursor()
    created_at = _now()

    # Mirror to media coverage
    cur.execute(
        """
        INSERT INTO media_ecosystem_log (
            item_id, item_type, year, week, title, subject_ref, impact_score, payload_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"media_{uuid.uuid4().hex[:12]}",
            "world_feed_story",
            year,
            week,
            headline,
            feed_id,
            float(significance),
            _jdumps({"impact": impact}),
            created_at,
        ),
    )

    # Mirror to industry sentiment
    sentiment_score = float(impact.get("buzz_delta", 0)) + float(impact.get("ratings_delta", 0))
    cur.execute(
        """
        INSERT INTO industry_sentiment_log (
            sentiment_id, source_type, source_name, headline, sentiment_score,
            credibility, payload_json, year, week, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"sent_{uuid.uuid4().hex[:12]}",
            "world_feed",
            "KNN",
            headline,
            sentiment_score,
            60.0 + min(40.0, significance * 8.0),
            _jdumps({"impact": impact, "feed_id": feed_id}),
            year,
            week,
            created_at,
        ),
    )

    # Persistent world modifiers
    duration_weeks = max(1, min(8, significance + 1))
    exp_year, exp_week = _future_year_week(year, week, duration_weeks)
    for effect_key, raw in (impact or {}).items():
        value = float(raw or 0.0)
        if abs(value) < 0.01:
            continue
        cur.execute(
            """
            INSERT INTO world_modifiers (
                modifier_id, effect_key, effect_value, source_feed_id, source_headline,
                starts_year, starts_week, expires_year, expires_week, is_active, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (
                f"wm_{uuid.uuid4().hex[:12]}",
                effect_key,
                value,
                feed_id,
                headline,
                year,
                week,
                exp_year,
                exp_week,
                created_at,
            ),
        )


def _story_from_evolve_event(event: dict) -> dict:
    payload = _jloads(event.get("payload_json"), {})
    et = event.get("event_type", "generic")

    if et == "training_injury":
        name = payload.get("wrestler_name", "A prospect")
        weeks = payload.get("injury_weeks", 0)
        return {
            "headline": f"🚑 Evolve Injury Alert: {name} sidelined",
            "details": {"event_type": et, "weeks": weeks, "payload": payload},
            "impact": {"morale_delta": -2, "buzz_delta": 1, "development_velocity": -1},
            "significance": 4,
        }

    if et == "call_up":
        name = payload.get("wrestler_name", "Prospect")
        return {
            "headline": f"📈 Call-Up Buzz: {name} reaches main roster",
            "details": {"event_type": et, "payload": payload},
            "impact": {"ratings_delta": 1, "buzz_delta": 3, "morale_delta": 1},
            "significance": 3,
        }

    if et == "tryout_held":
        count = payload.get("count", 0)
        return {
            "headline": f"🎯 Tryout Wave: Evolve scouts {count} new prospects",
            "details": {"event_type": et, "payload": payload},
            "impact": {"scouting_momentum": 2, "buzz_delta": 1},
            "significance": 2,
        }

    if et == "international_excursion":
        name = payload.get("wrestler_name", "Prospect")
        destination = payload.get("destination", "abroad")
        return {
            "headline": f"✈️ Excursion Update: {name} sent to {destination}",
            "details": {"event_type": et, "payload": payload},
            "impact": {"in_ring_growth": 2, "buzz_delta": 1},
            "significance": 2,
        }

    if et == "developmental_show":
        matches = payload.get("match_count", 0)
        return {
            "headline": f"🎬 Evolve Showcase airs with {matches} developmental matches",
            "details": {"event_type": et, "payload": payload},
            "impact": {"development_velocity": 1, "buzz_delta": 1},
            "significance": 2,
        }

    generic = [
        "📰 Backstage chatter grows after a busy Evolve week",
        "📣 Fans are discussing Evolve’s latest performance updates",
        "🎙️ Industry pundits note momentum in your talent pipeline",
    ]
    return {
        "headline": random.choice(generic),
        "details": {"event_type": et, "payload": payload},
        "impact": {"buzz_delta": 1},
        "significance": 1,
    }


@world_feed_bp.route("/api/world/tick", methods=["POST"])
def world_tick():
    """Generate up to N world-feed stories from recent evolve events."""
    data = request.get_json(force=True, silent=True) or {}
    max_items = max(1, min(10, int(data.get("max_items", 3))))

    cur = _cursor()
    year, week = _year_week()

    cur.execute(
        """
        SELECT * FROM evolve_events
        ORDER BY created_at DESC
        LIMIT 25
        """
    )
    events = [dict(r) for r in cur.fetchall()]

    created = []
    for ev in events:
        if len(created) >= max_items:
            break

        source_event_id = ev.get("event_id")
        cur.execute("SELECT 1 FROM world_feed WHERE source_event_id=? LIMIT 1", (source_event_id,))
        if cur.fetchone():
            continue

        story = _story_from_evolve_event(ev)
        feed_id = f"wf_{uuid.uuid4().hex[:12]}"
        cur.execute(
            """
            INSERT INTO world_feed (
                feed_id, year, week, source_type, source_event_id,
                headline, details_json, impact_json, significance, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                feed_id,
                year,
                week,
                "evolve_event",
                source_event_id,
                story["headline"],
                _jdumps(story["details"]),
                _jdumps(story["impact"]),
                int(story.get("significance", 1)),
                _now(),
            ),
        )

        _apply_consequences(feed_id, story["headline"], story["impact"], int(story.get("significance", 1)), year, week)

        if int(story.get("significance", 1)) >= 4:
            cur.execute(
                """
                INSERT INTO historical_moments (
                    moment_id, year, week, show_id, title, description,
                    significance_level, tags_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"hm_{uuid.uuid4().hex[:12]}",
                    year,
                    week,
                    "",
                    story["headline"],
                    "Auto-promoted from world feed due to high significance.",
                    int(story.get("significance", 1)),
                    _jdumps(["world_feed", "auto_promoted"]),
                    _now(),
                ),
            )

        created.append(feed_id)

    if not created:
        # Keep world alive even on quiet weeks
        ambience_headline = random.choice([
            "🌍 Quiet Week: Fans await your next major booking move",
            "📺 TV chatter steady as the roster prepares for upcoming angles",
            "🎟️ Attendance speculation rises ahead of your next card",
        ])
        feed_id = f"wf_{uuid.uuid4().hex[:12]}"
        cur.execute(
            """
            INSERT INTO world_feed (
                feed_id, year, week, source_type, source_event_id,
                headline, details_json, impact_json, significance, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                feed_id,
                year,
                week,
                "ambient",
                None,
                ambience_headline,
                _jdumps({"kind": "ambient"}),
                _jdumps({"buzz_delta": 0}),
                1,
                _now(),
            ),
        )
        _apply_consequences(feed_id, ambience_headline, {"buzz_delta": 0}, 1, year, week)
        created.append(feed_id)

    _db().conn.commit()
    return jsonify({"ok": True, "created": len(created), "feed_ids": created})


@world_feed_bp.route("/api/world/feed", methods=["GET"])
def get_world_feed():
    """Get live world-feed stories with optional cursor-like filtering."""
    since = request.args.get("since", "").strip()
    limit = max(1, min(100, int(request.args.get("limit", 30))))

    cur = _cursor()
    if since:
        cur.execute(
            """
            SELECT * FROM world_feed
            WHERE created_at > ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (since, limit),
        )
    else:
        cur.execute(
            """
            SELECT * FROM world_feed
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )

    rows = []
    for r in cur.fetchall():
        d = dict(r)
        d["details"] = _jloads(d.get("details_json"), {})
        d["impact"] = _jloads(d.get("impact_json"), {})
        rows.append(d)

    return jsonify({"ok": True, "items": rows})


@world_feed_bp.route("/api/world/modifiers", methods=["GET"])
def get_world_modifiers():
    """
    Phase B live consequences endpoint:
    returns active modifiers + aggregated totals.
    """
    cur = _cursor()
    year, week = _year_week()

    cur.execute("SELECT * FROM world_modifiers WHERE is_active=1 ORDER BY created_at DESC")
    all_mods = [dict(r) for r in cur.fetchall()]

    active = []
    expired_ids = []
    for m in all_mods:
        if _is_expired(year, week, int(m["expires_year"]), int(m["expires_week"])):
            expired_ids.append(m["modifier_id"])
        else:
            active.append(m)

    if expired_ids:
        cur.executemany("UPDATE world_modifiers SET is_active=0 WHERE modifier_id=?", [(mid,) for mid in expired_ids])
        _db().conn.commit()

    totals = {}
    for m in active:
        k = m.get("effect_key", "unknown")
        totals[k] = float(totals.get(k, 0.0)) + float(m.get("effect_value", 0.0))

    return jsonify(
        {
            "ok": True,
            "year": year,
            "week": week,
            "active_modifiers": active,
            "totals": totals,
        }
    )
