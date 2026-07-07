"""
Core Routes - Status, Universe State, Calendar
"""

from flask import Blueprint, jsonify, request, current_app
from datetime import datetime

core_bp = Blueprint('core', __name__)


def get_database():
    return current_app.config['DATABASE']


def get_universe():
    return current_app.config['UNIVERSE']


def _sync_house_shows_into_calendar(universe, database):
    """
    Ensure planned house shows from SQLite are represented in calendar.generated_shows.
    This keeps House Show tours visible after page refresh/server restart.
    """
    try:
        cursor = database.conn.cursor()
        exists = cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='house_shows'"
        ).fetchone()
        if not exists:
            return

        from models.calendar import ScheduledShow

        rows = cursor.execute(
            """
            SELECT house_show_id, brand, city, year, week, status
            FROM house_shows
            WHERE status IN ('planned', 'booked')
            ORDER BY year, week
            """
        ).fetchall()

        by_id = {s.show_id: s for s in universe.calendar.generated_shows}
        for r in rows:
            show_id = r['house_show_id']
            show_name = f"{r['brand']} House Show — {r['city']}"
            if show_id in by_id:
                # Refresh mutable fields in case city/brand changed.
                existing = by_id[show_id]
                existing.year = int(r['year'])
                existing.week = int(r['week'])
                existing.brand = r['brand']
                existing.name = show_name
                existing.show_type = 'house_show'
                existing.is_ppv = False
                existing.tier = 'house'
                if hasattr(existing, 'day_of_week'):
                    existing.day_of_week = 'Saturday'
                continue

            universe.calendar.generated_shows.append(
                ScheduledShow(
                    show_id=show_id,
                    year=int(r['year']),
                    week=int(r['week']),
                    day_of_week='Saturday',
                    brand=r['brand'],
                    name=show_name,
                    show_type='house_show',
                    is_ppv=False,
                    tier='house',
                )
            )
    except Exception:
        # Never break core calendar endpoints due to house show sync issues.
        pass

    try:
        cursor = database.conn.cursor()
        exists = cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='custom_ppvs'"
        ).fetchone()
        if not exists:
            return
        from models.calendar import ScheduledShow
        rows = cursor.execute(
            "SELECT * FROM custom_ppvs WHERE status='active' ORDER BY year, week"
        ).fetchall()
        by_id = {s.show_id: s for s in universe.calendar.generated_shows}
        for r in rows:
            sid = f"custom_ppv_{r['custom_ppv_id']}"
            if sid in by_id:
                continue
            universe.calendar.generated_shows.append(
                ScheduledShow(
                    show_id=sid,
                    year=int(r['year']),
                    week=int(r['week']),
                    day_of_week=r['day_of_week'],
                    brand=r.get('brand', 'Cross-Brand'),
                    name=r['name'],
                    show_type='major_ppv' if r['tier'] == 'major' else 'minor_ppv',
                    is_ppv=True,
                    tier=r['tier'],
                    location=r.get('location', ''),
                )
            )
    except Exception:
        pass


# ============================================================================
# API STATUS
# ============================================================================

@core_bp.route('/api/status')
def api_status():
    database = get_database()
    universe = get_universe()
    
    return jsonify({
        'status': 'online',
        'timestamp': datetime.now().isoformat(),
        'game': 'AWUM - AI Wrestling Universe Manager',
        'version': '0.1.0-alpha',
        'storage': 'SQLite',
        'db_path': database.db_path,
        'initialized': len(universe.wrestlers) > 0
    })


@core_bp.route('/api/universe/state')
def api_universe_state():
    universe = get_universe()
    database = get_database()
    _sync_house_shows_into_calendar(universe, database)
    
    current_show = universe.calendar.get_current_show()
    next_show = universe.calendar.get_next_show()
    next_ppv = universe.calendar.get_next_ppv()
    
    return jsonify({
        'promotion': 'Ring of Champions',
        'year': universe.current_year,
        'week': universe.current_week,
        'balance': universe.balance,
        'brands': ['ROC Alpha', 'ROC Velocity', 'ROC Vanguard'],
        'total_roster': len(universe.wrestlers),
        'active_roster': len(universe.get_active_wrestlers()),
        'retired_count': len(universe.retired_wrestlers),
        'active_feuds': len(universe.feud_manager.get_active_feuds()),
        'current_show': current_show.to_dict() if current_show else None,
        'next_show': next_show.to_dict() if next_show else None,
        'next_ppv': next_ppv.to_dict() if next_ppv else None
    })


@core_bp.route('/api/universe/advance', methods=['POST'])
def api_advance_universe():
    universe = get_universe()
    
    universe.calendar.advance_to_next_show()
    universe.save_all()
    
    return jsonify({
        'success': True,
        'year': universe.current_year,
        'week': universe.current_week
    })


# ============================================================================
# CALENDAR
# ============================================================================

@core_bp.route('/api/calendar/current')
def api_calendar_current():
    universe = get_universe()
    _sync_house_shows_into_calendar(universe, get_database())
    return jsonify(universe.calendar.to_dict())


@core_bp.route('/api/calendar/next')
def api_calendar_next():
    universe = get_universe()
    current_show = universe.calendar.get_current_show()
    
    if not current_show:
        return jsonify({'error': 'No shows scheduled'}), 404
    
    return jsonify(current_show.to_dict())


@core_bp.route('/api/calendar/upcoming-ppvs')
def api_calendar_upcoming_ppvs():
    universe = get_universe()
    count = request.args.get('count', 3, type=int)
    ppvs = universe.calendar.get_upcoming_ppvs(count)
    
    return jsonify({
        'count': len(ppvs),
        'ppvs': [ppv.to_dict() for ppv in ppvs]
    })


@core_bp.route('/api/calendar/shows')
def api_calendar_shows():
    universe = get_universe()
    _sync_house_shows_into_calendar(universe, get_database())
    start = request.args.get('start', 0, type=int)
    limit = request.args.get('limit', 20, type=int)
    
    shows = universe.calendar.generated_shows[start:start+limit]
    
    return jsonify({
        'total': len(universe.calendar.generated_shows),
        'start': start,
        'limit': limit,
        'shows': [show.to_dict() for show in shows]
    })


@core_bp.route('/api/calendar/schedule')
def api_calendar_schedule():
    """
    Returns a merged schedule view:
    - Generated weekly shows + PPVs from Calendar
    - Planned house shows from the show_production house_shows table (if it exists)
    - Venue/city assignments from show_venue_assignments (if present)
    """
    database = get_database()
    universe = get_universe()
    _sync_house_shows_into_calendar(universe, database)

    start = request.args.get('start', 0, type=int)
    limit = request.args.get('limit', 60, type=int)
    limit = max(1, min(limit, 250))

    base_slice = universe.calendar.generated_shows[start:start + limit]
    base = [s.to_dict() for s in base_slice]

    def abs_week(year: int, week: int) -> int:
        return (int(year) - 1) * 52 + int(week)

    if base:
        min_abs = min(abs_week(s["year"], s["week"]) for s in base)
        max_abs = max(abs_week(s["year"], s["week"]) for s in base)
    else:
        min_abs = abs_week(universe.current_year, universe.current_week)
        max_abs = min_abs + 16

    cursor = database.conn.cursor()

    # House shows are created lazily by show_production_routes; only query if table exists.
    house_shows = []
    try:
        exists = cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='house_shows'"
        ).fetchone()
        if exists:
            rows = cursor.execute(
                """
                SELECT house_show_id, brand, venue, city, year, week, status, projected_revenue, actual_revenue
                FROM house_shows
                """
            ).fetchall()
            for r in rows:
                aw = abs_week(r["year"], r["week"])
                if aw < min_abs or aw > max_abs:
                    continue
                house_shows.append(
                    {
                        "show_id": r["house_show_id"],
                        "year": int(r["year"]),
                        "week": int(r["week"]),
                        "day_of_week": "Saturday",
                        "brand": r["brand"],
                        "name": f"{r['brand']} House Show — {r['city']}",
                        "show_type": "house_show",
                        "is_ppv": False,
                        "tier": "house",
                        "house_show": True,
                        "status": r.get("status", "planned"),
                        "city": r.get("city"),
                        "venue": r.get("venue"),
                        "projected_revenue": int(r.get("projected_revenue") or 0),
                        "actual_revenue": int(r.get("actual_revenue") or 0),
                    }
                )
    except Exception:
        house_shows = []

    merged = base + house_shows

    day_order = {"Monday": 1, "Tuesday": 2, "Wednesday": 3, "Thursday": 4, "Friday": 5, "Saturday": 6, "Sunday": 7}

    def sort_key(s: dict):
        return (abs_week(s.get("year", 1), s.get("week", 1)), day_order.get(s.get("day_of_week", "Sunday"), 7), s.get("name", ""))

    merged.sort(key=sort_key)

    # Attach venue assignments (override city/venue on schedule if present)
    try:
        show_ids = [s["show_id"] for s in merged if s.get("show_id")]
        if show_ids:
            placeholders = ",".join(["?"] * len(show_ids))
            rows = cursor.execute(
                f"""
                SELECT sva.show_id, sva.city_id, sva.venue_id,
                       c.name as city_name, c.country as city_country, c.continent as city_continent,
                       v.name as venue_name, v.venue_tier as venue_tier, v.capacity as venue_capacity, v.cost as venue_cost
                FROM show_venue_assignments sva
                LEFT JOIN cities c ON c.city_id = sva.city_id
                LEFT JOIN venues v ON v.venue_id = sva.venue_id
                WHERE sva.show_id IN ({placeholders})
                """,
                show_ids,
            ).fetchall()
            by_id = {r["show_id"]: dict(r) for r in rows}
            for s in merged:
                a = by_id.get(s.get("show_id"))
                if not a:
                    continue
                s["venue_assignment"] = a
                if a.get("city_name"):
                    s["city"] = a["city_name"]
                if a.get("venue_name"):
                    s["venue"] = a["venue_name"]
    except Exception:
        pass

    return jsonify(
        {
            "success": True,
            "start": start,
            "limit": limit,
            "total_generated": len(universe.calendar.generated_shows),
            "shows": merged,
        }
    )
