"""
API endpoints for Championship Reign Goals

STEP 30: Reign goal tracking and satisfaction
"""

from flask import Blueprint, jsonify, request
from persistence.reign_goal_db import (
    get_active_reign_goals,
    get_wrestler_reign_history,
    get_unfulfilled_title_promises,
    save_contract_title_promise,
    check_promise_expiration
)
from models.reign_goal import ReignGoalPreset

reign_goals_bp = Blueprint('reign_goals', __name__)


@reign_goals_bp.route('/api/wrestlers/<wrestler_id>/reign-goals', methods=['GET'])
def get_wrestler_reign_goals(wrestler_id):
    """Get active reign goals for a wrestler."""
    from app import universe
    
    try:
        goals = get_active_reign_goals(universe.db, wrestler_id)
        
        return jsonify({
            'success': True,
            'wrestler_id': wrestler_id,
            'active_goals': goals,
            'total_goals': len(goals)
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reign_goals_bp.route('/api/wrestlers/<wrestler_id>/reign-history', methods=['GET'])
def get_wrestler_reign_satisfaction_history(wrestler_id):
    """Get reign satisfaction history for a wrestler."""
    from app import universe
    
    try:
        limit = request.args.get('limit', 10, type=int)
        history = get_wrestler_reign_history(universe.db, wrestler_id, limit)
        
        # Calculate averages
        if history:
            avg_satisfaction = sum(h['total_satisfaction'] for h in history) / len(history)
            avg_morale_change = sum(h['morale_change'] for h in history) / len(history)
            total_goals_met = sum(h['goals_met'] for h in history)
            total_goals_failed = sum(h['goals_failed'] for h in history)
        else:
            avg_satisfaction = 0
            avg_morale_change = 0
            total_goals_met = 0
            total_goals_failed = 0
        
        return jsonify({
            'success': True,
            'wrestler_id': wrestler_id,
            'history': history,
            'statistics': {
                'total_reigns': len(history),
                'avg_satisfaction': round(avg_satisfaction, 1),
                'avg_morale_change': round(avg_morale_change, 1),
                'total_goals_met': total_goals_met,
                'total_goals_failed': total_goals_failed,
                'success_rate': round((total_goals_met / (total_goals_met + total_goals_failed) * 100), 1) if (total_goals_met + total_goals_failed) > 0 else 0
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reign_goals_bp.route('/api/wrestlers/<wrestler_id>/title-promises', methods=['GET'])
def get_wrestler_title_promises(wrestler_id):
    """Get unfulfilled title promises for a wrestler."""
    from app import universe
    
    try:
        promises = get_unfulfilled_title_promises(universe.db, wrestler_id)
        
        return jsonify({
            'success': True,
            'wrestler_id': wrestler_id,
            'unfulfilled_promises': promises,
            'total_promises': len(promises)
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reign_goals_bp.route('/api/wrestlers/<wrestler_id>/promise-title-run', methods=['POST'])
def promise_title_run(wrestler_id):
    """
    Promise a wrestler a specific title run (contract negotiation).
    
    Request body:
    {
        "title_id": "title_world" (optional, can specify tier instead),
        "title_tier": "World" (optional, if title_id not specified),
        "promised_min_days": 60,
        "promised_min_defenses": 3,
        "expires_weeks": 52 (optional, promise expires after X weeks)
    }
    """
    from app import universe
    
    try:
        data = request.get_json()
        
        # Validate
        if 'promised_min_days' not in data or 'promised_min_defenses' not in data:
            return jsonify({
                'success': False,
                'error': 'Must specify promised_min_days and promised_min_defenses'
            }), 400
        
        if not data.get('title_id') and not data.get('title_tier'):
            return jsonify({
                'success': False,
                'error': 'Must specify either title_id or title_tier'
            }), 400
        
        # Get wrestler
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'success': False, 'error': 'Wrestler not found'}), 404
        
        # Calculate expiration
        expires_year = None
        expires_week = None
        if data.get('expires_weeks'):
            weeks_to_add = data['expires_weeks']
            expires_year = universe.current_year + (universe.current_week + weeks_to_add) // 52
            expires_week = (universe.current_week + weeks_to_add) % 52
        
        # Create promise
        promise_data = {
            'wrestler_id': wrestler_id,
            'title_id': data.get('title_id'),
            'title_tier': data.get('title_tier'),
            'promised_min_days': data['promised_min_days'],
            'promised_min_defenses': data['promised_min_defenses'],
            'promise_year': universe.current_year,
            'promise_week': universe.current_week,
            'expires_year': expires_year,
            'expires_week': expires_week
        }
        
        save_contract_title_promise(universe.db, promise_data)
        universe.db.conn.commit()
        
        # Morale boost for being promised a title run
        wrestler.adjust_morale(15)
        universe.save_wrestler(wrestler)
        universe.db.conn.commit()
        
        title_desc = data.get('title_id', data.get('title_tier', 'championship'))
        
        return jsonify({
            'success': True,
            'message': f"{wrestler.name} has been promised a {title_desc} run ({data['promised_min_days']} days, {data['promised_min_defenses']} defenses)",
            'promise': promise_data,
            'morale_boost': 15
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reign_goals_bp.route('/api/title-promises/check-expirations', methods=['GET'])
def check_title_promise_expirations():
    """Check for expired unfulfilled title promises."""
    from app import universe
    
    try:
        expired = check_promise_expiration(
            universe.db,
            universe.current_year,
            universe.current_week
        )
        
        # Apply morale penalties for broken promises
        penalties_applied = []
        
        for promise in expired:
            wrestler = universe.get_wrestler_by_id(promise['wrestler_id'])
            if wrestler:
                morale_penalty = -20
                wrestler.adjust_morale(morale_penalty)
                universe.save_wrestler(wrestler)
                
                penalties_applied.append({
                    'wrestler_id': wrestler.id,
                    'wrestler_name': wrestler.name,
                    'promise': promise,
                    'morale_penalty': morale_penalty
                })
        
        if penalties_applied:
            universe.db.conn.commit()
        
        return jsonify({
            'success': True,
            'expired_promises': expired,
            'penalties_applied': penalties_applied,
            'total_expired': len(expired)
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reign_goals_bp.route('/api/championships/<title_id>/reign-goals-preview', methods=['POST'])
def preview_reign_goals(title_id):
    """
    Preview what reign goals would be created for a wrestler winning this title.
    
    Request body:
    {
        "wrestler_id": "w001"
    }
    """
    from app import universe
    
    try:
        data = request.get_json()
        wrestler_id = data.get('wrestler_id')
        
        if not wrestler_id:
            return jsonify({'success': False, 'error': 'wrestler_id required'}), 400
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        championship = universe.get_championship_by_id(title_id)
        
        if not wrestler:
            return jsonify({'success': False, 'error': 'Wrestler not found'}), 404
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        # Check for contract promises
        promises = get_unfulfilled_title_promises(universe.db, wrestler_id)
        matching_promise = None
        
        for promise in promises:
            if (promise.get('title_id') == title_id or 
                promise.get('title_tier') == championship.title_type):
                matching_promise = promise
                break
        
        # Generate preview goals
        if matching_promise:
            goals = ReignGoalPreset.create_promised_reign(
                days=matching_promise['promised_min_days'],
                defenses=matching_promise['promised_min_defenses']
            )
            source = 'contract_promise'
        else:
            goals = ReignGoalPreset.get_default_goals_for_role(
                role=wrestler.role,
                title_tier=championship.title_type
            )
            source = 'default_for_role'
        
        # Check for record-breaking goal
        cursor = universe.db.conn.cursor()
        cursor.execute('''
            SELECT MAX(days_held) as longest
            FROM title_reigns
            WHERE title_id = ?
        ''', (title_id,))
        
        result = cursor.fetchone()
        longest_reign = result['longest'] if result and result['longest'] else 0
        
        will_pursue_record = (
            wrestler.is_major_superstar and 
            championship.title_type == 'World' and 
            longest_reign > 60
        )
        
        if will_pursue_record:
            record_goal = ReignGoalPreset.create_record_breaking_reign(longest_reign)
            goals.append(record_goal)
        
        return jsonify({
            'success': True,
            'wrestler': {
                'id': wrestler.id,
                'name': wrestler.name,
                'role': wrestler.role
            },
            'championship': {
                'id': championship.id,
                'name': championship.name,
                'title_type': championship.title_type
            },
            'preview': {
                'source': source,
                'total_goals': len(goals),
                'goals': [g.to_dict() for g in goals],
                'has_contract_promise': matching_promise is not None,
                'will_pursue_record': will_pursue_record,
                'current_record_days': longest_reign if will_pursue_record else None
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reign_goals_bp.route('/api/title-promises/all', methods=['GET'])
def get_all_title_promises():
    """Get all unfulfilled title promises across all wrestlers."""
    from app import universe
    
    try:
        promises = get_unfulfilled_title_promises(universe.db)
        
        # Group by urgency
        urgent = []  # Expiring soon
        normal = []
        
        for promise in promises:
            if promise.get('expires_year'):
                weeks_remaining = (
                    (promise['expires_year'] - universe.current_year) * 52 +
                    (promise['expires_week'] - universe.current_week)
                )
                
                if weeks_remaining <= 8:
                    urgent.append({**promise, 'weeks_remaining': weeks_remaining})
                else:
                    normal.append({**promise, 'weeks_remaining': weeks_remaining})
            else:
                normal.append({**promise, 'weeks_remaining': None})
        
        return jsonify({
            'success': True,
            'all_promises': promises,
            'urgent_promises': urgent,
            'normal_promises': normal,
            'total_promises': len(promises),
            'urgent_count': len(urgent)
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500