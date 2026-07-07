"""
Wellness policy routes.
"""

from flask import Blueprint, jsonify, request, current_app

wellness_bp = Blueprint('wellness', __name__)


def get_database():
    return current_app.config['DATABASE']


def get_universe():
    return current_app.config['UNIVERSE']


def _burnout_level(wrestler):
    if wrestler.fatigue >= 90 or wrestler.morale <= 15:
        return 'critical'
    if wrestler.fatigue >= 75 or wrestler.morale <= 30:
        return 'high'
    if wrestler.fatigue >= 60 or wrestler.morale <= 45:
        return 'medium'
    return 'low'


def _age_decline_score(wrestler):
    age_pressure = max(0, wrestler.age - 35) * 3
    stamina_pressure = max(0, 75 - wrestler.stamina)
    speed_pressure = max(0, 75 - wrestler.speed)
    injury_pressure = 15 if wrestler.is_injured else 0
    return min(100, age_pressure + stamina_pressure + speed_pressure + injury_pressure)


@wellness_bp.route('/api/wellness/policy')
def api_get_wellness_policy():
    return jsonify({
        'success': True,
        'policy': get_database().get_wellness_policy()
    })


@wellness_bp.route('/api/wellness/policy', methods=['POST'])
def api_update_wellness_policy():
    database = get_database()
    policy_data = request.get_json() or {}
    database.save_wellness_policy(policy_data)
    database.conn.commit()
    return jsonify({
        'success': True,
        'policy': database.get_wellness_policy()
    })


@wellness_bp.route('/api/wellness/violations')
def api_get_wellness_violations():
    wrestler_id = request.args.get('wrestler_id')
    return jsonify({
        'success': True,
        'violations': get_database().get_wellness_violations(wrestler_id=wrestler_id)
    })


@wellness_bp.route('/api/wellness/violations', methods=['POST'])
def api_record_wellness_violation():
    database = get_database()
    universe = get_universe()
    data = request.get_json() or {}

    wrestler = universe.get_wrestler_by_id(data.get('wrestler_id'))
    if not wrestler:
        return jsonify({'success': False, 'error': 'Wrestler not found'}), 404

    policy = database.get_wellness_policy()
    severity = data.get('severity', 'minor').lower()
    suspension_weeks = (
        policy.get('suspension_weeks_major', 4)
        if severity in {'major', 'severe'}
        else policy.get('suspension_weeks_minor', 1)
    )

    violation_id = database.record_wellness_violation({
        'wrestler_id': wrestler.id,
        'wrestler_name': wrestler.name,
        'violation_type': data.get('violation_type', 'wellness_violation'),
        'severity': severity,
        'year': universe.current_year,
        'week': universe.current_week,
        'suspension_weeks': int(data.get('suspension_weeks', suspension_weeks)),
        'notes': data.get('notes', ''),
    })

    wrestler.adjust_morale(-8 if severity == 'minor' else -15)
    universe.save_wrestler(wrestler)
    database.conn.commit()

    return jsonify({
        'success': True,
        'violation_id': violation_id,
        'recommended_suspension_weeks': int(data.get('suspension_weeks', suspension_weeks)),
        'wrestler': wrestler.to_dict()
    })


@wellness_bp.route('/api/wellness/overview')
def api_wellness_overview():
    universe = get_universe()
    roster = universe.get_active_wrestlers()
    burnout_risk = [w for w in roster if w.fatigue >= 70 or w.morale <= 35]
    injury_risk = [w for w in roster if w.is_injured or w.fatigue >= 80]
    veteran_watch = [w for w in roster if w.age >= 40]

    return jsonify({
        'success': True,
        'overview': {
            'burnout_risk_count': len(burnout_risk),
            'injury_risk_count': len(injury_risk),
            'veteran_watch_count': len(veteran_watch),
            'burnout_risk': [w.to_dict() for w in burnout_risk[:10]],
            'injury_risk': [w.to_dict() for w in injury_risk[:10]],
            'veteran_watch': [w.to_dict() for w in veteran_watch[:10]],
        }
    })


@wellness_bp.route('/api/wellness/dashboard')
def api_wellness_dashboard():
    database = get_database()
    universe = get_universe()
    roster = universe.get_active_wrestlers()
    policy = database.get_wellness_policy()
    violations = database.get_wellness_violations()

    burnout_board = []
    fatigue_board = []
    age_watch = []

    for wrestler in roster:
        burnout_level = _burnout_level(wrestler)
        age_decline_score = _age_decline_score(wrestler)
        entry = {
            'wrestler_id': wrestler.id,
            'name': wrestler.name,
            'brand': wrestler.primary_brand,
            'role': wrestler.role,
            'fatigue': wrestler.fatigue,
            'morale': wrestler.morale,
            'age': wrestler.age,
            'is_injured': wrestler.is_injured,
            'burnout_level': burnout_level,
            'age_decline_score': age_decline_score,
        }

        if burnout_level in {'critical', 'high', 'medium'}:
            burnout_board.append(entry)
        if wrestler.fatigue >= 60 or wrestler.is_injured:
            fatigue_board.append(entry)
        if wrestler.age >= 38 or age_decline_score >= 45:
            age_watch.append(entry)

    burnout_board.sort(key=lambda item: (item['burnout_level'], -item['fatigue'], item['morale']))
    fatigue_board.sort(key=lambda item: (-item['fatigue'], item['morale']))
    age_watch.sort(key=lambda item: (-item['age_decline_score'], -item['age']))

    suspension_total = sum(int(violation.get('suspension_weeks', 0)) for violation in violations)
    recent_violations = violations[:10]

    return jsonify({
        'success': True,
        'summary': {
            'burnout_risk_count': len(burnout_board),
            'fatigue_watch_count': len(fatigue_board),
            'age_watch_count': len(age_watch),
            'violation_count': len(violations),
            'suspension_weeks_total': suspension_total,
            'testing_frequency_weeks': policy.get('testing_frequency_weeks', 4),
            'policy_strictness': policy.get('strictness', 60),
        },
        'policy': policy,
        'burnout_watch': burnout_board[:12],
        'fatigue_watch': fatigue_board[:12],
        'age_watch': age_watch[:12],
        'recent_violations': recent_violations,
    })
