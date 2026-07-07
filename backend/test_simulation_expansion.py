import os
import sys
import unittest
import uuid

sys.path.insert(0, os.path.dirname(__file__))

from persistence.database import Database
from services.simulation_expansion_service import SimulationExpansionService


class SimulationExpansionTests(unittest.TestCase):
    def setUp(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        tmp_dir = os.path.join(root, "test_tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        self.db_path = os.path.join(tmp_dir, f"simulation_expansion_{uuid.uuid4().hex}.db")
        self.database = Database(self.db_path)
        self.service = SimulationExpansionService(self.database)
        self._seed_wrestlers()

    def tearDown(self):
        if self.database is not None:
            self.database.close()
        for suffix in ("", "-wal", "-shm"):
            path = self.db_path + suffix
            if os.path.exists(path):
                os.remove(path)

    def _seed_wrestlers(self):
        now = "2026-05-06T00:00:00"
        rows = [
            ("w_alpha", "Alpha Ace", 34, "Male", "face", "main_event", "ROC Alpha", 78, 76, 72, 70, 82, 74, 12, 1, 84, 18, 62, 12, "None", None, 0, 220000, 104, 70, 1, 1, 0),
            ("w_beta", "Beta Brawler", 29, "Male", "heel", "upper_midcard", "ROC Alpha", 70, 60, 58, 54, 62, 66, 7, 0, 58, -8, 38, 20, "None", None, 0, 78000, 52, 8, 1, 1, 0),
            ("w_gamma", "Gamma Prospect", 23, "Female", "face", "prospect", "ROC Vanguard", 42, 45, 68, 48, 44, 61, 1, 0, 35, 4, 55, 5, "None", None, 0, 36000, 52, 45, 1, 1, 0),
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
                id, name, assigned_brand, title_type, prestige,
                current_holder_id, current_holder_name, created_at, updated_at
            ) VALUES ('title_world', 'ROC World Championship', 'ROC Alpha',
                'world', 90, 'w_alpha', 'Alpha Ace', ?, ?)
            """,
            (now, now),
        )
        self.database.conn.execute(
            """
            INSERT INTO match_history (
                match_id, show_id, show_name, year, week,
                side_a_ids, side_a_names, side_b_ids, side_b_names,
                winner, finish_type, duration_minutes, star_rating,
                is_title_match, title_id, title_changed_hands,
                is_upset, feud_id, match_summary, highlights, created_at
            ) VALUES (
                'm_1', 'show_1', 'Test Show', 1, 1,
                '["w_alpha"]', '["Alpha Ace"]', '["w_beta"]', '["Beta Brawler"]',
                'side_b', 'pinfall', 14, 3.5, 0, NULL, 0, 1, NULL,
                'Upset win', '[]', ?
            )
            """,
            (now,),
        )
        self.database.conn.commit()

    def test_weekly_locker_room_culture_persists_after_restart(self):
        result = self.service.run_weekly_culture(1, 2, seed=149)

        self.assertFalse(result["already_ran"])
        self.assertEqual(3, result["updated_wrestlers"])
        self.assertGreaterEqual(len(result["brands"]), 2)

        alpha = self.service.wrestler_culture_detail("w_alpha")
        self.assertGreater(len(alpha["morale_history"]), 0)
        self.assertIn("booking_satisfaction", alpha["state"]["last_primary_factors_json"])

        self.database.close()
        self.database = Database(self.db_path)
        restarted = SimulationExpansionService(self.database)
        dashboard = restarted.locker_dashboard()

        self.assertEqual(3, dashboard["summary"]["total_wrestlers"])
        self.assertGreaterEqual(len(dashboard["atmosphere"]), 2)
        rerun = restarted.run_weekly_culture(1, 2, seed=149)
        self.assertTrue(rerun["already_ran"])

    def test_meetings_and_discipline_have_mechanical_outputs(self):
        self.service.run_weekly_culture(1, 2, seed=150)
        before = self.service.wrestler_culture_detail("w_beta")["state"]["morale_score"]

        meeting = self.service.create_meeting(
            {
                "meeting_type": "one_on_one",
                "purpose": "morale_boost",
                "wrestler_id": "w_beta",
                "communication_skill": 85,
                "credibility": 80,
                "year": 1,
                "week": 2,
            }
        )
        after_meeting = self.service.wrestler_culture_detail("w_beta")["state"]["morale_score"]
        self.assertGreater(after_meeting, before)
        self.assertGreater(meeting["effectiveness_score"], 68)

        discipline = self.service.create_disciplinary_action(
            {
                "wrestler_id": "w_beta",
                "violation_type": "no_show",
                "action_type": "written_warning",
                "severity": 45,
                "justification": "Documented first serious attendance violation.",
                "year": 1,
                "week": 2,
            }
        )
        after_discipline = self.service.wrestler_culture_detail("w_beta")["state"]["morale_score"]
        self.assertLess(after_discipline, after_meeting)
        self.assertGreaterEqual(discipline["perceived_fairness"], 60)

    def test_developmental_pipeline_records_weekly_snapshots_and_readiness(self):
        trainer = self.service.create_trainer(
            {
                "trainer_name": "Coach Prime",
                "specialization": "technical",
                "coaching_skill": 82,
                "reputation": 74,
            }
        )
        curriculum = self.service.create_curriculum({"template_type": "raw_athlete"})
        trainee = self.service.add_trainee(
            {
                "wrestler_id": "w_gamma",
                "wrestler_name": "Gamma Prospect",
                "assigned_trainer_id": trainer["id"],
                "curriculum_id": curriculum["id"],
                "attributes": {"brawling": 42, "technical": 45, "speed": 68, "mic": 48, "psychology": 44, "stamina": 61},
                "year": 1,
                "week": 2,
            }
        )
        self.assertGreaterEqual(trainee["readiness_score"], 0)

        result = self.service.run_development_week(1, 3, seed=171)
        self.assertEqual(1, result["updated_trainees"])
        updated = self.service.repo.get_trainee("w_gamma")
        self.assertGreater(updated["readiness_score"], trainee["readiness_score"])

        self.database.close()
        self.database = Database(self.db_path)
        restarted = SimulationExpansionService(self.database)
        snapshots = restarted.repo.fetch_all("SELECT * FROM dev_progress_snapshots WHERE wrestler_id = ?", ("w_gamma",))
        self.assertEqual(1, len(snapshots))
        self.assertIn("technical", snapshots[0]["attributes_json"])

    def test_tryout_signing_creates_persistent_trainee_origin(self):
        tryout = self.service.schedule_tryout(
            {
                "location": "Dallas",
                "candidate_count": 3,
                "target_profile": "former_athlete",
                "seed": 176,
                "year": 1,
                "week": 4,
            }
        )
        self.assertEqual(3, len(tryout["candidates"]))
        signed = self.service.sign_tryout_candidate(tryout["candidates"][0]["id"], {"year": 1, "week": 4})
        self.assertEqual("active", signed["status"])

        persisted = self.service.repo.fetch_one(
            "SELECT * FROM dev_tryout_candidates WHERE signed_wrestler_id = ?",
            (signed["wrestler_id"],),
        )
        self.assertEqual("signed", persisted["decision_status"])

    def test_advanced_simulation_outputs_are_database_backed(self):
        script = self.service.create_match_script(
            {
                "show_id": "show_script",
                "match_id": "match_script",
                "feud_id": None,
                "script_quality": 78,
                "beats": [
                    {"phase": "opening", "description": "Technical feeling out", "required_skill": "technical", "difficulty": 62},
                    {"phase": "finish", "description": "Clean decisive finish", "required_skill": "psychology", "difficulty": 68},
                ],
            }
        )
        evaluated = self.service.evaluate_match_script(script["id"], {"participant_ids": ["w_alpha", "w_beta"], "crowd_investment": 72})
        self.assertIsNotNone(evaluated["execution_score"])
        self.assertGreater(evaluated["match_quality_modifier"], 0)

        attendance = self.service.project_attendance(
            {
                "show_id": "show_att",
                "show_name": "Attendance Test",
                "market_id": "market_chicago",
                "card_quality": 82,
                "marketing_spend": 50000,
                "simulate_actual": True,
                "seed": 248,
                "year": 1,
                "week": 5,
            }
        )
        self.assertGreater(attendance["projected_high"], attendance["projected_low"])
        self.assertIsNotNone(attendance["actual_attendance"])

        production = self.service.record_production_quality(
            {"show_id": "show_att", "brand": "ROC Alpha", "camera_score": 80, "audio_score": 75, "commentary_score": 78, "year": 1, "week": 5}
        )
        self.assertGreater(production["broadcast_score"], 74)

        endgame = self.service.update_endgame_progress(1, 5)
        self.assertGreaterEqual(len(endgame["objectives"]), 4)


if __name__ == "__main__":
    unittest.main()
