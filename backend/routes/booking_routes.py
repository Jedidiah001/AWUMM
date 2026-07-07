"""
Booking Routes - Enhanced Show Card Management with Gender Separation
Adapted to work with custom Database class (not Flask-SQLAlchemy)
"""

from flask import Blueprint, request, jsonify, current_app
import json
import uuid
from datetime import datetime

from models.show import ShowDraft, SegmentDraft
from models.match import MatchDraft
from economy.finance import finance_calculator
from services.creative_director import CreativeDirector
from services.production_planner import ProductionPlanner

booking_bp = Blueprint('booking', __name__, url_prefix='/api/booking')

# ============================================================================
# HELPER: Get Database from App Config
# ============================================================================

def get_database():
    """Get database instance from Flask app config"""
    return current_app.config.get('DATABASE')


def get_universe():
    """Get universe state from app config"""
    return current_app.config.get('UNIVERSE')


def _wrestlers_on_card(show_draft: ShowDraft, universe) -> list:
    wrestler_ids = set()

    for match in show_draft.matches:
        wrestler_ids.update(match.side_a.wrestler_ids)
        wrestler_ids.update(match.side_b.wrestler_ids)

    for segment in show_draft.segments or []:
        for participant in getattr(segment, 'participants', []) or []:
            wrestler_id = participant.get('id') if isinstance(participant, dict) else None
            if wrestler_id:
                wrestler_ids.add(wrestler_id)

    wrestlers = []
    for wrestler_id in wrestler_ids:
        wrestler = universe.get_wrestler_by_id(wrestler_id) if universe else None
        if wrestler:
            wrestlers.append(wrestler)
    return wrestlers


def _brand_prestige(show_draft: ShowDraft, universe) -> int:
    if not universe:
        return 50

    if show_draft.brand == 'Cross-Brand':
        brand_wrestlers = universe.get_active_wrestlers()
    else:
        brand_wrestlers = universe.get_wrestlers_by_brand(show_draft.brand)

    if not brand_wrestlers:
        return 50

    total_popularity = sum(getattr(wrestler, 'popularity', 50) or 50 for wrestler in brand_wrestlers)
    return int(total_popularity / len(brand_wrestlers))


def _economics_projection(show_draft: ShowDraft, universe, balance: int) -> dict:
    wrestlers_on_card = _wrestlers_on_card(show_draft, universe)
    return finance_calculator.project_show_finances(
        show_draft,
        wrestlers_on_card,
        brand_prestige=_brand_prestige(show_draft, universe),
        current_balance=balance,
        randomize=False,
    )


def _get_show_venue_override(database, show_draft: ShowDraft) -> dict:
    """Pull a saved calendar venue assignment into the booking/show finance flow."""
    if not database or not getattr(show_draft, 'show_id', None):
        return {}

    row = database.conn.cursor().execute(
        """
        SELECT sva.city_id, sva.venue_id,
               c.name AS city_name, c.country AS city_country, c.continent AS city_continent,
               v.name AS venue_name, v.capacity AS venue_capacity, v.cost AS venue_cost, v.venue_tier
        FROM show_venue_assignments sva
        LEFT JOIN cities c ON c.city_id = sva.city_id
        LEFT JOIN venues v ON v.venue_id = sva.venue_id
        WHERE sva.show_id = ?
        """,
        (show_draft.show_id,),
    ).fetchone()

    if not row:
        return {}

    return {
        'city_id': row['city_id'],
        'venue_id': row['venue_id'],
        'city_name': row['city_name'],
        'city_country': row['city_country'],
        'city_continent': row['city_continent'],
        'venue_name': row['venue_name'],
        'venue_capacity': row['venue_capacity'],
        'venue_cost': row['venue_cost'],
        'venue_tier': row['venue_tier'],
    }


def _apply_show_context(show_draft: ShowDraft, database) -> ShowDraft:
    """Attach non-persistent runtime context used by projection/simulation."""
    venue_override = _get_show_venue_override(database, show_draft)
    if venue_override:
        show_draft.venue_override = venue_override
    return show_draft

# ============================================================================
# GENERATE SHOW CARD WITH PRODUCTION PLAN
# ============================================================================

@booking_bp.route('/preview-next', methods=['GET'])
def preview_next_show():
    """
    Return a lightweight preview of the next scheduled show.
    Called by the Office view on load. Returns show name, type, brand, week and year.
    """
    try:
        database = get_database()
        universe = get_universe()
        game_state = database.get_game_state()
        scheduled_show = universe.calendar.get_current_show() if universe else None

        current_year = scheduled_show.year if scheduled_show else game_state.get('current_year', 2025)
        current_week = scheduled_show.week if scheduled_show else game_state.get('current_week', 1)
        current_brand = scheduled_show.brand if scheduled_show else game_state.get('current_brand', 'ROC Alpha')
        current_show_id = scheduled_show.show_id if scheduled_show else None
        current_show_name = scheduled_show.name if scheduled_show else f'{current_brand} Weekly TV'
        current_show_type = scheduled_show.show_type if scheduled_show else 'weekly_tv'

        # Try to find an existing draft first
        existing_draft = database.get_show_draft(current_show_id) if current_show_id else None
        if existing_draft:
            return jsonify({
                'success': True,
                'show_id': existing_draft.get('show_id', current_show_id),
                'show_name': existing_draft.get('show_name', current_show_name),
                'show_type': existing_draft.get('show_type', current_show_type),
                'brand': current_brand,
                'year': current_year,
                'week': current_week,
                'has_draft': True,
                'available_wrestlers': len(universe.get_wrestlers_by_brand(current_brand)) if universe else 0,
                'hot_feuds': len(universe.feud_manager.get_active_feuds()) if universe else 0,
            })

        return jsonify({
            'success': True,
            'show_id': current_show_id,
            'show_name': current_show_name,
            'show_type': current_show_type,
            'brand': current_brand,
            'year': current_year,
            'week': current_week,
            'has_draft': False,
            'available_wrestlers': len(universe.get_wrestlers_by_brand(current_brand)) if universe else 0,
            'hot_feuds': len(universe.feud_manager.get_active_feuds()) if universe else 0,
        })

    except Exception as e:
        print(f"Error in preview-next: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@booking_bp.route('/generate', methods=['POST'])
def generate_show_card():
    """
    Generate a complete show card with production plan
    Includes gender-separated matches and creative direction
    """
    try:
        database = get_database()
        universe = get_universe()
        data = request.get_json() or {}
        
        include_production_plan = data.get('include_production_plan', True)
        force_regenerate = data.get('force_regenerate', False)
        game_state = database.get_game_state()
        scheduled_show = universe.calendar.get_current_show() if universe else None
        current_brand = data.get('brand') or (scheduled_show.brand if scheduled_show else game_state.get('current_brand', 'ROC Alpha'))
        current_year = data.get('year') or (scheduled_show.year if scheduled_show else game_state.get('current_year', 2025))
        current_week = data.get('week') or (scheduled_show.week if scheduled_show else game_state.get('current_week', 1))
        current_show_id = data.get('show_id') or (scheduled_show.show_id if scheduled_show else str(uuid.uuid4()))
        
        # Check if there's already a show draft in progress
        if not force_regenerate:
            existing_draft = database.get_show_draft(current_show_id)
            if existing_draft:
                production_plan = database.get_production_plan(existing_draft['show_id'])
                return jsonify({
                    'success': True,
                    'show_draft': existing_draft,
                    'production_plan': production_plan
                })
        
        # Determine show type
        show_type = data.get('show_type') or (scheduled_show.show_type if scheduled_show else 'weekly_tv')
        is_ppv = show_type in ['minor_ppv', 'major_ppv']
        
        # Generate show name
        if data.get('show_name'):
            show_name = data['show_name']
        elif scheduled_show:
            show_name = scheduled_show.name
        elif is_ppv:
            show_name = f"{current_brand} PPV - Week {current_week}"
        else:
            show_name = f"{current_brand} Weekly TV - Week {current_week}"
        
        # Create new show draft
        show_draft = ShowDraft(
            show_id=current_show_id,
            show_name=show_name,
            brand=current_brand,
            show_type=show_type,
            is_ppv=is_ppv,
            year=current_year,
            week=current_week
        )
        _apply_show_context(show_draft, database)
        
        # Initialize Production Planner
        planner = ProductionPlanner(show_draft)
        
        # Generate production plan
        production_plan = None
        if include_production_plan:
            production_plan = planner.generate_production_plan()
        
        # Initialize Creative Director
        director = CreativeDirector(show_draft)
        
        # Get active roster for this brand (FIXED: use primary_brand and is_retired)
        cursor = database.conn.cursor()
        if current_brand == 'Cross-Brand':
            cursor.execute('''
                SELECT * FROM wrestlers
                WHERE is_retired = 0
            ''')
        else:
            cursor.execute('''
                SELECT * FROM wrestlers 
                WHERE primary_brand = ? AND is_retired = 0
            ''', (current_brand,))
        
        active_roster = []
        for row in cursor.fetchall():
            active_roster.append(dict(row))
        
        # Separate by gender (DB stores 'Male'/'Female' with capital first letter)
        male_roster = [w for w in active_roster if w.get('gender', '').lower() == 'male']
        female_roster = [w for w in active_roster if w.get('gender', '').lower() == 'female']
        
        # Get active feuds (FIXED: no brand column in feuds table)
        cursor.execute('''
            SELECT * FROM feuds 
            WHERE status = 'active'
        ''')
        
        active_feuds = []
        for row in cursor.fetchall():
            feud_dict = dict(row)
            # Parse JSON fields
            if 'participant_ids' in feud_dict and feud_dict['participant_ids']:
                try:
                    feud_dict['participant_ids'] = json.loads(feud_dict['participant_ids'])
                except:
                    feud_dict['participant_ids'] = []
            if 'participant_names' in feud_dict and feud_dict['participant_names']:
                try:
                    feud_dict['participant_names'] = json.loads(feud_dict['participant_names'])
                except:
                    feud_dict['participant_names'] = []
            active_feuds.append(feud_dict)
        
        # Generate matches based on production plan
        if production_plan:
            matches = director.generate_full_card_dict(
                male_roster,
                female_roster,
                active_feuds,
                production_plan
            )
        else:
            matches = director.generate_default_card_dict(
                male_roster,
                female_roster,
                active_feuds
            )
        
        # Build a wrestler lookup dict for name resolution
        wrestler_lookup = {w['id']: w for w in active_roster}
        
        def normalize_match_dict(m: dict, position: int) -> dict:
            """Convert CreativeDirector match dict to MatchDraft.from_dict format"""
            import uuid as _uuid
            match_type = m.get('match_type', 'singles')
            participants = m.get('participants', [])
            
            if match_type in ['battle_royal', 'rumble', 'elimination_chamber', 'triple_threat', 'fatal_4way']:
                team_a_ids = [participant for participant in participants if participant]
                team_b_ids = []
            elif match_type == 'tag':
                # participants is [[id, id], [id, id]]
                team_a_ids = participants[0] if len(participants) > 0 else []
                team_b_ids = participants[1] if len(participants) > 1 else []
            elif match_type in ['trios_tag', 'triple_threat_tag', 'fatal_4way_tag']:
                flattened = []
                for team in participants:
                    if isinstance(team, list):
                        flattened.extend([participant for participant in team if participant])
                team_a_ids = flattened
                team_b_ids = []
            elif match_type == 'mixed_tag':
                # participants is [{'male': id, 'female': id}, {...}]
                team_a_ids = [participants[0]['male'], participants[0]['female']] if participants else []
                team_b_ids = [participants[1]['male'], participants[1]['female']] if len(participants) > 1 else []
            else:
                # singles / other: participants is [id, id]
                team_a_ids = [participants[0]] if len(participants) > 0 else []
                team_b_ids = [participants[1]] if len(participants) > 1 else []
            
            def get_names(ids):
                return [wrestler_lookup.get(wid, {}).get('name', wid) for wid in ids]
            
            return {
                'match_id': str(_uuid.uuid4()),
                'side_a': {
                    'wrestler_ids': team_a_ids,
                    'wrestler_names': get_names(team_a_ids),
                    'is_tag_team': len(team_a_ids) > 1
                },
                'side_b': {
                    'wrestler_ids': team_b_ids,
                    'wrestler_names': get_names(team_b_ids),
                    'is_tag_team': len(team_b_ids) > 1
                },
                'match_type': match_type,
                'is_title_match': m.get('is_title_match', False),
                'title_id': m.get('title_id'),
                'title_name': m.get('title_name'),
                'card_position': m.get('card_position_override', position),
                'booking_bias': m.get('booking_bias', 'even'),
                'importance': m.get('importance', 'normal'),
                'feud_id': m.get('feud_id'),
                'gender_division': m.get('gender_division'),
                'stipulation': m.get('stipulation'),
                'special_match_type': m.get('special_match_type'),
            }

        special_matches = []
        special_segments = []
        show_name_lower = (show_name or '').lower()

        if 'rumble royale' in show_name_lower:
            special_matches, special_segments = _book_rumble_royale_special(
                show_draft,
                male_roster,
                female_roster,
                wrestler_lookup,
            )
        elif 'elimination chamber' in show_name_lower:
            special_matches, special_segments = _book_elimination_chamber_special(
                show_draft,
                male_roster,
                female_roster,
                universe,
                database,
                wrestler_lookup,
            )
        elif show_name_lower.startswith('legacymania'):
            special_matches, special_segments = _book_legacymania_title_matches(
                show_draft,
                universe,
                database,
            )

        if special_matches:
            matches = special_matches
        # Rebalance for wider roster showcase opportunities
        else:
            matches = _rebalance_matches_for_showcase(matches, active_roster, show_type)

        # Add matches to show draft
        for i, match_dict in enumerate(matches):
            normalized = normalize_match_dict(match_dict, i + 1)
            match = MatchDraft.from_dict(normalized)
            match.gender_division = normalized.get('gender_division')
            show_draft.add_match(match)
        
        # Generate segments
        segment_dicts = director.generate_segments_dict(active_feuds, matches)
        if special_segments:
            segment_dicts = special_segments + segment_dicts
        
        for seg_dict in segment_dicts:
            import uuid as _uuid
            normalized_seg = {
                'segment_id': str(_uuid.uuid4()),
                'segment_type': seg_dict.get('segment_type', 'promo'),
                'participants': [
                    {
                        'wrestler_id': pid,
                        'wrestler_name': wrestler_lookup.get(pid, {}).get('name', pid),
                        'id': pid,
                        'name': wrestler_lookup.get(pid, {}).get('name', pid),
                        'role': 'speaker'
                    }
                    for pid in seg_dict.get('participants', []) if pid
                ],
                'duration_minutes': seg_dict.get('duration', seg_dict.get('duration_minutes', 5)),
                'card_position': seg_dict.get('position', seg_dict.get('card_position', 0)),
                'tone': seg_dict.get('tone', 'intense'),
                'purpose': seg_dict.get('purpose', 'general'),
                'feud_id': seg_dict.get('feud_id'),
            }
            segment = SegmentDraft.from_dict(normalized_seg)
            show_draft.add_segment(segment)
        
        # Save to database
        database.save_show_draft(show_draft, production_plan)
        
        return jsonify({
            'success': True,
            'show_draft': show_draft.to_dict(),
            'production_plan': production_plan,
            'economics_projection': _economics_projection(show_draft, universe, game_state.get('balance', 0)),
            'match_count': len(matches),
            'segment_count': len(segment_dicts)
        })
        
    except Exception as e:
        print(f"Error generating show card: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# AUTO-GENERATE SEGMENTS
# ============================================================================

@booking_bp.route('/generate_segments', methods=['POST'])
def generate_segments():
    """Auto-generate segments based on feuds and match card"""
    try:
        database = get_database()
        data = request.get_json()
        
        show_draft_data = data.get('show_draft')
        
        if not show_draft_data:
            return jsonify({
                'success': False,
                'error': 'No show draft provided'
            }), 400
        
        # Reconstruct ShowDraft from dict
        show_draft = ShowDraft.from_dict(show_draft_data)
        show_draft = _apply_show_context(show_draft, database)
        
        # Get active feuds (no brand filter)
        cursor = database.conn.cursor()
        cursor.execute('''
            SELECT * FROM feuds 
            WHERE status = 'active'
        ''')
        
        active_feuds = []
        for row in cursor.fetchall():
            feud_dict = dict(row)
            # Parse JSON fields
            if 'participant_ids' in feud_dict and feud_dict['participant_ids']:
                try:
                    feud_dict['participant_ids'] = json.loads(feud_dict['participant_ids'])
                except:
                    feud_dict['participant_ids'] = []
            active_feuds.append(feud_dict)
        
        # Initialize Creative Director
        director = CreativeDirector(show_draft)
        
        # Generate segments
        match_dicts = [m.to_dict() for m in show_draft.matches]
        segment_dicts = director.generate_segments_dict(active_feuds, match_dicts)
        
        # Build wrestler lookup for name resolution
        cursor.execute('SELECT id, name FROM wrestlers WHERE is_retired = 0')
        wrestler_lookup = {row['id']: dict(row) for row in cursor.fetchall()}
        
        # Add to show draft with normalized dicts
        for seg_dict in segment_dicts:
            import uuid as _uuid
            normalized_seg = {
                'segment_id': str(_uuid.uuid4()),
                'segment_type': seg_dict.get('segment_type', 'promo'),
                'participants': [
                    {
                        'wrestler_id': pid,
                        'wrestler_name': wrestler_lookup.get(pid, {}).get('name', pid),
                        'id': pid,
                        'name': wrestler_lookup.get(pid, {}).get('name', pid),
                        'role': 'speaker'
                    }
                    for pid in seg_dict.get('participants', []) if pid
                ],
                'duration_minutes': seg_dict.get('duration', seg_dict.get('duration_minutes', 5)),
                'card_position': seg_dict.get('position', seg_dict.get('card_position', 0)),
                'tone': seg_dict.get('tone', 'intense'),
                'purpose': seg_dict.get('purpose', 'general'),
                'feud_id': seg_dict.get('feud_id'),
            }
            segment = SegmentDraft.from_dict(normalized_seg)
            show_draft.add_segment(segment)
        
        # Update in database
        database.save_show_draft(show_draft)
        
        return jsonify({
            'success': True,
            'segments': [s.to_dict() for s in show_draft.segments]
        })
        
    except Exception as e:
        print(f"Error generating segments: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# RUN SHOW (SIMULATE)
# ============================================================================

@booking_bp.route('/run_show', methods=['POST'])
def run_show():
    """Simulate the show, generate results for all matches and segments"""
    try:
        database = get_database()
        universe = current_app.config.get('UNIVERSE')
        data = request.get_json()
        
        show_draft_data = data.get('show_draft')
        production_plan = data.get('production_plan')
        live_interruption_result = None
        
        if not show_draft_data:
            return jsonify({
                'success': False,
                'error': 'No show draft provided'
            }), 400

        try:
            live_mode = data.get('live_interruption_mode', True)
            if live_mode:
                from services.ai_showrunner_service import AIShowrunnerService
                showrunner = current_app.config.get('AI_SHOWRUNNER_SERVICE')
                if showrunner is None:
                    showrunner = AIShowrunnerService(database)
                    current_app.config['AI_SHOWRUNNER_SERVICE'] = showrunner
                live_interruption_result = showrunner.maybe_live_interruption(
                    show_draft_data,
                    universe=universe,
                    seed=data.get('live_interruption_seed'),
                    force=bool(data.get('force_live_interruption', False)),
                    autonomy_level=str(data.get('autonomy_level', 'balanced')).lower(),
                )
                show_draft_data = live_interruption_result.get('show_draft') or show_draft_data
        except Exception as interruption_error:
            print(f"Live interruption warning: {interruption_error}")
        
        # Reconstruct ShowDraft from dict
        show_draft = ShowDraft.from_dict(show_draft_data)

        required_competitor_counts = {
            'triple_threat': 3,
            'fatal_4way': 4,
            'elimination_chamber': 6,
        }
        for match in show_draft.matches:
            match_type = (getattr(match, 'match_type', '') or '').lower()
            required_count = required_competitor_counts.get(match_type)
            if not required_count:
                continue

            side_a_ids = getattr(getattr(match, 'side_a', None), 'wrestler_ids', []) or []
            side_b_ids = getattr(getattr(match, 'side_b', None), 'wrestler_ids', []) or []
            competitor_count = len([wid for wid in side_a_ids + side_b_ids if wid])
            if competitor_count < required_count:
                label = match_type.replace('_', ' ').title()
                return jsonify({
                    'success': False,
                    'error': f'{label} requires {required_count} wrestlers, got {competitor_count}. Please edit the match and select the full field.'
                }), 400
        
        minimum_matches = 3
        show_name_lower = (show_draft.show_name or '').lower()
        if 'rumble royale' in show_name_lower or 'elimination chamber' in show_name_lower:
            minimum_matches = 2
        elif show_name_lower.startswith('legacymania'):
            minimum_matches = 1

        if len(show_draft.matches) < minimum_matches:
            return jsonify({
                'success': False,
                'error': f'Need at least {minimum_matches} match(es) to run show'
            }), 400
        
        if not universe:
            return jsonify({
                'success': False,
                'error': 'Universe state is not available'
            }), 500

        # Import show simulator
        from simulation.show_sim import show_simulator
        
        # Simulate the show
        show_result = show_simulator.simulate_show(show_draft, universe)
        if live_interruption_result and live_interruption_result.get('inserted'):
            intr = live_interruption_result.get('interruption') or {}
            show_result.add_event(
                'live_interruption',
                f"LIVE INTERRUPTION: {intr.get('interruption_type', 'surprise')} altered the show.",
                interruption=intr,
            )

        try:
            from services.booking_story_media_service import BookingStoryMediaService
            media_service = current_app.config.get('BOOKING_STORY_MEDIA_SERVICE')
            if media_service is None:
                media_service = BookingStoryMediaService(database)
                current_app.config['BOOKING_STORY_MEDIA_SERVICE'] = media_service
            media_service.process_show_result(
                show_draft,
                show_result,
                universe,
                production_plan=production_plan,
            )
        except Exception as integration_error:
            print(f"Booking/story/media integration warning: {integration_error}")
        
        # Save show result to database
        database.save_show_result(show_result)

        # Persist all wrestler/title/feud changes created by the simulation
        universe.save_all()

        post_show_fallout = None
        try:
            from services.post_show_fallout_service import PostShowFalloutService
            fallout_service = current_app.config.get('POST_SHOW_FALLOUT_SERVICE')
            if fallout_service is None:
                fallout_service = PostShowFalloutService(database)
                current_app.config['POST_SHOW_FALLOUT_SERVICE'] = fallout_service
            post_show_fallout = fallout_service.generate_for_show(
                show_draft,
                show_result,
                universe=universe,
                seed=data.get('post_show_fallout_seed'),
                force=bool(data.get('force_post_show_fallout', False)),
                autonomy_level=str(data.get('autonomy_level', 'balanced')).lower(),
            )
        except Exception as fallout_error:
            print(f"Post-show fallout warning: {fallout_error}")

        # Advance to the next scheduled show and sync game state to it
        universe.calendar.advance_to_next_show()
        next_show = universe.calendar.get_current_show()
        database.update_game_state(
            current_year=next_show.year if next_show else show_draft.year,
            current_week=next_show.week if next_show else show_draft.week,
            current_show_index=universe.calendar.current_show_index,
            balance=universe.balance,
            show_count=universe.show_count,
            current_brand=next_show.brand if next_show else show_draft.brand
        )
        
        # Clear the draft
        database.clear_show_draft(show_draft.show_id)

        
        # LegacyMania/Rumble Royale progression logic
        try:
            show_name_lower = (show_draft.show_name or '').strip().lower()
            match_lookup = {m.match_id: m for m in show_draft.matches}
            if 'rumble royale' in show_name_lower:
                awarded_divisions = set()

                for result in show_result.match_results:
                    result_match_type = (getattr(result, 'match_type', '') or '').lower()
                    draft_match = match_lookup.get(getattr(result, 'match_id', None))
                    draft_match_type = (getattr(draft_match, 'match_type', '') or '').lower()

                    is_rumble = result_match_type == 'rumble' or draft_match_type == 'rumble'
                    if not is_rumble:
                        continue

                    division = (getattr(draft_match, 'gender_division', None) or 'male').lower()
                    winner_id = _match_result_winner_id(result, draft_match)
                    if winner_id and division not in awarded_divisions:
                        _award_rumble_opportunity(database, universe, winner_id, division, show_draft.year)
                        awarded_divisions.add(division)

            if 'elimination chamber' in show_name_lower:
                awarded_divisions = set()
                for result in show_result.match_results:
                    draft_match = match_lookup.get(getattr(result, 'match_id', None))
                    if not draft_match or (getattr(draft_match, 'match_type', '') or '').lower() != 'elimination_chamber':
                        continue
                    if getattr(draft_match, 'is_title_match', False):
                        continue

                    division = (getattr(draft_match, 'gender_division', None) or 'male').lower()
                    winner_id = _match_result_winner_id(result, draft_match)
                    if winner_id and division not in awarded_divisions:
                        _award_chamber_opportunity(
                            database,
                            universe,
                            winner_id,
                            division,
                            show_draft.year,
                            getattr(draft_match, 'title_id', None),
                        )
                        awarded_divisions.add(division)

            if (show_draft.show_name or '').lower().startswith('legacymania'):
                # Brand transfer: title winners move to title's home brand
                for result in show_result.match_results:
                    if not getattr(result, 'is_title_match', False):
                        continue
                    title_id = getattr(result, 'title_id', None)
                    winner_id = _match_result_winner_id(result, match_lookup.get(getattr(result, 'match_id', None)))
                    if not title_id or not winner_id:
                        continue
                    title = next((t for t in universe.championships if getattr(t, 'id', None) == title_id), None)
                    wrestler = next((w for w in universe.wrestlers if getattr(w, 'id', None) == winner_id), None)
                    target_brand = _get_title_brand(title) if title else None
                    if title and wrestler and target_brand:
                        wrestler.current_brand = target_brand
                        wrestler.primary_brand = target_brand
                universe.save_all()
        except Exception as legacy_err:
            print(f'Legacy progression warning: {legacy_err}')

        show_result_data = show_result.to_dict()
        show_result_data['tv_rating'] = round(show_result.overall_rating * 1.5, 2)
        show_result_data['highlights'] = generate_show_highlights(show_result.match_results, production_plan)
        show_result_data['media_business'] = getattr(show_result, 'media_business_result', None)
        show_result_data['live_interruption'] = (live_interruption_result or {}).get('interruption')
        show_result_data['post_show_fallout'] = (post_show_fallout or {}).get('report')
        
        return jsonify({
            'success': True,
            'show_result': show_result_data,
            'live_interruption': live_interruption_result,
            'post_show_fallout': post_show_fallout,
        })
        
    except Exception as e:
        print(f"Error running show: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@booking_bp.route('/projection', methods=['POST'])
def project_show_profitability():
    """Return a pre-show weekly economics projection for the current draft."""
    try:
        database = get_database()
        universe = get_universe()
        payload = request.get_json() or {}
        show_draft_data = payload.get('show_draft')

        if not show_draft_data:
            return jsonify({'success': False, 'error': 'No show draft provided'}), 400

        show_draft = ShowDraft.from_dict(show_draft_data)
        show_draft = _apply_show_context(show_draft, database)
        game_state = database.get_game_state()
        projection = _economics_projection(show_draft, universe, game_state.get('balance', 0))
        return jsonify({'success': True, 'projection': projection})
    except Exception as e:
        print(f"Error projecting show economics: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500





def _rebalance_matches_for_showcase(matches: list, roster: list, show_type: str) -> list:
    """Ensure more roster variety so more talent gets TV opportunities."""
    if show_type != 'weekly_tv' or not matches:
        return matches

    used = set()
    for m in matches:
        for p in m.get('participants', []):
            if isinstance(p, str):
                used.add(p)
            elif isinstance(p, list):
                used.update([x for x in p if x])
            elif isinstance(p, dict):
                if p.get('male'): used.add(p['male'])
                if p.get('female'): used.add(p['female'])

    available = [w for w in roster if w.get('id') and w.get('id') not in used]
    if len(available) < 2:
        return matches

    a, b = available[0], available[1]
    showcase = {
        'match_type': 'singles',
        'participants': [a['id'], b['id']],
        'is_title_match': False,
        'booking_bias': 'even',
        'importance': 'normal'
    }

    replace_idx = None
    for i, m in enumerate(matches):
        if not m.get('is_title_match') and m.get('match_type') in ('singles', 'triple_threat', 'fatal_4way'):
            replace_idx = i
            break

    if replace_idx is not None:
        matches[replace_idx] = showcase
    else:
        matches.append(showcase)
    return matches


def _is_world_title(title, division: str) -> bool:
    title_name = (getattr(title, 'name', '') or '').lower()
    title_division = (getattr(title, 'division', '') or '').lower()
    division = (division or '').lower()
    if division and title_division and title_division != division:
        return False
    if division == 'female' and 'women' not in title_name:
        return False
    if division == 'male' and 'women' in title_name:
        return False
    return 'world' in title_name


def _world_titles_for_division(universe, division: str) -> list:
    titles = [
        title for title in getattr(universe, 'championships', [])
        if not getattr(title, 'retired', False) and _is_world_title(title, division)
    ]
    return sorted(titles, key=lambda title: getattr(title, 'prestige', 0), reverse=True)


def _get_title_brand(title) -> str:
    return getattr(title, 'current_brand', None) or getattr(title, 'assigned_brand', None) or 'Cross-Brand'


def _get_title_holder(universe, title):
    holder_id = getattr(title, 'current_holder_id', None)
    if not holder_id:
        return None
    return next((w for w in universe.wrestlers if getattr(w, 'id', None) == holder_id), None)


def _match_result_winner_id(match_result, match_draft=None) -> str | None:
    winner_names = list(getattr(match_result, 'winner_names', []) or [])
    if not winner_names:
        return None

    if match_draft:
        for participant in [match_draft.side_a, match_draft.side_b]:
            for wrestler_id, wrestler_name in zip(participant.wrestler_ids, participant.wrestler_names):
                if wrestler_name in winner_names:
                    return wrestler_id

    return None


def _pick_top_wrestlers(roster: list, count: int, exclude_ids=None) -> list:
    exclude_ids = set(exclude_ids or [])
    available = [w for w in roster if w.get('id') not in exclude_ids]
    available.sort(
        key=lambda wrestler: (
            wrestler.get('overall_rating', 0),
            wrestler.get('popularity', 0),
            wrestler.get('momentum', 0),
        ),
        reverse=True,
    )
    return available[:count]


def _make_segment_dict(segment_type: str, participant_ids: list, wrestler_lookup: dict, position: int, purpose: str, tone: str = 'heated') -> dict:
    return {
        'segment_type': segment_type,
        'participants': [pid for pid in participant_ids if pid in wrestler_lookup],
        'duration': 5,
        'position': position,
        'purpose': purpose,
        'tone': tone,
    }


def _ensure_or_heat_legacy_feud(universe, database, challenger_id: str, title, year: int, week: int, show_id: str, source_label: str) -> str:
    challenger = universe.get_wrestler_by_id(challenger_id) if universe else None
    champion = _get_title_holder(universe, title) if universe else None
    if not challenger or not champion or challenger.id == champion.id:
        return ''

    existing_feud = universe.feud_manager.get_feud_between(challenger.id, champion.id)
    if existing_feud:
        desired_intensity = 85 if 'legacymania' in source_label.lower() else 70
        if existing_feud.intensity < desired_intensity:
            existing_feud.adjust_intensity(desired_intensity - existing_feud.intensity)
        existing_feud.add_segment(
            show_id=show_id,
            show_name=source_label,
            year=year,
            week=week,
            segment_type='promo',
            description=f"{challenger.name} and {champion.name} crossed paths on the road to LegacyMania.",
            intensity_change=8
        )
        universe.save_feud(existing_feud)
        return existing_feud.id

    from models.feud import FeudType

    feud = universe.feud_manager.create_feud(
        feud_type=FeudType.PERSONAL,
        participant_ids=[champion.id, challenger.id],
        participant_names=[champion.name, challenger.name],
        year=year,
        week=week,
        show_id=show_id,
        title_id=getattr(title, 'id', None),
        title_name=getattr(title, 'name', None),
        initial_intensity=68
    )
    feud.add_segment(
        show_id=show_id,
        show_name=source_label,
        year=year,
        week=week,
        segment_type='promo',
        description=f"{challenger.name} called out {champion.name} after locking in a LegacyMania opportunity.",
        intensity_change=10
    )
    universe.save_feud(feud)
    return feud.id


def _build_title_challenge_match(title, challenger_id: str, challenger_name: str, feud_id: str, card_position: int, division: str) -> dict | None:
    champion_id = getattr(title, 'current_holder_id', None)
    champion_name = getattr(title, 'current_holder_name', None)
    if not champion_id or not challenger_id:
        return None

    return {
        'match_type': 'singles',
        'participants': [champion_id, challenger_id],
        'gender_division': division,
        'is_intergender': False,
        'is_title_match': True,
        'title_id': getattr(title, 'id', None),
        'title_name': getattr(title, 'name', None),
        'importance': 'high_drama',
        'booking_bias': 'even',
        'feud_id': feud_id,
        'stipulation': f"{getattr(title, 'name', 'World Title')} Championship Match",
        'legacy_challenger_name': challenger_name,
        'legacy_champion_name': champion_name,
        'card_position_override': card_position,
    }


def _book_rumble_royale_special(show_draft: ShowDraft, male_roster: list, female_roster: list, wrestler_lookup: dict) -> tuple[list, list]:
    matches = []
    segments = []

    men = _pick_top_wrestlers(male_roster, 30)
    women = _pick_top_wrestlers(female_roster, 30)

    if len(men) >= 30:
        matches.append({
            'match_type': 'rumble',
            'participants': [w['id'] for w in men],
            'gender_division': 'male',
            'is_intergender': False,
            'importance': 'high_drama',
            'booking_bias': 'even',
            'stipulation': '30-Man Rumble Royale',
        })
        segments.append(_make_segment_dict('promo', [men[0]['id'], men[1]['id']], wrestler_lookup, 0, 'hype_match', 'grand'))

    if len(women) >= 30:
        matches.append({
            'match_type': 'rumble',
            'participants': [w['id'] for w in women],
            'gender_division': 'female',
            'is_intergender': False,
            'importance': 'high_drama',
            'booking_bias': 'even',
            'stipulation': '30-Woman Rumble Royale',
        })
        segments.append(_make_segment_dict('backstage', [women[0]['id'], women[1]['id']], wrestler_lookup, 120, 'build_feud', 'electric'))

    return matches, segments


def _load_legacy_opportunities(database, year: int | None = None) -> list:
    _ensure_legacy_tables(database)
    query = "SELECT * FROM legacy_title_opportunities"
    params = []
    if year is not None:
        query += " WHERE year = ?"
        params.append(year)
    query += " ORDER BY created_at DESC"
    rows = database.conn.cursor().execute(query, tuple(params)).fetchall()
    return [dict(row) for row in rows]


def _book_elimination_chamber_special(show_draft: ShowDraft, male_roster: list, female_roster: list, universe, database, wrestler_lookup: dict) -> tuple[list, list]:
    matches = []
    segments = []
    opportunities = _load_legacy_opportunities(database, show_draft.year)

    for division, roster in [('male', male_roster), ('female', female_roster)]:
        titles = _world_titles_for_division(universe, division)
        if len(titles) < 2:
            continue

        rumble_row = next(
            (
                row for row in opportunities
                if row.get('division') == division and row.get('source_event') == 'Rumble Royale'
            ),
            None,
        )
        chosen_title_id = rumble_row.get('target_title_id') if rumble_row else None
        target_title = next((title for title in titles if getattr(title, 'id', None) != chosen_title_id), None) or titles[0]

        chamber_field = _get_title_holder(universe, target_title)
        exclude_ids = {row.get('winner_id') for row in opportunities if row.get('division') == division}
        if chamber_field:
            exclude_ids.add(chamber_field.id)
        entrants = _pick_top_wrestlers(roster, 6, exclude_ids=exclude_ids)
        if len(entrants) < 6:
            continue

        matches.append({
            'match_type': 'elimination_chamber',
            'participants': [entrant['id'] for entrant in entrants],
            'gender_division': division,
            'is_intergender': False,
            'importance': 'high_drama',
            'booking_bias': 'even',
            'is_title_match': False,
            'title_id': getattr(target_title, 'id', None),
            'title_name': getattr(target_title, 'name', None),
            'special_match_type': 'elimination_chamber',
            'stipulation': f"Elimination Chamber - {getattr(target_title, 'name', 'World Title')} Contender",
        })
        segments.append(
            _make_segment_dict(
                'promo',
                [entrant['id'] for entrant in entrants[:2]],
                wrestler_lookup,
                80 if division == 'male' else 180,
                'build_feud',
                'heated',
            )
        )

    return matches, segments


def _book_legacymania_title_matches(show_draft: ShowDraft, universe, database) -> tuple[list, list]:
    opportunities = _load_legacy_opportunities(database, show_draft.year)
    current_night = 'Night 1' if 'night 1' in (show_draft.show_name or '').lower() else 'Night 2'
    matches = []
    segments = []
    card_position = 90

    for row in opportunities:
        if row.get('status') not in {'assigned', 'auto-assigned'}:
            continue
        if (row.get('legacy_night') or 'Night 1') != current_night:
            continue
        if not row.get('target_title_id'):
            continue

        title = next((t for t in universe.championships if getattr(t, 'id', None) == row.get('target_title_id')), None)
        challenger = universe.get_wrestler_by_id(row.get('winner_id')) if universe else None
        if not title or not challenger:
            continue

        feud_id = _ensure_or_heat_legacy_feud(
            universe,
            database,
            challenger.id,
            title,
            show_draft.year,
            show_draft.week,
            show_draft.show_id,
            'LegacyMania'
        )
        match_dict = _build_title_challenge_match(
            title,
            challenger.id,
            challenger.name,
            feud_id,
            card_position,
            row.get('division') or getattr(title, 'division', 'male')
        )
        if match_dict:
            matches.append(match_dict)
            champion = _get_title_holder(universe, title)
            if champion:
                segments.append({
                    'segment_type': 'promo',
                    'participants': [champion.id, challenger.id],
                    'duration': 6,
                    'position': max(0, card_position - 10),
                    'purpose': 'build_feud',
                    'tone': 'heated',
                    'feud_id': feud_id,
                })
            card_position += 40

    return matches, segments

def _ensure_legacy_tables(database):
    c = database.conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS legacy_title_opportunities (
            id TEXT PRIMARY KEY,
            year INTEGER NOT NULL,
            source_event TEXT NOT NULL,
            reward_type TEXT NOT NULL DEFAULT 'world_title_shot',
            winner_id TEXT NOT NULL,
            winner_name TEXT NOT NULL,
            division TEXT NOT NULL,
            target_title_id TEXT,
            target_title_name TEXT,
            target_brand TEXT,
            legacy_night TEXT DEFAULT 'Night 1',
            champion_id TEXT,
            champion_name TEXT,
            feud_id TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            storyline_text TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    database.conn.commit()


def _upsert_legacy_opportunity(
    database,
    universe,
    *,
    source_event: str,
    reward_type: str,
    winner_id: str,
    division: str,
    year: int,
    target_title,
    legacy_night: str,
    storyline: str,
    notes: str = '',
):
    import uuid as _uuid
    _ensure_legacy_tables(database)
    winner = next((w for w in universe.wrestlers if getattr(w, 'id', None) == winner_id), None)
    if not winner:
        return None

    c = database.conn.cursor()
    target_brand = _get_title_brand(target_title) if target_title else None
    champion = _get_title_holder(universe, target_title) if target_title else None
    feud_id = _ensure_or_heat_legacy_feud(
        universe,
        database,
        winner_id,
        target_title,
        year,
        0,
        f"legacy_{source_event.lower().replace(' ', '_')}_{division}_{year}",
        source_event,
    ) if target_title else ''
    existing = c.execute(
        """
        SELECT id FROM legacy_title_opportunities
        WHERE year=? AND division=? AND source_event=?
        ORDER BY created_at DESC LIMIT 1
        """,
        (year, division, source_event)
    ).fetchone()
    payload = (
        source_event,
        reward_type,
        winner_id,
        getattr(winner, 'name', winner_id),
        division,
        getattr(target_title, 'id', None),
        getattr(target_title, 'name', None),
        target_brand,
        legacy_night,
        getattr(champion, 'id', None),
        getattr(champion, 'name', None),
        feud_id,
        'auto-assigned',
        storyline,
        notes,
        datetime.now().isoformat(),
    )

    if existing:
        c.execute(
            """
            UPDATE legacy_title_opportunities
            SET source_event=?, reward_type=?, winner_id=?, winner_name=?, division=?,
                target_title_id=?, target_title_name=?, target_brand=?, legacy_night=?,
                champion_id=?, champion_name=?, feud_id=?, status=?, storyline_text=?, notes=?, updated_at=?
            WHERE id=?
            """,
            payload + (existing['id'],)
        )
        opportunity_id = existing['id']
    else:
        c.execute(
            """
            INSERT INTO legacy_title_opportunities
            (id, year, source_event, reward_type, winner_id, winner_name, division, target_title_id, target_title_name, target_brand, legacy_night,
             champion_id, champion_name, feud_id, status, storyline_text, notes, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (str(_uuid.uuid4()), year) + payload + (datetime.now().isoformat(),)
        )
        opportunity_id = c.lastrowid
    database.conn.commit()
    return opportunity_id


def _award_rumble_opportunity(database, universe, winner_id: str, division: str, year: int):
    titles = _world_titles_for_division(universe, division)[:2]
    target_title = titles[0] if titles else None
    legacy_night = 'Night 1' if division == 'male' else 'Night 2'
    winner = next((w for w in universe.wrestlers if getattr(w, 'id', None) == winner_id), None)
    winner_name = getattr(winner, 'name', winner_id)
    storyline = (
        f"After outlasting 29 opponents in the {division.title()} Rumble Royale, "
        f"{winner_name} has locked in a LegacyMania world-title challenge. ROC Creative is already framing the road "
        f"to {getattr(target_title, 'name', 'a world title')} through heated promos, recap packages, and social media callouts."
    )
    _upsert_legacy_opportunity(
        database,
        universe,
        source_event='Rumble Royale',
        reward_type='world_title_shot',
        winner_id=winner_id,
        division=division,
        year=year,
        target_title=target_title,
        legacy_night=legacy_night,
        storyline=storyline,
        notes='Auto-created from Rumble Royale victory.',
    )


def _award_chamber_opportunity(database, universe, winner_id: str, division: str, year: int, target_title_id: str | None):
    titles = _world_titles_for_division(universe, division)
    target_title = next((title for title in titles if getattr(title, 'id', None) == target_title_id), None)
    if not target_title:
        target_title = titles[0] if titles else None
    legacy_night = 'Night 2' if division == 'male' else 'Night 1'
    winner = next((w for w in universe.wrestlers if getattr(w, 'id', None) == winner_id), None)
    winner_name = getattr(winner, 'name', winner_id)
    storyline = (
        f"Winning inside the brutal Elimination Chamber has pushed {winner_name} into the other world-title picture for LegacyMania. "
        f"ROC Creative will keep the pressure on with face-offs, backstage shots, and heated recaps until the big stage."
    )
    _upsert_legacy_opportunity(
        database,
        universe,
        source_event='Elimination Chamber',
        reward_type='world_title_shot',
        winner_id=winner_id,
        division=division,
        year=year,
        target_title=target_title,
        legacy_night=legacy_night,
        storyline=storyline,
        notes='Auto-created from Elimination Chamber victory.',
    )

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_show_financials(show_type: str, overall_rating: float, 
                              production_plan: dict) -> tuple:
    """Calculate attendance and revenue"""
    
    # Base attendance
    base_attendance = {
        'weekly_tv': 5000,
        'minor_ppv': 10000,
        'major_ppv': 15000
    }.get(show_type, 5000)
    
    # Rating multiplier (0.0 - 5.0 -> 0.5 - 1.5)
    rating_multiplier = 0.5 + (overall_rating / 5.0)
    
    # Production plan bonus
    plan_multiplier = 1.0
    if production_plan:
        plan_multiplier += production_plan.get('theme_bonus_attendance_pct', 0.0)
    
    attendance = int(base_attendance * rating_multiplier * plan_multiplier)
    min_attendance = {
        'weekly_tv': 50000,
        'minor_ppv': 80000,
        'major_ppv': 150000
    }.get(show_type, 50000)
    attendance = max(min_attendance, attendance)
    
    # Revenue
    ticket_price = {
        'weekly_tv': 50,
        'minor_ppv': 75,
        'major_ppv': 100
    }.get(show_type, 50)
    database = get_database()
    if database:
        try:
            cursor = database.conn.cursor()
            cursor.execute("SELECT show_ticket_prices_json FROM finance_settings WHERE id = 1")
            row = cursor.fetchone()
            if row and row[0]:
                prices = json.loads(row[0])
                ticket_price = int(prices.get(show_type, ticket_price))
        except Exception:
            pass
    
    revenue = attendance * ticket_price
    
    return attendance, revenue

def generate_show_highlights(match_results: list, production_plan: dict) -> list:
    """Generate narrative highlights from show results"""
    highlights = []

    def format_match_label(match_result) -> str:
        title_name = getattr(match_result, 'title_name', None)
        if title_name:
            return title_name

        special_match_type = getattr(match_result, 'special_match_type', None)
        if special_match_type:
            return special_match_type.replace('_', ' ').title()

        match_type = getattr(match_result, 'match_type', 'singles')
        return match_type.replace('_', ' ').title()
    
    # Find best match
    if match_results:
        best_match = max(match_results, key=lambda x: x.star_rating)
        if best_match.star_rating >= 4.0:
            highlights.append(
                f"⭐ Match of the Night: {best_match.match_type.replace('_', ' ').title()} "
                f"({best_match.star_rating:.2f} stars)"
            )
    
    # Title changes
    title_changes = [r for r in match_results if getattr(r, 'title_changed_hands', False)]
    for change in title_changes:
        highlights.append(
            f"🏆 NEW CHAMPION: Title changed hands in "
            f"{change.match_type.replace('_', ' ')}"
        )
    
    # Intergender matches
    intergender_matches = [r for r in match_results 
                          if r.match_type in ['mixed_tag', 'intergender_singles']]
    if intergender_matches:
        highlights.append(
            f"⚥ Historic intergender action with {len(intergender_matches)} "
            f"mixed match(es)"
        )
    
    # Production plan theme
    if production_plan and production_plan.get('theme') != 'standard':
        highlights.append(
            f"🎨 Special theme: {production_plan.get('theme_display_name', 'Special Event')}"
        )
    
    return highlights

def generate_show_highlights(match_results: list, production_plan: dict) -> list:
    """Generate narrative highlights from show results."""
    highlights = []

    def format_match_label(match_result) -> str:
        title_name = getattr(match_result, 'title_name', None)
        if title_name:
            return title_name

        special_match_type = getattr(match_result, 'special_match_type', None)
        if special_match_type:
            return special_match_type.replace('_', ' ').title()

        match_type = getattr(match_result, 'match_type', 'singles')
        return match_type.replace('_', ' ').title()

    if match_results:
        best_match = max(match_results, key=lambda result: result.star_rating)
        if best_match.star_rating >= 4.0:
            highlights.append(
                f"Match of the Night: {format_match_label(best_match)} "
                f"({best_match.star_rating:.2f} stars)"
            )

    title_changes = [result for result in match_results if getattr(result, 'title_changed_hands', False)]
    for change in title_changes:
        champion_name = (
            getattr(change, 'new_champion_name', None)
            or ', '.join(getattr(change, 'winner_names', []))
            or 'A new champion'
        )
        highlights.append(
            f"NEW CHAMPION: {champion_name} won the {format_match_label(change)}"
        )

    intergender_matches = [
        result for result in match_results
        if getattr(result, 'match_type', '') in ['mixed_tag', 'intergender_singles']
    ]
    if intergender_matches:
        highlights.append(
            f"Historic intergender action with {len(intergender_matches)} mixed match(es)"
        )

    if production_plan and production_plan.get('theme') != 'standard':
        highlights.append(
            f"Special theme: {production_plan.get('theme_display_name', 'Special Event')}"
        )

    return highlights


def _backfill_rumble_opportunities_from_history(database, universe):
    """Recover missing male/female Rumble opportunities from saved match history."""
    import json
    import re

    _ensure_legacy_tables(database)
    cursor = database.conn.cursor()
    rows = cursor.execute(
        """
        SELECT year, side_a_names, match_summary
        FROM match_history
        WHERE lower(show_name) LIKE '%rumble royale%'
          AND lower(match_summary) LIKE '%won the rumble%'
        ORDER BY id
        """
    ).fetchall()
    if not rows:
        return

    existing = {
        (row['year'], row['division'])
        for row in cursor.execute(
            """
            SELECT year, division
            FROM legacy_title_opportunities
            WHERE source_event = 'Rumble Royale'
            """
        ).fetchall()
    }
    wrestlers_by_name = {getattr(w, 'name', ''): w for w in getattr(universe, 'wrestlers', [])}

    for row in rows:
        summary = row['match_summary'] or ''
        winner_match = re.match(r'(.+?) won the RUMBLE', summary, flags=re.IGNORECASE)
        if not winner_match:
            continue
        winner_name = winner_match.group(1).strip()
        winner = wrestlers_by_name.get(winner_name)
        if not winner:
            continue

        gender = str(getattr(winner, 'gender', '') or '').lower()
        division = 'female' if gender in ('female', 'woman', 'women') else 'male'
        if (row['year'], division) in existing:
            continue

        try:
            participant_names = json.loads(row['side_a_names'] or '[]')
        except Exception:
            participant_names = []
        if division == 'female' and len(participant_names) < 20:
            continue

        _award_rumble_opportunity(database, universe, winner.id, division, row['year'])
        existing.add((row['year'], division))


@booking_bp.route('/legacy/rumble-opportunities', methods=['GET'])
def get_rumble_opportunities():
    try:
        database = get_database()
        universe = get_universe()
        _ensure_legacy_tables(database)
        _backfill_rumble_opportunities_from_history(database, universe)
        game_state = database.get_game_state() or {}
        current_year = game_state.get('current_year') or getattr(universe, 'current_year', None)
        cursor = database.conn.cursor()
        rows = []
        if current_year is not None:
            rows = cursor.execute(
                """
                SELECT * FROM legacy_title_opportunities
                WHERE year = ?
                ORDER BY created_at DESC
                """,
                (current_year,)
            ).fetchall()
        if not rows:
            rows = cursor.execute(
                """
                SELECT * FROM legacy_title_opportunities
                ORDER BY year DESC, created_at DESC
                """
            ).fetchall()

        seen = set()
        opportunities = []
        for row in rows:
            data = dict(row)
            key = (data.get('year'), data.get('source_event'), data.get('division'))
            if key in seen:
                continue
            seen.add(key)
            opportunities.append(data)

        return jsonify({'success': True, 'opportunities': opportunities[:50]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@booking_bp.route('/legacy/rumble-opportunities/<opp_id>/assign', methods=['POST'])
def assign_rumble_opportunity(opp_id):
    try:
        database = get_database()
        universe = get_universe()
        payload = request.get_json() or {}
        target_title_id = payload.get('target_title_id')
        target_title_name = payload.get('target_title_name')
        target_brand = payload.get('target_brand')
        legacy_night = payload.get('legacy_night')
        status = payload.get('status', 'assigned')

        _ensure_legacy_tables(database)
        database.conn.cursor().execute(
            """
            UPDATE legacy_title_opportunities
            SET target_title_id=?, target_title_name=?, target_brand=?, legacy_night=?, status=?,
                storyline_text = COALESCE(storyline_text,'') || ?, updated_at=?
            WHERE id=?
            """,
            (
                target_title_id,
                target_title_name,
                target_brand,
                legacy_night,
                status,
                f' Assigned to {legacy_night} challenge.',
                datetime.now().isoformat(),
                opp_id,
            )
        )
        row = database.conn.cursor().execute(
            "SELECT * FROM legacy_title_opportunities WHERE id=?",
            (opp_id,),
        ).fetchone()
        database.conn.commit()

        if row and universe and target_title_id:
            row = dict(row)
            title = next((t for t in universe.championships if getattr(t, 'id', None) == target_title_id), None)
            if title:
                feud_id = _ensure_or_heat_legacy_feud(
                    universe,
                    database,
                    row.get('winner_id'),
                    title,
                    row.get('year', 1),
                    0,
                    f"legacy_assignment_{opp_id}",
                    'LegacyMania Assignment',
                )
                if feud_id:
                    database.conn.cursor().execute(
                        "UPDATE legacy_title_opportunities SET feud_id=?, updated_at=? WHERE id=?",
                        (feud_id, datetime.now().isoformat(), opp_id),
                    )
                    database.conn.commit()
        return jsonify({'success': True, 'id': opp_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# GET/DELETE SHOW DRAFT
# ============================================================================

@booking_bp.route('/draft/<show_id>', methods=['GET'])
def get_show_draft(show_id):
    """Get a show draft with all matches and segments"""
    try:
        database = get_database()
        show_draft = database.get_show_draft(show_id)
        
        if not show_draft:
            return jsonify({
                'success': False,
                'error': 'Show draft not found'
            }), 404
        
        production_plan = database.get_production_plan(show_id)
        
        return jsonify({
            'success': True,
            'show': show_draft,
            'production_plan': production_plan
        })
        
    except Exception as e:
        print(f"Error getting show draft: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@booking_bp.route('/draft/<show_id>', methods=['DELETE'])
def delete_show_draft(show_id):
    """Delete a show draft"""
    try:
        database = get_database()
        success = database.clear_show_draft(show_id)
        
        if not success:
            return jsonify({
                'success': False,
                'error': 'Show draft not found'
            }), 404
        
        return jsonify({
            'success': True,
            'message': 'Show draft deleted'
        })
        
    except Exception as e:
        print(f"Error deleting show draft: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
