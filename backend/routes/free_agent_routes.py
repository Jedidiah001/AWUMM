"""
Free Agent Routes - Free Agent Pool Management (Steps 113-115, 134)
"""

from flask import Blueprint, jsonify, request, current_app, render_template, redirect, url_for, flash
import traceback
import random
import json

from flask import send_file
import os

# Steps 167-172: Legend system
from models.legend_system import (
    LegendProfile, RetirementStatus, ComebackApproach,
    LegendMatchLimitations, FarewellTour, FarewellTourStatus
)

# Steps 185-190: Prospect system
from models.prospect_system import (
    ProspectProfile, ProspectDiscoveryMethod, ProspectEvaluation,
    ProspectCompetition, DevelopmentalContract, TrainingInvestmentLevel,
    BreakthroughStatus
)

free_agent_bp = Blueprint('free_agent', __name__)


def get_database():
    return current_app.config['DATABASE']


def get_universe():
    return current_app.config['UNIVERSE']


def get_free_agent_pool():
    return current_app.config.get('FREE_AGENT_POOL')


@free_agent_bp.route('/negotiation')
def negotiation_page_new():
    """
    STEP 134 – Full negotiation interface.
    Serves negotiation.html with fa= query param.
    URL: /negotiation?fa=<free_agent_id>
    """
    return render_template('negotiation.html')


@free_agent_bp.route('/api/free-agents')
def api_get_free_agents():
    free_agent_pool = get_free_agent_pool()
    
    discovered_only = request.args.get('discovered_only', 'true').lower() == 'true'
    visibility_tier = request.args.get('visibility_tier', type=int)
    source = request.args.get('source')
    
    if discovered_only:
        free_agents = free_agent_pool.get_discovered_free_agents()
    elif visibility_tier:
        free_agents = free_agent_pool.get_free_agents_by_visibility(visibility_tier)
    else:
        free_agents = free_agent_pool.available_free_agents
    
    if source:
        free_agents = [fa for fa in free_agents if fa.source.value == source]
    
    free_agents.sort(key=lambda fa: fa.market_value, reverse=True)
    
    return jsonify({
        'success': True,
        'total': len(free_agents),
        'free_agents': [fa.to_dict() for fa in free_agents]
    })


@free_agent_bp.route('/api/free-agents/<fa_id>')
def api_get_free_agent(fa_id):
    free_agent_pool = get_free_agent_pool()
    
    fa = free_agent_pool.get_free_agent_by_id(fa_id)
    
    if not fa:
        return jsonify({'success': False, 'error': 'Free agent not found'}), 404
    
    return jsonify({
        'success': True,
        'free_agent': fa.to_dict()
    })


@free_agent_bp.route('/api/free-agents/pool-summary')
def api_get_free_agent_pool_summary():
    free_agent_pool = get_free_agent_pool()
    
    summary = free_agent_pool.get_pool_summary()
    
    return jsonify({
        'success': True,
        'summary': summary
    })


@free_agent_bp.route('/api/free-agents/headlines')
def api_get_headline_free_agents():
    free_agent_pool = get_free_agent_pool()
    
    headlines = free_agent_pool.get_headline_free_agents()
    
    return jsonify({
        'success': True,
        'total': len(headlines),
        'free_agents': [fa.to_dict() for fa in headlines]
    })


@free_agent_bp.route('/api/free-agents/legends')
def api_get_legend_free_agents():
    free_agent_pool = get_free_agent_pool()
    
    legends = free_agent_pool.get_legends()
    discovered_legends = [l for l in legends if l.discovered]
    
    return jsonify({
        'success': True,
        'total': len(discovered_legends),
        'free_agents': [l.to_dict() for l in discovered_legends]
    })


@free_agent_bp.route('/api/free-agents/prospects')
def api_get_prospect_free_agents():
    free_agent_pool = get_free_agent_pool()
    
    prospects = free_agent_pool.get_prospects()
    discovered_prospects = [p for p in prospects if p.discovered]
    
    return jsonify({
        'success': True,
        'total': len(discovered_prospects),
        'free_agents': [p.to_dict() for p in discovered_prospects]
    })


@free_agent_bp.route('/api/free-agents/international')
def api_get_international_free_agents():
    free_agent_pool = get_free_agent_pool()
    
    region = request.args.get('region')
    international = free_agent_pool.get_international_talents(region)
    discovered = [i for i in international if i.discovered]
    
    return jsonify({
        'success': True,
        'total': len(discovered),
        'region': region,
        'free_agents': [i.to_dict() for i in discovered]
    })


@free_agent_bp.route('/api/free-agents/controversy')
def api_get_controversy_free_agents():
    free_agent_pool = get_free_agent_pool()
    
    controversy = free_agent_pool.get_controversy_cases()
    discovered = [c for c in controversy if c.discovered]
    
    return jsonify({
        'success': True,
        'total': len(discovered),
        'free_agents': [c.to_dict() for c in discovered]
    })


@free_agent_bp.route('/api/free-agents/<fa_id>/discover', methods=['POST'])
def api_discover_free_agent(fa_id):
    free_agent_pool = get_free_agent_pool()
    
    success = free_agent_pool.discover_free_agent(fa_id)
    
    if not success:
        return jsonify({'success': False, 'error': 'Free agent not found or already discovered'}), 404
    
    fa = free_agent_pool.get_free_agent_by_id(fa_id)
    
    return jsonify({
        'success': True,
        'message': f'{fa.wrestler_name} has been discovered!',
        'free_agent': fa.to_dict()
    })


@free_agent_bp.route('/api/free-agents/scout-region/<region>', methods=['POST'])
def api_scout_region(region):
    free_agent_pool = get_free_agent_pool()
    
    valid_regions = ['japan', 'mexico', 'uk', 'europe', 'australia']
    if region not in valid_regions:
        return jsonify({'success': False, 'error': 'Invalid region'}), 400
    
    if free_agent_pool._scouting_network.get(region, False):
        return jsonify({'success': False, 'error': 'Region already scouted'}), 400
    
    discovered = free_agent_pool.scout_region(region)
    
    return jsonify({
        'success': True,
        'region': region,
        'discovered_count': len(discovered),
        'discovered': [fa.to_dict() for fa in discovered],
        'message': f'Scouting network established in {region}. Discovered {len(discovered)} new talents!'
    })


@free_agent_bp.route('/api/free-agents/upgrade-scouting', methods=['POST'])
def api_upgrade_scouting():
    database = get_database()
    universe = get_universe()
    free_agent_pool = get_free_agent_pool()
    
    current_level = free_agent_pool._scouting_level
    
    if current_level >= 5:
        return jsonify({'success': False, 'error': 'Scouting already at maximum level'}), 400
    
    cost = 10000 * current_level
    
    if universe.balance < cost:
        return jsonify({'success': False, 'error': f'Insufficient funds. Need ${cost:,}'}), 400
    
    universe.balance -= cost
    new_level = free_agent_pool.upgrade_scouting()
    
    database.update_game_state(balance=universe.balance)
    
    return jsonify({
        'success': True,
        'new_level': new_level,
        'cost': cost,
        'new_balance': universe.balance,
        'message': f'Scouting upgraded to level {new_level}!'
    })


@free_agent_bp.route('/api/free-agents/release-wrestler', methods=['POST'])
def api_release_wrestler_to_free_agents():
    database = get_database()
    universe = get_universe()
    free_agent_pool = get_free_agent_pool()
    
    try:
        data = request.get_json()
        wrestler_id = data.get('wrestler_id')
        departure_reason = data.get('departure_reason', 'released')
        no_compete_weeks = data.get('no_compete_weeks', 0)
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'success': False, 'error': 'Wrestler not found'}), 404
        
        was_champion = False
        for championship in universe.championships:
            if championship.current_holder_id == wrestler_id:
                was_champion = True
                break
        
        relationship = max(10, min(90, 50 + wrestler.morale // 2))
        
        fa = free_agent_pool.add_from_release(
            wrestler=wrestler,
            departure_reason=departure_reason,
            relationship=relationship,
            year=universe.current_year,
            week=universe.current_week,
            no_compete_weeks=no_compete_weeks,
            was_champion=was_champion
        )
        
        wrestler.is_retired = True
        universe.save_wrestler(wrestler)
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'message': f'{wrestler.name} has been released and is now a free agent',
            'free_agent': fa.to_dict()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@free_agent_bp.route('/api/free-agents/process-week', methods=['POST'])
def api_process_free_agent_week():
    universe = get_universe()
    free_agent_pool = get_free_agent_pool()
    
    try:
        events = free_agent_pool.process_week(
            universe.current_year,
            universe.current_week
        )
        
        controversy_updates = free_agent_pool.process_controversy_cases(universe)
        
        return jsonify({
            'success': True,
            'events': events,
            'controversy_updates': controversy_updates,
            'message': f'Processed {len(events)} free agent events, {len(controversy_updates)} controversy updates'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@free_agent_bp.route('/api/free-agents/generate-prospects', methods=['POST'])
def api_generate_prospects():
    universe = get_universe()
    free_agent_pool = get_free_agent_pool()
    
    try:
        count = request.get_json().get('count', 3) if request.is_json else 3
        
        prospects = free_agent_pool.generate_random_prospects(
            count,
            universe.current_year,
            universe.current_week
        )
        
        return jsonify({
            'success': True,
            'count': len(prospects),
            'prospects': [p.to_dict() for p in prospects],
            'message': f'Generated {len(prospects)} new prospects'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# POOL POPULATION ROUTES (Step 114)
# ============================================================================

@free_agent_bp.route('/api/free-agents/populate/releases', methods=['POST'])
def api_populate_from_releases():
    universe = get_universe()
    free_agent_pool = get_free_agent_pool()
    
    try:
        count = request.get_json().get('count', 3) if request.is_json else 3
        
        generated = free_agent_pool.populate_pool_from_releases(
            universe,
            count=count
        )
        
        return jsonify({
            'success': True,
            'count': len(generated),
            'free_agents': [fa.to_dict() for fa in generated],
            'message': f'Generated {len(generated)} new free agents from rival releases'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@free_agent_bp.route('/api/free-agents/populate/international/<region>', methods=['POST'])
def api_populate_international(region):
    universe = get_universe()
    free_agent_pool = get_free_agent_pool()
    
    try:
        count = request.get_json().get('count', 2) if request.is_json else 2
        
        if not free_agent_pool._scouting_network.get(region, False):
            return jsonify({
                'success': False,
                'error': f'Region {region} not yet scouted. Scout the region first.'
            }), 400
        
        generated = free_agent_pool.generate_international_wave(
            universe,
            region=region,
            count=count
        )
        
        return jsonify({
            'success': True,
            'region': region,
            'count': len(generated),
            'free_agents': [fa.to_dict() for fa in generated],
            'message': f'Discovered {len(generated)} new talents from {region}'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@free_agent_bp.route('/api/free-agents/populate/prospects', methods=['POST'])
def api_populate_prospects():
    universe = get_universe()
    free_agent_pool = get_free_agent_pool()
    
    try:
        count = request.get_json().get('count', 5) if request.is_json else 5
        
        generated = free_agent_pool.generate_prospect_class(
            universe,
            count=count
        )
        
        return jsonify({
            'success': True,
            'count': len(generated),
            'free_agents': [fa.to_dict() for fa in generated],
            'message': f'Generated {len(generated)} new prospects'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@free_agent_bp.route('/api/free-agents/check-legends', methods=['POST'])
def api_check_legend_availability():
    universe = get_universe()
    free_agent_pool = get_free_agent_pool()
    
    try:
        comebacks = free_agent_pool.check_legend_availability(
            universe,
            universe.retired_wrestlers
        )
        
        return jsonify({
            'success': True,
            'count': len(comebacks),
            'legends': [fa.to_dict() for fa in comebacks],
            'message': f'{len(comebacks)} legends considering comeback!' if comebacks else 'No legends available for comeback at this time'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@free_agent_bp.route('/api/free-agents/pool-health')
def api_get_pool_health():
    free_agent_pool = get_free_agent_pool()
    
    try:
        report = free_agent_pool.get_pool_health_report()
        
        return jsonify({
            'success': True,
            'report': report
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# VISIBILITY TIER ROUTES (Step 115)
# ============================================================================

@free_agent_bp.route('/api/free-agents/visibility/breakdown')
def api_get_visibility_breakdown():
    free_agent_pool = get_free_agent_pool()
    
    try:
        breakdown = free_agent_pool.get_visibility_breakdown()
        
        return jsonify({
            'success': True,
            'breakdown': breakdown
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@free_agent_bp.route('/api/free-agents/visibility/auto-discover', methods=['POST'])
def api_auto_discover():
    free_agent_pool = get_free_agent_pool()
    
    try:
        discovered = free_agent_pool.auto_discover_by_scouting_level()
        
        return jsonify({
            'success': True,
            'count': len(discovered),
            'discovered': [fa.to_dict() for fa in discovered],
            'message': f'Discovered {len(discovered)} new free agents through scouting network'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@free_agent_bp.route('/api/free-agents/<fa_id>/trigger-news', methods=['POST'])
def api_trigger_news_event(fa_id):
    free_agent_pool = get_free_agent_pool()
    
    try:
        data = request.get_json()
        event_type = data.get('event_type', 'interview')
        
        valid_events = ['interview', 'social_media', 'rival_signing_failed', 
                       'injury_recovery', 'comeback_tease', 'shoot_promo']
        
        if event_type not in valid_events:
            return jsonify({
                'success': False,
                'error': f'Invalid event type. Valid types: {valid_events}'
            }), 400
        
        result = free_agent_pool.trigger_news_event(fa_id, event_type)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@free_agent_bp.route('/api/free-agents/<fa_id>/promote-visibility', methods=['POST'])
def api_promote_visibility(fa_id):
    free_agent_pool = get_free_agent_pool()
    
    try:
        reason = request.get_json().get('reason', 'manual') if request.is_json else 'manual'
        
        fa = free_agent_pool.promote_visibility(fa_id, reason)
        
        if not fa:
            return jsonify({'success': False, 'error': 'Free agent not found'}), 404
        
        return jsonify({
            'success': True,
            'free_agent': fa.to_dict(),
            'message': f'{fa.wrestler_name} visibility promoted to {fa.visibility_label}'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@free_agent_bp.route('/api/free-agents/<fa_id>/demote-visibility', methods=['POST'])
def api_demote_visibility(fa_id):
    free_agent_pool = get_free_agent_pool()
    
    try:
        reason = request.get_json().get('reason', 'manual') if request.is_json else 'manual'
        
        fa = free_agent_pool.demote_visibility(fa_id, reason)
        
        if not fa:
            return jsonify({'success': False, 'error': 'Free agent not found'}), 404
        
        return jsonify({
            'success': True,
            'free_agent': fa.to_dict(),
            'message': f'{fa.wrestler_name} visibility demoted to {fa.visibility_label}'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@free_agent_bp.route('/api/free-agents/visibility/process-weekly', methods=['POST'])
def api_process_visibility_changes():
    universe = get_universe()
    free_agent_pool = get_free_agent_pool()
    
    try:
        changes = free_agent_pool.process_visibility_changes(
            universe.current_year,
            universe.current_week
        )
        
        return jsonify({
            'success': True,
            'changes': changes,
            'message': f'Processed {len(changes)} visibility changes'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@free_agent_bp.route('/api/free-agents/<fa_id>/update-reputation', methods=['POST'])
def api_update_free_agent_reputation(fa_id):
    universe = get_universe()
    free_agent_pool = get_free_agent_pool()
    
    try:
        fa = free_agent_pool.get_free_agent_by_id(fa_id)
        
        if not fa:
            return jsonify({'success': False, 'error': 'Free agent not found'}), 404
        
        data = request.get_json()
        change = data.get('change', 0)
        reason = data.get('reason', '')
        
        old_reputation = fa.backstage_reputation
        fa.update_reputation(change, reason)
        
        fa.recalculate_market_value(
            year=universe.current_year,
            week=universe.current_week,
            use_calculator=True
        )
        
        free_agent_pool.save_free_agent(fa)
        
        return jsonify({
            'success': True,
            'free_agent_id': fa_id,
            'old_reputation': old_reputation,
            'new_reputation': fa.backstage_reputation,
            'locker_room_leader': fa.locker_room_leader,
            'known_difficult': fa.known_difficult,
            'new_market_value': fa.market_value
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@free_agent_bp.route('/api/free-agents/<fa_id>/record-injury', methods=['POST'])
def api_record_free_agent_injury(fa_id):
    universe = get_universe()
    free_agent_pool = get_free_agent_pool()
    
    try:
        fa = free_agent_pool.get_free_agent_by_id(fa_id)
        
        if not fa:
            return jsonify({'success': False, 'error': 'Free agent not found'}), 404
        
        data = request.get_json()
        severity = data.get('severity', 1)
        
        old_value = fa.market_value
        fa.record_injury(severity)
        
        fa.recalculate_market_value(
            year=universe.current_year,
            week=universe.current_week,
            use_calculator=True
        )
        
        free_agent_pool.save_free_agent(fa)
        
        return jsonify({
            'success': True,
            'free_agent_id': fa_id,
            'injury_history_count': fa.injury_history_count,
            'has_chronic_issues': fa.has_chronic_issues,
            'old_market_value': old_value,
            'new_market_value': fa.market_value,
            'value_change': fa.market_value - old_value
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# NEGOTIATION ROUTES (Step 134)
# ============================================================================

@free_agent_bp.route('/negotiate')
def negotiate_page():
    """Legacy /negotiate route — redirects to the new /negotiation page."""
    fa_id = request.args.get('fa')
    if not fa_id:
        flash('No free agent specified', 'error')
        return redirect('/free-agents')
    return redirect(f'/negotiation?fa={fa_id}')



@free_agent_bp.route('/api/free-agents/negotiate', methods=['POST'])
def api_negotiate_with_free_agent():
    """Handle negotiation offers to free agents"""
    try:
        database = get_database()
        universe = get_universe()
        free_agent_pool = get_free_agent_pool()
        
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        fa_id = data.get('fa_id')
        salary = data.get('salary', 0)
        contract_length = data.get('contract_length', 6)
        signing_bonus = data.get('signing_bonus', 0)
        role_promise = data.get('role_promise', 'none')
        creative_control = data.get('creative_control', 'none')
        
        if not fa_id:
            return jsonify({'success': False, 'error': 'No free agent ID provided'}), 400
        
        # Get free agent
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
        
        # Get asking price - try multiple possible locations
        asking_price = 50000  # Default
        if fa_dict.get('demands') and isinstance(fa_dict.get('demands'), dict):
            asking_price = fa_dict['demands'].get('asking_salary', asking_price)
        elif fa_dict.get('market_value'):
            asking_price = fa_dict.get('market_value', asking_price)
        elif fa_dict.get('asking_price'):
            asking_price = fa_dict.get('asking_price', asking_price)
        
        # Get base interest
        base_interest = fa_dict.get('interest_level', 50)
        if base_interest is None:
            base_interest = 50
        
        # Calculate acceptance chance
        acceptance_chance = base_interest
        
        # Salary impact
        if asking_price > 0:
            salary_ratio = salary / asking_price
        else:
            salary_ratio = 1.0
            
        if salary_ratio >= 2.0:
            acceptance_chance += 35
        elif salary_ratio >= 1.5:
            acceptance_chance += 25
        elif salary_ratio >= 1.2:
            acceptance_chance += 15
        elif salary_ratio >= 1.0:
            acceptance_chance += 5
        elif salary_ratio >= 0.8:
            acceptance_chance -= 15
        else:
            acceptance_chance -= 30
        
        # Signing bonus impact
        if signing_bonus >= 100000:
            acceptance_chance += 20
        elif signing_bonus >= 50000:
            acceptance_chance += 15
        elif signing_bonus >= 25000:
            acceptance_chance += 10
        elif signing_bonus >= 10000:
            acceptance_chance += 5
        
        # Role promise impact
        role_bonuses = {
            'main_event': 20,
            'upper_midcard': 10,
            'midcard': 5,
            'tag_team': 3,
            'manager': 0,
            'none': 0
        }
        acceptance_chance += role_bonuses.get(role_promise, 0)
        
        # Creative control impact
        if creative_control == 'full':
            acceptance_chance += 15
        elif creative_control == 'limited':
            acceptance_chance += 7
        
        # Clamp acceptance chance
        acceptance_chance = max(5, min(95, int(acceptance_chance)))
        
        # Roll for acceptance
        roll = random.randint(1, 100)
        
        current_app.logger.info(f"Negotiation: {wrestler_name}, Roll: {roll}, Acceptance: {acceptance_chance}%")
        
        if roll <= acceptance_chance:
            # ACCEPTED - Sign the wrestler
            
            # Check if we can afford signing bonus
            if signing_bonus > 0:
                current_balance = getattr(universe, 'balance', 0) or 0
                if current_balance < signing_bonus:
                    return jsonify({
                        'success': False,
                        'accepted': False,
                        'error': f'Insufficient funds for signing bonus. You have ${current_balance:,} but need ${signing_bonus:,}'
                    }), 400
                
                # Deduct signing bonus
                universe.balance = current_balance - signing_bonus
                try:
                    database.update_game_state(balance=universe.balance)
                except Exception as db_error:
                    current_app.logger.warning(f"Could not update balance in DB: {db_error}")
            
            # Try to remove from free agent pool
            try:
                if hasattr(free_agent_pool, 'remove_free_agent'):
                    free_agent_pool.remove_free_agent(fa_id)
                elif hasattr(free_agent_pool, 'available_free_agents'):
                    # Manual removal
                    free_agent_pool.available_free_agents = [
                        agent for agent in free_agent_pool.available_free_agents 
                        if getattr(agent, 'id', None) != fa_id
                    ]
            except Exception as remove_error:
                current_app.logger.warning(f"Could not remove FA from pool: {remove_error}")
            
            return jsonify({
                'success': True,
                'accepted': True,
                'message': f'{wrestler_name} has accepted your offer and signed with your promotion! Contract: ${salary:,}/month for {contract_length} months.'
            })
        
        elif roll <= acceptance_chance + 25:
            # COUNTER OFFER
            counter_multiplier = random.uniform(1.1, 1.25)
            counter_salary = int(salary * counter_multiplier)
            counter_salary = (counter_salary // 1000) * 1000  # Round to nearest 1000
            
            counter_messages = [
                f"{wrestler_name} is interested but wants ${counter_salary:,}/month instead.",
                f"{wrestler_name} likes what they hear, but feels they're worth ${counter_salary:,}/month.",
                f"{wrestler_name}'s agent has countered with a request for ${counter_salary:,}/month.",
                f"Close, but not quite. {wrestler_name} is looking for at least ${counter_salary:,}/month."
            ]
            
            return jsonify({
                'success': True,
                'accepted': False,
                'counter_offer': True,
                'counter_salary': counter_salary,
                'message': random.choice(counter_messages)
            })
        
        else:
            # REJECTED
            rejection_messages = [
                f"{wrestler_name} has declined your offer.",
                f"{wrestler_name} doesn't feel this is the right fit at this time.",
                f"{wrestler_name} is looking for a different opportunity.",
                f"{wrestler_name} respectfully declines. Perhaps try again with a better offer?",
                f"{wrestler_name}'s agent has informed you that they're pursuing other options.",
                f"Unfortunately, {wrestler_name} has decided to pass on your offer."
            ]
            
            return jsonify({
                'success': True,
                'accepted': False,
                'counter_offer': False,
                'message': random.choice(rejection_messages)
            })
    
    except Exception as e:
        current_app.logger.error(f"Negotiation error: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'accepted': False,
            'error': f'Negotiation failed: {str(e)}'
        }), 500

# ============================================================================
# STEP 167-172: LEGEND SYSTEM ROUTES
# ============================================================================

@free_agent_bp.route('/api/free-agents/<fa_id>/legend-profile')
def api_get_legend_profile(fa_id):
    """
    Step 167: Get full legend profile for a free agent.
    Returns retirement status, comeback likelihood, match limitations etc.
    """
    free_agent_pool = get_free_agent_pool()
    try:
        fa = free_agent_pool.get_free_agent_by_id(fa_id)
        if not fa:
            return jsonify({'success': False, 'error': 'Free agent not found'}), 404

        fa_dict = fa.to_dict() if hasattr(fa, 'to_dict') else fa

        if not fa_dict.get('is_legend'):
            return jsonify({'success': False, 'error': 'This free agent is not a legend'}), 400


        # Build or load the legend profile
        legend_data = fa_dict.get('legend_profile') or {}
        if legend_data and isinstance(legend_data, str):
            legend_data = json.loads(legend_data)

        if not legend_data:
            # Auto-generate one based on existing FA fields
            profile = LegendProfile.generate_for_retired_wrestler(
                age=fa_dict.get('age', 45),
                years_retired=fa_dict.get('years_unemployed', fa_dict.get('weeks_unemployed', 0) // 52),
                is_major_superstar=bool(fa_dict.get('is_major_superstar')),
                popularity=fa_dict.get('popularity', 60),
                injury_retired=(fa_dict.get('retirement_status') == 'injury_retired')
            )
        else:
            profile = LegendProfile.from_dict(legend_data)

        return jsonify({
            'success': True,
            'free_agent_id': fa_id,
            'wrestler_name': fa_dict.get('wrestler_name', 'Unknown'),
            'legend_profile': profile.to_dict()
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'traceback': traceback.format_exc()}), 500


@free_agent_bp.route('/api/free-agents/<fa_id>/approach-legend', methods=['POST'])
def api_approach_legend(fa_id):
    """
    Step 168: Attempt to approach a retired legend about a comeback.
    Requires approach_method in POST body.
    Valid methods: cold_call, mutual_friend, tribute_event, hall_of_fame, desperation_pitch
    """
    free_agent_pool = get_free_agent_pool()
    universe = get_universe()
    try:
        fa = free_agent_pool.get_free_agent_by_id(fa_id)
        if not fa:
            return jsonify({'success': False, 'error': 'Free agent not found'}), 404

        fa_dict = fa.to_dict() if hasattr(fa, 'to_dict') else fa
        if not fa_dict.get('is_legend'):
            return jsonify({'success': False, 'error': 'This free agent is not a legend'}), 400

        data = request.get_json() or {}
        approach_method = data.get('approach_method', 'cold_call')


        valid_approaches = [a.value for a in ComebackApproach]
        if approach_method not in valid_approaches:
            return jsonify({
                'success': False,
                'error': f'Invalid approach method. Valid: {valid_approaches}'
            }), 400

        legend_data = fa_dict.get('legend_profile') or {}
        if legend_data and isinstance(legend_data, str):
            legend_data = json.loads(legend_data)

        if not legend_data:
            profile = LegendProfile.generate_for_retired_wrestler(
                age=fa_dict.get('age', 45),
                years_retired=fa_dict.get('weeks_unemployed', 0) // 52,
                is_major_superstar=bool(fa_dict.get('is_major_superstar')),
                popularity=fa_dict.get('popularity', 60),
                injury_retired=(fa_dict.get('retirement_status') == 'injury_retired')
            )
        else:
            profile = LegendProfile.from_dict(legend_data)

        approach = ComebackApproach(approach_method)
        approach_result = profile.approach_for_comeback(
            approach,
            universe.current_year,
            universe.current_week
        )

        # If successful, bump the free agent's visibility and discovered status
        if approach_result['success']:
            if hasattr(fa, 'discovered'):
                fa.discovered = True
            if hasattr(fa, 'comeback_likelihood'):
                fa.comeback_likelihood = min(100, fa.comeback_likelihood + 15)
            if hasattr(free_agent_pool, 'save_free_agent'):
                free_agent_pool.save_free_agent(fa)

        # Build a clean profile dict with approach_history scrubbed to safe scalars.
        # Never nest profile.to_dict() inside approach_result — approach_history
        # already holds a reference to approach_result, causing a circular ref.
        profile_dict = profile.to_dict()
        safe_history = [
            {
                'approach': h.get('approach'),
                'success': h.get('success'),
                'message': h.get('message'),
                'year': h.get('year'),
                'week': h.get('week'),
            }
            for h in profile_dict.get('approach_history', [])
        ]
        profile_dict['approach_history'] = safe_history

        return jsonify({
            'success': True,
            'approached': approach_result.get('success', False),
            'approach': approach_result.get('approach'),
            'message': approach_result.get('message'),
            'roll': approach_result.get('roll'),
            'threshold': approach_result.get('threshold'),
            'free_agent_id': fa_id,
            'wrestler_name': fa_dict.get('wrestler_name', 'Unknown'),
            'legend_profile': profile_dict,
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'traceback': traceback.format_exc()}), 500


@free_agent_bp.route('/api/free-agents/<fa_id>/legend-limitations')
def api_get_legend_limitations(fa_id):
    """
    Step 169-171: Get match limitations and legacy demands for a returning legend.
    """
    free_agent_pool = get_free_agent_pool()
    try:
        fa = free_agent_pool.get_free_agent_by_id(fa_id)
        if not fa:
            return jsonify({'success': False, 'error': 'Free agent not found'}), 404

        fa_dict = fa.to_dict() if hasattr(fa, 'to_dict') else fa
        if not fa_dict.get('is_legend'):
            return jsonify({'success': False, 'error': 'Not a legend'}), 400


        legend_data = fa_dict.get('legend_profile') or {}
        if legend_data and isinstance(legend_data, str):
            legend_data = json.loads(legend_data)

        if legend_data:
            profile = LegendProfile.from_dict(legend_data)
        else:
            profile = LegendProfile.generate_for_retired_wrestler(
                age=fa_dict.get('age', 45),
                years_retired=fa_dict.get('weeks_unemployed', 0) // 52,
                is_major_superstar=bool(fa_dict.get('is_major_superstar')),
                popularity=fa_dict.get('popularity', 60)
            )

        return jsonify({
            'success': True,
            'wrestler_name': fa_dict.get('wrestler_name', 'Unknown'),
            'age': fa_dict.get('age'),
            'physical_condition': profile.physical_condition,
            'ring_rust_weeks': profile.ring_rust_weeks,
            'match_limitations': profile.match_limitations.to_dict(),
            'limitations_summary': profile.get_appearance_limitations_summary(),
            'legacy_demands': profile.legacy_demands,
            'legacy_demands_display': profile.get_legacy_demands_display(),
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@free_agent_bp.route('/api/free-agents/<fa_id>/announce-farewell', methods=['POST'])
def api_announce_farewell_tour(fa_id):
    """
    Step 172: Announce a farewell tour for a returning legend.
    Optionally pass final_show in POST body.
    """
    free_agent_pool = get_free_agent_pool()
    universe = get_universe()
    try:
        fa = free_agent_pool.get_free_agent_by_id(fa_id)
        if not fa:
            return jsonify({'success': False, 'error': 'Free agent not found'}), 404

        fa_dict = fa.to_dict() if hasattr(fa, 'to_dict') else fa
        data = request.get_json() or {}
        final_show = data.get('final_show')


        legend_data = fa_dict.get('legend_profile') or {}
        if legend_data and isinstance(legend_data, str):
            legend_data = json.loads(legend_data)

        profile = LegendProfile.from_dict(legend_data) if legend_data else LegendProfile()
        result = profile.announce_farewell_tour(
            universe.current_year,
            universe.current_week,
            final_show
        )

        result['success'] = True
        result['wrestler_name'] = fa_dict.get('wrestler_name', 'Unknown')
        result['farewell_tour'] = profile.farewell_tour.to_dict()

        return jsonify(result)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@free_agent_bp.route('/api/free-agents/legends/all')
def api_get_all_legends():
    """
    Step 167: Get all legend free agents with their retirement status breakdown.
    """
    free_agent_pool = get_free_agent_pool()
    try:
        all_fas = free_agent_pool.available_free_agents
        legends = [fa for fa in all_fas if getattr(fa, 'is_legend', False)]


        # Group by retirement status
        by_status = {}
        for legend in legends:
            status = getattr(legend, 'retirement_status', 'semi_retired')
            by_status.setdefault(status, []).append(legend.to_dict() if hasattr(legend, 'to_dict') else legend)

        return jsonify({
            'success': True,
            'total': len(legends),
            'by_status': by_status,
            'legends': [l.to_dict() if hasattr(l, 'to_dict') else l for l in legends],
            'status_options': [s.value for s in RetirementStatus]
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# STEP 185-190: PROSPECT SYSTEM ROUTES
# ============================================================================

@free_agent_bp.route('/api/prospects/discover', methods=['POST'])
def api_discover_prospect():
    """
    Step 185: Discover a new prospect via a specific method.
    POST body: { "method": "indie_show_scouting", "potential": "Midcard", "scouting_accuracy": 70 }
    Deducts discovery cost from balance.
    """
    universe = get_universe()
    free_agent_pool = get_free_agent_pool()
    database = get_database()

    try:
        data = request.get_json() or {}
        method_str = data.get('method', 'indie_show_scouting')
        potential = data.get('potential', 'Midcard')
        scouting_accuracy = data.get('scouting_accuracy', 70)

        import uuid
        from models.free_agent import FreeAgent, FreeAgentSource, FreeAgentVisibility, FreeAgentMood

        try:
            method = ProspectDiscoveryMethod(method_str)
        except ValueError:
            return jsonify({
                'success': False,
                'error': f'Invalid method. Valid: {[m.value for m in ProspectDiscoveryMethod]}'
            }), 400

        discovery_cost = method.base_discovery_cost

        # Check balance
        if discovery_cost > 0 and universe.balance < discovery_cost:
            return jsonify({
                'success': False,
                'error': f'Insufficient funds. Discovery costs ${discovery_cost:,}. Balance: ${universe.balance:,}'
            }), 400

        # Generate prospect profile
        prospect_profile = ProspectProfile.generate_new_prospect(
            discovery_method=method,
            current_year=universe.current_year,
            current_week=universe.current_week,
            potential_ceiling=potential,
            scouting_accuracy=scouting_accuracy
        )

        # Deduct cost
        if discovery_cost > 0:
            universe.balance -= discovery_cost
            try:
                database.update_game_state(balance=universe.balance)
            except Exception:
                pass

        # Generate prospect wrestler name
        first_names = ["Tyler", "Jordan", "Casey", "Alex", "Morgan", "Jamie",
                       "Devon", "Riley", "Taylor", "Blake", "Reese", "Quinn",
                       "Mariana", "Keisha", "Priya", "Yuki", "Aisha", "Zara"]
        last_names = ["Cross", "Storm", "Blade", "Steel", "Kane", "Drake",
                      "Rivers", "Stone", "Cruz", "Torres", "Nakamura", "Okafor",
                      "Bennett", "Walsh", "Diaz", "Petrov", "Yamamoto", "Olu"]

        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        fa_id = f"fa_prospect_{uuid.uuid4().hex[:8]}"
        wrestler_id = f"fa_w_prospect_{uuid.uuid4().hex[:8]}"

        eval_data = prospect_profile.evaluation
        raw_score = eval_data.overall_raw_score()

        # Build FreeAgent object using existing model
        try:
            fa = FreeAgent(
                fa_id=fa_id,
                wrestler_id=wrestler_id,
                wrestler_name=name,
                age=random.randint(18, 24),
                gender=random.choice(['Male', 'Female']),
                alignment=random.choice(['Face', 'Heel', 'Face']),
                role='Jobber',
                brawling=max(25, raw_score - 10 + random.randint(-8, 8)),
                technical=max(25, raw_score - 5 + random.randint(-8, 8)),
                speed=max(25, raw_score + 5 + random.randint(-8, 8)),
                mic=max(20, raw_score - 20 + random.randint(-8, 8)),
                psychology=max(20, raw_score - 15 + random.randint(-8, 8)),
                stamina=max(30, raw_score + random.randint(-8, 8)),
                years_experience=random.randint(0, 2),
                is_major_superstar=False,
                popularity=random.randint(5, 25),
                source=FreeAgentSource.PROSPECT,
                visibility=FreeAgentVisibility.TIER_3,
                mood=FreeAgentMood.HUNGRY,
                market_value=prospect_profile.developmental_contract.base_salary,
                is_prospect=True,
                ceiling_potential=eval_data.true_ceiling,
                training_investment_needed=prospect_profile.total_training_invested or 15000,
                available_from_year=universe.current_year,
                available_from_week=universe.current_week,
            )
            fa.discovered = True

            free_agent_pool.available_free_agents.append(fa)
            if hasattr(free_agent_pool, 'save_free_agent'):
                free_agent_pool.save_free_agent(fa)

            fa_dict = fa.to_dict()
        except Exception as fa_err:
            # Fallback: return just the profile without adding to pool
            fa_dict = {
                'id': fa_id,
                'wrestler_name': name,
                'is_prospect': True,
                'ceiling_potential': eval_data.true_ceiling
            }

        return jsonify({
            'success': True,
            'discovery_cost': discovery_cost,
            'remaining_balance': universe.balance,
            'free_agent': fa_dict,
            'prospect_profile': prospect_profile.to_dict(),
            'message': f'Discovered {name} via {method.label}! Ceiling: {eval_data.ceiling_display()}',
            'competing_offers': prospect_profile.competition.has_competing_offer,
            'rival_interest': prospect_profile.competition.rival_promotions_scouting,
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'traceback': traceback.format_exc()}), 500


@free_agent_bp.route('/api/prospects/<fa_id>/evaluate')
def api_evaluate_prospect(fa_id):
    """
    Step 186: Get detailed evaluation metrics for a prospect.
    Returns observable scores and ceiling estimate range.
    """
    free_agent_pool = get_free_agent_pool()
    try:
        fa = free_agent_pool.get_free_agent_by_id(fa_id)
        if not fa:
            return jsonify({'success': False, 'error': 'Prospect not found'}), 404

        fa_dict = fa.to_dict() if hasattr(fa, 'to_dict') else fa
        if not fa_dict.get('is_prospect'):
            return jsonify({'success': False, 'error': 'This free agent is not a prospect'}), 400


        # Generate evaluation based on current attributes
        attrs = fa_dict.get('attributes', {})
        brawling = attrs.get('brawling', fa_dict.get('brawling', 40))
        technical = attrs.get('technical', fa_dict.get('technical', 40))
        speed = attrs.get('speed', fa_dict.get('speed', 40))
        mic = attrs.get('mic', fa_dict.get('mic', 30))
        psychology = attrs.get('psychology', fa_dict.get('psychology', 30))
        stamina = attrs.get('stamina', fa_dict.get('stamina', 40))

        ceiling = fa_dict.get('ceiling_potential', 60)

        eval_data = ProspectEvaluation(
            athletic_ability=int((brawling + speed + stamina) / 3),
            learning_speed=int((technical + psychology) / 2),
            personality_presence=int(mic * 1.1),
            physical_appearance=random.randint(45, 75),
            microphone_potential=mic,
            work_ethic=random.randint(50, 85),
            true_ceiling=ceiling,
            ceiling_range_low=max(30, ceiling - random.randint(5, 15)),
            ceiling_range_high=min(100, ceiling + random.randint(5, 15)),
            evaluation_confidence=random.randint(55, 85)
        )

        return jsonify({
            'success': True,
            'free_agent_id': fa_id,
            'wrestler_name': fa_dict.get('wrestler_name', 'Unknown'),
            'evaluation': eval_data.to_dict(),
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@free_agent_bp.route('/api/prospects/<fa_id>/set-training', methods=['POST'])
def api_set_prospect_training(fa_id):
    """
    Step 188: Set or change training investment level for a prospect.
    POST body: { "training_level": "extensive" }
    Valid levels: none, basic, standard, extensive, veteran_mentorship, outside_supplements
    """
    free_agent_pool = get_free_agent_pool()
    universe = get_universe()
    try:
        fa = free_agent_pool.get_free_agent_by_id(fa_id)
        if not fa:
            return jsonify({'success': False, 'error': 'Prospect not found'}), 404

        fa_dict = fa.to_dict() if hasattr(fa, 'to_dict') else fa
        if not fa_dict.get('is_prospect'):
            return jsonify({'success': False, 'error': 'Not a prospect'}), 400

        data = request.get_json() or {}
        level_str = data.get('training_level', 'standard')

        try:
            level = TrainingInvestmentLevel(level_str)
        except ValueError:
            return jsonify({
                'success': False,
                'error': f'Invalid level. Valid: {[l.value for l in TrainingInvestmentLevel]}'
            }), 400

        return jsonify({
            'success': True,
            'free_agent_id': fa_id,
            'wrestler_name': fa_dict.get('wrestler_name', 'Unknown'),
            'training_level': level.value,
            'training_level_label': level.label,
            'training_description': level.description,
            'weekly_cost': level.weekly_cost,
            'development_speed_modifier': level.development_speed_modifier,
            'message': f'Training level set to {level.label}. Weekly cost: ${level.weekly_cost:,}'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@free_agent_bp.route('/api/prospects/<fa_id>/assign-mentor', methods=['POST'])
def api_assign_prospect_mentor(fa_id):
    """
    Step 188: Assign a veteran wrestler as mentor to a prospect.
    POST body: { "mentor_wrestler_id": "w001" }
    """
    free_agent_pool = get_free_agent_pool()
    universe = get_universe()
    try:
        fa = free_agent_pool.get_free_agent_by_id(fa_id)
        if not fa:
            return jsonify({'success': False, 'error': 'Prospect not found'}), 404

        fa_dict = fa.to_dict() if hasattr(fa, 'to_dict') else fa
        if not fa_dict.get('is_prospect'):
            return jsonify({'success': False, 'error': 'Not a prospect'}), 400

        data = request.get_json() or {}
        mentor_id = data.get('mentor_wrestler_id')
        if not mentor_id:
            return jsonify({'success': False, 'error': 'mentor_wrestler_id required'}), 400

        # Look up the mentor from the roster
        mentor = universe.get_wrestler_by_id(mentor_id) if hasattr(universe, 'get_wrestler_by_id') else None
        mentor_name = mentor.name if mentor else data.get('mentor_name', 'Veteran Mentor')


        return jsonify({
            'success': True,
            'free_agent_id': fa_id,
            'wrestler_name': fa_dict.get('wrestler_name', 'Unknown'),
            'mentor_id': mentor_id,
            'mentor_name': mentor_name,
            'training_level': TrainingInvestmentLevel.VETERAN_MENTORSHIP.value,
            'weekly_cost': TrainingInvestmentLevel.VETERAN_MENTORSHIP.weekly_cost,
            'development_speed': TrainingInvestmentLevel.VETERAN_MENTORSHIP.development_speed_modifier,
            'note': f'{mentor_name} is now mentoring {fa_dict.get("wrestler_name", "the prospect")}. '
                    f'Development speed: {TrainingInvestmentLevel.VETERAN_MENTORSHIP.development_speed_modifier}x. '
                    f'Note: This costs goodwill from the mentor.',
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@free_agent_bp.route('/api/prospects/<fa_id>/breakthrough-status')
def api_prospect_breakthrough_status(fa_id):
    """
    Step 190: Get current breakthrough readiness for a prospect.
    Shows whether it's too early, perfect timing, or overdue to promote.
    """
    free_agent_pool = get_free_agent_pool()
    universe = get_universe()
    try:
        fa = free_agent_pool.get_free_agent_by_id(fa_id)
        if not fa:
            return jsonify({'success': False, 'error': 'Prospect not found'}), 404

        fa_dict = fa.to_dict() if hasattr(fa, 'to_dict') else fa
        if not fa_dict.get('is_prospect'):
            return jsonify({'success': False, 'error': 'Not a prospect'}), 400


        # Estimate progress based on FA data
        weeks_in_system = fa_dict.get('weeks_unemployed', 0)
        # "weeks_unemployed" = 0 for new prospects, but we need weeks since signing
        # Use training_investment_needed as a proxy for ceiling
        ceiling = fa_dict.get('ceiling_potential', 60)
        if ceiling >= 80:
            weeks_needed = 40
        elif ceiling >= 65:
            weeks_needed = 60
        else:
            weeks_needed = 80

        progress = min(100, int((weeks_in_system / weeks_needed) * 100)) if weeks_needed > 0 else 0

        if progress < 50:
            status = BreakthroughStatus.NOT_READY
        elif progress < 75:
            status = BreakthroughStatus.APPROACHING
        elif progress <= 100:
            status = BreakthroughStatus.READY
        else:
            status = BreakthroughStatus.OVERDUE

        return jsonify({
            'success': True,
            'free_agent_id': fa_id,
            'wrestler_name': fa_dict.get('wrestler_name', 'Unknown'),
            'development_progress': progress,
            'breakthrough_status': status.value,
            'breakthrough_label': status.label,
            'promotion_risk': status.promotion_risk,
            'ceiling_potential': ceiling,
            'recommendation': _get_promotion_recommendation(status, fa_dict),
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@free_agent_bp.route('/api/prospects/<fa_id>/promote', methods=['POST'])
def api_promote_prospect_to_roster(fa_id):
    """
    Step 190: Promote a signed prospect to the main roster.
    Calculates timing quality (early/perfect/late) and morale impact.
    POST body: { "target_brand": "ROC Alpha", "target_role": "Lower Midcard" }
    """
    free_agent_pool = get_free_agent_pool()
    universe = get_universe()
    try:
        fa = free_agent_pool.get_free_agent_by_id(fa_id)
        if not fa:
            return jsonify({'success': False, 'error': 'Prospect not found'}), 404

        fa_dict = fa.to_dict() if hasattr(fa, 'to_dict') else fa
        if not fa_dict.get('is_prospect'):
            return jsonify({'success': False, 'error': 'Not a prospect'}), 400

        data = request.get_json() or {}
        target_brand = data.get('target_brand', 'ROC Alpha')
        target_role = data.get('target_role', 'Lower Midcard')


        ceiling = fa_dict.get('ceiling_potential', 60)
        weeks_in_system = fa_dict.get('weeks_unemployed', 0)
        if ceiling >= 80:
            weeks_needed = 40
        elif ceiling >= 65:
            weeks_needed = 60
        else:
            weeks_needed = 80
        progress = min(120, int((weeks_in_system / weeks_needed) * 100)) if weeks_needed > 0 else 50

        if progress < 50:
            timing = "early"
            morale_impact = -20
            message = (f"⚠️ Premature promotion! {fa_dict.get('wrestler_name')} isn't ready yet. "
                       f"Expect struggles and a confidence hit.")
        elif progress < 75:
            timing = "slightly_early"
            morale_impact = -5
            message = (f"A bit early, but {fa_dict.get('wrestler_name')} can make it work "
                       f"with strong creative support.")
        elif progress <= 100:
            timing = "perfect"
            morale_impact = +15
            message = (f"✅ Perfect timing! {fa_dict.get('wrestler_name')} is ready. "
                       f"This feels like an organic debut.")
        else:
            timing = "late"
            morale_impact = -10
            message = (f"⏰ Overdue. {fa_dict.get('wrestler_name')} has been waiting too long. "
                       f"They're relieved, but some frustration lingers.")

        morale_after = max(30, min(100, 70 + morale_impact))

        return jsonify({
            'success': True,
            'free_agent_id': fa_id,
            'wrestler_name': fa_dict.get('wrestler_name', 'Unknown'),
            'target_brand': target_brand,
            'target_role': target_role,
            'promotion_timing': timing,
            'morale_impact': morale_impact,
            'morale_after_promotion': morale_after,
            'development_progress': progress,
            'message': message,
            'next_step': 'Use the roster signing flow to officially add them to the brand.',
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@free_agent_bp.route('/api/prospects/all')
def api_get_all_prospects():
    """
    Step 185-190: Get all prospects with their development status.
    """
    free_agent_pool = get_free_agent_pool()
    universe = get_universe()
    try:
        all_fas = free_agent_pool.available_free_agents
        prospects = [fa for fa in all_fas if getattr(fa, 'is_prospect', False)]


        result = []
        for p in prospects:
            p_dict = p.to_dict() if hasattr(p, 'to_dict') else p
            ceiling = p_dict.get('ceiling_potential', 60)
            weeks_in_system = p_dict.get('weeks_unemployed', 0)

            if ceiling >= 80:
                weeks_needed = 40
            elif ceiling >= 65:
                weeks_needed = 60
            else:
                weeks_needed = 80

            progress = min(120, int((weeks_in_system / weeks_needed) * 100)) if weeks_needed > 0 else 0

            if progress < 50:
                status = BreakthroughStatus.NOT_READY
            elif progress < 75:
                status = BreakthroughStatus.APPROACHING
            elif progress <= 100:
                status = BreakthroughStatus.READY
            else:
                status = BreakthroughStatus.OVERDUE

            p_dict['development_progress'] = progress
            p_dict['breakthrough_status'] = status.value
            p_dict['breakthrough_label'] = status.label
            result.append(p_dict)

        # Sort: ready first, then approaching, then not_ready
        order = {
            'ready': 0, 'overdue': 1, 'approaching': 2, 'not_ready': 3, 'breakthrough': 4
        }
        result.sort(key=lambda x: order.get(x.get('breakthrough_status', 'not_ready'), 99))

        return jsonify({
            'success': True,
            'total': len(result),
            'ready_for_promotion': sum(1 for p in result if p.get('breakthrough_status') == 'ready'),
            'overdue': sum(1 for p in result if p.get('breakthrough_status') == 'overdue'),
            'prospects': result,
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@free_agent_bp.route('/api/prospects/discovery-methods')
def api_get_discovery_methods():
    """
    Step 185: List all available prospect discovery methods with costs.
    """
    methods = [
        {
            'value': m.value,
            'label': m.label,
            'cost': m.base_discovery_cost,
        }
        for m in ProspectDiscoveryMethod
    ]
    return jsonify({'success': True, 'methods': methods})


@free_agent_bp.route('/api/prospects/training-levels')
def api_get_training_levels():
    """
    Step 188: List all training investment levels with costs and descriptions.
    """
    levels = [
        {
            'value': l.value,
            'label': l.label,
            'weekly_cost': l.weekly_cost,
            'description': l.description,
            'speed_modifier': l.development_speed_modifier,
        }
        for l in TrainingInvestmentLevel
    ]
    return jsonify({'success': True, 'training_levels': levels})


# ============================================================================
# Helper
# ============================================================================

def _get_promotion_recommendation(status, fa_dict: dict) -> str:
    name = fa_dict.get('wrestler_name', 'This prospect')
    rec = {
        'not_ready': f"Wait. {name} needs more development time. Premature promotion risks their long-term potential.",
        'approaching': f"{name} is close. Consider promoting in 4–8 weeks, or sooner with a strong storyline hook.",
        'ready': f"Now is the right time. {name} is at peak readiness for a main roster debut.",
        'overdue': f"Act immediately. {name} has been waiting too long and morale is suffering. Promote now.",
        'breakthrough': f"{name} has already been promoted to the main roster.",
    }
    return rec.get(status.value, "No recommendation available.")


# ============================================================================
# STEP 134: NEGOTIATION SESSION ROUTES
# These power the full negotiation.html interface.
# ============================================================================

# In-memory session store (keyed by session_id)
# In production this would be persisted to SQLite, but for now
# sessions survive the request lifecycle fine for single-user play.
_negotiation_sessions = {}


def _build_session(fa_dict, fa_id, year, week):
    """Build a fresh negotiation session dict from a free agent."""
    import uuid
    demands = fa_dict.get('demands') or {}
    asking  = demands.get('asking_salary') or fa_dict.get('market_value', 10000)
    minimum = demands.get('minimum_salary') or int(asking * 0.65)
    mood    = fa_dict.get('mood', 'patient')

    # Mood affects patience / max rounds
    patience_by_mood = {
        'patient': 3, 'hungry': 3, 'desperate': 4,
        'bitter': 2, 'arrogant': 2,
    }
    max_rounds = patience_by_mood.get(mood, 3)

    session_id = str(uuid.uuid4())
    session = {
        'session_id': session_id,
        'fa_id': fa_id,
        'wrestler_name': fa_dict.get('wrestler_name', 'Unknown'),
        'round_number': 1,
        'max_rounds': max_rounds,
        'status': 'active',
        'asking_salary': asking,
        'minimum_salary': minimum,
        'mood': mood,
        'patience': 100,
        'year': year,
        'week': week,
        'log': [],
        'last_counter': None,
        'third_party_used': False,
        'flexibility': _build_flexibility(fa_dict),
        'tells': _build_tells(fa_dict),
        'deadline': _build_deadline(fa_dict, year, week),
    }
    return session_id, session


def _build_flexibility(fa_dict):
    """Step 137: How far will each side move?"""
    mood = fa_dict.get('mood', 'patient')
    points = {'patient': 3, 'hungry': 4, 'desperate': 5, 'bitter': 2, 'arrogant': 1}
    return {
        'movement_points_remaining': points.get(mood, 3),
        'total_movement_points': points.get(mood, 3),
        'salary_flexibility': 'moderate',
        'length_flexibility': 'moderate',
        'creative_flexibility': 'low' if fa_dict.get('is_major_superstar') else 'moderate',
    }


def _build_tells(fa_dict):
    """Step 138: Reading the room — hints about what the FA really wants."""
    tells = []
    if fa_dict.get('is_major_superstar'):
        tells.append('They keep circling back to creative control — that matters to them.')
    mood = fa_dict.get('mood', 'patient')
    if mood == 'desperate':
        tells.append("They accepted your salary range quickly — money isn't the main sticking point.")
    elif mood == 'bitter':
        tells.append('There\'s tension when contract length comes up. They want short-term commitment.')
    elif mood == 'arrogant':
        tells.append("They hesitate on length — they don't want to be locked in long-term.")
    if fa_dict.get('has_controversy'):
        tells.append('They seem eager to move past their recent history. Redemption matters here.')
    return tells


def _build_deadline(fa_dict, year, week):
    """Step 140: Does this negotiation have a hard deadline?"""
    rival_interest = fa_dict.get('rival_interest') or []
    has_rival_offer = any(
        (r.get('offer_made') or r.get('offer_salary', 0) > 0)
        for r in rival_interest
    )
    if has_rival_offer:
        deadline_week = week + random.randint(2, 5)
        return {
            'has_deadline': True,
            'reason': 'Rival promotion has made an offer',
            'deadline_year': year,
            'deadline_week': deadline_week,
            'weeks_remaining': deadline_week - week,
        }
    return {'has_deadline': False}


def _score_offer(offer, session):
    """
    Score an offer 0-100 from the FA's perspective.
    Used by both /probability and /offer endpoints.
    """
    asking  = session['asking_salary']
    minimum = session['minimum_salary']
    mood    = session['mood']
    score   = 0

    salary = offer.get('salary_per_show', 0)
    if salary < minimum:
        return 0
    ratio = salary / asking if asking > 0 else 1.0
    if ratio >= 1.2:
        score += 50
    elif ratio >= 1.0:
        score += 40
    elif ratio >= 0.85:
        score += 25
    else:
        score += max(0, int(((salary - minimum) / max(asking - minimum, 1)) * 25))

    # Signing bonus (Step 144)
    bonus = offer.get('signing_bonus', 0)
    if bonus >= 100000: score += 15
    elif bonus >= 50000: score += 10
    elif bonus >= 25000: score += 7
    elif bonus >= 10000: score += 4

    # Creative clauses (Steps 149-155)
    cc = offer.get('creative_clauses', {})
    ctrl_scores = {'none': 0, 'consultation': 3, 'approval': 6, 'partnership': 10, 'full': 15}
    score += ctrl_scores.get(cc.get('creative_control', 'none'), 0)
    if cc.get('title_guarantee_check'): score += 8
    if cc.get('storyline_veto_rights'): score += 4
    if cc.get('finish_protection'): score += 3

    # Lifestyle clauses (Steps 156-160)
    lc = offer.get('lifestyle_clauses', {})
    if lc.get('first_class_travel'): score += 3
    if lc.get('injury_pay_protection'): score += 5
    if lc.get('injury_job_security'): score += 4
    if lc.get('outside_projects_allowed'): score += 3
    if lc.get('family_time_off'): score += 2

    # Mood modifiers (Step 117)
    mood_mod = {'desperate': 15, 'hungry': 8, 'patient': 0, 'bitter': -10, 'arrogant': -8}
    score += mood_mod.get(mood, 0)

    return max(0, min(100, score))


def _make_counter_offer(offer, session):
    """Generate a counter-offer dict from the FA."""
    asking   = session['asking_salary']
    current  = offer.get('salary_per_show', 0)
    # Counter is between current offer and asking price
    counter_salary = int(current + (asking - current) * random.uniform(0.5, 0.85))
    counter_salary = max(session['minimum_salary'], (counter_salary // 500) * 500)

    counter = {
        'salary_per_show': counter_salary,
        'contract_weeks': offer.get('contract_weeks', 52),
        'signing_bonus': offer.get('signing_bonus', 0),
    }
    session['last_counter'] = counter
    return counter


def _tell_for_round(session, offer):
    """Step 138: Return a contextual tell based on current offer state."""
    tells = session.get('tells', [])
    if tells:
        idx = (session['round_number'] - 1) % len(tells)
        return tells[idx]
    score = _score_offer(offer, session)
    if score < 30:
        return "They seem unimpressed. Salary may be too low."
    elif score < 55:
        return "They're listening but not sold yet. Something is missing."
    else:
        return "They seem genuinely interested. Push a bit more to close."


@free_agent_bp.route('/api/free-agents/legacy-negotiation/start', methods=['POST'])
def api_negotiation_start():
    """
    Step 134: Start a new negotiation session.
    Returns session object with round tracking, flexibility, tells, and deadline.
    POST: { fa_id: "fa_init_001" }
    """
    universe = get_universe()
    free_agent_pool = get_free_agent_pool()
    try:
        data = request.get_json() or {}
        fa_id = data.get('fa_id')
        if not fa_id:
            return jsonify({'success': False, 'error': 'fa_id required'}), 400

        fa = free_agent_pool.get_free_agent_by_id(fa_id)
        if not fa:
            return jsonify({'success': False, 'error': 'Free agent not found'}), 404

        fa_dict = fa.to_dict() if hasattr(fa, 'to_dict') else fa

        session_id, session = _build_session(
            fa_dict, fa_id,
            universe.current_year,
            universe.current_week
        )
        _negotiation_sessions[session_id] = session

        # Opening guidance based on mood (Step 135)
        mood = fa_dict.get('mood', 'patient')
        guidance_by_mood = {
            'patient':    "They're in no rush. Don't lowball — they'll walk rather than settle.",
            'hungry':     "They want to work. A fair offer will likely land. Don't drag it out.",
            'desperate':  "They need a deal. Even a below-asking offer may close here.",
            'bitter':     "They're coming in with a chip on their shoulder. Lead with respect.",
            'arrogant':   "They think they're worth more than the market says. Manage expectations.",
        }
        opening_guidance = guidance_by_mood.get(mood, "Begin negotiations when ready.")

        deadline_warning = None
        if session['deadline']['has_deadline']:
            w = session['deadline']['weeks_remaining']
            rival = next(
                (r.get('promotion_name', 'A rival') for r in (fa_dict.get('rival_interest') or [])
                 if r.get('offer_made') or r.get('offer_salary', 0) > 0),
                'A rival promotion'
            )
            deadline_warning = f"⚠️ {rival} has made an offer. You have ~{w} week(s) to close this deal."

        return jsonify({
            'success': True,
            'session': session,
            'opening_guidance': opening_guidance,
            'deadline_warning': deadline_warning,
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'traceback': traceback.format_exc()}), 500


@free_agent_bp.route('/api/free-agents/legacy-negotiation/<session_id>/probability', methods=['POST'])
def api_negotiation_probability(session_id):
    """
    Step 134/137: Calculate live acceptance probability for current offer terms.
    Called on every slider change in negotiation.html.
    POST: full offer object from buildOffer()
    """
    try:
        session = _negotiation_sessions.get(session_id)
        offer   = request.get_json() or {}

        if not session:
            # Graceful fallback — calculate without session context
            salary  = offer.get('salary_per_show', 0)
            prob    = min(95, max(5, int(salary / 100)))
            return jsonify({
                'success': True,
                'probability_breakdown': {
                    'final_probability': prob,
                    'recommendation': 'Session not found — showing estimate only.',
                }
            })

        score = _score_offer(offer, session)

        # Breakdown for UI
        asking   = session['asking_salary']
        salary   = offer.get('salary_per_show', 0)
        ratio    = salary / asking if asking > 0 else 0
        rec_map  = [
            (80, "Strong offer — good chance of acceptance."),
            (60, "Solid offer. Consider sweetening creative terms to push over the line."),
            (40, "Borderline. Raise salary or add a signing bonus."),
            (20, "Weak offer. Significant gap to close."),
            (0,  "Below minimum — this will be rejected outright."),
        ]
        recommendation = next((r for threshold, r in rec_map if score >= threshold), rec_map[-1][1])

        return jsonify({
            'success': True,
            'probability_breakdown': {
                'final_probability': score,
                'salary_ratio': round(ratio, 2),
                'salary_score': min(50, int(ratio * 40)),
                'bonus_score': min(15, int(offer.get('signing_bonus', 0) / 7000)),
                'creative_score': min(15, sum([
                    {'none':0,'consultation':3,'approval':6,'partnership':10,'full':15}.get(
                        offer.get('creative_clauses', {}).get('creative_control','none'), 0
                    ),
                    8 if offer.get('creative_clauses', {}).get('title_guarantee_check') else 0,
                ])),
                'mood_modifier': {'desperate':15,'hungry':8,'patient':0,'bitter':-10,'arrogant':-8}.get(session['mood'], 0),
                'recommendation': recommendation,
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@free_agent_bp.route('/api/free-agents/legacy-negotiation/<session_id>/offer', methods=['POST'])
def api_negotiation_offer(session_id):
    """
    Step 134-140: Submit a round offer. Returns accepted / countered / rejected.
    POST: full offer object from buildOffer()
    """
    universe = get_universe()
    free_agent_pool = get_free_agent_pool()
    database = get_database()
    try:
        session = _negotiation_sessions.get(session_id)
        if not session:
            return jsonify({'success': False, 'error': 'Session not found or expired'}), 404

        if session['status'] != 'active':
            return jsonify({'success': False, 'error': f"Session is {session['status']}"}), 400

        offer = request.get_json() or {}
        score = _score_offer(offer, session)
        round_num = session['round_number']

        # Step 135-136: Opening offer tone
        asking   = session['asking_salary']
        salary   = offer.get('salary_per_show', 0)
        minimum  = session['minimum_salary']

        if salary < minimum:
            session['status'] = 'rejected'
            return jsonify({
                'success': True,
                'outcome': 'rejected',
                'message': f"{session['wrestler_name']} won't even consider this. Offer is below their minimum of ${minimum:,}/show.",
                'session': session,
            })

        # Acceptance thresholds tighten in later rounds
        accept_threshold = 65 - (round_num - 1) * 5

        if score >= accept_threshold:
            # ACCEPTED
            session['status'] = 'accepted'

            # Deduct signing bonus from balance
            bonus = offer.get('signing_bonus', 0)
            if bonus > 0 and universe.balance >= bonus:
                universe.balance -= bonus
                try:
                    database.update_game_state(balance=universe.balance)
                except Exception:
                    pass

            # Remove from free agent pool
            try:
                if hasattr(free_agent_pool, 'remove_free_agent'):
                    free_agent_pool.remove_free_agent(session['fa_id'])
            except Exception:
                pass

            return jsonify({
                'success': True,
                'outcome': 'accepted',
                'message': f"🎉 {session['wrestler_name']} accepts your offer! They're signing with Ring of Champions.",
                'session': session,
                'signing_result': {
                    'salary': salary,
                    'weeks': offer.get('contract_weeks', 52),
                    'bonus': bonus,
                },
            })

        elif round_num >= session['max_rounds']:
            # Out of rounds — rejected
            session['status'] = 'rejected'
            return jsonify({
                'success': True,
                'outcome': 'rejected',
                'message': f"{session['wrestler_name']} has run out of patience. Negotiations have broken down.",
                'session': session,
            })

        else:
            # COUNTER OFFER
            counter = _make_counter_offer(offer, session)
            tell    = _tell_for_round(session, offer)
            session['round_number'] += 1
            session['flexibility']['movement_points_remaining'] = max(
                0, session['flexibility']['movement_points_remaining'] - 1
            )

            mood_responses = {
                'patient':   f"{session['wrestler_name']} listens carefully, then counters.",
                'hungry':    f"{session['wrestler_name']} is keen but needs a bit more.",
                'desperate': f"{session['wrestler_name']} seems tempted but their agent pushes back.",
                'bitter':    f"{session['wrestler_name']} frowns. 'You can do better than that.'",
                'arrogant':  f"{session['wrestler_name']} laughs. 'Is that the best you've got?'",
            }
            message = mood_responses.get(session['mood'],
                f"{session['wrestler_name']} makes a counter-offer.")
            message += f" Counter: ${counter['salary_per_show']:,}/show."

            return jsonify({
                'success': True,
                'outcome': 'countered',
                'message': message,
                'tell': tell,
                'counter_offer': counter,
                'session': session,
            })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'traceback': traceback.format_exc()}), 500


@free_agent_bp.route('/api/free-agents/legacy-negotiation/<session_id>/counter-accept', methods=['POST'])
def api_negotiation_counter_accept(session_id):
    """
    Step 136: Player accepts the FA's counter-offer.
    """
    universe = get_universe()
    free_agent_pool = get_free_agent_pool()
    database = get_database()
    try:
        session = _negotiation_sessions.get(session_id)
        if not session:
            return jsonify({'success': False, 'error': 'Session not found'}), 404

        counter = session.get('last_counter')
        if not counter:
            return jsonify({'success': False, 'error': 'No counter-offer to accept'}), 400

        session['status'] = 'accepted'

        bonus = counter.get('signing_bonus', 0)
        if bonus > 0:
            try:
                universe.balance -= bonus
                database.update_game_state(balance=universe.balance)
            except Exception:
                pass

        try:
            if hasattr(free_agent_pool, 'remove_free_agent'):
                free_agent_pool.remove_free_agent(session['fa_id'])
        except Exception:
            pass

        return jsonify({
            'success': True,
            'outcome': 'accepted',
            'message': f"✅ You accepted {session['wrestler_name']}'s counter-offer. Deal done!",
            'session': session,
            'signing_result': counter,
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@free_agent_bp.route('/api/free-agents/legacy-negotiation/<session_id>/pause', methods=['POST'])
def api_negotiation_pause(session_id):
    """
    Step 139: Walk away / pause negotiations temporarily.
    """
    try:
        session = _negotiation_sessions.get(session_id)
        if not session:
            return jsonify({'success': False, 'error': 'Session not found'}), 404

        session['status'] = 'paused'
        has_deadline = session.get('deadline', {}).get('has_deadline', False)

        warning = None
        if has_deadline:
            warning = "⚠️ Warning: A rival promotion has made an offer. Walking away now risks losing them."

        return jsonify({
            'success': True,
            'message': f"Negotiations with {session['wrestler_name']} paused. You can return later, but they may lose patience.",
            'warning': warning,
            'session': session,
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@free_agent_bp.route('/api/free-agents/legacy-negotiation/<session_id>/third-party', methods=['POST'])
def api_negotiation_third_party(session_id):
    """
    Step 141: Bring in a third-party ally (roster member) to vouch for the promotion.
    POST: { ally_id, ally_type, ally_name }
    """
    universe = get_universe()
    try:
        session = _negotiation_sessions.get(session_id)
        if not session:
            return jsonify({'success': False, 'error': 'Session not found'}), 404

        if session.get('third_party_used'):
            return jsonify({'success': False, 'error': 'Third-party intervention already used this negotiation'}), 400

        data = request.get_json() or {}
        ally_id   = data.get('ally_id')
        ally_type = data.get('ally_type', 'friend')
        ally_name = data.get('ally_name', 'A roster member')

        if not ally_id:
            return jsonify({'success': False, 'error': 'ally_id required'}), 400

        # Look up ally on roster
        ally = universe.get_wrestler_by_id(ally_id) if hasattr(universe, 'get_wrestler_by_id') else None
        ally_pop = ally.popularity if ally else 50
        ally_role = ally.role if ally else 'Midcard'

        # Impact scales with ally's popularity and role
        role_bonus = {'Main Event': 15, 'Upper Midcard': 10, 'Midcard': 5}.get(ally_role, 3)
        pop_bonus  = int(ally_pop / 10)
        total_boost = role_bonus + pop_bonus

        type_messages = {
            'friend':  f"{ally_name} speaks highly of working here. The FA seems to appreciate the personal touch.",
            'legend':  f"{ally_name}'s endorsement carries serious weight. The FA's eyes light up.",
            'fan':     f"Turns out the FA has always respected {ally_name}'s work. Good connection.",
        }
        message = type_messages.get(ally_type, f"{ally_name} put in a good word.")
        message += f" Acceptance probability boosted by ~{total_boost}%."

        # Apply boost to session's asking/minimum (effectively makes them easier to please)
        session['asking_salary']  = max(1, int(session['asking_salary']  * (1 - total_boost / 200)))
        session['minimum_salary'] = max(1, int(session['minimum_salary'] * (1 - total_boost / 300)))
        session['third_party_used'] = True

        return jsonify({
            'success': True,
            'message': message,
            'boost': total_boost,
            'ally_name': ally_name,
            'session': session,
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@free_agent_bp.route('/api/free-agents/<fa_id>/negotiation-state')
def api_get_negotiation_state(fa_id):
    """
    Fallback: get any active session state for a given FA.
    Used when negotiation.html loads and checks for an in-progress session.
    """
    try:
        active = next(
            (s for s in _negotiation_sessions.values()
             if s['fa_id'] == fa_id and s['status'] == 'active'),
            None
        )
        if active:
            return jsonify({'success': True, 'state': active})
        return jsonify({'success': True, 'state': None})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@free_agent_bp.route('/api/free-agents/<fa_id>/rival-interest')
def api_get_rival_interest(fa_id):
    """
    Step 126: Get rival promotion interest for a specific free agent.
    Used by negotiation.html to display the bidding war alert.
    """
    free_agent_pool = get_free_agent_pool()
    try:
        fa = free_agent_pool.get_free_agent_by_id(fa_id)
        if not fa:
            return jsonify({'success': False, 'error': 'Free agent not found'}), 404

        fa_dict = fa.to_dict() if hasattr(fa, 'to_dict') else fa
        rival_interest = fa_dict.get('rival_interest') or []

        interested = [
            r for r in rival_interest
            if (r.get('interest_level', 0) >= 50 or r.get('offer_made') or r.get('offer_salary', 0) > 0)
        ]

        return jsonify({
            'success': True,
            'fa_id': fa_id,
            'wrestler_name': fa_dict.get('wrestler_name'),
            'total_interested': len(interested),
            'has_offer': any(r.get('offer_made') or r.get('offer_salary', 0) > 0 for r in interested),
            'rivals': interested,
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500