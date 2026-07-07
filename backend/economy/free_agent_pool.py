"""
Free Agent Pool Manager
Manages the dynamic pool of unsigned wrestlers.
Steps 113-118: Core free agent infrastructure
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import random
import json

from models.free_agent import (
    FreeAgent, FreeAgentSource, FreeAgentVisibility, FreeAgentMood,
    AgentInfo, AgentType, ContractDemands, RivalInterest, ContractHistory
)

from economy.free_agent_moods import MoodProcessor, get_mood_processor
from models.free_agent_mood import (
    FreeAgentMood, MoodEffects, MoodTransitionRules,
    calculate_mood, get_mood_modifiers
)


# Agent name pools for generation
AGENT_NAMES = [
    "Paul Heyman", "Scott Boras", "Arn Malenko", "Jimmy Hart",
    "Bobby Heenan Jr.", "Teddy Long III", "Vickie Guerrero",
    "Dutch Mantell", "Jim Cornette Jr.", "Sunny Days Agency",
    "The Franchise Group", "Elite Talent Management", "Titan Sports Agency",
    "Sterling Associates", "The Advocate Group"
]

# Rival promotion names
RIVAL_PROMOTIONS = [
    "Dynasty Pro Wrestling",
    "Global Championship Wrestling", 
    "Apex Wrestling Federation",
    "Revolution Pro",
    "Empire State Wrestling",
    "Pacific Coast Championship Wrestling",
    "Midwest Wrestling Alliance",
    "Southern Fried Wrestling"
]

# International regions and their characteristics
INTERNATIONAL_REGIONS = {
    'japan': {
        'style_bonus': {'technical': 10, 'psychology': 5},
        'visa_required': True,
        'exclusive_likelihood': 0.3
    },
    'mexico': {
        'style_bonus': {'speed': 10, 'technical': 5},
        'visa_required': True,
        'exclusive_likelihood': 0.4
    },
    'uk': {
        'style_bonus': {'technical': 8, 'brawling': 5},
        'visa_required': True,
        'exclusive_likelihood': 0.6
    },
    'europe': {
        'style_bonus': {'technical': 5, 'speed': 5},
        'visa_required': True,
        'exclusive_likelihood': 0.5
    },
    'australia': {
        'style_bonus': {'brawling': 5, 'stamina': 5},
        'visa_required': True,
        'exclusive_likelihood': 0.7
    },
    'domestic': {
        'style_bonus': {},
        'visa_required': False,
        'exclusive_likelihood': 1.0
    }
}


class FreeAgentPoolManager:
    """
    Manages the complete free agent ecosystem.
    
    Responsibilities:
    - Maintain pool of available free agents
    - Handle additions from releases, expirations, prospects
    - Process rival promotion interest
    - Track market dynamics
    - Manage discovery/scouting
    """
    
    def __init__(self, database):
        self.db = database
        self._free_agents: Dict[str, FreeAgent] = {}
        self._next_fa_id = 1
        self._scouting_level = 1  # 1-5, affects discovery
        self._scouting_network = {
            'japan': False,
            'mexico': False,
            'uk': False,
            'europe': False,
            'australia': False
        }
        
        self.mood_processor = get_mood_processor(database)
        self._load_from_database()
    
    def _load_from_database(self):
        """Load free agents from database"""
        from persistence.free_agent_db import get_all_free_agents
        
        try:
            fa_dicts = get_all_free_agents(self.db, available_only=False, discovered_only=False)
            
            for fa_dict in fa_dicts:
                fa = self._dict_to_free_agent(fa_dict)
                self._free_agents[fa.id] = fa
                
                # Track highest ID for new agents
                try:
                    id_num = int(fa.id.split('_')[-1])
                    self._next_fa_id = max(self._next_fa_id, id_num + 1)
                except:
                    pass
            
            print(f"✅ Loaded {len(self._free_agents)} free agents from database")
        except Exception as e:
            print(f"⚠️ Could not load free agents: {e}")
    
    def _dict_to_free_agent(self, data: Dict[str, Any]) -> FreeAgent:
        """Convert database dict to FreeAgent object"""
        # Handle the visibility field - it could be int or enum value
        visibility_val = data.get('visibility', 2)
        if isinstance(visibility_val, int):
            visibility = FreeAgentVisibility(visibility_val)
        else:
            visibility = FreeAgentVisibility(int(visibility_val))
        
        return FreeAgent(
            free_agent_id=data['id'],
            wrestler_id=data['wrestler_id'],
            wrestler_name=data['wrestler_name'],
            
            age=data['age'],
            gender=data['gender'],
            alignment=data['alignment'],
            role=data['role'],
            
            brawling=data['brawling'],
            technical=data['technical'],
            speed=data['speed'],
            mic=data['mic'],
            psychology=data['psychology'],
            stamina=data['stamina'],
            
            years_experience=data['years_experience'],
            is_major_superstar=bool(data.get('is_major_superstar', 0)),
            popularity=data['popularity'],
            
            source=FreeAgentSource(data['source']),
            visibility=visibility,
            mood=FreeAgentMood(data['mood']),
            market_value=data['market_value'],
            weeks_unemployed=data['weeks_unemployed'],
            
            agent=AgentInfo.from_dict(data['agent']) if data.get('agent') else None,
            demands=ContractDemands.from_dict(data['demands']) if data.get('demands') else None,
            rival_interest=[RivalInterest.from_dict(r) for r in data.get('rival_interest', [])],
            contract_history=[ContractHistory.from_dict(h) for h in data.get('contract_history', [])],
            
            has_controversy=bool(data.get('has_controversy', 0)),
            controversy_type=data.get('controversy_type'),
            controversy_severity=data.get('controversy_severity', 0),
            time_since_incident_weeks=data.get('time_since_incident_weeks', 0),
            
            is_legend=bool(data.get('is_legend', 0)),
            retirement_status=data.get('retirement_status', 'active'),
            comeback_likelihood=data.get('comeback_likelihood', 50),
            
            origin_region=data.get('origin_region', 'domestic'),
            requires_visa=bool(data.get('requires_visa', 0)),
            exclusive_willing=bool(data.get('exclusive_willing', 1)),
            
            is_prospect=bool(data.get('is_prospect', 0)),
            training_investment_needed=data.get('training_investment_needed', 0),
            ceiling_potential=data.get('ceiling_potential', 50),
            
            available_from_year=data.get('available_from_year', 1),
            available_from_week=data.get('available_from_week', 1),
            no_compete_until_year=data.get('no_compete_until_year'),
            no_compete_until_week=data.get('no_compete_until_week'),
            
            discovered=bool(data.get('discovered', 0)),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )
    

    # ========================================================================
    # Dynamic Pool Population (Step 114)
    # ========================================================================
    
    def populate_pool_from_releases(self, universe_state, count: int = 3) -> List[FreeAgent]:
        """
        Generate free agents from simulated releases by rival promotions.
        Called periodically to keep the pool fresh.
        """
        generated = []
        
        # Name pools for generation
        first_names_male = [
            "Ace", "Blake", "Chase", "Dean", "Eric", "Frank", "Grant", "Hunter",
            "Ivan", "Jack", "Kyle", "Lance", "Max", "Nick", "Oscar", "Pete",
            "Quinn", "Rex", "Steve", "Troy", "Victor", "Wade", "Xavier", "Zane"
        ]
        first_names_female = [
            "Amber", "Bella", "Cassie", "Diana", "Eva", "Fiona", "Grace", "Hannah",
            "Iris", "Julia", "Kate", "Lily", "Mia", "Nina", "Olive", "Paige",
            "Quinn", "Rosa", "Sara", "Tina", "Uma", "Vera", "Wendy", "Zoe"
        ]
        last_names = [
            "Anderson", "Brooks", "Carter", "Davis", "Evans", "Foster", "Garcia",
            "Hayes", "Jackson", "King", "Lee", "Martinez", "Nelson", "O'Brien",
            "Parker", "Quinn", "Roberts", "Smith", "Taylor", "Valentine", "Williams"
        ]
        
        for _ in range(count):
            gender = random.choice(['Male', 'Female'])
            first_name = random.choice(first_names_male if gender == 'Male' else first_names_female)
            last_name = random.choice(last_names)
            name = f"{first_name} {last_name}"
            
            # Check for duplicate names
            existing_names = [fa.wrestler_name for fa in self._free_agents.values()]
            if name in existing_names:
                continue
            
            age = random.randint(24, 38)
            years_exp = max(1, age - 20 - random.randint(0, 3))
            
            # Determine role based on experience and randomness
            role_weights = {
                'Main Event': 0.05,
                'Upper Midcard': 0.20,
                'Midcard': 0.40,
                'Lower Midcard': 0.25,
                'Jobber': 0.10
            }
            role = random.choices(list(role_weights.keys()), weights=list(role_weights.values()))[0]
            
            # Generate attributes based on role
            attr_ranges = {
                'Main Event': (70, 90),
                'Upper Midcard': (60, 80),
                'Midcard': (50, 70),
                'Lower Midcard': (40, 60),
                'Jobber': (30, 50)
            }
            min_attr, max_attr = attr_ranges[role]
            
            attributes = {
                'brawling': random.randint(min_attr, max_attr),
                'technical': random.randint(min_attr, max_attr),
                'speed': random.randint(min_attr, max_attr),
                'mic': random.randint(min_attr - 10, max_attr),
                'psychology': random.randint(min_attr, max_attr),
                'stamina': random.randint(min_attr, max_attr)
            }
            
            # Calculate popularity based on role and attributes
            base_pop = {
                'Main Event': 70,
                'Upper Midcard': 55,
                'Midcard': 40,
                'Lower Midcard': 25,
                'Jobber': 15
            }[role]
            popularity = base_pop + random.randint(-10, 15)
            popularity = max(10, min(85, popularity))
            
            # Determine departure reason
            departure_reasons = ['released', 'mutual_agreement', 'contract_expired']
            departure_weights = [0.5, 0.3, 0.2]
            departure_reason = random.choices(departure_reasons, weights=departure_weights)[0]
            
            # Create free agent
            fa = FreeAgent(
                free_agent_id=f"fa_gen_{self._next_fa_id}",
                wrestler_id=f"gen_{self._next_fa_id}",
                wrestler_name=name,
                
                age=age,
                gender=gender,
                alignment=random.choice(['Face', 'Heel', 'Tweener']),
                role=role,
                
                brawling=attributes['brawling'],
                technical=attributes['technical'],
                speed=attributes['speed'],
                mic=attributes['mic'],
                psychology=attributes['psychology'],
                stamina=attributes['stamina'],
                
                years_experience=years_exp,
                is_major_superstar=False,
                popularity=popularity,
                
                source=FreeAgentSource(departure_reason),
                visibility=FreeAgentVisibility.INDUSTRY_BUZZ if popularity >= 50 else FreeAgentVisibility.HIDDEN_GEM,
                mood=random.choice([FreeAgentMood.PATIENT, FreeAgentMood.HUNGRY, FreeAgentMood.BITTER]),
                
                available_from_year=universe_state.current_year,
                available_from_week=universe_state.current_week,
                discovered=False
            )
            self._next_fa_id += 1
            
            # Calculate market value
            fa.recalculate_market_value()
            
            # Set demands
            fa.demands = ContractDemands(
                minimum_salary=int(fa.market_value * 0.7),
                asking_salary=fa.market_value,
                preferred_length_weeks=52 if age < 35 else 26
            )
            
            # Add contract history from rival promotion
            rival_promo = random.choice(RIVAL_PROMOTIONS)
            tenure_years = random.randint(1, min(5, years_exp))
            fa.contract_history.append(ContractHistory(
                promotion_name=rival_promo,
                start_year=universe_state.current_year - tenure_years,
                end_year=universe_state.current_year,
                departure_reason=departure_reason,
                final_salary=int(fa.market_value * random.uniform(0.8, 1.0)),
                was_champion=random.random() < 0.15,
                relationship_on_departure=random.randint(30, 80)
            ))
            
            # Maybe generate rival interest
            if popularity >= 45:
                self._generate_initial_rival_interest(fa)
            
            # Maybe assign agent
            if popularity >= 60 or random.random() < 0.2:
                self._assign_agent(fa)
            
            self._free_agents[fa.id] = fa
            self._save_free_agent(fa)
            generated.append(fa)
        
        if generated:
            print(f"📦 Generated {len(generated)} new free agents from rival releases")
        
        return generated
    
    def populate_pool_from_expirations(self, universe_state, wrestlers_expiring: List) -> List[FreeAgent]:
        """
        Add wrestlers whose contracts expired to the free agent pool.
        Called when contracts expire in the main game.
        """
        added = []
        
        for wrestler in wrestlers_expiring:
            # Check if already in pool
            existing = self.get_free_agent_by_wrestler_id(wrestler.id)
            if existing:
                continue
            
            fa = self.add_from_contract_expiration(
                wrestler=wrestler,
                year=universe_state.current_year,
                week=universe_state.current_week,
                was_champion=False  # Would need to check this properly
            )
            added.append(fa)
        
        if added:
            print(f"📋 {len(added)} wrestlers with expired contracts entered free agency")
        
        return added
    
    def generate_international_wave(self, universe_state, region: str, count: int = 2) -> List[FreeAgent]:
        """
        Generate a wave of international talents from a specific region.
        Triggered by scouting or special events.
        """
        if region not in INTERNATIONAL_REGIONS:
            return []
        
        region_data = INTERNATIONAL_REGIONS[region]
        generated = []
        
        # Region-specific name pools
        name_pools = {
            'japan': {
                'first': ["Hiroshi", "Kenta", "Tetsuya", "Kazuchika", "Shinsuke", "Hiromu", "Taichi", "Yoshi"],
                'last': ["Tanaka", "Suzuki", "Nakamura", "Okada", "Tanahashi", "Shibata", "Ishii", "Goto"]
            },
            'mexico': {
                'first': ["El", "La", "Rey", "Dragon", "Mistico", "Ultimo", "Gran", "Principe"],
                'last': ["Azteca", "Dorado", "Fenix", "Guerrero", "Místico", "Volador", "Atlantis", "Pantera"]
            },
            'uk': {
                'first': ["William", "Pete", "Tyler", "Zack", "Trent", "Mark", "Eddie", "Joe"],
                'last': ["Regal", "Dunne", "Bate", "Sabre", "Seven", "Andrews", "Dennis", "Coffey"]
            },
            'europe': {
                'first': ["Walter", "Marcel", "Ilja", "Axel", "Ludwig", "Giovanni", "Fabian", "Alexander"],
                'last': ["Gunther", "Barthel", "Dragunov", "Dieter", "Kaiser", "Vinci", "Aichner", "Wolfe"]
            },
            'australia': {
                'first': ["Buddy", "Shane", "Robbie", "TM", "Jonah", "Grayson", "Matty", "Adam"],
                'last': ["Murphy", "Thorne", "Eagles", "Horus", "Rock", "Waller", "Wahlberg", "Brooks"]
            }
        }
        
        names = name_pools.get(region, {'first': ["Alex"], 'last': ["Smith"]})
        
        for _ in range(count):
            first = random.choice(names['first'])
            last = random.choice(names['last'])
            
            # For luchadors, combine differently
            if region == 'mexico':
                name = f"{first} {last}" if random.random() < 0.5 else f"{last} {first}"
            else:
                name = f"{first} {last}"
            
            # Check for duplicates
            existing_names = [fa.wrestler_name for fa in self._free_agents.values()]
            attempts = 0
            while name in existing_names and attempts < 10:
                first = random.choice(names['first'])
                last = random.choice(names['last'])
                name = f"{first} {last}"
                attempts += 1
            
            if name in existing_names:
                continue
            
            age = random.randint(23, 35)
            gender = 'Male' if random.random() < 0.8 else 'Female'
            
            # Base attributes with regional bonuses
            base_attr = random.randint(50, 75)
            attributes = {
                'brawling': base_attr + random.randint(-10, 10),
                'technical': base_attr + random.randint(-10, 10),
                'speed': base_attr + random.randint(-10, 10),
                'mic': base_attr - 15 + random.randint(-5, 5),  # Language barrier
                'psychology': base_attr + random.randint(-5, 10),
                'stamina': base_attr + random.randint(-5, 10)
            }
            
            # Apply regional style bonuses
            for attr, bonus in region_data['style_bonus'].items():
                attributes[attr] = min(100, attributes.get(attr, 50) + bonus)
            
            fa = self.add_international_talent(
                name=name,
                region=region,
                age=age,
                gender=gender,
                role='Midcard' if base_attr >= 60 else 'Lower Midcard',
                attributes=attributes,
                popularity=random.randint(30, 60),
                year=universe_state.current_year,
                week=universe_state.current_week
            )
            
            generated.append(fa)
        
        if generated:
            print(f"🌍 Discovered {len(generated)} new talents from {region}")
        
        return generated
    
    def generate_prospect_class(self, universe_state, count: int = 5) -> List[FreeAgent]:
        """
        Generate a new class of prospects.
        Called annually or when visiting training schools.
        """
        return self.generate_random_prospects(count, universe_state.current_year, universe_state.current_week)
    
    def check_legend_availability(self, universe_state, retired_wrestlers: List) -> List[FreeAgent]:
        """
        Check if any retired wrestlers are willing to make a comeback.
        Called periodically, especially before major PPVs.
        """
        potential_comebacks = []
        
        for wrestler in retired_wrestlers:
            # Only major superstars can make comeback
            if not wrestler.is_major_superstar:
                continue
            
            # Check if already in pool
            existing = self.get_free_agent_by_wrestler_id(wrestler.id)
            if existing:
                continue
            
            # Age check - not too old
            if wrestler.age > 55:
                continue
            
            # Random chance based on age and time retired
            comeback_chance = 0.05  # 5% base chance
            if wrestler.age < 45:
                comeback_chance += 0.10
            if wrestler.age < 50:
                comeback_chance += 0.05
            
            if random.random() < comeback_chance:
                comeback_type = random.choice(['limited', 'full', 'one_match'])
                fa = self.add_returning_legend(
                    wrestler=wrestler,
                    year=universe_state.current_year,
                    week=universe_state.current_week,
                    comeback_type=comeback_type
                )
                potential_comebacks.append(fa)
                print(f"🎉 LEGEND ALERT: {wrestler.name} is considering a comeback!")
        
        return potential_comebacks
    
    def process_controversy_cases(self, universe_state) -> List[Dict[str, Any]]:
        """
        Process existing controversy cases - reduce severity over time,
        potentially rehabilitate wrestlers.
        """
        updates = []
        
        for fa in self.available_free_agents:
            if not fa.has_controversy:
                continue
            
            # Severity reduces over time
            if fa.time_since_incident_weeks > 26:  # 6 months
                old_severity = fa.controversy_severity
                fa.controversy_severity = max(0, fa.controversy_severity - 5)
                
                if fa.controversy_severity < old_severity:
                    updates.append({
                        'type': 'severity_reduced',
                        'free_agent_id': fa.id,
                        'wrestler_name': fa.wrestler_name,
                        'old_severity': old_severity,
                        'new_severity': fa.controversy_severity
                    })
            
            # If severity drops to 0, controversy is essentially over
            if fa.controversy_severity <= 10 and fa.time_since_incident_weeks > 52:
                fa.has_controversy = False
                fa.recalculate_market_value()
                updates.append({
                    'type': 'controversy_cleared',
                    'free_agent_id': fa.id,
                    'wrestler_name': fa.wrestler_name,
                    'message': f"{fa.wrestler_name}'s controversy is now in the past"
                })
            
            self._save_free_agent(fa)
        
        return updates
    
    def get_pool_health_report(self) -> Dict[str, Any]:
        """
        Analyze pool health and recommend actions.
        """
        available = self.available_free_agents
        
        report = {
            'total_available': len(available),
            'recommendations': [],
            'breakdown': {
                'main_eventers': len([fa for fa in available if fa.role == 'Main Event']),
                'upper_midcard': len([fa for fa in available if fa.role == 'Upper Midcard']),
                'midcard': len([fa for fa in available if fa.role == 'Midcard']),
                'lower_card': len([fa for fa in available if fa.role in ['Lower Midcard', 'Jobber']]),
                'legends': len([fa for fa in available if fa.is_legend]),
                'prospects': len([fa for fa in available if fa.is_prospect]),
                'international': len([fa for fa in available if fa.origin_region != 'domestic']),
                'discovered': len([fa for fa in available if fa.discovered]),
                'undiscovered': len([fa for fa in available if not fa.discovered])
            },
            'average_popularity': sum(fa.popularity for fa in available) / len(available) if available else 0,
            'average_age': sum(fa.age for fa in available) / len(available) if available else 0
        }
        
        # Generate recommendations
        if report['breakdown']['main_eventers'] == 0:
            report['recommendations'].append("No main event free agents available - consider targeting rival promotions")
        
        if report['breakdown']['prospects'] < 3:
            report['recommendations'].append("Low prospect count - consider scouting training schools")
        
        if report['breakdown']['international'] < 2:
            report['recommendations'].append("Few international talents - expand scouting network")
        
        if report['breakdown']['undiscovered'] > report['total_available'] * 0.7:
            report['recommendations'].append("Many undiscovered talents - upgrade scouting level")
        
        if len(available) < 10:
            report['recommendations'].append("Pool is running low - more releases expected soon")
        
        return report
    
    # ========================================================================
    # Pool Access Methods
    # ========================================================================
    
    @property
    def all_free_agents(self) -> List[FreeAgent]:
        """Get all free agents (including signed)"""
        return list(self._free_agents.values())
    
    @property
    def available_free_agents(self) -> List[FreeAgent]:
        """Get only unsigned free agents"""
        return [fa for fa in self._free_agents.values() 
                if fa.id not in self._get_signed_ids()]
    
    def _get_signed_ids(self) -> set:
        """Get IDs of signed free agents from database"""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute('SELECT id FROM free_agents WHERE is_signed = 1')
            return {row['id'] for row in cursor.fetchall()}
        except:
            return set()
    
    def get_free_agent_by_id(self, fa_id: str) -> Optional[FreeAgent]:
        """Get a specific free agent"""
        return self._free_agents.get(fa_id)

    def remove_free_agent(self, fa_id: str, promotion: str = "Ring of Champions") -> bool:
        """Mark a free agent as signed and remove them from the in-memory pool."""
        if fa_id not in self._free_agents:
            return False

        try:
            from persistence.free_agent_db import mark_free_agent_signed

            state = self.db.get_game_state() if hasattr(self.db, "get_game_state") else {}
            mark_free_agent_signed(
                self.db,
                fa_id,
                promotion,
                state.get("current_year", 1),
                state.get("current_week", 1),
            )
        except Exception:
            pass

        self._free_agents.pop(fa_id, None)
        return True
    
    def get_free_agent_by_wrestler_id(self, wrestler_id: str) -> Optional[FreeAgent]:
        """Find a free agent by their original wrestler ID"""
        for fa in self._free_agents.values():
            if fa.wrestler_id == wrestler_id:
                return fa
        return None
    
    def get_discovered_free_agents(self) -> List[FreeAgent]:
        """Get free agents the player has discovered"""
        return [fa for fa in self.available_free_agents if fa.discovered]
    
    def get_free_agents_by_visibility(self, max_tier: int) -> List[FreeAgent]:
        """Get free agents up to a visibility tier"""
        return [fa for fa in self.available_free_agents 
                if fa.visibility.value <= max_tier]
    
    def get_headline_free_agents(self) -> List[FreeAgent]:
        """Get tier 1 (headline news) free agents - always visible"""
        return [fa for fa in self.available_free_agents 
                if fa.visibility == FreeAgentVisibility.HEADLINE_NEWS]
    
    def get_free_agents_by_source(self, source: FreeAgentSource) -> List[FreeAgent]:
        """Get free agents by their source type"""
        return [fa for fa in self.available_free_agents if fa.source == source]
    
    def get_legends(self) -> List[FreeAgent]:
        """Get available legend free agents"""
        return [fa for fa in self.available_free_agents if fa.is_legend]
    
    def get_prospects(self) -> List[FreeAgent]:
        """Get available prospect free agents"""
        return [fa for fa in self.available_free_agents if fa.is_prospect]
    
    def get_international_talents(self, region: Optional[str] = None) -> List[FreeAgent]:
        """Get international free agents, optionally filtered by region"""
        international = [fa for fa in self.available_free_agents 
                        if fa.origin_region != 'domestic']
        if region:
            international = [fa for fa in international if fa.origin_region == region]
        return international
    
    def get_controversy_cases(self) -> List[FreeAgent]:
        """Get free agents with controversy"""
        return [fa for fa in self.available_free_agents if fa.has_controversy]
    
    # ========================================================================
    # Adding Free Agents to Pool
    # ========================================================================
    
    def add_from_release(
        self,
        wrestler,
        departure_reason: str,
        relationship: int,
        year: int,
        week: int,
        no_compete_weeks: int = 0,
        was_champion: bool = False
    ) -> FreeAgent:
        """
        Add a released wrestler to the free agent pool (Steps 161-166)
        """
        source = FreeAgentSource.RELEASED
        if departure_reason == "mutual":
            source = FreeAgentSource.MUTUAL_AGREEMENT
        elif departure_reason == "controversy":
            source = FreeAgentSource.CONTROVERSY
        
        fa = FreeAgent.from_wrestler(wrestler, source, year, week)
        fa.id = f"fa_rel_{self._next_fa_id}"
        self._next_fa_id += 1
        
        # Add contract history
        fa.contract_history.append(ContractHistory(
            promotion_name="Ring of Champions",
            start_year=wrestler.contract.signing_year,
            end_year=year,
            departure_reason=departure_reason,
            final_salary=wrestler.contract.salary_per_show,
            was_champion=was_champion,
            relationship_on_departure=relationship
        ))
        
        # Set mood based on departure
        if relationship < 30:
            fa.mood = FreeAgentMood.BITTER
        elif relationship < 50:
            fa.mood = FreeAgentMood.HUNGRY
        else:
            fa.mood = FreeAgentMood.PATIENT
        
        # Set no-compete if applicable
        if no_compete_weeks > 0:
            no_compete_end = week + no_compete_weeks
            fa.no_compete_until_year = year + (no_compete_end // 52)
            fa.no_compete_until_week = no_compete_end % 52
            if fa.no_compete_until_week == 0:
                fa.no_compete_until_week = 52
                fa.no_compete_until_year -= 1
        
        # Headlines for major stars, otherwise industry buzz
        if wrestler.is_major_superstar or wrestler.popularity >= 80:
            fa.visibility = FreeAgentVisibility.HEADLINE_NEWS
            fa.discovered = True  # Auto-discovered
        elif wrestler.popularity >= 50:
            fa.visibility = FreeAgentVisibility.INDUSTRY_BUZZ
        else:
            fa.visibility = FreeAgentVisibility.HIDDEN_GEM
        
        # Generate rival interest for notable free agents
        if wrestler.popularity >= 60:
            self._generate_initial_rival_interest(fa)
        
        # Possibly assign an agent
        if wrestler.is_major_superstar or random.random() < 0.3:
            self._assign_agent(fa)
        
        self._free_agents[fa.id] = fa
        self._save_free_agent(fa)
        
        return fa
    
    def add_from_contract_expiration(
        self,
        wrestler,
        year: int,
        week: int,
        was_champion: bool = False
    ) -> FreeAgent:
        """
        Add a wrestler whose contract expired to the pool (Step 119-125)
        """
        fa = FreeAgent.from_wrestler(wrestler, FreeAgentSource.CONTRACT_EXPIRED, year, week)
        fa.id = f"fa_exp_{self._next_fa_id}"
        self._next_fa_id += 1
        
        # Contract expiration is usually amicable
        fa.mood = FreeAgentMood.PATIENT
        
        # Add contract history
        fa.contract_history.append(ContractHistory(
            promotion_name="Ring of Champions",
            start_year=wrestler.contract.signing_year,
            end_year=year,
            departure_reason="expired",
            final_salary=wrestler.contract.salary_per_show,
            was_champion=was_champion,
            relationship_on_departure=70  # Usually good terms
        ))
        
        # Higher visibility - they're testing the market
        if wrestler.is_major_superstar:
            fa.visibility = FreeAgentVisibility.HEADLINE_NEWS
            fa.discovered = True
        else:
            fa.visibility = FreeAgentVisibility.INDUSTRY_BUZZ
        
        # Generate significant rival interest - they're a known quantity
        self._generate_initial_rival_interest(fa, boost=20)
        
        # Likely has an agent
        if wrestler.popularity >= 50 or random.random() < 0.5:
            self._assign_agent(fa)
        
        self._free_agents[fa.id] = fa
        self._save_free_agent(fa)
        
        return fa
    
    def add_returning_legend(
        self,
        wrestler,
        year: int,
        week: int,
        comeback_type: str = "limited"  # "limited", "full", "one_match"
    ) -> FreeAgent:
        """
        Add a returning legend to the pool (Steps 167-172)
        """
        fa = FreeAgent.from_wrestler(wrestler, FreeAgentSource.RETIRED_COMEBACK, year, week)
        fa.id = f"fa_leg_{self._next_fa_id}"
        self._next_fa_id += 1
        
        fa.is_legend = True
        fa.retirement_status = "semi_retired" if comeback_type == "limited" else "soft_retired"
        
        # Legends are always headline news
        fa.visibility = FreeAgentVisibility.HEADLINE_NEWS
        fa.discovered = True
        
        # Legends are patient - they don't need the money
        fa.mood = FreeAgentMood.PATIENT
        
        # Legends have specific demands
        fa.demands.creative_control_level = 3  # Partnership level
        fa.demands.finish_protection = True
        fa.demands.title_guarantee_weeks = 0  # Usually don't need titles
        
        if comeback_type == "limited":
            fa.demands.max_appearances_per_year = 50
            fa.demands.preferred_length_weeks = 26
        elif comeback_type == "one_match":
            fa.demands.max_appearances_per_year = 10
            fa.demands.preferred_length_weeks = 13
        
        # Legends have high market value
        fa.market_value = int(fa.market_value * 2.0)
        fa.demands.asking_salary = int(fa.demands.asking_salary * 2.0)
        
        # Massive rival interest
        self._generate_initial_rival_interest(fa, boost=40)
        
        # Always has representation
        self._assign_agent(fa, power_agent=True)
        
        self._free_agents[fa.id] = fa
        self._save_free_agent(fa)
        
        return fa
    
    def add_international_talent(
        self,
        name: str,
        region: str,
        age: int,
        gender: str,
        role: str,
        attributes: Dict[str, int],
        popularity: int,
        year: int,
        week: int
    ) -> FreeAgent:
        """
        Add an international talent to the pool (Steps 179-184)
        """
        region_data = INTERNATIONAL_REGIONS.get(region, INTERNATIONAL_REGIONS['domestic'])
        
        # Apply regional style bonuses
        for attr, bonus in region_data['style_bonus'].items():
            if attr in attributes:
                attributes[attr] = min(100, attributes[attr] + bonus)
        
        fa = FreeAgent(
            free_agent_id=f"fa_int_{self._next_fa_id}",
            wrestler_id=f"int_{self._next_fa_id}",
            wrestler_name=name,
            
            age=age,
            gender=gender,
            alignment=random.choice(['Face', 'Heel']),
            role=role,
            
            brawling=attributes.get('brawling', 50),
            technical=attributes.get('technical', 50),
            speed=attributes.get('speed', 50),
            mic=attributes.get('mic', 40),  # Language barrier
            psychology=attributes.get('psychology', 50),
            stamina=attributes.get('stamina', 50),
            
            years_experience=max(1, age - 20),
            popularity=popularity,
            
            source=FreeAgentSource.INTERNATIONAL,
            visibility=FreeAgentVisibility.HIDDEN_GEM,  # Requires scouting
            mood=FreeAgentMood.PATIENT,
            
            origin_region=region,
            requires_visa=region_data['visa_required'],
            exclusive_willing=random.random() < region_data['exclusive_likelihood'],
            
            available_from_year=year,
            available_from_week=week
        )
        self._next_fa_id += 1
        
        # Only discovered if we have scouting network
        fa.discovered = self._scouting_network.get(region, False)
        
        fa.recalculate_market_value()
        
        self._free_agents[fa.id] = fa
        self._save_free_agent(fa)
        
        return fa
    
    def add_prospect(
        self,
        name: str,
        age: int,
        gender: str,
        attributes: Dict[str, int],
        ceiling_potential: int,
        training_needed: int,
        year: int,
        week: int
    ) -> FreeAgent:
        """
        Add a fresh prospect to the pool (Steps 185-190)
        """
        fa = FreeAgent(
            free_agent_id=f"fa_pro_{self._next_fa_id}",
            wrestler_id=f"pro_{self._next_fa_id}",
            wrestler_name=name,
            
            age=age,
            gender=gender,
            alignment='Face',  # Prospects usually start as faces
            role='Jobber',  # Start at the bottom
            
            brawling=attributes.get('brawling', 30),
            technical=attributes.get('technical', 30),
            speed=attributes.get('speed', 40),
            mic=attributes.get('mic', 25),
            psychology=attributes.get('psychology', 25),
            stamina=attributes.get('stamina', 40),
            
            years_experience=0,
            popularity=10,
            
            source=FreeAgentSource.PROSPECT,
            visibility=FreeAgentVisibility.DEEP_CUT,  # Hardest to find
            mood=FreeAgentMood.HUNGRY,  # Eager to get signed
            
            is_prospect=True,
            ceiling_potential=ceiling_potential,
            training_investment_needed=training_needed,
            
            available_from_year=year,
            available_from_week=week
        )
        self._next_fa_id += 1
        
        # Prospects have minimal demands
        fa.demands.minimum_salary = 1000
        fa.demands.asking_salary = 2000
        fa.demands.creative_control_level = 0
        fa.demands.preferred_length_weeks = 104  # 2 year developmental
        
        fa.recalculate_market_value()
        
        self._free_agents[fa.id] = fa
        self._save_free_agent(fa)
        
        return fa
    
    def add_controversy_case(
        self,
        wrestler,
        controversy_type: str,
        severity: int,
        year: int,
        week: int
    ) -> FreeAgent:
        """
        Add a wrestler with controversy baggage (Steps 191-197)
        """
        fa = FreeAgent.from_wrestler(wrestler, FreeAgentSource.CONTROVERSY, year, week)
        fa.id = f"fa_con_{self._next_fa_id}"
        self._next_fa_id += 1
        
        fa.has_controversy = True
        fa.controversy_type = controversy_type
        fa.controversy_severity = severity
        fa.time_since_incident_weeks = 0
        
        # Controversy lowers visibility despite talent
        if severity >= 80:
            fa.visibility = FreeAgentVisibility.DEEP_CUT
        elif severity >= 50:
            fa.visibility = FreeAgentVisibility.HIDDEN_GEM
        else:
            fa.visibility = FreeAgentVisibility.INDUSTRY_BUZZ
        
        # Mood varies
        if severity >= 70:
            fa.mood = FreeAgentMood.DESPERATE
        else:
            fa.mood = FreeAgentMood.BITTER
        
        # Significant market value discount
        fa.recalculate_market_value()
        
        # Less rival interest due to risk
        if severity < 60:
            self._generate_initial_rival_interest(fa, boost=-20)
        
        self._free_agents[fa.id] = fa
        self._save_free_agent(fa)
        
        return fa
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _generate_initial_rival_interest(self, fa: FreeAgent, boost: int = 0):
        """Generate initial rival promotion interest"""
        # Higher popularity = more interest
        base_interest = fa.popularity + boost
        
        # Determine how many promotions are interested
        if base_interest >= 80:
            num_interested = random.randint(3, 5)
        elif base_interest >= 60:
            num_interested = random.randint(2, 4)
        elif base_interest >= 40:
            num_interested = random.randint(1, 2)
        else:
            num_interested = random.randint(0, 1)
        
        interested_promotions = random.sample(
            RIVAL_PROMOTIONS, 
            min(num_interested, len(RIVAL_PROMOTIONS))
        )
        
        for promo in interested_promotions:
            interest_level = base_interest + random.randint(-20, 20)
            interest_level = max(10, min(100, interest_level))
            
            fa.add_rival_interest(promo, interest_level)
    
    def _assign_agent(self, fa: FreeAgent, power_agent: bool = False):
        """Assign an agent to a free agent"""
        agent_name = random.choice(AGENT_NAMES)
        
        if power_agent or fa.is_major_superstar:
            agent_type = AgentType.POWER_AGENT
            commission = 0.15
            difficulty = random.randint(60, 90)
        elif random.random() < 0.2:
            agent_type = AgentType.PACKAGE_DEALER
            commission = 0.12
            difficulty = random.randint(50, 75)
        else:
            agent_type = AgentType.STANDARD
            commission = 0.10
            difficulty = random.randint(30, 60)
        
        fa.agent = AgentInfo(
            agent_type=agent_type,
            agent_name=agent_name,
            commission_rate=commission,
            negotiation_difficulty=difficulty
        )
    
    def _save_free_agent(self, fa: FreeAgent):
        """Save free agent to database"""
        from persistence.free_agent_db import save_free_agent
        save_free_agent(self.db, fa)
        self.db.conn.commit()
    
    # ========================================================================
    # Weekly Processing
    # ========================================================================
    
    def process_week(self, year: int, week: int):
        """
        Process weekly updates for all free agents.
        Called at the end of each week.
        """
        events = []

        # STEP 117: Process mood changes FIRST
        mood_changes = self.process_mood_changes(year, week)
        for change in mood_changes:
            events.append({
                'type': 'mood_change',
                'free_agent_id': change['free_agent_id'],
                'wrestler_name': change['wrestler_name'],
                'description': f"{change['wrestler_name']}'s mood changed from {change['old_mood']} to {change['new_mood']}: {change['reason']}",
                'year': year,
                'week': week
            })
        
        for fa in self.available_free_agents:
            # Advance time for each free agent
            old_mood = fa.mood
            fa.advance_week()
            
            # Log mood changes
            if fa.mood != old_mood and fa.discovered:
                events.append({
                    'type': 'mood_change',
                    'free_agent_id': fa.id,
                    'wrestler_name': fa.wrestler_name,
                    'old_mood': old_mood.value,
                    'new_mood': fa.mood.value,
                    'message': f"{fa.wrestler_name}'s mood has shifted from {old_mood.value} to {fa.mood.value}"
                })
            
            # Rival promotions may make offers
            for rival in fa.rival_interest:
                if not rival.offer_made and rival.interest_level >= 70:
                    if random.random() < 0.15:  # 15% chance per week
                        offer_amount = int(fa.market_value * random.uniform(0.9, 1.2))
                        deadline = week + random.randint(1, 4)
                        rival.offer_made = True
                        rival.offer_salary = offer_amount
                        rival.deadline_week = deadline
                        
                        if fa.discovered:
                            events.append({
                                'type': 'rival_offer',
                                'free_agent_id': fa.id,
                                'wrestler_name': fa.wrestler_name,
                                'promotion': rival.promotion_name,
                                'offer': offer_amount,
                                'deadline_week': deadline,
                                'message': f"⚠️ {rival.promotion_name} has made an offer to {fa.wrestler_name}!"
                            })
            
            # Check for deadline expirations - wrestler signs elsewhere
            for rival in fa.rival_interest:
                if rival.offer_made and rival.deadline_week == week:
                    # Free agent signs with rival
                    if random.random() < 0.7:  # 70% chance they accept
                        events.append({
                            'type': 'signed_elsewhere',
                            'free_agent_id': fa.id,
                            'wrestler_name': fa.wrestler_name,
                            'promotion': rival.promotion_name,
                            'message': f"❌ {fa.wrestler_name} has signed with {rival.promotion_name}!"
                        })
                        
                        # Mark as signed
                        from persistence.free_agent_db import mark_free_agent_signed
                        mark_free_agent_signed(self.db, fa.id, rival.promotion_name, year, week)
                        break
            
            # Initialize mood for this free agent
            self.initialize_free_agent_mood(fa)
            # Save updated state
            self._save_free_agent(fa)
        
        return events
    
    def generate_random_prospects(self, count: int, year: int, week: int) -> List[FreeAgent]:
        """Generate random prospects for the pool"""
        from models.wrestler import Wrestler  # For name generation if needed
        
        first_names_male = [
            "Jake", "Tyler", "Austin", "Brandon", "Derek", "Marcus", "Jason", 
            "Kevin", "Ryan", "Trevor", "Shane", "Cody", "Lance", "Drew", "Zack"
        ]
        first_names_female = [
            "Alexa", "Bayley", "Carmen", "Dakota", "Elena", "Faith", "Gina",
            "Holly", "Ivy", "Jade", "Kelly", "Luna", "Morgan", "Nova", "Ruby"
        ]
        last_names = [
            "Storm", "Phoenix", "Blaze", "Cruz", "Steele", "Knight", "Wolf",
            "Hawk", "Stone", "Fox", "Black", "Savage", "Young", "Strong", "Wild"
        ]
        
        prospects = []
        
        for _ in range(count):
            gender = random.choice(['Male', 'Female'])
            first_name = random.choice(first_names_male if gender == 'Male' else first_names_female)
            last_name = random.choice(last_names)
            name = f"{first_name} {last_name}"
            
            age = random.randint(18, 24)
            
            # Raw attributes - prospects are undeveloped
            attributes = {
                'brawling': random.randint(20, 50),
                'technical': random.randint(20, 50),
                'speed': random.randint(30, 60),
                'mic': random.randint(15, 40),
                'psychology': random.randint(15, 40),
                'stamina': random.randint(30, 60)
            }
            
            ceiling = random.randint(50, 95)
            training_cost = random.randint(10000, 50000)
            
            prospect = self.add_prospect(
                name=name,
                age=age,
                gender=gender,
                attributes=attributes,
                ceiling_potential=ceiling,
                training_needed=training_cost,
                year=year,
                week=week
            )
            prospects.append(prospect)
        
        return prospects
    
    # ========================================================================
    # Discovery & Scouting
    # ========================================================================
    
    def discover_free_agent(self, fa_id: str) -> bool:
        """Mark a free agent as discovered"""
        fa = self._free_agents.get(fa_id)
        if fa and not fa.discovered:
            fa.discovered = True
            fa.updated_at = datetime.now().isoformat()
            
            from persistence.free_agent_db import mark_free_agent_discovered
            mark_free_agent_discovered(self.db, fa_id)
            return True
        return False
    
    def scout_region(self, region: str) -> List[FreeAgent]:
        """
        Scout a region to discover international talents.
        Returns newly discovered free agents.
        """
        if region not in self._scouting_network:
            return []
        
        self._scouting_network[region] = True
        
        # Find and discover free agents from this region
        discovered = []
        for fa in self._free_agents.values():
            if fa.origin_region == region and not fa.discovered:
                fa.discovered = True
                discovered.append(fa)
                self._save_free_agent(fa)
        
        return discovered
    
    def upgrade_scouting(self) -> int:
        """Upgrade scouting level, returns new level"""
        if self._scouting_level < 5:
            self._scouting_level += 1
            
            # Higher scouting reveals more free agents
            visibility_threshold = 5 - self._scouting_level  # Level 5 = see tier 1+
            
            for fa in self._free_agents.values():
                if fa.visibility.value <= visibility_threshold and not fa.discovered:
                    if random.random() < 0.3:  # 30% chance per upgrade
                        fa.discovered = True
                        self._save_free_agent(fa)
        
        return self._scouting_level
    
    # ========================================================================
    # Pool Statistics
    # ========================================================================
    
    def get_pool_summary(self) -> Dict[str, Any]:
        """Get summary of the free agent pool"""
        available = self.available_free_agents
        discovered = [fa for fa in available if fa.discovered]
        
        return {
            'total_available': len(available),
            'total_discovered': len(discovered),
            'by_source': {
                source.value: len([fa for fa in available if fa.source == source])
                for source in FreeAgentSource
            },
            'by_visibility': {
                vis.value: len([fa for fa in available if fa.visibility == vis])
                for vis in FreeAgentVisibility
            },
            'by_mood': {
                mood.value: len([fa for fa in available if fa.mood == mood])
                for mood in FreeAgentMood
            },
            'legends_available': len([fa for fa in available if fa.is_legend]),
            'prospects_available': len([fa for fa in available if fa.is_prospect]),
            'international_available': len([fa for fa in available if fa.origin_region != 'domestic']),
            'controversy_cases': len([fa for fa in available if fa.has_controversy]),
            'average_market_value': int(sum(fa.market_value for fa in available) / len(available)) if available else 0,
            'highest_market_value': max((fa.market_value for fa in available), default=0),
            'scouting_level': self._scouting_level,
            'scouting_networks': self._scouting_network
        }
    

        # ========================================================================
    # Visibility Tier Management (Step 115)
    # ========================================================================
    
    def get_visible_free_agents_for_scouting_level(self) -> List[FreeAgent]:
        """
        Get free agents visible at current scouting level.
        Level 1: Tier 1 only (Headline News)
        Level 2: Tier 1-2 (+ Industry Buzz)
        Level 3: Tier 1-3 (+ Hidden Gems)
        Level 4: Tier 1-4 (+ Deep Cuts)
        Level 5: All tiers + bonus discovery chance
        """
        max_visibility = self._scouting_level
        
        visible = []
        for fa in self.available_free_agents:
            # Tier 1 (Headline News) always visible
            if fa.visibility == FreeAgentVisibility.HEADLINE_NEWS:
                visible.append(fa)
            # Other tiers based on scouting level
            elif fa.visibility.value <= max_visibility:
                visible.append(fa)
        
        return visible
    
    def auto_discover_by_scouting_level(self) -> List[FreeAgent]:
        """
        Automatically discover free agents based on scouting level.
        Called when scouting is upgraded or periodically.
        """
        newly_discovered = []
        
        for fa in self.available_free_agents:
            if fa.discovered:
                continue
            
            # Auto-discover based on visibility tier and scouting level
            should_discover = False
            
            # Tier 1: Always discovered
            if fa.visibility == FreeAgentVisibility.HEADLINE_NEWS:
                should_discover = True
            
            # Tier 2: Discovered at scouting level 2+
            elif fa.visibility == FreeAgentVisibility.INDUSTRY_BUZZ:
                if self._scouting_level >= 2:
                    # 80% chance at level 2, 100% at level 3+
                    if self._scouting_level >= 3 or random.random() < 0.8:
                        should_discover = True
            
            # Tier 3: Discovered at scouting level 3+
            elif fa.visibility == FreeAgentVisibility.HIDDEN_GEM:
                if self._scouting_level >= 3:
                    # 60% chance at level 3, 80% at level 4, 100% at level 5
                    chance = 0.4 + (self._scouting_level - 3) * 0.2
                    if random.random() < chance:
                        should_discover = True
            
            # Tier 4: Discovered at scouting level 4+
            elif fa.visibility == FreeAgentVisibility.DEEP_CUT:
                if self._scouting_level >= 4:
                    # 40% chance at level 4, 70% at level 5
                    chance = 0.4 + (self._scouting_level - 4) * 0.3
                    if random.random() < chance:
                        should_discover = True
            
            if should_discover:
                fa.discovered = True
                fa.updated_at = datetime.now().isoformat()
                self._save_free_agent(fa)
                newly_discovered.append(fa)
        
        return newly_discovered
    
    def promote_visibility(self, fa_id: str, reason: str = "news") -> Optional[FreeAgent]:
        """
        Promote a free agent to a higher visibility tier.
        Called when news breaks about them or they do something notable.
        """
        fa = self.get_free_agent_by_id(fa_id)
        if not fa:
            return None
        
        old_visibility = fa.visibility
        
        # Can't go higher than Headline News
        if fa.visibility == FreeAgentVisibility.HEADLINE_NEWS:
            return fa
        
        # Promote one tier
        new_tier = fa.visibility.value - 1
        fa.visibility = FreeAgentVisibility(new_tier)
        
        # Headline news = auto discovered
        if fa.visibility == FreeAgentVisibility.HEADLINE_NEWS:
            fa.discovered = True
        
        fa.updated_at = datetime.now().isoformat()
        self._save_free_agent(fa)
        
        print(f"📰 {fa.wrestler_name} visibility promoted: {old_visibility.name} → {fa.visibility.name} ({reason})")
        
        return fa
    
    def demote_visibility(self, fa_id: str, reason: str = "time") -> Optional[FreeAgent]:
        """
        Demote a free agent to a lower visibility tier.
        Called when they've been unemployed too long or news dies down.
        """
        fa = self.get_free_agent_by_id(fa_id)
        if not fa:
            return None
        
        old_visibility = fa.visibility
        
        # Can't go lower than Deep Cut
        if fa.visibility == FreeAgentVisibility.DEEP_CUT:
            return fa
        
        # Demote one tier
        new_tier = fa.visibility.value + 1
        fa.visibility = FreeAgentVisibility(new_tier)
        
        fa.updated_at = datetime.now().isoformat()
        self._save_free_agent(fa)
        
        print(f"📉 {fa.wrestler_name} visibility demoted: {old_visibility.name} → {fa.visibility.name} ({reason})")
        
        return fa
    
    def process_visibility_changes(self, year: int, week: int) -> List[Dict[str, Any]]:
        """
        Process weekly visibility changes based on various factors.
        """
        changes = []
        
        for fa in self.available_free_agents:
            # Skip legends - they stay in headlines
            if fa.is_legend:
                continue
            
            old_visibility = fa.visibility
            
            # Long unemployment can reduce visibility
            if fa.weeks_unemployed >= 26:  # 6+ months
                if fa.visibility.value < 4 and random.random() < 0.1:  # 10% weekly chance
                    self.demote_visibility(fa.id, "long unemployment")
                    changes.append({
                        'type': 'demoted',
                        'free_agent_id': fa.id,
                        'wrestler_name': fa.wrestler_name,
                        'old_tier': old_visibility.name,
                        'new_tier': fa.visibility.name,
                        'reason': 'Long-term unemployment'
                    })
            
            # Controversy can increase visibility (bad publicity is still publicity)
            if fa.has_controversy and fa.controversy_severity >= 60:
                if fa.visibility.value > 1 and random.random() < 0.05:  # 5% weekly chance
                    self.promote_visibility(fa.id, "controversy in news")
                    changes.append({
                        'type': 'promoted',
                        'free_agent_id': fa.id,
                        'wrestler_name': fa.wrestler_name,
                        'old_tier': old_visibility.name,
                        'new_tier': fa.visibility.name,
                        'reason': 'Controversy keeping them in the news'
                    })
            
            # High rival interest can increase visibility
            if len(fa.rival_interest) >= 3:
                if fa.visibility.value > 2 and random.random() < 0.1:  # 10% weekly chance
                    self.promote_visibility(fa.id, "bidding war attention")
                    changes.append({
                        'type': 'promoted',
                        'free_agent_id': fa.id,
                        'wrestler_name': fa.wrestler_name,
                        'old_tier': old_visibility.name,
                        'new_tier': fa.visibility.name,
                        'reason': 'Multiple promotions showing interest'
                    })
            
            # Prospects who've been around a while may get discovered
            if fa.is_prospect and fa.weeks_unemployed >= 13:  # 3+ months
                if not fa.discovered and random.random() < 0.05:  # 5% weekly chance
                    fa.discovered = True
                    self._save_free_agent(fa)
                    changes.append({
                        'type': 'discovered',
                        'free_agent_id': fa.id,
                        'wrestler_name': fa.wrestler_name,
                        'reason': 'Word spreading about promising prospect'
                    })
        
        return changes
    
    def trigger_news_event(self, fa_id: str, event_type: str) -> Dict[str, Any]:
        """
        Trigger a news event that affects visibility.
        
        Event types:
        - 'interview': Wrestler gives notable interview
        - 'social_media': Viral social media moment
        - 'rival_signing_failed': Almost signed with rival, fell through
        - 'injury_recovery': Cleared from injury
        - 'comeback_tease': Teased a comeback
        - 'shoot_promo': Shot on former employer
        """
        fa = self.get_free_agent_by_id(fa_id)
        if not fa:
            return {'success': False, 'error': 'Free agent not found'}
        
        old_visibility = fa.visibility
        old_discovered = fa.discovered
        
        # Different events have different effects
        if event_type == 'interview':
            if fa.mic >= 70:  # Good talkers benefit more
                self.promote_visibility(fa.id, "great interview")
            fa.discovered = True
        
        elif event_type == 'social_media':
            self.promote_visibility(fa.id, "viral moment")
            fa.discovered = True
        
        elif event_type == 'rival_signing_failed':
            # Adds intrigue - why did it fail?
            if fa.visibility.value > 2:
                self.promote_visibility(fa.id, "failed signing news")
            fa.discovered = True
        
        elif event_type == 'injury_recovery':
            fa.discovered = True
            # Only promote if they were notable before
            if fa.popularity >= 50:
                self.promote_visibility(fa.id, "cleared to compete")
        
        elif event_type == 'comeback_tease':
            if fa.is_legend:
                fa.visibility = FreeAgentVisibility.HEADLINE_NEWS
            else:
                self.promote_visibility(fa.id, "comeback speculation")
            fa.discovered = True
        
        elif event_type == 'shoot_promo':
            # Controversial but attention-grabbing
            self.promote_visibility(fa.id, "controversial comments")
            fa.discovered = True
            # Might make some promotions hesitant
            if fa.mood != FreeAgentMood.BITTER:
                fa.mood = FreeAgentMood.BITTER
        
        self._save_free_agent(fa)
        
        return {
            'success': True,
            'free_agent_id': fa.id,
            'wrestler_name': fa.wrestler_name,
            'event_type': event_type,
            'visibility_changed': fa.visibility != old_visibility,
            'old_visibility': old_visibility.name,
            'new_visibility': fa.visibility.name,
            'newly_discovered': fa.discovered and not old_discovered
        }
    
    def get_visibility_breakdown(self) -> Dict[str, Any]:
        """Get detailed visibility statistics"""
        available = self.available_free_agents
        
        breakdown = {
            'by_tier': {
                'headline_news': {
                    'count': 0,
                    'discovered': 0,
                    'free_agents': []
                },
                'industry_buzz': {
                    'count': 0,
                    'discovered': 0,
                    'free_agents': []
                },
                'hidden_gem': {
                    'count': 0,
                    'discovered': 0,
                    'free_agents': []
                },
                'deep_cut': {
                    'count': 0,
                    'discovered': 0,
                    'free_agents': []
                }
            },
            'scouting_level': self._scouting_level,
            'total_visible_at_current_level': 0,
            'total_discovered': 0,
            'discovery_rate': 0
        }
        
        tier_map = {
            FreeAgentVisibility.HEADLINE_NEWS: 'headline_news',
            FreeAgentVisibility.INDUSTRY_BUZZ: 'industry_buzz',
            FreeAgentVisibility.HIDDEN_GEM: 'hidden_gem',
            FreeAgentVisibility.DEEP_CUT: 'deep_cut'
        }
        
        for fa in available:
            tier_key = tier_map.get(fa.visibility, 'deep_cut')
            breakdown['by_tier'][tier_key]['count'] += 1
            breakdown['by_tier'][tier_key]['free_agents'].append({
                'id': fa.id,
                'name': fa.wrestler_name,
                'discovered': fa.discovered
            })
            
            if fa.discovered:
                breakdown['by_tier'][tier_key]['discovered'] += 1
                breakdown['total_discovered'] += 1
            
            if fa.visibility.value <= self._scouting_level:
                breakdown['total_visible_at_current_level'] += 1
        
        if len(available) > 0:
            breakdown['discovery_rate'] = round(breakdown['total_discovered'] / len(available) * 100, 1)
        
        return breakdown
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize pool manager state"""
        return {
            'scouting_level': self._scouting_level,
            'scouting_networks': self._scouting_network,
            'next_fa_id': self._next_fa_id,
            'pool_summary': self.get_pool_summary()
        }
        # ========================================================================
    # STEP 117: Mood State Management
    # ========================================================================

    def initialize_free_agent_mood(self, free_agent):
        """
        Initialize mood for a newly created free agent.
        Called when adding free agents to pool.
        """
        mood = self.mood_processor.initialize_mood(free_agent)
        free_agent.mood = mood
        
        # Update demands based on initial mood
        self._apply_mood_to_demands(free_agent)
        
        return mood

    def _apply_mood_to_demands(self, free_agent):
        """
        Apply mood modifiers to free agent demands.
        Updates asking price and minimum salary.
        """
        modifiers = get_mood_modifiers(free_agent.mood)
        
        # Get base market value
        base_value = free_agent.market_value
        
        # Apply mood multipliers
        free_agent.demands.asking_salary = int(base_value * modifiers.asking_price_multiplier)
        free_agent.demands.minimum_salary = int(base_value * modifiers.minimum_price_multiplier)
        
        # Update other demands based on mood
        if modifiers.demands_extras:
            if not free_agent.demands.creative_control_level or free_agent.demands.creative_control_level == 0:
                free_agent.demands.creative_control_level = 1  # At least consultation
        
        if modifiers.will_accept_lowball:
            # Desperate wrestlers have very low minimums
            free_agent.demands.minimum_salary = int(base_value * 0.5)

    def process_mood_changes(self, year: int, week: int) -> List[Dict]:
        """
        Process weekly mood updates for all free agents.
        Should be called during weekly processing.
        
        Returns:
            List of mood change events
        """
        changes = self.mood_processor.process_weekly_moods(
            self.available_free_agents,
            year,
            week
        )
        
        # Save updated moods to database
        for change in changes:
            fa = self.get_free_agent_by_id(change['free_agent_id'])
            if fa:
                self._save_free_agent(fa)
        
        return changes

    def trigger_mood_event(self, free_agent_id: str, event_type: str, **event_data) -> Optional[Dict]:
        """
        Trigger a mood event for a specific free agent.
        
        Args:
            free_agent_id: Free agent ID
            event_type: Type of event (rejection, rival_offer, etc.)
            event_data: Additional event information
            
        Returns:
            Mood change event dict if transition occurred, None otherwise
        """
        fa = self.get_free_agent_by_id(free_agent_id)
        if not fa:
            return None
        
        old_mood = fa.mood
        
        should_transition, new_mood, reason = self.mood_processor.check_event_trigger(
            fa,
            event_type,
            **event_data
        )
        
        if should_transition and new_mood:
            fa.mood = new_mood
            self._apply_mood_to_demands(fa)
            
            # Save to database
            self._save_free_agent(fa)
            
            return {
                'free_agent_id': fa.id,
                'wrestler_name': fa.wrestler_name,
                'old_mood': old_mood.value,
                'new_mood': new_mood.value,
                'reason': reason,
                'new_asking_salary': fa.demands.asking_salary,
                'new_minimum_salary': fa.demands.minimum_salary
            }
        
        return None

    def recalculate_all_moods(self, year: int, week: int) -> List[Dict]:
        """
        Force recalculation of all free agent moods.
        Useful after major events or for testing.
        
        Returns:
            List of mood changes
        """
        changes = []
        
        for fa in self.available_free_agents:
            old_mood = fa.mood
            
            new_mood, changed = self.mood_processor.recalculate_mood(fa, force=True)
            
            if changed:
                fa.mood = new_mood
                self._apply_mood_to_demands(fa)
                
                changes.append({
                    'free_agent_id': fa.id,
                    'wrestler_name': fa.wrestler_name,
                    'old_mood': old_mood.value,
                    'new_mood': new_mood.value,
                    'reason': 'Force recalculation',
                    'year': year,
                    'week': week
                })
                
                # Save to database
                self._save_free_agent(fa)
        
        return changes

    def get_mood_statistics(self) -> Dict:
        """Get statistical breakdown of moods in the pool"""
        return self.mood_processor.get_mood_statistics(self.available_free_agents)

    def get_free_agents_by_mood(self, mood: FreeAgentMood, discovered_only: bool = True) -> List:
        """
        Get all free agents with a specific mood.
        
        Args:
            mood: FreeAgentMood to filter by
            discovered_only: Only return discovered free agents
            
        Returns:
            List of matching free agents
        """
        agents = self.get_discovered_free_agents() if discovered_only else self.available_free_agents
        return [fa for fa in agents if fa.mood == mood]

    def get_easiest_to_sign(self, limit: int = 10, discovered_only: bool = True) -> List:
        """
        Get free agents who are easiest to sign (Desperate/Hungry moods).
        Sorted by acceptance threshold (lowest first).
        
        Args:
            limit: Maximum number to return
            discovered_only: Only return discovered free agents
            
        Returns:
            List of free agents sorted by ease of signing
        """
        agents = self.get_discovered_free_agents() if discovered_only else self.available_free_agents
        
        # Sort by acceptance threshold (lower = easier to sign)
        sorted_agents = sorted(
            agents,
            key=lambda fa: get_mood_modifiers(fa.mood).acceptance_threshold
        )
        
        return sorted_agents[:limit]

    def get_bargain_signings(self, limit: int = 10, discovered_only: bool = True) -> List[Dict]:
        """
        Get free agents who are undervalued bargains.
        High quality but low asking price due to mood.
        
        Args:
            limit: Maximum number to return
            discovered_only: Only return discovered free agents
            
        Returns:
            List of bargain opportunity dicts
        """
        agents = self.get_discovered_free_agents() if discovered_only else self.available_free_agents
        
        bargains = []
        
        for fa in agents:
            # Calculate value vs asking price
            overall = fa.attributes.get('overall', 50)
            asking = fa.demands.asking_salary
            
            # Estimate what they "should" cost based on overall rating
            expected_salary = (overall / 100) * 30000  # Rough estimate
            
            discount_percent = ((expected_salary - asking) / max(expected_salary, 1)) * 100
            
            # Only include if at least 15% discount
            if discount_percent >= 15:
                bargains.append({
                    'free_agent': fa,
                    'overall_rating': overall,
                    'expected_salary': int(expected_salary),
                    'asking_salary': asking,
                    'discount_percent': round(discount_percent, 1),
                    'mood': fa.mood.value,
                    'reason': fa.mood_label
                })
        
        # Sort by discount percentage (highest first)
        bargains.sort(key=lambda x: x['discount_percent'], reverse=True)
        
        return bargains[:limit]

    def simulate_negotiation(self, free_agent_id: str, initial_offer: int, max_rounds: int = 5) -> Dict:
        """
        Simulate negotiation with a free agent.
        
        Args:
            free_agent_id: Free agent ID
            initial_offer: Starting salary offer
            max_rounds: Maximum negotiation rounds
            
        Returns:
            Negotiation result dict
        """
        fa = self.get_free_agent_by_id(free_agent_id)
        if not fa:
            return {'success': False, 'error': 'Free agent not found'}
        
        return self.mood_processor.simulate_negotiation_rounds(fa, initial_offer, max_rounds)

    def quick_negotiation_check(self, free_agent_id: str, offered_salary: int) -> Dict:
        """
        Quick check if an offer would be accepted.
        
        Args:
            free_agent_id: Free agent ID
            offered_salary: Salary being offered
            
        Returns:
            Result dict with acceptance info
        """
        fa = self.get_free_agent_by_id(free_agent_id)
        if not fa:
            return {'success': False, 'error': 'Free agent not found'}
        
        return self.mood_processor.apply_mood_effects_to_negotiation(
            fa,
            offered_salary,
            {}  # Simplified - would include actual contract terms
        )


# Global instance (will be initialized with database)
free_agent_pool: Optional[FreeAgentPoolManager] = None


def initialize_free_agent_pool(database) -> FreeAgentPoolManager:
    """Initialize the global free agent pool"""
    global free_agent_pool
    free_agent_pool = FreeAgentPoolManager(database)
    return free_agent_pool
