"""
Early Renewal Routes
STEP 121: Early Renewal Window
"""

from flask import Blueprint, jsonify, request, current_app
from economy.early_renewal import early_renewal_calculator
from economy.contracts import contract_manager
from typing import Optional

renewal_bp = Blueprint('renewal', __name__)


def get_database():
    return current_app.config['DATABASE']


def get_universe():
    return current_app.config['UNIVERSE']


@renewal_bp.route('/api/contracts/<wrestler_id>/renewal-probability', methods=['POST'])
def api_calculate_renewal_probability(wrestler_id):
    """
    Calculate the probability of a wrestler accepting an early renewal offer.
    
    POST body:
    {
        "salary_per_show": int,
        "weeks": int,
        "signing_bonus": int (optional),
        "title_promise": bool (optional),
        "brand_transfer": str (optional)
    }
    """
    try:
        universe = get_universe()
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        data = request.get_json()
        offered_salary = data.get('salary_per_show', wrestler.contract.salary_per_show)
        offered_weeks = data.get('weeks', 52)
        signing_bonus = data.get('signing_bonus', 0)
        title_promise = data.get('title_promise', False)
        brand_transfer = data.get('brand_transfer')
        
        # Calculate market value
        market_value = contract_manager.calculate_market_value(wrestler)
        
        # Calculate probability
        include_incentives = signing_bonus > 0 or title_promise or brand_transfer is not None
        probability_data = early_renewal_calculator.calculate_renewal_probability(
            wrestler=wrestler,
            offered_salary=offered_salary,
            offered_weeks=offered_weeks,
            market_value=market_value,
            include_incentives=include_incentives
        )
        
        # Add wrestler info
        probability_data['wrestler'] = {
            'id': wrestler.id,
            'name': wrestler.name,
            'current_salary': wrestler.contract.salary_per_show,
            'weeks_remaining': wrestler.contract.weeks_remaining,
            'morale': wrestler.morale,
            'popularity': wrestler.popularity,
            'role': wrestler.role
        }
        
        return jsonify(probability_data)
    
    except Exception as e:
        print(f"Error calculating renewal probability: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@renewal_bp.route('/api/contracts/<wrestler_id>/early-renewal', methods=['POST'])
def api_attempt_early_renewal(wrestler_id):
    """
    Attempt to renew a wrestler's contract early.
    
    POST body:
    {
        "salary_per_show": int,
        "weeks": int,
        "signing_bonus": int (optional),
        "title_promise": bool (optional),
        "brand_transfer": str (optional)
    }
    """
    try:
        universe = get_universe()
        database = get_database()
        game_state = database.get_game_state()
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        data = request.get_json()
        offered_salary = data.get('salary_per_show')
        offered_weeks = data.get('weeks', 52)
        signing_bonus = data.get('signing_bonus', 0)
        title_promise = data.get('title_promise', False)
        brand_transfer = data.get('brand_transfer')
        
        if not offered_salary:
            return jsonify({'error': 'salary_per_show is required'}), 400
        
        # Check if can afford signing bonus
        if signing_bonus > universe.balance:
            return jsonify({
                'error': f'Cannot afford signing bonus. Balance: ${universe.balance:,}, Bonus: ${signing_bonus:,}'
            }), 400
        
        # Calculate market value
        market_value = contract_manager.calculate_market_value(wrestler)
        
        # Attempt renewal
        success, message, details = early_renewal_calculator.attempt_early_renewal(
            wrestler=wrestler,
            offered_salary=offered_salary,
            offered_weeks=offered_weeks,
            market_value=market_value,
            signing_bonus=signing_bonus,
            title_promise=title_promise,
            brand_transfer=brand_transfer,
            current_week=game_state['current_week'],
            current_year=game_state['current_year']
        )
        
        if success:
            # Deduct signing bonus from balance
            if signing_bonus > 0:
                universe.balance -= signing_bonus
                # Use the database's direct SQL update for balance
                cursor = database.conn.cursor()
                cursor.execute(
                    'UPDATE game_state SET balance = ? WHERE id = 1',
                    (universe.balance,)
                )
            
            # Save wrestler
            universe.save_wrestler(wrestler)
            database.conn.commit()
        
        return jsonify({
            'success': success,
            'message': message,
            'details': details,
            'wrestler': wrestler.to_dict() if success else None
        })
    
    except Exception as e:
        print(f"Error attempting early renewal: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@renewal_bp.route('/api/contracts/<wrestler_id>/renewal-status')
def api_get_renewal_status(wrestler_id):
    """
    Get renewal status and history for a wrestler.
    """
    try:
        universe = get_universe()
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        market_value = contract_manager.calculate_market_value(wrestler)
        
        # Check if eligible for early renewal
        eligible = wrestler.contract.weeks_remaining <= 52  # Can renew in last year
        
        # Calculate recommended offer
        recommended_salary = int(market_value * 1.1)  # 110% of market value for early renewal
        recommended_weeks = 52 if wrestler.contract.weeks_remaining <= 26 else 104
        
        return jsonify({
            'wrestler_id': wrestler.id,
            'wrestler_name': wrestler.name,
            'current_contract': {
                'salary_per_show': wrestler.contract.salary_per_show,
                'weeks_remaining': wrestler.contract.weeks_remaining,
                'total_length_weeks': wrestler.contract.total_length_weeks
            },
            'market_value': market_value,
            'eligible_for_early_renewal': eligible,
            'early_renewal_offered': wrestler.contract.early_renewal_offered,
            'renewal_attempts': wrestler.contract.renewal_attempts,
            'last_attempt': {
                'week': wrestler.contract.last_renewal_attempt_week,
                'year': wrestler.contract.last_renewal_attempt_year
            } if wrestler.contract.last_renewal_attempt_week else None,
            'recommended_offer': {
                'salary_per_show': recommended_salary,
                'weeks': recommended_weeks,
                'rationale': 'Based on market value + early renewal premium'
            },
            'wrestler_status': {
                'morale': wrestler.morale,
                'popularity': wrestler.popularity,
                'role': wrestler.role,
                'age': wrestler.age
            }
        })
    
    except Exception as e:
        print(f"Error getting renewal status: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500