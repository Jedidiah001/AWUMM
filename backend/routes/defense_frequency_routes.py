"""
Defense Frequency Routes - Championship Defense Frequency (Step 25)
"""

from flask import Blueprint, jsonify, request, current_app
import traceback

defense_frequency_bp = Blueprint('defense_frequency', __name__)

DAY_OFFSETS = {
    'Monday': 0,
    'Tuesday': 1,
    'Wednesday': 2,
    'Thursday': 3,
    'Friday': 4,
    'Saturday': 5,
    'Sunday': 6,
}


def get_database():
    return current_app.config['DATABASE']


def get_universe():
    return current_app.config['UNIVERSE']


def _resolve_show_day(calendar, show_id, fallback_week=None):
    if not show_id:
        return None

    for show in calendar.generated_shows:
        if show.show_id == show_id:
            return show.day_of_week

    lowered = show_id.lower()
    if 'roc_alpha' in lowered:
        return 'Monday'
    if 'roc_velocity' in lowered:
        return 'Friday'
    if 'roc_vanguard' in lowered:
        return 'Saturday'

    if lowered.startswith('ppv_') and fallback_week is not None:
        ppv_config = calendar._get_ppv_for_week(fallback_week)
        if ppv_config:
            replacement_day = {
                'ROC Alpha': 'Monday',
                'ROC Velocity': 'Friday',
                'ROC Vanguard': 'Saturday',
            }
            return replacement_day.get(ppv_config.get('replaces_show'), 'Sunday')

    return None


def _build_status(championship, universe):
    status = championship.get_defense_status(
        universe.current_year,
        universe.current_week
    )

    current_show = universe.calendar.get_current_show()
    if not current_show or not championship.last_defense_year or not championship.last_defense_week:
        return status

    last_day = _resolve_show_day(
        universe.calendar,
        championship.last_defense_show_id,
        championship.last_defense_week
    )
    current_day = current_show.day_of_week

    if last_day not in DAY_OFFSETS or current_day not in DAY_OFFSETS:
        return status

    weeks_since = (
        (universe.current_year - championship.last_defense_year) * 52
        + (universe.current_week - championship.last_defense_week)
    )
    exact_days = max(0, (weeks_since * 7) + DAY_OFFSETS[current_day] - DAY_OFFSETS[last_day])
    days_until_required = championship.defense_frequency_days - exact_days

    if exact_days >= championship.defense_frequency_days:
        urgency_level = 3
        urgency_label = 'CRITICAL'
        is_overdue = True
    elif exact_days >= championship.defense_frequency_days * 0.85:
        urgency_level = 2
        urgency_label = 'High'
        is_overdue = False
    elif exact_days >= championship.defense_frequency_days * 0.70:
        urgency_level = 1
        urgency_label = 'Medium'
        is_overdue = False
    else:
        urgency_level = 0
        urgency_label = 'Normal'
        is_overdue = False

    status.update({
        'days_since_defense': exact_days,
        'days_until_required': max(0, days_until_required),
        'urgency_level': urgency_level,
        'urgency_label': urgency_label,
        'is_overdue': is_overdue
    })
    return status


@defense_frequency_bp.route('/api/championships/<title_id>/defense-frequency')
def api_get_defense_frequency(title_id):
    universe = get_universe()

    try:
        championship = universe.get_championship_by_id(title_id)

        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404

        status = _build_status(championship, universe)

        champion_info = None
        if not championship.is_vacant:
            champion = universe.get_wrestler_by_id(championship.effective_champion_id)
            if champion:
                champion_info = {
                    'id': champion.id,
                    'name': champion.name,
                    'is_interim': championship.has_interim_champion
                }

        return jsonify({
            'success': True,
            'championship': {
                'id': championship.id,
                'name': championship.name,
                'is_vacant': championship.is_vacant
            },
            'champion': champion_info,
            'requirements': {
                'max_days_between_defenses': championship.defense_frequency_days,
                'min_defenses_per_year': championship.min_annual_defenses
            },
            'status': status,
            'last_defense': {
                'year': championship.last_defense_year,
                'week': championship.last_defense_week,
                'show_id': championship.last_defense_show_id
            } if championship.last_defense_year else None
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@defense_frequency_bp.route('/api/championships/<title_id>/defense-frequency/set', methods=['POST'])
def api_set_defense_frequency(title_id):
    database = get_database()
    universe = get_universe()

    try:
        from persistence.championship_custom_db import log_championship_action

        championship = universe.get_championship_by_id(title_id)

        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404

        data = request.get_json()

        max_days = data.get('max_days_between_defenses')
        min_annual = data.get('min_defenses_per_year')

        if max_days is not None:
            if not isinstance(max_days, int) or max_days < 14 or max_days > 90:
                return jsonify({
                    'success': False,
                    'error': 'max_days_between_defenses must be integer between 14-90'
                }), 400

        if min_annual is not None:
            if not isinstance(min_annual, int) or min_annual < 4 or min_annual > 52:
                return jsonify({
                    'success': False,
                    'error': 'min_defenses_per_year must be integer between 4-52'
                }), 400

        try:
            championship.set_defense_requirements(max_days, min_annual)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400

        universe.save_championship(championship)
        database.conn.commit()

        log_championship_action(
            database,
            title_id,
            'defense_requirements_updated',
            universe.current_year,
            universe.current_week,
            f"Defense requirements updated: {max_days or championship.defense_frequency_days} days, {min_annual or championship.min_annual_defenses}/year"
        )

        return jsonify({
            'success': True,
            'message': 'Defense frequency requirements updated',
            'requirements': {
                'max_days_between_defenses': championship.defense_frequency_days,
                'min_defenses_per_year': championship.min_annual_defenses
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@defense_frequency_bp.route('/api/championships/overdue-defenses')
def api_get_overdue_defenses():
    universe = get_universe()

    try:
        championships = universe.championships
        overdue = []

        for championship in championships:
            if championship.is_vacant:
                continue

            status = _build_status(championship, universe)

            if status['is_overdue'] or status['urgency_level'] >= 2:
                champion = universe.get_wrestler_by_id(championship.effective_champion_id)

                overdue.append({
                    'championship': {
                        'id': championship.id,
                        'name': championship.name,
                        'brand': championship.assigned_brand,
                        'tier': championship.title_type
                    },
                    'champion': {
                        'id': champion.id if champion else None,
                        'name': champion.name if champion else 'Unknown',
                        'is_interim': championship.has_interim_champion
                    },
                    'status': status
                })

        overdue.sort(key=lambda x: x['status']['urgency_level'], reverse=True)

        return jsonify({
            'success': True,
            'current_year': universe.current_year,
            'current_week': universe.current_week,
            'total': len(overdue),
            'overdue_defenses': overdue
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@defense_frequency_bp.route('/api/championships/defense-schedule')
def api_get_full_defense_schedule():
    universe = get_universe()

    try:
        championships = universe.championships
        schedule = []

        for championship in championships:
            if championship.is_vacant:
                continue

            status = _build_status(championship, universe)
            champion = universe.get_wrestler_by_id(championship.effective_champion_id)

            schedule.append({
                'title_id': championship.id,
                'title_name': championship.name,
                'title_tier': championship.title_type,
                'brand': championship.assigned_brand,
                'prestige': championship.prestige,
                'champion_id': champion.id if champion else None,
                'champion_name': champion.name if champion else 'Unknown',
                'is_interim': championship.has_interim_champion,
                'days_since_defense': status['days_since_defense'],
                'weeks_since_defense': status['days_since_defense'] // 7,
                'urgency_level': status['urgency_level'],
                'urgency_label': status['urgency_label'],
                'is_overdue': status['is_overdue'],
                'days_until_required': status['days_until_required'],
                'total_defenses': championship.total_defenses,
                'championship': {
                    'id': championship.id,
                    'name': championship.name,
                    'brand': championship.assigned_brand,
                    'tier': championship.title_type,
                    'prestige': championship.prestige
                },
                'champion': {
                    'id': champion.id if champion else None,
                    'name': champion.name if champion else 'Unknown',
                    'is_interim': championship.has_interim_champion
                },
                'status': status
            })

        schedule.sort(key=lambda x: x['urgency_level'], reverse=True)

        return jsonify({
            'success': True,
            'current_year': universe.current_year,
            'current_week': universe.current_week,
            'total': len(schedule),
            'schedule': schedule
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@defense_frequency_bp.route('/api/championships/<title_id>/is-overdue')
def api_check_if_defense_overdue(title_id):
    universe = get_universe()

    try:
        championship = universe.get_championship_by_id(title_id)

        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404

        if championship.is_vacant:
            return jsonify({
                'success': True,
                'is_overdue': False,
                'reason': 'Championship is vacant'
            })

        status = _build_status(championship, universe)

        return jsonify({
            'success': True,
            'championship_id': title_id,
            'championship_name': championship.name,
            'is_overdue': status['is_overdue'],
            'urgency_level': status['urgency_level'],
            'urgency_label': status['urgency_label'],
            'days_since_defense': status['days_since_defense'],
            'days_until_required': status['days_until_required']
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@defense_frequency_bp.route('/api/championships/defense-alerts')
def api_get_defense_alerts():
    universe = get_universe()

    try:
        championships = universe.championships
        alerts = []

        for championship in championships:
            if championship.is_vacant:
                continue

            status = _build_status(championship, universe)

            if status['urgency_level'] >= 1:
                champion = universe.get_wrestler_by_id(championship.effective_champion_id)

                alert = {
                    'championship_id': championship.id,
                    'championship_name': championship.name,
                    'champion_name': champion.name if champion else 'Unknown',
                    'urgency_level': status['urgency_level'],
                    'urgency_label': status['urgency_label'],
                    'days_since_defense': status['days_since_defense'],
                    'message': f"{championship.name} defense needed soon ({status['days_until_required']} days remaining)"
                }

                if status['is_overdue']:
                    alert['message'] = f"Title defense overdue by {status['days_since_defense'] - championship.defense_frequency_days} days"

                alerts.append(alert)

        alerts.sort(key=lambda x: x['urgency_level'], reverse=True)

        return jsonify({
            'success': True,
            'total': len(alerts),
            'alerts': alerts
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
