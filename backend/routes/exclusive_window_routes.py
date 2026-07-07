"""
Exclusive Negotiating Window Routes (STEP 124)
Handles purchasing and managing exclusive negotiating rights with free agents.
"""

from flask import Blueprint, jsonify, request, current_app
import traceback
from datetime import datetime

exclusive_window_bp = Blueprint('exclusive_window', __name__)


def get_database():
    return current_app.config['DATABASE']


def get_universe():
    return current_app.config['UNIVERSE']


def get_free_agent_pool():
    return current_app.config.get('FREE_AGENT_POOL')


# ============================================================================
# EXCLUSIVE WINDOW PURCHASE & MANAGEMENT
# ============================================================================

@exclusive_window_bp.route('/api/exclusive-windows/calculate-cost/<fa_id>')
def api_calculate_exclusive_window_cost(fa_id):
    """
    Calculate the cost and terms for purchasing an exclusive negotiating window.
    
    Query params:
        - relationship_quality: 0-100 (default 50)
    """
    try:
        free_agent_pool = get_free_agent_pool()
        universe = get_universe()
        
        fa = free_agent_pool.get_free_agent_by_id(fa_id)
        
        if not fa:
            return jsonify({
                'success': False,
                'error': 'Free agent not found'
            }), 404
        
        # Check if already in exclusive window
        if fa.has_active_exclusive_window():
            holder = fa.get_exclusive_window_holder()
            expires = fa.get_exclusive_window_expires()
            
            return jsonify({
                'success': False,
                'error': 'Free agent already in exclusive negotiating window',
                'details': {
                    'holder': getattr(fa, 'exclusive_window_holder_name', 'Unknown'),
                    'expires_year': expires['year'],
                    'expires_week': expires['week']
                }
            }), 400
        
        # Get relationship quality (for now, default to 50)
        relationship_quality = request.args.get('relationship_quality', 50, type=int)
        relationship_quality = max(0, min(100, relationship_quality))
        
        # Calculate cost
        terms = fa.calculate_exclusive_window_cost(
            relationship_quality=relationship_quality,
            current_year=universe.current_year,
            current_week=universe.current_week
        )
        
        return jsonify({
            'success': True,
            'free_agent_id': fa_id,
            'wrestler_name': fa.wrestler_name,
            'terms': terms,
            'current_balance': universe.balance,
            'can_afford': universe.balance >= terms['cost']
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@exclusive_window_bp.route('/api/exclusive-windows/purchase/<fa_id>', methods=['POST'])
def api_purchase_exclusive_window(fa_id):
    """
    Purchase an exclusive negotiating window for a free agent.
    
    Body:
        {
            "relationship_quality": 50  # optional, 0-100
        }
    """
    try:
        database = get_database()
        universe = get_universe()
        free_agent_pool = get_free_agent_pool()
        
        fa = free_agent_pool.get_free_agent_by_id(fa_id)
        
        if not fa:
            return jsonify({
                'success': False,
                'error': 'Free agent not found'
            }), 404
        
        # Check if already in exclusive window
        if fa.has_active_exclusive_window():
            return jsonify({
                'success': False,
                'error': 'Free agent already in exclusive negotiating window'
            }), 400
        
        # Get relationship quality
        data = request.get_json() or {}
        relationship_quality = data.get('relationship_quality', 50)
        relationship_quality = max(0, min(100, relationship_quality))
        
        # Calculate terms
        terms = fa.calculate_exclusive_window_cost(
            relationship_quality=relationship_quality,
            current_year=universe.current_year,
            current_week=universe.current_week
        )
        
        # Check if can afford
        if universe.balance < terms['cost']:
            return jsonify({
                'success': False,
                'error': f"Insufficient funds. Need ${terms['cost']:,}, have ${universe.balance:,}",
                'cost': terms['cost'],
                'balance': universe.balance,
                'shortfall': terms['cost'] - universe.balance
            }), 400
        
        # Deduct cost
        universe.balance -= terms['cost']
        database.update_game_state(balance=universe.balance)
        
        # Start exclusive window
        window_id = fa.start_exclusive_window(
            promotion_id='player',  # Player's promotion
            promotion_name='Ring of Champions',
            cost_paid=terms['cost'],
            duration_days=terms['duration_days'],
            started_year=universe.current_year,
            started_week=universe.current_week,
            expires_year=terms['expires_year'],
            expires_week=terms['expires_week']
        )
        
        # Save to database
        from persistence.exclusive_window_db import save_exclusive_window, record_window_event
        
        window_data = {
            'id': window_id,
            'free_agent_id': fa.id,
            'wrestler_name': fa.wrestler_name,
            'promotion_id': 'player',
            'promotion_name': 'Ring of Champions',
            'cost_paid': terms['cost'],
            'duration_days': terms['duration_days'],
            'started_year': universe.current_year,
            'started_week': universe.current_week,
            'expires_year': terms['expires_year'],
            'expires_week': terms['expires_week'],
            'refund_eligible': terms['refund_eligible'],
            'refund_percentage': terms['refund_percentage'],
            'negotiation_status': 'active',
            'created_at': datetime.now().isoformat()
        }
        
        save_exclusive_window(database, window_data)
        
        # Record event
        record_window_event(
            database,
            window_id,
            'purchased',
            f"Purchased exclusive negotiating rights for ${terms['cost']:,}",
            universe.current_year,
            universe.current_week
        )
        
        # Save free agent
        free_agent_pool.save_free_agent(fa)
        
        # Commit all changes
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'message': f"Secured exclusive negotiating rights to {fa.wrestler_name}!",
            'window_id': window_id,
            'free_agent': fa.to_dict(),
            'terms': terms,
            'new_balance': universe.balance,
            'cost_paid': terms['cost']
        })
        
    except Exception as e:
        database.conn.rollback()
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@exclusive_window_bp.route('/api/exclusive-windows/active')
def api_get_active_exclusive_windows():
    """Get all active exclusive windows for the player"""
    try:
        database = get_database()
        free_agent_pool = get_free_agent_pool()
        
        from persistence.exclusive_window_db import get_promotion_exclusive_windows
        
        windows = get_promotion_exclusive_windows(
            database,
            'player',
            active_only=True
        )
        
        # Enrich with free agent data
        enriched_windows = []
        for window in windows:
            fa = free_agent_pool.get_free_agent_by_id(window['free_agent_id'])
            
            enriched_window = {
                **window,
                'free_agent': fa.to_dict() if fa else None,
                'days_remaining': calculate_days_remaining(window),
                'is_expired': is_window_expired(window)
            }
            
            enriched_windows.append(enriched_window)
        
        return jsonify({
            'success': True,
            'total': len(enriched_windows),
            'windows': enriched_windows
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@exclusive_window_bp.route('/api/exclusive-windows/<window_id>')
def api_get_exclusive_window_details(window_id):
    """Get details of a specific exclusive window"""
    try:
        database = get_database()
        free_agent_pool = get_free_agent_pool()
        
        from persistence.exclusive_window_db import get_active_exclusive_window, get_window_events
        
        cursor = database.conn.cursor()
        cursor.execute('SELECT * FROM exclusive_windows WHERE id = ?', (window_id,))
        window_row = cursor.fetchone()
        
        if not window_row:
            return jsonify({
                'success': False,
                'error': 'Window not found'
            }), 404
        
        window = dict(window_row)
        
        # Get free agent
        fa = free_agent_pool.get_free_agent_by_id(window['free_agent_id'])
        
        # Get events
        events = get_window_events(database, window_id)
        
        return jsonify({
            'success': True,
            'window': window,
            'free_agent': fa.to_dict() if fa else None,
            'events': events,
            'days_remaining': calculate_days_remaining(window),
            'is_expired': is_window_expired(window)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@exclusive_window_bp.route('/api/exclusive-windows/<window_id>/make-offer', methods=['POST'])
def api_make_offer_during_window(window_id):
    """
    Make a contract offer during an exclusive window.
    
    Body:
        {
            "salary": 10000,
            "length_weeks": 52,
            "signing_bonus": 5000,
            ...other contract terms
        }
    """
    try:
        database = get_database()
        universe = get_universe()
        free_agent_pool = get_free_agent_pool()
        
        # Get window
        cursor = database.conn.cursor()
        cursor.execute('SELECT * FROM exclusive_windows WHERE id = ?', (window_id,))
        window_row = cursor.fetchone()
        
        if not window_row:
            return jsonify({
                'success': False,
                'error': 'Window not found'
            }), 404
        
        window = dict(window_row)
        
        # Verify window is active
        if not window['is_active']:
            return jsonify({
                'success': False,
                'error': 'Window is no longer active'
            }), 400
        
        # Verify not expired
        if is_window_expired(window):
            return jsonify({
                'success': False,
                'error': 'Window has expired'
            }), 400
        
        # Get free agent
        fa = free_agent_pool.get_free_agent_by_id(window['free_agent_id'])
        
        if not fa:
            return jsonify({
                'success': False,
                'error': 'Free agent not found'
            }), 404
        
        # Get offer details
        offer_data = request.get_json()
        
        # Update window with offer
        cursor.execute('''
            UPDATE exclusive_windows
            SET offers_made = offers_made + 1,
                last_offer_amount = ?
            WHERE id = ?
        ''', (offer_data.get('salary', 0), window_id))
        
        # Record event
        from persistence.exclusive_window_db import record_window_event
        
        record_window_event(
            database,
            window_id,
            'offer_made',
            f"Offered ${offer_data.get('salary', 0):,}/show for {offer_data.get('length_weeks', 52)} weeks",
            universe.current_year,
            universe.current_week
        )
        
        database.conn.commit()
        
        # For now, just return success
        # Full negotiation system will be implemented in later steps
        return jsonify({
            'success': True,
            'message': f"Offer made to {fa.wrestler_name}",
            'offer': offer_data,
            'window_id': window_id
        })
        
    except Exception as e:
        database.conn.rollback()
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@exclusive_window_bp.route('/api/exclusive-windows/<window_id>/cancel', methods=['POST'])
def api_cancel_exclusive_window(window_id):
    """Cancel an exclusive window early (forfeit payment)"""
    try:
        database = get_database()
        free_agent_pool = get_free_agent_pool()
        
        # Get window
        cursor = database.conn.cursor()
        cursor.execute('SELECT * FROM exclusive_windows WHERE id = ?', (window_id,))
        window_row = cursor.fetchone()
        
        if not window_row:
            return jsonify({
                'success': False,
                'error': 'Window not found'
            }), 404
        
        window = dict(window_row)
        
        if not window['is_active']:
            return jsonify({
                'success': False,
                'error': 'Window is already inactive'
            }), 400
        
        # Get free agent
        fa = free_agent_pool.get_free_agent_by_id(window['free_agent_id'])
        
        # End window
        from persistence.exclusive_window_db import expire_exclusive_window, record_window_event
        
        expire_exclusive_window(database, window_id, resulted_in_signing=False, refund_amount=0)
        
        record_window_event(
            database,
            window_id,
            'cancelled',
            'Window cancelled by promotion',
            None,
            None
        )
        
        # End on free agent
        if fa:
            fa.end_exclusive_window(resulted_in_signing=False)
            free_agent_pool.save_free_agent(fa)
        
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'message': f"Cancelled exclusive window for {window['wrestler_name']}",
            'refund': 0  # No refund for cancellation
        })
        
    except Exception as e:
        database.conn.rollback()
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


# ============================================================================
# WEEKLY PROCESSING
# ============================================================================

@exclusive_window_bp.route('/api/exclusive-windows/process-expirations', methods=['POST'])
def api_process_window_expirations():
    """
    Process expired exclusive windows (called during week advancement).
    Internal use only.
    """
    try:
        database = get_database()
        universe = get_universe()
        free_agent_pool = get_free_agent_pool()
        
        from persistence.exclusive_window_db import check_expired_windows, expire_exclusive_window, record_window_event
        
        # Find expired windows
        expired_windows = check_expired_windows(
            database,
            universe.current_year,
            universe.current_week
        )
        
        results = []
        
        for window in expired_windows:
            # Calculate refund if eligible
            refund_amount = 0
            if window['refund_eligible']:
                refund_amount = int(window['cost_paid'] * (window['refund_percentage'] / 100))
                universe.balance += refund_amount
            
            # Expire window
            expire_exclusive_window(
                database,
                window['id'],
                resulted_in_signing=False,
                refund_amount=refund_amount
            )
            
            # Record event
            record_window_event(
                database,
                window['id'],
                'expired',
                f"Window expired naturally" + (f" - Refund: ${refund_amount:,}" if refund_amount > 0 else ""),
                universe.current_year,
                universe.current_week
            )
            
            # End on free agent
            fa = free_agent_pool.get_free_agent_by_id(window['free_agent_id'])
            if fa:
                fa.end_exclusive_window(resulted_in_signing=False)
                free_agent_pool.save_free_agent(fa)
            
            results.append({
                'window_id': window['id'],
                'wrestler_name': window['wrestler_name'],
                'refund': refund_amount,
                'cost_paid': window['cost_paid']
            })
        
        if results:
            database.update_game_state(balance=universe.balance)
        
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'expired_count': len(results),
            'expired_windows': results,
            'total_refunds': sum(r['refund'] for r in results)
        })
        
    except Exception as e:
        database.conn.rollback()
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_days_remaining(window: dict) -> int:
    """Calculate days remaining in window"""
    # Simplified - just use weeks
    # In reality would need proper date calculation
    started = window['started_week']
    expires = window['expires_week']
    return max(0, (expires - started) * 7)


def is_window_expired(window: dict) -> bool:
    """Check if window is expired (based on current game time)"""
    universe = get_universe()
    
    if universe.current_year > window['expires_year']:
        return True
    elif universe.current_year == window['expires_year']:
        return universe.current_week >= window['expires_week']
    
    return False