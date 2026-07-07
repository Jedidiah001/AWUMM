"""
Custom Championship Routes - Custom Championship Creation (Step 22)
"""

from flask import Blueprint, jsonify, request, current_app
import traceback

custom_championship_bp = Blueprint('custom_championship', __name__)


def get_database():
    return current_app.config['DATABASE']


def get_universe():
    return current_app.config['UNIVERSE']


@custom_championship_bp.route('/api/championships/custom/presets')
def api_get_championship_presets():
    try:
        from models.championship_factory import ChampionshipPresets
        
        presets = ChampionshipPresets.get_all_presets()
        
        return jsonify({
            'success': True,
            'total': len(presets),
            'presets': presets
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@custom_championship_bp.route('/api/championships/custom/validate', methods=['POST'])
def api_validate_custom_championship():
    universe = get_universe()
    
    try:
        from models.championship_factory import ChampionshipValidator, ChampionshipFactory
        
        data = request.get_json()
        
        existing_names = [c.name for c in universe.championships]
        
        is_valid, errors = ChampionshipValidator.validate_all(data, existing_names)
        
        suggested_prestige = ChampionshipFactory.get_suggested_prestige(
            data.get('title_type', 'Midcard'),
            data.get('assigned_brand', 'ROC Alpha')
        )
        
        return jsonify({
            'success': True,
            'is_valid': is_valid,
            'errors': errors,
            'suggestions': {
                'prestige': suggested_prestige
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@custom_championship_bp.route('/api/championships/custom/create', methods=['POST'])
def api_create_custom_championship():
    database = get_database()
    universe = get_universe()
    
    try:
        from models.championship_factory import ChampionshipValidator, ChampionshipFactory
        from persistence.championship_custom_db import save_championship_extended, log_championship_action
        
        data = request.get_json()
        
        print(f"\n{'='*60}")
        print(f"🏆 CREATE CUSTOM CHAMPIONSHIP REQUEST")
        print(f"{'='*60}")
        print(f"Name: {data.get('name')}")
        print(f"Brand: {data.get('assigned_brand')}")
        print(f"Type: {data.get('title_type')}")
        print(f"{'='*60}\n")
        
        existing_names = [c.name for c in universe.championships]
        
        is_valid, errors = ChampionshipValidator.validate_all(data, existing_names)
        
        if not is_valid:
            return jsonify({
                'success': False,
                'error': 'Validation failed',
                'errors': errors
            }), 400
        
        championship_id = ChampionshipFactory.generate_championship_id(database)
        print(f"✅ Generated ID: {championship_id}")
        
        championship = ChampionshipFactory.create_championship(
            data=data,
            championship_id=championship_id,
            current_year=universe.current_year,
            current_week=universe.current_week
        )
        
        print(f"✅ Created championship: {championship.name}")
        print(f"   Prestige: {championship.prestige}")
        
        database.save_championship(championship)
        
        extended_data = {
            'division': data.get('division', 'open'),
            'weight_class': data.get('weight_class', 'open'),
            'is_tag_team': data.get('is_tag_team', False),
            'tag_team_size': data.get('tag_team_size', 2),
            'description': data.get('description', ''),
            'is_custom': True,
            'created_year': universe.current_year,
            'created_week': universe.current_week,
            'retired': False,
            'appearance': data.get('appearance'),
            'defense_requirements': data.get('defense_requirements')
        }
        
        save_championship_extended(database, championship_id, extended_data)
        
        log_championship_action(
            database,
            championship_id,
            'created',
            universe.current_year,
            universe.current_week,
            f"Custom championship created: {championship.name}"
        )
        
        database.conn.commit()
        
        print(f"✅ Saved to database")
        print()
        
        full_data = championship.to_dict()
        full_data.update(extended_data)
        
        return jsonify({
            'success': True,
            'message': f'Championship "{championship.name}" created successfully',
            'championship': full_data
        })
    
    except Exception as e:
        error_trace = traceback.format_exc()
        
        print(f"\n❌ Championship Creation Error:")
        print(error_trace)
        print()
        
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': error_trace
        }), 500


@custom_championship_bp.route('/api/championships/custom/create-from-preset', methods=['POST'])
def api_create_championship_from_preset():
    database = get_database()
    universe = get_universe()
    
    try:
        from models.championship_factory import ChampionshipValidator, ChampionshipFactory, ChampionshipPresets
        from persistence.championship_custom_db import save_championship_extended, log_championship_action
        
        data = request.get_json()
        
        preset_id = data.get('preset_id')
        if not preset_id:
            return jsonify({'success': False, 'error': 'preset_id required'}), 400
        
        preset = ChampionshipPresets.get_preset_by_id(preset_id)
        if not preset:
            return jsonify({'success': False, 'error': f'Preset "{preset_id}" not found'}), 404
        
        champ_data = {
            'name': data.get('name_override', preset['name']),
            'assigned_brand': data.get('assigned_brand', 'ROC Alpha'),
            'title_type': preset['title_type'],
            'division': preset.get('division', 'open'),
            'weight_class': preset.get('weight_class', 'open'),
            'initial_prestige': preset.get('suggested_prestige', 50),
            'is_tag_team': preset.get('is_tag_team', False),
            'tag_team_size': preset.get('tag_team_size', 2),
            'description': preset.get('description', ''),
            'defense_requirements': preset.get('defense_requirements')
        }
        
        existing_names = [c.name for c in universe.championships]
        is_valid, errors = ChampionshipValidator.validate_all(champ_data, existing_names)
        
        if not is_valid:
            return jsonify({
                'success': False,
                'error': 'Validation failed',
                'errors': errors
            }), 400
        
        championship_id = ChampionshipFactory.generate_championship_id(database)
        
        championship = ChampionshipFactory.create_championship(
            data=champ_data,
            championship_id=championship_id,
            current_year=universe.current_year,
            current_week=universe.current_week
        )
        
        database.save_championship(championship)
        
        extended_data = {
            'division': champ_data['division'],
            'weight_class': champ_data['weight_class'],
            'is_tag_team': champ_data['is_tag_team'],
            'tag_team_size': champ_data['tag_team_size'],
            'description': champ_data['description'],
            'is_custom': True,
            'created_year': universe.current_year,
            'created_week': universe.current_week,
            'defense_requirements': champ_data.get('defense_requirements')
        }
        
        save_championship_extended(database, championship_id, extended_data)
        
        log_championship_action(
            database,
            championship_id,
            'created_from_preset',
            universe.current_year,
            universe.current_week,
            f"Created from preset: {preset_id}"
        )
        
        database.conn.commit()
        
        full_data = championship.to_dict()
        full_data.update(extended_data)
        
        return jsonify({
            'success': True,
            'message': f'Championship "{championship.name}" created from preset',
            'championship': full_data
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@custom_championship_bp.route('/api/championships/<title_id>/update', methods=['PUT'])
def api_update_championship(title_id):
    database = get_database()
    universe = get_universe()
    
    try:
        from models.championship_factory import ChampionshipValidator
        from persistence.championship_custom_db import get_championship_extended, save_championship_extended, log_championship_action
        
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        data = request.get_json()
        
        current_extended = get_championship_extended(database, title_id) or {}
        
        if 'description' in data:
            current_extended['description'] = data['description']
        
        if 'appearance' in data:
            current_extended['appearance'] = data['appearance']
        
        if 'defense_requirements' in data:
            valid, errors = ChampionshipValidator.validate_defense_requirements(data['defense_requirements'])
            if not valid:
                return jsonify({
                    'success': False,
                    'error': 'Invalid defense requirements',
                    'errors': errors
                }), 400
            current_extended['defense_requirements'] = data['defense_requirements']
        
        save_championship_extended(database, title_id, current_extended)
        
        log_championship_action(
            database,
            title_id,
            'updated',
            universe.current_year,
            universe.current_week,
            'Extended properties updated'
        )
        
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'message': 'Championship updated successfully'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@custom_championship_bp.route('/api/championships/<title_id>/retire', methods=['POST'])
def api_retire_championship(title_id):
    database = get_database()
    universe = get_universe()
    
    try:
        from persistence.championship_custom_db import retire_championship
        
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        data = request.get_json() if request.is_json else {}
        reason = data.get('reason', 'Championship retired')
        
        retire_championship(
            database,
            title_id,
            universe.current_year,
            universe.current_week,
            reason
        )
        
        return jsonify({
            'success': True,
            'message': f'{championship.name} has been retired'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@custom_championship_bp.route('/api/championships/<title_id>/reactivate', methods=['POST'])
def api_reactivate_championship(title_id):
    database = get_database()
    universe = get_universe()
    
    try:
        from persistence.championship_custom_db import get_championship_extended, reactivate_championship
        
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        extended = get_championship_extended(database, title_id)
        if not extended or not extended.get('retired'):
            return jsonify({
                'success': False,
                'error': 'Championship is not retired'
            }), 400
        
        reactivate_championship(
            database,
            title_id,
            universe.current_year,
            universe.current_week
        )
        
        return jsonify({
            'success': True,
            'message': f'{championship.name} has been reactivated'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@custom_championship_bp.route('/api/championships/<title_id>/delete', methods=['DELETE'])
def api_delete_championship(title_id):
    database = get_database()
    universe = get_universe()
    
    try:
        from persistence.championship_custom_db import delete_championship
        
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        title_name = championship.name
        
        delete_championship(database, title_id)
        
        return jsonify({
            'success': True,
            'message': f'{title_name} has been permanently deleted'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@custom_championship_bp.route('/api/championships/custom')
def api_get_custom_championships():
    database = get_database()
    
    try:
        from persistence.championship_custom_db import get_all_custom_championships
        
        include_retired = request.args.get('include_retired', 'false').lower() == 'true'
        
        championships = get_all_custom_championships(database, include_retired)
        
        return jsonify({
            'success': True,
            'total': len(championships),
            'championships': championships
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@custom_championship_bp.route('/api/championships/by-division/<division>')
def api_get_championships_by_division(division):
    database = get_database()
    
    try:
        from persistence.championship_custom_db import get_championships_by_division
        
        valid_divisions = ['mens', 'womens', 'tag_team', 'open', 'intergender']
        if division not in valid_divisions:
            return jsonify({
                'success': False,
                'error': f'Invalid division. Must be one of: {", ".join(valid_divisions)}'
            }), 400
        
        championships = get_championships_by_division(database, division)
        
        return jsonify({
            'success': True,
            'division': division,
            'total': len(championships),
            'championships': championships
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@custom_championship_bp.route('/api/championships/<title_id>/statistics')
def api_get_championship_full_stats(title_id):
    database = get_database()
    
    try:
        from persistence.championship_custom_db import get_championship_statistics
        
        stats = get_championship_statistics(database, title_id)
        
        if not stats:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        return jsonify({
            'success': True,
            'statistics': stats
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@custom_championship_bp.route('/api/championships/<title_id>/action-log')
def api_get_championship_action_log(title_id):
    database = get_database()
    
    try:
        from persistence.championship_custom_db import get_championship_action_log
        
        limit = request.args.get('limit', 20, type=int)
        
        log = get_championship_action_log(database, title_id, limit)
        
        return jsonify({
            'success': True,
            'total': len(log),
            'log': log
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@custom_championship_bp.route('/api/championships/options')
def api_get_championship_options():
    try:
        from models.championship_factory import (
            ChampionshipValidator, DivisionRestriction, WeightClass, 
            BeltStyle, BeltColor
        )
        
        return jsonify({
            'success': True,
            'options': {
                'brands': ChampionshipValidator.VALID_BRANDS,
                'title_types': ChampionshipValidator.VALID_TITLE_TYPES,
                'divisions': [d.value for d in DivisionRestriction],
                'weight_classes': [w.value for w in WeightClass],
                'belt_styles': [s.value for s in BeltStyle],
                'belt_colors': [c.value for c in BeltColor],
                'prestige_range': {
                    'min': ChampionshipValidator.MIN_PRESTIGE,
                    'max': ChampionshipValidator.MAX_PRESTIGE
                },
                'name_length': {
                    'min': ChampionshipValidator.MIN_NAME_LENGTH,
                    'max': ChampionshipValidator.MAX_NAME_LENGTH
                }
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@custom_championship_bp.route('/api/championships/<title_id>/check-eligibility/<wrestler_id>')
def api_check_wrestler_eligibility(title_id, wrestler_id):
    database = get_database()
    universe = get_universe()
    
    try:
        from persistence.championship_custom_db import get_championship_extended
        
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'success': False, 'error': 'Wrestler not found'}), 404
        
        extended = get_championship_extended(database, title_id)
        
        eligible = True
        reasons = []
        
        if extended:
            division = extended.get('division', 'open')
            weight_class = extended.get('weight_class', 'open')
            
            if division == 'mens' and wrestler.gender != 'Male':
                eligible = False
                reasons.append("This championship is for male competitors only")
            elif division == 'womens' and wrestler.gender != 'Female':
                eligible = False
                reasons.append("This championship is for female competitors only")
            
            if weight_class == 'cruiserweight' and wrestler.speed < 60:
                eligible = False
                reasons.append("Cruiserweight division requires high speed attribute (60+)")
            elif weight_class == 'super_heavyweight' and wrestler.brawling < 70:
                eligible = False
                reasons.append("Super heavyweight division requires high brawling (70+)")
        
        return jsonify({
            'success': True,
            'eligible': eligible,
            'reasons': reasons if not eligible else ['Wrestler is eligible to compete'],
            'wrestler': {
                'id': wrestler.id,
                'name': wrestler.name,
                'gender': wrestler.gender
            },
            'championship': {
                'id': championship.id,
                'name': championship.name
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
