"""
Roster Routes - Wrestler Management
"""

from flask import Blueprint, jsonify, request, current_app

roster_bp = Blueprint('roster', __name__)


def get_universe():
    return current_app.config['UNIVERSE']


def get_database():
    return current_app.config.get('DATABASE')


def _alignment_label(percentage):
    percentage = int(percentage if percentage is not None else 50)
    if 40 <= percentage <= 60:
        return 'Tweener'
    return 'Face' if percentage > 60 else 'Heel'


def _character_rows_by_wrestler(ids):
    if not ids:
        return {}
    database = get_database()
    if not database:
        return {}

    placeholders = ','.join(['?'] * len(ids))
    cursor = database.conn.cursor()
    rows = cursor.execute(f'''
        SELECT
            w.id,
            w.alignment_percentage,
            w.gimmick_effectiveness,
            w.primary_wrestling_style,
            w.secondary_wrestling_style,
            w.nationality,
            w.birth_city,
            w.birth_country,
            w.kayfabe_hometown,
            w.ethnic_background,
            gt.name AS gimmick_name,
            wg.template_id AS gimmick_template_id,
            rh.attribute_name AS latest_rating_attribute,
            rh.old_value AS latest_rating_old_value,
            rh.new_value AS latest_rating_new_value,
            rh.recorded_at AS latest_rating_recorded_at,
            rh.change_reason AS latest_rating_reason
        FROM wrestlers w
        LEFT JOIN wrestler_gimmicks wg ON wg.wrestler_id = w.id
        LEFT JOIN gimmick_templates gt ON gt.id = wg.template_id
        LEFT JOIN rating_history rh ON rh.id = (
            SELECT id FROM rating_history
            WHERE wrestler_id = w.id
            ORDER BY recorded_at DESC
            LIMIT 1
        )
        WHERE w.id IN ({placeholders})
    ''', ids).fetchall()
    return {row['id']: dict(row) for row in rows}


def _apply_character_fields(wrestler_data, character_row):
    if not character_row:
        wrestler_data['character'] = {
            'alignment_percentage': 50,
            'alignment_label': wrestler_data.get('alignment', 'Tweener'),
            'gimmick_name': None,
            'gimmick_effectiveness': 50,
            'primary_wrestling_style': 'hybrid',
            'rating_trend': None,
        }
        return wrestler_data

    alignment_percentage = character_row.get('alignment_percentage')
    wrestler_data['alignment'] = _alignment_label(alignment_percentage)
    wrestler_data['character'] = {
        'alignment_percentage': alignment_percentage if alignment_percentage is not None else 50,
        'alignment_label': _alignment_label(alignment_percentage),
        'gimmick_name': character_row.get('gimmick_name'),
        'gimmick_template_id': character_row.get('gimmick_template_id'),
        'gimmick_effectiveness': character_row.get('gimmick_effectiveness') or 50,
        'primary_wrestling_style': character_row.get('primary_wrestling_style') or 'hybrid',
        'secondary_wrestling_style': character_row.get('secondary_wrestling_style'),
        'nationality': character_row.get('nationality'),
        'birth_city': character_row.get('birth_city'),
        'birth_country': character_row.get('birth_country'),
        'kayfabe_hometown': character_row.get('kayfabe_hometown'),
        'ethnic_background': character_row.get('ethnic_background'),
        'rating_trend': {
            'attribute': character_row.get('latest_rating_attribute'),
            'old_value': character_row.get('latest_rating_old_value'),
            'new_value': character_row.get('latest_rating_new_value'),
            'recorded_at': character_row.get('latest_rating_recorded_at'),
            'reason': character_row.get('latest_rating_reason'),
        } if character_row.get('latest_rating_attribute') else None,
    }
    return wrestler_data


@roster_bp.route('/api/roster')
def api_get_roster():
    universe = get_universe()
    
    brand = request.args.get('brand')
    role = request.args.get('role')
    gender = request.args.get('gender')
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    
    wrestlers = universe.wrestlers
    
    if active_only:
        wrestlers = [w for w in wrestlers if not w.is_retired]
    
    if brand:
        wrestlers = [w for w in wrestlers if w.primary_brand == brand]
    
    if role:
        wrestlers = [w for w in wrestlers if w.role == role]
    
    if gender:
        wrestlers = [w for w in wrestlers if w.gender == gender]
    
    character_rows = _character_rows_by_wrestler([w.id for w in wrestlers])
    serialized = [
        _apply_character_fields(w.to_dict(), character_rows.get(w.id))
        for w in wrestlers
    ]

    return jsonify({
        'total': len(wrestlers),
        'wrestlers': serialized
    })


@roster_bp.route('/api/roster/<wrestler_id>')
def api_get_wrestler(wrestler_id):
    universe = get_universe()
    wrestler = universe.get_wrestler_by_id(wrestler_id)
    
    if not wrestler:
        return jsonify({'error': 'Wrestler not found'}), 404
    
    character_rows = _character_rows_by_wrestler([wrestler_id])
    wrestler_data = _apply_character_fields(wrestler.to_dict(), character_rows.get(wrestler_id))
    title_reigns = []

    for championship in universe.championships:
        history = getattr(championship, 'history', []) or []
        for reign in history:
            if getattr(reign, 'wrestler_id', None) != wrestler_id:
                continue

            title_reigns.append({
                'title_id': getattr(championship, 'id', None),
                'title_name': getattr(championship, 'name', 'Unknown Championship'),
                'won_at_show_name': getattr(reign, 'won_at_show_name', 'Unknown Event'),
                'won_date_year': getattr(reign, 'won_date_year', None),
                'won_date_week': getattr(reign, 'won_date_week', None),
                'is_current_reign': (
                    getattr(championship, 'current_holder_id', None) == wrestler_id
                    and not getattr(championship, 'is_vacant', False)
                )
            })

    title_reigns.sort(
        key=lambda r: (
            r.get('won_date_year') if r.get('won_date_year') is not None else -1,
            r.get('won_date_week') if r.get('won_date_week') is not None else -1
        ),
        reverse=True
    )
    wrestler_data['title_reigns'] = title_reigns

    return jsonify(wrestler_data)


@roster_bp.route('/api/stats/roster-summary')
def api_roster_summary():
    universe = get_universe()
    
    summary = {
        'total_wrestlers': len(universe.wrestlers),
        'active_wrestlers': len(universe.get_active_wrestlers()),
        'retired_wrestlers': len(universe.retired_wrestlers),
        'by_brand': {},
        'by_role': {},
        'by_gender': {},
        'major_superstars': len([w for w in universe.wrestlers if w.is_major_superstar]),
        'injured_wrestlers': len([w for w in universe.wrestlers if w.is_injured]),
        'contracts_expiring_soon': len([w for w in universe.wrestlers if w.contract_expires_soon])
    }
    
    for brand in ['ROC Alpha', 'ROC Velocity', 'ROC Vanguard']:
        summary['by_brand'][brand] = len([w for w in universe.wrestlers if w.primary_brand == brand and not w.is_retired])
    
    for role in ['Main Event', 'Upper Midcard', 'Midcard', 'Lower Midcard', 'Jobber']:
        summary['by_role'][role] = len([w for w in universe.wrestlers if w.role == role and not w.is_retired])
    
    for gender in ['Male', 'Female']:
        summary['by_gender'][gender] = len([w for w in universe.wrestlers if w.gender == gender and not w.is_retired])
    
    return jsonify(summary)
