"""
Agent System Routes (STEP 118)
API endpoints for agent representation and package deals.
"""

from flask import Blueprint, jsonify, request
from models.agent_manager import AgentManager
from models.agent_negotiation import AgentNegotiationTactics, NegotiationHistory

agent_bp = Blueprint('agent', __name__)

# Will be set by app.py
agent_manager = None


def get_free_agent_pool():
    """Get free agent pool from app context"""
    from flask import current_app
    return current_app.config.get('FREE_AGENT_POOL')


def get_universe():
    """Get universe from app context"""
    from flask import current_app
    return current_app.config.get('UNIVERSE')


@agent_bp.route('/api/agents')
def api_get_all_agents():
    """Get list of all agents and their rosters"""
    try:
        if not agent_manager:
            return jsonify({'success': False, 'error': 'Agent manager not initialized'}), 500
        
        agents = agent_manager.get_all_agents()
        
        return jsonify({
            'success': True,
            'total': len(agents),
            'agents': agents
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_bp.route('/api/agents/<agent_name>')
def api_get_agent_roster(agent_name):
    """Get specific agent's roster"""
    try:
        if not agent_manager:
            return jsonify({'success': False, 'error': 'Agent manager not initialized'}), 500
        
        roster = agent_manager.get_agent_roster(agent_name)
        
        if not roster:
            return jsonify({'success': False, 'error': 'Agent not found'}), 404
        
        return jsonify({
            'success': True,
            'agent': roster
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_bp.route('/api/agents/package-dealers')
def api_get_package_dealers():
    """Get all package dealers and their clients"""
    try:
        if not agent_manager:
            return jsonify({'success': False, 'error': 'Agent manager not initialized'}), 500
        
        free_agent_pool = get_free_agent_pool()
        if not free_agent_pool:
            return jsonify({'success': False, 'error': 'Free agent pool not initialized'}), 500
        
        package_dealers = agent_manager.get_package_dealers()
        
        # Get detailed info for each package
        packages = []
        for agent_name, client_ids in package_dealers.items():
            package_info = agent_manager.get_package_deal_info(agent_name, free_agent_pool.available_free_agents)
            if package_info:
                packages.append(package_info)
        
        return jsonify({
            'success': True,
            'total': len(packages),
            'packages': packages
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_bp.route('/api/agents/package-deal/<agent_name>')
def api_get_package_deal(agent_name):
    """Get detailed package deal information"""
    try:
        if not agent_manager:
            return jsonify({'success': False, 'error': 'Agent manager not initialized'}), 500
        
        free_agent_pool = get_free_agent_pool()
        if not free_agent_pool:
            return jsonify({'success': False, 'error': 'Free agent pool not initialized'}), 500
        
        package_info = agent_manager.get_package_deal_info(agent_name, free_agent_pool.available_free_agents)
        
        if not package_info:
            return jsonify({'success': False, 'error': 'Package deal not found'}), 404
        
        return jsonify({
            'success': True,
            'package': package_info
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_bp.route('/api/agents/create-package-deal', methods=['POST'])
def api_create_package_deal():
    """Create a new package deal"""
    try:
        if not agent_manager:
            return jsonify({'success': False, 'error': 'Agent manager not initialized'}), 500
        
        free_agent_pool = get_free_agent_pool()
        if not free_agent_pool:
            return jsonify({'success': False, 'error': 'Free agent pool not initialized'}), 500
        
        data = request.get_json() if request.is_json else {}
        min_clients = data.get('min_clients', 2)
        max_clients = data.get('max_clients', 4)
        
        agent_name = agent_manager.create_package_deal(
            free_agent_pool.available_free_agents,
            min_clients,
            max_clients
        )
        
        if not agent_name:
            return jsonify({
                'success': False,
                'error': 'Not enough available free agents to create package deal'
            }), 400
        
        # Save updated free agents
        free_agent_pool.save_all()
        
        package_info = agent_manager.get_package_deal_info(agent_name, free_agent_pool.available_free_agents)
        
        return jsonify({
            'success': True,
            'message': f'Package deal created with {agent_name}',
            'package': package_info
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_bp.route('/api/negotiate/<fa_id>', methods=['POST'])
def api_negotiate_with_free_agent(fa_id):
    """
    Negotiate with a free agent (and their agent).
    
    POST body:
    {
        "offer_salary": 15000,
        "offer_bonus": 5000,
        "offer_length_weeks": 52,
        "offer_creative_control": 1
    }
    """
    try:
        free_agent_pool = get_free_agent_pool()
        if not free_agent_pool:
            return jsonify({'success': False, 'error': 'Free agent pool not initialized'}), 500
        
        fa = free_agent_pool.get_free_agent_by_id(fa_id)
        if not fa:
            return jsonify({'success': False, 'error': 'Free agent not found'}), 404
        
        data = request.get_json()
        
        offer_salary = data.get('offer_salary', 0)
        offer_bonus = data.get('offer_bonus', 0)
        offer_length_weeks = data.get('offer_length_weeks', 52)
        offer_creative_control = data.get('offer_creative_control', 0)
        
        # Get opening statement (first time negotiating)
        opening_statement = AgentNegotiationTactics.get_negotiation_opening_statement(fa)
        
        # Evaluate offer
        result = AgentNegotiationTactics.evaluate_offer(
            fa,
            offer_salary,
            offer_bonus,
            offer_length_weeks,
            offer_creative_control
        )
        
        # Add leverage statement if applicable
        leverage = AgentNegotiationTactics.generate_agent_leverage_statement(fa)
        
        return jsonify({
            'success': True,
            'free_agent_id': fa_id,
            'free_agent_name': fa.wrestler_name,
            'opening_statement': opening_statement,
            'leverage_statement': leverage,
            'negotiation_result': result,
            'your_offer': {
                'salary': offer_salary,
                'bonus': offer_bonus,
                'length_weeks': offer_length_weeks,
                'creative_control': offer_creative_control
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_bp.route('/api/negotiate/<fa_id>/tips')
def api_get_negotiation_tips(fa_id):
    """Get tips for negotiating with this free agent"""
    try:
        free_agent_pool = get_free_agent_pool()
        if not free_agent_pool:
            return jsonify({'success': False, 'error': 'Free agent pool not initialized'}), 500
        
        fa = free_agent_pool.get_free_agent_by_id(fa_id)
        if not fa:
            return jsonify({'success': False, 'error': 'Free agent not found'}), 404
        
        from models.free_agent_moods import MoodEffects
        
        tips = {
            'mood_tips': MoodEffects.get_negotiation_tips(fa.mood),
            'agent_tips': [],
            'leverage_warnings': []
        }
        
        # Agent-specific tips
        if fa.agent.agent_type.value == 'power_agent':
            tips['agent_tips'] = [
                f"{fa.agent.agent_name} is a power agent - expect tough negotiations",
                "Power agents rarely budge below 95% of asking price",
                "Offering creative control can help seal the deal",
                "Be prepared for aggressive counter-offers"
            ]
        elif fa.agent.agent_type.value == 'package_dealer':
            tips['agent_tips'] = [
                f"{fa.agent.agent_name} represents {len(fa.agent.other_clients) + 1} wrestlers",
                "Consider signing multiple clients for 10-15% discount",
                "Package dealers are more flexible on individual terms",
                f"Other clients available: {len(fa.agent.other_clients)}"
            ]
        elif fa.agent.agent_type.value == 'standard':
            tips['agent_tips'] = [
                f"{fa.agent.agent_name} is a standard agent - straightforward negotiations",
                "Expect reasonable counter-offers",
                "Meeting them halfway usually works"
            ]
        else:
            tips['agent_tips'] = [
                "No agent - negotiate directly with wrestler",
                "Simpler negotiations without agent markup",
                "Personality and mood matter more"
            ]
        
        # Leverage warnings
        if fa.rival_interest:
            active = [r for r in fa.rival_interest if r.offer_made]
            if active:
                tips['leverage_warnings'].append(
                    f"⚠️ {len(active)} rival promotion(s) have made offers"
                )
        
        if fa.is_major_superstar or fa.is_legend:
            tips['leverage_warnings'].append(
                "⚠️ High-profile talent - expect premium demands"
            )
        
        # Calculate agent markup
        markup = AgentNegotiationTactics.calculate_agent_markup(fa)
        markup_pct = (markup - 1.0) * 100
        
        tips['financial_analysis'] = {
            'asking_salary': fa.demands.asking_salary,
            'minimum_salary': fa.demands.minimum_salary,
            'agent_markup': f"{markup_pct:.1f}%",
            'true_market_value': fa.market_value,
            'inflated_asking': fa.demands.asking_salary - fa.market_value
        }
        
        return jsonify({
            'success': True,
            'free_agent': fa.wrestler_name,
            'agent': fa.agent.agent_name if fa.agent.agent_name else 'None',
            'tips': tips
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_bp.route('/api/agents/assign-all', methods=['POST'])
def api_assign_agents_to_pool():
    """Assign agents to all free agents who don't have one"""
    try:
        if not agent_manager:
            return jsonify({'success': False, 'error': 'Agent manager not initialized'}), 500
        
        free_agent_pool = get_free_agent_pool()
        if not free_agent_pool:
            return jsonify({'success': False, 'error': 'Free agent pool not initialized'}), 500
        
        # Count before
        before_count = sum(1 for fa in free_agent_pool.available_free_agents if fa.agent.agent_type.value != 'none')
        
        # Assign agents
        agent_manager.assign_agents_to_pool(free_agent_pool.available_free_agents)
        
        # Count after
        after_count = sum(1 for fa in free_agent_pool.available_free_agents if fa.agent.agent_type.value != 'none')
        
        # Save
        free_agent_pool.save_all()
        
        return jsonify({
            'success': True,
            'message': f'Assigned agents to {after_count - before_count} free agents',
            'before': before_count,
            'after': after_count,
            'total_agents': len(agent_manager.get_all_agents())
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
@agent_bp.route('/api/agents/suggest-packages', methods=['POST'])
def api_suggest_package_deals():
    """
    Suggest potential package deals based on roster needs.
    
    POST body:
    {
        "roster_needs": ["midcard", "tag_team"],
        "max_budget": 50000,
        "preferred_regions": ["japan", "mexico"]
    }
    """
    try:
        if not agent_manager:
            return jsonify({'success': False, 'error': 'Agent manager not initialized'}), 500
        
        free_agent_pool = get_free_agent_pool()
        if not free_agent_pool:
            return jsonify({'success': False, 'error': 'Free agent pool not initialized'}), 500
        
        data = request.get_json() if request.is_json else {}
        roster_needs = data.get('roster_needs', [])
        max_budget = data.get('max_budget', 100000)
        preferred_regions = data.get('preferred_regions', [])
        
        # Get all package dealers
        package_dealers = agent_manager.get_package_dealers()
        
        suggestions = []
        
        for agent_name, client_ids in package_dealers.items():
            package_info = agent_manager.get_package_deal_info(agent_name, free_agent_pool.available_free_agents)
            
            if not package_info:
                continue
            
            # Check if package fits budget
            total_cost = package_info['total_asking_salary']
            discount_multiplier = AgentNegotiationTactics.get_package_deal_discount(package_info['client_count'])
            discounted_cost = int(total_cost * discount_multiplier)
            
            if discounted_cost <= max_budget:
                # Check roster fit
                fit_score = 0
                clients = package_info['clients']
                
                for client in clients:
                    # Role matching
                    if any(need.lower() in client['role'].lower() for need in roster_needs):
                        fit_score += 20
                    
                    # Region matching
                    fa = free_agent_pool.get_free_agent_by_id(client['id'])
                    if fa and fa.origin_region in preferred_regions:
                        fit_score += 15
                    
                    # Value for money
                    if client['market_value'] > client['asking_salary']:
                        fit_score += 10
                
                suggestions.append({
                    'agent_name': agent_name,
                    'package': package_info,
                    'original_cost': total_cost,
                    'discounted_cost': discounted_cost,
                    'savings': total_cost - discounted_cost,
                    'discount_percent': int((1 - discount_multiplier) * 100),
                    'fit_score': fit_score,
                    'recommendation': 'Strong Match' if fit_score >= 40 else 'Moderate Match' if fit_score >= 20 else 'Weak Match'
                })
        
        # Sort by fit score
        suggestions.sort(key=lambda x: x['fit_score'], reverse=True)
        
        return jsonify({
            'success': True,
            'total_suggestions': len(suggestions),
            'suggestions': suggestions,
            'search_criteria': {
                'roster_needs': roster_needs,
                'max_budget': max_budget,
                'preferred_regions': preferred_regions
            }
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@agent_bp.route('/api/agents/expand-package/<agent_name>', methods=['POST'])
def api_expand_package_deal(agent_name):
    """
    Add more clients to an existing package dealer.
    Finds compatible free agents and adds them to the package.
    """
    try:
        if not agent_manager:
            return jsonify({'success': False, 'error': 'Agent manager not initialized'}), 500
        
        free_agent_pool = get_free_agent_pool()
        if not free_agent_pool:
            return jsonify({'success': False, 'error': 'Free agent pool not initialized'}), 500
        
        data = request.get_json() if request.is_json else {}
        max_additions = data.get('max_additions', 2)
        
        # Get current package
        current_package = agent_manager.get_package_deal_info(agent_name, free_agent_pool.available_free_agents)
        
        if not current_package:
            return jsonify({'success': False, 'error': 'Package dealer not found'}), 404
        
        # Get existing agent info
        current_client_ids = [c['id'] for c in current_package['clients']]
        if not current_client_ids:
            return jsonify({'success': False, 'error': 'Package has no clients'}), 400
        
        sample_client = free_agent_pool.get_free_agent_by_id(current_client_ids[0])
        if not sample_client:
            return jsonify({'success': False, 'error': 'Sample client not found'}), 404
        
        agent_info = sample_client.agent
        
        # Find compatible free agents (no agent, similar value range)
        avg_value = current_package['total_package_value'] / current_package['client_count']
        value_range = (avg_value * 0.5, avg_value * 1.5)  # ±50% range
        
        compatible = []
        for fa in free_agent_pool.available_free_agents:
            if fa.agent.agent_type.value == 'none' and fa.id not in current_client_ids:
                if value_range[0] <= fa.market_value <= value_range[1]:
                    compatible.append(fa)
        
        if not compatible:
            return jsonify({
                'success': False,
                'error': 'No compatible free agents available for this package'
            }), 400
        
        # Select random compatible free agents
        import random
        additions = random.sample(compatible, min(max_additions, len(compatible)))
        
        # Add to package
        from models.free_agent import AgentInfo
        
        for fa in additions:
            # Update other_clients for all package members
            all_package_ids = current_client_ids + [fa.id]
            
            fa.agent = AgentInfo(
                agent_type=agent_info.agent_type,
                agent_name=agent_name,
                commission_rate=agent_info.commission_rate,
                other_clients=[cid for cid in all_package_ids if cid != fa.id],
                negotiation_difficulty=agent_info.negotiation_difficulty
            )
            
            agent_manager._register_agent(fa.agent, fa.id)
        
        # Update existing clients' other_clients list
        for client_id in current_client_ids:
            client = free_agent_pool.get_free_agent_by_id(client_id)
            if client:
                all_package_ids = current_client_ids + [fa.id for fa in additions]
                client.agent.other_clients = [cid for cid in all_package_ids if cid != client_id]
        
        # Save
        free_agent_pool.save_all()
        
        # Get updated package info
        updated_package = agent_manager.get_package_deal_info(agent_name, free_agent_pool.available_free_agents)
        
        return jsonify({
            'success': True,
            'message': f'Added {len(additions)} wrestlers to {agent_name}\'s package',
            'added': [{'id': fa.id, 'name': fa.wrestler_name} for fa in additions],
            'package': updated_package
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500
    
@agent_bp.route('/api/negotiate/<fa_id>/simulate', methods=['POST'])
def api_simulate_full_negotiation(fa_id):
    """
    Simulate a full multi-round negotiation to find optimal offer.
    
    POST body:
    {
        "max_salary": 50000,
        "max_bonus": 20000,
        "max_creative_control": 2,
        "max_rounds": 5
    }
    """
    try:
        free_agent_pool = get_free_agent_pool()
        if not free_agent_pool:
            return jsonify({'success': False, 'error': 'Free agent pool not initialized'}), 500
        
        fa = free_agent_pool.get_free_agent_by_id(fa_id)
        if not fa:
            return jsonify({'success': False, 'error': 'Free agent not found'}), 404
        
        data = request.get_json()
        
        max_salary = data.get('max_salary', 100000)
        max_bonus = data.get('max_bonus', 50000)
        max_creative_control = data.get('max_creative_control', 3)
        max_rounds = data.get('max_rounds', 5)
        
        # Simulate negotiation rounds
        history = NegotiationHistory()
        current_offer = {
            'salary': fa.demands.minimum_salary,
            'bonus': 0,
            'length_weeks': 52,
            'creative_control': 0
        }
        
        for round_num in range(1, max_rounds + 1):
            result = AgentNegotiationTactics.evaluate_offer(
                fa,
                current_offer['salary'],
                current_offer['bonus'],
                current_offer['length_weeks'],
                current_offer['creative_control']
            )
            
            history.add_round(round_num, current_offer.copy(), result)
            
            if result['accepted']:
                break
            
            # If rejected, try to meet counter-offer
            if result['counter_offer']:
                counter = result['counter_offer']
                
                # Meet halfway between current and counter
                new_salary = min(
                    (current_offer['salary'] + counter['salary']) // 2,
                    max_salary
                )
                new_bonus = min(
                    (current_offer['bonus'] + counter['signing_bonus']) // 2,
                    max_bonus
                )
                new_creative = min(
                    (current_offer['creative_control'] + counter['creative_control']) // 2,
                    max_creative_control
                )
                
                current_offer = {
                    'salary': new_salary,
                    'bonus': new_bonus,
                    'length_weeks': counter['length_weeks'],
                    'creative_control': new_creative
                }
            else:
                # No counter-offer provided, increase by 10%
                current_offer['salary'] = min(int(current_offer['salary'] * 1.1), max_salary)
                current_offer['bonus'] = min(int(current_offer['bonus'] * 1.1), max_bonus)
        
        summary = history.get_summary()
        
        # Find optimal offer
        optimal = None
        for round_data in summary['rounds']:
            if round_data['response']['accepted']:
                optimal = round_data['offer']
                break
        
        return jsonify({
            'success': True,
            'free_agent': fa.wrestler_name,
            'agent': fa.agent.agent_name if fa.agent.agent_name else 'None',
            'simulation': {
                'total_rounds': summary['total_rounds'],
                'deal_reached': summary['final_result'],
                'rounds': summary['rounds'],
                'optimal_offer': optimal,
                'total_cost': (optimal['salary'] * 52 + optimal['bonus']) if optimal else None
            }
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500
    
@agent_bp.route('/api/agents/statistics')
def api_get_agent_statistics():
    """Get comprehensive agent system statistics"""
    try:
        if not agent_manager:
            return jsonify({'success': False, 'error': 'Agent manager not initialized'}), 500
        
        free_agent_pool = get_free_agent_pool()
        if not free_agent_pool:
            return jsonify({'success': False, 'error': 'Free agent pool not initialized'}), 500
        
        all_agents = agent_manager.get_all_agents()
        all_free_agents = free_agent_pool.available_free_agents
        
        # Count by type
        type_counts = {
            'none': 0,
            'standard': 0,
            'power_agent': 0,
            'package_dealer': 0
        }
        
        total_commission = 0.0
        total_value_represented = 0
        
        for fa in all_free_agents:
            agent_type = fa.agent.agent_type.value if fa.agent.agent_type else 'none'
            type_counts[agent_type] = type_counts.get(agent_type, 0) + 1
            
            if fa.agent.agent_type.value != 'none':
                total_commission += fa.agent.commission_rate
                total_value_represented += fa.market_value
        
        # Average commission by type
        avg_commissions = {}
        for agent in all_agents:
            agent_type = agent['type']
            if agent_type not in avg_commissions:
                avg_commissions[agent_type] = {'total': 0, 'count': 0}
            avg_commissions[agent_type]['total'] += agent['commission_rate']
            avg_commissions[agent_type]['count'] += 1
        
        for agent_type in avg_commissions:
            avg = avg_commissions[agent_type]['total'] / avg_commissions[agent_type]['count']
            avg_commissions[agent_type] = round(avg * 100, 2)  # Convert to percentage
        
        # Top agents by total client value
        agent_values = []
        for agent in all_agents:
            total_value = 0
            for client_id in agent['clients']:
                fa = free_agent_pool.get_free_agent_by_id(client_id)
                if fa:
                    total_value += fa.market_value
            
            agent_values.append({
                'name': agent['name'],
                'type': agent['type'],
                'clients': len(agent['clients']),
                'total_value': total_value,
                'commission_rate': round(agent['commission_rate'] * 100, 2)
            })
        
        agent_values.sort(key=lambda x: x['total_value'], reverse=True)
        
        return jsonify({
            'success': True,
            'statistics': {
                'total_agents': len(all_agents),
                'total_free_agents': len(all_free_agents),
                'represented_count': sum(type_counts.values()) - type_counts['none'],
                'unrepresented_count': type_counts['none'],
                'representation_rate': round((1 - type_counts['none'] / len(all_free_agents)) * 100, 1),
                'by_type': type_counts,
                'average_commission_by_type': avg_commissions,
                'total_value_represented': total_value_represented,
                'top_agents': agent_values[:10]
            }
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500