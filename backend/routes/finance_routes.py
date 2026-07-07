import json
import math
import uuid
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request

from services.finance_enterprise import FinanceEnterpriseService


finance_bp = Blueprint('finance_api', __name__)

_tables_ensured = False

DEFAULT_SETTINGS = {
    'ppv_price': 49.99,
    'show_ticket_prices': {
        'weekly_tv': 100,
        'minor_ppv': 75,
        'major_ppv': 100,
    },
    'ticket_tiers': {
        'floor': 120,
        'lower_bowl': 80,
        'upper_bowl': 45,
        'premium': 180,
    },
    'budget_allocations': {
        'wrestler_salaries': 70000,
        'production_expenses': 40000,
        'venue_rentals': 18000,
        'staff_payroll': 20000,
        'travel': 10000,
        'marketing': 12000,
        'merchandise_production': 15000,
    },
}

LEGACY_DEFAULT_SETTINGS = {
    'show_ticket_prices': {
        'weekly_tv': 50,
        'minor_ppv': 75,
        'major_ppv': 100,
    },
    'budget_allocations': {
        'wrestler_salaries': 90000,
        'production_expenses': 60000,
        'venue_rentals': 25000,
        'staff_payroll': 28000,
        'travel': 18000,
        'marketing': 22000,
        'merchandise_production': 15000,
    },
}


def get_database():
    return current_app.config['DATABASE']


def get_universe():
    return current_app.config['UNIVERSE']


def _enterprise_service():
    return FinanceEnterpriseService(get_database())


def _game_period(db):
    state = db.get_game_state()
    return state.get('current_year', 1), state.get('current_week', 1), state.get('balance', 0)


def _weeks_between(start_year, start_week, end_year, end_week):
    return max(0, (end_year - start_year) * 52 + (end_week - start_week))


def _clamp(value, lower, upper):
    return max(lower, min(upper, value))


def _ensure_tables():
    global _tables_ensured
    if _tables_ensured:
        return

    db = get_database()
    cursor = db.conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS finance_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            ppv_price REAL NOT NULL DEFAULT 49.99,
            show_ticket_prices_json TEXT NOT NULL DEFAULT '{}',
            ticket_tiers_json TEXT NOT NULL DEFAULT '{}',
            budget_allocations_json TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS finance_tv_deals (
            deal_id TEXT PRIMARY KEY,
            network_name TEXT NOT NULL,
            weekly_fee INTEGER NOT NULL,
            ppv_bonus INTEGER NOT NULL DEFAULT 0,
            market_size INTEGER NOT NULL DEFAULT 50,
            content_quality INTEGER NOT NULL DEFAULT 50,
            content_requirement TEXT DEFAULT '',
            signing_bonus INTEGER NOT NULL DEFAULT 0,
            start_year INTEGER NOT NULL,
            start_week INTEGER NOT NULL,
            duration_weeks INTEGER NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS finance_sponsorship_deals (
            deal_id TEXT PRIMARY KEY,
            sponsor_name TEXT NOT NULL,
            category TEXT NOT NULL,
            weekly_fee INTEGER NOT NULL,
            signing_bonus INTEGER NOT NULL DEFAULT 0,
            content_restriction TEXT DEFAULT '',
            promo_obligation TEXT DEFAULT '',
            start_year INTEGER NOT NULL,
            start_week INTEGER NOT NULL,
            duration_weeks INTEGER NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS finance_merchandise (
            item_id TEXT PRIMARY KEY,
            wrestler_id TEXT,
            wrestler_name TEXT,
            item_name TEXT NOT NULL,
            category TEXT NOT NULL,
            unit_cost REAL NOT NULL,
            unit_price REAL NOT NULL,
            inventory INTEGER NOT NULL DEFAULT 0,
            hype_score INTEGER NOT NULL DEFAULT 50,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS finance_capital (
            instrument_id TEXT PRIMARY KEY,
            instrument_type TEXT NOT NULL,
            counterparty TEXT NOT NULL,
            principal INTEGER NOT NULL,
            weekly_payment INTEGER NOT NULL DEFAULT 0,
            interest_rate REAL NOT NULL DEFAULT 0.0,
            equity_pct REAL NOT NULL DEFAULT 0.0,
            start_year INTEGER NOT NULL,
            start_week INTEGER NOT NULL,
            duration_weeks INTEGER NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS finance_ledger_entries (
            entry_id TEXT PRIMARY KEY,
            entry_year INTEGER NOT NULL,
            entry_week INTEGER NOT NULL,
            category TEXT NOT NULL,
            amount INTEGER NOT NULL,
            direction TEXT NOT NULL,
            source_ref TEXT,
            notes TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS finance_settlement_state (
            id INTEGER PRIMARY KEY CHECK (id=1),
            last_year INTEGER NOT NULL DEFAULT 1,
            last_week INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        );
    """)
    cursor.execute("PRAGMA table_info(finance_settings)")
    existing_cols = {row[1] for row in cursor.fetchall()}
    if 'show_ticket_prices_json' not in existing_cols:
        cursor.execute("ALTER TABLE finance_settings ADD COLUMN show_ticket_prices_json TEXT NOT NULL DEFAULT '{}'")

    now = datetime.now().isoformat()
    cursor.execute(
        """
        INSERT OR IGNORE INTO finance_settings
        (id, ppv_price, show_ticket_prices_json, ticket_tiers_json, budget_allocations_json, updated_at)
        VALUES (1, ?, ?, ?, ?, ?)
        """,
        (
            DEFAULT_SETTINGS['ppv_price'],
            json.dumps(DEFAULT_SETTINGS['show_ticket_prices']),
            json.dumps(DEFAULT_SETTINGS['ticket_tiers']),
            json.dumps(DEFAULT_SETTINGS['budget_allocations']),
            now,
        ),
    )
    db.conn.commit()
    _tables_ensured = True


def _load_settings(db):
    _ensure_tables()
    cursor = db.conn.cursor()
    cursor.execute('SELECT * FROM finance_settings WHERE id = 1')
    row = cursor.fetchone()
    if not row:
        return DEFAULT_SETTINGS.copy()

    data = dict(row)
    show_ticket_prices = json.loads(data.get('show_ticket_prices_json') or '{}')
    ticket_tiers = json.loads(data.get('ticket_tiers_json') or '{}')
    budget_allocations = json.loads(data.get('budget_allocations_json') or '{}')
    merged = {
        'ppv_price': float(data.get('ppv_price', DEFAULT_SETTINGS['ppv_price'])),
        'show_ticket_prices': {**DEFAULT_SETTINGS['show_ticket_prices'], **show_ticket_prices},
        'ticket_tiers': {**DEFAULT_SETTINGS['ticket_tiers'], **ticket_tiers},
        'budget_allocations': {**DEFAULT_SETTINGS['budget_allocations'], **budget_allocations},
    }

    if merged['show_ticket_prices'].get('weekly_tv') == LEGACY_DEFAULT_SETTINGS['show_ticket_prices']['weekly_tv']:
        merged['show_ticket_prices']['weekly_tv'] = DEFAULT_SETTINGS['show_ticket_prices']['weekly_tv']

    for key, legacy_value in LEGACY_DEFAULT_SETTINGS['budget_allocations'].items():
        if merged['budget_allocations'].get(key) == legacy_value:
            merged['budget_allocations'][key] = DEFAULT_SETTINGS['budget_allocations'][key]

    return merged


def _save_settings(db, payload):
    _ensure_tables()
    settings = _load_settings(db)
    ticket_tiers = payload.get('ticket_tiers') or settings['ticket_tiers']
    show_ticket_prices = payload.get('show_ticket_prices') or settings.get('show_ticket_prices', DEFAULT_SETTINGS['show_ticket_prices'])
    budget_allocations = payload.get('budget_allocations') or settings['budget_allocations']
    ppv_price = float(payload.get('ppv_price', settings['ppv_price']))

    cursor = db.conn.cursor()
    cursor.execute(
        """
        UPDATE finance_settings
        SET ppv_price = ?, show_ticket_prices_json = ?, ticket_tiers_json = ?, budget_allocations_json = ?, updated_at = ?
        WHERE id = 1
        """,
        (
            ppv_price,
            json.dumps(show_ticket_prices),
            json.dumps(ticket_tiers),
            json.dumps(budget_allocations),
            datetime.now().isoformat(),
        ),
    )
    db.conn.commit()
    return _load_settings(db)


def _fetch_all(cursor, query, params=()):
    cursor.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]


def _economic_state(year, week):
    consumer = _clamp(72 + (18 * math.sin((week + (year * 4)) / 5.0)), 42, 96)
    sponsorship = _clamp(70 + (15 * math.cos((week + year) / 6.0)), 45, 95)
    media = _clamp(76 + (14 * math.sin((week + 8) / 9.0)), 50, 98)
    merch = _clamp(68 + (20 * math.sin((week + 2) / 4.5)), 40, 96)
    inflation = round(2.2 + max(0, (65 - consumer) / 18), 1)

    if consumer >= 80 and sponsorship >= 75:
        outlook = 'Bullish'
    elif consumer <= 55:
        outlook = 'Constrained'
    else:
        outlook = 'Stable'

    return {
        'consumer_confidence': round(consumer, 1),
        'sponsorship_market': round(sponsorship, 1),
        'media_rights_index': round(media, 1),
        'merchandise_demand': round(merch, 1),
        'inflation_rate': inflation,
        'outlook': outlook,
    }


def _current_average_rating(show_history, show_filter=None):
    ratings = []
    for show in show_history:
        show_type = show.get('show_type', '')
        if show_filter and not show_filter(show_type):
            continue
        ratings.append(show.get('overall_rating') or 0)
    return round(sum(ratings) / max(len(ratings), 1), 2)


def _active_deals(rows, year, week):
    active = []
    for row in rows:
        elapsed = _weeks_between(row['start_year'], row['start_week'], year, week)
        remaining = max(0, row['duration_weeks'] - elapsed)
        if remaining <= 0:
            continue
        row = dict(row)
        row['weeks_remaining'] = remaining
        active.append(row)
    return active


def _weighted_ticket_price(settings):
    tiers = settings['ticket_tiers']
    return (
        tiers['floor'] * 0.14 +
        tiers['premium'] * 0.08 +
        tiers['lower_bowl'] * 0.33 +
        tiers['upper_bowl'] * 0.45
    )


def _show_revenue_split(show):
    total_revenue = float(show.get('total_revenue') or 0)
    show_type = show.get('show_type') or ''
    is_ppv = 'ppv' in show_type or show_type in ('major_ppv', 'minor_ppv')

    gate_pct = 0.82
    ppv_pct = 0.0
    licensing_pct = 0.03

    if is_ppv:
        gate_pct = 0.38
        ppv_pct = 0.54
        licensing_pct = 0.05
    elif show_type == 'house_show':
        gate_pct = 0.90
        licensing_pct = 0.02

    return {
        'live_gate': round(total_revenue * gate_pct),
        'ppv_buys': round(total_revenue * ppv_pct),
        'licensing': round(total_revenue * licensing_pct),
        'event_revenue': round(total_revenue),
    }


def _wrestler_popularity(universe, wrestler_id):
    wrestler = universe.get_wrestler_by_id(wrestler_id) if wrestler_id else None
    if not wrestler:
        return 55
    for field in ('popularity', 'overness', 'overall_rating'):
        value = getattr(wrestler, field, None)
        if value is not None:
            return float(value)
    return 55


def _merchandise_summary(universe, merch_rows, economy):
    items = []
    total_units = 0
    total_revenue = 0
    total_cost = 0

    for row in merch_rows:
        popularity = _wrestler_popularity(universe, row.get('wrestler_id'))
        demand_score = (
            (economy['merchandise_demand'] * 0.45) +
            (row.get('hype_score', 50) * 0.30) +
            (popularity * 0.25)
        )
        projected_units = int(_clamp(round(demand_score / 9.5), 0, row.get('inventory', 0)))
        projected_revenue = round(projected_units * float(row.get('unit_price', 0)))
        projected_cost = round(projected_units * float(row.get('unit_cost', 0)))

        item = dict(row)
        item['projected_units'] = projected_units
        item['projected_revenue'] = projected_revenue
        item['projected_cost'] = projected_cost
        item['sell_through_pct'] = round((projected_units / max(row.get('inventory', 1), 1)) * 100, 1) if row.get('inventory') else 0
        items.append(item)

        total_units += projected_units
        total_revenue += projected_revenue
        total_cost += projected_cost

    top_sellers = sorted(items, key=lambda item: item['projected_revenue'], reverse=True)[:5]
    return {
        'items': items,
        'top_sellers': top_sellers,
        'projected_weekly_units': total_units,
        'projected_weekly_revenue': total_revenue,
        'projected_weekly_cost': total_cost,
    }


def _build_period_reports(show_history, settings, tv_deals, sponsors, merch_summary, capital_rows, economy, current_year, current_week, granularity):
    groups = {}
    for show in show_history:
        if granularity == 'monthly':
            period_index = ((show.get('week', 1) - 1) // 4) + 1
            key = f"Y{show.get('year', 1)}-M{period_index}"
        else:
            key = f"Y{show.get('year', 1)}-W{int(show.get('week', 1)):02d}"
        groups.setdefault(key, []).append(show)

    if granularity == 'monthly':
        current_key = f"Y{current_year}-M{((current_week - 1) // 4) + 1}"
    else:
        current_key = f"Y{current_year}-W{current_week:02d}"
    groups.setdefault(current_key, [])

    reports = []
    for key, shows in groups.items():
        weekly_tv_count = len([show for show in shows if show.get('show_type') == 'weekly_tv'])
        ppv_count = len([show for show in shows if 'ppv' in (show.get('show_type') or '')])
        show_count = len(shows)
        if granularity == 'monthly':
            weeks_in_period = max(1, len({(show.get('year'), show.get('week')) for show in shows}) or 4)
            period_number = int(key.split('-M')[1])
        else:
            weeks_in_period = 1
            period_number = int(key.split('-W')[1])
        period_year = int(key.split('-')[0][1:])

        live_gate = 0
        ppv_buys = 0
        licensing = 0
        event_revenue = 0
        wrestler_salaries = 0
        production_expenses = 0

        for show in shows:
            split = _show_revenue_split(show)
            live_gate += split['live_gate']
            ppv_buys += split['ppv_buys']
            licensing += split['licensing']
            event_revenue += split['event_revenue']
            wrestler_salaries += int(show.get('total_payroll') or 0)
            production_expenses += max(0, int((show.get('total_revenue') or 0) - (show.get('net_profit') or 0) - (show.get('total_payroll') or 0)))

        tv_rights = int(sum(deal['weekly_fee'] for deal in tv_deals) * max(weekly_tv_count, weeks_in_period))
        ppv_tv_bonus = int(sum(deal.get('ppv_bonus', 0) for deal in tv_deals) * ppv_count)
        sponsorship_income = int(sum(deal['weekly_fee'] for deal in sponsors) * weeks_in_period)
        merchandise_income = int(merch_summary['projected_weekly_revenue'] * weeks_in_period)
        merchandise_cost = int(merch_summary['projected_weekly_cost'] * weeks_in_period)

        debt_service = 0
        investor_distribution = 0
        for row in capital_rows:
            if row['instrument_type'] == 'loan':
                debt_service += row['weekly_payment'] * weeks_in_period

        revenue_total = live_gate + ppv_buys + licensing + tv_rights + ppv_tv_bonus + sponsorship_income + merchandise_income

        for row in capital_rows:
            if row['instrument_type'] == 'investment':
                investor_distribution += int(max(revenue_total - wrestler_salaries - production_expenses, 0) * (row.get('equity_pct', 0) / 100.0))

        expense_breakdown = {
            'wrestler_salaries': wrestler_salaries,
            'production_expenses': production_expenses,
            'venue_rentals': int(max(show_count, weeks_in_period) * 6500),
            'staff_payroll': int(settings['budget_allocations']['staff_payroll'] * weeks_in_period),
            'travel': int(settings['budget_allocations']['travel'] * max(show_count, 1) / 3),
            'marketing': int(settings['budget_allocations']['marketing'] * weeks_in_period),
            'merchandise_production': merchandise_cost,
            'debt_service': debt_service + investor_distribution,
        }
        expense_total = sum(expense_breakdown.values())

        revenue_breakdown = {
            'live_gate': live_gate,
            'ppv_buys': ppv_buys,
            'tv_rights': tv_rights + ppv_tv_bonus,
            'merchandise': merchandise_income,
            'sponsorships': sponsorship_income,
            'licensing': licensing,
        }

        reports.append({
            'period': key,
            'sort_year': period_year,
            'sort_period': period_number,
            'show_count': show_count,
            'revenue_total': revenue_total,
            'expense_total': expense_total,
            'profit': revenue_total - expense_total,
            'revenue_breakdown': revenue_breakdown,
            'expense_breakdown': expense_breakdown,
            'attendance_total': int(sum(show.get('total_attendance') or 0 for show in shows)),
            'average_rating': _current_average_rating(shows) if shows else 0,
            'economic_outlook': economy['outlook'],
        })

    reports.sort(key=lambda item: (item['sort_year'], item['sort_period']), reverse=True)
    for index, report in enumerate(reports):
        previous_profit = reports[index + 1]['profit'] if index + 1 < len(reports) else report['profit']
        report['trend_delta'] = report['profit'] - previous_profit
        report.pop('sort_year', None)
        report.pop('sort_period', None)
    return reports


def _budget_status(settings, weekly_report):
    allocations = settings['budget_allocations']
    actuals = weekly_report['expense_breakdown']
    rows = []
    for category, limit in allocations.items():
        actual = int(actuals.get(category, 0))
        rows.append({
            'category': category,
            'limit': int(limit),
            'actual': actual,
            'variance': actual - int(limit),
            'over_budget': actual > int(limit),
        })
    return rows


def _risk_summary(balance, weekly_report, budget_rows):
    warnings = []
    consequences = []
    risk_score = 0

    if balance < 0:
        risk_score += 3
        warnings.append('Cash reserves are already negative.')
        consequences.append('Late salary payments can trigger morale collapses and talent exits.')
        consequences.append('Credit pressure is rising; bankruptcy risk is active.')
    if weekly_report['profit'] < 0:
        risk_score += 2
        warnings.append('The current weekly P&L is negative.')
    if any(row['over_budget'] for row in budget_rows):
        risk_score += 1
        warnings.append('One or more operating categories are over budget.')
    if weekly_report['expense_breakdown']['wrestler_salaries'] > max(balance, 0):
        risk_score += 2
        consequences.append('You may be unable to cover wrestler salaries from cash on hand.')

    fixed_outflow = sum(weekly_report['expense_breakdown'].values())
    runway = 0 if fixed_outflow <= 0 else round(balance / fixed_outflow, 1)

    if risk_score >= 5:
        risk_level = 'High'
    elif risk_score >= 3:
        risk_level = 'Medium'
    else:
        risk_level = 'Low'

    if risk_level == 'High' and not consequences:
        consequences.append('Severe financial difficulty is likely to damage morale and roster stability.')

    return {
        'risk_level': risk_level,
        'warnings': warnings,
        'consequences': consequences,
        'projected_runway_weeks': runway,
    }


def _post_ledger_entry(cursor, year, week, category, amount, direction, source_ref='', notes=''):
    cursor.execute(
        """
        INSERT INTO finance_ledger_entries
        (entry_id, entry_year, entry_week, category, amount, direction, source_ref, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f'led_{uuid.uuid4().hex[:12]}',
            year,
            week,
            category,
            int(amount),
            direction,
            source_ref,
            notes,
            datetime.now().isoformat(),
        ),
    )


def _apply_periodic_settlement(db, year, week):
    cursor = db.conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO finance_settlement_state (id, last_year, last_week, updated_at) VALUES (1, 1, 0, ?)",
        (datetime.now().isoformat(),),
    )
    state = cursor.execute("SELECT last_year, last_week FROM finance_settlement_state WHERE id = 1").fetchone()
    if state and state['last_year'] == year and state['last_week'] == week:
        return {'applied': False, 'net': 0}

    current = db.get_game_state()
    balance = int(current.get('balance', 0))
    net = 0

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tv_deals'")
    tv_rows = []
    if cursor.fetchone():
        tv_rows = _fetch_all(cursor, "SELECT id, network_name, annual_value, ppv_share_percent, years FROM tv_deals WHERE status = 'active'")
    for deal in tv_rows:
        weekly_base = int(float(deal['annual_value']) / 52)
        production_cost = int(weekly_base * 0.18)
        amortized_cost = int(float(deal['annual_value']) * 0.05 / max(1, int(deal['years']) * 52))
        weekly_net = weekly_base - production_cost - amortized_cost
        net += weekly_net
        _post_ledger_entry(cursor, year, week, 'tv_rights_weekly', weekly_net, 'credit', f"tv:{deal['id']}", deal['network_name'])

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='merchandise_items'")
    merch_rows = []
    if cursor.fetchone():
        merch_rows = _fetch_all(cursor, "SELECT id, name, price, unit_cost, inventory, popularity FROM merchandise_items WHERE is_deleted = 0")
    demand_index = _economic_state(year, week)['merchandise_demand'] / 100.0
    for item in merch_rows:
        projected = int((item['popularity'] / 100.0) * demand_index * max(3, item['inventory'] * 0.08))
        sold_units = max(0, min(int(item['inventory']), projected))
        if sold_units <= 0:
            continue
        revenue = int(sold_units * float(item['price']))
        cogs = int(sold_units * float(item['unit_cost']))
        net += (revenue - cogs)
        cursor.execute("UPDATE merchandise_items SET inventory = inventory - ? WHERE id = ?", (sold_units, item['id']))
        _post_ledger_entry(cursor, year, week, 'merch_sales', revenue, 'credit', f"merch:{item['id']}", f"units={sold_units}")
        _post_ledger_entry(cursor, year, week, 'merch_cogs', cogs, 'debit', f"merch:{item['id']}", f"units={sold_units}")

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='shows'")
    ppv_shows = []
    if cursor.fetchone():
        ppv_shows = _fetch_all(
            cursor,
            "SELECT id, total_revenue FROM shows WHERE year = ? AND week = ? AND (show_type LIKE '%ppv%' OR show_type IN ('major_ppv','minor_ppv'))",
            (year, week),
        )
    ppv_total = sum(int(float(s.get('total_revenue') or 0)) for s in ppv_shows)
    ppv_share = int(ppv_total * 0.05)
    if ppv_share > 0:
        net += ppv_share
        _post_ledger_entry(cursor, year, week, 'ppv_distribution', ppv_share, 'credit', 'ppv:weekly', f"events={len(ppv_shows)}")

    db.update_game_state(balance=balance + net)
    cursor.execute(
        "UPDATE finance_settlement_state SET last_year = ?, last_week = ?, updated_at = ? WHERE id = 1",
        (year, week, datetime.now().isoformat()),
    )
    db.conn.commit()
    return {'applied': True, 'net': net}


def _ledger_report(cursor, year, week):
    rows = _fetch_all(
        cursor,
        "SELECT * FROM finance_ledger_entries WHERE entry_year = ? AND entry_week = ? ORDER BY created_at DESC",
        (year, week),
    )
    totals = {'credit': 0, 'debit': 0}
    for row in rows:
        totals[row['direction']] = totals.get(row['direction'], 0) + int(row['amount'])
    return {'entries': rows[:100], 'totals': totals}


def _dashboard_payload():
    _ensure_tables()
    db = get_database()
    universe = get_universe()
    year, week, balance = _game_period(db)
    settings = _load_settings(db)
    economy = _economic_state(year, week)
    settlement = _apply_periodic_settlement(db, year, week)
    year, week, balance = _game_period(db)

    show_history = db.get_show_history(limit=120)
    cursor = db.conn.cursor()
    tv_deals = _active_deals(_fetch_all(cursor, 'SELECT * FROM finance_tv_deals ORDER BY created_at DESC'), year, week)
    sponsors = _active_deals(_fetch_all(cursor, 'SELECT * FROM finance_sponsorship_deals ORDER BY created_at DESC'), year, week)
    merchandise_rows = _fetch_all(cursor, 'SELECT * FROM finance_merchandise ORDER BY created_at DESC')
    capital_rows = _active_deals(_fetch_all(cursor, 'SELECT * FROM finance_capital ORDER BY created_at DESC'), year, week)

    merch_summary = _merchandise_summary(universe, merchandise_rows, economy)
    weekly_reports = _build_period_reports(show_history, settings, tv_deals, sponsors, merch_summary, capital_rows, economy, year, week, 'weekly')
    monthly_reports = _build_period_reports(show_history, settings, tv_deals, sponsors, merch_summary, capital_rows, economy, year, week, 'monthly')

    current_week = weekly_reports[0] if weekly_reports else {
        'profit': 0,
        'revenue_total': 0,
        'expense_total': 0,
        'revenue_breakdown': {},
        'expense_breakdown': {key: 0 for key in settings['budget_allocations']},
        'show_count': 0,
        'attendance_total': 0,
        'average_rating': 0,
    }
    current_month = monthly_reports[0] if monthly_reports else current_week

    budget_rows = _budget_status(settings, current_week)
    risk = _risk_summary(balance, current_week, budget_rows)
    ledger = _ledger_report(cursor, year, week)

    revenue_streams = [
        {'category': key, 'amount': int(value)}
        for key, value in current_week['revenue_breakdown'].items()
    ]
    expense_categories = [
        {'category': key, 'amount': int(value)}
        for key, value in current_week['expense_breakdown'].items()
    ]

    return {
        'success': True,
        'overview': {
            'balance': balance,
            'year': year,
            'week': week,
            'weekly_profit': current_week['profit'],
            'monthly_profit': current_month['profit'],
            'weekly_revenue': current_week['revenue_total'],
            'weekly_expenses': current_week['expense_total'],
            'average_show_rating': _current_average_rating(show_history),
        },
        'economy': economy,
        'settings': settings,
        'revenue_streams': revenue_streams,
        'expense_categories': expense_categories,
        'budget_allocations': budget_rows,
        'reports': {
            'weekly': weekly_reports[:8],
            'monthly': monthly_reports[:6],
        },
        'tv_rights': tv_deals,
        'sponsorships': sponsors,
        'merchandise': merch_summary,
        'capital': capital_rows,
        'difficulty': risk,
        'settlement': settlement,
        'ledger': ledger,
        'enterprise': _enterprise_service().enterprise_dashboard(),
    }


@finance_bp.route('/api/finance/dashboard')
def api_finance_dashboard():
    try:
        return jsonify(_dashboard_payload())
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@finance_bp.route('/api/finance/transactions', methods=['GET'])
def api_finance_transactions():
    try:
        return jsonify({'success': True, 'transactions': _enterprise_service().list_transactions()})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@finance_bp.route('/api/finance/transactions', methods=['POST'])
def api_create_finance_transaction():
    try:
        transaction = _enterprise_service().post_transaction(request.get_json() or {})
        return jsonify({'success': True, 'transaction': transaction})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@finance_bp.route('/api/finance/sponsorships', methods=['GET'])
def api_enterprise_sponsorships():
    try:
        return jsonify({'success': True, **_enterprise_service().list_sponsorships()})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@finance_bp.route('/api/finance/sponsors', methods=['POST'])
def api_create_sponsor_profile():
    try:
        sponsor = _enterprise_service().create_sponsor(request.get_json() or {})
        return jsonify({'success': True, 'sponsor': sponsor})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@finance_bp.route('/api/finance/sponsorships/<sponsor_id>/contracts', methods=['POST'])
def api_create_sponsorship_contract(sponsor_id):
    try:
        contract = _enterprise_service().create_contract(sponsor_id, request.get_json() or {})
        return jsonify({'success': True, 'contract': contract})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@finance_bp.route('/api/finance/sponsorship-requirements/<requirement_id>/deliverables', methods=['POST'])
def api_record_sponsorship_deliverable(requirement_id):
    try:
        progress = _enterprise_service().record_deliverable(requirement_id, request.get_json() or {})
        return jsonify({'success': True, 'progress': progress})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@finance_bp.route('/api/finance/sponsorships/<sponsor_id>/controversies', methods=['POST'])
def api_record_sponsorship_controversy(sponsor_id):
    try:
        result = _enterprise_service().record_controversy(sponsor_id, request.get_json() or {})
        return jsonify({'success': True, **result})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@finance_bp.route('/api/finance/sponsorship-contracts/<contract_id>/payments', methods=['POST'])
def api_process_sponsorship_payment(contract_id):
    try:
        result = _enterprise_service().process_sponsorship_payment(contract_id, request.get_json() or {})
        return jsonify({'success': True, **result})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@finance_bp.route('/api/finance/venues-tours', methods=['GET'])
def api_finance_venues_tours():
    try:
        return jsonify({'success': True, **_enterprise_service().list_venues_tours()})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@finance_bp.route('/api/finance/venue-upgrades', methods=['POST'])
def api_purchase_venue_upgrade():
    try:
        result = _enterprise_service().purchase_upgrade(request.get_json() or {})
        return jsonify({'success': True, **result})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@finance_bp.route('/api/finance/tours', methods=['POST'])
def api_create_finance_tour():
    try:
        tour = _enterprise_service().create_tour(request.get_json() or {})
        return jsonify({'success': True, 'tour': tour})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@finance_bp.route('/api/finance/tours/<tour_id>/optimize', methods=['POST'])
def api_optimize_finance_tour(tour_id):
    try:
        return jsonify({'success': True, **_enterprise_service().optimize_tour(tour_id)})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@finance_bp.route('/api/finance/settlements/event/<event_id>', methods=['POST'])
def api_settle_finance_event(event_id):
    try:
        settlement = _enterprise_service().settle_event(event_id, request.get_json() or {})
        return jsonify({'success': True, 'settlement': settlement})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@finance_bp.route('/api/finance/settlements/tour/<tour_id>', methods=['POST'])
def api_settle_finance_tour(tour_id):
    try:
        settlement = _enterprise_service().settle_tour(tour_id, request.get_json() or {})
        return jsonify({'success': True, 'settlement': settlement})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@finance_bp.route('/api/finance/reports/profitability')
def api_finance_profitability_report():
    try:
        return jsonify({'success': True, 'report': _enterprise_service().profitability_report()})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@finance_bp.route('/api/finance/reports/budget-variance')
def api_finance_budget_variance_report():
    try:
        period = request.args.get('period', 'current_quarter')
        return jsonify({'success': True, 'report': _enterprise_service().budget_variance_report(period)})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@finance_bp.route('/api/finance/forecasts')
def api_finance_forecasts():
    try:
        return jsonify({'success': True, 'forecasts': _enterprise_service().forecasts()})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@finance_bp.route('/api/finance/reconcile', methods=['POST'])
def api_finance_reconcile():
    try:
        transaction = _enterprise_service().reconcile(request.get_json() or {})
        return jsonify({'success': True, 'transaction': transaction})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@finance_bp.route('/api/finance/settings', methods=['POST'])
def api_update_finance_settings():
    try:
        db = get_database()
        payload = request.get_json() or {}
        settings = _save_settings(db, payload)
        return jsonify({'success': True, 'settings': settings})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@finance_bp.route('/api/finance/tv-rights/negotiate', methods=['POST'])
def api_negotiate_tv_rights():
    try:
        _ensure_tables()
        db = get_database()
        payload = request.get_json() or {}
        year, week, balance = _game_period(db)
        economy = _economic_state(year, week)
        show_history = db.get_show_history(limit=80)

        network_name = payload.get('network_name', 'Global Sports One').strip() or 'Global Sports One'
        market_size = int(payload.get('market_size', 65))
        content_quality = int(payload.get('content_quality', max(55, int(_current_average_rating(show_history, lambda show_type: show_type == 'weekly_tv') * 20))))
        duration_weeks = max(4, int(payload.get('duration_weeks', 26)))
        content_requirement = payload.get('content_requirement', 'Prime-time consistency')

        avg_rating = _current_average_rating(show_history, lambda show_type: show_type == 'weekly_tv')
        weekly_fee = int(
            18000 +
            (avg_rating * 7000) +
            (market_size * 240) +
            (content_quality * 180) +
            (economy['media_rights_index'] * 90)
        )
        ppv_bonus = int(weekly_fee * 0.35)
        signing_bonus = int(weekly_fee * 2.2)

        cursor = db.conn.cursor()
        deal_id = f"tv_{uuid.uuid4().hex[:8]}"
        cursor.execute(
            """
            INSERT INTO finance_tv_deals
            (deal_id, network_name, weekly_fee, ppv_bonus, market_size, content_quality,
             content_requirement, signing_bonus, start_year, start_week, duration_weeks, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                deal_id,
                network_name,
                weekly_fee,
                ppv_bonus,
                market_size,
                content_quality,
                content_requirement,
                signing_bonus,
                year,
                week,
                duration_weeks,
                datetime.now().isoformat(),
            ),
        )
        db.update_game_state(balance=balance + signing_bonus)
        db.conn.commit()

        return jsonify({
            'success': True,
            'deal': {
                'deal_id': deal_id,
                'network_name': network_name,
                'weekly_fee': weekly_fee,
                'ppv_bonus': ppv_bonus,
                'weeks_remaining': duration_weeks,
                'content_requirement': content_requirement,
                'signing_bonus': signing_bonus,
            },
            'message': f'{network_name} agreed to a {duration_weeks}-week deal.',
        })
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@finance_bp.route('/api/finance/sponsorships', methods=['POST'])
def api_create_sponsorship():
    try:
        _ensure_tables()
        db = get_database()
        payload = request.get_json() or {}
        year, week, balance = _game_period(db)
        economy = _economic_state(year, week)

        sponsor_name = payload.get('sponsor_name', 'Northstar Energy').strip() or 'Northstar Energy'
        category = payload.get('category', 'Consumer Brand')
        duration_weeks = max(4, int(payload.get('duration_weeks', 16)))
        content_restriction = payload.get('content_restriction', 'Avoid excessive gore')
        promo_obligation = payload.get('promo_obligation', 'Two logo mentions per weekly show')

        weekly_fee = int(7000 + (economy['sponsorship_market'] * 120) + (duration_weeks * 35))
        signing_bonus = int(weekly_fee * 1.5)

        cursor = db.conn.cursor()
        deal_id = f"sponsor_{uuid.uuid4().hex[:8]}"
        cursor.execute(
            """
            INSERT INTO finance_sponsorship_deals
            (deal_id, sponsor_name, category, weekly_fee, signing_bonus, content_restriction,
             promo_obligation, start_year, start_week, duration_weeks, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                deal_id,
                sponsor_name,
                category,
                weekly_fee,
                signing_bonus,
                content_restriction,
                promo_obligation,
                year,
                week,
                duration_weeks,
                datetime.now().isoformat(),
            ),
        )
        db.update_game_state(balance=balance + signing_bonus)
        db.conn.commit()

        return jsonify({
            'success': True,
            'deal': {
                'deal_id': deal_id,
                'sponsor_name': sponsor_name,
                'category': category,
                'weekly_fee': weekly_fee,
                'signing_bonus': signing_bonus,
                'weeks_remaining': duration_weeks,
                'content_restriction': content_restriction,
                'promo_obligation': promo_obligation,
            },
        })
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@finance_bp.route('/api/finance/merchandise', methods=['POST'])
def api_create_merchandise():
    try:
        _ensure_tables()
        db = get_database()
        universe = get_universe()
        payload = request.get_json() or {}
        _, _, balance = _game_period(db)

        wrestler_id = payload.get('wrestler_id') or None
        wrestler_name = payload.get('wrestler_name') or None
        if wrestler_id and not wrestler_name:
            wrestler = universe.get_wrestler_by_id(wrestler_id)
            wrestler_name = wrestler.name if wrestler else 'Roster Item'

        item_name = payload.get('item_name', '').strip()
        category = payload.get('category', 'Apparel')
        inventory = max(10, int(payload.get('inventory', 100)))
        unit_cost = float(payload.get('unit_cost', 12))
        unit_price = float(payload.get('unit_price', 30))
        hype_score = max(1, min(100, int(payload.get('hype_score', 60))))

        if not item_name:
            return jsonify({'success': False, 'error': 'item_name is required'}), 400

        production_cost = int(round(unit_cost * inventory))
        db.update_game_state(balance=balance - production_cost)

        cursor = db.conn.cursor()
        item_id = f"merch_{uuid.uuid4().hex[:8]}"
        cursor.execute(
            """
            INSERT INTO finance_merchandise
            (item_id, wrestler_id, wrestler_name, item_name, category, unit_cost,
             unit_price, inventory, hype_score, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item_id,
                wrestler_id,
                wrestler_name,
                item_name,
                category,
                unit_cost,
                unit_price,
                inventory,
                hype_score,
                datetime.now().isoformat(),
            ),
        )
        db.conn.commit()

        return jsonify({
            'success': True,
            'item': {
                'item_id': item_id,
                'item_name': item_name,
                'wrestler_name': wrestler_name,
                'category': category,
                'inventory': inventory,
                'unit_cost': unit_cost,
                'unit_price': unit_price,
                'hype_score': hype_score,
                'production_cost': production_cost,
            },
        })
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@finance_bp.route('/api/finance/capital', methods=['POST'])
def api_create_capital_instrument():
    try:
        _ensure_tables()
        db = get_database()
        payload = request.get_json() or {}
        year, week, balance = _game_period(db)

        instrument_type = payload.get('instrument_type', 'loan')
        counterparty = payload.get('counterparty', 'Commonwealth Bank').strip() or 'Commonwealth Bank'
        principal = max(10000, int(payload.get('principal', 100000)))
        duration_weeks = max(4, int(payload.get('duration_weeks', 26)))
        interest_rate = float(payload.get('interest_rate', 7.5))
        equity_pct = float(payload.get('equity_pct', 8.0 if instrument_type == 'investment' else 0.0))

        if instrument_type == 'loan':
            total_repayment = principal * (1 + (interest_rate / 100.0) * (duration_weeks / 52.0))
            weekly_payment = int(round(total_repayment / duration_weeks))
            equity_pct = 0.0
        else:
            weekly_payment = 0
            interest_rate = 0.0

        cursor = db.conn.cursor()
        instrument_id = f"capital_{uuid.uuid4().hex[:8]}"
        cursor.execute(
            """
            INSERT INTO finance_capital
            (instrument_id, instrument_type, counterparty, principal, weekly_payment,
             interest_rate, equity_pct, start_year, start_week, duration_weeks, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                instrument_id,
                instrument_type,
                counterparty,
                principal,
                weekly_payment,
                interest_rate,
                equity_pct,
                year,
                week,
                duration_weeks,
                datetime.now().isoformat(),
            ),
        )
        db.update_game_state(balance=balance + principal)
        db.conn.commit()

        return jsonify({
            'success': True,
            'instrument': {
                'instrument_id': instrument_id,
                'instrument_type': instrument_type,
                'counterparty': counterparty,
                'principal': principal,
                'weekly_payment': weekly_payment,
                'interest_rate': interest_rate,
                'equity_pct': equity_pct,
                'weeks_remaining': duration_weeks,
            },
        })
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
