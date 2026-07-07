"""
show_production_routes.py  —  Steps 58-72
Complete rewrite v4: all frontend field contracts honoured, no column mismatches.
"""

import json
import importlib
import uuid
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app
import traceback

show_production_bp = Blueprint('show_production', __name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _universe():
    return current_app.config['UNIVERSE']

def _db():
    return current_app.config['DATABASE']

def _game_state():
    gs = _db().get_game_state()
    return gs.get('current_year', 1), gs.get('current_week', 1)


def _load_symbol(module_name, symbol_name):
    """
    Resolve lazily imported symbols with a reload fallback.
    This keeps long-running dev servers resilient when modules were edited
    after the Flask process first imported them.
    """
    module = importlib.import_module(module_name)
    if not hasattr(module, symbol_name):
        module = importlib.reload(module)
    return getattr(module, symbol_name)


def _show_config(symbol_name):
    return _load_symbol('models.show_config', symbol_name)


def _show_production(symbol_name):
    return _load_symbol('simulation.show_production', symbol_name)

# ---------------------------------------------------------------------------
# Bootstrap extra tables (called lazily – show_production_db.py owns dark_matches
# so we only add what it doesn't cover)
# ---------------------------------------------------------------------------

_tables_ensured = False

def _ensure_tables():
    global _tables_ensured
    if _tables_ensured:
        return
    db = _db()
    db.conn.cursor().executescript("""
        CREATE TABLE IF NOT EXISTS show_production_plans (
            plan_id           TEXT PRIMARY KEY,
            show_id           TEXT NOT NULL,
            brand             TEXT NOT NULL,
            year              INTEGER NOT NULL,
            week              INTEGER NOT NULL,
            theme             TEXT DEFAULT 'standard',
            opening_segment   TEXT DEFAULT 'hot_match',
            runtime_minutes   INTEGER DEFAULT 120,
            commercial_breaks INTEGER DEFAULT 8,
            ppv_buildup_score INTEGER DEFAULT 0,
            notes             TEXT DEFAULT '',
            created_at        TEXT NOT NULL,
            updated_at        TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS house_shows (
            house_show_id     TEXT PRIMARY KEY,
            brand             TEXT NOT NULL,
            venue             TEXT NOT NULL,
            city              TEXT NOT NULL,
            year              INTEGER NOT NULL,
            week              INTEGER NOT NULL,
            projected_revenue INTEGER DEFAULT 0,
            actual_revenue    INTEGER DEFAULT 0,
            status            TEXT DEFAULT 'planned',
            show_card         TEXT DEFAULT '[]',
            created_at        TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS production_debuts (
            debut_id        TEXT PRIMARY KEY,
            wrestler_id     TEXT NOT NULL,
            wrestler_name   TEXT NOT NULL,
            show_id         TEXT NOT NULL,
            year            INTEGER NOT NULL,
            week            INTEGER NOT NULL,
            debut_type      TEXT DEFAULT 'surprise',
            target_feud_id  TEXT DEFAULT '',
            angle_summary   TEXT DEFAULT '',
            status          TEXT DEFAULT 'planned',
            created_at      TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS debut_secrecy_tracking (
            secrecy_id       TEXT PRIMARY KEY,
            wrestler_id      TEXT NOT NULL,
            signing_year     INTEGER NOT NULL,
            signing_week     INTEGER NOT NULL,
            leaked           INTEGER NOT NULL DEFAULT 0,
            leak_week        INTEGER,
            debut_year       INTEGER,
            debut_week       INTEGER,
            secrecy_weeks    INTEGER NOT NULL DEFAULT 0,
            multiplier       REAL NOT NULL DEFAULT 1.0,
            created_at       TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS production_returns (
            return_id       TEXT PRIMARY KEY,
            wrestler_id     TEXT NOT NULL,
            wrestler_name   TEXT NOT NULL,
            show_id         TEXT NOT NULL,
            year            INTEGER NOT NULL,
            week            INTEGER NOT NULL,
            return_type     TEXT DEFAULT 'surprise',
            angle_summary   TEXT DEFAULT '',
            pop_score       INTEGER DEFAULT 50,
            status          TEXT DEFAULT 'planned',
            created_at      TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS production_run_ins (
            run_in_id       TEXT PRIMARY KEY,
            show_id         TEXT NOT NULL,
            year            INTEGER NOT NULL,
            week            INTEGER NOT NULL,
            feud_id         TEXT NOT NULL,
            interferer_id   TEXT DEFAULT '',
            interferer_name TEXT DEFAULT '',
            target_match_id TEXT DEFAULT '',
            outcome         TEXT DEFAULT 'pending',
            created_at      TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_house_shows_brand ON house_shows(brand, year, week);
        CREATE INDEX IF NOT EXISTS idx_debuts_status     ON production_debuts(status);
        CREATE INDEX IF NOT EXISTS idx_returns_status    ON production_returns(status);

        CREATE TABLE IF NOT EXISTS custom_ppvs (
            custom_ppv_id    TEXT PRIMARY KEY,
            name             TEXT NOT NULL,
            year             INTEGER NOT NULL,
            week             INTEGER NOT NULL,
            day_of_week      TEXT NOT NULL DEFAULT 'Sunday',
            tier             TEXT NOT NULL DEFAULT 'minor',
            location         TEXT NOT NULL DEFAULT '',
            brand            TEXT NOT NULL DEFAULT 'Cross-Brand',
            status           TEXT NOT NULL DEFAULT 'active',
            created_at       TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS cinematic_matches (
            cinematic_id      TEXT PRIMARY KEY,
            show_id           TEXT NOT NULL,
            year              INTEGER NOT NULL,
            week              INTEGER NOT NULL,
            title             TEXT NOT NULL,
            location          TEXT NOT NULL,
            script_quality    INTEGER NOT NULL,
            production_value  INTEGER NOT NULL,
            acting_quality    INTEGER NOT NULL,
            originality       INTEGER NOT NULL,
            overall_rating    REAL NOT NULL,
            notes             TEXT DEFAULT '',
            created_at        TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS long_term_story_arcs (
            arc_id             TEXT PRIMARY KEY,
            name               TEXT NOT NULL,
            start_year         INTEGER NOT NULL,
            start_week         INTEGER NOT NULL,
            planned_end_year   INTEGER NOT NULL,
            planned_end_week   INTEGER NOT NULL,
            current_phase      TEXT NOT NULL DEFAULT 'setup',
            beats_json         TEXT NOT NULL DEFAULT '[]',
            status             TEXT NOT NULL DEFAULT 'active',
            unresolved_penalty INTEGER NOT NULL DEFAULT 0,
            created_at         TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS twist_swerve_events (
            swerve_id           TEXT PRIMARY KEY,
            show_id             TEXT NOT NULL,
            year                INTEGER NOT NULL,
            week                INTEGER NOT NULL,
            title               TEXT NOT NULL,
            surprise_rating     INTEGER NOT NULL,
            logic_rating        INTEGER NOT NULL,
            follow_through      INTEGER NOT NULL,
            trust_impact        INTEGER NOT NULL,
            created_at          TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS main_event_quality_history (
            record_id             TEXT PRIMARY KEY,
            show_id               TEXT NOT NULL,
            year                  INTEGER NOT NULL,
            week                  INTEGER NOT NULL,
            match_title           TEXT NOT NULL,
            quality_score         REAL NOT NULL,
            draw_score            REAL NOT NULL,
            placement_correctness REAL NOT NULL,
            legacy_impact         REAL NOT NULL,
            created_at            TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS pacing_sessions (
            session_id           TEXT PRIMARY KEY,
            show_id              TEXT NOT NULL,
            year                 INTEGER NOT NULL,
            week                 INTEGER NOT NULL,
            show_type            TEXT NOT NULL,
            brand                TEXT NOT NULL,
            target_peaks         INTEGER NOT NULL DEFAULT 3,
            final_grade          TEXT DEFAULT '',
            final_crowd_energy   INTEGER DEFAULT 50,
            peaks_hit            INTEGER DEFAULT 0,
            status               TEXT NOT NULL DEFAULT 'draft',
            created_at           TEXT NOT NULL,
            updated_at           TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS pacing_session_items (
            item_id              TEXT PRIMARY KEY,
            session_id           TEXT NOT NULL,
            position             INTEGER NOT NULL,
            item_type            TEXT NOT NULL,
            item_name            TEXT NOT NULL,
            duration_minutes     INTEGER NOT NULL,
            star_rating          REAL DEFAULT 0,
            segment_type         TEXT DEFAULT '',
            crowd_energy_before  INTEGER NOT NULL,
            crowd_energy_after   INTEGER NOT NULL,
            momentum_delta       INTEGER NOT NULL,
            created_at           TEXT NOT NULL
        );
    """)
    db.conn.commit()
    _tables_ensured = True


def _sync_custom_ppvs_into_calendar():
    """Inject custom PPVs from DB into in-memory calendar for current process."""
    _ensure_tables()
    from models.calendar import ScheduledShow
    rows = _db().conn.execute(
        "SELECT * FROM custom_ppvs WHERE status='active' ORDER BY year, week"
    ).fetchall()
    cal = _universe().calendar
    by_id = {s.show_id: s for s in cal.generated_shows}
    for r in rows:
        row = dict(r)
        show_id = f"custom_ppv_{row['custom_ppv_id']}"
        if show_id in by_id:
            continue
        cal.generated_shows.append(ScheduledShow(
            show_id=show_id,
            year=int(row['year']),
            week=int(row['week']),
            day_of_week=row.get('day_of_week', 'Sunday'),
            brand=row.get('brand', 'Cross-Brand'),
            name=row['name'],
            show_type='major_ppv' if row.get('tier') == 'major' else 'minor_ppv',
            is_ppv=True,
            tier=row.get('tier', 'minor'),
            location=row.get('location', ''),
        ))
    cal.generated_shows.sort(key=lambda s: (s.year, s.week, {"Monday": 1, "Friday": 2, "Saturday": 3, "Sunday": 4}.get(s.day_of_week, 9)))


# ---------------------------------------------------------------------------
# Dark-match helper — reads from show_production_db's table and normalises
# every row to the exact shape the frontend expects:
#   dm.match_type  ('pre_show' | 'post_show')
#   dm.side_a      (list of names)
#   dm.side_b      (list of names)
#   dm.duration_minutes, dm.purpose
# ---------------------------------------------------------------------------

def _normalise_dm_row(row: dict) -> dict:
    row['side_a_ids']   = json.loads(row.get('side_a_ids')   or '[]')
    row['side_a_names'] = json.loads(row.get('side_a_names') or '[]')
    row['side_b_ids']   = json.loads(row.get('side_b_ids')   or '[]')
    row['side_b_names'] = json.loads(row.get('side_b_names') or '[]')
    row['side_a']       = row['side_a_names']   # frontend alias
    row['side_b']       = row['side_b_names']   # frontend alias
    row['match_type']   = 'pre_show' if row.get('is_pre_show', 1) else 'post_show'
    return row


@show_production_bp.route('/api/show-production/dashboard')
def api_show_production_dashboard():
    universe = _universe()
    try:
        current_show = universe.calendar.get_current_show()
        upcoming_ppvs = universe.calendar.get_upcoming_ppvs(5)

        weekly_schedule = []
        seen_brands = set()
        generated_shows = getattr(universe.calendar, 'generated_shows', []) or []
        for show in generated_shows:
            if show.show_type != 'weekly_tv' or show.brand in seen_brands:
                continue
            seen_brands.add(show.brand)
            weekly_schedule.append({
                'brand': show.brand,
                'day': getattr(show, 'day_of_week', getattr(show, 'day', 'TBD')),
                'start_time': getattr(show, 'time_slot', None) or 'Prime Time',
                'duration_minutes': 120 if show.brand != 'ROC Vanguard' else 90,
            })

        theme_catalogue = [
            {
                'value': 'standard',
                'display_name': 'Standard Show',
                'description': 'Balanced weekly episode with normal stakes.',
            },
            {
                'value': 'anniversary',
                'display_name': 'Anniversary Special',
                'description': 'Legacy-focused episode with celebratory presentation.',
            },
            {
                'value': 'extreme',
                'display_name': 'Extreme Rules',
                'description': 'Higher-risk stipulations and violent energy.',
            },
            {
                'value': 'draft',
                'display_name': 'Draft Night',
                'description': 'Roster movement and brand-defining announcements.',
            },
        ]
        segment_types = [
            {'type': 'match', 'display_name': 'Standard Match'},
            {'type': 'promo', 'display_name': 'Promo Segment'},
            {'type': 'interview', 'display_name': 'Backstage Interview'},
            {'type': 'vignette', 'display_name': 'Vignette'},
            {'type': 'contract_signing', 'display_name': 'Contract Signing'},
            {'type': 'talk_show', 'display_name': 'Talk Show Segment'},
            {'type': 'run_in', 'display_name': 'Run-In / Interference'},
            {'type': 'debut', 'display_name': 'Debut / Return Angle'},
        ]
        supercard_templates = {
            'Victory Dome': {
                'min_matches': 9,
                'must_have_title_matches': 3,
            },
            'Champions Summit': {
                'min_matches': 7,
                'must_have_title_matches': 2,
            },
            'Legacy Finale': {
                'min_matches': 8,
                'must_have_title_matches': 2,
            },
        }

        return jsonify({
            'success': True,
            'overview': {
                'current_show': current_show.to_dict() if current_show else None,
                'weekly_schedule': weekly_schedule,
                'upcoming_ppvs': [ppv.to_dict() for ppv in upcoming_ppvs],
                'supercards': supercard_templates,
                'segment_type_count': len(segment_types),
                'theme_count': len(theme_catalogue),
            },
            'segment_types': segment_types,
            'themes': theme_catalogue,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# ===========================================================================
# STEP 58 — Weekly schedule / time slots
# ===========================================================================

@show_production_bp.route('/api/show-production/weekly-schedule')
def api_weekly_schedule():
    try:
        from models.show_config import BRAND_TIME_SLOTS, TARGET_MATCH_COUNTS
        schedule = []
        for brand, slot in BRAND_TIME_SLOTS.items():
            target = TARGET_MATCH_COUNTS.get("weekly_tv", {})
            schedule.append({
                **slot.to_dict(),
                "target_matches": target.get("target", 5),
                "min_matches":    target.get("min", 4),
                "max_matches":    target.get("max", 6),
            })
        return jsonify({"success": True, "weekly_schedule": schedule})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@show_production_bp.route('/api/show-production/time-slots')
def api_time_slots():
    try:
        from models.show_config import BRAND_TIME_SLOTS, SHOW_TYPE_DURATIONS
        return jsonify({
            "success": True,
            "brand_time_slots":   {b: s.to_dict() for b, s in BRAND_TIME_SLOTS.items()},
            "show_type_durations": SHOW_TYPE_DURATIONS,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ===========================================================================
# STEP 59 — PPV calendar
# ===========================================================================

@show_production_bp.route('/api/show-production/ppv-calendar')
def api_ppv_calendar():
    universe = _universe()
    try:
        ppvs = universe.calendar.get_upcoming_ppvs(8)
        active_feuds  = universe.feud_manager.get_active_feuds()
        current_show  = universe.calendar.get_current_show()
        ppv_data = []
        for ppv in ppvs:
            brand_feuds = [f for f in active_feuds if ppv.brand == "Cross-Brand" or any(
                universe.get_wrestler_by_id(pid) and
                universe.get_wrestler_by_id(pid).primary_brand == ppv.brand
                for pid in f.participant_ids
            )]
            avg_int = sum(f.intensity for f in brand_feuds) / len(brand_feuds) if brand_feuds else 0
            ppv_data.append({
                **ppv.to_dict(),
                "buildup_score":     int(avg_int),
                "weeks_away":        (ppv.week - current_show.week) if current_show else 0,
                "active_feuds_count": len(brand_feuds),
                "hot_feuds_count":   len([f for f in brand_feuds if f.intensity >= 70]),
            })
        return jsonify({"success": True, "ppv_calendar": ppv_data})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# ===========================================================================
# STEP 60 — House show tours
# Frontend expects:
#   d.tour.tour_name, d.tour.event_count, d.tour.scheduled_events[]
#   each event: {week, venue, city, expected_attendance, ticket_price}
#   d.projected_revenue: {gross_revenue, production_cost, net_profit, total_attendance}
# ===========================================================================

# Cities available per brand for the frontend city-picker
BRAND_CITIES = {
    "ROC Alpha":    ["New York", "Los Angeles", "Chicago", "Houston", "Philadelphia",
                     "Boston", "Miami", "Atlanta", "Denver", "Seattle"],
    "ROC Velocity": ["Dallas", "Phoenix", "San Antonio", "San Diego", "Orlando",
                     "Nashville", "Portland", "Indianapolis", "Columbus", "Austin"],
    "ROC Vanguard": ["Las Vegas", "Detroit", "Minneapolis", "Toronto", "Montreal",
                     "Cleveland", "Pittsburgh", "Sacramento", "Memphis", "Baltimore"],
}

@show_production_bp.route('/api/show-production/house-show/cities')
def api_house_show_cities():
    """Return the selectable city list for a brand."""
    brand = request.args.get('brand', 'ROC Alpha')
    continent = request.args.get('continent')
    try:
        from persistence.venue_db import list_cities
        db = _db()
        cities = list_cities(db, continent=continent, limit=250)
        names = [c["name"] for c in cities]
        return jsonify({"success": True, "brand": brand, "cities": names})
    except Exception:
        return jsonify({"success": True, "brand": brand, "cities": BRAND_CITIES.get(brand, [])})


@show_production_bp.route('/api/show-production/house-show/plan', methods=['POST'])
def api_plan_house_show_tour():
    universe = _universe()
    db = _db()
    try:
        _ensure_tables()
        from simulation.show_production import house_show_tour_manager

        data         = request.get_json() or {}
        brand         = data.get("brand", "ROC Alpha")
        duration_weeks = int(data.get("duration_weeks", 4))
        # Cities may be supplied by the frontend; otherwise use brand defaults
        req_cities   = data.get("cities") or []

        default_cities = BRAND_CITIES.get(brand, ["Regional City"] * 10)
        # Pad/trim to duration_weeks
        city_pool = (req_cities + default_cities * 2)[:duration_weeks]

        current_show = universe.calendar.get_current_show()
        start_year   = current_show.year if current_show else 1
        start_week   = (current_show.week + 1) if current_show else 1

        # Call sim
        schedule = house_show_tour_manager.plan_tour(
            brand=brand,
            start_year=start_year,
            start_week=start_week,
            duration_weeks=duration_weeks,
        )

        # calculate_tour_revenue may return dict or number
        raw_rev = house_show_tour_manager.calculate_tour_revenue(schedule)
        if isinstance(raw_rev, dict):
            rev_dict = raw_rev
            gross = int(rev_dict.get('gross_revenue', rev_dict.get('total_revenue', 0)))
        else:
            gross = int(raw_rev)
            rev_dict = {}

        if not rev_dict:
            cost   = int(gross * 0.35)
            profit = gross - cost
            rev_dict = {
                "gross_revenue":   gross,
                "production_cost": cost,
                "net_profit":      profit,
                "total_attendance": max(1, gross // 45),
            }
        # Ensure all four keys always present
        rev_dict.setdefault("gross_revenue",    gross)
        rev_dict.setdefault("production_cost",  int(gross * 0.35))
        rev_dict.setdefault("net_profit",       gross - rev_dict["production_cost"])
        rev_dict.setdefault("total_attendance", max(1, gross // 45))

        per_show_rev   = gross // max(duration_weeks, 1)
        per_show_attend = max(1, per_show_rev // 45)

        # Extract individual show entries (handle any schedule shape)
        sim_shows = (
            getattr(schedule, 'shows', None) or
            getattr(schedule, 'scheduled_events', None) or
            []
        )

        now = datetime.now().isoformat()
        saved_shows = []
        cursor = db.conn.cursor()

        # Optional: map requested cities to seeded venue database for nicer/consistent venues
        city_name_to_city_id = {}
        city_id_to_arena_name = {}
        try:
            if city_pool:
                placeholders = ",".join(["?"] * len(set(city_pool)))
                rows = cursor.execute(
                    f"SELECT city_id, name FROM cities WHERE name IN ({placeholders})",
                    list(dict.fromkeys(city_pool)),
                ).fetchall()
                city_name_to_city_id = {r["name"]: r["city_id"] for r in rows}

                if rows:
                    city_ids = [r["city_id"] for r in rows]
                    placeholders2 = ",".join(["?"] * len(city_ids))
                    arena_rows = cursor.execute(
                        f"""
                        SELECT city_id, name FROM venues
                        WHERE city_id IN ({placeholders2}) AND venue_tier='arena'
                        """,
                        city_ids,
                    ).fetchall()
                    city_id_to_arena_name = {r["city_id"]: r["name"] for r in arena_rows}
        except Exception:
            city_name_to_city_id = {}
            city_id_to_arena_name = {}

        for i in range(duration_weeks):
            hs_id   = f"hs_{uuid.uuid4().hex[:8]}"
            city    = city_pool[i] if i < len(city_pool) else "Regional City"
            hs_obj  = sim_shows[i] if i < len(sim_shows) else None

            hs_week   = getattr(hs_obj, 'week',   start_week + i) if hs_obj else start_week + i
            hs_year   = getattr(hs_obj, 'year',   start_year)     if hs_obj else start_year
            venue     = getattr(hs_obj, 'venue',  f"{city} Arena") if hs_obj else f"{city} Arena"
            city_id = city_name_to_city_id.get(city)
            if city_id and city_id in city_id_to_arena_name:
                venue = city_id_to_arena_name[city_id]
            rev       = int(getattr(hs_obj, 'projected_revenue', per_show_rev) if hs_obj else per_show_rev)
            attend    = int(getattr(hs_obj, 'expected_attendance', per_show_attend) if hs_obj else per_show_attend)
            ticket_p  = int(getattr(hs_obj, 'ticket_price', 45) if hs_obj else 45)

            cursor.execute("""
                INSERT OR REPLACE INTO house_shows
                (house_show_id, brand, venue, city, year, week,
                 projected_revenue, actual_revenue, status, show_card, created_at)
                VALUES (?,?,?,?,?,?,?,0,'planned','[]',?)
            """, (hs_id, brand, venue, city, hs_year, hs_week, rev, now))

            # Inject into in-memory calendar for Booking page
            try:
                from models.calendar import ScheduledShow
                cal = ScheduledShow(
                    show_id=hs_id, year=hs_year, week=hs_week, day_of_week="Saturday",
                    brand=brand, name=f"{brand} House Show — {city}",
                    show_type="house_show", is_ppv=False,
                    tier="house",
                )
                if hs_id not in {s.show_id for s in universe.calendar.generated_shows}:
                    universe.calendar.generated_shows.append(cal)
            except Exception:
                pass

            saved_shows.append({
                "house_show_id":      hs_id,
                "brand":              brand,
                "venue":              venue,
                "city":               city,
                "year":               hs_year,
                "week":               hs_week,
                "projected_revenue":  rev,
                "expected_attendance": attend,
                "ticket_price":       ticket_p,
            })

        db.conn.commit()

        # Build tour dict exactly matching frontend keys
        tour_dict = {
            "tour_name": f"{brand} House Show Tour",
            "event_count": len(saved_shows),
            "scheduled_events": [
                {
                    "week":               s["week"],
                    "venue":              s["venue"],
                    "city":               s["city"],
                    "expected_attendance": s["expected_attendance"],
                    "ticket_price":       s["ticket_price"],
                }
                for s in saved_shows
            ],
        }

        return jsonify({
            "success": True,
            "message": f"{len(saved_shows)} house show(s) planned and added to the Booking calendar.",
            "tour":              tour_dict,
            "saved_shows":       saved_shows,
            "projected_revenue": rev_dict,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@show_production_bp.route('/api/show-production/house-show/list')
def api_house_show_list():
    db = _db()
    try:
        _ensure_tables()
        cursor = db.conn.cursor()
        year  = request.args.get('year',  type=int)
        brand = request.args.get('brand')
        clauses, params = [], []
        if year:  clauses.append("year=?");  params.append(year)
        if brand: clauses.append("brand=?"); params.append(brand)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        cursor.execute(f"SELECT * FROM house_shows {where} ORDER BY year,week", params)
        shows = [dict(r) for r in cursor.fetchall()]
        return jsonify({"success": True, "total": len(shows), "house_shows": shows})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@show_production_bp.route('/api/show-production/house-show/<hs_id>/card', methods=['POST'])
def api_book_house_show_card(hs_id):
    db = _db()
    try:
        _ensure_tables()
        card = (request.get_json() or {}).get("card", [])
        db.conn.cursor().execute(
            "UPDATE house_shows SET show_card=? WHERE house_show_id=?",
            (json.dumps(card), hs_id)
        )
        db.conn.commit()
        return jsonify({"success": True, "house_show_id": hs_id, "card": card})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@show_production_bp.route('/api/show-production/house-show/<hs_id>/location', methods=['PUT'])
def api_update_house_show_location(hs_id):
    """Update a planned house show's city/venue (for Calendar edits)."""
    db = _db()
    try:
        _ensure_tables()
        data = request.get_json() or {}
        city = data.get("city")
        venue = data.get("venue")
        if not city and not venue:
            return jsonify({"success": False, "error": "city or venue is required"}), 400

        sets, params = [], []
        if city:
            sets.append("city=?")
            params.append(city)
        if venue:
            sets.append("venue=?")
            params.append(venue)
        params.append(hs_id)

        db.conn.cursor().execute(
            f"UPDATE house_shows SET {', '.join(sets)} WHERE house_show_id=?",
            params,
        )
        db.conn.commit()
        return jsonify({"success": True, "house_show_id": hs_id, "city": city, "venue": venue})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@show_production_bp.route('/api/show-production/house-show/<hs_id>/complete', methods=['POST'])
def api_complete_house_show(hs_id):
    db = _db()
    try:
        _ensure_tables()
        actual_revenue = int((request.get_json() or {}).get("actual_revenue", 0))
        cursor = db.conn.cursor()
        cursor.execute(
            "UPDATE house_shows SET status='completed', actual_revenue=? WHERE house_show_id=?",
            (actual_revenue, hs_id)
        )
        gs          = db.get_game_state()
        new_balance = gs.get('balance', 0) + actual_revenue
        db.update_game_state(balance=new_balance)
        db.conn.commit()
        return jsonify({"success": True, "house_show_id": hs_id,
                        "actual_revenue": actual_revenue, "new_balance": new_balance})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@show_production_bp.route('/api/show-production/house-show/venues')
def api_house_show_venues():
    try:
        from simulation.show_production import HOUSE_SHOW_VENUES
        return jsonify({"success": True, "venues": HOUSE_SHOW_VENUES})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ===========================================================================
# STEP 61 — Supercard requirements
# ===========================================================================

@show_production_bp.route('/api/show-production/supercard/requirements')
def api_supercard_requirements():
    try:
        from simulation.show_production import SUPERCARD_REQUIREMENTS
        return jsonify({"success": True, "supercard_requirements": SUPERCARD_REQUIREMENTS})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@show_production_bp.route('/api/show-production/supercard/requirements/<show_name>')
def api_supercard_requirements_for_show(show_name):
    try:
        from simulation.show_production import get_supercard_requirements
        return jsonify({"success": True, "show_name": show_name,
                        "requirements": get_supercard_requirements(show_name)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ===========================================================================
# STEP 62 — Segment type catalogue
# ===========================================================================

@show_production_bp.route('/api/show-production/segment-types')
def api_segment_type_catalogue():
    try:
        SEGMENT_TYPE_CATALOGUE = _show_config('SEGMENT_TYPE_CATALOGUE')
        opening_only = request.args.get("opening_only", "false").lower() == "true"
        ppv_only     = request.args.get("ppv_only",     "false").lower() == "true"
        types = []
        for cfg in SEGMENT_TYPE_CATALOGUE.values():
            if opening_only and not cfg.suitable_for_opening: continue
            if ppv_only     and not cfg.ppv_only:             continue
            types.append(cfg.to_dict())
        return jsonify({"success": True, "total": len(types), "segment_types": types})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# ===========================================================================
# STEP 63 — Show pacing
# ===========================================================================

@show_production_bp.route('/api/show-production/pacing/analyze', methods=['POST'])
def api_analyze_show_pacing():
    try:
        ShowPacingManager = _show_config('ShowPacingManager')
        data      = request.get_json() or {}
        show_type = data.get("show_type", "weekly_tv")
        brand     = data.get("brand",     "ROC Alpha")
        items     = data.get("items",     [])
        pacing    = ShowPacingManager(show_type=show_type, brand=brand)
        for i, item in enumerate(items):
            pacing.record_item(
                position=i + 1,
                item_type=item.get("type", "match"),
                item_name=item.get("name", f"Item {i+1}"),
                duration_minutes=item.get("duration", 10),
                star_rating=item.get("star_rating", 0.0),
                segment_type=item.get("segment_type"),
            )
            if pacing.should_take_commercial_break():
                pacing.take_commercial_break()
        return jsonify({"success": True, "pacing_report": pacing.to_dict()})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@show_production_bp.route('/api/show-production/pacing/session/create', methods=['POST'])
def api_create_pacing_session():
    try:
        _ensure_tables()
        year, week = _game_state()
        cs = _universe().calendar.get_current_show()
        data = request.get_json() or {}
        session_id = f"pace_{uuid.uuid4().hex[:10]}"
        show_type = data.get("show_type", getattr(cs, "show_type", "weekly_tv"))
        brand = data.get("brand", getattr(cs, "brand", "ROC Alpha"))
        show_id = data.get("show_id", getattr(cs, "show_id", f"show_y{year}_w{week}"))
        now = datetime.utcnow().isoformat()
        _db().conn.execute("""
            INSERT INTO pacing_sessions
            (session_id, show_id, year, week, show_type, brand, target_peaks, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'draft', ?, ?)
        """, (session_id, show_id, year, week, show_type, brand, int(data.get("target_peaks", 3)), now, now))
        _db().conn.commit()
        return jsonify({"success": True, "session_id": session_id})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@show_production_bp.route('/api/show-production/pacing/session/<session_id>/add-item', methods=['POST'])
def api_add_pacing_item(session_id):
    try:
        _ensure_tables()
        ShowPacingManager = _show_config('ShowPacingManager')
        conn = _db().conn
        s = conn.execute("SELECT * FROM pacing_sessions WHERE session_id=?", (session_id,)).fetchone()
        if not s:
            return jsonify({"success": False, "error": "Session not found"}), 404
        rows = conn.execute("SELECT * FROM pacing_session_items WHERE session_id=? ORDER BY position", (session_id,)).fetchall()
        pacing = ShowPacingManager(show_type=s['show_type'], brand=s['brand'])
        for r in rows:
            pacing.record_item(position=r['position'], item_type=r['item_type'], item_name=r['item_name'], duration_minutes=r['duration_minutes'], star_rating=r['star_rating'], segment_type=r['segment_type'] or None)
            if pacing.should_take_commercial_break():
                pacing.take_commercial_break()
        data = request.get_json() or {}
        pos = len(rows) + 1
        before = int(getattr(pacing, "crowd_energy", 50))
        pacing.record_item(position=pos, item_type=data.get("item_type", "segment"), item_name=data.get("item_name", f"Segment {pos}"), duration_minutes=int(data.get("duration_minutes", 8)), star_rating=float(data.get("star_rating", 0.0)), segment_type=data.get("segment_type"))
        after = int(getattr(pacing, "crowd_energy", before))
        delta = after - before
        item_id = f"pace_item_{uuid.uuid4().hex[:10]}"
        conn.execute("""INSERT INTO pacing_session_items
            (item_id, session_id, position, item_type, item_name, duration_minutes, star_rating, segment_type, crowd_energy_before, crowd_energy_after, momentum_delta, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (item_id, session_id, pos, data.get("item_type", "segment"), data.get("item_name", f"Segment {pos}"), int(data.get("duration_minutes", 8)), float(data.get("star_rating", 0.0)), data.get("segment_type", ""), before, after, delta, datetime.utcnow().isoformat()))
        conn.execute("UPDATE pacing_sessions SET updated_at=? WHERE session_id=?", (datetime.utcnow().isoformat(), session_id))
        conn.commit()
        return jsonify({"success": True, "item_id": item_id, "energy_before": before, "energy_after": after, "momentum_delta": delta, "pacing_report": pacing.to_dict()})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# ===========================================================================
# STEP 65 — Run-ins
# ===========================================================================

@show_production_bp.route('/api/show-production/run-in/generate', methods=['POST'])
def api_generate_run_in():
    universe = _universe()
    db = _db()
    try:
        _ensure_tables()
        from simulation.show_production import run_in_manager
        data      = request.get_json() or {}
        brand     = data.get("brand",     "ROC Alpha")
        match_id  = data.get("match_id",  "match_1")
        show_type = data.get("show_type", "weekly_tv")
        is_ppv    = data.get("is_ppv",    False)
        save_it   = data.get("save",      True)

        year, week   = _game_state()
        current_show = universe.calendar.get_current_show()
        show_id      = current_show.show_id if current_show else "unknown"

        active_feuds = universe.feud_manager.get_active_feuds()
        if brand != "Cross-Brand":
            active_feuds = [f for f in active_feuds if any(
                universe.get_wrestler_by_id(pid) and
                universe.get_wrestler_by_id(pid).primary_brand == brand
                for pid in f.participant_ids
            )]

        hot_feuds = sorted([f for f in active_feuds if f.intensity >= 50],
                           key=lambda f: f.intensity, reverse=True)
        if not hot_feuds:
            return jsonify({"success": False, "message": "No feuds hot enough for a run-in."})

        if not run_in_manager.should_book_run_in(
            show_type=show_type, current_run_in_count=0,
            active_feuds=hot_feuds, is_ppv=is_ppv
        ):
            return jsonify({"success": False, "message": "Run-in not recommended for this show."})

        run_in = run_in_manager.book_run_in(
            feud=hot_feuds[0], match_id=match_id,
            all_wrestlers=universe.get_active_wrestlers(),
        )
        ri_dict = run_in.to_dict() if run_in else None

        if run_in and save_it:
            now = datetime.now().isoformat()
            db.conn.cursor().execute("""
                INSERT OR REPLACE INTO production_run_ins
                (run_in_id, show_id, year, week, feud_id,
                 interferer_id, interferer_name, target_match_id, outcome, created_at)
                VALUES (?,?,?,?,?,?,?,?,'planned',?)
            """, (
                ri_dict.get('run_in_id', uuid.uuid4().hex[:8]),
                show_id, year, week, hot_feuds[0].id,
                ri_dict.get('interferer_id',   ''),
                ri_dict.get('interferer_name', ''),
                match_id, now,
            ))
            db.conn.commit()

        return jsonify({"success": True, "run_in": ri_dict,
                        "saved": save_it and run_in is not None})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# ===========================================================================
# STEP 66 — Debuts
# ===========================================================================

@show_production_bp.route('/api/show-production/debut/candidates')
def api_debut_candidates():
    try:
        _ensure_tables()
        fa_pool    = current_app.config.get('FREE_AGENT_POOL')
        candidates = []

        # From free-agent pool
        if fa_pool:
            for fa in getattr(fa_pool, 'available_free_agents', []):
                if not getattr(fa, 'discovered', False):
                    continue
                candidates.append({
                    "id":         getattr(fa, 'free_agent_id', getattr(fa, 'id', '')),
                    "name":       getattr(fa, 'wrestler_name', getattr(fa, 'name', 'Unknown')),
                    "age":        getattr(fa, 'age',           0),
                    "role":       getattr(fa, 'role',          'Unknown'),
                    "alignment":  getattr(fa, 'alignment',     'neutral'),
                    "popularity": getattr(fa, 'popularity',    50),
                    "overall":    getattr(fa, 'overall',       getattr(fa, 'overall_rating', 70)),
                    "is_prospect": getattr(fa, 'is_prospect',  False),
                    "source":     "free_agent",
                })

        # Also developmental/unsigned roster members
        cursor = _db().conn.cursor()
        cursor.execute("SELECT wrestler_id FROM production_debuts WHERE status='planned'")
        planned_ids = {r['wrestler_id'] for r in cursor.fetchall()}

        for w in getattr(_universe(), 'wrestlers', []):
            if w.id in planned_ids:
                continue
            if getattr(w, 'status', 'active') in ('developmental', 'unsigned'):
                candidates.append({
                    "id":         w.id,
                    "name":       w.name,
                    "age":        getattr(w, 'age',           0),
                    "role":       getattr(w, 'role',          'Unknown'),
                    "alignment":  getattr(w, 'alignment',     'neutral'),
                    "popularity": getattr(w, 'popularity',    50),
                    "overall":    getattr(w, 'overall_rating', 70),
                    "is_prospect": True,
                    "source":     "developmental",
                })

        return jsonify({"success": True, "total": len(candidates),
                        "debut_candidates": candidates})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@show_production_bp.route('/api/show-production/debut/plan', methods=['POST'])
def api_plan_debut():
    universe = _universe()
    db = _db()
    try:
        _ensure_tables()
        from simulation.show_production import surprise_debut_manager
        data       = request.get_json() or {}
        wid        = data.get("wrestler_id")
        show_type  = data.get("show_type", "weekly_tv")
        if not wid:
            return jsonify({"success": False, "error": "wrestler_id required"}), 400

        year, week   = _game_state()
        current_show = universe.calendar.get_current_show()
        show_id      = current_show.show_id if current_show else "unknown"

        wrestler      = universe.get_wrestler_by_id(wid)
        wrestler_name = "Unknown"
        if wrestler:
            wrestler_name = wrestler.name
        else:
            fa_pool = current_app.config.get('FREE_AGENT_POOL')
            if fa_pool:
                for fa in getattr(fa_pool, 'available_free_agents', []):
                    fa_id = getattr(fa, 'free_agent_id', getattr(fa, 'id', ''))
                    if fa_id == wid:
                        wrestler_name = getattr(fa, 'wrestler_name', getattr(fa, 'name', 'Unknown'))
                        wrestler = fa
                        break

        if not wrestler:
            return jsonify({"success": False, "error": "Wrestler not found"}), 404

        # Safe defaults — every field the frontend accesses with .replace()
        angle_dict = {
            "wrestler_id":     wid,
            "wrestler_name":   wrestler_name,
            "show_id":         show_id,
            "debut_type":      "surprise",
            "crowd_reaction":  "mixed",
            "momentum_boost":  10,
            "popularity_boost": 5,
            "target_name":     None,
            "creates_feud":    False,
            "summary":         f"Surprise debut at {show_id}",
        }
        target_feud_id = ""
        try:
            angle = surprise_debut_manager.plan_debut(
                new_wrestler=wrestler,
                show_type=show_type,
                existing_feuds=universe.feud_manager.get_active_feuds(),
                active_roster=universe.get_active_wrestlers(),
            )
            sim = angle.to_dict()
            angle_dict.update(sim)
            # Guarantee string fields never None (frontend calls .replace())
            angle_dict['debut_type']     = str(angle_dict.get('debut_type')     or 'surprise')
            angle_dict['crowd_reaction'] = str(angle_dict.get('crowd_reaction') or 'mixed')
            target_feud_id = str(angle_dict.get('target_feud_id') or '')
        except Exception as _sim_err:
            print(f"[debut/plan] sim error (using defaults): {_sim_err}")

        debut_id = f"debut_{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        db.conn.cursor().execute("""
            INSERT INTO production_debuts
            (debut_id, wrestler_id, wrestler_name, show_id, year, week,
             debut_type, target_feud_id, angle_summary, status, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,'planned',?)
        """, (debut_id, wid, wrestler_name, show_id, year, week,
              angle_dict['debut_type'], target_feud_id,
              angle_dict.get('summary', ''), now))
        db.conn.commit()

        return jsonify({"success": True, "debut_id": debut_id, "debut_angle": angle_dict,
                        "saved": True,
                        "message": f"{wrestler_name} debut planned for Week {week}, Year {year}."})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@show_production_bp.route('/api/show-production/debut/list')
def api_debut_list():
    try:
        _ensure_tables()
        status = request.args.get('status', 'planned')
        cursor = _db().conn.cursor()
        if status == 'all':
            cursor.execute("SELECT * FROM production_debuts ORDER BY year DESC, week DESC")
        else:
            cursor.execute("SELECT * FROM production_debuts WHERE status=? ORDER BY year DESC, week DESC", (status,))
        return jsonify({"success": True, "debuts": [dict(r) for r in cursor.fetchall()]})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ===========================================================================
# STEP 67 — Returns
# ===========================================================================

@show_production_bp.route('/api/show-production/return/candidates')
def api_return_candidates():
    universe = _universe()
    db = _db()
    try:
        _ensure_tables()
        return_booking_manager = _show_production('return_booking_manager')
        current_show = universe.calendar.get_current_show()
        cursor = db.conn.cursor()
        cursor.execute("SELECT wrestler_id FROM production_returns WHERE status='planned'")
        planned_ids = {r['wrestler_id'] for r in cursor.fetchall()}

        raw = return_booking_manager.find_return_candidates(
            all_wrestlers=universe.wrestlers,
            show_name=current_show.name if current_show else "",
            is_major_ppv=current_show.is_ppv if current_show else False,
        )
        candidates = []
        for w in raw:
            if w.id in planned_ids:
                continue
            candidates.append({
                "id":               w.id,
                "name":             w.name,
                "age":              getattr(w, 'age', 0),
                "role":             getattr(w, 'role', 'Unknown'),
                "alignment":        getattr(w, 'alignment', 'neutral'),
                "is_retired":       getattr(w, 'is_retired', False),
                "is_injured":       getattr(w, 'is_injured', False),
                "injury_description": (
                    w.injury.description
                    if getattr(w, 'is_injured', False) and
                       hasattr(w, 'injury') and w.injury else None
                ),
            })
        return jsonify({"success": True, "total": len(candidates),
                        "return_candidates": candidates})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@show_production_bp.route('/api/show-production/return/plan', methods=['POST'])
def api_plan_return():
    universe = _universe()
    db = _db()
    try:
        _ensure_tables()
        return_booking_manager = _show_production('return_booking_manager')
        data          = request.get_json() or {}
        wid           = data.get("wrestler_id")
        is_surprise   = data.get("is_surprise", True)
        absence_weeks = int(data.get("absence_weeks", 8))
        show_type     = data.get("show_type", "weekly_tv")
        if not wid:
            return jsonify({"success": False, "error": "wrestler_id required"}), 400

        wrestler = universe.get_wrestler_by_id(wid)
        if not wrestler:
            return jsonify({"success": False, "error": "Wrestler not found"}), 404

        year, week   = _game_state()
        current_show = universe.calendar.get_current_show()
        show_id      = current_show.show_id if current_show else "unknown"

        # Safe defaults matching every frontend .replace() call
        angle_dict = {
            "wrestler_id":     wid,
            "wrestler_name":   wrestler.name,
            "is_surprise":     is_surprise,
            "return_type":     "surprise" if is_surprise else "announced",
            "crowd_reaction":  "pop",
            "absence_weeks":   absence_weeks,
            "momentum_boost":  15,
            "popularity_boost": 8,
            "target_name":     None,
        }
        try:
            angle = return_booking_manager.plan_return(
                returning_wrestler=wrestler,
                absence_weeks=absence_weeks,
                is_surprise=is_surprise,
                active_roster=universe.get_active_wrestlers(),
                active_feuds=universe.feud_manager.get_active_feuds(),
                show_type=show_type,
            )
            sim = angle.to_dict()
            angle_dict.update(sim)
            angle_dict['return_type']    = str(angle_dict.get('return_type')    or 'surprise')
            angle_dict['crowd_reaction'] = str(angle_dict.get('crowd_reaction') or 'pop')
        except Exception as _sim_err:
            print(f"[return/plan] sim error (using defaults): {_sim_err}")

        return_id = f"return_{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        db.conn.cursor().execute("""
            INSERT INTO production_returns
            (return_id, wrestler_id, wrestler_name, show_id, year, week,
             return_type, angle_summary, pop_score, status, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,'planned',?)
        """, (
            return_id, wid, wrestler.name, show_id, year, week,
            angle_dict['return_type'],
            angle_dict.get('summary', ''),
            int(angle_dict.get('expected_pop', angle_dict.get('momentum_boost', 50))),
            now,
        ))
        db.conn.commit()

        return jsonify({"success": True, "return_id": return_id, "return_angle": angle_dict,
                        "saved": True,
                        "message": f"{wrestler.name} return planned for Week {week}, Year {year}."})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@show_production_bp.route('/api/show-production/return/list')
def api_return_list():
    try:
        _ensure_tables()
        status = request.args.get('status', 'planned')
        cursor = _db().conn.cursor()
        if status == 'all':
            cursor.execute("SELECT * FROM production_returns ORDER BY year DESC, week DESC")
        else:
            cursor.execute("SELECT * FROM production_returns WHERE status=? ORDER BY year DESC, week DESC", (status,))
        return jsonify({"success": True, "returns": [dict(r) for r in cursor.fetchall()]})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ===========================================================================
# STEP 68 — Commercial breaks
# ===========================================================================

@show_production_bp.route('/api/show-production/commercial-breaks')
def api_commercial_break_strategy():
    try:
        from models.show_config import CommercialBreakStrategy, BRAND_TIME_SLOTS
        show_type = request.args.get("show_type", "weekly_tv")
        brand     = request.args.get("brand",     "ROC Alpha")
        if show_type in ("major_ppv", "supercard"):
            strategy, count = CommercialBreakStrategy.MINIMAL, 3
            advice = "PPV/Supercard: Minimal breaks to maintain tension."
        elif show_type == "house_show":
            strategy, count = CommercialBreakStrategy.HEAVY, 0
            advice = "House shows are not televised — no commercial breaks."
        else:
            strategy = CommercialBreakStrategy.STANDARD
            slot = BRAND_TIME_SLOTS.get(brand)
            count = slot.commercial_breaks if slot else 8
            advice = f"Standard TV: {count} breaks positioned to maintain tension."
        return jsonify({"success": True, "strategy": strategy.value,
                        "break_count": count, "advice": advice})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ===========================================================================
# STEP 69 — Opening segment
# ===========================================================================

@show_production_bp.route('/api/show-production/opening-segment/recommend')
def api_recommend_opening_segment():
    universe = _universe()
    try:
        from simulation.show_production import opening_segment_selector
        cs = universe.calendar.get_current_show()
        if not cs:
            return jsonify({"success": False, "error": "No show scheduled"}), 404
        brand = cs.brand
        feuds = universe.feud_manager.get_active_feuds()
        if brand != "Cross-Brand":
            feuds = [f for f in feuds if any(
                universe.get_wrestler_by_id(p) and
                universe.get_wrestler_by_id(p).primary_brand == brand
                for p in f.participant_ids
            )]
        has_vacancy = any(
            c.is_vacant for c in universe.championships
            if c.assigned_brand in (brand, "Cross-Brand")
        )
        opening_type, reason = opening_segment_selector.select_opening(
            show_type=cs.show_type, is_ppv=cs.is_ppv,
            active_feuds=feuds, week=cs.week,
            has_returning_star=False, has_title_vacancy=has_vacancy,
        )
        return jsonify({"success": True, "show": cs.to_dict(),
                        "recommended_opening": opening_type.value,
                        "reason": reason,
                        "crowd_energy_impact": opening_segment_selector.get_energy_impact(opening_type)})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# ===========================================================================
# STEP 70 — Main event criteria
# ===========================================================================

@show_production_bp.route('/api/show-production/main-event/criteria')
def api_main_event_criteria():
    universe = _universe()
    try:
        from simulation.show_production import main_event_selector
        cs = universe.calendar.get_current_show()
        if not cs:
            return jsonify({"success": False, "error": "No show scheduled"}), 404
        titles = [c for c in universe.championships
                  if c.assigned_brand in (cs.brand, "Cross-Brand")]
        criteria = main_event_selector.select_main_event_criteria(
            show_type=cs.show_type, is_ppv=cs.is_ppv,
            tier=getattr(cs, 'tier', 'standard'),
            active_feuds=universe.feud_manager.get_active_feuds(),
            brand_titles=titles, show_name=cs.name,
        )
        return jsonify({"success": True, "show": cs.to_dict(),
                        "main_event_criteria": criteria})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# ===========================================================================
# STEP 71 — Dark matches
# Frontend expects each dm: {match_type, side_a[], side_b[], duration_minutes, purpose}
# Persisted in show_production_db's dark_matches table (NOT our own table)
# On load, display previously saved dark matches for selected brand
# ===========================================================================

@show_production_bp.route('/api/show-production/dark-matches/generate', methods=['POST'])
def api_generate_dark_matches():
    universe = _universe()
    db = _db()
    try:
        dark_match_manager = _show_production('dark_match_manager')
        save_dark_match = _load_symbol('persistence.show_production_db', 'save_dark_match')

        data      = request.get_json() or {}
        brand     = data.get("brand",     "ROC Alpha")
        count     = int(data.get("count", 1))
        booked    = set(data.get("booked_wrestler_ids", []))
        save_flag = data.get("save", True)

        year, week   = _game_state()
        current_show = universe.calendar.get_current_show()
        show_id      = current_show.show_id if current_show else f"show_y{year}_w{week}"
        show_name    = current_show.name    if current_show else f"Week {week} Show"

        available = (
            universe.get_wrestlers_by_brand(brand)
            if brand != "Cross-Brand" else universe.get_active_wrestlers()
        )

        raw_matches = dark_match_manager.book_dark_matches(
            available_wrestlers=available,
            show_type=data.get("show_type", "weekly_tv"),
            booked_wrestler_ids=booked,
            year=year, week=week, count=count,
        )

        result = []
        for dm in raw_matches:
            d = dm.to_dict() if hasattr(dm, 'to_dict') else dm

            # Normalise participant fields — sim may use different keys
            side_a_names = (d.get('side_a') or d.get('side_a_names') or
                            ([d['participant_names'][0]] if d.get('participant_names') else []))
            side_b_names = (d.get('side_b') or d.get('side_b_names') or
                            (d.get('participant_names', [])[1:2]))
            side_a_ids   = d.get('side_a_ids', [])
            side_b_ids   = d.get('side_b_ids', [])
            is_pre       = bool(d.get('is_pre_show', True))

            normalised = {
                **d,
                "side_a":          list(side_a_names),
                "side_b":          list(side_b_names),
                "side_a_names":    list(side_a_names),
                "side_b_names":    list(side_b_names),
                "side_a_ids":      list(side_a_ids),
                "side_b_ids":      list(side_b_ids),
                "match_type":      "pre_show" if is_pre else "post_show",
                "duration_minutes": int(d.get('duration_minutes', 8)),
                "purpose":          str(d.get('purpose', 'crowd_warmup')),
                "winner":           str(d.get('winner',  'pending')),
                "finish_type":      str(d.get('finish_type', 'pending')),
                "star_rating":      float(d.get('star_rating', 0.0)),
                "brand":            brand,
            }
            result.append(normalised)

            if save_flag:
                dm_id = f"dm_{uuid.uuid4().hex[:8]}"
                save_dark_match(db, {
                    "dark_match_id":    dm_id,
                    "show_id":          show_id,
                    "show_name":        show_name,
                    "year":             year,
                    "week":             week,
                    "match_type":       normalised["match_type"],
                    "side_a_ids":       normalised["side_a_ids"],
                    "side_a_names":     normalised["side_a_names"],
                    "side_b_ids":       normalised["side_b_ids"],
                    "side_b_names":     normalised["side_b_names"],
                    "winner":           normalised["winner"],
                    "finish_type":      normalised["finish_type"],
                    "duration_minutes": normalised["duration_minutes"],
                    "star_rating":      normalised["star_rating"],
                    "purpose":          normalised["purpose"],
                    "is_tryout":        bool(d.get('is_tryout',        False)),
                    "is_developmental": bool(d.get('is_developmental', False)),
                    "is_pre_show":      is_pre,
                    "is_post_show":     not is_pre,
                    "match_summary":    str(d.get('match_summary', d.get('summary', ''))),
                    "highlights":       d.get('highlights', []),
                })

        if save_flag and result:
            db.conn.commit()

        return jsonify({"success": True, "total": len(result),
                        "dark_matches": result, "saved": save_flag and bool(result)})
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e),
            "hint": "If this happened after code changes, restart Flask or trigger module reload."
        }), 500


@show_production_bp.route('/api/show-production/dark-matches/list')
def api_dark_match_list():
    """
    Return saved dark matches, optionally filtered by brand or show_id.
    Pre-show matches for the selected brand appear in the Pre-Show Dark Match tab.
    """
    db = _db()
    try:
        cursor  = db.conn.cursor()
        brand   = request.args.get('brand')
        show_id = request.args.get('show_id')
        year    = request.args.get('year',  type=int)
        week    = request.args.get('week',  type=int)

        clauses, params = [], []
        if show_id: clauses.append("show_id=?"); params.append(show_id)
        if year:    clauses.append("year=?");    params.append(year)
        if week:    clauses.append("week=?");    params.append(week)

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        cursor.execute(
            f"SELECT * FROM dark_matches {where} ORDER BY year DESC, week DESC, created_at DESC",
            params
        )
        rows = [dict(r) for r in cursor.fetchall()]

        # Normalise and optionally filter by brand (stored in side_a/b or looked up)
        result = []
        for row in rows:
            row = _normalise_dm_row(row)
            # Brand filter — dark_matches table has no brand column, so we skip
            # (brand is implicit via show_id; caller passes show_id when filtering by brand)
            result.append(row)

        pre  = [r for r in result if r.get('match_type') == 'pre_show'  or r.get('is_pre_show')]
        post = [r for r in result if r.get('match_type') == 'post_show' or r.get('is_post_show')]

        return jsonify({"success": True, "total": len(result),
                        "dark_matches": result,
                        "pre_show_matches":  pre,
                        "post_show_matches": post})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# ===========================================================================
# STEP 72 — Themes
# ===========================================================================

@show_production_bp.route('/api/show-production/themes')
def api_get_all_themes():
    try:
        show_theme_manager = _show_production('show_theme_manager')
        return jsonify({"success": True,
                        "themes": show_theme_manager.get_all_themes()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@show_production_bp.route('/api/show-production/themes/recommend')
def api_recommend_theme():
    universe = _universe()
    try:
        show_theme_manager = _show_production('show_theme_manager')
        SHOW_THEME_CONFIGS = _show_config('SHOW_THEME_CONFIGS')
        cs = universe.calendar.get_current_show()
        if not cs:
            return jsonify({"success": False, "error": "No show scheduled"}), 404
        theme = show_theme_manager.determine_show_theme(
            week=cs.week, year=cs.year, show_name=cs.name,
            is_ppv=cs.is_ppv, brand=cs.brand,
        )
        cfg = SHOW_THEME_CONFIGS.get(theme)
        return jsonify({"success": True, "show": cs.to_dict(),
                        "recommended_theme": theme.value,
                        "theme_config": cfg.to_dict() if cfg else None})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@show_production_bp.route('/api/show-production/themes/apply', methods=['POST'])
def api_apply_theme():
    universe = _universe()
    db = _db()
    try:
        _ensure_tables()
        show_production_manager = _show_production('show_production_manager')
        ShowTheme = _show_config('ShowTheme')
        SHOW_THEME_CONFIGS = _show_config('SHOW_THEME_CONFIGS')

        theme_value = (request.get_json() or {}).get("theme", "standard")
        try:
            theme = ShowTheme(theme_value)
        except ValueError:
            return jsonify({"success": False, "error": f"Unknown theme: {theme_value}"}), 400

        cs = universe.calendar.get_current_show()
        if not cs:
            return jsonify({"success": False, "error": "No show scheduled"}), 404

        year, week = _game_state()
        plan = show_production_manager.build_production_plan(
            scheduled_show=cs, universe_state=universe, force_theme=theme,
        )
        cfg  = SHOW_THEME_CONFIGS.get(theme)

        plan_id = f"plan_{cs.show_id}"
        now = datetime.now().isoformat()
        db.conn.cursor().execute("""
            INSERT OR REPLACE INTO show_production_plans
            (plan_id, show_id, brand, year, week, theme, opening_segment,
             runtime_minutes, commercial_breaks, ppv_buildup_score, notes,
             created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,
                COALESCE((SELECT created_at FROM show_production_plans WHERE plan_id=?),?),
                ?)
        """, (
            plan_id, cs.show_id, cs.brand, year, week,
            theme_value,
            plan.get('opening_segment_type', 'hot_match'),
            plan.get('total_runtime_minutes', 120),
            plan.get('commercial_breaks_count', 8),
            plan.get('ppv_buildup_score', 0),
            json.dumps(plan),
            plan_id, now, now,
        ))
        db.conn.commit()

        return jsonify({
            "success": True,
            "theme_applied": theme_value,
            "theme_label":   cfg.label if cfg and hasattr(cfg, 'label') else theme_value,
            "production_plan": plan,
            "saved": True,
            "message": f"Theme '{theme_value}' applied and saved for {cs.name}.",
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# ===========================================================================
# Master production plan (Steps 58-72 combined)
# ===========================================================================

@show_production_bp.route('/api/show-production/plan')
def api_get_production_plan():
    universe = _universe()
    db = _db()
    try:
        _ensure_tables()
        show_production_manager = _show_production('show_production_manager')

        cs = universe.calendar.get_current_show()
        if not cs:
            return jsonify({"success": False, "error": "No show scheduled"}), 404

        force_theme = None
        if request.args.get("theme"):
            ShowTheme = _show_config('ShowTheme')
            try:
                force_theme = ShowTheme(request.args["theme"])
            except ValueError:
                pass

        plan = show_production_manager.build_production_plan(
            scheduled_show=cs, universe_state=universe, force_theme=force_theme,
        )

        # Merge any saved production plan overrides
        cursor = db.conn.cursor()
        cursor.execute("SELECT * FROM show_production_plans WHERE show_id=?", (cs.show_id,))
        saved = cursor.fetchone()
        if saved:
            sd = dict(saved)
            plan['theme']                = sd.get('theme', plan.get('theme'))
            plan['opening_segment_type'] = sd.get('opening_segment', plan.get('opening_segment_type'))
            plan['saved'] = True
        else:
            plan['saved'] = False

        # Attach this-week production items
        year, week = _game_state()

        cursor.execute(
            "SELECT * FROM production_debuts WHERE year=? AND week=? AND status='planned'",
            (year, week))
        plan['planned_debuts'] = [dict(r) for r in cursor.fetchall()]

        cursor.execute(
            "SELECT * FROM production_returns WHERE year=? AND week=? AND status='planned'",
            (year, week))
        plan['planned_returns'] = [dict(r) for r in cursor.fetchall()]

        cursor.execute(
            "SELECT * FROM production_run_ins WHERE year=? AND week=? AND outcome='planned'",
            (year, week))
        plan['planned_run_ins'] = [dict(r) for r in cursor.fetchall()]

        # dark_matches uses finish_type, NOT result
        cursor.execute(
            "SELECT * FROM dark_matches WHERE year=? AND week=? AND finish_type='pending'",
            (year, week))
        plan['dark_matches'] = [_normalise_dm_row(dict(r)) for r in cursor.fetchall()]
        plan['planned_dark_matches'] = plan['dark_matches']   # alias

        return jsonify({"success": True, "production_plan": plan})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@show_production_bp.route('/api/show-production/plan/<show_id>')
def api_get_production_plan_for_show(show_id):
    universe = _universe()
    try:
        show_production_manager = _show_production('show_production_manager')
        ss = next((s for s in universe.calendar.generated_shows if s.show_id == show_id), None)
        if not ss:
            return jsonify({"success": False, "error": "Show not found"}), 404
        plan = show_production_manager.build_production_plan(
            scheduled_show=ss, universe_state=universe,
        )
        return jsonify({"success": True, "production_plan": plan})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# ===========================================================================
# Booking summary — real-time feed for Booking page
# ===========================================================================

@show_production_bp.route('/api/show-production/booking-summary')
def api_booking_summary():
    universe = _universe()
    db = _db()
    try:
        _ensure_tables()
        year, week = _game_state()
        cursor = db.conn.cursor()
        cs = universe.calendar.get_current_show()

        plan_data = {}
        if cs:
            cursor.execute("SELECT * FROM show_production_plans WHERE show_id=?", (cs.show_id,))
            row = cursor.fetchone()
            if row:
                plan_data = dict(row)

        cursor.execute(
            "SELECT * FROM production_debuts WHERE year=? AND week=? AND status='planned'",
            (year, week))
        debuts = [dict(r) for r in cursor.fetchall()]

        cursor.execute(
            "SELECT * FROM production_returns WHERE year=? AND week=? AND status='planned'",
            (year, week))
        returns = [dict(r) for r in cursor.fetchall()]

        cursor.execute(
            "SELECT * FROM production_run_ins WHERE year=? AND week=? AND outcome='planned'",
            (year, week))
        run_ins = [dict(r) for r in cursor.fetchall()]

        # Use finish_type, not result
        cursor.execute(
            "SELECT * FROM dark_matches WHERE year=? AND week=? AND finish_type='pending'",
            (year, week))
        dark_matches = [_normalise_dm_row(dict(r)) for r in cursor.fetchall()]

        cursor.execute("""
            SELECT * FROM house_shows
            WHERE (year > ? OR (year=? AND week>=?)) AND status='planned'
            ORDER BY year, week LIMIT 8
        """, (year, year, week))
        upcoming_hs = [dict(r) for r in cursor.fetchall()]

        notes = []
        for d in debuts:
            notes.append(f"⭐ DEBUT: {d['wrestler_name']} — {d['angle_summary']}")
        for r in returns:
            notes.append(f"🔥 RETURN: {r['wrestler_name']} — {r['angle_summary']}")
        for ri in run_ins:
            notes.append(f"⚡ RUN-IN: {ri.get('interferer_name','?')} in {ri['target_match_id']}")
        if dark_matches:
            notes.append(f"🌑 {len(dark_matches)} dark match(es) booked pre-show")
        if not notes:
            notes.append("No special production elements planned for this week.")

        return jsonify({
            "success": True,
            "year": year, "week": week,
            "current_show":    cs.to_dict() if cs else None,
            "production_plan": plan_data,
            "this_week": {
                "debuts":       debuts,
                "returns":      returns,
                "run_ins":      run_ins,
                "dark_matches": dark_matches,
            },
            "upcoming_house_shows": upcoming_hs,
            "booking_notes": notes,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@show_production_bp.route('/api/show-production/custom-ppv/create', methods=['POST'])
def api_create_custom_ppv():
    try:
        _ensure_tables()
        payload = request.get_json(force=True) or {}
        required = ['name', 'tier', 'location']
        missing = [k for k in required if not payload.get(k)]
        if missing:
            return jsonify({"success": False, "error": f"Missing fields: {', '.join(missing)}"}), 400
        if payload.get('date'):
            dt = datetime.fromisoformat(str(payload['date']))
            year = int(payload.get('year', max(1, dt.year - 2024)))
            week = int(payload.get('week', min(52, max(1, ((dt.timetuple().tm_yday - 1) // 7) + 1))))
        else:
            year = int(payload.get('year', _game_state()[0]))
            week = int(payload.get('week', _game_state()[1]))
        custom_ppv_id = f"cppv_{uuid.uuid4().hex[:10]}"
        _db().conn.execute("""
            INSERT INTO custom_ppvs
            (custom_ppv_id, name, year, week, day_of_week, tier, location, brand, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)
        """, (
            custom_ppv_id, str(payload['name']).strip(), year, week,
            payload.get('day_of_week', 'Sunday'), payload['tier'], payload['location'],
            payload.get('brand', 'Cross-Brand'), datetime.utcnow().isoformat()
        ))
        _db().conn.commit()
        _sync_custom_ppvs_into_calendar()
        return jsonify({"success": True, "custom_ppv_id": custom_ppv_id})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@show_production_bp.route('/api/show-production/advanced/book', methods=['POST'])
def api_book_advanced_features():
    """Unified persistence endpoint for cinematic, swerves, arcs, debut secrecy, and main-event grading."""
    try:
        _ensure_tables()
        p = request.get_json(force=True) or {}
        feature_type = str(p.get('feature_type', '')).strip()
        year, week = _game_state()
        cs = _universe().calendar.get_current_show()
        show_id = p.get('show_id') or (cs.show_id if cs else f"show_y{year}_w{week}")
        now = datetime.utcnow().isoformat()
        conn = _db().conn

        if feature_type == 'cinematic_match':
            vals = [int(p.get(k, 50)) for k in ('script_quality', 'production_value', 'acting_quality', 'originality')]
            overall = round(sum(vals) / len(vals), 1)
            cid = f"cine_{uuid.uuid4().hex[:10]}"
            conn.execute("""INSERT INTO cinematic_matches
                (cinematic_id, show_id, year, week, title, location, script_quality, production_value, acting_quality, originality, overall_rating, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (cid, show_id, year, week, p.get('title', 'Cinematic Match'), p.get('location', 'Off-site'),
                 vals[0], vals[1], vals[2], vals[3], overall, p.get('notes', ''), now))
            conn.commit()
            return jsonify({"success": True, "feature_id": cid, "overall_rating": overall})

        if feature_type == 'twist_swerve':
            s, l, f = int(p.get('surprise_rating', 50)), int(p.get('logic_rating', 50)), int(p.get('follow_through', 50))
            trust_impact = int(((s * 0.35) + (l * 0.40) + (f * 0.25) - 50) / 2)
            sid = f"swrv_{uuid.uuid4().hex[:10]}"
            conn.execute("""INSERT INTO twist_swerve_events
                (swerve_id, show_id, year, week, title, surprise_rating, logic_rating, follow_through, trust_impact, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (sid, show_id, year, week, p.get('title', 'Storyline Swerve'), s, l, f, trust_impact, now))
            conn.commit()
            return jsonify({"success": True, "feature_id": sid, "trust_impact": trust_impact})
        if feature_type == 'surprise_debut':
            wid = str(p.get('wrestler_id', '')).strip()
            if not wid:
                return jsonify({"success": False, "error": "wrestler_id is required"}), 400
            signing_year = int(p.get('signing_year', year))
            signing_week = int(p.get('signing_week', max(1, week - 1)))
            leaked = 1 if p.get('leaked', False) else 0
            secrecy_weeks = max(0, ((year - signing_year) * 52) + (week - signing_week))
            base_mult = min(2.6, 1.0 + (secrecy_weeks * 0.08))
            mult = round(base_mult * (0.4 if leaked else 1.0), 3)
            sid = f"sec_{uuid.uuid4().hex[:10]}"
            conn.execute("""INSERT INTO debut_secrecy_tracking
                (secrecy_id, wrestler_id, signing_year, signing_week, leaked, leak_week, debut_year, debut_week, secrecy_weeks, multiplier, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (sid, wid, signing_year, signing_week, leaked, int(p.get('leak_week', week if leaked else 0) or 0), year, week, secrecy_weeks, mult, now))
            conn.commit()
            return jsonify({"success": True, "feature_id": sid, "secrecy_weeks": secrecy_weeks, "surprise_multiplier": mult})
        if feature_type == 'main_event_selection':
            quality = float(p.get('quality_score', 70))
            draw = float(p.get('draw_score', 70))
            placement = float(p.get('placement_correctness', 70))
            legacy = round((quality * 0.5 + draw * 0.3 + placement * 0.2 - 60) / 8, 3)
            rid = f"mev_{uuid.uuid4().hex[:10]}"
            conn.execute("""INSERT INTO main_event_quality_history
                (record_id, show_id, year, week, match_title, quality_score, draw_score, placement_correctness, legacy_impact, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (rid, show_id, year, week, p.get('match_title', 'Main Event'), quality, draw, placement, legacy, now))
            conn.commit()
            return jsonify({"success": True, "feature_id": rid, "legacy_impact": legacy})

        if feature_type == 'long_term_arc':
            aid = f"arc_{uuid.uuid4().hex[:10]}"
            conn.execute("""INSERT INTO long_term_story_arcs
                (arc_id, name, start_year, start_week, planned_end_year, planned_end_week, current_phase, beats_json, status, unresolved_penalty, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', 0, ?)""",
                (aid, p.get('name', 'Unnamed Arc'), year, week, int(p.get('planned_end_year', year)), int(p.get('planned_end_week', week + 12)),
                 p.get('current_phase', 'setup'), json.dumps(p.get('beats', [])), now))
            conn.commit()
            return jsonify({"success": True, "feature_id": aid})

        return jsonify({"success": False, "error": "Unsupported feature_type"}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500
