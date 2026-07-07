"""
Market Value Routes - Market Value Calculation (Step 116)
"""

from flask import Blueprint, jsonify, request, current_app
import traceback

market_value_bp = Blueprint('market_value', __name__)


def get_database():
    return current_app.config['DATABASE']


def get_universe():
    return current_app.config['UNIVERSE']


def get_free_agent_pool():
    return current_app.config.get('FREE_AGENT_POOL')


@market_value_bp.route('/api/market-value/wrestler/<wrestler_id>')
def api_wrestler_market_value(wrestler_id):
    universe = get_universe()
    
    wrestler = universe.get_wrestler_by_id(wrestler_id)
    
    if not wrestler:
        return jsonify({'error': 'Wrestler not found'}), 404
    
    try:
        from economy.market_value import market_value_calculator, MarketValueFactors
        
        factors = MarketValueFactors(
            base_value=wrestler.contract.salary_per_show,
            current_popularity=wrestler.popularity,
            peak_popularity=getattr(wrestler, 'peak_popularity', wrestler.popularity),
            popularity_trend=0,
            average_match_rating=3.0,
            recent_match_rating=3.0,
            five_star_match_count=0,
            four_plus_match_count=0,
            age=wrestler.age,
            years_experience=wrestler.years_experience,
            role=wrestler.role,
            is_major_superstar=wrestler.is_major_superstar,
            is_legend=False,
            current_injury_severity=0 if not wrestler.is_injured else 2,
            injury_history_count=0,
            months_since_last_injury=12,
            has_chronic_issues=False,
            backstage_reputation=wrestler.morale,
            locker_room_leader=wrestler.is_major_superstar and wrestler.years_experience >= 10,
            known_difficult=wrestler.morale < 30,
            controversy_severity=0,
            rival_promotion_interest=0,
            highest_rival_offer=0,
            bidding_war_active=False,
            weeks_unemployed=0,
            mood='patient'
        )
        
        market_value, breakdown = market_value_calculator.calculate_market_value(factors)
        
        return jsonify({
            'success': True,
            'wrestler_id': wrestler.id,
            'wrestler_name': wrestler.name,
            'market_value': market_value,
            'current_salary': wrestler.contract.salary_per_show,
            'difference': market_value - wrestler.contract.salary_per_show,
            'difference_percent': ((market_value - wrestler.contract.salary_per_show) / wrestler.contract.salary_per_show * 100) if wrestler.contract.salary_per_show > 0 else 0,
            'breakdown': breakdown.to_dict() if breakdown else None
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@market_value_bp.route('/api/market-value/free-agent/<free_agent_id>')
def api_free_agent_market_value(free_agent_id):
    universe = get_universe()
    free_agent_pool = get_free_agent_pool()
    
    try:
        fa = free_agent_pool.get_free_agent_by_id(free_agent_id)
        
        if not fa:
            return jsonify({'error': 'Free agent not found'}), 404
        
        market_value, breakdown = fa.calculate_comprehensive_market_value(
            year=universe.current_year,
            week=universe.current_week,
            include_breakdown=True
        )
        
        return jsonify({
            'success': True,
            'free_agent_id': fa.id,
            'wrestler_name': fa.wrestler_name,
            'market_value': market_value,
            'asking_salary': fa.demands.asking_salary,
            'minimum_salary': fa.demands.minimum_salary,
            'mood': fa.mood_label,
            'weeks_unemployed': fa.weeks_unemployed,
            'market_trend': fa.market_value_trend,
            'breakdown': breakdown.to_dict() if breakdown else None,
            'value_history': [h.to_dict() for h in fa.market_value_history[-12:]]
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@market_value_bp.route('/api/market-value/free-agent/<free_agent_id>/recalculate', methods=['POST'])
def api_recalculate_free_agent_market_value(free_agent_id):
    database = get_database()
    universe = get_universe()
    free_agent_pool = get_free_agent_pool()
    
    try:
        fa = free_agent_pool.get_free_agent_by_id(free_agent_id)
        
        if not fa:
            return jsonify({'error': 'Free agent not found'}), 404
        
        old_value = fa.market_value
        
        new_value, breakdown = fa.calculate_comprehensive_market_value(
            year=universe.current_year,
            week=universe.current_week,
            include_breakdown=True
        )
        
        try:
            cursor = database.conn.cursor()
            cursor.execute('''
                UPDATE free_agents 
                SET market_value = ?, 
                    updated_at = ?,
                    mood = ?,
                    weeks_unemployed = ?
                WHERE id = ?
            ''', (
                fa.market_value,
                fa.updated_at,
                fa.mood.value if hasattr(fa.mood, 'value') else fa.mood,
                fa.weeks_unemployed,
                fa.id
            ))
            database.conn.commit()
        except Exception as save_error:
            print(f"Warning: Could not save free agent: {save_error}")
        
        return jsonify({
            'success': True,
            'free_agent_id': fa.id,
            'wrestler_name': fa.wrestler_name,
            'old_value': old_value,
            'new_value': new_value,
            'change': new_value - old_value,
            'change_percent': ((new_value - old_value) / old_value * 100) if old_value > 0 else 0,
            'breakdown': breakdown.to_dict() if breakdown else None
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@market_value_bp.route('/api/market-value/bulk-recalculate', methods=['POST'])
def api_bulk_recalculate_market_values():
    database = get_database()
    universe = get_universe()
    free_agent_pool = get_free_agent_pool()
    
    try:
        results = []
        updated_count = 0
        
        for fa in free_agent_pool.available_free_agents:
            old_value = fa.market_value
            
            new_value, _ = fa.calculate_comprehensive_market_value(
                year=universe.current_year,
                week=universe.current_week,
                include_breakdown=False
            )
            
            try:
                cursor = database.conn.cursor()
                cursor.execute('''
                    UPDATE free_agents 
                    SET market_value = ?, 
                        updated_at = ?,
                        mood = ?,
                        weeks_unemployed = ?
                    WHERE id = ?
                ''', (
                    fa.market_value,
                    fa.updated_at,
                    fa.mood.value if hasattr(fa.mood, 'value') else fa.mood,
                    fa.weeks_unemployed,
                    fa.id
                ))
            except Exception as save_error:
                print(f"Warning: Could not save free agent {fa.id}: {save_error}")
            
            results.append({
                'free_agent_id': fa.id,
                'wrestler_name': fa.wrestler_name,
                'old_value': old_value,
                'new_value': new_value,
                'change': new_value - old_value
            })
            
            updated_count += 1
        
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'updated_count': updated_count,
            'results': results
        })
        
    except Exception as e:
        traceback.print_exc()
        try:
            database.conn.rollback()
        except:
            pass
        return jsonify({'error': str(e)}), 500


@market_value_bp.route('/api/market-value/compare', methods=['POST'])
def api_compare_market_values():
    universe = get_universe()
    free_agent_pool = get_free_agent_pool()
    
    try:
        from economy.market_value import market_value_calculator
        
        data = request.get_json()
        wrestler_ids = data.get('wrestler_ids', [])
        free_agent_ids = data.get('free_agent_ids', [])
        
        comparisons = []
        
        for wid in wrestler_ids:
            wrestler = universe.get_wrestler_by_id(wid)
            if wrestler:
                estimate = market_value_calculator.get_quick_estimate(
                    popularity=wrestler.popularity,
                    role=wrestler.role,
                    age=wrestler.age,
                    is_major_superstar=wrestler.is_major_superstar
                )
                
                comparisons.append({
                    'type': 'wrestler',
                    'id': wrestler.id,
                    'name': wrestler.name,
                    'market_value': estimate,
                    'current_salary': wrestler.contract.salary_per_show,
                    'popularity': wrestler.popularity,
                    'role': wrestler.role,
                    'age': wrestler.age
                })
        
        for faid in free_agent_ids:
            fa = free_agent_pool.get_free_agent_by_id(faid)
            if fa:
                comparisons.append({
                    'type': 'free_agent',
                    'id': fa.id,
                    'name': fa.wrestler_name,
                    'market_value': fa.market_value,
                    'asking_salary': fa.demands.asking_salary,
                    'popularity': fa.popularity,
                    'role': fa.role,
                    'age': fa.age,
                    'mood': fa.mood_label,
                    'weeks_unemployed': fa.weeks_unemployed
                })
        
        comparisons.sort(key=lambda x: x['market_value'], reverse=True)
        
        return jsonify({
            'success': True,
            'count': len(comparisons),
            'comparisons': comparisons
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@market_value_bp.route('/api/market-value/quick-estimate', methods=['POST'])
def api_quick_market_value_estimate():
    try:
        from economy.market_value import market_value_calculator
        
        data = request.get_json()
        
        popularity = data.get('popularity', 50)
        role = data.get('role', 'Midcard')
        age = data.get('age', 30)
        is_major_superstar = data.get('is_major_superstar', False)
        
        estimate = market_value_calculator.get_quick_estimate(
            popularity=popularity,
            role=role,
            age=age,
            is_major_superstar=is_major_superstar
        )
        
        return jsonify({
            'success': True,
            'estimate': estimate,
            'inputs': {
                'popularity': popularity,
                'role': role,
                'age': age,
                'is_major_superstar': is_major_superstar
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@market_value_bp.route('/api/market-value/full-calculation', methods=['POST'])
def api_full_market_value_calculation():
    try:
        from economy.market_value import market_value_calculator, MarketValueFactors
        
        data = request.get_json()
        
        factors = MarketValueFactors(
            current_popularity=data.get('current_popularity', 50),
            peak_popularity=data.get('peak_popularity', data.get('current_popularity', 50)),
            popularity_trend=data.get('popularity_trend', 0),
            average_match_rating=data.get('average_match_rating', 3.0),
            recent_match_rating=data.get('recent_match_rating', 3.0),
            five_star_match_count=data.get('five_star_match_count', 0),
            four_plus_match_count=data.get('four_plus_match_count', 0),
            age=data.get('age', 30),
            years_experience=data.get('years_experience', 5),
            role=data.get('role', 'Midcard'),
            is_major_superstar=data.get('is_major_superstar', False),
            is_legend=data.get('is_legend', False),
            injury_history_count=data.get('injury_history_count', 0),
            months_since_last_injury=data.get('months_since_last_injury', 12),
            has_chronic_issues=data.get('has_chronic_issues', False),
            backstage_reputation=data.get('backstage_reputation', 50),
            locker_room_leader=data.get('locker_room_leader', False),
            known_difficult=data.get('known_difficult', False),
            controversy_severity=data.get('controversy_severity', 0),
            rival_promotion_interest=data.get('rival_promotion_interest', 0),
            highest_rival_offer=data.get('highest_rival_offer', 0),
            bidding_war_active=data.get('bidding_war_active', False),
            weeks_unemployed=data.get('weeks_unemployed', 0),
            mood=data.get('mood', 'patient')
        )
        
        value, breakdown = market_value_calculator.calculate_market_value(factors)
        
        return jsonify({
            'success': True,
            'market_value': value,
            'breakdown': breakdown.to_dict(),
            'factors': factors.to_dict()
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@market_value_bp.route('/api/market-value/market-trend')
def api_get_market_trend():
    try:
        from economy.market_value import market_value_calculator, MarketTrend
        
        return jsonify({
            'success': True,
            'current_trend': market_value_calculator._market_trend.value,
            'available_trends': [t.value for t in MarketTrend]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@market_value_bp.route('/api/market-value/market-trend', methods=['POST'])
def api_set_market_trend():
    try:
        from economy.market_value import market_value_calculator, MarketTrend
        
        data = request.get_json()
        trend_str = data.get('trend', 'balanced')
        
        try:
            trend = MarketTrend(trend_str)
        except ValueError:
            return jsonify({
                'success': False,
                'error': f'Invalid trend. Must be one of: {[t.value for t in MarketTrend]}'
            }), 400
        
        market_value_calculator.set_market_trend(trend)
        
        return jsonify({
            'success': True,
            'message': f'Market trend set to {trend.value}',
            'new_trend': trend.value
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@market_value_bp.route('/api/free-agents/top-values')
def api_get_top_market_values():
    free_agent_pool = get_free_agent_pool()
    
    try:
        limit = request.args.get('limit', 10, type=int)
        discovered_only = request.args.get('discovered_only', 'true').lower() == 'true'
        
        if discovered_only:
            agents = free_agent_pool.get_discovered_free_agents()
        else:
            agents = free_agent_pool.available_free_agents
        
        sorted_agents = sorted(agents, key=lambda fa: fa.market_value, reverse=True)[:limit]
        
        return jsonify({
            'success': True,
            'total': len(sorted_agents),
            'free_agents': [{
                'id': fa.id,
                'name': fa.wrestler_name,
                'role': fa.role,
                'market_value': fa.market_value,
                'asking_salary': fa.demands.asking_salary,
                'popularity': fa.popularity,
                'age': fa.age,
                'mood': fa.mood_label,
                'trend': fa.market_value_trend
            } for fa in sorted_agents]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@market_value_bp.route('/api/free-agents/bargains')
def api_get_bargain_free_agents():
    free_agent_pool = get_free_agent_pool()
    
    try:
        from economy.market_value import market_value_calculator
        from models.free_agent import FreeAgentMood
        
        limit = request.args.get('limit', 10, type=int)
        
        agents = free_agent_pool.get_discovered_free_agents()
        
        bargains = []
        for fa in agents:
            quick_estimate = market_value_calculator.get_quick_estimate(
                popularity=fa.popularity,
                role=fa.role,
                age=fa.age,
                is_major_superstar=fa.is_major_superstar
            )
            
            discount = ((quick_estimate - fa.demands.asking_salary) / max(quick_estimate, 1)) * 100
            
            if discount > 15:
                bargains.append({
                    'free_agent': fa,
                    'estimated_value': quick_estimate,
                    'asking_salary': fa.demands.asking_salary,
                    'discount_percent': round(discount, 1),
                    'reason': fa.mood_label if fa.mood in [FreeAgentMood.DESPERATE, FreeAgentMood.HUNGRY] else 'Undervalued'
                })
        
        bargains.sort(key=lambda x: x['discount_percent'], reverse=True)
        bargains = bargains[:limit]
        
        return jsonify({
            'success': True,
            'total': len(bargains),
            'bargains': [{
                'id': b['free_agent'].id,
                'name': b['free_agent'].wrestler_name,
                'role': b['free_agent'].role,
                'estimated_value': b['estimated_value'],
                'asking_salary': b['asking_salary'],
                'discount_percent': b['discount_percent'],
                'reason': b['reason'],
                'mood': b['free_agent'].mood_label,
                'weeks_unemployed': b['free_agent'].weeks_unemployed
            } for b in bargains]
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500