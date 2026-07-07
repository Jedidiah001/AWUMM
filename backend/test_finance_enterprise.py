import os
import sqlite3
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from services.finance_enterprise import FinanceEnterpriseService


class FakeDatabase:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            """
            CREATE TABLE game_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                balance INTEGER NOT NULL
            )
            """
        )
        self.conn.execute("INSERT INTO game_state (id, balance) VALUES (1, 1000000)")
        self.conn.commit()

    def get_game_state(self):
        row = self.conn.execute("SELECT balance FROM game_state WHERE id=1").fetchone()
        return {"balance": row["balance"]}

    def update_game_state(self, balance):
        self.conn.execute("UPDATE game_state SET balance=? WHERE id=1", (balance,))
        self.conn.commit()


class FinanceEnterpriseTests(unittest.TestCase):
    def setUp(self):
        self.database = FakeDatabase()
        self.service = FinanceEnterpriseService(self.database)

    def test_sponsorship_payment_posts_to_finance_transactions(self):
        sponsor = self.service.create_sponsor(
            {
                "company_name": "Acme Corporation",
                "industry_category": "Technology",
                "tier_level": "Major Sponsor",
                "contact_email": "contact@acme.com",
            }
        )
        contract = self.service.create_contract(
            sponsor["sponsor_id"],
            {
                "contract_type": "Title Sponsorship",
                "duration_months": 24,
                "total_value": 5_000_000,
                "payment_schedule": "Quarterly",
            },
        )

        result = self.service.process_sponsorship_payment(contract["contract_id"], {"label": "Q1 Payment"})

        self.assertEqual(625_000, result["transaction"]["amount"])
        self.assertEqual("Sponsorship Revenue", result["transaction"]["category"])
        self.assertEqual(1_625_000, self.database.get_game_state()["balance"])

    def test_deliverables_and_controversy_update_relationship_state(self):
        sponsor = self.service.create_sponsor({"company_name": "Acme Corporation"})
        contract = self.service.create_contract(
            sponsor["sponsor_id"],
            {
                "requirements": [
                    {
                        "requirement_type": "TV Exposure",
                        "description": "Logo on ring apron",
                        "target_value": 10,
                        "unit": "seconds",
                        "cadence": "episode",
                    }
                ]
            },
        )
        requirement_id = contract["requirements"][0]["requirement_id"]

        progress = self.service.record_deliverable(
            requirement_id,
            {"event_name": "Monday Night Show", "delivered_value": 12},
        )
        controversy = self.service.record_controversy(
            sponsor["sponsor_id"],
            {
                "incident_type": "Social Media Controversy",
                "severity": "High",
                "description": "Offensive tweet posted",
            },
        )

        self.assertEqual(100.0, progress["compliance_pct"])
        self.assertEqual("Suspending", controversy["controversy"]["threat_level"])
        self.assertLess(controversy["sponsor"]["satisfaction_score"], sponsor["satisfaction_score"])

    def test_venue_upgrade_posts_capital_expenditure(self):
        result = self.service.purchase_upgrade(
            {
                "venue_id": "venue_msg",
                "upgrade_name": "LED Video Wall Installation",
                "upfront_cost": 500_000,
                "expected_revenue_increase": 50_000,
            }
        )

        self.assertEqual(10, result["upgrade"]["roi_events"])
        self.assertEqual(-500_000, result["transaction"]["amount"])
        self.assertEqual("Capital Expenditure", result["transaction"]["category"])

    def test_tour_event_settlement_posts_balanced_financials(self):
        tour = self.service.create_tour(
            {
                "tour_name": "Summer Tour 2024",
                "tour_type": "House Shows",
                "start_date": "2024-06-01",
                "end_date": "2024-08-31",
                "events": [
                    {"venue_id": "venue_msg", "event_name": "MSG", "event_type": "house_show", "event_date": "2024-06-05"},
                    {"venue_id": "venue_td_garden", "event_name": "Boston", "event_type": "house_show", "event_date": "2024-06-08"},
                    {"venue_id": "venue_wells_fargo", "event_name": "Philadelphia", "event_type": "house_show", "event_date": "2024-06-12"},
                ],
            }
        )
        event_id = tour["events"][0]["event_id"]

        settlement = self.service.settle_event(
            event_id,
            {
                "ticket_sales": 750_000,
                "merchandise_sales": 125_000,
                "concession_revenue": 25_000,
                "venue_rental": 150_000,
                "production_costs": 75_000,
                "talent_costs": 200_000,
                "travel_costs": 30_000,
                "marketing_costs": 20_000,
            },
        )
        transactions = self.service.list_transactions()

        self.assertEqual(900_000, settlement["revenue"])
        self.assertEqual(475_000, settlement["expenses"])
        self.assertEqual(425_000, settlement["profit"])
        self.assertEqual(6, len([tx for tx in transactions if tx["source_id"] == event_id]))


if __name__ == "__main__":
    unittest.main()
