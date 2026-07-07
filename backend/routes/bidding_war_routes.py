"""
Bidding War Routes
STEPS 126-133: Rival promotion interest, bidding rounds, strategic decisions,
               outbid notifications, and anti-bidding-war tactics.

Register in routes/__init__.py:
    from routes.bidding_war_routes import bidding_war_bp
    app.register_blueprint(bidding_war_bp)
"""

from flask import Blueprint, jsonify, request, current_app
import traceback

bidding_war_bp = Blueprint('bidding_war', __name__)


# -------------------------------------------------------------------------- #
# Helpers                                                                     #
# -------------------------------------------------------------------------- #

def get_database():
    return current_app.config['DATABASE']

def get_universe():
    return current_app.config['UNIVERSE']

def get_free_agent_pool():
    return current_app.config.get('FREE_AGENT_POOL')

def get_rival_manager():
    return current_app.config.get('RIVAL_PROMOTION_MANAGER')

def get_bidding_engine():
    return current_app.config.get('BIDDING_WAR_ENGINE')


# ============================================================================ #
# STEP 126: Rival Promotion Interest                                           #
# ============================================================================ #

@bidding_war_bp.route('/api/rivals')
def api_get_rivals():
    """Get all rival promotions with their current state."""
    rival_manager = get_rival_manager()
    try:
        return jsonify({
            'success': True,
            'total': len(rival_manager.get_all_promotions()),
            'rivals': rival_manager.to_dict_list()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bidding_war_bp.route('/api/rivals/<promotion_id>')
def api_get_rival(promotion_id):
    """Get a single rival promotion."""
    rival_manager = get_rival_manager()
    promo = rival_manager.get_promotion_by_id(promotion_id)
    if not promo:
        return jsonify({'success': False, 'error': 'Promotion not found'}), 404
    return jsonify({'success': True, 'rival': promo.to_dict()})


@bidding_war_bp.route('/api/rivals/<promotion_id>/relationship-history')
def api_get_rival_relationship_history(promotion_id):
    """Get full relationship log between player and a rival."""
    database = get_database()
    from persistence.rival_promotion_db import get_relationship_history
    try:
        history = get_relationship_history(database, promotion_id)
        return jsonify({'success': True, 'history': history})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bidding_war_bp.route('/api/free-agents/<fa_id>/rival-interest')
def api_get_rival_interest(fa_id):
    """
    STEP 126: Get rival promotion interest in a specific free agent.
    Returns interest levels and projected initial offers.
    """
    free_agent_pool = get_free_agent_pool()
    engine = get_bidding_engine()
    universe = get_universe()

    try:
        fa = free_agent_pool.get_free_agent_by_id(fa_id)
        if not fa:
            return jsonify({'success': False, 'error': 'Free agent not found'}), 404

        interested = engine.generate_rival_interest(
            fa,
            universe.current_year,
            universe.current_week
        )

        return jsonify({
            'success': True,
            'fa_id': fa_id,
            'fa_name': fa.wrestler_name,
            'total_interested': len([i for i in interested if i['will_bid']]),
            'interest_details': [
                {
                    'promotion_id':    i['promotion'].promotion_id,
                    'promotion_name':  i['promotion'].name,
                    'tier':            i['promotion'].tier.value,
                    'interest_level':  i['interest_level'],
                    'initial_offer':   i['initial_offer'],
                    'will_bid':        i['will_bid'],
                    'prestige':        i['promotion'].prestige,
                    'aggression':      i['promotion'].aggression,
                }
                for i in interested
            ]
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================ #
# STEP 127-128: Starting & Viewing Bidding Wars                               #
# ============================================================================ #

@bidding_war_bp.route('/api/bidding-wars/active')
def api_get_active_bidding_wars():
    """Get all currently open bidding wars."""
    database = get_database()
    from persistence.rival_promotion_db import get_active_bidding_wars
    try:
        wars = get_active_bidding_wars(database)
        return jsonify({'success': True, 'total': len(wars), 'bidding_wars': wars})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bidding_war_bp.route('/api/bidding-wars/<bidding_war_id>')
def api_get_bidding_war(bidding_war_id):
    """Get a single bidding war with full detail."""
    engine = get_bidding_engine()
    try:
        war = engine.load_war(bidding_war_id)
        if not war:
            return jsonify({'success': False, 'error': 'Bidding war not found'}), 404
        return jsonify({'success': True, 'bidding_war': war.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bidding_war_bp.route('/api/free-agents/<fa_id>/start-bidding-war', methods=['POST'])
def api_start_bidding_war(fa_id):
    """
    STEP 127: Start a bidding war for a free agent.
    If you initiate signing, this also triggers rival interest and
    generates their Round 1 offers.

    Optional body: { "force_open": true }
    """
    free_agent_pool = get_free_agent_pool()
    engine = get_bidding_engine()
    universe = get_universe()

    try:
        fa = free_agent_pool.get_free_agent_by_id(fa_id)
        if not fa:
            return jsonify({'success': False, 'error': 'Free agent not found'}), 404

        # Check if a war already exists
        from persistence.rival_promotion_db import get_bidding_war_for_fa
        existing = get_bidding_war_for_fa(get_database(), fa_id)
        if existing:
            return jsonify({
                'success': False,
                'error': 'A bidding war already exists for this free agent.',
                'existing_war_id': existing['bidding_war_id']
            }), 409

        data = request.get_json(silent=True) or {}
        force_open = data.get('force_open', False)

        war = engine.start_bidding_war(
            free_agent=fa,
            year=universe.current_year,
            week=universe.current_week,
            force_open_bidding=force_open
        )

        if not war:
            return jsonify({
                'success': True,
                'bidding_war': None,
                'message': 'No rival promotions are interested in this free agent. You can sign directly.',
                'direct_signing_available': True
            })

        notifications = engine.get_outbid_notifications(
            war, universe.current_year, universe.current_week
        )

        return jsonify({
            'success': True,
            'bidding_war': war.to_dict(),
            'notifications': notifications,
            'message': (
                f"Bidding war started for {fa.wrestler_name}. "
                f"{war.get_active_rival_count()} rival(s) are competing. "
                f"{'Open' if war.is_open_bidding else 'Blind'} bidding."
            )
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================ #
# STEP 130: Outbid Notifications                                               #
# ============================================================================ #

@bidding_war_bp.route('/api/bidding-wars/<bidding_war_id>/notifications')
def api_get_outbid_notifications(bidding_war_id):
    """Get current outbid notifications for a bidding war."""
    engine = get_bidding_engine()
    universe = get_universe()
    try:
        war = engine.load_war(bidding_war_id)
        if not war:
            return jsonify({'success': False, 'error': 'Bidding war not found'}), 404

        notifications = engine.get_outbid_notifications(
            war, universe.current_year, universe.current_week
        )
        return jsonify({'success': True, 'notifications': notifications})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bidding_war_bp.route('/api/bidding-wars/all-notifications')
def api_get_all_notifications():
    """
    Get outbid notifications for ALL active bidding wars.
    Useful for the office dashboard alert panel.
    """
    database = get_database()
    engine = get_bidding_engine()
    universe = get_universe()

    from persistence.rival_promotion_db import get_active_bidding_wars

    try:
        active_wars_data = get_active_bidding_wars(database)
        all_notifications = []

        for war_data in active_wars_data:
            war = engine.load_war(war_data['bidding_war_id'])
            if war:
                notes = engine.get_outbid_notifications(
                    war, universe.current_year, universe.current_week
                )
                for n in notes:
                    n['bidding_war_id'] = war.bidding_war_id
                    n['fa_name'] = war.fa_name
                all_notifications.extend(notes)

        urgent = [n for n in all_notifications if n.get('urgency') == 'high']

        return jsonify({
            'success': True,
            'total_notifications': len(all_notifications),
            'urgent_count': len(urgent),
            'notifications': all_notifications
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================ #
# STEP 131: Player Strategic Actions                                           #
# ============================================================================ #

@bidding_war_bp.route('/api/bidding-wars/<bidding_war_id>/act', methods=['POST'])
def api_player_bidding_action(bidding_war_id):
    """
    STEP 131: Submit a strategic action in a bidding war.

    Body:
    {
        "action": "match_offer" | "exceed_offer" | "sweeten_perks" |
                  "hold_firm" | "withdraw" | "request_meeting" | "exclusive_window",

        // For exceed_offer:
        "exceed_by": 1500,

        // For sweeten_perks:
        "perks": {
            "creative_control": "consultation",
            "title_guarantee": true,
            "signing_bonus": 20000
        },

        // For exclusive_window:
        "cost": 15000
    }
    """
    engine = get_bidding_engine()
    universe = get_universe()
    free_agent_pool = get_free_agent_pool()

    try:
        war = engine.load_war(bidding_war_id)
        if not war:
            return jsonify({'success': False, 'error': 'Bidding war not found'}), 404

        data = request.get_json()
        if not data or 'action' not in data:
            return jsonify({'success': False, 'error': 'action is required'}), 400

        from economy.bidding_war import PlayerBidAction
        try:
            action = PlayerBidAction(data['action'])
        except ValueError:
            return jsonify({
                'success': False,
                'error': f"Invalid action. Valid: {[a.value for a in PlayerBidAction]}"
            }), 400

        result = engine.apply_player_action(
            war=war,
            action=action,
            params=data,
            year=universe.current_year,
            week=universe.current_week
        )

        if not result['success']:
            return jsonify(result), 400

        # After player acts: roll for escalation events, then rivals counter
        fa = free_agent_pool.get_free_agent_by_id(war.fa_id)
        escalation_events = []
        new_rival_bids = []

        if fa and war.status.value not in ('decided', 'cancelled', 'final'):
            escalation_events = engine.roll_escalation_events(war, fa)
            new_rival_bids = engine.generate_rival_counter_bids(
                war, fa, universe.current_year, universe.current_week
            )

        notifications = engine.get_outbid_notifications(
            war, universe.current_year, universe.current_week
        )

        return jsonify({
            'success': True,
            'result': result,
            'bidding_war': engine.load_war(bidding_war_id).to_dict(),
            'escalation_events': [e.to_dict() for e in escalation_events],
            'new_rival_bids': [b.to_dict() for b in new_rival_bids],
            'notifications': notifications
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================ #
# STEP 132: Resolution                                                         #
# ============================================================================ #

@bidding_war_bp.route('/api/bidding-wars/<bidding_war_id>/resolve', methods=['POST'])
def api_resolve_bidding_war(bidding_war_id):
    """
    STEP 132: Resolve a bidding war — wrestler picks the winner.

    Should be called when war reaches 'final' status.
    Optional body: { "meeting_bonus": 8 }  (if player requested a meeting)
    """
    engine = get_bidding_engine()
    free_agent_pool = get_free_agent_pool()
    universe = get_universe()

    try:
        war = engine.load_war(bidding_war_id)
        if not war:
            return jsonify({'success': False, 'error': 'Bidding war not found'}), 404

        if war.status.value == 'decided':
            return jsonify({'success': False, 'error': 'Bidding war already resolved.'}), 400

        fa = free_agent_pool.get_free_agent_by_id(war.fa_id)
        if not fa:
            return jsonify({'success': False, 'error': 'Free agent no longer available.'}), 404

        data = request.get_json(silent=True) or {}
        meeting_bonus = data.get('meeting_bonus', 0)

        result = engine.resolve_bidding_war(
            war=war,
            free_agent=fa,
            year=universe.current_year,
            week=universe.current_week,
            player_meeting_bonus=meeting_bonus
        )

        return jsonify({
            'success': True,
            'resolution': result,
            'bidding_war': engine.load_war(bidding_war_id).to_dict(),
            'player_won': result['winner_is_player'],
            'message': (
                f"🎉 {fa.wrestler_name} chose your promotion!" if result['winner_is_player']
                else f"❌ {fa.wrestler_name} signed with {result['outcome_reason'].split('offered')[0].strip()}."
            )
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================ #
# STEP 133: Anti-Bidding War Tactics                                          #
# ============================================================================ #

@bidding_war_bp.route('/api/free-agents/<fa_id>/preemptive-signing')
def api_check_preemptive_signing(fa_id):
    """
    STEP 133: Check if a pre-emptive signing is available for a free agent
    before rivals become aware and trigger a bidding war.
    """
    free_agent_pool = get_free_agent_pool()
    engine = get_bidding_engine()
    universe = get_universe()

    try:
        fa = free_agent_pool.get_free_agent_by_id(fa_id)
        if not fa:
            return jsonify({'success': False, 'error': 'Free agent not found'}), 404

        result = engine.check_pre_emptive_signing_window(
            fa, universe.current_year, universe.current_week
        )
        return jsonify({'success': True, 'fa_id': fa_id, 'fa_name': fa.wrestler_name, **result})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bidding_war_bp.route('/api/roster/<wrestler_id>/loyalty-bonus-value')
def api_loyalty_bonus_value(wrestler_id):
    """
    STEP 133: Calculate how much you save by extending a current roster
    member now vs. letting them hit free agency and face a bidding war.
    """
    universe = get_universe()
    engine = get_bidding_engine()

    try:
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'success': False, 'error': 'Wrestler not found'}), 404

        result = engine.calculate_loyalty_bonus_value(wrestler)
        return jsonify({'success': True, **result})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bidding_war_bp.route('/api/roster/anti-bidding-war-report')
def api_anti_bidding_war_report():
    """
    STEP 133: Report of all rostered wrestlers at risk of triggering bidding
    wars (contracts expiring within 12 weeks), with loyalty bonus calculations.
    """
    universe = get_universe()
    engine = get_bidding_engine()

    try:
        at_risk = [
            w for w in universe.get_active_wrestlers()
            if w.contract.weeks_remaining <= 12
        ]

        report = []
        for wrestler in sorted(at_risk, key=lambda w: w.contract.weeks_remaining):
            value_data = engine.calculate_loyalty_bonus_value(wrestler)
            report.append({
                'wrestler_id':         wrestler.id,
                'wrestler_name':       wrestler.name,
                'brand':               wrestler.primary_brand,
                'role':                wrestler.role,
                'weeks_remaining':     wrestler.contract.weeks_remaining,
                'morale':              wrestler.morale,
                'current_salary':      wrestler.contract.salary_per_show,
                'extension_salary':    value_data['extension_salary'],
                'annual_savings':      value_data['annual_savings'],
                'mood_label':          value_data['mood_label'],
                'recommendation':      value_data['recommendation'],
            })

        return jsonify({
            'success': True,
            'at_risk_count': len(report),
            'wrestlers': report
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500