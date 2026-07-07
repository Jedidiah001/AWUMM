"""Free-agent signing finalization service.

This module owns the transition from an accepted negotiation to a real roster
contract.  Negotiation engines should decide *whether* a deal is accepted; this
service performs the durable side effects: balance update, wrestler creation,
contract creation, free-agent status update, and session cleanup.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from models.contract import Contract, CreativeControlLevel
from models.wrestler import Injury, Wrestler
from persistence.free_agent_db import mark_free_agent_signed, save_negotiation_attempt


DEFAULT_SIGNING_PROMOTION = "Ring of Champions"
DEFAULT_SIGNING_BRAND = "ROC Alpha"


def _enum_value(value: Any, default: str = "") -> str:
    """Return an enum value or string fallback."""
    if value is None:
        return default
    return getattr(value, "value", value) or default


def _get_offer_attr(offer: Any, attr: str, default: Any = None) -> Any:
    """Read an offer attribute from either a dataclass/object or dict."""
    if isinstance(offer, dict):
        return offer.get(attr, default)
    return getattr(offer, attr, default)


def _creative_control_from_offer(offer: Any) -> CreativeControlLevel:
    creative_clauses = _get_offer_attr(offer, "creative_clauses")
    if isinstance(creative_clauses, dict):
        raw = creative_clauses.get("creative_control", CreativeControlLevel.NONE.value)
    else:
        raw = getattr(creative_clauses, "creative_control", CreativeControlLevel.NONE)

    raw = _enum_value(raw, CreativeControlLevel.NONE.value)
    try:
        return CreativeControlLevel(raw)
    except ValueError:
        return CreativeControlLevel.NONE


def _brand_from_offer(offer: Any, fallback: str = DEFAULT_SIGNING_BRAND) -> str:
    creative_clauses = _get_offer_attr(offer, "creative_clauses")
    if isinstance(creative_clauses, dict):
        return creative_clauses.get("brand_preference") or fallback
    return getattr(creative_clauses, "brand_preference", None) or fallback


def _bool_lifestyle_clause(offer: Any, key: str) -> bool:
    lifestyle_clauses = _get_offer_attr(offer, "lifestyle_clauses")
    if isinstance(lifestyle_clauses, dict):
        return bool(lifestyle_clauses.get(key, False))
    return bool(getattr(lifestyle_clauses, key, False))


def _max_appearances_from_offer(offer: Any) -> Optional[int]:
    lifestyle_clauses = _get_offer_attr(offer, "lifestyle_clauses")
    if isinstance(lifestyle_clauses, dict):
        value = lifestyle_clauses.get("max_appearances_per_year")
    else:
        value = getattr(lifestyle_clauses, "max_appearances_per_year", None)
    try:
        value = int(value)
    except (TypeError, ValueError):
        return None
    return value or None


def _merchandise_share_from_offer(offer: Any) -> float:
    merch_deal = _get_offer_attr(offer, "merch_deal")
    if isinstance(merch_deal, dict):
        value = merch_deal.get("wrestler_pct", 30)
    else:
        value = getattr(merch_deal, "wrestler_pct", 30)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 30.0


def _guaranteed_ppv_from_offer(offer: Any) -> int:
    ppv_bonuses = _get_offer_attr(offer, "ppv_bonuses")
    if isinstance(ppv_bonuses, dict):
        value = ppv_bonuses.get("guaranteed_ppv_minimum", 0)
    else:
        value = getattr(ppv_bonuses, "guaranteed_ppv_minimum", 0)
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _build_contract(offer: Any, current_year: int, current_week: int) -> Contract:
    salary = int(_get_offer_attr(offer, "salary_per_show", 0) or 0)
    weeks = int(_get_offer_attr(offer, "contract_weeks", 52) or 52)
    creative_control = _creative_control_from_offer(offer)

    return Contract(
        salary_per_show=salary,
        total_length_weeks=weeks,
        weeks_remaining=weeks,
        signing_year=current_year,
        signing_week=current_week,
        base_salary=salary,
        current_escalated_salary=salary,
        merchandise_share_percentage=_merchandise_share_from_offer(offer),
        creative_control_level=creative_control,
        guaranteed_ppv_appearances=_guaranteed_ppv_from_offer(offer),
        has_injury_protection=_bool_lifestyle_clause(offer, "injury_pay_protection"),
        max_appearances_per_year=_max_appearances_from_offer(offer),
    )


def _build_wrestler_from_free_agent(
    free_agent: Any,
    contract: Contract,
    brand: str,
) -> Wrestler:
    return Wrestler(
        wrestler_id=free_agent.wrestler_id,
        name=free_agent.wrestler_name,
        age=free_agent.age,
        gender=free_agent.gender,
        alignment=free_agent.alignment,
        role=free_agent.role,
        primary_brand=brand,
        brawling=free_agent.brawling,
        technical=free_agent.technical,
        speed=free_agent.speed,
        mic=free_agent.mic,
        psychology=free_agent.psychology,
        stamina=free_agent.stamina,
        years_experience=free_agent.years_experience,
        is_major_superstar=free_agent.is_major_superstar,
        popularity=free_agent.popularity,
        momentum=0,
        morale=60,
        fatigue=0,
        contract=contract,
        injury=Injury.none(),
        is_retired=False,
    )


def finalize_free_agent_signing(
    *,
    free_agent_pool: Any,
    universe: Any,
    database: Any,
    free_agent_id: str,
    offer: Any,
    promotion_name: str = DEFAULT_SIGNING_PROMOTION,
) -> Dict[str, Any]:
    """Finalize an accepted free-agent negotiation as a roster signing."""
    if not free_agent_pool:
        return {"success": False, "error": "Free agent pool is unavailable"}
    if not universe or not database:
        return {"success": False, "error": "Universe/database is unavailable"}

    free_agent = free_agent_pool.get_free_agent_by_id(free_agent_id)
    if not free_agent:
        return {"success": False, "error": "Free agent no longer available"}

    state = database.get_game_state()
    current_year = int(state.get("current_year", getattr(universe, "current_year", 1)))
    current_week = int(state.get("current_week", getattr(universe, "current_week", 1)))
    signing_bonus = int(_get_offer_attr(offer, "signing_bonus", 0) or 0)

    if signing_bonus > 0:
        balance = int(state.get("balance", getattr(universe, "balance", 0)) or 0)
        if balance < signing_bonus:
            return {
                "success": False,
                "error": f"Insufficient funds for signing bonus (${signing_bonus:,})",
            }
        database.update_game_state(balance=balance - signing_bonus)

    contract = _build_contract(offer, current_year, current_week)
    brand = _brand_from_offer(offer)
    wrestler = _build_wrestler_from_free_agent(free_agent, contract, brand)

    universe.save_wrestler(wrestler)
    mark_free_agent_signed(
        database,
        free_agent_id,
        promotion_name,
        current_year,
        current_week,
    )

    if hasattr(free_agent_pool, "remove_free_agent"):
        free_agent_pool.remove_free_agent(free_agent_id)

    try:
        save_negotiation_attempt(
            database,
            free_agent_id=free_agent_id,
            promotion_name=promotion_name,
            offer_salary=contract.salary_per_show,
            offer_length_weeks=contract.total_length_weeks,
            offer_signing_bonus=signing_bonus,
            accepted=True,
            rejection_reason=None,
            negotiation_round=int(_get_offer_attr(offer, "round_number", 1) or 1),
            year=current_year,
            week=current_week,
        )
    except Exception:
        # Signing is already durable; history is best-effort because older DBs may
        # not have negotiation-history tables initialized.
        pass

    return {
        "success": True,
        "wrestler_id": wrestler.id,
        "wrestler_name": wrestler.name,
        "brand": wrestler.primary_brand,
        "salary": contract.salary_per_show,
        "contract_weeks": contract.total_length_weeks,
        "signing_bonus": signing_bonus,
        "message": (
            f"🎉 {wrestler.name} signed for "
            f"${contract.salary_per_show:,}/show × {contract.total_length_weeks} weeks!"
        ),
    }
