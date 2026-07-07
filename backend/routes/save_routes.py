"""
Save Routes - Save/Load System (Step 12)
"""

from flask import Blueprint, jsonify, request, current_app, send_file
import os
import tempfile

save_bp = Blueprint('save', __name__)


def get_database():
    return current_app.config['DATABASE']


def get_universe():
    return current_app.config['UNIVERSE']


def get_save_manager():
    return current_app.config.get('SAVE_MANAGER')


@save_bp.route('/api/saves/list')
def api_list_saves():
    save_manager = get_save_manager()
    
    try:
        saves = save_manager.list_saves()
        
        return jsonify({
            'success': True,
            'total': len(saves),
            'saves': [s.to_dict() for s in saves]
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@save_bp.route('/api/saves/save', methods=['POST'])
def api_save_universe():
    database = get_database()
    save_manager = get_save_manager()
    
    try:
        data = request.get_json()
        
        slot = data.get('slot', 1)
        save_name = data.get('save_name', f'Save {slot}')
        include_history = data.get('include_history', True)
        
        if slot < 0 or slot > 10:
            return jsonify({'success': False, 'error': 'Slot must be between 0-10'}), 400
        
        metadata = save_manager.save_universe(
            database=database,
            slot=slot,
            save_name=save_name,
            include_history=include_history
        )
        
        return jsonify({
            'success': True,
            'message': f'Universe saved to slot {slot}',
            'metadata': metadata.to_dict()
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@save_bp.route('/api/saves/load', methods=['POST'])
def api_load_universe():
    database = get_database()
    universe = get_universe()
    save_manager = get_save_manager()
    
    try:
        data = request.get_json()
        slot = data.get('slot', 1)
        
        if slot < 0 or slot > 10:
            return jsonify({'success': False, 'error': 'Slot must be between 0-10'}), 400
        
        snapshot = save_manager.load_universe(
            database=database,
            slot=slot
        )
        
        universe.sync_calendar_from_state()
        
        return jsonify({
            'success': True,
            'message': f'Universe loaded from slot {slot}',
            'metadata': snapshot.metadata.to_dict()
        })
    
    except FileNotFoundError as e:
        return jsonify({'success': False, 'error': f'Save slot {slot} not found'}), 404
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@save_bp.route('/api/saves/delete/<int:slot>', methods=['DELETE'])
def api_delete_save(slot: int):
    save_manager = get_save_manager()
    
    try:
        if slot < 0 or slot > 10:
            return jsonify({'success': False, 'error': 'Slot must be between 0-10'}), 400
        
        success = save_manager.delete_save(slot)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Save slot {slot} deleted'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Save slot {slot} not found'
            }), 404
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@save_bp.route('/api/saves/autosave', methods=['POST'])
def api_autosave():
    database = get_database()
    save_manager = get_save_manager()
    
    try:
        metadata = save_manager.save_universe(
            database=database,
            slot=0,
            save_name='Autosave',
            include_history=False
        )
        
        return jsonify({
            'success': True,
            'message': 'Autosave created',
            'metadata': metadata.to_dict()
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@save_bp.route('/api/saves/export/<int:slot>')
def api_export_save(slot: int):
    save_manager = get_save_manager()
    
    try:
        save_path = save_manager.get_save_path(slot) if slot > 0 else save_manager.get_autosave_path()
        
        if not os.path.exists(save_path):
            return jsonify({'error': f'Save slot {slot} not found'}), 404
        
        filename = f'awum_save_slot_{slot}.json'
        
        return send_file(
            save_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/json'
        )
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@save_bp.route('/api/saves/import', methods=['POST'])
def api_import_save():
    save_manager = get_save_manager()
    
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        slot = int(request.form.get('slot', 1))
        
        if slot < 0 or slot > 10:
            return jsonify({'success': False, 'error': 'Slot must be between 0-10'}), 400
        
        temp_path = os.path.join(tempfile.gettempdir(), 'awum_import.json')
        file.save(temp_path)
        
        save_manager.import_save(temp_path, slot)
        
        os.remove(temp_path)
        
        return jsonify({
            'success': True,
            'message': f'Save imported to slot {slot}'
        })
    
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500