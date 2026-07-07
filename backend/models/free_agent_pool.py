"""
Free Agent Pool Manager (STEP 117)
Manages the collection of free agents with discovery and scouting mechanics.
UPDATED STEP 126: Rival interest generation when new free agents are added.
"""

from typing import List, Optional, Dict, Any
import random
from datetime import datetime

from models.free_agent import FreeAgent, FreeAgentSource, FreeAgentVisibility, FreeAgentMood, AgentInfo, ContractDemands, RivalInterest, ContractHistory
from models.free_agent_moods import MoodTransitionRules, MoodEffects
from persistence.free_agent_db import (
    save_free_agent,
    get_free_agent_by_id,
    get_all_free_agents,
    get_free_agents_by_visibility,
    get_free_agents_by_source,
    mark_free_agent_discovered,
    mark_free_agent_signed,
    get_free_agent_pool_summary
)


class FreeAgentPool:
    """
    Manages the free agent pool with discovery mechanics and scouting.
    
    Features:
    - Visibility tiers (Headline News, Industry Buzz, Hidden Gems, Deep Cuts)
    - Scouting network (upgradeable levels)
    - Regional scouting (Japan, Mexico, UK, Europe, Australia)
    - Auto-discovery based on scouting level
    - Mood state management
    - Rival promotion interest generation (STEP 126)
    """
    
    def __init__(self, database):
        self.db = database
        self.available_free_agents: List[FreeAgent] = []
        
        # Scouting system
        self._scouting_level = 1  # 1-5 stars
        self._scouting_network: Dict[str, bool] = {
            'japan': False,
            'mexico': False,
            'uk': False,
            'europe': False,
            'australia': False
        }
        
        # STEP 126: Rival promotion manager (set externally after init)
        self.rival_manager = None
        
        # Load free agents from database
        self.load_from_database()
    
    # ========================================================================
    # Loading & Saving
    # ========================================================================
    
    def load_from_database(self):
        """Load all free agents from database"""
        fa_dicts = get_all_free_agents(self.db, available_only=True, discovered_only=False)
        
        self.available_free_agents = []
        for fa_dict in fa_dicts:
            try:
                fa = FreeAgent.from_dict(fa_dict)
                self.available_free_agents.append(fa)
            except Exception as e:
                print(f"⚠️ Error loading free agent {fa_dict.get('id', 'unknown')}: {e}")
        
        print(f"✅ Loaded {len(self.available_free_agents)} free agents from database")
    
    def save_free_agent(self, free_agent: FreeAgent):
        """Save a free agent to database"""
        save_free_agent(self.db, free_agent)
        self.db.conn.commit()
    
    def save_all(self):
        """Save all free agents to database"""
        for fa in self.available_free_agents:
            save_free_agent(self.db, fa)
        self.db.conn.commit()
    
    # ========================================================================
    # Getters
    # ========================================================================
    
    def get_free_agent_by_id(self, fa_id: str) -> Optional[FreeAgent]:
        """Get a free agent by ID"""
        for fa in self.available_free_agents:
            if fa.id == fa_id:
                return fa
        return None

    def remove_free_agent(self, fa_id: str, promotion: str = "Ring of Champions") -> bool:
        """Mark a free agent signed and remove them from the active in-memory list."""
        free_agent = self.get_free_agent_by_id(fa_id)
        if not free_agent:
            return False

        try:
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

        self.available_free_agents = [
            fa for fa in self.available_free_agents if fa.id != fa_id
        ]
        return True
    
    def get_discovered_free_agents(self) -> List[FreeAgent]:
        """Get all free agents that have been discovered"""
        return [fa for fa in self.available_free_agents if fa.discovered]
    
    def get_undiscovered_free_agents(self) -> List[FreeAgent]:
        """Get all free agents not yet discovered"""
        return [fa for fa in self.available_free_agents if not fa.discovered]
    
    def get_free_agents_by_visibility(self, max_tier: int) -> List[FreeAgent]:
        """Get free agents up to a certain visibility tier"""
        return [fa for fa in self.available_free_agents if fa.visibility.value <= max_tier]
    
    def get_headline_free_agents(self) -> List[FreeAgent]:
        """Get headline news free agents (tier 1)"""
        return [fa for fa in self.available_free_agents if fa.visibility == FreeAgentVisibility.HEADLINE_NEWS]
    
    def get_legends(self) -> List[FreeAgent]:
        """Get all legend free agents"""
        return [fa for fa in self.available_free_agents if fa.is_legend]
    
    def get_prospects(self) -> List[FreeAgent]:
        """Get all prospect free agents"""
        return [fa for fa in self.available_free_agents if fa.is_prospect]
    
    def get_international_talents(self, region: Optional[str] = None) -> List[FreeAgent]:
        """Get international free agents, optionally filtered by region"""
        if region:
            return [fa for fa in self.available_free_agents if fa.origin_region == region]
        else:
            return [fa for fa in self.available_free_agents if fa.origin_region != 'domestic']
    
    def get_controversy_cases(self) -> List[FreeAgent]:
        """Get all controversy case free agents"""
        return [fa for fa in self.available_free_agents if fa.has_controversy]
    
    # ========================================================================
    # Discovery Mechanics (STEP 115)
    # ========================================================================
    
    def discover_free_agent(self, fa_id: str) -> bool:
        """
        Discover a specific free agent.
        Returns True if successfully discovered, False if already discovered or not found.
        """
        fa = self.get_free_agent_by_id(fa_id)
        
        if not fa:
            return False
        
        if fa.discovered:
            return False  # Already discovered
        
        fa.discovered = True
        fa.updated_at = datetime.now().isoformat()
        
        # Save to database
        mark_free_agent_discovered(self.db, fa_id)
        
        print(f"🔍 Discovered: {fa.wrestler_name} ({fa.visibility_label})")
        
        return True
    
    def auto_discover_by_scouting_level(self) -> List[FreeAgent]:
        """
        Auto-discover free agents based on current scouting level.
        
        Level 1: Only Headline News
        Level 2: Headline News + Industry Buzz
        Level 3: Headline News + Industry Buzz + some Hidden Gems
        Level 4: All except Deep Cuts
        Level 5: Everything
        """
        newly_discovered = []
        
        for fa in self.get_undiscovered_free_agents():
            should_discover = False
            
            # Level-based discovery
            if self._scouting_level >= 5:
                should_discover = True  # Discover everything
            elif self._scouting_level >= 4:
                should_discover = fa.visibility.value <= 3  # All except Deep Cuts
            elif self._scouting_level >= 3:
                # Headline + Industry + 50% of Hidden Gems
                if fa.visibility.value <= 2:
                    should_discover = True
                elif fa.visibility.value == 3 and random.random() < 0.5:
                    should_discover = True
            elif self._scouting_level >= 2:
                should_discover = fa.visibility.value <= 2  # Headline + Industry
            else:  # Level 1
                should_discover = fa.visibility.value == 1  # Only Headline News
            
            # Regional scouting override
            if fa.origin_region != 'domestic':
                if not self._scouting_network.get(fa.origin_region, False):
                    should_discover = False  # Region not scouted yet
            
            if should_discover:
                fa.discovered = True
                mark_free_agent_discovered(self.db, fa.id)
                newly_discovered.append(fa)
        
        if newly_discovered:
            print(f"🔍 Auto-discovered {len(newly_discovered)} free agents")
        
        return newly_discovered
    
    def scout_region(self, region: str) -> List[FreeAgent]:
        """
        Establish scouting network in a region.
        Returns newly discovered free agents from that region.
        """
        if region not in self._scouting_network:
            return []
        
        if self._scouting_network[region]:
            return []  # Already scouted
        
        self._scouting_network[region] = True
        
        # Discover all free agents from this region up to current scouting level
        newly_discovered = []
        for fa in self.get_international_talents(region):
            if not fa.discovered:
                # Respect scouting level visibility limits
                max_tier = min(self._scouting_level + 1, 4)
                if fa.visibility.value <= max_tier:
                    fa.discovered = True
                    mark_free_agent_discovered(self.db, fa.id)
                    newly_discovered.append(fa)
        
        print(f"🌍 Scouted {region}: Discovered {len(newly_discovered)} talents")
        
        return newly_discovered
    
    def upgrade_scouting(self) -> int:
        """
        Upgrade scouting level.
        Returns new scouting level.
        """
        if self._scouting_level >= 5:
            return self._scouting_level  # Max level
        
        self._scouting_level += 1
        
        # Auto-discover newly accessible free agents
        self.auto_discover_by_scouting_level()
        
        print(f"⬆️ Scouting upgraded to level {self._scouting_level}")
        
        return self._scouting_level
    
    # ========================================================================
    # Visibility Management (STEP 115)
    # ========================================================================
    
    def promote_visibility(self, fa_id: str, reason: str = "") -> Optional[FreeAgent]:
        """Promote free agent to higher visibility tier"""
        fa = self.get_free_agent_by_id(fa_id)
        if not fa:
            return None
        
        current_tier = fa.visibility.value
        if current_tier <= 1:
            return fa  # Already at max visibility
        
        # Move up one tier
        new_tier = current_tier - 1
        fa.visibility = FreeAgentVisibility(new_tier)
        fa.updated_at = datetime.now().isoformat()
        
        self.save_free_agent(fa)
        
        print(f"⬆️ {fa.wrestler_name} visibility: {current_tier} → {new_tier} ({reason})")
        
        return fa
    
    def demote_visibility(self, fa_id: str, reason: str = "") -> Optional[FreeAgent]:
        """Demote free agent to lower visibility tier"""
        fa = self.get_free_agent_by_id(fa_id)
        if not fa:
            return None
        
        current_tier = fa.visibility.value
        if current_tier >= 4:
            return fa  # Already at min visibility
        
        # Move down one tier
        new_tier = current_tier + 1
        fa.visibility = FreeAgentVisibility(new_tier)
        fa.updated_at = datetime.now().isoformat()
        
        self.save_free_agent(fa)
        
        print(f"⬇️ {fa.wrestler_name} visibility: {current_tier} → {new_tier} ({reason})")
        
        return fa
    
    def process_visibility_changes(self, year: int, week: int) -> List[Dict[str, Any]]:
        """
        Process weekly visibility changes.
        Free agents can rise or fall in visibility based on activity.
        """
        changes = []
        
        for fa in self.available_free_agents:
            # Promote if getting rival interest
            if len(fa.rival_interest) >= 3 and fa.visibility.value > 1:
                old_tier = fa.visibility.value
                self.promote_visibility(fa.id, "High rival interest")
                changes.append({
                    'wrestler_name': fa.wrestler_name,
                    'change': 'promoted',
                    'old_tier': old_tier,
                    'new_tier': fa.visibility.value,
                    'reason': 'High rival interest'
                })
            
            # Demote if unemployed too long without interest
            if fa.weeks_unemployed > 20 and len(fa.rival_interest) == 0 and fa.visibility.value < 4:
                old_tier = fa.visibility.value
                self.demote_visibility(fa.id, "Long unemployment, no interest")
                changes.append({
                    'wrestler_name': fa.wrestler_name,
                    'change': 'demoted',
                    'old_tier': old_tier,
                    'new_tier': fa.visibility.value,
                    'reason': 'Long unemployment, no interest'
                })
        
        return changes
    
    def trigger_news_event(self, fa_id: str, event_type: str) -> Dict[str, Any]:
        """
        Trigger a news event that affects visibility.
        
        Event types:
        - interview: Wrestler does media appearance
        - social_media: Viral social media moment
        - rival_signing_failed: Public failed negotiation
        - injury_recovery: Announced recovery from injury
        - comeback_tease: Legend teases return
        - shoot_promo: Controversial public statement
        """
        fa = self.get_free_agent_by_id(fa_id)
        if not fa:
            return {'success': False, 'error': 'Free agent not found'}
        
        visibility_boost = False
        message = ""
        
        if event_type == 'interview':
            if random.random() < 0.3:
                self.promote_visibility(fa_id, "Media appearance")
                visibility_boost = True
                message = f"{fa.wrestler_name} gains attention from recent interview"
        
        elif event_type == 'social_media':
            if random.random() < 0.5:
                self.promote_visibility(fa_id, "Viral moment")
                visibility_boost = True
                message = f"{fa.wrestler_name} trends on social media"
        
        elif event_type == 'rival_signing_failed':
            self.promote_visibility(fa_id, "Public negotiation")
            visibility_boost = True
            message = f"Reports: {fa.wrestler_name} negotiations with rival promotion fell through"
        
        elif event_type == 'injury_recovery':
            if fa.injury_history_count > 0:
                self.promote_visibility(fa_id, "Injury update")
                visibility_boost = True
                message = f"{fa.wrestler_name} announces full recovery, ready to compete"
        
        elif event_type == 'comeback_tease':
            if fa.is_legend:
                self.promote_visibility(fa_id, "Comeback tease")
                visibility_boost = True
                message = f"LEGEND ALERT: {fa.wrestler_name} hints at possible return!"
        
        elif event_type == 'shoot_promo':
            # 50/50 helps or hurts
            if random.random() < 0.5:
                self.promote_visibility(fa_id, "Controversial statement")
                visibility_boost = True
                message = f"{fa.wrestler_name}'s controversial comments generate buzz"
            else:
                self.demote_visibility(fa_id, "Negative publicity")
                message = f"{fa.wrestler_name}'s comments draw criticism"
        
        return {
            'success': True,
            'event_type': event_type,
            'visibility_changed': visibility_boost,
            'message': message,
            'free_agent': fa.to_dict()
        }
    
    # ========================================================================
    # Mood Management (STEP 117)
    # ========================================================================
    
    def update_all_moods(self, year: int, week: int) -> List[Dict[str, Any]]:
        """Update moods for all free agents"""
        mood_changes = []
        
        for fa in self.available_free_agents:
            result = fa.update_mood(year, week)
            if result['changed']:
                mood_changes.append({
                    'wrestler_name': fa.wrestler_name,
                    'old_mood': result['old_mood'],
                    'new_mood': result['new_mood'],
                    'reason': result['reason']
                })
                
                # Save updated mood
                self.save_free_agent(fa)
        
        return mood_changes
    
    # ========================================================================
    # Pool Population (STEP 114)
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
        Add a wrestler to the free agent pool after release/contract expiration.
        STEP 126: Also generate rival interest.
        """
        source_map = {
            'released': FreeAgentSource.RELEASED,
            'fired': FreeAgentSource.RELEASED,
            'contract_expired': FreeAgentSource.CONTRACT_EXPIRED,
            'mutual': FreeAgentSource.MUTUAL_AGREEMENT
        }
        
        source = source_map.get(departure_reason, FreeAgentSource.RELEASED)
        
        fa = FreeAgent.from_wrestler(wrestler, source, year, week)
        
        # Add contract history
        fa.contract_history.append(ContractHistory(
            promotion_name="Ring of Champions",  # Your promotion name
            start_year=max(1, year - 2),  # Estimate
            end_year=year,
            departure_reason=departure_reason,
            final_salary=wrestler.contract.salary_per_show,
            was_champion=was_champion,
            relationship_on_departure=relationship
        ))
        
        # Set no-compete if applicable
        if no_compete_weeks > 0:
            fa.no_compete_until_year = year
            fa.no_compete_until_week = week + no_compete_weeks
            
            # Handle year overflow
            if fa.no_compete_until_week > 52:
                fa.no_compete_until_year += 1
                fa.no_compete_until_week -= 52
        
        # Auto-discover if major star
        if fa.visibility == FreeAgentVisibility.HEADLINE_NEWS:
            fa.discovered = True
        
        # STEP 126: Generate rival interest
        if self.rival_manager:
            rival_interests = self.rival_manager.generate_interest(fa, year, week)
            for interest in rival_interests:
                fa.add_rival_interest(interest.promotion_name, interest.interest_level)
        
        self.available_free_agents.append(fa)
        self.save_free_agent(fa)
        
        print(f"➕ Added to free agent pool: {fa.wrestler_name} ({source.value})")
        
        return fa
    
    def populate_pool_from_releases(self, universe, count: int = 3) -> List[FreeAgent]:
        """
        Generate free agents representing releases from rival promotions.
        STEP 126: Also generate rival interest.
        """
        generated = []
        
        for _ in range(count):
            # Generate random wrestler-like free agent
            fa = self._generate_random_free_agent(
                source=FreeAgentSource.RELEASED,
                year=universe.current_year,
                week=universe.current_week
            )
            
            # STEP 126: Generate rival interest
            if self.rival_manager:
                rival_interests = self.rival_manager.generate_interest(fa, universe.current_year, universe.current_week)
                for interest in rival_interests:
                    fa.add_rival_interest(interest.promotion_name, interest.interest_level)
            
            self.available_free_agents.append(fa)
            self.save_free_agent(fa)
            generated.append(fa)
        
        print(f"📦 Generated {len(generated)} free agents from rival releases")
        
        return generated
    
    def generate_international_wave(self, universe, region: str, count: int = 2) -> List[FreeAgent]:
        """Generate international free agents from a specific region"""
        generated = []
        
        for _ in range(count):
            fa = self._generate_random_free_agent(
                source=FreeAgentSource.INTERNATIONAL,
                year=universe.current_year,
                week=universe.current_week,
                region=region
            )
            
            # STEP 126: Generate rival interest
            if self.rival_manager:
                rival_interests = self.rival_manager.generate_interest(fa, universe.current_year, universe.current_week)
                for interest in rival_interests:
                    fa.add_rival_interest(interest.promotion_name, interest.interest_level)
            
            self.available_free_agents.append(fa)
            self.save_free_agent(fa)
            generated.append(fa)
        
        print(f"🌍 Generated {len(generated)} international talents from {region}")
        
        return generated
    
    def generate_prospect_class(self, universe, count: int = 5) -> List[FreeAgent]:
        """Generate fresh prospects"""
        generated = []
        
        for _ in range(count):
            fa = self._generate_random_free_agent(
                source=FreeAgentSource.PROSPECT,
                year=universe.current_year,
                week=universe.current_week,
                is_prospect=True
            )
            
            # STEP 126: Generate rival interest
            if self.rival_manager:
                rival_interests = self.rival_manager.generate_interest(fa, universe.current_year, universe.current_week)
                for interest in rival_interests:
                    fa.add_rival_interest(interest.promotion_name, interest.interest_level)
            
            self.available_free_agents.append(fa)
            self.save_free_agent(fa)
            generated.append(fa)
        
        print(f"🌟 Generated {len(generated)} new prospects")
        
        return generated
    
    def generate_random_prospects(self, count: int, year: int, week: int) -> List[FreeAgent]:
        """Generate random prospects (wrapper for compatibility)"""
        generated = []
        
        for _ in range(count):
            fa = self._generate_random_free_agent(
                source=FreeAgentSource.PROSPECT,
                year=year,
                week=week,
                is_prospect=True
            )
            
            # STEP 126: Generate rival interest
            if self.rival_manager:
                rival_interests = self.rival_manager.generate_interest(fa, year, week)
                for interest in rival_interests:
                    fa.add_rival_interest(interest.promotion_name, interest.interest_level)
            
            self.available_free_agents.append(fa)
            self.save_free_agent(fa)
            generated.append(fa)
        
        return generated
    
    def check_legend_availability(self, universe, retired_wrestlers: List) -> List[FreeAgent]:
        """Check if any retired legends are considering comebacks"""
        comebacks = []
        
        for retired in retired_wrestlers:
            if not retired.is_major_superstar:
                continue
            
            if retired.age > 50:
                continue  # Too old
            
            # 10% chance per check
            if random.random() < 0.10:
                fa = FreeAgent.from_wrestler(
                    retired,
                    FreeAgentSource.RETIRED_COMEBACK,
                    universe.current_year,
                    universe.current_week
                )
                
                fa.is_legend = True
                fa.retirement_status = 'soft_retired'
                fa.comeback_likelihood = random.randint(50, 80)
                fa.discovered = True  # Legends are always big news
                
                # STEP 126: Generate rival interest
                if self.rival_manager:
                    rival_interests = self.rival_manager.generate_interest(fa, universe.current_year, universe.current_week)
                    for interest in rival_interests:
                        fa.add_rival_interest(interest.promotion_name, interest.interest_level)
                
                self.available_free_agents.append(fa)
                self.save_free_agent(fa)
                comebacks.append(fa)
        
        if comebacks:
            print(f"👴 {len(comebacks)} legends considering comeback!")
        
        return comebacks
    
    def _generate_random_free_agent(
        self,
        source: FreeAgentSource,
        year: int,
        week: int,
        region: str = 'domestic',
        is_prospect: bool = False
    ) -> FreeAgent:
        """Generate a random free agent"""
        from models.wrestler import generate_random_name
        
        # Generate attributes
        if is_prospect:
            # Prospects have lower current but higher ceiling
            attrs = {
                'brawling': random.randint(40, 65),
                'technical': random.randint(40, 65),
                'speed': random.randint(45, 70),
                'mic': random.randint(35, 60),
                'psychology': random.randint(30, 55),
                'stamina': random.randint(50, 70)
            }
            age = random.randint(20, 25)
            years_exp = random.randint(1, 3)
            ceiling = random.randint(70, 95)
        else:
            attrs = {
                'brawling': random.randint(50, 85),
                'technical': random.randint(50, 85),
                'speed': random.randint(50, 85),
                'mic': random.randint(45, 80),
                'psychology': random.randint(50, 85),
                'stamina': random.randint(55, 85)
            }
            age = random.randint(25, 40)
            years_exp = random.randint(5, 20)
            ceiling = 0
        
        gender = random.choice(['Male', 'Female'])
        name = generate_random_name(gender)
        
        alignment = random.choice(['Face', 'Heel', 'Tweener'])
        role = random.choice(['Main Event', 'Upper Midcard', 'Midcard', 'Lower Midcard'])
        
        fa_id = f"fa_{name.replace(' ', '_').lower()}_{year}_{week}"
        wrestler_id = f"w_{name.replace(' ', '_').lower()}"
        
        fa = FreeAgent(
            free_agent_id=fa_id,
            wrestler_id=wrestler_id,
            wrestler_name=name,
            age=age,
            gender=gender,
            alignment=alignment,
            role=role,
            **attrs,
            years_experience=years_exp,
            popularity=random.randint(40, 75),
            source=source,
            visibility=FreeAgentVisibility(random.randint(2, 4)),
            mood=FreeAgentMood.PATIENT,
            origin_region=region,
            is_prospect=is_prospect,
            ceiling_potential=ceiling,
            available_from_year=year,
            available_from_week=week
        )
        
        return fa
    
    # ========================================================================
    # Weekly Processing
    # ========================================================================
    
    def process_week(self, year: int, week: int) -> List[Dict[str, Any]]:
        """Process weekly updates for all free agents"""
        events = []
        
        for fa in self.available_free_agents:
            fa.advance_week()
            self.save_free_agent(fa)
        
        # Update moods
        mood_changes = self.update_all_moods(year, week)
        events.extend([{'type': 'mood_change', **change} for change in mood_changes])
        
        # Process visibility changes
        visibility_changes = self.process_visibility_changes(year, week)
        events.extend([{'type': 'visibility_change', **change} for change in visibility_changes])
        
        return events
    
    def process_controversy_cases(self, universe) -> List[Dict[str, Any]]:
        """Process controversy case updates"""
        updates = []
        
        for fa in self.get_controversy_cases():
            # Controversy fades over time
            if fa.time_since_incident_weeks > 52:
                old_severity = fa.controversy_severity
                fa.controversy_severity = max(0, fa.controversy_severity - 10)
                
                if fa.controversy_severity == 0:
                    fa.has_controversy = False
                    updates.append({
                        'wrestler_name': fa.wrestler_name,
                        'status': 'cleared',
                        'message': f"{fa.wrestler_name}'s controversy has been forgiven"
                    })
                else:
                    updates.append({
                        'wrestler_name': fa.wrestler_name,
                        'status': 'improving',
                        'old_severity': old_severity,
                        'new_severity': fa.controversy_severity
                    })
                
                self.save_free_agent(fa)
        
        return updates
    
    # ========================================================================
    # Utility
    # ========================================================================
    
    def get_pool_summary(self) -> Dict[str, Any]:
        """Get summary of free agent pool"""
        summary = get_free_agent_pool_summary(self.db)
        
        # Add runtime info
        summary['scouting_level'] = self._scouting_level
        summary['scouting_networks'] = self._scouting_network.copy()
        
        return summary
    
    def get_pool_health_report(self) -> Dict[str, Any]:
        """Get detailed health report of the pool"""
        total = len(self.available_free_agents)
        discovered = len(self.get_discovered_free_agents())
        
        by_source = {}
        by_mood = {}
        by_visibility = {}
        
        for fa in self.available_free_agents:
            # Count by source
            source_key = fa.source.value
            by_source[source_key] = by_source.get(source_key, 0) + 1
            
            # Count by mood
            mood_key = fa.mood.value
            by_mood[mood_key] = by_mood.get(mood_key, 0) + 1
            
            # Count by visibility
            vis_key = fa.visibility_label
            by_visibility[vis_key] = by_visibility.get(vis_key, 0) + 1
        
        return {
            'total_available': total,
            'discovered': discovered,
            'undiscovered': total - discovered,
            'discovery_rate': round((discovered / total * 100) if total > 0 else 0, 1),
            'by_source': by_source,
            'by_mood': by_mood,
            'by_visibility': by_visibility,
            'scouting_level': self._scouting_level,
            'regions_scouted': sum(1 for v in self._scouting_network.values() if v),
            'legends_available': len(self.get_legends()),
            'prospects_available': len(self.get_prospects()),
            'international_available': len(self.get_international_talents()),
            'controversy_cases': len(self.get_controversy_cases())
        }
    
    def get_visibility_breakdown(self) -> Dict[str, Any]:
        """Get breakdown of free agents by visibility tier"""
        breakdown = {
            'headline_news': [],
            'industry_buzz': [],
            'hidden_gems': [],
            'deep_cuts': []
        }
        
        for fa in self.available_free_agents:
            if fa.visibility == FreeAgentVisibility.HEADLINE_NEWS:
                breakdown['headline_news'].append(fa.to_dict())
            elif fa.visibility == FreeAgentVisibility.INDUSTRY_BUZZ:
                breakdown['industry_buzz'].append(fa.to_dict())
            elif fa.visibility == FreeAgentVisibility.HIDDEN_GEM:
                breakdown['hidden_gems'].append(fa.to_dict())
            elif fa.visibility == FreeAgentVisibility.DEEP_CUT:
                breakdown['deep_cuts'].append(fa.to_dict())
        
        return {
            'headline_news': {
                'count': len(breakdown['headline_news']),
                'discovered': sum(1 for fa in breakdown['headline_news'] if fa['discovered']),
                'free_agents': breakdown['headline_news']
            },
            'industry_buzz': {
                'count': len(breakdown['industry_buzz']),
                'discovered': sum(1 for fa in breakdown['industry_buzz'] if fa['discovered']),
                'free_agents': breakdown['industry_buzz']
            },
            'hidden_gems': {
                'count': len(breakdown['hidden_gems']),
                'discovered': sum(1 for fa in breakdown['hidden_gems'] if fa['discovered']),
                'free_agents': breakdown['hidden_gems']
            },
            'deep_cuts': {
                'count': len(breakdown['deep_cuts']),
                'discovered': sum(1 for fa in breakdown['deep_cuts'] if fa['discovered']),
                'free_agents': breakdown['deep_cuts']
            }
        }
