"""
Awards Routes - End-of-Year Awards (Step 17)
"""

from flask import Blueprint, jsonify, request, current_app
import traceback

awards_bp = Blueprint('awards', __name__)


def get_database():
    return current_app.config['DATABASE']


def get_universe():
    return current_app.config['UNIVERSE']


@awards_bp.route('/api/awards/calculate/<int:year>', methods=['POST'])
def api_calculate_year_awards(year: int):
    database = get_database()
    universe = get_universe()
    
    try:
        from simulation.awards_engine import awards_engine
        from persistence.awards_db import save_awards_ceremony
        
        print(f"\n🏆 Calculating Year {year} Awards...")
        
        ceremony = awards_engine.calculate_year_end_awards(year, database, universe)
        
        save_awards_ceremony(database, ceremony)
        
        return jsonify({
            'success': True,
            'message': f'Calculated {len(ceremony.awards)} awards for Year {year}',
            'ceremony': ceremony.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@awards_bp.route('/api/awards/<int:year>')
def api_get_year_awards(year: int):
    database = get_database()
    
    try:
        from persistence.awards_db import get_awards_ceremony
        
        ceremony = get_awards_ceremony(database, year)
        
        if not ceremony:
            return jsonify({
                'success': False,
                'error': f'No awards found for Year {year}'
            }), 404
        
        return jsonify({
            'success': True,
            'ceremony': ceremony
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@awards_bp.route('/api/awards/all')
def api_get_all_awards():
    database = get_database()
    
    try:
        from persistence.awards_db import get_all_awards_ceremonies
        
        ceremonies = get_all_awards_ceremonies(database)
        
        return jsonify({
            'success': True,
            'total': len(ceremonies),
            'ceremonies': ceremonies
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@awards_bp.route('/api/awards/wrestler/<wrestler_id>')
def api_get_wrestler_awards_list(wrestler_id: str):
    database = get_database()
    universe = get_universe()
    
    try:
        from persistence.awards_db import get_wrestler_awards
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        
        if not wrestler:
            return jsonify({'success': False, 'error': 'Wrestler not found'}), 404
        
        awards = get_wrestler_awards(database, wrestler_id)
        
        return jsonify({
            'success': True,
            'wrestler_id': wrestler_id,
            'wrestler_name': wrestler.name,
            'total_awards': len(awards),
            'awards': awards
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@awards_bp.route('/api/awards/latest')
def api_get_latest_awards():
    database = get_database()
    
    try:
        from persistence.awards_db import get_all_awards_ceremonies
        
        ceremonies = get_all_awards_ceremonies(database)
        
        if not ceremonies:
            return jsonify({
                'success': False,
                'error': 'No awards ceremonies found'
            }), 404
        
        latest = ceremonies[0]
        
        return jsonify({
            'success': True,
            'ceremony': latest
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500