"""
Contract Routes - Contract Management
STEP 119: Enhanced with Contract Countdown Tracking endpoints
STEP 121: Enhanced early renewal with full incentive support
STEP 122: Enhanced with Contract Incentive endpoints
"""

import random
from flask import Blueprint, jsonify, request, current_app
from economy.contracts import contract_manager
from datetime import datetime
from typing import List, Dict, Any, Optional

contract_bp = Blueprint('contract', __name__)


def get_database():
    return current_app.config['DATABASE']


def get_universe():
    return current_app.config['UNIVERSE']


def get_contract_roster():
    """Contract workflows should include injured talent with active deals."""
    universe = get_universe()
    if not universe:
        return []
    return [
        wrestler for wrestler in universe.wrestlers
        if not wrestler.is_retired and getattr(wrestler, 'contract', None)
    ]


def _contract_weeks_remaining(wrestler):
    """Normalize nullable contract timelines for alert/report code paths."""
    return contract_manager._get_contract_weeks(wrestler)


@contract_bp.route('/api/contracts/expiring')
def api_get_expiring_contracts():
    universe = get_universe()
    weeks_threshold = request.args.get('weeks', 4, type=int)
    
    expiring = contract_manager.get_expiring_contracts(
        get_contract_roster(),
        weeks_threshold
    )
    
    return jsonify({
        'total': len(expiring),
        'threshold_weeks': weeks_threshold,
        'wrestlers': [w.to_dict() for w in expiring]
    })


@contract_bp.route('/api/contracts/expired')
def api_get_expired_contracts():
    universe = get_universe()
    expired = contract_manager.get_expired_contracts(universe.wrestlers)
    
    return jsonify({
        'total': len(expired),
        'wrestlers': [w.to_dict() for w in expired]
    })


# ========================================================================
# STEP 119: Contract Countdown Tracking Endpoints
# ========================================================================

@contract_bp.route('/api/contracts/countdown')
def api_get_contract_countdown():
    """
    STEP 119: Get all wrestlers categorized by contract expiration timeline.
    
    Returns:
    {
        "critical": [...],      // <= 4 weeks
        "negotiate_soon": [...], // 5-13 weeks  
        "monitor": [...],       // 14-26 weeks
        "secure": [...],        // > 26 weeks
        "expired": [...]        // 0 weeks
    }
    """
    try:
        universe = get_universe()
        categories = contract_manager.get_contract_countdown_categories(
            get_contract_roster()
        )
        
        # Convert to dict format for JSON
        result = {}
        for category, wrestlers in categories.items():
            result[category] = [w.to_dict() for w in wrestlers]
        
        return jsonify(result)
    
    except Exception as e:
        print(f"Error in /api/contracts/countdown: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@contract_bp.route('/api/contracts/countdown/summary')
def api_get_contract_countdown_summary():
    """
    STEP 119: Get summary statistics for contract statuses.
    
    Returns counts and percentages for each category.
    """
    try:
        universe = get_universe()
        summary = contract_manager.get_contract_status_summary(
            get_contract_roster()
        )
        
        # Convert wrestler objects to serializable format
        serialized_summary = {
            'total_active_contracts': summary['total_active_contracts'],
            'requires_immediate_action': summary['requires_immediate_action'],
            'requires_planning': summary['requires_planning'],
            'categories': {}
        }
        
        for category, data in summary['categories'].items():
            serialized_summary['categories'][category] = {
                'count': data['count'],
                'percentage': data['percentage'],
                'wrestlers': [w.to_dict() for w in data['wrestlers']]
            }
        
        return jsonify(serialized_summary)
    
    except Exception as e:
        print(f"Error in /api/contracts/countdown/summary: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@contract_bp.route('/api/contracts/timeline')
def api_get_contract_timeline():
    """
    STEP 119: Get detailed timeline report for all contracts.
    
    Returns sorted list of contract details with urgency indicators.
    """
    try:
        universe = get_universe()
        report = contract_manager.get_contract_timeline_report(
            get_contract_roster()
        )
        
        return jsonify({
            'total': len(report),
            'contracts': report
        })
    
    except Exception as e:
        print(f"Error in /api/contracts/timeline: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ========================================================================
# STEP 121: Early Renewal with Full Incentive Support
# ========================================================================

@contract_bp.route('/api/contracts/<wrestler_id>/early-renewal', methods=['POST'])
def api_early_renewal_contract(wrestler_id):
    """
    STEP 121: Enhanced early renewal with full incentive support.
    """
    try:
        universe = get_universe()
        database = get_database()
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        data = request.get_json()
        base_salary = data.get('salary_per_show')
        contract_weeks = data.get('weeks', 52)
        signing_bonus = data.get('signing_bonus', 0)
        title_promise = data.get('title_promise', False)
        brand_transfer = data.get('brand_transfer')
        
        # Validate inputs
        if not base_salary or base_salary < 5000:
            return jsonify({'error': 'Invalid salary'}), 400
        
        # Check if can afford signing bonus
        state = database.get_game_state()
        if signing_bonus > state['balance']:
            return jsonify({'error': f'Cannot afford signing bonus. Balance: ${state["balance"]:,}'}), 400
        
        # Calculate acceptance probability
        prob_data = contract_manager.calculate_early_renewal_probability(
            wrestler,
            base_salary,
            contract_weeks,
            signing_bonus,
            title_promise,
            brand_transfer
        )
        
        # Roll for acceptance
        random_roll = random.random() * 100
        accepted = random_roll <= prob_data['final_probability']
        
        if accepted:
            # Update contract
            wrestler.contract.salary_per_show = base_salary
            wrestler.contract.base_salary = base_salary
            wrestler.contract.current_escalated_salary = base_salary
            wrestler.contract.weeks_remaining += contract_weeks
            wrestler.contract.total_length_weeks += contract_weeks
            
            # Mark early renewal
            wrestler.contract.early_renewal_offered = True
            wrestler.contract.early_renewal_year = state['current_year']
            wrestler.contract.early_renewal_week = state['current_week']
            wrestler.contract.renewal_attempts += 1
            wrestler.contract.last_renewal_attempt_year = state['current_year']
            wrestler.contract.last_renewal_attempt_week = state['current_week']
            
            # Deduct signing bonus
            if signing_bonus > 0:
                universe.balance -= signing_bonus
                database.update_game_state(balance=universe.balance)
            
            # Apply brand transfer if promised
            if brand_transfer and brand_transfer != wrestler.primary_brand:
                old_brand = wrestler.primary_brand
                wrestler.primary_brand = brand_transfer
                brand_change_msg = f"\n🔄 Brand Transfer: {old_brand} → {brand_transfer}"
            else:
                brand_change_msg = ""
            
            # Morale boost based on deal quality
            if prob_data['final_probability'] >= 80:
                wrestler.adjust_morale(15)
                morale_msg = "+15 morale (excellent deal)"
            elif prob_data['final_probability'] >= 60:
                wrestler.adjust_morale(10)
                morale_msg = "+10 morale (good deal)"
            else:
                wrestler.adjust_morale(5)
                morale_msg = "+5 morale (acceptable deal)"
            
            # Save everything
            universe.save_wrestler(wrestler)
            
            # Record promises for tracking
            promises = []
            if title_promise:
                promises.append({
                    'type': 'title_shot',
                    'wrestler_id': wrestler_id,
                    'promised_year': state['current_year'],
                    'promised_week': state['current_week'],
                    'deadline_weeks': 26  # 6 months to deliver
                })
            
            # Store promises in a tracking table
            if promises:
                for promise in promises:
                    _save_contract_promise(database, promise)
            
            database.conn.commit()
            
            # Build success message
            message = f"""✅ {wrestler.name} ACCEPTED the early renewal offer!

Contract Details:
• Base Salary: ${base_salary:,}/show
• Length: {contract_weeks} weeks ({contract_weeks // 52} year{'s' if contract_weeks > 52 else ''})
• New Total Weeks: {wrestler.contract.weeks_remaining} weeks
• Signing Bonus: ${signing_bonus:,}
{brand_change_msg}

{morale_msg}

Acceptance Probability: {prob_data['final_probability']}%
Rolled: {random_roll:.1f}

{'🏆 TITLE SHOT PROMISED within 6 months' if title_promise else ''}"""
            
            return jsonify({
                'success': True,
                'accepted': True,
                'message': message,
                'wrestler': wrestler.to_dict(),
                'probability_data': prob_data,
                'promises': promises,
                'new_balance': universe.balance
            })
        
        else:
            # Rejected
            wrestler.adjust_morale(-5)
            wrestler.contract.renewal_attempts += 1
            wrestler.contract.last_renewal_attempt_year = state['current_year']
            wrestler.contract.last_renewal_attempt_week = state['current_week']
            
            universe.save_wrestler(wrestler)
            database.conn.commit()
            
            # Generate feedback
            market_value = prob_data['market_value']
            feedback = []
            
            if base_salary < market_value * 0.9:
                feedback.append(f"Salary too low (${base_salary:,} vs market ${market_value:,})")
            if wrestler.morale < 30:
                feedback.append("Morale too low - relationship damaged")
            if signing_bonus < market_value * 2:
                feedback.append("Signing bonus not compelling enough")
            
            message = f"""❌ {wrestler.name} REJECTED the early renewal offer (-5 morale)

Acceptance Probability: {prob_data['final_probability']}%
Rolled: {random_roll:.1f}

Possible Issues:
{chr(10).join('• ' + f for f in feedback)}

Recommendation: {prob_data['recommendation']}"""
            
            return jsonify({
                'success': True,
                'accepted': False,
                'message': message,
                'wrestler': wrestler.to_dict(),
                'probability_data': prob_data,
                'feedback': feedback
            })
    
    except Exception as e:
        print(f"Error in early renewal: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def _save_contract_promise(database, promise):
    """Helper to save contract promises for tracking"""
    cursor = database.conn.cursor()
    
    # Create table if doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contract_promises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            promise_type TEXT NOT NULL,
            wrestler_id TEXT NOT NULL,
            promised_year INTEGER NOT NULL,
            promised_week INTEGER NOT NULL,
            deadline_weeks INTEGER NOT NULL,
            fulfilled INTEGER DEFAULT 0,
            fulfilled_year INTEGER,
            fulfilled_week INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
        )
    ''')
    
    now = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT INTO contract_promises (
            promise_type, wrestler_id, promised_year, promised_week,
            deadline_weeks, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        promise['type'],
        promise['wrestler_id'],
        promise['promised_year'],
        promise['promised_week'],
        promise['deadline_weeks'],
        now
    ))


@contract_bp.route('/api/contracts/<wrestler_id>/renewal-probability', methods=['POST'])
def api_calculate_renewal_probability(wrestler_id):
    """
    STEP 121: Calculate renewal probability without actually renewing.
    Used by frontend to show live probability updates.
    """
    try:
        universe = get_universe()
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        data = request.get_json()
        base_salary = data.get('salary_per_show', wrestler.contract.salary_per_show)
        contract_weeks = data.get('weeks', 52)
        signing_bonus = data.get('signing_bonus', 0)
        title_promise = data.get('title_promise', False)
        brand_transfer = data.get('brand_transfer')
        
        prob_data = contract_manager.calculate_early_renewal_probability(
            wrestler,
            base_salary,
            contract_weeks,
            signing_bonus,
            title_promise,
            brand_transfer
        )
        
        return jsonify({
            'success': True,
            'wrestler_id': wrestler_id,
            'wrestler_name': wrestler.name,
            **prob_data
        })
    
    except Exception as e:
        print(f"Error calculating probability: {e}")
        return jsonify({'error': str(e)}), 500


@contract_bp.route('/api/contracts/<wrestler_id>/renewal-status')
def api_get_renewal_status(wrestler_id):
    """
    STEP 121: Get renewal eligibility and history for a wrestler.
    """
    try:
        universe = get_universe()
        database = get_database()
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        state = database.get_game_state()
        
        # Check eligibility for early renewal (must have 4+ weeks remaining)
        eligible_for_early_renewal = wrestler.contract.weeks_remaining >= 4
        
        response = {
            'wrestler_id': wrestler_id,
            'wrestler_name': wrestler.name,
            'weeks_remaining': wrestler.contract.weeks_remaining,
            'eligible_for_early_renewal': eligible_for_early_renewal,
            'early_renewal_offered': getattr(wrestler.contract, 'early_renewal_offered', False),
            'renewal_attempts': getattr(wrestler.contract, 'renewal_attempts', 0),
            'current_salary': wrestler.contract.salary_per_show,
            'market_value': contract_manager.calculate_market_value(wrestler)
        }
        
        # Add last attempt info if exists
        if hasattr(wrestler.contract, 'last_renewal_attempt_year'):
            response['last_attempt'] = {
                'year': wrestler.contract.last_renewal_attempt_year,
                'week': wrestler.contract.last_renewal_attempt_week
            }
        
        # Add early renewal info if exists
        if hasattr(wrestler.contract, 'early_renewal_year') and wrestler.contract.early_renewal_year:
            response['early_renewal'] = {
                'year': wrestler.contract.early_renewal_year,
                'week': wrestler.contract.early_renewal_week
            }
        
        return jsonify(response)
    
    except Exception as e:
        print(f"Error getting renewal status: {e}")
        return jsonify({'error': str(e)}), 500


# ========================================================================
# STEP 122: Contract Incentive Endpoints
# ========================================================================

@contract_bp.route('/api/contracts/incentives/templates')
def api_get_incentive_templates():
    """Get all available incentive templates"""
    from economy.contract_incentives import incentive_engine
    
    templates = {}
    for name, template in incentive_engine.incentive_templates.items():
        templates[name] = {
            'name': name,
            'type': template['type'].value,
            'description': template['description'],
            'value': template['value'],
            'acceptance_modifier': template.get('acceptance_modifier', 0),
            'conditions': template.get('conditions', {})
        }
    
    # Group by type
    grouped = {}
    for name, template in templates.items():
        template_type = template['type']
        if template_type not in grouped:
            grouped[template_type] = []
        grouped[template_type].append({
            'template_name': name,
            **template
        })
    
    return jsonify({
        'total_templates': len(templates),
        'templates': templates,
        'grouped_by_type': grouped
    })


@contract_bp.route('/api/contracts/incentives/recommended/<wrestler_id>')
def api_get_recommended_incentives(wrestler_id):
    """Get recommended incentives for a specific wrestler"""
    try:
        from economy.contract_incentives import incentive_engine
        universe = get_universe()
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        recommendations = incentive_engine.get_recommended_incentives_for_wrestler(wrestler)
        
        # Get full template details
        detailed_recs = []
        for template_name in recommendations:
            template = incentive_engine.incentive_templates.get(template_name)
            if template:
                detailed_recs.append({
                    'template_name': template_name,
                    'type': template['type'].value,
                    'description': template['description'],
                    'value': template['value'],
                    'acceptance_modifier': template.get('acceptance_modifier', 0)
                })
        
        return jsonify({
            'wrestler_id': wrestler_id,
            'wrestler_name': wrestler.name,
            'role': wrestler.role,
            'is_major_superstar': wrestler.is_major_superstar,
            'recommendations': detailed_recs
        })
    
    except Exception as e:
        print(f"Error in recommended incentives: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@contract_bp.route('/api/contracts/incentives/package-builder', methods=['POST'])
def api_build_incentive_package():
    """Build and analyze a contract package with incentives"""
    try:
        from economy.contract_incentives import incentive_engine
        universe = get_universe()
        
        data = request.get_json()
        wrestler_id = data.get('wrestler_id')
        base_salary = data.get('base_salary')
        contract_weeks = data.get('contract_weeks', 52)
        incentive_templates = data.get('incentives', [])
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        # Build package
        contract, analysis = incentive_engine.build_contract_package(
            wrestler,
            base_salary,
            contract_weeks,
            incentive_templates
        )
        
        return jsonify({
            'success': True,
            'wrestler_name': wrestler.name,
            'package_analysis': analysis,
            'contract_details': {
                'base_salary': base_salary,
                'contract_weeks': contract_weeks,
                'total_incentives': len(contract.incentives),
                'merchandise_share': contract.merchandise_share_percentage,
                'creative_control': contract.creative_control_level.value,
                'guaranteed_ppv': contract.guaranteed_ppv_appearances,
                'has_no_trade': contract.has_no_trade_clause,
                'has_injury_protection': contract.has_injury_protection
            }
        })
    
    except Exception as e:
        print(f"Error building package: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@contract_bp.route('/api/contracts/incentives/compare', methods=['POST'])
def api_compare_incentive_packages():
    """Compare two incentive packages side-by-side"""
    try:
        from economy.contract_incentives import incentive_engine
        universe = get_universe()
        
        data = request.get_json()
        wrestler_id = data.get('wrestler_id')
        base_salary = data.get('base_salary')
        contract_weeks = data.get('contract_weeks', 52)
        package_a = data.get('package_a', [])
        package_b = data.get('package_b', [])
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        comparison = incentive_engine.compare_incentive_packages(
            wrestler,
            base_salary,
            contract_weeks,
            package_a,
            package_b
        )
        
        return jsonify({
            'success': True,
            'wrestler_name': wrestler.name,
            'comparison': comparison
        })
    
    except Exception as e:
        print(f"Error comparing packages: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@contract_bp.route('/api/contracts/<wrestler_id>/extend-with-incentives', methods=['POST'])
def api_extend_contract_with_incentives(wrestler_id):
    """
    STEP 122: Extend contract with custom incentive package.
    Enhanced version of contract extension with full incentive support.
    """
    try:
        from economy.contract_incentives import incentive_engine
        from models.contract import Contract
        universe = get_universe()
        database = get_database()
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        data = request.get_json()
        base_salary = data.get('salary_per_show')
        contract_weeks = data.get('weeks', 52)
        incentive_templates = data.get('incentives', [])
        
        # Build contract with incentives
        new_contract, analysis = incentive_engine.build_contract_package(
            wrestler,
            base_salary,
            contract_weeks,
            incentive_templates
        )
        
        # Check acceptance
        acceptance_prob = analysis['acceptance_probability']
        random_roll = random.random() * 100
        
        accepted = random_roll <= acceptance_prob
        
        if accepted:
            # Replace wrestler's contract
            state = database.get_game_state()
            new_contract.signing_year = state['current_year']
            new_contract.signing_week = state['current_week']
            
            wrestler.contract = new_contract
            
            # Morale boost
            if acceptance_prob >= 80:
                wrestler.adjust_morale(15)
                morale_msg = "+15 morale (excellent deal)"
            elif acceptance_prob >= 60:
                wrestler.adjust_morale(10)
                morale_msg = "+10 morale (good deal)"
            else:
                wrestler.adjust_morale(5)
                morale_msg = "+5 morale (acceptable deal)"
            
            # Save
            universe.save_wrestler(wrestler)
            database.conn.commit()
            
            message = f"""✅ {wrestler.name} ACCEPTED the contract offer!
            
Contract Details:
• Base Salary: ${base_salary:,}/show
• Length: {contract_weeks} weeks
• Total Value: ${analysis['total_cost']:,}
• Incentives: {len(new_contract.incentives)}

{morale_msg}

Acceptance Probability: {acceptance_prob:.1f}%
Rolled: {random_roll:.1f}"""
            
            return jsonify({
                'success': True,
                'accepted': True,
                'message': message,
                'wrestler': wrestler.to_dict(),
                'analysis': analysis
            })
        
        else:
            # Rejected
            wrestler.adjust_morale(-5)
            
            universe.save_wrestler(wrestler)
            database.conn.commit()
            
            # Provide feedback on why rejected
            market_value = contract_manager.calculate_market_value(wrestler)
            salary_diff = market_value - base_salary
            
            feedback = []
            if salary_diff > 1000:
                feedback.append(f"Salary ${salary_diff:,} below market value")
            if wrestler.morale < 30:
                feedback.append("Low morale makes acceptance difficult")
            if acceptance_prob < 40:
                feedback.append("Overall package not competitive")
            
            warnings = analysis.get('validation', {}).get('warnings', [])
            recommendation = warnings[0] if warnings else 'Improve salary or add more incentives'
            
            message = f"""❌ {wrestler.name} REJECTED the contract offer (-5 morale)
            
Acceptance Probability: {acceptance_prob:.1f}%
Rolled: {random_roll:.1f}

Possible Issues:
{chr(10).join('• ' + f for f in feedback)}

Recommendation: {recommendation}"""
            
            return jsonify({
                'success': True,
                'accepted': False,
                'message': message,
                'wrestler': wrestler.to_dict(),
                'analysis': analysis,
                'feedback': feedback
            })
    
    except Exception as e:
        print(f"Error extending with incentives: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@contract_bp.route('/api/contracts/<wrestler_id>/current-incentives')
def api_get_current_incentives(wrestler_id):
    """Get wrestler's current contract incentives"""
    try:
        universe = get_universe()
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        if not hasattr(wrestler.contract, 'incentives'):
            return jsonify({
                'wrestler_id': wrestler_id,
                'wrestler_name': wrestler.name,
                'total_incentives': 0,
                'incentives': []
            })
        
        incentives_data = [i.to_dict() for i in wrestler.contract.incentives]
        
        return jsonify({
            'wrestler_id': wrestler_id,
            'wrestler_name': wrestler.name,
            'total_incentives': len(incentives_data),
            'incentives': incentives_data,
            'contract_summary': {
                'base_salary': wrestler.contract.base_salary,
                'current_salary': wrestler.contract.salary_per_show,
                'merchandise_share': wrestler.contract.merchandise_share_percentage,
                'creative_control': wrestler.contract.creative_control_level.value if hasattr(wrestler.contract.creative_control_level, 'value') else wrestler.contract.creative_control_level,
                'guaranteed_ppv': wrestler.contract.guaranteed_ppv_appearances,
                'has_no_trade': wrestler.contract.has_no_trade_clause,
                'has_injury_protection': wrestler.contract.has_injury_protection
            }
        })
    
    except Exception as e:
        print(f"Error getting incentives: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ========================================================================
# Existing endpoints continue below...
# ========================================================================

@contract_bp.route('/api/contracts/<wrestler_id>/market-value')
def api_get_market_value(wrestler_id):
    try:
        universe = get_universe()
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        market_value = contract_manager.calculate_market_value(wrestler)
        
        return jsonify({
            'wrestler_id': wrestler.id,
            'wrestler_name': wrestler.name,
            'market_value': market_value,
            'current_salary': wrestler.contract.salary_per_show,
            'difference': market_value - wrestler.contract.salary_per_show
        })
    
    except Exception as e:
        print(f"Error in market-value: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@contract_bp.route('/api/contracts/<wrestler_id>/extend', methods=['POST'])
def api_extend_contract_negotiation(wrestler_id):
    try:
        universe = get_universe()
        database = get_database()
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        data = request.get_json()
        weeks = data.get('weeks', 52)
        offered_salary = data.get('salary_per_show', wrestler.contract.salary_per_show)
        
        success, message = contract_manager.negotiate_extension(
            wrestler,
            offered_salary,
            weeks,
            universe.balance
        )
        
        if success:
            universe.save_wrestler(wrestler)
            database.conn.commit()
        
        return jsonify({
            'success': success,
            'message': message,
            'wrestler': wrestler.to_dict() if success else None
        })
    
    except Exception as e:
        print(f"Error in extend: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@contract_bp.route('/api/contracts/<wrestler_id>/auto-extend', methods=['POST'])
def api_auto_extend_contract(wrestler_id):
    try:
        universe = get_universe()
        database = get_database()
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        data = request.get_json() if request.is_json else {}
        weeks_to_add = data.get('weeks', 52)
        
        result = contract_manager.auto_extend(wrestler, weeks_to_add)
        
        universe.save_wrestler(wrestler)
        database.conn.commit()
        
        return jsonify(result)
    
    except Exception as e:
        print(f"Error in auto-extend: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@contract_bp.route('/api/contracts/<wrestler_id>/release', methods=['POST'])
def api_release_wrestler_contract(wrestler_id):
    try:
        universe = get_universe()
        database = get_database()
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        result = contract_manager.release_wrestler(wrestler)
        
        universe.save_wrestler(wrestler)
        database.conn.commit()
        
        return jsonify(result)
    
    except Exception as e:
        print(f"Error in release: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# Legacy endpoints for backward compatibility
@contract_bp.route('/api/roster/<wrestler_id>/extend-contract', methods=['POST'])
def api_extend_contract_legacy(wrestler_id):
    return api_auto_extend_contract(wrestler_id)


@contract_bp.route('/api/roster/<wrestler_id>/release', methods=['POST'])
def api_release_wrestler_legacy(wrestler_id):
    return api_release_wrestler_contract(wrestler_id)


# ========================================================================
# ENHANCEMENT A: Contract History Endpoints
# ========================================================================

@contract_bp.route('/api/contracts/<wrestler_id>/history')
def api_get_contract_history(wrestler_id):
    """Get complete contract history for a wrestler"""
    try:
        database = get_database()
        universe = get_universe()
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        history = database.get_wrestler_contract_history(wrestler_id)
        stats = database.get_contract_statistics(wrestler_id)
        
        return jsonify({
            'wrestler_id': wrestler_id,
            'wrestler_name': wrestler.name,
            'total_contracts': len(history),
            'contracts': history,
            'statistics': stats
        })
    
    except Exception as e:
        print(f"Error getting contract history: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@contract_bp.route('/api/contracts/<wrestler_id>/salary-progression')
def api_get_salary_progression(wrestler_id):
    """Get salary progression over time (for charts)"""
    try:
        database = get_database()
        
        history = database.get_wrestler_contract_history(wrestler_id)
        
        progression = []
        for contract in reversed(history):  # Oldest to newest
            progression.append({
                'year': contract['signed_year'],
                'week': contract['signed_week'],
                'salary': contract['salary_per_show'],
                'signing_bonus': contract['signing_bonus'],
                'total_incentives': contract['total_incentives']
            })
        
        return jsonify({
            'wrestler_id': wrestler_id,
            'progression': progression
        })
    
    except Exception as e:
        print(f"Error getting salary progression: {e}")
        return jsonify({'error': str(e)}), 500

# ========================================================================
# ENHANCEMENT B: Incentive Performance Dashboard
# ========================================================================

@contract_bp.route('/api/contracts/incentives/performance-dashboard')
def api_get_performance_dashboard():
    """
    Get global view of all active performance escalators and their status.
    Shows which wrestlers are close to triggering bonuses.
    """
    try:
        universe = get_universe()
        database = get_database()
        
        dashboard_data = {
            'active_escalators': [],
            'recently_triggered': [],
            'close_to_triggering': [],
            'summary': {
                'total_active_escalators': 0,
                'total_triggered_this_year': 0,
                'potential_cost_if_all_trigger': 0
            }
        }
        
        for wrestler in get_contract_roster():
            contract = getattr(wrestler, 'contract', None)
            if not contract or not hasattr(contract, 'incentives'):
                continue
            
            for incentive in contract.incentives:
                if incentive.incentive_type.value != 'performance_escalator':
                    continue
                
                dashboard_data['summary']['total_active_escalators'] += 1
                
                # Check status
                conditions = incentive.conditions or {}
                status = check_escalator_status(wrestler, conditions)
                
                escalator_info = {
                    'wrestler_id': wrestler.id,
                    'wrestler_name': wrestler.name,
                    'description': incentive.description,
                    'value': incentive.value,
                    'conditions': conditions,
                    'triggered_count': incentive.triggered_count,
                    'current_status': status,
                    'progress_percentage': status['progress']
                }
                
                dashboard_data['active_escalators'].append(escalator_info)
                
                # Categorize
                if incentive.triggered_count > 0:
                    dashboard_data['recently_triggered'].append(escalator_info)
                    dashboard_data['summary']['total_triggered_this_year'] += 1
                
                if status['progress'] >= 80 and status['progress'] < 100:
                    dashboard_data['close_to_triggering'].append(escalator_info)
                
                # Estimate cost
                if isinstance(incentive.value, str) and '%' in incentive.value:
                    pct = float(incentive.value.replace('%', '')) / 100
                    cost = wrestler.contract.base_salary * pct * 52 * 3
                else:
                    cost = int(incentive.value) * 52 * 3
                
                dashboard_data['summary']['potential_cost_if_all_trigger'] += cost
        
        return jsonify(dashboard_data)
    
    except Exception as e:
        print(f"Error generating performance dashboard: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def check_escalator_status(wrestler, conditions):
    """Check how close a wrestler is to triggering an escalator"""
    status = {
        'met': False,
        'progress': 0,
        'details': ''
    }
    
    if 'min_popularity' in conditions:
        target = conditions['min_popularity']
        current = wrestler.popularity
        progress = (current / target) * 100
        status['progress'] = min(progress, 100)
        status['met'] = current >= target
        status['details'] = f"{current}/{target} popularity"
    
    elif 'min_avg_rating' in conditions:
        target = conditions['min_avg_rating']
        current = getattr(wrestler.contract, 'average_match_rating', 0)
        progress = (current / target) * 100
        status['progress'] = min(progress, 100)
        status['met'] = current >= target
        status['details'] = f"{current:.1f}/{target} avg rating"
    
    elif 'min_title_reigns' in conditions:
        target = conditions['min_title_reigns']
        current = getattr(wrestler.contract, 'title_reigns_this_contract', 0)
        progress = (current / target) * 100
        status['progress'] = min(progress, 100)
        status['met'] = current >= target
        status['details'] = f"{current}/{target} title reigns"
    
    elif 'min_ppv_appearances' in conditions:
        target = conditions['min_ppv_appearances']
        current = getattr(wrestler.contract, 'ppv_appearances_this_year', 0)
        progress = (current / target) * 100
        status['progress'] = min(progress, 100)
        status['met'] = current >= target
        status['details'] = f"{current}/{target} PPV appearances"
    
    return status

# ========================================================================
# ENHANCEMENT D: Bulk Contract Operations
# ========================================================================

@contract_bp.route('/api/contracts/bulk/expiring-preview')
def api_preview_bulk_extensions():
    """
    Preview what bulk extension would do.
    Shows all expiring contracts and estimated costs.
    """
    try:
        universe = get_universe()
        
        weeks_threshold = request.args.get('weeks', 13, type=int)
        
        expiring = contract_manager.get_expiring_contracts(
            get_contract_roster(),
            weeks_threshold
        )
        
        preview_data = {
            'total_wrestlers': len(expiring),
            'total_estimated_cost': 0,
            'wrestlers': [],
            'by_category': {
                'critical': [],
                'negotiate_soon': [],
                'monitor': []
            }
        }
        
        for wrestler in expiring:
            market_value = contract_manager.calculate_market_value(wrestler)
            extension_cost = market_value * 52 * 3  # 1 year, 3 shows/week
            
            wrestler_preview = {
                'wrestler_id': wrestler.id,
                'wrestler_name': wrestler.name,
                'current_salary': wrestler.contract.salary_per_show,
                'market_value': market_value,
                'weeks_remaining': wrestler.contract.weeks_remaining,
                'recommended_salary': market_value,
                'estimated_cost': extension_cost,
                'morale': wrestler.morale,
                'likely_accepts': wrestler.morale >= 50
            }
            
            preview_data['wrestlers'].append(wrestler_preview)
            preview_data['total_estimated_cost'] += extension_cost
            
            # Categorize
            if wrestler.contract.weeks_remaining <= 4:
                preview_data['by_category']['critical'].append(wrestler_preview)
            elif wrestler.contract.weeks_remaining <= 13:
                preview_data['by_category']['negotiate_soon'].append(wrestler_preview)
            else:
                preview_data['by_category']['monitor'].append(wrestler_preview)
        
        return jsonify(preview_data)
    
    except Exception as e:
        print(f"Error previewing bulk extensions: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@contract_bp.route('/api/contracts/bulk/extend-all', methods=['POST'])
def api_bulk_extend_contracts():
    """
    Bulk extend all expiring contracts.
    Can filter by category, morale threshold, etc.
    """
    try:
        universe = get_universe()
        database = get_database()
        
        data = request.get_json()
        weeks_threshold = data.get('weeks_threshold', 13)
        categories = data.get('categories', ['critical', 'negotiate_soon'])  # Which to extend
        min_morale = data.get('min_morale', 30)  # Only extend if morale >= this
        salary_strategy = data.get('salary_strategy', 'market_value')  # 'current', 'market_value', 'below_market'
        extension_weeks = data.get('extension_weeks', 52)
        
        expiring = contract_manager.get_expiring_contracts(
            get_contract_roster(),
            weeks_threshold
        )
        
        results = {
            'processed': 0,
            'accepted': 0,
            'rejected': 0,
            'skipped': 0,
            'total_cost': 0,
            'details': []
        }
        
        state = database.get_game_state()
        current_year = state['current_year']
        current_week = state['current_week']
        
        for wrestler in expiring:
            # Filter by morale
            if wrestler.morale < min_morale:
                results['skipped'] += 1
                results['details'].append({
                    'wrestler_name': wrestler.name,
                    'status': 'skipped',
                    'reason': 'Low morale'
                })
                continue
            
            # Filter by category
            if wrestler.contract.weeks_remaining <= 4 and 'critical' not in categories:
                results['skipped'] += 1
                continue
            if 5 <= wrestler.contract.weeks_remaining <= 13 and 'negotiate_soon' not in categories:
                results['skipped'] += 1
                continue
            
            # Determine salary
            market_value = contract_manager.calculate_market_value(wrestler)
            
            if salary_strategy == 'current':
                offered_salary = wrestler.contract.salary_per_show
            elif salary_strategy == 'market_value':
                offered_salary = market_value
            elif salary_strategy == 'below_market':
                offered_salary = int(market_value * 0.9)  # 10% below market
            elif salary_strategy == 'above_market':
                offered_salary = int(market_value * 1.1)  # 10% above market
            else:
                offered_salary = market_value
            
            # Attempt extension
            success, message = contract_manager.negotiate_extension(
                wrestler,
                offered_salary,
                extension_weeks,
                universe.balance
            )
            
            results['processed'] += 1
            
            if success:
                results['accepted'] += 1
                results['total_cost'] += offered_salary * extension_weeks * 3
                
                # Save to database
                universe.save_wrestler(wrestler)
                
                results['details'].append({
                    'wrestler_name': wrestler.name,
                    'status': 'accepted',
                    'salary': offered_salary,
                    'weeks_added': extension_weeks,
                    'morale_change': '+5 to +15'
                })
            else:
                results['rejected'] += 1
                results['details'].append({
                    'wrestler_name': wrestler.name,
                    'status': 'rejected',
                    'reason': message
                })
        
        # Commit all changes
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'results': results
        })
    
    except Exception as e:
        print(f"Error in bulk extend: {e}")
        import traceback
        traceback.print_exc()
        database.conn.rollback()
        return jsonify({'error': str(e)}), 500


@contract_bp.route('/api/contracts/bulk/release-multiple', methods=['POST'])
def api_bulk_release_contracts():
    """
    Release multiple wrestlers at once.
    Useful for mass roster cuts.
    """
    try:
        universe = get_universe()
        database = get_database()
        
        data = request.get_json()
        wrestler_ids = data.get('wrestler_ids', [])
        
        if not wrestler_ids:
            return jsonify({'error': 'No wrestler IDs provided'}), 400
        
        results = {
            'total': len(wrestler_ids),
            'released': 0,
            'failed': 0,
            'details': []
        }
        
        for wrestler_id in wrestler_ids:
            wrestler = universe.get_wrestler_by_id(wrestler_id)
            
            if not wrestler:
                results['failed'] += 1
                results['details'].append({
                    'wrestler_id': wrestler_id,
                    'status': 'failed',
                    'reason': 'Wrestler not found'
                })
                continue
            
            result = contract_manager.release_wrestler(wrestler)
            
            if result['success']:
                universe.save_wrestler(wrestler)
                results['released'] += 1
                results['details'].append({
                    'wrestler_id': wrestler_id,
                    'wrestler_name': wrestler.name,
                    'status': 'released'
                })
            else:
                results['failed'] += 1
                results['details'].append({
                    'wrestler_id': wrestler_id,
                    'wrestler_name': wrestler.name,
                    'status': 'failed',
                    'reason': 'Release failed'
                })
        
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'results': results
        })
    
    except Exception as e:
        print(f"Error in bulk release: {e}")
        import traceback
        traceback.print_exc()
        database.conn.rollback()
        return jsonify({'error': str(e)}), 500


@contract_bp.route('/api/contracts/bulk/strategies')
def api_get_bulk_strategies():
    """
    Get recommended bulk contract strategies based on current roster state.
    AI suggests different approaches.
    """
    try:
        universe = get_universe()
        database = get_database()
        
        expiring = contract_manager.get_expiring_contracts(
            get_contract_roster(),
            26  # 6 months
        )
        
        state = database.get_game_state()
        balance = state['balance']
        
        strategies = []
        
        # Strategy 1: Aggressive - Extend everyone at market value
        total_cost_aggressive = sum(
            contract_manager.calculate_market_value(w) * 52 * 3 
            for w in expiring
        )
        
        strategies.append({
            'name': 'Aggressive Retention',
            'description': 'Extend all expiring contracts at market value',
            'targets': len(expiring),
            'estimated_cost': total_cost_aggressive,
            'risk_level': 'LOW',
            'pros': ['Retain entire roster', 'High morale'],
            'cons': ['Very expensive', 'May overpay some wrestlers'],
            'recommended': balance >= total_cost_aggressive
        })
        
        # Strategy 2: Selective - Only extend high morale wrestlers
        high_morale = [w for w in expiring if w.morale >= 60]
        total_cost_selective = sum(
            contract_manager.calculate_market_value(w) * 52 * 3 
            for w in high_morale
        )
        
        strategies.append({
            'name': 'Selective Retention',
            'description': 'Only extend wrestlers with high morale (60+)',
            'targets': len(high_morale),
            'estimated_cost': total_cost_selective,
            'risk_level': 'MEDIUM',
            'pros': ['Lower cost', 'Focus on happy wrestlers'],
            'cons': ['Lose some talent', 'Roster gaps'],
            'recommended': balance >= total_cost_selective and balance < total_cost_aggressive
        })
        
        # Strategy 3: Budget - Extend at below-market rates
        total_cost_budget = sum(
            int(contract_manager.calculate_market_value(w) * 0.85) * 52 * 3 
            for w in expiring
        )
        
        strategies.append({
            'name': 'Budget Retention',
            'description': 'Extend all at 15% below market value',
            'targets': len(expiring),
            'estimated_cost': total_cost_budget,
            'risk_level': 'HIGH',
            'pros': ['Save money', 'Retain most wrestlers'],
            'cons': ['Lower acceptance rate', 'Morale hits'],
            'recommended': balance < total_cost_selective
        })
        
        # Strategy 4: Stars Only - Main eventers and upper midcard only
        stars = [w for w in expiring if w.role in ['Main Event', 'Upper Midcard']]
        total_cost_stars = sum(
            contract_manager.calculate_market_value(w) * 52 * 3 
            for w in stars
        )
        
        strategies.append({
            'name': 'Star Focus',
            'description': 'Only extend Main Event and Upper Midcard wrestlers',
            'targets': len(stars),
            'estimated_cost': total_cost_stars,
            'risk_level': 'MEDIUM',
            'pros': ['Secure top talent', 'Moderate cost'],
            'cons': ['Lose depth', 'Need to hire replacements'],
            'recommended': True
        })
        
        # Strategy 5: Youth Movement - Release veterans, extend young talent
        young_talent = [w for w in expiring if w.age <= 30]
        veterans = [w for w in expiring if w.age > 35]
        
        total_cost_youth = sum(
            contract_manager.calculate_market_value(w) * 52 * 3 
            for w in young_talent
        )
        
        strategies.append({
            'name': 'Youth Movement',
            'description': 'Release veterans (35+), extend young wrestlers (≤30)',
            'targets': len(young_talent),
            'releases': len(veterans),
            'estimated_cost': total_cost_youth,
            'risk_level': 'MEDIUM',
            'pros': ['Build for future', 'Lower salaries', 'Room for growth'],
            'cons': ['Lose experience', 'Short-term weakness'],
            'recommended': len(veterans) > 5
        })
        
        return jsonify({
            'total_expiring': len(expiring),
            'current_balance': balance,
            'strategies': strategies
        })
    
    except Exception as e:
        print(f"Error generating strategies: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    
# ========================================================================
# ENHANCEMENT E: Contract Alerts Widget
# ========================================================================

@contract_bp.route('/api/contracts/alerts/dashboard')
def api_get_contract_alerts_dashboard():
    """
    Get intelligent contract alerts for the office/dashboard view.
    Shows actionable warnings and upcoming events.
    """
    try:
        universe = get_universe()
        database = get_database()
        contract_roster = get_contract_roster()
        
        state = database.get_game_state()
        current_year = state['current_year']
        current_week = state['current_week']
        
        alerts = {
            'critical': [],  # Immediate action needed
            'warnings': [],  # Attention required soon
            'info': [],      # Good to know
            'opportunities': []  # Positive alerts
        }
        
        # Alert 1: Expiring contracts
        expiring_critical = contract_manager.get_expiring_contracts(
            contract_roster, 4
        )
        
        if expiring_critical:
            alerts['critical'].append({
                'type': 'expiring_contracts',
                'severity': 'critical',
                'title': f'{len(expiring_critical)} Contract(s) Expiring This Week!',
                'message': f'{len(expiring_critical)} wrestlers have ≤4 weeks remaining',
                'action': 'Negotiate immediately',
                'action_url': '/contracts',
                'wrestlers': [w.name for w in expiring_critical[:3]],
                'icon': '🚨'
            })
        
        # Alert 2: Performance escalators about to trigger
        escalators_ready = []
        for wrestler in contract_roster:
            if not hasattr(wrestler.contract, 'incentives'):
                continue
            
            for incentive in wrestler.contract.incentives:
                if incentive.incentive_type.value != 'performance_escalator':
                    continue
                
                conditions = incentive.conditions or {}
                status = check_escalator_status(wrestler, conditions)
                
                if status['progress'] >= 90 and not status['met']:
                    escalators_ready.append({
                        'wrestler_name': wrestler.name,
                        'description': incentive.description,
                        'progress': status['progress'],
                        'value': incentive.value
                    })
        
        if escalators_ready:
            total_cost = len(escalators_ready) * 50000  # Estimate
            alerts['warnings'].append({
                'type': 'escalators_triggering',
                'severity': 'warning',
                'title': f'{len(escalators_ready)} Performance Bonus(es) About to Trigger',
                'message': f'{len(escalators_ready)} wrestlers are close to earning salary increases',
                'estimated_cost': total_cost,
                'action': 'Review performance bonuses',
                'action_url': '/contracts',
                'details': escalators_ready[:3],
                'icon': '📈'
            })
        
        # Alert 3: Unhappy high-value wrestlers
        unhappy_stars = [
            w for w in contract_roster
            if getattr(w, 'morale', 50) < 30 and getattr(w, 'is_major_superstar', False)
        ]
        
        if unhappy_stars:
            alerts['critical'].append({
                'type': 'unhappy_stars',
                'severity': 'critical',
                'title': f'{len(unhappy_stars)} Star(s) Unhappy',
                'message': 'Major superstars have low morale and may leave',
                'action': 'Improve morale or renegotiate',
                'action_url': '/contracts',
                'wrestlers': [w.name for w in unhappy_stars],
                'icon': '😡'
            })
        
        # Alert 4: Good contract opportunities
        bargains = []
        for wrestler in contract_roster:
            weeks_remaining = _contract_weeks_remaining(wrestler)
            if weeks_remaining is None or weeks_remaining > 26:
                continue
            
            market_value = contract_manager.calculate_market_value(wrestler)
            current_salary = getattr(getattr(wrestler, 'contract', None), 'salary_per_show', 0) or 0
            
            if current_salary < market_value * 0.8 and wrestler.morale >= 60:
                bargains.append({
                    'wrestler_name': wrestler.name,
                    'current_salary': current_salary,
                    'market_value': market_value,
                    'savings': market_value - current_salary
                })
        
        if bargains:
            total_savings = sum(b['savings'] for b in bargains) * 52 * 3
            alerts['opportunities'].append({
                'type': 'bargain_extensions',
                'severity': 'info',
                'title': f'{len(bargains)} Bargain Extension(s) Available',
                'message': f'Extend these wrestlers now before their value increases',
                'potential_savings': total_savings,
                'action': 'Lock in current rates',
                'action_url': '/contracts',
                'details': bargains[:3],
                'icon': '💰'
            })
        
        # Alert 5: PPV guarantee violations
        ppv_violations = []
        for wrestler in contract_roster:
            contract = getattr(wrestler, 'contract', None)
            if not contract or not hasattr(contract, 'guaranteed_ppv_appearances'):
                continue
            
            guaranteed = contract.guaranteed_ppv_appearances
            if guaranteed == 0:
                continue
            
            actual = getattr(contract, 'ppv_appearances_this_year', 0)
            weeks_left = 52 - current_week
            ppvs_remaining = max(0, (weeks_left // 4))  # Rough estimate
            
            if actual + ppvs_remaining < guaranteed:
                ppv_violations.append({
                    'wrestler_name': wrestler.name,
                    'guaranteed': guaranteed,
                    'actual': actual,
                    'shortfall': guaranteed - actual
                })
        
        if ppv_violations:
            alerts['warnings'].append({
                'type': 'ppv_guarantee_violation',
                'severity': 'warning',
                'title': f'{len(ppv_violations)} PPV Guarantee(s) At Risk',
                'message': 'Some wrestlers may not meet their guaranteed PPV appearances',
                'action': 'Book more PPV matches',
                'action_url': '/booking',
                'details': ppv_violations[:3],
                'icon': '🎪'
            })
        
        # Alert 6: Option years available
        option_years = []
        for wrestler in contract_roster:
            contract = getattr(wrestler, 'contract', None)
            if not contract or not hasattr(contract, 'option_years_remaining'):
                continue

            weeks_remaining = _contract_weeks_remaining(wrestler)
            if (
                contract.option_years_remaining > 0
                and weeks_remaining is not None
                and weeks_remaining <= 8
            ):
                option_years.append({
                    'wrestler_name': wrestler.name,
                    'option_years': contract.option_years_remaining,
                    'weeks_remaining': weeks_remaining
                })
        
        if option_years:
            alerts['info'].append({
                'type': 'option_years',
                'severity': 'info',
                'title': f'{len(option_years)} Option Year(s) Available',
                'message': 'You can extend these contracts without negotiation',
                'action': 'Exercise options',
                'action_url': '/contracts',
                'details': option_years[:3],
                'icon': '📅'
            })
        
        # Alert 7: Recent rejections
        recent_rejections = get_recent_contract_rejections(database, 4)  # Last 4 weeks
        
        if recent_rejections:
            alerts['warnings'].append({
                'type': 'recent_rejections',
                'severity': 'warning',
                'title': f'{len(recent_rejections)} Recent Contract Rejection(s)',
                'message': 'These wrestlers rejected offers recently',
                'action': 'Improve offers or consider releasing',
                'action_url': '/contracts',
                'details': recent_rejections,
                'icon': '❌'
            })
        
        # Count totals
        summary = {
            'total_alerts': sum(len(alerts[cat]) for cat in alerts),
            'critical_count': len(alerts['critical']),
            'warnings_count': len(alerts['warnings']),
            'info_count': len(alerts['info']),
            'opportunities_count': len(alerts['opportunities'])
        }
        
        return jsonify({
            'summary': summary,
            'alerts': alerts,
            'generated_at': {
                'year': current_year,
                'week': current_week
            }
        })
    
    except Exception as e:
        print(f"Error generating contract alerts: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def get_recent_contract_rejections(database, weeks_ago):
    """Get wrestlers who rejected offers recently"""
    # This would require tracking rejections in database
    # For now, return empty list
    return []


@contract_bp.route('/api/contracts/alerts/upcoming-events')
def api_get_upcoming_contract_events():
    """
    Get timeline of upcoming contract-related events.
    Shows what will happen in the next 4-12 weeks.
    """
    try:
        universe = get_universe()
        database = get_database()
        
        state = database.get_game_state()
        current_week = state['current_week']
        
        timeline = []
        
        # Scan next 12 weeks
        for week_offset in range(1, 13):
            future_week = current_week + week_offset
            week_events = []
            
            # Check expirations
            for wrestler in get_contract_roster():
                if wrestler.contract.weeks_remaining == week_offset:
                    week_events.append({
                        'type': 'expiration',
                        'wrestler_name': wrestler.name,
                        'description': f"Contract expires",
                        'severity': 'high' if week_offset <= 4 else 'medium'
                    })
            
            # Check PPV guarantees (simplified)
            if week_offset % 4 == 0:  # Assume PPV every 4 weeks
                for wrestler in get_contract_roster():
                    if getattr(wrestler.contract, 'guaranteed_ppv_appearances', 0) > 0:
                        week_events.append({
                            'type': 'ppv_guarantee',
                            'wrestler_name': wrestler.name,
                            'description': 'PPV guarantee check',
                            'severity': 'low'
                        })
            
            if week_events:
                timeline.append({
                    'week': future_week,
                    'week_offset': week_offset,
                    'events': week_events
                })
        
        return jsonify({
            'timeline': timeline,
            'next_4_weeks': timeline[:4],
            'total_events': sum(len(w['events']) for w in timeline)
        })
    
    except Exception as e:
        print(f"Error generating timeline: {e}")
        return jsonify({'error': str(e)}), 500

# ========================================================================
# ENHANCEMENT C: Interactive Contract Visualizer & Sharing
# ========================================================================

@contract_bp.route('/api/contracts/<wrestler_id>/generate-card')
def api_generate_contract_card(wrestler_id):
    """
    Generate a beautiful contract card with all details.
    Returns structured data for frontend rendering.
    """
    try:
        universe = get_universe()
        database = get_database()
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        # Get incentives
        incentives_response = database.load_contract_incentives(wrestler_id)
        
        # Get contract history
        history = database.get_wrestler_contract_history(wrestler_id)
        stats = database.get_contract_statistics(wrestler_id)
        
        # Calculate contract score (0-100)
        contract_score = calculate_contract_score(wrestler, incentives_response)
        
        # Generate unique shareable ID
        import hashlib
        import time
        share_id = hashlib.md5(f"{wrestler_id}{time.time()}".encode()).hexdigest()[:12]
        
        card_data = {
            'share_id': share_id,
            'wrestler': {
                'id': wrestler.id,
                'name': wrestler.name,
                'age': wrestler.age,
                'role': wrestler.role,
                'brand': wrestler.primary_brand,
                'overall_rating': wrestler.overall_rating,
                'popularity': wrestler.popularity,
                'is_major_superstar': wrestler.is_major_superstar
            },
            'contract': {
                'base_salary': wrestler.contract.base_salary,
                'current_salary': wrestler.contract.salary_per_show,
                'weeks_total': wrestler.contract.total_length_weeks,
                'weeks_remaining': wrestler.contract.weeks_remaining,
                'signing_year': wrestler.contract.signing_year,
                'signing_week': wrestler.contract.signing_week,
                'merchandise_share': wrestler.contract.merchandise_share_percentage,
                'creative_control': wrestler.contract.creative_control_level.value if hasattr(wrestler.contract.creative_control_level, 'value') else wrestler.contract.creative_control_level,
                'guaranteed_ppv': wrestler.contract.guaranteed_ppv_appearances,
                'has_no_trade': wrestler.contract.has_no_trade_clause,
                'has_injury_protection': wrestler.contract.has_injury_protection
            },
            'incentives': [
                {
                    'type': inc.incentive_type.value,
                    'description': inc.description,
                    'value': inc.value,
                    'triggered_count': inc.triggered_count,
                    'is_active': inc.is_active
                }
                for inc in incentives_response
            ],
            'stats': {
                'total_contracts': stats.get('total_contracts', 0),
                'avg_salary': stats.get('avg_salary', 0),
                'highest_salary': stats.get('highest_salary', 0),
                'total_bonuses': stats.get('total_bonuses', 0)
            },
            'performance': {
                'total_matches': getattr(wrestler.contract, 'total_matches_this_contract', 0),
                'avg_rating': getattr(wrestler.contract, 'average_match_rating', 0),
                'ppv_appearances': getattr(wrestler.contract, 'ppv_appearances_this_year', 0),
                'title_reigns': getattr(wrestler.contract, 'title_reigns_this_contract', 0)
            },
            'score': contract_score,
            'grade': get_contract_grade(contract_score),
            'value_analysis': analyze_contract_value(wrestler, database),
            'generated_at': datetime.now().isoformat()
        }
        
        # Save to database for sharing
        save_contract_card(database, share_id, card_data)
        
        return jsonify(card_data)
    
    except Exception as e:
        print(f"Error generating contract card: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def calculate_contract_score(wrestler, incentives):
    """Calculate overall contract quality score (0-100)"""
    score = 50  # Base score
    
    # Salary fairness
    market_value = contract_manager.calculate_market_value(wrestler)
    salary_ratio = wrestler.contract.salary_per_show / market_value if market_value > 0 else 1.0
    
    if salary_ratio >= 1.2:
        score += 20  # Overpaid
    elif salary_ratio >= 1.0:
        score += 15  # Fair
    elif salary_ratio >= 0.9:
        score += 10  # Slight underpay
    else:
        score += 5   # Underpaid
    
    # Incentives
    score += min(len(incentives) * 3, 15)  # Up to +15 for incentives
    
    # Creative control
    creative = wrestler.contract.creative_control_level
    creative_value = creative.value if hasattr(creative, 'value') else creative
    creative_scores = {
        'none': 0,
        'consultation': 3,
        'approval': 6,
        'partnership': 9,
        'full': 12
    }
    score += creative_scores.get(creative_value, 0)
    
    # Security features
    if wrestler.contract.has_no_trade_clause:
        score += 5
    if wrestler.contract.has_injury_protection:
        score += 5
    if wrestler.contract.guaranteed_ppv_appearances >= 8:
        score += 5
    
    # Merchandise share
    if wrestler.contract.merchandise_share_percentage >= 50:
        score += 8
    elif wrestler.contract.merchandise_share_percentage >= 40:
        score += 5
    
    return min(score, 100)


def get_contract_grade(score):
    """Convert score to letter grade"""
    if score >= 90:
        return 'S'
    elif score >= 80:
        return 'A'
    elif score >= 70:
        return 'B'
    elif score >= 60:
        return 'C'
    elif score >= 50:
        return 'D'
    else:
        return 'F'


def analyze_contract_value(wrestler, database):
    """Analyze if contract is good value"""
    market_value = contract_manager.calculate_market_value(wrestler)
    current_salary = wrestler.contract.salary_per_show
    
    diff = current_salary - market_value
    diff_pct = (diff / market_value * 100) if market_value > 0 else 0
    
    if diff_pct > 20:
        verdict = 'OVERPAID'
        color = 'danger'
    elif diff_pct > 5:
        verdict = 'SLIGHT OVERPAY'
        color = 'warning'
    elif diff_pct > -5:
        verdict = 'FAIR VALUE'
        color = 'success'
    elif diff_pct > -20:
        verdict = 'GOOD VALUE'
        color = 'info'
    else:
        verdict = 'EXCELLENT VALUE'
        color = 'primary'
    
    return {
        'verdict': verdict,
        'color': color,
        'difference': diff,
        'difference_percentage': round(diff_pct, 1)
    }


def save_contract_card(database, share_id, card_data):
    """Save contract card for sharing"""
    cursor = database.conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contract_cards (
            share_id TEXT PRIMARY KEY,
            wrestler_id TEXT NOT NULL,
            card_data TEXT NOT NULL,
            created_at TEXT NOT NULL,
            views INTEGER DEFAULT 0
        )
    ''')
    
    import json
    cursor.execute('''
        INSERT OR REPLACE INTO contract_cards (share_id, wrestler_id, card_data, created_at)
        VALUES (?, ?, ?, ?)
    ''', (share_id, card_data['wrestler']['id'], json.dumps(card_data), datetime.now().isoformat()))
    
    database.conn.commit()


@contract_bp.route('/api/contracts/cards/<share_id>')
def api_get_shared_contract_card(share_id):
    """Get a shared contract card by ID"""
    try:
        database = get_database()
        cursor = database.conn.cursor()
        
        cursor.execute('SELECT * FROM contract_cards WHERE share_id = ?', (share_id,))
        row = cursor.fetchone()
        
        if not row:
            return jsonify({'error': 'Contract card not found'}), 404
        
        # Increment view count
        cursor.execute('UPDATE contract_cards SET views = views + 1 WHERE share_id = ?', (share_id,))
        database.conn.commit()
        
        import json
        card_data = json.loads(row['card_data'])
        card_data['views'] = row['views'] + 1
        
        return jsonify(card_data)
    
    except Exception as e:
        print(f"Error fetching shared card: {e}")
        return jsonify({'error': str(e)}), 500


@contract_bp.route('/api/contracts/<wrestler_id>/portfolio')
def api_get_contract_portfolio(wrestler_id):
    """
    Generate a complete contract portfolio showing all contracts,
    incentives, performance, and history.
    """
    try:
        universe = get_universe()
        database = get_database()
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        # Get everything
        current_card = api_generate_contract_card(wrestler_id).get_json()
        history = database.get_wrestler_contract_history(wrestler_id)
        
        portfolio = {
            'wrestler': {
                'id': wrestler.id,
                'name': wrestler.name,
                'age': wrestler.age,
                'years_experience': wrestler.years_experience
            },
            'current_contract': current_card,
            'contract_history': history,
            'career_summary': {
                'total_contracts': len(history),
                'total_value_earned': sum(h['salary_per_show'] * h['contract_weeks'] * 3 for h in history),
                'total_bonuses': sum(h.get('signing_bonus', 0) for h in history),
                'average_contract_length': sum(h['contract_weeks'] for h in history) / len(history) if history else 0
            },
            'generated_at': datetime.now().isoformat()
        }
        
        return jsonify(portfolio)
    
    except Exception as e:
        print(f"Error generating portfolio: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@contract_bp.route('/api/contracts/compare-cards', methods=['POST'])
def api_compare_contract_cards():
    """
    Compare multiple contract cards side-by-side.
    Great for comparing offers or tracking career progression.
    """
    try:
        data = request.get_json()
        wrestler_ids = data.get('wrestler_ids', [])
        
        if not wrestler_ids or len(wrestler_ids) < 2:
            return jsonify({'error': 'Provide at least 2 wrestler IDs'}), 400
        
        cards = []
        for wid in wrestler_ids:
            card_response = api_generate_contract_card(wid)
            if card_response.status_code == 200:
                cards.append(card_response.get_json())
        
        # Generate comparison matrix
        comparison = {
            'wrestlers': [c['wrestler']['name'] for c in cards],
            'cards': cards,
            'comparison_matrix': {
                'salaries': [c['contract']['current_salary'] for c in cards],
                'scores': [c['score'] for c in cards],
                'grades': [c['grade'] for c in cards],
                'incentive_counts': [len(c['incentives']) for c in cards],
                'creative_control': [c['contract']['creative_control'] for c in cards]
            },
            'winner': {
                'best_salary': max(cards, key=lambda c: c['contract']['current_salary'])['wrestler']['name'],
                'best_score': max(cards, key=lambda c: c['score'])['wrestler']['name'],
                'most_incentives': max(cards, key=lambda c: len(c['incentives']))['wrestler']['name']
            }
        }
        
        return jsonify(comparison)
    
    except Exception as e:
        print(f"Error comparing cards: {e}")
        return jsonify({'error': str(e)}), 500


@contract_bp.route('/api/contracts/compare-wrestlers', methods=['POST'])
def api_compare_wrestler_contracts():
    """
    Compare contracts of multiple wrestlers side-by-side.
    Useful for roster analysis and budget planning.
    """
    try:
        universe = get_universe()
        data = request.get_json()
        database = get_database()
        wrestler_ids = data.get('wrestler_ids', [])
        
        if not wrestler_ids or len(wrestler_ids) < 2:
            return jsonify({'error': 'Provide at least 2 wrestler IDs'}), 400
        
        comparisons = []
        
        for wid in wrestler_ids:
            wrestler = universe.get_wrestler_by_id(wid)
            if not wrestler:
                continue
            
            market_value = contract_manager.calculate_market_value(wrestler)
            
            # Load incentives
            incentives = database.load_contract_incentives(wid)
            
            # Calculate total contract value
            base_value = wrestler.contract.salary_per_show * wrestler.contract.weeks_remaining * 3
            
            comparisons.append({
                'wrestler_id': wid,
                'wrestler_name': wrestler.name,
                'role': wrestler.role,
                'brand': wrestler.primary_brand,
                'contract': {
                    'current_salary': wrestler.contract.salary_per_show,
                    'market_value': market_value,
                    'salary_vs_market': ((wrestler.contract.salary_per_show - market_value) / market_value * 100) if market_value > 0 else 0,
                    'weeks_remaining': wrestler.contract.weeks_remaining,
                    'total_value_remaining': base_value,
                    'base_salary': wrestler.contract.base_salary,
                    'escalated_salary': wrestler.contract.current_escalated_salary,
                    'merchandise_share': wrestler.contract.merchandise_share_percentage,
                    'creative_control': wrestler.contract.creative_control_level.value if hasattr(wrestler.contract.creative_control_level, 'value') else wrestler.contract.creative_control_level,
                    'guaranteed_ppv': wrestler.contract.guaranteed_ppv_appearances,
                    'has_no_trade': wrestler.contract.has_no_trade_clause,
                    'has_injury_protection': wrestler.contract.has_injury_protection
                },
                'incentives': {
                    'count': len(incentives),
                    'types': list(set([i.incentive_type.value for i in incentives]))
                },
                'performance': {
                    'morale': wrestler.morale,
                    'popularity': wrestler.popularity,
                    'momentum': wrestler.momentum
                }
            })
        
        # Generate comparison insights
        insights = _generate_comparison_insights(comparisons)
        
        return jsonify({
            'success': True,
            'wrestlers_compared': len(comparisons),
            'comparisons': comparisons,
            'insights': insights
        })
        
    except Exception as e:
        print(f"Error comparing contracts: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def _generate_comparison_insights(comparisons: List[Dict]) -> Dict[str, Any]:
    """Generate insights from contract comparisons"""
    if not comparisons:
        return {}
    
    # Find highest/lowest salaries
    highest_salary = max(comparisons, key=lambda c: c['contract']['current_salary'])
    lowest_salary = min(comparisons, key=lambda c: c['contract']['current_salary'])
    
    # Find best/worst value
    best_value = min(comparisons, key=lambda c: c['contract']['salary_vs_market'])
    worst_value = max(comparisons, key=lambda c: c['contract']['salary_vs_market'])
    
    # Total remaining obligations
    total_obligation = sum(c['contract']['total_value_remaining'] for c in comparisons)
    
    # Average values
    avg_salary = sum(c['contract']['current_salary'] for c in comparisons) / len(comparisons)
    avg_weeks = sum(c['contract']['weeks_remaining'] for c in comparisons) / len(comparisons)
    
    return {
        'highest_paid': {
            'wrestler': highest_salary['wrestler_name'],
            'salary': highest_salary['contract']['current_salary']
        },
        'lowest_paid': {
            'wrestler': lowest_salary['wrestler_name'],
            'salary': lowest_salary['contract']['current_salary']
        },
        'best_value': {
            'wrestler': best_value['wrestler_name'],
            'percentage': round(best_value['contract']['salary_vs_market'], 1)
        },
        'worst_value': {
            'wrestler': worst_value['wrestler_name'],
            'percentage': round(worst_value['contract']['salary_vs_market'], 1)
        },
        'totals': {
            'combined_obligation': total_obligation,
            'average_salary': round(avg_salary),
            'average_weeks_remaining': round(avg_weeks, 1)
        }
    }


# ========================================================================
# Contract Projection Endpoints
# ========================================================================

@contract_bp.route('/api/contracts/projections/wrestler/<wrestler_id>')
def api_project_wrestler_cost(wrestler_id):
    """Project a single wrestler's costs over 3 years"""
    try:
        from economy.contract_projections import contract_projector
        universe = get_universe()
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        years = request.args.get('years', 3, type=int)
        
        projection = contract_projector.project_wrestler_cost(wrestler, years)
        
        return jsonify(projection)
        
    except Exception as e:
        print(f"Error projecting wrestler cost: {e}")
        return jsonify({'error': str(e)}), 500


@contract_bp.route('/api/contracts/projections/roster')
def api_project_roster_costs():
    """Project total roster costs over 3 years"""
    try:
        from economy.contract_projections import contract_projector
        universe = get_universe()
        
        years = request.args.get('years', 3, type=int)
        
        projection = contract_projector.project_roster_costs(
            get_contract_roster(),
            years
        )
        
        return jsonify(projection)
        
    except Exception as e:
        print(f"Error projecting roster costs: {e}")
        return jsonify({'error': str(e)}), 500


@contract_bp.route('/api/contracts/projections/cliffs')
def api_identify_contract_cliffs():
    """Identify contract cliff periods"""
    try:
        from economy.contract_projections import contract_projector
        universe = get_universe()
        
        years = request.args.get('years', 3, type=int)
        
        cliffs = contract_projector.identify_contract_cliffs(
            get_contract_roster(),
            years
        )
        
        return jsonify({
            'total_cliffs_identified': len(cliffs),
            'cliffs': cliffs
        })
        
    except Exception as e:
        print(f"Error identifying cliffs: {e}")
        return jsonify({'error': str(e)}), 500


@contract_bp.route('/api/contracts/projections/budget-analysis', methods=['POST'])
def api_budget_scenario_analysis():
    """Analyze budget scenarios"""
    try:
        from economy.contract_projections import contract_projector
        universe = get_universe()
        
        data = request.get_json()
        annual_budget = data.get('annual_budget', 5000000)
        years = data.get('years', 3)
        
        analysis = contract_projector.budget_scenario_analysis(
            get_contract_roster(),
            annual_budget,
            years
        )
        
        return jsonify(analysis)
        
    except Exception as e:
        print(f"Error analyzing budget: {e}")
        return jsonify({'error': str(e)}), 500


# ========================================================================
# Contract Promises Tracking Endpoints
# ========================================================================

@contract_bp.route('/api/contracts/promises')
def api_get_all_promises():
    """Get all active contract promises"""
    try:
        database = get_database()
        cursor = database.conn.cursor()
        
        # Ensure table exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contract_promises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                promise_type TEXT NOT NULL,
                wrestler_id TEXT NOT NULL,
                promised_year INTEGER NOT NULL,
                promised_week INTEGER NOT NULL,
                deadline_weeks INTEGER NOT NULL,
                fulfilled INTEGER DEFAULT 0,
                fulfilled_year INTEGER,
                fulfilled_week INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
            )
        ''')
        
        cursor.execute('''
            SELECT * FROM contract_promises 
            WHERE fulfilled = 0
            ORDER BY promised_year, promised_week
        ''')
        
        rows = cursor.fetchall()
        
        promises = []
        for row in rows:
            promises.append({
                'id': row['id'],
                'promise_type': row['promise_type'],
                'wrestler_id': row['wrestler_id'],
                'promised_year': row['promised_year'],
                'promised_week': row['promised_week'],
                'deadline_weeks': row['deadline_weeks'],
                'fulfilled': bool(row['fulfilled']),
                'created_at': row['created_at']
            })
        
        return jsonify({
            'total_promises': len(promises),
            'promises': promises
        })
        
    except Exception as e:
        print(f"Error getting promises: {e}")
        return jsonify({'error': str(e)}), 500


@contract_bp.route('/api/contracts/promises/<int:promise_id>/fulfill', methods=['POST'])
def api_fulfill_promise(promise_id):
    """Mark a promise as fulfilled"""
    try:
        database = get_database()
        state = database.get_game_state()
        cursor = database.conn.cursor()
        
        cursor.execute('''
            UPDATE contract_promises
            SET fulfilled = 1, fulfilled_year = ?, fulfilled_week = ?
            WHERE id = ?
        ''', (state['current_year'], state['current_week'], promise_id))
        
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'message': 'Promise fulfilled'
        })
        
    except Exception as e:
        print(f"Error fulfilling promise: {e}")
        return jsonify({'error': str(e)}), 500


@contract_bp.route('/api/contracts/promises/overdue')
def api_get_overdue_promises():
    """Get promises that are past their deadline"""
    try:
        database = get_database()
        universe = get_universe()
        state = database.get_game_state()
        cursor = database.conn.cursor()
        
        # Ensure table exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contract_promises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                promise_type TEXT NOT NULL,
                wrestler_id TEXT NOT NULL,
                promised_year INTEGER NOT NULL,
                promised_week INTEGER NOT NULL,
                deadline_weeks INTEGER NOT NULL,
                fulfilled INTEGER DEFAULT 0,
                fulfilled_year INTEGER,
                fulfilled_week INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
            )
        ''')
        
        cursor.execute('''
            SELECT * FROM contract_promises 
            WHERE fulfilled = 0
        ''')
        
        rows = cursor.fetchall()
        
        overdue = []
        current_total_weeks = state['current_year'] * 52 + state['current_week']
        
        for row in rows:
            promise_total_weeks = row['promised_year'] * 52 + row['promised_week']
            deadline_total_weeks = promise_total_weeks + row['deadline_weeks']
            
            if current_total_weeks > deadline_total_weeks:
                wrestler = universe.get_wrestler_by_id(row['wrestler_id'])
                overdue.append({
                    'id': row['id'],
                    'promise_type': row['promise_type'],
                    'wrestler_id': row['wrestler_id'],
                    'wrestler_name': wrestler.name if wrestler else 'Unknown',
                    'promised_year': row['promised_year'],
                    'promised_week': row['promised_week'],
                    'deadline_weeks': row['deadline_weeks'],
                    'weeks_overdue': current_total_weeks - deadline_total_weeks
                })
        
        return jsonify({
            'total_overdue': len(overdue),
            'overdue_promises': overdue
        })
        
    except Exception as e:
        print(f"Error getting overdue promises: {e}")
        return jsonify({'error': str(e)}), 500


@contract_bp.route('/api/contracts/promises/wrestler/<wrestler_id>')
def api_get_wrestler_promises(wrestler_id):
    """Get all promises for a specific wrestler"""
    try:
        database = get_database()
        universe = get_universe()
        state = database.get_game_state()
        cursor = database.conn.cursor()
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        # Ensure table exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contract_promises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                promise_type TEXT NOT NULL,
                wrestler_id TEXT NOT NULL,
                promised_year INTEGER NOT NULL,
                promised_week INTEGER NOT NULL,
                deadline_weeks INTEGER NOT NULL,
                fulfilled INTEGER DEFAULT 0,
                fulfilled_year INTEGER,
                fulfilled_week INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
            )
        ''')
        
        cursor.execute('''
            SELECT * FROM contract_promises 
            WHERE wrestler_id = ?
            ORDER BY promised_year DESC, promised_week DESC
        ''', (wrestler_id,))
        
        rows = cursor.fetchall()
        
        current_total_weeks = state['current_year'] * 52 + state['current_week']
        
        promises = []
        for row in rows:
            promise_total_weeks = row['promised_year'] * 52 + row['promised_week']
            deadline_total_weeks = promise_total_weeks + row['deadline_weeks']
            weeks_until_deadline = deadline_total_weeks - current_total_weeks
            
            promises.append({
                'id': row['id'],
                'promise_type': row['promise_type'],
                'promised_year': row['promised_year'],
                'promised_week': row['promised_week'],
                'deadline_weeks': row['deadline_weeks'],
                'fulfilled': bool(row['fulfilled']),
                'fulfilled_year': row['fulfilled_year'],
                'fulfilled_week': row['fulfilled_week'],
                'weeks_until_deadline': weeks_until_deadline if not row['fulfilled'] else None,
                'is_overdue': weeks_until_deadline < 0 and not row['fulfilled'],
                'created_at': row['created_at']
            })
        
        return jsonify({
            'wrestler_id': wrestler_id,
            'wrestler_name': wrestler.name,
            'total_promises': len(promises),
            'active_promises': len([p for p in promises if not p['fulfilled']]),
            'fulfilled_promises': len([p for p in promises if p['fulfilled']]),
            'overdue_promises': len([p for p in promises if p.get('is_overdue', False)]),
            'promises': promises
        })
        
    except Exception as e:
        print(f"Error getting wrestler promises: {e}")
        return jsonify({'error': str(e)}), 500

# ========================================================================
# STEP 121: Missing Promise & Loyalty Endpoints
# ========================================================================

@contract_bp.route('/api/contracts/promises/active')
def api_get_active_promises():
    """Get all active contract promises"""
    try:
        database = get_database()
        
        wrestler_id = request.args.get('wrestler_id')
        
        # Check if table exists
        cursor = database.conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='contract_promises'
        """)
        
        if not cursor.fetchone():
            # Table doesn't exist yet - create it
            database.create_contract_promises_table()
            return jsonify({
                'success': True,
                'total': 0,
                'promises': [],
                'message': 'Promises table created'
            })
        
        active_promises = database.get_active_promises(wrestler_id)
        
        return jsonify({
            'success': True,
            'total': len(active_promises),
            'promises': active_promises
        })
    
    except Exception as e:
        print(f"Error getting active promises: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@contract_bp.route('/api/contracts/loyalty-discount/<wrestler_id>')
def api_get_loyalty_discount(wrestler_id):
    """Calculate loyalty discount for a wrestler"""
    try:
        universe = get_universe()
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        # Get market value
        from economy.contracts import contract_manager
        market_value = contract_manager.calculate_market_value(wrestler)
        
        # Calculate loyalty discount
        discount_data = contract_manager.calculate_loyalty_discount(wrestler, market_value)
        
        return jsonify({
            'success': True,
            'wrestler_id': wrestler_id,
            'wrestler_name': wrestler.name,
            **discount_data
        })
    
    except Exception as e:
        print(f"Error calculating loyalty discount: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@contract_bp.route('/api/contracts/brand-transfer/<wrestler_id>', methods=['POST'])
def api_execute_brand_transfer(wrestler_id):
    """Execute a brand transfer"""
    try:
        universe = get_universe()
        database = get_database()
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        data = request.get_json()
        target_brand = data.get('target_brand')
        reason = data.get('reason', 'Management decision')
        
        from economy.contracts import contract_manager
        
        # Execute transfer
        result = contract_manager.execute_brand_transfer(wrestler, target_brand, reason)
        
        if result['success']:
            # Save wrestler
            universe.save_wrestler(wrestler)
            database.conn.commit()
        
        return jsonify(result)
    
    except Exception as e:
        print(f"Error executing brand transfer: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ========================================================================
# STEP 125: Contract Expiration Storyline Endpoints
# ========================================================================

@contract_bp.route('/api/contracts/storylines/available')
def api_get_available_storylines():
    """Get all wrestlers eligible for contract storylines"""
    try:
        from creative.contract_storylines import contract_storyline_engine
        universe = get_universe()
        database = get_database()
        
        state = database.get_game_state()
        current_year = state['current_year']
        current_week = state['current_week']
        
        # Get next major PPV
        next_ppv = _get_next_major_ppv(current_week)
        
        eligible = []
        for wrestler in universe.get_active_wrestlers():
            if contract_storyline_engine.should_generate_storyline(wrestler, current_year, current_week):
                # Determine what storyline would be generated
                storyline_type = contract_storyline_engine._determine_storyline_type(
                    wrestler, 
                    wrestler.contract.weeks_remaining
                )
                
                eligible.append({
                    'wrestler_id': wrestler.id,
                    'wrestler_name': wrestler.name,
                    'weeks_remaining': wrestler.contract.weeks_remaining,
                    'morale': wrestler.morale,
                    'popularity': wrestler.popularity,
                    'is_major_superstar': wrestler.is_major_superstar,
                    'recommended_storyline': storyline_type.value if storyline_type else None
                })
        
        return jsonify({
            'success': True,
            'total_eligible': len(eligible),
            'eligible_wrestlers': eligible
        })
    
    except Exception as e:
        print(f"Error getting available storylines: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@contract_bp.route('/api/contracts/storylines/active')
def api_get_active_storylines():
    """Get all active contract storylines"""
    try:
        from creative.contract_storylines import contract_storyline_engine
        
        active = contract_storyline_engine.get_active_storylines()
        
        return jsonify({
            'success': True,
            'total_active': len(active),
            'storylines': [s.to_dict() for s in active]
        })
    
    except Exception as e:
        print(f"Error getting active storylines: {e}")
        return jsonify({'error': str(e)}), 500


@contract_bp.route('/api/contracts/storylines/generate/<wrestler_id>', methods=['POST'])
def api_generate_contract_storyline(wrestler_id):
    """Generate a contract storyline for a wrestler"""
    try:
        from creative.contract_storylines import contract_storyline_engine
        universe = get_universe()
        database = get_database()
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        state = database.get_game_state()
        current_year = state['current_year']
        current_week = state['current_week']
        
        # Get next major PPV
        next_ppv = _get_next_major_ppv(current_week)
        
        # Check eligibility
        if not contract_storyline_engine.should_generate_storyline(wrestler, current_year, current_week):
            return jsonify({
                'error': f'{wrestler.name} is not eligible for a contract storyline',
                'reasons': _get_ineligibility_reasons(wrestler, contract_storyline_engine)
            }), 400
        
        # Generate storyline
        storyline = contract_storyline_engine.generate_storyline_for_wrestler(
            wrestler,
            current_year,
            current_week,
            next_ppv
        )
        
        if not storyline:
            return jsonify({'error': 'Failed to generate storyline'}), 500
        
        # Save to database
        _save_storyline_to_db(database, storyline)
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'message': f'Contract storyline created for {wrestler.name}',
            'storyline': storyline.to_dict()
        })
    
    except Exception as e:
        print(f"Error generating storyline: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@contract_bp.route('/api/contracts/storylines/<storyline_id>/progress', methods=['POST'])
def api_progress_storyline(storyline_id):
    """Progress a storyline to the next beat"""
    try:
        from creative.contract_storylines import contract_storyline_engine
        database = get_database()
        
        data = request.get_json()
        segment_summary = data.get('segment_summary', 'Storyline progressed')
        
        # Progress storyline
        can_continue = contract_storyline_engine.progress_storyline(storyline_id, segment_summary)
        
        # Get updated storyline
        storyline = contract_storyline_engine._get_storyline_by_id(storyline_id)
        
        if not storyline:
            return jsonify({'error': 'Storyline not found'}), 404
        
        # Update in database
        _update_storyline_in_db(database, storyline)
        database.conn.commit()
        
        # Get current segment
        current_segment = contract_storyline_engine.get_current_segment(storyline_id)
        
        return jsonify({
            'success': True,
            'can_continue': can_continue,
            'current_beat': storyline.current_beat,
            'total_beats': storyline.total_beats,
            'status': storyline.status.value,
            'current_segment': current_segment,
            'storyline': storyline.to_dict()
        })
    
    except Exception as e:
        print(f"Error progressing storyline: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@contract_bp.route('/api/contracts/storylines/<storyline_id>/resolve', methods=['POST'])
def api_resolve_storyline(storyline_id):
    """Resolve a contract storyline"""
    try:
        from creative.contract_storylines import contract_storyline_engine
        universe = get_universe()
        database = get_database()
        
        data = request.get_json()
        outcome = data.get('outcome')  # 'stayed', 'left', 'retired', 'cancelled'
        resolution_details = data.get('resolution_details', '')
        
        if outcome not in ['stayed', 'left', 'retired', 'cancelled']:
            return jsonify({'error': 'Invalid outcome. Must be: stayed, left, retired, or cancelled'}), 400
        
        # Resolve storyline
        contract_storyline_engine.resolve_storyline(storyline_id, outcome, resolution_details)
        
        # Get storyline
        storyline = contract_storyline_engine._get_storyline_by_id(storyline_id)
        
        if not storyline:
            return jsonify({'error': 'Storyline not found'}), 404
        
        # Apply outcome to wrestler
        wrestler = universe.get_wrestler_by_id(storyline.wrestler_id)
        if wrestler and outcome == 'stayed':
            # Morale boost for successful resolution
            wrestler.adjust_morale(10)
            universe.save_wrestler(wrestler)
        
        # Update in database
        _update_storyline_in_db(database, storyline)
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'message': f'Storyline resolved: {outcome}',
            'storyline': storyline.to_dict()
        })
    
    except Exception as e:
        print(f"Error resolving storyline: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@contract_bp.route('/api/contracts/storylines/<storyline_id>/cancel', methods=['POST'])
def api_cancel_storyline(storyline_id):
    """Cancel a contract storyline (e.g., wrestler signed early)"""
    try:
        from creative.contract_storylines import contract_storyline_engine
        database = get_database()
        
        data = request.get_json()
        reason = data.get('reason', 'Cancelled by management')
        
        contract_storyline_engine.cancel_storyline(storyline_id, reason)
        
        storyline = contract_storyline_engine._get_storyline_by_id(storyline_id)
        
        if storyline:
            _update_storyline_in_db(database, storyline)
            database.conn.commit()
        
        return jsonify({
            'success': True,
            'message': 'Storyline cancelled',
            'storyline': storyline.to_dict() if storyline else None
        })
    
    except Exception as e:
        print(f"Error cancelling storyline: {e}")
        return jsonify({'error': str(e)}), 500


@contract_bp.route('/api/contracts/storylines/wrestler/<wrestler_id>')
def api_get_wrestler_storylines(wrestler_id):
    """Get all storylines for a wrestler"""
    try:
        from creative.contract_storylines import contract_storyline_engine
        universe = get_universe()
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        storylines = contract_storyline_engine.get_storylines_for_wrestler(wrestler_id)
        
        return jsonify({
            'success': True,
            'wrestler_id': wrestler_id,
            'wrestler_name': wrestler.name,
            'total_storylines': len(storylines),
            'storylines': [s.to_dict() for s in storylines]
        })
    
    except Exception as e:
        print(f"Error getting wrestler storylines: {e}")
        return jsonify({'error': str(e)}), 500


# ========================================================================
# STEP 125: Enhanced Promise Management Endpoints
# ========================================================================

@contract_bp.route('/api/contracts/<wrestler_id>/promises')
def api_get_wrestler_promise_details(wrestler_id):
    """Get detailed promise information for a wrestler"""
    try:
        database = get_database()
        universe = get_universe()
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        # Get promises categorized
        promises = database.get_wrestler_promises(wrestler_id)
        
        # Calculate trust rating
        total_promises = len(promises['active']) + len(promises['fulfilled']) + len(promises['broken'])
        
        if total_promises == 0:
            trust_rating = 'NEW'
        else:
            fulfillment_rate = len(promises['fulfilled']) / total_promises
            
            if fulfillment_rate >= 0.9:
                trust_rating = 'EXCELLENT'
            elif fulfillment_rate >= 0.7:
                trust_rating = 'GOOD'
            elif fulfillment_rate >= 0.5:
                trust_rating = 'FAIR'
            elif fulfillment_rate >= 0.3:
                trust_rating = 'POOR'
            else:
                trust_rating = 'TERRIBLE'
        
        return jsonify({
            'success': True,
            'wrestler_id': wrestler_id,
            'wrestler_name': wrestler.name,
            'promises': promises,
            'summary': {
                'active_count': len(promises['active']),
                'fulfilled_count': len(promises['fulfilled']),
                'broken_count': len(promises['broken']),
                'total_count': total_promises,
                'trust_rating': trust_rating,
                'fulfillment_rate': round(len(promises['fulfilled']) / total_promises * 100, 1) if total_promises > 0 else 0
            }
        })
    
    except Exception as e:
        print(f"Error getting promise details: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@contract_bp.route('/api/contracts/promises/<int:promise_id>/break', methods=['POST'])
def api_break_promise(promise_id):
    """Break a promise (apply morale penalty)"""
    try:
        database = get_database()
        universe = get_universe()
        
        data = request.get_json()
        reason = data.get('reason', 'Promise not fulfilled')
        
        # Get promise details first
        cursor = database.conn.cursor()
        cursor.execute('SELECT * FROM contract_promises WHERE id = ?', (promise_id,))
        promise_row = cursor.fetchone()
        
        if not promise_row:
            return jsonify({'error': 'Promise not found'}), 404
        
        wrestler_id = promise_row['wrestler_id']
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        # Apply morale penalty
        morale_penalty = -20
        wrestler.adjust_morale(morale_penalty)
        
        # Mark promise as broken
        database.break_promise(promise_id, reason, abs(morale_penalty))
        
        # Save wrestler
        universe.save_wrestler(wrestler)
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'message': f'Promise broken. {wrestler.name} lost {abs(morale_penalty)} morale.',
            'morale_penalty': morale_penalty,
            'new_morale': wrestler.morale,
            'wrestler': wrestler.to_dict()
        })
    
    except Exception as e:
        print(f"Error breaking promise: {e}")
        import traceback
        traceback.print_exc()
        database.conn.rollback()
        return jsonify({'error': str(e)}), 500


@contract_bp.route('/api/contracts/promises/auto-fulfill', methods=['POST'])
def api_auto_fulfill_promises():
    """
    Auto-fulfill promises based on recent actions.
    E.g., if wrestler just had a title match, fulfill title shot promise.
    """
    try:
        database = get_database()
        data = request.get_json()
        
        wrestler_id = data.get('wrestler_id')
        promise_type = data.get('promise_type')
        details = data.get('details', 'Automatically fulfilled')
        
        state = database.get_game_state()
        
        # Find matching promise
        cursor = database.conn.cursor()
        cursor.execute('''
            SELECT * FROM contract_promises
            WHERE wrestler_id = ? AND promise_type = ? AND fulfilled = 0 AND broken = 0
            ORDER BY id ASC
            LIMIT 1
        ''', (wrestler_id, promise_type))
        
        promise = cursor.fetchone()
        
        if not promise:
            return jsonify({
                'success': False,
                'message': 'No matching unfulfilled promise found'
            })
        
        # Fulfill promise
        database.fulfill_promise(
            promise['id'],
            state['current_year'],
            state['current_week'],
            details
        )
        
        return jsonify({
            'success': True,
            'message': f'Promise fulfilled: {promise_type}',
            'promise_id': promise['id']
        })
    
    except Exception as e:
        print(f"Error auto-fulfilling promise: {e}")
        return jsonify({'error': str(e)}), 500


@contract_bp.route('/api/contracts/promises/booking-suggestions')
def api_get_promise_booking_suggestions():
    """
    Get booking suggestions to fulfill active promises.
    E.g., "Book title match for X to fulfill title shot promise"
    """
    try:
        database = get_database()
        universe = get_universe()
        
        active_promises = database.get_active_promises()
        
        suggestions = []
        
        for promise in active_promises:
            wrestler = universe.get_wrestler_by_id(promise['wrestler_id'])
            if not wrestler:
                continue
            
            if promise['promise_type'] == 'title_shot':
                suggestions.append({
                    'priority': 'HIGH',
                    'wrestler_id': wrestler.id,
                    'wrestler_name': wrestler.name,
                    'promise_type': 'title_shot',
                    'suggestion': f'Book {wrestler.name} in a championship match',
                    'recommended_show': 'Next PPV',
                    'promise_id': promise['id']
                })
            
            elif promise['promise_type'] == 'brand_transfer':
                suggestions.append({
                    'priority': 'MEDIUM',
                    'wrestler_id': wrestler.id,
                    'wrestler_name': wrestler.name,
                    'promise_type': 'brand_transfer',
                    'suggestion': f'Transfer {wrestler.name} to promised brand',
                    'recommended_show': 'Next episode',
                    'promise_id': promise['id']
                })
            
            elif promise['promise_type'] == 'main_event_push':
                suggestions.append({
                    'priority': 'MEDIUM',
                    'wrestler_id': wrestler.id,
                    'wrestler_name': wrestler.name,
                    'promise_type': 'main_event_push',
                    'suggestion': f'Feature {wrestler.name} in main event segment',
                    'recommended_show': 'Next 2 weeks',
                    'promise_id': promise['id']
                })
        
        # Sort by priority
        priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
        suggestions.sort(key=lambda s: priority_order.get(s['priority'], 3))
        
        return jsonify({
            'success': True,
            'total_suggestions': len(suggestions),
            'suggestions': suggestions
        })
    
    except Exception as e:
        print(f"Error getting booking suggestions: {e}")
        return jsonify({'error': str(e)}), 500


@contract_bp.route('/api/debug/unretire/<wrestler_id>', methods=['POST'])
def api_debug_unretire(wrestler_id):
    """Debug endpoint to un-retire a wrestler"""
    try:
        universe = get_universe()
        database = get_database()
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        wrestler.is_retired = False
        universe.save_wrestler(wrestler)
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'message': f'{wrestler.name} is no longer retired',
            'wrestler': wrestler.to_dict()
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ========================================================================
# Helper Functions for Storylines
# ========================================================================

def _get_next_major_ppv(current_week: int) -> Optional[Dict]:
    """Get next major PPV event"""
    # Simplified - you'd integrate with your calendar system
    major_ppvs = [
        {'name': 'Rumble Royale', 'week': 4, 'show_id': 'show_rumble'},
        {'name': 'Clash of Titans', 'week': 12, 'show_id': 'show_clash'},
        {'name': 'Overdrive', 'week': 20, 'show_id': 'show_overdrive'},
        {'name': "Champions' Ascent", 'week': 24, 'show_id': 'show_ascent'},
        {'name': 'Summer Slamfest', 'week': 32, 'show_id': 'show_summer'},
        {'name': 'Autumn Annihilation', 'week': 40, 'show_id': 'show_autumn'},
        {'name': 'Night of Glory', 'week': 44, 'show_id': 'show_glory'},
        {'name': 'Victory Dome', 'week': 52, 'show_id': 'show_victory'}
    ]
    
    for ppv in major_ppvs:
        if ppv['week'] > current_week:
            return ppv
    
    # Wrap to next year
    return major_ppvs[0]


def _get_ineligibility_reasons(wrestler, storyline_engine) -> List[str]:
    """Get reasons why wrestler is ineligible for storyline"""
    reasons = []
    
    if wrestler.is_retired:
        reasons.append('Wrestler is retired')
    
    if wrestler.contract.weeks_remaining > 13:
        reasons.append(f'Contract has {wrestler.contract.weeks_remaining} weeks remaining (needs ≤13)')
    
    if storyline_engine._has_active_storyline(wrestler.id):
        reasons.append('Wrestler already has active contract storyline')
    
    min_popularity = 30 if wrestler.is_major_superstar else 40
    if wrestler.popularity < min_popularity:
        reasons.append(f'Popularity too low ({wrestler.popularity} < {min_popularity})')
    
    if wrestler.injury.severity in ['Major', 'Severe']:
        reasons.append(f'Wrestler has {wrestler.injury.severity} injury')
    
    return reasons


def _save_storyline_to_db(database, storyline):
    """Save storyline to database"""
    cursor = database.conn.cursor()
    
    # Ensure table exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contract_storylines (
            storyline_id TEXT PRIMARY KEY,
            storyline_type TEXT NOT NULL,
            wrestler_id TEXT NOT NULL,
            wrestler_name TEXT NOT NULL,
            status TEXT NOT NULL,
            trigger_year INTEGER NOT NULL,
            trigger_week INTEGER NOT NULL,
            planned_resolution_show TEXT,
            planned_resolution_week INTEGER,
            current_beat INTEGER DEFAULT 0,
            total_beats INTEGER DEFAULT 4,
            description TEXT,
            weekly_segments TEXT,
            outcome TEXT,
            resolution_details TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,  -- ADD THIS LINE IF MISSING
            FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
        )
    ''')
    
    import json
    now = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT OR REPLACE INTO contract_storylines (
            storyline_id, storyline_type, wrestler_id, wrestler_name,
            status, trigger_year, trigger_week,
            planned_resolution_show, planned_resolution_week,
            current_beat, total_beats, description, weekly_segments,
            outcome, resolution_details, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        storyline.storyline_id,
        storyline.storyline_type.value,
        storyline.wrestler_id,
        storyline.wrestler_name,
        storyline.status.value,
        storyline.trigger_year,
        storyline.trigger_week,
        storyline.planned_resolution_show,
        storyline.planned_resolution_week,
        storyline.current_beat,
        storyline.total_beats,
        storyline.description,
        json.dumps(storyline.weekly_segments),
        storyline.outcome,
        storyline.resolution_details,
        now,
        now  # ADD THIS - updated_at value
    ))


def _update_storyline_in_db(database, storyline):
    """Update existing storyline in database"""
    cursor = database.conn.cursor()
    
    import json
    
    cursor.execute('''
        UPDATE contract_storylines
        SET status = ?,
            current_beat = ?,
            outcome = ?,
            resolution_details = ?
        WHERE storyline_id = ?
    ''', (
        storyline.status.value,
        storyline.current_beat,
        storyline.outcome,
        storyline.resolution_details,
        storyline.storyline_id
    ))
