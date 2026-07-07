"""
Injury Routes - Injury & Rehabilitation System (Step 20)
"""

from flask import Blueprint, jsonify, request, current_app
import traceback

injury_bp = Blueprint('injury', __name__)


def get_database():
    return current_app.config['DATABASE']


def get_universe():
    return current_app.config['UNIVERSE']


def get_injury_manager():
    return current_app.config.get('INJURY_MANAGER')


def _severity_bucket(severity):
    severity = (severity or '').lower()
    if severity in {'career threatening', 'critical'}:
        return 'critical'
    if severity in {'severe', 'major'}:
        return 'severe'
    if severity == 'moderate':
        return 'moderate'
    return 'minor'


@injury_bp.route('/api/injuries/report')
def api_injury_report():
    universe = get_universe()
    injury_manager = get_injury_manager()
    
    try:
        roster = universe.get_active_wrestlers()
        report = injury_manager.get_injury_report(roster)
        
        return jsonify({
            'success': True,
            'report': report
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@injury_bp.route('/api/injuries/active')
def api_get_active_injuries():
    universe = get_universe()
    injury_manager = get_injury_manager()
    
    try:
        injured_wrestlers = [w for w in universe.get_active_wrestlers() if w.is_injured]
        
        injuries = []
        for wrestler in injured_wrestlers:
            injury_details = injury_manager.active_injuries.get(wrestler.id)
            
            injury_data = {
                'wrestler': wrestler.to_dict(),
                'injury': {
                    'severity': wrestler.injury.severity,
                    'description': wrestler.injury.description,
                    'weeks_remaining': wrestler.injury.weeks_remaining
                }
            }
            
            if injury_details:
                injury_data['injury'].update({
                    'body_part': injury_details.body_part.value,
                    'requires_surgery': injury_details.requires_surgery,
                    'can_appear_limited': injury_details.can_appear_limited,
                    'rehab_progress': injury_details.rehab_progress,
                    'medical_costs': injury_details.medical_costs,
                    'milestones': injury_details.rehab_milestones
                })
            
            injuries.append(injury_data)
        
        return jsonify({
            'success': True,
            'total': len(injuries),
            'injuries': injuries
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@injury_bp.route('/api/injuries/<wrestler_id>')
def api_get_wrestler_injury(wrestler_id):
    universe = get_universe()
    injury_manager = get_injury_manager()
    
    try:
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        
        if not wrestler:
            return jsonify({'success': False, 'error': 'Wrestler not found'}), 404
        
        if not wrestler.is_injured:
            return jsonify({'success': False, 'error': 'Wrestler is not injured'}), 404
        
        injury_details = injury_manager.active_injuries.get(wrestler_id)
        
        response = {
            'success': True,
            'wrestler': wrestler.to_dict(),
            'injury': {
                'severity': wrestler.injury.severity,
                'description': wrestler.injury.description,
                'weeks_remaining': wrestler.injury.weeks_remaining
            }
        }
        
        if injury_details:
            response['injury'].update({
                'body_part': injury_details.body_part.value,
                'requires_surgery': injury_details.requires_surgery,
                'can_appear_limited': injury_details.can_appear_limited,
                'rehab_progress': injury_details.rehab_progress,
                'medical_costs': injury_details.medical_costs,
                'milestones': injury_details.rehab_milestones,
                'occurred_date': injury_details.occurred_date,
                'estimated_return': injury_details.return_date
            })
        
        return jsonify(response)
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@injury_bp.route('/api/injuries/<wrestler_id>/apply', methods=['POST'])
def api_apply_injury(wrestler_id):
    universe = get_universe()
    
    try:
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        
        if not wrestler:
            return jsonify({'success': False, 'error': 'Wrestler not found'}), 404
        
        data = request.get_json()
        
        severity = data.get('severity', 'Moderate')
        description = data.get('description', 'Unspecified injury')
        weeks_out = data.get('weeks_out', 4)
        
        wrestler.apply_injury(severity, description, weeks_out)
        
        universe.save_wrestler(wrestler)
        
        return jsonify({
            'success': True,
            'message': f'Injury applied to {wrestler.name}',
            'wrestler': wrestler.to_dict()
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@injury_bp.route('/api/injuries/<wrestler_id>/heal', methods=['POST'])
def api_heal_injury(wrestler_id):
    universe = get_universe()
    injury_manager = get_injury_manager()
    
    try:
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        
        if not wrestler:
            return jsonify({'success': False, 'error': 'Wrestler not found'}), 404
        
        if not wrestler.is_injured:
            return jsonify({'success': False, 'error': 'Wrestler is not injured'}), 404
        
        data = request.get_json()
        weeks_to_heal = data.get('weeks', wrestler.injury.weeks_remaining)
        
        wrestler.heal_injury(weeks_to_heal)
        
        if not wrestler.is_injured and wrestler_id in injury_manager.active_injuries:
            del injury_manager.active_injuries[wrestler_id]
        
        universe.save_wrestler(wrestler)
        
        return jsonify({
            'success': True,
            'message': f'{wrestler.name} {"fully healed" if not wrestler.is_injured else "partially healed"}',
            'wrestler': wrestler.to_dict()
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@injury_bp.route('/api/injuries/<wrestler_id>/rush-return', methods=['POST'])
def api_rush_return(wrestler_id):
    universe = get_universe()
    injury_manager = get_injury_manager()
    
    try:
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        
        if not wrestler:
            return jsonify({'success': False, 'error': 'Wrestler not found'}), 404
        
        if not wrestler.is_injured:
            return jsonify({'success': False, 'error': 'Wrestler is not injured'}), 404
        
        injury_details = injury_manager.active_injuries.get(wrestler_id)
        
        if not injury_details:
            return jsonify({
                'success': False,
                'message': 'Cannot rush return from this injury'
            })
        
        success, message = injury_manager.simulator.attempt_rushed_return(wrestler, injury_details)
        
        if success and wrestler_id in injury_manager.active_injuries:
            del injury_manager.active_injuries[wrestler_id]
        
        universe.save_wrestler(wrestler)
        
        return jsonify({
            'success': success,
            'message': message,
            'wrestler': wrestler.to_dict()
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@injury_bp.route('/api/injuries/dashboard')
def api_injury_dashboard():
    universe = get_universe()
    injury_manager = get_injury_manager()

    try:
        roster = universe.get_active_wrestlers()
        injured_wrestlers = [w for w in roster if w.is_injured]
        severity_counts = {
            'critical': 0,
            'severe': 0,
            'moderate': 0,
            'minor': 0,
        }
        body_part_counts = {}
        return_windows = {
            '1_2_weeks': 0,
            '3_4_weeks': 0,
            '5_plus_weeks': 0,
        }
        work_through_candidates = []
        at_risk = []

        for wrestler in roster:
            if wrestler.is_injured:
                bucket = _severity_bucket(wrestler.injury.severity)
                severity_counts[bucket] += 1

                details = injury_manager.active_injuries.get(wrestler.id) if injury_manager else None
                if details:
                    body_part = details.body_part.value
                    body_part_counts[body_part] = body_part_counts.get(body_part, 0) + 1

                weeks_remaining = int(wrestler.injury.weeks_remaining or 0)
                if weeks_remaining <= 2:
                    return_windows['1_2_weeks'] += 1
                elif weeks_remaining <= 4:
                    return_windows['3_4_weeks'] += 1
                else:
                    return_windows['5_plus_weeks'] += 1

                if bucket in {'minor', 'moderate'}:
                    work_through_candidates.append({
                        'wrestler_id': wrestler.id,
                        'name': wrestler.name,
                        'brand': wrestler.primary_brand,
                        'severity': wrestler.injury.severity,
                        'description': wrestler.injury.description,
                        'weeks_remaining': weeks_remaining,
                        'fatigue': wrestler.fatigue,
                    })

            injury_risk_score = min(
                100,
                wrestler.fatigue + (20 if wrestler.age >= 40 else 0) + (15 if wrestler.is_injured else 0)
            )
            if injury_risk_score >= 70:
                at_risk.append({
                    'wrestler_id': wrestler.id,
                    'name': wrestler.name,
                    'brand': wrestler.primary_brand,
                    'age': wrestler.age,
                    'fatigue': wrestler.fatigue,
                    'is_injured': wrestler.is_injured,
                    'injury_risk_score': injury_risk_score,
                })

        body_part_breakdown = [
            {'body_part': body_part, 'count': count}
            for body_part, count in sorted(body_part_counts.items(), key=lambda item: (-item[1], item[0]))
        ]
        at_risk.sort(key=lambda item: (-item['injury_risk_score'], -item['fatigue']))
        work_through_candidates.sort(key=lambda item: (item['weeks_remaining'], item['fatigue']))

        staff = injury_manager.simulator.staff_config if injury_manager else {}
        return jsonify({
            'success': True,
            'summary': {
                'active_injuries': len(injured_wrestlers),
                'critical_count': severity_counts['critical'] + severity_counts['severe'],
                'work_through_candidates': len(work_through_candidates),
                'at_risk_count': len(at_risk),
                'medical_staff_tier': getattr(injury_manager.simulator, 'medical_staff_tier', 'Unknown') if injury_manager else 'Unknown',
                'weekly_medical_cost': int(staff.get('cost_per_week', 0)),
            },
            'severity_counts': severity_counts,
            'body_part_breakdown': body_part_breakdown,
            'return_windows': return_windows,
            'work_through_candidates': work_through_candidates[:12],
            'at_risk': at_risk[:12],
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@injury_bp.route('/api/injuries/<wrestler_id>/work-through', methods=['POST'])
def api_work_through_injury(wrestler_id):
    """Allow a wrestler to work through an injury at reduced condition."""
    universe = get_universe()
    injury_manager = get_injury_manager()

    try:
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'success': False, 'error': 'Wrestler not found'}), 404
        if not wrestler.is_injured:
            return jsonify({'success': False, 'error': 'Wrestler is not injured'}), 400

        if wrestler.injury.severity == 'Major':
            return jsonify({
                'success': False,
                'error': 'Major injuries cannot be worked through safely'
            }), 400

        wrestler.injury.severity = 'Minor'
        wrestler.injury.description = f"{wrestler.injury.description} (working through injury)"
        wrestler.adjust_fatigue(15)
        wrestler.adjust_morale(-5)

        injury_details = injury_manager.active_injuries.get(wrestler_id) if injury_manager else None
        if injury_details:
            injury_details.can_appear_limited = True

        universe.save_wrestler(wrestler)

        return jsonify({
            'success': True,
            'message': f'{wrestler.name} will work through the injury with reduced performance and elevated risk',
            'wrestler': wrestler.to_dict()
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@injury_bp.route('/api/injuries/create-angle', methods=['POST'])
def api_create_injury_angle():
    universe = get_universe()
    injury_manager = get_injury_manager()
    
    try:
        from models.feud import FeudType
        
        data = request.get_json()
        wrestler_id = data.get('wrestler_id')
        attacker_id = data.get('attacker_id')
        
        injured_wrestler = universe.get_wrestler_by_id(wrestler_id)
        
        if not injured_wrestler:
            return jsonify({'success': False, 'error': 'Wrestler not found'}), 404
        
        attacker = None
        if attacker_id:
            attacker = universe.get_wrestler_by_id(attacker_id)
        
        angle = injury_manager.create_injury_writeoff(
            injured_wrestler=injured_wrestler,
            roster=universe.get_active_wrestlers(),
            existing_feuds=universe.feud_manager.get_active_feuds()
        )
        
        if angle.get('creates_feud') and attacker:
            feud = universe.feud_manager.create_feud(
                feud_type=FeudType.PERSONAL,
                participant_ids=[wrestler_id, attacker_id],
                participant_names=[injured_wrestler.name, attacker.name],
                year=universe.current_year,
                week=universe.current_week,
                initial_intensity=angle.get('feud_intensity', 50)
            )
            
            universe.save_feud(feud)
            
            angle['feud_created'] = True
            angle['feud_id'] = feud.id
        
        return jsonify({
            'success': True,
            'angle': angle
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@injury_bp.route('/api/injuries/return-angle', methods=['POST'])
def api_create_return_angle():
    universe = get_universe()
    injury_manager = get_injury_manager()
    
    try:
        data = request.get_json()
        wrestler_id = data.get('wrestler_id')
        is_surprise = data.get('is_surprise', True)
        target_id = data.get('target_id')
        
        returning_wrestler = universe.get_wrestler_by_id(wrestler_id)
        
        if not returning_wrestler:
            return jsonify({'success': False, 'error': 'Wrestler not found'}), 404
        
        target = None
        if target_id:
            target = universe.get_wrestler_by_id(target_id)
        
        angle = injury_manager.angle_generator.generate_return_angle(
            returning_wrestler=returning_wrestler,
            is_surprise=is_surprise,
            target=target
        )
        
        returning_wrestler.adjust_momentum(angle['momentum_boost'])
        returning_wrestler.adjust_popularity(angle['popularity_boost'])
        
        universe.save_wrestler(returning_wrestler)
        
        return jsonify({
            'success': True,
            'angle': angle
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@injury_bp.route('/api/injuries/process-weekly', methods=['POST'])
def api_process_weekly_recovery():
    database = get_database()
    universe = get_universe()
    injury_manager = get_injury_manager()
    
    try:
        roster = universe.get_active_wrestlers()
        recovery_updates = injury_manager.process_weekly_recovery(
            roster,
            universe.current_year,
            universe.current_week
        )
        
        for wrestler in roster:
            universe.save_wrestler(wrestler)
        
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'updates': recovery_updates
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@injury_bp.route('/api/injuries/medical-staff')
def api_get_medical_staff():
    injury_manager = get_injury_manager()
    
    try:
        from simulation.injuries import MedicalStaff
        
        current_tier = injury_manager.simulator.medical_staff_tier
        current_config = injury_manager.simulator.staff_config
        
        return jsonify({
            'success': True,
            'current_tier': current_tier,
            'current_config': current_config,
            'available_tiers': MedicalStaff.STAFF_TIERS
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@injury_bp.route('/api/injuries/medical-staff/upgrade', methods=['POST'])
def api_upgrade_medical_staff():
    universe = get_universe()
    injury_manager = get_injury_manager()
    
    try:
        from simulation.injuries import MedicalStaff
        
        data = request.get_json()
        new_tier = data.get('tier', 'Standard')
        
        if new_tier not in MedicalStaff.STAFF_TIERS:
            return jsonify({'success': False, 'error': 'Invalid tier'}), 400
        
        old_cost = injury_manager.simulator.staff_config['cost_per_week']
        new_cost = MedicalStaff.STAFF_TIERS[new_tier]['cost_per_week']
        upgrade_fee = (new_cost - old_cost) * 4
        
        if universe.balance < upgrade_fee:
            return jsonify({
                'success': False,
                'error': f'Insufficient funds. Need ${upgrade_fee:,}'
            }), 400
        
        injury_manager.simulator.medical_staff_tier = new_tier
        injury_manager.simulator.staff_config = MedicalStaff.STAFF_TIERS[new_tier]
        
        universe.balance -= upgrade_fee
        
        return jsonify({
            'success': True,
            'message': f'Medical staff upgraded to {new_tier}',
            'new_tier': new_tier,
            'upgrade_cost': upgrade_fee,
            'new_balance': universe.balance
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@injury_bp.route('/api/injuries/weekly-recovery', methods=['POST'])
def api_weekly_injury_recovery():
    database = get_database()
    universe = get_universe()
    injury_manager = get_injury_manager()
    
    try:
        roster = universe.wrestlers
        
        recovery_updates = injury_manager.process_weekly_recovery(
            roster,
            universe.current_year,
            universe.current_week
        )
        
        for update in recovery_updates:
            wrestler = universe.get_wrestler_by_id(update['wrestler_id'])
            if wrestler:
                universe.save_wrestler(wrestler)
        
        medical_costs = injury_manager.simulator.staff_config['cost_per_week']
        injured_count = len([w for w in roster if w.is_injured])
        
        if injured_count > 0:
            total_medical_cost = medical_costs
            universe.balance -= total_medical_cost
            
            recovery_updates.append({
                'type': 'medical_costs',
                'message': f'Medical staff costs: ${total_medical_cost:,}',
                'injured_count': injured_count
            })
        
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'updates': recovery_updates,
            'current_balance': universe.balance
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500
