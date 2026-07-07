"""
Storyline Model
Represents scripted storylines that trigger at specific times.
These are pre-written narrative beats that enhance the universe.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
from datetime import datetime


class StorylineType(Enum):
    """Types of scripted storylines"""
    BETRAYAL = "betrayal"                    # Tag partner or faction member turns
    RETURN = "return"                        # Legend or injured star returns
    TITLE_PURSUIT = "title_pursuit"          # Underdog chases championship
    FACTION_WAR = "faction_war"              # Groups collide
    RETIREMENT = "retirement"                # Career-ending storyline
    ROOKIE_RISE = "rookie_rise"              # Young star's journey
    AUTHORITY = "authority"                  # Power struggle with management
    MYSTERY = "mystery"                      # Who attacked/who's the leader
    TOURNAMENT = "tournament"                # Multi-week competition
    INVASION = "invasion"                    # Brand warfare


class StorylineStatus(Enum):
    """Current state of the storyline"""
    PENDING = "pending"          # Not yet triggered
    ACTIVE = "active"           # Currently playing out
    COMPLETED = "completed"     # Finished successfully
    FAILED = "failed"          # Conditions not met, abandoned


class TriggerCondition(Enum):
    """When a storyline can trigger"""
    SPECIFIC_WEEK = "specific_week"          # Exact week number
    SPECIFIC_PPV = "specific_ppv"            # At a named PPV
    AFTER_WEEK = "after_week"                # Any time after week X
    WRESTLER_STATE = "wrestler_state"        # Based on wrestler condition
    FEUD_INTENSITY = "feud_intensity"        # When feud reaches threshold
    TITLE_REIGN_LENGTH = "title_reign_length" # Champion held X weeks
    RANDOM_CHANCE = "random_chance"          # X% chance each week


@dataclass
class StorylineBeat:
    """A single story development within a storyline"""
    beat_id: str
    week_offset: int  # Weeks after storyline starts
    description: str
    segment_type: str  # 'promo', 'attack', 'match', 'reveal', etc.
    participants: List[str]  # Wrestler IDs or roles
    
    # Effects
    create_feud: bool = False
    end_feud: bool = False
    turn_alignment: Optional[Dict[str, str]] = None  # wrestler_id -> new_alignment
    injury_target: Optional[str] = None
    title_change_setup: bool = False
    
    # Conditions for this beat to happen
    required_conditions: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'beat_id': self.beat_id,
            'week_offset': self.week_offset,
            'description': self.description,
            'segment_type': self.segment_type,
            'participants': self.participants,
            'create_feud': self.create_feud,
            'end_feud': self.end_feud,
            'turn_alignment': self.turn_alignment,
            'injury_target': self.injury_target,
            'title_change_setup': self.title_change_setup,
            'required_conditions': self.required_conditions
        }


@dataclass
class Storyline:
    """
    A complete scripted storyline with multiple beats.
    
    Storylines have trigger conditions and play out over multiple weeks.
    They can involve specific wrestlers or roles that get cast dynamically.
    """
    
    storyline_id: str
    name: str
    storyline_type: StorylineType
    description: str
    
    # Triggering
    trigger_conditions: List[Dict[str, Any]]  # All must be true
    
    # Casting - can use specific IDs or roles
    required_cast: Dict[str, Dict[str, Any]]  # role -> requirements
    # Example: {"hero": {"alignment": "Face", "role": "Main Event"}}
    
    # Optional fields with defaults
    priority: int = 50  # Higher priority storylines trigger first
    
    # Story beats
    beats: List[StorylineBeat] = field(default_factory=list)
    
    # Tracking
    status: StorylineStatus = StorylineStatus.PENDING
    triggered_year: Optional[int] = None
    triggered_week: Optional[int] = None
    cast_assignments: Dict[str, str] = field(default_factory=dict)  # role -> wrestler_id
    completed_beats: List[str] = field(default_factory=list)
    
    # Outcomes
    payoff_show: Optional[str] = None  # PPV name for climax
    legacy_effects: Dict[str, Any] = field(default_factory=dict)
    
    def can_trigger(self, universe_state, year: int, week: int) -> bool:
        """Check if all trigger conditions are met"""
        for condition in self.trigger_conditions:
            if not self._check_condition(condition, universe_state, year, week):
                return False
        return True
    
    def _check_condition(self, condition: Dict[str, Any], universe_state, year: int, week: int) -> bool:
        """Check a single trigger condition"""
        cond_type = condition.get('type')
        
        if cond_type == TriggerCondition.SPECIFIC_WEEK.value:
            return year == condition.get('year', 1) and week == condition['week']
        
        elif cond_type == TriggerCondition.SPECIFIC_PPV.value:
            current_show = universe_state.calendar.get_current_show()
            return current_show and current_show.name == condition['ppv_name']
        
        elif cond_type == TriggerCondition.AFTER_WEEK.value:
            target_year = condition.get('year', 1)
            target_week = condition['week']
            current_total_weeks = (year - 1) * 52 + week
            target_total_weeks = (target_year - 1) * 52 + target_week
            return current_total_weeks >= target_total_weeks
        
        elif cond_type == TriggerCondition.WRESTLER_STATE.value:
            wrestler_id = condition.get('wrestler_id')
            if wrestler_id:
                wrestler = universe_state.get_wrestler_by_id(wrestler_id)
                if not wrestler:
                    return False
                
                state_check = condition.get('state')
                if state_check == 'is_champion':
                    for title in universe_state.championships:
                        if title.current_holder_id == wrestler_id:
                            return True
                    return False
                elif state_check == 'is_injured':
                    return wrestler.is_injured
                elif state_check == 'high_popularity':
                    return wrestler.popularity >= condition.get('min_popularity', 80)
        
        elif cond_type == TriggerCondition.RANDOM_CHANCE.value:
            import random
            return random.random() < condition.get('chance', 0.1)
        
        return True
    
    def cast_storyline(self, universe_state) -> bool:
        """
        Assign wrestlers to storyline roles.
        Returns True if casting successful, False otherwise.
        """
        cast = {}
        available_wrestlers = universe_state.get_active_wrestlers()
        
        for role, requirements in self.required_cast.items():
            # Check if specific wrestler required
            if 'wrestler_id' in requirements:
                wrestler = universe_state.get_wrestler_by_id(requirements['wrestler_id'])
                if wrestler and wrestler.can_compete:
                    cast[role] = wrestler.id
                else:
                    return False  # Required wrestler not available
            else:
                # Find wrestler matching requirements
                candidates = []
                for wrestler in available_wrestlers:
                    if self._wrestler_matches_requirements(wrestler, requirements):
                        candidates.append(wrestler)
                
                if not candidates:
                    return False  # No suitable wrestler for role
                
                # Pick best candidate (highest popularity for now)
                best = max(candidates, key=lambda w: w.popularity)
                cast[role] = best.id
                
                # Remove from available pool to avoid double-casting
                available_wrestlers = [w for w in available_wrestlers if w.id != best.id]
        
        self.cast_assignments = cast
        return True
    
    def _wrestler_matches_requirements(self, wrestler, requirements: Dict[str, Any]) -> bool:
        """Check if wrestler meets role requirements"""
        if 'alignment' in requirements and wrestler.alignment != requirements['alignment']:
            return False
        
        if 'role' in requirements and wrestler.role != requirements['role']:
            return False
        
        if 'gender' in requirements and wrestler.gender != requirements['gender']:
            return False
        
        if 'brand' in requirements and wrestler.primary_brand != requirements['brand']:
            return False
        
        if 'min_popularity' in requirements and wrestler.popularity < requirements['min_popularity']:
            return False
        
        if 'max_age' in requirements and wrestler.age > requirements['max_age']:
            return False
        
        if 'is_champion' in requirements:
            # Would need to check championships
            pass
        
        return True
    
    def get_next_beat(self) -> Optional[StorylineBeat]:
        """Get the next story beat to execute"""
        if not self.triggered_week:
            return None
        
        current_week_offset = 0  # Would calculate from triggered_week
        
        for beat in self.beats:
            if beat.beat_id not in self.completed_beats and beat.week_offset <= current_week_offset:
                return beat
        
        return None
    
    def execute_beat(self, beat: StorylineBeat, universe_state) -> Dict[str, Any]:
        """
        Execute a story beat and return the results.
        This would create segments, feuds, injuries, etc.
        """
        results = {
            'beat_id': beat.beat_id,
            'description': beat.description,
            'effects': []
        }
        
        # Resolve participant IDs from roles
        actual_participants = []
        for participant in beat.participants:
            if participant in self.cast_assignments:
                actual_participants.append(self.cast_assignments[participant])
            else:
                actual_participants.append(participant)  # Already an ID
        
        # Create feud if needed
        if beat.create_feud and len(actual_participants) >= 2:
            from models.feud import FeudType
            
            # Get wrestler names
            names = []
            for pid in actual_participants[:2]:
                wrestler = universe_state.get_wrestler_by_id(pid)
                if wrestler:
                    names.append(wrestler.name)
            
            if len(names) == 2:
                feud = universe_state.feud_manager.create_feud(
                    feud_type=FeudType.PERSONAL,
                    participant_ids=actual_participants[:2],
                    participant_names=names,
                    year=universe_state.current_year,
                    week=universe_state.current_week,
                    initial_intensity=60  # Storyline feuds start hot
                )
                results['effects'].append(f"Created feud: {names[0]} vs {names[1]}")
        
        # Handle alignment turns
        if beat.turn_alignment:
            for role, new_alignment in beat.turn_alignment.items():
                if role in self.cast_assignments:
                    wrestler_id = self.cast_assignments[role]
                    wrestler = universe_state.get_wrestler_by_id(wrestler_id)
                    if wrestler:
                        old_alignment = wrestler.alignment
                        wrestler.alignment = new_alignment
                        universe_state.save_wrestler(wrestler)
                        results['effects'].append(
                            f"{wrestler.name} turned {new_alignment}! (was {old_alignment})"
                        )
        
        # Handle injuries
        if beat.injury_target:
            target_role = beat.injury_target
            if target_role in self.cast_assignments:
                wrestler_id = self.cast_assignments[target_role]
                wrestler = universe_state.get_wrestler_by_id(wrestler_id)
                if wrestler:
                    wrestler.apply_injury('Major', 'storyline attack', 12)
                    universe_state.save_wrestler(wrestler)
                    results['effects'].append(f"{wrestler.name} was injured in the attack!")
        
        # Mark beat as completed
        self.completed_beats.append(beat.beat_id)
        
        # Check if storyline is complete
        if len(self.completed_beats) == len(self.beats):
            self.status = StorylineStatus.COMPLETED
            results['storyline_completed'] = True
        
        return results
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'storyline_id': self.storyline_id,
            'name': self.name,
            'storyline_type': self.storyline_type.value,
            'description': self.description,
            'trigger_conditions': self.trigger_conditions,
            'priority': self.priority,
            'required_cast': self.required_cast,
            'beats': [beat.to_dict() for beat in self.beats],
            'status': self.status.value,
            'triggered_year': self.triggered_year,
            'triggered_week': self.triggered_week,
            'cast_assignments': self.cast_assignments,
            'completed_beats': self.completed_beats,
            'payoff_show': self.payoff_show,
            'legacy_effects': self.legacy_effects
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Storyline':
        """Create storyline from dictionary"""
        storyline = Storyline(
            storyline_id=data['storyline_id'],
            name=data['name'],
            storyline_type=StorylineType(data['storyline_type']),
            description=data['description'],
            trigger_conditions=data.get('trigger_conditions', []),
            priority=data.get('priority', 50),
            required_cast=data.get('required_cast', {}),
            status=StorylineStatus(data.get('status', 'pending')),
            triggered_year=data.get('triggered_year'),
            triggered_week=data.get('triggered_week'),
            cast_assignments=data.get('cast_assignments', {}),
            completed_beats=data.get('completed_beats', []),
            payoff_show=data.get('payoff_show'),
            legacy_effects=data.get('legacy_effects', {})
        )
        
        # Load beats
        for beat_data in data.get('beats', []):
            beat = StorylineBeat(
                beat_id=beat_data['beat_id'],
                week_offset=beat_data['week_offset'],
                description=beat_data['description'],
                segment_type=beat_data['segment_type'],
                participants=beat_data['participants'],
                create_feud=beat_data.get('create_feud', False),
                end_feud=beat_data.get('end_feud', False),
                turn_alignment=beat_data.get('turn_alignment'),
                injury_target=beat_data.get('injury_target'),
                title_change_setup=beat_data.get('title_change_setup', False),
                required_conditions=beat_data.get('required_conditions', [])
            )
            storyline.beats.append(beat)
        return storyline


class StorylineManager:
    """Manages all storylines in the universe"""
    
    def __init__(self):
        self.storylines: List[Storyline] = []
        self.completed_storylines: List[Storyline] = []
    
    def add_storyline(self, storyline: Storyline):
        """Add a storyline to the manager"""
        self.storylines.append(storyline)
    
    def check_triggers(self, universe_state, year: int, week: int) -> List[Storyline]:
        """
        Check all pending storylines for trigger conditions.
        Returns list of newly triggered storylines.
        """
        triggered = []
        
        # Sort by priority (highest first)
        pending = [s for s in self.storylines if s.status == StorylineStatus.PENDING]
        pending.sort(key=lambda s: s.priority, reverse=True)
        
        for storyline in pending:
            if storyline.can_trigger(universe_state, year, week):
                # Try to cast the storyline
                if storyline.cast_storyline(universe_state):
                    storyline.status = StorylineStatus.ACTIVE
                    storyline.triggered_year = year
                    storyline.triggered_week = week
                    triggered.append(storyline)
                    
                    print(f"🎭 STORYLINE TRIGGERED: {storyline.name}")
                    print(f"   Cast: {storyline.cast_assignments}")
        
        return triggered
    
    def get_active_storylines(self) -> List[Storyline]:
        """Get all currently active storylines"""
        return [s for s in self.storylines if s.status == StorylineStatus.ACTIVE]
    
    def process_week(self, universe_state, year: int, week: int) -> List[Dict[str, Any]]:
        """
        Process all active storylines for the current week.
        Returns list of story beat results.
        """
        results = []
        
        for storyline in self.get_active_storylines():
            if not storyline.triggered_week:
                continue
            
            # Calculate weeks since trigger
            weeks_elapsed = (year - storyline.triggered_year) * 52 + (week - storyline.triggered_week)
            
            # Find beats that should execute this week
            for beat in storyline.beats:
                if beat.beat_id not in storyline.completed_beats and beat.week_offset == weeks_elapsed:
                    # Execute the beat
                    beat_result = storyline.execute_beat(beat, universe_state)
                    beat_result['storyline_name'] = storyline.name
                    results.append(beat_result)
                    
                    # Check if storyline completed
                    if storyline.status == StorylineStatus.COMPLETED:
                        self.completed_storylines.append(storyline)
        
        # Remove completed storylines from active list
        self.storylines = [s for s in self.storylines if s.status != StorylineStatus.COMPLETED]
        
        return results
    
    def get_storyline_by_id(self, storyline_id: str) -> Optional[Storyline]:
        """Get a specific storyline by ID"""
        for storyline in self.storylines + self.completed_storylines:
            if storyline.storyline_id == storyline_id:
                return storyline
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize all storylines"""
        return {
            'active_storylines': [s.to_dict() for s in self.storylines],
            'completed_storylines': [s.to_dict() for s in self.completed_storylines]
        }
    
    def load_from_dict(self, data: Dict[str, Any]):
        """Load storylines from dictionary"""
        self.storylines = []
        self.completed_storylines = []
        
        for storyline_data in data.get('active_storylines', []):
            self.storylines.append(Storyline.from_dict(storyline_data))
        
        for storyline_data in data.get('completed_storylines', []):
            self.completed_storylines.append(Storyline.from_dict(storyline_data))