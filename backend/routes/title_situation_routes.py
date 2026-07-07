"""
Title Situation Routes - Championship Hierarchy & Title Situations (Step 21)
"""

from flask import Blueprint, jsonify, request, current_app
import traceback

title_situation_bp = Blueprint('title_situation', __name__)


def get_database():
    return current_app.config['DATABASE']


def get_universe():
    return current_app.config['UNIVERSE']


@title_situation_bp.route('/api/championships/<title_id>/situation')
def api_get_title_situation(title_id):
    universe = get_universe()
    
    try:
        championship = universe.get_championship_by_id(title_id)
        
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        holder = None
        if championship.current_holder_id:
            holder = universe.get_wrestler_by_id(championship.current_holder_id)
        
        situation = universe.championship_hierarchy.get_title_situation(
            championship=championship,
            holder_wrestler=holder,
            current_year=universe.current_year,
            current_week=universe.current_week,
            last_defense_year=championship.last_defense_year,
            last_defense_week=championship.last_defense_week
        )
        
        return jsonify({
            'success': True,
            'situation': situation.to_dict()
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@title_situation_bp.route('/api/championships/<title_id>/analyze-injury')
def api_analyze_champion_injury(title_id):
    universe = get_universe()
    
    try:
        from creative.title_situations import title_situation_manager
        
        championship = universe.get_championship_by_id(title_id)
        
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        if championship.is_vacant:
            return jsonify({'success': False, 'error': 'Championship is already vacant'}), 400
        
        champion = universe.get_wrestler_by_id(championship.current_holder_id)
        
        if not champion:
            return jsonify({'success': False, 'error': 'Champion not found'}), 404
        
        if not champion.is_injured:
            return jsonify({'success': False, 'error': 'Champion is not injured'}), 400
        
        next_ppv = universe.calendar.get_next_ppv()
        upcoming_ppv_weeks = None
        if next_ppv:
            upcoming_ppv_weeks = next_ppv.week - universe.current_week
            if upcoming_ppv_weeks < 0:
                upcoming_ppv_weeks += 52
        
        analysis = title_situation_manager.analyze_champion_injury(
            championship=championship,
            champion=champion,
            current_year=universe.current_year,
            current_week=universe.current_week,
            upcoming_ppv_weeks=upcoming_ppv_weeks
        )
        
        return jsonify({
            'success': True,
            'analysis': analysis
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@title_situation_bp.route('/api/championships/<title_id>/vacate', methods=['POST'])
def api_vacate_championship(title_id):
    database = get_database()
    universe = get_universe()
    
    try:
        from models.championship_hierarchy import VacancyReason
        from creative.title_situations import title_situation_manager, TitleDecision
        from persistence.championship_db import save_vacancy, log_title_situation
        
        data = request.get_json() if request.is_json else {}
        
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        if championship.is_vacant:
            return jsonify({'success': False, 'error': 'Championship is already vacant'}), 400
        
        champion = universe.get_wrestler_by_id(championship.current_holder_id)
        if not champion:
            return jsonify({'success': False, 'error': 'Champion not found'}), 404
        
        reason_str = data.get('reason', 'injury')
        try:
            reason = VacancyReason(reason_str)
        except ValueError:
            reason = VacancyReason.RELINQUISHED
        
        show_name = data.get('show_name', f'Week {universe.current_week} Show')
        show_id = f"show_y{universe.current_year}_w{universe.current_week}"
        notes = data.get('notes', '')
        
        attacker = None
        if data.get('attacker_id'):
            attacker = universe.get_wrestler_by_id(data['attacker_id'])
        
        result = title_situation_manager.execute_title_decision(
            decision=TitleDecision.VACATE,
            championship=championship,
            champion=champion,
            year=universe.current_year,
            week=universe.current_week,
            show_id=show_id,
            show_name=show_name,
            vacancy_reason=reason,
            attacker=attacker,
            notes=notes
        )
        
        if result.success:
            if result.vacancy_id:
                vacancy = universe.championship_hierarchy.get_vacancy_for_title(title_id)
                if vacancy:
                    save_vacancy(database, vacancy.to_dict())
            
            if result.guaranteed_shot_id:
                from persistence.championship_db import save_guaranteed_shot
                for shot in universe.championship_hierarchy.guaranteed_shots:
                    if shot.shot_id == result.guaranteed_shot_id:
                        save_guaranteed_shot(database, shot.to_dict())
                        break
            
            log_title_situation(
                database,
                title_id=title_id,
                situation_type='vacancy_created',
                description=result.message,
                year=universe.current_year,
                week=universe.current_week,
                decision_made='vacate',
                decision_result='success'
            )
            
            universe.save_championship(championship)
            database.conn.commit()
        
        return jsonify({
            'success': result.success,
            'result': result.to_dict()
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@title_situation_bp.route('/api/championships/<title_id>/interim', methods=['POST'])
def api_create_interim_champion(title_id):
    database = get_database()
    universe = get_universe()
    
    try:
        from creative.title_situations import title_situation_manager, TitleDecision
        from persistence.championship_db import log_title_situation
        
        data = request.get_json()
        
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        if championship.is_vacant:
            return jsonify({'success': False, 'error': 'Cannot create interim for vacant title'}), 400
        
        if championship.has_interim_champion:
            return jsonify({'success': False, 'error': 'Already has interim champion'}), 400
        
        champion = universe.get_wrestler_by_id(championship.current_holder_id)
        interim_champion_id = data.get('interim_champion_id')
        
        if not interim_champion_id:
            return jsonify({'success': False, 'error': 'interim_champion_id required'}), 400
        
        interim_champion = universe.get_wrestler_by_id(interim_champion_id)
        if not interim_champion:
            return jsonify({'success': False, 'error': 'Interim champion not found'}), 404
        
        show_name = data.get('show_name', f'Week {universe.current_week} Show')
        show_id = f"show_y{universe.current_year}_w{universe.current_week}"
        
        result = title_situation_manager.execute_title_decision(
            decision=TitleDecision.INTERIM_CHAMPION,
            championship=championship,
            champion=champion,
            year=universe.current_year,
            week=universe.current_week,
            show_id=show_id,
            show_name=show_name,
            new_champion=interim_champion
        )
        
        if result.success:
            log_title_situation(
                database,
                title_id=title_id,
                situation_type='interim_created',
                description=result.message,
                year=universe.current_year,
                week=universe.current_week,
                decision_made='interim_champion',
                decision_result='success'
            )
            
            cursor = database.conn.cursor()
            cursor.execute('''
                UPDATE championships 
                SET current_holder_id = ?,
                    current_holder_name = ?
                WHERE id = ?
            ''', (championship.current_holder_id, championship.current_holder_name, title_id))
            
            database.save_championship(championship)
            database.conn.commit()
        
        return jsonify({
            'success': result.success,
            'result': result.to_dict()
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@title_situation_bp.route('/api/championships/<title_id>/strip-interim', methods=['POST'])
def api_strip_interim_champion(title_id):
    database = get_database()
    universe = get_universe()
    
    try:
        from persistence.championship_db import log_title_situation
        
        data = request.get_json(silent=True) or {}
        
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        if not championship.has_interim_champion:
            return jsonify({'success': False, 'error': 'No interim champion to strip'}), 400
        
        show_name = data.get('show_name', f'Week {universe.current_week} Show')
        show_id = f"show_y{universe.current_year}_w{universe.current_week}"
        
        interim_name = championship.interim_holder_name
        
        championship.strip_interim_champion(
            show_id=show_id,
            show_name=show_name,
            year=universe.current_year,
            week=universe.current_week
        )
        
        log_title_situation(
            database,
            title_id=title_id,
            situation_type='interim_stripped',
            description=f'{interim_name} stripped as interim champion',
            year=universe.current_year,
            week=universe.current_week,
            decision_made='strip_interim',
            decision_result='success'
        )
        
        universe.save_championship(championship)
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'message': f'{interim_name} stripped as interim champion. {championship.current_holder_name} is undisputed champion.',
            'championship': championship.to_dict()
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@title_situation_bp.route('/api/championships/<title_id>/unify', methods=['POST'])
def api_unify_championship(title_id):
    database = get_database()
    universe = get_universe()
    
    try:
        from persistence.championship_db import log_title_situation
        
        data = request.get_json()
        
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        if not championship.has_interim_champion:
            return jsonify({'success': False, 'error': 'No interim champion to unify'}), 400
        
        winner_id = data.get('winner_id')
        if not winner_id:
            return jsonify({'success': False, 'error': 'winner_id required'}), 400
        
        if winner_id not in [championship.current_holder_id, championship.interim_holder_id]:
            return jsonify({
                'success': False, 
                'error': 'Winner must be either the main champion or interim champion'
            }), 400
        
        winner = universe.get_wrestler_by_id(winner_id)
        if not winner:
            return jsonify({'success': False, 'error': 'Winner not found'}), 404
        
        show_name = data.get('show_name', f'Week {universe.current_week} Show')
        show_id = f"show_y{universe.current_year}_w{universe.current_week}"
        
        loser_name = championship.interim_holder_name if winner_id == championship.current_holder_id else championship.current_holder_name
        
        championship.strip_interim_champion(show_id, show_name, universe.current_year, universe.current_week)
        
        if winner_id != championship.current_holder_id:
            championship.award_title(
                wrestler_id=winner_id,
                wrestler_name=winner.name,
                show_id=show_id,
                show_name=show_name,
                year=universe.current_year,
                week=universe.current_week,
                is_interim=False
            )
        
        log_title_situation(
            database,
            title_id=title_id,
            situation_type='title_unified',
            description=f'{winner.name} defeats {loser_name} to become undisputed champion',
            year=universe.current_year,
            week=universe.current_week,
            decision_made='unification_match',
            decision_result='success'
        )
        
        universe.save_championship(championship)
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'message': f'{winner.name} is the UNDISPUTED {championship.name}!',
            'championship': championship.to_dict()
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@title_situation_bp.route('/api/championships/<title_id>/fill-vacancy', methods=['POST'])
def api_fill_vacancy(title_id):
    database = get_database()
    universe = get_universe()
    
    try:
        from persistence.championship_db import fill_vacancy, log_title_situation
        
        data = request.get_json()
        
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        if not championship.is_vacant:
            return jsonify({'success': False, 'error': 'Championship is not vacant'}), 400
        
        new_champion_id = data.get('new_champion_id')
        if not new_champion_id:
            return jsonify({'success': False, 'error': 'new_champion_id required'}), 400
        
        new_champion = universe.get_wrestler_by_id(new_champion_id)
        if not new_champion:
            return jsonify({'success': False, 'error': 'New champion not found'}), 404
        
        show_name = data.get('show_name', f'Week {universe.current_week} Show')
        show_id = f"show_y{universe.current_year}_w{universe.current_week}"
        resolution_method = data.get('resolution_method', 'match')
        
        vacancy = universe.championship_hierarchy.get_vacancy_for_title(title_id)
        
        championship.award_title(
            wrestler_id=new_champion_id,
            wrestler_name=new_champion.name,
            show_id=show_id,
            show_name=show_name,
            year=universe.current_year,
            week=universe.current_week,
            is_interim=False
        )
        
        if vacancy:
            universe.championship_hierarchy.fill_vacancy(
                vacancy_id=vacancy.vacancy_id,
                new_champion_id=new_champion_id,
                new_champion_name=new_champion.name,
                year=universe.current_year,
                week=universe.current_week,
                show_id=show_id,
                show_name=show_name,
                resolution_method=resolution_method
            )
            
            fill_vacancy(database, vacancy.vacancy_id, {
                'filled_year': universe.current_year,
                'filled_week': universe.current_week,
                'filled_show_id': show_id,
                'filled_show_name': show_name,
                'new_champion_id': new_champion_id,
                'new_champion_name': new_champion.name,
                'weeks_vacant': vacancy.weeks_vacant,
                'resolution_method': resolution_method
            })
        
        log_title_situation(
            database,
            title_id=title_id,
            situation_type='vacancy_filled',
            description=f'{new_champion.name} wins the vacant {championship.name}',
            year=universe.current_year,
            week=universe.current_week,
            decision_made=resolution_method,
            decision_result='success'
        )
        
        universe.save_championship(championship)
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'message': f'{new_champion.name} is the NEW {championship.name}!',
            'championship': championship.to_dict()
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@title_situation_bp.route('/api/championships/<title_id>/record-defense', methods=['POST'])
def api_record_title_defense(title_id):
    database = get_database()
    universe = get_universe()
    
    try:
        from persistence.championship_db import save_defense
        
        data = request.get_json()
        
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        if championship.is_vacant:
            return jsonify({'success': False, 'error': 'Cannot record defense for vacant title'}), 400
        
        champion = universe.get_wrestler_by_id(championship.effective_champion_id)
        challenger_id = data.get('challenger_id')
        challenger = universe.get_wrestler_by_id(challenger_id)
        
        if not challenger:
            return jsonify({'success': False, 'error': 'Challenger not found'}), 404
        
        show_name = data.get('show_name', f'Week {universe.current_week} Show')
        show_id = f"show_y{universe.current_year}_w{universe.current_week}"
        
        defense = universe.championship_hierarchy.record_defense(
            title_id=title_id,
            champion_id=champion.id,
            champion_name=champion.name,
            challenger_id=challenger_id,
            challenger_name=challenger.name,
            show_id=show_id,
            show_name=show_name,
            year=universe.current_year,
            week=universe.current_week,
            is_ppv=data.get('is_ppv', False),
            result=data.get('result', 'retained'),
            finish_type=data.get('finish_type', 'clean_pin'),
            star_rating=data.get('star_rating', 3.0),
            duration_minutes=data.get('duration_minutes', 15)
        )
        
        championship.record_successful_defense(
            year=universe.current_year,
            week=universe.current_week,
            show_id=show_id
        )
        
        star_rating = data.get('star_rating', 3.0)
        if star_rating >= 4.5:
            championship.adjust_prestige(5)
        elif star_rating >= 4.0:
            championship.adjust_prestige(3)
        elif star_rating >= 3.5:
            championship.adjust_prestige(1)
        elif star_rating < 2.5:
            championship.adjust_prestige(-2)
        
        save_defense(database, defense.to_dict())
        universe.save_championship(championship)
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'message': f'Defense recorded: {champion.name} vs {challenger.name}',
            'defense': defense.to_dict(),
            'championship': championship.to_dict()
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@title_situation_bp.route('/api/championships/<title_id>/vacancies')
def api_get_title_vacancies(title_id):
    database = get_database()
    universe = get_universe()
    
    try:
        from persistence.championship_db import get_title_vacancies
        
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        vacancies = get_title_vacancies(database, title_id)
        
        return jsonify({
            'success': True,
            'title_id': title_id,
            'title_name': championship.name,
            'total': len(vacancies),
            'vacancies': vacancies
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@title_situation_bp.route('/api/championships/<title_id>/guaranteed-shots')
def api_get_title_guaranteed_shots(title_id):
    database = get_database()
    universe = get_universe()
    
    try:
        from persistence.championship_db import get_active_shots_for_title
        
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        active_shots = get_active_shots_for_title(
            database, title_id, universe.current_year, universe.current_week
        )
        
        return jsonify({
            'success': True,
            'title_id': title_id,
            'title_name': championship.name,
            'active_shots': active_shots
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@title_situation_bp.route('/api/championships/<title_id>/situation-log')
def api_get_title_situation_log(title_id):
    database = get_database()
    universe = get_universe()
    
    try:
        from persistence.championship_db import get_title_situation_log
        
        limit = request.args.get('limit', 20, type=int)
        
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        log = get_title_situation_log(database, title_id, limit)
        
        return jsonify({
            'success': True,
            'title_id': title_id,
            'title_name': championship.name,
            'log': log
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@title_situation_bp.route('/api/championships/<title_id>/interim-candidates')
def api_get_interim_candidates(title_id):
    universe = get_universe()
    
    try:
        from creative.title_situations import title_situation_manager
        
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        roster = universe.get_active_wrestlers()
        
        candidates = title_situation_manager.get_interim_champion_candidates(
            championship=championship,
            roster=roster
        )
        
        return jsonify({
            'success': True,
            'title_id': title_id,
            'title_name': championship.name,
            'candidates': candidates
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@title_situation_bp.route('/api/championships/vacancies')
def api_get_all_active_vacancies():
    database = get_database()
    
    try:
        from persistence.championship_db import get_all_active_vacancies
        
        vacancies = get_all_active_vacancies(database)
        
        return jsonify({
            'success': True,
            'total': len(vacancies),
            'vacancies': vacancies
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@title_situation_bp.route('/api/wrestlers/<wrestler_id>/guaranteed-shots')
def api_get_wrestler_guaranteed_shots(wrestler_id):
    database = get_database()
    universe = get_universe()
    
    try:
        from persistence.championship_db import get_wrestler_shots
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'success': False, 'error': 'Wrestler not found'}), 404
        
        all_shots = get_wrestler_shots(database, wrestler_id, active_only=False)
        active_shots = get_wrestler_shots(database, wrestler_id, active_only=True)
        
        return jsonify({
            'success': True,
            'wrestler_id': wrestler_id,
            'wrestler_name': wrestler.name,
            'active_shots': active_shots,
            'all_shots': all_shots
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@title_situation_bp.route('/api/wrestlers/<wrestler_id>/grant-title-shot', methods=['POST'])
def api_grant_title_shot(wrestler_id):
    database = get_database()
    universe = get_universe()
    
    try:
        from persistence.championship_db import save_guaranteed_shot
        
        data = request.get_json()
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'success': False, 'error': 'Wrestler not found'}), 404
        
        title_id = data.get('title_id')
        if not title_id:
            return jsonify({'success': False, 'error': 'title_id required'}), 400
        
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        reason = data.get('reason', 'storyline')
        expires_weeks = data.get('expires_weeks', 52)
        
        expires_year = universe.current_year
        expires_week = universe.current_week + expires_weeks
        while expires_week > 52:
            expires_week -= 52
            expires_year += 1
        
        shot = universe.championship_hierarchy.grant_title_shot(
            wrestler_id=wrestler_id,
            wrestler_name=wrestler.name,
            title_id=title_id,
            title_name=championship.name,
            reason=reason,
            year=universe.current_year,
            week=universe.current_week,
            expires_year=expires_year,
            expires_week=expires_week,
            notes=data.get('notes', '')
        )
        
        save_guaranteed_shot(database, shot.to_dict())
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'message': f'{wrestler.name} granted a {championship.name} title shot',
            'shot': shot.to_dict()
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500