"""
Controversy, Loyalty & Surprise Returns Routes — Steps 191-223

Register in routes/__init__.py:
    from routes.controversy_loyalty_routes import controversy_bp
    app.register_blueprint(controversy_bp)

Endpoints:
  --- STEP 191-197: Controversy Cases ---
  GET  /api/controversy/all                          - All controversy free agents with full case data
  GET  /api/controversy/<fa_id>/case                 - Full case assessment for one FA
  POST /api/controversy/<fa_id>/probationary-contract - Generate probationary contract terms
  POST /api/controversy/<fa_id>/rehab-plan           - Set up a rehabilitation plan
  POST /api/controversy/<fa_id>/rehab-plan/mentor    - Assign a mentor to the rehab plan
  POST /api/controversy/<fa_id>/activate-redemption  - Mark redemption arc as active
  POST /api/controversy/<fa_id>/issue-strike         - Issue a behaviour strike (probationary)

  --- STEPS 198-207: Surprise Returns / Secret Signings ---
  GET  /api/secret-signings/all                      - All active secret signings
  POST /api/secret-signings/create                   - Plan a secret signing
  GET  /api/secret-signings/<signing_id>             - Get one signing
  POST /api/secret-signings/<signing_id>/reveal      - Officially reveal / debut
  POST /api/secret-signings/<signing_id>/add-tease   - Add a tease video package
  GET  /api/debut/<wrestler_id>/momentum             - Get debut momentum window
  POST /api/debut/engineer                           - Score a debut plan
  POST /api/debut/execute                            - Execute a debut and record momentum

  --- STEPS 201-203: Forbidden Door ---
  GET  /api/forbidden-door/proposals                 - All FD proposals
  POST /api/forbidden-door/propose                   - Propose a cross-promotional scenario
  GET  /api/forbidden-door/<proposal_id>             - Get one proposal
  POST /api/forbidden-door/<proposal_id>/agree       - Agree to the proposal
  POST /api/forbidden-door/<proposal_id>/cancel      - Cancel the proposal
  GET  /api/forbidden-door/types                     - List door types + requirements

  --- STEPS 208-220: Loyalty ---
  GET  /api/loyalty/<wrestler_id>/score              - Calculate loyalty score
  GET  /api/loyalty/at-risk                          - All rostered wrestlers with low loyalty
  POST /api/loyalty/<wrestler_id>/loyalty-bonus      - Pay a loyalty bonus
  GET  /api/loyalty/<wrestler_id>/tenure-award       - Check tenure award eligibility
  POST /api/loyalty/<wrestler_id>/tenure-award/grant - Grant tenure award
  GET  /api/loyalty/exclusive-window/<wrestler_id>   - Check exclusive negotiating window

  --- STEPS 210-211: Holdouts ---
  GET  /api/holdouts/active                          - All active holdouts
  POST /api/holdouts/start                           - A wrestler enters a holdout
  GET  /api/holdouts/<wrestler_id>                   - Holdout status for one wrestler
  POST /api/holdouts/<wrestler_id>/resolve-deal      - Resolve holdout with a deal
  POST /api/holdouts/<wrestler_id>/resolve-release   - Resolve holdout with release

  --- STEPS 212-213: Tampering ---
  GET  /api/tampering/incidents                      - All detected tampering
  POST /api/tampering/report                         - Report a new tampering incident
  POST /api/tampering/<wrestler_id>/counter          - Apply a counter-measure

  --- STEPS 215-217: Failed Negotiations ---
  POST /api/failed-negotiations/consequences         - Get consequence for failed negotiation
  POST /api/failed-negotiations/goodwill-action      - Take a goodwill action to re-open window
  GET  /api/failed-negotiations/re-approach-windows  - All blocked re-approach windows

  --- STEP 221-223: Surprise Returns ---
  POST /api/surprise-returns/plan                    - Plan a surprise return
  POST /api/surprise-returns/<wrestler_id>/tease     - Add a tease video
  POST /api/surprise-returns/<wrestler_id>/execute   - Execute the return
  GET  /api/surprise-returns/<wrestler_id>/relationship - Historical relationship check
  GET  /api/surprise-returns/return-types            - List return types
"""

from flask import Blueprint, jsonify, request, current_app
import traceback
import random
import json
import uuid

from models.controversy_system import (
    ControversyCase, ControversyType,
    RehabilitationPlan, ProbationaryContract,
)
from models.loyalty_system import (
    calculate_loyalty_score, LoyaltyTier,
    HoldoutSituation, HoldoutStatus,
    TamperingIncident, TamperingIntensity,
    LoyaltyBonus,
    determine_failed_negotiation_consequence,
    generate_public_fallout_narrative,
    ReApproachWindow,
    ExclusiveNegotiatingWindow,
    MultiYearLoyaltyIncentive,
    HistoricalRelationship,
    SurpriseReturnPlan, SurpriseReturnType,
    calculate_loyalty_bidding_war_exception,
    FailedNegotiationConsequence,
)
from economy.surprise_returns import (
    surprise_returns_engine,
    SecretSigning, SecretLevel, SecretSigningStatus,
    DebutEngineering, DebutQuality, DebutMomentum,
    ForbiddenDoorProposal, ForbiddenDoorType,
    handle_premature_reveal,
)

controversy_bp = Blueprint("controversy", __name__)

# In-memory stores for holdouts, tampering, re-approach windows
# (persisted to SQLite in a full implementation; in-memory is fine for single-player)
_holdouts:         dict = {}    # wrestler_id -> HoldoutSituation
_tampering:        dict = {}    # wrestler_id -> List[TamperingIncident]
_reapproach:       dict = {}    # wrestler_id -> ReApproachWindow
_excl_windows:     dict = {}    # wrestler_id -> ExclusiveNegotiatingWindow
_surprise_plans:   dict = {}    # wrestler_id -> SurpriseReturnPlan
_controversy_cache: dict = {}   # fa_id -> ControversyCase (avoids rebuilding each call)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_database():
    return current_app.config["DATABASE"]


def get_universe():
    return current_app.config["UNIVERSE"]


def _get_debut_show_options():
    universe = get_universe()
    shows = getattr(universe.calendar, "generated_shows", []) or []
    options = []
    for show in shows:
        show_type = getattr(show, "show_type", "")
        if show_type not in {"weekly_tv", "minor_ppv", "major_ppv"} and not getattr(show, "is_ppv", False):
            continue
        options.append({
            "show_id": show.show_id,
            "show_name": show.name,
            "year": show.year,
            "week": show.week,
            "show_type": show_type,
            "is_ppv": bool(show.is_ppv),
            "brand": show.brand,
            "label": f"Y{show.year} W{show.week} · {show.name}",
        })
    options.sort(key=lambda s: (s["year"], s["week"], s["show_name"]))
    return options


def get_free_agent_pool():
    return current_app.config.get("FREE_AGENT_POOL")


def get_rival_manager():
    return current_app.config.get("RIVAL_PROMOTION_MANAGER")


def _get_fa_dict(fa_id: str) -> dict:
    pool = get_free_agent_pool()
    fa   = pool.get_free_agent_by_id(fa_id) if pool else None
    return fa.to_dict() if fa else {}


def _get_or_build_case(fa_id: str, fa_dict: dict) -> ControversyCase:
    """Return cached ControversyCase or build fresh from FA dict."""
    if fa_id not in _controversy_cache:
        _controversy_cache[fa_id] = ControversyCase.generate_for_free_agent(fa_dict)
    return _controversy_cache[fa_id]


def _get_roster_morale_avg() -> int:
    universe = get_universe()
    wrestlers = universe.get_active_wrestlers() if universe else []
    if not wrestlers:
        return 60
    morales = [getattr(w, "morale", 60) for w in wrestlers]
    return int(sum(morales) / len(morales))


# ═════════════════════════════════════════════════════════════════════════════
# STEPS 191-197: Controversy Case Routes
# ═════════════════════════════════════════════════════════════════════════════

@controversy_bp.route("/api/controversy/all")
def api_get_all_controversy():
    """Step 191: All free agents with controversies + full case assessments."""
    pool = get_free_agent_pool()
    try:
        controversy_fas = pool.get_controversy_cases() if pool else []
        morale_avg      = _get_roster_morale_avg()
        cases = []
        for fa in controversy_fas:
            fa_dict = fa.to_dict()
            case    = _get_or_build_case(fa.id, fa_dict)
            cases.append({
                "fa_id":          fa.id,
                "wrestler_name":  fa.wrestler_name,
                "role":           fa.role,
                "popularity":     fa.popularity,
                "age":            fa.age,
                "market_value":   getattr(fa, "market_value", 0),
                "mood":           fa.mood.value if hasattr(fa.mood, "value") else str(fa.mood),
                "controversy":    case.to_dict(),
            })
        return jsonify({
            "success": True,
            "total":   len(cases),
            "cases":   cases,
            "roster_morale_avg": morale_avg,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@controversy_bp.route("/api/controversy/<fa_id>/case")
def api_get_controversy_case(fa_id):
    """Step 191-195: Full case assessment for a single free agent."""
    try:
        fa_dict = _get_fa_dict(fa_id)
        if not fa_dict:
            return jsonify({"success": False, "error": "Free agent not found"}), 404
        if not fa_dict.get("has_controversy"):
            return jsonify({"success": False, "error": "This free agent has no controversy"}), 400

        morale_avg = _get_roster_morale_avg()
        # Rebuild fresh (updated severity may differ from cached)
        case = ControversyCase.generate_for_free_agent(fa_dict, morale_avg)
        _controversy_cache[fa_id] = case

        return jsonify({
            "success":        True,
            "fa_id":          fa_id,
            "wrestler_name":  fa_dict.get("wrestler_name"),
            "controversy":    case.to_dict(),
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@controversy_bp.route("/api/controversy/<fa_id>/probationary-contract", methods=["POST"])
def api_generate_probationary_contract(fa_id):
    """
    Step 196: Generate an appropriate probationary contract for a controversy case.
    POST: { "base_salary": 15000 }  (optional — uses market_value if not provided)
    """
    try:
        fa_dict = _get_fa_dict(fa_id)
        if not fa_dict:
            return jsonify({"success": False, "error": "Free agent not found"}), 404

        data        = request.get_json() or {}
        base_salary = data.get("base_salary") or fa_dict.get("market_value", 10000)
        severity    = int(fa_dict.get("controversy_severity", 40))

        contract = ProbationaryContract.generate_for_severity(severity, base_salary)

        # Cache this against the case
        case = _get_or_build_case(fa_id, fa_dict)
        case.probationary_contract = contract
        _controversy_cache[fa_id]  = case

        return jsonify({
            "success":             True,
            "fa_id":               fa_id,
            "wrestler_name":       fa_dict.get("wrestler_name"),
            "severity":            severity,
            "base_salary":         base_salary,
            "probationary_contract": contract.to_dict(),
            "vs_standard_contract": {
                "standard_salary": base_salary,
                "probationary_salary": contract.salary_per_show,
                "difference":     base_salary - contract.salary_per_show,
                "length_weeks":   contract.contract_length_weeks,
                "note": "Probationary contracts are shorter and include immediate-release clauses.",
            },
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@controversy_bp.route("/api/controversy/<fa_id>/rehab-plan", methods=["POST"])
def api_set_rehab_plan(fa_id):
    """
    Step 197: Set up a rehabilitation plan for a controversy case.
    POST: {
        counseling_access: bool,
        sobriety_support: bool,
        reduced_schedule: bool,
        weekly_check_in: bool,
    }
    """
    try:
        fa_dict = _get_fa_dict(fa_id)
        if not fa_dict:
            return jsonify({"success": False, "error": "Free agent not found"}), 404

        data = request.get_json() or {}
        plan = RehabilitationPlan(
            counseling_access             = bool(data.get("counseling_access", False)),
            sobriety_support              = bool(data.get("sobriety_support", False)),
            reduced_schedule              = bool(data.get("reduced_schedule", False)),
            weekly_check_in               = bool(data.get("weekly_check_in", False)),
            clear_expectations_documented = True,
        )

        case = _get_or_build_case(fa_id, fa_dict)
        case.rehabilitation_plan = plan
        _controversy_cache[fa_id] = case

        # Recalculate assessment with rehab in place
        talent   = int((fa_dict.get("brawling", 50) + fa_dict.get("technical", 50) + fa_dict.get("psychology", 50)) / 3)
        case.build_full_assessment(
            talent, fa_dict.get("popularity", 50),
            fa_dict.get("years_experience", 5),
            _get_roster_morale_avg(),
        )

        return jsonify({
            "success":            True,
            "fa_id":              fa_id,
            "wrestler_name":      fa_dict.get("wrestler_name"),
            "rehabilitation_plan": plan.to_dict(),
            "updated_assessment": case.assessment.to_dict() if case.assessment else None,
            "new_risk_score":     case.assessment.overall_risk_score() if case.assessment else None,
            "message": (
                f"Rehabilitation plan established. Plan quality: {plan.plan_quality()}/100. "
                f"Severity will reduce by {plan.severity_reduction_per_week():.1f} pts/week."
            ),
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@controversy_bp.route("/api/controversy/<fa_id>/rehab-plan/mentor", methods=["POST"])
def api_assign_rehab_mentor(fa_id):
    """
    Step 197: Assign a current roster member as mentor for a controversy case.
    POST: { wrestler_id: "w001" }
    """
    try:
        fa_dict  = _get_fa_dict(fa_id)
        if not fa_dict:
            return jsonify({"success": False, "error": "Free agent not found"}), 404

        data         = request.get_json() or {}
        wrestler_id  = data.get("wrestler_id")
        if not wrestler_id:
            return jsonify({"success": False, "error": "wrestler_id required"}), 400

        universe = get_universe()
        mentor   = universe.get_wrestler_by_id(wrestler_id)
        if not mentor:
            return jsonify({"success": False, "error": "Wrestler not found"}), 404

        case = _get_or_build_case(fa_id, fa_dict)
        if not case.rehabilitation_plan:
            case.rehabilitation_plan = RehabilitationPlan()

        case.rehabilitation_plan.mentor_assigned       = True
        case.rehabilitation_plan.mentor_wrestler_id    = wrestler_id
        case.rehabilitation_plan.mentor_wrestler_name  = mentor.name
        _controversy_cache[fa_id] = case

        return jsonify({
            "success":          True,
            "mentor_name":      mentor.name,
            "mentor_role":      mentor.role,
            "mentor_popularity": mentor.popularity,
            "plan_quality":     case.rehabilitation_plan.plan_quality(),
            "message": f"{mentor.name} assigned as mentor. Plan quality increased to {case.rehabilitation_plan.plan_quality()}/100.",
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@controversy_bp.route("/api/controversy/<fa_id>/activate-redemption", methods=["POST"])
def api_activate_redemption_arc(fa_id):
    """Step 193: Mark a controversy case as having an active redemption arc."""
    try:
        fa_dict = _get_fa_dict(fa_id)
        if not fa_dict:
            return jsonify({"success": False, "error": "Free agent not found"}), 404

        case = _get_or_build_case(fa_id, fa_dict)
        case.redemption_arc_active = True
        _controversy_cache[fa_id]  = case

        return jsonify({
            "success":             True,
            "fa_id":               fa_id,
            "wrestler_name":       fa_dict.get("wrestler_name"),
            "redemption_potential": case.redemption_potential.value,
            "booking_bonus":       case.redemption_potential.booking_bonus,
            "message": (
                f"Redemption arc activated for {fa_dict.get('wrestler_name')}. "
                f"Potential: {case.redemption_potential.label}. "
                f"+{case.redemption_potential.booking_bonus} booking bonus if arc is executed well."
            ),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@controversy_bp.route("/api/controversy/<fa_id>/issue-strike", methods=["POST"])
def api_issue_behaviour_strike(fa_id):
    """
    Step 196: Issue a behaviour strike against a wrestler on a probationary contract.
    POST: { "reason": "Missed scheduled appearance" }
    """
    try:
        fa_dict = _get_fa_dict(fa_id)
        if not fa_dict:
            return jsonify({"success": False, "error": "Free agent not found"}), 404

        case = _get_or_build_case(fa_id, fa_dict)
        if not case.probationary_contract:
            return jsonify({"success": False, "error": "No probationary contract on file — generate one first"}), 400

        data   = request.get_json() or {}
        reason = data.get("reason", "Unspecified behaviour issue")
        result = case.probationary_contract.issue_strike(reason)
        _controversy_cache[fa_id] = case

        return jsonify({
            "success":    True,
            "fa_id":      fa_id,
            "wrestler_name": fa_dict.get("wrestler_name"),
            "strike_result": result,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ═════════════════════════════════════════════════════════════════════════════
# STEPS 198-207: Secret Signings & Debut Engineering
# ═════════════════════════════════════════════════════════════════════════════

@controversy_bp.route("/api/secret-signings/all")
def api_get_all_secret_signings():
    """Step 198: All active and recent secret signings."""
    try:
        signings = surprise_returns_engine.get_all_signings()
        return jsonify({
            "success": True,
            "total":   len(signings),
            "signings": [s.to_dict() for s in signings],
            "summary":  surprise_returns_engine.summary(),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@controversy_bp.route("/api/secret-signings/debut-shows")
def api_get_secret_signing_debut_shows():
    """Return database-backed scheduled shows for debut planning."""
    try:
        return jsonify({"success": True, "shows": _get_debut_show_options()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@controversy_bp.route("/api/secret-signings/create", methods=["POST"])
def api_create_secret_signing():
    """
    Step 198: Plan a secret signing for a free agent.
    POST: {
        fa_id: str,
        secret_level: "tight"|"iron_clad"|"loose",
        salary_per_show: int,
        contract_weeks: int,
        signing_bonus: int,
        planned_show: str,
        planned_week: int,
        planned_year: int,
        planned_opponent_name: str (optional)
    }
    """
    try:
        data            = request.get_json() or {}
        fa_id           = data.get("fa_id")
        wrestler_name   = data.get("wrestler_name", "")
        secret_level    = data.get("secret_level", "tight")
        salary          = int(data.get("salary_per_show", 0))
        weeks           = int(data.get("contract_weeks", 52))
        bonus           = int(data.get("signing_bonus", 0))
        planned_show_id = data.get("planned_show_id", "")
        planned_show    = data.get("planned_show", "")
        planned_week    = int(data.get("planned_week", 1))
        planned_year    = int(data.get("planned_year", 1))
        opponent_name   = data.get("planned_opponent_name", "")

        if not fa_id:
            return jsonify({"success": False, "error": "fa_id required"}), 400

        # Resolve wrestler name from pool if not provided
        if not wrestler_name:
            fa_dict      = _get_fa_dict(fa_id)
            wrestler_name = fa_dict.get("wrestler_name", "Unknown")

        # Deduct signing bonus from balance
        if bonus > 0:
            universe = get_universe()
            if universe.balance < bonus:
                return jsonify({"success": False, "error": f"Insufficient funds for signing bonus (${bonus:,})"}), 400
            universe.balance -= bonus
            get_database().update_game_state(balance=universe.balance)

        show_options = _get_debut_show_options()
        selected_show = next((s for s in show_options if s["show_id"] == planned_show_id), None)
        if not selected_show and planned_show:
            selected_show = next((s for s in show_options if s["show_name"] == planned_show), None)
        if selected_show:
            planned_show_id = selected_show["show_id"]
            planned_show = selected_show["show_name"]
            planned_week = int(selected_show["week"])
            planned_year = int(selected_show["year"])

        signing = surprise_returns_engine.create_secret_signing(
            fa_id=fa_id, wrestler_name=wrestler_name,
            secret_level=secret_level, salary=salary, weeks=weeks, bonus=bonus,
            planned_show=planned_show, planned_week=planned_week, planned_year=planned_year,
            planned_opponent_name=opponent_name,
        )

        booked_match = False
        auto_book_message = ""
        if planned_show_id and opponent_name:
            roster = get_database().get_all_wrestlers(active_only=False)
            opponent = next((w for w in roster if w.get("name") == opponent_name), None)
            if opponent:
                db = get_database()
                show_draft = db.get_show_draft(planned_show_id) or {
                    "show_id": planned_show_id,
                    "show_name": planned_show or selected_show["show_name"],
                    "brand": selected_show["brand"] if selected_show else "Cross-Brand",
                    "show_type": selected_show["show_type"] if selected_show else "weekly_tv",
                    "is_ppv": bool(selected_show["is_ppv"]) if selected_show else False,
                    "year": planned_year,
                    "week": planned_week,
                    "matches": [],
                    "segments": [],
                }
                show_draft.setdefault("matches", []).append({
                    "match_id": f"secret_signing_{uuid.uuid4().hex[:10]}",
                    "side_a": {"wrestler_ids": [fa_id], "wrestler_names": [wrestler_name], "is_tag_team": False},
                    "side_b": {"wrestler_ids": [opponent["id"]], "wrestler_names": [opponent["name"]], "is_tag_team": False},
                    "match_type": "singles",
                    "is_title_match": False,
                    "title_id": None,
                    "title_name": None,
                    "card_position": len(show_draft.get("matches", [])),
                    "booking_bias": "even",
                    "importance": "normal",
                    "feud_id": None,
                    "stipulation": None,
                    "referee_id": None,
                    "special_match_type": None,
                    "booked_winner": None,
                    "booked_runner_up": None,
                    "booked_iron_man": None,
                    "booked_most_eliminations": None,
                })
                cursor = db.conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO show_drafts (show_id, show_data, production_plan, created_at)
                    VALUES (?, ?, COALESCE((SELECT production_plan FROM show_drafts WHERE show_id=?), NULL), datetime('now'))
                    """,
                    (planned_show_id, json.dumps(show_draft), planned_show_id),
                )
                db.conn.commit()
                booked_match = True
                auto_book_message = f" Match auto-booked vs {opponent['name']} on booking page."

        return jsonify({
            "success": True,
            "signing": signing.to_dict(),
            "booked_match": booked_match,
            "message": (
                f"Secret signing created for {wrestler_name}. "
                f"Security level: {signing.secret_level.label}. "
                f"Planned debut: {planned_show} (Week {planned_week}).{auto_book_message}"
            ),
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@controversy_bp.route("/api/secret-signings/<signing_id>")
def api_get_secret_signing(signing_id):
    """Step 198: Get a specific secret signing."""
    signing = surprise_returns_engine.get_signing(signing_id)
    if not signing:
        return jsonify({"success": False, "error": "Signing not found"}), 404
    return jsonify({"success": True, "signing": signing.to_dict()})


@controversy_bp.route("/api/secret-signings/<signing_id>/reveal", methods=["POST"])
def api_reveal_secret_signing(signing_id):
    """
    Step 199-200: Officially reveal a secret signing / debut the wrestler.
    POST: { show_name: str }
    """
    try:
        universe = get_universe()
        data     = request.get_json() or {}
        show     = data.get("show_name", "")
        if not show:
            return jsonify({"success": False, "error": "show_name required"}), 400

        result = surprise_returns_engine.reveal_signing(
            signing_id, show, universe.current_week, universe.current_year
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@controversy_bp.route("/api/secret-signings/<signing_id>/add-tease", methods=["POST"])
def api_add_tease_video(signing_id):
    """Step 199: Add a pre-debut tease video package."""
    signing = surprise_returns_engine.get_signing(signing_id)
    if not signing:
        return jsonify({"success": False, "error": "Signing not found"}), 404

    data     = request.get_json() or {}
    tease_result = signing.add_tease_video() if hasattr(signing, "add_tease_video") else None

    # Handle tease on signing (or SurpriseReturnPlan)
    plan_key = signing.fa_id
    if plan_key in _surprise_plans:
        tease_result = _surprise_plans[plan_key].add_tease_video()
    else:
        # Increment manually on the SecretSigning
        if not hasattr(signing, "_tease_count"):
            signing._tease_count = 0
        signing._tease_count = getattr(signing, "_tease_count", 0) + 1
        tease_result = {
            "tease_number":   signing._tease_count,
            "fan_excitement": min(100, 40 + signing._tease_count * 15),
            "message":        f"Tease video #{signing._tease_count} posted. Buzz building.",
        }

    return jsonify({"success": True, "signing_id": signing_id, **tease_result})


@controversy_bp.route("/api/debut/engineer", methods=["POST"])
def api_engineer_debut():
    """
    Step 199: Score a debut configuration before committing.
    POST: {
        wrestler_name: str,
        popularity: int,
        show_type: "weekly_tv"|"ppv"|"special_event"|"stadium",
        opponent_role: "curtain_jerker"|"midcard"|"upper_midcard"|"main_event",
        crowd_size: int,
        is_surprise: bool,
        has_vignette_buildup: bool,
        planned_result: "win"|"loss"|"draw"|"interrupted",
        mystery_partner: bool
    }
    """
    try:
        data = request.get_json() or {}
        config = DebutEngineering(
            wrestler_name        = data.get("wrestler_name", ""),
            show_type            = data.get("show_type", "weekly_tv"),
            opponent_role        = data.get("opponent_role", "midcard"),
            crowd_size           = int(data.get("crowd_size", 5000)),
            is_surprise          = bool(data.get("is_surprise", True)),
            has_vignette_buildup = bool(data.get("has_vignette_buildup", False)),
            planned_result       = data.get("planned_result", "win"),
            mystery_partner      = bool(data.get("mystery_partner", False)),
        )
        popularity = int(data.get("popularity", 50))
        return jsonify({
            "success": True,
            "debut_plan": config.to_dict(popularity),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@controversy_bp.route("/api/debut/execute", methods=["POST"])
def api_execute_debut():
    """
    Step 200: Execute a debut and record momentum.
    POST: {
        wrestler_id: str,
        wrestler_name: str,
        popularity: int,
        show_type, opponent_role, crowd_size, is_surprise,
        has_vignette_buildup, planned_result, mystery_partner
    }
    """
    try:
        data = request.get_json() or {}
        wrestler_id   = data.get("wrestler_id", "")
        wrestler_name = data.get("wrestler_name", "")
        popularity    = int(data.get("popularity", 50))

        config = DebutEngineering(
            wrestler_name        = wrestler_name,
            show_type            = data.get("show_type", "weekly_tv"),
            opponent_role        = data.get("opponent_role", "midcard"),
            crowd_size           = int(data.get("crowd_size", 5000)),
            is_surprise          = bool(data.get("is_surprise", True)),
            has_vignette_buildup = bool(data.get("has_vignette_buildup", False)),
            planned_result       = data.get("planned_result", "win"),
            mystery_partner      = bool(data.get("mystery_partner", False)),
        )

        dm = surprise_returns_engine.record_debut(wrestler_id, wrestler_name, config, popularity)

        return jsonify({
            "success":       True,
            "debut_result":  config.to_dict(popularity),
            "momentum":      dm.to_dict(),
            "message": (
                f"{wrestler_name} debuted! Quality: {dm.quality.label}. "
                f"Momentum window: {dm.weeks_remaining} weeks."
            ),
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@controversy_bp.route("/api/debut/<wrestler_id>/momentum")
def api_get_debut_momentum(wrestler_id):
    """Step 206-207: Get current debut momentum window for a wrestler."""
    dm = surprise_returns_engine.get_momentum(wrestler_id)
    if not dm:
        return jsonify({"success": True, "momentum": None, "message": "No active momentum window."})
    return jsonify({"success": True, "momentum": dm.to_dict()})


# ═════════════════════════════════════════════════════════════════════════════
# STEPS 201-203: Forbidden Door
# ═════════════════════════════════════════════════════════════════════════════

@controversy_bp.route("/api/forbidden-door/types")
def api_fd_types():
    """Step 201: List all forbidden door types with relationship requirements."""
    types = []
    for dt in ForbiddenDoorType:
        types.append({
            "value":                dt.value,
            "label":                dt.label,
            "relationship_required": dt.relationship_required,
            "base_cost":            dt.base_cost,
        })
    return jsonify({"success": True, "types": types})


@controversy_bp.route("/api/forbidden-door/proposals")
def api_get_fd_proposals():
    """Step 201-203: All forbidden door proposals."""
    proposals = surprise_returns_engine.get_all_fd_proposals()
    return jsonify({
        "success":   True,
        "total":     len(proposals),
        "proposals": [p.to_dict() for p in proposals],
    })


@controversy_bp.route("/api/forbidden-door/<proposal_id>")
def api_get_fd_proposal(proposal_id):
    proposal = surprise_returns_engine.get_fd_proposal(proposal_id)
    if not proposal:
        return jsonify({"success": False, "error": "Proposal not found"}), 404
    return jsonify({"success": True, "proposal": proposal.to_dict()})


@controversy_bp.route("/api/forbidden-door/propose", methods=["POST"])
def api_propose_forbidden_door():
    """
    Step 201-203: Propose a cross-promotional scenario.
    POST: {
        door_type: str,
        rival_promotion_id: str,
        our_wrestlers: [str],
        their_wrestlers: [str],
        our_payment: int,
        their_payment: int,
        event_name: str,
        event_week: int,
        event_year: int,
        revenue_split_pct: int (optional, default 50)
    }
    """
    try:
        data              = request.get_json() or {}
        rival_mgr         = get_rival_manager()
        rival_id          = data.get("rival_promotion_id", "")
        rival             = rival_mgr.get_promotion_by_id(rival_id) if rival_mgr else None
        rival_name        = rival.name if rival else data.get("rival_promotion_name", "Unknown Promotion")

        # Step 201: Check relationship is sufficient
        if rival:
            rel = rival.relationship_with_player
            door_type_str = data.get("door_type", "dream_match")
            try:
                dt = ForbiddenDoorType(door_type_str)
            except ValueError:
                dt = ForbiddenDoorType.DREAM_MATCH
            if rel < dt.relationship_required:
                return jsonify({
                    "success": False,
                    "error":   f"Relationship too low ({rel}/100). Need {dt.relationship_required} for {dt.label}.",
                    "current_relationship": rel,
                    "required_relationship": dt.relationship_required,
                }), 400

        proposal = surprise_returns_engine.create_fd_proposal(
            door_type            = data.get("door_type", "dream_match"),
            rival_promotion_id   = rival_id,
            rival_promotion_name = rival_name,
            our_wrestlers        = data.get("our_wrestlers", []),
            their_wrestlers      = data.get("their_wrestlers", []),
            our_payment          = int(data.get("our_payment", 0)),
            their_payment        = int(data.get("their_payment", 0)),
            event_name           = data.get("event_name", ""),
            event_week           = int(data.get("event_week", 1)),
            event_year           = int(data.get("event_year", 1)),
            revenue_split_pct    = int(data.get("revenue_split_pct", 50)),
        )

        return jsonify({
            "success":  True,
            "proposal": proposal.to_dict(),
            "message":  f"Forbidden Door proposal sent to {rival_name}.",
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@controversy_bp.route("/api/forbidden-door/<proposal_id>/agree", methods=["POST"])
def api_agree_fd_proposal(proposal_id):
    """Step 203: Agree to a cross-promotional scenario."""
    try:
        result = surprise_returns_engine.agree_fd_proposal(proposal_id)
        if not result["success"]:
            return jsonify(result), 404

        # Improve relationship with the rival
        proposal = surprise_returns_engine.get_fd_proposal(proposal_id)
        if proposal:
            rival_mgr = get_rival_manager()
            universe  = get_universe()
            if rival_mgr and proposal.rival_promotion_id:
                rival_mgr.adjust_relationship(
                    proposal.rival_promotion_id,
                    proposal.relationship_impact(),
                    f"Forbidden Door: {proposal.event_name}",
                    universe.current_year,
                    universe.current_week,
                )

        return jsonify({**result, "message": "Forbidden Door agreed. Relationship improved."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@controversy_bp.route("/api/forbidden-door/<proposal_id>/cancel", methods=["POST"])
def api_cancel_fd_proposal(proposal_id):
    """Step 203: Cancel a cross-promotional proposal."""
    try:
        result = surprise_returns_engine.cancel_fd_proposal(proposal_id)
        if not result["success"]:
            return jsonify(result), 404

        # Damage relationship
        proposal = surprise_returns_engine.get_fd_proposal(proposal_id)
        if proposal and proposal.rival_promotion_id:
            rival_mgr = get_rival_manager()
            universe  = get_universe()
            if rival_mgr:
                rival_mgr.adjust_relationship(
                    proposal.rival_promotion_id,
                    result.get("relationship_impact", -5),
                    f"Cancelled Forbidden Door: {proposal.event_name}",
                    universe.current_year,
                    universe.current_week,
                )

        return jsonify({**result, "message": "Proposal cancelled. Relationship with rival damaged."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ═════════════════════════════════════════════════════════════════════════════
# STEPS 208-220: Loyalty
# ═════════════════════════════════════════════════════════════════════════════

@controversy_bp.route("/api/loyalty/<wrestler_id>/score")
def api_get_loyalty_score(wrestler_id):
    """Step 208-209: Calculate loyalty score and tier for a rostered wrestler."""
    try:
        universe = get_universe()
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({"success": False, "error": "Wrestler not found"}), 404

        # Infer fields from wrestler object
        years_with  = getattr(wrestler.contract, "weeks_on_contract", 52) / 52 if hasattr(wrestler, "contract") else 1.0
        morale      = getattr(wrestler, "morale", 60)
        was_champ   = getattr(wrestler, "is_champion", False) or getattr(wrestler, "championship_reigns", 0) > 0
        above_market = getattr(wrestler.contract, "salary_per_show", 5000) > getattr(wrestler, "market_value", 5000) * 0.9 if hasattr(wrestler, "contract") else False

        score = calculate_loyalty_score(
            years_with_promotion     = years_with,
            morale                   = morale,
            was_champion             = was_champ,
            was_pushed_consistently  = morale >= 65,
            had_contract_dispute     = False,
            had_wellness_strike      = False,
            paid_above_market        = above_market,
        )
        tier = LoyaltyTier.from_score(score)
        exception = calculate_loyalty_bidding_war_exception(tier, years_with, was_champ)

        return jsonify({
            "success":        True,
            "wrestler_id":    wrestler_id,
            "wrestler_name":  wrestler.name,
            "loyalty_score":  score,
            "tier":           tier.value,
            "tier_label":     tier.label,
            "tier_description": tier.description,
            "renewal_discount":  tier.renewal_discount,
            "tampering_vulnerability": tier.tampering_vulnerability,
            "holdout_risk":    tier.holdout_risk,
            "bidding_war_exception": exception,     # Step 222
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@controversy_bp.route("/api/loyalty/at-risk")
def api_loyalty_at_risk():
    """Step 208-209: All rostered wrestlers with concerning loyalty levels."""
    try:
        universe = get_universe()
        wrestlers = universe.get_active_wrestlers()
        at_risk   = []

        for w in wrestlers:
            morale = getattr(w, "morale", 60)
            years  = getattr(getattr(w, "contract", None), "weeks_on_contract", 52) / 52
            was_champ = getattr(w, "championship_reigns", 0) > 0

            score = calculate_loyalty_score(
                years_with_promotion    = years,
                morale                  = morale,
                was_champion            = was_champ,
                was_pushed_consistently = morale >= 65,
                had_contract_dispute    = False,
                had_wellness_strike     = False,
                paid_above_market       = False,
            )
            tier = LoyaltyTier.from_score(score)

            if tier in (LoyaltyTier.DISGRUNTLED, LoyaltyTier.INDIFFERENT):
                at_risk.append({
                    "wrestler_id":   w.id,
                    "wrestler_name": w.name,
                    "brand":         getattr(w, "primary_brand", ""),
                    "role":          w.role,
                    "morale":        morale,
                    "loyalty_score": score,
                    "tier":          tier.value,
                    "tier_label":    tier.label,
                    "holdout_risk":  tier.holdout_risk,
                    "tampering_vulnerability": tier.tampering_vulnerability,
                    "weeks_remaining": getattr(getattr(w, "contract", None), "weeks_remaining", "?"),
                })

        at_risk.sort(key=lambda x: x["loyalty_score"])
        return jsonify({"success": True, "total_at_risk": len(at_risk), "wrestlers": at_risk})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@controversy_bp.route("/api/loyalty/<wrestler_id>/loyalty-bonus", methods=["POST"])
def api_pay_loyalty_bonus(wrestler_id):
    """
    Step 214: Pay a loyalty bonus to a roster member.
    POST: { bonus_type: "monetary"|"creative"|"title_push", amount: 10000 }
    """
    try:
        universe = get_universe()
        database = get_database()
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({"success": False, "error": "Wrestler not found"}), 404

        data       = request.get_json() or {}
        bonus_type = data.get("bonus_type", "monetary")
        amount     = int(data.get("amount", 0))

        if bonus_type == "monetary" and amount > 0:
            if universe.balance < amount:
                return jsonify({"success": False, "error": f"Insufficient funds (${amount:,})"}), 400
            universe.balance -= amount
            database.update_game_state(balance=universe.balance)

        morale_gain  = {"monetary": 8, "creative": 12, "title_push": 15}.get(bonus_type, 5)
        loyalty_gain = {"monetary": 5, "creative": 8, "title_push": 10}.get(bonus_type, 3)

        bonus = LoyaltyBonus(
            wrestler_id   = wrestler_id,
            wrestler_name = wrestler.name,
            bonus_type    = bonus_type,
            amount        = amount,
            loyalty_gain  = loyalty_gain,
            morale_gain   = morale_gain,
            description   = f"{bonus_type.title()} loyalty bonus awarded to {wrestler.name}.",
        )

        return jsonify({
            "success":      True,
            "bonus":        bonus.to_dict(),
            "message": (
                f"Loyalty bonus paid to {wrestler.name}. "
                f"+{morale_gain} morale, +{loyalty_gain} loyalty."
            ),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@controversy_bp.route("/api/loyalty/<wrestler_id>/tenure-award")
def api_check_tenure_award(wrestler_id):
    """Step 214: Check if this wrestler is eligible for a tenure milestone award."""
    try:
        universe = get_universe()
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({"success": False, "error": "Wrestler not found"}), 404

        years = getattr(getattr(wrestler, "contract", None), "weeks_on_contract", 52) / 52
        award = LoyaltyBonus.generate_tenure_award(wrestler_id, wrestler.name, years)

        return jsonify({
            "success":              True,
            "wrestler_name":        wrestler.name,
            "years_with_promotion": round(years, 1),
            "eligible_award":       award.to_dict(),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@controversy_bp.route("/api/loyalty/<wrestler_id>/tenure-award/grant", methods=["POST"])
def api_grant_tenure_award(wrestler_id):
    """Step 214: Grant the tenure award and deduct cost."""
    try:
        universe = get_universe()
        database = get_database()
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({"success": False, "error": "Wrestler not found"}), 404

        years = getattr(getattr(wrestler, "contract", None), "weeks_on_contract", 52) / 52
        award = LoyaltyBonus.generate_tenure_award(wrestler_id, wrestler.name, years)

        if award.amount > 0:
            if universe.balance < award.amount:
                return jsonify({"success": False, "error": f"Insufficient funds (${award.amount:,})"}), 400
            universe.balance -= award.amount
            database.update_game_state(balance=universe.balance)

        return jsonify({
            "success": True,
            "award":   award.to_dict(),
            "message": f"Tenure award granted to {wrestler.name}! {award.description}",
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@controversy_bp.route("/api/loyalty/exclusive-window/<wrestler_id>")
def api_check_exclusive_window(wrestler_id):
    """Step 219: Check if an exclusive negotiating window exists for a wrestler."""
    universe = get_universe()
    window   = _excl_windows.get(wrestler_id)
    wrestler = universe.get_wrestler_by_id(wrestler_id)
    if not wrestler:
        return jsonify({"success": False, "error": "Wrestler not found"}), 404

    is_active = window.is_active(universe.current_year, universe.current_week) if window else False
    weeks_rem = window.weeks_remaining(universe.current_year, universe.current_week) if window else 0

    # Auto-create window if contract is ≤ 12 weeks remaining
    contract_weeks_left = getattr(getattr(wrestler, "contract", None), "weeks_remaining", 99)
    can_open = contract_weeks_left <= 12 and not is_active

    return jsonify({
        "success":           True,
        "wrestler_id":       wrestler_id,
        "wrestler_name":     wrestler.name,
        "has_window":        is_active,
        "weeks_remaining":   weeks_rem,
        "can_open_window":   can_open,
        "contract_weeks_left": contract_weeks_left,
        "window":            window.to_dict() if window else None,
    })


# ═════════════════════════════════════════════════════════════════════════════
# STEPS 210-211: Holdouts
# ═════════════════════════════════════════════════════════════════════════════

@controversy_bp.route("/api/holdouts/active")
def api_get_active_holdouts():
    """Step 210: All active wrestler holdouts."""
    active = [h.to_dict() for h in _holdouts.values() if h.status == HoldoutStatus.ACTIVE]
    return jsonify({"success": True, "total": len(active), "holdouts": active})


@controversy_bp.route("/api/holdouts/start", methods=["POST"])
def api_start_holdout():
    """
    Step 210: A wrestler enters a holdout.
    POST: {
        wrestler_id: str,
        wrestler_name: str,
        original_demand: int,
        current_offer: int
    }
    """
    try:
        data = request.get_json() or {}
        wid  = data.get("wrestler_id")
        if not wid:
            return jsonify({"success": False, "error": "wrestler_id required"}), 400

        holdout = HoldoutSituation(
            wrestler_id      = wid,
            wrestler_name    = data.get("wrestler_name", "Unknown"),
            status           = HoldoutStatus.ACTIVE,
            original_demand  = int(data.get("original_demand", 0)),
            current_offer    = int(data.get("current_offer", 0)),
            minimum_to_end   = int(data.get("original_demand", 0)),
        )
        _holdouts[wid] = holdout

        return jsonify({
            "success":  True,
            "holdout":  holdout.to_dict(),
            "message": f"{holdout.wrestler_name} has entered a holdout. Demanding ${holdout.original_demand:,}/show.",
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@controversy_bp.route("/api/holdouts/<wrestler_id>")
def api_get_holdout(wrestler_id):
    """Step 210: Get holdout status for one wrestler."""
    h = _holdouts.get(wrestler_id)
    if not h:
        return jsonify({"success": True, "holdout": None, "message": "No active holdout."})
    return jsonify({"success": True, "holdout": h.to_dict()})


@controversy_bp.route("/api/holdouts/<wrestler_id>/resolve-deal", methods=["POST"])
def api_resolve_holdout_deal(wrestler_id):
    """Step 210-211: Resolve a holdout by reaching an agreement."""
    try:
        h = _holdouts.get(wrestler_id)
        if not h:
            return jsonify({"success": False, "error": "No holdout found"}), 404

        data           = request.get_json() or {}
        agreed_salary  = int(data.get("agreed_salary", h.minimum_to_end))
        result         = h.resolve_with_deal(agreed_salary)
        return jsonify({"success": True, "resolution": result, "holdout": h.to_dict()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@controversy_bp.route("/api/holdouts/<wrestler_id>/resolve-release", methods=["POST"])
def api_resolve_holdout_release(wrestler_id):
    """Step 210-211: Resolve a holdout by releasing the wrestler."""
    try:
        h = _holdouts.get(wrestler_id)
        if not h:
            return jsonify({"success": False, "error": "No holdout found"}), 404
        result = h.resolve_with_release()
        return jsonify({"success": True, "resolution": result, "holdout": h.to_dict()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ═════════════════════════════════════════════════════════════════════════════
# STEPS 212-213: Tampering
# ═════════════════════════════════════════════════════════════════════════════

@controversy_bp.route("/api/tampering/incidents")
def api_get_tampering_incidents():
    """Step 212: All detected tampering incidents."""
    all_incidents = []
    for wid, incidents in _tampering.items():
        for inc in incidents:
            if inc.detected:
                all_incidents.append(inc.to_dict())
    return jsonify({"success": True, "total": len(all_incidents), "incidents": all_incidents})


@controversy_bp.route("/api/tampering/report", methods=["POST"])
def api_report_tampering():
    """
    Step 212: Report a tampering incident (rival approaching your wrestler).
    POST: {
        promotion_id: str,
        promotion_name: str,
        wrestler_id: str,
        wrestler_name: str,
        intensity: "feelers"|"contact"|"offer"|"aggressive"
    }
    """
    try:
        data = request.get_json() or {}
        wid  = data.get("wrestler_id")
        if not wid:
            return jsonify({"success": False, "error": "wrestler_id required"}), 400

        try:
            intensity = TamperingIntensity(data.get("intensity", "feelers"))
        except ValueError:
            intensity = TamperingIntensity.FEELERS

        incident = TamperingIncident(
            promotion_id   = data.get("promotion_id", ""),
            promotion_name = data.get("promotion_name", "Unknown Promotion"),
            wrestler_id    = wid,
            wrestler_name  = data.get("wrestler_name", "Unknown"),
            intensity      = intensity,
            detected       = True,
        )

        if wid not in _tampering:
            _tampering[wid] = []
        _tampering[wid].append(incident)

        return jsonify({
            "success":  True,
            "incident": incident.to_dict(),
            "warning": (
                f"⚠️ {incident.promotion_name} has been {intensity.label.lower()}y approaching "
                f"{incident.wrestler_name}. Apply counter-measures immediately."
            ),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@controversy_bp.route("/api/tampering/<wrestler_id>/counter", methods=["POST"])
def api_counter_tampering(wrestler_id):
    """
    Step 213: Apply a counter-measure to resist tampering.
    POST: {
        measure: "loyalty_bonus"|"meeting"|"media_statement"|"legal_threat",
        loyalty_score: int (current loyalty score, for context)
    }
    """
    try:
        universe = get_universe()
        database = get_database()
        incidents = _tampering.get(wrestler_id, [])
        active    = [i for i in incidents if i.detected and not i.counter_measure_applied]

        if not active:
            return jsonify({"success": False, "error": "No active tampering incidents for this wrestler"}), 404

        data         = request.get_json() or {}
        measure      = data.get("measure", "meeting")
        loyalty_score = int(data.get("loyalty_score", 50))

        incident = active[-1]  # Apply to most recent
        result   = incident.apply_counter_measure(measure, loyalty_score)

        # Deduct cost
        cost = result.get("cost", 0)
        if cost > 0 and universe.balance >= cost:
            universe.balance -= cost
            database.update_game_state(balance=universe.balance)

        return jsonify({
            "success":         True,
            "wrestler_id":     wrestler_id,
            "measure_applied": measure,
            "effect":          result,
            "cost_paid":       cost,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ═════════════════════════════════════════════════════════════════════════════
# STEPS 215-217: Failed Negotiations
# ═════════════════════════════════════════════════════════════════════════════

@controversy_bp.route("/api/failed-negotiations/consequences", methods=["POST"])
def api_failed_negotiation_consequences():
    """
    Step 215-216: Determine consequence of a failed negotiation.
    POST: {
        wrestler_id: str,
        loyalty_score: int,
        morale: int,
        age: int,
        rival_offers_exist: bool,
        weeks_until_expiry: int
    }
    """
    try:
        data = request.get_json() or {}
        score = int(data.get("loyalty_score", 50))
        tier  = LoyaltyTier.from_score(score)

        consequence = determine_failed_negotiation_consequence(
            loyalty_tier                 = tier,
            morale                       = int(data.get("morale", 60)),
            age                          = int(data.get("age", 30)),
            rival_offers_exist           = bool(data.get("rival_offers_exist", False)),
            weeks_until_contract_expires = int(data.get("weeks_until_expiry", 12)),
        )

        wrestler_id   = data.get("wrestler_id", "")
        wrestler_name = data.get("wrestler_name", "The Wrestler")

        fallout = generate_public_fallout_narrative(consequence, wrestler_name)

        # Create re-approach window if applicable
        if consequence != FailedNegotiationConsequence.WALKS_TO_RIVAL:
            universe = get_universe()
            cooldown = {"enters_holdout": 12, "demands_public_trade": 8, "accepts_grudgingly": 4}.get(
                consequence.value, 6
            )
            window = ReApproachWindow(
                wrestler_id       = wrestler_id,
                wrestler_name     = wrestler_name,
                blocked_until_week = (universe.current_week + cooldown) % 52 or 1,
                blocked_until_year = universe.current_year + ((universe.current_week + cooldown) // 52),
                cooldown_reason   = f"Failed negotiation — {consequence.label}",
            )
            _reapproach[wrestler_id] = window

        return jsonify({
            "success":     True,
            "consequence": consequence.value,
            "consequence_label": consequence.label,
            "severity":    consequence.severity,
            "fallout":     fallout,
            "loyalty_tier": tier.value,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@controversy_bp.route("/api/failed-negotiations/re-approach-windows")
def api_re_approach_windows():
    """Step 217: All blocked re-approach windows."""
    universe = get_universe()
    windows  = []
    for wid, window in _reapproach.items():
        is_open = window.is_open(universe.current_year, universe.current_week)
        windows.append({
            **window.to_dict(),
            "is_open":            is_open,
            "weeks_until_open":   window.weeks_until_open(universe.current_year, universe.current_week),
        })
    return jsonify({"success": True, "total": len(windows), "windows": windows})


@controversy_bp.route("/api/failed-negotiations/goodwill-action", methods=["POST"])
def api_take_goodwill_action():
    """
    Step 217: Take a goodwill action to re-open a blocked window sooner.
    POST: { wrestler_id: str, action: "public_apology"|"tribute_video"|... }
    """
    try:
        universe = get_universe()
        database = get_database()
        data     = request.get_json() or {}
        wid      = data.get("wrestler_id")
        action   = data.get("action")

        if not wid or not action:
            return jsonify({"success": False, "error": "wrestler_id and action required"}), 400

        window = _reapproach.get(wid)
        if not window:
            return jsonify({"success": False, "error": "No blocked window for this wrestler"}), 404

        # Cost for some actions
        action_costs = {"public_apology": 5000, "hall_of_fame_hint": 25000}
        cost = action_costs.get(action, 0)
        if cost > 0:
            if universe.balance < cost:
                return jsonify({"success": False, "error": f"Insufficient funds (${cost:,})"}), 400
            universe.balance -= cost
            database.update_game_state(balance=universe.balance)

        result = window.take_goodwill_action(action)
        return jsonify({
            "success": True,
            "wrestler_id": wid,
            "action_result": result,
            "is_now_open": window.is_open(universe.current_year, universe.current_week),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ═════════════════════════════════════════════════════════════════════════════
# STEPS 221-223: Surprise Returns
# ═════════════════════════════════════════════════════════════════════════════

@controversy_bp.route("/api/surprise-returns/return-types")
def api_return_types():
    """Step 223: List all return types with their effects."""
    types = []
    for rt in SurpriseReturnType:
        types.append({
            "value":          rt.value,
            "label":          rt.label,
            "fan_pop_modifier": rt.fan_pop_modifier,
            "popularity_gain": rt.popularity_gain,
        })
    return jsonify({"success": True, "types": types})


@controversy_bp.route("/api/surprise-returns/<wrestler_id>/relationship")
def api_historical_relationship(wrestler_id):
    """
    Step 221: Get the historical relationship record with a wrestler
    who previously left the promotion.
    """
    fa_dict = _get_fa_dict(wrestler_id)
    if not fa_dict:
        # Check if we have stored history
        pass  # Falls through to generate basic relationship

    contract_history = fa_dict.get("contract_history", []) if fa_dict else []
    roc_history = [h for h in contract_history if "ring of champions" in str(h.get("promotion_name", "")).lower()]

    was_champion       = any(h.get("was_champion", False) for h in roc_history)
    years_together     = sum(
        (h.get("end_year", 1) - h.get("start_year", 1)) for h in roc_history
    ) if roc_history else 0
    departure_reason   = roc_history[-1].get("departure_reason", "contract_expired") if roc_history else "unknown"
    relationship_score = roc_history[-1].get("relationship_on_departure", 50) if roc_history else 50

    rel = HistoricalRelationship(
        wrestler_id            = wrestler_id,
        wrestler_name          = fa_dict.get("wrestler_name", "Unknown") if fa_dict else "Unknown",
        years_worked_together  = float(years_together),
        was_champion           = was_champion,
        departure_reason       = departure_reason,
        departed_on_good_terms = relationship_score >= 50,
        had_public_dispute     = relationship_score < 30,
        return_interest_modifier = int((relationship_score - 50) / 2),
    )

    return jsonify({"success": True, "relationship": rel.to_dict()})


@controversy_bp.route("/api/surprise-returns/plan", methods=["POST"])
def api_plan_surprise_return():
    """
    Step 223: Plan a surprise return for a wrestler.
    POST: {
        wrestler_id: str,
        wrestler_name: str,
        return_type: str,
        planned_show: str,
        planned_week: int,
        planned_year: int,
        secret_until_week: int  (0 = announce now)
    }
    """
    try:
        data          = request.get_json() or {}
        wrestler_id   = data.get("wrestler_id", "")
        wrestler_name = data.get("wrestler_name", "")

        try:
            rt = SurpriseReturnType(data.get("return_type", "face_return"))
        except ValueError:
            rt = SurpriseReturnType.FACE_RETURN

        universe   = get_universe()
        plan = SurpriseReturnPlan(
            wrestler_id      = wrestler_id,
            wrestler_name    = wrestler_name,
            return_type      = rt,
            planned_show     = data.get("planned_show", ""),
            planned_year     = int(data.get("planned_year", universe.current_year)),
            planned_week     = int(data.get("planned_week", universe.current_week)),
            secret_until_week = int(data.get("secret_until_week", 0)),
        )

        _surprise_plans[wrestler_id] = plan

        return jsonify({
            "success":        True,
            "plan":           plan.to_dict(),
            "expected_pop":   plan.expected_pop_score(),
            "message": (
                f"Return plan created for {wrestler_name}. "
                f"Type: {rt.label}. Expected pop score: {plan.expected_pop_score()}/100."
            ),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@controversy_bp.route("/api/surprise-returns/<wrestler_id>/tease", methods=["POST"])
def api_add_return_tease(wrestler_id):
    """Step 223: Add a tease video for a planned surprise return."""
    plan = _surprise_plans.get(wrestler_id)
    if not plan:
        return jsonify({"success": False, "error": "No return plan found for this wrestler"}), 404
    result = plan.add_tease_video()
    return jsonify({"success": True, "wrestler_id": wrestler_id, **result, "plan": plan.to_dict()})


@controversy_bp.route("/api/surprise-returns/<wrestler_id>/execute", methods=["POST"])
def api_execute_surprise_return(wrestler_id):
    """
    Step 223: Execute a planned surprise return at a show.
    POST: { show_name: str }
    """
    try:
        plan = _surprise_plans.get(wrestler_id)
        data = request.get_json() or {}
        show = data.get("show_name", "")

        if not plan:
            return jsonify({"success": False, "error": "No return plan found"}), 404
        if not show:
            return jsonify({"success": False, "error": "show_name required"}), 400

        result = plan.execute_return(show)
        return jsonify({
            "success": True,
            "return_result": result,
            "plan":          plan.to_dict(),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
