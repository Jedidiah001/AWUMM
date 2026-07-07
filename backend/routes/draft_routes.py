"""
Draft Routes - Brand Draft (Step 19)
"""

from flask import Blueprint, jsonify, request, current_app
import traceback

draft_bp = Blueprint('draft', __name__)


def get_database():
    return current_app.config['DATABASE']


def get_universe():
    return current_app.config['UNIVERSE']


def get_draft_manager():
    return current_app.config.get('DRAFT_MANAGER')


def get_data_dir():
    return current_app.config.get('DATA_DIR')


@draft_bp.route('/api/draft/initiate', methods=['POST'])
def api_initiate_draft():
    universe = get_universe()
    draft_manager = get_draft_manager()
    data_dir = get_data_dir()
    
    try:
        from models.draft import DraftFormat
        
        data = request.get_json() if request.is_json else {}
        
        format_str = data.get('format', 'snake')
        format_type = DraftFormat(format_str)
        
        if not draft_manager.gm_data:
            draft_manager.load_gm_data(data_dir)
        
        eligible, message, weeks_until = draft_manager.check_draft_eligibility(
            universe.current_year,
            universe.current_week
        )
        
        if not eligible:
            return jsonify({
                'success': False,
                'error': message,
                'weeks_until_eligible': weeks_until
            }), 400
        
        draft = draft_manager.initiate_draft(
            universe_state=universe,
            year=universe.current_year,
            week=universe.current_week,
            format_type=format_type
        )
        
        if data.get('randomize_order', False):
            draft.randomize_draft_order()
        
        return jsonify({
            'success': True,
            'message': 'Draft initiated',
            'draft': {
                'draft_id': draft.draft_id,
                'format': draft.format_type.value,
                'total_eligible': len(draft.eligible_wrestlers),
                'total_exempt': len(draft.exemptions),
                'draft_order': draft.base_draft_order,
                'current_picking': draft.get_current_picking_brand()
            }
        })
    
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
        
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"\n❌ Draft initiation error:")
        print(error_trace)
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': error_trace
        }), 500


@draft_bp.route('/api/draft/current')
def api_get_current_draft():
    draft_manager = get_draft_manager()
    
    try:
        if not draft_manager.current_draft:
            return jsonify({
                'success': False,
                'error': 'No draft currently active'
            }), 404
        
        draft = draft_manager.current_draft
        
        return jsonify({
            'success': True,
            'draft': draft.to_dict()
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@draft_bp.route('/api/draft/exemptions')
def api_get_draft_exemptions():
    draft_manager = get_draft_manager()
    
    try:
        if not draft_manager.current_draft:
            return jsonify({
                'success': False,
                'error': 'No draft currently active'
            }), 404
        
        exemptions = draft_manager.current_draft.exemptions
        
        return jsonify({
            'success': True,
            'total': len(exemptions),
            'exemptions': [
                {
                    'wrestler_id': e.wrestler_id,
                    'wrestler_name': e.wrestler_name,
                    'reason': e.reason.value,
                    'description': e.description,
                    'expires_week': e.expires_week
                }
                for e in exemptions
            ]
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@draft_bp.route('/api/draft/eligible')
def api_get_eligible_wrestlers():
    draft_manager = get_draft_manager()
    
    try:
        if not draft_manager.current_draft:
            return jsonify({
                'success': False,
                'error': 'No draft currently active'
            }), 404
        
        draft = draft_manager.current_draft
        
        available = [w for w in draft.eligible_wrestlers if w['id'] in draft.draft_pool]
        
        available.sort(key=lambda x: x['overall'], reverse=True)
        
        return jsonify({
            'success': True,
            'total': len(available),
            'wrestlers': available
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@draft_bp.route('/api/draft/simulate', methods=['POST'])
def api_simulate_draft():
    universe = get_universe()
    draft_manager = get_draft_manager()
    
    try:
        if not draft_manager.current_draft:
            return jsonify({
                'success': False,
                'error': 'No draft currently active'
            }), 404
        
        draft = draft_manager.current_draft
        
        summary = draft_manager.simulate_full_draft(universe)
        
        report = draft_manager.get_draft_report(draft)
        
        return jsonify({
            'success': True,
            'message': 'Draft simulation complete',
            'summary': summary,
            'report': report
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@draft_bp.route('/api/draft/make-pick', methods=['POST'])
def api_make_draft_pick():
    draft_manager = get_draft_manager()
    
    try:
        if not draft_manager.current_draft:
            return jsonify({
                'success': False,
                'error': 'No draft currently active'
            }), 404
        
        data = request.get_json()
        wrestler_id = data.get('wrestler_id')
        
        if not wrestler_id:
            return jsonify({
                'success': False,
                'error': 'wrestler_id required'
            }), 400
        
        draft = draft_manager.current_draft
        current_brand = draft.get_current_picking_brand()
        
        if not current_brand:
            return jsonify({
                'success': False,
                'error': 'Draft is complete or no brand currently picking'
            }), 400
        
        pick = draft.make_pick(current_brand, wrestler_id, 0.0)
        
        return jsonify({
            'success': True,
            'pick': {
                'overall_pick': pick.overall_pick,
                'brand': pick.brand,
                'wrestler_name': pick.wrestler_name,
                'wrestler_role': pick.wrestler_role
            },
            'next_picking': draft.get_current_picking_brand(),
            'is_complete': draft.is_complete
        })
    
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@draft_bp.route('/api/draft/history')
def api_get_draft_history():
    draft_manager = get_draft_manager()
    
    try:
        history = []
        
        for draft in draft_manager.draft_history:
            history.append({
                'draft_id': draft.draft_id,
                'year': draft.year,
                'week': draft.week,
                'format': draft.format_type.value,
                'total_picks': draft.overall_pick_count,
                'total_trades': len(draft.trades)
            })
        
        return jsonify({
            'success': True,
            'total': len(history),
            'drafts': history
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@draft_bp.route('/api/draft/gms')
def api_get_draft_gms():
    draft_manager = get_draft_manager()
    data_dir = get_data_dir()
    
    try:
        if not draft_manager.gm_data:
            draft_manager.load_gm_data(data_dir)
        
        gms = draft_manager.gm_data.get('general_managers', [])
        personalities = draft_manager.gm_data.get('personality_descriptions', {})
        
        return jsonify({
            'success': True,
            'gms': gms,
            'personality_types': personalities
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@draft_bp.route('/api/draft/check-eligibility')
def api_check_draft_eligibility():
    universe = get_universe()
    draft_manager = get_draft_manager()
    data_dir = get_data_dir()
    
    try:
        if not draft_manager.gm_data:
            draft_manager.load_gm_data(data_dir)
        
        eligible, message, weeks_until = draft_manager.check_draft_eligibility(
            universe.current_year,
            universe.current_week
        )
        
        if not eligible:
            last_draft = draft_manager.get_last_draft()
            
            return jsonify({
                'success': True,
                'eligible': False,
                'message': message,
                'weeks_until_eligible': weeks_until,
                'last_draft': {
                    'year': last_draft.year,
                    'week': last_draft.week
                } if last_draft else None
            })
        
        return jsonify({
            'success': True,
            'eligible': True,
            'message': 'Draft can be initiated'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@draft_bp.route('/api/draft/debug/clear-history', methods=['POST'])
def api_clear_draft_history():
    draft_manager = get_draft_manager()
    
    try:
        draft_manager.draft_history = []
        draft_manager.current_draft = None
        
        return jsonify({
            'success': True,
            'message': 'Draft history cleared. You can now initiate a new draft.'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500