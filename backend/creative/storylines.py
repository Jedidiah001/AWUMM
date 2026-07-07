"""
Storyline Engine
Manages scripted storylines that trigger throughout the year.
These add narrative structure and memorable moments to the universe.
"""

import json
import os
from typing import List, Dict, Any, Optional
from models.storyline import Storyline, StorylineManager, StorylineStatus, StorylineBeat
from models.segment import SegmentTemplate, SegmentType, SegmentTone


class StorylineEngine:
    """
    Main engine for managing scripted storylines.
    Loads storylines from JSON, checks triggers, and executes beats.
    """
    
    def __init__(self):
        self.manager = StorylineManager()
        self.loaded = False
    
    def load_storylines(self, filepath: str):
        """Load storylines from JSON file"""
        if not os.path.exists(filepath):
            print(f"⚠️ Storylines file not found: {filepath}")
            return
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            for storyline_data in data.get('storylines', []):
                storyline = Storyline.from_dict(storyline_data)
                self.manager.add_storyline(storyline)
            
            self.loaded = True
            print(f"📚 Loaded {len(self.manager.storylines)} scripted storylines")
            
        except Exception as e:
            print(f"❌ Error loading storylines: {e}")
    
    def check_and_trigger_storylines(self, universe_state, year: int, week: int) -> List[Storyline]:
        """
        Check all storylines for trigger conditions.
        Returns newly triggered storylines.
        """
        if not self.loaded:
            return []
        
        triggered = self.manager.check_triggers(universe_state, year, week)
        
        for storyline in triggered:
            print(f"\n🎭 STORYLINE TRIGGERED: {storyline.name}")
            print(f"   Type: {storyline.storyline_type.value}")
            print(f"   Description: {storyline.description}")
            
            # Log cast
            for role, wrestler_id in storyline.cast_assignments.items():
                wrestler = universe_state.get_wrestler_by_id(wrestler_id)
                if wrestler:
                    print(f"   {role}: {wrestler.name}")
        
        return triggered
    
    def process_current_week(self, universe_state, year: int, week: int) -> List[Dict[str, Any]]:
        """
        Process all active storylines for the current week.
        Returns story beat results.
        """
        if not self.loaded:
            return []
        
        results = self.manager.process_week(universe_state, year, week)
        
        for result in results:
            print(f"\n📖 STORY BEAT: {result['storyline_name']}")
            print(f"   {result['description']}")
            for effect in result.get('effects', []):
                print(f"   → {effect}")
        
        return results
    
    def get_active_storylines(self) -> List[Storyline]:
        """Get all currently active storylines"""
        return self.manager.get_active_storylines()
    
    def get_storyline_segments_for_show(
        self,
        show_type: str,
        brand: str,
        universe_state
    ) -> List[SegmentTemplate]:
        """
        Generate segments for storylines that need them this week.
        Called during show generation.
        """
        segments = []
        
        active_storylines = self.get_active_storylines()
        
        for storyline in active_storylines:
            if not storyline.triggered_week:
                continue
            
            # Calculate weeks elapsed
            weeks_elapsed = (universe_state.current_year - storyline.triggered_year) * 52 + \
                          (universe_state.current_week - storyline.triggered_week)
            
            # Find beats for this week
            for beat in storyline.beats:
                if beat.beat_id not in storyline.completed_beats and beat.week_offset == weeks_elapsed:
                    # Check if this beat should create a segment
                    segment = self._create_segment_from_beat(
                        beat,
                        storyline,
                        brand,
                        universe_state
                    )
                    if segment:
                        segments.append(segment)
        
        return segments
    
    def _create_segment_from_beat(
        self,
        beat: StorylineBeat,
        storyline: Storyline,
        brand: str,
        universe_state
    ) -> Optional[SegmentTemplate]:
        """Create a segment template from a story beat"""
        
        # Resolve participants
        actual_participants = []
        participant_names = []
        
        for participant in beat.participants:
            if participant in storyline.cast_assignments:
                wrestler_id = storyline.cast_assignments[participant]
            else:
                wrestler_id = participant
            
            wrestler = universe_state.get_wrestler_by_id(wrestler_id)
            if wrestler:
                # Check if wrestler is on the right brand (or if it's a cross-brand show)
                if brand == 'Cross-Brand' or wrestler.primary_brand == brand:
                    actual_participants.append({
                        'wrestler_id': wrestler.id,
                        'wrestler_name': wrestler.name,
                        'role': 'speaker' if beat.segment_type == 'promo' else 'participant',
                        'mic_skill': wrestler.mic
                    })
                    participant_names.append(wrestler.name)
        
        if not actual_participants:
            return None
        
        # Create segment based on type
        if beat.segment_type == 'promo':
            if len(actual_participants) >= 1:
                speaker = actual_participants[0]
                return SegmentTemplate.create_promo(
                    speaker_id=speaker['wrestler_id'],
                    speaker_name=speaker['wrestler_name'],
                    mic_skill=speaker['mic_skill'],
                    tone=SegmentTone.INTENSE
                )
        
        elif beat.segment_type == 'attack':
            if len(actual_participants) >= 2:
                return SegmentTemplate.create_attack(
                    attacker_id=actual_participants[0]['wrestler_id'],
                    attacker_name=actual_participants[0]['wrestler_name'],
                    victim_id=actual_participants[1]['wrestler_id'],
                    victim_name=actual_participants[1]['wrestler_name'],
                    location='backstage'
                )
        
        elif beat.segment_type == 'confrontation':
            if len(actual_participants) >= 2:
                return SegmentTemplate.create_confrontation(
                    wrestler1_id=actual_participants[0]['wrestler_id'],
                    wrestler1_name=actual_participants[0]['wrestler_name'],
                    wrestler2_id=actual_participants[1]['wrestler_id'],
                    wrestler2_name=actual_participants[1]['wrestler_name'],
                    ends_in_brawl=True
                )
        
        elif beat.segment_type == 'reveal':
            # Create a special promo for reveals
            if len(actual_participants) >= 1:
                speaker = actual_participants[0]
                segment = SegmentTemplate.create_promo(
                    speaker_id=speaker['wrestler_id'],
                    speaker_name=speaker['wrestler_name'],
                    mic_skill=speaker['mic_skill'],
                    tone=SegmentTone.THREATENING
                )
                segment.is_opening = True  # Reveals often open shows
                return segment
        
        elif beat.segment_type == 'announcement':
            # Authority figure announcement
            if len(actual_participants) >= 1:
                return SegmentTemplate.create_announcement(
                    authority_name="General Manager",
                    announcement_type="match",
                    participants=actual_participants
                )
        
        return None
    
    def get_storyline_status_report(self) -> Dict[str, Any]:
        """Get a status report of all storylines"""
        return {
            'total_storylines': len(self.manager.storylines) + len(self.manager.completed_storylines),
            'pending': len([s for s in self.manager.storylines if s.status == StorylineStatus.PENDING]),
            'active': len(self.manager.get_active_storylines()),
            'completed': len(self.manager.completed_storylines),
            'storylines': [
                {
                    'id': s.storyline_id,
                    'name': s.name,
                    'type': s.storyline_type.value,
                    'status': s.status.value,
                    'triggered_week': s.triggered_week,
                    'cast': s.cast_assignments,
                    'completed_beats': len(s.completed_beats),
                    'total_beats': len(s.beats)
                }
                for s in self.manager.storylines + self.manager.completed_storylines
            ]
        }
    
    def save_state(self) -> Dict[str, Any]:
        """Save storyline state for persistence"""
        return self.manager.to_dict()
    
    def load_state(self, data: Dict[str, Any]):
        """Load storyline state from saved data"""
        self.manager.load_from_dict(data)
        self.loaded = True


# Global storyline engine instance
storyline_engine = StorylineEngine()