"""Thin API routes for simulation features #149-182 and #243-250."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from services.simulation_expansion_service import SimulationExpansionService, ValidationError


simulation_expansion_bp = Blueprint("simulation_expansion", __name__)


def get_database():
    return current_app.config["DATABASE"]


def get_service() -> SimulationExpansionService:
    service = current_app.config.get("SIMULATION_EXPANSION_SERVICE")
    if service is None:
        service = SimulationExpansionService(get_database())
        current_app.config["SIMULATION_EXPANSION_SERVICE"] = service
    return service


def payload() -> dict:
    return request.get_json(silent=True) or {}


def ok(data=None, status=200, **extra):
    response = {"success": True, "data": data}
    response.update(extra)
    return jsonify(response), status


def fail(message: str, status: int = 400, **extra):
    response = {"success": False, "error": {"message": message, **extra}}
    return jsonify(response), status


def handle(callable_, success_status: int = 200):
    try:
        return ok(callable_(), success_status)
    except ValidationError as exc:
        return fail(str(exc), 422)
    except Exception as exc:
        current_app.logger.exception("Simulation expansion route failed")
        return fail(str(exc), 500)


def with_calendar_defaults(data: dict) -> dict:
    merged = dict(data)
    try:
        state = get_database().get_game_state()
        merged.setdefault("year", state.get("current_year", 1))
        merged.setdefault("week", state.get("current_week", 1))
    except Exception:
        merged.setdefault("year", 1)
        merged.setdefault("week", 1)
    return merged


@simulation_expansion_bp.route("/api/simulation-expansion/dashboard", methods=["GET"])
def simulation_dashboard():
    def _run():
        service = get_service()
        return {
            "locker_room": service.locker_dashboard(request.args.get("brand")),
            "developmental": service.developmental_dashboard(),
            "advanced": service.advanced_dashboard(),
            "dynamic_events": service.dynamic_event_dashboard(),
        }

    return handle(_run)


@simulation_expansion_bp.route("/api/simulation-expansion/weekly", methods=["POST"])
def run_weekly_simulation():
    def _run():
        data = with_calendar_defaults(payload())
        return get_service().run_weekly_simulation(int(data["year"]), int(data["week"]), data.get("seed"))

    return handle(_run)


# Dynamic event system


@simulation_expansion_bp.route("/api/dynamic-events/dashboard", methods=["GET"])
def dynamic_events_dashboard():
    return handle(lambda: get_service().dynamic_event_dashboard())


@simulation_expansion_bp.route("/api/dynamic-events/audit", methods=["GET"])
def dynamic_events_audit():
    return handle(lambda: get_service().sync_dynamic_event_audit())


@simulation_expansion_bp.route("/api/dynamic-events/weekly", methods=["POST"])
def dynamic_events_weekly():
    def _run():
        data = with_calendar_defaults(payload())
        return get_service().run_dynamic_events(
            int(data["year"]),
            int(data["week"]),
            data.get("seed"),
            data,
        )

    return handle(_run)


@simulation_expansion_bp.route("/api/dynamic-events/pulse", methods=["POST"])
def dynamic_events_pulse():
    return handle(lambda: get_service().dynamic_event_pulse(with_calendar_defaults(payload())))


@simulation_expansion_bp.route("/api/dynamic-events/<event_id>/resolve", methods=["POST"])
def resolve_dynamic_event(event_id):
    return handle(lambda: get_service().resolve_dynamic_event(event_id, payload()))


# Locker room and backstage culture


@simulation_expansion_bp.route("/api/locker-room/enterprise", methods=["GET"])
def locker_room_enterprise():
    return handle(lambda: get_service().locker_dashboard(request.args.get("brand")))


@simulation_expansion_bp.route("/api/locker-room/weekly", methods=["POST"])
def locker_room_weekly():
    def _run():
        data = with_calendar_defaults(payload())
        return get_service().run_weekly_culture(int(data["year"]), int(data["week"]), data.get("seed"))

    return handle(_run)


@simulation_expansion_bp.route("/api/locker-room/wrestlers/<wrestler_id>", methods=["GET"])
def wrestler_culture(wrestler_id):
    return handle(lambda: get_service().wrestler_culture_detail(wrestler_id))


@simulation_expansion_bp.route("/api/locker-room/meetings", methods=["POST"])
def create_meeting():
    return handle(lambda: get_service().create_meeting(with_calendar_defaults(payload())), 201)


@simulation_expansion_bp.route("/api/locker-room/discipline", methods=["POST"])
def create_discipline():
    return handle(lambda: get_service().create_disciplinary_action(with_calendar_defaults(payload())), 201)


@simulation_expansion_bp.route("/api/locker-room/creative-disagreements/<disagreement_id>/resolve", methods=["POST"])
def resolve_creative_disagreement(disagreement_id):
    return handle(lambda: get_service().resolve_creative_disagreement(disagreement_id, payload()))


# Performance center and developmental


@simulation_expansion_bp.route("/api/performance-center/dashboard", methods=["GET"])
def performance_center_dashboard():
    return handle(lambda: get_service().developmental_dashboard())


@simulation_expansion_bp.route("/api/performance-center/weekly", methods=["POST"])
def performance_center_weekly():
    def _run():
        data = with_calendar_defaults(payload())
        return get_service().run_development_week(int(data["year"]), int(data["week"]), data.get("seed"))

    return handle(_run)


@simulation_expansion_bp.route("/api/performance-center/trainers", methods=["POST"])
def create_trainer():
    return handle(lambda: get_service().create_trainer(payload()), 201)


@simulation_expansion_bp.route("/api/performance-center/curricula", methods=["POST"])
def create_curriculum():
    return handle(lambda: get_service().create_curriculum(payload()), 201)


@simulation_expansion_bp.route("/api/performance-center/trainees", methods=["POST"])
def add_trainee():
    return handle(lambda: get_service().add_trainee(with_calendar_defaults(payload())), 201)


@simulation_expansion_bp.route("/api/performance-center/tryouts", methods=["POST"])
def schedule_tryout():
    return handle(lambda: get_service().schedule_tryout(with_calendar_defaults(payload())), 201)


@simulation_expansion_bp.route("/api/performance-center/tryouts/<tryout_id>", methods=["GET"])
def get_tryout(tryout_id):
    return handle(lambda: get_service().get_tryout(tryout_id))


@simulation_expansion_bp.route("/api/performance-center/candidates/<candidate_id>/sign", methods=["POST"])
def sign_candidate(candidate_id):
    return handle(lambda: get_service().sign_tryout_candidate(candidate_id, with_calendar_defaults(payload())), 201)


@simulation_expansion_bp.route("/api/performance-center/callups", methods=["POST"])
def create_callup():
    return handle(lambda: get_service().create_callup(with_calendar_defaults(payload())), 201)


@simulation_expansion_bp.route("/api/performance-center/senddowns", methods=["POST"])
def create_senddown():
    return handle(lambda: get_service().create_senddown(with_calendar_defaults(payload())), 201)


@simulation_expansion_bp.route("/api/performance-center/excursions", methods=["POST"])
def start_excursion():
    return handle(lambda: get_service().start_excursion(with_calendar_defaults(payload())), 201)


@simulation_expansion_bp.route("/api/performance-center/veteran-trainers", methods=["POST"])
def veteran_trainer_transition():
    return handle(lambda: get_service().transition_veteran_to_trainer(with_calendar_defaults(payload())), 201)


# Advanced simulation layer


@simulation_expansion_bp.route("/api/advanced-simulation/dashboard", methods=["GET"])
def advanced_dashboard():
    return handle(lambda: get_service().advanced_dashboard())


@simulation_expansion_bp.route("/api/advanced-simulation/match-scripts", methods=["POST"])
def create_match_script():
    return handle(lambda: get_service().create_match_script(payload()), 201)


@simulation_expansion_bp.route("/api/advanced-simulation/match-scripts/<script_id>/evaluate", methods=["POST"])
def evaluate_match_script(script_id):
    return handle(lambda: get_service().evaluate_match_script(script_id, payload()))


@simulation_expansion_bp.route("/api/advanced-simulation/production", methods=["POST"])
def record_production():
    return handle(lambda: get_service().record_production_quality(with_calendar_defaults(payload())), 201)


@simulation_expansion_bp.route("/api/advanced-simulation/attendance", methods=["POST"])
def project_attendance():
    return handle(lambda: get_service().project_attendance(with_calendar_defaults(payload())), 201)


@simulation_expansion_bp.route("/api/advanced-simulation/aging/run", methods=["POST"])
def run_aging():
    def _run():
        data = with_calendar_defaults(payload())
        return get_service().run_aging(int(data["year"]), int(data["week"]), data.get("seed"))

    return handle(_run)


@simulation_expansion_bp.route("/api/advanced-simulation/industry/run", methods=["POST"])
def run_industry():
    def _run():
        data = with_calendar_defaults(payload())
        return get_service().run_industry_evolution(int(data["year"]), int(data["week"]))

    return handle(_run)


@simulation_expansion_bp.route("/api/advanced-simulation/brands/assign", methods=["POST"])
def assign_brand():
    return handle(lambda: get_service().assign_brand(with_calendar_defaults(payload())))


@simulation_expansion_bp.route("/api/advanced-simulation/endgame/update", methods=["POST"])
def update_endgame():
    def _run():
        data = with_calendar_defaults(payload())
        return get_service().update_endgame_progress(int(data["year"]), int(data["week"]))

    return handle(_run)
