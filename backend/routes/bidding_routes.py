"""
Bidding War Routes
STEP 126: Rival Promotion Interest Generation
STEP 127: Bidding Round Structure
STEP 128: Blind vs Open Bidding
STEP 129: Bidding Escalation Events
STEP 130: Outbid Notifications
STEP 131: Strategic Bidding Decisions
STEP 132: Post-Bidding Relationship Effects
"""

from flask import Blueprint, jsonify, request, current_app
import traceback

bidding_bp = Blueprint('bidding', __name__)


def get_database():
    return current_app.config['DATABASE']


def get_universe():
    return current_app.config['UNIVERSE']


def get_free_agent_pool():
    return current_app.config.get('FREE_AGENT_POOL')


def get_rival_engine():
    from economy.rival_interest import rival_interest_engine
    return rival_interest_engine


# ============================================================
# STEP 126: Rival Promotion Info
# ============================================================

@bidding_bp.route('/api/rivals')
def api_get_rival_promotions():
    """Get all rival promotions and their current status"""
    try:
        engine = get_rival_engine()

        return jsonify({
            'success': True,
            'total': len(engine.rival_promotions),
            'rivals': [p.to_dict() for p in engine.rival_promotions]
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bidding_bp.route('/api/rivals/<promotion_id>')
def api_get_rival_promotion(promotion_id):
    """Get a specific rival promotion"""
    try:
        engine = get_rival_engine()
        promotion = engine.get_promotion_by_id(promotion_id)

        if not promotion:
            return jsonify({'success': False, 'error': 'Rival promotion not found'}), 404

        return jsonify({'success': True, 'rival': promotion.to_dict()})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bidding_bp.route('/api/rivals/<promotion_id>/relationship', methods=['POST'])
def api_update_rival_relationship(promotion_id):
    """Update relationship standing with a rival promotion"""
    try:
        engine = get_rival_engine()
        database = get_database()
        promotion = engine.get_promotion_by_id(promotion_id)

        if not promotion:
            return jsonify({'success': False, 'error': 'Rival promotion not found'}), 404

        data = request.get_json()
        change = data.get('change', 0)
        reason = data.get('reason', '')

        old_rel = promotion.relationship_with_player
        promotion.relationship_with_player = max(0, min(100, old_rel + change))

        engine.save_to_db(database)

        return jsonify({
            'success': True,
            'promotion_id': promotion_id,
            'old_relationship': old_rel,
            'new_relationship': promotion.relationship_with_player,
            'reason': reason
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# STEP 126: Interest Generation
# ============================================================

@bidding_bp.route('/api/rivals/generate-interest/<fa_id>', methods=['POST'])
def api_generate_rival_interest(fa_id):
    """
    STEP 126: Generate rival promotion interest for a specific free agent.

    Call this when a desirable free agent becomes available.
    """
    try:
        universe = get_universe()
        database = get_database()
        free_agent_pool = get_free_agent_pool()
        engine = get_rival_engine()

        fa = free_agent_pool.get_free_agent_by_id(fa_id)
        if not fa:
            return jsonify({'success': False, 'error': 'Free agent not found'}), 404

        interested = engine.generate_interest_for_free_agent(
            free_agent=fa,
            current_year=universe.current_year,
            current_week=universe.current_week,
            db=database
        )

        # Recalculate market value now that interest exists
        fa.recalculate_market_value(
            year=universe.current_year,
            week=universe.current_week,
            use_calculator=True
        )
        free_agent_pool.save_free_agent(fa)

        return jsonify({
            'success': True,
            'free_agent': fa.wrestler_name,
            'interested_count': len(interested),
            'interested_promotions': interested,
            'new_market_value': fa.market_value,
            'bidding_war_likely': len(interested) >= 2
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bidding_bp.route('/api/rivals/interest-summary/<fa_id>')
def api_get_interest_summary(fa_id):
    """Get rival interest summary for a free agent"""
    try:
        database = get_database()
        free_agent_pool = get_free_agent_pool()
        engine = get_rival_engine()

        fa = free_agent_pool.get_free_agent_by_id(fa_id)
        if not fa:
            return jsonify({'success': False, 'error': 'Free agent not found'}), 404

        summary = engine.get_interest_summary_for_free_agent(fa, db=database)

        return jsonify({'success': True, 'summary': summary})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# STEP 127: Bidding Round Structure
# ============================================================

@bidding_bp.route('/api/bidding/initiate/<fa_id>', methods=['POST'])
def api_initiate_bidding_war(fa_id):
    """
    STEP 127: Initiate a structured bidding war for a free agent.

    Body:
    - initial_offer: int (optional) - player's opening offer
    """
    try:
        universe = get_universe()
        free_agent_pool = get_free_agent_pool()
        engine = get_rival_engine()

        fa = free_agent_pool.get_free_agent_by_id(fa_id)
        if not fa:
            return jsonify({'success': False, 'error': 'Free agent not found'}), 404

        data = request.get_json() or {}
        initial_offer = data.get('initial_offer')

        # Check if bidding war already active
        if fa_id in engine.active_bidding_wars:
            war = engine.active_bidding_wars[fa_id]
            return jsonify({
                'success': True,
                'message': 'Bidding war already active',
                'war': war.to_dict()
            })

        # Generate rival interest first if none exists
        if not fa.rival_interest:
            engine.generate_interest_for_free_agent(
                free_agent=fa,
                current_year=universe.current_year,
                current_week=universe.current_week
            )

        war = engine.initiate_bidding_war(
            free_agent=fa,
            current_year=universe.current_year,
            current_week=universe.current_week,
            player_initial_offer=initial_offer
        )

        return jsonify({
            'success': True,
            'message': f'Bidding war initiated for {fa.wrestler_name}!',
            'is_open_bidding': war.is_open_bidding,
            'bidding_type': 'Open (Leaked to Media)' if war.is_open_bidding else 'Blind (Confidential)',
            'war': war.to_dict()
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bidding_bp.route('/api/bidding/advance/<fa_id>', methods=['POST'])
def api_advance_bidding_round(fa_id):
    """
    STEP 127: Advance to the next bidding round.

    Body:
    - player_offer: int - your offer for this round (null to hold or withdraw)
    """
    try:
        universe = get_universe()
        free_agent_pool = get_free_agent_pool()
        engine = get_rival_engine()

        fa = free_agent_pool.get_free_agent_by_id(fa_id)
        if not fa:
            return jsonify({'success': False, 'error': 'Free agent not found'}), 404

        data = request.get_json() or {}
        player_offer = data.get('player_offer')

        result = engine.advance_bidding_round(
            free_agent_id=fa_id,
            player_offer=player_offer,
            current_year=universe.current_year,
            current_week=universe.current_week
        )

        # Save updated free agent
        free_agent_pool.save_free_agent(fa)

        return jsonify({'success': True, **result})

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bidding_bp.route('/api/bidding/active')
def api_get_active_bidding_wars():
    """Get all currently active bidding wars"""
    try:
        engine = get_rival_engine()

        wars = [
            war.to_dict()
            for war in engine.active_bidding_wars.values()
        ]

        return jsonify({
            'success': True,
            'total': len(wars),
            'bidding_wars': wars
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bidding_bp.route('/api/bidding/status/<fa_id>')
def api_get_bidding_war_status(fa_id):
    """Get current bidding war status for a free agent"""
    try:
        engine = get_rival_engine()

        war = engine.active_bidding_wars.get(fa_id)
        if not war:
            return jsonify({
                'success': True,
                'active': False,
                'message': 'No active bidding war for this free agent'
            })

        return jsonify({
            'success': True,
            'active': True,
            'war': war.to_dict()
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# STEP 129: Escalation Events
# ============================================================

@bidding_bp.route('/api/bidding/escalation-events/<fa_id>')
def api_get_escalation_events(fa_id):
    """Get all escalation events for a bidding war"""
    try:
        engine = get_rival_engine()

        war = engine.active_bidding_wars.get(fa_id)
        if not war:
            return jsonify({
                'success': False,
                'error': 'No active bidding war'
            }), 404

        return jsonify({
            'success': True,
            'events': war.escalation_events,
            'total': len(war.escalation_events)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# STEP 130: Outbid Notifications
# ============================================================

@bidding_bp.route('/api/bidding/notifications')
def api_get_outbid_notifications():
    """
    STEP 130: Get all pending outbid notifications.
    """
    try:
        universe = get_universe()
        engine = get_rival_engine()

        notifications = engine.get_pending_outbid_notifications(
            current_year=universe.current_year,
            current_week=universe.current_week
        )

        return jsonify({
            'success': True,
            'total': len(notifications),
            'notifications': notifications
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bidding_bp.route('/api/bidding/notifications/dismiss/<fa_id>', methods=['POST'])
def api_dismiss_notification(fa_id):
    """Dismiss outbid notification for a free agent"""
    try:
        engine = get_rival_engine()
        success = engine.dismiss_outbid_notification(fa_id)

        return jsonify({
            'success': success,
            'message': 'Notification dismissed' if success else 'No notification found'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# STEP 131: Strategic Bidding Decisions
# ============================================================

@bidding_bp.route('/api/bidding/strategic-options/<fa_id>')
def api_get_strategic_options(fa_id):
    """
    STEP 131: Get available strategic options during a bidding war.
    """
    try:
        universe = get_universe()
        free_agent_pool = get_free_agent_pool()
        engine = get_rival_engine()

        fa = free_agent_pool.get_free_agent_by_id(fa_id)
        if not fa:
            return jsonify({'success': False, 'error': 'Free agent not found'}), 404

        data = request.args
        current_offer = data.get('current_offer', type=int)

        options = engine.get_strategic_options(
            free_agent=fa,
            current_player_offer=current_offer,
            current_year=universe.current_year,
            current_week=universe.current_week
        )

        return jsonify({'success': True, 'options': options})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bidding_bp.route('/api/bidding/strategic-action/<fa_id>', methods=['POST'])
def api_apply_strategic_action(fa_id):
    """
    STEP 131: Apply a strategic bidding decision.

    Body:
    - action: str (match_offer, exceed_offer, sweeten_non_monetary, hold_firm, withdraw, request_meeting)
    - player_offer: int (current or new offer amount)
    - non_monetary_perks: dict (optional for sweeten action)
    """
    try:
        universe = get_universe()
        free_agent_pool = get_free_agent_pool()
        engine = get_rival_engine()

        fa = free_agent_pool.get_free_agent_by_id(fa_id)
        if not fa:
            return jsonify({'success': False, 'error': 'Free agent not found'}), 404

        data = request.get_json() or {}
        action = data.get('action')
        player_offer = data.get('player_offer')
        non_monetary_perks = data.get('non_monetary_perks')

        if not action:
            return jsonify({'success': False, 'error': 'action is required'}), 400

        result = engine.apply_strategic_decision(
            free_agent=fa,
            action=action,
            player_offer=player_offer,
            non_monetary_perks=non_monetary_perks,
            current_year=universe.current_year,
            current_week=universe.current_week
        )

        free_agent_pool.save_free_agent(fa)

        return jsonify({'success': True, 'result': result})

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


# ============================================================
# STEP 132: Post-Bidding Information
# ============================================================

@bidding_bp.route('/api/bidding/completed')
def api_get_completed_bidding_wars():
    """Get recently completed bidding wars"""
    try:
        engine = get_rival_engine()
        limit = request.args.get('limit', 10, type=int)

        completed = engine.completed_bidding_wars[-limit:]
        completed.reverse()  # Most recent first

        return jsonify({
            'success': True,
            'total': len(engine.completed_bidding_wars),
            'showing': len(completed),
            'completed_wars': completed
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bidding_bp.route('/api/bidding/rival-stats')
def api_get_rival_stats():
    """Get win/loss stats for rival promotions in bidding wars"""
    try:
        engine = get_rival_engine()

        stats = []
        for promotion in engine.rival_promotions:
            total = promotion.won_bidding_wars + promotion.lost_bidding_wars
            win_rate = (promotion.won_bidding_wars / total * 100) if total > 0 else 0

            stats.append({
                'promotion_id': promotion.promotion_id,
                'name': promotion.name,
                'won_bidding_wars': promotion.won_bidding_wars,
                'lost_bidding_wars': promotion.lost_bidding_wars,
                'win_rate': round(win_rate, 1),
                'signed_this_year': promotion.signed_this_year,
                'relationship_with_player': promotion.relationship_with_player
            })

        stats.sort(key=lambda x: x['won_bidding_wars'], reverse=True)

        return jsonify({
            'success': True,
            'rival_stats': stats
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# STEP 133: Anti-Bidding War Tactics
# ============================================================

@bidding_bp.route('/api/bidding/anti-war/at-risk')
def api_get_at_risk_wrestlers():
    """
    STEP 133: Scan roster for wrestlers at risk of triggering bidding wars.

    Returns wrestlers sorted by risk score with primary concerns.
    """
    try:
        universe = get_universe()
        from economy.anti_bidding_tactics import anti_bidding_tactics

        wrestlers = universe.get_active_wrestlers()
        at_risk = anti_bidding_tactics.get_at_risk_wrestlers(wrestlers)

        return jsonify({
            'success': True,
            'total_at_risk': len(at_risk),
            'critical': sum(1 for w in at_risk if w['risk_level'] == 'CRITICAL'),
            'high': sum(1 for w in at_risk if w['risk_level'] == 'HIGH'),
            'medium': sum(1 for w in at_risk if w['risk_level'] == 'MEDIUM'),
            'at_risk_wrestlers': at_risk
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e),
                        'traceback': traceback.format_exc()}), 500


@bidding_bp.route('/api/bidding/anti-war/recommend/<wrestler_id>')
def api_recommend_anti_war_tactics(wrestler_id):
    """
    STEP 133: Get personalised anti-bidding war tactic recommendations for a wrestler.
    """
    try:
        universe = get_universe()
        from economy.anti_bidding_tactics import anti_bidding_tactics

        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'success': False, 'error': 'Wrestler not found'}), 404

        report = anti_bidding_tactics.recommend_tactics(wrestler)
        return jsonify({'success': True, 'report': report})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bidding_bp.route('/api/bidding/anti-war/preemptive/<wrestler_id>', methods=['POST'])
def api_preemptive_signing(wrestler_id):
    """
    STEP 133 — Tactic 1: Attempt a pre-emptive signing to avoid free agency.

    Body:
    - offered_salary: int  (weekly salary)
    - offered_weeks:  int  (contract length in weeks)
    """
    try:
        universe = get_universe()
        database = get_database()
        from economy.anti_bidding_tactics import anti_bidding_tactics

        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'success': False, 'error': 'Wrestler not found'}), 404

        data = request.get_json() or {}
        offered_salary = data.get('offered_salary')
        offered_weeks = data.get('offered_weeks')

        if not offered_salary or not offered_weeks:
            return jsonify({
                'success': False,
                'error': 'offered_salary and offered_weeks are required'
            }), 400

        balance = universe.balance if hasattr(universe, 'balance') else 1_000_000

        result = anti_bidding_tactics.attempt_preemptive_signing(
            wrestler=wrestler,
            offered_salary=int(offered_salary),
            offered_weeks=int(offered_weeks),
            promotion_balance=balance
        )

        # Apply contract extension if accepted
        if result.success and wrestler.contract:
            wrestler.contract.weeks_remaining = (
                getattr(wrestler.contract, 'weeks_remaining', 0) + result.weeks_added
            )
            wrestler.contract.salary_per_show = int(offered_salary)
            wrestler.morale = min(100, getattr(wrestler, 'morale', 50) + result.relationship_change)
            universe.save_wrestler(wrestler)

        return jsonify({'success': True, 'result': result.to_dict()})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e),
                        'traceback': traceback.format_exc()}), 500


@bidding_bp.route('/api/bidding/anti-war/long-term-lock/<wrestler_id>', methods=['POST'])
def api_long_term_lock(wrestler_id):
    """
    STEP 133 — Tactic 2: Offer a long-term contract lock.

    Body:
    - years:       int  (1–5)
    - lock_salary: int  (weekly salary for the locked deal)
    """
    try:
        universe = get_universe()
        database = get_database()
        from economy.anti_bidding_tactics import anti_bidding_tactics

        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'success': False, 'error': 'Wrestler not found'}), 404

        data = request.get_json() or {}
        years = data.get('years')
        lock_salary = data.get('lock_salary')

        if not years or not lock_salary:
            return jsonify({'success': False, 'error': 'years and lock_salary are required'}), 400

        balance = universe.balance if hasattr(universe, 'balance') else 1_000_000

        result = anti_bidding_tactics.offer_long_term_lock(
            wrestler=wrestler,
            years=int(years),
            lock_salary=int(lock_salary),
            promotion_balance=balance
        )

        if result.success and wrestler.contract:
            wrestler.contract.weeks_remaining = result.weeks_added
            wrestler.contract.salary_per_show = int(lock_salary)
            wrestler.morale = min(100, getattr(wrestler, 'morale', 50) + result.relationship_change)
            universe.save_wrestler(wrestler)

        return jsonify({'success': True, 'result': result.to_dict()})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e),
                        'traceback': traceback.format_exc()}), 500


@bidding_bp.route('/api/bidding/anti-war/loyalty-bonus/<wrestler_id>', methods=['POST'])
def api_loyalty_bonus(wrestler_id):
    """
    STEP 133 — Tactic 3: Award a loyalty bonus to deter free agency.

    Body:
    - bonus_tier: str ('small', 'medium', or 'large')
    """
    try:
        universe = get_universe()
        database = get_database()
        from economy.anti_bidding_tactics import anti_bidding_tactics

        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'success': False, 'error': 'Wrestler not found'}), 404

        data = request.get_json() or {}
        bonus_tier = data.get('bonus_tier', 'medium')

        balance = universe.balance if hasattr(universe, 'balance') else 1_000_000

        result = anti_bidding_tactics.award_loyalty_bonus(
            wrestler=wrestler,
            bonus_tier=bonus_tier,
            promotion_balance=balance
        )

        if result.success:
            # Deduct bonus from balance
            if hasattr(universe, 'balance'):
                universe.balance -= result.cost
            # Apply morale boost
            morale_boost = result.details.get('morale_boost', 0)
            wrestler.morale = min(100, getattr(wrestler, 'morale', 50) + morale_boost)
            universe.save_wrestler(wrestler)

        return jsonify({'success': True, 'result': result.to_dict()})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e),
                        'traceback': traceback.format_exc()}), 500


@bidding_bp.route('/api/bidding/anti-war/relationship/<wrestler_id>', methods=['POST'])
def api_relationship_investment(wrestler_id):
    """
    STEP 133 — Tactic 4: Invest in wrestler relationship to make money secondary.

    Body:
    - investment_type: str
      Options: personal_call, creative_meeting, public_praise,
               merchandise_push, mentorship_role, title_conversation, schedule_relief
    """
    try:
        universe = get_universe()
        from economy.anti_bidding_tactics import anti_bidding_tactics

        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'success': False, 'error': 'Wrestler not found'}), 404

        data = request.get_json() or {}
        investment_type = data.get('investment_type')

        if not investment_type:
            return jsonify({'success': False, 'error': 'investment_type is required'}), 400

        balance = universe.balance if hasattr(universe, 'balance') else 1_000_000

        result = anti_bidding_tactics.invest_in_relationship(
            wrestler=wrestler,
            investment_type=investment_type,
            promotion_balance=balance
        )

        if result.success:
            if result.cost > 0 and hasattr(universe, 'balance'):
                universe.balance -= result.cost
            morale_boost = result.details.get('morale_boost', 0)
            wrestler.morale = min(100, getattr(wrestler, 'morale', 50) + morale_boost)
            universe.save_wrestler(wrestler)

        return jsonify({'success': True, 'result': result.to_dict()})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e),
                        'traceback': traceback.format_exc()}), 500


@bidding_bp.route('/api/bidding/anti-war/investment-types')
def api_get_investment_types():
    """
    STEP 133: Return all available relationship investment types with costs and descriptions.
    """
    return jsonify({
        'success': True,
        'investment_types': [
            {'id': 'personal_call', 'label': '📞 Personal Call from Management',
             'cost': 0, 'rival_deterrence_pct': 15,
             'description': 'Direct conversation showing the wrestler matters to leadership.'},
            {'id': 'creative_meeting', 'label': '🎭 Collaborative Creative Meeting',
             'cost': 0, 'rival_deterrence_pct': 20,
             'description': 'Co-develop their storylines and character direction.'},
            {'id': 'public_praise', 'label': '📣 Public Management Praise',
             'cost': 0, 'rival_deterrence_pct': 12,
             'description': 'Validate their contributions publicly — interviews or on-air.'},
            {'id': 'merchandise_push', 'label': '👕 Priority Merchandise Push',
             'cost': 15000, 'rival_deterrence_pct': 35,
             'description': 'Priority merch production with a larger revenue share.'},
            {'id': 'mentorship_role', 'label': '🎓 Mentorship / Leadership Role',
             'cost': 0, 'rival_deterrence_pct': 28,
             'description': 'Give veterans coaching responsibility — purpose beyond matches.'},
            {'id': 'title_conversation', 'label': '🏆 Honest Title Picture Discussion',
             'cost': 0, 'rival_deterrence_pct': 30,
             'description': 'Candid title trajectory talk. Honesty builds more trust.'},
            {'id': 'schedule_relief', 'label': '🏖 Schedule Relief',
             'cost': 0, 'rival_deterrence_pct': 22,
             'description': 'Reduce road schedule — shows you value their wellbeing.'},
        ]
    })