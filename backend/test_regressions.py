import os
import sys
import unittest
import uuid
import importlib.util
import types

sys.path.insert(0, os.path.dirname(__file__))

from economy.contracts import ContractManager
from models.calendar import ScheduledShow
from models.championship import Championship
from models.contract import IncentiveType
from models.wrestler import Wrestler
from persistence.database import Database
from persistence.universe_db import DatabaseUniverseState


def _load_defense_frequency_status_builder():
    try:
        from routes.defense_frequency_routes import _build_status as build_status
        return build_status
    except ModuleNotFoundError as exc:
        if exc.name != "flask":
            raise

    class _Blueprint:
        def __init__(self, *args, **kwargs):
            pass

        def route(self, *args, **kwargs):
            return lambda func: func

    flask_stub = types.SimpleNamespace(
        Blueprint=_Blueprint,
        jsonify=lambda *args, **kwargs: args[0] if len(args) == 1 and not kwargs else {"args": args, "kwargs": kwargs},
        request=types.SimpleNamespace(args={}, get_json=lambda *args, **kwargs: {}),
        current_app=types.SimpleNamespace(config={}),
    )
    previous = sys.modules.get("flask")
    sys.modules["flask"] = flask_stub
    try:
        route_path = os.path.join(os.path.dirname(__file__), "routes", "defense_frequency_routes.py")
        spec = importlib.util.spec_from_file_location("_test_defense_frequency_routes", route_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module._build_status
    finally:
        if previous is None:
            sys.modules.pop("flask", None)
        else:
            sys.modules["flask"] = previous


_build_status = _load_defense_frequency_status_builder()


class _StubCalendar:
    def __init__(self, current_show, generated_shows):
        self._current_show = current_show
        self.generated_shows = generated_shows

    def get_current_show(self):
        return self._current_show

    def _get_ppv_for_week(self, week):
        return None


class _StubUniverse:
    def __init__(self, current_year, current_week, calendar):
        self.current_year = current_year
        self.current_week = current_week
        self.calendar = calendar


class RegressionTests(unittest.TestCase):
    def test_contract_manager_ignores_missing_weeks_remaining(self):
        contract_manager = ContractManager()

        missing_weeks = Wrestler(
            wrestler_id='w_missing',
            name='Missing Weeks',
            age=31,
            gender='Male',
            alignment='Face',
            role='Midcard',
            primary_brand='ROC Alpha',
            brawling=60,
            technical=60,
            speed=60,
            mic=60,
            psychology=60,
            stamina=60,
            years_experience=8,
        )
        missing_weeks.contract.weeks_remaining = None

        expiring = Wrestler(
            wrestler_id='w_expiring',
            name='Expiring Contract',
            age=29,
            gender='Male',
            alignment='Heel',
            role='Upper Midcard',
            primary_brand='ROC Alpha',
            brawling=70,
            technical=65,
            speed=72,
            mic=68,
            psychology=66,
            stamina=71,
            years_experience=6,
        )
        expiring.contract.weeks_remaining = 3

        expiring_contracts = contract_manager.get_expiring_contracts(
            [missing_weeks, expiring],
            weeks_threshold=4
        )

        self.assertEqual([expiring.id], [w.id for w in expiring_contracts])

    def test_contract_alert_generation_handles_weeks_remaining_edge_cases(self):
        contract_manager = ContractManager()

        monitored = Wrestler(
            wrestler_id='w_monitored',
            name='Monitored Deal',
            age=30,
            gender='Male',
            alignment='Heel',
            role='Upper Midcard',
            primary_brand='ROC Velocity',
            brawling=73,
            technical=69,
            speed=74,
            mic=71,
            psychology=72,
            stamina=75,
            years_experience=7,
        )
        monitored.contract.weeks_remaining = 6

        invalid_cases = [
            ('none', None),
            ('negative', -1),
        ]
        for label, invalid_weeks in invalid_cases:
            with self.subTest(case=label):
                edge_case = Wrestler(
                    wrestler_id=f'w_{label}_weeks',
                    name=f'Invalid Weeks {label}',
                    age=34,
                    gender='Male',
                    alignment='Face',
                    role='Midcard',
                    primary_brand='ROC Alpha',
                    brawling=62,
                    technical=58,
                    speed=61,
                    mic=57,
                    psychology=63,
                    stamina=60,
                    years_experience=9,
                )
                edge_case.contract.weeks_remaining = invalid_weeks

                alerts = contract_manager.generate_alerts_for_contracts(
                    [edge_case, monitored],
                    current_week=10,
                    current_year=2,
                )
                alert_ids = {alert.wrestler_id for alert in alerts}

                self.assertEqual({monitored.id}, alert_ids)
                self.assertEqual(1, len(alerts))

    def test_championship_defense_fields_persist(self):
        temp_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'test_tmp'))
        os.makedirs(temp_root, exist_ok=True)
        db_path = os.path.join(temp_root, f'{uuid.uuid4().hex}.db')
        database = None
        try:
            database = Database(db_path)

            championship = Championship(
                title_id='title_test',
                name='Test Championship',
                assigned_brand='ROC Alpha',
                title_type='World'
            )
            championship.defense_frequency_days = 21
            championship.min_annual_defenses = 18
            championship.last_defense_year = 2
            championship.last_defense_week = 12
            championship.last_defense_show_id = 'show_y2_w12_roc_alpha'
            championship.total_defenses = 7

            database.save_championship(championship)
            database.conn.commit()

            universe = DatabaseUniverseState(database)
            reloaded = universe.get_championship_by_id('title_test')

            self.assertIsNotNone(reloaded)
            self.assertEqual(reloaded.defense_frequency_days, 21)
            self.assertEqual(reloaded.min_annual_defenses, 18)
            self.assertEqual(reloaded.last_defense_year, 2)
            self.assertEqual(reloaded.last_defense_week, 12)
            self.assertEqual(reloaded.last_defense_show_id, 'show_y2_w12_roc_alpha')
            self.assertEqual(reloaded.total_defenses, 7)
        finally:
            if database is not None:
                database.close()
            if os.path.exists(db_path):
                os.remove(db_path)

    def test_day_level_defense_status_uses_show_days(self):
        last_show = ScheduledShow(
            show_id='show_y1_w1_roc_velocity',
            year=1,
            week=1,
            day_of_week='Friday',
            brand='ROC Velocity',
            name='ROC Velocity Weekly',
            show_type='weekly_tv',
            is_ppv=False,
            tier='weekly'
        )
        current_show = ScheduledShow(
            show_id='show_y1_w1_roc_vanguard',
            year=1,
            week=1,
            day_of_week='Saturday',
            brand='ROC Vanguard',
            name='ROC Vanguard Weekly',
            show_type='weekly_tv',
            is_ppv=False,
            tier='weekly'
        )

        championship = Championship(
            title_id='title_days',
            name='Day Counter Test',
            assigned_brand='ROC Velocity',
            title_type='Midcard'
        )
        championship.last_defense_year = 1
        championship.last_defense_week = 1
        championship.last_defense_show_id = last_show.show_id

        calendar = _StubCalendar(current_show=current_show, generated_shows=[last_show, current_show])
        universe = _StubUniverse(current_year=1, current_week=1, calendar=calendar)

        status = _build_status(championship, universe)

        self.assertEqual(status['days_since_defense'], 1)

    def test_load_contract_incentives_skips_invalid_rows(self):
        temp_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'test_tmp'))
        os.makedirs(temp_root, exist_ok=True)
        db_path = os.path.join(temp_root, f'{uuid.uuid4().hex}.db')
        database = None
        try:
            database = Database(db_path)
            cursor = database.conn.cursor()
            now = '2026-04-25T00:00:00'
            cursor.execute(
                '''
                INSERT INTO contract_incentives (
                    wrestler_id, incentive_type, description, value,
                    conditions, is_active, triggered_count, date_added, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                ('w_test', 'signing_bonus', 'Valid bonus', '10000', None, 1, 0, now, now)
            )
            cursor.execute(
                '''
                INSERT INTO contract_incentives (
                    wrestler_id, incentive_type, description, value,
                    conditions, is_active, triggered_count, date_added, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                ('w_test', 'not_a_real_type', 'Broken row', 'oops', '{bad json', 1, 0, now, now)
            )
            database.conn.commit()

            incentives = database.load_contract_incentives('w_test')

            self.assertEqual(1, len(incentives))
            self.assertEqual(IncentiveType.SIGNING_BONUS, incentives[0].incentive_type)
        finally:
            if database is not None:
                database.close()
            if os.path.exists(db_path):
                os.remove(db_path)


if __name__ == '__main__':
    unittest.main()
