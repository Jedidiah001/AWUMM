"""
Alert Routes - Contract Expiration Alert Management
STEP 120: Expiration Alert System
"""

from flask import Blueprint, jsonify, request, current_app
from models.contract_alert import contract_alert_manager, AlertType, AlertPriority
from economy.contracts import contract_manager

alert_bp = Blueprint('alerts', __name__)


def get_database():
    return current_app.config['DATABASE']


def get_universe():
    return current_app.config['UNIVERSE']


# ========================================================================
# STEP 120: Contract Alert Endpoints
# ========================================================================

@alert_bp.route('/api/alerts/contracts')
def api_get_contract_alerts():
    """
    Get all active contract expiration alerts.
    
    Query params:
    - unacknowledged_only: bool - Only return unacknowledged alerts
    - priority: str - Filter by priority (urgent, high, medium, low)
    - type: str - Filter by type (critical, warning, planning, expired)
    """
    try:
        unacknowledged_only = request.args.get('unacknowledged_only', 'false').lower() == 'true'
        priority_filter = request.args.get('priority', '').lower()
        type_filter = request.args.get('type', '').lower()
        
        # Get alerts
        if unacknowledged_only:
            alerts = contract_alert_manager.get_unacknowledged_alerts()
        else:
            alerts = contract_alert_manager.get_active_alerts()
        
        # Apply filters
        if priority_filter:
            priority_map = {
                'urgent': AlertPriority.URGENT,
                'high': AlertPriority.HIGH,
                'medium': AlertPriority.MEDIUM,
                'low': AlertPriority.LOW
            }
            if priority_filter in priority_map:
                alerts = [a for a in alerts if a.priority == priority_map[priority_filter]]
        
        if type_filter:
            type_map = {
                'critical': AlertType.CRITICAL,
                'warning': AlertType.WARNING,
                'planning': AlertType.PLANNING,
                'expired': AlertType.CONTRACT_EXPIRED
            }
            if type_filter in type_map:
                alerts = [a for a in alerts if a.alert_type == type_map[type_filter]]
        
        # Sort by priority (urgent first), then by weeks remaining
        alerts.sort(key=lambda a: (a.priority.value, a.weeks_remaining))
        
        return jsonify({
            'total': len(alerts),
            'alerts': [alert.to_dict() for alert in alerts]
        })
    
    except Exception as e:
        print(f"Error in /api/alerts/contracts: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@alert_bp.route('/api/alerts/contracts/summary')
def api_get_alert_summary():
    """
    Get summary of contract alerts.
    
    Returns counts by priority and type, plus action required count.
    """
    try:
        summary = contract_alert_manager.get_alert_summary()
        return jsonify(summary)
    
    except Exception as e:
        print(f"Error in /api/alerts/contracts/summary: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@alert_bp.route('/api/alerts/contracts/generate', methods=['POST'])
def api_generate_contract_alerts():
    """
    Manually trigger contract alert generation.
    
    Usually called automatically during show simulation, but can be
    triggered manually to refresh alerts.
    """
    try:
        universe = get_universe()
        game_state = get_database().get_game_state()
        
        alerts = contract_manager.generate_alerts_for_contracts(
            wrestlers=universe.get_active_wrestlers(),
            current_week=game_state['current_week'],
            current_year=game_state['current_year']
        )
        
        return jsonify({
            'success': True,
            'alerts_generated': len(alerts),
            'alerts': [alert.to_dict() for alert in alerts]
        })
    
    except Exception as e:
        print(f"Error in /api/alerts/contracts/generate: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@alert_bp.route('/api/alerts/contracts/<alert_id>/acknowledge', methods=['POST'])
def api_acknowledge_alert(alert_id):
    """
    Acknowledge a specific alert.
    
    Marks the alert as seen/acknowledged but keeps it active.
    """
    try:
        game_state = get_database().get_game_state()
        
        success = contract_alert_manager.acknowledge_alert(
            alert_id=alert_id,
            current_week=game_state['current_week'],
            current_year=game_state['current_year']
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Alert {alert_id} acknowledged'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Alert not found'
            }), 404
    
    except Exception as e:
        print(f"Error in acknowledge alert: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@alert_bp.route('/api/alerts/contracts/<alert_id>/dismiss', methods=['POST'])
def api_dismiss_alert(alert_id):
    """
    Dismiss a specific alert.
    
    Removes the alert from active view (soft delete).
    """
    try:
        success = contract_alert_manager.dismiss_alert(alert_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Alert {alert_id} dismissed'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Alert not found'
            }), 404
    
    except Exception as e:
        print(f"Error in dismiss alert: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@alert_bp.route('/api/alerts/contracts/acknowledge-all', methods=['POST'])
def api_acknowledge_all_alerts():
    """
    Acknowledge all active alerts at once.
    """
    try:
        game_state = get_database().get_game_state()
        
        contract_alert_manager.acknowledge_all(
            current_week=game_state['current_week'],
            current_year=game_state['current_year']
        )
        
        return jsonify({
            'success': True,
            'message': 'All alerts acknowledged'
        })
    
    except Exception as e:
        print(f"Error in acknowledge all: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@alert_bp.route('/api/alerts/contracts/cleanup', methods=['POST'])
def api_cleanup_old_alerts():
    """
    Clean up old dismissed/acknowledged alerts.
    
    Removes alerts older than specified threshold (default 52 weeks).
    """
    try:
        game_state = get_database().get_game_state()
        weeks_threshold = request.args.get('weeks', 52, type=int)
        
        removed = contract_alert_manager.cleanup_expired_alerts(
            current_week=game_state['current_week'],
            current_year=game_state['current_year'],
            weeks_threshold=weeks_threshold
        )
        
        return jsonify({
            'success': True,
            'alerts_removed': removed,
            'message': f'Removed {removed} old alerts'
        })
    
    except Exception as e:
        print(f"Error in cleanup: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500