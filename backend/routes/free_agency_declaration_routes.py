"""
Free Agency Declaration Routes
STEP 123: API endpoints for wrestlers testing free agency
"""

from flask import Blueprint, jsonify, request
from models.free_agency_declaration import (
    free_agency_declaration_manager,
    FreeAgencyDeclaration,
    DeclarationType,
    DeclarationStatus
)

free_agency_declaration_bp = Blueprint('free_agency_declaration', __name__)


def get_database():
    from flask import current_app
    return current_app.config['DATABASE']


def get_universe():
    from flask import current_app
    return current_app.config['UNIVERSE']


@free_agency_declaration_bp.route('/api/free-agency/declarations')
def api_get_all_declarations():
    """Get all free agency declarations"""
    try:
        database = get_database()
        declarations = database.load_all_free_agency_declarations()
        
        return jsonify({
            'total': len(declarations),
            'declarations': declarations
        })
        
    except Exception as e:
        print(f"Error loading declarations: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@free_agency_declaration_bp.route('/api/free-agency/declarations/active')
def api_get_active_declarations():
    """Get only active free agency declarations"""
    try:
        database = get_database()
        declarations = database.get_active_free_agency_declarations()
        
        # Enrich with current wrestler data
        universe = get_universe()
        
        for decl in declarations:
            wrestler = universe.get_wrestler_by_id(decl['wrestler_id'])
            if wrestler:
                decl['current_weeks_remaining'] = wrestler.contract.weeks_remaining
                decl['current_morale'] = wrestler.morale
                decl['current_popularity'] = wrestler.popularity
        
        return jsonify({
            'total_active': len(declarations),
            'declarations': declarations
        })
        
    except Exception as e:
        print(f"Error loading active declarations: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@free_agency_declaration_bp.route('/api/free-agency/declare/<wrestler_id>', methods=['POST'])
def api_declare_free_agency(wrestler_id):
    """
    Wrestler declares intention to test free agency.
    
    Body:
    {
        "declaration_type": "testing_market" | "open_to_offers" | "seeking_change" | "leveraging" | "retirement",
        "reasons": ["seeking_title_opportunities", "salary_concerns", "creative_freedom"]
    }
    """
    try:
        universe = get_universe()
        database = get_database()
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        # Check if already has active declaration
        existing = free_agency_declaration_manager.get_declaration_by_wrestler(wrestler_id)
        if existing:
            return jsonify({
                'error': 'Wrestler already has an active free agency declaration',
                'existing_declaration': existing.to_dict()
            }), 400
        
        # Get request data
        data = request.get_json()
        declaration_type = DeclarationType(data.get('declaration_type', 'testing_market'))
        reasons = data.get('reasons', ['exploring_options'])
        
        # Get current game state
        state = database.get_game_state()
        current_year = state['current_year']
        current_week = state['current_week']
        
        # Create declaration
        declaration = free_agency_declaration_manager.create_declaration(
            wrestler,
            declaration_type,
            reasons,
            current_year,
            current_week
        )
        
        # Save to database
        database.save_free_agency_declaration(declaration)
        database.conn.commit()
        
        # Morale impact (varies by type)
        morale_impact = {
            DeclarationType.TESTING_MARKET: -5,
            DeclarationType.OPEN_TO_OFFERS: -3,
            DeclarationType.SEEKING_CHANGE: -10,
            DeclarationType.LEVERAGING: 5,  # Feeling empowered
            DeclarationType.RETIREMENT_CONSIDERATION: -15
        }
        wrestler.adjust_morale(morale_impact.get(declaration_type, 0))
        universe.save_wrestler(wrestler)
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'message': f"{wrestler.name} has declared free agency!",
            'declaration': declaration.to_dict(),
            'media_reaction': generate_media_reaction(declaration),
            'morale_impact': morale_impact.get(declaration_type, 0)
        })
        
    except ValueError as e:
        return jsonify({'error': f'Invalid declaration type: {str(e)}'}), 400
    except Exception as e:
        print(f"Error declaring free agency: {e}")
        import traceback
        traceback.print_exc()
        database.conn.rollback()
        return jsonify({'error': str(e)}), 500


@free_agency_declaration_bp.route('/api/free-agency/withdraw/<wrestler_id>', methods=['POST'])
def api_withdraw_declaration(wrestler_id):
    """
    Wrestler withdraws free agency declaration.
    
    Body:
    {
        "reason": "re_signing" | "changed_mind" | "better_offer_received"
    }
    """
    try:
        universe = get_universe()
        database = get_database()
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        declaration = free_agency_declaration_manager.get_declaration_by_wrestler(wrestler_id)
        if not declaration:
            return jsonify({'error': 'No active declaration found'}), 404
        
        data = request.get_json()
        reason = data.get('reason', 'changed_mind')
        
        state = database.get_game_state()
        
        free_agency_declaration_manager.withdraw_declaration(
            declaration,
            reason,
            state['current_year'],
            state['current_week']
        )
        
        # Save updated declaration
        database.save_free_agency_declaration(declaration)
        
        # Morale boost for resolution
        wrestler.adjust_morale(10)
        universe.save_wrestler(wrestler)
        
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'message': f"{wrestler.name} has withdrawn their free agency declaration",
            'declaration': declaration.to_dict()
        })
        
    except Exception as e:
        print(f"Error withdrawing declaration: {e}")
        import traceback
        traceback.print_exc()
        database.conn.rollback()
        return jsonify({'error': str(e)}), 500


@free_agency_declaration_bp.route('/api/free-agency/counter-offer/<wrestler_id>', methods=['POST'])
def api_make_counter_offer(wrestler_id):
    """
    Make counter-offer to wrestler who declared free agency.
    
    Body:
    {
        "salary_per_show": 30000,
        "weeks": 104,
        "incentives": ["signing_bonus_large", "ppv_guarantee_8"]
    }
    """
    try:
        universe = get_universe()
        database = get_database()
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        declaration = free_agency_declaration_manager.get_declaration_by_wrestler(wrestler_id)
        if not declaration:
            return jsonify({'error': 'No active declaration found'}), 404
        
        data = request.get_json()
        offered_salary = data.get('salary_per_show')
        offered_weeks = data.get('weeks', 52)
        incentives = data.get('incentives', [])
        
        # Record counter-offer
        declaration.current_promotion_counter_offer = offered_salary
        database.save_free_agency_declaration(declaration)
        
        # Evaluate if counter-offer meets or beats rival offers
        beats_rivals = offered_salary >= declaration.highest_rival_offer
        
        # Calculate acceptance probability
        from economy.contract_incentives import incentive_engine
        
        contract, analysis = incentive_engine.build_contract_package(
            wrestler,
            offered_salary,
            offered_weeks,
            incentives
        )
        
        acceptance_prob = analysis['acceptance_probability']
        
        # Bonus if beats rival offers
        if beats_rivals and declaration.highest_rival_offer > 0:
            acceptance_prob += 15
            acceptance_message = f"Your offer beats the highest rival offer of ${declaration.highest_rival_offer:,}/show!"
        else:
            acceptance_message = f"Rival offers are higher (${declaration.highest_rival_offer:,}/show). This may not be enough."
        
        acceptance_prob = min(98, acceptance_prob)
        
        # Roll for acceptance
        import random
        accepted = random.random() * 100 <= acceptance_prob
        
        state = database.get_game_state()
        
        if accepted:
            # Wrestler accepts - re-sign them
            wrestler.contract.salary_per_show = offered_salary
            wrestler.contract.weeks_remaining = offered_weeks
            wrestler.contract.total_length_weeks = offered_weeks
            wrestler.contract.signing_year = state['current_year']
            wrestler.contract.signing_week = state['current_week']
            
            # Apply incentives
            contract.incentives = []
            for template_name in incentives:
                try:
                    incentive = incentive_engine.create_incentive_from_template(template_name)
                    contract.add_incentive(incentive)
                except:
                    pass
            
            wrestler.contract = contract
            
            # Resolve declaration
            free_agency_declaration_manager.resolve_declaration(
                declaration,
                DeclarationStatus.RE_SIGNED,
                f"Re-signed for ${offered_salary:,}/show, {offered_weeks} weeks, {len(incentives)} incentives",
                state['current_year'],
                state['current_week']
            )
            
            # Huge morale boost
            wrestler.adjust_morale(20)
            
            universe.save_wrestler(wrestler)
            database.save_free_agency_declaration(declaration)
            database.conn.commit()
            
            return jsonify({
                'success': True,
                'accepted': True,
                'message': f"🎉 {wrestler.name} ACCEPTED YOUR COUNTER-OFFER!\n\nThey've re-signed for ${offered_salary:,}/show over {offered_weeks} weeks.\n\nMorale: +20\n\n{acceptance_message}",
                'declaration': declaration.to_dict(),
                'wrestler': wrestler.to_dict()
            })
        
        else:
            # Rejected
            wrestler.adjust_morale(-5)
            universe.save_wrestler(wrestler)
            database.conn.commit()
            
            return jsonify({
                'success': True,
                'accepted': False,
                'message': f"❌ {wrestler.name} REJECTED your counter-offer.\n\nThey're still testing the market.\n\nMorale: -5\n\n{acceptance_message}\n\nAcceptance probability was {acceptance_prob:.1f}%",
                'acceptance_probability': acceptance_prob,
                'beats_rivals': beats_rivals,
                'highest_rival_offer': declaration.highest_rival_offer
            })
        
    except Exception as e:
        print(f"Error making counter-offer: {e}")
        import traceback
        traceback.print_exc()
        database.conn.rollback()
        return jsonify({'error': str(e)}), 500


@free_agency_declaration_bp.route('/api/free-agency/simulate-interest/<wrestler_id>', methods=['POST'])
def api_simulate_rival_interest(wrestler_id):
    """
    Manually trigger rival promotion interest simulation.
    (Normally happens automatically each week)
    """
    try:
        universe = get_universe()
        database = get_database()
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        declaration = free_agency_declaration_manager.get_declaration_by_wrestler(wrestler_id)
        if not declaration:
            return jsonify({'error': 'No active declaration found'}), 404
        
        # Simulate rival interest
        old_offer_count = declaration.rival_offers_count
        old_highest = declaration.highest_rival_offer
        
        free_agency_declaration_manager.simulate_rival_interest(declaration, wrestler)
        
        # Save updated declaration
        database.save_free_agency_declaration(declaration)
        database.conn.commit()
        
        new_offers = declaration.rival_offers_count > old_offer_count
        
        if new_offers:
            message = f"📰 BREAKING: Rival promotion has made {wrestler.name} an offer of ${declaration.highest_rival_offer:,}/show!"
        else:
            message = f"No new rival offers this week. Current highest: ${declaration.highest_rival_offer:,}/show"
        
        return jsonify({
            'success': True,
            'new_offer_received': new_offers,
            'message': message,
            'declaration': declaration.to_dict()
        })
        
    except Exception as e:
        print(f"Error simulating interest: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@free_agency_declaration_bp.route('/api/free-agency/check-eligibility/<wrestler_id>')
def api_check_declaration_eligibility(wrestler_id):
    """
    Check if wrestler is eligible to declare free agency.
    
    Rules:
    - Contract must have <= 26 weeks remaining
    - Cannot have existing active declaration
    - Must not be retired
    """
    try:
        universe = get_universe()
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        # Check eligibility
        eligible = True
        reasons = []
        
        if wrestler.is_retired:
            eligible = False
            reasons.append("Wrestler is retired")
        
        if wrestler.contract.weeks_remaining > 26:
            eligible = False
            reasons.append(f"Contract has {wrestler.contract.weeks_remaining} weeks remaining (must be ≤ 26 weeks)")
        
        existing = free_agency_declaration_manager.get_declaration_by_wrestler(wrestler_id)
        if existing:
            eligible = False
            reasons.append("Wrestler already has an active free agency declaration")
        
        # Recommendations
        recommendations = []
        
        if wrestler.morale < 30:
            recommendations.append({
                'type': DeclarationType.SEEKING_CHANGE.value,
                'reason': 'Low morale suggests dissatisfaction'
            })
        
        if wrestler.popularity >= 70:
            recommendations.append({
                'type': DeclarationType.LEVERAGING.value,
                'reason': 'High popularity gives strong leverage'
            })
        
        if wrestler.age >= 40:
            recommendations.append({
                'type': DeclarationType.RETIREMENT_CONSIDERATION.value,
                'reason': 'Age makes retirement consideration realistic'
            })
        
        if not recommendations:
            recommendations.append({
                'type': DeclarationType.TESTING_MARKET.value,
                'reason': 'Standard free agency exploration'
            })
        
        return jsonify({
            'wrestler_id': wrestler_id,
            'wrestler_name': wrestler.name,
            'eligible': eligible,
            'reasons': reasons if not eligible else [],
            'weeks_remaining': wrestler.contract.weeks_remaining,
            'morale': wrestler.morale,
            'recommendations': recommendations
        })
        
    except Exception as e:
        print(f"Error checking eligibility: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def generate_media_reaction(declaration: FreeAgencyDeclaration) -> str:
    """Generate media reaction based on declaration details"""
    reactions = []
    
    if declaration.media_attention >= 80:
        reactions.append("🔥 MAJOR BREAKING NEWS")
    elif declaration.media_attention >= 60:
        reactions.append("📰 Significant Industry Buzz")
    else:
        reactions.append("📝 Wrestling Media Reports")
    
    if declaration.leverage_level >= 70:
        reactions.append("Insiders say multiple promotions are interested")
    
    if declaration.declaration_type == DeclarationType.SEEKING_CHANGE:
        reactions.append("Sources close to the wrestler confirm frustration with current situation")
    
    return " | ".join(reactions)