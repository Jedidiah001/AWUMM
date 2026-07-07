"""
recovery_routes.py
Steps 254-259: Morale Recovery API Endpoints

Endpoints:
  GET  /api/recovery/wrestler/<id>/menu          — Available recovery options + cooldowns
  POST /api/recovery/wrestler/<id>/meeting        — Step 254: Private meeting
  POST /api/recovery/wrestler/<id>/push           — Step 255: Push adjustment
  POST /api/recovery/wrestler/<id>/renegotiate    — Step 256: Contract renegotiation
  POST /api/recovery/wrestler/<id>/creative       — Step 257: Creative input
  POST /api/recovery/wrestler/<id>/time-off       — Step 258: Time off / rest
  POST /api/recovery/mentorship                   — Step 259: Assign mentorship
  GET  /api/recovery/history                      — Recovery event log
  GET  /api/recovery/wrestler/<id>/history        — Per-wrestler recovery history
  GET  /api/recovery/summary                      — Roster-wide recovery overview
"""

import json
from flask import Blueprint, jsonify, request, current_app
from simulation.morale_recovery import (
    morale_recovery_engine,
    MeetingApproach,
    PushType,
    RenegotiationTool,
    CreativeInputType,
    TimeOffType,
    RecoveryCooldown,
    _abs_week,
)

recovery_bp = Blueprint('recovery', __name__)


# ============================================================
# Helpers
# ============================================================

def get_universe():
    return current_app.config['UNIVERSE']


def get_database():
    return current_app.config['DATABASE']


def _load_cooldown(db, wrestler_id: str) -> RecoveryCooldown:
    """Load or create a RecoveryCooldown for a wrestler from DB."""
    data = db.get_recovery_cooldown(wrestler_id)
    if data:
        return RecoveryCooldown(
            wrestler_id=wrestler_id,
            last_used=json.loads(data.get('last_used_json', '{}')),
        )
    return RecoveryCooldown(wrestler_id=wrestler_id)


def _save_cooldown(db, cooldown: RecoveryCooldown) -> None:
    db.save_recovery_cooldown(cooldown)


def _load_behavior_state(db, wrestler_id: str):
    """Load WrestlerBehaviorState from DB, or create fresh."""
    from simulation.morale_behaviors import WrestlerBehaviorState
    data = db.get_behavior_state(wrestler_id)
    if data:
        return WrestlerBehaviorState.from_dict(data)
    return WrestlerBehaviorState(wrestler_id=wrestler_id)


def _save_behavior_state(db, state) -> None:
    db.save_behavior_state(state)


def _get_game_week(db):
    gs = db.get_game_state()
    return gs['current_year'], gs['current_week']


# ============================================================
# GET /api/recovery/wrestler/<id>/menu
# ============================================================

@recovery_bp.route('/api/recovery/wrestler/<wrestler_id>/menu')
def api_recovery_menu(wrestler_id):
    """
    Return all 6 recovery options with availability, cooldown info,
    and recommendations for this wrestler.
    """
    try:
        universe = get_universe()
        db = get_database()

        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404

        year, week = _get_game_week(db)
        cooldown = _load_cooldown(db, wrestler_id)
        menu = morale_recovery_engine.get_recovery_menu(wrestler, cooldown, year, week)

        return jsonify({
            'wrestler_id': wrestler_id,
            'wrestler_name': wrestler.name,
            'morale': wrestler.morale,
            'menu': menu,
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================
# POST /api/recovery/wrestler/<id>/meeting  — Step 254
# ============================================================

@recovery_bp.route('/api/recovery/wrestler/<wrestler_id>/meeting', methods=['POST'])
def api_private_meeting(wrestler_id):
    """
    Hold a private meeting with the wrestler.

    Body:
      approach: "listen" | "acknowledge" | "commit"
      promise_detail: str   (required when approach == "commit")
    """
    try:
        universe = get_universe()
        db = get_database()

        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404

        year, week = _get_game_week(db)
        cooldown = _load_cooldown(db, wrestler_id)
        abs_w = _abs_week(year, week)

        from simulation.morale_recovery import RecoveryType
        if not cooldown.can_use(RecoveryType.PRIVATE_MEETING, abs_w):
            weeks_left = cooldown.weeks_until_available(RecoveryType.PRIVATE_MEETING, abs_w)
            return jsonify({
                'error': f'Private meeting on cooldown. Available in {weeks_left} week(s).'
            }), 400

        data = request.get_json() or {}
        approach_str = data.get('approach', 'listen')
        promise_detail = data.get('promise_detail', '')

        try:
            approach = MeetingApproach(approach_str)
        except ValueError:
            return jsonify({'error': f'Invalid approach. Use: listen | acknowledge | commit'}), 400

        if approach == MeetingApproach.COMMIT and not promise_detail:
            return jsonify({'error': 'promise_detail is required when approach is "commit"'}), 400

        event = morale_recovery_engine.private_meeting(
            wrestler, approach, promise_detail, year, week, cooldown
        )

        universe.save_wrestler(wrestler)
        db.save_recovery_event(event)
        _save_cooldown(db, cooldown)
        db.conn.commit()

        return jsonify({
            'success': True,
            'event': event.to_dict(),
            'new_morale': wrestler.morale,
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================
# POST /api/recovery/wrestler/<id>/push  — Step 255
# ============================================================

@recovery_bp.route('/api/recovery/wrestler/<wrestler_id>/push', methods=['POST'])
def api_push_adjustment(wrestler_id):
    """
    Adjust the wrestler's on-screen push.

    Body:
      push_type: "main_event" | "midcard" | "protection"
    """
    try:
        universe = get_universe()
        db = get_database()

        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404

        year, week = _get_game_week(db)
        cooldown = _load_cooldown(db, wrestler_id)
        abs_w = _abs_week(year, week)

        from simulation.morale_recovery import RecoveryType
        if not cooldown.can_use(RecoveryType.PUSH_ADJUSTMENT, abs_w):
            weeks_left = cooldown.weeks_until_available(RecoveryType.PUSH_ADJUSTMENT, abs_w)
            return jsonify({
                'error': f'Push adjustment on cooldown. Available in {weeks_left} week(s).'
            }), 400

        data = request.get_json() or {}
        push_type_str = data.get('push_type', 'midcard')

        try:
            push_type = PushType(push_type_str)
        except ValueError:
            return jsonify({'error': 'Invalid push_type. Use: main_event | midcard | protection'}), 400

        event = morale_recovery_engine.push_adjustment(
            wrestler, push_type, year, week, cooldown
        )

        universe.save_wrestler(wrestler)
        db.save_recovery_event(event)
        _save_cooldown(db, cooldown)
        db.conn.commit()

        return jsonify({
            'success': True,
            'event': event.to_dict(),
            'new_morale': wrestler.morale,
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================
# POST /api/recovery/wrestler/<id>/renegotiate  — Step 256
# ============================================================

@recovery_bp.route('/api/recovery/wrestler/<wrestler_id>/renegotiate', methods=['POST'])
def api_contract_renegotiation(wrestler_id):
    """
    Offer a contract sweetener.

    Body:
      tool: "salary_raise" | "extension" | "signing_bonus"
      salary_raise: int          ($ per show — for salary_raise)
      extension_weeks: int       (weeks to add — for extension)
      bonus_amount: int          ($ one-time — for signing_bonus)
    """
    try:
        universe = get_universe()
        db = get_database()

        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404

        year, week = _get_game_week(db)
        cooldown = _load_cooldown(db, wrestler_id)
        abs_w = _abs_week(year, week)

        from simulation.morale_recovery import RecoveryType
        if not cooldown.can_use(RecoveryType.CONTRACT_RENEGOTIATION, abs_w):
            weeks_left = cooldown.weeks_until_available(RecoveryType.CONTRACT_RENEGOTIATION, abs_w)
            return jsonify({
                'error': f'Contract renegotiation on cooldown. Available in {weeks_left} week(s).'
            }), 400

        data = request.get_json() or {}
        tool_str = data.get('tool', 'salary_raise')

        try:
            tool = RenegotiationTool(tool_str)
        except ValueError:
            return jsonify({'error': 'Invalid tool. Use: salary_raise | extension | signing_bonus'}), 400

        salary_raise   = int(data.get('salary_raise', 1000))
        extension_weeks = int(data.get('extension_weeks', 12))
        bonus_amount   = int(data.get('bonus_amount', 10000))

        event, cost = morale_recovery_engine.contract_renegotiation(
            wrestler=wrestler,
            tool=tool,
            salary_raise=salary_raise,
            extension_weeks=extension_weeks,
            bonus_amount=bonus_amount,
            year=year,
            week=week,
            cooldown=cooldown,
            universe=universe,
        )

        # Deduct bonus from promotion balance if applicable
        if cost > 0 and tool == RenegotiationTool.SIGNING_BONUS:
            gs = db.get_game_state()
            new_balance = gs['balance'] - cost
            if new_balance < 0:
                return jsonify({'error': f'Insufficient funds. Need ${cost:,}, have ${gs["balance"]:,}.'}), 400
            db.update_balance(new_balance)

        universe.save_wrestler(wrestler)
        db.save_recovery_event(event)
        _save_cooldown(db, cooldown)
        db.conn.commit()

        return jsonify({
            'success': True,
            'event': event.to_dict(),
            'new_morale': wrestler.morale,
            'cost': cost,
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================
# POST /api/recovery/wrestler/<id>/creative  — Step 257
# ============================================================

@recovery_bp.route('/api/recovery/wrestler/<wrestler_id>/creative', methods=['POST'])
def api_creative_input(wrestler_id):
    """
    Give the wrestler creative control.

    Body:
      input_type: "storyline_direction" | "match_type_approval" | "segment_veto"
    """
    try:
        universe = get_universe()
        db = get_database()

        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404

        year, week = _get_game_week(db)
        cooldown = _load_cooldown(db, wrestler_id)
        abs_w = _abs_week(year, week)

        from simulation.morale_recovery import RecoveryType
        if not cooldown.can_use(RecoveryType.CREATIVE_INPUT, abs_w):
            weeks_left = cooldown.weeks_until_available(RecoveryType.CREATIVE_INPUT, abs_w)
            return jsonify({
                'error': f'Creative input on cooldown. Available in {weeks_left} week(s).'
            }), 400

        data = request.get_json() or {}
        input_type_str = data.get('input_type', 'storyline_direction')

        try:
            input_type = CreativeInputType(input_type_str)
        except ValueError:
            return jsonify({
                'error': 'Invalid input_type. Use: storyline_direction | match_type_approval | segment_veto'
            }), 400

        event = morale_recovery_engine.creative_input(
            wrestler, input_type, year, week, cooldown
        )

        universe.save_wrestler(wrestler)
        db.save_recovery_event(event)
        _save_cooldown(db, cooldown)
        db.conn.commit()

        return jsonify({
            'success': True,
            'event': event.to_dict(),
            'new_morale': wrestler.morale,
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================
# POST /api/recovery/wrestler/<id>/time-off  — Step 258
# ============================================================

@recovery_bp.route('/api/recovery/wrestler/<wrestler_id>/time-off', methods=['POST'])
def api_time_off(wrestler_id):
    """
    Grant the wrestler time off.

    Body:
      off_type: "hiatus" | "lighter_schedule" | "vacation"
      hiatus_weeks: int   (2-8, used when off_type == hiatus)
    """
    try:
        universe = get_universe()
        db = get_database()

        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404

        year, week = _get_game_week(db)
        cooldown = _load_cooldown(db, wrestler_id)
        abs_w = _abs_week(year, week)

        from simulation.morale_recovery import RecoveryType
        if not cooldown.can_use(RecoveryType.TIME_OFF, abs_w):
            weeks_left = cooldown.weeks_until_available(RecoveryType.TIME_OFF, abs_w)
            return jsonify({
                'error': f'Time off on cooldown. Available in {weeks_left} week(s).'
            }), 400

        data = request.get_json() or {}
        off_type_str = data.get('off_type', 'lighter_schedule')
        hiatus_weeks = int(data.get('hiatus_weeks', 4))

        try:
            off_type = TimeOffType(off_type_str)
        except ValueError:
            return jsonify({'error': 'Invalid off_type. Use: hiatus | lighter_schedule | vacation'}), 400

        behavior_state = _load_behavior_state(db, wrestler_id)

        event = morale_recovery_engine.time_off(
            wrestler=wrestler,
            off_type=off_type,
            hiatus_weeks=hiatus_weeks,
            year=year,
            week=week,
            cooldown=cooldown,
            behavior_state=behavior_state,
        )

        # For hiatus — mark wrestler as temporarily inactive in their record
        if off_type == TimeOffType.HIATUS:
            if hasattr(wrestler, 'hiatus_weeks_remaining'):
                wrestler.hiatus_weeks_remaining = hiatus_weeks
            # Clear lame duck state
            behavior_state.is_running_down_contract = False
            behavior_state.lame_duck_effort_penalty = 0.0

        # Deduct vacation cost from balance
        if event.cost > 0:
            gs = db.get_game_state()
            new_balance = gs['balance'] - event.cost
            if new_balance < 0:
                return jsonify({'error': f'Insufficient funds for vacation (${event.cost:,}).'}), 400
            db.update_balance(new_balance)

        universe.save_wrestler(wrestler)
        _save_behavior_state(db, behavior_state)
        db.save_recovery_event(event)
        _save_cooldown(db, cooldown)
        db.conn.commit()

        return jsonify({
            'success': True,
            'event': event.to_dict(),
            'new_morale': wrestler.morale,
            'cost': event.cost,
            'hiatus_weeks': hiatus_weeks if off_type == TimeOffType.HIATUS else 0,
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================
# POST /api/recovery/mentorship  — Step 259
# ============================================================

@recovery_bp.route('/api/recovery/mentorship', methods=['POST'])
def api_assign_mentorship():
    """
    Assign a mentor-mentee pairing.

    Body:
      mentor_id: str
      mentee_id: str
    """
    try:
        universe = get_universe()
        db = get_database()

        data = request.get_json() or {}
        mentor_id = data.get('mentor_id')
        mentee_id = data.get('mentee_id')

        if not mentor_id or not mentee_id:
            return jsonify({'error': 'mentor_id and mentee_id are required'}), 400

        if mentor_id == mentee_id:
            return jsonify({'error': 'Mentor and mentee must be different wrestlers'}), 400

        mentor = universe.get_wrestler_by_id(mentor_id)
        mentee = universe.get_wrestler_by_id(mentee_id)

        if not mentor:
            return jsonify({'error': f'Mentor wrestler {mentor_id} not found'}), 404
        if not mentee:
            return jsonify({'error': f'Mentee wrestler {mentee_id} not found'}), 404

        year, week = _get_game_week(db)
        cooldown = _load_cooldown(db, mentor_id)
        abs_w = _abs_week(year, week)

        from simulation.morale_recovery import RecoveryType
        if not cooldown.can_use(RecoveryType.MENTORSHIP_ROLE, abs_w):
            weeks_left = cooldown.weeks_until_available(RecoveryType.MENTORSHIP_ROLE, abs_w)
            return jsonify({
                'error': f'Mentorship on cooldown for {mentor.name}. Available in {weeks_left} week(s).'
            }), 400

        all_wrestlers = universe.get_active_wrestlers()

        mentor_event, mentee_event = morale_recovery_engine.assign_mentorship(
            mentor=mentor,
            mentee=mentee,
            year=year,
            week=week,
            cooldown=cooldown,
            all_wrestlers=all_wrestlers,
        )

        universe.save_wrestler(mentor)
        if mentee_event:
            universe.save_wrestler(mentee)

        db.save_recovery_event(mentor_event)
        if mentee_event:
            db.save_recovery_event(mentee_event)

        _save_cooldown(db, cooldown)
        db.conn.commit()

        response = {
            'success': True,
            'mentor_event': mentor_event.to_dict(),
            'mentor_new_morale': mentor.morale,
        }
        if mentee_event:
            response['mentee_event'] = mentee_event.to_dict()
            response['mentee_new_morale'] = mentee.morale
        else:
            response['note'] = (
                'Mentee is on a different brand — mentor still gained morale, '
                'but mentee benefit requires same-brand assignment.'
            )

        return jsonify(response)

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================
# GET /api/recovery/history  — All recovery events
# ============================================================

@recovery_bp.route('/api/recovery/history')
def api_recovery_history():
    """Get recent recovery events across the whole roster."""
    try:
        db = get_database()
        wrestler_id = request.args.get('wrestler_id')
        recovery_type = request.args.get('type')
        limit = request.args.get('limit', 50, type=int)

        events = db.get_recovery_events(
            wrestler_id=wrestler_id,
            recovery_type=recovery_type,
            limit=limit,
        )

        return jsonify({
            'total': len(events),
            'events': events,
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================
# GET /api/recovery/wrestler/<id>/history
# ============================================================

@recovery_bp.route('/api/recovery/wrestler/<wrestler_id>/history')
def api_wrestler_recovery_history(wrestler_id):
    """Get all recovery actions taken for a specific wrestler."""
    try:
        db = get_database()

        events = db.get_recovery_events(wrestler_id=wrestler_id, limit=100)
        cooldown_data = db.get_recovery_cooldown(wrestler_id)

        return jsonify({
            'wrestler_id': wrestler_id,
            'total_events': len(events),
            'events': events,
            'cooldowns': json.loads(cooldown_data['last_used_json']) if cooldown_data else {},
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================
# GET /api/recovery/summary  — Roster-wide overview
# ============================================================

@recovery_bp.route('/api/recovery/summary')
def api_recovery_summary():
    """
    Roster-wide recovery summary:
    - Who most needs recovery
    - Which wrestlers are being neglected
    - Recent recovery actions
    - Total money spent on recovery this year
    """
    try:
        universe = get_universe()
        db = get_database()
        year, week = _get_game_week(db)
        abs_w = _abs_week(year, week)

        wrestlers = universe.get_active_wrestlers()

        needs_recovery = []
        neglected = []    # unhappy but no recovery this year
        total_cost = 0

        # Get all events this year
        all_events = db.get_recovery_events(limit=500)
        events_this_year = [e for e in all_events if e.get('game_year') == year]
        wrestler_ids_helped = {e['wrestler_id'] for e in events_this_year}
        total_cost = sum(e.get('cost', 0) for e in events_this_year)

        for w in wrestlers:
            if w.morale <= 55:
                cooldown = _load_cooldown(db, w.id)
                # Check if any recovery available
                available_count = sum(
                    1 for rtype in __import__('simulation.morale_recovery', fromlist=['RecoveryType']).RecoveryType
                    if cooldown.can_use(rtype, abs_w)
                )
                needs_recovery.append({
                    'wrestler_id': w.id,
                    'wrestler_name': w.name,
                    'morale': w.morale,
                    'brand': getattr(w, 'primary_brand', ''),
                    'role': getattr(w, 'role', ''),
                    'available_recoveries': available_count,
                    'helped_this_year': w.id in wrestler_ids_helped,
                })

                if w.morale <= 40 and w.id not in wrestler_ids_helped:
                    neglected.append({
                        'wrestler_id': w.id,
                        'wrestler_name': w.name,
                        'morale': w.morale,
                    })

        needs_recovery.sort(key=lambda x: x['morale'])

        return jsonify({
            'year': year,
            'week': week,
            'summary': {
                'wrestlers_needing_recovery': len(needs_recovery),
                'neglected_wrestlers': len(neglected),
                'total_cost_this_year': total_cost,
                'recovery_actions_this_year': len(events_this_year),
            },
            'needs_recovery': needs_recovery[:15],
            'neglected': neglected,
            'recent_actions': all_events[:10],
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500