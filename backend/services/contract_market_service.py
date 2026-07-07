"""Business logic for contract signings, releases, and rival promotion strategy."""

from __future__ import annotations

import random

from repositories.contract_market_repository import ContractMarketRepository


class ContractMarketValidationError(ValueError):
    pass


CONTRACT_TYPES = {
    "legends": {
        "label": "Legends Deal",
        "description": "Part-time legends for special appearances",
        "risk": "High cost, limited availability",
        "salary_multiplier": 1.65,
        "default_weeks": 26,
        "availability": "limited",
    },
    "full_time": {
        "label": "Full-Time Contract",
        "description": "Regular roster member",
        "risk": "Salary commitment",
        "salary_multiplier": 1.0,
        "default_weeks": 104,
        "availability": "regular",
    },
    "per_appearance": {
        "label": "Per-Appearance Deal",
        "description": "Pay per show basis",
        "risk": "Wrestler can leave anytime",
        "salary_multiplier": 1.18,
        "default_weeks": 26,
        "availability": "flexible",
    },
    "developmental": {
        "label": "Developmental Deal",
        "description": "Training facility prospects",
        "risk": "Low cost, long term investment",
        "salary_multiplier": 0.42,
        "default_weeks": 156,
        "availability": "developmental",
    },
    "freelance": {
        "label": "Freelance Deal",
        "description": "One-off appearances",
        "risk": "No long term commitment",
        "salary_multiplier": 1.35,
        "default_weeks": 4,
        "availability": "one_off",
    },
}


class ContractMarketService:
    def __init__(self, database):
        self.repo = ContractMarketRepository(database)

    def contract_types(self) -> dict:
        return CONTRACT_TYPES

    def dashboard(self) -> dict:
        return {
            "contract_types": CONTRACT_TYPES,
            "reputation": self.repo.reputation(),
            "recent_negotiations": self.repo.fetch_all(
                """
                SELECT * FROM contract_market_negotiations
                ORDER BY created_at DESC
                LIMIT 12
                """
            ),
            "active_deals": self.repo.fetch_all(
                """
                SELECT * FROM contract_market_deals
                WHERE status = 'active'
                ORDER BY created_at DESC
                LIMIT 12
                """
            ),
            "handshakes": self.repo.fetch_all(
                """
                SELECT * FROM contract_market_handshake_deals
                ORDER BY created_at DESC
                LIMIT 12
                """
            ),
            "rival_events": self.repo.fetch_all(
                """
                SELECT * FROM rival_strategy_events
                ORDER BY year DESC, week DESC, created_at DESC
                LIMIT 20
                """
            ),
            "negotiation_targets": self.repo.fetch_all(
                """
                SELECT id, name, primary_brand, role, popularity, morale,
                       contract_salary, contract_weeks_remaining, is_major_superstar
                FROM wrestlers
                WHERE is_retired = 0
                ORDER BY popularity DESC, name
                LIMIT 40
                """
            ),
        }

    def calculate_market_value(self, profile: dict) -> int:
        overall = self._overall(profile)
        popularity = float(profile.get("popularity", 50) or 50)
        momentum = float(profile.get("momentum", 0) or 0)
        role = str(profile.get("role", "Midcard") or "Midcard").lower()
        age = int(profile.get("age", 30) or 30)
        base = 5000 + (overall * 175) + (popularity * 145) + (momentum * 55)
        role_mult = {
            "main_event": 2.25,
            "main event": 2.25,
            "upper_midcard": 1.65,
            "upper midcard": 1.65,
            "midcard": 1.25,
            "lower_midcard": 0.9,
            "lower midcard": 0.9,
            "prospect": 0.55,
            "jobber": 0.65,
        }.get(role, 1.0)
        age_mod = 1.12 if 31 <= age <= 38 else 0.92 if age < 24 else max(0.74, 1 - max(0, age - 42) * 0.05)
        superstar = 1.25 if int(profile.get("is_major_superstar", 0) or 0) else 1.0
        value = int(base * role_mult * age_mod * superstar)
        return max(2500, round(value / 500) * 500)

    def generate_demands(self, profile: dict, contract_type: str, clauses: dict | None = None) -> dict:
        if contract_type not in CONTRACT_TYPES:
            raise ContractMarketValidationError(f"Unsupported contract type: {contract_type}")
        clauses = clauses or {}
        reputation = self.repo.reputation()
        market_value = self.calculate_market_value(profile)
        type_meta = CONTRACT_TYPES[contract_type]
        morale = int(profile.get("morale", 50) or 50)
        popularity = int(profile.get("popularity", 50) or 50)
        agent_leverage = self._agent_leverage(profile, popularity)
        reputation_drag = max(0, 60 - float(reputation["reputation_score"])) / 100
        morale_drag = max(0, 55 - morale) / 140
        clause_premium = self._clause_salary_premium(clauses)
        asking = market_value * type_meta["salary_multiplier"]
        asking *= 1 + agent_leverage + reputation_drag + morale_drag + clause_premium
        minimum = asking * (0.78 if morale >= 70 else 0.86 if morale >= 45 else 0.94)
        demanded_clauses = self._demanded_clauses(profile, contract_type, clauses)
        return {
            "market_value": market_value,
            "asking_salary": max(1000, round(int(asking) / 500) * 500),
            "minimum_salary": max(1000, round(int(minimum) / 500) * 500),
            "contract_weeks": type_meta["default_weeks"],
            "agent_name": self._agent_name(profile),
            "agent_leverage": round(agent_leverage, 3),
            "demanded_clauses": demanded_clauses,
            "reputation_score": round(float(reputation["reputation_score"]), 2),
            "trust_score": round(float(reputation["trust_score"]), 2),
        }

    def propose_contract(self, data: dict, seed: int | None = None) -> dict:
        target = self._target_profile(data)
        contract_type = data.get("contract_type", "full_time")
        if contract_type not in CONTRACT_TYPES:
            raise ContractMarketValidationError("Invalid contract_type")
        clauses = self._normalize_clauses(data.get("clauses") or {})
        year, week = self.repo.game_week()
        year = int(data.get("year", year))
        week = int(data.get("week", week))
        offer_salary = int(data.get("salary_per_show", 0) or 0)
        contract_weeks = int(data.get("contract_weeks", CONTRACT_TYPES[contract_type]["default_weeks"]) or 0)
        signing_bonus = int(data.get("signing_bonus", 0) or 0)
        if offer_salary <= 0:
            raise ContractMarketValidationError("salary_per_show must be greater than zero")
        if contract_weeks <= 0:
            raise ContractMarketValidationError("contract_weeks must be greater than zero")

        demands = self.generate_demands(target, contract_type, clauses)
        reputation = self.repo.reputation()
        rng = random.Random(seed if seed is not None else f"{target['name']}:{year}:{week}:{offer_salary}")
        acceptance = self._acceptance_score(target, demands, offer_salary, signing_bonus, contract_weeks, clauses, rng)
        refusal_reason = None
        status = "open"
        outcome = "countered"
        counter_salary = None
        response = {}

        if self._refuses_reputation(target, reputation):
            status = "closed"
            outcome = "rejected"
            acceptance = min(acceptance, 18)
            refusal_reason = "Promotion reputation is too weak for this wrestler's camp."
            response = {"message": refusal_reason}
        elif offer_salary >= demands["minimum_salary"] and acceptance >= 72:
            status = "closed"
            outcome = "accepted"
            response = {"message": f"{target['name']} accepted the {CONTRACT_TYPES[contract_type]['label']}."}
        elif acceptance >= 38:
            counter_salary = max(demands["minimum_salary"], round(int((demands["asking_salary"] + offer_salary) / 2) / 500) * 500)
            response = {
                "message": f"{target['name']}'s camp countered at ${counter_salary:,}/show.",
                "counter_salary": counter_salary,
            }
        else:
            status = "closed"
            outcome = "rejected"
            refusal_reason = "Offer was too far below market demands."
            response = {"message": refusal_reason}

        row = {
            "target_type": target["target_type"],
            "wrestler_id": target.get("id") if target["target_type"] == "roster" else None,
            "wrestler_name": target["name"],
            "free_agent_id": target.get("free_agent_id"),
            "status": status,
            "outcome": outcome,
            "contract_type": contract_type,
            "offered_salary": offer_salary,
            "demanded_salary": demands["asking_salary"],
            "counter_salary": counter_salary,
            "contract_weeks": contract_weeks,
            "signing_bonus": signing_bonus,
            "market_value": demands["market_value"],
            "popularity": int(target.get("popularity", 50) or 50),
            "morale": int(target.get("morale", 50) or 50),
            "agent_name": demands["agent_name"],
            "agent_leverage": demands["agent_leverage"],
            "promotion_reputation": reputation["reputation_score"],
            "acceptance_score": round(acceptance, 2),
            "refusal_reason": refusal_reason,
            "clauses_json": clauses,
            "demands_json": demands,
            "response_json": response,
            "year": year,
            "week": week,
        }

        with self.repo.transaction():
            negotiation = self.repo.insert_negotiation(row)
            deal = None
            if outcome == "accepted":
                deal = self._sign_deal(negotiation, target, clauses)
        return {"negotiation": negotiation, "deal": deal, "response": response}

    def create_handshake(self, data: dict) -> dict:
        target = self._target_profile(data)
        year, week = self.repo.game_week()
        with self.repo.transaction():
            handshake = self.repo.insert_handshake({
                "wrestler_id": target.get("id") if target["target_type"] == "roster" else None,
                "wrestler_name": target["name"],
                "free_agent_id": target.get("free_agent_id"),
                "promised_terms_json": data.get("promised_terms") or {},
                "status": "pending",
                "trust_delta": 0,
                "morale_delta": 0,
                "consequence_json": {},
                "year": int(data.get("year", year)),
                "week": int(data.get("week", week)),
            })
        return handshake

    def break_handshake(self, handshake_id: str, reason: str = "Management broke the handshake deal") -> dict:
        handshake = self.repo.fetch_one(
            "SELECT * FROM contract_market_handshake_deals WHERE id = ?",
            (handshake_id,),
        )
        if not handshake:
            raise ContractMarketValidationError("Handshake deal not found")
        year, week = self.repo.game_week()
        morale_delta = -14
        trust_delta = -12
        with self.repo.transaction():
            updated = self.repo.update_handshake(
                handshake_id,
                {
                    "status": "broken",
                    "trust_delta": trust_delta,
                    "morale_delta": morale_delta,
                    "consequence_json": {"reason": reason, "reputation_delta": -8, "future_agent_leverage": 0.08},
                    "resolved_year": year,
                    "resolved_week": week,
                },
            )
            if handshake.get("wrestler_id"):
                wrestler = self.repo.get_wrestler(handshake["wrestler_id"])
                if wrestler:
                    self.repo.update_wrestler_contract(
                        handshake["wrestler_id"],
                        {"morale": max(0, int(wrestler["morale"]) + morale_delta)},
                    )
            reputation = self.repo.adjust_reputation(-8, trust_delta, reason)
        return {"handshake": updated, "reputation": reputation}

    def release_wrestler(self, wrestler_id: str, data: dict) -> dict:
        wrestler = self.repo.get_wrestler(wrestler_id)
        if not wrestler:
            raise ContractMarketValidationError("Wrestler not found")
        year, week = self.repo.game_week()
        clauses = {
            "release_clause_amount": int(wrestler.get("release_clause_amount", 0) or data.get("release_clause_amount", 0) or 0),
            "no_compete_weeks": int(data.get("no_compete_weeks", wrestler.get("no_compete_weeks", 0) or 0) or 0),
            "creative_control": wrestler.get("creative_control_clause", "none"),
        }
        remaining = int(wrestler.get("contract_weeks_remaining", 0) or 0)
        salary = int(wrestler.get("contract_salary", 0) or 0)
        buyout = clauses["release_clause_amount"] or int(min(salary * max(1, remaining), salary * 26))
        no_compete_week = week + clauses["no_compete_weeks"]
        no_compete_year = year + ((no_compete_week - 1) // 52)
        no_compete_week = ((no_compete_week - 1) % 52) + 1
        with self.repo.transaction():
            self.repo.update_wrestler_contract(wrestler_id, {
                "contract_weeks_remaining": 0,
                "is_retired": 1,
                "morale": max(0, int(wrestler.get("morale", 50) or 50) - 8),
            })
            deal = self.repo.insert_deal({
                "negotiation_id": None,
                "wrestler_id": wrestler_id,
                "wrestler_name": wrestler["name"],
                "free_agent_id": None,
                "contract_type": wrestler.get("contract_type", "full_time") or "full_time",
                "salary_per_show": salary,
                "contract_weeks": int(wrestler.get("contract_total_weeks", remaining) or remaining),
                "weeks_remaining": 0,
                "signing_bonus": 0,
                "status": "released",
                "release_reason": data.get("reason", "Released by management"),
                "release_cost": buyout,
                "no_compete_until_year": no_compete_year if clauses["no_compete_weeks"] else None,
                "no_compete_until_week": no_compete_week if clauses["no_compete_weeks"] else None,
                "clauses_json": clauses,
                "signed_year": year,
                "signed_week": week,
            })
            reputation = self.repo.adjust_reputation(-2, -2, f"Released {wrestler['name']}")
        return {"deal": deal, "release_cost": buyout, "reputation": reputation}

    def simulate_rival_week(self, data: dict | None = None, seed: int | None = None) -> dict:
        data = data or {}
        year, week = self.repo.game_week()
        year = int(data.get("year", year))
        week = int(data.get("week", week))
        rng = random.Random(seed if seed is not None else f"rivals:{year}:{week}")
        rivals = self.repo.fetch_all("SELECT * FROM rival_promotions ORDER BY prestige DESC")
        wrestlers = self.repo.fetch_all(
            """
            SELECT id, name, popularity, morale, role, contract_salary,
                   contract_weeks_remaining, primary_brand
            FROM wrestlers
            WHERE is_retired = 0
            ORDER BY popularity DESC
            LIMIT 30
            """
        )
        events = []
        with self.repo.transaction():
            for rival in rivals:
                event = self._rival_event_for(rival, wrestlers, year, week, data, rng)
                if event:
                    events.append(self.repo.insert_rival_event(event))
        return {"events": events, "total": len(events)}

    def _sign_deal(self, negotiation: dict, target: dict, clauses: dict) -> dict:
        year = int(negotiation["year"])
        week = int(negotiation["week"])
        wrestler_id = target.get("id") if target["target_type"] == "roster" else None
        if wrestler_id:
            self.repo.update_wrestler_contract(wrestler_id, {
                "contract_salary": negotiation["offered_salary"],
                "contract_total_weeks": negotiation["contract_weeks"],
                "contract_weeks_remaining": negotiation["contract_weeks"],
                "contract_signing_year": year,
                "contract_signing_week": week,
                "contract_type": negotiation["contract_type"],
                "release_clause_amount": int(clauses.get("release_clause_amount", 0) or 0),
                "no_compete_weeks": int(clauses.get("no_compete_weeks", 0) or 0),
                "creative_control_clause": clauses.get("creative_control", "none"),
                "creative_control_level": clauses.get("creative_control", "none"),
                "buy_out_penalty": int(clauses.get("release_clause_amount", 0) or 0),
                "max_appearances_per_year": clauses.get("max_appearances_per_year"),
                "morale": min(100, int(target.get("morale", 50) or 50) + 6),
            })
        deal = self.repo.insert_deal({
            "negotiation_id": negotiation["id"],
            "wrestler_id": wrestler_id,
            "wrestler_name": target["name"],
            "free_agent_id": target.get("free_agent_id"),
            "contract_type": negotiation["contract_type"],
            "salary_per_show": negotiation["offered_salary"],
            "contract_weeks": negotiation["contract_weeks"],
            "weeks_remaining": negotiation["contract_weeks"],
            "signing_bonus": negotiation["signing_bonus"],
            "status": "active",
            "release_reason": None,
            "release_cost": 0,
            "no_compete_until_year": None,
            "no_compete_until_week": None,
            "clauses_json": clauses,
            "signed_year": year,
            "signed_week": week,
        })
        self.repo.adjust_reputation(1, 1, f"Signed {target['name']}")
        return deal

    def _target_profile(self, data: dict) -> dict:
        if data.get("wrestler_id"):
            wrestler = self.repo.get_wrestler(data["wrestler_id"])
            if not wrestler:
                raise ContractMarketValidationError("Wrestler not found")
            wrestler["target_type"] = "roster"
            return wrestler
        name = data.get("wrestler_name") or data.get("free_agent_name")
        if not name:
            raise ContractMarketValidationError("wrestler_id or wrestler_name is required")
        return {
            "target_type": "free_agent",
            "free_agent_id": data.get("free_agent_id"),
            "id": None,
            "name": name,
            "age": int(data.get("age", 30) or 30),
            "role": data.get("role", "Midcard"),
            "popularity": int(data.get("popularity", 50) or 50),
            "momentum": int(data.get("momentum", 0) or 0),
            "morale": int(data.get("morale", 55) or 55),
            "brawling": int(data.get("brawling", 55) or 55),
            "technical": int(data.get("technical", 55) or 55),
            "speed": int(data.get("speed", 55) or 55),
            "mic": int(data.get("mic", 55) or 55),
            "psychology": int(data.get("psychology", 55) or 55),
            "stamina": int(data.get("stamina", 55) or 55),
            "is_major_superstar": 1 if data.get("is_major_superstar") else 0,
            "agent_name": data.get("agent_name"),
        }

    def _overall(self, profile: dict) -> float:
        keys = ("brawling", "technical", "speed", "mic", "psychology", "stamina")
        return sum(float(profile.get(key, 50) or 50) for key in keys) / len(keys)

    def _normalize_clauses(self, clauses: dict) -> dict:
        return {
            "release_clause_amount": int(clauses.get("release_clause_amount", 0) or 0),
            "no_compete_weeks": int(clauses.get("no_compete_weeks", 0) or 0),
            "creative_control": clauses.get("creative_control", "none") or "none",
            "max_appearances_per_year": clauses.get("max_appearances_per_year"),
            "handshake": bool(clauses.get("handshake", False)),
        }

    def _clause_salary_premium(self, clauses: dict) -> float:
        premium = 0.0
        if clauses.get("release_clause_amount"):
            premium -= 0.03
        if int(clauses.get("no_compete_weeks", 0) or 0) > 0:
            premium += min(0.12, int(clauses["no_compete_weeks"]) / 260)
        premium += {"none": 0, "consultation": 0.03, "approval": 0.07, "partnership": 0.12, "full": 0.20}.get(
            clauses.get("creative_control", "none"), 0
        )
        return premium

    def _demanded_clauses(self, profile: dict, contract_type: str, clauses: dict) -> dict:
        popularity = int(profile.get("popularity", 50) or 50)
        demanded = {}
        if popularity >= 78:
            demanded["creative_control"] = "consultation"
        if popularity >= 86:
            demanded["release_clause_amount"] = max(int(clauses.get("release_clause_amount", 0) or 0), self.calculate_market_value(profile) * 26)
        if contract_type == "legends":
            demanded["max_appearances_per_year"] = int(clauses.get("max_appearances_per_year") or 8)
        if contract_type in {"freelance", "per_appearance"}:
            demanded["no_exclusivity"] = True
        return demanded

    def _agent_name(self, profile: dict) -> str | None:
        if profile.get("agent_name"):
            return profile["agent_name"]
        popularity = int(profile.get("popularity", 50) or 50)
        if popularity >= 72:
            return "Power Agent Group"
        if popularity >= 55:
            return "Standard Representation"
        return None

    def _agent_leverage(self, profile: dict, popularity: int) -> float:
        if profile.get("agent_name") or popularity >= 72:
            return min(0.18, popularity / 650)
        if popularity >= 55:
            return 0.05
        return 0.0

    def _acceptance_score(self, target, demands, offer_salary, signing_bonus, contract_weeks, clauses, rng) -> float:
        salary_ratio = offer_salary / max(1, demands["asking_salary"])
        score = 34 + (salary_ratio * 46)
        score += min(10, signing_bonus / max(1, demands["market_value"]))
        score += (int(target.get("morale", 50) or 50) - 50) * 0.24
        score += (float(demands["reputation_score"]) - 50) * 0.18
        score += 4 if contract_weeks >= demands["contract_weeks"] else -5
        if clauses.get("creative_control") in {"approval", "partnership", "full"}:
            score += 3
        if clauses.get("handshake"):
            score += float(demands["trust_score"] - 50) * 0.08
        score -= demands["agent_leverage"] * 30
        score += rng.uniform(-4, 4)
        return max(0, min(100, score))

    def _refuses_reputation(self, target: dict, reputation: dict) -> bool:
        popularity = int(target.get("popularity", 50) or 50)
        morale = int(target.get("morale", 50) or 50)
        return popularity >= 80 and float(reputation["reputation_score"]) < 35 and morale >= 45

    def _rival_event_for(self, rival, wrestlers, year, week, data, rng):
        name = rival.get("name") or rival.get("abbreviation") or "Rival Promotion"
        relationship = int(rival.get("relationship_with_player", 50) or 50)
        aggression = int(rival.get("aggression", 50) or 50)
        cash = int(rival.get("cash_reserves", rival.get("remaining_budget", 0)) or 0)
        momentum = int(rival.get("momentum", 50) or 50)
        if cash < 50000 and momentum < 25:
            return {
                "promotion_id": rival["promotion_id"],
                "promotion_name": name,
                "event_type": "out_of_business",
                "target_type": "promotion",
                "target_id": rival["promotion_id"],
                "target_name": name,
                "details_json": {"reason": "Low reserves and prolonged weak momentum", "cash_reserves": cash, "momentum": momentum},
                "impact_score": -25,
                "year": year,
                "week": week,
            }
        if relationship >= 72 and rng.random() < 0.28:
            return {
                "promotion_id": rival["promotion_id"],
                "promotion_name": name,
                "event_type": "partnership_offer",
                "target_type": "promotion",
                "target_id": "player",
                "target_name": "Player Promotion",
                "details_json": {"proposal": "Talent sharing and cross-promoted special event", "relationship": relationship},
                "impact_score": 8,
                "year": year,
                "week": week,
            }
        vulnerable = [
            wrestler for wrestler in wrestlers
            if int(wrestler.get("contract_weeks_remaining", 99) or 99) <= 16
            or int(wrestler.get("morale", 50) or 50) < 38
        ]
        if vulnerable and (aggression >= 60 or rng.random() < 0.35):
            target = rng.choice(vulnerable)
            offer = round(int(self.calculate_market_value(target) * (1.08 + aggression / 500)) / 500) * 500
            return {
                "promotion_id": rival["promotion_id"],
                "promotion_name": name,
                "event_type": "poach_attempt",
                "target_type": "wrestler",
                "target_id": target["id"],
                "target_name": target["name"],
                "details_json": {"offer_salary": offer, "morale": target["morale"], "weeks_remaining": target["contract_weeks_remaining"]},
                "impact_score": 12,
                "year": year,
                "week": week,
            }
        if data.get("player_show_name") and (aggression >= 55 or rng.random() < 0.22):
            return {
                "promotion_id": rival["promotion_id"],
                "promotion_name": name,
                "event_type": "counter_programming",
                "target_type": "show",
                "target_id": data.get("player_show_id"),
                "target_name": data.get("player_show_name"),
                "details_json": {"special_match": "Loaded main event", "expected_rating_split": round(0.05 + aggression / 1000, 3)},
                "impact_score": 10,
                "year": year,
                "week": week,
            }
        if rng.random() < 0.24:
            return {
                "promotion_id": rival["promotion_id"],
                "promotion_name": name,
                "event_type": "spy_report",
                "target_type": "show",
                "target_id": data.get("player_show_id"),
                "target_name": data.get("player_show_name", "Upcoming show"),
                "details_json": {"intel_quality": rng.randint(45, 90), "lead": "Rival scouting suggests a ratings push is coming."},
                "impact_score": 4,
                "year": year,
                "week": week,
            }
        if relationship <= 25 and aggression >= 75 and rng.random() < 0.16:
            return {
                "promotion_id": rival["promotion_id"],
                "promotion_name": name,
                "event_type": "invasion_angle",
                "target_type": "promotion",
                "target_id": "player",
                "target_name": "Player Promotion",
                "details_json": {"trigger": "Aggressive competition and poor relationship", "legal_risk": "medium"},
                "impact_score": 16,
                "year": year,
                "week": week,
            }
        return None

