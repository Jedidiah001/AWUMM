import os
import sys
import unittest
import uuid

sys.path.insert(0, os.path.dirname(__file__))

from persistence.database import Database
from services.post_show_fallout_service import PostShowFalloutService


class PostShowFalloutTests(unittest.TestCase):
    def setUp(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        tmp_dir = os.path.join(root, "test_tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        self.db_path = os.path.join(tmp_dir, f"post_show_fallout_{uuid.uuid4().hex}.db")
        self.database = Database(self.db_path)
        self.service = PostShowFalloutService(self.database)
        self._seed_world()

    def tearDown(self):
        if self.database is not None:
            self.database.close()
        for suffix in ("", "-wal", "-shm"):
            path = self.db_path + suffix
            if os.path.exists(path):
                os.remove(path)

    def _seed_world(self):
        now = "2026-07-03T00:00:00"
        rows = [
            ("w_ace", "Ace Morgan", 34, "Male", "face", "main_event", "ROC Alpha", 80, 75, 70, 82, 85, 78, 14, 1, 90, 70, 62, 8, "None", None, 0, 250000, 104, 50, 1, 1, 0),
            ("w_riot", "Blake Riot", 32, "Male", "heel", "main_event", "ROC Alpha", 84, 68, 61, 74, 76, 72, 11, 1, 84, 66, 38, 12, "None", None, 0, 210000, 104, 8, 1, 1, 0),
            ("w_nova", "Nova Vale", 27, "Female", "face", "midcard", "ROC Alpha", 62, 72, 88, 66, 70, 80, 6, 0, 68, 55, 74, 6, "None", None, 0, 90000, 52, 32, 1, 1, 0),
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
        self.database.conn.execute(
            """
            INSERT OR REPLACE INTO championships (
                id, name, assigned_brand, title_type, prestige, current_holder_id,
                current_holder_name, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("t_world", "World Championship", "ROC Alpha", "world", 88, "w_ace", "Ace Morgan", now, now),
        )
        self.database.conn.commit()

    def test_post_show_fallout_persists_approvals_and_effects(self):
        show_draft = {
            "show_id": "fallout_show",
            "show_name": "Fallout Test",
            "brand": "ROC Alpha",
            "show_type": "weekly_tv",
            "year": 1,
            "week": 12,
        }
        show_result = {
            **show_draft,
            "overall_rating": 4.35,
            "events": [{"type": "live_interruption", "description": "A live interruption changed the show."}],
            "match_results": [
                {
                    "match_id": "m1",
                    "winner_names": ["Ace Morgan"],
                    "loser_names": ["Blake Riot"],
                    "star_rating": 4.6,
                    "crowd_energy": 92,
                    "is_title_match": True,
                    "title_name": "World Championship",
                    "title_changed_hands": False,
                    "finish_type": "clean_pin",
                    "card_position": 5,
                }
            ],
            "segment_results": [],
        }

        result = self.service.generate_for_show(show_draft, show_result, seed=3, force=True)
        report = result["report"]

        self.assertGreaterEqual(len(report["items"]), 4)
        self.assertGreaterEqual(len(report["open_actions"]), 1)
        self.assertGreaterEqual(len(report["urgent_items"]), 1)
        self.assertGreaterEqual(
            self.database.conn.execute("SELECT COUNT(*) FROM booker_approval_queue").fetchone()[0],
            1,
        )

        restarted = PostShowFalloutService(self.database)
        persisted = restarted.get_latest("fallout_show", 1, 12)["report"]
        self.assertEqual(report["id"], persisted["id"])
        self.assertEqual(len(report["items"]), len(persisted["items"]))

        first_action = persisted["open_actions"][0]
        decided = restarted.decide_item(first_action["id"], {"decision": "approve", "notes": "Use it next week."})
        self.assertEqual("approved", decided["status"])

        handled = restarted.auto_handle_report(report["id"])
        self.assertGreaterEqual(handled["resolved"], 1)


if __name__ == "__main__":
    unittest.main()
