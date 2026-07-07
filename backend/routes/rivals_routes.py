"""
Rival Promotions & Bidding Wars Routes (Steps 126-132)
"""

from flask import Blueprint, jsonify, request, current_app
import traceback
import random

rivals_bp = Blueprint('rivals', __name__)


def get_database():
    return current_app.config.get('DATABASE')


def get_universe():
    return current_app.config.get('UNIVERSE')


def get_free_agent_pool():
    return current_app.config.get('FREE_AGENT_POOL')


# ============================================================================
# RIVAL PROMOTIONS DATA
# ============================================================================

# Default rival promotions if none exist
DEFAULT_RIVALS = [
    {
        'promotion_id': 'rival_001',
        'name': 'World Wrestling Federation',
        'tier': 'major',
        'brand_identity': 'Sports Entertainment',
        'budget': 500000,
        'roster_size': 85,
        'aggression': 75,
        'prestige': 90,
        'relationship_with_player': 0,
        'won_bidding_wars': 0,
        'lost_bidding_wars': 0
    },
    {
        'promotion_id': 'rival_002',
        'name': 'All Elite Wrestling',
        'tier': 'major',
        'brand_identity': 'Alternative Wrestling',
        'budget': 350000,
        'roster_size': 65,
        'aggression': 80,
        'prestige': 75,
        'relationship_with_player': 0,
        'won_bidding_wars': 0,
        'lost_bidding_wars': 0
    },
    {
        'promotion_id': 'rival_003',
        'name': 'Impact Wrestling',
        'tier': 'regional',
        'brand_identity': 'Traditional Wrestling',
        'budget': 150000,
        'roster_size': 45,
        'aggression': 60,
        'prestige': 55,
        'relationship_with_player': 10,
        'won_bidding_wars': 0,
        'lost_bidding_wars': 0
    },
    {
        'promotion_id': 'rival_004',
        'name': 'Ring of Honor',
        'tier': 'regional',
        'brand_identity': 'Pure Wrestling',
        'budget': 100000,
        'roster_size': 35,
        'aggression': 50,
        'prestige': 60,
        'relationship_with_player': 15,
        'won_bidding_wars': 0,
        'lost_bidding_wars': 0
    },
    {
        'promotion_id': 'rival_005',
        'name': 'New Japan Pro Wrestling',
        'tier': 'major',
        'brand_identity': 'Strong Style',
        'budget': 300000,
        'roster_size': 55,
        'aggression': 45,
        'prestige': 85,
        'relationship_with_player': 5,
        'won_bidding_wars': 0,
        'lost_bidding_wars': 0
    },
    {
        'promotion_id': 'rival_006',
        'name': 'Game Changer Wrestling',
        'tier': 'indie',
        'brand_identity': 'Hardcore/Deathmatch',
        'budget': 50000,
        'roster_size': 25,
        'aggression': 70,
        'prestige': 40,
        'relationship_with_player': 0,
        'won_bidding_wars': 0,
        'lost_bidding_wars': 0
    },
    {
        'promotion_id': 'rival_007',
        'name': 'Major League Wrestling',
        'tier': 'regional',
        'brand_identity': 'Old School Wrestling',
        'budget': 80000,
        'roster_size': 30,
        'aggression': 55,
        'prestige': 45,
        'relationship_with_player': 5,
        'won_bidding_wars': 0,
        'lost_bidding_wars': 0
    },
    {
        'promotion_id': 'rival_008',
        'name': 'Pro Wrestling NOAH',
        'tier': 'regional',
        'brand_identity': 'Kings Road Style',
        'budget': 120000,
        'roster_size': 40,
        'aggression': 40,
        'prestige': 65,
        'relationship_with_player': 10,
        'won_bidding_wars': 0,
        'lost_bidding_wars': 0
    }
]


def get_rivals_data():
    """Get rivals data from app config or use default"""
    if 'RIVALS_DATA' not in current_app.config:
        current_app.config['RIVALS_DATA'] = {
            'rivals': [r.copy() for r in DEFAULT_RIVALS],
            'active_wars': [],
            'completed_wars': [],
            'notifications': [],
            'player_wins': 0,
            'player_losses': 0
        }
    return current_app.config['RIVALS_DATA']


# ============================================================================
# RIVAL PROMOTION ROUTES
# ============================================================================

@rivals_bp.route('/api/rivals')
def api_get_rivals():
    """Get all rival promotions"""
    try:
        rivals_data = get_rivals_data()
        return jsonify({
            'success': True,
            'rivals': rivals_data['rivals']
        })
    except Exception as e:
        current_app.logger.error(f"Error getting rivals: {e}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@rivals_bp.route('/api/rivals/<promotion_id>')
def api_get_rival(promotion_id):
    """Get a specific rival promotion"""
    try:
        rivals_data = get_rivals_data()
        rival = next((r for r in rivals_data['rivals'] if r['promotion_id'] == promotion_id), None)
        
        if not rival:
            return jsonify({'success': False, 'error': 'Rival not found'}), 404
        
        return jsonify({
            'success': True,
            'rival': rival
        })
    except Exception as e:
        current_app.logger.error(f"Error getting rival: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@rivals_bp.route('/api/rivals/generate-interest/<fa_id>', methods=['POST'])
def api_generate_rival_interest(fa_id):
    """Generate rival promotion interest in a free agent"""
    try:
        free_agent_pool = get_free_agent_pool()
        
        if not free_agent_pool:
            return jsonify({
                'success': False, 
                'error': 'Free agent pool not available'
            }), 500
        
        rivals_data = get_rivals_data()
        
        # Get the free agent
        fa = free_agent_pool.get_free_agent_by_id(fa_id)
        
        if not fa:
            return jsonify({'success': False, 'error': 'Free agent not found'}), 404
        
        # Get FA data - handle both object and dict
        if hasattr(fa, 'to_dict'):
            fa_dict = fa.to_dict()
        elif isinstance(fa, dict):
            fa_dict = fa
        else:
            fa_dict = {'wrestler_name': 'Unknown', 'market_value': 50000, 'popularity': 50}
        
        market_value = fa_dict.get('market_value', 50000) or 50000
        popularity = fa_dict.get('popularity', 50) or 50
        wrestler_name = fa_dict.get('wrestler_name', fa_dict.get('name', 'Unknown'))
        
        interested_rivals = []
        
        for rival in rivals_data['rivals']:
            # Calculate interest based on various factors
            base_interest = random.randint(20, 60)
            
            # Budget check - can they afford this talent?
            budget = rival.get('budget', 50000)
            if market_value > budget * 0.3:
                # Too expensive for their budget
                base_interest -= 30
            elif market_value < budget * 0.1:
                # Very affordable
                base_interest += 20
            
            # Tier affects interest
            tier = rival.get('tier', 'indie')
            if tier == 'major':
                base_interest += 15
            elif tier == 'regional':
                base_interest += 5
            
            # Aggression affects likelihood to pursue
            aggression = rival.get('aggression', 50)
            base_interest += (aggression - 50) // 5
            
            # Popular wrestlers get more attention
            if popularity > 70:
                base_interest += 20
            elif popularity > 50:
                base_interest += 10
            
            # Random factor
            base_interest += random.randint(-10, 10)
            
            # Clamp interest
            interest_level = max(0, min(100, base_interest))
            
            # Only include if interest is above threshold
            if interest_level >= 40:
                # Determine if they make an offer
                offer_salary = None
                if interest_level >= 60 and random.random() < 0.6:
                    # Make an offer based on market value and their budget
                    offer_multiplier = random.uniform(0.8, 1.2)
                    offer_salary = int(market_value * offer_multiplier)
                    offer_salary = min(offer_salary, int(budget * 0.25))  # Cap at 25% of budget
                    offer_salary = (offer_salary // 1000) * 1000  # Round to thousands
                
                interested_rivals.append({
                    'promotion_id': rival['promotion_id'],
                    'promotion_name': rival['name'],
                    'tier': rival['tier'],
                    'interest_level': interest_level,
                    'offer_salary': offer_salary,
                    'offer_made': offer_salary is not None
                })
        
        # Sort by interest level
        interested_rivals.sort(key=lambda x: x['interest_level'], reverse=True)
        
        # Store interest on the free agent (if the pool supports it)
        try:
            if hasattr(fa, 'rival_interest'):
                fa.rival_interest = interested_rivals
            elif hasattr(free_agent_pool, 'update_rival_interest'):
                free_agent_pool.update_rival_interest(fa_id, interested_rivals)
        except Exception as update_error:
            current_app.logger.warning(f"Could not update FA rival interest: {update_error}")
        
        return jsonify({
            'success': True,
            'free_agent_id': fa_id,
            'free_agent_name': wrestler_name,
            'interested_rivals': interested_rivals,
            'total_interested': len(interested_rivals)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error generating rival interest: {e}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@rivals_bp.route('/api/bidding/rival-stats')
def api_get_rival_stats():
    """Get bidding war statistics for all rivals"""
    try:
        rivals_data = get_rivals_data()
        
        stats = []
        for rival in rivals_data['rivals']:
            stats.append({
                'promotion_id': rival['promotion_id'],
                'name': rival['name'],
                'tier': rival['tier'],
                'won': rival.get('won_bidding_wars', 0),
                'lost': rival.get('lost_bidding_wars', 0),
                'relationship': rival.get('relationship_with_player', 0)
            })
        
        return jsonify({
            'success': True,
            'stats': stats,
            'player_wins': rivals_data.get('player_wins', 0),
            'player_losses': rivals_data.get('player_losses', 0),
            'active_wars': len(rivals_data.get('active_wars', []))
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting rival stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# BIDDING WAR ROUTES
# ============================================================================

@rivals_bp.route('/api/bidding/initiate/<fa_id>', methods=['POST'])
def api_initiate_bidding_war(fa_id):
    """Start a bidding war for a free agent"""
    try:
        free_agent_pool = get_free_agent_pool()
        
        if not free_agent_pool:
            return jsonify({
                'success': False, 
                'error': 'Free agent pool not available'
            }), 500
        
        rivals_data = get_rivals_data()
        
        data = request.get_json() or {}
        initial_offer = data.get('initial_offer', 0)
        
        if not initial_offer or initial_offer < 1000:
            return jsonify({'success': False, 'error': 'Initial offer must be at least $1,000'}), 400
        
        # Get the free agent
        fa = free_agent_pool.get_free_agent_by_id(fa_id)
        if not fa:
            return jsonify({'success': False, 'error': 'Free agent not found'}), 404
        
        # Get FA data - handle both object and dict
        if hasattr(fa, 'to_dict'):
            fa_dict = fa.to_dict()
        elif isinstance(fa, dict):
            fa_dict = fa
        else:
            fa_dict = {'wrestler_name': 'Unknown', 'market_value': 50000}
        
        wrestler_name = fa_dict.get('wrestler_name', fa_dict.get('name', 'Unknown'))
        market_value = fa_dict.get('market_value', 50000) or 50000
        
        # Check if already in a bidding war
        active_wars = rivals_data.get('active_wars', [])
        existing_war = next((w for w in active_wars if w.get('free_agent_id') == fa_id), None)
        if existing_war:
            return jsonify({'success': False, 'error': 'A bidding war is already active for this free agent'}), 400
        
        # Generate rival offers
        rival_offers = []
        for rival in rivals_data['rivals']:
            # Determine if this rival will participate
            aggression = rival.get('aggression', 50)
            participation_chance = aggression + random.randint(-20, 20)
            
            if random.randint(1, 100) <= participation_chance:
                # Generate their initial offer
                budget = rival.get('budget', 50000)
                max_offer = min(market_value * 1.5, budget * 0.3)
                min_offer = market_value * 0.7
                
                if max_offer >= min_offer:
                    offer = random.randint(int(min_offer), int(max_offer))
                    offer = (offer // 1000) * 1000
                    
                    rival_offers.append({
                        'promotion_id': rival['promotion_id'],
                        'promotion_name': rival['name'],
                        'tier': rival['tier'],
                        'offer': offer,
                        'dropped_out': False,
                        'max_budget': int(budget * 0.35)
                    })
        
        if not rival_offers:
            # No rivals interested, auto-win
            return jsonify({
                'success': True,
                'free_agent_id': fa_id,
                'free_agent_name': wrestler_name,
                'status': 'no_competition',
                'message': f'No rival promotions are interested in {wrestler_name}. You can sign them directly!'
            })
        
        # Create the bidding war
        war_id = f'war_{fa_id}_{random.randint(1000, 9999)}'
        war = {
            'war_id': war_id,
            'free_agent_id': fa_id,
            'free_agent_name': wrestler_name,
            'market_value': market_value,
            'current_round': 1,
            'max_rounds': 3,
            'player_offer': initial_offer,
            'rival_offers': rival_offers,
            'status': 'active',
            'escalation_events': []
        }
        
        rivals_data['active_wars'].append(war)
        
        return jsonify({
            'success': True,
            'war_id': war_id,
            'free_agent_id': fa_id,
            'free_agent_name': wrestler_name,
            'current_round': 1,
            'player_offer': initial_offer,
            'rival_count': len(rival_offers),
            'message': f'Bidding war initiated for {wrestler_name}! {len(rival_offers)} rival(s) are competing.'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error initiating bidding war: {e}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


@rivals_bp.route('/api/bidding/active')
def api_get_active_bidding_wars():
    """Get all active bidding wars"""
    try:
        rivals_data = get_rivals_data()
        
        active_wars = []
        for war in rivals_data.get('active_wars', []):
            # Calculate if player is leading
            player_offer = war.get('player_offer', 0)
            rival_offers = war.get('rival_offers', [])
            active_rival_offers = [r.get('offer', 0) for r in rival_offers if not r.get('dropped_out')]
            top_rival_offer = max(active_rival_offers, default=0)
            
            active_wars.append({
                'war_id': war.get('war_id'),
                'free_agent_id': war.get('free_agent_id'),
                'free_agent_name': war.get('free_agent_name'),
                'current_round': war.get('current_round', 1),
                'player_offer': player_offer,
                'rival_count': len([r for r in rival_offers if not r.get('dropped_out')]),
                'leading': player_offer >= top_rival_offer,
                'status': war.get('status', 'active')
            })
        
        return jsonify({
            'success': True,
            'active_wars': active_wars
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting active wars: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@rivals_bp.route('/api/bidding/completed')
def api_get_completed_bidding_wars():
    """Get completed bidding wars"""
    try:
        rivals_data = get_rivals_data()
        
        return jsonify({
            'success': True,
            'completed_wars': rivals_data.get('completed_wars', [])[-20:]  # Last 20
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting completed wars: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@rivals_bp.route('/api/bidding/notifications')
def api_get_bidding_notifications():
    """Get bidding war notifications (outbid alerts, etc.)"""
    try:
        rivals_data = get_rivals_data()
        
        notifications = []
        
        # Check active wars for outbid situations
        for war in rivals_data.get('active_wars', []):
            player_offer = war.get('player_offer', 0)
            rival_offers = war.get('rival_offers', [])
            
            for rival in rival_offers:
                if not rival.get('dropped_out') and rival.get('offer', 0) > player_offer:
                    notifications.append({
                        'type': 'outbid',
                        'free_agent_id': war.get('free_agent_id'),
                        'free_agent_name': war.get('free_agent_name'),
                        'rival_promotion': rival.get('promotion_name'),
                        'rival_offer': rival.get('offer'),
                        'your_offer': player_offer,
                        'gap': rival.get('offer', 0) - player_offer,
                        'deadline': war.get('current_round', 1) + 1
                    })
                    break  # Only one notification per war
        
        return jsonify({
            'success': True,
            'notifications': notifications
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting notifications: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@rivals_bp.route('/api/bidding/strategic-options/<fa_id>')
def api_get_strategic_options(fa_id):
    """Get strategic options for a bidding war"""
    try:
        rivals_data = get_rivals_data()
        
        war = next((w for w in rivals_data.get('active_wars', []) if w.get('free_agent_id') == fa_id), None)
        
        if not war:
            return jsonify({'success': False, 'error': 'No active bidding war for this free agent'}), 404
        
        player_offer = war.get('player_offer', 0)
        rival_offers = [r for r in war.get('rival_offers', []) if not r.get('dropped_out')]
        top_rival_offer = max([r.get('offer', 0) for r in rival_offers], default=0)
        
        # Generate strategic options
        options = [
            {
                'action': 'hold_firm',
                'label': 'Hold Firm',
                'description': 'Maintain your current offer and wait for rivals to back down.',
                'new_offer': player_offer,
                'acceptance_bonus': 0,
                'cost': 0
            },
            {
                'action': 'small_increase',
                'label': 'Small Increase (+10%)',
                'description': 'Slightly increase your offer to show continued interest.',
                'new_offer': int(player_offer * 1.1),
                'acceptance_bonus': 5,
                'cost': 0
            },
            {
                'action': 'match_top',
                'label': 'Match Top Offer',
                'description': 'Match the highest rival offer exactly.',
                'new_offer': max(top_rival_offer, player_offer),
                'acceptance_bonus': 10,
                'cost': 0
            },
            {
                'action': 'aggressive_bid',
                'label': 'Aggressive Bid (+25%)',
                'description': 'Make a strong statement with a significantly higher offer.',
                'new_offer': int(max(top_rival_offer, player_offer) * 1.25),
                'acceptance_bonus': 20,
                'cost': 0
            },
            {
                'action': 'blowout_offer',
                'label': 'Blowout Offer (+50%)',
                'description': 'Make an offer rivals cannot match. May cause them to drop out.',
                'new_offer': int(max(top_rival_offer, player_offer) * 1.5),
                'acceptance_bonus': 35,
                'cost': 0
            }
        ]
        
        return jsonify({
            'success': True,
            'options': options,
            'war_state': {
                'current_round': war.get('current_round', 1),
                'player_offer': player_offer,
                'rival_offers': rival_offers,
                'escalation_events': war.get('escalation_events', []),
                'status': war.get('status', 'active')
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting strategic options: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@rivals_bp.route('/api/bidding/strategic-action/<fa_id>', methods=['POST'])
def api_apply_strategic_action(fa_id):
    """Apply a strategic action in a bidding war"""
    try:
        rivals_data = get_rivals_data()
        
        data = request.get_json() or {}
        action = data.get('action', 'hold_firm')
        player_offer = data.get('player_offer', 0)
        
        war = next((w for w in rivals_data.get('active_wars', []) if w.get('free_agent_id') == fa_id), None)
        
        if not war:
            return jsonify({'success': False, 'error': 'No active bidding war for this free agent'}), 404
        
        if action == 'withdraw':
            # Player withdraws from war
            war['status'] = 'withdrawn'
            rivals_data['active_wars'].remove(war)
            rivals_data['completed_wars'].append({
                **war,
                'player_won': False,
                'final_player_offer': war.get('player_offer', 0),
                'winner_name': 'Withdrawn'
            })
            rivals_data['player_losses'] = rivals_data.get('player_losses', 0) + 1
            
            return jsonify({
                'success': True,
                'message': 'You have withdrawn from the bidding war.'
            })
        
        # Update player offer
        war['player_offer'] = player_offer
        
        return jsonify({
            'success': True,
            'action': action,
            'new_offer': player_offer
        })
        
    except Exception as e:
        current_app.logger.error(f"Error applying strategic action: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@rivals_bp.route('/api/bidding/advance/<fa_id>', methods=['POST'])
def api_advance_bidding_round(fa_id):
    """Advance to the next round of a bidding war"""
    try:
        rivals_data = get_rivals_data()
        free_agent_pool = get_free_agent_pool()
        
        data = request.get_json() or {}
        player_offer = data.get('player_offer', 0)
        
        war = next((w for w in rivals_data.get('active_wars', []) if w.get('free_agent_id') == fa_id), None)
        
        if not war:
            return jsonify({'success': False, 'error': 'No active bidding war for this free agent'}), 404
        
        # Update player offer
        war['player_offer'] = player_offer
        
        # Process rival responses
        for rival in war.get('rival_offers', []):
            if rival.get('dropped_out'):
                continue
            
            current_offer = rival.get('offer', 0)
            max_budget = rival.get('max_budget', current_offer * 1.5)
            
            # Decide if rival raises, holds, or drops out
            if player_offer > current_offer:
                # Player outbid them - decide response
                if player_offer > max_budget:
                    # Can't afford to match
                    rival['dropped_out'] = True
                elif random.random() < 0.7:
                    # Raise their offer
                    increase = random.uniform(1.05, 1.2)
                    new_offer = min(int(player_offer * increase), max_budget)
                    new_offer = (new_offer // 1000) * 1000
                    rival['offer'] = new_offer
                else:
                    # Drop out despite being able to afford it
                    if random.random() < 0.3:
                        rival['dropped_out'] = True
        
        # Check if all rivals dropped out
        active_rivals = [r for r in war.get('rival_offers', []) if not r.get('dropped_out')]
        
        war['current_round'] = war.get('current_round', 1) + 1
        
        if not active_rivals or war['current_round'] > war.get('max_rounds', 3):
            # War is over - determine winner
            all_rival_offers = [r.get('offer', 0) for r in war.get('rival_offers', []) if not r.get('dropped_out')]
            top_rival_offer = max(all_rival_offers, default=0)
            player_won = player_offer >= top_rival_offer
            
            war['status'] = 'resolved'
            
            # Remove from active, add to completed
            if war in rivals_data['active_wars']:
                rivals_data['active_wars'].remove(war)
            
            if player_won:
                rivals_data['player_wins'] = rivals_data.get('player_wins', 0) + 1
                winner_name = 'Your Promotion'
                
                # Try to remove from free agent pool
                if free_agent_pool:
                    try:
                        if hasattr(free_agent_pool, 'remove_free_agent'):
                            free_agent_pool.remove_free_agent(fa_id)
                        elif hasattr(free_agent_pool, 'available_free_agents'):
                            free_agent_pool.available_free_agents = [
                                agent for agent in free_agent_pool.available_free_agents 
                                if getattr(agent, 'id', None) != fa_id
                            ]
                    except Exception as remove_err:
                        current_app.logger.warning(f"Could not remove FA: {remove_err}")
            else:
                rivals_data['player_losses'] = rivals_data.get('player_losses', 0) + 1
                winning_rival = max(
                    [r for r in war.get('rival_offers', []) if not r.get('dropped_out')], 
                    key=lambda x: x.get('offer', 0), 
                    default=None
                )
                winner_name = winning_rival.get('promotion_name', 'Unknown') if winning_rival else 'Unknown'
            
            rivals_data['completed_wars'].append({
                'free_agent_id': fa_id,
                'free_agent_name': war.get('free_agent_name'),
                'player_won': player_won,
                'final_player_offer': player_offer,
                'winner_name': winner_name,
                'winning_offer': player_offer if player_won else top_rival_offer
            })
            
            return jsonify({
                'success': True,
                'status': 'resolved',
                'player_won': player_won,
                'free_agent_name': war.get('free_agent_name'),
                'final_offer': player_offer,
                'winner_name': winner_name,
                'winning_offer': player_offer if player_won else top_rival_offer
            })
        
        return jsonify({
            'success': True,
            'status': 'active',
            'new_round': war['current_round'],
            'active_rivals': len(active_rivals),
            'player_offer': player_offer
        })
        
    except Exception as e:
        current_app.logger.error(f"Error advancing bidding round: {e}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500
from persistence.rival_promotion_db import get_rival_world_events


@rivals_bp.route('/api/rivals/landscape')
def api_rivals_landscape():
    """Persistent competitor landscape with management personalities and strategy."""
    try:
        mgr = current_app.config.get('RIVAL_PROMOTION_MANAGER') or current_app.config.get('RIVAL_MANAGER')
        if not mgr:
            return jsonify({'success': False, 'error': 'Rival manager unavailable'}), 500
        rivals = []
        for promo in mgr.get_all_promotions():
            rivals.append({
                'promotion_id': promo.promotion_id,
                'name': promo.name,
                'abbreviation': promo.abbreviation,
                'tier': promo.tier.value if hasattr(promo.tier, 'value') else str(promo.tier),
                'brand_identity': promo.brand_identity.value if hasattr(promo.brand_identity, 'value') else str(promo.brand_identity),
                'booking_philosophy': getattr(promo, 'booking_philosophy', 'balanced'),
                'management_style': getattr(promo, 'management_style', 'relationship_builder'),
                'budget_per_year': promo.budget_per_year,
                'remaining_budget': promo.remaining_budget,
                'cash_reserves': getattr(promo, 'cash_reserves', 0),
                'momentum': getattr(promo, 'momentum', 50),
                'roster_size': promo.roster_size,
                'prestige': promo.prestige,
                'aggression': promo.aggression,
            })
        return jsonify({'success': True, 'rivals': rivals})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@rivals_bp.route('/api/rivals/simulate-week', methods=['POST'])
def api_rivals_simulate_week():
    """Simulate one week of rival promotion AI reactions and persist outcomes."""
    try:
        ai = current_app.config.get('COMPETING_PROMOTION_AI')
        if not ai:
            return jsonify({'success': False, 'error': 'Competing promotion AI unavailable'}), 500

        payload = request.get_json(silent=True) or {}
        year = int(payload.get('year', 1))
        week = int(payload.get('week', 1))
        player_context = payload.get('player_context', {})
        events = ai.simulate_week(year=year, week=week, player_context=player_context)
        return jsonify({'success': True, 'year': year, 'week': week, 'events': events})
    except Exception as e:
        current_app.logger.error(f"simulate-week failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@rivals_bp.route('/api/rivals/world-feed')
def api_rivals_world_feed():
    """Get latest persistent rival ecosystem events."""
    try:
        db = get_database()
        limit = int(request.args.get('limit', 30))
        events = get_rival_world_events(db, limit=limit)
        return jsonify({'success': True, 'events': events})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
