import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from economy.finance import FinanceCalculator
from models.contract import Contract
from models.match import MatchDraft, MatchParticipant
from models.show import ShowDraft
from models.wrestler import Wrestler


def _wrestler(wrestler_id, name, brand, salary, popularity=70):
    return Wrestler(
        wrestler_id=wrestler_id,
        name=name,
        age=30,
        gender='Male',
        alignment='Face',
        role='Main Event',
        primary_brand=brand,
        brawling=75,
        technical=72,
        speed=70,
        mic=78,
        psychology=76,
        stamina=74,
        years_experience=8,
        popularity=popularity,
        contract=Contract(
            salary_per_show=salary,
            total_length_weeks=52,
            weeks_remaining=52,
            signing_year=1,
            signing_week=1,
        ),
    )


def _match(match_id, a_id, b_id, is_title_match=False, feud_id=None, position=1):
    return MatchDraft(
        match_id=match_id,
        side_a=MatchParticipant(wrestler_ids=[a_id], wrestler_names=[a_id]),
        side_b=MatchParticipant(wrestler_ids=[b_id], wrestler_names=[b_id]),
        match_type='singles',
        is_title_match=is_title_match,
        card_position=position,
        feud_id=feud_id,
    )


class WeeklyTvEconomicsTests(unittest.TestCase):
    def setUp(self):
        self.calculator = FinanceCalculator()

    def test_alpha_weekly_projection_has_brand_specific_profit_floor(self):
        wrestlers = [
            _wrestler(f'w{i}', f'Worker {i}', 'ROC Alpha', 12000, popularity=72 + i)
            for i in range(1, 9)
        ]
        show_draft = ShowDraft(
            show_id='alpha_weekly',
            show_name='ROC Alpha',
            brand='ROC Alpha',
            show_type='weekly_tv',
            is_ppv=False,
            year=1,
            week=1,
            matches=[
                _match('m1', 'w1', 'w2', position=1),
                _match('m2', 'w3', 'w4', position=2),
                _match('m3', 'w5', 'w6', position=3),
                _match('m4', 'w7', 'w8', is_title_match=True, feud_id='feud_world', position=4),
            ],
        )

        projection = self.calculator.project_show_finances(
            show_draft,
            wrestlers,
            brand_prestige=78,
            current_balance=2000000,
            randomize=False,
        )

        self.assertEqual(100, projection['revenue_breakdown']['ticket_price'])
        self.assertGreaterEqual(projection['projected_attendance'], 12000)
        self.assertEqual(20000, projection['expense_breakdown']['production'])
        self.assertGreater(projection['revenue_breakdown']['guaranteed_media_revenue'], 0)
        self.assertGreater(projection['projected_net_profit'], 0)

    def test_vanguard_projection_warns_when_payroll_is_over_soft_cap(self):
        wrestlers = [
            _wrestler(f'v{i}', f'Vanguard {i}', 'ROC Vanguard', 28000, popularity=65 + i)
            for i in range(1, 7)
        ]
        show_draft = ShowDraft(
            show_id='vanguard_weekly',
            show_name='ROC Vanguard',
            brand='ROC Vanguard',
            show_type='weekly_tv',
            is_ppv=False,
            year=1,
            week=2,
            matches=[
                _match('m1', 'v1', 'v2', position=1),
                _match('m2', 'v3', 'v4', position=2),
                _match('m3', 'v5', 'v6', feud_id='development_feud', position=3),
            ],
        )

        projection = self.calculator.project_show_finances(
            show_draft,
            wrestlers,
            brand_prestige=60,
            current_balance=250000,
            randomize=False,
        )

        self.assertGreater(projection['expense_breakdown']['payroll_over_soft_cap'], 0)
        self.assertTrue(any('soft cap' in warning.lower() for warning in projection['warnings']))
        self.assertTrue(any('trim' in recommendation.lower() for recommendation in projection['recommendations']))

    def test_title_and_feud_main_event_raise_projection(self):
        wrestlers = [
            _wrestler(f'x{i}', f'Performer {i}', 'ROC Velocity', 10000, popularity=68 + i)
            for i in range(1, 9)
        ]
        base_show = ShowDraft(
            show_id='velocity_plain',
            show_name='ROC Velocity',
            brand='ROC Velocity',
            show_type='weekly_tv',
            is_ppv=False,
            year=1,
            week=3,
            matches=[
                _match('m1', 'x1', 'x2', position=1),
                _match('m2', 'x3', 'x4', position=2),
                _match('m3', 'x5', 'x6', position=3),
                _match('m4', 'x7', 'x8', position=4),
            ],
        )
        hot_show = ShowDraft.from_dict(base_show.to_dict())
        hot_show.matches[-1].is_title_match = True
        hot_show.matches[-1].feud_id = 'heated_feud'

        plain_projection = self.calculator.project_show_finances(base_show, wrestlers, 70, 500000, randomize=False)
        hot_projection = self.calculator.project_show_finances(hot_show, wrestlers, 70, 500000, randomize=False)

        self.assertGreater(hot_projection['projected_attendance'], plain_projection['projected_attendance'])
        self.assertGreater(hot_projection['projected_net_profit'], plain_projection['projected_net_profit'])


if __name__ == '__main__':
    unittest.main()
