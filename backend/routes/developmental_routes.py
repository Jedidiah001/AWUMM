"""
Developmental Routes - API endpoints for ROC Vanguard developmental brand
Handles call-ups, roster management, and developmental championship.
"""

from flask import Blueprint, jsonify, request, current_app
import random
from datetime import datetime

developmental_bp = Blueprint('developmental', __name__)


def get_universe():
    """Get the universe state from app config"""
    return current_app.config.get('UNIVERSE')


def get_dev_manager():
    """Get the developmental roster manager from app config"""
    return current_app.config.get('DEV_ROSTER_MANAGER')


def get_call_up_engine():
    """Get the call-up engine from app config"""
    return current_app.config.get('CALL_UP_ENGINE')


def get_database():
    """Get the database from app config."""
    return current_app.config.get('DATABASE')


def _score_wrestler_readiness(wrestler):
    """Build a stable Vanguard readiness profile from existing wrestler stats."""
    in_ring = int((wrestler.brawling + wrestler.technical + wrestler.speed + wrestler.psychology + wrestler.stamina) / 5)
    promo = int(wrestler.mic)
    character = int((wrestler.mic + wrestler.psychology + wrestler.popularity) / 3)
    crowd = int(max(0, min(100, (wrestler.popularity * 0.75) + ((wrestler.momentum + 100) * 0.125))))
    aggregate = int((in_ring * 0.35) + (promo * 0.25) + (character * 0.20) + (crowd * 0.20))
    status = 'ready' if aggregate >= 75 and min(in_ring, promo, character, crowd) >= 60 else 'developing'
    return {
        'in_ring_score': in_ring,
        'promo_score': promo,
        'character_score': character,
        'crowd_reaction_score': crowd,
        'aggregate_readiness_score': aggregate,
        'readiness_status': status
    }


def _decision_score(readiness, brand_need=70, timing=65, buzz=None):
    """Calculate call-up decision score using the requested business weights."""
    buzz_score = buzz if buzz is not None else readiness['crowd_reaction_score']
    creative_fit = int((readiness['promo_score'] + readiness['character_score']) / 2)
    return {
        'performance_score': readiness['aggregate_readiness_score'],
        'creative_fit_score': creative_fit,
        'timing_score': timing,
        'brand_need_score': brand_need,
        'buzz_score': buzz_score,
        'decision_score': int(
            readiness['aggregate_readiness_score'] * 0.35
            + creative_fit * 0.25
            + timing * 0.20
            + brand_need * 0.15
            + buzz_score * 0.05
        )
    }


@developmental_bp.route('/api/developmental/vanguard-dashboard', methods=['GET'])
def api_get_vanguard_dashboard():
    """Executive dashboard for ROC Vanguard readiness, call-ups, and GM health."""
    try:
        universe = get_universe()
        database = get_database()
        if not universe or not database:
            return jsonify({'error': 'Developmental system not initialized'}), 500

        roster = [w for w in universe.wrestlers if w.primary_brand == 'ROC Vanguard' and not w.is_retired]
        prospects = []
        for wrestler in roster:
            readiness = _score_wrestler_readiness(wrestler)
            decision = _decision_score(readiness)
            prospects.append({
                'wrestler_id': wrestler.id,
                'wrestler_name': wrestler.name,
                'role': wrestler.role,
                'age': wrestler.age,
                'popularity': wrestler.popularity,
                **readiness,
                **decision,
                'recommended_brand': 'ROC Alpha' if wrestler.popularity >= 70 else 'ROC Velocity'
            })

        prospects.sort(key=lambda row: row['decision_score'], reverse=True)
        ready_count = len([row for row in prospects if row['readiness_status'] == 'ready'])

        cursor = database.conn.cursor()
        cursor.execute('SELECT * FROM brand_metadata ORDER BY brand_tier, prestige_level DESC')
        brands = [dict(row) for row in cursor.fetchall()]
        cursor.execute('SELECT * FROM general_managers ORDER BY current_brand')
        general_managers = [dict(row) for row in cursor.fetchall()]

        return jsonify({
            'success': True,
            'summary': {
                'vanguard_roster_count': len(roster),
                'call_up_ready_count': ready_count,
                'average_readiness': round(sum(p['aggregate_readiness_score'] for p in prospects) / len(prospects), 1) if prospects else 0,
                'top_prospect': prospects[0] if prospects else None
            },
            'brands': brands,
            'prospects': prospects,
            'general_managers': general_managers
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@developmental_bp.route('/api/developmental/evaluations/<wrestler_id>', methods=['POST'])
def api_record_vanguard_evaluation(wrestler_id):
    """Record manual scout/coach readiness evaluation for a Vanguard wrestler."""
    try:
        data = request.get_json() or {}
        universe = get_universe()
        database = get_database()
        wrestler = universe.get_wrestler_by_id(wrestler_id) if universe else None
        if not wrestler:
            return jsonify({'success': False, 'error': 'Wrestler not found'}), 404

        current_year = getattr(universe, 'current_year', 1)
        current_week = getattr(universe, 'current_week', 1)
        readiness = {
            'in_ring_score': int(data.get('in_ring_score', 50)),
            'promo_score': int(data.get('promo_score', 50)),
            'character_score': int(data.get('character_score', 50)),
            'crowd_reaction_score': int(data.get('crowd_reaction_score', 50)),
        }
        for key, value in readiness.items():
            if value < 0 or value > 100:
                return jsonify({'success': False, 'error': f'{key} must be between 0 and 100'}), 400

        aggregate = int(
            readiness['in_ring_score'] * 0.35
            + readiness['promo_score'] * 0.25
            + readiness['character_score'] * 0.20
            + readiness['crowd_reaction_score'] * 0.20
        )
        status = 'ready' if aggregate >= 75 and min(readiness.values()) >= 60 else 'developing'
        cursor = database.conn.cursor()
        cursor.execute('''
            INSERT INTO wrestler_evaluations (
                wrestler_id, brand_name, evaluation_year, evaluation_week,
                in_ring_score, promo_score, character_score, crowd_reaction_score,
                aggregate_readiness_score, readiness_status, scout_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            wrestler_id, 'ROC Vanguard', current_year, current_week,
            readiness['in_ring_score'], readiness['promo_score'],
            readiness['character_score'], readiness['crowd_reaction_score'],
            aggregate, status, data.get('scout_notes', '')
        ))
        database.conn.commit()

        return jsonify({
            'success': True,
            'wrestler_id': wrestler_id,
            'aggregate_readiness_score': aggregate,
            'readiness_status': status
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@developmental_bp.route('/api/developmental/gm-dashboard', methods=['GET'])
def api_get_gm_dashboard():
    """GM promotion dashboard with seeded brand authority figures."""
    try:
        database = get_database()
        if not database:
            return jsonify({'success': False, 'error': 'Database unavailable'}), 500

        cursor = database.conn.cursor()
        cursor.execute('SELECT COUNT(*) AS count FROM general_managers')
        if cursor.fetchone()['count'] == 0:
            cursor.executemany('''
                INSERT INTO general_managers (
                    gm_name, current_brand, gm_tier, background, character_type,
                    mic_skill, screen_presence, crisis_management,
                    political_navigation, executive_satisfaction
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', [
                ('Eli Drakeon', 'ROC Vanguard', 'developmental_authority', 'former_wrestler', 'fair_but_firm', 82, 78, 86, 70, 76),
                ('Monica Vale', 'ROC Velocity', 'flagship_authority', 'outside_executive', 'corporate_political', 76, 84, 74, 88, 82),
                ('Marcus Sterling', 'ROC Alpha', 'top_flagship_authority', 'backstage_producer', 'authoritative_strict', 84, 88, 82, 86, 85),
            ])
            database.conn.commit()

        cursor.execute('SELECT * FROM general_managers ORDER BY CASE current_brand WHEN "ROC Alpha" THEN 1 WHEN "ROC Velocity" THEN 2 ELSE 3 END')
        gms = [dict(row) for row in cursor.fetchall()]
        for gm in gms:
            aggregate = int((gm['mic_skill'] * 0.20) + (gm['screen_presence'] * 0.20) + (gm['crisis_management'] * 0.30) + (gm['political_navigation'] * 0.15) + (gm['executive_satisfaction'] * 0.15))
            gm['aggregate_score'] = aggregate
            gm['promotion_eligible'] = aggregate >= 75 and gm['current_brand'] != 'ROC Alpha'
            gm['next_step'] = 'Shadow ROC Velocity' if gm['current_brand'] == 'ROC Vanguard' else 'Shadow ROC Alpha' if gm['current_brand'] == 'ROC Velocity' else 'Executive oversight'

        return jsonify({'success': True, 'general_managers': gms})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# DEVELOPMENTAL ROSTER ENDPOINTS
# ============================================================================

@developmental_bp.route('/api/developmental/roster', methods=['GET'])
def api_get_developmental_roster():
    """Get all wrestlers on the developmental roster"""
    try:
        dev_manager = get_dev_manager()
        if not dev_manager:
            return jsonify({'error': 'Developmental system not initialized'}), 500
        
        entries = dev_manager.get_all_entries()
        
        return jsonify({
            'total': len(entries),
            'ready_for_call_up': len(dev_manager.get_ready_for_call_up()),
            'wrestlers': [entry.to_dict() for entry in entries]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@developmental_bp.route('/api/developmental/wrestler/<wrestler_id>', methods=['GET'])
def api_get_developmental_wrestler(wrestler_id):
    """Get details for a specific developmental wrestler"""
    try:
        dev_manager = get_dev_manager()
        if not dev_manager:
            return jsonify({'error': 'Developmental system not initialized'}), 500
        
        entry = dev_manager.get_entry(wrestler_id)
        if not entry:
            return jsonify({'error': 'Wrestler not found in developmental roster'}), 404
        
        return jsonify(entry.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@developmental_bp.route('/api/developmental/wrestler/<wrestler_id>/training', methods=['GET'])
def api_get_wrestler_training(wrestler_id):
    """Get training plan and stats for a developmental wrestler"""
    try:
        dev_manager = get_dev_manager()
        if not dev_manager:
            return jsonify({'error': 'Developmental system not initialized'}), 500
        
        entry = dev_manager.get_entry(wrestler_id)
        if not entry:
            return jsonify({'error': 'Wrestler not found in developmental roster'}), 404
        
        # Generate skill breakdown based on developmental rating
        base_skill = entry.developmental_rating
        skills = {
            'in_ring': min(100, max(0, base_skill + random.randint(-10, 10))),
            'mic_work': min(100, max(0, base_skill + random.randint(-10, 10))),
            'character': min(100, max(0, base_skill + random.randint(-10, 10))),
            'psychology': min(100, max(0, base_skill + random.randint(-10, 10))),
            'selling': min(100, max(0, base_skill + random.randint(-10, 10))),
            'conditioning': min(100, max(0, base_skill + random.randint(-10, 10)))
        }
        
        return jsonify({
            'wrestler_id': entry.wrestler_id,
            'wrestler_name': entry.wrestler_name,
            'weeks_in_developmental': entry.weeks_in_developmental,
            'developmental_rating': entry.developmental_rating,
            'coach_evaluation': entry.coach_evaluation,
            'skills': skills,
            'training_focus': entry.training_focus,
            'coaching_notes': entry.coaching_notes,
            'achievements': entry.achievements,
            'readiness_summary': entry.get_readiness_summary()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@developmental_bp.route('/api/developmental/wrestler/<wrestler_id>/train', methods=['POST'])
def api_run_training_session(wrestler_id):
    """Run a training session for a developmental wrestler"""
    try:
        data = request.get_json()
        training_focus = data.get('training_focus', 'in_ring')
        
        dev_manager = get_dev_manager()
        if not dev_manager:
            return jsonify({'error': 'Developmental system not initialized'}), 500
        
        entry = dev_manager.get_entry(wrestler_id)
        if not entry:
            return jsonify({'error': 'Wrestler not found in developmental roster'}), 404
        
        # Simulate training session
        improvement = random.randint(1, 5)
        session_quality = random.randint(60, 100)
        
        # Update coaching notes
        focus_labels = {
            'in_ring': 'In-Ring Skills',
            'mic_work': 'Mic Work/Promo',
            'character': 'Character Development',
            'psychology': 'Match Psychology',
            'selling': 'Selling/Storytelling',
            'conditioning': 'Physical Conditioning'
        }
        
        note = f"Week {entry.weeks_in_developmental + 1}: Focused on {focus_labels.get(training_focus, training_focus)}. Session quality: {session_quality}/100. Showed improvement."
        if entry.coaching_notes:
            entry.coaching_notes += "\n" + note
        else:
            entry.coaching_notes = note
        
        # Add to training focus if not already there
        if training_focus not in entry.training_focus:
            entry.training_focus.append(training_focus)
        
        # Small rating increase
        entry.developmental_rating = min(100, entry.developmental_rating + improvement)
        entry.coach_evaluation = min(100, entry.coach_evaluation + random.randint(0, 3))
        
        return jsonify({
            'success': True,
            'message': f'Training session completed. Rating increased by {improvement} points.',
            'session_quality': session_quality,
            'improvement': improvement,
            'new_developmental_rating': entry.developmental_rating,
            'coaching_notes': entry.coaching_notes
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@developmental_bp.route('/api/developmental/wrestler/<wrestler_id>/update_performance', methods=['POST'])
def api_update_developmental_performance(wrestler_id):
    """Update performance metrics for a developmental wrestler after a match"""
    try:
        data = request.get_json()
        match_quality = float(data.get('match_quality', 50))
        crowd_reaction = float(data.get('crowd_reaction', 50))
        
        dev_manager = get_dev_manager()
        if not dev_manager:
            return jsonify({'error': 'Developmental system not initialized'}), 500
        
        entry = dev_manager.get_entry(wrestler_id)
        if not entry:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        entry.update_performance(match_quality, crowd_reaction)
        
        return jsonify({
            'success': True,
            'message': 'Performance updated',
            'updated_stats': {
                'developmental_rating': entry.developmental_rating,
                'match_quality_avg': round(entry.match_quality_avg, 2),
                'crowd_reaction_avg': round(entry.crowd_reaction_avg, 2),
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@developmental_bp.route('/api/developmental/wrestler/<wrestler_id>/coaching_notes', methods=['PUT'])
def api_update_coaching_notes(wrestler_id):
    """Update coaching notes for a developmental wrestler"""
    try:
        data = request.get_json()
        notes = data.get('notes', '')
        
        dev_manager = get_dev_manager()
        if not dev_manager:
            return jsonify({'error': 'Developmental system not initialized'}), 500
        
        entry = dev_manager.get_entry(wrestler_id)
        if not entry:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        entry.coaching_notes = notes
        
        return jsonify({
            'success': True,
            'message': 'Coaching notes updated',
            'notes': entry.coaching_notes
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@developmental_bp.route('/api/developmental/wrestler/<wrestler_id>/training_focus', methods=['PUT'])
def api_update_training_focus(wrestler_id):
    """Update training focus areas for a developmental wrestler"""
    try:
        data = request.get_json()
        training_focus = data.get('training_focus', [])
        
        dev_manager = get_dev_manager()
        if not dev_manager:
            return jsonify({'error': 'Developmental system not initialized'}), 500
        
        entry = dev_manager.get_entry(wrestler_id)
        if not entry:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        entry.training_focus = training_focus
        
        return jsonify({
            'success': True,
            'message': 'Training focus updated',
            'training_focus': entry.training_focus
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@developmental_bp.route('/api/developmental/wrestler/<wrestler_id>/achievement', methods=['POST'])
def api_add_achievement(wrestler_id):
    """Add an achievement to a developmental wrestler's record"""
    try:
        data = request.get_json()
        achievement = data.get('achievement', '')
        
        dev_manager = get_dev_manager()
        if not dev_manager:
            return jsonify({'error': 'Developmental system not initialized'}), 500
        
        entry = dev_manager.get_entry(wrestler_id)
        if not entry:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        entry.add_achievement(achievement)
        
        return jsonify({
            'success': True,
            'message': 'Achievement added',
            'achievements': entry.achievements
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# CALL-UP ENDPOINTS
# ============================================================================

@developmental_bp.route('/api/developmental/call-up/recommendations', methods=['GET'])
def api_get_call_up_recommendations():
    """Get AI-generated call-up recommendations"""
    try:
        universe = get_universe()
        call_up_engine = get_call_up_engine()
        
        if not call_up_engine:
            return jsonify({'error': 'Call-up engine not initialized'}), 500
        
        current_year = getattr(universe, 'current_year', 2024)
        current_week = getattr(universe, 'current_week', 1)
        
        recommendations = call_up_engine.generate_recommendations(
            universe_state=universe,
            current_year=current_year,
            current_week=current_week
        )
        
        return jsonify({
            'total': len(recommendations),
            'recommendations': [rec.to_dict() for rec in recommendations]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@developmental_bp.route('/api/developmental/call-up/initiate', methods=['POST'])
def api_initiate_call_up():
    """Initiate a call-up from developmental to main roster"""
    try:
        data = request.get_json()
        wrestler_id = data.get('wrestler_id')
        destination_brand = data.get('destination_brand')
        reason = data.get('reason', 'brand_need')
        initiating_gm = data.get('initiating_gm')
        
        if not wrestler_id or not destination_brand:
            return jsonify({'error': 'Missing required fields'}), 400
        
        valid_brands = ['ROC Alpha', 'ROC Velocity', 'ROC Vanguard']
        if destination_brand not in valid_brands:
            return jsonify({'error': f'Invalid brand. Must be one of: {valid_brands}'}), 400
        
        dev_manager = get_dev_manager()
        call_up_engine = get_call_up_engine()
        universe = get_universe()
        
        if not dev_manager or not call_up_engine:
            return jsonify({'error': 'Developmental system not initialized'}), 500
        
        # Import CallUpReason enum
        from models.developmental_roster import CallUpReason
        
        try:
            reason_enum = CallUpReason(reason)
        except ValueError:
            return jsonify({'error': f'Invalid reason. Valid reasons: {[r.value for r in CallUpReason]}'}), 400
        
        current_year = getattr(universe, 'current_year', 2024)
        current_week = getattr(universe, 'current_week', 1)
        
        result = call_up_engine.execute_call_up(
            wrestler_id=wrestler_id,
            destination_brand=destination_brand,
            reason=reason_enum,
            universe_state=universe,
            current_year=current_year,
            current_week=current_week,
            initiating_gm=initiating_gm
        )
        
        status_code = 200 if result['success'] else 400
        return jsonify(result), status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@developmental_bp.route('/api/developmental/call-up/outcome', methods=['POST'])
def api_process_call_up_outcome():
    """Process the outcome of a call-up (success/failure)"""
    try:
        data = request.get_json()
        wrestler_id = data.get('wrestler_id')
        success = data.get('success', False)
        
        if not wrestler_id:
            return jsonify({'error': 'Missing wrestler_id'}), 400
        
        dev_manager = get_dev_manager()
        call_up_engine = get_call_up_engine()
        universe = get_universe()
        
        if not dev_manager or not call_up_engine:
            return jsonify({'error': 'Developmental system not initialized'}), 500
        
        result = call_up_engine.simulate_call_up_outcome(
            wrestler_id=wrestler_id,
            universe_state=universe
        )
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@developmental_bp.route('/api/developmental/call-up/history', methods=['GET'])
def api_get_call_up_history():
    """Get call-up history"""
    try:
        dev_manager = get_dev_manager()
        if not dev_manager:
            return jsonify({'error': 'Developmental system not initialized'}), 500
        
        limit = request.args.get('limit', 20, type=int)
        history = dev_manager.get_recent_call_ups(limit)
        
        return jsonify({
            'total': len(history),
            'history': history
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@developmental_bp.route('/api/developmental/statistics', methods=['GET'])
def api_get_developmental_statistics():
    """Get overall developmental system statistics"""
    try:
        dev_manager = get_dev_manager()
        call_up_engine = get_call_up_engine()
        universe = get_universe()
        
        if not dev_manager:
            return jsonify({'error': 'Developmental system not initialized'}), 500
        
        stats = dev_manager.get_call_up_statistics()
        
        brand_stats = {}
        if call_up_engine and universe:
            brand_stats = call_up_engine.get_brand_statistics(universe)
        
        return jsonify({
            'overall': stats,
            'by_brand': brand_stats,
            'vanguard_championship': dev_manager.nexus_championship.to_dict(),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# DEVELOPMENTAL CHAMPIONSHIP ENDPOINTS
# ============================================================================

@developmental_bp.route('/api/developmental/championship', methods=['GET'])
def api_get_nexus_championship():
    """Get the ROC Vanguard developmental championship details"""
    try:
        dev_manager = get_dev_manager()
        if not dev_manager:
            return jsonify({'error': 'Developmental system not initialized'}), 500
        
        return jsonify(dev_manager.nexus_championship.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@developmental_bp.route('/api/developmental/championship/crown', methods=['POST'])
def api_crown_nexus_champion():
    """Crown a new ROC Vanguard developmental champion"""
    try:
        data = request.get_json()
        wrestler_id = data.get('wrestler_id')
        wrestler_name = data.get('wrestler_name')
        
        if not wrestler_id or not wrestler_name:
            return jsonify({'error': 'Missing wrestler_id or wrestler_name'}), 400
        
        dev_manager = get_dev_manager()
        universe = get_universe()
        
        if not dev_manager or not universe:
            return jsonify({'error': 'Developmental system not initialized'}), 500
        
        current_year = getattr(universe, 'current_year', 2024)
        current_week = getattr(universe, 'current_week', 1)
        
        # Update championship
        champ = dev_manager.nexus_championship
        champ.current_holder_id = wrestler_id
        champ.current_holder_name = wrestler_name
        champ.won_date_year = current_year
        champ.won_date_week = current_week
        champ.days_held = 0
        champ.defense_count = 0
        
        # Add to history
        champ.history.append({
            'wrestler_id': wrestler_id,
            'wrestler_name': wrestler_name,
            'won_date_year': current_year,
            'won_date_week': current_week,
            'days_held': 0,
        })
        
        # Add achievement to wrestler if in developmental
        entry = dev_manager.get_entry(wrestler_id)
        if entry:
            entry.add_achievement('vanguard_prospects_champion')
        
        return jsonify({
            'success': True,
            'message': f'{wrestler_name} is the new ROC Vanguard Prospects Champion!',
            'championship': champ.to_dict()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@developmental_bp.route('/api/developmental/championship/book-match', methods=['POST'])
def api_book_nexus_championship_match():
    """Book and simulate a ROC Vanguard match with optional title stakes."""
    try:
        data = request.get_json() or {}
        wrestler1_id = data.get('wrestler1_id')
        wrestler2_id = data.get('wrestler2_id')
        is_title_match = bool(data.get('is_title_match', False))
        winner_id = data.get('winner_id')
        finish_type = (data.get('finish_type') or 'pinfall').strip().lower()

        valid_finishes = {'pinfall', 'submission', 'dq', 'countout', 'rollup', 'ref_stoppage'}
        if finish_type not in valid_finishes:
            return jsonify({'success': False, 'error': f'Invalid finish_type: {finish_type}'}), 400

        if not wrestler1_id or not wrestler2_id:
            return jsonify({'success': False, 'error': 'wrestler1_id and wrestler2_id are required'}), 400
        if wrestler1_id == wrestler2_id:
            return jsonify({'success': False, 'error': 'Cannot book a wrestler against themselves'}), 400
        if winner_id and winner_id not in {wrestler1_id, wrestler2_id}:
            return jsonify({'success': False, 'error': 'winner_id must match one of the selected wrestlers'}), 400

        dev_manager = get_dev_manager()
        universe = get_universe()
        database = current_app.config.get('DATABASE')
        if not dev_manager or not universe or not database:
            return jsonify({'success': False, 'error': 'Developmental system not initialized'}), 500

        entry1 = dev_manager.get_entry(wrestler1_id)
        entry2 = dev_manager.get_entry(wrestler2_id)
        if not entry1 or not entry2:
            return jsonify({'success': False, 'error': 'Both wrestlers must be on the developmental roster'}), 400

        if winner_id == wrestler1_id:
            winner_entry, loser_entry = entry1, entry2
        elif winner_id == wrestler2_id:
            winner_entry, loser_entry = entry2, entry1
        else:
            winner_entry = random.choice([entry1, entry2])
            loser_entry = entry2 if winner_entry is entry1 else entry1

        base_quality = (entry1.developmental_rating + entry2.developmental_rating) / 2
        match_rating = int(max(40, min(100, base_quality + random.randint(-10, 15))))
        crowd_reaction = int(max(35, min(100, base_quality + random.randint(-12, 18))))

        entry1.update_performance(match_rating, crowd_reaction)
        entry2.update_performance(match_rating, crowd_reaction)

        champ = dev_manager.nexus_championship
        title_change = False
        current_year = getattr(universe, 'current_year', 2024)
        current_week = getattr(universe, 'current_week', 1)

        if is_title_match:
            title_change = bool(champ.current_holder_id and winner_entry.wrestler_id != champ.current_holder_id)

            if champ.current_holder_id == winner_entry.wrestler_id:
                champ.defense_count += 1
                champ.days_held += 7
            else:
                champ.current_holder_id = winner_entry.wrestler_id
                champ.current_holder_name = winner_entry.wrestler_name
                champ.won_date_year = current_year
                champ.won_date_week = current_week
                champ.days_held = 0
                champ.defense_count = 0
                champ.history.append({
                    'wrestler_id': winner_entry.wrestler_id,
                    'wrestler_name': winner_entry.wrestler_name,
                    'won_date_year': current_year,
                    'won_date_week': current_week,
                    'days_held': 0,
                    'defense_count': 0
                })

        cursor = database.conn.cursor()
        cursor.execute('''
            INSERT INTO nexus_championship_matches (
                match_date_year, match_date_week, wrestler1_id, wrestler1_name,
                wrestler2_id, wrestler2_name, winner_id, winner_name,
                was_title_match, title_changed, match_quality, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            current_year, current_week,
            entry1.wrestler_id, entry1.wrestler_name,
            entry2.wrestler_id, entry2.wrestler_name,
            winner_entry.wrestler_id, winner_entry.wrestler_name,
            1 if is_title_match else 0,
            1 if title_change else 0,
            match_rating,
            f'Finish: {finish_type}',
            datetime.now().isoformat(),
        ))
        database.conn.commit()

        return jsonify({
            'success': True,
            'winner_id': winner_entry.wrestler_id,
            'winner_name': winner_entry.wrestler_name,
            'loser_id': loser_entry.wrestler_id,
            'loser_name': loser_entry.wrestler_name,
            'finish_type': finish_type,
            'match_rating': match_rating,
            'crowd_reaction': crowd_reaction,
            'is_title_match': is_title_match,
            'title_change': title_change,
            'championship': champ.to_dict(),
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@developmental_bp.route('/api/developmental/championship/defense', methods=['POST'])
def api_nexus_championship_defense():
    """Record a championship defense"""
    try:
        data = request.get_json()
        wrestler_id = data.get('wrestler_id')
        successful = data.get('successful', True)
        
        dev_manager = get_dev_manager()
        if not dev_manager:
            return jsonify({'error': 'Developmental system not initialized'}), 500
        
        champ = dev_manager.nexus_championship
        
        if champ.current_holder_id != wrestler_id:
            return jsonify({'error': 'Wrestler is not the current champion'}), 400
        
        if successful:
            champ.defense_count += 1
            champ.days_held += 7  # Assume weekly shows
        else:
            # Champion lost - will need to crown new champion separately
            pass
        
        return jsonify({
            'success': True,
            'message': 'Championship defense recorded',
            'defenses': champ.defense_count,
            'days_held': champ.days_held
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# WEEKLY PROGRESS ENDPOINT
# ============================================================================

@developmental_bp.route('/api/developmental/update_weekly', methods=['POST'])
def api_update_weekly_progress():
    """Update weekly progress for all developmental wrestlers"""
    try:
        dev_manager = get_dev_manager()
        call_up_engine = get_call_up_engine()
        universe = get_universe()
        
        if not dev_manager:
            return jsonify({'error': 'Developmental system not initialized'}), 500
        
        current_year = getattr(universe, 'current_year', 2024)
        current_week = getattr(universe, 'current_week', 1)
        
        # Update developmental progress
        dev_manager.update_weekly_progress(current_year, current_week)
        
        # Update cooldowns
        if call_up_engine:
            call_up_engine.update_cooldowns()
        
        return jsonify({
            'success': True,
            'message': 'Weekly progress updated',
            'developmental_count': len(dev_manager.developmental_roster),
            'ready_for_call_up': len(dev_manager.get_ready_for_call_up())
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# ADD TO DEVELOPMENTAL ENDPOINT
# ============================================================================

@developmental_bp.route('/api/developmental/add', methods=['POST'])
def api_add_to_developmental():
    """Add a wrestler to the developmental roster"""
    try:
        data = request.get_json()
        wrestler_id = data.get('wrestler_id')
        wrestler_name = data.get('wrestler_name')
        initial_rating = data.get('initial_rating', 50)
        coaching_notes = data.get('coaching_notes', '')
        
        if not wrestler_id or not wrestler_name:
            return jsonify({'error': 'Missing required fields'}), 400
        
        dev_manager = get_dev_manager()
        universe = get_universe()
        
        if not dev_manager or not universe:
            return jsonify({'error': 'Developmental system not initialized'}), 500
        
        current_year = getattr(universe, 'current_year', 2024)
        current_week = getattr(universe, 'current_week', 1)
        
        entry = dev_manager.add_to_developmental(
            wrestler_id=wrestler_id,
            wrestler_name=wrestler_name,
            current_year=current_year,
            current_week=current_week,
            initial_rating=initial_rating,
            coaching_notes=coaching_notes
        )
        
        # Update wrestler's brand to ROC Vanguard
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if wrestler:
            from models.developmental_roster import DevelopmentalBrand
            wrestler.primary_brand = DevelopmentalBrand.ROC_VANGUARD.value
        
        return jsonify({
            'success': True,
            'message': f'{wrestler_name} added to developmental roster',
            'entry': entry.to_dict()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
