"""
Morale Behavior Routes
Steps 245-253: Unhappy Wrestler Behavior System

Endpoints:
  GET  /api/morale/dashboard              — Full roster morale overview
  GET  /api/morale/behaviors              — All active negative behaviors
  GET  /api/morale/wrestler/<id>          — Single wrestler morale state
  POST /api/morale/wrestler/<id>/release  — Respond to release demand
  POST /api/morale/wrestler/<id>/dismiss-public — Respond to public demand
  POST /api/morale/wrestler/<id>/evaluate — Force behavior evaluation
  GET  /api/morale/events                 — Behavior event log
  POST /api/morale/weekly-tick            — Run weekly behavior tick for all wrestlers
  GET  /api/morale/penalties              — Match quality penalties summary
  POST /api/morale/wrestler/<id>/meet     — Hold private meeting (+morale)
"""

import json
import random
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app

morale_bp = Blueprint('morale', __name__)


BRAND_ALIASES = {
    'Alpha': 'ROC Alpha',
    'Velocity': 'ROC Velocity',
    'Vanguard': 'ROC Vanguard',
}


NEGATIVE_EVENT_LIBRARY = {
    'burial_clean_loss_to_lower': {
        'description': 'Booked to lose clean to a lower-ranked opponent.',
        'delta': -12,
        'component': 'push_satisfaction',
    },
    'ppv_removed_without_reason': {
        'description': 'Removed from the PPV card without explanation.',
        'delta': -18,
        'component': 'push_satisfaction',
    },
    'sudden_demotion': {
        'description': 'Suddenly demoted on the card.',
        'delta': -20,
        'component': 'push_satisfaction',
    },
    'forced_character_change': {
        'description': 'Forced into a creative direction they dislike.',
        'delta': -20,
        'component': 'promo_satisfaction',
    },
    'creative_control_violated': {
        'description': 'Creative input was ignored.',
        'delta': -25,
        'component': 'promo_satisfaction',
    },
    'stale_repetitive_booking': {
        'description': 'Creative has gone stale and repetitive.',
        'delta': -10,
        'component': 'promo_satisfaction',
    },
    'missed_from_tv': {
        'description': 'Left off television despite expecting time.',
        'delta': -15,
        'component': 'push_satisfaction',
    },
    'overbooked_schedule': {
        'description': 'Workload feels unsustainable.',
        'delta': -12,
        'component': 'management_appreciation',
    },
    'fatigue_ignored': {
        'description': 'Fatigue concerns were ignored.',
        'delta': -14,
        'component': 'management_appreciation',
    },
    'pay_cut_issued': {
        'description': 'Hit with a pay cut.',
        'delta': -22,
        'component': 'management_appreciation',
    },
    'peer_salary_leaked': {
        'description': 'Salary disparity with peers became public.',
        'delta': -14,
        'component': 'management_appreciation',
    },
    'raise_request_denied': {
        'description': 'Raise request was denied.',
        'delta': -16,
        'component': 'management_appreciation',
    },
    'title_shot_promise_broken': {
        'description': 'A promised title shot never arrived.',
        'delta': -25,
        'component': 'management_appreciation',
    },
    'push_promise_broken': {
        'description': 'A promised push was broken.',
        'delta': -22,
        'component': 'management_appreciation',
    },
    'ppv_slot_promise_broken': {
        'description': 'A promised PPV slot was broken.',
        'delta': -18,
        'component': 'management_appreciation',
    },
    'public_humiliation_angle': {
        'description': 'Embarrassed on-screen in a humiliating angle.',
        'delta': -20,
        'component': 'peer_respect',
    },
    'shoot_style_embarrassment': {
        'description': 'Put in a disrespectful shoot-style embarrassment segment.',
        'delta': -24,
        'component': 'peer_respect',
    },
    'locker_room_argument': {
        'description': 'Backstage conflict has hurt locker-room standing.',
        'delta': -16,
        'component': 'peer_respect',
    },
}


def get_universe():
    return current_app.config['UNIVERSE']


def get_database():
    return current_app.config['DATABASE']


# ============================================================
# Helpers
# ============================================================

def _load_behavior_state(db, wrestler_id):
    """Load WrestlerBehaviorState from database, or create fresh."""
    from simulation.morale_behaviors import WrestlerBehaviorState
    data = db.get_behavior_state(wrestler_id)
    if data:
        return WrestlerBehaviorState.from_dict(data)
    return WrestlerBehaviorState(wrestler_id=wrestler_id)


def _save_behavior_state(db, state):
    """Persist a WrestlerBehaviorState to database."""
    db.save_behavior_state(state)


def _save_behavior_event(db, event):
    """Persist a BehaviorEvent to database."""
    db.save_behavior_event(event)


def _normalize_brand(brand):
    if not brand:
        return None
    return BRAND_ALIASES.get(brand, brand)


def _clamp(value, lower=0.0, upper=100.0):
    return max(lower, min(upper, value))


def _morale_record_from_dict(data, wrestler):
    from simulation.morale import (
        HiddenMoraleFactors,
        ManagementAppreciationEvent,
        MoraleComponents,
        MoraleMomentum,
        WrestlerMoraleRecord,
    )

    base_score = float(data.get('morale_score') if data else getattr(wrestler, 'morale', 50))
    default_components = {
        'push_satisfaction': base_score,
        'win_loss_satisfaction': base_score,
        'championship_satisfaction': base_score,
        'match_quality_satisfaction': base_score,
        'promo_satisfaction': base_score,
        'merch_satisfaction': base_score,
        'peer_respect': base_score,
        'management_appreciation': base_score,
    }

    components = MoraleComponents(**(data.get('components') or default_components if data else default_components))
    momentum = MoraleMomentum(**(data.get('momentum') or {})) if data else MoraleMomentum()
    hidden = HiddenMoraleFactors(**(data.get('hidden_factors') or {})) if data else HiddenMoraleFactors()

    record = WrestlerMoraleRecord(
        wrestler_id=wrestler.id,
        wrestler_name=wrestler.name,
        morale_score=base_score,
        components=components,
        momentum=momentum,
        hidden_factors=hidden,
        recent_events=(data.get('recent_events') or []) if data else [],
        last_processed_week=(data.get('last_processed_week') or 0) if data else 0,
        last_processed_year=(data.get('last_processed_year') or 1) if data else 1,
    )

    appreciation_events = []
    if data:
        for event in data.get('appreciation_events', []) or []:
            appreciation_events.append(ManagementAppreciationEvent(
                event_type=event.get('event_type', 'verbal_praise'),
                description=event.get('description', 'Management interaction'),
                morale_boost=event.get('morale_boost', 5.0),
                week=event.get('week', 1),
                year=event.get('year', 1),
            ))
    record._appreciation_events = appreciation_events
    record.morale_score = _clamp(record.morale_score)
    return record


def _load_morale_record(db, wrestler):
    return _morale_record_from_dict(db.load_morale_record(wrestler.id), wrestler)


def _persist_morale_record(db, universe, wrestler, record):
    wrestler.morale = int(round(_clamp(record.morale_score)))
    universe.save_wrestler(wrestler)
    db.save_morale_record(record)


def _serialize_morale_roster_entry(record, wrestler, morale_engine):
    negative_summary = morale_engine.get_negative_factors_summary(record)
    top_concern = negative_summary['most_critical']['label'] if negative_summary['most_critical'] else (
        record.recent_events[0]['description'] if record.recent_events else 'Stable morale'
    )
    return {
        'wrestler_id': wrestler.id,
        'id': wrestler.id,
        'name': wrestler.name,
        'role': getattr(wrestler, 'role', 'Unknown'),
        'brand': getattr(wrestler, 'primary_brand', 'Unassigned'),
        'morale_score': round(record.morale_score, 1),
        'category': record.category.value,
        'category_color': record.category.color,
        'category_emoji': record.category.emoji,
        'trend': record.momentum.to_dict()['trend'],
        'top_concern': top_concern,
        'negative_factors_count': negative_summary['total_negative_components'],
    }


# ============================================================
# Frontend compatibility endpoints
# ============================================================

@morale_bp.route('/api/morale/roster/summary')
def api_morale_roster_summary():
    try:
        from simulation.morale import morale_engine

        universe = get_universe()
        db = get_database()
        brand = _normalize_brand(request.args.get('brand'))

        wrestlers = universe.get_active_wrestlers()
        if brand:
            wrestlers = [w for w in wrestlers if getattr(w, 'primary_brand', '') == brand]

        entries = []
        category_breakdown = {
            'Ecstatic': 0,
            'Happy': 0,
            'Content': 0,
            'Unhappy': 0,
            'Miserable': 0,
        }

        for wrestler in wrestlers:
            record = _load_morale_record(db, wrestler)
            entry = _serialize_morale_roster_entry(record, wrestler, morale_engine)
            entries.append(entry)
            category_breakdown[entry['category']] += 1

        entries.sort(key=lambda item: item['morale_score'])
        average_morale = round(sum(item['morale_score'] for item in entries) / max(len(entries), 1), 1)

        return jsonify({
            'success': True,
            'average_morale': average_morale,
            'category_breakdown': category_breakdown,
            'wrestlers': entries,
            'total': len(entries),
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@morale_bp.route('/api/morale/categories')
def api_morale_categories():
    try:
        from simulation.morale import morale_engine

        universe = get_universe()
        db = get_database()
        brand = _normalize_brand(request.args.get('brand'))

        wrestlers = universe.get_active_wrestlers()
        if brand:
            wrestlers = [w for w in wrestlers if getattr(w, 'primary_brand', '') == brand]

        categories = {
            'Ecstatic': {'emoji': '😄', 'color': '#00c851', 'wrestlers': []},
            'Happy': {'emoji': '🙂', 'color': '#33b5e5', 'wrestlers': []},
            'Content': {'emoji': '😐', 'color': '#ffbb33', 'wrestlers': []},
            'Unhappy': {'emoji': '😞', 'color': '#ff8800', 'wrestlers': []},
            'Miserable': {'emoji': '😡', 'color': '#ff4444', 'wrestlers': []},
        }

        for wrestler in wrestlers:
            record = _load_morale_record(db, wrestler)
            entry = _serialize_morale_roster_entry(record, wrestler, morale_engine)
            categories[entry['category']]['wrestlers'].append({
                'id': wrestler.id,
                'name': wrestler.name,
                'role': getattr(wrestler, 'role', 'Unknown'),
                'score': entry['morale_score'],
            })

        for category in categories.values():
            category['wrestlers'].sort(key=lambda item: item['score'])

        return jsonify({'success': True, 'categories': categories})

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@morale_bp.route('/api/morale/<wrestler_id>')
def api_morale_detail_compat(wrestler_id):
    try:
        from simulation.morale import morale_engine

        universe = get_universe()
        db = get_database()
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404

        record = _load_morale_record(db, wrestler)
        summary = morale_engine.get_morale_summary(record)

        return jsonify({
            **summary,
            'wrestler_name': wrestler.name,
            'role': getattr(wrestler, 'role', 'Unknown'),
            'brand': getattr(wrestler, 'primary_brand', 'Unassigned'),
            'trend': summary['momentum']['trend'],
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@morale_bp.route('/api/morale/<wrestler_id>/negative-factors')
def api_morale_negative_factors_compat(wrestler_id):
    try:
        from simulation.morale import morale_engine

        universe = get_universe()
        db = get_database()
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404

        record = _load_morale_record(db, wrestler)
        negative_summary = morale_engine.get_negative_factors_summary(record)
        components = record.components.to_dict()
        component_breakdown = []
        for key, label in (
            ('push_satisfaction', 'Push Satisfaction'),
            ('win_loss_satisfaction', 'Win/Loss Satisfaction'),
            ('championship_satisfaction', 'Championship Satisfaction'),
            ('match_quality_satisfaction', 'Match Quality Satisfaction'),
            ('promo_satisfaction', 'Promo Satisfaction'),
            ('merch_satisfaction', 'Merchandise Satisfaction'),
            ('peer_respect', 'Peer Respect'),
            ('management_appreciation', 'Management Appreciation'),
        ):
            score = round(components.get(key, 50.0), 1)
            if score < 35:
                status = 'critical'
            elif score < 50:
                status = 'warning'
            else:
                status = 'healthy'
            component_breakdown.append({
                'component': key,
                'label': label,
                'score': score,
                'status': status,
            })

        return jsonify({
            'success': True,
            **negative_summary,
            'component_breakdown': component_breakdown,
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@morale_bp.route('/api/morale/<wrestler_id>/appreciate', methods=['POST'])
def api_morale_appreciate_compat(wrestler_id):
    try:
        from simulation.morale import ManagementAppreciationEngine, morale_engine

        universe = get_universe()
        db = get_database()
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404

        event_type = (request.get_json() or {}).get('event_type', 'verbal_praise')
        if event_type not in ManagementAppreciationEngine.APPRECIATION_EVENTS:
            return jsonify({'error': f'Unknown appreciation event: {event_type}'}), 400

        year, week = db.get_game_state()['current_year'], db.get_game_state()['current_week']
        record = _load_morale_record(db, wrestler)
        record, morale_delta = morale_engine.apply_management_appreciation(record, event_type, week, year)
        record.components.management_appreciation = _clamp(
            record.components.management_appreciation + morale_delta
        )
        _persist_morale_record(db, universe, wrestler, record)

        event_meta = ManagementAppreciationEngine.APPRECIATION_EVENTS[event_type]
        return jsonify({
            'success': True,
            'wrestler_id': wrestler.id,
            'wrestler_name': wrestler.name,
            'morale_delta': round(morale_delta, 1),
            'new_morale': round(record.morale_score, 1),
            'description': event_meta['description'],
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@morale_bp.route('/api/morale/<wrestler_id>/meeting', methods=['POST'])
def api_morale_meeting_compat(wrestler_id):
    try:
        from simulation.morale import morale_engine

        universe = get_universe()
        db = get_database()
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404

        response = (request.get_json() or {}).get('response', 'acknowledge')
        year, week = db.get_game_state()['current_year'], db.get_game_state()['current_week']
        record = _load_morale_record(db, wrestler)

        warning = None
        if response == 'acknowledge':
            record, delta = morale_engine.apply_management_appreciation(record, 'creative_meeting', week, year)
            record.components.management_appreciation = _clamp(
                record.components.management_appreciation + delta
            )
            message = f'You heard out {wrestler.name} and gave them a clearer direction.'
        elif response == 'promise_push':
            record, delta = morale_engine.apply_management_appreciation(record, 'promised_push', week, year)
            record.components.management_appreciation = _clamp(
                record.components.management_appreciation + delta
            )
            message = f'You promised {wrestler.name} a stronger push.'
            warning = 'Broken promises will come back hard later.'
        elif response == 'give_time_off':
            if hasattr(wrestler, 'fatigue'):
                wrestler.fatigue = max(0, getattr(wrestler, 'fatigue', 0) - 10)
            record.add_morale_event(
                event_type='meeting_time_off',
                description='Management approved time off to reset and recover.',
                delta=12,
                component='management_appreciation',
            )
            delta = 12
            record.components.management_appreciation = _clamp(
                record.components.management_appreciation + delta
            )
            message = f'{wrestler.name} appreciated the time off.'
        elif response == 'ignore':
            record, delta = morale_engine.apply_negative_event(
                record,
                event_type='meeting_ignored',
                description='Management ignored a direct morale meeting request.',
                delta=-10,
                component='management_appreciation',
            )
            record.components.management_appreciation = _clamp(
                record.components.management_appreciation + delta
            )
            message = f'{wrestler.name} left the meeting feeling dismissed.'
        else:
            return jsonify({'error': f'Unknown meeting response: {response}'}), 400

        _persist_morale_record(db, universe, wrestler, record)
        if response == 'give_time_off':
            universe.save_wrestler(wrestler)

        return jsonify({
            'success': True,
            'outcome': {
                'delta': round(delta, 1),
                'message': message,
                'warning': warning,
            },
            'new_morale': round(record.morale_score, 1),
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@morale_bp.route('/api/morale/<wrestler_id>/negative-event', methods=['POST'])
def api_morale_negative_event_compat(wrestler_id):
    try:
        from simulation.morale import morale_engine

        universe = get_universe()
        db = get_database()
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404

        event_type = (request.get_json() or {}).get('event_type')
        event_def = NEGATIVE_EVENT_LIBRARY.get(event_type)
        if not event_def:
            return jsonify({'error': f'Unknown negative event: {event_type}'}), 400

        record = _load_morale_record(db, wrestler)
        record, morale_delta = morale_engine.apply_negative_event(
            record,
            event_type=event_type,
            description=event_def['description'],
            delta=event_def['delta'],
            component=event_def['component'],
        )
        if hasattr(record.components, event_def['component']):
            current_component = getattr(record.components, event_def['component'])
            setattr(record.components, event_def['component'], _clamp(current_component + morale_delta))
        _persist_morale_record(db, universe, wrestler, record)

        return jsonify({
            'success': True,
            'wrestler_id': wrestler.id,
            'wrestler_name': wrestler.name,
            'morale_delta': round(morale_delta, 1),
            'new_morale': round(record.morale_score, 1),
            'description': event_def['description'],
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================
# GET /api/morale/dashboard
# ============================================================

@morale_bp.route('/api/morale/dashboard')
def api_morale_dashboard():
    """
    Full morale overview: roster health, active behaviors, top warnings.
    """
    try:
        from simulation.morale_behaviors import morale_behavior_engine, _morale_category

        universe = get_universe()
        db = get_database()
        wrestlers = universe.get_active_wrestlers()

        total = len(wrestlers)
        ecstatic = happy = content = discontented = unhappy = miserable = 0
        active_behavior_count = 0
        critical_alerts = []
        high_risk = []
        behavior_breakdown = {
            'release_demand': 0,
            'public_release_demand': 0,
            'match_quality_decline': 0,
            'sandbagging': 0,
            'cooperation_refusal': 0,
            'dirt_sheet_leak': 0,
            'social_media_vent': 0,
            'backstage_poison': 0,
            'contract_running_down': 0,
        }
        total_match_penalty = 0.0

        for w in wrestlers:
            cat = _morale_category(w.morale)
            if cat == 'ecstatic':      ecstatic += 1
            elif cat == 'happy':       happy += 1
            elif cat == 'content':     content += 1
            elif cat == 'discontented': discontented += 1
            elif cat == 'unhappy':     unhappy += 1
            elif cat == 'miserable':   miserable += 1

            state = _load_behavior_state(db, w.id)
            summary = morale_behavior_engine.get_wrestler_behavior_summary(w, state)

            if summary['active_behaviors']:
                active_behavior_count += 1
                for beh in summary['active_behaviors']:
                    btype = beh['type']
                    if btype in behavior_breakdown:
                        behavior_breakdown[btype] += 1
                    if beh['severity'] == 'critical':
                        critical_alerts.append({
                            'wrestler_id': w.id,
                            'wrestler_name': w.name,
                            'morale': w.morale,
                            **beh
                        })
                    elif beh['severity'] == 'high':
                        high_risk.append({
                            'wrestler_id': w.id,
                            'wrestler_name': w.name,
                            'morale': w.morale,
                            **beh
                        })

            total_match_penalty += summary['total_match_penalty']

        return jsonify({
            'summary': {
                'total_active': total,
                'with_active_behaviors': active_behavior_count,
                'critical_alerts': len(critical_alerts),
                'high_risk': len(high_risk),
                'average_match_penalty': round(total_match_penalty / max(total, 1), 3),
            },
            'morale_distribution': {
                'ecstatic': ecstatic,
                'happy': happy,
                'content': content,
                'discontented': discontented,
                'unhappy': unhappy,
                'miserable': miserable,
            },
            'behavior_breakdown': behavior_breakdown,
            'critical_alerts': critical_alerts[:10],
            'high_risk': high_risk[:10],
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================
# GET /api/morale/behaviors
# ============================================================

@morale_bp.route('/api/morale/behaviors')
def api_active_behaviors():
    """List all wrestlers with active negative behaviors."""
    try:
        from simulation.morale_behaviors import morale_behavior_engine

        universe = get_universe()
        db = get_database()
        brand = request.args.get('brand')
        severity_filter = request.args.get('severity')  # critical|high|medium|low
        behavior_filter = request.args.get('type')

        wrestlers = universe.get_active_wrestlers()
        if brand:
            wrestlers = [w for w in wrestlers if w.primary_brand == brand]

        results = []
        for w in wrestlers:
            state = _load_behavior_state(db, w.id)
            summary = morale_behavior_engine.get_wrestler_behavior_summary(w, state)

            behaviors = summary['active_behaviors']
            if severity_filter:
                behaviors = [b for b in behaviors if b['severity'] == severity_filter]
            if behavior_filter:
                behaviors = [b for b in behaviors if b['type'] == behavior_filter]

            if behaviors:
                results.append({
                    'wrestler_id': w.id,
                    'wrestler_name': w.name,
                    'morale': w.morale,
                    'morale_category': summary['morale_category'],
                    'total_match_penalty': summary['total_match_penalty'],
                    'active_behaviors': behaviors,
                })

        results.sort(key=lambda x: x['morale'])

        return jsonify({
            'total': len(results),
            'wrestlers': results,
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================
# GET /api/morale/wrestler/<id>
# ============================================================

@morale_bp.route('/api/morale/wrestler/<wrestler_id>')
def api_wrestler_morale(wrestler_id):
    """Full morale and behavior state for a single wrestler."""
    try:
        from simulation.morale_behaviors import morale_behavior_engine

        universe = get_universe()
        db = get_database()

        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404

        state = _load_behavior_state(db, wrestler_id)
        summary = morale_behavior_engine.get_wrestler_behavior_summary(wrestler, state)

        # Recent behavior events
        recent_events = db.get_behavior_events(wrestler_id, limit=10)

        return jsonify({
            **summary,
            'recent_events': recent_events,
            'wrestler': {
                'id': wrestler.id,
                'name': wrestler.name,
                'morale': wrestler.morale,
                'role': wrestler.role,
                'brand': wrestler.primary_brand,
                'is_major_superstar': wrestler.is_major_superstar,
                'contract_weeks_remaining': wrestler.contract.weeks_remaining,
            }
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================
# POST /api/morale/wrestler/<id>/release
# Respond to a release demand
# ============================================================

@morale_bp.route('/api/morale/wrestler/<wrestler_id>/release', methods=['POST'])
def api_respond_release_demand(wrestler_id):
    """
    Respond to a wrestler's release demand.
    Actions: 'grant' | 'refuse' | 'negotiate'
    """
    try:
        universe = get_universe()
        db = get_database()

        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404

        state = _load_behavior_state(db, wrestler_id)

        if not state.has_requested_release:
            return jsonify({'error': 'This wrestler has not requested a release'}), 400

        data = request.get_json() or {}
        action = data.get('action', 'refuse')  # grant | refuse | negotiate

        result = {}

        if action == 'grant':
            # Release the wrestler
            wrestler.contract.weeks_remaining = 0
            state.has_requested_release = False
            state.has_gone_public = False
            # Small morale boost — they get what they want
            wrestler.adjust_morale(20)
            result = {
                'outcome': 'granted',
                'message': f'✅ {wrestler.name} has been released. Morale +20.',
                'morale_change': 20,
            }

        elif action == 'refuse':
            # Refuse — morale drops further, they may escalate
            wrestler.adjust_morale(-15)
            result = {
                'outcome': 'refused',
                'message': f'❌ Release denied. {wrestler.name} is furious. Morale −15. Expect escalation.',
                'morale_change': -15,
            }

        elif action == 'negotiate':
            # Negotiate — meet in the middle
            # Requires salary data from request
            new_salary = data.get('new_salary', wrestler.contract.salary_per_show)
            promise = data.get('promise', None)  # 'title_shot' | 'push' | None

            morale_gain = 10
            if new_salary > wrestler.contract.salary_per_show:
                gain = min(int((new_salary - wrestler.contract.salary_per_show) / 500), 15)
                morale_gain += gain
                wrestler.contract.salary_per_show = new_salary

            if promise == 'title_shot':
                morale_gain += 15
            elif promise == 'push':
                morale_gain += 10

            wrestler.adjust_morale(morale_gain)

            # 50% chance the negotiation resolves the demand
            if wrestler.morale > 40:
                state.has_requested_release = False
                state.has_gone_public = False
                resolved_msg = f"✅ Negotiations succeeded. {wrestler.name} has withdrawn their release request."
            else:
                resolved_msg = f"⚠️ Negotiations helped but {wrestler.name} still wants out eventually."

            result = {
                'outcome': 'negotiated',
                'message': resolved_msg,
                'morale_change': morale_gain,
                'new_salary': new_salary,
            }

        universe.save_wrestler(wrestler)
        _save_behavior_state(db, state)
        db.conn.commit()

        return jsonify({
            'success': True,
            'wrestler': wrestler.to_dict(),
            **result,
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================
# POST /api/morale/wrestler/<id>/dismiss-public
# Respond to a public release demand
# ============================================================

@morale_bp.route('/api/morale/wrestler/<wrestler_id>/dismiss-public', methods=['POST'])
def api_respond_public_demand(wrestler_id):
    """
    Respond to a wrestler's public release demand.
    Actions: 'address' | 'ignore' | 'suspend'
    """
    try:
        universe = get_universe()
        db = get_database()

        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404

        state = _load_behavior_state(db, wrestler_id)

        if not state.has_gone_public:
            return jsonify({'error': 'No public demand active'}), 400

        data = request.get_json() or {}
        action = data.get('action', 'ignore')

        if action == 'address':
            # Public statement and salary improvement
            wrestler.adjust_morale(10)
            state.has_gone_public = False
            result = {
                'outcome': 'addressed',
                'message': f'📢 You made a public statement addressing {wrestler.name}\'s concerns. Morale +10, PR damage limited.',
                'morale_change': 10,
                'pr_damage': 'minimal',
            }
        elif action == 'ignore':
            # Fans notice the silence
            wrestler.adjust_morale(-5)
            result = {
                'outcome': 'ignored',
                'message': f'😶 No response issued. Fans and media are speculating. {wrestler.name}\'s morale worsened.',
                'morale_change': -5,
                'pr_damage': 'moderate',
            }
        elif action == 'suspend':
            # Fine or suspend — drastic
            wrestler.adjust_morale(-20)
            result = {
                'outcome': 'suspended',
                'message': f'🔴 {wrestler.name} suspended for conduct. Morale −20. This may trigger immediate legal action.',
                'morale_change': -20,
                'pr_damage': 'severe',
            }
        else:
            return jsonify({'error': 'Invalid action'}), 400

        universe.save_wrestler(wrestler)
        _save_behavior_state(db, state)
        db.conn.commit()

        return jsonify({
            'success': True,
            'wrestler': wrestler.to_dict(),
            **result,
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================
# POST /api/morale/wrestler/<id>/meet
# Hold a private meeting to address grievances
# ============================================================

@morale_bp.route('/api/morale/wrestler/<wrestler_id>/meet', methods=['POST'])
def api_hold_meeting(wrestler_id):
    """
    Hold a private meeting with a wrestler.
    Step 254 integration point. Can calm tensions if done correctly.
    """
    try:
        universe = get_universe()
        db = get_database()

        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404

        data = request.get_json() or {}
        approach = data.get('approach', 'listen')  # listen | promise | salary | push

        state = _load_behavior_state(db, wrestler_id)

        morale_gain = 0
        notes = []

        if approach == 'listen':
            morale_gain = random.randint(5, 12)
            notes.append("You listened to their concerns without making commitments.")

        elif approach == 'promise':
            morale_gain = random.randint(8, 18)
            promise_type = data.get('promise_type', 'push')
            notes.append(f"You promised a {promise_type}. They feel valued — for now.")
            # Track promise broken probability later

        elif approach == 'salary':
            raise_amount = data.get('raise_amount', 1000)
            wrestler.contract.salary_per_show += raise_amount
            morale_gain = min(int(raise_amount / 200), 25)
            notes.append(f"Salary raised by ${raise_amount:,}/show. They appreciate the gesture.")

        elif approach == 'push':
            morale_gain = random.randint(10, 20)
            notes.append("Promised improved booking. They'll hold you to it.")

        wrestler.adjust_morale(morale_gain)

        # If morale recovers enough, clear some behaviors
        if wrestler.morale > 50:
            state.is_phoning_it_in = False
            state.phone_in_penalty = 0.0
            state.is_sandbagging = False
            state.sandbagging_penalty = 0.0
            state.cooperation_refusal_active = False
            state.is_venting_online = False
            notes.append("Their attitude in the ring has improved.")

        universe.save_wrestler(wrestler)
        _save_behavior_state(db, state)
        db.conn.commit()

        return jsonify({
            'success': True,
            'morale_gain': morale_gain,
            'new_morale': wrestler.morale,
            'notes': notes,
            'wrestler': wrestler.to_dict(),
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================
# POST /api/morale/wrestler/<id>/evaluate
# Force re-evaluation for one wrestler
# ============================================================

@morale_bp.route('/api/morale/wrestler/<wrestler_id>/evaluate', methods=['POST'])
def api_evaluate_wrestler(wrestler_id):
    """Force a behavior evaluation cycle for a single wrestler."""
    try:
        from simulation.morale_behaviors import morale_behavior_engine

        universe = get_universe()
        db = get_database()
        state_data = db.get_game_state()
        year = state_data['current_year']
        week = state_data['current_week']

        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404

        state = _load_behavior_state(db, wrestler_id)
        all_wrestlers = universe.get_active_wrestlers()

        new_events = morale_behavior_engine.evaluate_wrestler(
            wrestler, state, year, week, all_wrestlers
        )

        # Save state and events
        _save_behavior_state(db, state)
        for event in new_events:
            _save_behavior_event(db, event)

        # Save all wrestlers affected by poisoning
        if state.is_poisoning_locker_room:
            for w in all_wrestlers:
                if w.id in state.poisoning_targets:
                    universe.save_wrestler(w)

        universe.save_wrestler(wrestler)
        db.conn.commit()

        summary = morale_behavior_engine.get_wrestler_behavior_summary(wrestler, state)

        return jsonify({
            'success': True,
            'new_events': [e.to_dict() for e in new_events],
            'summary': summary,
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================
# POST /api/morale/weekly-tick
# Run behavior evaluation for ALL wrestlers
# ============================================================

@morale_bp.route('/api/morale/weekly-tick', methods=['POST'])
def api_weekly_morale_tick():
    """
    Run full morale behavior evaluation for all active wrestlers.
    Called at end of each simulated week/show.
    """
    try:
        from simulation.morale_behaviors import morale_behavior_engine

        universe = get_universe()
        db = get_database()
        state_data = db.get_game_state()
        year = state_data['current_year']
        week = state_data['current_week']

        all_wrestlers = universe.get_active_wrestlers()
        all_events = []
        affected_wrestlers = []

        for wrestler in all_wrestlers:
            state = _load_behavior_state(db, wrestler.id)

            new_events = morale_behavior_engine.evaluate_wrestler(
                wrestler, state, year, week, all_wrestlers
            )

            _save_behavior_state(db, state)

            for event in new_events:
                _save_behavior_event(db, event)
                all_events.append(event.to_dict())

            if new_events:
                universe.save_wrestler(wrestler)
                affected_wrestlers.append(wrestler.name)

        db.conn.commit()

        return jsonify({
            'success': True,
            'year': year,
            'week': week,
            'total_evaluated': len(all_wrestlers),
            'new_events_fired': len(all_events),
            'affected_wrestlers': affected_wrestlers,
            'events': all_events,
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================
# GET /api/morale/events
# Behavior event log
# ============================================================

@morale_bp.route('/api/morale/events')
def api_behavior_events():
    """Get recent behavior events, optionally filtered."""
    try:
        db = get_database()
        wrestler_id = request.args.get('wrestler_id')
        behavior_type = request.args.get('type')
        limit = request.args.get('limit', 50, type=int)

        events = db.get_behavior_events(wrestler_id=wrestler_id, behavior_type=behavior_type, limit=limit)

        return jsonify({
            'total': len(events),
            'events': events,
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================
# GET /api/morale/penalties
# Active match quality penalties
# ============================================================

@morale_bp.route('/api/morale/penalties')
def api_match_penalties():
    """
    List all wrestlers currently imposing a match quality penalty.
    Used by the booking screen to warn the booker.
    """
    try:
        from simulation.morale_behaviors import morale_behavior_engine

        universe = get_universe()
        db = get_database()

        wrestlers = universe.get_active_wrestlers()
        penalties = []

        for w in wrestlers:
            state = _load_behavior_state(db, w.id)
            penalty = morale_behavior_engine.get_match_quality_penalty(state)
            if penalty > 0:
                penalties.append({
                    'wrestler_id': w.id,
                    'wrestler_name': w.name,
                    'morale': w.morale,
                    'penalty': round(penalty, 2),
                    'reasons': [
                        b['label'] for b in
                        morale_behavior_engine.get_wrestler_behavior_summary(w, state)['active_behaviors']
                        if b.get('match_quality_penalty', 0) > 0 or b['type'] in
                        ('match_quality_decline', 'sandbagging', 'contract_running_down')
                    ]
                })

        penalties.sort(key=lambda x: -x['penalty'])

        return jsonify({
            'total': len(penalties),
            'total_penalty_pool': round(sum(p['penalty'] for p in penalties), 2),
            'penalties': penalties,
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================
# GET /api/morale/release-demands
# All active release demands
# ============================================================

@morale_bp.route('/api/morale/release-demands')
def api_release_demands():
    """List all wrestlers with active release demands (private or public)."""
    try:
        universe = get_universe()
        db = get_database()

        wrestlers = universe.get_active_wrestlers()
        demands = []

        for w in wrestlers:
            state = _load_behavior_state(db, w.id)
            if state.has_requested_release:
                demands.append({
                    'wrestler_id': w.id,
                    'wrestler_name': w.name,
                    'morale': w.morale,
                    'role': w.role,
                    'brand': w.primary_brand,
                    'is_major_superstar': w.is_major_superstar,
                    'is_public': state.has_gone_public,
                    'public_statement': state.public_statement,
                    'demand_year': state.release_demand_year,
                    'demand_week': state.release_demand_week,
                    'demand_count': state.release_demand_count,
                    'contract_weeks_remaining': w.contract.weeks_remaining,
                    'actions': ['grant', 'refuse', 'negotiate'],
                })

        return jsonify({
            'total': len(demands),
            'public_demands': len([d for d in demands if d['is_public']]),
            'private_demands': len([d for d in demands if not d['is_public']]),
            'demands': demands,
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500
