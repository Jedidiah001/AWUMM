import os
import sys
import unittest
import uuid
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(__file__))

from persistence.database import Database
from services.booking_story_media_service import BookingStoryMediaService


class BookingStoryMediaExpansionTests(unittest.TestCase):
    def setUp(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        tmp_dir = os.path.join(root, "test_tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        self.db_path = os.path.join(tmp_dir, f"phase_expansion_{uuid.uuid4().hex}.db")
        self.database = Database(self.db_path)
        self.service = BookingStoryMediaService(self.database)

    def tearDown(self):
        if self.database is not None:
            self.database.close()
        for suffix in ("", "-wal", "-shm"):
            path = self.db_path + suffix
            if os.path.exists(path):
                os.remove(path)

    def _show_draft(self, show_id="show_test_1", year=1, week=1):
        return {
            "show_id": show_id,
            "show_name": "ROC Test Broadcast",
            "brand": "ROC Alpha",
            "show_type": "weekly_tv",
            "year": year,
            "week": week,
            "total_runtime_minutes": 60,
            "matches": [
                {
                    "match_id": "match_open",
                    "match_type": "singles",
                    "card_position": 1,
                    "planned_duration_minutes": 8,
                    "side_a": {"wrestler_ids": ["w_alpha"]},
                    "side_b": {"wrestler_ids": ["w_beta"]},
                    "importance": "normal",
                },
                {
                    "match_id": "match_main",
                    "match_type": "singles",
                    "card_position": 99,
                    "planned_duration_minutes": 18,
                    "side_a": {"wrestler_ids": ["w_alpha"]},
                    "side_b": {"wrestler_ids": ["w_gamma"]},
                    "importance": "high_drama",
                    "is_title_match": True,
                    "title_id": "title_world",
                },
            ],
            "segments": [
                {
                    "segment_id": "promo_1",
                    "segment_type": "promo",
                    "card_position": 50,
                    "duration_minutes": 6,
                    "participants": [{"wrestler_id": "w_alpha"}],
                }
            ],
        }

    def test_show_plan_time_allocations_survive_database_restart(self):
        show_draft = self._show_draft()

        saved = self.service.save_show_plan(
            {
                "show_draft": show_draft,
                "accept_overrun": True,
                "commercial_breaks": [
                    {
                        "placement_type": "between_segments",
                        "strategy": "cliffhanger",
                        "minute_marker": 14,
                    }
                ],
            }
        )

        self.assertEqual(3, len(saved["segments"]))
        self.assertEqual(8, saved["segments"][0]["planned_duration_minutes"])
        self.assertGreater(saved["commercial_breaks"][0]["quality_score"], 55)

        self.database.close()
        self.database = Database(self.db_path)
        restarted_service = BookingStoryMediaService(self.database)
        restarted = restarted_service.repo.get_show_plan(show_draft["show_id"])

        self.assertIsNotNone(restarted)
        self.assertEqual("ROC Test Broadcast", restarted["show_name"])
        self.assertEqual([8, 6, 18], [segment["planned_duration_minutes"] for segment in restarted["segments"]])
        self.assertEqual("cliffhanger", restarted["commercial_breaks"][0]["strategy"])

    def test_interference_overuse_records_warning_and_degrades_impact(self):
        feud = self.service.create_story_feud(
            {
                "name": "Alpha vs Beta",
                "basis": "personal_grudge",
                "initial_heat": 70,
                "year": 1,
                "week": 1,
                "participants": [
                    {"participant_id": "w_alpha", "participant_name": "Alpha"},
                    {"participant_id": "w_beta", "participant_name": "Beta"},
                ],
            }
        )

        first = self.service.record_interference(
            {
                "show_id": "show_1",
                "match_id": "match_1",
                "feud_id": feud["id"],
                "interfering_wrestler_id": "w_alpha",
                "interfering_wrestler_name": "Alpha",
                "purpose": "attack_competitor",
                "year": 1,
                "week": 1,
            }
        )
        self.service.record_interference(
            {
                "show_id": "show_2",
                "match_id": "match_2",
                "feud_id": feud["id"],
                "interfering_wrestler_id": "w_alpha",
                "interfering_wrestler_name": "Alpha",
                "purpose": "distract_to_cause_loss",
                "year": 1,
                "week": 2,
            }
        )

        projection = self.service.project_interference(
            {
                "show_id": "show_3",
                "match_id": "match_3",
                "feud_id": feud["id"],
                "interfering_wrestler_id": "w_alpha",
                "purpose": "assist_in_win",
                "year": 1,
                "week": 3,
            }
        )

        self.assertTrue(projection["overuse_warning"])
        self.assertGreater(projection["credibility_penalty"], 0)
        self.assertLess(projection["impact_score"], first["impact_score"])

    def test_weekly_jobs_decay_heat_and_are_idempotent_for_internal_calendar_week(self):
        feud = self.service.create_story_feud(
            {
                "name": "Alpha vs Gamma",
                "basis": "championship_dispute",
                "initial_heat": 80,
                "year": 1,
                "week": 1,
                "participants": [
                    {"participant_id": "w_alpha", "participant_name": "Alpha"},
                    {"participant_id": "w_gamma", "participant_name": "Gamma"},
                ],
            }
        )

        first = self.service.run_weekly_jobs(1, 4)
        second = self.service.run_weekly_jobs(1, 4)
        updated_feud = self.service.repo.get_story_feud(feud["id"])

        self.assertEqual(1, first["heat_decay"]["updated"])
        self.assertTrue(second["already_ran"])
        self.assertLess(updated_feud["heat_score"], 80)

    def test_show_simulation_persists_ratings_demographics_and_business_effects(self):
        show_draft = self._show_draft("show_test_2", year=1, week=6)
        show_result = SimpleNamespace(
            overall_rating=3.9,
            match_results=[
                SimpleNamespace(
                    match_id="match_open",
                    duration_minutes=9,
                    star_rating=3.4,
                    crowd_energy=62,
                    is_title_match=False,
                    match_summary="Opener landed strongly",
                    finish_type=SimpleNamespace(value="clean_pin"),
                ),
                SimpleNamespace(
                    match_id="match_main",
                    duration_minutes=20,
                    star_rating=4.2,
                    crowd_energy=78,
                    is_title_match=True,
                    match_summary="Main event overdelivered",
                    finish_type=SimpleNamespace(value="clean_pin"),
                ),
            ],
            segment_results=[
                SimpleNamespace(
                    segment_id="promo_1",
                    duration_minutes=5,
                    segment_rating=3.6,
                    crowd_heat=70,
                )
            ],
        )

        result = self.service.process_show_result(show_draft, show_result)
        rating = self.service.repo.get_show_rating(show_draft["show_id"])
        network = self.service.repo.get_primary_network()
        social = self.service.repo.get_social_metrics()

        self.assertIn("media_business_result", show_result.__dict__)
        self.assertGreater(result["ratings"]["total_viewership"], 10000)
        self.assertIsNotNone(rating)
        self.assertGreaterEqual(len(rating["quarter_hours"]), 4)
        self.assertEqual(5, len(rating["demographics"]))
        self.assertGreater(network["relationship_score"], 0)
        self.assertGreaterEqual(len(social), 5)


if __name__ == "__main__":
    unittest.main()
