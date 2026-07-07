"""Finance-integrated sponsorship, venue, tour, and settlement services."""

from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

from services.finance_enterprise_schema import ensure_finance_enterprise_tables


REVENUE_ACCOUNTS = {
    "Sponsorship Revenue": "4000",
    "Event Revenue": "4100",
    "Merchandise Revenue": "4200",
}
EXPENSE_ACCOUNTS = {
    "Venue Rental": "5000",
    "Venue Costs": "5000",
    "Travel": "5100",
    "Production Costs": "5200",
    "Talent Costs": "5300",
    "Marketing": "5400",
    "Capital Expenditure": "1500",
}
SEVERITY_IMPACT = {"Low": 6, "Medium": 12, "High": 24, "Critical": 38}
SHOW_TARGET_MARGINS = {"weekly_tv": 0.0, "house_show": 15.0, "minor_ppv": 30.0, "major_ppv": 30.0}


def _now() -> str:
    return datetime.now().isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _money(value: Any, default: int = 0) -> int:
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default


def _clamp(value: int, lower: int, upper: int) -> int:
    return max(lower, min(upper, value))


def _rows(cursor, query: str, params: Iterable[Any] = ()) -> List[Dict[str, Any]]:
    cursor.execute(query, tuple(params))
    return [dict(row) for row in cursor.fetchall()]


def _row(cursor, query: str, params: Iterable[Any] = ()) -> Optional[Dict[str, Any]]:
    cursor.execute(query, tuple(params))
    result = cursor.fetchone()
    return dict(result) if result else None


def _event_margin(revenue: int, expenses: int) -> float:
    return round(((revenue - expenses) / revenue) * 100, 2) if revenue else 0.0


def _date_after_months(start_date: str, months: int) -> str:
    start = datetime.fromisoformat(start_date)
    return (start + timedelta(days=30 * months)).date().isoformat()


def _haversine(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    if None in (a.get("latitude"), a.get("longitude"), b.get("latitude"), b.get("longitude")):
        return 0.0
    radius = 3958.8
    lat1, lon1 = math.radians(float(a["latitude"])), math.radians(float(a["longitude"]))
    lat2, lon2 = math.radians(float(b["latitude"])), math.radians(float(b["longitude"]))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    value = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return round(radius * (2 * math.asin(math.sqrt(value))), 1)


class FinanceEnterpriseService:
    """Coordinates enterprise finance features against the existing SQLite DB."""

    def __init__(self, database):
        self.database = database
        ensure_finance_enterprise_tables(database)

    def post_transaction(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        category = payload.get("category", "Event Revenue")
        amount = _money(payload.get("amount"))
        tx_type = payload.get("type") or ("Revenue" if amount >= 0 else "Expense")
        account = payload.get("account_code") or self._account_for(category, tx_type)
        status = payload.get("status", "Posted")
        tx_id = payload.get("id") or _new_id("fin_tx")
        today = datetime.now().date().isoformat()
        cursor = self.database.conn.cursor()
        cursor.execute(
            """
            INSERT INTO finance_transactions
            (id, transaction_date, posting_date, amount, type, category,
             source_module, source_id, description, status, account_code,
             created_by, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tx_id,
                payload.get("transaction_date", today),
                payload.get("posting_date", payload.get("transaction_date", today)),
                amount,
                tx_type,
                category,
                payload.get("source_module", "Finance"),
                payload.get("source_id"),
                payload.get("description", category),
                status,
                account,
                payload.get("created_by", "system"),
                _now(),
                _now(),
            ),
        )
        if status == "Posted":
            self._apply_balance(amount)
        self.database.conn.commit()
        return self.get_transaction(tx_id)

    def get_transaction(self, tx_id: str) -> Dict[str, Any]:
        cursor = self.database.conn.cursor()
        tx = _row(cursor, "SELECT * FROM finance_transactions WHERE id=?", (tx_id,))
        if not tx:
            raise ValueError("Transaction not found")
        return tx

    def list_transactions(self, limit: int = 100) -> List[Dict[str, Any]]:
        cursor = self.database.conn.cursor()
        return _rows(cursor, "SELECT * FROM finance_transactions ORDER BY created_at DESC LIMIT ?", (limit,))

    def create_sponsor(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        name = (payload.get("company_name") or payload.get("sponsor_name") or "").strip()
        if not name:
            raise ValueError("company_name is required")
        sponsor_id = _new_id("sponsor")
        now = _now()
        cursor = self.database.conn.cursor()
        cursor.execute(
            """
            INSERT INTO sponsors
            (sponsor_id, company_name, logo_url, industry_category, tier_level,
             brand_value, market_reputation_score, contact_name, contact_email,
             contact_phone, satisfaction_score, historical_partnerships, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sponsor_id,
                name,
                payload.get("logo_url", ""),
                payload.get("industry_category") or payload.get("industry", "Consumer Brand"),
                payload.get("tier_level") or payload.get("tier", "Official Partner"),
                _clamp(_money(payload.get("brand_value"), 65), 1, 100),
                _clamp(_money(payload.get("market_reputation_score"), 70), 1, 100),
                payload.get("contact_name", ""),
                payload.get("contact_email", ""),
                payload.get("contact_phone") or payload.get("phone", ""),
                _clamp(_money(payload.get("satisfaction_score"), 78), 0, 100),
                payload.get("historical_partnerships", ""),
                now,
                now,
            ),
        )
        self.database.conn.commit()
        return self.get_sponsor(sponsor_id)

    def get_sponsor(self, sponsor_id: str) -> Dict[str, Any]:
        cursor = self.database.conn.cursor()
        sponsor = _row(cursor, "SELECT * FROM sponsors WHERE sponsor_id=? AND deleted_at IS NULL", (sponsor_id,))
        if not sponsor:
            raise ValueError("Sponsor not found")
        sponsor["contracts"] = _rows(cursor, "SELECT * FROM sponsorship_contracts WHERE sponsor_id=? AND deleted_at IS NULL", (sponsor_id,))
        sponsor["controversies"] = _rows(cursor, "SELECT * FROM sponsorship_controversies WHERE sponsor_id=? ORDER BY created_at DESC", (sponsor_id,))
        return sponsor

    def list_sponsorships(self) -> Dict[str, Any]:
        cursor = self.database.conn.cursor()
        sponsors = _rows(cursor, "SELECT * FROM sponsors WHERE deleted_at IS NULL ORDER BY company_name")
        for sponsor in sponsors:
            sponsor["contracts"] = self._contracts_for_sponsor(cursor, sponsor["sponsor_id"])
        return {"sponsors": sponsors, "summary": self._sponsorship_summary(cursor)}

    def create_contract(self, sponsor_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.get_sponsor(sponsor_id)
        start = payload.get("start_date") or datetime.now().date().isoformat()
        months = max(1, _money(payload.get("duration_months") or payload.get("duration"), 12))
        contract_id = _new_id("contract")
        now = _now()
        cursor = self.database.conn.cursor()
        cursor.execute(
            """
            INSERT INTO sponsorship_contracts
            (contract_id, sponsor_id, contract_type, status, start_date, end_date,
             duration_months, total_value, payment_schedule, exclusivity_clause,
             territory, renewal_option, performance_bonus, termination_penalty,
             created_at, updated_at)
            VALUES (?, ?, ?, 'Active', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                contract_id,
                sponsor_id,
                payload.get("contract_type", "Presenting Sponsorship"),
                start,
                payload.get("end_date") or _date_after_months(start, months),
                months,
                _money(payload.get("total_value"), 250_000),
                payload.get("payment_schedule", "Quarterly"),
                payload.get("exclusivity_clause", ""),
                payload.get("territory", "Global"),
                payload.get("renewal_option", ""),
                _money(payload.get("performance_bonus"), 0),
                _money(payload.get("termination_penalty"), 0),
                now,
                now,
            ),
        )
        for requirement in payload.get("requirements", []):
            self._insert_requirement(cursor, contract_id, requirement, now)
        self.database.conn.commit()
        return self._contract_detail(contract_id)

    def record_deliverable(self, requirement_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        cursor = self.database.conn.cursor()
        requirement = _row(cursor, "SELECT * FROM sponsorship_requirements WHERE requirement_id=?", (requirement_id,))
        if not requirement:
            raise ValueError("Requirement not found")
        tracking_id = _new_id("deliverable")
        cursor.execute(
            """
            INSERT INTO sponsorship_deliverable_tracking
            (tracking_id, requirement_id, event_id, event_name, delivered_value,
             notes, delivered_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tracking_id,
                requirement_id,
                payload.get("event_id"),
                payload.get("event_name", ""),
                float(payload.get("delivered_value", 0)),
                payload.get("notes", ""),
                payload.get("delivered_at") or datetime.now().date().isoformat(),
                _now(),
            ),
        )
        self.database.conn.commit()
        return self._requirement_progress(requirement_id)

    def record_controversy(self, sponsor_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.get_sponsor(sponsor_id)
        severity = payload.get("severity", "Medium").title()
        impact = SEVERITY_IMPACT.get(severity, SEVERITY_IMPACT["Medium"])
        threat = self._threat_level(severity)
        controversy_id = _new_id("controversy")
        cursor = self.database.conn.cursor()
        cursor.execute(
            """
            INSERT INTO sponsorship_controversies
            (controversy_id, sponsor_id, contract_id, incident_type, severity,
             description, impact_score, threat_level, response_required, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                controversy_id,
                sponsor_id,
                payload.get("contract_id"),
                payload.get("incident_type", "Brand Safety Incident"),
                severity,
                payload.get("description", ""),
                impact,
                threat,
                payload.get("response_required", "Sponsor notification and recovery plan"),
                _now(),
            ),
        )
        cursor.execute(
            "UPDATE sponsors SET satisfaction_score = MAX(0, satisfaction_score - ?), updated_at=? WHERE sponsor_id=?",
            (impact, _now(), sponsor_id),
        )
        self.database.conn.commit()
        return {"controversy": _row(cursor, "SELECT * FROM sponsorship_controversies WHERE controversy_id=?", (controversy_id,)), "sponsor": self.get_sponsor(sponsor_id)}

    def process_sponsorship_payment(self, contract_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        contract = self._contract_detail(contract_id)
        amount = _money(payload.get("amount")) or self._scheduled_payment_amount(contract)
        sponsor = self.get_sponsor(contract["sponsor_id"])
        tx = self.post_transaction({
            "amount": amount,
            "type": "Revenue",
            "category": "Sponsorship Revenue",
            "source_module": "Sponsorship",
            "source_id": contract_id,
            "description": f"{sponsor['company_name']} - {payload.get('label', 'Sponsor payment')}",
            "status": "Posted",
        })
        cursor = self.database.conn.cursor()
        cursor.execute(
            """
            INSERT INTO sponsorship_transactions
            (sponsorship_transaction_id, contract_id, finance_transaction_id,
             transaction_kind, amount, created_at)
            VALUES (?, ?, ?, 'Payment', ?, ?)
            """,
            (_new_id("spon_tx"), contract_id, tx["id"], amount, _now()),
        )
        self.database.conn.commit()
        return {"transaction": tx, "contract": contract}

    def list_venues_tours(self) -> Dict[str, Any]:
        cursor = self.database.conn.cursor()
        venues = _rows(cursor, "SELECT * FROM venues WHERE COALESCE(is_active,1)=1 AND deleted_at IS NULL ORDER BY prestige_score DESC, name LIMIT 100")
        tours = _rows(cursor, "SELECT * FROM tours WHERE deleted_at IS NULL ORDER BY created_at DESC LIMIT 50")
        for venue in venues:
            venue["facilities"] = _rows(cursor, "SELECT * FROM venue_facilities WHERE venue_id=?", (venue["venue_id"],))
            venue["upgrades"] = _rows(cursor, "SELECT * FROM venue_upgrades WHERE venue_id=? ORDER BY purchased_at DESC", (venue["venue_id"],))
        for tour in tours:
            tour["events"] = _rows(cursor, "SELECT * FROM tour_events WHERE tour_id=? ORDER BY sequence_no", (tour["tour_id"],))
        return {"venues": venues, "tours": tours, "summary": self._venue_tour_summary(cursor)}

    def purchase_upgrade(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        venue_id = payload.get("venue_id")
        cursor = self.database.conn.cursor()
        venue = _row(cursor, "SELECT * FROM venues WHERE venue_id=?", (venue_id,))
        if not venue:
            raise ValueError("Venue not found")
        cost = _money(payload.get("upfront_cost"), 500_000)
        revenue_lift = _money(payload.get("expected_revenue_increase"), 50_000)
        roi_events = max(1, math.ceil(cost / max(1, revenue_lift)))
        upgrade_id = _new_id("upgrade")
        cursor.execute(
            """
            INSERT INTO venue_upgrades
            (upgrade_id, venue_id, upgrade_category, upgrade_name, upfront_cost,
             maintenance_cost, expected_revenue_increase, capacity_increase,
             premium_revenue_boost, roi_events, purchased_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                upgrade_id,
                venue_id,
                payload.get("upgrade_category", "Infrastructure"),
                payload.get("upgrade_name", "LED Video Wall Installation"),
                cost,
                _money(payload.get("maintenance_cost"), 8_000),
                revenue_lift,
                _money(payload.get("capacity_increase"), 0),
                _money(payload.get("premium_revenue_boost"), 0),
                roi_events,
                datetime.now().date().isoformat(),
                _now(),
                _now(),
            ),
        )
        self._insert_facility(cursor, venue_id, payload.get("upgrade_name", "LED Video Wall Installation"))
        tx = self.post_transaction({
            "amount": -cost,
            "type": "Expense",
            "category": "Capital Expenditure",
            "source_module": "Venue",
            "source_id": upgrade_id,
            "description": f"{venue['name']} - {payload.get('upgrade_name', 'Venue upgrade')}",
        })
        return {"upgrade": _row(cursor, "SELECT * FROM venue_upgrades WHERE upgrade_id=?", (upgrade_id,)), "transaction": tx}

    def create_tour(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        tour_id = _new_id("tour")
        now = _now()
        cursor = self.database.conn.cursor()
        cursor.execute(
            """
            INSERT INTO tours
            (tour_id, tour_name, theme, tour_type, start_date, end_date,
             roster_assignment, budget_allocation, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tour_id,
                payload.get("tour_name", "House Show Tour"),
                payload.get("theme", ""),
                payload.get("tour_type", "House Shows"),
                payload.get("start_date", datetime.now().date().isoformat()),
                payload.get("end_date", datetime.now().date().isoformat()),
                json.dumps(payload.get("roster", [])),
                _money(payload.get("budget_allocation"), 0),
                now,
                now,
            ),
        )
        for index, event in enumerate(payload.get("events", []), start=1):
            self._insert_tour_event(cursor, tour_id, event, index, now)
        self.database.conn.commit()
        self.optimize_tour(tour_id)
        return self.get_tour(tour_id)

    def get_tour(self, tour_id: str) -> Dict[str, Any]:
        cursor = self.database.conn.cursor()
        tour = _row(cursor, "SELECT * FROM tours WHERE tour_id=?", (tour_id,))
        if not tour:
            raise ValueError("Tour not found")
        tour["events"] = _rows(cursor, "SELECT * FROM tour_events WHERE tour_id=? ORDER BY sequence_no", (tour_id,))
        tour["routing"] = _rows(cursor, "SELECT * FROM tour_routing WHERE tour_id=? ORDER BY created_at", (tour_id,))
        return tour

    def optimize_tour(self, tour_id: str) -> Dict[str, Any]:
        cursor = self.database.conn.cursor()
        events = _rows(cursor, "SELECT te.*, v.latitude, v.longitude, v.name venue_name FROM tour_events te JOIN venues v ON v.venue_id=te.venue_id WHERE te.tour_id=? ORDER BY sequence_no", (tour_id,))
        if len(events) < 2:
            return {"tour": self.get_tour(tour_id), "distance_miles": 0, "travel_cost": 0}
        ordered = self._nearest_neighbor(events)
        cursor.execute("DELETE FROM tour_routing WHERE tour_id=?", (tour_id,))
        distance_total, cost_total = self._write_route_rows(cursor, tour_id, ordered)
        for index, event in enumerate(ordered, start=1):
            cursor.execute("UPDATE tour_events SET sequence_no=?, updated_at=? WHERE event_id=?", (index, _now(), event["event_id"]))
        self.database.conn.commit()
        return {"tour": self.get_tour(tour_id), "distance_miles": distance_total, "travel_cost": cost_total}

    def settle_event(self, event_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        revenue = self._event_revenue(payload)
        expenses = self._event_expenses(payload)
        profit = revenue - expenses
        margin = _event_margin(revenue, expenses)
        cursor = self.database.conn.cursor()
        self._upsert_event_financials(cursor, event_id, payload, revenue, expenses, profit, margin)
        self._post_event_transactions(event_id, payload, revenue)
        cursor.execute("UPDATE tour_events SET status='Settled', updated_at=? WHERE event_id=?", (_now(), event_id))
        self._insert_event_settlement(cursor, event_id, revenue, expenses, profit, margin)
        self.database.conn.commit()
        return {"event_id": event_id, "revenue": revenue, "expenses": expenses, "profit": profit, "margin_pct": margin}

    def settle_tour(self, tour_id: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        cursor = self.database.conn.cursor()
        rows = _rows(cursor, "SELECT ef.* FROM event_financials ef JOIN tour_events te ON te.event_id=ef.event_id WHERE te.tour_id=?", (tour_id,))
        revenue = sum(row["total_revenue"] for row in rows)
        expenses = sum(row["total_expenses"] for row in rows)
        profit = revenue - expenses
        settlement_id = _new_id("settlement")
        cursor.execute(
            """
            INSERT INTO finance_settlements
            (id, settlement_type, source_id, period, revenue_total, expense_total,
             profit, margin_pct, status, notes, created_at, updated_at)
            VALUES (?, 'Tour', ?, ?, ?, ?, ?, ?, 'Reconciled', ?, ?, ?)
            """,
            (settlement_id, tour_id, "tour_close", revenue, expenses, profit, _event_margin(revenue, expenses), (payload or {}).get("notes", ""), _now(), _now()),
        )
        cursor.execute("UPDATE tours SET status='Settled', updated_at=? WHERE tour_id=?", (_now(), tour_id))
        self.database.conn.commit()
        return {"settlement_id": settlement_id, "tour_id": tour_id, "revenue": revenue, "expenses": expenses, "profit": profit, "events": rows}

    def profitability_report(self) -> Dict[str, Any]:
        cursor = self.database.conn.cursor()
        tour_rows = _rows(cursor, "SELECT te.event_id, te.event_name, te.event_type, ef.total_revenue, ef.total_expenses, ef.profit, ef.margin_pct FROM event_financials ef JOIN tour_events te ON te.event_id=ef.event_id ORDER BY ef.created_at DESC LIMIT 10")
        show_rows = self._show_history_profitability(cursor)
        events = tour_rows + show_rows
        avg_profit = round(sum(e["profit"] for e in events) / max(1, len(events)))
        profitable = len([e for e in events if e["profit"] >= 0])
        return {"events": events[:10], "average_profit": avg_profit, "profitable_events": profitable, "loss_events": len(events) - profitable}

    def budget_variance_report(self, period: str = "current_quarter") -> Dict[str, Any]:
        cursor = self.database.conn.cursor()
        budgets = _rows(cursor, "SELECT * FROM finance_budgets WHERE period=?", (period,))
        rows = []
        for budget in budgets:
            actual = self._actual_for_budget(cursor, budget["category"])
            baseline = int(budget["baseline_amount"])
            rows.append({"category": budget["category"], "budget": baseline, "actual": actual, "variance": actual - baseline, "variance_pct": _event_margin(actual, baseline)})
        return {"period": period, "rows": rows}

    def forecasts(self) -> Dict[str, Any]:
        cursor = self.database.conn.cursor()
        active_contracts = _rows(cursor, "SELECT * FROM sponsorship_contracts WHERE status='Active' AND deleted_at IS NULL")
        scheduled_events = _rows(cursor, "SELECT * FROM tour_events WHERE status='Scheduled' ORDER BY event_date LIMIT 30")
        weekly_sponsor = sum(self._scheduled_payment_amount(c) for c in active_contracts) / 13
        event_profit = sum(e["projected_profit"] for e in scheduled_events)
        return {"next_30_days": round(weekly_sponsor * 4 + event_profit), "next_60_days": round(weekly_sponsor * 8 + event_profit), "next_90_days": round(weekly_sponsor * 13 + event_profit)}

    def reconcile(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        tx_id = payload.get("transaction_id")
        cursor = self.database.conn.cursor()
        cursor.execute("UPDATE finance_transactions SET status='Reconciled', updated_at=? WHERE id=?", (_now(), tx_id))
        self.database.conn.commit()
        return self.get_transaction(tx_id)

    def enterprise_dashboard(self) -> Dict[str, Any]:
        cursor = self.database.conn.cursor()
        return {
            "sponsorship": self._sponsorship_summary(cursor),
            "venues_tours": self._venue_tour_summary(cursor),
            "profitability": self.profitability_report(),
            "budget_variance": self.budget_variance_report(),
            "forecasts": self.forecasts(),
            "transactions": self.list_transactions(25),
        }

    def _account_for(self, category: str, tx_type: str) -> str:
        if tx_type == "Revenue":
            return REVENUE_ACCOUNTS.get(category, "4100")
        return EXPENSE_ACCOUNTS.get(category, "5200")

    def _apply_balance(self, amount: int) -> None:
        if not hasattr(self.database, "get_game_state") or not hasattr(self.database, "update_game_state"):
            return
        state = self.database.get_game_state()
        self.database.update_game_state(balance=int(state.get("balance", 0)) + amount)

    def _contracts_for_sponsor(self, cursor, sponsor_id: str) -> List[Dict[str, Any]]:
        contracts = _rows(cursor, "SELECT * FROM sponsorship_contracts WHERE sponsor_id=? AND deleted_at IS NULL", (sponsor_id,))
        for contract in contracts:
            contract["requirements"] = self._requirements_for_contract(cursor, contract["contract_id"])
        return contracts

    def _contract_detail(self, contract_id: str) -> Dict[str, Any]:
        cursor = self.database.conn.cursor()
        contract = _row(cursor, "SELECT * FROM sponsorship_contracts WHERE contract_id=? AND deleted_at IS NULL", (contract_id,))
        if not contract:
            raise ValueError("Contract not found")
        contract["requirements"] = self._requirements_for_contract(cursor, contract_id)
        return contract

    def _requirements_for_contract(self, cursor, contract_id: str) -> List[Dict[str, Any]]:
        requirements = _rows(cursor, "SELECT * FROM sponsorship_requirements WHERE contract_id=? AND deleted_at IS NULL", (contract_id,))
        for requirement in requirements:
            requirement.update(self._requirement_progress(requirement["requirement_id"], cursor))
        return requirements

    def _insert_requirement(self, cursor, contract_id: str, requirement: Dict[str, Any], now: str) -> None:
        cursor.execute(
            """
            INSERT INTO sponsorship_requirements
            (requirement_id, contract_id, requirement_type, description,
             target_value, unit, cadence, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _new_id("req"),
                contract_id,
                requirement.get("requirement_type", "TV Exposure"),
                requirement.get("description", "Sponsor exposure commitment"),
                float(requirement.get("target_value", 1)),
                requirement.get("unit", "occurrence"),
                requirement.get("cadence", "weekly"),
                now,
                now,
            ),
        )

    def _requirement_progress(self, requirement_id: str, cursor=None) -> Dict[str, Any]:
        cursor = cursor or self.database.conn.cursor()
        requirement = _row(cursor, "SELECT * FROM sponsorship_requirements WHERE requirement_id=?", (requirement_id,))
        delivered = _row(cursor, "SELECT COALESCE(SUM(delivered_value), 0) delivered FROM sponsorship_deliverable_tracking WHERE requirement_id=?", (requirement_id,))
        amount = float(delivered["delivered"] if delivered else 0)
        target = float(requirement["target_value"] if requirement else 1)
        return {"delivered_value": amount, "compliance_pct": round(min(100.0, (amount / max(target, 1)) * 100), 1)}

    def _sponsorship_summary(self, cursor) -> Dict[str, Any]:
        active_value = _row(cursor, "SELECT COALESCE(SUM(total_value),0) value FROM sponsorship_contracts WHERE status='Active' AND deleted_at IS NULL")["value"]
        posted = _row(cursor, "SELECT COALESCE(SUM(amount),0) value FROM finance_transactions WHERE category='Sponsorship Revenue' AND amount > 0")["value"]
        at_risk = _row(cursor, "SELECT COUNT(*) count FROM sponsors WHERE satisfaction_score < 55 AND deleted_at IS NULL")["count"]
        return {"active_contract_value": int(active_value), "revenue_recognized": int(posted), "pipeline_value": 0, "at_risk_contracts": int(at_risk)}

    def _scheduled_payment_amount(self, contract: Dict[str, Any]) -> int:
        months = max(1, int(contract.get("duration_months") or 12))
        total = int(contract.get("total_value") or 0)
        schedule = (contract.get("payment_schedule") or "Quarterly").lower()
        divisor = {"upfront": 1, "annual": max(1, math.ceil(months / 12)), "quarterly": max(1, math.ceil(months / 3))}.get(schedule, months)
        return round(total / divisor)

    def _threat_level(self, severity: str) -> str:
        return {"Low": "Concerned", "Medium": "Reviewing", "High": "Suspending", "Critical": "Withdrawing"}.get(severity, "Reviewing")

    def _insert_facility(self, cursor, venue_id: str, facility_name: str) -> None:
        cursor.execute(
            """
            INSERT INTO venue_facilities
            (facility_id, venue_id, facility_type, quality_score, notes, created_at, updated_at)
            VALUES (?, ?, 'Production', 88, ?, ?, ?)
            """,
            (_new_id("facility"), venue_id, facility_name, _now(), _now()),
        )

    def _venue_tour_summary(self, cursor) -> Dict[str, Any]:
        venue_count = _row(cursor, "SELECT COUNT(*) count FROM venues WHERE COALESCE(is_active,1)=1 AND deleted_at IS NULL")["count"]
        tour_count = _row(cursor, "SELECT COUNT(*) count FROM tours WHERE deleted_at IS NULL")["count"]
        upcoming = _row(cursor, "SELECT COALESCE(SUM(projected_profit),0) profit FROM tour_events WHERE status='Scheduled'")["profit"]
        capex = _row(cursor, "SELECT COALESCE(SUM(upfront_cost),0) total FROM venue_upgrades")["total"]
        return {"venue_count": int(venue_count), "tour_count": int(tour_count), "upcoming_event_profit": int(upcoming), "upgrade_capex": int(capex)}

    def _insert_tour_event(self, cursor, tour_id: str, event: Dict[str, Any], index: int, now: str) -> None:
        venue = _row(cursor, "SELECT * FROM venues WHERE venue_id=?", (event["venue_id"],))
        if not venue:
            raise ValueError("Venue not found")
        revenue = self._projected_revenue(venue, event.get("event_type", "house_show"))
        expenses = self._projected_expenses(venue, event.get("event_type", "house_show"))
        cursor.execute(
            """
            INSERT INTO tour_events
            (event_id, tour_id, venue_id, event_name, event_type, event_date,
             sequence_no, projected_revenue, projected_expenses, projected_profit,
             created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.get("event_id") or _new_id("event"),
                tour_id,
                event["venue_id"],
                event.get("event_name") or f"{venue['name']} Event",
                event.get("event_type", "house_show"),
                event.get("event_date"),
                index,
                revenue,
                expenses,
                revenue - expenses,
                now,
                now,
            ),
        )

    def _projected_revenue(self, venue: Dict[str, Any], event_type: str) -> int:
        capacity = int(venue.get("wrestling_capacity") or venue.get("capacity") or 10_000)
        draw = {"weekly_tv": 0.72, "house_show": 0.68, "minor_ppv": 0.86, "major_ppv": 0.96}.get(event_type, 0.70)
        ticket = {"weekly_tv": 58, "house_show": 64, "minor_ppv": 95, "major_ppv": 140}.get(event_type, 64)
        return round(capacity * draw * ticket * 1.22)

    def _projected_expenses(self, venue: Dict[str, Any], event_type: str) -> int:
        production = {"weekly_tv": 115_000, "house_show": 80_000, "minor_ppv": 230_000, "major_ppv": 520_000}.get(event_type, 90_000)
        return int(venue.get("cost") or 0) + production + 180_000

    def _nearest_neighbor(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        remaining = events[:]
        ordered = [remaining.pop(0)]
        while remaining:
            current = ordered[-1]
            next_event = min(remaining, key=lambda event: _haversine(current, event))
            remaining.remove(next_event)
            ordered.append(next_event)
        return ordered

    def _write_route_rows(self, cursor, tour_id: str, ordered: List[Dict[str, Any]]) -> tuple[float, int]:
        distance_total, cost_total = 0.0, 0
        for previous, current in zip(ordered, ordered[1:]):
            distance = _haversine(previous, current)
            cost = round(distance * 18)
            distance_total += distance
            cost_total += cost
            cursor.execute(
                "INSERT INTO tour_routing (route_id, tour_id, from_event_id, to_event_id, distance_miles, travel_cost, travel_mode, rest_day_required, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (_new_id("route"), tour_id, previous["event_id"], current["event_id"], distance, cost, "Truck/Bus", 1 if distance > 500 else 0, _now()),
            )
        return round(distance_total, 1), cost_total

    def _event_revenue(self, payload: Dict[str, Any]) -> int:
        return sum(_money(payload.get(key)) for key in ("ticket_sales", "merchandise_sales", "concession_revenue", "parking_vip_revenue", "local_sponsorship_revenue"))

    def _event_expenses(self, payload: Dict[str, Any]) -> int:
        return sum(_money(payload.get(key)) for key in ("venue_rental", "production_costs", "talent_costs", "travel_costs", "marketing_costs"))

    def _upsert_event_financials(self, cursor, event_id: str, payload: Dict[str, Any], revenue: int, expenses: int, profit: int, margin: float) -> None:
        values = [event_id] + [_money(payload.get(k)) for k in ("ticket_sales", "merchandise_sales", "concession_revenue", "parking_vip_revenue", "local_sponsorship_revenue", "venue_rental", "production_costs", "talent_costs", "travel_costs", "marketing_costs")] + [revenue, expenses, profit, margin, _now(), _now()]
        cursor.execute(
            """
            INSERT OR REPLACE INTO event_financials
            (financial_id, event_id, ticket_sales, merchandise_sales, concession_revenue,
             parking_vip_revenue, local_sponsorship_revenue, venue_rental,
             production_costs, talent_costs, travel_costs, marketing_costs,
             total_revenue, total_expenses, profit, margin_pct, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [_new_id("event_fin"), *values],
        )

    def _post_event_transactions(self, event_id: str, payload: Dict[str, Any], revenue: int) -> None:
        self.post_transaction({"amount": revenue, "type": "Revenue", "category": "Event Revenue", "source_module": "Tour", "source_id": event_id, "description": f"Event revenue - {event_id}"})
        expense_map = [("venue_rental", "Venue Rental"), ("production_costs", "Production Costs"), ("talent_costs", "Talent Costs"), ("travel_costs", "Travel"), ("marketing_costs", "Marketing")]
        for key, category in expense_map:
            amount = _money(payload.get(key))
            if amount:
                self.post_transaction({"amount": -amount, "type": "Expense", "category": category, "source_module": "Tour", "source_id": event_id, "description": f"{category} - {event_id}"})

    def _insert_event_settlement(self, cursor, event_id: str, revenue: int, expenses: int, profit: int, margin: float) -> None:
        cursor.execute(
            """
            INSERT OR REPLACE INTO finance_settlements
            (id, settlement_type, source_id, period, revenue_total, expense_total,
             profit, margin_pct, status, notes, created_at, updated_at)
            VALUES (?, 'Event', ?, ?, ?, ?, ?, ?, 'Reconciled', '', ?, ?)
            """,
            (_new_id("settlement"), event_id, datetime.now().date().isoformat(), revenue, expenses, profit, margin, _now(), _now()),
        )

    def _show_history_profitability(self, cursor) -> List[Dict[str, Any]]:
        try:
            rows = _rows(cursor, "SELECT show_id event_id, show_name event_name, show_type event_type, total_revenue, (total_revenue - net_profit) total_expenses, net_profit profit FROM show_history ORDER BY id DESC LIMIT 10")
        except Exception:
            return []
        for row in rows:
            row["margin_pct"] = _event_margin(int(row["total_revenue"] or 0), int(row["total_expenses"] or 0))
            row["target_margin_pct"] = SHOW_TARGET_MARGINS.get(row.get("event_type"), 0.0)
            row["meets_target"] = row["margin_pct"] >= row["target_margin_pct"]
        return rows

    def _actual_for_budget(self, cursor, category: str) -> int:
        if "Revenue" in category:
            row = _row(cursor, "SELECT COALESCE(SUM(amount),0) total FROM finance_transactions WHERE category=? AND amount > 0", (category,))
        elif category == "Tour Expenses":
            row = _row(cursor, "SELECT COALESCE(SUM(ABS(amount)),0) total FROM finance_transactions WHERE source_module='Tour' AND amount < 0")
        else:
            row = _row(cursor, "SELECT COALESCE(SUM(ABS(amount)),0) total FROM finance_transactions WHERE category=? AND amount < 0", (category,))
        return int(row["total"] if row else 0)
