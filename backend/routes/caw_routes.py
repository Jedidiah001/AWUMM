"""
CAW Routes - Create-A-Wrestler (Step 18)
"""

from flask import Blueprint, jsonify, request, current_app
import traceback
import random

caw_bp = Blueprint('caw', __name__)


def get_database():
    return current_app.config['DATABASE']


def get_universe():
    return current_app.config['UNIVERSE']


def _normalize_caw_payload(data):
    """Accept older frontend payload shapes while keeping backend validation strict."""
    normalized = dict(data or {})

    numeric_fields = [
        'age', 'brawling', 'technical', 'speed', 'mic', 'psychology',
        'stamina', 'salary_per_show', 'contract_weeks', 'years_experience'
    ]
    for field in numeric_fields:
        if field in normalized and normalized[field] not in (None, ''):
            try:
                normalized[field] = int(normalized[field])
            except (TypeError, ValueError):
                pass

    return normalized


@caw_bp.route('/api/caw/presets')
def api_get_caw_presets():
    try:
        from models.caw import CAWPresets
        
        presets = CAWPresets.get_all_presets()
        
        return jsonify({
            'success': True,
            'total': len(presets),
            'presets': presets
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@caw_bp.route('/api/caw/validate', methods=['POST'])
def api_validate_caw():
    try:
        from models.caw import CAWValidator, CAWFactory
        
        data = _normalize_caw_payload(request.get_json())
        
        is_valid, errors = CAWValidator.validate_all(data)
        
        overall = CAWFactory.calculate_overall_preview(data)
        suggested_salary = CAWFactory.get_suggested_salary(
            data.get('role', 'Midcard'),
            overall
        )
        
        return jsonify({
            'success': True,
            'is_valid': is_valid,
            'errors': errors,
            'preview': {
                'overall_rating': overall,
                'suggested_salary': suggested_salary
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@caw_bp.route('/api/caw/create', methods=['POST'])
def api_create_wrestler():
    database = get_database()
    universe = get_universe()
    
    try:
        from models.caw import CAWValidator, CAWFactory
        
        data = _normalize_caw_payload(request.get_json())
        
        print(f"\n{'='*60}")
        print(f"🎨 CREATE-A-WRESTLER REQUEST")
        print(f"{'='*60}")
        print(f"Name: {data.get('name')}")
        print(f"Brand: {data.get('primary_brand')}")
        print(f"Role: {data.get('role')}")
        print(f"{'='*60}\n")
        
        is_valid, errors = CAWValidator.validate_all(data)
        
        if not is_valid:
            return jsonify({
                'success': False,
                'error': 'Validation failed',
                'errors': errors
            }), 400
        
        existing_wrestlers = database.get_all_wrestlers(active_only=False)
        existing_names = [w['name'].lower() for w in existing_wrestlers]
        
        if data['name'].strip().lower() in existing_names:
            return jsonify({
                'success': False,
                'error': 'A wrestler with this name already exists'
            }), 400
        
        wrestler_id = CAWFactory.generate_wrestler_id(database)
        
        print(f"✅ Generated ID: {wrestler_id}")
        
        wrestler = CAWFactory.create_wrestler(
            data=data,
            wrestler_id=wrestler_id,
            current_year=universe.current_year,
            current_week=universe.current_week
        )
        
        print(f"✅ Created wrestler object: {wrestler.name}")
        print(f"   Overall Rating: {wrestler.overall_rating}")
        print(f"   Salary: ${wrestler.contract.salary_per_show:,}/show")
        
        database.save_wrestler(wrestler)
        database.conn.commit()
        
        print(f"✅ Saved to database")
        
        database.update_wrestler_stats_cache(wrestler_id)
        database.conn.commit()
        
        print(f"✅ Initialized stats cache")
        print()
        
        return jsonify({
            'success': True,
            'message': f'Wrestler "{wrestler.name}" created successfully',
            'wrestler': wrestler.to_dict()
        })
    
    except Exception as e:
        error_trace = traceback.format_exc()
        
        print(f"\n❌ CAW Creation Error:")
        print(error_trace)
        print()
        
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': error_trace
        }), 500


@caw_bp.route('/api/caw/next-id')
def api_get_next_wrestler_id():
    database = get_database()
    
    try:
        from models.caw import CAWFactory
        
        next_id = CAWFactory.generate_wrestler_id(database)
        
        return jsonify({
            'success': True,
            'next_id': next_id
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@caw_bp.route('/api/caw/calculate-overall', methods=['POST'])
def api_calculate_overall():
    try:
        from models.caw import CAWFactory
        
        data = _normalize_caw_payload(request.get_json())
        
        overall = CAWFactory.calculate_overall_preview(data)
        suggested_salary = CAWFactory.get_suggested_salary(
            data.get('role', 'Midcard'),
            overall
        )
        
        return jsonify({
            'success': True,
            'overall_rating': overall,
            'suggested_salary': suggested_salary
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@caw_bp.route('/api/caw/random', methods=['POST'])
def api_create_random_wrestler():
    database = get_database()
    universe = get_universe()
    
    try:
        from models.caw import CAWValidator, CAWFactory
        
        data = request.get_json() if request.is_json else {}
        
        gender = data.get('gender', random.choice(['Male', 'Female']))
        brand = data.get('primary_brand', random.choice(['ROC Alpha', 'ROC Velocity', 'ROC Vanguard']))
        role = data.get('role', random.choice(['Upper Midcard', 'Midcard', 'Lower Midcard']))
        
        first_names_male = ['Jake', 'Marcus', 'Tyler', 'Ryan', 'Chris', 'Alex', 'Jordan', 'Max', 'Cole', 'Finn']
        first_names_female = ['Luna', 'Ember', 'Jade', 'Phoenix', 'Storm', 'Nova', 'Raven', 'Blaze', 'Ivy', 'Sky']
        last_names = ['Steel', 'Shadow', 'Thunder', 'Phoenix', 'Knight', 'Storm', 'Blaze', 'Savage', 'Viper', 'Wolf']
        
        first = random.choice(first_names_male if gender == 'Male' else first_names_female)
        last = random.choice(last_names)
        name = f"{first} {last}"
        
        if role == 'Main Event':
            attr_min, attr_max = 65, 95
        elif role == 'Upper Midcard':
            attr_min, attr_max = 55, 85
        elif role == 'Midcard':
            attr_min, attr_max = 45, 75
        else:
            attr_min, attr_max = 35, 65
        
        random_data = {
            'name': name,
            'age': random.randint(22, 38),
            'gender': gender,
            'alignment': 'Neutral',
            'role': role,
            'primary_brand': brand,
            'brawling': random.randint(attr_min, attr_max),
            'technical': random.randint(attr_min, attr_max),
            'speed': random.randint(attr_min, attr_max),
            'mic': random.randint(attr_min, attr_max),
            'psychology': random.randint(attr_min, attr_max),
            'stamina': random.randint(attr_min, attr_max),
            'years_experience': random.randint(1, 12),
            'is_major_superstar': False
        }
        
        overall = CAWFactory.calculate_overall_preview(random_data)
        salary = CAWFactory.get_suggested_salary(role, overall)
        
        random_data['salary_per_show'] = salary
        random_data['contract_weeks'] = random.choice([52, 104, 156])
        
        is_valid, errors = CAWValidator.validate_all(random_data)
        
        if not is_valid:
            return jsonify({
                'success': False,
                'error': 'Generated data failed validation',
                'errors': errors
            }), 500
        
        wrestler_id = CAWFactory.generate_wrestler_id(database)
        
        wrestler = CAWFactory.create_wrestler(
            data=random_data,
            wrestler_id=wrestler_id,
            current_year=universe.current_year,
            current_week=universe.current_week
        )
        
        database.save_wrestler(wrestler)
        database.conn.commit()
        
        database.update_wrestler_stats_cache(wrestler_id)
        database.conn.commit()
        
        print(f"🎲 Random wrestler created: {wrestler.name} ({wrestler_id})")
        
        return jsonify({
            'success': True,
            'message': f'Random wrestler "{wrestler.name}" created',
            'wrestler': wrestler.to_dict()
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@caw_bp.route('/api/caw/test/create-sample', methods=['POST'])
def api_test_create_sample_wrestler():
    database = get_database()
    universe = get_universe()
    
    try:
        from models.caw import CAWValidator, CAWFactory
        
        first_names = [
            'Sample', 'Test', 'Demo', 'Trial',
            'Mock', 'Dummy', 'Example', 'Pilot', 'Proto', 'Draft', 'Preview', 'Sketch',
            'Max', 'Rex', 'Nova', 'Blaze', 'Ace', 'Dash', 'Jet', 'Hawk',
            'Wolf', 'Raven', 'Hunter', 'Atlas', 'Zero', 'Neo', 'Echo', 'Apex',
            'Cipher', 'Vector', 'Nexus', 'Prime', 'Onyx', 'Axel', 'Zane', 'Kai',
            'Drake', 'Jax', 'Finn', 'Cole', 'Reed', 'Blake', 'Chase', 'Grant'
        ]
        
        last_names = [
            'Alpha', 'Beta', 'Gamma', 'Delta', 'Thunder', 'Lightning',
            'Storm', 'Phoenix', 'Titan', 'Steel', 'Knight', 'Shadow',
            'Blaze', 'Frost', 'Flame', 'Ember', 'Aurora', 'Vortex', 'Cyclone', 'Avalanche',
            'Iron', 'Bronze', 'Silver', 'Chrome', 'Diamond', 'Obsidian', 'Granite', 'Cobalt',
            'Fury', 'Valor', 'Glory', 'Legend', 'Striker', 'Blade', 'Shield', 'Hammer',
            'Falcon', 'Viper', 'Dragon', 'Griffin', 'Panther', 'Hawk', 'Raven', 'Wolf',
            'Surge', 'Pulse', 'Core', 'Zenith', 'Apex', 'Edge', 'Rider', 'Hunter',
            'Specter', 'Phantom', 'Wraith', 'Sentinel', 'Guardian', 'Warden', 'Ranger', 'Slayer'
        ]
        
        existing_names = [w['name'].lower() for w in database.get_all_wrestlers(active_only=False)]
        
        max_attempts = 20
        for _ in range(max_attempts):
            first = random.choice(first_names)
            last = random.choice(last_names)
            sample_name = f"{first} {last}"
            
            if sample_name.lower() not in existing_names:
                break
        else:
            sample_name = f"Test Wrestler {random.randint(1000, 9999)}"
        
        sample_data = {
            'name': sample_name,
            'age': 28,
            'gender': 'Male',
            'alignment': 'Neutral',
            'role': 'Midcard',
            'primary_brand': 'ROC Alpha',
            'brawling': 70,
            'technical': 65,
            'speed': 75,
            'mic': 60,
            'psychology': 70,
            'stamina': 68,
            'salary_per_show': 8000,
            'contract_weeks': 52,
            'years_experience': 5,
            'is_major_superstar': False
        }
        
        is_valid, errors = CAWValidator.validate_all(sample_data)
        
        if not is_valid:
            return jsonify({
                'success': False,
                'error': 'Sample data validation failed',
                'errors': errors
            }), 500
        
        wrestler_id = CAWFactory.generate_wrestler_id(database)
        
        wrestler = CAWFactory.create_wrestler(
            data=sample_data,
            wrestler_id=wrestler_id,
            current_year=universe.current_year,
            current_week=universe.current_week
        )
        
        database.save_wrestler(wrestler)
        database.conn.commit()
        
        database.update_wrestler_stats_cache(wrestler_id)
        database.conn.commit()
        
        print(f"✅ Test wrestler created: {wrestler.name} ({wrestler_id})")
        
        return jsonify({
            'success': True,
            'message': f'Sample wrestler "{wrestler.name}" created',
            'wrestler': wrestler.to_dict()
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500
