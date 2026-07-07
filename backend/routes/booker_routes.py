from __future__ import annotations

import json
import uuid
from datetime import datetime
from flask import Blueprint, current_app, jsonify, request
from services.ai_showrunner_service import AIShowrunnerService
from services.post_show_fallout_service import PostShowFalloutService

booker_bp = Blueprint('booker', __name__)

PERSONALITIES = {"veteran", "marketer", "historian", "anarchist"}
PRIORITIES = {"urgent", "opportunity", "spark"}
STATUSES = {"open", "accepted", "rejected", "modified", "pinned", "dismissed"}


def get_database():
    return current_app.config['DATABASE']


def get_universe():
    return current_app.config.get('UNIVERSE')


def get_showrunner():
    service = current_app.config.get('AI_SHOWRUNNER_SERVICE')
    if service is None:
        service = AIShowrunnerService(get_database())
        current_app.config['AI_SHOWRUNNER_SERVICE'] = service
    return service


def get_post_show_fallout():
    service = current_app.config.get('POST_SHOW_FALLOUT_SERVICE')
    if service is None:
        service = PostShowFalloutService(get_database())
        current_app.config['POST_SHOW_FALLOUT_SERVICE'] = service
    return service


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec='seconds') + 'Z'


def _coerce_int(value, fallback: int) -> int:
    if value in (None, ""):
        return fallback
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _request_year_week(data: dict, state: dict) -> tuple[int, int]:
    year = _coerce_int(data.get('year'), _coerce_int((state or {}).get('current_year'), 1))
    week = _coerce_int(data.get('week'), _coerce_int((state or {}).get('current_week'), 1))
    return year, week


def _ensure_tables(db):
    c = db.conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS creative_assistant_profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            personality TEXT NOT NULL DEFAULT 'veteran',
            risk_tolerance REAL NOT NULL DEFAULT 0.5,
            storytelling_tempo REAL NOT NULL DEFAULT 0.5,
            updated_at TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS booker_suggestions (
            suggestion_id TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            priority TEXT NOT NULL,
            headline TEXT NOT NULL,
            rationale TEXT NOT NULL,
            options_json TEXT NOT NULL,
            projections_json TEXT NOT NULL,
            context_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            response_reason TEXT,
            counter_pitch TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS creative_notebook_entries (
            entry_id TEXT PRIMARY KEY,
            suggestion_id TEXT,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            tag TEXT,
            pinned INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (suggestion_id) REFERENCES booker_suggestions(suggestion_id)
        )
    ''')
    db.conn.commit()


def _row_to_suggestion(row):
    d = dict(row)
    d['options'] = json.loads(d.pop('options_json'))
    d['projections'] = json.loads(d.pop('projections_json'))
    d['context'] = json.loads(d.pop('context_json'))
    return d


@booker_bp.route('/api/booker/profile', methods=['GET', 'PUT'])
def booker_profile():
    db = get_database()
    _ensure_tables(db)
    c = db.conn.cursor()
    if request.method == 'PUT':
        payload = request.get_json(silent=True) or {}
        personality = str(payload.get('personality', 'veteran')).lower()
        if personality not in PERSONALITIES:
            return jsonify({'error': 'Invalid personality'}), 400
        risk = max(0.0, min(1.0, float(payload.get('risk_tolerance', 0.5))))
        tempo = max(0.0, min(1.0, float(payload.get('storytelling_tempo', 0.5))))
        c.execute('''
            INSERT INTO creative_assistant_profile (id, personality, risk_tolerance, storytelling_tempo, updated_at)
            VALUES (1, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET personality=excluded.personality,
                risk_tolerance=excluded.risk_tolerance, storytelling_tempo=excluded.storytelling_tempo,
                updated_at=excluded.updated_at
        ''', (personality, risk, tempo, _now_iso()))
        db.conn.commit()

    row = c.execute('SELECT * FROM creative_assistant_profile WHERE id = 1').fetchone()
    if not row:
        c.execute('INSERT INTO creative_assistant_profile (id, personality, risk_tolerance, storytelling_tempo, updated_at) VALUES (1, ?, ?, ?, ?)',
                  ('veteran', 0.5, 0.5, _now_iso()))
        db.conn.commit()
        row = c.execute('SELECT * FROM creative_assistant_profile WHERE id = 1').fetchone()
    return jsonify(dict(row))


@booker_bp.route('/api/booker/suggestions', methods=['GET', 'POST'])
def suggestions():
    db = get_database()
    _ensure_tables(db)
    c = db.conn.cursor()

    if request.method == 'POST':
        p = request.get_json(silent=True) or {}
        priority = str(p.get('priority', 'opportunity')).lower()
        status = str(p.get('status', 'open')).lower()
        if priority not in PRIORITIES or status not in STATUSES:
            return jsonify({'error': 'Invalid priority or status'}), 400

        sid = f"sg_{uuid.uuid4().hex[:12]}"
        now = _now_iso()
        c.execute('''
            INSERT INTO booker_suggestions (
                suggestion_id, category, priority, headline, rationale, options_json,
                projections_json, context_json, status, response_reason, counter_pitch,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            sid,
            p.get('category', 'creative-spark'),
            priority,
            p.get('headline', 'New suggestion'),
            p.get('rationale', ''),
            json.dumps(p.get('options', [])),
            json.dumps(p.get('projections', {})),
            json.dumps(p.get('context', {})),
            status,
            p.get('response_reason'),
            p.get('counter_pitch'),
            now,
            now,
        ))
        db.conn.commit()
        row = c.execute('SELECT * FROM booker_suggestions WHERE suggestion_id = ?', (sid,)).fetchone()
        return jsonify(_row_to_suggestion(row)), 201

    status = request.args.get('status')
    query = 'SELECT * FROM booker_suggestions'
    params = []
    if status:
        query += ' WHERE status = ?'
        params.append(status)
    query += ' ORDER BY created_at DESC'
    rows = c.execute(query, params).fetchall()
    return jsonify({'total': len(rows), 'suggestions': [_row_to_suggestion(r) for r in rows]})


@booker_bp.route('/api/booker/suggestions/<suggestion_id>/respond', methods=['POST'])
def respond_suggestion(suggestion_id):
    db = get_database()
    _ensure_tables(db)
    c = db.conn.cursor()
    p = request.get_json(silent=True) or {}
    action = str(p.get('action', '')).lower()
    mapping = {'accept': 'accepted', 'reject': 'rejected', 'modify': 'modified', 'pin': 'pinned', 'dismiss': 'dismissed'}
    if action not in mapping:
        return jsonify({'error': 'Invalid action'}), 400
    new_status = mapping[action]
    c.execute('''
        UPDATE booker_suggestions
        SET status = ?, response_reason = ?, counter_pitch = ?, updated_at = ?
        WHERE suggestion_id = ?
    ''', (new_status, p.get('reason'), p.get('counter_pitch'), _now_iso(), suggestion_id))
    if c.rowcount == 0:
        return jsonify({'error': 'Suggestion not found'}), 404

    title = p.get('notebook_title') or f"{action.title()}: {suggestion_id}"
    body = p.get('notebook_body') or p.get('note') or 'Player response captured.'
    c.execute('''
        INSERT INTO creative_notebook_entries (entry_id, suggestion_id, title, body, tag, pinned, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (f"nb_{uuid.uuid4().hex[:12]}", suggestion_id, title, body, p.get('tag'), 1 if new_status == 'pinned' else 0, _now_iso()))
    db.conn.commit()
    return jsonify({'success': True, 'status': new_status})


@booker_bp.route('/api/booker/notebook', methods=['GET'])
def notebook():
    db = get_database()
    _ensure_tables(db)
    c = db.conn.cursor()
    rows = c.execute('SELECT * FROM creative_notebook_entries ORDER BY created_at DESC').fetchall()
    return jsonify({'total': len(rows), 'entries': [dict(r) for r in rows]})


@booker_bp.route('/api/booker/showrunner/dashboard', methods=['GET'])
def showrunner_dashboard():
    try:
        return jsonify(get_showrunner().dashboard())
    except Exception as exc:
        current_app.logger.exception("Showrunner dashboard failed")
        return jsonify({'error': str(exc)}), 500


@booker_bp.route('/api/booker/showrunner/weekly', methods=['POST'])
def run_showrunner_weekly():
    try:
        data = request.get_json(silent=True) or {}
        state = get_database().get_game_state() if hasattr(get_database(), 'get_game_state') else {}
        year, week = _request_year_week(data, state)
        result = get_showrunner().run_weekly(
            year,
            week,
            universe=get_universe(),
            seed=data.get('seed'),
            force=bool(data.get('force', False)),
            autonomy_level=str(data.get('autonomy_level', 'balanced')).lower(),
        )
        return jsonify(result)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 422
    except Exception as exc:
        current_app.logger.exception("Showrunner weekly run failed")
        return jsonify({'error': str(exc)}), 500


@booker_bp.route('/api/booker/showrunner/latest-booking-draft', methods=['GET'])
def latest_showrunner_booking_draft():
    try:
        return jsonify(get_showrunner().latest_booking_draft())
    except Exception as exc:
        current_app.logger.exception("Showrunner latest booking draft failed")
        return jsonify({'error': str(exc)}), 500


@booker_bp.route('/api/booker/showrunner/dark-house-week', methods=['POST'])
def run_dark_house_week():
    try:
        data = request.get_json(silent=True) or {}
        state = get_database().get_game_state() if hasattr(get_database(), 'get_game_state') else {}
        year, week = _request_year_week(data, state)
        return jsonify(get_showrunner().run_dark_house_autopilot(
            year,
            week,
            universe=get_universe(),
            seed=data.get('seed'),
            force=bool(data.get('force', False)),
            autonomy_level=str(data.get('autonomy_level', 'balanced')).lower(),
        ))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 422
    except Exception as exc:
        current_app.logger.exception("Dark/house autopilot failed")
        return jsonify({'error': str(exc)}), 500


@booker_bp.route('/api/booker/showrunner/promo-beats', methods=['POST'])
def generate_promo_beats():
    try:
        data = request.get_json(silent=True) or {}
        state = get_database().get_game_state() if hasattr(get_database(), 'get_game_state') else {}
        year, week = _request_year_week(data, state)
        return jsonify(get_showrunner().generate_promo_beats(
            year,
            week,
            show_draft=data.get('show_draft'),
            seed=data.get('seed'),
            force=bool(data.get('force', False)),
        ))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 422
    except Exception as exc:
        current_app.logger.exception("Promo beat generation failed")
        return jsonify({'error': str(exc)}), 500


@booker_bp.route('/api/booker/showrunner/live-interruption', methods=['POST'])
def preview_live_interruption():
    try:
        data = request.get_json(silent=True) or {}
        return jsonify(get_showrunner().maybe_live_interruption(
            data.get('show_draft') or {},
            universe=get_universe(),
            seed=data.get('seed'),
            force=bool(data.get('force', False)),
            autonomy_level=str(data.get('autonomy_level', 'balanced')).lower(),
        ))
    except Exception as exc:
        current_app.logger.exception("Live interruption preview failed")
        return jsonify({'error': str(exc)}), 500


@booker_bp.route('/api/booker/approval-queue/<approval_id>/decision', methods=['POST'])
def decide_booker_approval(approval_id):
    try:
        return jsonify(get_showrunner().decide_approval(approval_id, request.get_json(silent=True) or {}))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 422
    except Exception as exc:
        current_app.logger.exception("Booker approval decision failed")
        return jsonify({'error': str(exc)}), 500


@booker_bp.route('/api/booker/approval-queue/auto-resolve', methods=['POST'])
def auto_resolve_booker_queue():
    try:
        data = request.get_json(silent=True) or {}
        state = get_database().get_game_state() if hasattr(get_database(), 'get_game_state') else {}
        year, week = _request_year_week(data, state)
        return jsonify(get_showrunner().auto_resolve_due(year, week))
    except Exception as exc:
        current_app.logger.exception("Booker queue auto-resolve failed")
        return jsonify({'error': str(exc)}), 500


@booker_bp.route('/api/booker/post-show/fallout/latest', methods=['GET'])
def latest_post_show_fallout():
    try:
        show_id = request.args.get('show_id')
        year = request.args.get('year')
        week = request.args.get('week')
        limit = _coerce_int(request.args.get('limit'), 8)
        return jsonify(get_post_show_fallout().get_latest(
            show_id=show_id,
            year=_coerce_int(year, None) if year not in (None, "") else None,
            week=_coerce_int(week, None) if week not in (None, "") else None,
            limit=limit,
        ))
    except Exception as exc:
        current_app.logger.exception("Post-show fallout latest failed")
        return jsonify({'error': str(exc)}), 500


@booker_bp.route('/api/booker/post-show/fallout/items/<item_id>/decision', methods=['POST'])
def decide_post_show_fallout_item(item_id):
    try:
        return jsonify(get_post_show_fallout().decide_item(item_id, request.get_json(silent=True) or {}))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 422
    except Exception as exc:
        current_app.logger.exception("Post-show fallout decision failed")
        return jsonify({'error': str(exc)}), 500


@booker_bp.route('/api/booker/post-show/fallout/<report_id>/auto-handle', methods=['POST'])
def auto_handle_post_show_fallout(report_id):
    try:
        return jsonify(get_post_show_fallout().auto_handle_report(report_id))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 422
    except Exception as exc:
        current_app.logger.exception("Post-show fallout auto-handle failed")
        return jsonify({'error': str(exc)}), 500
