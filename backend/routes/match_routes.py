"""
Match Routes - Match Simulation & Testing
"""

from flask import Blueprint, jsonify, request, current_app
import time
from models.match import MatchDraft, MatchParticipant, BookingBias, MatchImportance
from simulation.match_sim import match_simulator

match_bp = Blueprint('match', __name__)


def get_universe():
    return current_app.config['UNIVERSE']


@match_bp.route('/api/test/simulate-match', methods=['POST'])
def api_test_simulate_match():
    universe = get_universe()
    
    try:
        data = request.get_json()
        
        wrestler_a_id = data.get('wrestler_a_id')
        wrestler_b_id = data.get('wrestler_b_id')
        
        wrestler_a = universe.get_wrestler_by_id(wrestler_a_id)
        wrestler_b = universe.get_wrestler_by_id(wrestler_b_id)
        
        if not wrestler_a or not wrestler_b:
            return jsonify({'error': 'One or both wrestlers not found'}), 404
        
        booking_bias_str = data.get('booking_bias', 'even')
        importance_str = data.get('importance', 'normal')
        is_title_match = data.get('is_title_match', False)
        title_id = data.get('title_id')
        
        booking_bias = BookingBias(booking_bias_str)
        importance = MatchImportance(importance_str)
        
        title_name = None
        if is_title_match and title_id:
            title = universe.get_championship_by_id(title_id)
            title_name = title.name if title else None
        
        existing_feud = universe.feud_manager.get_feud_between(wrestler_a.id, wrestler_b.id)
        feud_id = existing_feud.id if existing_feud else None
        
        match_draft = MatchDraft(
            match_id=f"test_match_{wrestler_a_id}_vs_{wrestler_b_id}",
            side_a=MatchParticipant(
                wrestler_ids=[wrestler_a.id],
                wrestler_names=[wrestler_a.name],
                is_tag_team=False
            ),
            side_b=MatchParticipant(
                wrestler_ids=[wrestler_b.id],
                wrestler_names=[wrestler_b.name],
                is_tag_team=False
            ),
            match_type='singles',
            is_title_match=is_title_match,
            title_id=title_id,
            title_name=title_name,
            card_position=5,
            booking_bias=booking_bias,
            importance=importance,
            feud_id=feud_id
        )
        
        result = match_simulator.simulate_match(
            match_draft,
            [wrestler_a],
            [wrestler_b]
        )
        
        if result.is_upset:
            from models.feud import FeudType
            
            winner_id = wrestler_a.id if result.winner == 'side_a' else wrestler_b.id
            winner_name = wrestler_a.name if result.winner == 'side_a' else wrestler_b.name
            loser_id = wrestler_b.id if result.winner == 'side_a' else wrestler_a.id
            loser_name = wrestler_b.name if result.winner == 'side_a' else wrestler_a.name
            
            feud = universe.feud_manager.auto_create_from_upset(
                winner_id=winner_id,
                winner_name=winner_name,
                loser_id=loser_id,
                loser_name=loser_name,
                year=universe.current_year,
                week=universe.current_week,
                show_id="test_show"
            )
            
            universe.save_feud(feud)
            
            return jsonify({
                'success': True,
                'match_result': result.to_dict(),
                'feud_created': True,
                'feud': feud.to_dict()
            })
        
        return jsonify({
            'success': True,
            'match_result': result.to_dict(),
            'feud_created': False
        })
    
    except ValueError as e:
        return jsonify({'error': f'Invalid parameter: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'Simulation failed: {str(e)}'}), 500


@match_bp.route('/api/test/quick-match')
def api_test_quick_match():
    universe = get_universe()
    
    try:
        import random
        
        active = universe.get_active_wrestlers()
        if len(active) < 2:
            return jsonify({'error': 'Not enough active wrestlers'}), 400
        
        wrestler_a, wrestler_b = random.sample(active, 2)
        
        match_draft = MatchDraft(
            match_id=f"quick_test_{wrestler_a.id}_vs_{wrestler_b.id}",
            side_a=MatchParticipant(
                wrestler_ids=[wrestler_a.id],
                wrestler_names=[wrestler_a.name],
                is_tag_team=False
            ),
            side_b=MatchParticipant(
                wrestler_ids=[wrestler_b.id],
                wrestler_names=[wrestler_b.name],
                is_tag_team=False
            ),
            match_type='singles',
            card_position=5,
            booking_bias=BookingBias.EVEN,
            importance=MatchImportance.NORMAL
        )
        
        result = match_simulator.simulate_match(
            match_draft,
            [wrestler_a],
            [wrestler_b]
        )
        
        return jsonify({
            'success': True,
            'match_result': result.to_dict()
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# MULTI-COMPETITOR MATCH TESTING (STEP 14)
# ============================================================================

@match_bp.route('/api/test/triple-threat', methods=['POST'])
def api_test_triple_threat():
    universe = get_universe()
    
    try:
        data = request.get_json()
        
        wrestler_ids = data.get('wrestler_ids', [])
        if len(wrestler_ids) != 3:
            return jsonify({'error': 'Triple threat requires exactly 3 wrestlers'}), 400
        
        wrestlers = [universe.get_wrestler_by_id(wid) for wid in wrestler_ids]
        wrestlers = [w for w in wrestlers if w]
        
        if len(wrestlers) != 3:
            return jsonify({'error': 'One or more wrestlers not found'}), 404
        
        booking_bias = BookingBias(data.get('booking_bias', 'even'))
        importance = MatchImportance(data.get('importance', 'normal'))
        
        match_draft = MatchDraft(
            match_id=f"test_triple_threat_{int(time.time())}",
            side_a=MatchParticipant(
                wrestler_ids=wrestler_ids,
                wrestler_names=[w.name for w in wrestlers],
                is_tag_team=False
            ),
            side_b=MatchParticipant(
                wrestler_ids=[],
                wrestler_names=[],
                is_tag_team=False
            ),
            match_type='triple_threat',
            card_position=5,
            booking_bias=booking_bias,
            importance=importance
        )
        
        result = match_simulator.simulate_match(
            match_draft,
            wrestlers,
            [],
            universe_state=universe
        )
        
        return jsonify({
            'success': True,
            'match_result': result.to_dict()
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@match_bp.route('/api/test/fatal-4way', methods=['POST'])
def api_test_fatal_4way():
    universe = get_universe()
    
    try:
        data = request.get_json()
        
        wrestler_ids = data.get('wrestler_ids', [])
        if len(wrestler_ids) != 4:
            return jsonify({'error': 'Fatal 4-way requires exactly 4 wrestlers'}), 400
        
        wrestlers = [universe.get_wrestler_by_id(wid) for wid in wrestler_ids]
        wrestlers = [w for w in wrestlers if w]
        
        if len(wrestlers) != 4:
            return jsonify({'error': 'One or more wrestlers not found'}), 404
        
        match_draft = MatchDraft(
            match_id=f"test_fatal_4way_{int(time.time())}",
            side_a=MatchParticipant(
                wrestler_ids=wrestler_ids,
                wrestler_names=[w.name for w in wrestlers],
                is_tag_team=False
            ),
            side_b=MatchParticipant(
                wrestler_ids=[],
                wrestler_names=[],
                is_tag_team=False
            ),
            match_type='fatal_4way',
            card_position=5,
            booking_bias=BookingBias(data.get('booking_bias', 'even')),
            importance=MatchImportance(data.get('importance', 'normal'))
        )
        
        result = match_simulator.simulate_match(
            match_draft,
            wrestlers,
            [],
            universe_state=universe
        )
        
        return jsonify({
            'success': True,
            'match_result': result.to_dict()
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@match_bp.route('/api/test/battle-royal', methods=['POST'])
def api_test_battle_royal():
    universe = get_universe()
    
    try:
        data = request.get_json()
        
        wrestler_ids = data.get('wrestler_ids', [])
        match_type = data.get('match_type', 'battle_royal')
        
        if len(wrestler_ids) < 8:
            return jsonify({'error': 'Battle royals require at least 8 wrestlers'}), 400
        
        wrestlers = [universe.get_wrestler_by_id(wid) for wid in wrestler_ids]
        wrestlers = [w for w in wrestlers if w]
        
        if len(wrestlers) < 8:
            return jsonify({'error': 'Not enough valid wrestlers found'}), 404
        
        match_draft = MatchDraft(
            match_id=f"test_{match_type}_{int(time.time())}",
            side_a=MatchParticipant(
                wrestler_ids=wrestler_ids,
                wrestler_names=[w.name for w in wrestlers],
                is_tag_team=False
            ),
            side_b=MatchParticipant(
                wrestler_ids=[],
                wrestler_names=[],
                is_tag_team=False
            ),
            match_type=match_type,
            card_position=8,
            booking_bias=BookingBias.EVEN,
            importance=MatchImportance.HIGH_DRAMA
        )
        
        result = match_simulator.simulate_match(
            match_draft,
            wrestlers,
            [],
            universe_state=universe
        )
        
        return jsonify({
            'success': True,
            'match_result': result.to_dict()
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@match_bp.route('/api/test/random-battle-royal')
def api_test_random_battle_royal():
    universe = get_universe()
    
    try:
        import random
        
        active_wrestlers = universe.get_active_wrestlers()
        
        if len(active_wrestlers) < 20:
            return jsonify({'error': f'Not enough active wrestlers (need 20, have {len(active_wrestlers)})'}), 400
        
        participants = random.sample(active_wrestlers, 20)
        wrestler_ids = [w.id for w in participants]
        
        match_draft = MatchDraft(
            match_id=f"test_random_br_{int(time.time())}",
            side_a=MatchParticipant(
                wrestler_ids=wrestler_ids,
                wrestler_names=[w.name for w in participants],
                is_tag_team=False
            ),
            side_b=MatchParticipant(
                wrestler_ids=[],
                wrestler_names=[],
                is_tag_team=False
            ),
            match_type='battle_royal',
            card_position=8,
            booking_bias=BookingBias.EVEN,
            importance=MatchImportance.HIGH_DRAMA
        )
        
        result = match_simulator.simulate_match(
            match_draft,
            participants,
            [],
            universe_state=universe
        )
        
        return jsonify({
            'success': True,
            'match_result': result.to_dict()
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@match_bp.route('/api/test/random-rumble')
def api_test_random_rumble():
    universe = get_universe()
    
    try:
        import random
        
        active_wrestlers = universe.get_active_wrestlers()
        
        if len(active_wrestlers) < 30:
            return jsonify({'error': f'Not enough active wrestlers (need 30, have {len(active_wrestlers)})'}), 400
        
        participants = random.sample(active_wrestlers, 30)
        wrestler_ids = [w.id for w in participants]
        
        match_draft = MatchDraft(
            match_id=f"test_rumble_{int(time.time())}",
            side_a=MatchParticipant(
                wrestler_ids=wrestler_ids,
                wrestler_names=[w.name for w in participants],
                is_tag_team=False
            ),
            side_b=MatchParticipant(
                wrestler_ids=[],
                wrestler_names=[],
                is_tag_team=False
            ),
            match_type='rumble',
            card_position=8,
            booking_bias=BookingBias.EVEN,
            importance=MatchImportance.HIGH_DRAMA
        )
        
        result = match_simulator.simulate_match(
            match_draft,
            participants,
            [],
            universe_state=universe
        )
        
        return jsonify({
            'success': True,
            'match_result': result.to_dict()
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500