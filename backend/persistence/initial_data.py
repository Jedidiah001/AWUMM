"""
Initial Data Loader
Loads initial roster and championships into SQLite database.
Only runs if database is empty.
"""

import json
import os
from models.wrestler import Wrestler
from models.championship import Championship
from persistence.initial_free_agents import load_initial_free_agents


def load_initial_data_to_db(database, data_dir: str):
    """
    Load initial roster and championships from JSON into database.
    Only loads if database is empty.
    """
    
    # Check if we already have wrestlers
    existing_wrestlers = database.get_all_wrestlers(active_only=False)
    
    if len(existing_wrestlers) > 0:
        print(f"   Database already contains {len(existing_wrestlers)} wrestlers, skipping initial load")
        return True
    
    print("   Database is empty, loading initial data...")
    
    # Load roster from JSON
    roster_path = os.path.join(data_dir, 'initial_roster.json')
    
    try:
        with open(roster_path, 'r', encoding='utf-8') as f:
            roster_data = json.load(f)
        
        print(f"   Loading {len(roster_data)} wrestlers...")
        for wrestler_dict in roster_data:
            wrestler = Wrestler.from_dict(wrestler_dict)
            database.save_wrestler(wrestler)
        
        print(f"   ✅ Loaded {len(roster_data)} wrestlers")
        
    except FileNotFoundError:
        print(f"   ❌ ERROR: initial_roster.json not found")
        return False
    except Exception as e:
        print(f"   ❌ ERROR loading roster: {e}")
        return False
    
    # Load championships from JSON
    champ_path = os.path.join(data_dir, 'championships.json')
    
    try:
        with open(champ_path, 'r', encoding='utf-8') as f:
            champ_data = json.load(f)
        
        print(f"   Loading {len(champ_data)} championships...")
        for champ_dict in champ_data:
            championship = Championship.from_dict(champ_dict)
            database.save_championship(championship)
        
        print(f"   ✅ Loaded {len(champ_data)} championships")
        
    except FileNotFoundError:
        print(f"   ❌ ERROR: championships.json not found")
        return False
    except Exception as e:
        print(f"   ❌ ERROR loading championships: {e}")
        return False
    
    # Load free agents
    free_agent_count = load_initial_free_agents(database, data_dir)
    
    return True