"""
Feud Routes - Feud Management
"""

from flask import Blueprint, jsonify, request, current_app
from models.feud import FeudType

feud_bp = Blueprint('feud', __name__)


def get_database():
    return current_app.config['DATABASE']


def get_universe():
    return current_app.config['UNIVERSE']


@feud_bp.route('/api/feuds')
def api_get_feuds():
    universe = get_universe()
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    
    if active_only:
        feuds = universe.feud_manager.get_active_feuds()
    else:
        feuds = universe.feud_manager.feuds
    
    return jsonify({
        'total': len(feuds),
        'feuds': [f.to_dict() for f in feuds]
    })


@feud_bp.route('/api/feuds/<feud_id>')
def api_get_feud(feud_id):
    universe = get_universe()
    feud = universe.feud_manager.get_feud_by_id(feud_id)
    
    if not feud:
        return jsonify({'error': 'Feud not found'}), 404
    
    return jsonify(feud.to_dict())


@feud_bp.route('/api/feuds/active')
def api_get_active_feuds():
    universe = get_universe()
    feuds = universe.feud_manager.get_active_feuds()
    
    return jsonify({
        'total': len(feuds),
        'feuds': [f.to_dict() for f in feuds]
    })


@feud_bp.route('/api/feuds/hot')
def api_get_hot_feuds():
    universe = get_universe()
    min_intensity = request.args.get('min_intensity', 70, type=int)
    feuds = universe.feud_manager.get_hot_feuds(min_intensity)
    
    return jsonify({
        'total': len(feuds),
        'min_intensity': min_intensity,
        'feuds': [f.to_dict() for f in feuds]
    })


@feud_bp.route('/api/feuds/wrestler/<wrestler_id>')
def api_get_wrestler_feuds(wrestler_id):
    universe = get_universe()
    feuds = universe.feud_manager.get_feuds_involving(wrestler_id)
    
    wrestler = universe.get_wrestler_by_id(wrestler_id)
    wrestler_name = wrestler.name if wrestler else "Unknown"
    
    return jsonify({
        'wrestler_id': wrestler_id,
        'wrestler_name': wrestler_name,
        'total': len(feuds),
        'feuds': [f.to_dict() for f in feuds]
    })


@feud_bp.route('/api/feuds/create', methods=['POST'])
def api_create_feud():
    universe = get_universe()
    
    try:
        data = request.get_json()
        
        feud_type_str = data.get('feud_type', 'personal')
        participant_ids = data.get('participant_ids', [])
        title_id = data.get('title_id')
        initial_intensity = data.get('initial_intensity', 20)
        
        if len(participant_ids) < 2:
            return jsonify({'error': 'At least 2 participants required'}), 400
        
        participant_names = []
        for pid in participant_ids:
            wrestler = universe.get_wrestler_by_id(pid)
            if not wrestler:
                return jsonify({'error': f'Wrestler {pid} not found'}), 404
            participant_names.append(wrestler.name)
        
        title_name = None
        if title_id:
            title = universe.get_championship_by_id(title_id)
            if title:
                title_name = title.name
        
        feud = universe.feud_manager.create_feud(
            feud_type=FeudType(feud_type_str),
            participant_ids=participant_ids,
            participant_names=participant_names,
            year=universe.current_year,
            week=universe.current_week,
            title_id=title_id,
            title_name=title_name,
            initial_intensity=initial_intensity
        )
        
        universe.save_feud(feud)
        
        return jsonify({
            'success': True,
            'feud': feud.to_dict()
        })
    
    except ValueError as e:
        return jsonify({'error': f'Invalid parameter: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@feud_bp.route('/api/feuds/<feud_id>/add-segment', methods=['POST'])
def api_add_feud_segment(feud_id):
    universe = get_universe()
    
    try:
        feud = universe.feud_manager.get_feud_by_id(feud_id)
        
        if not feud:
            return jsonify({'error': 'Feud not found'}), 404
        
        data = request.get_json()
        
        segment_type = data.get('segment_type', 'match')
        description = data.get('description', '')
        intensity_change = data.get('intensity_change', 0)
        winner_id = data.get('winner_id')
        
        feud.add_segment(
            show_id=f"show_y{universe.current_year}_w{universe.current_week}",
            show_name=f"Week {universe.current_week} Show",
            year=universe.current_year,
            week=universe.current_week,
            segment_type=segment_type,
            description=description,
            intensity_change=intensity_change
        )
        
        if winner_id and segment_type == 'match':
            feud.record_match_result(winner_id)
        
        universe.save_feud(feud)
        
        return jsonify({
            'success': True,
            'feud': feud.to_dict()
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@feud_bp.route('/api/feuds/<feud_id>/resolve', methods=['POST'])
def api_resolve_feud(feud_id):
    universe = get_universe()
    feud = universe.feud_manager.get_feud_by_id(feud_id)
    
    if not feud:
        return jsonify({'error': 'Feud not found'}), 404
    
    feud.resolve()
    universe.save_feud(feud)
    
    return jsonify({
        'success': True,
        'feud': feud.to_dict()
    })


@feud_bp.route('/api/feuds/<feud_id>/reignite', methods=['POST'])
def api_reignite_feud(feud_id):
    universe = get_universe()
    feud = universe.feud_manager.get_feud_by_id(feud_id)
    
    if not feud:
        return jsonify({'error': 'Feud not found'}), 404
    
    intensity = request.get_json().get('intensity', 50) if request.is_json else 50
    
    feud.reignite(intensity)
    universe.save_feud(feud)
    
    return jsonify({
        'success': True,
        'feud': feud.to_dict()
    })


@feud_bp.route('/api/feuds/stats')
def api_feud_stats():
    universe = get_universe()
    return jsonify(universe.feud_manager.to_dict())