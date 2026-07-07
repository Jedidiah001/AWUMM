"""
Tag Team Routes - Tag Team Management (Step 13)
"""

from flask import Blueprint, jsonify, request, current_app

tag_team_bp = Blueprint('tag_team', __name__)


def get_database():
    return current_app.config['DATABASE']


def get_universe():
    return current_app.config['UNIVERSE']


@tag_team_bp.route('/api/tag-teams')
def api_get_tag_teams():
    universe = get_universe()
    
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    brand = request.args.get('brand')
    
    try:
        teams = universe.tag_team_manager.get_active_teams() if active_only else universe.tag_team_manager.teams
        
        if brand:
            teams = [t for t in teams if t.primary_brand == brand]
        
        return jsonify({
            'success': True,
            'total': len(teams),
            'teams': [t.to_dict() for t in teams]
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@tag_team_bp.route('/api/tag-teams/<team_id>')
def api_get_tag_team(team_id):
    universe = get_universe()
    
    try:
        team = universe.tag_team_manager.get_team_by_id(team_id)
        
        if not team:
            return jsonify({'success': False, 'error': 'Tag team not found'}), 404
        
        return jsonify({
            'success': True,
            'team': team.to_dict()
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@tag_team_bp.route('/api/tag-teams/create', methods=['POST'])
def api_create_tag_team():
    universe = get_universe()
    database = get_database()
    
    try:
        data = request.get_json()
        
        member_ids = data.get('member_ids', [])
        team_name = data.get('team_name')
        primary_brand = data.get('primary_brand')
        team_identity = data.get('team_identity', '')
        entrance_style = data.get('entrance_style', 'standard')
        signature_double_team = data.get('signature_double_team')
        manager_id = data.get('manager_id')
        manager_name = data.get('manager_name')
        initial_chemistry = data.get('initial_chemistry', 50)
        
        if len(member_ids) < 2:
            return jsonify({'success': False, 'error': 'At least 2 members required'}), 400
        
        if not team_name:
            return jsonify({'success': False, 'error': 'Team name required'}), 400
        
        member_names = []
        for member_id in member_ids:
            wrestler = universe.get_wrestler_by_id(member_id)
            if not wrestler:
                return jsonify({'success': False, 'error': f'Wrestler {member_id} not found'}), 404
            member_names.append(wrestler.name)
            
            if not primary_brand:
                primary_brand = wrestler.primary_brand
        
        team = universe.tag_team_manager.create_team(
            member_ids=member_ids,
            member_names=member_names,
            team_name=team_name,
            primary_brand=primary_brand,
            year=universe.current_year,
            week=universe.current_week,
            initial_chemistry=initial_chemistry
        )

        team.team_identity = team_identity
        team.entrance_style = entrance_style
        team.signature_double_team = signature_double_team
        team.manager_id = manager_id
        team.manager_name = manager_name
        
        universe.save_tag_team(team)
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'message': f'Tag team "{team_name}" created',
            'team': team.to_dict()
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@tag_team_bp.route('/api/tag-teams/<team_id>', methods=['PUT'])
def api_update_tag_team(team_id):
    universe = get_universe()
    database = get_database()

    try:
        team = universe.tag_team_manager.get_team_by_id(team_id)
        if not team:
            return jsonify({'success': False, 'error': 'Tag team not found'}), 404

        data = request.get_json() or {}
        for field in ['team_name', 'team_identity', 'entrance_style', 'signature_double_team', 'manager_id', 'manager_name']:
            if field in data:
                setattr(team, field, data.get(field))

        if 'chemistry' in data:
            team.chemistry = max(0, min(100, int(data['chemistry'])))
        if 'experience_weeks' in data:
            team.experience_weeks = max(0, int(data['experience_weeks']))

        universe.save_tag_team(team)
        database.conn.commit()

        return jsonify({
            'success': True,
            'message': f'Tag team "{team.team_name}" updated',
            'team': team.to_dict()
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@tag_team_bp.route('/api/tag-teams/<team_id>/disband', methods=['POST'])
def api_disband_tag_team(team_id):
    universe = get_universe()
    database = get_database()
    
    try:
        team = universe.tag_team_manager.get_team_by_id(team_id)
        
        if not team:
            return jsonify({'success': False, 'error': 'Tag team not found'}), 404
        
        team.disband()
        
        universe.save_tag_team(team)
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'message': f'Tag team "{team.team_name}" disbanded'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@tag_team_bp.route('/api/tag-teams/suggestions/<brand>')
def api_get_tag_team_suggestions(brand):
    universe = get_universe()
    
    try:
        max_suggestions = request.args.get('max', 5, type=int)
        
        wrestlers = universe.get_wrestlers_by_brand(brand)
        
        suggestions = universe.tag_team_manager.suggest_teams_for_brand(
            brand=brand,
            wrestlers=wrestlers,
            max_suggestions=max_suggestions
        )
        
        return jsonify({
            'success': True,
            'brand': brand,
            'total': len(suggestions),
            'suggestions': suggestions
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@tag_team_bp.route('/api/tag-teams/wrestler/<wrestler_id>')
def api_get_wrestler_teams(wrestler_id):
    universe = get_universe()
    
    try:
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        
        if not wrestler:
            return jsonify({'success': False, 'error': 'Wrestler not found'}), 404
        
        teams = universe.tag_team_manager.get_teams_involving_wrestler(wrestler_id)
        
        return jsonify({
            'success': True,
            'wrestler_id': wrestler_id,
            'wrestler_name': wrestler.name,
            'teams': [t.to_dict() for t in teams]
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
