"""
Debug Routes - Debug & Testing Endpoints
"""

from flask import Blueprint, jsonify, request, current_app
import traceback
import os

debug_bp = Blueprint('debug', __name__)


def get_database():
    return current_app.config['DATABASE']


def get_universe():
    return current_app.config['UNIVERSE']


def get_free_agent_pool():
    return current_app.config.get('FREE_AGENT_POOL')


def get_data_dir():
    return current_app.config.get('DATA_DIR')


@debug_bp.route('/api/debug/fix-game-state', methods=['POST'])
def api_debug_fix_game_state():
    database = get_database()
    universe = get_universe()
    
    try:
        universe.sync_calendar_from_state()
        
        current_show = universe.calendar.get_current_show()
        
        if current_show:
            database.update_game_state(
                current_year=current_show.year,
                current_week=current_show.week,
                current_show_index=universe.calendar.current_show_index
            )
            
            return jsonify({
                'success': True,
                'message': 'Game state fixed',
                'year': current_show.year,
                'week': current_show.week,
                'show_index': universe.calendar.current_show_index
            })
        else:
            return jsonify({'success': False, 'error': 'No current show found'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@debug_bp.route('/api/debug/show-history-raw')
def api_debug_show_history():
    database = get_database()
    
    try:
        cursor = database.conn.cursor()
        cursor.execute('SELECT COUNT(*) as count FROM show_history')
        count = cursor.fetchone()['count']
        
        cursor.execute('SELECT * FROM show_history ORDER BY id DESC LIMIT 5')
        recent = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({
            'total_shows_in_db': count,
            'recent_shows': recent
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@debug_bp.route('/api/debug/create-stats-tables', methods=['POST'])
def api_debug_create_stats_tables():
    database = get_database()
    
    try:
        database._create_stats_tables()
        
        cursor = database.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name='wrestler_stats' OR name='milestones')")
        tables = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({
            'success': True,
            'message': 'Stats tables created',
            'tables': tables
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@debug_bp.route('/api/debug/recreate-stats-tables', methods=['POST'])
def api_debug_recreate_stats_tables():
    database = get_database()
    
    try:
        cursor = database.conn.cursor()
        
        print("🗑️ Dropping old tables...")
        cursor.execute('DROP TABLE IF EXISTS wrestler_stats')
        cursor.execute('DROP TABLE IF EXISTS milestones')
        database.conn.commit()
        
        print("📊 Creating new tables with full schema...")
        database._create_stats_tables()
        
        cursor.execute("PRAGMA table_info(wrestler_stats)")
        columns = [row[1] for row in cursor.fetchall()]
        
        return jsonify({
            'success': True,
            'message': 'Tables recreated with correct schema',
            'columns': columns
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@debug_bp.route('/api/debug/load-initial-free-agents', methods=['POST'])
def api_debug_load_initial_free_agents():
    database = get_database()
    data_dir = get_data_dir()
    
    try:
        from persistence.initial_free_agents import load_initial_free_agents
        
        count = load_initial_free_agents(database, data_dir)
        
        return jsonify({
            'success': True,
            'message': f'Loaded {count} free agents',
            'count': count
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@debug_bp.route('/api/debug/free-agent-db-check')
def api_debug_free_agent_db_check():
    database = get_database()
    data_dir = get_data_dir()
    
    try:
        cursor = database.conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='free_agents'")
        table_exists = cursor.fetchone() is not None
        
        if table_exists:
            cursor.execute('SELECT COUNT(*) as count FROM free_agents')
            count = cursor.fetchone()['count']
            
            cursor.execute('SELECT id, wrestler_name, is_signed FROM free_agents LIMIT 10')
            rows = [dict(row) for row in cursor.fetchall()]
        else:
            count = 0
            rows = []
        
        import json
        json_path = os.path.join(data_dir, 'initial_free_agents.json')
        file_exists = os.path.exists(json_path)
        
        if file_exists:
            with open(json_path, 'r') as f:
                data = json.load(f)
                json_count = len(data.get('free_agents', []))
        else:
            json_count = 0
        
        return jsonify({
            'table_exists': table_exists,
            'db_count': count,
            'db_rows': rows,
            'json_file_exists': file_exists,
            'json_file_path': json_path,
            'json_count': json_count
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@debug_bp.route('/api/debug/free-agent-status')
def api_debug_free_agent_status():
    database = get_database()
    free_agent_pool = get_free_agent_pool()
    
    try:
        cursor = database.conn.cursor()
        cursor.execute('SELECT id, wrestler_name, discovered, visibility, is_signed FROM free_agents')
        db_agents = [dict(row) for row in cursor.fetchall()]
        
        pool_agents = [fa.to_dict() for fa in free_agent_pool.available_free_agents]
        discovered_agents = [fa.to_dict() for fa in free_agent_pool.get_discovered_free_agents()]
        
        return jsonify({
            'db_count': len(db_agents),
            'db_agents': db_agents,
            'pool_manager_count': len(pool_agents),
            'discovered_count': len(discovered_agents),
            'pool_manager_loaded': len(free_agent_pool._free_agents)
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@debug_bp.route('/api/debug/reload-free-agent-pool', methods=['POST'])
def api_debug_reload_free_agent_pool():
    database = get_database()
    
    try:
        from economy.free_agent_pool import FreeAgentPoolManager
        
        free_agent_pool = FreeAgentPoolManager(database)
        current_app.config['FREE_AGENT_POOL'] = free_agent_pool
        
        return jsonify({
            'success': True,
            'message': 'Pool manager reloaded',
            'total_loaded': len(free_agent_pool._free_agents),
            'available': len(free_agent_pool.available_free_agents),
            'discovered': len(free_agent_pool.get_discovered_free_agents())
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


# ============================================================================
# DEFENSE FREQUENCY DEBUG ROUTES
# ============================================================================

@debug_bp.route('/api/test/defense-frequency/simulate-overdue', methods=['POST'])
def api_test_simulate_overdue_defense():
    database = get_database()
    universe = get_universe()
    
    try:
        data = request.get_json()
        title_id = data.get('title_id')
        days_overdue = data.get('days_overdue', 10)
        
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        if championship.is_vacant:
            return jsonify({'success': False, 'error': 'Championship is vacant'}), 400
        
        weeks_ago = ((championship.defense_frequency_days + days_overdue) // 7) + 1
        
        past_year = universe.current_year
        past_week = universe.current_week - weeks_ago
        
        while past_week < 1:
            past_week += 52
            past_year -= 1
        
        championship.last_defense_year = past_year
        championship.last_defense_week = past_week
        championship.last_defense_show_id = f"test_show_y{past_year}_w{past_week}"
        
        universe.save_championship(championship)
        database.conn.commit()
        
        status = championship.get_defense_status(
            universe.current_year,
            universe.current_week
        )
        
        return jsonify({
            'success': True,
            'message': f'Championship {championship.name} now has overdue defense',
            'championship': {
                'id': championship.id,
                'name': championship.name
            },
            'last_defense': {
                'year': past_year,
                'week': past_week
            },
            'status': status
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@debug_bp.route('/api/test/defense-frequency/reset', methods=['POST'])
def api_test_reset_defense_frequency():
    database = get_database()
    universe = get_universe()
    
    try:
        championships = universe.championships
        reset_count = 0
        
        for championship in championships:
            championship.defense_frequency_days = 30
            championship.min_annual_defenses = 12
            universe.save_championship(championship)
            reset_count += 1
        
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'message': f'Reset defense frequency for {reset_count} championships',
            'reset_count': reset_count
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@debug_bp.route('/api/test/defense-frequency/report')
def api_test_defense_frequency_report():
    universe = get_universe()
    
    try:
        championships = universe.championships
        report = {
            'total_championships': len(championships),
            'vacant': 0,
            'normal': 0,
            'medium_urgency': 0,
            'high_urgency': 0,
            'overdue': 0,
            'championships': []
        }
        
        for championship in championships:
            if championship.is_vacant:
                report['vacant'] += 1
                continue
            
            status = championship.get_defense_status(
                universe.current_year,
                universe.current_week
            )
            
            if status['is_overdue']:
                report['overdue'] += 1
            elif status['urgency_level'] == 2:
                report['high_urgency'] += 1
            elif status['urgency_level'] == 1:
                report['medium_urgency'] += 1
            else:
                report['normal'] += 1
            
            champion = universe.get_wrestler_by_id(championship.effective_champion_id)
            
            report['championships'].append({
                'id': championship.id,
                'name': championship.name,
                'champion': champion.name if champion else 'Unknown',
                'requirements': {
                    'max_days': championship.defense_frequency_days,
                    'min_annual': championship.min_annual_defenses
                },
                'status': status
            })
        
        report['championships'].sort(
            key=lambda x: x['status']['urgency_level'],
            reverse=True
        )
        
        return jsonify({
            'success': True,
            'current_year': universe.current_year,
            'current_week': universe.current_week,
            'report': report
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500