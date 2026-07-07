"""
Character system API routes for features 26-38.
"""

import json
import uuid
from flask import Blueprint, current_app, jsonify, request

from services.character_system_service import (
    age_progression_delta,
    alignment_label,
    apply_attribute_delta,
    calculate_finisher_protection,
    calculate_gimmick_effectiveness,
    calculate_turn_impact,
    chemistry_modifier,
    clamp,
    now_iso,
)


character_system_bp = Blueprint('character_system', __name__)


def _database():
    return current_app.config['DATABASE']


def _json_error(message, status=400, details=None):
    return jsonify({
        "status": "error",
        "message": message,
        "details": details or [],
    }), status


def _row_to_dict(row):
    return dict(row) if row else None


@character_system_bp.route('/api/character-system/overview')
def overview():
    db = _database()
    cur = db.conn.cursor()
    wrestlers = [
        dict(row) for row in cur.execute('''
            SELECT id, name, gender, primary_brand, popularity, alignment,
                   alignment_percentage, gimmick_effectiveness,
                   primary_wrestling_style, secondary_wrestling_style,
                   nationality, kayfabe_hometown
            FROM wrestlers
            WHERE is_retired = 0
            ORDER BY primary_brand, name
        ''').fetchall()
    ]
    for wrestler in wrestlers:
        wrestler['alignment_label'] = alignment_label(wrestler.get('alignment_percentage') or 50)

    templates = [dict(row) for row in cur.execute(
        'SELECT * FROM gimmick_templates ORDER BY is_custom, name'
    ).fetchall()]
    turns = [dict(row) for row in cur.execute(
        'SELECT * FROM alignment_turns ORDER BY turn_date DESC LIMIT 25'
    ).fetchall()]
    return jsonify({
        "success": True,
        "wrestlers": wrestlers,
        "gimmick_templates": templates,
        "recent_turns": turns,
    })


@character_system_bp.route('/api/character-system/wrestlers/<wrestler_id>/alignment', methods=['GET', 'PUT'])
def wrestler_alignment(wrestler_id):
    db = _database()
    cur = db.conn.cursor()
    wrestler = _row_to_dict(cur.execute(
        'SELECT id, name, alignment_percentage FROM wrestlers WHERE id = ?',
        (wrestler_id,),
    ).fetchone())
    if not wrestler:
        return _json_error('Wrestler not found', 404)

    if request.method == 'GET':
        value = wrestler.get('alignment_percentage') or 50
        return jsonify({"success": True, "percentage": value, "label": alignment_label(value)})

    data = request.get_json(silent=True) or {}
    try:
        percentage = clamp(int(data.get('alignment_percentage')))
    except (TypeError, ValueError):
        return _json_error('alignment_percentage must be a number between 0 and 100')

    cur.execute(
        'UPDATE wrestlers SET alignment_percentage = ?, alignment = ?, updated_at = ? WHERE id = ?',
        (percentage, alignment_label(percentage), now_iso(), wrestler_id),
    )
    db.conn.commit()
    return jsonify({"success": True, "percentage": percentage, "label": alignment_label(percentage)})


@character_system_bp.route('/api/character-system/wrestlers/<wrestler_id>/turn', methods=['POST'])
def execute_turn(wrestler_id):
    db = _database()
    cur = db.conn.cursor()
    wrestler = _row_to_dict(cur.execute(
        'SELECT * FROM wrestlers WHERE id = ?',
        (wrestler_id,),
    ).fetchone())
    if not wrestler:
        return _json_error('Wrestler not found', 404)

    data = request.get_json(silent=True) or {}
    try:
        new_alignment = clamp(int(data.get('new_alignment')))
        timing = clamp(int(data.get('timing_score', 50)))
        build = clamp(int(data.get('build_score', 5)), 1, 10)
        surprise = clamp(int(data.get('surprise_factor', 50)))
    except (TypeError, ValueError):
        return _json_error('Turn inputs must be numeric and within their valid ranges')

    impact = calculate_turn_impact(timing, build, surprise)
    old_alignment = wrestler.get('alignment_percentage') or 50
    new_popularity = clamp((wrestler.get('popularity') or 50) + impact['overness_change'])
    now = now_iso()
    turn_id = f"turn_{uuid.uuid4().hex[:12]}"

    try:
        cur.execute('BEGIN')
        cur.execute('''
            INSERT INTO alignment_turns (
                id, wrestler_id, old_alignment, new_alignment, turn_date,
                timing_score, build_score, surprise_factor, impact_score,
                overness_change, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            turn_id, wrestler_id, old_alignment, new_alignment, now,
            timing, build, surprise, impact['impact_score'],
            impact['overness_change'], data.get('notes'), now,
        ))
        cur.execute('''
            UPDATE wrestlers
            SET alignment_percentage = ?, alignment = ?, popularity = ?, updated_at = ?
            WHERE id = ?
        ''', (new_alignment, alignment_label(new_alignment), new_popularity, now, wrestler_id))
        db.conn.commit()
    except Exception:
        db.conn.rollback()
        raise

    return jsonify({
        "success": True,
        "turn_id": turn_id,
        "impact": impact,
        "new_popularity": new_popularity,
        "alignment_label": alignment_label(new_alignment),
    })


@character_system_bp.route('/api/character-system/gimmick-templates', methods=['GET', 'POST'])
def gimmick_templates():
    db = _database()
    cur = db.conn.cursor()

    if request.method == 'GET':
        rows = cur.execute('SELECT * FROM gimmick_templates ORDER BY is_custom, name').fetchall()
        return jsonify({"success": True, "templates": [dict(row) for row in rows]})

    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return _json_error('Template name is required')
    template_id = f"custom_{uuid.uuid4().hex[:10]}"
    now = now_iso()
    cur.execute('''
        INSERT INTO gimmick_templates (
            id, name, description, default_alignment, recommended_wrestling_style,
            base_popularity_modifier, attributes_json, is_custom, version,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?)
    ''', (
        template_id,
        name,
        data.get('description', ''),
        data.get('default_alignment', 'Tweener'),
        data.get('recommended_wrestling_style', 'hybrid'),
        int(data.get('base_popularity_modifier', 0)),
        json.dumps(data.get('attributes', {})),
        now,
        now,
    ))
    db.conn.commit()
    return jsonify({"success": True, "template_id": template_id})


@character_system_bp.route('/api/character-system/wrestlers/<wrestler_id>/gimmick', methods=['POST'])
def assign_gimmick(wrestler_id):
    db = _database()
    cur = db.conn.cursor()
    wrestler = _row_to_dict(cur.execute('SELECT * FROM wrestlers WHERE id = ?', (wrestler_id,)).fetchone())
    if not wrestler:
        return _json_error('Wrestler not found', 404)

    data = request.get_json(silent=True) or {}
    template_id = data.get('template_id')
    template = _row_to_dict(cur.execute('SELECT * FROM gimmick_templates WHERE id = ?', (template_id,)).fetchone())
    if not template:
        return _json_error('Gimmick template not found', 404)

    effectiveness = calculate_gimmick_effectiveness(wrestler, template_id)
    now = now_iso()
    cur.execute('''
        INSERT OR REPLACE INTO wrestler_gimmicks (
            wrestler_id, template_id, custom_name, effectiveness, assigned_at, updated_at
        ) VALUES (?, ?, ?, ?, COALESCE((SELECT assigned_at FROM wrestler_gimmicks WHERE wrestler_id = ?), ?), ?)
    ''', (wrestler_id, template_id, data.get('custom_name'), effectiveness, wrestler_id, now, now))
    cur.execute(
        'UPDATE wrestlers SET gimmick_effectiveness = ?, updated_at = ? WHERE id = ?',
        (effectiveness, now, wrestler_id),
    )
    db.conn.commit()
    return jsonify({"success": True, "effectiveness": effectiveness})


@character_system_bp.route('/api/character-system/wrestlers/<wrestler_id>/profile', methods=['PUT'])
def update_character_profile(wrestler_id):
    db = _database()
    cur = db.conn.cursor()
    data = request.get_json(silent=True) or {}
    allowed = [
        'primary_wrestling_style', 'secondary_wrestling_style', 'nationality',
        'birth_city', 'birth_country', 'kayfabe_hometown', 'ethnic_background',
    ]
    assignments = []
    values = []
    for field in allowed:
        if field in data:
            assignments.append(f"{field} = ?")
            values.append(data[field])
    if not assignments:
        return _json_error('No profile fields supplied')
    values.extend([now_iso(), wrestler_id])
    cur.execute(
        f"UPDATE wrestlers SET {', '.join(assignments)}, updated_at = ? WHERE id = ?",
        values,
    )
    db.conn.commit()
    return jsonify({"success": cur.rowcount > 0})


@character_system_bp.route('/api/character-system/wrestlers/<wrestler_id>/entrance', methods=['POST'])
def save_entrance(wrestler_id):
    data = request.get_json(silent=True) or {}
    settings = data.get('settings') or {}
    weekly_cost = _entrance_cost(settings)
    boost = clamp(5 + weekly_cost // 2000, 5, 25)
    now = now_iso()
    config_id = data.get('id') or f"entrance_{uuid.uuid4().hex[:12]}"
    cur = _database().conn.cursor()
    cur.execute('''
        INSERT OR REPLACE INTO entrance_configurations (
            id, wrestler_id, name, settings_json, weekly_cost,
            presentation_boost, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM entrance_configurations WHERE id = ?), ?), ?)
    ''', (config_id, wrestler_id, data.get('name', 'Default Entrance'), json.dumps(settings), weekly_cost, boost, config_id, now, now))
    _database().conn.commit()
    return jsonify({"success": True, "id": config_id, "weekly_cost": weekly_cost, "presentation_boost": boost})


@character_system_bp.route('/api/character-system/wrestlers/<wrestler_id>/catchphrases', methods=['POST'])
def create_catchphrase(wrestler_id):
    phrase = ((request.get_json(silent=True) or {}).get('phrase_text') or '').strip()
    if not phrase or len(phrase) > 140:
        return _json_error('Catchphrase must be between 1 and 140 characters')
    now = now_iso()
    phrase_id = f"phrase_{uuid.uuid4().hex[:12]}"
    cur = _database().conn.cursor()
    cur.execute('''
        INSERT INTO catchphrases (id, wrestler_id, phrase_text, popularity_score, usage_count, created_date, updated_at)
        VALUES (?, ?, ?, 50, 0, ?, ?)
    ''', (phrase_id, wrestler_id, phrase, now, now))
    _database().conn.commit()
    return jsonify({"success": True, "id": phrase_id})


@character_system_bp.route('/api/character-system/wrestlers/<wrestler_id>/moves', methods=['POST'])
def create_move(wrestler_id):
    data = request.get_json(silent=True) or {}
    move_name = (data.get('move_name') or '').strip()
    move_family = data.get('move_family', 'signature')
    if not move_name:
        return _json_error('move_name is required')
    now = now_iso()
    cur = _database().conn.cursor()
    move_id = f"move_{uuid.uuid4().hex[:12]}"

    if move_family == 'finisher':
        pins = int(data.get('successful_pin_count', 0))
        kickouts = int(data.get('kickout_count', 0))
        cur.execute('''
            INSERT INTO finisher_moves (
                id, wrestler_id, move_name, move_type, protection_rating,
                kickout_count, successful_pin_count, debut_date, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (move_id, wrestler_id, move_name, data.get('move_type', 'primary'), calculate_finisher_protection(pins, kickouts), kickouts, pins, now, now))
    else:
        cur.execute('''
            INSERT INTO signature_moves (
                id, wrestler_id, move_name, sequence_position,
                crowd_anticipation_level, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (move_id, wrestler_id, move_name, int(data.get('sequence_position', 1)), clamp(int(data.get('crowd_anticipation_level', 50))), now, now))

    _database().conn.commit()
    return jsonify({"success": True, "id": move_id})


@character_system_bp.route('/api/character-system/wrestlers/<wrestler_id>/companions', methods=['POST'])
def assign_companion(wrestler_id):
    data = request.get_json(silent=True) or {}
    companion_id = data.get('companion_id')
    role = data.get('role', 'manager')
    if not companion_id or companion_id == wrestler_id:
        return _json_error('A different companion wrestler is required')
    tendency = clamp(int(data.get('interference_tendency', 20)))
    now = now_iso()
    companion_row_id = f"companion_{uuid.uuid4().hex[:12]}"
    cur = _database().conn.cursor()
    cur.execute('''
        INSERT INTO entrance_companions (
            id, wrestler_id, companion_id, role, start_date, end_date,
            interference_tendency, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (companion_row_id, wrestler_id, companion_id, role, now, data.get('end_date'), tendency, now, now))
    _database().conn.commit()
    return jsonify({"success": True, "id": companion_row_id})


@character_system_bp.route('/api/character-system/wrestlers/<wrestler_id>/evolution', methods=['POST'])
def record_evolution(wrestler_id):
    db = _database()
    cur = db.conn.cursor()
    wrestler = _row_to_dict(cur.execute(
        'SELECT id FROM wrestlers WHERE id = ?',
        (str(wrestler_id),),
    ).fetchone())
    if not wrestler:
        return _json_error('Wrestler not found', 404)

    data = request.get_json(silent=True) or {}
    new_state = (data.get('new_state') or '').strip()
    if not new_state:
        return _json_error('new_state is required')
    try:
        readiness_score = clamp(int(data.get('readiness_score', 50)))
    except (TypeError, ValueError):
        return _json_error('readiness_score must be a number between 0 and 100')

    now = now_iso()
    event_id = f"evolution_{uuid.uuid4().hex[:12]}"
    cur.execute('''
        INSERT INTO character_evolution_events (
            id, wrestler_id, event_type, previous_state, new_state,
            trigger_reason, readiness_score, event_date, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        str(event_id),
        str(wrestler_id),
        str(data.get('event_type') or 'manual_evolution'),
        str(data.get('previous_state') or ''),
        str(new_state),
        str(data.get('trigger_reason') or 'manual booking decision'),
        readiness_score,
        str(now),
        str(now),
    ))
    db.conn.commit()
    return jsonify({"success": True, "id": event_id})


@character_system_bp.route('/api/character-system/chemistry')
def style_chemistry():
    return jsonify({
        "success": True,
        "modifier": chemistry_modifier(request.args.get('style_a'), request.args.get('style_b')),
    })


@character_system_bp.route('/api/character-system/age-progression/run', methods=['POST'])
def run_age_progression():
    db = _database()
    cur = db.conn.cursor()
    rows = cur.execute('SELECT * FROM wrestlers WHERE is_retired = 0').fetchall()
    now = now_iso()
    updates = []
    for row in rows:
        wrestler = dict(row)
        deltas = age_progression_delta(wrestler['age'], wrestler.get('primary_wrestling_style'))
        new_values = apply_attribute_delta(wrestler, deltas)
        for attr, new_value in new_values.items():
            old_value = int(wrestler.get(attr, 50))
            if old_value == new_value:
                continue
            cur.execute(
                f'UPDATE wrestlers SET {attr} = ?, updated_at = ? WHERE id = ?',
                (new_value, now, wrestler['id']),
            )
            cur.execute('''
                INSERT INTO rating_history (
                    id, wrestler_id, attribute_name, old_value, new_value,
                    change_reason, recorded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (f"rating_{uuid.uuid4().hex[:12]}", wrestler['id'], attr, old_value, new_value, 'age_progression', now))
            updates.append({"wrestler_id": wrestler['id'], "attribute": attr, "old": old_value, "new": new_value})
    db.conn.commit()
    return jsonify({"success": True, "updates": updates})


def _entrance_cost(settings):
    costs = {
        'pyro': {'none': 0, 'basic': 2500, 'full': 10000, 'specialty': 18000},
        'lighting': {'standard': 0, 'spotlight': 750, 'color': 1500, 'choreographed': 5000},
        'video': {'none': 0, 'simple': 1000, 'full': 6000},
        'props': {'none': 0, 'signature': 800, 'elaborate': 4500},
        'effects': {'none': 0, 'fog': 500, 'laser': 4000, 'confetti': 2500},
    }
    return sum(costs.get(key, {}).get(value, 0) for key, value in settings.items())
