"""
Segment Routes - Segments & Promos (Step 15)
"""

from flask import Blueprint, jsonify, request, current_app
import traceback

segment_bp = Blueprint('segment', __name__)


def get_universe():
    return current_app.config['UNIVERSE']


@segment_bp.route('/api/segments/test/promo', methods=['POST'])
def api_test_segment_promo():
    universe = get_universe()
    
    try:
        from models.segment import SegmentTemplate, SegmentTone
        from simulation.segment_sim import segment_simulator
        
        data = request.get_json()
        
        wrestler_id = data.get('wrestler_id')
        tone_str = data.get('tone', 'intense')
        feud_id = data.get('feud_id')
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        segment_draft = SegmentTemplate.create_promo(
            speaker_id=wrestler.id,
            speaker_name=wrestler.name,
            mic_skill=wrestler.mic,
            feud_id=feud_id,
            tone=SegmentTone(tone_str)
        )
        
        wrestler_dict = {wrestler.id: wrestler}
        result = segment_simulator.simulate_segment(segment_draft, wrestler_dict)
        
        return jsonify({
            'success': True,
            'segment_result': result.to_dict()
        })
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@segment_bp.route('/api/segments/test/promo-battle', methods=['POST'])
def api_test_segment_promo_battle():
    universe = get_universe()
    
    try:
        from models.segment import SegmentTemplate
        from simulation.segment_sim import segment_simulator
        
        data = request.get_json()
        
        wrestler_ids = data.get('wrestler_ids', [])
        feud_id = data.get('feud_id')
        
        if len(wrestler_ids) < 2:
            return jsonify({'error': 'At least 2 wrestlers required'}), 400
        
        wrestlers = [universe.get_wrestler_by_id(wid) for wid in wrestler_ids]
        wrestlers = [w for w in wrestlers if w]
        
        if len(wrestlers) < 2:
            return jsonify({'error': 'One or more wrestlers not found'}), 404
        
        participants = [(w.id, w.name, w.mic) for w in wrestlers]
        
        segment_draft = SegmentTemplate.create_promo_battle(
            participants=participants,
            feud_id=feud_id
        )
        
        wrestler_dict = {w.id: w for w in wrestlers}
        result = segment_simulator.simulate_segment(segment_draft, wrestler_dict)
        
        return jsonify({
            'success': True,
            'segment_result': result.to_dict()
        })
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@segment_bp.route('/api/segments/test/interview', methods=['POST'])
def api_test_segment_interview():
    universe = get_universe()
    
    try:
        from models.segment import SegmentTemplate
        from simulation.segment_sim import segment_simulator
        
        data = request.get_json()
        
        wrestler_id = data.get('wrestler_id')
        interviewer_name = data.get('interviewer_name', 'Rachel Stone')
        feud_id = data.get('feud_id')
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        segment_draft = SegmentTemplate.create_interview(
            interviewer_name=interviewer_name,
            subject_id=wrestler.id,
            subject_name=wrestler.name,
            mic_skill=wrestler.mic,
            feud_id=feud_id
        )
        
        wrestler_dict = {wrestler.id: wrestler}
        result = segment_simulator.simulate_segment(segment_draft, wrestler_dict)
        
        return jsonify({
            'success': True,
            'segment_result': result.to_dict()
        })
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@segment_bp.route('/api/segments/test/attack', methods=['POST'])
def api_test_segment_attack():
    universe = get_universe()
    
    try:
        from models.segment import SegmentTemplate
        from simulation.segment_sim import segment_simulator
        
        data = request.get_json()
        
        attacker_id = data.get('attacker_id')
        victim_id = data.get('victim_id')
        location = data.get('location', 'backstage')
        
        attacker = universe.get_wrestler_by_id(attacker_id)
        victim = universe.get_wrestler_by_id(victim_id)
        
        if not attacker or not victim:
            return jsonify({'error': 'One or both wrestlers not found'}), 404
        
        segment_draft = SegmentTemplate.create_attack(
            attacker_id=attacker.id,
            attacker_name=attacker.name,
            victim_id=victim.id,
            victim_name=victim.name,
            location=location
        )
        
        wrestler_dict = {
            attacker.id: attacker,
            victim.id: victim
        }
        result = segment_simulator.simulate_segment(segment_draft, wrestler_dict)
        
        return jsonify({
            'success': True,
            'segment_result': result.to_dict()
        })
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@segment_bp.route('/api/segments/generate', methods=['POST'])
def api_generate_show_segments():
    universe = get_universe()
    
    try:
        from creative.segments import segment_generator
        
        data = request.get_json()
        
        show_type = data.get('show_type', 'weekly_tv')
        is_ppv = data.get('is_ppv', False)
        brand = data.get('brand', 'ROC Alpha')
        
        if brand == 'Cross-Brand':
            brand_roster = universe.get_active_wrestlers()
            active_feuds = universe.feud_manager.get_active_feuds()
            titles = universe.championships
        else:
            brand_roster = universe.get_wrestlers_by_brand(brand)
            active_feuds = []
            for feud in universe.feud_manager.get_active_feuds():
                for pid in feud.participant_ids:
                    wrestler = universe.get_wrestler_by_id(pid)
                    if wrestler and wrestler.primary_brand == brand:
                        active_feuds.append(feud)
                        break
            titles = [c for c in universe.championships 
                     if c.assigned_brand == brand or c.assigned_brand == 'Cross-Brand']
        
        segments = segment_generator.generate_segments_for_show(
            show_type=show_type,
            is_ppv=is_ppv,
            brand_roster=brand_roster,
            active_feuds=active_feuds,
            titles=titles
        )
        
        return jsonify({
            'success': True,
            'total': len(segments),
            'segments': [s.to_dict() for s in segments]
        })
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@segment_bp.route('/api/segments/test/random-promo')
def api_test_segment_random_promo():
    universe = get_universe()
    
    try:
        from models.segment import SegmentTemplate, SegmentTone
        from simulation.segment_sim import segment_simulator
        import random
        
        active_wrestlers = universe.get_active_wrestlers()
        
        good_talkers = [w for w in active_wrestlers if w.mic >= 60]
        
        if not good_talkers:
            good_talkers = active_wrestlers
        
        if not good_talkers:
            return jsonify({'error': 'No active wrestlers available'}), 400
        
        wrestler = random.choice(good_talkers)
        
        segment_draft = SegmentTemplate.create_promo(
            speaker_id=wrestler.id,
            speaker_name=wrestler.name,
            mic_skill=wrestler.mic,
            tone=SegmentTone.INTENSE
        )
        
        wrestler_dict = {wrestler.id: wrestler}
        result = segment_simulator.simulate_segment(segment_draft, wrestler_dict)
        
        return jsonify({
            'success': True,
            'wrestler': {
                'id': wrestler.id,
                'name': wrestler.name,
                'mic': wrestler.mic,
                'alignment': wrestler.alignment
            },
            'segment_result': result.to_dict()
        })
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@segment_bp.route('/api/segments/test/random-battle')
def api_test_segment_random_battle():
    universe = get_universe()
    
    try:
        from models.segment import SegmentTemplate
        from simulation.segment_sim import segment_simulator
        import random
        
        active_feuds = universe.feud_manager.get_active_feuds()
        
        if not active_feuds:
            return jsonify({'error': 'No active feuds available'}), 400
        
        feud = random.choice(active_feuds)
        
        if len(feud.participant_ids) < 2:
            return jsonify({'error': 'Selected feud has insufficient participants'}), 400
        
        wrestler_ids = feud.participant_ids[:2]
        wrestlers = [universe.get_wrestler_by_id(wid) for wid in wrestler_ids]
        wrestlers = [w for w in wrestlers if w]
        
        if len(wrestlers) < 2:
            return jsonify({'error': 'One or more wrestlers not found'}), 404
        
        participants = [(w.id, w.name, w.mic) for w in wrestlers]
        
        segment_draft = SegmentTemplate.create_promo_battle(
            participants=participants,
            feud_id=feud.id
        )
        
        wrestler_dict = {w.id: w for w in wrestlers}
        result = segment_simulator.simulate_segment(segment_draft, wrestler_dict)
        
        return jsonify({
            'success': True,
            'feud': {
                'id': feud.id,
                'intensity': feud.intensity,
                'participant_names': feud.participant_names
            },
            'segment_result': result.to_dict()
        })
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500