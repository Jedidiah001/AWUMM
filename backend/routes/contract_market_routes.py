"""API routes for contract market, release, and rival strategy mechanics."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from services.contract_market_service import (
    ContractMarketService,
    ContractMarketValidationError,
)


contract_market_bp = Blueprint("contract_market", __name__)


def service() -> ContractMarketService:
    return ContractMarketService(current_app.config["DATABASE"])


def ok(payload: dict, status: int = 200):
    return jsonify({"success": True, **payload}), status


def fail(message: str, status: int = 400):
    return jsonify({"success": False, "error": message}), status


@contract_market_bp.route("/api/contract-market/dashboard")
def contract_market_dashboard():
    return ok(service().dashboard())


@contract_market_bp.route("/api/contract-market/contract-types")
def contract_market_types():
    return ok({"contract_types": service().contract_types()})


@contract_market_bp.route("/api/contract-market/reputation")
def contract_market_reputation():
    return ok({"reputation": service().repo.reputation()})


@contract_market_bp.route("/api/contract-market/demands", methods=["POST"])
def contract_market_demands():
    try:
        svc = service()
        data = request.get_json() or {}
        target = svc._target_profile(data)
        return ok({
            "target": target,
            "demands": svc.generate_demands(
                target,
                data.get("contract_type", "full_time"),
                data.get("clauses") or {},
            ),
        })
    except ContractMarketValidationError as exc:
        return fail(str(exc), 400)
    except Exception as exc:
        return fail(str(exc), 500)


@contract_market_bp.route("/api/contract-market/negotiate", methods=["POST"])
def contract_market_negotiate():
    try:
        data = request.get_json() or {}
        result = service().propose_contract(data, seed=data.get("seed"))
        return ok(result)
    except ContractMarketValidationError as exc:
        return fail(str(exc), 400)
    except Exception as exc:
        return fail(str(exc), 500)


@contract_market_bp.route("/api/contract-market/handshake", methods=["POST"])
def contract_market_handshake():
    try:
        return ok({"handshake": service().create_handshake(request.get_json() or {})}, 201)
    except ContractMarketValidationError as exc:
        return fail(str(exc), 400)
    except Exception as exc:
        return fail(str(exc), 500)


@contract_market_bp.route("/api/contract-market/handshake/<handshake_id>/break", methods=["POST"])
def contract_market_break_handshake(handshake_id):
    try:
        data = request.get_json() or {}
        return ok(service().break_handshake(handshake_id, data.get("reason", "Management broke the handshake deal")))
    except ContractMarketValidationError as exc:
        return fail(str(exc), 404)
    except Exception as exc:
        return fail(str(exc), 500)


@contract_market_bp.route("/api/contract-market/release/<wrestler_id>", methods=["POST"])
def contract_market_release(wrestler_id):
    try:
        return ok(service().release_wrestler(wrestler_id, request.get_json() or {}))
    except ContractMarketValidationError as exc:
        return fail(str(exc), 404)
    except Exception as exc:
        return fail(str(exc), 500)


@contract_market_bp.route("/api/contract-market/rivals/simulate", methods=["POST"])
def contract_market_rivals_simulate():
    try:
        data = request.get_json() or {}
        return ok(service().simulate_rival_week(data, seed=data.get("seed")))
    except Exception as exc:
        return fail(str(exc), 500)

