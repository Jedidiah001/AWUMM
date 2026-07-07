"""
morale_events_routes.py
Steps 260-265: Morale Events & Storyline Consequences — API Endpoints

Endpoints:
  GET  /api/morale-events/recap/<show_id>          — Step 260: Recap morale cards for a show
  GET  /api/morale-events/storylines               — Step 261: Active storyline seeds
  POST /api/morale-events/storylines/<id>/accept   — Step 261: Accept a seed
  POST /api/morale-events/storylines/<id>/reject   — Step 261: Reject a seed
  POST /api/morale-events/storylines/scan          — Step 261: Re-scan roster for seeds
  GET  /api/morale-events/crisis                   — Step 262: Current crisis tier + active crises
  POST /api/morale-events/crisis/tick              — Step 262: Run weekly crisis evaluation
  GET  /api/morale-events/office-alerts            — Step 263: Full alert feed for office screen
  POST /api/morale-events/office-alerts/<id>/dismiss — Step 263: Dismiss an alert
  GET  /api/morale-events/digest                   — Step 264: Weekly narrative digest
  POST /api/morale-events/propagate                — Step 265: Trigger consequence propagation
  POST /api/morale-events/weekly-tick              — Master tick: runs 260-265 in sequence
"""

import json
from flask import Blueprint, jsonify, request, current_app

from simulation.morale_events import (
    show_recap_injector,
    morale_storyline_generator,
    crisis_escalation_engine,
    office_alert_broadcaster,
    weekly_morale_digest,
    consequence_propagator,
    CrisisTier,
    MoraleEventCategory,
)

morale_events_bp = Blueprint('morale_events', __name__)


# ============================================================
# Helpers
# ============================================================

def get_universe():
    return current_app.config['UNIVERSE']


def get_database():
    return current_app.config['DATABASE']


def _get_game_state(db):
    gs = db.get_game_state()
    return gs['current_year'], gs['current_week']


def _load_behavior_states(db, wrestlers) -> dict:
    """Load all behavior states in a single bulk query keyed by wrestler_id."""
    states = {w.id: {} for w in wrestlers}
    try:
        cursor = db.conn.cursor()
        cursor.execute('SELECT * FROM wrestler_behavior_states')
        for row in cursor.fetchall():
            d = dict(row)
            wid = d.get('wrestler_id')
            if wid and wid in states:
                d['refused_bookings'] = __import__('json').loads(d.get('refused_bookings') or '[]')
                d['refused_match_types'] = __import__('json').loads(d.get('refused_match_types') or '[]')
                d['poisoning_targets'] = __import__('json').loads(d.get('poisoning_targets') or '[]')
                for bool_field in (
                    'has_requested_release', 'has_gone_public', 'is_phoning_it_in',
                    'is_sandbagging', 'cooperation_refusal_active', 'is_leaking_info',
                    'is_venting_online', 'is_poisoning_locker_room', 'is_running_down_contract',
                ):
                    d[bool_field] = bool(d.get(bool_field, 0))
                states[wid] = d
    except Exception as e:
        print(f"[behavior_states] bulk load failed, falling back to per-wrestler: {e}")
        for w in wrestlers:
            data = db.get_behavior_state(w.id)
            if data:
                states[w.id] = data
    return states


# ============================================================
# GET /api/morale-events/recap/<show_id>  — Step 260
# ============================================================

@morale_events_bp.route('/api/morale-events/recap/<show_id>')
def api_recap_morale_events(show_id):
    """
    Return morale event cards for a specific show's recap feed.
    Pass ?year=&week= to scope behavior + recovery events to that show's week.
    """
    try:
        db = get_database()
        universe = get_universe()

        year  = request.args.get('year',  type=int)
        week  = request.args.get('week',  type=int)

        if not year or not week:
            year, week = _get_game_state(db)

        # Fetch behavior events from this week
        behavior_events = db.get_behavior_events(limit=100)
        behavior_events = [
            e for e in behavior_events
            if e.get('game_year') == year and e.get('game_week') == week
        ]

        # Fetch recovery events from this week
        recovery_events = db.get_recovery_events(limit=100)
        recovery_events = [
            e for e in recovery_events
            if e.get('game_year') == year and e.get('game_week') == week
        ]

        wrestlers = universe.get_active_wrestlers()
        wrestlers_by_id = {w.id: w for w in wrestlers}

        cards = show_recap_injector.generate_recap_events(
            show_id=show_id,
            year=year,
            week=week,
            behavior_events=behavior_events,
            recovery_events=recovery_events,
            wrestlers_by_id=wrestlers_by_id,
        )

        return jsonify({
            'show_id': show_id,
            'year': year,
            'week': week,
            'total_cards': len(cards),
            'cards': [c.to_dict() for c in cards],
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================
# GET /api/morale-events/storylines  — Step 261
# ============================================================

@morale_events_bp.route('/api/morale-events/storylines')
def api_storyline_seeds():
    """Return all pending morale-driven storyline seeds."""
    try:
        db = get_database()
        status_filter = request.args.get('status', 'pending')  # pending | accepted | rejected | all
        limit = request.args.get('limit', 20, type=int)

        seeds = db.get_morale_storyline_seeds(status=status_filter, limit=limit)

        return jsonify({
            'total': len(seeds),
            'seeds': seeds,
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@morale_events_bp.route('/api/morale-events/storylines/scan', methods=['POST'])
def api_scan_storylines():
    """Re-scan the roster and generate new morale storyline seeds."""
    try:
        universe = get_universe()
        db = get_database()
        year, week = _get_game_state(db)

        wrestlers = universe.get_active_wrestlers()
        behavior_states = _load_behavior_states(db, wrestlers)

        seeds = morale_storyline_generator.scan_roster(
            wrestlers=wrestlers,
            behavior_states=behavior_states,
            year=year,
            week=week,
        )

        saved = 0
        for seed in seeds:
            # Only save if no pending seed for same wrestler+type already exists
            existing = db.get_morale_storyline_seeds(
                wrestler_id=seed.primary_wrestler_id,
                storyline_type=seed.storyline_type.value,
                status='pending',
                limit=1,
            )
            if not existing:
                db.save_morale_storyline_seed(seed)
                saved += 1

        db.conn.commit()

        return jsonify({
            'success': True,
            'seeds_generated': len(seeds),
            'seeds_saved': saved,
            'seeds': [s.to_dict() for s in seeds],
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@morale_events_bp.route('/api/morale-events/storylines/<seed_id>/accept', methods=['POST'])
def api_accept_storyline(seed_id):
    """Accept a morale storyline seed (mark it for implementation)."""
    try:
        db = get_database()
        db.update_morale_storyline_seed_status(seed_id, 'accepted')
        db.conn.commit()
        return jsonify({'success': True, 'seed_id': seed_id, 'status': 'accepted'})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@morale_events_bp.route('/api/morale-events/storylines/<seed_id>/reject', methods=['POST'])
def api_reject_storyline(seed_id):
    """Reject a morale storyline seed."""
    try:
        db = get_database()
        db.update_morale_storyline_seed_status(seed_id, 'rejected')
        db.conn.commit()
        return jsonify({'success': True, 'seed_id': seed_id, 'status': 'rejected'})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================
# GET /api/morale-events/crisis  — Step 262
# ============================================================

@morale_events_bp.route('/api/morale-events/crisis')
def api_crisis_status():
    """Return current crisis tier and per-brand breakdown."""
    try:
        universe = get_universe()
        db = get_database()
        year, week = _get_game_state(db)

        wrestlers = universe.get_active_wrestlers()
        behavior_states = _load_behavior_states(db, wrestlers)

        tier, alerts = crisis_escalation_engine.evaluate(
            wrestlers=wrestlers,
            behavior_states=behavior_states,
            year=year,
            week=week,
        )

        # Per-brand breakdown
        brands: dict = {}
        for w in wrestlers:
            brand = getattr(w, 'primary_brand', 'Unknown')
            if brand not in brands:
                brands[brand] = {'total': 0, 'miserable': 0, 'unhappy': 0, 'content': 0,
                                 'happy': 0, 'public_demands': 0, 'sandbagging': 0}
            from simulation.morale_events import _morale_category
            cat = _morale_category(w.morale)
            brands[brand]['total'] += 1
            brands[brand][cat] = brands[brand].get(cat, 0) + 1
            state = behavior_states.get(w.id, {})
            if state.get('has_gone_public'):
                brands[brand]['public_demands'] += 1
            if state.get('is_sandbagging'):
                brands[brand]['sandbagging'] += 1

        return jsonify({
            'crisis_tier': tier.value,
            'year': year,
            'week': week,
            'brand_breakdown': brands,
            'alerts': [a.to_dict() for a in alerts],
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@morale_events_bp.route('/api/morale-events/crisis/tick', methods=['POST'])
def api_crisis_tick():
    """
    Run the weekly crisis evaluation:
    1. Determine tier
    2. Apply passive morale drain to bystanders
    3. Save alerts
    4. Return results
    """
    try:
        universe = get_universe()
        db = get_database()
        year, week = _get_game_state(db)

        wrestlers = universe.get_active_wrestlers()
        behavior_states = _load_behavior_states(db, wrestlers)

        tier, alerts = crisis_escalation_engine.evaluate(
            wrestlers=wrestlers,
            behavior_states=behavior_states,
            year=year,
            week=week,
        )

        # Apply passive drain
        deltas = crisis_escalation_engine.apply_crisis_drain(
            tier=tier,
            wrestlers=wrestlers,
            behavior_states=behavior_states,
        )

        # Save affected wrestlers
        if deltas:
            for w in wrestlers:
                if w.id in deltas:
                    universe.save_wrestler(w)

        # Save alerts to DB
        for alert in alerts:
            db.save_office_alert(alert)

        db.conn.commit()

        return jsonify({
            'success': True,
            'crisis_tier': tier.value,
            'year': year,
            'week': week,
            'alerts_generated': len(alerts),
            'wrestlers_drained': len(deltas),
            'drain_deltas': deltas,
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================
# GET /api/morale-events/office-alerts  — Step 263
# ============================================================

@morale_events_bp.route('/api/morale-events/office-alerts')
def api_office_alerts():
    """
    Return the full prioritised alert feed for the GM office screen.
    Combines undismissed DB alerts + live scan of current roster state.
    """
    try:
        universe = get_universe()
        db = get_database()
        year, week = _get_game_state(db)

        include_dismissed = request.args.get('include_dismissed', 'false').lower() == 'true'

        wrestlers = universe.get_active_wrestlers()
        behavior_states = _load_behavior_states(db, wrestlers)

        # Get current crisis tier (lightweight)
        tier, crisis_alerts = crisis_escalation_engine.evaluate(
            wrestlers=wrestlers,
            behavior_states=behavior_states,
            year=year,
            week=week,
        )

        # Generate live feed — gracefully degrade if broadcaster crashes
        live_feed = []
        try:
            live_feed = office_alert_broadcaster.generate_weekly_feed(
                wrestlers=wrestlers,
                behavior_states=behavior_states,
                crisis_tier=tier,
                crisis_alerts=crisis_alerts,
                year=year,
                week=week,
            )
        except Exception as feed_err:
            import traceback as _tb
            _tb.print_exc()
            print(f"[office-alerts] live feed generation failed: {feed_err}")

        # Merge with persisted undismissed alerts
        stored_alerts = db.get_office_alerts(include_dismissed=include_dismissed, limit=50)

        # Deduplicate by title (live takes precedence)
        live_titles = {a.title for a in live_feed}
        merged = [a.to_dict() for a in live_feed]
        for sa in stored_alerts:
            if sa.get('title') not in live_titles:
                merged.append(sa)

        return jsonify({
            'crisis_tier': tier.value,
            'year': year,
            'week': week,
            'total_alerts': len(merged),
            'critical_count': sum(1 for a in merged if a.get('priority') == 'critical'),
            'urgent_count': sum(1 for a in merged if a.get('priority') == 'urgent'),
            'alerts': merged,
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@morale_events_bp.route('/api/morale-events/office-alerts/<alert_id>/dismiss', methods=['POST'])
def api_dismiss_alert(alert_id):
    """Dismiss a persisted office alert."""
    try:
        db = get_database()
        db.dismiss_office_alert(alert_id)
        db.conn.commit()
        return jsonify({'success': True, 'alert_id': alert_id})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================
# GET /api/morale-events/digest  — Step 264
# ============================================================

@morale_events_bp.route('/api/morale-events/digest')
def api_weekly_digest():
    """Return the weekly narrative morale digest."""
    try:
        universe = get_universe()
        db = get_database()
        year, week = _get_game_state(db)

        wrestlers = universe.get_active_wrestlers()
        behavior_states = _load_behavior_states(db, wrestlers)

        tier, _ = crisis_escalation_engine.evaluate(
            wrestlers=wrestlers,
            behavior_states=behavior_states,
            year=year,
            week=week,
        )

        recovery_events_this_week = db.get_recovery_events(limit=200)
        recovery_events_this_week = [
            e for e in recovery_events_this_week
            if e.get('game_year') == year and e.get('game_week') == week
        ]

        digest = weekly_morale_digest.generate(
            wrestlers=wrestlers,
            behavior_states=behavior_states,
            recovery_events_this_week=recovery_events_this_week,
            crisis_tier=tier,
            year=year,
            week=week,
        )

        return jsonify(digest)

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================
# POST /api/morale-events/propagate  — Step 265
# ============================================================

@morale_events_bp.route('/api/morale-events/propagate', methods=['POST'])
def api_propagate():
    """
    Trigger consequence propagation from a specific morale event.

    Body:
      wrestler_id: str
      event_type: "public_demand" | "release" | "push" | "crisis_resolved"
    """
    try:
        universe = get_universe()
        db = get_database()
        year, week = _get_game_state(db)

        data = request.get_json() or {}
        wrestler_id = data.get('wrestler_id')
        event_type  = data.get('event_type')

        if not wrestler_id or not event_type:
            return jsonify({'error': 'wrestler_id and event_type are required'}), 400

        valid_types = ('public_demand', 'release', 'push', 'crisis_resolved')
        if event_type not in valid_types:
            return jsonify({'error': f'event_type must be one of: {", ".join(valid_types)}'}), 400

        trigger_wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not trigger_wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404

        all_wrestlers = universe.get_active_wrestlers()

        effects = consequence_propagator.propagate(
            trigger_wrestler=trigger_wrestler,
            trigger_event_type=event_type,
            all_wrestlers=all_wrestlers,
            year=year,
            week=week,
        )

        # Save affected wrestlers
        affected_ids = {e['wrestler_id'] for e in effects}
        for w in all_wrestlers:
            if w.id in affected_ids:
                universe.save_wrestler(w)

        db.conn.commit()

        return jsonify({
            'success': True,
            'trigger_wrestler': trigger_wrestler.name,
            'event_type': event_type,
            'wrestlers_affected': len(effects),
            'effects': effects,
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================
# POST /api/morale-events/weekly-tick  — Master tick
# ============================================================

@morale_events_bp.route('/api/morale-events/weekly-tick', methods=['POST'])
def api_master_weekly_tick():
    """
    Master end-of-week tick. Runs all Steps 260-265 in order:
    1. Scan for new storyline seeds (261)
    2. Run crisis evaluation + drain (262)
    3. Generate office alerts (263)
    4. Generate weekly digest (264)
    Returns a unified summary.
    """
    try:
        universe = get_universe()
        db = get_database()
        year, week = _get_game_state(db)

        wrestlers = universe.get_active_wrestlers()
        behavior_states = _load_behavior_states(db, wrestlers)

        # Step 261 — Storyline seeds
        seeds = morale_storyline_generator.scan_roster(
            wrestlers=wrestlers,
            behavior_states=behavior_states,
            year=year,
            week=week,
        )
        seeds_saved = 0
        for seed in seeds:
            existing = db.get_morale_storyline_seeds(
                wrestler_id=seed.primary_wrestler_id,
                storyline_type=seed.storyline_type.value,
                status='pending',
                limit=1,
            )
            if not existing:
                db.save_morale_storyline_seed(seed)
                seeds_saved += 1

        # Step 262 — Crisis tick
        tier, alerts = crisis_escalation_engine.evaluate(
            wrestlers=wrestlers,
            behavior_states=behavior_states,
            year=year,
            week=week,
        )
        deltas = crisis_escalation_engine.apply_crisis_drain(
            tier=tier,
            wrestlers=wrestlers,
            behavior_states=behavior_states,
        )
        for w in wrestlers:
            if w.id in deltas:
                universe.save_wrestler(w)
        for alert in alerts:
            db.save_office_alert(alert)

        # Step 263 — Office feed (generated live, no extra save needed)
        live_feed = office_alert_broadcaster.generate_weekly_feed(
            wrestlers=wrestlers,
            behavior_states=behavior_states,
            crisis_tier=tier,
            crisis_alerts=alerts,
            year=year,
            week=week,
        )

        # Step 264 — Digest
        recovery_events_this_week = db.get_recovery_events(limit=200)
        recovery_events_this_week = [
            e for e in recovery_events_this_week
            if e.get('game_year') == year and e.get('game_week') == week
        ]
        digest = weekly_morale_digest.generate(
            wrestlers=wrestlers,
            behavior_states=behavior_states,
            recovery_events_this_week=recovery_events_this_week,
            crisis_tier=tier,
            year=year,
            week=week,
        )

        db.conn.commit()

        return jsonify({
            'success': True,
            'year': year,
            'week': week,
            'crisis_tier': tier.value,
            'storyline_seeds_generated': seeds_saved,
            'crisis_alerts': len(alerts),
            'wrestlers_drained_by_crisis': len(deltas),
            'office_alerts': len(live_feed),
            'digest': digest,
            'alerts_preview': [a.to_dict() for a in live_feed[:5]],
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500