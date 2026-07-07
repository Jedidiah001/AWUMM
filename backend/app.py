"""
AWUM - AI Wrestling Universe Manager
Main Flask Application Entry Point

NOW WITH SQLITE DATABASE PERSISTENCE + CONTRACT MANAGEMENT + FREE AGENT POOL
REFACTORED: Routes split into separate modules
STEP 117: Free Agent Pool with Mood System Integrated
STEP 121: Early Renewal System Added
STEP 126: Rival Promotion Interest Generation
"""

from flask import Flask, render_template, jsonify, request
import os
import atexit
import signal
from datetime import datetime


# ============================================================================
# FLASK APP INITIALIZATION
# ============================================================================

app = Flask(
    __name__,
    template_folder='../frontend/templates',
    static_folder='../frontend/static'
)

# Configuration
app.config['JSON_SORT_KEYS'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

# ============================================================================
# DATABASE & CORE SERVICES INITIALIZATION
# ============================================================================

# Paths
data_dir = os.path.join(os.path.dirname(__file__), 'data')
db_path = os.path.join(data_dir, 'awum.db')

# Import persistence layer
from persistence.database import Database
from persistence.universe_db import DatabaseUniverseState
from persistence.initial_data import load_initial_data_to_db
from persistence.lineage_db import create_lineage_tables
from persistence.exclusive_window_db import create_exclusive_window_tables


# Initialize database
database = Database(db_path)
universe = DatabaseUniverseState(database)

# Create lineage tables
create_lineage_tables(database)

# Initialize lineage tracker
from models.title_lineage import TitleLineageTracker
universe.lineage_tracker = TitleLineageTracker(database)

create_exclusive_window_tables(database)
print("✅ Exclusive window tables created")

from economy.rival_interest import rival_interest_engine
rival_interest_engine.load_from_db(database)
app.config['RIVAL_ENGINE'] = rival_interest_engine
print("✅ Rival promotion engine initialized")

# STEP 118: Import Agent Routes (but don't register yet)
from routes.agent_routes import agent_bp, agent_manager as agent_routes_manager
from models.agent_manager import AgentManager

# Alert Routes
from routes.alert_routes import alert_bp

# STEP 121: Import Renewal and Rivals Routes (but don't register yet)
from routes.renewal_routes import renewal_bp
from routes.rivals_routes import rivals_bp

# STEP 126: Rival Promotion Manager & Bidding Wars
from economy.rival_promotion_manager import initialize_rival_promotion_manager
from economy.competing_promotion_ai import CompetingPromotionAI
from economy.bidding_war import BiddingWarEngine
from routes.bidding_war_routes import bidding_war_bp
from routes.negotiation_routes import negotiation_bp
app.register_blueprint(negotiation_bp)

#from routes.booking_routes import booking_bp

#app.register_blueprint(booking_bp)

# NOTE: controversy_bp, morale_bp, recovery_bp, morale_events_bp
# are registered via register_all_routes() in routes/__init__.py
# Do NOT register them here to avoid duplicate registration errors!

# ============================================================================
# GAME SYSTEMS INITIALIZATION
# ============================================================================

# Initialize Agent Manager
agent_manager = AgentManager()

# Initialize Rival Promotion Manager
rival_mgr = initialize_rival_promotion_manager(database)

# Store in app config BEFORE registering blueprints that need them
app.config['AGENT_MANAGER'] = agent_manager
app.config['RIVAL_PROMOTION_MANAGER'] = rival_mgr
app.config['RIVAL_MANAGER'] = rival_mgr  # Alias for compatibility
app.config['BIDDING_WAR_ENGINE'] = BiddingWarEngine(database, rival_mgr)
competing_ai = CompetingPromotionAI(database, rival_mgr)
try:
    competing_ai.initialize_metadata()
except Exception as exc:
    try:
        database.conn.rollback()
    except Exception:
        pass
    print(f"⚠️ Competing promotion metadata init skipped during startup: {exc}")
app.config['COMPETING_PROMOTION_AI'] = competing_ai
app.config['DATABASE'] = database  # Make database available to blueprints
from services.booking_story_media_service import BookingStoryMediaService
app.config['BOOKING_STORY_MEDIA_SERVICE'] = BookingStoryMediaService(database)
from services.simulation_expansion_service import SimulationExpansionService
app.config['SIMULATION_EXPANSION_SERVICE'] = SimulationExpansionService(database)


# Injury Manager
from simulation.injuries import InjuryManager
import simulation.injuries
injury_manager = InjuryManager(database, medical_staff_tier="Standard")
simulation.injuries.injury_manager = injury_manager

# STEP 117: Free Agent Pool Manager (New Import)
from models.free_agent_pool import FreeAgentPool

# Initialize Free Agent Pool
print("\n👥 Initializing Free Agent Pool...")
try:
    free_agent_pool = FreeAgentPool(database)
    app.config['FREE_AGENT_POOL'] = free_agent_pool
    
    # Get initial summary
    pool_summary = free_agent_pool.get_pool_summary()
    print(f"✅ Free Agent Pool initialized")
    print(f"   - Total Available: {pool_summary.get('total_available', 0)}")
    print(f"   - Discovered: {pool_summary.get('discovered', 0)}")
    print(f"   - Scouting Level: {pool_summary.get('scouting_level', 1)}/5")
    
    # Auto-discover based on scouting level
    if pool_summary.get('total_available', 0) > 0:
        discovered = free_agent_pool.auto_discover_by_scouting_level()
        if discovered:
            print(f"   - Auto-discovered {len(discovered)} free agents")
    
    # Link rival manager to free agent pool
    free_agent_pool.rival_manager = rival_mgr
    
    free_agent_pool_manager = free_agent_pool  # Alias for compatibility
    
except Exception as e:
    print(f"⚠️ Failed to initialize Free Agent Pool: {e}")
    import traceback
    traceback.print_exc()
    # Create empty pool as fallback
    free_agent_pool = FreeAgentPool(database)
    free_agent_pool.rival_manager = rival_mgr
    app.config['FREE_AGENT_POOL'] = free_agent_pool
    free_agent_pool_manager = free_agent_pool

print("🤝 Rival promotion interest system loaded (STEP 126)")

# Legacy free agent pool (keeping for backward compatibility)
try:
    from economy.free_agent_pool import initialize_free_agent_pool
    legacy_free_agent_pool = initialize_free_agent_pool(database)
    # Don't override the new pool manager
    print("   ℹ️ Legacy free agent pool also loaded for compatibility")
except ImportError:
    print("   ℹ️ Legacy free agent pool not available")
    legacy_free_agent_pool = None

# Storyline Engine
from creative.storylines import storyline_engine

# Draft Manager
from creative.draft_manager import draft_manager

# Save Manager
from persistence.save_manager import SaveManager
saves_dir = os.path.join(data_dir, 'saves')
save_manager = SaveManager(saves_dir)

# ============================================================================
# BLUEPRINT REGISTRATION (After all dependencies are configured)
# ============================================================================

import routes.agent_routes
routes.agent_routes.agent_manager = agent_manager

app.register_blueprint(agent_bp)
print("🤝 Agent representation system loaded")

app.register_blueprint(alert_bp)
print("📢 Contract alert system loaded")

app.register_blueprint(renewal_bp)
print("🔄 Early renewal system loaded")

# Register rivals blueprint AFTER rival_mgr is in app.config
app.register_blueprint(rivals_bp)
print("🤝 Rivals routes loaded")

app.register_blueprint(bidding_war_bp)
print("⚔️ Bidding war system loaded")

# REMOVED: Duplicate registration of exclusive_window_bp
# This is now handled by register_all_routes() in routes/__init__.py
print("🔒 Exclusive negotiating windows loaded (STEP 124)")


# ============================================================================
# ROUTE REGISTRATION
# ============================================================================

# Register reign goals API (separate blueprint)
from api.reign_goals_api import reign_goals_bp
app.register_blueprint(reign_goals_bp)

from routes.show_production_routes import show_production_bp
from routes.roster_business_routes import roster_business_bp
app.register_blueprint(show_production_bp)
app.register_blueprint(roster_business_bp)

# Register championship routes (legacy - keeping for compatibility)
from routes.championship_routes import register_championship_routes

# Register all modular routes
from routes import register_all_routes

register_all_routes(
    app,
    database=database,
    universe=universe,
    injury_manager=injury_manager,
    free_agent_pool=free_agent_pool_manager,  # Pass the new pool manager
    save_manager=save_manager,
    storyline_engine=storyline_engine,
    draft_manager=draft_manager,
    data_dir=data_dir
)

# ============================================================================
# VIEW ROUTES (HTML Pages)
# ============================================================================

@app.route('/controversy')
def controversy_page():
    return render_template('controversy_loyalty.html')


@app.route('/morale')
def morale_view():
    return render_template('morale.html')


@app.route('/locker-room')
def locker_room_view():
    """Steps 260-265: Locker Room — Morale Events, Crisis, Creative Seeds"""
    return render_template('locker_room.html')





@app.route('/')
def index():
    return render_template('index.html')


@app.route('/office')
def office_view():
    return render_template('office.html')


@app.route('/booking')
def booking_view():
    return render_template('booking.html')


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


@app.route('/media-business')
def media_business_view():
    return render_template('media_business.html')


@app.route('/caw')
def caw_view():
    return render_template('caw.html')


@app.route('/championships')
def championships_view():
    return render_template('championships.html')


@app.route('/free-agents')
def free_agents_view():
    """STEP 117: Free Agents view with mood system"""
    return render_template('free_agents.html')


@app.route('/stats')
def stats_view():
    return render_template('stats.html')


@app.route('/saves')
def saves_view():
    return render_template('saves.html')


@app.route('/tag-teams')
def tag_teams_view():
    return render_template('tag_teams.html')


@app.route('/factions')
def factions_view():
    return render_template('factions.html')


@app.route('/relationships')
def relationships_view():
    return render_template('relationships.html')


@app.route('/storylines')
def storylines_view():
    return render_template('storylines.html')


@app.route('/awards')
def awards_view():
    return render_template('awards.html')


@app.route('/draft')
def draft_view():
    return render_template('draft.html')


@app.route('/developmental')
def developmental_view():
    """Developmental brand (ROC Nexus) management page"""
    return render_template('developmental.html')


@app.route('/injuries')
def injuries_view():
    return render_template('injuries.html')


@app.route('/wellness')
def wellness_view():
    return render_template('wellness.html')


@app.route('/booking-test')
def booking_test_view():
    return render_template('booking_test.html')


@app.route('/agents')
def agents_view():
    """STEP 118: Agents representation view"""
    return render_template('agents.html')


@app.route('/alerts')
def alerts_view():
    """STEP 120: Contract Expiration Alerts view"""
    return render_template('alerts.html')


@app.route('/renewals')
def renewals_view():
    """STEP 121: Early Renewal System view"""
    return render_template('renewals.html')

@app.route('/show-production')
def show_production_view():
    return render_template('show_production.html')

@app.route('/calendar')
def calendar_view():
    return render_template('calendar.html')

@app.route('/evolve')
def evolve_view():
    return render_template('evolve.html')

@app.route('/character-system')
def character_system_view():
    return render_template('character_system.html')

@app.route('/world-feed')
def world_feed_view():
    return render_template('world_feed.html')

@app.route('/rivals-intelligence')
def rivals_intelligence_view():
    return render_template('rivals_intelligence.html')

@app.route('/legacy-expansion')
def legacy_expansion_view():
    """Dashboard for feature sets added in Steps 126-212."""
    return render_template('legacy_expansion.html')

@app.route('/simulation-expansion')
def simulation_expansion_view():
    """Enterprise simulation dashboard for features 149-182 and 243-250."""
    return render_template('simulation_expansion.html')



@app.route('/booker')
def booker_view():
    return render_template('booker.html')
@app.route('/history-hub')
def history_hub_view():
    """Historical records and archive dashboard."""
    return render_template('history_hub.html')

@app.route('/contract-card/<share_id>')
def contract_card_view(share_id):
    """View a shared contract card"""
    return render_template('contract_card.html', share_id=share_id)


@app.route('/api/legacy/overview')
def legacy_overview_api():
    """Aggregate overview for the legacy expansion frontend page."""
    cursor = database.conn.cursor()

    def _table_rows(table_name: str) -> int:
        try:
            cursor.execute(f"SELECT COUNT(*) AS c FROM {table_name}")
            row = cursor.fetchone()
            return int(row["c"] if row and "c" in row.keys() else row[0])
        except Exception:
            return 0

    groups = {
        "tv_media_126_137": [
            "tv_ratings_weekly",
            "tv_ratings_quarter_hours",
            "network_relationship_log",
            "media_ecosystem_log",
        ],
        "venues_138_148": [
            "venue_strategy_profiles",
            "regional_popularity",
            "tour_routing_plans",
            "venue_relationships",
            "venue_external_factors",
            "venue_sellout_streaks",
        ],
        "industry_161_170": [
            "industry_promotions",
            "industry_talent_movement",
            "industry_partnerships",
            "invasion_storylines",
            "industry_sentiment_log",
            "market_share_snapshots",
        ],
        "development_171_182": [
            "evolve_performance_center",
            "evolve_trainers",
            "evolve_curricula",
            "evolve_roster",
            "evolve_events",
        ],
        "marketing_183_192": [
            "marketing_campaigns",
            "event_promotion_log",
        ],
        "staff_193_202": [
            "staff_roles",
            "talent_relations_log",
        ],
        "history_203_212": [
            "history_matches",
            "history_storylines",
            "history_championships",
            "hall_of_fame",
            "rivalry_history",
            "history_anniversaries",
            "history_records",
            "historical_moments",
            "named_eras",
            "wrestler_legacy_stats",
        ],
    }

    payload = {}
    for group_name, tables in groups.items():
        payload[group_name] = {
            "tables": [{ "name": t, "rows": _table_rows(t) } for t in tables],
            "total_rows": sum(_table_rows(t) for t in tables),
        }

    return jsonify({"ok": True, "groups": payload})

    
# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Endpoint not found'}), 404
    if request.path == '/contract-market':
        return 'Contract Market page has been removed. Use /contracts.', 404
    return render_template('index.html')


@app.errorhandler(500)
def server_error(e):
    return jsonify({
        'error': 'Internal server error',
        'message': str(e)
    }), 500


# ============================================================================
# SHUTDOWN HANDLER
# ============================================================================

def save_universe_on_exit():
    """Save universe state when app closes"""
    original_sigint = signal.signal(signal.SIGINT, signal.SIG_IGN)
    
    try:
        print("\n💾 Saving universe state...")
        universe.save_all()
        
        # STEP 117: Save free agent pool
        if free_agent_pool:
            print("💾 Saving free agent pool...")
            free_agent_pool.save_all()
        
        print("✅ Universe saved successfully")
    except Exception as e:
        print(f"❌ Failed to save on exit: {e}")
        import traceback
        traceback.print_exc()
    finally:
        signal.signal(signal.SIGINT, original_sigint)


atexit.register(save_universe_on_exit)


# ============================================================================
# DATA LOADING FUNCTIONS
# ============================================================================

def initialize_universe_data():
    """Load initial data into database if needed"""
    return load_initial_data_to_db(database, data_dir)


def load_initial_free_agents():
    """
    STEP 117: Load initial free agents from JSON.
    Called only if the pool is empty.
    """
    import json
    from models.free_agent import FreeAgent, FreeAgentSource, FreeAgentVisibility, FreeAgentMood
    
    json_path = os.path.join(data_dir, 'initial_free_agents.json')
    
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        if not free_agent_pool:
            print("⚠️ Free Agent Pool not initialized, skipping")
            return 0
        
        loaded_count = 0
        
        for fa_data in data.get('free_agents', []):
            # Create free agent
            fa_id = f"fa_{fa_data['wrestler_name'].replace(' ', '_').lower()}"
            wrestler_id = f"w_{fa_data['wrestler_name'].replace(' ', '_').lower()}"
            
            attrs = fa_data.get('attributes', {})
            
            fa = FreeAgent(
                free_agent_id=fa_id,
                wrestler_id=wrestler_id,
                wrestler_name=fa_data['wrestler_name'],
                age=fa_data['age'],
                gender=fa_data['gender'],
                alignment=fa_data['alignment'],
                role=fa_data['role'],
                brawling=attrs.get('brawling', 50),
                technical=attrs.get('technical', 50),
                speed=attrs.get('speed', 50),
                mic=attrs.get('mic', 50),
                psychology=attrs.get('psychology', 50),
                stamina=attrs.get('stamina', 50),
                years_experience=fa_data.get('years_experience', 5),
                is_major_superstar=fa_data.get('is_major_superstar', False),
                popularity=fa_data.get('popularity', 50),
                peak_popularity=fa_data.get('popularity', 50),
                source=FreeAgentSource(fa_data.get('source', 'released')),
                visibility=FreeAgentVisibility(fa_data.get('visibility', 2)),
                mood=FreeAgentMood.PATIENT,
                origin_region=fa_data.get('origin_region', 'domestic'),
                is_prospect=fa_data.get('is_prospect', False),
                ceiling_potential=fa_data.get('ceiling_potential', 50),
                has_controversy=fa_data.get('has_controversy', False),
                discovered=fa_data.get('visibility', 2) <= 1  # Auto-discover tier 1
            )
            
            free_agent_pool.available_free_agents.append(fa)
            free_agent_pool.save_free_agent(fa)
            loaded_count += 1
        
        print(f"✅ Loaded {loaded_count} initial free agents from JSON")
        return loaded_count
        
    except FileNotFoundError:
        print(f"   ℹ️ {json_path} not found, skipping initial free agents")
        return 0
    except Exception as e:
        print(f"⚠️ Error loading initial free agents: {e}")
        import traceback
        traceback.print_exc()
        return 0


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
    
    # STEP 117: Load initial free agents if pool is empty
    if free_agent_pool:
        pool_summary = free_agent_pool.get_pool_summary()
        if pool_summary.get('total_available', 0) == 0:
            print("\n👥 Free agent pool is empty, loading initial free agents...")
            loaded = load_initial_free_agents()
            if loaded > 0:
                # Refresh pool after loading
                free_agent_pool.load_from_database()
                # Auto-discover based on scouting level
                discovered = free_agent_pool.auto_discover_by_scouting_level()
                if discovered:
                    print(f"   🔍 Auto-discovered {len(discovered)} free agents")
    
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
            print(f"   ℹ️ No saved storyline state found")
    except Exception as e:
        print(f"   ⚠️ Error loading storyline state: {e}")
    
    # Print all 8 PPVs for Year 1
    print("\n🎪 Year 1 PPV/PLE Schedule:")
    year_1_ppvs = [s for s in universe.calendar.generated_shows if s.year == 1 and s.is_ppv]
    for ppv in year_1_ppvs:
        print(f"   - Week {ppv.week:2d}: {ppv.name} ({ppv.tier.upper()})")
    
    # Register legacy championship routes
    print("\n🏆 Registering championship management routes...")
    register_championship_routes(app, database, universe)
    
    # Game systems status
    print("\n⚔️  Match simulation engine loaded")
    print("🔥 Feud system initialized")
    print("🤖 AI Creative Director loaded")
    print("📝 Contract management system loaded")
    print("🎂 Aging system loaded")
    print("🎉 Events manager loaded")
    print("🎭 Storyline engine loaded")
    print("🏥 Injury & rehabilitation system loaded")
    print("💰 Free agent pool loaded (STEP 117 - Mood System)")
    print("🔄 Early renewal system loaded (STEP 121)")
    print("🤝 Rival promotion interest system loaded (STEP 126)")
    print("💾 Save/Load system loaded")

    # Load storylines from file if not loaded from state
    print("\n📚 Loading scripted storylines...")
    storylines_path = os.path.join(data_dir, 'storylines_year_one.json')
    try:
        if not storyline_engine.loaded:
            storyline_engine.load_storylines(storylines_path)
    except Exception as e:
        print(f"   ⚠️ Could not load storylines: {e}")
    
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
        _populate_initial_stats()
    else:
        print(f"   ✅ Stats tables contain {stats_count} wrestler records")
    
    # STEP 117: Free Agent Pool Health Check
    if free_agent_pool:
        print("\n👥 Free Agent Pool Status:")
        pool_health = free_agent_pool.get_pool_health_report()
        print(f"   - Total Available: {pool_health['total_available']}")
        print(f"   - Discovered: {pool_health['discovered']} ({pool_health['discovery_rate']}%)")
        print(f"   - Scouting Level: {pool_health['scouting_level']}/5")
        print(f"   - Regions Scouted: {pool_health['regions_scouted']}/5")
        print(f"   - Legends: {pool_health['legends_available']}")
        print(f"   - Prospects: {pool_health['prospects_available']}")
        print(f"   - International: {pool_health['international_available']}")
        
        if pool_health['by_mood']:
            print(f"   - Mood Breakdown:")
            for mood, count in pool_health['by_mood'].items():
                print(f"      • {mood.title()}: {count}")
    
    # STEP 126: Rival Promotion Status
    if rival_mgr:
        print("\n🤝 Rival Promotion Status:")
        rival_summary = rival_mgr.get_summary()
        print(f"   - Total Promotions: {rival_summary['total_promotions']}")
        print(f"   - Total Remaining Budget: ${rival_summary['total_remaining_budget']:,}")
        print(f"   - Signed This Year: {rival_summary['total_signed_this_year']}")
        print(f"   - Active Pursuits: {rival_summary['active_pursuits']}")
        if rival_summary.get('by_tier'):
            print(f"   - By Tier:")
            for tier, count in rival_summary['by_tier'].items():
                print(f"      • {tier}: {count}")
    
    # Print final status
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


def _populate_initial_stats():
    """Auto-populate stats tables from match history"""
    wrestlers_with_matches = 0
    milestones_created = 0
    
    for wrestler in universe.wrestlers:
        stats_dict = database.calculate_wrestler_stats(wrestler.id)
        
        if stats_dict and stats_dict['record']['total_matches'] > 0:
            database.update_wrestler_stats_cache(wrestler.id)
            wrestlers_with_matches += 1
            
            # Create debut milestone
            cursor = database.conn.cursor()
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


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    initialize_app()
    
    print("🚀 Starting Flask server...")
    print("   🏠 Locker Room (Steps 260-265): http://localhost:8080/locker-room")
    print("📱 Access the game at: http://localhost:8080")
    print("   🆕 Free Agents (STEP 117): http://localhost:8080/free-agents")
    print("   🔄 Renewals (STEP 121): http://localhost:8080/renewals")
    print("   🤝 Rival Promotions (STEP 126): Integrated with free agents")
    print("⚠️  Press Ctrl+C to stop the server")
    print()
    
    app.run(
        host='0.0.0.0',
        port=8080,
        debug=True,
        use_reloader=False
    )
