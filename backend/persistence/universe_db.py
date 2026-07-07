"""
Database-Backed Universe State
Replaces in-memory state with SQLite persistence.
"""

from typing import List, Optional
from models.wrestler import Wrestler, Injury
from models.contract import Contract, CreativeControlLevel
from models.championship import Championship, TitleReign
from models.feud import Feud, FeudManager, FeudType, FeudStatus, FeudSegment
from models.calendar import Calendar
from models.faction import FactionManager, Faction
from models.relationship_network import RelationshipNetwork, LockerRoomRelationship
from persistence.database import Database
import json
from models.championship_hierarchy import championship_hierarchy, ChampionshipHierarchy
from persistence.championship_db import load_championship_hierarchy_state, save_championship_hierarchy_state


class DatabaseUniverseState:
    """
    Universe state backed by SQLite database.
    All operations read/write to the database for persistence.
    """
    
    def __init__(self, database: Database):
        self.db = database
        self.calendar = Calendar()
        self._feud_manager = None
        self._championship_hierarchy = None
        self._championship_hierarchy_loaded = False
        self._contract_storyline_engine = None
        
        # BUGFIX #1: Load calendar index from saved game state
        game_state = database.get_game_state()
        if game_state and 'current_show_index' in game_state:
            self.calendar.current_show_index = game_state['current_show_index']
            print(f"✅ Loaded calendar index from database: {self.calendar.current_show_index}")
    
    @property
    def current_year(self) -> int:
        state = self.db.get_game_state()
        return state['current_year']
    
    @property
    def current_week(self) -> int:
        state = self.db.get_game_state()
        return state['current_week']
    
    @property
    def balance(self) -> int:
        state = self.db.get_game_state()
        return state['balance']
    
    @balance.setter
    def balance(self, value: int):
        self.db.update_game_state(balance=value)
    
    @property
    def show_count(self) -> int:
        state = self.db.get_game_state()
        return state['show_count']
    
    @show_count.setter
    def show_count(self, value: int):
        self.db.update_game_state(show_count=value)
    
    @property
    def wrestlers(self) -> List[Wrestler]:
        """Get all wrestlers from database"""
        wrestler_dicts = self.db.get_all_wrestlers(active_only=False)
        return [self._wrestler_from_db(w) for w in wrestler_dicts]
    
    @property
    def retired_wrestlers(self) -> List[Wrestler]:
        """Get retired wrestlers"""
        return [w for w in self.wrestlers if w.is_retired]
    
    @property
    def championships(self) -> List[Championship]:
        """Get all championships from database"""
        champ_dicts = self.db.get_all_championships()
        return [self._championship_from_db(c) for c in champ_dicts]
    
    @property
    def tag_team_manager(self):
        """Get tag team manager (lazy loaded from database)"""
        if not hasattr(self, '_tag_team_manager') or self._tag_team_manager is None:
            from models.tag_team import TagTeamManager, TagTeam
            
            self._tag_team_manager = TagTeamManager()
            
            # Load tag teams from database
            team_dicts = self.db.get_all_tag_teams(active_only=False)
            for team_dict in team_dicts:
                team = TagTeam.from_dict(team_dict)
                self._tag_team_manager.teams.append(team)
            
            # Set next ID based on existing teams
            if self._tag_team_manager.teams:
                max_id = max(int(t.team_id.replace('team_', '')) for t in self._tag_team_manager.teams)
                self._tag_team_manager._next_team_id = max_id + 1
        
        return self._tag_team_manager

    @property
    def faction_manager(self) -> FactionManager:
        """Get faction manager (lazy loaded from database)."""
        if not hasattr(self, '_faction_manager') or self._faction_manager is None:
            self._faction_manager = FactionManager()
            faction_dicts = self.db.get_all_factions(active_only=False)
            for faction_dict in faction_dicts:
                faction = Faction.from_dict(faction_dict)
                self._faction_manager.factions.append(faction)

            if self._faction_manager.factions:
                max_id = max(int(f.faction_id.replace('faction_', '')) for f in self._faction_manager.factions)
                self._faction_manager._next_faction_id = max_id + 1

        return self._faction_manager

    @property
    def relationship_network(self) -> RelationshipNetwork:
        """Get locker-room relationship network (lazy loaded from database)."""
        if not hasattr(self, '_relationship_network') or self._relationship_network is None:
            self._relationship_network = RelationshipNetwork()
            relationship_dicts = self.db.get_all_relationships(active_only=False)
            for relationship_dict in relationship_dicts:
                relationship = LockerRoomRelationship.from_dict(relationship_dict)
                self._relationship_network.relationships.append(relationship)

            if self._relationship_network.relationships:
                max_id = max(int(rel.relationship_id.replace('rel_', '')) for rel in self._relationship_network.relationships)
                self._relationship_network._next_relationship_id = max_id + 1

        return self._relationship_network
    
    def save_tag_team(self, tag_team):
        """Save a tag team to database (NO COMMIT - batched)"""
        self.db.save_tag_team(tag_team)

    def save_faction(self, faction):
        """Save a faction to database (NO COMMIT - batched)."""
        self.db.save_faction(faction)

    def save_relationship(self, relationship):
        """Save a relationship to database (NO COMMIT - batched)."""
        self.db.save_relationship(relationship)
    
    @property
    def championship_hierarchy(self) -> ChampionshipHierarchy:
        """Get championship hierarchy (lazy loaded from database)"""
        if not self._championship_hierarchy_loaded:
            try:
                state = load_championship_hierarchy_state(self.db)
                championship_hierarchy.load_from_dict(state)
                self._championship_hierarchy_loaded = True
            except Exception as e:
                print(f"⚠️ Could not load championship hierarchy state: {e}")
                self._championship_hierarchy_loaded = True  # Mark as loaded to avoid retrying
            
            self._championship_hierarchy = championship_hierarchy
        
        return self._championship_hierarchy

    def save_championship_hierarchy(self):
        """Save championship hierarchy state to database"""
        save_championship_hierarchy_state(self.db, self.championship_hierarchy)
    
    @property
    def contract_storyline_engine(self):
        """Get contract storyline engine (lazy loaded)"""
        if not hasattr(self, '_contract_storyline_engine') or self._contract_storyline_engine is None:
            from creative.contract_storylines import contract_storyline_engine
            
            # Load storylines from database
            storylines_data = self.db.load_contract_storylines()
            
            if storylines_data:
                # Convert to engine format
                engine_data = {
                    'active_storylines': storylines_data,
                    'next_storyline_id': max([int(s['storyline_id'].split('_')[-1]) for s in storylines_data], default=0) + 1
                }
                contract_storyline_engine.load_from_dict(engine_data)
            
            self._contract_storyline_engine = contract_storyline_engine
        
        return self._contract_storyline_engine

    def save_contract_storyline_engine(self):
        """Save contract storyline engine state to database"""
        if hasattr(self, '_contract_storyline_engine') and self._contract_storyline_engine:
            for storyline in self._contract_storyline_engine.active_storylines:
                self.db.save_contract_storyline(storyline)
    

    @property
    def feud_manager(self) -> FeudManager:
        """Get feud manager (lazy loaded from database)"""
        if self._feud_manager is None:
            self._feud_manager = FeudManager()
            
            # Load feuds from database
            feud_dicts = self.db.get_all_feuds(active_only=False)
            for feud_dict in feud_dicts:
                feud = self._feud_from_db(feud_dict)
                self._feud_manager.feuds.append(feud)
            
            # Set next ID based on existing feuds
            if self._feud_manager.feuds:
                max_id = max(int(f.id.replace('feud_', '')) for f in self._feud_manager.feuds)
                self._feud_manager._next_feud_id = max_id + 1
        
        return self._feud_manager
    

    def get_wrestler_by_id(self, wrestler_id: str) -> Optional[Wrestler]:
        """Get wrestler by ID from database"""
        w_dict = self.db.get_wrestler_by_id(wrestler_id)
        return self._wrestler_from_db(w_dict) if w_dict else None
    
    def get_championship_by_id(self, title_id: str) -> Optional[Championship]:
        """Get championship by ID"""
        for champ in self.championships:
            if champ.id == title_id:
                return champ
        return None
    
    def get_wrestlers_by_brand(self, brand: str) -> List[Wrestler]:
        """Get all wrestlers for a specific brand"""
        return [w for w in self.wrestlers if w.primary_brand == brand and w.can_compete]
    
    def get_active_wrestlers(self) -> List[Wrestler]:
        """Get all non-retired, able-to-compete wrestlers"""
        return [w for w in self.wrestlers if not w.is_retired and w.can_compete]
    
    def save_wrestler(self, wrestler: Wrestler):
        """Save a wrestler to database (NO COMMIT - batched)"""
        self.db.save_wrestler(wrestler)
    
    def save_championship(self, championship: Championship):
        """Save a championship to database (NO COMMIT - batched)"""
        self.db.save_championship(championship)
    
    def save_feud(self, feud: Feud):
        """Save a feud to database (NO COMMIT - batched)"""
        self.db.save_feud(feud)
        if hasattr(self, '_tag_team_manager') and self._tag_team_manager:
            for team in self._tag_team_manager.teams:
                self.db.save_tag_team(team)
    
    def save_all(self):
        """Save entire universe state to database in one transaction"""
        try:
            # Save all wrestlers
            for wrestler in self.wrestlers:
                self.db.save_wrestler(wrestler)
            
            # Save all championships
            for championship in self.championships:
                self.db.save_championship(championship)
            
            # Save all feuds
            for feud in self.feud_manager.feuds:
                self.db.save_feud(feud)

            # Save tag teams if loaded
            if hasattr(self, '_tag_team_manager') and self._tag_team_manager:
                for team in self._tag_team_manager.teams:
                    self.db.save_tag_team(team)

            if hasattr(self, '_faction_manager') and self._faction_manager:
                for faction in self._faction_manager.factions:
                    self.db.save_faction(faction)

            if hasattr(self, '_relationship_network') and self._relationship_network:
                for relationship in self._relationship_network.relationships:
                    self.db.save_relationship(relationship)
            
            # STEP 21: Save championship hierarchy
            if self._championship_hierarchy_loaded:
                self.save_championship_hierarchy()
            
            # STEP 125: Save contract storylines
            if hasattr(self, '_contract_storyline_engine') and self._contract_storyline_engine:
                self.save_contract_storyline_engine()
            
            # Update calendar position
            self.db.update_game_state(
                current_show_index=self.calendar.current_show_index
            )
            
            # Single commit for everything
            self.db.conn.commit()
            print("💾 Universe state saved to database")
            
        except Exception as e:
            print(f"⚠️ Error during save_all: {e}")
            try:
                self.db.conn.rollback()
            except:
                pass
            raise
    
    def sync_calendar_from_state(self):
        """Sync calendar position from database state"""
        state = self.db.get_game_state()
        self.calendar.current_show_index = state['current_show_index']
    
    # Helper conversion methods
    
    def _wrestler_from_db(self, w_dict: dict) -> Wrestler:
        """Convert database row to Wrestler object with STEP 122 support"""
        def _safe_int(key: str, default: int = 0) -> int:
            value = w_dict.get(key, default)
            try:
                return int(value)
            except (TypeError, ValueError):
                return default
        
        # Load contract with enhanced fields
        contract = Contract(
            salary_per_show=_safe_int('contract_salary'),
            total_length_weeks=_safe_int('contract_total_weeks', _safe_int('contract_weeks_remaining')),
            weeks_remaining=_safe_int('contract_weeks_remaining', _safe_int('contract_total_weeks')),
            signing_year=_safe_int('contract_signing_year', 1),
            signing_week=_safe_int('contract_signing_week', 1),
            
            # STEP 121 fields
            early_renewal_offered=w_dict.get('early_renewal_offered', False),
            early_renewal_week=w_dict.get('early_renewal_week'),
            early_renewal_year=w_dict.get('early_renewal_year'),
            renewal_attempts=w_dict.get('renewal_attempts', 0),
            last_renewal_attempt_week=w_dict.get('last_renewal_attempt_week'),
            last_renewal_attempt_year=w_dict.get('last_renewal_attempt_year'),
            
            # STEP 122 fields
            base_salary=w_dict.get('base_salary') or w_dict['contract_salary'],
            current_escalated_salary=w_dict.get('current_escalated_salary') or w_dict['contract_salary'],
            merchandise_share_percentage=w_dict.get('merchandise_share_percentage', 30.0),
            creative_control_level=CreativeControlLevel(w_dict.get('creative_control_level') or 'none'),
            guaranteed_ppv_appearances=w_dict.get('guaranteed_ppv_appearances', 0),
            has_no_trade_clause=bool(w_dict.get('has_no_trade_clause', 0)),
            has_injury_protection=bool(w_dict.get('has_injury_protection', 0)),
            injury_protection_percentage=w_dict.get('injury_protection_percentage', 100.0),
            option_years_remaining=w_dict.get('option_years_remaining', 0),
            buy_out_penalty=w_dict.get('buy_out_penalty', 0),
            restricted_brands=json.loads(w_dict.get('restricted_brands') or '[]'),
            max_appearances_per_year=w_dict.get('max_appearances_per_year'),
            
            ppv_appearances_this_year=w_dict.get('ppv_appearances_this_year', 0),
            title_reigns_this_contract=w_dict.get('title_reigns_this_contract', 0),
            average_match_rating=w_dict.get('average_match_rating', 0.0),
            total_matches_this_contract=w_dict.get('total_matches_this_contract', 0)
        )
        
        # Load incentives from database
        contract.incentives = self.db.load_contract_incentives(w_dict['id'])
        
        return Wrestler(
            wrestler_id=w_dict['id'],
            name=w_dict['name'],
            age=w_dict['age'],
            gender=w_dict['gender'],
            alignment=w_dict['alignment'],
            role=w_dict['role'],
            primary_brand=w_dict['primary_brand'],
            brawling=w_dict['brawling'],
            technical=w_dict['technical'],
            speed=w_dict['speed'],
            mic=w_dict['mic'],
            psychology=w_dict['psychology'],
            stamina=w_dict['stamina'],
            years_experience=w_dict['years_experience'],
            is_major_superstar=bool(w_dict['is_major_superstar']),
            popularity=w_dict['popularity'],
            momentum=w_dict['momentum'],
            morale=w_dict['morale'],
            fatigue=w_dict['fatigue'],
            contract=contract,
            injury=Injury(
                severity=w_dict['injury_severity'],
                description=w_dict['injury_description'] or 'Healthy',
                weeks_remaining=_safe_int('injury_weeks_remaining')
            ),
            is_retired=bool(w_dict['is_retired'])
        )
    
    def _championship_from_db(self, c_dict: dict) -> Championship:
        """Convert database row to Championship object - FIXED VERSION"""
        from models.championship import Championship
    
        champ = Championship(
            title_id=c_dict['id'],
            name=c_dict['name'],
            assigned_brand=c_dict['assigned_brand'],
            title_type=c_dict['title_type'],
            prestige=c_dict['prestige'],
            current_holder_id=c_dict['current_holder_id'],
            current_holder_name=c_dict['current_holder_name']
        )
    
        # Load interim champion data
        champ.interim_holder_id = c_dict.get('interim_holder_id')
        champ.interim_holder_name = c_dict.get('interim_holder_name')
        champ.defense_frequency_days = c_dict.get('defense_frequency_days', champ.defense_frequency_days)
        champ.min_annual_defenses = c_dict.get('min_annual_defenses', champ.min_annual_defenses)
        champ.total_defenses = c_dict.get('total_defenses', 0)
        
        # BUGFIX #3: Load last defense tracking fields
        champ.last_defense_year = c_dict.get('last_defense_year')
        champ.last_defense_week = c_dict.get('last_defense_week')
        champ.last_defense_show_id = c_dict.get('last_defense_show_id')
    
        # Load title reigns from database - WITH ERROR HANDLING
        cursor = self.db.conn.cursor()
        
        try:
            cursor.execute('''
                SELECT * FROM title_reigns 
                WHERE title_id = ? 
                ORDER BY won_date_year, won_date_week
            ''', (c_dict['id'],))
        
            for reign_row in cursor.fetchall():
                # Convert Row to dict to avoid indexing issues
                reign_dict = dict(reign_row)
                
                reign = TitleReign(
                    wrestler_id=reign_dict.get('wrestler_id', ''),
                    wrestler_name=reign_dict.get('wrestler_name', 'Unknown'),
                    won_at_show_id=reign_dict.get('won_at_show_id'),
                    won_at_show_name=reign_dict.get('won_at_show_name', 'Unknown'),
                    won_date_year=reign_dict.get('won_date_year', 1),
                    won_date_week=reign_dict.get('won_date_week', 1),
                    lost_at_show_id=reign_dict.get('lost_at_show_id'),
                    lost_at_show_name=reign_dict.get('lost_at_show_name'),
                    lost_date_year=reign_dict.get('lost_date_year'),
                    lost_date_week=reign_dict.get('lost_date_week'),
                    days_held=reign_dict.get('days_held', 0)
                )
                champ.history.append(reign)
        
        except Exception as e:
            print(f"⚠️ Error loading reigns for {c_dict['name']}: {e}")
            # Continue without history rather than crashing
    
        return champ
    
    def _feud_from_db(self, f_dict: dict) -> Feud:
        """Convert database row to Feud object"""
        feud = Feud(
            feud_id=f_dict['id'],
            feud_type=FeudType(f_dict['feud_type']),
            participant_ids=f_dict['participant_ids'],
            participant_names=f_dict['participant_names'],
            title_id=f_dict['title_id'],
            title_name=f_dict['title_name'],
            intensity=f_dict['intensity'],
            start_year=f_dict['start_year'],
            start_week=f_dict['start_week'],
            start_show_id=f_dict['start_show_id'],
            planned_payoff_show_id=f_dict['planned_payoff_show_id'],
            planned_payoff_event=f_dict['planned_payoff_event'],
            status=FeudStatus(f_dict['status'])
        )
        
        feud.last_segment_show_id = f_dict['last_segment_show_id']
        feud.last_segment_year = f_dict['last_segment_year']
        feud.last_segment_week = f_dict['last_segment_week']
        feud.match_count = f_dict['match_count']
        feud.wins_by_participant = f_dict['wins_by_participant']
        
        # Load segments
        for seg_dict in f_dict['segments']:
            segment = FeudSegment(
                show_id=seg_dict['show_id'],
                show_name=seg_dict['show_name'],
                year=seg_dict['year'],
                week=seg_dict['week'],
                segment_type=seg_dict['segment_type'],
                description=seg_dict['description'],
                intensity_change=seg_dict['intensity_change']
            )
            feud.segments.append(segment)
        
        return feud
    
    def to_dict(self) -> dict:
        """Serialize universe state (for API responses)"""
        return {
            'year': self.current_year,
            'week': self.current_week,
            'balance': self.balance,
            'show_count': self.show_count,
            'total_roster': len(self.wrestlers),
            'active_roster': len(self.get_active_wrestlers()),
            'retired_count': len(self.retired_wrestlers),
            'calendar': self.calendar.to_dict()
        }

    def get_wrestlers_for_show(self, show_draft) -> dict:
        """
        Get all wrestlers needed for a show draft.
        Returns dict mapping wrestler_id -> Wrestler object
        """
        wrestler_ids = set()
        
        for match in show_draft.matches:
            wrestler_ids.update(match.side_a.wrestler_ids)
            wrestler_ids.update(match.side_b.wrestler_ids)
        
        wrestlers_dict = {}
        for wid in wrestler_ids:
            wrestler = self.get_wrestler_by_id(wid)
            if wrestler:
                wrestlers_dict[wid] = wrestler
        
        return wrestlers_dict
