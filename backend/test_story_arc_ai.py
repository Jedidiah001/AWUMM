import os
import sys
import unittest
import uuid
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(__file__))

from persistence.database import Database
from services.booking_story_media_service import BookingStoryMediaService
from services.simulation_expansion_service import SimulationExpansionService


class StoryArcAITests(unittest.TestCase):
    def setUp(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        tmp_dir = os.path.join(root, "test_tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        self.db_path = os.path.join(tmp_dir, f"story_arc_ai_{uuid.uuid4().hex}.db")
        self.database = Database(self.db_path)
        self.story_service = BookingStoryMediaService(self.database)
        self.sim_service = SimulationExpansionService(self.database)
        self._seed_wrestlers()

    def tearDown(self):
        if self.database is not None:
            self.database.close()
        for suffix in ("", "-wal", "-shm"):
            path = self.db_path + suffix
            if os.path.exists(path):
                os.remove(path)

    def _seed_wrestlers(self):
        now = "2026-06-21T00:00:00"
        rows = [
            ("w_alpha", "Alpha Ace", 34, "Male", "face", "main_event", "ROC Alpha", 80, 76, 72, 70, 84, 74, 12, 1, 86, 20, 68, 10, "None", None, 0, 250000, 104, 70, 1, 1, 0),
            ("w_beta", "Beta Brawler", 31, "Male", "heel", "upper_midcard", "ROC Alpha", 74, 65, 58, 57, 66, 67, 8, 0, 78, 12, 52, 18, "None", None, 0, 120000, 78, 30, 1, 1, 0),
            ("w_gamma", "Gamma Prospect", 24, "Female", "face", "midcard", "ROC Vanguard", 58, 61, 70, 55, 60, 72, 3, 0, 63, 8, 61, 12, "None", None, 0, 70000, 52, 44, 1, 1, 0),
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

    def test_foundation_seed_persists_after_restart(self):
        result = self.story_service.ensure_story_arc_foundation(1)

        self.assertGreaterEqual(result["templates"], 12)
        self.assertGreaterEqual(result["calendar_events"], 9)
        self.assertGreaterEqual(result["vision_goals"], 9)

        self.database.close()
        self.database = Database(self.db_path)
        restarted = BookingStoryMediaService(self.database)
        dashboard = restarted.story_arc_ai_dashboard()

        self.assertGreaterEqual(dashboard["summary"]["next_calendar_events"], 9)
        self.assertEqual(0, dashboard["summary"]["active_arcs"])

    def test_weekly_ai_drafts_review_and_approval_persists(self):
        result = self.story_service.run_story_arc_ai_week(1, 1, seed=245, force=True)

        self.assertEqual(1, result["drafted"]["created"])
        reviews = self.story_service.pending_story_arc_reviews()
        self.assertTrue(any(review["review_type"] == "new_arc_approval" for review in reviews))

        review = next(review for review in reviews if review["review_type"] == "new_arc_approval")
        decided = self.story_service.decide_story_arc_review(
            review["id"],
            {"decision": "approve", "selected_option": "approve", "notes": "Test approval"},
        )
        self.assertEqual("approved", decided["status"])

        self.database.close()
        self.database = Database(self.db_path)
        restarted = BookingStoryMediaService(self.database)
        dashboard = restarted.story_arc_ai_dashboard()

        self.assertEqual(1, dashboard["summary"]["active_arcs"])
        self.assertEqual(0, len([r for r in dashboard["pending_reviews"] if r["id"] == review["id"]]))

    def test_dynamic_event_creates_story_rebooking_review(self):
        self.story_service.run_story_arc_ai_week(1, 1, seed=246, force=True)
        review = next(r for r in self.story_service.pending_story_arc_reviews() if r["review_type"] == "new_arc_approval")
        self.story_service.decide_story_arc_review(review["id"], {"decision": "approve", "selected_option": "approve"})

        result = self.sim_service.run_dynamic_events(
            1,
            2,
            seed=247,
            data={"force": True, "event_type": "wrestler_no_show", "max_events": 1, "guarantee_event": True},
        )

        self.assertEqual(1, result["created"])
        self.assertGreaterEqual(len(result["story_reviews"]), 1)
        pending = self.story_service.pending_story_arc_reviews(20)
        self.assertTrue(any(review["source_type"] == "dynamic_event" for review in pending))

    def test_show_result_completes_due_story_milestone(self):
        self.story_service.run_story_arc_ai_week(1, 1, seed=248, force=True)
        show_draft = {"show_id": "show_story_ai", "year": 1, "week": 1}
        show_result = SimpleNamespace(
            match_results=[SimpleNamespace(star_rating=4.0)],
            segment_results=[SimpleNamespace(segment_rating=3.5)],
        )

        result = self.story_service.process_story_arc_show_result(show_draft, show_result)

        self.assertGreaterEqual(result["count"], 1)
        completed = self.story_service.repo.fetch_all(
            "SELECT * FROM story_arc_milestones WHERE status = 'completed' AND deleted_at IS NULL"
        )
        self.assertGreaterEqual(len(completed), 1)
        self.assertGreaterEqual(completed[0]["success_score"], 60)


if __name__ == "__main__":
    unittest.main()
