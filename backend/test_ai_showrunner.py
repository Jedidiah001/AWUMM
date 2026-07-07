import os
import sys
import unittest
import uuid

sys.path.insert(0, os.path.dirname(__file__))

from persistence.database import Database
from services.ai_showrunner_service import AIShowrunnerService


class AIShowrunnerTests(unittest.TestCase):
    def setUp(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        tmp_dir = os.path.join(root, "test_tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        self.db_path = os.path.join(tmp_dir, f"ai_showrunner_{uuid.uuid4().hex}.db")
        self.database = Database(self.db_path)
        self.service = AIShowrunnerService(self.database)
        self._seed_wrestlers()

    def tearDown(self):
        if self.database is not None:
            self.database.close()
        for suffix in ("", "-wal", "-shm"):
            path = self.db_path + suffix
            if os.path.exists(path):
                os.remove(path)

    def _seed_wrestlers(self):
        now = "2026-06-30T00:00:00"
        rows = [
            ("w_alpha", "Alpha Ace", 34, "Male", "face", "main_event", "Cross-Brand", 82, 75, 68, 78, 84, 72, 12, 1, 86, 20, 70, 10, "None", None, 0, 250000, 104, 70, 1, 1, 0),
            ("w_beta", "Beta Brawler", 31, "Male", "heel", "upper_midcard", "Cross-Brand", 76, 64, 58, 62, 72, 68, 8, 0, 78, 12, 52, 18, "None", None, 0, 120000, 78, 30, 1, 1, 0),
            ("w_gamma", "Gamma Prospect", 24, "Female", "face", "midcard", "Cross-Brand", 58, 61, 74, 55, 60, 72, 3, 0, 63, 8, 48, 12, "None", None, 0, 70000, 52, 44, 1, 1, 0),
            ("w_delta", "Delta Storm", 28, "Female", "heel", "midcard", "Cross-Brand", 67, 69, 77, 64, 65, 70, 5, 0, 69, 15, 62, 9, "None", None, 0, 90000, 52, 40, 1, 1, 0),
            ("w_echo", "Echo Knight", 39, "Male", "face", "veteran", "Cross-Brand", 71, 82, 51, 75, 86, 64, 17, 1, 81, 10, 58, 15, "None", None, 0, 180000, 104, 62, 1, 1, 0),
        ]
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
            [row + (now, now) for row in rows],
        )
        self.database.conn.commit()

    def test_weekly_showrunner_persists_card_roadmap_and_approvals(self):
        result = self.service.run_weekly(1, 9, seed=77, force=True, autonomy_level="balanced")

        self.assertFalse(result["already_ran"])
        self.assertGreaterEqual(len(result["card"]["segments"]), 7)
        self.assertGreaterEqual(len(result["approvals_created"]), 3)
        self.assertGreaterEqual(len(result["roadmaps"]), 1)
        self.assertIn("angle_execution", result["special_systems"])
        self.assertGreaterEqual(len(result["special_systems"]["mitb"]["briefcases"]), 1)
        self.assertTrue(result["special_systems"]["war_games"]["id"])
        self.assertGreaterEqual(len(result["special_systems"]["crown_payoffs"]), 1)
        self.assertGreaterEqual(result["special_systems"]["dark_house_autopilot"]["total"], 2)
        self.assertGreaterEqual(len(result["special_systems"]["promo_beats"]), 1)

        saved_plan = self.service.repo.get_show_plan(result["show"]["show_id"])
        self.assertIsNotNone(saved_plan)
        self.assertGreaterEqual(len(saved_plan["segments"]), 7)

        self.database.close()
        self.database = Database(self.db_path)
        restarted = AIShowrunnerService(self.database)
        dashboard = restarted.dashboard()

        self.assertGreaterEqual(dashboard["summary"]["pending_approvals"], 3)
        self.assertGreaterEqual(dashboard["summary"]["active_roadmaps"], 1)
        self.assertGreaterEqual(dashboard["summary"]["angle_templates"], 12)
        self.assertGreaterEqual(dashboard["summary"]["active_mitb"], 1)
        self.assertGreaterEqual(dashboard["summary"]["active_war_games"], 1)
        self.assertGreaterEqual(dashboard["summary"]["crown_payoffs"], 1)
        self.assertGreaterEqual(dashboard["summary"]["dark_house_runs"], 2)
        self.assertGreaterEqual(dashboard["summary"]["promo_beats"], 1)
        self.assertEqual("drafted", dashboard["summary"]["last_run_status"])

        categories = {item["category"] for item in dashboard["pending_approvals"]}
        self.assertIn("angle_library", categories)
        self.assertIn("money_in_bank_setup", categories)
        self.assertIn("war_games", categories)
        self.assertIn("crown_tournament", categories)
        self.assertIn("dark_house_autopilot", categories)
        self.assertIn("promo_dialogue", categories)

    def test_approving_war_games_materializes_factions(self):
        self.service.run_weekly(1, 9, seed=77, force=True, autonomy_level="balanced")
        dashboard = self.service.dashboard()
        war_games_item = next(item for item in dashboard["pending_approvals"] if item["category"] == "war_games")

        before = self.database.get_all_factions(active_only=True)
        self.service.decide_approval(war_games_item["id"], {"decision": "approve", "notes": "Lock the teams."})
        after = self.database.get_all_factions(active_only=True)

        self.assertGreaterEqual(len(after), len(before) + 1)
        names = {faction["faction_name"] for faction in after}
        self.assertTrue(any(name.endswith("Team A") for name in names))
        self.assertTrue(any("Team" in name for name in names))

    def test_approval_decision_and_aggressive_auto_execute(self):
        result = self.service.run_weekly(1, 10, seed=88, force=True, autonomy_level="aggressive")

        self.assertGreaterEqual(len(result["auto_executed"]), 1)
        dashboard = self.service.dashboard()
        pending = dashboard["pending_approvals"][0]
        decided = self.service.decide_approval(pending["id"], {"decision": "counter", "counter_pitch": "Keep the beat, change the winner."})

        self.assertEqual("countered", decided["status"])
        self.assertEqual("Keep the beat, change the winner.", decided["player_response_json"]["counter_pitch"])

        latest = self.service.latest_booking_draft()
        original_segment_count = len(latest["show_draft"]["segments"])
        live = self.service.maybe_live_interruption(latest["show_draft"], seed=5, force=True)
        self.assertTrue(live["inserted"])
        self.assertGreater(len(live["show_draft"]["segments"]), original_segment_count)

        beats = self.service.generate_promo_beats(1, 10, show_draft=latest["show_draft"], seed=7, force=True)
        self.assertGreaterEqual(beats["total"], 1)

        dark = self.service.run_dark_house_autopilot(1, 11, seed=9, force=True)
        self.assertGreaterEqual(dark["total"], 2)


if __name__ == "__main__":
    unittest.main()
