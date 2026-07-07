"""
Locker-room relationship routes.
"""

from flask import Blueprint, jsonify, request, current_app

from models.relationship_network import (
    RELATIONSHIP_FRIENDSHIP,
    RELATIONSHIP_HEAT,
    RELATIONSHIP_MANAGER_CLIENT,
    RELATIONSHIP_MENTORSHIP,
    RELATIONSHIP_ROMANTIC,
)

relationship_bp = Blueprint('relationship', __name__)


def get_database():
    return current_app.config['DATABASE']


def get_universe():
    return current_app.config['UNIVERSE']


def _relationship_view(relationship):
    data = relationship.to_dict()
    data['display_label'] = relationship.relationship_type.replace('_', ' ').title()
    return data


def _faction_story_hooks(faction):
    hooks = []
    faction_data = faction.to_dict()
    hierarchy = faction_data.get('hierarchy', [])
    dynamics = faction_data.get('dynamics', {})

    for entry in hierarchy:
        metrics = dynamics.get(entry['wrestler_id'], {})
        jealousy = int(metrics.get('jealousy', 0))
        loyalty = int(metrics.get('loyalty', 0))
        power = int(metrics.get('power', 0))

        if jealousy >= 70:
            hooks.append({
                'faction_id': faction.faction_id,
                'faction_name': faction.faction_name,
                'type': 'jealousy_flashpoint',
                'wrestler_id': entry['wrestler_id'],
                'wrestler_name': entry['wrestler_name'],
                'summary': f"{entry['wrestler_name']} is openly jealous of their position in {faction.faction_name}.",
                'severity': 'high'
            })
        elif loyalty <= 35:
            hooks.append({
                'faction_id': faction.faction_id,
                'faction_name': faction.faction_name,
                'type': 'loyalty_drop',
                'wrestler_id': entry['wrestler_id'],
                'wrestler_name': entry['wrestler_name'],
                'summary': f"{entry['wrestler_name']}'s loyalty to {faction.faction_name} is slipping.",
                'severity': 'medium'
            })

        if power >= 80 and entry['wrestler_id'] != faction.leader_id:
            hooks.append({
                'faction_id': faction.faction_id,
                'faction_name': faction.faction_name,
                'type': 'power_struggle',
                'wrestler_id': entry['wrestler_id'],
                'wrestler_name': entry['wrestler_name'],
                'summary': f"{entry['wrestler_name']} is building enough influence to threaten the faction pecking order.",
                'severity': 'high'
            })

    return hooks


@relationship_bp.route('/api/relationships/dashboard')
def api_relationship_dashboard():
    universe = get_universe()
    roster = universe.get_active_wrestlers()
    relationships = [
        rel for rel in universe.relationship_network.relationships
        if rel.is_active
    ]
    teams = universe.tag_team_manager.get_active_teams()
    factions = universe.faction_manager.get_active_factions()

    grouped = {
        RELATIONSHIP_FRIENDSHIP: [],
        RELATIONSHIP_HEAT: [],
        RELATIONSHIP_MENTORSHIP: [],
        RELATIONSHIP_ROMANTIC: [],
        RELATIONSHIP_MANAGER_CLIENT: [],
    }
    for relationship in relationships:
        grouped.setdefault(relationship.relationship_type, []).append(_relationship_view(relationship))

    grouped[RELATIONSHIP_FRIENDSHIP].sort(key=lambda rel: rel['strength'], reverse=True)
    grouped[RELATIONSHIP_HEAT].sort(key=lambda rel: rel['strength'], reverse=True)
    grouped[RELATIONSHIP_MENTORSHIP].sort(key=lambda rel: rel['strength'], reverse=True)
    grouped[RELATIONSHIP_ROMANTIC].sort(key=lambda rel: rel['strength'], reverse=True)
    grouped[RELATIONSHIP_MANAGER_CLIENT].sort(key=lambda rel: rel['strength'], reverse=True)

    manager_effectiveness = []
    for relationship in grouped[RELATIONSHIP_MANAGER_CLIENT]:
        manager_id = relationship['wrestler_a_id']
        client_id = relationship['wrestler_b_id']
        match_bonus = universe.relationship_network.get_manager_bonus([client_id], context='match')
        promo_bonus = universe.relationship_network.get_manager_bonus([client_id], context='promo')
        metadata = relationship.get('metadata') or {}
        manager_effectiveness.append({
            'relationship_id': relationship['relationship_id'],
            'manager_id': manager_id,
            'manager_name': relationship['wrestler_a_name'],
            'client_id': client_id,
            'client_name': relationship['wrestler_b_name'],
            'effectiveness': int(metadata.get('effectiveness', relationship['strength'])),
            'fit': int(metadata.get('fit', relationship['strength'])),
            'strength': relationship['strength'],
            'match_bonus': match_bonus,
            'promo_bonus': promo_bonus,
        })

    chemistry_bands = {
        'elite': [team.to_dict() for team in teams if team.chemistry >= 80],
        'solid': [team.to_dict() for team in teams if 60 <= team.chemistry < 80],
        'volatile': [team.to_dict() for team in teams if team.chemistry < 60],
    }
    experienced_teams = [
        team.to_dict() for team in sorted(
            teams,
            key=lambda item: (item.experience_weeks, item.chemistry),
            reverse=True,
        )[:5]
    ]

    faction_hooks = []
    for faction in factions:
        faction_hooks.extend(_faction_story_hooks(faction))
    faction_hooks.sort(key=lambda hook: (hook['severity'] != 'high', hook['summary']))

    return jsonify({
        'success': True,
        'summary': {
            'total_relationships': len(relationships),
            'friendships': len(grouped[RELATIONSHIP_FRIENDSHIP]),
            'heat': len(grouped[RELATIONSHIP_HEAT]),
            'mentorships': len(grouped[RELATIONSHIP_MENTORSHIP]),
            'romantic_relationships': len(grouped[RELATIONSHIP_ROMANTIC]),
            'manager_clients': len(grouped[RELATIONSHIP_MANAGER_CLIENT]),
            'active_tag_teams': len(teams),
            'active_factions': len(factions),
            'roster_size': len(roster),
        },
        'tag_teams': {
            'all': [team.to_dict() for team in teams],
            'chemistry_bands': chemistry_bands,
            'most_experienced': experienced_teams,
        },
        'factions': {
            'all': [faction.to_dict() for faction in factions],
            'story_hooks': faction_hooks[:12],
        },
        'relationships': {
            'friendships': grouped[RELATIONSHIP_FRIENDSHIP][:12],
            'heat': grouped[RELATIONSHIP_HEAT][:12],
            'mentorships': grouped[RELATIONSHIP_MENTORSHIP][:12],
            'romantic': grouped[RELATIONSHIP_ROMANTIC][:12],
            'manager_clients': grouped[RELATIONSHIP_MANAGER_CLIENT][:12],
        },
        'manager_effectiveness': manager_effectiveness[:12],
    })


@relationship_bp.route('/api/relationships')
def api_get_relationships():
    universe = get_universe()
    relationship_type = request.args.get('type')
    wrestler_id = request.args.get('wrestler_id')

    if wrestler_id:
        relationships = universe.relationship_network.get_relationships_for_wrestler(wrestler_id, relationship_type)
    else:
        relationships = [
            rel for rel in universe.relationship_network.relationships
            if rel.is_active and (relationship_type is None or rel.relationship_type == relationship_type)
        ]

    return jsonify({
        'success': True,
        'total': len(relationships),
        'relationships': [rel.to_dict() for rel in relationships]
    })


@relationship_bp.route('/api/relationships/wrestler/<wrestler_id>')
def api_get_relationships_for_wrestler(wrestler_id):
    universe = get_universe()
    relationship_type = request.args.get('type')
    relationships = universe.relationship_network.get_relationships_for_wrestler(wrestler_id, relationship_type)
    return jsonify({
        'success': True,
        'total': len(relationships),
        'relationships': [rel.to_dict() for rel in relationships]
    })


@relationship_bp.route('/api/relationships/create', methods=['POST'])
def api_create_relationship():
    universe = get_universe()
    database = get_database()
    data = request.get_json() or {}

    wrestler_a = universe.get_wrestler_by_id(data.get('wrestler_a_id'))
    wrestler_b = universe.get_wrestler_by_id(data.get('wrestler_b_id'))
    if not wrestler_a or not wrestler_b:
        return jsonify({'success': False, 'error': 'Both wrestlers must exist'}), 404

    relationship_type = data.get('relationship_type', RELATIONSHIP_FRIENDSHIP)
    if relationship_type not in {
        RELATIONSHIP_FRIENDSHIP,
        RELATIONSHIP_HEAT,
        RELATIONSHIP_MENTORSHIP,
        RELATIONSHIP_ROMANTIC,
        RELATIONSHIP_MANAGER_CLIENT,
    }:
        return jsonify({'success': False, 'error': 'Invalid relationship type'}), 400

    relationship = universe.relationship_network.create_or_update_relationship(
        wrestler_a.id,
        wrestler_a.name,
        wrestler_b.id,
        wrestler_b.name,
        relationship_type,
        base_strength=int(data.get('strength', 55)),
        metadata=data.get('metadata', {}),
        note=data.get('note'),
    )

    universe.save_relationship(relationship)
    database.conn.commit()

    return jsonify({'success': True, 'relationship': relationship.to_dict()})


@relationship_bp.route('/api/relationships/<relationship_id>/adjust', methods=['POST'])
def api_adjust_relationship(relationship_id):
    universe = get_universe()
    database = get_database()
    relationship = universe.relationship_network.get_relationship_by_id(relationship_id)
    if not relationship:
        return jsonify({'success': False, 'error': 'Relationship not found'}), 404

    data = request.get_json() or {}
    relationship.adjust_strength(int(data.get('delta', 0)), data.get('note'))
    if 'metadata' in data:
        relationship.metadata.update(data.get('metadata') or {})

    universe.save_relationship(relationship)
    database.conn.commit()

    return jsonify({'success': True, 'relationship': relationship.to_dict()})


@relationship_bp.route('/api/relationships/auto-seed', methods=['POST'])
def api_auto_seed_relationships():
    universe = get_universe()
    database = get_database()
    data = request.get_json() or {}

    brand = data.get('brand')
    max_new_relationships = int(data.get('max_new_relationships', 20))
    wrestlers = universe.get_active_wrestlers()
    seeded = universe.relationship_network.seed_natural_relationships(
        wrestlers,
        brand=brand,
        max_new_relationships=max_new_relationships
    )

    for relationship in seeded:
        universe.save_relationship(relationship)
    database.conn.commit()

    return jsonify({
        'success': True,
        'seeded_count': len(seeded),
        'relationships': [rel.to_dict() for rel in seeded]
    })
