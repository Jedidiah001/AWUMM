"""
AWUM - AI Wrestling Universe Manager
Main Flask Application Entry Point

NOW WITH SQLITE DATABASE PERSISTENCE + CONTRACT MANAGEMENT
"""

from flask import Flask, render_template, jsonify, request
import os
import json
from datetime import datetime
from typing import List, Dict, Any
import atexit
import time
from creative.draft_manager import draft_manager
from models.draft import DraftFormat
from economy.free_agent_pool import initialize_free_agent_pool, free_agent_pool
from models.free_agent import FreeAgentVisibility, FreeAgentMood



# Import our models
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.wrestler import Wrestler
from models.championship import Championship
from models.calendar import Calendar
from models.match import MatchDraft, MatchParticipant, BookingBias, MatchImportance
from models.feud import FeudManager, FeudType, FeudStatus
from models.show import ShowDraft, ShowResult
from simulation.match_sim import match_simulator
from creative.ai_director import ai_director
from persistence.database import Database
from persistence.universe_db import DatabaseUniverseState
from persistence.initial_data import load_initial_data_to_db
from economy.contracts import contract_manager
from simulation.aging import aging_system
from simulation.events import events_manager
from creative.storylines import storyline_engine
from simulation.injuries import InjuryManager
from simulation.injuries import InjuryManager, injury_manager as global_injury_manager
import simulation.injuries
from routes.championship_routes import register_championship_routes
from simulation.prestige_calculator import prestige_calculator
from models.title_lineage import TitleLineageTracker
from persistence.lineage_db import create_lineage_tables


# Initialize Flask app
app = Flask(
    __name__,
    template_folder='../frontend/templates',
    static_folder='../frontend/static'
)

from api.reign_goals_api import reign_goals_bp
app.register_blueprint(reign_goals_bp)

# Configuration
app.config['JSON_SORT_KEYS'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

# ============================================================================
# GLOBAL STATE - NOW DATABASE-BACKED
# ============================================================================

# Initialize database
data_dir = os.path.join(os.path.dirname(__file__), 'data')
db_path = os.path.join(data_dir, 'awum.db')

database = Database(db_path)
universe = DatabaseUniverseState(database)
free_agent_pool_manager = initialize_free_agent_pool(database)
simulation.injuries.injury_manager = InjuryManager(database, medical_staff_tier="Standard")
injury_manager = simulation.injuries.injury_manager


def save_universe_on_exit():
    """Save universe state when app closes"""
    import signal
    
    # Ignore further interrupts during save
    original_sigint = signal.signal(signal.SIGINT, signal.SIG_IGN)
    
    try:
        print("\n💾 Saving universe state...")
        universe.save_all()
        print("✅ Universe saved successfully")
    except Exception as e:
        print(f"❌ Failed to save on exit: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Restore original handler
        signal.signal(signal.SIGINT, original_sigint)


# ============================================================================
# DATA LOADING FUNCTIONS
# ============================================================================

def initialize_universe_data():
    """Load initial data into database if needed"""
    return load_initial_data_to_db(database, data_dir)
injury_manager = InjuryManager(database, medical_staff_tier="Standard")
create_lineage_tables(database)
universe.lineage_tracker = TitleLineageTracker(database)


# ============================================================================
# ROUTES - Main Pages
# ============================================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/office')
def office_view():
    return render_template('office.html')

@app.route('/booking')
def booking_view():
    return render_template('booking.html')

@app.route('/calendar')
def calendar_view():
    return render_template('calendar.html')

@app.route('/show-production')
def show_production_view():
    return render_template('show_production.html')

@app.route('/locker-room')
def locker_room_view():
    return render_template('locker_room.html')

@app.route('/evolve')
def evolve_view():
    return render_template('evolve.html')

@app.route('/world-feed')
def world_feed_view():
    return render_template('world_feed.html')

@app.route('/history-hub')
def history_hub_view():
    return render_template('history_hub.html')

@app.route('/legacy-expansion')
def legacy_expansion_view():
    return render_template('legacy_expansion.html')

@app.route('/recap')
def recap_view():
    return render_template('recap.html')

@app.route('/roster')
def roster_view():
    return render_template('roster.html')

@app.route('/feuds')
def feuds_view():
    return render_template('feuds.html')

@app.route('/contracts')
def contracts_view():
    return render_template('contracts.html')

@app.route('/finance')
def finance_view():
    return render_template('finance.html')

@app.route('/caw')
def caw_view():
    return render_template('caw.html')

@app.route('/championships')
def championships_view():
    """Championships management view"""
    return render_template('championships.html')

@app.route('/free-agents')
def free_agents_view():
    return render_template('free_agents.html')


# ============================================================================
# API ROUTES - Core Endpoints
# ============================================================================

@app.route('/api/status')
def api_status():
    return jsonify({
        'status': 'online',
        'timestamp': datetime.now().isoformat(),
        'game': 'AWUM - AI Wrestling Universe Manager',
        'version': '0.1.0-alpha',
        'storage': 'SQLite',
        'db_path': db_path,
        'initialized': len(universe.wrestlers) > 0
    })


@app.route('/api/universe/state')
def api_universe_state():
    current_show = universe.calendar.get_current_show()
    next_ppv = universe.calendar.get_next_ppv()
    
    return jsonify({
        'promotion': 'Ring of Champions',
        'year': universe.current_year,
        'week': universe.current_week,
        'balance': universe.balance,
        'brands': ['ROC Alpha', 'ROC Velocity', 'ROC Vanguard'],
        'total_roster': len(universe.wrestlers),
        'active_roster': len(universe.get_active_wrestlers()),
        'retired_count': len(universe.retired_wrestlers),
        'active_feuds': len(universe.feud_manager.get_active_feuds()),
        'current_show': current_show.to_dict() if current_show else None,
        'next_show': current_show.to_dict() if current_show else None,
        'next_ppv': next_ppv.to_dict() if next_ppv else None
    })


@app.route('/api/universe/advance', methods=['POST'])
def api_advance_universe():
    universe.calendar.advance_to_next_show()
    universe.save_all()
    
    return jsonify({
        'success': True,
        'year': universe.current_year,
        'week': universe.current_week
    })


# ============================================================================
# API ROUTES - Calendar
# ============================================================================

@app.route('/api/calendar/current')
def api_calendar_current():
    return jsonify(universe.calendar.to_dict())


@app.route('/api/calendar/next')
def api_calendar_next():
    current_show = universe.calendar.get_current_show()
    
    if not current_show:
        return jsonify({'error': 'No shows scheduled'}), 404
    
    return jsonify(current_show.to_dict())


@app.route('/api/calendar/upcoming-ppvs')
def api_calendar_upcoming_ppvs():
    count = request.args.get('count', 3, type=int)
    ppvs = universe.calendar.get_upcoming_ppvs(count)
    
    return jsonify({
        'count': len(ppvs),
        'ppvs': [ppv.to_dict() for ppv in ppvs]
    })


@app.route('/api/calendar/shows')
def api_calendar_shows():
    start = request.args.get('start', 0, type=int)
    limit = request.args.get('limit', 20, type=int)
    
    shows = universe.calendar.generated_shows[start:start+limit]
    
    return jsonify({
        'total': len(universe.calendar.generated_shows),
        'start': start,
        'limit': limit,
        'shows': [show.to_dict() for show in shows]
    })


# ============================================================================
# API ROUTES - Feuds
# ============================================================================

@app.route('/api/feuds')
def api_get_feuds():
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    
    if active_only:
        feuds = universe.feud_manager.get_active_feuds()
    else:
        feuds = universe.feud_manager.feuds
    
    return jsonify({
        'total': len(feuds),
        'feuds': [f.to_dict() for f in feuds]
    })


@app.route('/api/feuds/<feud_id>')
def api_get_feud(feud_id):
    feud = universe.feud_manager.get_feud_by_id(feud_id)
    
    if not feud:
        return jsonify({'error': 'Feud not found'}), 404
    
    return jsonify(feud.to_dict())


@app.route('/api/feuds/active')
def api_get_active_feuds():
    feuds = universe.feud_manager.get_active_feuds()
    
    return jsonify({
        'total': len(feuds),
        'feuds': [f.to_dict() for f in feuds]
    })


@app.route('/api/feuds/hot')
def api_get_hot_feuds():
    min_intensity = request.args.get('min_intensity', 70, type=int)
    feuds = universe.feud_manager.get_hot_feuds(min_intensity)
    
    return jsonify({
        'total': len(feuds),
        'min_intensity': min_intensity,
        'feuds': [f.to_dict() for f in feuds]
    })


@app.route('/api/feuds/wrestler/<wrestler_id>')
def api_get_wrestler_feuds(wrestler_id):
    feuds = universe.feud_manager.get_feuds_involving(wrestler_id)
    
    wrestler = universe.get_wrestler_by_id(wrestler_id)
    wrestler_name = wrestler.name if wrestler else "Unknown"
    
    return jsonify({
        'wrestler_id': wrestler_id,
        'wrestler_name': wrestler_name,
        'total': len(feuds),
        'feuds': [f.to_dict() for f in feuds]
    })


@app.route('/api/feuds/create', methods=['POST'])
def api_create_feud():
    try:
        data = request.get_json()
        
        feud_type_str = data.get('feud_type', 'personal')
        participant_ids = data.get('participant_ids', [])
        title_id = data.get('title_id')
        initial_intensity = data.get('initial_intensity', 20)
        
        if len(participant_ids) < 2:
            return jsonify({'error': 'At least 2 participants required'}), 400
        
        participant_names = []
        for pid in participant_ids:
            wrestler = universe.get_wrestler_by_id(pid)
            if not wrestler:
                return jsonify({'error': f'Wrestler {pid} not found'}), 404
            participant_names.append(wrestler.name)
        
        title_name = None
        if title_id:
            title = universe.get_championship_by_id(title_id)
            if title:
                title_name = title.name
        
        feud = universe.feud_manager.create_feud(
            feud_type=FeudType(feud_type_str),
            participant_ids=participant_ids,
            participant_names=participant_names,
            year=universe.current_year,
            week=universe.current_week,
            title_id=title_id,
            title_name=title_name,
            initial_intensity=initial_intensity
        )
        
        # Save to database
        universe.save_feud(feud)
        
        return jsonify({
            'success': True,
            'feud': feud.to_dict()
        })
    
    except ValueError as e:
        return jsonify({'error': f'Invalid parameter: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/feuds/<feud_id>/add-segment', methods=['POST'])
def api_add_feud_segment(feud_id):
    try:
        feud = universe.feud_manager.get_feud_by_id(feud_id)
        
        if not feud:
            return jsonify({'error': 'Feud not found'}), 404
        
        data = request.get_json()
        
        segment_type = data.get('segment_type', 'match')
        description = data.get('description', '')
        intensity_change = data.get('intensity_change', 0)
        winner_id = data.get('winner_id')
        
        feud.add_segment(
            show_id=f"show_y{universe.current_year}_w{universe.current_week}",
            show_name=f"Week {universe.current_week} Show",
            year=universe.current_year,
            week=universe.current_week,
            segment_type=segment_type,
            description=description,
            intensity_change=intensity_change
        )
        
        if winner_id and segment_type == 'match':
            feud.record_match_result(winner_id)
        
        # Save to database
        universe.save_feud(feud)
        
        return jsonify({
            'success': True,
            'feud': feud.to_dict()
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/feuds/<feud_id>/resolve', methods=['POST'])
def api_resolve_feud(feud_id):
    feud = universe.feud_manager.get_feud_by_id(feud_id)
    
    if not feud:
        return jsonify({'error': 'Feud not found'}), 404
    
    feud.resolve()
    universe.save_feud(feud)
    
    return jsonify({
        'success': True,
        'feud': feud.to_dict()
    })


@app.route('/api/feuds/<feud_id>/reignite', methods=['POST'])
def api_reignite_feud(feud_id):
    feud = universe.feud_manager.get_feud_by_id(feud_id)
    
    if not feud:
        return jsonify({'error': 'Feud not found'}), 404
    
    intensity = request.get_json().get('intensity', 50) if request.is_json else 50
    
    feud.reignite(intensity)
    universe.save_feud(feud)
    
    return jsonify({
        'success': True,
        'feud': feud.to_dict()
    })


@app.route('/api/feuds/stats')
def api_feud_stats():
    return jsonify(universe.feud_manager.to_dict())


# ============================================================================
# API ROUTES - Match Simulation
# ============================================================================

@app.route('/api/test/simulate-match', methods=['POST'])
def api_test_simulate_match():
    try:
        data = request.get_json()
        
        wrestler_a_id = data.get('wrestler_a_id')
        wrestler_b_id = data.get('wrestler_b_id')
        
        wrestler_a = universe.get_wrestler_by_id(wrestler_a_id)
        wrestler_b = universe.get_wrestler_by_id(wrestler_b_id)
        
        if not wrestler_a or not wrestler_b:
            return jsonify({'error': 'One or both wrestlers not found'}), 404
        
        booking_bias_str = data.get('booking_bias', 'even')
        importance_str = data.get('importance', 'normal')
        is_title_match = data.get('is_title_match', False)
        title_id = data.get('title_id')
        
        booking_bias = BookingBias(booking_bias_str)
        importance = MatchImportance(importance_str)
        
        title_name = None
        if is_title_match and title_id:
            title = universe.get_championship_by_id(title_id)
            title_name = title.name if title else None
        
        existing_feud = universe.feud_manager.get_feud_between(wrestler_a.id, wrestler_b.id)
        feud_id = existing_feud.id if existing_feud else None
        
        match_draft = MatchDraft(
            match_id=f"test_match_{wrestler_a_id}_vs_{wrestler_b_id}",
            side_a=MatchParticipant(
                wrestler_ids=[wrestler_a.id],
                wrestler_names=[wrestler_a.name],
                is_tag_team=False
            ),
            side_b=MatchParticipant(
                wrestler_ids=[wrestler_b.id],
                wrestler_names=[wrestler_b.name],
                is_tag_team=False
            ),
            match_type='singles',
            is_title_match=is_title_match,
            title_id=title_id,
            title_name=title_name,
            card_position=5,
            booking_bias=booking_bias,
            importance=importance,
            feud_id=feud_id
        )
        
        result = match_simulator.simulate_match(
            match_draft,
            [wrestler_a],
            [wrestler_b]
        )
        
        if result.is_upset:
            winner_id = wrestler_a.id if result.winner == 'side_a' else wrestler_b.id
            winner_name = wrestler_a.name if result.winner == 'side_a' else wrestler_b.name
            loser_id = wrestler_b.id if result.winner == 'side_a' else wrestler_a.id
            loser_name = wrestler_b.name if result.winner == 'side_a' else wrestler_a.name
            
            feud = universe.feud_manager.auto_create_from_upset(
                winner_id=winner_id,
                winner_name=winner_name,
                loser_id=loser_id,
                loser_name=loser_name,
                year=universe.current_year,
                week=universe.current_week,
                show_id="test_show"
            )
            
            universe.save_feud(feud)
            
            return jsonify({
                'success': True,
                'match_result': result.to_dict(),
                'feud_created': True,
                'feud': feud.to_dict()
            })
        
        return jsonify({
            'success': True,
            'match_result': result.to_dict(),
            'feud_created': False
        })
    
    except ValueError as e:
        return jsonify({'error': f'Invalid parameter: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'Simulation failed: {str(e)}'}), 500


@app.route('/api/test/quick-match')
def api_test_quick_match():
    try:
        import random
        
        active = universe.get_active_wrestlers()
        if len(active) < 2:
            return jsonify({'error': 'Not enough active wrestlers'}), 400
        
        wrestler_a, wrestler_b = random.sample(active, 2)
        
        match_draft = MatchDraft(
            match_id=f"quick_test_{wrestler_a.id}_vs_{wrestler_b.id}",
            side_a=MatchParticipant(
                wrestler_ids=[wrestler_a.id],
                wrestler_names=[wrestler_a.name],
                is_tag_team=False
            ),
            side_b=MatchParticipant(
                wrestler_ids=[wrestler_b.id],
                wrestler_names=[wrestler_b.name],
                is_tag_team=False
            ),
            match_type='singles',
            card_position=5,
            booking_bias=BookingBias.EVEN,
            importance=MatchImportance.NORMAL
        )
        
        result = match_simulator.simulate_match(
            match_draft,
            [wrestler_a],
            [wrestler_b]
        )
        
        return jsonify({
            'success': True,
            'match_result': result.to_dict()
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# API ROUTES - Booking & Show Generation
# ============================================================================

@app.route('/api/booking/generate', methods=['POST'])
def api_generate_show_card():
    try:
        data = request.get_json() if request.is_json else {}
        show_id = data.get('show_id')
        
        if show_id:
            scheduled_show = None
            for show in universe.calendar.generated_shows:
                if show.show_id == show_id:
                    scheduled_show = show
                    break
            
            if not scheduled_show:
                return jsonify({'error': 'Show not found'}), 404
        else:
            scheduled_show = universe.calendar.get_current_show()
            
            if not scheduled_show:
                return jsonify({'error': 'No show scheduled'}), 404
        
        if scheduled_show.brand == 'Cross-Brand':
            brand_roster = universe.get_active_wrestlers()
        else:
            brand_roster = universe.get_wrestlers_by_brand(scheduled_show.brand)
        
        if scheduled_show.brand == 'Cross-Brand':
            brand_titles = universe.championships
        else:
            brand_titles = [
                c for c in universe.championships 
                if c.assigned_brand == scheduled_show.brand or c.assigned_brand == 'Cross-Brand'
            ]
        
        if scheduled_show.brand == 'Cross-Brand':
            active_feuds = universe.feud_manager.get_active_feuds()
        else:
            active_feuds = []
            for feud in universe.feud_manager.get_active_feuds():
                for pid in feud.participant_ids:
                    wrestler = universe.get_wrestler_by_id(pid)
                    if wrestler and wrestler.primary_brand == scheduled_show.brand:
                        active_feuds.append(feud)
                        break
        
        upcoming_ppvs = universe.calendar.get_upcoming_ppvs(3)
        
        show_draft = ai_director.generate_show_card(
            scheduled_show=scheduled_show,
            brand_roster=brand_roster,
            all_wrestlers=universe.wrestlers,
            brand_titles=brand_titles,
            all_titles=universe.championships,
            active_feuds=active_feuds,
            feud_manager=universe.feud_manager,
            upcoming_ppvs=upcoming_ppvs,
            universe_state=universe 
        )
        
        return jsonify({
            'success': True,
            'show_draft': show_draft.to_dict()
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/booking/preview-next')
def api_preview_next_show():
    try:
        current_show = universe.calendar.get_current_show()
        
        if not current_show:
            return jsonify({'error': 'No show scheduled'}), 404
        
        if current_show.brand == 'Cross-Brand':
            available_count = len(universe.get_active_wrestlers())
        else:
            available_count = len(universe.get_wrestlers_by_brand(current_show.brand))
        
        if current_show.brand == 'Cross-Brand':
            relevant_feuds = universe.feud_manager.get_active_feuds()
        else:
            relevant_feuds = []
            for feud in universe.feud_manager.get_active_feuds():
                for pid in feud.participant_ids:
                    wrestler = universe.get_wrestler_by_id(pid)
                    if wrestler and wrestler.primary_brand == current_show.brand:
                        relevant_feuds.append(feud)
                        break
        
        return jsonify({
            'show': current_show.to_dict(),
            'available_wrestlers': available_count,
            'active_feuds': len(relevant_feuds),
            'hot_feuds': len([f for f in relevant_feuds if f.intensity >= 70])
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# API ROUTES - Roster Management
# ============================================================================

@app.route('/api/roster')
def api_get_roster():
    brand = request.args.get('brand')
    alignment = request.args.get('alignment')
    role = request.args.get('role')
    gender = request.args.get('gender')
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    
    wrestlers = universe.wrestlers
    
    if active_only:
        wrestlers = [w for w in wrestlers if not w.is_retired]
    
    if brand:
        wrestlers = [w for w in wrestlers if w.primary_brand == brand]
    
    if alignment:
        wrestlers = [w for w in wrestlers if w.alignment == alignment]
    
    if role:
        wrestlers = [w for w in wrestlers if w.role == role]
    
    if gender:
        wrestlers = [w for w in wrestlers if w.gender == gender]
    
    return jsonify({
        'total': len(wrestlers),
        'wrestlers': [w.to_dict() for w in wrestlers]
    })



@app.route('/api/roster/<wrestler_id>')
def api_get_wrestler(wrestler_id):
    wrestler = universe.get_wrestler_by_id(wrestler_id)
    
    if not wrestler:
        return jsonify({'error': 'Wrestler not found'}), 404
    
    return jsonify(wrestler.to_dict())


# ============================================================================
# API ROUTES - CONTRACT MANAGEMENT (STEP 10 NEW!)
# ============================================================================

@app.route('/api/contracts/expiring')
def api_get_expiring_contracts():
    """Get all wrestlers with contracts expiring soon"""
    weeks_threshold = request.args.get('weeks', 4, type=int)
    
    expiring = contract_manager.get_expiring_contracts(
        universe.get_active_wrestlers(),
        weeks_threshold
    )
    
    return jsonify({
        'total': len(expiring),
        'threshold_weeks': weeks_threshold,
        'wrestlers': [w.to_dict() for w in expiring]
    })


@app.route('/api/contracts/expired')
def api_get_expired_contracts():
    """Get all wrestlers with expired contracts (0 weeks remaining)"""
    expired = contract_manager.get_expired_contracts(universe.wrestlers)
    
    return jsonify({
        'total': len(expired),
        'wrestlers': [w.to_dict() for w in expired]
    })


@app.route('/api/contracts/<wrestler_id>/market-value')
def api_get_market_value(wrestler_id):
    """Calculate a wrestler's market value"""
    wrestler = universe.get_wrestler_by_id(wrestler_id)
    
    if not wrestler:
        return jsonify({'error': 'Wrestler not found'}), 404
    
    market_value = contract_manager.calculate_market_value(wrestler)
    
    return jsonify({
        'wrestler_id': wrestler.id,
        'wrestler_name': wrestler.name,
        'market_value': market_value,
        'current_salary': wrestler.contract.salary_per_show,
        'difference': market_value - wrestler.contract.salary_per_show
    })


@app.route('/api/contracts/<wrestler_id>/extend', methods=['POST'])
def api_extend_contract_negotiation(wrestler_id):
    """
    Extend a wrestler's contract with negotiation.
    
    Request body:
    {
        "weeks": 52,
        "salary_per_show": 15000
    }
    """
    wrestler = universe.get_wrestler_by_id(wrestler_id)
    
    if not wrestler:
        return jsonify({'error': 'Wrestler not found'}), 404
    
    data = request.get_json()
    weeks = data.get('weeks', 52)
    offered_salary = data.get('salary_per_show', wrestler.contract.salary_per_show)
    
    # Attempt negotiation
    success, message = contract_manager.negotiate_extension(
        wrestler,
        offered_salary,
        weeks,
        universe.balance
    )
    
    if success:
        # Save wrestler
        universe.save_wrestler(wrestler)
        database.conn.commit()
    
    return jsonify({
        'success': success,
        'message': message,
        'wrestler': wrestler.to_dict() if success else None
    })


@app.route('/api/contracts/<wrestler_id>/auto-extend', methods=['POST'])
def api_auto_extend_contract(wrestler_id):
    """
    Simple auto-extend at current salary (original endpoint, kept for compatibility).
    
    Request body (optional):
    {
        "weeks": 52
    }
    """
    wrestler = universe.get_wrestler_by_id(wrestler_id)
    
    if not wrestler:
        return jsonify({'error': 'Wrestler not found'}), 404
    
    data = request.get_json() if request.is_json else {}
    weeks_to_add = data.get('weeks', 52)
    
    result = contract_manager.auto_extend(wrestler, weeks_to_add)
    
    universe.save_wrestler(wrestler)
    database.conn.commit()
    
    return jsonify(result)


@app.route('/api/contracts/<wrestler_id>/release', methods=['POST'])
def api_release_wrestler_contract(wrestler_id):
    """Release a wrestler from their contract"""
    wrestler = universe.get_wrestler_by_id(wrestler_id)
    
    if not wrestler:
        return jsonify({'error': 'Wrestler not found'}), 404
    
    result = contract_manager.release_wrestler(wrestler)
    
    universe.save_wrestler(wrestler)
    database.conn.commit()
    
    return jsonify(result)


# LEGACY ENDPOINT (kept for backward compatibility with old office.html)
@app.route('/api/roster/<wrestler_id>/extend-contract', methods=['POST'])
def api_extend_contract(wrestler_id):
    """Legacy endpoint - redirects to auto-extend"""
    return api_auto_extend_contract(wrestler_id)


@app.route('/api/roster/<wrestler_id>/release', methods=['POST'])
def api_release_wrestler(wrestler_id):
    """Legacy endpoint - redirects to contract release"""
    return api_release_wrestler_contract(wrestler_id)


# ============================================================================
# API ROUTES - STEP 116: MARKET VALUE CALCULATION (MISSING ENDPOINTS)
# ============================================================================

@app.route('/api/market-value/wrestler/<wrestler_id>')
def api_wrestler_market_value(wrestler_id):
    """
    Calculate market value for an active wrestler.
    Useful for contract negotiations and roster management.
    """
    wrestler = universe.get_wrestler_by_id(wrestler_id)
    
    if not wrestler:
        return jsonify({'error': 'Wrestler not found'}), 404
    
    try:
        from economy.market_value import market_value_calculator, MarketValueFactors
        
        # Build factors from wrestler
        factors = MarketValueFactors(
            base_value=wrestler.contract.salary_per_show,
            current_popularity=wrestler.popularity,
            peak_popularity=getattr(wrestler, 'peak_popularity', wrestler.popularity),
            popularity_trend=0,  # Would need to track this
            average_match_rating=3.0,  # Would get from match history
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
            backstage_reputation=wrestler.morale,  # Use morale as proxy
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
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/market-value/free-agent/<free_agent_id>')
def api_free_agent_market_value(free_agent_id):
    """
    Get comprehensive market value for a free agent.
    Returns detailed breakdown of all factors.
    """
    try:
        fa = free_agent_pool_manager.get_free_agent_by_id(free_agent_id)
        
        if not fa:
            return jsonify({'error': 'Free agent not found'}), 404
        
        # Calculate comprehensive market value
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
            'value_history': [h.to_dict() for h in fa.market_value_history[-12:]]  # Last 12 weeks
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/market-value/free-agent/<free_agent_id>/recalculate', methods=['POST'])
def api_recalculate_free_agent_market_value(free_agent_id):
    """
    Force recalculation of a free agent's market value.
    Useful after major events or weekly updates.
    """
    try:
        fa = free_agent_pool_manager.get_free_agent_by_id(free_agent_id)
        
        if not fa:
            return jsonify({'error': 'Free agent not found'}), 404
        
        old_value = fa.market_value
        
        # Recalculate
        new_value, breakdown = fa.calculate_comprehensive_market_value(
            year=universe.current_year,
            week=universe.current_week,
            include_breakdown=True
        )
        
        # Save to database
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
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500




@app.route('/api/market-value/bulk-recalculate', methods=['POST'])
def api_bulk_recalculate_market_values():
    """
    Recalculate market values for all free agents.
    Should be run weekly or after major events.
    """
    try:
        results = []
        updated_count = 0
        
        for fa in free_agent_pool_manager.available_free_agents:
            old_value = fa.market_value
            
            new_value, _ = fa.calculate_comprehensive_market_value(
                year=universe.current_year,
                week=universe.current_week,
                include_breakdown=False
            )
            
            # Save to database
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
        
        # Commit all changes
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'updated_count': updated_count,
            'results': results
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Rollback on error
        try:
            database.conn.rollback()
        except:
            pass
        return jsonify({'error': str(e)}), 500


@app.route('/api/market-value/compare', methods=['POST'])
def api_compare_market_values():
    """
    Compare market values of multiple wrestlers/free agents.
    
    Request body:
    {
        "wrestler_ids": ["w001", "w002"],
        "free_agent_ids": ["fa_w003_1_1"]
    }
    """
    try:
        from economy.market_value import market_value_calculator
        
        data = request.get_json()
        wrestler_ids = data.get('wrestler_ids', [])
        free_agent_ids = data.get('free_agent_ids', [])
        
        comparisons = []
        
        # Process wrestlers
        for wid in wrestler_ids:
            wrestler = universe.get_wrestler_by_id(wid)
            if wrestler:
                # Use simple estimate for wrestlers
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
        
        # Process free agents
        for faid in free_agent_ids:
            fa = free_agent_pool_manager.get_free_agent_by_id(faid)
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
        
        # Sort by market value descending
        comparisons.sort(key=lambda x: x['market_value'], reverse=True)
        
        return jsonify({
            'success': True,
            'count': len(comparisons),
            'comparisons': comparisons
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# API ROUTES - Championships
# ============================================================================

@app.route('/api/championships')
def api_get_championships():
    brand = request.args.get('brand')
    
    championships = universe.championships
    
    if brand and brand != 'All':
        championships = [c for c in championships if c.assigned_brand == brand or c.assigned_brand == 'Cross-Brand']
    
    return jsonify({
        'total': len(championships),
        'championships': [c.to_dict() for c in championships]
    })


@app.route('/api/championships/<title_id>')
def api_get_championship(title_id):
    championship = universe.get_championship_by_id(title_id)
    
    if not championship:
        return jsonify({'error': 'Championship not found'}), 404
    
    return jsonify(championship.to_dict())


# ============================================================================
# API ROUTES - Statistics
# ============================================================================

@app.route('/api/stats/roster-summary')
def api_roster_summary():
    summary = {
        'total_wrestlers': len(universe.wrestlers),
        'active_wrestlers': len(universe.get_active_wrestlers()),
        'retired_wrestlers': len(universe.retired_wrestlers),
        'by_brand': {},
        'by_role': {},
        'by_alignment': {},
        'by_gender': {},
        'major_superstars': len([w for w in universe.wrestlers if w.is_major_superstar]),
        'injured_wrestlers': len([w for w in universe.wrestlers if w.is_injured]),
        'contracts_expiring_soon': len([w for w in universe.wrestlers if w.contract_expires_soon])
    }
    
    for brand in ['ROC Alpha', 'ROC Velocity', 'ROC Vanguard']:
        summary['by_brand'][brand] = len([w for w in universe.wrestlers if w.primary_brand == brand and not w.is_retired])
    
    for role in ['Main Event', 'Upper Midcard', 'Midcard', 'Lower Midcard', 'Jobber']:
        summary['by_role'][role] = len([w for w in universe.wrestlers if w.role == role and not w.is_retired])
    
    for alignment in ['Face', 'Heel', 'Tweener']:
        summary['by_alignment'][alignment] = len([w for w in universe.wrestlers if w.alignment == alignment and not w.is_retired])
    
    for gender in ['Male', 'Female']:
        summary['by_gender'][gender] = len([w for w in universe.wrestlers if w.gender == gender and not w.is_retired])
    
    return jsonify(summary)


@app.route('/api/show/simulate', methods=['POST'])
def api_simulate_show():
    """
    Simulate a complete show.
    Accepts a ShowDraft JSON and returns ShowResult.
    """
    try:
        from simulation.show_sim import show_simulator
        from models.show import ShowDraft
        
        data = request.get_json()
        
        # Parse ShowDraft from JSON
        show_draft = ShowDraft.from_dict(data)
        
        print(f"\n{'='*60}")
        print(f"📡 API: Received show simulation request")
        print(f"   Show: {show_draft.show_name}")
        print(f"   Year {show_draft.year}, Week {show_draft.week}")
        print(f"   Matches: {len(show_draft.matches)}")
        print(f"{'='*60}\n")
        
        # Simulate the show
        show_result = show_simulator.simulate_show(show_draft, universe)

        # Process weekly injury recovery
        if injury_manager:
            print("\n🏥 Processing injury recovery...")
            recovery_updates = injury_manager.process_weekly_recovery(
                universe.wrestlers,
                show_draft.year,
                show_draft.week
            )
            
            for update in recovery_updates:
                if update['status'] == 'recovered':
                    show_result.add_event(
                        'injury_recovery',
                        f"✅ {update['wrestler_name']} has recovered from injury!"
                    )
                elif update['status'] == 'milestone':
                    show_result.add_event(
                        'rehab_milestone',
                        f"🏥 {update['message']}"
                    )
            
            print(f"   {len(recovery_updates)} recovery updates processed")
        
        # Check if any severe injuries need angles next week
        if hasattr(show_result, 'injury_angles_needed'):
            print(f"\n📝 Injury angles needed for next week: {len(show_result.injury_angles_needed)}")
        
        print("\n💾 Saving results to database...")
        
        # Save show result to database (this saves matches too)
        database.save_show_result(show_result)
        
        # Save updated universe state (wrestlers, championships, feuds)
        universe.save_all()
        
        # Advance calendar to next show
        universe.calendar.advance_to_next_show()
        
        # Get the new current show after advancing
        next_show = universe.calendar.get_current_show()
        
        # Update game state with NEW year/week from the next show
        database.update_game_state(
            current_year=next_show.year if next_show else show_draft.year,
            current_week=next_show.week if next_show else show_draft.week,
            current_show_index=universe.calendar.current_show_index,
            balance=universe.balance,
            show_count=universe.show_count,
            current_brand=next_show.brand if next_show else show_draft.brand
        )
        
        print(f"✅ All data saved successfully!")
        print(f"   Advanced to: Year {next_show.year if next_show else '?'}, Week {next_show.week if next_show else '?'}")
        print()
        
        return jsonify({
            'success': True,
            'show_result': show_result.to_dict()
        })
    
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        
        print("\n" + "="*60)
        print("❌ SHOW SIMULATION ERROR")
        print("="*60)
        print(error_trace)
        print("="*60 + "\n")
        
        # Try to rollback any pending changes
        try:
            database.conn.rollback()
        except:
            pass
        
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': error_trace
        }), 500

@app.route('/api/debug/fix-game-state', methods=['POST'])
def api_debug_fix_game_state():
    """Manually fix game state to match calendar position"""
    try:
        # Sync calendar from database
        universe.sync_calendar_from_state()
        
        # Get current show from calendar
        current_show = universe.calendar.get_current_show()
        
        if current_show:
            # Update game state
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

@app.route('/api/show/history')
def api_show_history():
    """Get show history with pagination"""
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    try:
        history = database.get_show_history(limit=limit, offset=offset)
        
        # Get total count
        cursor = database.conn.cursor()
        cursor.execute('SELECT COUNT(*) as total FROM show_history')
        total = cursor.fetchone()['total']
        
        return jsonify({
            'success': True,
            'total': total,
            'shows': history
        })
    except Exception as e:
        import traceback
        print(f"Error getting show history: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'shows': []
        }), 500


@app.route('/api/match/history')
def api_match_history():
    """Get match history, optionally filtered by wrestler"""
    wrestler_id = request.args.get('wrestler_id')
    limit = request.args.get('limit', 20, type=int)
    
    matches = database.get_match_history(wrestler_id=wrestler_id, limit=limit)
    
    return jsonify({
        'total': len(matches),
        'matches': matches
    })


# ============================================================================
# API ROUTES - Financial Statistics
# ============================================================================

@app.route('/api/stats/financial-summary')
def api_financial_summary():
    """Get complete financial summary"""
    try:
        # Get show history
        show_history = database.get_show_history(limit=100)
        
        # Calculate totals
        total_revenue = sum(show['total_revenue'] for show in show_history)
        total_payroll = sum(show['total_payroll'] for show in show_history)
        total_profit = sum(show['net_profit'] for show in show_history)
        
        # Calculate averages
        if show_history:
            avg_revenue = total_revenue / len(show_history)
            avg_payroll = total_payroll / len(show_history)
            avg_profit = total_profit / len(show_history)
            avg_attendance = sum(show['total_attendance'] for show in show_history) / len(show_history)
            avg_rating = sum(show['overall_rating'] for show in show_history) / len(show_history)
        else:
            avg_revenue = avg_payroll = avg_profit = avg_attendance = avg_rating = 0
        
        # Breakdown by show type
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
        
        # Calculate averages for each type
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

@app.route('/api/debug/show-history-raw')
def api_debug_show_history():
    """Debug endpoint to check raw show history data"""
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

# ============================================================================
# API ROUTES - STEP 11: Historical Stats & Records
# ============================================================================

@app.route('/api/stats/wrestler/<wrestler_id>')
def api_get_wrestler_stats(wrestler_id):
    """Get complete career statistics for a wrestler"""
    try:
        stats = database.calculate_wrestler_stats(wrestler_id)
        
        if not stats:
            return jsonify({'error': 'Wrestler not found or no stats available'}), 404
        
        # Also get milestones
        milestones = database.get_wrestler_milestones(wrestler_id)
        
        return jsonify({
            'success': True,
            'stats': stats,
            'milestones': milestones
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats/wrestler/<wrestler_id>/matches')
def api_get_wrestler_match_history(wrestler_id):
    """Get match history for a specific wrestler with pagination"""
    limit = request.args.get('limit', 20, type=int)
    
    try:
        matches = database.get_match_history(wrestler_id=wrestler_id, limit=limit)
        
        # Enhance with win/loss info for this wrestler
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


@app.route('/api/stats/promotion/records')
def api_get_promotion_records():
    """Get promotion-wide records"""
    try:
        records = database.get_promotion_records()
        
        return jsonify({
            'success': True,
            'records': records
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats/milestones/recent')
def api_get_recent_milestones():
    """Get recently achieved milestones"""
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


@app.route('/api/stats/leaderboard/<stat_type>')
def api_get_leaderboard(stat_type):
    """
    Get leaderboard for a specific stat.
    stat_type: wins, matches, win_percentage, title_reigns, star_rating
    """
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


@app.route('/api/stats/championship/<title_id>')
def api_get_championship_stats(title_id):
    """Get statistics for a specific championship"""
    try:
        cursor = database.conn.cursor()
        
        # Get championship info
        cursor.execute('SELECT * FROM championships WHERE id = ?', (title_id,))
        title_row = cursor.fetchone()
        
        if not title_row:
            return jsonify({'error': 'Championship not found'}), 404
        
        title = dict(title_row)
        
        # Get all reigns
        cursor.execute('''
            SELECT * FROM title_reigns
            WHERE title_id = ?
            ORDER BY won_date_year DESC, won_date_week DESC
        ''', (title_id,))
        
        reigns = [dict(row) for row in cursor.fetchall()]
        
        # Calculate stats
        total_reigns = len(reigns)
        completed_reigns = [r for r in reigns if r['lost_at_show_id'] is not None]
        
        stats = {
            'title': title,
            'total_reigns': total_reigns,
            'total_defenses': 0,  # Would need to track in matches
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


@app.route('/api/stats/update-all', methods=['POST'])
def api_update_all_stats():
    """
    Manually recalculate all wrestler stats.
    USE SPARINGLY - can be slow with large databases.
    """
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

@app.route('/stats')
def stats_view():
    return render_template('stats.html')


@app.route('/api/debug/create-stats-tables', methods=['POST'])
def api_debug_create_stats_tables():
    """One-time endpoint to create stats tables"""
    try:
        database._create_stats_tables()
        
        # Verify
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


@app.route('/api/debug/recreate-stats-tables', methods=['POST'])
def api_debug_recreate_stats_tables():
    """Drop and recreate stats tables with correct schema"""
    try:
        cursor = database.conn.cursor()
        
        print("🗑️ Dropping old tables...")
        cursor.execute('DROP TABLE IF EXISTS wrestler_stats')
        cursor.execute('DROP TABLE IF EXISTS milestones')
        database.conn.commit()
        
        print("📊 Creating new tables with full schema...")
        
        # Create wrestler_stats with ALL columns
        cursor.execute('''
            CREATE TABLE wrestler_stats (
                wrestler_id TEXT PRIMARY KEY,
                
                total_matches INTEGER NOT NULL DEFAULT 0,
                wins INTEGER NOT NULL DEFAULT 0,
                losses INTEGER NOT NULL DEFAULT 0,
                draws INTEGER NOT NULL DEFAULT 0,
                
                total_star_rating REAL NOT NULL DEFAULT 0,
                highest_star_rating REAL NOT NULL DEFAULT 0,
                five_star_matches INTEGER NOT NULL DEFAULT 0,
                four_star_plus_matches INTEGER NOT NULL DEFAULT 0,
                
                total_title_reigns INTEGER NOT NULL DEFAULT 0,
                total_days_as_champion INTEGER NOT NULL DEFAULT 0,
                longest_reign_days INTEGER NOT NULL DEFAULT 0,
                
                total_main_events INTEGER NOT NULL DEFAULT 0,
                total_ppv_matches INTEGER NOT NULL DEFAULT 0,
                total_upsets INTEGER NOT NULL DEFAULT 0,
                total_upset_losses INTEGER NOT NULL DEFAULT 0,
                
                clean_wins INTEGER NOT NULL DEFAULT 0,
                cheating_wins INTEGER NOT NULL DEFAULT 0,
                dq_countout_wins INTEGER NOT NULL DEFAULT 0,
                submission_wins INTEGER NOT NULL DEFAULT 0,
                
                current_win_streak INTEGER NOT NULL DEFAULT 0,
                current_loss_streak INTEGER NOT NULL DEFAULT 0,
                longest_win_streak INTEGER NOT NULL DEFAULT 0,
                longest_loss_streak INTEGER NOT NULL DEFAULT 0,
                
                last_updated TEXT NOT NULL,
                
                FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
            )
        ''')
        
        # Create milestones table
        cursor.execute('''
            CREATE TABLE milestones (
                id TEXT PRIMARY KEY,
                wrestler_id TEXT NOT NULL,
                milestone_type TEXT NOT NULL,
                description TEXT NOT NULL,
                achieved_at_show_id TEXT NOT NULL,
                achieved_at_show_name TEXT NOT NULL,
                year INTEGER NOT NULL,
                week INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_milestones_wrestler ON milestones(wrestler_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_milestones_type ON milestones(milestone_type)')
        
        database.conn.commit()
        
        # Verify columns
        cursor.execute("PRAGMA table_info(wrestler_stats)")
        columns = [row[1] for row in cursor.fetchall()]
        
        return jsonify({
            'success': True,
            'message': 'Tables recreated with correct schema',
            'columns': columns
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/stats/populate-initial', methods=['POST'])
def api_populate_initial_stats():
    """
    One-time population of stats tables from existing match history.
    Run this after Step 11 installation to populate stats.
    """
    try:
        print("📊 Populating initial statistics...")
        
        # Get all wrestlers
        wrestlers = universe.wrestlers
        populated_count = 0
        milestone_count = 0
        
        for wrestler in wrestlers:
            # Calculate and cache stats
            stats_dict = database.calculate_wrestler_stats(wrestler.id)
            
            if stats_dict and stats_dict['record']['total_matches'] > 0:
                # Update stats cache
                database.update_wrestler_stats_cache(wrestler.id)
                populated_count += 1
                
                # Check for basic milestones that should already exist
                # Get match history for this wrestler
                cursor = database.conn.cursor()
                cursor.execute('''
                    SELECT * FROM match_history
                    WHERE side_a_ids LIKE ? OR side_b_ids LIKE ?
                    ORDER BY year, week, id
                    LIMIT 1
                ''', (f'%{wrestler.id}%', f'%{wrestler.id}%'))
                
                first_match = cursor.fetchone()
                
                if first_match:
                    # Record debut milestone
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
                    
                    # Check for first win
                    if stats_dict['record']['wins'] > 0 and 'first_win' not in existing_types:
                        # Find first win
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
                    
                    # Check for 100 matches milestone
                    if stats_dict['record']['total_matches'] >= 100 and 'match_100' not in existing_types:
                        # Find 100th match
                        cursor.execute('''
                            SELECT * FROM match_history
                            WHERE side_a_ids LIKE ? OR side_b_ids LIKE ?
                            ORDER BY year, week, id
                            LIMIT 100
                        ''', (f'%{wrestler.id}%', f'%{wrestler.id}%'))
                        
                        matches = cursor.fetchall()
                        if len(matches) >= 100:
                            match_100 = matches[99]  # 100th match (0-indexed)
                            database.record_milestone(
                                wrestler_id=wrestler.id,
                                wrestler_name=wrestler.name,
                                milestone_type='match_100',
                                description=f"{wrestler.name} competed in their 100th match!",
                                show_id=match_100['show_id'],
                                show_name=match_100['show_name'],
                                year=match_100['year'],
                                week=match_100['week']
                            )
                            milestone_count += 1
                    
                    # Check for first title
                    if stats_dict['title_history']['total_reigns'] > 0 and 'first_title' not in existing_types:
                        # Find first title win
                        cursor.execute('''
                            SELECT * FROM title_reigns
                            WHERE wrestler_id = ?
                            ORDER BY won_date_year, won_date_week
                            LIMIT 1
                        ''', (wrestler.id,))
                        
                        first_title = cursor.fetchone()
                        if first_title:
                            database.record_milestone(
                                wrestler_id=wrestler.id,
                                wrestler_name=wrestler.name,
                                milestone_type='first_title',
                                description=f"{wrestler.name} won their first championship!",
                                show_id=first_title['won_at_show_id'],
                                show_name=first_title['won_at_show_name'],
                                year=first_title['won_date_year'],
                                week=first_title['won_date_week']
                            )
                            milestone_count += 1
        
        # Commit all changes
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
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


# ============================================================================
# API ROUTES - STEP 12: Save/Load System
# ============================================================================

from persistence.save_manager import SaveManager

# Initialize save manager
saves_dir = os.path.join(data_dir, 'saves')
save_manager = SaveManager(saves_dir)


@app.route('/api/saves/list')
def api_list_saves():
    """List all available save files"""
    try:
        saves = save_manager.list_saves()
        
        return jsonify({
            'success': True,
            'total': len(saves),
            'saves': [s.to_dict() for s in saves]
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/saves/save', methods=['POST'])
def api_save_universe():
    """
    Save current universe to a slot.
    
    Request body:
    {
        "slot": 1,
        "save_name": "My Save",
        "include_history": true
    }
    """
    try:
        data = request.get_json()
        
        slot = data.get('slot', 1)
        save_name = data.get('save_name', f'Save {slot}')
        include_history = data.get('include_history', True)
        
        if slot < 0 or slot > 10:
            return jsonify({'success': False, 'error': 'Slot must be between 0-10'}), 400
        
        # Perform save
        metadata = save_manager.save_universe(
            database=database,
            slot=slot,
            save_name=save_name,
            include_history=include_history
        )
        
        return jsonify({
            'success': True,
            'message': f'Universe saved to slot {slot}',
            'metadata': metadata.to_dict()
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/saves/load', methods=['POST'])
def api_load_universe():
    """
    Load universe from a save slot.
    
    Request body:
    {
        "slot": 1
    }
    """
    try:
        data = request.get_json()
        slot = data.get('slot', 1)
        
        if slot < 0 or slot > 10:
            return jsonify({'success': False, 'error': 'Slot must be between 0-10'}), 400
        
        # Perform load
        snapshot = save_manager.load_universe(
            database=database,
            slot=slot
        )
        
        # Reload universe state in memory
        universe.sync_calendar_from_state()
        
        return jsonify({
            'success': True,
            'message': f'Universe loaded from slot {slot}',
            'metadata': snapshot.metadata.to_dict()
        })
    
    except FileNotFoundError as e:
        return jsonify({'success': False, 'error': f'Save slot {slot} not found'}), 404
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/saves/delete/<int:slot>', methods=['DELETE'])
def api_delete_save(slot: int):
    """Delete a save slot"""
    try:
        if slot < 0 or slot > 10:
            return jsonify({'success': False, 'error': 'Slot must be between 0-10'}), 400
        
        success = save_manager.delete_save(slot)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Save slot {slot} deleted'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Save slot {slot} not found'
            }), 404
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/saves/autosave', methods=['POST'])
def api_autosave():
    """Create an autosave (slot 0)"""
    try:
        metadata = save_manager.save_universe(
            database=database,
            slot=0,
            save_name='Autosave',
            include_history=False  # Quick save, no full history
        )
        
        return jsonify({
            'success': True,
            'message': 'Autosave created',
            'metadata': metadata.to_dict()
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/saves/export/<int:slot>')
def api_export_save(slot: int):
    """Export a save file for download"""
    try:
        from flask import send_file
        
        save_path = save_manager.get_save_path(slot) if slot > 0 else save_manager.get_autosave_path()
        
        if not os.path.exists(save_path):
            return jsonify({'error': f'Save slot {slot} not found'}), 404
        
        filename = f'awum_save_slot_{slot}.json'
        
        return send_file(
            save_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/json'
        )
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/saves/import', methods=['POST'])
def api_import_save():
    """
    Import a save file.
    
    Expects multipart/form-data with:
    - file: the save file
    - slot: target slot number
    """
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        slot = int(request.form.get('slot', 1))
        
        if slot < 0 or slot > 10:
            return jsonify({'success': False, 'error': 'Slot must be between 0-10'}), 400
        
        # Save uploaded file temporarily
        import tempfile
        temp_path = os.path.join(tempfile.gettempdir(), 'awum_import.json')
        file.save(temp_path)
        
        # Import the save
        save_manager.import_save(temp_path, slot)
        
        # Clean up temp file
        os.remove(temp_path)
        
        return jsonify({
            'success': True,
            'message': f'Save imported to slot {slot}'
        })
    
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/saves')
def saves_view():
    return render_template('saves.html')


# ============================================================================
# API ROUTES - STEP 13: Tag Teams
# ============================================================================

@app.route('/api/tag-teams')
def api_get_tag_teams():
    """Get all tag teams"""
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    brand = request.args.get('brand')
    
    try:
        teams = universe.tag_team_manager.get_active_teams() if active_only else universe.tag_team_manager.teams
        
        # Filter by brand if specified
        if brand:
            teams = [t for t in teams if t.primary_brand == brand]
        
        return jsonify({
            'success': True,
            'total': len(teams),
            'teams': [t.to_dict() for t in teams]
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tag-teams/<team_id>')
def api_get_tag_team(team_id):
    """Get a specific tag team"""
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


@app.route('/api/tag-teams/create', methods=['POST'])
def api_create_tag_team():
    """
    Create a new tag team.
    
    Request body:
    {
        "member_ids": ["w001", "w002"],
        "team_name": "The Destroyers",
        "primary_brand": "ROC Alpha"
    }
    """
    try:
        data = request.get_json()
        
        member_ids = data.get('member_ids', [])
        team_name = data.get('team_name')
        primary_brand = data.get('primary_brand')
        
        if len(member_ids) < 2:
            return jsonify({'success': False, 'error': 'At least 2 members required'}), 400
        
        if not team_name:
            return jsonify({'success': False, 'error': 'Team name required'}), 400
        
        # Get member names
        member_names = []
        for member_id in member_ids:
            wrestler = universe.get_wrestler_by_id(member_id)
            if not wrestler:
                return jsonify({'success': False, 'error': f'Wrestler {member_id} not found'}), 404
            member_names.append(wrestler.name)
            
            # Use first member's brand if not specified
            if not primary_brand:
                primary_brand = wrestler.primary_brand
        
        # Create team
        team = universe.tag_team_manager.create_team(
            member_ids=member_ids,
            member_names=member_names,
            team_name=team_name,
            primary_brand=primary_brand,
            year=universe.current_year,
            week=universe.current_week
        )
        
        # Save to database
        universe.save_tag_team(team)
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'message': f'Tag team "{team_name}" created',
            'team': team.to_dict()
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tag-teams/<team_id>/disband', methods=['POST'])
def api_disband_tag_team(team_id):
    """Disband a tag team"""
    try:
        team = universe.tag_team_manager.get_team_by_id(team_id)
        
        if not team:
            return jsonify({'success': False, 'error': 'Tag team not found'}), 404
        
        team.disband()
        
        # Save to database
        universe.save_tag_team(team)
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'message': f'Tag team "{team.team_name}" disbanded'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tag-teams/suggestions/<brand>')
def api_get_tag_team_suggestions(brand):
    """Get suggested tag team pairings for a brand"""
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


@app.route('/api/tag-teams/wrestler/<wrestler_id>')
def api_get_wrestler_teams(wrestler_id):
    """Get all tag teams a wrestler is part of"""
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


@app.route('/tag-teams')
def tag_teams_view():
    return render_template('tag_teams.html')


# ============================================================================
# API ROUTES - STEP 14: Multi-Competitor Match Testing
# ============================================================================

@app.route('/api/test/triple-threat', methods=['POST'])
def api_test_triple_threat():
    """
    Test triple threat match simulation.
    
    Request body:
    {
        "wrestler_ids": ["w001", "w002", "w003"],
        "booking_bias": "even",  # Optional
        "importance": "normal"   # Optional
    }
    """
    try:
        data = request.get_json()
        
        wrestler_ids = data.get('wrestler_ids', [])
        if len(wrestler_ids) != 3:
            return jsonify({'error': 'Triple threat requires exactly 3 wrestlers'}), 400
        
        # Get wrestlers
        wrestlers = [universe.get_wrestler_by_id(wid) for wid in wrestler_ids]
        wrestlers = [w for w in wrestlers if w]  # Filter out None
        
        if len(wrestlers) != 3:
            return jsonify({'error': 'One or more wrestlers not found'}), 404
        
        # Create match draft
        from models.match import MatchDraft, MatchParticipant, BookingBias, MatchImportance
        
        booking_bias = BookingBias(data.get('booking_bias', 'even'))
        importance = MatchImportance(data.get('importance', 'normal'))
        
        match_draft = MatchDraft(
            match_id=f"test_triple_threat_{int(time.time())}",
            side_a=MatchParticipant(
                wrestler_ids=wrestler_ids,
                wrestler_names=[w.name for w in wrestlers],
                is_tag_team=False
            ),
            side_b=MatchParticipant(
                wrestler_ids=[],
                wrestler_names=[],
                is_tag_team=False
            ),
            match_type='triple_threat',
            card_position=5,
            booking_bias=booking_bias,
            importance=importance
        )
        
        # Simulate
        result = match_simulator.simulate_match(
            match_draft,
            wrestlers,
            [],
            universe_state=universe
        )
        
        return jsonify({
            'success': True,
            'match_result': result.to_dict()
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/test/fatal-4way', methods=['POST'])
def api_test_fatal_4way():
    """
    Test fatal 4-way match simulation.
    
    Request body:
    {
        "wrestler_ids": ["w001", "w002", "w003", "w004"]
    }
    """
    try:
        data = request.get_json()
        
        wrestler_ids = data.get('wrestler_ids', [])
        if len(wrestler_ids) != 4:
            return jsonify({'error': 'Fatal 4-way requires exactly 4 wrestlers'}), 400
        
        wrestlers = [universe.get_wrestler_by_id(wid) for wid in wrestler_ids]
        wrestlers = [w for w in wrestlers if w]
        
        if len(wrestlers) != 4:
            return jsonify({'error': 'One or more wrestlers not found'}), 404
        
        from models.match import MatchDraft, MatchParticipant, BookingBias, MatchImportance
        
        match_draft = MatchDraft(
            match_id=f"test_fatal_4way_{int(time.time())}",
            side_a=MatchParticipant(
                wrestler_ids=wrestler_ids,
                wrestler_names=[w.name for w in wrestlers],
                is_tag_team=False
            ),
            side_b=MatchParticipant(
                wrestler_ids=[],
                wrestler_names=[],
                is_tag_team=False
            ),
            match_type='fatal_4way',
            card_position=5,
            booking_bias=BookingBias(data.get('booking_bias', 'even')),
            importance=MatchImportance(data.get('importance', 'normal'))
        )
        
        result = match_simulator.simulate_match(
            match_draft,
            wrestlers,
            [],
            universe_state=universe
        )
        
        return jsonify({
            'success': True,
            'match_result': result.to_dict()
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/test/battle-royal', methods=['POST'])
def api_test_battle_royal():
    """
    Test battle royal match simulation.
    
    Request body:
    {
        "wrestler_ids": ["w001", "w002", ..., "w020"],
        "match_type": "battle_royal"  # or "rumble", "casino_battle_royal"
    }
    """
    try:
        data = request.get_json()
        
        wrestler_ids = data.get('wrestler_ids', [])
        match_type = data.get('match_type', 'battle_royal')
        
        if len(wrestler_ids) < 8:
            return jsonify({'error': 'Battle royals require at least 8 wrestlers'}), 400
        
        wrestlers = [universe.get_wrestler_by_id(wid) for wid in wrestler_ids]
        wrestlers = [w for w in wrestlers if w]
        
        if len(wrestlers) < 8:
            return jsonify({'error': 'Not enough valid wrestlers found'}), 404
        
        from models.match import MatchDraft, MatchParticipant, BookingBias, MatchImportance
        
        match_draft = MatchDraft(
            match_id=f"test_{match_type}_{int(time.time())}",
            side_a=MatchParticipant(
                wrestler_ids=wrestler_ids,
                wrestler_names=[w.name for w in wrestlers],
                is_tag_team=False
            ),
            side_b=MatchParticipant(
                wrestler_ids=[],
                wrestler_names=[],
                is_tag_team=False
            ),
            match_type=match_type,
            card_position=8,
            booking_bias=BookingBias.EVEN,
            importance=MatchImportance.HIGH_DRAMA
        )
        
        result = match_simulator.simulate_match(
            match_draft,
            wrestlers,
            [],
            universe_state=universe
        )
        
        return jsonify({
            'success': True,
            'match_result': result.to_dict()
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/test/random-battle-royal')
def api_test_random_battle_royal():
    """Quick test - generate a random battle royal with 20 wrestlers"""
    try:
        import random
        import time
        
        active_wrestlers = universe.get_active_wrestlers()
        
        if len(active_wrestlers) < 20:
            return jsonify({'error': f'Not enough active wrestlers (need 20, have {len(active_wrestlers)})'}), 400
        
        # Pick random 20
        participants = random.sample(active_wrestlers, 20)
        wrestler_ids = [w.id for w in participants]
        
        from models.match import MatchDraft, MatchParticipant, BookingBias, MatchImportance
        
        match_draft = MatchDraft(
            match_id=f"test_random_br_{int(time.time())}",
            side_a=MatchParticipant(
                wrestler_ids=wrestler_ids,
                wrestler_names=[w.name for w in participants],
                is_tag_team=False
            ),
            side_b=MatchParticipant(
                wrestler_ids=[],
                wrestler_names=[],
                is_tag_team=False
            ),
            match_type='battle_royal',
            card_position=8,
            booking_bias=BookingBias.EVEN,
            importance=MatchImportance.HIGH_DRAMA
        )
        
        result = match_simulator.simulate_match(
            match_draft,
            participants,
            [],
            universe_state=universe
        )
        
        return jsonify({
            'success': True,
            'match_result': result.to_dict()
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/test/random-rumble')
def api_test_random_rumble():
    """Quick test - generate a Royal Rumble with 30 wrestlers"""
    try:
        import random
        import time
        
        active_wrestlers = universe.get_active_wrestlers()
        
        if len(active_wrestlers) < 30:
            return jsonify({'error': f'Not enough active wrestlers (need 30, have {len(active_wrestlers)})'}), 400
        
        # Pick random 30
        participants = random.sample(active_wrestlers, 30)
        wrestler_ids = [w.id for w in participants]
        
        from models.match import MatchDraft, MatchParticipant, BookingBias, MatchImportance
        
        match_draft = MatchDraft(
            match_id=f"test_rumble_{int(time.time())}",
            side_a=MatchParticipant(
                wrestler_ids=wrestler_ids,
                wrestler_names=[w.name for w in participants],
                is_tag_team=False
            ),
            side_b=MatchParticipant(
                wrestler_ids=[],
                wrestler_names=[],
                is_tag_team=False
            ),
            match_type='rumble',
            card_position=8,
            booking_bias=BookingBias.EVEN,
            importance=MatchImportance.HIGH_DRAMA
        )
        
        result = match_simulator.simulate_match(
            match_draft,
            participants,
            [],
            universe_state=universe
        )
        
        return jsonify({
            'success': True,
            'match_result': result.to_dict()
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

# ============================================================================
# API ROUTES - STEP 14: Advanced Booking Systems
# ============================================================================

@app.route('/api/booking/protection-report')
def api_get_protection_report():
    """Get wrestler protection status report"""
    try:
        from creative.protection import protection_manager
        
        wrestlers = universe.get_active_wrestlers()
        summary = protection_manager.get_roster_protection_summary(wrestlers)
        
        return jsonify({
            'success': True,
            'summary': summary
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/booking/rotation-report')
def api_get_rotation_report():
    """Get roster rotation status report"""
    try:
        from creative.rotation import rotation_manager
        
        wrestlers = universe.get_active_wrestlers()
        summary = rotation_manager.get_rotation_summary(wrestlers)
        
        return jsonify({
            'success': True,
            'summary': summary
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/booking/wrestler/<wrestler_id>/record')
def api_get_wrestler_booking_record(wrestler_id):
    """Get a wrestler's booking record (protection data)"""
    try:
        from creative.protection import protection_manager
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'success': False, 'error': 'Wrestler not found'}), 404
        
        record = protection_manager.get_or_create_record(wrestler_id)
        
        return jsonify({
            'success': True,
            'wrestler': {
                'id': wrestler.id,
                'name': wrestler.name,
                'role': wrestler.role
            },
            'record': record.to_dict()
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/booking/wrestler/<wrestler_id>/usage')
def api_get_wrestler_usage(wrestler_id):
    """Get a wrestler's usage stats (rotation data)"""
    try:
        from creative.rotation import rotation_manager
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'success': False, 'error': 'Wrestler not found'}), 404
        
        stats = rotation_manager.get_or_create_stats(wrestler_id)
        
        return jsonify({
            'success': True,
            'wrestler': {
                'id': wrestler.id,
                'name': wrestler.name,
                'role': wrestler.role,
                'fatigue': wrestler.fatigue
            },
            'usage': stats.to_dict()
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/referees')
def api_get_referees():
    """Get all referees in the pool"""
    try:
        from models.referee import referee_pool
        
        return jsonify({
            'success': True,
            'total': len(referee_pool.referees),
            'referees': [ref.to_dict() for ref in referee_pool.referees]
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/special-matches/types')
def api_get_special_match_types():
    """Get all available special match types"""
    try:
        from creative.special_matches import SpecialMatchType, special_match_selector
        
        match_types = []
        
        for match_type in SpecialMatchType:
            match_types.append({
                'value': match_type.value,
                'name': match_type.value.replace('_', ' ').title(),
                'description': special_match_selector.get_match_description(match_type)
            })
        
        return jsonify({
            'success': True,
            'total': len(match_types),
            'match_types': match_types
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/booking-test')
def booking_test_view():
    return render_template('booking_test.html')


# ============================================================================
# API ROUTES - STEP 15: Segments & Promos
# ============================================================================

@app.route('/api/segments/test/promo', methods=['POST'])
def api_test_segment_promo():
    """
    Test promo segment simulation.
    
    Request body:
    {
        "wrestler_id": "w001",
        "tone": "intense",  # Optional
        "feud_id": "feud_xxx"  # Optional
    }
    """
    try:
        from models.segment import SegmentTemplate, SegmentTone
        from simulation.segment_sim import segment_simulator
        
        data = request.get_json()
        
        wrestler_id = data.get('wrestler_id')
        tone_str = data.get('tone', 'intense')
        feud_id = data.get('feud_id')
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        # Create promo draft
        segment_draft = SegmentTemplate.create_promo(
            speaker_id=wrestler.id,
            speaker_name=wrestler.name,
            mic_skill=wrestler.mic,
            feud_id=feud_id,
            tone=SegmentTone(tone_str)
        )
        
        # Simulate
        wrestler_dict = {wrestler.id: wrestler}
        result = segment_simulator.simulate_segment(segment_draft, wrestler_dict)
        
        return jsonify({
            'success': True,
            'segment_result': result.to_dict()
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/segments/test/promo-battle', methods=['POST'])
def api_test_segment_promo_battle():
    """
    Test promo battle simulation.
    
    Request body:
    {
        "wrestler_ids": ["w001", "w002"],
        "feud_id": "feud_xxx"  # Optional
    }
    """
    try:
        from models.segment import SegmentTemplate
        from simulation.segment_sim import segment_simulator
        
        data = request.get_json()
        
        wrestler_ids = data.get('wrestler_ids', [])
        feud_id = data.get('feud_id')
        
        if len(wrestler_ids) < 2:
            return jsonify({'error': 'At least 2 wrestlers required'}), 400
        
        # Get wrestlers
        wrestlers = [universe.get_wrestler_by_id(wid) for wid in wrestler_ids]
        wrestlers = [w for w in wrestlers if w]
        
        if len(wrestlers) < 2:
            return jsonify({'error': 'One or more wrestlers not found'}), 404
        
        # Create promo battle
        participants = [(w.id, w.name, w.mic) for w in wrestlers]
        
        segment_draft = SegmentTemplate.create_promo_battle(
            participants=participants,
            feud_id=feud_id
        )
        
        # Simulate
        wrestler_dict = {w.id: w for w in wrestlers}
        result = segment_simulator.simulate_segment(segment_draft, wrestler_dict)
        
        return jsonify({
            'success': True,
            'segment_result': result.to_dict()
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/segments/test/interview', methods=['POST'])
def api_test_segment_interview():
    """
    Test interview segment.
    
    Request body:
    {
        "wrestler_id": "w001",
        "interviewer_name": "Rachel Stone",  # Optional
        "feud_id": "feud_xxx"  # Optional
    }
    """
    try:
        from models.segment import SegmentTemplate
        from simulation.segment_sim import segment_simulator
        
        data = request.get_json()
        
        wrestler_id = data.get('wrestler_id')
        interviewer_name = data.get('interviewer_name', 'Rachel Stone')
        feud_id = data.get('feud_id')
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        # Create interview
        segment_draft = SegmentTemplate.create_interview(
            interviewer_name=interviewer_name,
            subject_id=wrestler.id,
            subject_name=wrestler.name,
            mic_skill=wrestler.mic,
            feud_id=feud_id
        )
        
        # Simulate
        wrestler_dict = {wrestler.id: wrestler}
        result = segment_simulator.simulate_segment(segment_draft, wrestler_dict)
        
        return jsonify({
            'success': True,
            'segment_result': result.to_dict()
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/segments/test/attack', methods=['POST'])
def api_test_segment_attack():
    """
    Test attack segment.
    
    Request body:
    {
        "attacker_id": "w001",
        "victim_id": "w002",
        "location": "backstage"  # or "in_ring"
    }
    """
    try:
        from models.segment import SegmentTemplate
        from simulation.segment_sim import segment_simulator
        
        data = request.get_json()
        
        attacker_id = data.get('attacker_id')
        victim_id = data.get('victim_id')
        location = data.get('location', 'backstage')
        
        attacker = universe.get_wrestler_by_id(attacker_id)
        victim = universe.get_wrestler_by_id(victim_id)
        
        if not attacker or not victim:
            return jsonify({'error': 'One or both wrestlers not found'}), 404
        
        # Create attack
        segment_draft = SegmentTemplate.create_attack(
            attacker_id=attacker.id,
            attacker_name=attacker.name,
            victim_id=victim.id,
            victim_name=victim.name,
            location=location
        )
        
        # Simulate
        wrestler_dict = {
            attacker.id: attacker,
            victim.id: victim
        }
        result = segment_simulator.simulate_segment(segment_draft, wrestler_dict)
        
        return jsonify({
            'success': True,
            'segment_result': result.to_dict()
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/segments/generate', methods=['POST'])
def api_generate_show_segments():
    """
    Generate segments for a show.
    
    Request body:
    {
        "show_type": "weekly_tv",
        "is_ppv": false,
        "brand": "ROC Alpha"
    }
    """
    try:
        from creative.segments import segment_generator
        
        data = request.get_json()
        
        show_type = data.get('show_type', 'weekly_tv')
        is_ppv = data.get('is_ppv', False)
        brand = data.get('brand', 'ROC Alpha')
        
        # Get roster and feuds for brand
        if brand == 'Cross-Brand':
            brand_roster = universe.get_active_wrestlers()
            active_feuds = universe.feud_manager.get_active_feuds()
            titles = universe.championships
        else:
            brand_roster = universe.get_wrestlers_by_brand(brand)
            active_feuds = []
            for feud in universe.feud_manager.get_active_feuds():
                for pid in feud.participant_ids:
                    wrestler = universe.get_wrestler_by_id(pid)
                    if wrestler and wrestler.primary_brand == brand:
                        active_feuds.append(feud)
                        break
            titles = [c for c in universe.championships 
                     if c.assigned_brand == brand or c.assigned_brand == 'Cross-Brand']
        
        # Generate segments
        segments = segment_generator.generate_segments_for_show(
            show_type=show_type,
            is_ppv=is_ppv,
            brand_roster=brand_roster,
            active_feuds=active_feuds,
            titles=titles
        )
        
        return jsonify({
            'success': True,
            'total': len(segments),
            'segments': [s.to_dict() for s in segments]
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/segments/test/random-promo')
def api_test_segment_random_promo():
    """Quick test - generate a random promo with a high mic skill wrestler"""
    try:
        from models.segment import SegmentTemplate, SegmentTone
        from simulation.segment_sim import segment_simulator
        import random
        
        active_wrestlers = universe.get_active_wrestlers()
        
        # Find wrestlers with high mic skills
        good_talkers = [w for w in active_wrestlers if w.mic >= 60]
        
        if not good_talkers:
            good_talkers = active_wrestlers
        
        if not good_talkers:
            return jsonify({'error': 'No active wrestlers available'}), 400
        
        wrestler = random.choice(good_talkers)
        
        # Create promo
        segment_draft = SegmentTemplate.create_promo(
            speaker_id=wrestler.id,
            speaker_name=wrestler.name,
            mic_skill=wrestler.mic,
            tone=SegmentTone.INTENSE
        )
        
        # Simulate
        wrestler_dict = {wrestler.id: wrestler}
        result = segment_simulator.simulate_segment(segment_draft, wrestler_dict)
        
        return jsonify({
            'success': True,
            'wrestler': {
                'id': wrestler.id,
                'name': wrestler.name,
                'mic': wrestler.mic,
                'alignment': wrestler.alignment
            },
            'segment_result': result.to_dict()
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/segments/test/random-battle')
def api_test_segment_random_battle():
    """Quick test - generate a random promo battle between feuding wrestlers"""
    try:
        from models.segment import SegmentTemplate
        from simulation.segment_sim import segment_simulator
        import random
        
        active_feuds = universe.feud_manager.get_active_feuds()
        
        if not active_feuds:
            return jsonify({'error': 'No active feuds available'}), 400
        
        # Pick a random feud
        feud = random.choice(active_feuds)
        
        if len(feud.participant_ids) < 2:
            return jsonify({'error': 'Selected feud has insufficient participants'}), 400
        
        # Get wrestlers
        wrestler_ids = feud.participant_ids[:2]
        wrestlers = [universe.get_wrestler_by_id(wid) for wid in wrestler_ids]
        wrestlers = [w for w in wrestlers if w]
        
        if len(wrestlers) < 2:
            return jsonify({'error': 'One or more wrestlers not found'}), 404
        
        # Create promo battle
        participants = [(w.id, w.name, w.mic) for w in wrestlers]
        
        segment_draft = SegmentTemplate.create_promo_battle(
            participants=participants,
            feud_id=feud.id
        )
        
        # Simulate
        wrestler_dict = {w.id: w for w in wrestlers}
        result = segment_simulator.simulate_segment(segment_draft, wrestler_dict)
        
        return jsonify({
            'success': True,
            'feud': {
                'id': feud.id,
                'intensity': feud.intensity,
                'participant_names': feud.participant_names
            },
            'segment_result': result.to_dict()
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/booking/generate-segments', methods=['POST'])
def api_booking_generate_segments():
    """
    Generate segments for the current show card.
    Called by the "Auto-Segments" button on the booking page.
    
    Request body:
    {
        "show_type": "weekly_tv",
        "is_ppv": false,
        "brand": "ROC Alpha",
        "max_segments": 3
    }
    """
    try:
        from creative.segments import segment_generator
        
        data = request.get_json() if request.is_json else {}
        
        show_type = data.get('show_type', 'weekly_tv')
        is_ppv = data.get('is_ppv', False)
        brand = data.get('brand', 'ROC Alpha')
        max_segments = data.get('max_segments', 3)
        
        # Get roster and feuds for brand
        if brand == 'Cross-Brand':
            brand_roster = universe.get_active_wrestlers()
            active_feuds = universe.feud_manager.get_active_feuds()
            titles = universe.championships
        else:
            brand_roster = universe.get_wrestlers_by_brand(brand)
            active_feuds = []
            for feud in universe.feud_manager.get_active_feuds():
                for pid in feud.participant_ids:
                    wrestler = universe.get_wrestler_by_id(pid)
                    if wrestler and wrestler.primary_brand == brand:
                        active_feuds.append(feud)
                        break
            titles = [c for c in universe.championships 
                     if c.assigned_brand == brand or c.assigned_brand == 'Cross-Brand']
        
        # Generate segments
        segments = segment_generator.generate_segments_for_show(
            show_type=show_type,
            is_ppv=is_ppv,
            brand_roster=brand_roster,
            active_feuds=active_feuds,
            titles=titles
        )
        
        # Limit to max_segments
        segments = segments[:max_segments]
        
        return jsonify({
            'success': True,
            'total': len(segments),
            'segments': [s.to_dict() for s in segments]
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500



# ============================================================================
# API ROUTES - STEP 16: Scripted Storylines
# ============================================================================

@app.route('/api/storylines')
def api_get_storylines():
    """Get all storylines with their current status"""
    try:
        # Ensure storylines are loaded
        if not storyline_engine.loaded:
            storylines_path = os.path.join(data_dir, 'storylines_year_one.json')
            storyline_engine.load_storylines(storylines_path)
        
        report = storyline_engine.get_storyline_status_report()
        
        return jsonify({
            'success': True,
            **report
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/storylines/<storyline_id>')
def api_get_storyline(storyline_id):
    """Get detailed information about a specific storyline"""
    try:
        storyline = storyline_engine.manager.get_storyline_by_id(storyline_id)
        
        if not storyline:
            return jsonify({'success': False, 'error': 'Storyline not found'}), 404
        
        # Get wrestler names for cast
        cast_with_names = {}
        for role, wrestler_id in storyline.cast_assignments.items():
            wrestler = universe.get_wrestler_by_id(wrestler_id)
            cast_with_names[role] = {
                'id': wrestler_id,
                'name': wrestler.name if wrestler else 'Unknown'
            }
        
        return jsonify({
            'success': True,
            'storyline': storyline.to_dict(),
            'cast_with_names': cast_with_names
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/storylines/active')
def api_get_active_storylines():
    """Get only currently active storylines"""
    try:
        active = storyline_engine.get_active_storylines()
        
        storylines_data = []
        for storyline in active:
            # Add wrestler names
            cast_with_names = {}
            for role, wrestler_id in storyline.cast_assignments.items():
                wrestler = universe.get_wrestler_by_id(wrestler_id)
                cast_with_names[role] = {
                    'id': wrestler_id,
                    'name': wrestler.name if wrestler else 'Unknown'
                }
            
            data = storyline.to_dict()
            data['cast_with_names'] = cast_with_names
            storylines_data.append(data)
        
        return jsonify({
            'success': True,
            'total': len(storylines_data),
            'storylines': storylines_data
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/storylines/check-triggers', methods=['POST'])
def api_check_storyline_triggers():
    """Manually check for storyline triggers (for testing)"""
    try:
        # Get current year/week
        year = universe.current_year
        week = universe.current_week
        
        triggered = storyline_engine.check_and_trigger_storylines(universe, year, week)
        
        triggered_data = []
        for storyline in triggered:
            cast_with_names = {}
            for role, wrestler_id in storyline.cast_assignments.items():
                wrestler = universe.get_wrestler_by_id(wrestler_id)
                cast_with_names[role] = {
                    'id': wrestler_id,
                    'name': wrestler.name if wrestler else 'Unknown'
                }
            
            data = {
                'id': storyline.storyline_id,
                'name': storyline.name,
                'type': storyline.storyline_type.value,
                'description': storyline.description,
                'cast': cast_with_names
            }
            triggered_data.append(data)
        
        return jsonify({
            'success': True,
            'year': year,
            'week': week,
            'triggered_count': len(triggered_data),
            'triggered': triggered_data
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/storylines/process-week', methods=['POST'])
def api_process_storyline_week():
    """Manually process storyline beats for current week (for testing)"""
    try:
        year = universe.current_year
        week = universe.current_week
        
        results = storyline_engine.process_current_week(universe, year, week)
        
        return jsonify({
            'success': True,
            'year': year,
            'week': week,
            'beats_processed': len(results),
            'results': results
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/storylines/preview-segments', methods=['POST'])
def api_preview_storyline_segments():
    """Preview segments that would be generated for storylines"""
    try:
        data = request.get_json() if request.is_json else {}
        
        show_type = data.get('show_type', 'weekly_tv')
        brand = data.get('brand', 'ROC Alpha')
        
        segments = storyline_engine.get_storyline_segments_for_show(
            show_type,
            brand,
            universe
        )
        
        segments_data = [seg.to_dict() for seg in segments]
        
        return jsonify({
            'success': True,
            'show_type': show_type,
            'brand': brand,
            'total': len(segments_data),
            'segments': segments_data
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/storylines')
def storylines_view():
    return render_template('storylines.html')


@app.route('/api/storylines/<storyline_id>/trigger', methods=['POST'])
def api_trigger_storyline_manually(storyline_id):
    """Manually trigger a specific storyline (for testing/debugging)"""
    try:
        from models.storyline import StorylineStatus  # ADD THIS IMPORT
        
        storyline = storyline_engine.manager.get_storyline_by_id(storyline_id)
        
        if not storyline:
            return jsonify({'success': False, 'error': 'Storyline not found'}), 404
        
        if storyline.status.value != 'pending':
            return jsonify({'success': False, 'error': f'Storyline is already {storyline.status.value}'}), 400
        
        # Try to cast the storyline
        if storyline.cast_storyline(universe):
            storyline.status = StorylineStatus.ACTIVE  # FIXED: Use imported StorylineStatus
            storyline.triggered_year = universe.current_year
            storyline.triggered_week = universe.current_week
            
            # Save state
            storyline_state = storyline_engine.save_state()
            database.save_storyline_state(storyline_state)
            database.conn.commit()
            
            # Get cast names
            cast_with_names = {}
            for role, wrestler_id in storyline.cast_assignments.items():
                wrestler = universe.get_wrestler_by_id(wrestler_id)
                cast_with_names[role] = {
                    'id': wrestler_id,
                    'name': wrestler.name if wrestler else 'Unknown'
                }
            
            return jsonify({
                'success': True,
                'message': f'Storyline "{storyline.name}" manually triggered',
                'storyline': storyline.to_dict(),
                'cast_with_names': cast_with_names
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to cast storyline - required wrestlers not available'
            }), 400
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/storylines/reload', methods=['POST'])
def api_reload_storylines():
    """Reload storylines from JSON file (resets all progress)"""
    try:
        # Clear current storylines
        storyline_engine.manager.storylines = []
        storyline_engine.manager.completed_storylines = []
        
        # Reload from file
        storylines_path = os.path.join(data_dir, 'storylines_year_one.json')
        storyline_engine.load_storylines(storylines_path)
        
        # Save to database
        storyline_state = storyline_engine.save_state()
        database.save_storyline_state(storyline_state)
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'message': 'Storylines reloaded from file',
            'total_loaded': len(storyline_engine.manager.storylines)
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# API ROUTES - STEP 17: End-of-Year Awards
# ============================================================================

from simulation.awards_engine import awards_engine
from persistence.awards_db import (
    save_awards_ceremony,
    get_awards_ceremony,
    get_all_awards_ceremonies,
    get_wrestler_awards
)


@app.route('/api/awards/calculate/<int:year>', methods=['POST'])
def api_calculate_year_awards(year: int):
    """
    Calculate awards for a completed year.
    Typically called automatically at the end of Week 52.
    """
    try:
        print(f"\n🏆 Calculating Year {year} Awards...")
        
        # Calculate awards
        ceremony = awards_engine.calculate_year_end_awards(year, database, universe)
        
        # Save to database
        save_awards_ceremony(database, ceremony)
        
        return jsonify({
            'success': True,
            'message': f'Calculated {len(ceremony.awards)} awards for Year {year}',
            'ceremony': ceremony.to_dict()
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/awards/<int:year>')
def api_get_year_awards(year: int):
    """Get awards ceremony for a specific year"""
    try:
        ceremony = get_awards_ceremony(database, year)
        
        if not ceremony:
            return jsonify({
                'success': False,
                'error': f'No awards found for Year {year}'
            }), 404
        
        return jsonify({
            'success': True,
            'ceremony': ceremony
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/awards/all')
def api_get_all_awards():
    """Get all awards ceremonies"""
    try:
        ceremonies = get_all_awards_ceremonies(database)
        
        return jsonify({
            'success': True,
            'total': len(ceremonies),
            'ceremonies': ceremonies
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/awards/wrestler/<wrestler_id>')
def api_get_wrestler_awards_list(wrestler_id: str):
    """Get all awards won by a wrestler"""
    try:
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        
        if not wrestler:
            return jsonify({'success': False, 'error': 'Wrestler not found'}), 404
        
        awards = get_wrestler_awards(database, wrestler_id)
        
        return jsonify({
            'success': True,
            'wrestler_id': wrestler_id,
            'wrestler_name': wrestler.name,
            'total_awards': len(awards),
            'awards': awards
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/awards/latest')
def api_get_latest_awards():
    """Get the most recent awards ceremony"""
    try:
        ceremonies = get_all_awards_ceremonies(database)
        
        if not ceremonies:
            return jsonify({
                'success': False,
                'error': 'No awards ceremonies found'
            }), 404
        
        # Most recent is first (DESC order)
        latest = ceremonies[0]
        
        return jsonify({
            'success': True,
            'ceremony': latest
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/awards')
def awards_view():
    return render_template('awards.html')


# ============================================================================
# API ROUTES - STEP 18: Create-A-Wrestler
# ============================================================================

from models.caw import CAWValidator, CAWFactory, CAWPresets


@app.route('/api/caw/presets')
def api_get_caw_presets():
    """Get all available CAW presets"""
    try:
        presets = CAWPresets.get_all_presets()
        
        return jsonify({
            'success': True,
            'total': len(presets),
            'presets': presets
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/caw/validate', methods=['POST'])
def api_validate_caw():
    """
    Validate CAW data without creating the wrestler.
    Useful for real-time form validation.
    """
    try:
        data = request.get_json()
        
        is_valid, errors = CAWValidator.validate_all(data)
        
        # Calculate preview stats
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


@app.route('/api/caw/create', methods=['POST'])
def api_create_wrestler():
    """
    Create a new custom wrestler and add to roster.
    
    Request body:
    {
        "name": "John Doe",
        "age": 28,
        "gender": "Male",
        "alignment": "Face",
        "role": "Midcard",
        "primary_brand": "ROC Alpha",
        "brawling": 70,
        "technical": 65,
        "speed": 75,
        "mic": 60,
        "psychology": 70,
        "stamina": 68,
        "salary_per_show": 8000,
        "contract_weeks": 52,
        "years_experience": 5,
        "is_major_superstar": false
    }
    """
    try:
        data = request.get_json()
        
        print(f"\n{'='*60}")
        print(f"🎨 CREATE-A-WRESTLER REQUEST")
        print(f"{'='*60}")
        print(f"Name: {data.get('name')}")
        print(f"Brand: {data.get('primary_brand')}")
        print(f"Role: {data.get('role')}")
        print(f"{'='*60}\n")
        
        # Validate all data
        is_valid, errors = CAWValidator.validate_all(data)
        
        if not is_valid:
            return jsonify({
                'success': False,
                'error': 'Validation failed',
                'errors': errors
            }), 400
        
        # Check for duplicate name
        existing_wrestlers = database.get_all_wrestlers(active_only=False)
        existing_names = [w['name'].lower() for w in existing_wrestlers]
        
        if data['name'].strip().lower() in existing_names:
            return jsonify({
                'success': False,
                'error': 'A wrestler with this name already exists'
            }), 400
        
        # Generate wrestler ID
        wrestler_id = CAWFactory.generate_wrestler_id(database)
        
        print(f"✅ Generated ID: {wrestler_id}")
        
        # Create wrestler object
        wrestler = CAWFactory.create_wrestler(
            data=data,
            wrestler_id=wrestler_id,
            current_year=universe.current_year,
            current_week=universe.current_week
        )
        
        print(f"✅ Created wrestler object: {wrestler.name}")
        print(f"   Overall Rating: {wrestler.overall_rating}")
        print(f"   Salary: ${wrestler.contract.salary_per_show:,}/show")
        
        # Save to database
        database.save_wrestler(wrestler)
        database.conn.commit()
        
        print(f"✅ Saved to database")
        
        # Initialize empty stats
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
        import traceback
        error_trace = traceback.format_exc()
        
        print(f"\n❌ CAW Creation Error:")
        print(error_trace)
        print()
        
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': error_trace
        }), 500


@app.route('/api/caw/next-id')
def api_get_next_wrestler_id():
    """Get the next available wrestler ID (for preview)"""
    try:
        next_id = CAWFactory.generate_wrestler_id(database)
        
        return jsonify({
            'success': True,
            'next_id': next_id
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/caw/calculate-overall', methods=['POST'])
def api_calculate_overall():
    """Calculate overall rating for given attributes"""
    try:
        data = request.get_json()
        
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


@app.route('/api/caw/random', methods=['POST'])
def api_create_random_wrestler():
    """
    Create a random wrestler with randomized attributes.
    Optional: specify gender, brand, or role
    """
    try:
        import random
        
        data = request.get_json() if request.is_json else {}
        
        # Random or specified values
        gender = data.get('gender', random.choice(['Male', 'Female']))
        brand = data.get('primary_brand', random.choice(['ROC Alpha', 'ROC Velocity', 'ROC Vanguard']))
        role = data.get('role', random.choice(['Upper Midcard', 'Midcard', 'Lower Midcard']))
        alignment = data.get('alignment', random.choice(['Face', 'Heel', 'Tweener']))
        
        # Generate random name
        first_names_male = ['Jake', 'Marcus', 'Tyler', 'Ryan', 'Chris', 'Alex', 'Jordan', 'Max', 'Cole', 'Finn']
        first_names_female = ['Luna', 'Ember', 'Jade', 'Phoenix', 'Storm', 'Nova', 'Raven', 'Blaze', 'Ivy', 'Sky']
        last_names = ['Steel', 'Shadow', 'Thunder', 'Phoenix', 'Knight', 'Storm', 'Blaze', 'Savage', 'Viper', 'Wolf']
        
        first = random.choice(first_names_male if gender == 'Male' else first_names_female)
        last = random.choice(last_names)
        name = f"{first} {last}"
        
        # Randomized attributes (weighted toward role)
        def random_attribute(base_min=40, base_max=80):
            return random.randint(base_min, base_max)
        
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
            'alignment': alignment,
            'role': role,
            'primary_brand': brand,
            'brawling': random_attribute(attr_min, attr_max),
            'technical': random_attribute(attr_min, attr_max),
            'speed': random_attribute(attr_min, attr_max),
            'mic': random_attribute(attr_min, attr_max),
            'psychology': random_attribute(attr_min, attr_max),
            'stamina': random_attribute(attr_min, attr_max),
            'years_experience': random.randint(1, 12),
            'is_major_superstar': False
        }
        
        # Calculate salary
        overall = CAWFactory.calculate_overall_preview(random_data)
        salary = CAWFactory.get_suggested_salary(role, overall)
        
        random_data['salary_per_show'] = salary
        random_data['contract_weeks'] = random.choice([52, 104, 156])  # 1, 2, or 3 years
        
        # Validate
        is_valid, errors = CAWValidator.validate_all(random_data)
        
        if not is_valid:
            return jsonify({
                'success': False,
                'error': 'Generated data failed validation',
                'errors': errors
            }), 500
        
        # Generate ID
        wrestler_id = CAWFactory.generate_wrestler_id(database)
        
        # Create wrestler
        wrestler = CAWFactory.create_wrestler(
            data=random_data,
            wrestler_id=wrestler_id,
            current_year=universe.current_year,
            current_week=universe.current_week
        )
        
        # Save
        database.save_wrestler(wrestler)
        database.conn.commit()
        
        # Initialize stats
        database.update_wrestler_stats_cache(wrestler_id)
        database.conn.commit()
        
        print(f"🎲 Random wrestler created: {wrestler.name} ({wrestler_id})")
        
        return jsonify({
            'success': True,
            'message': f'Random wrestler "{wrestler.name}" created',
            'wrestler': wrestler.to_dict()
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/caw/test/create-sample', methods=['POST'])
def api_test_create_sample_wrestler():
    """
    Quick test endpoint to create a sample wrestler.
    Useful for testing the CAW system.
    """
    try:
        import random
        
        # Use random name from pool
        first_names = [
             # Original
             'Sample', 'Test', 'Demo', 'Trial',
             # Test/Dev Related
             'Mock', 'Dummy', 'Example', 'Pilot', 'Proto', 'Draft', 'Preview', 'Sketch',
             # Cool/Strong Names
             'Max', 'Rex', 'Nova', 'Blaze', 'Ace', 'Dash', 'Jet', 'Hawk',
             'Wolf', 'Raven', 'Hunter', 'Atlas', 'Zero', 'Neo', 'Echo', 'Apex',
             'Cipher', 'Vector', 'Nexus', 'Prime', 'Onyx', 'Axel', 'Zane', 'Kai',
             'Drake', 'Jax', 'Finn', 'Cole', 'Reed', 'Blake', 'Chase', 'Grant'
             ]
        
        last_names = [
            # Original
            'Alpha', 'Beta', 'Gamma', 'Delta', 'Thunder', 'Lightning',
            'Storm', 'Phoenix', 'Titan', 'Steel', 'Knight', 'Shadow',
            # Elements/Nature
            'Blaze', 'Frost', 'Flame', 'Ember', 'Aurora', 'Vortex', 'Cyclone', 'Avalanche',
            # Metals/Materials
            'Iron', 'Bronze', 'Silver', 'Chrome', 'Diamond', 'Obsidian', 'Granite', 'Cobalt',
            # Power Words
            'Fury', 'Valor', 'Glory', 'Legend', 'Striker', 'Blade', 'Shield', 'Hammer',
            # Animals
            'Falcon', 'Viper', 'Dragon', 'Griffin', 'Panther', 'Hawk', 'Raven', 'Wolf',
            # Other Cool Words
            'Surge', 'Pulse', 'Core', 'Zenith', 'Apex', 'Edge', 'Rider', 'Hunter',
            'Specter', 'Phantom', 'Wraith', 'Sentinel', 'Guardian', 'Warden', 'Ranger', 'Slayer'
        ]
        
        # Keep trying names until we find one that doesn't exist
        existing_names = [w['name'].lower() for w in database.get_all_wrestlers(active_only=False)]
        
        max_attempts = 20
        for _ in range(max_attempts):
            first = random.choice(first_names)
            last = random.choice(last_names)
            sample_name = f"{first} {last}"
            
            if sample_name.lower() not in existing_names:
                break
        else:
            # If all combinations exist, just use timestamp
            import time
            sample_name = f"Test Wrestler"  # This will fail, but that's OK for testing
        
        sample_data = {
            'name': sample_name,
            'age': 28,
            'gender': 'Male',
            'alignment': 'Face',
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
        
        # Validate
        is_valid, errors = CAWValidator.validate_all(sample_data)
        
        if not is_valid:
            return jsonify({
                'success': False,
                'error': 'Sample data validation failed',
                'errors': errors
            }), 500
        
        # Generate ID
        wrestler_id = CAWFactory.generate_wrestler_id(database)
        
        # Create
        wrestler = CAWFactory.create_wrestler(
            data=sample_data,
            wrestler_id=wrestler_id,
            current_year=universe.current_year,
            current_week=universe.current_week
        )
        
        # Save
        database.save_wrestler(wrestler)
        database.conn.commit()
        
        # Initialize stats
        database.update_wrestler_stats_cache(wrestler_id)
        database.conn.commit()
        
        print(f"✅ Test wrestler created: {wrestler.name} ({wrestler_id})")
        
        return jsonify({
            'success': True,
            'message': f'Sample wrestler "{wrestler.name}" created',
            'wrestler': wrestler.to_dict()
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500



# ============================================================================
# API ROUTES - STEP 19: Brand Draft
# ============================================================================

@app.route('/api/draft/initiate', methods=['POST'])
def api_initiate_draft():
    """
    Initiate a new brand draft.
    
    Request body:
    {
        "format": "snake",  # or "rotating", "lottery"
        "randomize_order": true
    }
    """
    try:
        data = request.get_json() if request.is_json else {}
        
        # Get format
        format_str = data.get('format', 'snake')
        format_type = DraftFormat(format_str)
        
        # Load GM data if not loaded
        if not draft_manager.gm_data:
            draft_manager.load_gm_data(data_dir)
        
        # Check eligibility first
        eligible, message, weeks_until = draft_manager.check_draft_eligibility(
            universe.current_year,
            universe.current_week
        )
        
        if not eligible:
            return jsonify({
                'success': False,
                'error': message,
                'weeks_until_eligible': weeks_until
            }), 400
        
        # Initiate draft
        draft = draft_manager.initiate_draft(
            universe_state=universe,
            year=universe.current_year,
            week=universe.current_week,
            format_type=format_type
        )
        
        # Randomize order if requested
        if data.get('randomize_order', False):
            draft.randomize_draft_order()
        
        return jsonify({
            'success': True,
            'message': 'Draft initiated',
            'draft': {
                'draft_id': draft.draft_id,
                'format': draft.format_type.value,
                'total_eligible': len(draft.eligible_wrestlers),
                'total_exempt': len(draft.exemptions),
                'draft_order': draft.base_draft_order,
                'current_picking': draft.get_current_picking_brand()
            }
        })
    
    except ValueError as e:
        # This catches the eligibility check error from draft_manager
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"\n❌ Draft initiation error:")
        print(error_trace)
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': error_trace
        }), 500


@app.route('/api/draft/current')
def api_get_current_draft():
    """Get current draft status"""
    try:
        if not draft_manager.current_draft:
            return jsonify({
                'success': False,
                'error': 'No draft currently active'
            }), 404
        
        draft = draft_manager.current_draft
        
        return jsonify({
            'success': True,
            'draft': draft.to_dict()
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/draft/exemptions')
def api_get_draft_exemptions():
    """Get all draft exemptions"""
    try:
        if not draft_manager.current_draft:
            return jsonify({
                'success': False,
                'error': 'No draft currently active'
            }), 404
        
        exemptions = draft_manager.current_draft.exemptions
        
        return jsonify({
            'success': True,
            'total': len(exemptions),
            'exemptions': [
                {
                    'wrestler_id': e.wrestler_id,
                    'wrestler_name': e.wrestler_name,
                    'reason': e.reason.value,
                    'description': e.description,
                    'expires_week': e.expires_week
                }
                for e in exemptions
            ]
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/draft/eligible')
def api_get_eligible_wrestlers():
    """Get all wrestlers eligible for draft"""
    try:
        if not draft_manager.current_draft:
            return jsonify({
                'success': False,
                'error': 'No draft currently active'
            }), 404
        
        draft = draft_manager.current_draft
        
        # Filter to only those still in pool
        available = [w for w in draft.eligible_wrestlers if w['id'] in draft.draft_pool]
        
        # Sort by overall rating
        available.sort(key=lambda x: x['overall'], reverse=True)
        
        return jsonify({
            'success': True,
            'total': len(available),
            'wrestlers': available
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/draft/simulate', methods=['POST'])
def api_simulate_draft():
    """
    Simulate the entire draft with AI GMs.
    
    Request body (optional):
    {
        "pause_between_picks": false  # For UI animation
    }
    """
    try:
        if not draft_manager.current_draft:
            return jsonify({
                'success': False,
                'error': 'No draft currently active'
            }), 404
        
        # Store reference to draft before simulation
        # (simulation may clear current_draft)
        draft = draft_manager.current_draft
        
        # Run simulation
        summary = draft_manager.simulate_full_draft(universe)
        
        # Get detailed report using the stored draft reference
        # (not current_draft which may be None now)
        report = draft_manager.get_draft_report(draft)
        
        return jsonify({
            'success': True,
            'message': 'Draft simulation complete',
            'summary': summary,
            'report': report
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/draft/make-pick', methods=['POST'])
def api_make_draft_pick():
    """
    Make a single draft pick (for manual drafting).
    
    Request body:
    {
        "wrestler_id": "w001"
    }
    """
    try:
        if not draft_manager.current_draft:
            return jsonify({
                'success': False,
                'error': 'No draft currently active'
            }), 404
        
        data = request.get_json()
        wrestler_id = data.get('wrestler_id')
        
        if not wrestler_id:
            return jsonify({
                'success': False,
                'error': 'wrestler_id required'
            }), 400
        
        draft = draft_manager.current_draft
        current_brand = draft.get_current_picking_brand()
        
        if not current_brand:
            return jsonify({
                'success': False,
                'error': 'Draft is complete or no brand currently picking'
            }), 400
        
        # Make the pick
        pick = draft.make_pick(current_brand, wrestler_id, 0.0)
        
        return jsonify({
            'success': True,
            'pick': {
                'overall_pick': pick.overall_pick,
                'brand': pick.brand,
                'wrestler_name': pick.wrestler_name,
                'wrestler_role': pick.wrestler_role
            },
            'next_picking': draft.get_current_picking_brand(),
            'is_complete': draft.is_complete
        })
    
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/draft/history')
def api_get_draft_history():
    """Get history of all drafts"""
    try:
        history = []
        
        for draft in draft_manager.draft_history:
            history.append({
                'draft_id': draft.draft_id,
                'year': draft.year,
                'week': draft.week,
                'format': draft.format_type.value,
                'total_picks': draft.overall_pick_count,
                'total_trades': len(draft.trades)
            })
        
        return jsonify({
            'success': True,
            'total': len(history),
            'drafts': history
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/draft/gms')
def api_get_draft_gms():
    """Get GM information for draft"""
    try:
        # Load GM data if not loaded
        if not draft_manager.gm_data:
            draft_manager.load_gm_data(data_dir)
        
        gms = draft_manager.gm_data.get('general_managers', [])
        personalities = draft_manager.gm_data.get('personality_descriptions', {})
        
        return jsonify({
            'success': True,
            'gms': gms,
            'personality_types': personalities
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/draft')
def draft_view():
    return render_template('draft.html')



@app.route('/api/draft/check-eligibility')
def api_check_draft_eligibility():
    """Check if a draft can be initiated (15 week cooldown)"""
    try:
        # Load GM data if needed
        if not draft_manager.gm_data:
            draft_manager.load_gm_data(data_dir)
        
        # Check eligibility
        eligible, message, weeks_until = draft_manager.check_draft_eligibility(
            universe.current_year,
            universe.current_week
        )
        
        if not eligible:
            # Get last draft info
            last_draft = draft_manager.get_last_draft()
            
            return jsonify({
                'success': True,
                'eligible': False,
                'message': message,
                'weeks_until_eligible': weeks_until,
                'last_draft': {
                    'year': last_draft.year,
                    'week': last_draft.week
                } if last_draft else None
            })
        
        return jsonify({
            'success': True,
            'eligible': True,
            'message': 'Draft can be initiated'
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/draft/debug/clear-history', methods=['POST'])
def api_clear_draft_history():
    """DEBUG: Clear draft history to allow testing"""
    try:
        draft_manager.draft_history = []
        draft_manager.current_draft = None
        
        return jsonify({
            'success': True,
            'message': 'Draft history cleared. You can now initiate a new draft.'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500



# ============================================================================
# API ROUTES - INJURY SYSTEM
# ============================================================================

from simulation.injuries import injury_manager, InjurySeverity

@app.route('/injuries')
def injuries_view():
    """Injury/Rehab Center view"""
    return render_template('injuries.html')


@app.route('/api/injuries/report')
def api_injury_report():
    """Get comprehensive injury report"""
    try:
        roster = universe.get_active_wrestlers()
        report = injury_manager.get_injury_report(roster)
        
        return jsonify({
            'success': True,
            'report': report
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/injuries/active')
def api_get_active_injuries():
    """Get all currently injured wrestlers with details"""
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


@app.route('/api/injuries/<wrestler_id>')
def api_get_wrestler_injury(wrestler_id):
    """Get specific wrestler's injury details"""
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


@app.route('/api/injuries/<wrestler_id>/apply', methods=['POST'])
def api_apply_injury(wrestler_id):
    """Manually apply an injury to a wrestler"""
    try:
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        
        if not wrestler:
            return jsonify({'success': False, 'error': 'Wrestler not found'}), 404
        
        data = request.get_json()
        
        severity = data.get('severity', 'Moderate')
        description = data.get('description', 'Unspecified injury')
        weeks_out = data.get('weeks_out', 4)
        
        # Apply injury
        wrestler.apply_injury(severity, description, weeks_out)
        
        # Save to database
        universe.save_wrestler(wrestler)
        
        return jsonify({
            'success': True,
            'message': f'Injury applied to {wrestler.name}',
            'wrestler': wrestler.to_dict()
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/injuries/<wrestler_id>/heal', methods=['POST'])
def api_heal_injury(wrestler_id):
    """Manually heal a wrestler's injury"""
    try:
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        
        if not wrestler:
            return jsonify({'success': False, 'error': 'Wrestler not found'}), 404
        
        if not wrestler.is_injured:
            return jsonify({'success': False, 'error': 'Wrestler is not injured'}), 404
        
        data = request.get_json()
        weeks_to_heal = data.get('weeks', wrestler.injury.weeks_remaining)
        
        # Heal injury
        wrestler.heal_injury(weeks_to_heal)
        
        # Remove from detailed tracking if fully healed
        if not wrestler.is_injured and wrestler_id in injury_manager.active_injuries:
            del injury_manager.active_injuries[wrestler_id]
        
        # Save to database
        universe.save_wrestler(wrestler)
        
        return jsonify({
            'success': True,
            'message': f'{wrestler.name} {"fully healed" if not wrestler.is_injured else "partially healed"}',
            'wrestler': wrestler.to_dict()
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/injuries/<wrestler_id>/rush-return', methods=['POST'])
def api_rush_return(wrestler_id):
    """Attempt to rush a wrestler back from injury early"""
    try:
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        
        if not wrestler:
            return jsonify({'success': False, 'error': 'Wrestler not found'}), 404
        
        if not wrestler.is_injured:
            return jsonify({'success': False, 'error': 'Wrestler is not injured'}), 404
        
        injury_details = injury_manager.active_injuries.get(wrestler_id)
        
        if not injury_details:
            # Simple injury - can't rush
            return jsonify({
                'success': False,
                'message': 'Cannot rush return from this injury'
            })
        
        success, message = injury_manager.simulator.attempt_rushed_return(wrestler, injury_details)
        
        if success and wrestler_id in injury_manager.active_injuries:
            del injury_manager.active_injuries[wrestler_id]
        
        # Save to database
        universe.save_wrestler(wrestler)
        
        return jsonify({
            'success': success,
            'message': message,
            'wrestler': wrestler.to_dict()
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/injuries/create-angle', methods=['POST'])
def api_create_injury_angle():
    """Create an injury angle to write off an injured wrestler"""
    try:
        data = request.get_json()
        wrestler_id = data.get('wrestler_id')
        attacker_id = data.get('attacker_id')
        
        injured_wrestler = universe.get_wrestler_by_id(wrestler_id)
        
        if not injured_wrestler:
            return jsonify({'success': False, 'error': 'Wrestler not found'}), 404
        
        attacker = None
        if attacker_id:
            attacker = universe.get_wrestler_by_id(attacker_id)
        
        # Generate injury angle
        angle = injury_manager.create_injury_writeoff(
            injured_wrestler=injured_wrestler,
            roster=universe.get_active_wrestlers(),
            existing_feuds=universe.feud_manager.get_active_feuds()
        )
        
        # Create or intensify feud if angle creates one
        if angle.get('creates_feud') and attacker:
            from models.feud import FeudType
            
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


@app.route('/api/injuries/return-angle', methods=['POST'])
def api_create_return_angle():
    """Create a return angle for a wrestler coming back from injury"""
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
        
        # Generate return angle
        angle = injury_manager.angle_generator.generate_return_angle(
            returning_wrestler=returning_wrestler,
            is_surprise=is_surprise,
            target=target
        )
        
        # Apply boosts
        returning_wrestler.adjust_momentum(angle['momentum_boost'])
        returning_wrestler.adjust_popularity(angle['popularity_boost'])
        
        # Save wrestler
        universe.save_wrestler(returning_wrestler)
        
        return jsonify({
            'success': True,
            'angle': angle
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/injuries/process-weekly', methods=['POST'])
def api_process_weekly_recovery():
    """Process weekly recovery for all injured wrestlers"""
    try:
        roster = universe.get_active_wrestlers()
        recovery_updates = injury_manager.process_weekly_recovery(
            roster,
            universe.current_year,
            universe.current_week
        )
        
        # Save all wrestlers
        for wrestler in roster:
            universe.save_wrestler(wrestler)
        
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'updates': recovery_updates
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/injuries/medical-staff')
def api_get_medical_staff():
    """Get current medical staff configuration"""
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


@app.route('/api/injuries/medical-staff/upgrade', methods=['POST'])
def api_upgrade_medical_staff():
    """Upgrade medical staff tier"""
    try:
        data = request.get_json()
        new_tier = data.get('tier', 'Standard')
        
        from simulation.injuries import MedicalStaff, InjuryManager
        
        if new_tier not in MedicalStaff.STAFF_TIERS:
            return jsonify({'success': False, 'error': 'Invalid tier'}), 400
        
        # Calculate cost
        old_cost = injury_manager.simulator.staff_config['cost_per_week']
        new_cost = MedicalStaff.STAFF_TIERS[new_tier]['cost_per_week']
        upgrade_fee = (new_cost - old_cost) * 4  # One month upgrade fee
        
        if universe.balance < upgrade_fee:
            return jsonify({
                'success': False,
                'error': f'Insufficient funds. Need ${upgrade_fee:,}'
            }), 400
        
        # Apply upgrade
        injury_manager.simulator.medical_staff_tier = new_tier
        injury_manager.simulator.staff_config = MedicalStaff.STAFF_TIERS[new_tier]
        
        # Deduct cost
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


@app.route('/api/booking/generate-with-injuries', methods=['POST'])
def api_generate_show_card_with_injuries():
    """Generate show card that includes injury angles for recently injured wrestlers"""
    try:
        # First generate normal card
        response = api_generate_show_card()
        
        if response.status_code != 200:
            return response
        
        show_draft_data = response.get_json()['show_draft']
        
        # Check for wrestlers who need injury write-offs
        injured_needing_angles = []
        
        for wrestler in universe.get_active_wrestlers():
            if wrestler.is_injured and wrestler.injury.severity in ['Severe', 'Career Threatening']:
                # Check if they were injured recently (within 2 weeks)
                injury_details = injury_manager.database.execute_raw(
                    'SELECT * FROM injury_details WHERE wrestler_id = ?',
                    (wrestler.id,)
                )
                
                if injury_details:
                    injury = injury_details[0]
                    weeks_since_injury = (universe.current_week - injury['occurred_week'])
                    
                    # Handle year wraparound
                    if weeks_since_injury < 0:
                        weeks_since_injury += 52
                    
                    if weeks_since_injury <= 2:
                        injured_needing_angles.append(wrestler)
        
        # Add injury angle segments for each
        if injured_needing_angles and 'segments' not in show_draft_data:
            show_draft_data['segments'] = []
        
        for injured_wrestler in injured_needing_angles[:2]:  # Max 2 injury angles per show
            print(f"   Adding injury angle for {injured_wrestler.name}")
            
            # Generate injury angle
            angle = injury_manager.create_injury_writeoff(
                injured_wrestler=injured_wrestler,
                roster=universe.get_active_wrestlers(),
                existing_feuds=universe.feud_manager.get_active_feuds(),
                year=universe.current_year,
                week=universe.current_week,
                show_id=show_draft_data['show_id'],
                show_name=show_draft_data['show_name']
            )
            
            # Add as segment to show
            segment = {
                'segment_id': f"injury_{injured_wrestler.id}",
                'segment_type': 'backstage_attack',
                'participants': [
                    {
                        'wrestler_id': angle['attacker_id'],
                        'wrestler_name': angle['attacker_name'],
                        'role': 'attacker'
                    },
                    {
                        'wrestler_id': injured_wrestler.id,
                        'wrestler_name': injured_wrestler.name,
                        'role': 'victim'
                    }
                ],
                'duration_minutes': 5,
                'card_position': 2,  # Early in the show
                'description': angle['description']
            }
            
            show_draft_data['segments'].append(segment)
            
            # Create or intensify feud
            if angle.get('creates_feud') and angle.get('attacker_id'):
                from models.feud import FeudType
                
                feud = universe.feud_manager.create_feud(
                    feud_type=FeudType.PERSONAL,
                    participant_ids=[injured_wrestler.id, angle['attacker_id']],
                    participant_names=[injured_wrestler.name, angle['attacker_name']],
                    year=universe.current_year,
                    week=universe.current_week,
                    initial_intensity=angle.get('feud_intensity', 50)
                )
                
                universe.save_feud(feud)
                print(f"      Created injury feud: {injured_wrestler.name} vs {angle['attacker_name']}")
        
        return jsonify({
            'success': True,
            'show_draft': show_draft_data,
            'injury_angles_added': len(injured_needing_angles)
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/injuries/weekly-recovery', methods=['POST'])
def api_weekly_injury_recovery():
    """Process weekly recovery for all injured wrestlers (called automatically after each show)"""
    try:
        # Get all wrestlers
        roster = universe.wrestlers  # All wrestlers, not just active
        
        # Process recovery
        recovery_updates = injury_manager.process_weekly_recovery(
            roster,
            universe.current_year,
            universe.current_week
        )
        
        # Save all wrestlers that were updated
        for update in recovery_updates:
            wrestler = universe.get_wrestler_by_id(update['wrestler_id'])
            if wrestler:
                universe.save_wrestler(wrestler)
        
        # Deduct medical staff costs from balance
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
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500



# ============================================================================
# API ROUTES - STEP 21: Championship Hierarchy & Title Situations
# ============================================================================

from models.championship_hierarchy import (
    championship_hierarchy, TitleTier, VacancyReason, 
    TitleSituationType, TitleSituation
)
from creative.title_situations import (
    title_situation_manager, TitleDecision, ResolutionMethod
)
from persistence.championship_db import (
    create_championship_tables, save_vacancy, get_title_vacancies,
    get_all_active_vacancies, fill_vacancy, save_defense, get_title_defenses,
    get_last_defense, save_guaranteed_shot, get_active_shots_for_title,
    get_wrestler_shots, use_guaranteed_shot, log_title_situation,
    get_title_situation_log, get_defense_stats
)


@app.route('/api/championships/<title_id>/situation')
def api_get_title_situation(title_id):
    """Get current situation/status for a championship"""
    try:
        championship = universe.get_championship_by_id(title_id)
        
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        # Get holder
        holder = None
        if championship.current_holder_id:
            holder = universe.get_wrestler_by_id(championship.current_holder_id)
        
        # Get situation
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
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/championships/<title_id>/analyze-injury')
def api_analyze_champion_injury(title_id):
    """Analyze an injured champion situation with recommendations"""
    try:
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
        
        # Get upcoming PPV info
        next_ppv = universe.calendar.get_next_ppv()
        upcoming_ppv_weeks = None
        if next_ppv:
            upcoming_ppv_weeks = next_ppv.week - universe.current_week
            if upcoming_ppv_weeks < 0:
                upcoming_ppv_weeks += 52
        
        # Analyze
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
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/championships/<title_id>/vacate', methods=['POST'])
def api_vacate_championship(title_id):
    """
    Vacate a championship.
    
    Request body:
    {
        "reason": "injury",  # injury, contract_expiration, released, etc.
        "show_name": "ROC Alpha Week 15",
        "notes": "Champion injured for 6 months",
        "attacker_id": "w002"  # Optional - for injury angle
    }
    """
    try:
        data = request.get_json() if request.is_json else {}
        
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        if championship.is_vacant:
            return jsonify({'success': False, 'error': 'Championship is already vacant'}), 400
        
        champion = universe.get_wrestler_by_id(championship.current_holder_id)
        if not champion:
            return jsonify({'success': False, 'error': 'Champion not found'}), 404
        
        # Get parameters
        reason_str = data.get('reason', 'injury')
        try:
            reason = VacancyReason(reason_str)
        except ValueError:
            reason = VacancyReason.RELINQUISHED
        
        show_name = data.get('show_name', f'Week {universe.current_week} Show')
        show_id = f"show_y{universe.current_year}_w{universe.current_week}"
        notes = data.get('notes', '')
        
        # Get attacker if specified
        attacker = None
        if data.get('attacker_id'):
            attacker = universe.get_wrestler_by_id(data['attacker_id'])
        
        # Execute decision
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
            # Save to database
            if result.vacancy_id:
                vacancy = universe.championship_hierarchy.get_vacancy_for_title(title_id)
                if vacancy:
                    save_vacancy(database, vacancy.to_dict())
            
            if result.guaranteed_shot_id:
                for shot in universe.championship_hierarchy.guaranteed_shots:
                    if shot.shot_id == result.guaranteed_shot_id:
                        save_guaranteed_shot(database, shot.to_dict())
                        break
            
            # Log the situation
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
            
            # Save championship
            universe.save_championship(championship)
            database.conn.commit()
        
        return jsonify({
            'success': result.success,
            'result': result.to_dict()
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/championships/<title_id>/interim', methods=['POST'])
@app.route('/api/championships/<title_id>/interim', methods=['POST'])
def api_create_interim_champion(title_id):
    """
    Create an interim champion.
    
    Request body:
    {
        "interim_champion_id": "w005",
        "show_name": "Summer Slamfest"
    }
    """
    try:
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
        
        # Execute decision
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
            # Log the situation
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
            
            # IMPORTANT: Save the interim champion data directly to database
            cursor = database.conn.cursor()
            cursor.execute('''
                UPDATE championships 
                SET current_holder_id = ?,
                    current_holder_name = ?
                WHERE id = ?
            ''', (championship.current_holder_id, championship.current_holder_name, title_id))
            
            # We need to store interim data - add columns if they don't exist
            # For now, save in a simple way by updating the championship
            database.save_championship(championship)
            database.conn.commit()
        
        return jsonify({
            'success': result.success,
            'result': result.to_dict()
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/championships/<title_id>/strip-interim', methods=['POST'])
def api_strip_interim_champion(title_id):
    """Strip the interim champion (original champion returns)"""
    try:
        data = request.get_json(silent=True) or {}
        
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        if not championship.has_interim_champion:
            return jsonify({'success': False, 'error': 'No interim champion to strip'}), 400
        
        show_name = data.get('show_name', f'Week {universe.current_week} Show')
        show_id = f"show_y{universe.current_year}_w{universe.current_week}"
        
        interim_name = championship.interim_holder_name
        
        # Strip interim
        championship.strip_interim_champion(
            show_id=show_id,
            show_name=show_name,
            year=universe.current_year,
            week=universe.current_week
        )
        
        # Log
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
        
        # Save
        universe.save_championship(championship)
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'message': f'{interim_name} stripped as interim champion. {championship.current_holder_name} is undisputed champion.',
            'championship': championship.to_dict()
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/championships/<title_id>/unify', methods=['POST'])
def api_unify_championship(title_id):
    """
    Unify interim and main championship (after unification match).
    
    Request body:
    {
        "winner_id": "w001",  # ID of the winner (becomes undisputed)
        "show_name": "Victory Dome"
    }
    """
    try:
        data = request.get_json()
        
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        if not championship.has_interim_champion:
            return jsonify({'success': False, 'error': 'No interim champion to unify'}), 400
        
        winner_id = data.get('winner_id')
        if not winner_id:
            return jsonify({'success': False, 'error': 'winner_id required'}), 400
        
        # Winner must be either the main or interim champion
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
        
        # Perform unification
        loser_name = championship.interim_holder_name if winner_id == championship.current_holder_id else championship.current_holder_name
        
        # Strip interim first
        championship.strip_interim_champion(show_id, show_name, universe.current_year, universe.current_week)
        
        # If interim champion won, they become the new undisputed champion
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
        
        # Log
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
        
        # Save
        universe.save_championship(championship)
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'message': f'{winner.name} is the UNDISPUTED {championship.name}!',
            'championship': championship.to_dict()
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/championships/<title_id>/fill-vacancy', methods=['POST'])
def api_fill_vacancy(title_id):
    """
    Fill a vacant championship.
    
    Request body:
    {
        "new_champion_id": "w005",
        "show_name": "Clash of Titans",
        "resolution_method": "tournament"  # tournament, match, battle_royal, awarded
    }
    """
    try:
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
        
        # Find active vacancy
        vacancy = universe.championship_hierarchy.get_vacancy_for_title(title_id)
        
        # Award title
        championship.award_title(
            wrestler_id=new_champion_id,
            wrestler_name=new_champion.name,
            show_id=show_id,
            show_name=show_name,
            year=universe.current_year,
            week=universe.current_week,
            is_interim=False
        )
        
        # Fill vacancy record
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
            
            # Save to database
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
        
        # Log
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
        
        # Save championship
        universe.save_championship(championship)
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'message': f'{new_champion.name} is the NEW {championship.name}!',
            'championship': championship.to_dict()
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/championships/<title_id>/record-defense', methods=['POST'])
def api_record_title_defense(title_id):
    """
    Record a title defense (called automatically by show simulation, but can be manual).
    
    Request body:
    {
        "challenger_id": "w002",
        "show_name": "ROC Alpha Week 20",
        "is_ppv": false,
        "result": "retained",  # retained, lost
        "finish_type": "clean_pin",
        "star_rating": 4.25,
        "duration_minutes": 18
    }
    """
    try:
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
        
        # Record defense
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
        
        # Update championship's last defense
        championship.record_successful_defense(
            year=universe.current_year,
            week=universe.current_week,
            show_id=show_id
        )
        
        # Update prestige based on match quality
        star_rating = data.get('star_rating', 3.0)
        if star_rating >= 4.5:
            championship.adjust_prestige(5)
        elif star_rating >= 4.0:
            championship.adjust_prestige(3)
        elif star_rating >= 3.5:
            championship.adjust_prestige(1)
        elif star_rating < 2.5:
            championship.adjust_prestige(-2)
        
        # Save to database
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
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500



@app.route('/api/championships/<title_id>/vacancies')
def api_get_title_vacancies(title_id):
    """Get vacancy history for a championship"""
    try:
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


@app.route('/api/championships/<title_id>/guaranteed-shots')
def api_get_title_guaranteed_shots(title_id):
    """Get all guaranteed title shots for a championship"""
    try:
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


@app.route('/api/championships/<title_id>/situation-log')
def api_get_title_situation_log(title_id):
    """Get situation/decision log for a championship"""
    try:
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


@app.route('/api/championships/<title_id>/interim-candidates')
def api_get_interim_candidates(title_id):
    """Get ranked candidates for interim championship"""
    try:
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


@app.route('/api/championships/vacancies')
def api_get_all_active_vacancies():
    """Get all currently active title vacancies"""
    try:
        vacancies = get_all_active_vacancies(database)
        
        return jsonify({
            'success': True,
            'total': len(vacancies),
            'vacancies': vacancies
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/championships/<title_id>/generate-injury-angle', methods=['POST'])
def api_generate_injury_angle(title_id):
    """
    Generate an injury write-off angle for a champion.
    
    Request body:
    {
        "attacker_id": "w002"  # Optional - will pick one if not specified
    }
    """
    try:
        data = request.get_json() if request.is_json else {}
        
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        if championship.is_vacant:
            return jsonify({'success': False, 'error': 'Championship is vacant'}), 400
        
        champion = universe.get_wrestler_by_id(championship.current_holder_id)
        if not champion:
            return jsonify({'success': False, 'error': 'Champion not found'}), 404
        
        # Get attacker
        attacker = None
        if data.get('attacker_id'):
            attacker = universe.get_wrestler_by_id(data['attacker_id'])
        else:
            # Find a suitable heel attacker
            roster = universe.get_active_wrestlers()
            heels = [w for w in roster if w.alignment == 'Heel' and w.id != champion.id and not w.is_injured]
            if heels:
                # Prefer higher-card heels
                heels.sort(key=lambda w: {'Main Event': 5, 'Upper Midcard': 4, 'Midcard': 3, 'Lower Midcard': 2, 'Jobber': 1}.get(w.role, 1), reverse=True)
                attacker = heels[0]
        
        if not attacker:
            return jsonify({'success': False, 'error': 'No suitable attacker found'}), 400
        
        # Generate angle
        body_part = 'shoulder'  # Default, could be based on injury
        if champion.injury and champion.injury.description:
            desc = champion.injury.description.lower()
            if 'knee' in desc:
                body_part = 'knee'
            elif 'back' in desc:
                body_part = 'back'
            elif 'neck' in desc:
                body_part = 'neck'
            elif 'arm' in desc or 'elbow' in desc:
                body_part = 'arm'
        
        angle = title_situation_manager.generate_injury_angle(
            victim=champion,
            attacker=attacker,
            injury_description=champion.injury.description if champion.injury else 'injury',
            body_part=body_part
        )
        
        return jsonify({
            'success': True,
            'angle': angle.to_dict()
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/championships/<title_id>/generate-return-angle', methods=['POST'])
def api_generate_return_angle(title_id):
    """
    Generate a return from injury angle.
    
    Request body:
    {
        "wrestler_id": "w001",  # The returning wrestler
        "target_id": "w002",    # Optional - the target of revenge
        "is_ppv": true,
        "prefer_surprise": true
    }
    """
    try:
        data = request.get_json()
        
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        wrestler_id = data.get('wrestler_id')
        if not wrestler_id:
            return jsonify({'success': False, 'error': 'wrestler_id required'}), 400
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'success': False, 'error': 'Wrestler not found'}), 404
        
        target = None
        if data.get('target_id'):
            target = universe.get_wrestler_by_id(data['target_id'])
        
        angle = title_situation_manager.generate_return_angle(
            returning_wrestler=wrestler,
            target=target,
            is_ppv=data.get('is_ppv', False),
            prefer_surprise=data.get('prefer_surprise', True)
        )
        
        return jsonify({
            'success': True,
            'angle': angle.to_dict()
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/wrestlers/<wrestler_id>/guaranteed-shots')
def api_get_wrestler_guaranteed_shots(wrestler_id):
    """Get all guaranteed title shots for a wrestler"""
    try:
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


@app.route('/api/wrestlers/<wrestler_id>/grant-title-shot', methods=['POST'])
def api_grant_title_shot(wrestler_id):
    """
    Grant a wrestler a guaranteed future title shot.
    
    Request body:
    {
        "title_id": "title001",
        "reason": "tournament_winner",  # injury_return, rematch_clause, tournament_winner, storyline
        "expires_weeks": 52  # Optional, defaults to 1 year
    }
    """
    try:
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
        
        # Calculate expiration
        expires_year = universe.current_year
        expires_week = universe.current_week + expires_weeks
        while expires_week > 52:
            expires_week -= 52
            expires_year += 1
        
        # Grant shot
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
        
        # Save to database
        save_guaranteed_shot(database, shot.to_dict())
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'message': f'{wrestler.name} granted a {championship.name} title shot',
            'shot': shot.to_dict()
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/wrestlers/<wrestler_id>/process-return', methods=['POST'])
def api_process_champion_return(wrestler_id):
    """
    Process a champion returning from injury.
    
    Request body:
    {
        "title_id": "title001",
        "unify_immediately": false  # If true, immediately becomes undisputed
    }
    """
    try:
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
        
        show_name = data.get('show_name', f'Week {universe.current_week} Show')
        show_id = f"show_y{universe.current_year}_w{universe.current_week}"
        
        # Get current champion if any
        current_champion = None
        if championship.current_holder_id and championship.current_holder_id != wrestler_id:
            current_champion = universe.get_wrestler_by_id(championship.current_holder_id)
        
        # Process return
        result = title_situation_manager.process_champion_return(
            championship=championship,
            returning_champion=wrestler,
            year=universe.current_year,
            week=universe.current_week,
            show_id=show_id,
            show_name=show_name,
            current_champion=current_champion,
            unify_immediately=data.get('unify_immediately', False)
        )
        
        # Save changes
        universe.save_wrestler(wrestler)
        universe.save_championship(championship)
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'result': result,
            'wrestler': wrestler.to_dict(),
            'championship': championship.to_dict()
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500



# ============================================================================
# API ROUTES - STEP 22: Custom Championship Creation
# ============================================================================

from models.championship_factory import (
    ChampionshipFactory, ChampionshipValidator, ChampionshipPresets,
    DivisionRestriction, WeightClass, BeltAppearance, BeltStyle, BeltColor,
    CustomDefenseRequirements, ChampionshipTemplate
)
from models.championship_extended import ExtendedChampionship
from persistence.championship_custom_db import (
    create_custom_championship_tables, save_championship_extended,
    get_championship_extended, get_all_custom_championships,
    get_championships_by_division, retire_championship,
    reactivate_championship, log_championship_action,
    get_championship_action_log, delete_championship,
    get_championship_statistics
)


@app.route('/api/championships/custom/presets')
def api_get_championship_presets():
    """Get all available championship creation presets"""
    try:
        presets = ChampionshipPresets.get_all_presets()
        
        return jsonify({
            'success': True,
            'total': len(presets),
            'presets': presets
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/championships/custom/validate', methods=['POST'])
def api_validate_custom_championship():
    """
    Validate custom championship data without creating it.
    Useful for real-time form validation.
    """
    try:
        data = request.get_json()
        
        # Get existing championship names
        existing_names = [c.name for c in universe.championships]
        
        # Validate
        is_valid, errors = ChampionshipValidator.validate_all(data, existing_names)
        
        # Calculate suggested prestige
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


@app.route('/api/championships/custom/create', methods=['POST'])
def api_create_custom_championship():
    """
    Create a new custom championship.
    
    Request body:
    {
        "name": "ROC Hardcore Championship",
        "assigned_brand": "ROC Alpha",
        "title_type": "Midcard",
        "division": "open",
        "weight_class": "open",
        "initial_prestige": 45,
        "is_tag_team": false,
        "tag_team_size": 2,
        "description": "Defended under extreme rules",
        "appearance": {
            "style": "modern",
            "primary_color": "black",
            "secondary_color": "red"
        },
        "defense_requirements": {
            "max_days_between_defenses": 14,
            "ppv_defense_required": false
        }
    }
    """
    try:
        data = request.get_json()
        
        print(f"\n{'='*60}")
        print(f"🏆 CREATE CUSTOM CHAMPIONSHIP REQUEST")
        print(f"{'='*60}")
        print(f"Name: {data.get('name')}")
        print(f"Brand: {data.get('assigned_brand')}")
        print(f"Type: {data.get('title_type')}")
        print(f"{'='*60}\n")
        
        # Get existing championship names
        existing_names = [c.name for c in universe.championships]
        
        # Validate all data
        is_valid, errors = ChampionshipValidator.validate_all(data, existing_names)
        
        if not is_valid:
            return jsonify({
                'success': False,
                'error': 'Validation failed',
                'errors': errors
            }), 400
        
        # Generate championship ID
        championship_id = ChampionshipFactory.generate_championship_id(database)
        print(f"✅ Generated ID: {championship_id}")
        
        # Create base championship
        championship = ChampionshipFactory.create_championship(
            data=data,
            championship_id=championship_id,
            current_year=universe.current_year,
            current_week=universe.current_week
        )
        
        print(f"✅ Created championship: {championship.name}")
        print(f"   Prestige: {championship.prestige}")
        
        # Save to main championships table
        database.save_championship(championship)
        
        # Prepare extended data
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
        
        # Save extended data
        save_championship_extended(database, championship_id, extended_data)
        
        # Log the creation
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
        
        # Get full championship data for response
        full_data = championship.to_dict()
        full_data.update(extended_data)
        
        return jsonify({
            'success': True,
            'message': f'Championship "{championship.name}" created successfully',
            'championship': full_data
        })
    
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        
        print(f"\n❌ Championship Creation Error:")
        print(error_trace)
        print()
        
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': error_trace
        }), 500


@app.route('/api/championships/custom/create-from-preset', methods=['POST'])
def api_create_championship_from_preset():
    """
    Create a championship from a preset template.
    
    Request body:
    {
        "preset_id": "cruiserweight",
        "assigned_brand": "ROC Velocity",
        "name_override": "ROC Velocity Cruiserweight Title"  # Optional
    }
    """
    try:
        data = request.get_json()
        
        preset_id = data.get('preset_id')
        if not preset_id:
            return jsonify({'success': False, 'error': 'preset_id required'}), 400
        
        # Get preset
        preset = ChampionshipPresets.get_preset_by_id(preset_id)
        if not preset:
            return jsonify({'success': False, 'error': f'Preset "{preset_id}" not found'}), 404
        
        # Build championship data from preset
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
        
        # Validate
        existing_names = [c.name for c in universe.championships]
        is_valid, errors = ChampionshipValidator.validate_all(champ_data, existing_names)
        
        if not is_valid:
            return jsonify({
                'success': False,
                'error': 'Validation failed',
                'errors': errors
            }), 400
        
        # Generate ID and create
        championship_id = ChampionshipFactory.generate_championship_id(database)
        
        championship = ChampionshipFactory.create_championship(
            data=champ_data,
            championship_id=championship_id,
            current_year=universe.current_year,
            current_week=universe.current_week
        )
        
        # Save
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
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500





@app.route('/api/championships/<title_id>/update', methods=['PUT'])
def api_update_championship(title_id):
    """
    Update an existing championship's extended properties.
    
    Request body (all fields optional):
    {
        "description": "New description",
        "appearance": {...},
        "defense_requirements": {...}
    }
    """
    try:
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        data = request.get_json()
        
        # Get current extended data
        current_extended = get_championship_extended(database, title_id) or {}
        
        # Update fields
        if 'description' in data:
            current_extended['description'] = data['description']
        
        if 'appearance' in data:
            current_extended['appearance'] = data['appearance']
        
        if 'defense_requirements' in data:
            # Validate defense requirements
            valid, errors = ChampionshipValidator.validate_defense_requirements(data['defense_requirements'])
            if not valid:
                return jsonify({
                    'success': False,
                    'error': 'Invalid defense requirements',
                    'errors': errors
                }), 400
            current_extended['defense_requirements'] = data['defense_requirements']
        
        # Save updated extended data
        save_championship_extended(database, title_id, current_extended)
        
        # Log the update
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


@app.route('/api/championships/<title_id>/retire', methods=['POST'])
def api_retire_championship(title_id):
    """
    Retire a championship (make inactive but preserve history).
    
    Request body (optional):
    {
        "reason": "Merged with another championship"
    }
    """
    try:
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        # Check if vacant first
        if not championship.is_vacant:
            return jsonify({
                'success': False,
                'error': 'Championship must be vacated before retiring'
            }), 400
        
        data = request.get_json() if request.is_json else {}
        reason = data.get('reason', 'Championship retired')
        
        # Retire the championship
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


@app.route('/api/championships/<title_id>/reactivate', methods=['POST'])
def api_reactivate_championship(title_id):
    """Reactivate a retired championship"""
    try:
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        # Check if retired
        extended = get_championship_extended(database, title_id)
        if not extended or not extended.get('retired'):
            return jsonify({
                'success': False,
                'error': 'Championship is not retired'
            }), 400
        
        # Reactivate
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


@app.route('/api/championships/<title_id>/delete', methods=['DELETE'])
def api_delete_championship(title_id):
    """
    Permanently delete a championship.
    WARNING: This removes all history and cannot be undone.
    """
    try:
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        # Check if it's a default championship
        extended = get_championship_extended(database, title_id)
        if not extended or not extended.get('is_custom'):
            return jsonify({
                'success': False,
                'error': 'Cannot delete default championships. Use retire instead.'
            }), 400
        
        # Check if vacant
        if not championship.is_vacant:
            return jsonify({
                'success': False,
                'error': 'Championship must be vacated before deletion'
            }), 400
        
        title_name = championship.name
        
        # Delete
        delete_championship(database, title_id)
        
        return jsonify({
            'success': True,
            'message': f'{title_name} has been permanently deleted'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/championships/custom')
def api_get_custom_championships():
    """Get all custom (user-created) championships"""
    try:
        include_retired = request.args.get('include_retired', 'false').lower() == 'true'
        
        championships = get_all_custom_championships(database, include_retired)
        
        return jsonify({
            'success': True,
            'total': len(championships),
            'championships': championships
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/championships/by-division/<division>')
def api_get_championships_by_division(division):
    """Get all championships for a specific division"""
    try:
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


@app.route('/api/championships/<title_id>/statistics')
def api_get_championship_full_stats(title_id):
    """Get comprehensive statistics for a championship"""
    try:
        stats = get_championship_statistics(database, title_id)
        
        if not stats:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        return jsonify({
            'success': True,
            'statistics': stats
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/championships/<title_id>/action-log')
def api_get_championship_action_log(title_id):
    """Get action log for a championship"""
    try:
        limit = request.args.get('limit', 20, type=int)
        
        log = get_championship_action_log(database, title_id, limit)
        
        return jsonify({
            'success': True,
            'total': len(log),
            'log': log
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# API ROUTES - STEP 25: Championship Defense Frequency
# ============================================================================

@app.route('/api/championships/<title_id>/defense-frequency')
def api_get_defense_frequency(title_id):
    """Get defense frequency requirements and current status for a championship"""
    try:
        championship = universe.get_championship_by_id(title_id)
        
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        # Get defense status
        status = championship.get_defense_status(
            universe.current_year,
            universe.current_week
        )
        
        # Get champion info
        champion_info = None
        if not championship.is_vacant:
            champion = universe.get_wrestler_by_id(championship.effective_champion_id)
            if champion:
                champion_info = {
                    'id': champion.id,
                    'name': champion.name,
                    'is_interim': championship.has_interim_champion
                }
        
        return jsonify({
            'success': True,
            'championship': {
                'id': championship.id,
                'name': championship.name,
                'is_vacant': championship.is_vacant
            },
            'champion': champion_info,
            'requirements': {
                'max_days_between_defenses': championship.defense_frequency_days,
                'min_defenses_per_year': championship.min_annual_defenses
            },
            'status': status,
            'last_defense': {
                'year': championship.last_defense_year,
                'week': championship.last_defense_week,
                'show_id': championship.last_defense_show_id
            } if championship.last_defense_year else None
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/championships/<title_id>/defense-frequency/set', methods=['POST'])
def api_set_defense_frequency(title_id):
    """
    Set defense frequency requirements for a championship.
    
    Request body:
    {
        "max_days_between_defenses": 30,
        "min_defenses_per_year": 12
    }
    """
    try:
        championship = universe.get_championship_by_id(title_id)
        
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        data = request.get_json()
        
        max_days = data.get('max_days_between_defenses')
        min_annual = data.get('min_defenses_per_year')
        
        # Validate
        if max_days is not None:
            if not isinstance(max_days, int) or max_days < 14 or max_days > 90:
                return jsonify({
                    'success': False,
                    'error': 'max_days_between_defenses must be integer between 14-90'
                }), 400
        
        if min_annual is not None:
            if not isinstance(min_annual, int) or min_annual < 4 or min_annual > 52:
                return jsonify({
                    'success': False,
                    'error': 'min_defenses_per_year must be integer between 4-52'
                }), 400
        
        # Set requirements
        try:
            championship.set_defense_requirements(max_days, min_annual)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        
        # Save to database
        universe.save_championship(championship)
        database.conn.commit()
        
        # Log the change
        from persistence.championship_custom_db import log_championship_action
        log_championship_action(
            database,
            title_id,
            'defense_requirements_updated',
            universe.current_year,
            universe.current_week,
            f"Defense requirements updated: {max_days or championship.defense_frequency_days} days, {min_annual or championship.min_annual_defenses}/year"
        )
        
        return jsonify({
            'success': True,
            'message': 'Defense frequency requirements updated',
            'requirements': {
                'max_days_between_defenses': championship.defense_frequency_days,
                'min_defenses_per_year': championship.min_annual_defenses
            }
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/championships/overdue-defenses')
def api_get_overdue_defenses():
    """Get all championships with overdue defenses"""
    try:
        championships = universe.championships
        overdue = []
        
        for championship in championships:
            if championship.is_vacant:
                continue
            
            status = championship.get_defense_status(
                universe.current_year,
                universe.current_week
            )
            
            if status['is_overdue'] or status['urgency_level'] >= 2:
                champion = universe.get_wrestler_by_id(championship.effective_champion_id)
                
                overdue.append({
                    'championship': {
                        'id': championship.id,
                        'name': championship.name,
                        'brand': championship.assigned_brand,
                        'tier': championship.title_type
                    },
                    'champion': {
                        'id': champion.id if champion else None,
                        'name': champion.name if champion else 'Unknown',
                        'is_interim': championship.has_interim_champion
                    },
                    'status': status
                })
        
        # Sort by urgency level (highest first)
        overdue.sort(key=lambda x: x['status']['urgency_level'], reverse=True)
        
        return jsonify({
            'success': True,
            'current_year': universe.current_year,
            'current_week': universe.current_week,
            'total': len(overdue),
            'overdue_defenses': overdue
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/championships/defense-schedule')
def api_get_full_defense_schedule():
    """Get complete defense schedule for all championships"""
    try:
        championships = universe.championships
        schedule = []
        
        for championship in championships:
            if championship.is_vacant:
                continue
            
            status = championship.get_defense_status(
                universe.current_year,
                universe.current_week
            )
            
            champion = universe.get_wrestler_by_id(championship.effective_champion_id)
            
            schedule.append({
                'championship': {
                    'id': championship.id,
                    'name': championship.name,
                    'brand': championship.assigned_brand,
                    'tier': championship.title_type,
                    'prestige': championship.prestige
                },
                'champion': {
                    'id': champion.id if champion else None,
                    'name': champion.name if champion else 'Unknown',
                    'is_interim': championship.has_interim_champion
                },
                'status': status,
                'total_defenses': championship.total_defenses
            })
        
        # Sort by urgency level (highest first)
        schedule.sort(key=lambda x: x['status']['urgency_level'], reverse=True)
        
        return jsonify({
            'success': True,
            'current_year': universe.current_year,
            'current_week': universe.current_week,
            'total': len(schedule),
            'schedule': schedule
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/championships/<title_id>/is-overdue')
def api_check_if_defense_overdue(title_id):
    """Quick check if a championship defense is overdue"""
    try:
        championship = universe.get_championship_by_id(title_id)
        
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        if championship.is_vacant:
            return jsonify({
                'success': True,
                'is_overdue': False,
                'reason': 'Championship is vacant'
            })
        
        status = championship.get_defense_status(
            universe.current_year,
            universe.current_week
        )
        
        return jsonify({
            'success': True,
            'championship_id': title_id,
            'championship_name': championship.name,
            'is_overdue': status['is_overdue'],
            'urgency_level': status['urgency_level'],
            'urgency_label': status['urgency_label'],
            'days_since_defense': status['days_since_defense'],
            'days_until_required': status['days_until_required']
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/championships/defense-alerts')
def api_get_defense_alerts():
    """Get championships requiring attention (for dashboard alerts)"""
    try:
        championships = universe.championships
        alerts = []
        
        for championship in championships:
            if championship.is_vacant:
                continue
            
            status = championship.get_defense_status(
                universe.current_year,
                universe.current_week
            )
            
            # Only include medium urgency or higher
            if status['urgency_level'] >= 1:
                champion = universe.get_wrestler_by_id(championship.effective_champion_id)
                
                alert = {
                    'championship_id': championship.id,
                    'championship_name': championship.name,
                    'champion_name': champion.name if champion else 'Unknown',
                    'urgency_level': status['urgency_level'],
                    'urgency_label': status['urgency_label'],
                    'days_since_defense': status['days_since_defense'],
                    'message': f"{championship.name} defense needed soon ({status['days_until_required']} days remaining)"
                }
                
                if status['is_overdue']:
                    alert['message'] = f"🚨 {championship.name} defense OVERDUE by {status['days_since_defense'] - championship.defense_frequency_days} days!"
                
                alerts.append(alert)
        
        # Sort by urgency
        alerts.sort(key=lambda x: x['urgency_level'], reverse=True)
        
        return jsonify({
            'success': True,
            'total': len(alerts),
            'alerts': alerts
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/championships/action-log')
def api_get_all_championship_action_log():
    """Get action log for all championships"""
    try:
        limit = request.args.get('limit', 50, type=int)
        
        log = get_championship_action_log(database, None, limit)
        
        return jsonify({
            'success': True,
            'total': len(log),
            'log': log
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/championships/<title_id>/check-eligibility/<wrestler_id>')
def api_check_wrestler_eligibility(title_id, wrestler_id):
    """Check if a wrestler is eligible to compete for a championship"""
    try:
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'success': False, 'error': 'Wrestler not found'}), 404
        
        # Get extended data
        extended = get_championship_extended(database, title_id)
        
        eligible = True
        reasons = []
        
        if extended:
            division = extended.get('division', 'open')
            weight_class = extended.get('weight_class', 'open')
            
            # Check division
            if division == 'mens' and wrestler.gender != 'Male':
                eligible = False
                reasons.append("This championship is for male competitors only")
            elif division == 'womens' and wrestler.gender != 'Female':
                eligible = False
                reasons.append("This championship is for female competitors only")
            
            # Check weight class (simplified)
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


@app.route('/api/championships/options')
def api_get_championship_options():
    """Get all available options for championship creation dropdowns"""
    try:
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



@app.route('/api/championships/<title_id>/lineage')
def api_get_title_lineage(title_id):
    """Get complete lineage for a championship"""
    try:
        limit = request.args.get('limit', type=int)
        
        lineage = universe.lineage_tracker.get_title_lineage(title_id, limit)
        
        # Get title name
        title = universe.get_championship_by_id(title_id)
        title_name = title.name if title else "Unknown Championship"
        
        return jsonify({
            'success': True,
            'title_id': title_id,
            'title_name': title_name,
            'total_reigns': len(lineage),
            'lineage': lineage
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/championships/<title_id>/statistics')
def api_get_championship_statistics(title_id):
    """Get comprehensive statistics for a championship"""
    try:
        stats = universe.lineage_tracker.get_championship_statistics(title_id)
        
        # Get title info
        title = universe.get_championship_by_id(title_id)
        
        return jsonify({
            'success': True,
            'title_id': title_id,
            'title_name': title.name if title else "Unknown",
            'statistics': stats
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/championships/<title_id>/defenses')
def api_get_title_defenses(title_id):
    """Get defense history for a championship"""
    try:
        from persistence.lineage_db import get_title_defenses
        
        limit = request.args.get('limit', 50, type=int)
        defenses = get_title_defenses(database, title_id=title_id, limit=limit)
        
        # Get title name
        title = universe.get_championship_by_id(title_id)
        
        return jsonify({
            'success': True,
            'title_id': title_id,
            'title_name': title.name if title else "Unknown",
            'defenses': defenses
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/wrestlers/<wrestler_id>/title-history')
def api_get_wrestler_title_history(wrestler_id):
    """Get complete title history for a wrestler"""
    try:
        from persistence.lineage_db import get_wrestler_title_history
        
        history = get_wrestler_title_history(database, wrestler_id)
        
        # Get wrestler name
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        
        return jsonify({
            'success': True,
            'wrestler_id': wrestler_id,
            'wrestler_name': wrestler.name if wrestler else "Unknown",
            'history': history
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/championships/<title_id>/reign/<wrestler_id>/<int:year>/<int:week>')
def api_get_reign_statistics(title_id, wrestler_id, year, week):
    """Get detailed statistics for a specific title reign"""
    try:
        stats = universe.lineage_tracker.get_reign_statistics(
            title_id, wrestler_id, year, week
        )
        
        return jsonify({
            'success': True,
            'title_id': title_id,
            'wrestler_id': wrestler_id,
            'year': year,
            'week': week,
            'statistics': stats.to_dict()
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500



# ============================================================================
# API ROUTES - STEP 25: Testing & Debug Endpoints
# ============================================================================

@app.route('/api/test/defense-frequency/simulate-overdue', methods=['POST'])
def api_test_simulate_overdue_defense():
    """
    TEST ONLY: Artificially make a championship defense overdue for testing.
    
    Request body:
    {
        "title_id": "title001",
        "days_overdue": 10
    }
    """
    try:
        data = request.get_json()
        title_id = data.get('title_id')
        days_overdue = data.get('days_overdue', 10)
        
        championship = universe.get_championship_by_id(title_id)
        if not championship:
            return jsonify({'success': False, 'error': 'Championship not found'}), 404
        
        if championship.is_vacant:
            return jsonify({'success': False, 'error': 'Championship is vacant'}), 400
        
        # Calculate weeks to set last defense in the past
        weeks_ago = ((championship.defense_frequency_days + days_overdue) // 7) + 1
        
        past_year = universe.current_year
        past_week = universe.current_week - weeks_ago
        
        # Handle year wraparound
        while past_week < 1:
            past_week += 52
            past_year -= 1
        
        # Set last defense to past date
        championship.last_defense_year = past_year
        championship.last_defense_week = past_week
        championship.last_defense_show_id = f"test_show_y{past_year}_w{past_week}"
        
        # Save
        universe.save_championship(championship)
        database.conn.commit()
        
        # Get new status
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
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/test/defense-frequency/reset', methods=['POST'])
def api_test_reset_defense_frequency():
    """
    TEST ONLY: Reset all championships to default defense requirements.
    """
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


@app.route('/api/test/defense-frequency/report')
def api_test_defense_frequency_report():
    """
    TEST ONLY: Get comprehensive defense frequency report for all championships.
    """
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
        
        # Sort by urgency
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
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


# ============================================================================
# API ROUTES - FREE AGENTS (Steps 113-223)
# ============================================================================

@app.route('/api/free-agents')
def api_get_free_agents():
    """Get all available free agents"""
    discovered_only = request.args.get('discovered_only', 'true').lower() == 'true'
    visibility_tier = request.args.get('visibility_tier', type=int)
    source = request.args.get('source')
    
    if discovered_only:
        free_agents = free_agent_pool_manager.get_discovered_free_agents()
    elif visibility_tier:
        free_agents = free_agent_pool_manager.get_free_agents_by_visibility(visibility_tier)
    else:
        free_agents = free_agent_pool_manager.available_free_agents
    
    # Filter by source if specified
    if source:
        free_agents = [fa for fa in free_agents if fa.source.value == source]
    
    # Sort by market value descending
    free_agents.sort(key=lambda fa: fa.market_value, reverse=True)
    
    return jsonify({
        'success': True,
        'total': len(free_agents),
        'free_agents': [fa.to_dict() for fa in free_agents]
    })


@app.route('/api/free-agents/<fa_id>')
def api_get_free_agent(fa_id):
    """Get a specific free agent"""
    fa = free_agent_pool_manager.get_free_agent_by_id(fa_id)
    
    if not fa:
        return jsonify({'success': False, 'error': 'Free agent not found'}), 404
    
    # Allow force parameter to bypass discovery check
    force = request.args.get('force', 'false').lower() == 'true'
    
    # If not discovered and not forcing, return 403
    # But we want clicking to discover them, so let's allow access
    # The frontend will handle the discovery flow
    
    return jsonify({
        'success': True,
        'free_agent': fa.to_dict()
    })

@app.route('/api/free-agents/pool-summary')
def api_get_free_agent_pool_summary():
    """Get summary statistics for the free agent pool"""
    summary = free_agent_pool_manager.get_pool_summary()
    
    return jsonify({
        'success': True,
        'summary': summary
    })


@app.route('/api/free-agents/headlines')
def api_get_headline_free_agents():
    """Get tier 1 headline free agents (always visible)"""
    headlines = free_agent_pool_manager.get_headline_free_agents()
    
    return jsonify({
        'success': True,
        'total': len(headlines),
        'free_agents': [fa.to_dict() for fa in headlines]
    })


@app.route('/api/free-agents/legends')
def api_get_legend_free_agents():
    """Get available legend free agents"""
    legends = free_agent_pool_manager.get_legends()
    discovered_legends = [l for l in legends if l.discovered]
    
    return jsonify({
        'success': True,
        'total': len(discovered_legends),
        'free_agents': [l.to_dict() for l in discovered_legends]
    })


@app.route('/api/free-agents/prospects')
def api_get_prospect_free_agents():
    """Get available prospect free agents"""
    prospects = free_agent_pool_manager.get_prospects()
    discovered_prospects = [p for p in prospects if p.discovered]
    
    return jsonify({
        'success': True,
        'total': len(discovered_prospects),
        'free_agents': [p.to_dict() for p in discovered_prospects]
    })


@app.route('/api/free-agents/international')
def api_get_international_free_agents():
    """Get international free agents"""
    region = request.args.get('region')
    international = free_agent_pool_manager.get_international_talents(region)
    discovered = [i for i in international if i.discovered]
    
    return jsonify({
        'success': True,
        'total': len(discovered),
        'region': region,
        'free_agents': [i.to_dict() for i in discovered]
    })


@app.route('/api/free-agents/controversy')
def api_get_controversy_free_agents():
    """Get free agents with controversy"""
    controversy = free_agent_pool_manager.get_controversy_cases()
    discovered = [c for c in controversy if c.discovered]
    
    return jsonify({
        'success': True,
        'total': len(discovered),
        'free_agents': [c.to_dict() for c in discovered]
    })


@app.route('/api/free-agents/<fa_id>/discover', methods=['POST'])
def api_discover_free_agent(fa_id):
    """Mark a free agent as discovered"""
    success = free_agent_pool_manager.discover_free_agent(fa_id)
    
    if not success:
        return jsonify({'success': False, 'error': 'Free agent not found or already discovered'}), 404
    
    fa = free_agent_pool_manager.get_free_agent_by_id(fa_id)
    
    return jsonify({
        'success': True,
        'message': f'{fa.wrestler_name} has been discovered!',
        'free_agent': fa.to_dict()
    })


@app.route('/api/free-agents/scout-region/<region>', methods=['POST'])
def api_scout_region(region):
    """Scout a region to discover international talents"""
    # Check if valid region
    valid_regions = ['japan', 'mexico', 'uk', 'europe', 'australia']
    if region not in valid_regions:
        return jsonify({'success': False, 'error': 'Invalid region'}), 400
    
    # Check if already scouted
    if free_agent_pool_manager._scouting_network.get(region, False):
        return jsonify({'success': False, 'error': 'Region already scouted'}), 400
    
    # Scout the region
    discovered = free_agent_pool_manager.scout_region(region)
    
    return jsonify({
        'success': True,
        'region': region,
        'discovered_count': len(discovered),
        'discovered': [fa.to_dict() for fa in discovered],
        'message': f'Scouting network established in {region}. Discovered {len(discovered)} new talents!'
    })


@app.route('/api/free-agents/upgrade-scouting', methods=['POST'])
def api_upgrade_scouting():
    """Upgrade scouting level"""
    current_level = free_agent_pool_manager._scouting_level
    
    if current_level >= 5:
        return jsonify({'success': False, 'error': 'Scouting already at maximum level'}), 400
    
    # Cost increases with level
    cost = 10000 * current_level
    
    if universe.balance < cost:
        return jsonify({'success': False, 'error': f'Insufficient funds. Need ${cost:,}'}), 400
    
    # Deduct cost and upgrade
    universe.balance -= cost
    new_level = free_agent_pool_manager.upgrade_scouting()
    
    # Save state
    database.update_game_state(balance=universe.balance)
    
    return jsonify({
        'success': True,
        'new_level': new_level,
        'cost': cost,
        'new_balance': universe.balance,
        'message': f'Scouting upgraded to level {new_level}!'
    })


@app.route('/api/free-agents/release-wrestler', methods=['POST'])
def api_release_wrestler_to_free_agents():
    """
    Release a wrestler from contract, adding them to free agent pool.
    
    Request body:
    {
        "wrestler_id": "w001",
        "departure_reason": "released",  # or "mutual"
        "no_compete_weeks": 0
    }
    """
    try:
        data = request.get_json()
        wrestler_id = data.get('wrestler_id')
        departure_reason = data.get('departure_reason', 'released')
        no_compete_weeks = data.get('no_compete_weeks', 0)
        
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({'success': False, 'error': 'Wrestler not found'}), 404
        
        # Check if wrestler has any championships
        was_champion = False
        for championship in universe.championships:
            if championship.current_holder_id == wrestler_id:
                was_champion = True
                # Would need to vacate title here
                break
        
        # Calculate relationship based on morale
        relationship = max(10, min(90, 50 + wrestler.morale // 2))
        
        # Add to free agent pool
        fa = free_agent_pool_manager.add_from_release(
            wrestler=wrestler,
            departure_reason=departure_reason,
            relationship=relationship,
            year=universe.current_year,
            week=universe.current_week,
            no_compete_weeks=no_compete_weeks,
            was_champion=was_champion
        )
        
        # Mark wrestler as released/retired
        wrestler.is_retired = True
        universe.save_wrestler(wrestler)
        database.conn.commit()
        
        return jsonify({
            'success': True,
            'message': f'{wrestler.name} has been released and is now a free agent',
            'free_agent': fa.to_dict()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/free-agents/process-week', methods=['POST'])
def api_process_free_agent_week():
    """Process weekly free agent updates"""
    try:
        events = free_agent_pool_manager.process_week(
            universe.current_year,
            universe.current_week
        )
        
        # Also process controversy cases (Step 114 addition)
        controversy_updates = free_agent_pool_manager.process_controversy_cases(universe)
        
        return jsonify({
            'success': True,
            'events': events,
            'controversy_updates': controversy_updates,
            'message': f'Processed {len(events)} free agent events, {len(controversy_updates)} controversy updates'
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/free-agents/generate-prospects', methods=['POST'])
def api_generate_prospects():
    """Generate random prospects (for testing)"""
    try:
        count = request.get_json().get('count', 3) if request.is_json else 3
        
        prospects = free_agent_pool_manager.generate_random_prospects(
            count,
            universe.current_year,
            universe.current_week
        )
        
        return jsonify({
            'success': True,
            'count': len(prospects),
            'prospects': [p.to_dict() for p in prospects],
            'message': f'Generated {len(prospects)} new prospects'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/debug/load-initial-free-agents', methods=['POST'])
def api_debug_load_initial_free_agents():
    """Debug endpoint to manually load initial free agents"""
    try:
        from persistence.initial_free_agents import load_initial_free_agents
        
        count = load_initial_free_agents(database, data_dir)
        
        return jsonify({
            'success': True,
            'message': f'Loaded {count} free agents',
            'count': count
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/debug/free-agent-db-check')
def api_debug_free_agent_db_check():
    """Check free agent database state"""
    try:
        cursor = database.conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='free_agents'")
        table_exists = cursor.fetchone() is not None
        
        # Count rows
        if table_exists:
            cursor.execute('SELECT COUNT(*) as count FROM free_agents')
            count = cursor.fetchone()['count']
            
            # Get all rows
            cursor.execute('SELECT id, wrestler_name, is_signed FROM free_agents LIMIT 10')
            rows = [dict(row) for row in cursor.fetchall()]
        else:
            count = 0
            rows = []
        
        # Check if file exists
        import os
        json_path = os.path.join(data_dir, 'initial_free_agents.json')
        file_exists = os.path.exists(json_path)
        
        if file_exists:
            with open(json_path, 'r') as f:
                import json
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
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/debug/free-agent-status')
def api_debug_free_agent_status():
    """Check free agent status in DB vs pool manager"""
    try:
        # Check database directly
        cursor = database.conn.cursor()
        cursor.execute('SELECT id, wrestler_name, discovered, visibility, is_signed FROM free_agents')
        db_agents = [dict(row) for row in cursor.fetchall()]
        
        # Check pool manager
        pool_agents = [fa.to_dict() for fa in free_agent_pool_manager.available_free_agents]
        discovered_agents = [fa.to_dict() for fa in free_agent_pool_manager.get_discovered_free_agents()]
        
        return jsonify({
            'db_count': len(db_agents),
            'db_agents': db_agents,
            'pool_manager_count': len(pool_agents),
            'discovered_count': len(discovered_agents),
            'pool_manager_loaded': len(free_agent_pool_manager._free_agents)
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/debug/reload-free-agent-pool', methods=['POST'])
def api_debug_reload_free_agent_pool():
    """Reload free agent pool from database"""
    try:
        global free_agent_pool_manager
        
        # Re-initialize the pool manager
        from economy.free_agent_pool import FreeAgentPoolManager
        free_agent_pool_manager = FreeAgentPoolManager(database)
        
        return jsonify({
            'success': True,
            'message': 'Pool manager reloaded',
            'total_loaded': len(free_agent_pool_manager._free_agents),
            'available': len(free_agent_pool_manager.available_free_agents),
            'discovered': len(free_agent_pool_manager.get_discovered_free_agents())
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500



# ============================================================================
# API ROUTES - FREE AGENT POOL POPULATION (Step 114)
# ============================================================================

@app.route('/api/free-agents/populate/releases', methods=['POST'])
def api_populate_from_releases():
    """Generate free agents from rival promotion releases"""
    try:
        count = request.get_json().get('count', 3) if request.is_json else 3
        
        generated = free_agent_pool_manager.populate_pool_from_releases(
            universe,
            count=count
        )
        
        return jsonify({
            'success': True,
            'count': len(generated),
            'free_agents': [fa.to_dict() for fa in generated],
            'message': f'Generated {len(generated)} new free agents from rival releases'
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/free-agents/populate/international/<region>', methods=['POST'])
def api_populate_international(region):
    """Generate international talents from a specific region"""
    try:
        count = request.get_json().get('count', 2) if request.is_json else 2
        
        # Must have scouted the region first
        if not free_agent_pool_manager._scouting_network.get(region, False):
            return jsonify({
                'success': False,
                'error': f'Region {region} not yet scouted. Scout the region first.'
            }), 400
        
        generated = free_agent_pool_manager.generate_international_wave(
            universe,
            region=region,
            count=count
        )
        
        return jsonify({
            'success': True,
            'region': region,
            'count': len(generated),
            'free_agents': [fa.to_dict() for fa in generated],
            'message': f'Discovered {len(generated)} new talents from {region}'
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/free-agents/populate/prospects', methods=['POST'])
def api_populate_prospects():
    """Generate new prospect class"""
    try:
        count = request.get_json().get('count', 5) if request.is_json else 5
        
        generated = free_agent_pool_manager.generate_prospect_class(
            universe,
            count=count
        )
        
        return jsonify({
            'success': True,
            'count': len(generated),
            'free_agents': [fa.to_dict() for fa in generated],
            'message': f'Generated {len(generated)} new prospects'
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/free-agents/check-legends', methods=['POST'])
def api_check_legend_availability():
    """Check if any retired legends are willing to comeback"""
    try:
        comebacks = free_agent_pool_manager.check_legend_availability(
            universe,
            universe.retired_wrestlers
        )
        
        return jsonify({
            'success': True,
            'count': len(comebacks),
            'legends': [fa.to_dict() for fa in comebacks],
            'message': f'{len(comebacks)} legends considering comeback!' if comebacks else 'No legends available for comeback at this time'
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/free-agents/pool-health')
def api_get_pool_health():
    """Get pool health report with recommendations"""
    try:
        report = free_agent_pool_manager.get_pool_health_report()
        
        return jsonify({
            'success': True,
            'report': report
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# API ROUTES - VISIBILITY TIERS (Step 115)
# ============================================================================

@app.route('/api/free-agents/visibility/breakdown')
def api_get_visibility_breakdown():
    """Get detailed visibility tier breakdown"""
    try:
        breakdown = free_agent_pool_manager.get_visibility_breakdown()
        
        return jsonify({
            'success': True,
            'breakdown': breakdown
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/free-agents/visibility/auto-discover', methods=['POST'])
def api_auto_discover():
    """Auto-discover free agents based on current scouting level"""
    try:
        discovered = free_agent_pool_manager.auto_discover_by_scouting_level()
        
        return jsonify({
            'success': True,
            'count': len(discovered),
            'discovered': [fa.to_dict() for fa in discovered],
            'message': f'Discovered {len(discovered)} new free agents through scouting network'
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/free-agents/<fa_id>/trigger-news', methods=['POST'])
def api_trigger_news_event(fa_id):
    """
    Trigger a news event for a free agent.
    
    Request body:
    {
        "event_type": "interview"  // interview, social_media, rival_signing_failed, etc.
    }
    """
    try:
        data = request.get_json()
        event_type = data.get('event_type', 'interview')
        
        valid_events = ['interview', 'social_media', 'rival_signing_failed', 
                       'injury_recovery', 'comeback_tease', 'shoot_promo']
        
        if event_type not in valid_events:
            return jsonify({
                'success': False,
                'error': f'Invalid event type. Valid types: {valid_events}'
            }), 400
        
        result = free_agent_pool_manager.trigger_news_event(fa_id, event_type)
        
        return jsonify(result)
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/free-agents/<fa_id>/promote-visibility', methods=['POST'])
def api_promote_visibility(fa_id):
    """Manually promote a free agent's visibility tier"""
    try:
        reason = request.get_json().get('reason', 'manual') if request.is_json else 'manual'
        
        fa = free_agent_pool_manager.promote_visibility(fa_id, reason)
        
        if not fa:
            return jsonify({'success': False, 'error': 'Free agent not found'}), 404
        
        return jsonify({
            'success': True,
            'free_agent': fa.to_dict(),
            'message': f'{fa.wrestler_name} visibility promoted to {fa.visibility_label}'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/free-agents/<fa_id>/demote-visibility', methods=['POST'])
def api_demote_visibility(fa_id):
    """Manually demote a free agent's visibility tier"""
    try:
        reason = request.get_json().get('reason', 'manual') if request.is_json else 'manual'
        
        fa = free_agent_pool_manager.demote_visibility(fa_id, reason)
        
        if not fa:
            return jsonify({'success': False, 'error': 'Free agent not found'}), 404
        
        return jsonify({
            'success': True,
            'free_agent': fa.to_dict(),
            'message': f'{fa.wrestler_name} visibility demoted to {fa.visibility_label}'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/free-agents/visibility/process-weekly', methods=['POST'])
def api_process_visibility_changes():
    """Process weekly visibility changes for all free agents"""
    try:
        changes = free_agent_pool_manager.process_visibility_changes(
            universe.current_year,
            universe.current_week
        )
        
        return jsonify({
            'success': True,
            'changes': changes,
            'message': f'Processed {len(changes)} visibility changes'
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500



# ============================================================================
# API ROUTES - STEP 116: Market Value Calculation
# ============================================================================

from economy.market_value import market_value_calculator, MarketValueFactors, MarketTrend

@app.route('/api/free-agents/<fa_id>/market-value')
def api_get_free_agent_market_value(fa_id):
    """Get detailed market value breakdown for a free agent"""
    try:
        fa = free_agent_pool_manager.get_free_agent_by_id(fa_id)
        
        if not fa:
            return jsonify({'success': False, 'error': 'Free agent not found'}), 404
        
        breakdown = fa.get_market_value_breakdown()
        
        return jsonify({
            'success': True,
            'free_agent_id': fa_id,
            'wrestler_name': fa.wrestler_name,
            'market_value': fa.market_value,
            'breakdown': breakdown,
            'demands': fa.demands.to_dict(),
            'market_value_trend': fa.market_value_trend,
            'market_value_history': [h.to_dict() for h in fa.market_value_history[-12:]]
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/free-agents/<fa_id>/recalculate-value', methods=['POST'])
def api_recalculate_free_agent_value(fa_id):
    """Force recalculation of market value for a free agent"""
    try:
        fa = free_agent_pool_manager.get_free_agent_by_id(fa_id)
        
        if not fa:
            return jsonify({'success': False, 'error': 'Free agent not found'}), 404
        
        old_value = fa.market_value
        
        # Recalculate with full calculator
        new_value = fa.recalculate_market_value(
            year=universe.current_year,
            week=universe.current_week,
            use_calculator=True
        )
        
        # Save to database using the pool manager's internal method
        # or directly to database if pool manager doesn't have save method
        try:
            if hasattr(free_agent_pool_manager, 'save_free_agent'):
                free_agent_pool_manager.save_free_agent(fa)
            elif hasattr(free_agent_pool_manager, '_save_free_agent_to_db'):
                free_agent_pool_manager._save_free_agent_to_db(fa)
            else:
                # Direct database save
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
            'free_agent_id': fa_id,
            'wrestler_name': fa.wrestler_name,
            'old_value': old_value,
            'new_value': new_value,
            'change': new_value - old_value,
            'change_percent': round(((new_value - old_value) / max(old_value, 1)) * 100, 1),
            'breakdown': fa.get_market_value_breakdown()
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/free-agents/recalculate-all-values', methods=['POST'])
def api_recalculate_all_free_agent_values():
    """Recalculate market values for all free agents"""
    try:
        updated = []
        
        for fa in free_agent_pool_manager.available_free_agents:
            old_value = fa.market_value
            
            new_value = fa.recalculate_market_value(
                year=universe.current_year,
                week=universe.current_week,
                use_calculator=True
            )
            
            if old_value != new_value:
                updated.append({
                    'id': fa.id,
                    'name': fa.wrestler_name,
                    'old_value': old_value,
                    'new_value': new_value,
                    'change': new_value - old_value
                })
        
        # Batch save to database
        try:
            cursor = database.conn.cursor()
            for fa in free_agent_pool_manager.available_free_agents:
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
            print(f"Warning: Could not batch save free agents: {save_error}")
        
        return jsonify({
            'success': True,
            'total_processed': len(free_agent_pool_manager.available_free_agents),
            'total_updated': len(updated),
            'updates': updated
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

        

@app.route('/api/free-agents/market-value/quick-estimate', methods=['POST'])
def api_quick_market_value_estimate():
    """
    Get a quick market value estimate without a full free agent.
    Useful for UI previews.
    
    Request body:
    {
        "popularity": 65,
        "role": "Upper Midcard",
        "age": 28,
        "is_major_superstar": false
    }
    """
    try:
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


@app.route('/api/free-agents/market-value/full-calculation', methods=['POST'])
def api_full_market_value_calculation():
    """
    Calculate full market value with all factors.
    
    Request body:
    {
        "current_popularity": 70,
        "peak_popularity": 85,
        "role": "Main Event",
        "age": 32,
        "years_experience": 12,
        "is_major_superstar": true,
        "is_legend": false,
        "average_match_rating": 4.2,
        "recent_match_rating": 4.5,
        "five_star_match_count": 3,
        "four_plus_match_count": 15,
        "injury_history_count": 2,
        "backstage_reputation": 75,
        "weeks_unemployed": 4,
        "mood": "patient",
        "rival_promotion_interest": 2,
        "highest_rival_offer": 25000,
        "controversy_severity": 0
    }
    """
    try:
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
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/free-agents/market-trend')
def api_get_market_trend():
    """Get current market trend"""
    try:
        return jsonify({
            'success': True,
            'current_trend': market_value_calculator._market_trend.value,
            'available_trends': [t.value for t in MarketTrend]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/free-agents/market-trend', methods=['POST'])
def api_set_market_trend():
    """
    Set market trend (for testing or storyline events).
    
    Request body:
    {
        "trend": "sellers_market"
    }
    """
    try:
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


@app.route('/api/free-agents/top-values')
def api_get_top_market_values():
    """Get free agents sorted by market value"""
    try:
        limit = request.args.get('limit', 10, type=int)
        discovered_only = request.args.get('discovered_only', 'true').lower() == 'true'
        
        if discovered_only:
            agents = free_agent_pool_manager.get_discovered_free_agents()
        else:
            agents = free_agent_pool_manager.available_free_agents
        
        # Sort by market value
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


@app.route('/api/free-agents/bargains')
def api_get_bargain_free_agents():
    """Get free agents who are undervalued (desperate, hungry, or controversy cases)"""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        agents = free_agent_pool_manager.get_discovered_free_agents()
        
        # Find bargains - those whose asking salary is significantly below their potential
        bargains = []
        for fa in agents:
            # Calculate what they "should" be worth vs what they're asking
            quick_estimate = market_value_calculator.get_quick_estimate(
                popularity=fa.popularity,
                role=fa.role,
                age=fa.age,
                is_major_superstar=fa.is_major_superstar
            )
            
            discount = ((quick_estimate - fa.demands.asking_salary) / max(quick_estimate, 1)) * 100
            
            if discount > 15:  # At least 15% below estimate
                bargains.append({
                    'free_agent': fa,
                    'estimated_value': quick_estimate,
                    'asking_salary': fa.demands.asking_salary,
                    'discount_percent': round(discount, 1),
                    'reason': fa.mood_label if fa.mood in [FreeAgentMood.DESPERATE, FreeAgentMood.HUNGRY] else 'Undervalued'
                })
        
        # Sort by discount
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
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/free-agents/<fa_id>/update-reputation', methods=['POST'])
def api_update_free_agent_reputation(fa_id):
    """
    Update a free agent's backstage reputation.
    
    Request body:
    {
        "change": 10,  # Positive or negative
        "reason": "Good interview"
    }
    """
    try:
        fa = free_agent_pool_manager.get_free_agent_by_id(fa_id)
        
        if not fa:
            return jsonify({'success': False, 'error': 'Free agent not found'}), 404
        
        data = request.get_json()
        change = data.get('change', 0)
        reason = data.get('reason', '')
        
        old_reputation = fa.backstage_reputation
        fa.update_reputation(change, reason)
        
        # Recalculate market value after reputation change
        fa.recalculate_market_value(
            year=universe.current_year,
            week=universe.current_week,
            use_calculator=True
        )
        
        free_agent_pool_manager.save_free_agent(fa)
        
        return jsonify({
            'success': True,
            'free_agent_id': fa_id,
            'old_reputation': old_reputation,
            'new_reputation': fa.backstage_reputation,
            'locker_room_leader': fa.locker_room_leader,
            'known_difficult': fa.known_difficult,
            'new_market_value': fa.market_value
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/free-agents/<fa_id>/record-injury', methods=['POST'])
def api_record_free_agent_injury(fa_id):
    """
    Record an injury for market value tracking.
    
    Request body:
    {
        "severity": 2  # 1=Minor, 2=Moderate, 3=Severe
    }
    """
    try:
        fa = free_agent_pool_manager.get_free_agent_by_id(fa_id)
        
        if not fa:
            return jsonify({'success': False, 'error': 'Free agent not found'}), 404
        
        data = request.get_json()
        severity = data.get('severity', 1)
        
        old_value = fa.market_value
        fa.record_injury(severity)
        
        # Recalculate market value after injury
        fa.recalculate_market_value(
            year=universe.current_year,
            week=universe.current_week,
            use_calculator=True
        )
        
        free_agent_pool_manager.save_free_agent(fa)
        
        return jsonify({
            'success': True,
            'free_agent_id': fa_id,
            'injury_history_count': fa.injury_history_count,
            'has_chronic_issues': fa.has_chronic_issues,
            'old_market_value': old_value,
            'new_market_value': fa.market_value,
            'value_change': fa.market_value - old_value
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500



# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Endpoint not found'}), 404
    return render_template('index.html')


@app.errorhandler(500)
def server_error(e):
    return jsonify({
        'error': 'Internal server error',
        'message': str(e)
    }), 500




# ============================================================================
# APPLICATION STARTUP
# ============================================================================

def initialize_app():
    print("=" * 60)
    print("🎮 AWUM - AI Wrestling Universe Manager")
    print("📍 Promotion: Ring of Champions")
    print("🏢 Brands: ROC Alpha, ROC Velocity, ROC Vanguard")
    print("💾 Storage: SQLite Database")
    print("=" * 60)
    
    # Load initial data
    print("\n📦 Loading game data...")
    data_loaded = initialize_universe_data()
    
    # Sync calendar
    print("\n📅 Initializing calendar system...")
    universe.sync_calendar_from_state()
    current_show = universe.calendar.get_current_show()
    next_ppv = universe.calendar.get_next_ppv()
    
    print(f"✅ Calendar initialized with {len(universe.calendar.generated_shows)} shows")
    print(f"   - Current show: {current_show.name if current_show else 'None'}")
    print(f"   - Next PPV: {next_ppv.name if next_ppv else 'None'} (Week {next_ppv.week if next_ppv else '?'})")
    
    # Load storyline state from database
    print("\n📚 Loading storyline state...")
    try:
        storyline_state = database.load_storyline_state()
        if storyline_state and (storyline_state.get('active_storylines') or storyline_state.get('completed_storylines')):
            storyline_engine.load_state(storyline_state)
            print(f"   ✅ Loaded {len(storyline_engine.manager.storylines)} active storylines")
            print(f"   ✅ Loaded {len(storyline_engine.manager.completed_storylines)} completed storylines")
        else:
            print(f"   No saved storyline state found")
    except Exception as e:
        print(f"   ⚠️ Error loading storyline state: {e}")
    
    # Print all 8 PPVs for Year 1
    print("\n🎪 Year 1 PPV/PLE Schedule:")
    year_1_ppvs = [s for s in universe.calendar.generated_shows if s.year == 1 and s.is_ppv]
    for ppv in year_1_ppvs:
        print(f"   - Week {ppv.week:2d}: {ppv.name} ({ppv.tier.upper()})")
    
    print("\n🏆 Registering championship management routes...")
    register_championship_routes(app, database, universe)
    
    # Game systems
    print("\n⚔️  Match simulation engine loaded")
    print("🔥 Feud system initialized")
    print("🤖 AI Creative Director loaded")
    print("📝 Contract management system loaded")
    print("🎂 Aging system loaded")
    print("🎉 Events manager loaded")
    print("🎭 Storyline engine loaded")

    # Load storylines
    print("\n📚 Loading scripted storylines...")
    storylines_path = os.path.join(data_dir, 'storylines_year_one.json')
    try:
        storyline_engine.load_storylines(storylines_path)
    except Exception as e:
        print(f"   ⚠️ Could not load storylines: {e}")
    
    # Initialize injury system (routes are already defined in app.py)
    print("\n🏥 Initializing injury & rehabilitation system...")
    print("   ✅ Injury routes registered")
    
    # Initialize championship hierarchy
    print("\n🏆 Initializing championship hierarchy system...")
    try:
        from persistence.championship_db import create_championship_tables
        create_championship_tables(database)
        
        # Load existing hierarchy state
        _ = universe.championship_hierarchy  # This triggers lazy loading
        print("   ✅ Championship hierarchy loaded")
    except Exception as e:
        print(f"   ⚠️ Championship hierarchy initialization: {e}")
    
    # Stats
    game_state = database.get_game_state()
    print(f"\n📊 Universe Status:")
    print(f"   - Year {game_state['current_year']}, Week {game_state['current_week']}")
    print(f"   - Balance: ${game_state['balance']:,}")
    print(f"   - Roster: {len(universe.wrestlers)} wrestlers")
    print(f"   - Active Feuds: {len(universe.feud_manager.get_active_feuds())}")
    print(f"   - Storylines: {len(storyline_engine.manager.storylines)} loaded")
    
    if data_loaded:
        print("\n✅ Application initialized successfully")
    else:
        print("\n⚠️  WARNING: Some game data failed to load")
    
    print()
    
    # Initialize championship hierarchy
    print("\n🏆 Initializing championship hierarchy system...")
    try:
        from persistence.championship_db import create_championship_tables
        create_championship_tables(database)
        
        # Load existing hierarchy state
        _ = universe.championship_hierarchy  # This triggers lazy loading
        print("   ✅ Championship hierarchy loaded")
    except Exception as e:
        print(f"   ⚠️ Championship hierarchy initialization: {e}")

    # Initialize custom championship tables
    print("\n🏆 Initializing custom championship tables...")
    try:
        from persistence.championship_custom_db import create_custom_championship_tables
        create_custom_championship_tables(database)
        print("   ✅ Custom championship tables created")
    except Exception as e:
        print(f"   ⚠️ Custom championship tables: {e}")
    
    # Check if stats need population
    print("\n📊 Checking stats tables...")
    cursor = database.conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM wrestler_stats')
    stats_count = cursor.fetchone()[0]
    
    if stats_count == 0:
        print("   ⚠️ Stats tables empty, populating from match history...")
        
        # Auto-populate stats
        wrestlers_with_matches = 0
        milestones_created = 0
        
        for wrestler in universe.wrestlers:
            stats_dict = database.calculate_wrestler_stats(wrestler.id)
            
            if stats_dict and stats_dict['record']['total_matches'] > 0:
                database.update_wrestler_stats_cache(wrestler.id)
                wrestlers_with_matches += 1
                
                # Create debut milestone
                cursor.execute('''
                    SELECT * FROM match_history
                    WHERE side_a_ids LIKE ? OR side_b_ids LIKE ?
                    ORDER BY year, week, id
                    LIMIT 1
                ''', (f'%{wrestler.id}%', f'%{wrestler.id}%'))
                
                first_match = cursor.fetchone()
                if first_match:
                    existing = database.get_wrestler_milestones(wrestler.id)
                    if not any(m['milestone_type'] == 'debut' for m in existing):
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
                        milestones_created += 1
        
        database.conn.commit()
        print(f"   ✅ Populated stats for {wrestlers_with_matches} wrestlers")
        print(f"   ✅ Created {milestones_created} debut milestones")
    else:
        print(f"   ✅ Stats tables contain {stats_count} wrestler records")


if __name__ == '__main__':
    initialize_app()
    
    print("🚀 Starting Flask server...")
    print("📱 Access the game at: http://localhost:8080")
    print("⚠️  Press Ctrl+C to stop the server")
    print()
    
    app.run(
        host='0.0.0.0',
        port=8080,
        debug=True,
        use_reloader=False
    )
