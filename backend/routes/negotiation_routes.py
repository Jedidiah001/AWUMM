"""
Negotiation Routes - Steps 134-160
All API endpoints for the full negotiation mini-game.

Endpoints:
  POST /api/negotiation/start                      - Step 134: Open session
  GET  /api/negotiation/<session_id>               - Get session state
  POST /api/negotiation/<session_id>/offer         - Step 135/136: Submit offer
  POST /api/negotiation/<session_id>/counter-accept - Accept the counter
  POST /api/negotiation/<session_id>/pause         - Step 139: Walk away
  POST /api/negotiation/<session_id>/resume        - Step 139: Return
  POST /api/negotiation/<session_id>/third-party   - Step 141: Call in ally
  GET  /api/negotiation/<session_id>/probability   - Step 137: Live probability
  GET  /api/negotiation/<session_id>/tells         - Step 138: Reading the room
  GET  /api/negotiation/templates/offer            - Build blank offer template
  GET  /api/negotiation/active                     - All active sessions
  DELETE /api/negotiation/<session_id>             - Close session
"""

from flask import Blueprint, jsonify, request, current_app
from economy.negotiation import (
    negotiation_engine,
    NegotiationOffer,
    NegotiationStatus,
    SalaryStructure,
    CreativeControlLevel,
    CreativeClauses,
    LifestyleClauses,
    MerchandiseDeal,
    DownsideGuarantee,
    PPVBonusTier,
    IncentiveClause,
)
from services.free_agent_signing_service import finalize_free_agent_signing

negotiation_bp = Blueprint('negotiation', __name__)


def get_database():
    return current_app.config['DATABASE']


def get_universe():
    return current_app.config['UNIVERSE']


def get_free_agent_pool():
    return current_app.config.get('FREE_AGENT_POOL')


# ─────────────────────────────────────────────
# HELPER: Build NegotiationOffer from request JSON
# ─────────────────────────────────────────────

def _build_offer_from_json(data: dict, from_promotion: bool = True) -> NegotiationOffer:
    offer = NegotiationOffer(from_promotion=from_promotion)

    # Monetary
    offer.salary_per_show = int(data.get('salary_per_show', 0))
    offer.contract_weeks  = int(data.get('contract_weeks', 52))
    offer.signing_bonus   = int(data.get('signing_bonus', 0))

    # Salary structure (Step 142)
    struct = data.get('salary_structure', 'weekly')
    try:
        offer.salary_structure = SalaryStructure(struct)
    except ValueError:
        offer.salary_structure = SalaryStructure.WEEKLY

    # Merch split (Step 145)
    merch = data.get('merch_deal', {})
    offer.merch_deal = MerchandiseDeal(
        promotion_pct=int(merch.get('promotion_pct', 70)),
        wrestler_pct=int(merch.get('wrestler_pct', 30))
    )

    # Downside guarantee (Step 146)
    dg = data.get('downside_guarantee', {})
    offer.downside_guarantee = DownsideGuarantee(
        weekly_guarantee=int(dg.get('weekly_guarantee', 0)),
        is_active=bool(dg.get('is_active', False))
    )

    # PPV bonuses (Step 147)
    ppv = data.get('ppv_bonuses', {})
    offer.ppv_bonuses = PPVBonusTier(
        base_appearance_bonus=int(ppv.get('base_appearance_bonus', 0)),
        main_event_bonus=int(ppv.get('main_event_bonus', 0)),
        championship_match_bonus=int(ppv.get('championship_match_bonus', 0)),
        headliner_bonus=int(ppv.get('headliner_bonus', 0)),
        guaranteed_ppv_minimum=int(ppv.get('guaranteed_ppv_minimum', 0)),
    )

    # Incentives (Step 148)
    inc = data.get('incentives', {})
    offer.incentives = IncentiveClause(
        match_quality_bonus=int(inc.get('match_quality_bonus', 0)),
        match_quality_threshold=float(inc.get('match_quality_threshold', 3.5)),
        merch_sales_bonus=int(inc.get('merch_sales_bonus', 0)),
        attendance_bonus=int(inc.get('attendance_bonus', 0)),
        championship_bonus=int(inc.get('championship_bonus', 0)),
        loyalty_bonus=int(inc.get('loyalty_bonus', 0)),
    )

    # Creative clauses (Steps 149-155)
    cc = data.get('creative_clauses', {})
    try:
        cc_level = CreativeControlLevel(cc.get('creative_control', 'none'))
    except ValueError:
        cc_level = CreativeControlLevel.NONE

    offer.creative_clauses = CreativeClauses(
        creative_control=cc_level,
        no_job_clauses=cc.get('no_job_clauses', []),
        title_guarantee=cc.get('title_guarantee', ''),
        brand_preference=cc.get('brand_preference', ''),
        storyline_veto_rights=bool(cc.get('storyline_veto_rights', False)),
        finish_protection=bool(cc.get('finish_protection', False)),
        promo_style=cc.get('promo_style', 'none'),
        promo_time_minimum=int(cc.get('promo_time_minimum', 0)),
    )

    # Lifestyle clauses (Steps 156-160)
    lc = data.get('lifestyle_clauses', {})
    offer.lifestyle_clauses = LifestyleClauses(
        max_appearances_per_year=int(lc.get('max_appearances_per_year', 0)),
        first_class_travel=bool(lc.get('first_class_travel', False)),
        private_car_service=bool(lc.get('private_car_service', False)),
        minimum_hotel_tier=lc.get('minimum_hotel_tier', 'standard'),
        outside_projects_allowed=bool(lc.get('outside_projects_allowed', True)),
        outside_projects_approval_required=bool(lc.get('outside_projects_approval_required', False)),
        family_time_off=bool(lc.get('family_time_off', False)),
        hometown_show_preference=bool(lc.get('hometown_show_preference', False)),
        injury_pay_protection=bool(lc.get('injury_pay_protection', False)),
        injury_job_security=bool(lc.get('injury_job_security', False)),
    )

    offer.notes = data.get('notes', '')
    return offer


# ─────────────────────────────────────────────
# STEP 134: Start negotiation session
# ─────────────────────────────────────────────

@negotiation_bp.route('/api/negotiation/start', methods=['POST'])
def api_start_negotiation():
    """
    Step 134 – Open a negotiation session for a free agent.
    Reveals tells, checks for rival deadlines, sets up flexibility points.

    Body: { "fa_id": "fa_001" }
    """
    try:
        data             = request.get_json()
        fa_id            = data.get('fa_id')
        free_agent_pool  = get_free_agent_pool()
        database         = get_database()

        if not fa_id:
            return jsonify({'error': 'fa_id is required'}), 400

        fa = free_agent_pool.get_free_agent_by_id(fa_id) if free_agent_pool else None
        if not fa:
            return jsonify({'error': 'Free agent not found'}), 404

        state        = database.get_game_state()
        current_year = state.get('current_year', 1)
        current_week = state.get('current_week', 1)

        session = negotiation_engine.start_negotiation(fa, current_year, current_week)

        return jsonify({
            'success': True,
            'session': session.to_dict(),
            'deadline_warning': (
                f"⚠️ {session.deadline.rival_offer_rival} has made an offer expiring Week {session.deadline.deadline_week}!"
                if session.deadline.has_deadline else None
            ),
            'opening_guidance': _opening_guidance(session),
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# GET: Session state
# ─────────────────────────────────────────────

@negotiation_bp.route('/api/negotiation/<session_id>', methods=['GET'])
def api_get_negotiation(session_id):
    """Get the current state of a negotiation session."""
    session = negotiation_engine.get_session(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    return jsonify({'success': True, 'session': session.to_dict()})


# ─────────────────────────────────────────────
# STEP 135/136: Submit an offer
# ─────────────────────────────────────────────

@negotiation_bp.route('/api/negotiation/<session_id>/offer', methods=['POST'])
def api_submit_offer(session_id):
    """
    Steps 135 & 136 – Submit your offer for this round.
    Returns: accepted | countered | rejected | expired
    """
    try:
        session = negotiation_engine.get_session(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404

        data  = request.get_json()
        offer = _build_offer_from_json(data)

        result = negotiation_engine.submit_offer(session, offer)

        # If accepted – sign the wrestler
        if result.get('outcome') == 'accepted':
            sign_result = _sign_free_agent(session, offer)
            result['signing_result'] = sign_result

        return jsonify(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# Accept the counter-offer as-is
# ─────────────────────────────────────────────

@negotiation_bp.route('/api/negotiation/<session_id>/counter-accept', methods=['POST'])
def api_accept_counter(session_id):
    """
    Accept the wrestler's latest counter-offer without modification.
    Convenience endpoint for when you're happy with their counter.
    """
    try:
        session = negotiation_engine.get_session(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404

        counter = session.latest_offer()
        if not counter or counter.from_promotion:
            return jsonify({'error': 'No counter-offer to accept'}), 400

        # Force the session to accepted
        session.status = NegotiationStatus.ACCEPTED
        sign_result = _sign_free_agent(session, counter)

        return jsonify({
            'success': True,
            'outcome': 'accepted',
            'message': f"✅ You accepted {session.wrestler_name}'s counter-offer.",
            'signing_result': sign_result,
            'session': session.to_dict(),
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# STEP 139: Walk away / Resume
# ─────────────────────────────────────────────

@negotiation_bp.route('/api/negotiation/<session_id>/pause', methods=['POST'])
def api_pause_negotiation(session_id):
    """Step 139 – Walk away from the negotiation temporarily."""
    try:
        session  = negotiation_engine.get_session(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404

        database = get_database()
        state    = database.get_game_state()

        result = negotiation_engine.pause_negotiation(session, state.get('current_week', 1))
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@negotiation_bp.route('/api/negotiation/<session_id>/resume', methods=['POST'])
def api_resume_negotiation(session_id):
    """Step 139 – Return to a paused negotiation."""
    try:
        session  = negotiation_engine.get_session(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404

        database = get_database()
        state    = database.get_game_state()

        result = negotiation_engine.resume_negotiation(session, state.get('current_week', 1))
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# STEP 141: Third-party intervention
# ─────────────────────────────────────────────

@negotiation_bp.route('/api/negotiation/<session_id>/third-party', methods=['POST'])
def api_third_party_intervention(session_id):
    """
    Step 141 – Bring in a trusted ally to boost negotiation probability.
    Body: { "ally_id": "w001", "ally_type": "roster_friend" }
    """
    try:
        session  = negotiation_engine.get_session(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404

        data      = request.get_json()
        ally_id   = data.get('ally_id', '')
        ally_type = data.get('ally_type', 'roster_friend')

        universe  = get_universe()
        ally      = universe.get_wrestler_by_id(ally_id)
        ally_name = ally.name if ally else data.get('ally_name', 'Unknown Ally')

        result = negotiation_engine.apply_third_party_intervention(session, ally_name, ally_type)
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# STEP 137: Live probability check
# ─────────────────────────────────────────────

@negotiation_bp.route('/api/negotiation/<session_id>/probability', methods=['POST'])
def api_check_probability(session_id):
    """
    Step 137 – Calculate acceptance probability for a hypothetical offer
    WITHOUT advancing the session state. Used for live UI updates.
    """
    try:
        session = negotiation_engine.get_session(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404

        data  = request.get_json()
        offer = _build_offer_from_json(data)

        prob_data = negotiation_engine.calculate_acceptance_probability(session, offer)

        return jsonify({
            'success': True,
            'session_id': session_id,
            'wrestler_name': session.wrestler_name,
            'probability_breakdown': prob_data,
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# STEP 138: Get tells
# ─────────────────────────────────────────────

@negotiation_bp.route('/api/negotiation/<session_id>/tells', methods=['GET'])
def api_get_tells(session_id):
    """
    Step 138 – Return the negotiation tells for this session.
    These hint at what the wrestler really prioritises.
    """
    session = negotiation_engine.get_session(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404

    return jsonify({
        'success': True,
        'wrestler_name': session.wrestler_name,
        'tells': session.tells,
        'primary_focus': session.priority_focus.value,
        'flexibility': {
            'points_remaining': session.flexibility.points_remaining,
            'total_points': session.flexibility.total_points,
            'stubbornness_pct': session.flexibility.stubbornness_pct,
        }
    })


# ─────────────────────────────────────────────
# Offer template builder
# ─────────────────────────────────────────────

@negotiation_bp.route('/api/negotiation/templates/offer', methods=['GET'])
def api_offer_template():
    """
    Return a blank offer template with all available fields and their defaults.
    Useful for the frontend form to know what fields exist.
    """
    template = NegotiationOffer()
    return jsonify({
        'success': True,
        'template': template.to_dict(),
        'field_info': {
            'salary_structure': [s.value for s in SalaryStructure],
            'creative_control': [c.value for c in CreativeControlLevel],
            'promo_styles': ['none', 'scripted', 'bullets', 'improv'],
            'hotel_tiers': ['standard', '4-star', '5-star'],
        }
    })


# ─────────────────────────────────────────────
# All active sessions
# ─────────────────────────────────────────────

@negotiation_bp.route('/api/negotiation/active', methods=['GET'])
def api_active_sessions():
    """List all currently open negotiation sessions."""
    sessions = negotiation_engine.get_all_active_sessions()
    return jsonify({
        'success': True,
        'total': len(sessions),
        'sessions': [s.to_dict() for s in sessions]
    })


# ─────────────────────────────────────────────
# Close session
# ─────────────────────────────────────────────

@negotiation_bp.route('/api/negotiation/<session_id>', methods=['DELETE'])
def api_close_negotiation(session_id):
    """Close and remove a negotiation session."""
    negotiation_engine.close_session(session_id)
    return jsonify({'success': True, 'message': 'Session closed.'})


# ─────────────────────────────────────────────
# PRIVATE: Sign a free agent after acceptance
# ─────────────────────────────────────────────

def _sign_free_agent(session, offer: NegotiationOffer) -> dict:
    """
    Convert an accepted negotiation offer into an actual roster signing.
    Deducts signing bonus from balance, adds wrestler to universe.
    """
    result = finalize_free_agent_signing(
        free_agent_pool=get_free_agent_pool(),
        universe=get_universe(),
        database=get_database(),
        free_agent_id=session.fa_id,
        offer=offer,
    )

    if result.get('success'):
        negotiation_engine.close_session(session.session_id)

    return result


def _opening_guidance(session) -> str:
    """Step 135 – Advise the player on opening offer strategy."""
    asking = session.asking_price
    fair   = int(asking * 0.95)
    low    = int(asking * 0.8)

    return (
        f"💡 {session.wrestler_name} is asking ${asking:,}/show. "
        f"A fair opener is around ${fair:,}. "
        f"Going below ${low:,} risks insulting them."
    )
