"""
AWUM Routes Package
All API route blueprints for the application
"""

from .core_routes import core_bp
from .roster_routes import roster_bp
from .feud_routes import feud_bp
from .match_routes import match_bp
from .booking_routes import booking_bp
from .contract_routes import contract_bp
from .stats_routes import stats_bp
from .save_routes import save_bp
from .tag_team_routes import tag_team_bp
from .faction_routes import faction_bp
from .relationship_routes import relationship_bp
from .segment_routes import segment_bp
from .storyline_routes import storyline_bp
from .awards_routes import awards_bp
from .caw_routes import caw_bp
from .draft_routes import draft_bp
from .injury_routes import injury_bp
from .title_situation_routes import title_situation_bp
from .custom_championship_routes import custom_championship_bp
from .defense_frequency_routes import defense_frequency_bp
from .free_agent_routes import free_agent_bp
from .market_value_routes import market_value_bp
from .show_routes import show_bp
from .lineage_routes import lineage_bp
from .debug_routes import debug_bp
from .free_agency_declaration_routes import free_agency_declaration_bp
from .exclusive_window_routes import exclusive_window_bp
from .bidding_routes import bidding_bp
from .controversy_loyalty_routes import controversy_bp
from .morale_routes import morale_bp
from .recovery_routes import recovery_bp
from .morale_events_routes import morale_events_bp
from .wellness_routes import wellness_bp
from .finance_routes import finance_bp
from .venue_routes import venue_bp
from .evolve_routes import evolve_bp
from .world_feed_routes import world_feed_bp
from .history_hub_routes import history_hub_bp
from .booker_routes import booker_bp
from .developmental_routes import developmental_bp
from .character_system_routes import character_system_bp
from .phase_expansion_routes import phase_expansion_bp
from .simulation_expansion_routes import simulation_expansion_bp
from .contract_market_routes import contract_market_bp

# Existing imports...
from models.wrestler import Wrestler
from models.championship import Championship
from models.feud import Feud

# Add these new imports:
#from models.show_db import Show, ShowMatch, ShowSegment


def register_all_routes(app, database, universe, **kwargs):
    """
    Register all route blueprints with the Flask app.
    """

    # Store references in app config for routes to access
    app.config['DATABASE'] = database
    app.config['UNIVERSE'] = universe

    # Store additional managers/services
    for key, value in kwargs.items():
        app.config[key.upper()] = value

    # Initialize Developmental Roster System
    if 'DEV_ROSTER_MANAGER' not in app.config:
        try:
            from models.developmental_roster import DevelopmentalRosterManager
            from simulation.call_up_engine import CallUpEngine
            
            dev_manager = DevelopmentalRosterManager()
            call_up_engine = CallUpEngine(dev_manager)
            
            app.config['DEV_ROSTER_MANAGER'] = dev_manager
            app.config['CALL_UP_ENGINE'] = call_up_engine
            print("✅ Developmental roster system initialized")
        except Exception as e:
            print(f"⚠️ Could not initialize developmental system: {e}")
            app.config['DEV_ROSTER_MANAGER'] = None
            app.config['CALL_UP_ENGINE'] = None

    # STEP 121: Initialize promise manager if not already provided
    if 'PROMISE_MANAGER' not in app.config:
        try:
            from economy.contract_promises import initialize_promise_manager
            promise_manager = initialize_promise_manager(database)
            app.config['PROMISE_MANAGER'] = promise_manager
            print("✅ Promise manager initialized")
        except Exception as e:
            print(f"⚠️ Could not initialize promise manager: {e}")
            app.config['PROMISE_MANAGER'] = None

    # STEP 126: Ensure rival engine is in app config for bidding routes
    if 'RIVAL_ENGINE' not in app.config:
        try:
            from economy.rival_interest import rival_interest_engine
            rival_interest_engine.load_from_db(database)
            app.config['RIVAL_ENGINE'] = rival_interest_engine
            print("✅ Rival engine initialized in register_all_routes")
        except Exception as e:
            print(f"⚠️ Could not initialize rival engine: {e}")

    # Register all blueprints
    blueprints = [
        core_bp,
        roster_bp,
        feud_bp,
        match_bp,
        booking_bp,
        contract_bp,
        stats_bp,
        save_bp,
        tag_team_bp,
        faction_bp,
        relationship_bp,
        segment_bp,
        storyline_bp,
        awards_bp,
        caw_bp,
        draft_bp,
        injury_bp,
        title_situation_bp,
        custom_championship_bp,
        defense_frequency_bp,
        free_agent_bp,
        market_value_bp,
        show_bp,
        lineage_bp,
        debug_bp,
        free_agency_declaration_bp,
        exclusive_window_bp,
        bidding_bp,
        controversy_bp,
        morale_bp,
        recovery_bp,
        morale_events_bp,
        wellness_bp,
        finance_bp,
        venue_bp,
        evolve_bp,
        world_feed_bp,
        history_hub_bp,
        booker_bp,
        developmental_bp,
        character_system_bp,
        phase_expansion_bp,
        simulation_expansion_bp,
        contract_market_bp,
    ]

    # DEBUG: Print all blueprint names to find duplicates
    print("\n" + "="*50)
    print("BLUEPRINT REGISTRATION DEBUG")
    print("="*50)
    bp_names = {}
    for bp in blueprints:
        name = bp.name
        if name in bp_names:
            print(f"❌ DUPLICATE FOUND: '{name}'")
            print(f"   First:  {bp_names[name]}")
            print(f"   Second: {bp}")
        else:
            bp_names[name] = bp
        print(f"   Blueprint: {name} -> {bp}")
    print("="*50 + "\n")

    # Register with duplicate check
    registered_names = set()
    for bp in blueprints:
        if bp.name in registered_names:
            print(f"⚠️ SKIPPING duplicate blueprint: '{bp.name}'")
            continue
        registered_names.add(bp.name)
        app.register_blueprint(bp)

    print(f"✅ Registered {len(registered_names)} route blueprints")

    # STEP 121: Verify contract promises table exists
    try:
        cursor = database.conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='contract_promises'
        """)

        if not cursor.fetchone():
            print("⚠️ Contract promises table not found - creating...")
            database.create_contract_promises_table()
        else:
            print("✅ Contract promises table verified")
    except Exception as e:
        print(f"⚠️ Could not verify promises table: {e}")


__all__ = [
    'register_all_routes',
    'core_bp',
    'roster_bp',
    'feud_bp',
    'match_bp',
    'booking_bp',
    'contract_bp',
    'stats_bp',
    'save_bp',
    'tag_team_bp',
    'faction_bp',
    'relationship_bp',
    'segment_bp',
    'storyline_bp',
    'awards_bp',
    'caw_bp',
    'draft_bp',
    'injury_bp',
    'title_situation_bp',
    'custom_championship_bp',
    'defense_frequency_bp',
    'free_agent_bp',
    'market_value_bp',
    'show_bp',
    'lineage_bp',
    'debug_bp',
    'free_agency_declaration_bp',
    'exclusive_window_bp',
    'bidding_bp',
    'controversy_bp',
    'morale_bp',
    'recovery_bp',
    'morale_events_bp',
    'wellness_bp',
    'finance_bp',
    'evolve_bp',
    'world_feed_bp',
    'history_hub_bp',
    'booker_bp',
    'developmental_bp',
    'character_system_bp',
    'phase_expansion_bp',
    'simulation_expansion_bp',
    'contract_market_bp',
]
