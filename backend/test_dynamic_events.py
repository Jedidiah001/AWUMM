import os
import sys
import unittest
import uuid

sys.path.insert(0, os.path.dirname(__file__))

from persistence.database import Database
from services.simulation_expansion_service import SimulationExpansionService


class DynamicEventSystemTests(unittest.TestCase):
    def setUp(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        tmp_dir = os.path.join(root, "test_tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        self.db_path = os.path.join(tmp_dir, f"dynamic_events_{uuid.uuid4().hex}.db")
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
        now = "2026-06-21T00:00:00"
        rows = [
            (
                "w_star",
                "Star Catalyst",
                39,
                "Male",
                "face",
                "main_event",
                "ROC Alpha",
                82,
                79,
                71,
                86,
                84,
                73,
                18,
                1,
                91,
                30,
                42,
                48,
                "None",
                None,
                0,
                275000,
                104,
                8,
                1,
                1,
                0,
            ),
            (
                "w_rival",
                "Rival Pressure",
                31,
                "Female",
                "heel",
                "upper_midcard",
                "ROC Alpha",
                70,
                68,
                75,
                71,
                74,
                69,
                9,
                0,
                77,
                12,
                58,
                18,
                "None",
                None,
                0,
                120000,
                78,
                40,
                1,
                1,
                0,
            ),
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
            INSERT INTO match_history (
                match_id, show_id, show_name, year, week,
                side_a_ids, side_a_names, side_b_ids, side_b_names,
                winner, finish_type, duration_minutes, star_rating,
                is_title_match, title_id, title_changed_hands,
                is_upset, feud_id, match_summary, highlights, created_at
            ) VALUES (
                'dyn_match_1', 'dyn_show_1', 'Dynamic Test Show', 1, 1,
                '["w_star"]', '["Star Catalyst"]', '["w_rival"]', '["Rival Pressure"]',
                'side_a', 'pinfall', 18, 4.0, 0, NULL, 0, 0, NULL,
                'Test main event', '[]', ?
            )
            """,
            (now,),
        )
        self.database.conn.commit()

    def test_dynamic_event_audit_records_existing_feature_overlap(self):
        audit = self.service.sync_dynamic_event_audit()

        self.assertEqual(16, len(audit))
        statuses = {row["feature_key"]: row["overlap_status"] for row in audit}
        self.assertEqual("partial", statuses["match_injury_rebooking"])
        self.assertEqual("exists", statuses["power_clique"])
        self.assertEqual("missing", statuses["storyline_leak"])

    def test_forced_dynamic_event_persists_after_restart(self):
        result = self.service.run_dynamic_events(
            1,
            2,
            seed=250,
            data={"event_type": "storyline_leak", "force": True, "wrestler_id": "w_star"},
        )

        self.assertFalse(result["already_ran"])
        self.assertEqual(1, result["created"])
        event = result["events"][0]
        self.assertEqual("storyline_leak", event["event_type"])
        self.assertEqual("open", event["status"])
        self.assertGreaterEqual(len(event["response_options_json"]), 3)

        self.database.close()
        self.database = Database(self.db_path)
        restarted = SimulationExpansionService(self.database)
        dashboard = restarted.dynamic_event_dashboard()

        persisted = [row for row in dashboard["open_events"] if row["id"] == event["id"]]
        self.assertEqual(1, len(persisted))
        self.assertEqual("storyline_leak", persisted[0]["event_type"])

    def test_resolution_applies_mechanical_effects_and_impacts(self):
        result = self.service.run_dynamic_events(
            1,
            3,
            seed=251,
            data={"event_type": "viral_social_moment", "force": True, "wrestler_id": "w_star"},
        )
        event = result["events"][0]
        before = self.service.repo.get_wrestler("w_star")

        resolved = self.service.resolve_dynamic_event(event["id"], {"choice": "amplify"})
        after = self.service.repo.get_wrestler("w_star")

        self.assertEqual("resolved", resolved["event"]["status"])
        self.assertEqual("amplify", resolved["event"]["selected_response"])
        self.assertGreater(after["popularity"], before["popularity"])
        self.assertGreater(after["momentum"], before["momentum"])
        self.assertGreaterEqual(len(resolved["impacts"]), 3)

    def test_weekly_dynamic_events_are_idempotent_without_force(self):
        first = self.service.run_dynamic_events(1, 4, seed=252, data={"guarantee_event": True})
        second = self.service.run_dynamic_events(1, 4, seed=252, data={"guarantee_event": True})

        self.assertFalse(first["already_ran"])
        self.assertTrue(second["already_ran"])
        self.assertEqual(first["created"], second["created"])

    def test_dynamic_event_pulse_can_force_global_surprise(self):
        pulse = self.service.dynamic_event_pulse(
            {
                "year": 1,
                "week": 5,
                "context": "show_simulation",
                "origin": "show_simulation",
                "force": True,
                "event_type": "wrestler_no_show",
                "show_id": "pulse_show",
                "show_name": "Pulse Test Show",
                "brand": "ROC Alpha",
                "seed": 253,
            }
        )

        self.assertTrue(pulse["triggered"])
        self.assertEqual(1, len(pulse["events"]))
        event = pulse["events"][0]
        self.assertEqual("wrestler_no_show", event["event_type"])
        self.assertEqual("pulse_show", event["show_id"])
        self.assertEqual("show_simulation", event["payload_json"]["pulse_context"])

    def test_dynamic_event_pulse_surfaces_existing_open_events_without_spam(self):
        first = self.service.dynamic_event_pulse(
            {
                "year": 1,
                "week": 6,
                "context": "global",
                "force": True,
                "event_type": "storyline_leak",
                "seed": 254,
            }
        )
        second = self.service.dynamic_event_pulse(
            {
                "year": 1,
                "week": 6,
                "context": "global",
                "chance": 1,
                "seed": 255,
            }
        )

        self.assertTrue(first["triggered"])
        self.assertFalse(second["triggered"])
        self.assertEqual("open_events_pending", second["reason"])
        self.assertGreaterEqual(len(second["open_events"]), 1)


if __name__ == "__main__":
    unittest.main()
