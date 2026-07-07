"""
Stats Routes - Statistics & Records (Step 11)
"""

from flask import Blueprint, jsonify, request, current_app
import traceback

stats_bp = Blueprint('stats', __name__)


def get_database():
    return current_app.config['DATABASE']


def get_universe():
    return current_app.config['UNIVERSE']


@stats_bp.route('/api/stats/wrestler/<wrestler_id>')
def api_get_wrestler_stats(wrestler_id):
    database = get_database()
    
    try:
        stats = database.calculate_wrestler_stats(wrestler_id)
        
        if not stats:
            return jsonify({'error': 'Wrestler not found or no stats available'}), 404
        
        milestones = database.get_wrestler_milestones(wrestler_id)
        
        return jsonify({
            'success': True,
            'stats': stats,
            'milestones': milestones
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@stats_bp.route('/api/stats/wrestler/<wrestler_id>/matches')
def api_get_wrestler_match_history(wrestler_id):
    database = get_database()
    limit = request.args.get('limit', 20, type=int)
    
    try:
        matches = database.get_match_history(wrestler_id=wrestler_id, limit=limit)
        
        for match in matches:
            side_a_ids = match['side_a_ids']
            side_b_ids = match['side_b_ids']
            
            on_side_a = wrestler_id in side_a_ids
            winner = match['winner']
            
            if winner == 'draw':
                match['result'] = 'DRAW'
                match['result_class'] = 'text-secondary'
            elif (winner == 'side_a' and on_side_a) or (winner == 'side_b' and not on_side_a):
                match['result'] = 'WIN'
                match['result_class'] = 'text-success'
            else:
                match['result'] = 'LOSS'
                match['result_class'] = 'text-danger'
        
        return jsonify({
            'success': True,
            'total': len(matches),
            'matches': matches
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@stats_bp.route('/api/stats/promotion/records')
def api_get_promotion_records():
    database = get_database()
    
    try:
        records = database.get_promotion_records()
        
        return jsonify({
            'success': True,
            'records': records
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@stats_bp.route('/api/stats/milestones/recent')
def api_get_recent_milestones():
    database = get_database()
    limit = request.args.get('limit', 10, type=int)
    
    try:
        milestones = database.get_recent_milestones(limit=limit)
        
        return jsonify({
            'success': True,
            'total': len(milestones),
            'milestones': milestones
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@stats_bp.route('/api/stats/leaderboard/<stat_type>')
def api_get_leaderboard(stat_type):
    database = get_database()
    limit = request.args.get('limit', 10, type=int)
    
    try:
        cursor = database.conn.cursor()
        
        if stat_type == 'wins':
            cursor.execute('''
                SELECT ws.*, w.name, w.primary_brand, w.role
                FROM wrestler_stats ws
                JOIN wrestlers w ON ws.wrestler_id = w.id
                WHERE w.is_retired = 0
                ORDER BY ws.wins DESC
                LIMIT ?
            ''', (limit,))
        
        elif stat_type == 'matches':
            cursor.execute('''
                SELECT ws.*, w.name, w.primary_brand, w.role
                FROM wrestler_stats ws
                JOIN wrestlers w ON ws.wrestler_id = w.id
                WHERE w.is_retired = 0
                ORDER BY ws.total_matches DESC
                LIMIT ?
            ''', (limit,))
        
        elif stat_type == 'win_percentage':
            cursor.execute('''
                SELECT ws.*, w.name, w.primary_brand, w.role,
                       (CAST(ws.wins AS FLOAT) / ws.total_matches * 100) as win_pct
                FROM wrestler_stats ws
                JOIN wrestlers w ON ws.wrestler_id = w.id
                WHERE w.is_retired = 0 AND ws.total_matches >= 5
                ORDER BY win_pct DESC
                LIMIT ?
            ''', (limit,))
        
        elif stat_type == 'title_reigns':
            cursor.execute('''
                SELECT ws.*, w.name, w.primary_brand, w.role
                FROM wrestler_stats ws
                JOIN wrestlers w ON ws.wrestler_id = w.id
                WHERE w.is_retired = 0
                ORDER BY ws.total_title_reigns DESC
                LIMIT ?
            ''', (limit,))
        
        elif stat_type == 'star_rating':
            cursor.execute('''
                SELECT ws.*, w.name, w.primary_brand, w.role,
                       (ws.total_star_rating / ws.total_matches) as avg_rating
                FROM wrestler_stats ws
                JOIN wrestlers w ON ws.wrestler_id = w.id
                WHERE w.is_retired = 0 AND ws.total_matches >= 5
                ORDER BY avg_rating DESC
                LIMIT ?
            ''', (limit,))
        
        else:
            return jsonify({'error': 'Invalid stat_type'}), 400
        
        rows = cursor.fetchall()
        leaderboard = [dict(row) for row in rows]
        
        return jsonify({
            'success': True,
            'stat_type': stat_type,
            'leaderboard': leaderboard
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@stats_bp.route('/api/stats/championship/<title_id>')
def api_get_championship_stats(title_id):
    database = get_database()
    
    try:
        cursor = database.conn.cursor()
        
        cursor.execute('SELECT * FROM championships WHERE id = ?', (title_id,))
        title_row = cursor.fetchone()
        
        if not title_row:
            return jsonify({'error': 'Championship not found'}), 404
        
        title = dict(title_row)
        
        cursor.execute('''
            SELECT * FROM title_reigns
            WHERE title_id = ?
            ORDER BY won_date_year DESC, won_date_week DESC
        ''', (title_id,))
        
        reigns = [dict(row) for row in cursor.fetchall()]
        
        total_reigns = len(reigns)
        completed_reigns = [r for r in reigns if r['lost_at_show_id'] is not None]
        
        stats = {
            'title': title,
            'total_reigns': total_reigns,
            'total_defenses': 0,
            'unique_champions': len(set(r['wrestler_id'] for r in reigns)),
            'longest_reign': max(completed_reigns, key=lambda r: r['days_held']) if completed_reigns else None,
            'shortest_reign': min(completed_reigns, key=lambda r: r['days_held']) if completed_reigns else None,
            'average_reign_length': sum(r['days_held'] for r in completed_reigns) / len(completed_reigns) if completed_reigns else 0,
            'current_reign': reigns[0] if reigns and reigns[0]['lost_at_show_id'] is None else None,
            'recent_reigns': reigns[:5]
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@stats_bp.route('/api/stats/update-all', methods=['POST'])
def api_update_all_stats():
    database = get_database()
    universe = get_universe()
    
    try:
        print("🔄 Recalculating all wrestler stats...")
        
        wrestlers = universe.wrestlers
        
        for wrestler in wrestlers:
            database.update_wrestler_stats_cache(wrestler.id)
        
        database.conn.commit()
        
        print(f"✅ Updated stats for {len(wrestlers)} wrestlers")
        
        return jsonify({
            'success': True,
            'message': f'Updated stats for {len(wrestlers)} wrestlers'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@stats_bp.route('/api/stats/financial-summary')
def api_financial_summary():
    database = get_database()
    universe = get_universe()
    
    try:
        show_history = database.get_show_history(limit=100)
        
        total_revenue = sum(show['total_revenue'] for show in show_history)
        total_payroll = sum(show['total_payroll'] for show in show_history)
        total_profit = sum(show['net_profit'] for show in show_history)
        
        if show_history:
            avg_revenue = total_revenue / len(show_history)
            avg_payroll = total_payroll / len(show_history)
            avg_profit = total_profit / len(show_history)
            avg_attendance = sum(show['total_attendance'] for show in show_history) / len(show_history)
            avg_rating = sum(show['overall_rating'] for show in show_history) / len(show_history)
        else:
            avg_revenue = avg_payroll = avg_profit = avg_attendance = avg_rating = 0
        
        breakdown = {}
        for show in show_history:
            show_type = show['show_type']
            if show_type not in breakdown:
                breakdown[show_type] = {
                    'count': 0,
                    'total_revenue': 0,
                    'total_expenses': 0,
                    'total_profit': 0,
                    'total_rating': 0
                }
            
            breakdown[show_type]['count'] += 1
            breakdown[show_type]['total_revenue'] += show['total_revenue']
            breakdown[show_type]['total_expenses'] += (show['total_revenue'] - show['net_profit'])
            breakdown[show_type]['total_profit'] += show['net_profit']
            breakdown[show_type]['total_rating'] += show['overall_rating']
        
        for show_type in breakdown:
            count = breakdown[show_type]['count']
            breakdown[show_type]['avg_revenue'] = breakdown[show_type]['total_revenue'] / count
            breakdown[show_type]['avg_expenses'] = breakdown[show_type]['total_expenses'] / count
            breakdown[show_type]['avg_profit'] = breakdown[show_type]['total_profit'] / count
            breakdown[show_type]['avg_rating'] = breakdown[show_type]['total_rating'] / count
        
        return jsonify({
            'total_shows': len(show_history),
            'total_revenue': total_revenue,
            'total_payroll': total_payroll,
            'total_profit': total_profit,
            'avg_revenue': avg_revenue,
            'avg_payroll': avg_payroll,
            'avg_profit': avg_profit,
            'avg_attendance': avg_attendance,
            'avg_rating': avg_rating,
            'breakdown_by_type': breakdown,
            'current_balance': universe.balance
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@stats_bp.route('/api/stats/populate-initial', methods=['POST'])
def api_populate_initial_stats():
    database = get_database()
    universe = get_universe()
    
    try:
        print("📊 Populating initial statistics...")
        
        wrestlers = universe.wrestlers
        populated_count = 0
        milestone_count = 0
        
        for wrestler in wrestlers:
            stats_dict = database.calculate_wrestler_stats(wrestler.id)
            
            if stats_dict and stats_dict['record']['total_matches'] > 0:
                database.update_wrestler_stats_cache(wrestler.id)
                populated_count += 1
                
                cursor = database.conn.cursor()
                cursor.execute('''
                    SELECT * FROM match_history
                    WHERE side_a_ids LIKE ? OR side_b_ids LIKE ?
                    ORDER BY year, week, id
                    LIMIT 1
                ''', (f'%{wrestler.id}%', f'%{wrestler.id}%'))
                
                first_match = cursor.fetchone()
                
                if first_match:
                    existing_milestones = database.get_wrestler_milestones(wrestler.id)
                    existing_types = {m['milestone_type'] for m in existing_milestones}
                    
                    if 'debut' not in existing_types:
                        database.record_milestone(
                            wrestler_id=wrestler.id,
                            wrestler_name=wrestler.name,
                            milestone_type='debut',
                            description=f"{wrestler.name} made their in-ring debut!",
                            show_id=first_match['show_id'],
                            show_name=first_match['show_name'],
                            year=first_match['year'],
                            week=first_match['week']
                        )
                        milestone_count += 1
                    
                    if stats_dict['record']['wins'] > 0 and 'first_win' not in existing_types:
                        cursor.execute('''
                            SELECT * FROM match_history
                            WHERE (side_a_ids LIKE ? AND winner = 'side_a')
                               OR (side_b_ids LIKE ? AND winner = 'side_b')
                            ORDER BY year, week, id
                            LIMIT 1
                        ''', (f'%{wrestler.id}%', f'%{wrestler.id}%'))
                        
                        first_win = cursor.fetchone()
                        if first_win:
                            database.record_milestone(
                                wrestler_id=wrestler.id,
                                wrestler_name=wrestler.name,
                                milestone_type='first_win',
                                description=f"{wrestler.name} earned their first victory!",
                                show_id=first_win['show_id'],
                                show_name=first_win['show_name'],
                                year=first_win['year'],
                                week=first_win['week']
                            )
                            milestone_count += 1
        
        database.conn.commit()
        
        print(f"✅ Populated stats for {populated_count} wrestlers")
        print(f"✅ Created {milestone_count} milestone records")
        
        return jsonify({
            'success': True,
            'message': f'Populated stats for {populated_count} wrestlers, created {milestone_count} milestones',
            'wrestlers_processed': len(wrestlers),
            'stats_populated': populated_count,
            'milestones_created': milestone_count
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500