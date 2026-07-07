"""
Storyline Routes - Scripted Storylines (Step 16)
"""

from flask import Blueprint, jsonify, request, current_app
import os
import traceback

storyline_bp = Blueprint('storyline', __name__)


def get_database():
    return current_app.config['DATABASE']


def get_universe():
    return current_app.config['UNIVERSE']


def get_storyline_engine():
    return current_app.config.get('STORYLINE_ENGINE')


def get_data_dir():
    return current_app.config.get('DATA_DIR')


@storyline_bp.route('/api/storylines')
def api_get_storylines():
    storyline_engine = get_storyline_engine()
    data_dir = get_data_dir()
    
    try:
        if not storyline_engine.loaded:
            storylines_path = os.path.join(data_dir, 'storylines_year_one.json')
            storyline_engine.load_storylines(storylines_path)
        
        report = storyline_engine.get_storyline_status_report()
        
        return jsonify({
            'success': True,
            **report
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@storyline_bp.route('/api/storylines/<storyline_id>')
def api_get_storyline(storyline_id):
    universe = get_universe()
    storyline_engine = get_storyline_engine()
    
    try:
        storyline = storyline_engine.manager.get_storyline_by_id(storyline_id)
        
        if not storyline:
            return jsonify({'success': False, 'error': 'Storyline not found'}), 404
        
        cast_with_names = {}
        for role, wrestler_id in storyline.cast_assignments.items():
            wrestler = universe.get_wrestler_by_id(wrestler_id)
            cast_with_names[role] = {
                'id': wrestler_id,
                'name': wrestler.name if wrestler else 'Unknown'
            }
        
        return jsonify({
            'success': True,
            'storyline': storyline.to_dict(),
            'cast_with_names': cast_with_names
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@storyline_bp.route('/api/storylines/active')
def api_get_active_storylines():
    universe = get_universe()
    storyline_engine = get_storyline_engine()
    
    try:
        active = storyline_engine.get_active_storylines()
        
        storylines_data = []
        for storyline in active:
            cast_with_names = {}
            for role, wrestler_id in storyline.cast_assignments.items():
                wrestler = universe.get_wrestler_by_id(wrestler_id)
                cast_with_names[role] = {
                    'id': wrestler_id,
                    'name': wrestler.name if wrestler else 'Unknown'
                }
            
            data = storyline.to_dict()
            data['cast_with_names'] = cast_with_names
            storylines_data.append(data)
        
        return jsonify({
            'success': True,
            'total': len(storylines_data),
            'storylines': storylines_data
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@storyline_bp.route('/api/storylines/check-triggers', methods=['POST'])
def api_check_storyline_triggers():
    universe = get_universe()
    storyline_engine = get_storyline_engine()
    
    try:
        year = universe.current_year
        week = universe.current_week
        
        triggered = storyline_engine.check_and_trigger_storylines(universe, year, week)
        
        triggered_data = []
        for storyline in triggered:
            cast_with_names = {}
            for role, wrestler_id in storyline.cast_assignments.items():
                wrestler = universe.get_wrestler_by_id(wrestler_id)
                cast_with_names[role] = {
                    'id': wrestler_id,
                    'name': wrestler.name if wrestler else 'Unknown'
                }
            
            data = {
                'id': storyline.storyline_id,
                'name': storyline.name,
                'type': storyline.storyline_type.value,
                'description': storyline.description,
                'cast': cast_with_names
            }
            triggered_data.append(data)
        
        return jsonify({
            'success': True,
            'year': year,
            'week': week,
            'triggered_count': len(triggered_data),
            'triggered': triggered_data
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@storyline_bp.route('/api/storylines/process-week', methods=['POST'])
def api_process_storyline_week():
    universe = get_universe()
    storyline_engine = get_storyline_engine()
    
    try:
        year = universe.current_year
        week = universe.current_week
        
        results = storyline_engine.process_current_week(universe, year, week)
        
        return jsonify({
            'success': True,
            'year': year,
            'week': week,
            'beats_processed': len(results),
            'results': results
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@storyline_bp.route('/api/storylines/preview-segments', methods=['POST'])
def api_preview_storyline_segments():
    universe = get_universe()
    storyline_engine = get_storyline_engine()
    
    try:
        data = request.get_json() if request.is_json else {}
        
        show_type = data.get('show_type', 'weekly_tv')
        brand = data.get('brand', 'ROC Alpha')
        
        segments = storyline_engine.get_storyline_segments_for_show(
            show_type,
            brand,
            universe
        )
        
        segments_data = [seg.to_dict() for seg in segments]
        
        return jsonify({
            'success': True,
            'show_type': show_type,
            'brand': brand,
            'total': len(segments_data),
            'segments': segments_data
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@storyline_bp.route('/api/storylines/<storyline_id>/trigger', methods=['POST'])
def api_trigger_storyline_manually(storyline_id):
    universe = get_universe()
    database = get_database()
    storyline_engine = get_storyline_engine()
    
    try:
        from models.storyline import StorylineStatus
        
        storyline = storyline_engine.manager.get_storyline_by_id(storyline_id)
        
        if not storyline:
            return jsonify({'success': False, 'error': 'Storyline not found'}), 404
        
        if storyline.status.value != 'pending':
            return jsonify({'success': False, 'error': f'Storyline is already {storyline.status.value}'}), 400
        
        if storyline.cast_storyline(universe):
            storyline.status = StorylineStatus.ACTIVE
            storyline.triggered_year = universe.current_year
            storyline.triggered_week = universe.current_week
            
            storyline_state = storyline_engine.save_state()
            database.save_storyline_state(storyline_state)
            database.conn.commit()
            
            cast_with_names = {}
            for role, wrestler_id in storyline.cast_assignments.items():
                wrestler = universe.get_wrestler_by_id(wrestler_id)
                cast_with_names[role] = {
                    'id': wrestler_id,
                    'name': wrestler.name if wrestler else 'Unknown'
                }
            
            return jsonify({
                'success': True,
                'message': f'Storyline "{storyline.name}" manually triggered',
                'storyline': storyline.to_dict(),
                'cast_with_names': cast_with_names
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to cast storyline - required wrestlers not available'
            }), 400
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@storyline_bp.route('/api/storylines/reload', methods=['POST'])
def api_reload_storylines():
    database = get_database()
    storyline_engine = get_storyline_engine()
    data_dir = get_data_dir()
    
    try:
        storyline_engine.manager.storylines = []
        storyline_engine.manager.completed_storylines = []
        
        storylines_path = os.path.join(data_dir, 'storylines_year_one.json')
        storyline_engine.load_storylines(storylines_path)
        
        storyline_state = storyline_engine.save_state()
        database.save_storyline_state(storyline_state)
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'message': 'Storylines reloaded from file',
            'total_loaded': len(storyline_engine.manager.storylines)
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500