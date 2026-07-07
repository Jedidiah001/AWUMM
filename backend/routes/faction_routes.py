"""
Faction and stable management routes.
"""

from flask import Blueprint, jsonify, request, current_app

faction_bp = Blueprint('faction', __name__)


def get_database():
    return current_app.config['DATABASE']


def get_universe():
    return current_app.config['UNIVERSE']


@faction_bp.route('/api/factions')
def api_get_factions():
    universe = get_universe()
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    brand = request.args.get('brand')

    factions = universe.faction_manager.get_active_factions() if active_only else universe.faction_manager.factions
    if brand:
        factions = [faction for faction in factions if faction.primary_brand == brand]

    return jsonify({
        'success': True,
        'total': len(factions),
        'factions': [faction.to_dict() for faction in factions]
    })


@faction_bp.route('/api/factions/<faction_id>')
def api_get_faction(faction_id):
    universe = get_universe()
    faction = universe.faction_manager.get_faction_by_id(faction_id)
    if not faction:
        return jsonify({'success': False, 'error': 'Faction not found'}), 404

    return jsonify({'success': True, 'faction': faction.to_dict()})


@faction_bp.route('/api/factions/create', methods=['POST'])
def api_create_faction():
    universe = get_universe()
    database = get_database()
    data = request.get_json() or {}

    member_ids = data.get('member_ids', [])
    faction_name = data.get('faction_name')
    leader_id = data.get('leader_id')

    if len(member_ids) < 3:
        return jsonify({'success': False, 'error': 'At least 3 members are required to form a faction'}), 400
    if not faction_name:
        return jsonify({'success': False, 'error': 'Faction name required'}), 400
    if not leader_id:
        return jsonify({'success': False, 'error': 'Leader ID required'}), 400

    member_names = []
    primary_brand = data.get('primary_brand')
    leader_name = None

    for member_id in member_ids:
        wrestler = universe.get_wrestler_by_id(member_id)
        if not wrestler:
            return jsonify({'success': False, 'error': f'Wrestler {member_id} not found'}), 404
        member_names.append(wrestler.name)
        primary_brand = primary_brand or wrestler.primary_brand
        if member_id == leader_id:
            leader_name = wrestler.name

    if not leader_name:
        return jsonify({'success': False, 'error': 'Leader must be part of the faction'}), 400

    faction = universe.faction_manager.create_faction(
        faction_name=faction_name,
        member_ids=member_ids,
        member_names=member_names,
        leader_id=leader_id,
        leader_name=leader_name,
        primary_brand=primary_brand or 'Cross-Brand',
        identity=data.get('identity', ''),
        goals=data.get('goals', []),
        entrance_style=data.get('entrance_style', 'standard'),
        manager_id=data.get('manager_id'),
        manager_name=data.get('manager_name'),
    )

    universe.save_faction(faction)
    database.conn.commit()

    return jsonify({
        'success': True,
        'message': f'Faction "{faction_name}" created',
        'faction': faction.to_dict()
    })


@faction_bp.route('/api/factions/<faction_id>/members', methods=['POST'])
def api_add_faction_member(faction_id):
    universe = get_universe()
    database = get_database()
    faction = universe.faction_manager.get_faction_by_id(faction_id)
    if not faction:
        return jsonify({'success': False, 'error': 'Faction not found'}), 404

    data = request.get_json() or {}
    wrestler_id = data.get('wrestler_id')
    role = data.get('role', 'member')
    wrestler = universe.get_wrestler_by_id(wrestler_id)
    if not wrestler:
        return jsonify({'success': False, 'error': 'Wrestler not found'}), 404

    faction.add_member(wrestler.id, wrestler.name, role=role)
    universe.save_faction(faction)
    database.conn.commit()

    return jsonify({'success': True, 'faction': faction.to_dict()})


@faction_bp.route('/api/factions/<faction_id>/dynamics', methods=['POST'])
def api_update_faction_dynamics(faction_id):
    universe = get_universe()
    database = get_database()
    faction = universe.faction_manager.get_faction_by_id(faction_id)
    if not faction:
        return jsonify({'success': False, 'error': 'Faction not found'}), 404

    data = request.get_json() or {}
    wrestler_id = data.get('wrestler_id')
    if wrestler_id not in faction.member_ids:
        return jsonify({'success': False, 'error': 'Wrestler is not in this faction'}), 400

    faction.update_member_dynamics(
        wrestler_id,
        loyalty_delta=int(data.get('loyalty_delta', 0)),
        jealousy_delta=int(data.get('jealousy_delta', 0)),
        power_delta=int(data.get('power_delta', 0)),
    )
    universe.save_faction(faction)
    database.conn.commit()

    return jsonify({'success': True, 'faction': faction.to_dict()})


@faction_bp.route('/api/factions/<faction_id>/disband', methods=['POST'])
def api_disband_faction(faction_id):
    universe = get_universe()
    database = get_database()
    faction = universe.faction_manager.get_faction_by_id(faction_id)
    if not faction:
        return jsonify({'success': False, 'error': 'Faction not found'}), 404

    faction.is_active = False
    faction.is_disbanded = True
    universe.save_faction(faction)
    database.conn.commit()

    return jsonify({'success': True, 'message': f'Faction "{faction.faction_name}" disbanded'})
