"""
Lineage Routes - Championship Lineage & Title History
"""

from flask import Blueprint, jsonify, request, current_app
import traceback

lineage_bp = Blueprint('lineage', __name__)


def get_database():
    return current_app.config['DATABASE']


def get_universe():
    return current_app.config['UNIVERSE']


@lineage_bp.route('/api/championships/<title_id>/lineage')
def api_get_title_lineage(title_id):
    universe = get_universe()
    
    try:
        limit = request.args.get('limit', type=int)
        
        lineage = universe.lineage_tracker.get_title_lineage(title_id, limit)
        
        title = universe.get_championship_by_id(title_id)
        title_name = title.name if title else "Unknown Championship"
        
        return jsonify({
            'success': True,
            'title_id': title_id,
            'title_name': title_name,
            'total_reigns': len(lineage),
            'lineage': lineage
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@lineage_bp.route('/api/championships/<title_id>/lineage-statistics')
def api_get_championship_lineage_statistics(title_id):
    universe = get_universe()
    
    try:
        stats = universe.lineage_tracker.get_championship_statistics(title_id)
        
        title = universe.get_championship_by_id(title_id)
        
        return jsonify({
            'success': True,
            'title_id': title_id,
            'title_name': title.name if title else "Unknown",
            'statistics': stats
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@lineage_bp.route('/api/championships/<title_id>/defenses')
def api_get_title_defenses(title_id):
    database = get_database()
    universe = get_universe()
    
    try:
        from persistence.lineage_db import get_title_defenses
        
        limit = request.args.get('limit', 50, type=int)
        defenses = get_title_defenses(database, title_id=title_id, limit=limit)
        
        title = universe.get_championship_by_id(title_id)
        
        return jsonify({
            'success': True,
            'title_id': title_id,
            'title_name': title.name if title else "Unknown",
            'defenses': defenses
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@lineage_bp.route('/api/wrestlers/<wrestler_id>/title-history')
def api_get_wrestler_title_history(wrestler_id):
    database = get_database()
    universe = get_universe()
    
    try:
        from persistence.lineage_db import get_wrestler_title_history
        
        history = get_wrestler_title_history(database, wrestler_id)
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        
        return jsonify({
            'success': True,
            'wrestler_id': wrestler_id,
            'wrestler_name': wrestler.name if wrestler else "Unknown",
            'history': history
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@lineage_bp.route('/api/championships/<title_id>/reign/<wrestler_id>/<int:year>/<int:week>')
def api_get_reign_statistics(title_id, wrestler_id, year, week):
    universe = get_universe()
    
    try:
        stats = universe.lineage_tracker.get_reign_statistics(
            title_id, wrestler_id, year, week
        )
        
        return jsonify({
            'success': True,
            'title_id': title_id,
            'wrestler_id': wrestler_id,
            'year': year,
            'week': week,
            'statistics': stats.to_dict()
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500