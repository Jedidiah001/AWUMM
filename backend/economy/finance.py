"""
Finance System
Calculates attendance, revenue, expenses, and profit for shows.
"""

import random
from typing import Any, Dict, List

from models.show import ShowDraft


class FinanceCalculator:
    """Handles show economics and pre-show profitability projections."""

    TICKET_PRICES = {
        'weekly_tv': 100,
        'minor_ppv': 75,
        'major_ppv': 150,
    }

    BASE_ATTENDANCE = {
        'weekly_tv': (12000, 20000),
        'minor_ppv': (5000, 8000),
        'major_ppv': (12000, 18000),
    }

    PRODUCTION_COSTS = {
        'weekly_tv': 18000,
        'minor_ppv': 150000,
        'major_ppv': 500000,
    }

    WEEKLY_TV_BRAND_PROFILES = {
        'ROC Alpha': {
            'attendance_range': (12000, 20000),
            'production_cost': 20000,
            'venue_cost': 18000,
            'tv_rights': 95000,
            'sponsor_revenue': 40000,
            'streaming_floor': 12000,
            'recap_revenue': 18000,
            'local_sponsorship': 22000,
            'merch_per_attendee': 6.5,
            'salary_soft_cap': 190000,
            'ideal_roster_size': 10,
        },
        'ROC Velocity': {
            'attendance_range': (12000, 20000),
            'production_cost': 18000,
            'venue_cost': 18000,
            'tv_rights': 80000,
            'sponsor_revenue': 30000,
            'streaming_floor': 8000,
            'recap_revenue': 12000,
            'local_sponsorship': 16000,
            'merch_per_attendee': 5.5,
            'salary_soft_cap': 165000,
            'ideal_roster_size': 10,
        },
        'ROC Vanguard': {
            'attendance_range': (9000, 12000),
            'production_cost': 15000,
            'venue_cost': 12000,
            'tv_rights': 55000,
            'sponsor_revenue': 18000,
            'streaming_floor': 6000,
            'recap_revenue': 9000,
            'local_sponsorship': 9000,
            'merch_per_attendee': 4.5,
            'salary_soft_cap': 120000,
            'ideal_roster_size': 8,
        },
    }

    def _venue_override(self, show_draft: ShowDraft) -> Dict[str, Any]:
        venue_override = getattr(show_draft, 'venue_override', None) or {}
        return venue_override if isinstance(venue_override, dict) else {}

    def _show_profile(self, show_draft: ShowDraft) -> Dict[str, Any]:
        if show_draft.show_type != 'weekly_tv':
            profile = {
                'attendance_range': self.BASE_ATTENDANCE.get(show_draft.show_type, (2000, 4000)),
                'ticket_price': self.TICKET_PRICES.get(show_draft.show_type, 35),
                'production_cost': self.PRODUCTION_COSTS.get(show_draft.show_type, 50000),
                'venue_cost': 0,
                'tv_rights': 0,
                'sponsor_revenue': 0,
                'streaming_floor': 0,
                'recap_revenue': 0,
                'local_sponsorship': 0,
                'merch_per_attendee': 2.0,
                'salary_soft_cap': 999999999,
                'ideal_roster_size': 12,
            }
        else:
            brand_profile = self.WEEKLY_TV_BRAND_PROFILES.get(
                show_draft.brand,
                self.WEEKLY_TV_BRAND_PROFILES['ROC Velocity'],
            )
            profile = {
                **brand_profile,
                'ticket_price': self.TICKET_PRICES['weekly_tv'],
            }

        venue_override = self._venue_override(show_draft)
        if venue_override.get('venue_cost') is not None:
            profile['venue_cost'] = int(venue_override.get('venue_cost') or 0)
        return profile

    def _main_event_multiplier(self, show_draft: ShowDraft) -> float:
        if not show_draft.matches:
            return 1.0

        main_event = show_draft.matches[-1]
        multiplier = 1.0
        if main_event.is_title_match:
            multiplier *= 1.45
        if main_event.feud_id:
            multiplier *= 1.28
        return multiplier

    def _card_focus_multiplier(self, show_draft: ShowDraft, roster_size: int, ideal_roster_size: int) -> float:
        total_items = len(show_draft.matches) + len(show_draft.segments or [])
        multiplier = 1.0

        if roster_size <= ideal_roster_size and 3 <= len(show_draft.matches) <= 5 and total_items <= 9:
            multiplier *= 1.08
        if roster_size > ideal_roster_size:
            penalty_steps = roster_size - ideal_roster_size
            multiplier *= max(0.82, 1.0 - (penalty_steps * 0.025))
        if total_items >= 11:
            multiplier *= 0.94
        if len(show_draft.matches) >= 7:
            multiplier *= 0.96

        return multiplier

    def _star_power(self, wrestlers_on_card: List[Any]) -> float:
        if not wrestlers_on_card:
            return 55.0

        popularity_scores = sorted(
            [float(getattr(wrestler, 'popularity', 55) or 55) for wrestler in wrestlers_on_card],
            reverse=True,
        )
        sample = popularity_scores[:4]
        return sum(sample) / max(len(sample), 1)

    def _attendance_projection(
        self,
        show_draft: ShowDraft,
        brand_prestige: int,
        current_balance: int,
        wrestlers_on_card: List[Any],
        randomize: bool,
    ) -> Dict[str, Any]:
        profile = self._show_profile(show_draft)
        venue_override = self._venue_override(show_draft)
        forced_capacity = venue_override.get('venue_capacity')
        if forced_capacity:
            forced_attendance = max(500, int(forced_capacity))
            return {
                'attendance': forced_attendance,
                'main_event_multiplier': round(self._main_event_multiplier(show_draft), 3),
                'focus_multiplier': round(
                    self._card_focus_multiplier(show_draft, len(wrestlers_on_card), profile['ideal_roster_size']),
                    3,
                ),
                'star_power': round(self._star_power(wrestlers_on_card), 1),
            }

        min_attendance, max_attendance = profile['attendance_range']
        base_attendance = random.randint(min_attendance, max_attendance) if randomize else int((min_attendance + max_attendance) / 2)

        prestige_modifier = 1.0 + (((brand_prestige - 50) / 50) * 0.12)
        star_power = self._star_power(wrestlers_on_card)
        star_modifier = 1.0 + max(-0.08, min(0.18, (star_power - 60) / 250))

        roster_size = len(wrestlers_on_card)
        focus_multiplier = self._card_focus_multiplier(show_draft, roster_size, profile['ideal_roster_size'])
        main_event_multiplier = self._main_event_multiplier(show_draft)

        financial_modifier = 1.0
        if current_balance < 0:
            financial_modifier = 0.90
        elif current_balance > 5000000:
            financial_modifier = 1.05

        variance = random.uniform(0.94, 1.06) if randomize else 1.0
        attendance = int(
            base_attendance
            * prestige_modifier
            * star_modifier
            * focus_multiplier
            * main_event_multiplier
            * financial_modifier
            * variance
        )

        return {
            'attendance': max(500, attendance),
            'main_event_multiplier': round(main_event_multiplier, 3),
            'focus_multiplier': round(focus_multiplier, 3),
            'star_power': round(star_power, 1),
        }

    def _revenue_breakdown(
        self,
        show_draft: ShowDraft,
        attendance: int,
        star_power: float,
        focus_multiplier: float,
    ) -> Dict[str, int]:
        profile = self._show_profile(show_draft)
        gate_revenue = attendance * profile['ticket_price']

        if show_draft.show_type == 'weekly_tv':
            guaranteed_media_revenue = (
                profile['tv_rights']
                + profile['sponsor_revenue']
                + profile['streaming_floor']
                + profile['recap_revenue']
            )
            merchandise_revenue = int(attendance * profile['merch_per_attendee'] * (0.92 + (star_power / 500)))
            local_sponsorship_revenue = int(profile['local_sponsorship'] * max(0.9, focus_multiplier))
            ppv_revenue = 0
        else:
            guaranteed_media_revenue = 0
            merchandise_revenue = int(attendance * profile['merch_per_attendee'])
            local_sponsorship_revenue = 0
            ppv_revenue = 0
            if show_draft.is_ppv and show_draft.show_type == 'major_ppv':
                ppv_buys = int(attendance * random.uniform(0.10, 0.30))
                ppv_revenue = int(ppv_buys * 49.99)

        total_revenue = gate_revenue + ppv_revenue + guaranteed_media_revenue + merchandise_revenue + local_sponsorship_revenue
        return {
            'ticket_price': profile['ticket_price'],
            'gate_revenue': gate_revenue,
            'ppv_revenue': ppv_revenue,
            'guaranteed_media_revenue': guaranteed_media_revenue,
            'merchandise_revenue': merchandise_revenue,
            'local_sponsorship_revenue': local_sponsorship_revenue,
            'total_revenue': total_revenue,
        }

    def calculate_payroll(self, wrestlers_on_card: List[Any]) -> int:
        return sum(getattr(getattr(wrestler, 'contract', None), 'salary_per_show', 0) or 0 for wrestler in wrestlers_on_card)

    def _expense_breakdown(self, show_draft: ShowDraft, payroll: int, roster_size: int) -> Dict[str, int]:
        profile = self._show_profile(show_draft)
        salary_soft_cap = profile['salary_soft_cap']
        payroll_overage = max(0, payroll - salary_soft_cap)
        overstack_fee = int(payroll_overage * 0.10) if show_draft.show_type == 'weekly_tv' else 0
        total_expenses = payroll + profile['production_cost'] + profile['venue_cost'] + overstack_fee

        return {
            'payroll': payroll,
            'production': profile['production_cost'],
            'venue': profile['venue_cost'],
            'overstack_fee': overstack_fee,
            'salary_soft_cap': salary_soft_cap,
            'payroll_over_soft_cap': payroll_overage,
            'roster_size': roster_size,
            'ideal_roster_size': profile['ideal_roster_size'],
            'total_expenses': total_expenses,
        }

    def _warnings_and_recommendations(
        self,
        show_draft: ShowDraft,
        projection: Dict[str, Any],
    ) -> Dict[str, List[str]]:
        warnings: List[str] = []
        recommendations: List[str] = []
        expenses = projection['expense_breakdown']

        if expenses['payroll_over_soft_cap'] > 0:
            warnings.append(
                f"Booked payroll is ${expenses['payroll_over_soft_cap']:,} over the soft cap for {show_draft.brand}."
            )
            recommendations.append('Trim one expensive appearance or shift a top salary to a PPV or special episode.')

        if expenses['roster_size'] > expenses['ideal_roster_size']:
            warnings.append('The card is overcrowded, so extra appearances are producing weaker returns at the gate.')
            recommendations.append('Aim for one hot main event, 3-5 matches, and a tighter supporting cast.')

        if show_draft.matches and not (show_draft.matches[-1].is_title_match or show_draft.matches[-1].feud_id):
            recommendations.append('Put a title match or a live feud in the main event to unlock the bigger attendance bonus.')

        if projection['projected_net_profit'] < 0:
            warnings.append('This card is currently projected to lose money.')
            recommendations.append('Lower payroll, tighten the card, or center the episode around a stronger main-event hook.')

        if not recommendations:
            recommendations.append('This card is in a healthy range. Protect the main event and avoid unnecessary extra appearances.')

        return {'warnings': warnings, 'recommendations': recommendations}

    def project_show_finances(
        self,
        show_draft: ShowDraft,
        wrestlers_on_card: List[Any],
        brand_prestige: int = 50,
        current_balance: int = 1000000,
        randomize: bool = False,
    ) -> Dict[str, Any]:
        attendance_data = self._attendance_projection(
            show_draft,
            brand_prestige=brand_prestige,
            current_balance=current_balance,
            wrestlers_on_card=wrestlers_on_card,
            randomize=randomize,
        )
        payroll = self.calculate_payroll(wrestlers_on_card)
        revenue_breakdown = self._revenue_breakdown(
            show_draft,
            attendance=attendance_data['attendance'],
            star_power=attendance_data['star_power'],
            focus_multiplier=attendance_data['focus_multiplier'],
        )
        expense_breakdown = self._expense_breakdown(
            show_draft,
            payroll=payroll,
            roster_size=len(wrestlers_on_card),
        )
        projected_net_profit = revenue_breakdown['total_revenue'] - expense_breakdown['total_expenses']
        projected_margin_pct = 0.0
        if revenue_breakdown['total_revenue'] > 0:
            projected_margin_pct = round((projected_net_profit / revenue_breakdown['total_revenue']) * 100, 2)

        projection = {
            'brand': show_draft.brand,
            'show_type': show_draft.show_type,
            'venue_name': self._venue_override(show_draft).get('venue_name'),
            'city_name': self._venue_override(show_draft).get('city_name'),
            'projected_attendance': attendance_data['attendance'],
            'projected_total_revenue': revenue_breakdown['total_revenue'],
            'projected_total_expenses': expense_breakdown['total_expenses'],
            'projected_net_profit': projected_net_profit,
            'projected_margin_pct': projected_margin_pct,
            'main_event_multiplier': attendance_data['main_event_multiplier'],
            'card_focus_multiplier': attendance_data['focus_multiplier'],
            'star_power': attendance_data['star_power'],
            'revenue_breakdown': revenue_breakdown,
            'expense_breakdown': expense_breakdown,
        }
        projection.update(self._warnings_and_recommendations(show_draft, projection))
        return projection

    def calculate_attendance(self, show_draft: ShowDraft, brand_prestige: int = 50, current_balance: int = 1000000) -> int:
        projection = self.project_show_finances(show_draft, [], brand_prestige, current_balance, randomize=True)
        return projection['projected_attendance']

    def calculate_revenue(self, show_draft: ShowDraft, attendance: int) -> Dict[str, int]:
        breakdown = self._revenue_breakdown(show_draft, attendance, star_power=60.0, focus_multiplier=1.0)
        return {
            'gate_revenue': breakdown['gate_revenue'],
            'ppv_revenue': breakdown['ppv_revenue'],
            'total_revenue': breakdown['total_revenue'],
        }

    def calculate_expenses(self, show_draft: ShowDraft, payroll: int) -> Dict[str, int]:
        return self._expense_breakdown(show_draft, payroll, roster_size=0)

    def calculate_net_profit(self, revenue: int, expenses: int) -> int:
        return revenue - expenses


finance_calculator = FinanceCalculator()
