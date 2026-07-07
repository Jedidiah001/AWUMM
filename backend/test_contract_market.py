import os
import sys
import unittest
import uuid

sys.path.insert(0, os.path.dirname(__file__))

from persistence.database import Database
from services.contract_market_service import (
    ContractMarketService,
    ContractMarketValidationError,
)


class ContractMarketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        tmp_dir = os.path.join(root, "test_tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        cls.db_path = os.path.join(tmp_dir, f"contract_market_{uuid.uuid4().hex}.db")
        cls.database = Database(cls.db_path)
        cls.service = ContractMarketService(cls.database)

    @classmethod
    def tearDownClass(cls):
        if cls.database is not None:
            cls.database.close()
        for suffix in ("", "-wal", "-shm"):
            path = cls.db_path + suffix
            if os.path.exists(path):
                os.remove(path)

    def setUp(self):
        self._reset_owned_rows()
        self._seed_data()

    def _reset_owned_rows(self):
        for table in (
            "contract_market_negotiations",
            "contract_market_deals",
            "contract_market_handshake_deals",
            "rival_strategy_events",
        ):
            self.database.conn.execute(f"DELETE FROM {table}")
        self.database.conn.execute("DELETE FROM wrestlers WHERE id IN ('w_star', 'w_low')")
        self.database.conn.execute("DELETE FROM rival_promotions WHERE promotion_id = 'rp_aggressive'")
        self.database.conn.execute(
            """
            UPDATE contract_market_reputation
            SET reputation_score = 62,
                trust_score = 62,
                last_reason = 'Initial market reputation',
                updated_at = datetime('now')
            WHERE id = 1
            """
        )
        self.database.conn.commit()

    def _seed_data(self):
        now = "2026-06-21T00:00:00"
        self.database.conn.executemany(
            """
            INSERT OR REPLACE INTO wrestlers (
                id, name, age, gender, alignment, role, primary_brand,
                brawling, technical, speed, mic, psychology, stamina,
                years_experience, is_major_superstar, popularity, momentum,
                morale, fatigue, injury_severity, injury_description,
                injury_weeks_remaining, contract_salary, contract_total_weeks,
                contract_weeks_remaining, contract_signing_year,
                contract_signing_week, is_retired, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "w_star",
                    "Market Star",
                    33,
                    "Male",
                    "face",
                    "main_event",
                    "AUM",
                    82,
                    78,
                    75,
                    84,
                    80,
                    77,
                    13,
                    1,
                    90,
                    25,
                    76,
                    8,
                    "None",
                    None,
                    0,
                    30000,
                    104,
                    12,
                    1,
                    1,
                    0,
                    now,
                    now,
                ),
                (
                    "w_low",
                    "Undervalued Ace",
                    28,
                    "Female",
                    "heel",
                    "upper_midcard",
                    "AUM",
                    72,
                    74,
                    70,
                    68,
                    73,
                    72,
                    8,
                    0,
                    74,
                    10,
                    31,
                    14,
                    "None",
                    None,
                    0,
                    9000,
                    52,
                    8,
                    1,
                    1,
                    0,
                    now,
                    now,
                ),
            ],
        )
        self.database.conn.execute(
            """
            INSERT OR REPLACE INTO rival_promotions (
                promotion_id, name, abbreviation, tier, brand_identity,
                budget_per_year, remaining_budget, avg_salary_per_show,
                roster_size, max_roster_size, roster_needs, gender_focus,
                aggression, loyalty_to_talent, prestige, relationship_with_player,
                active_pursuits, signed_this_year, lost_bidding_wars, won_bidding_wars,
                booking_philosophy, management_style, cash_reserves, momentum,
                created_at, updated_at
            ) VALUES (
                'rp_aggressive', 'Rival Elite', 'REW', 'major', 'sports_entertainment',
                2000000, 1200000, 20000, 38, 45, '[]', 'both',
                88, 55, 78, 30, '[]', 0, 0, 0,
                'aggressive', 'cutthroat', 1200000, 70, ?, ?
            )
            """,
            (now, now),
        )
        self.database.conn.commit()

    def test_accepted_contract_persists_deal_and_wrestler_terms(self):
        demands = self.service.generate_demands(
            self.service.repo.get_wrestler("w_star"),
            "full_time",
            {"creative_control": "approval"},
        )
        result = self.service.propose_contract(
            {
                "wrestler_id": "w_star",
                "contract_type": "full_time",
                "salary_per_show": demands["asking_salary"] + 25000,
                "contract_weeks": 104,
                "signing_bonus": 100000,
                "clauses": {
                    "creative_control": "approval",
                    "release_clause_amount": 500000,
                    "no_compete_weeks": 12,
                },
            },
            seed=1,
        )

        self.assertEqual(result["negotiation"]["outcome"], "accepted")
        self.assertEqual(result["deal"]["status"], "active")

        wrestler = self.service.repo.get_wrestler("w_star")
        self.assertEqual(wrestler["contract_type"], "full_time")
        self.assertEqual(wrestler["creative_control_clause"], "approval")
        self.assertEqual(wrestler["release_clause_amount"], 500000)
        self.assertGreaterEqual(wrestler["morale"], 82)

    def test_low_offer_generates_counter_offer(self):
        demands = self.service.generate_demands(
            self.service.repo.get_wrestler("w_low"),
            "per_appearance",
            {},
        )
        result = self.service.propose_contract(
            {
                "wrestler_id": "w_low",
                "contract_type": "per_appearance",
                "salary_per_show": int(demands["minimum_salary"] * 0.82),
                "contract_weeks": 26,
            },
            seed=9,
        )

        self.assertEqual(result["negotiation"]["outcome"], "countered")
        self.assertGreaterEqual(
            result["negotiation"]["counter_salary"],
            demands["minimum_salary"],
        )

    def test_top_talent_can_refuse_bad_reputation(self):
        self.service.repo.adjust_reputation(-40, -20, "Scandal-heavy year")

        result = self.service.propose_contract(
            {
                "wrestler_id": "w_star",
                "contract_type": "legends",
                "salary_per_show": 250000,
                "contract_weeks": 12,
            },
            seed=3,
        )

        self.assertEqual(result["negotiation"]["outcome"], "rejected")
        self.assertIn("reputation", result["negotiation"]["refusal_reason"].lower())

    def test_breaking_handshake_deal_hits_trust_and_morale(self):
        before = self.service.repo.get_wrestler("w_low")
        handshake = self.service.create_handshake(
            {
                "wrestler_id": "w_low",
                "promised_terms": {"summary": "Title match next month"},
            }
        )

        result = self.service.break_handshake(handshake["id"], "Promise could not be honored")
        after = self.service.repo.get_wrestler("w_low")

        self.assertEqual(result["handshake"]["status"], "broken")
        self.assertLess(after["morale"], before["morale"])
        self.assertLess(result["reputation"]["trust_score"], 62)

    def test_release_applies_clause_cost_and_no_compete(self):
        self.service.repo.update_wrestler_contract(
            "w_low",
            {"release_clause_amount": 150000, "no_compete_weeks": 8},
        )
        self.database.conn.commit()

        result = self.service.release_wrestler(
            "w_low",
            {"reason": "Budget reset", "no_compete_weeks": 8},
        )

        wrestler = self.service.repo.get_wrestler("w_low")
        self.assertEqual(result["deal"]["status"], "released")
        self.assertEqual(result["release_cost"], 150000)
        self.assertEqual(wrestler["is_retired"], 1)
        self.assertIsNotNone(result["deal"]["no_compete_until_week"])

    def test_rival_ai_generates_persistent_strategy_events(self):
        result = self.service.simulate_rival_week(
            {"player_show_name": "AUM Prime"},
            seed=2,
        )

        self.assertGreaterEqual(result["total"], 1)
        event_types = {event["event_type"] for event in result["events"]}
        self.assertTrue(
            event_types & {
                "poach_attempt",
                "counter_programming",
                "spy_report",
                "partnership_offer",
                "invasion_angle",
                "out_of_business",
            }
        )

    def test_invalid_contract_type_is_rejected(self):
        with self.assertRaises(ContractMarketValidationError):
            self.service.generate_demands(
                self.service.repo.get_wrestler("w_low"),
                "lifetime",
                {},
            )


if __name__ == "__main__":
    unittest.main()
