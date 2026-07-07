"""
Initial Free Agent Pool Loader
Loads the starting free agent pool from JSON data.
"""

import os
import json
from typing import Dict, Any

from models.free_agent import (
    FreeAgent, FreeAgentSource, FreeAgentVisibility, FreeAgentMood,
    AgentInfo, AgentType, ContractDemands, RivalInterest, ContractHistory
)
from persistence.free_agent_db import save_free_agent


def load_initial_free_agents(database, data_dir: str) -> int:
    """
    Load initial free agent pool from JSON file.
    Returns count of loaded free agents.
    """
    json_path = os.path.join(data_dir, 'initial_free_agents.json')
    
    if not os.path.exists(json_path):
        print(f"⚠️ No initial_free_agents.json found at {json_path}")
        return 0
    
    # Check if free agents already loaded - FIXED: Check correctly
    cursor = database.conn.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM free_agents')
    existing_count = cursor.fetchone()['count']
    
    if existing_count > 0:
        print(f"✅ Free agent pool already has {existing_count} entries")
        return existing_count
    
    # Load JSON data
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading JSON file: {e}")
        return 0
    
    free_agents_data = data.get('free_agents', [])
    rival_interest_data = data.get('rival_interest', [])
    contract_history_data = data.get('contract_history', [])
    
    if len(free_agents_data) == 0:
        print("⚠️ No free agents found in JSON file")
        return 0
    
    print(f"📦 Loading {len(free_agents_data)} free agents from JSON...")
    
    # Build lookup maps
    rival_by_fa = {}
    for ri in rival_interest_data:
        fa_id = ri['free_agent_id']
        if fa_id not in rival_by_fa:
            rival_by_fa[fa_id] = []
        rival_by_fa[fa_id].append(RivalInterest(
            promotion_name=ri['promotion_name'],
            interest_level=ri['interest_level'],
            offer_salary=ri.get('offer_salary', 0),
            offer_made=ri.get('offer_made', False),
            deadline_week=ri.get('deadline_week')
        ))
    
    history_by_fa = {}
    for ch in contract_history_data:
        fa_id = ch['free_agent_id']
        if fa_id not in history_by_fa:
            history_by_fa[fa_id] = []
        history_by_fa[fa_id].append(ContractHistory(
            promotion_name=ch['promotion_name'],
            start_year=ch['start_year'],
            end_year=ch['end_year'],
            departure_reason=ch['departure_reason'],
            final_salary=ch.get('final_salary', 5000),
            was_champion=ch.get('was_champion', False),
            relationship_on_departure=ch.get('relationship_on_departure', 50)
        ))
    
    loaded_count = 0
    
    for fa_data in free_agents_data:
        try:
            # Map visibility integer to enum
            visibility_val = fa_data.get('visibility', 2)
            visibility = FreeAgentVisibility(visibility_val)
            
            # Create base demands
            base_salary = fa_data.get('market_value', 10000)
            demands = ContractDemands(
                minimum_salary=int(base_salary * 0.7),
                asking_salary=base_salary,
                preferred_length_weeks=52 if fa_data.get('age', 30) < 35 else 26
            )
            
            # Adjust demands for special types
            if fa_data.get('is_legend'):
                demands.creative_control_level = 3
                demands.finish_protection = True
                demands.max_appearances_per_year = 50
            
            if fa_data.get('is_prospect'):
                demands.minimum_salary = 1000
                demands.asking_salary = 3000
                demands.preferred_length_weeks = 104
            
            fa = FreeAgent(
                free_agent_id=fa_data['id'],
                wrestler_id=fa_data['wrestler_id'],
                wrestler_name=fa_data['wrestler_name'],
                
                age=fa_data['age'],
                gender=fa_data['gender'],
                alignment=fa_data['alignment'],
                role=fa_data['role'],
                
                brawling=fa_data['brawling'],
                technical=fa_data['technical'],
                speed=fa_data['speed'],
                mic=fa_data['mic'],
                psychology=fa_data['psychology'],
                stamina=fa_data['stamina'],
                
                years_experience=fa_data['years_experience'],
                is_major_superstar=fa_data.get('is_major_superstar', False),
                popularity=fa_data['popularity'],
                
                source=FreeAgentSource(fa_data['source']),
                visibility=visibility,
                mood=FreeAgentMood(fa_data['mood']),
                market_value=fa_data['market_value'],
                weeks_unemployed=fa_data.get('weeks_unemployed', 0),
                
                demands=demands,
                rival_interest=rival_by_fa.get(fa_data['id'], []),
                contract_history=history_by_fa.get(fa_data['id'], []),
                
                has_controversy=fa_data.get('has_controversy', False),
                controversy_type=fa_data.get('controversy_type'),
                controversy_severity=fa_data.get('controversy_severity', 0),
                time_since_incident_weeks=fa_data.get('time_since_incident_weeks', 0),
                
                is_legend=fa_data.get('is_legend', False),
                retirement_status=fa_data.get('retirement_status', 'active'),
                comeback_likelihood=fa_data.get('comeback_likelihood', 50),
                
                origin_region=fa_data.get('origin_region', 'domestic'),
                requires_visa=fa_data.get('requires_visa', False),
                exclusive_willing=fa_data.get('exclusive_willing', True),
                
                is_prospect=fa_data.get('is_prospect', False),
                training_investment_needed=fa_data.get('training_investment_needed', 0),
                ceiling_potential=fa_data.get('ceiling_potential', 50),
                
                available_from_year=1,
                available_from_week=1,
                
                # Headline news is auto-discovered
                discovered=(visibility == FreeAgentVisibility.HEADLINE_NEWS)
            )
            
            save_free_agent(database, fa)
            loaded_count += 1
            print(f"   ✓ Loaded {fa.wrestler_name}")
            
        except Exception as e:
            print(f"⚠️ Error loading free agent {fa_data.get('wrestler_name', 'unknown')}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    database.conn.commit()
    print(f"✅ Loaded {loaded_count} free agents into pool")
    
    return loaded_count