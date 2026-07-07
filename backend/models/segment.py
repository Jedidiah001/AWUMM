"""
Segment Models
Defines non-match show content: promos, interviews, attacks, celebrations, etc.

Segments add variety to shows and build storylines between matches.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import uuid


class SegmentType(Enum):
    """Types of non-match segments"""
    
    # Talking Segments
    PROMO = "promo"                      # Solo promo/speech
    PROMO_BATTLE = "promo_battle"        # Two+ wrestlers verbal confrontation
    INTERVIEW = "interview"               # Interviewer + wrestler
    ANNOUNCEMENT = "announcement"         # Authority figure announcement
    
    # Action Segments
    BACKSTAGE_ATTACK = "backstage_attack" # Surprise attack backstage
    IN_RING_ATTACK = "in_ring_attack"     # Attack in the ring
    RUN_IN = "run_in"                     # Interruption during/after match
    BRAWL = "brawl"                       # Multi-person fight
    
    # Celebration/Ceremony
    CELEBRATION = "celebration"           # Title celebration, victory lap
    CONTRACT_SIGNING = "contract_signing" # Match contract signing
    CHAMPIONSHIP_PRESENTATION = "championship_presentation"
    AWARD_CEREMONY = "award_ceremony"
    
    # Story Segments
    VIGNETTE = "vignette"                 # Pre-taped character piece
    CONFRONTATION = "confrontation"       # Face-to-face staredown
    ALLIANCE_FORMED = "alliance_formed"   # New team/faction announcement
    BETRAYAL = "betrayal"                 # Shocking turn
    RETURN = "return"                     # Surprise return
    DEBUT = "debut"                       # New wrestler debut


class SegmentTone(Enum):
    """Tone/mood of the segment"""
    INTENSE = "intense"           # Angry, aggressive
    COMEDIC = "comedic"           # Funny, lighthearted
    EMOTIONAL = "emotional"       # Sad, touching
    DRAMATIC = "dramatic"         # Serious, high-stakes
    SHOCKING = "shocking"         # Surprise, twist
    CELEBRATORY = "celebratory"   # Happy, triumphant
    THREATENING = "threatening"   # Intimidating


class SegmentLocation(Enum):
    """Where the segment takes place"""
    IN_RING = "in_ring"
    BACKSTAGE = "backstage"
    INTERVIEW_AREA = "interview_area"
    PARKING_LOT = "parking_lot"
    LOCKER_ROOM = "locker_room"
    OFFICE = "office"             # GM/Authority office
    ENTRANCE_RAMP = "entrance_ramp"
    PRE_TAPED = "pre_taped"       # Vignette, not live


@dataclass
class SegmentParticipant:
    """A participant in a segment"""
    wrestler_id: str
    wrestler_name: str
    role: str  # 'speaker', 'target', 'interviewer', 'attacker', 'victim', etc.
    mic_skill: int = 50  # For promo quality calculation
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'wrestler_id': self.wrestler_id,
            'wrestler_name': self.wrestler_name,
            'role': self.role,
            'mic_skill': self.mic_skill
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'SegmentParticipant':
        return SegmentParticipant(
            wrestler_id=data['wrestler_id'],
            wrestler_name=data['wrestler_name'],
            role=data['role'],
            mic_skill=data.get('mic_skill', 50)
        )


@dataclass
class SegmentTemplate:
    """
    Pre-simulation segment definition.
    Created by AI Creative Director or manual booking.
    """
    segment_id: str
    segment_type: SegmentType
    
    # Participants
    participants: List[SegmentParticipant] = field(default_factory=list)
    
    # Context
    location: SegmentLocation = SegmentLocation.IN_RING
    tone: SegmentTone = SegmentTone.DRAMATIC
    
    # Storyline connections
    feud_id: Optional[str] = None
    title_id: Optional[str] = None
    
    # Booking
    duration_minutes: int = 5
    card_position: int = 1  # Where in the show (between matches)
    is_opening: bool = False  # Opens the show
    is_closing: bool = False  # Closes the show
    
    # Optional scripted content
    scripted_outcome: Optional[str] = None  # 'attack', 'handshake', 'brawl', etc.
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'segment_id': self.segment_id,
            'segment_type': self.segment_type.value,
            'participants': [p.to_dict() for p in self.participants],
            'location': self.location.value,
            'tone': self.tone.value,
            'feud_id': self.feud_id,
            'title_id': self.title_id,
            'duration_minutes': self.duration_minutes,
            'card_position': self.card_position,
            'is_opening': self.is_opening,
            'is_closing': self.is_closing,
            'scripted_outcome': self.scripted_outcome
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'SegmentTemplate':
        return SegmentTemplate(
            segment_id=data['segment_id'],
            segment_type=SegmentType(data['segment_type']),
            participants=[SegmentParticipant.from_dict(p) for p in data.get('participants', [])],
            location=SegmentLocation(data.get('location', 'in_ring')),
            tone=SegmentTone(data.get('tone', 'dramatic')),
            feud_id=data.get('feud_id'),
            title_id=data.get('title_id'),
            duration_minutes=data.get('duration_minutes', 5),
            card_position=data.get('card_position', 1),
            is_opening=data.get('is_opening', False),
            is_closing=data.get('is_closing', False),
            scripted_outcome=data.get('scripted_outcome')
        )
    
    # ========================================================================
    # FACTORY METHODS for common segment types
    # ========================================================================
    
    @staticmethod
    def create_promo(
        speaker_id: str,
        speaker_name: str,
        mic_skill: int,
        feud_id: Optional[str] = None,
        tone: SegmentTone = SegmentTone.INTENSE
    ) -> 'SegmentTemplate':
        """Create a solo promo segment"""
        return SegmentTemplate(
            segment_id=f"promo_{speaker_id}_{uuid.uuid4().hex[:8]}",
            segment_type=SegmentType.PROMO,
            participants=[
                SegmentParticipant(
                    wrestler_id=speaker_id,
                    wrestler_name=speaker_name,
                    role='speaker',
                    mic_skill=mic_skill
                )
            ],
            location=SegmentLocation.IN_RING,
            tone=tone,
            feud_id=feud_id,
            duration_minutes=5
        )
    
    @staticmethod
    def create_promo_battle(
        participants: List[tuple],  # [(id, name, mic_skill), ...]
        feud_id: Optional[str] = None
    ) -> 'SegmentTemplate':
        """Create a promo battle/verbal confrontation"""
        segment_participants = [
            SegmentParticipant(
                wrestler_id=p[0],
                wrestler_name=p[1],
                role='speaker',
                mic_skill=p[2]
            )
            for p in participants
        ]
        
        return SegmentTemplate(
            segment_id=f"promo_battle_{uuid.uuid4().hex[:8]}",
            segment_type=SegmentType.PROMO_BATTLE,
            participants=segment_participants,
            location=SegmentLocation.IN_RING,
            tone=SegmentTone.INTENSE,
            feud_id=feud_id,
            duration_minutes=8
        )
    
    @staticmethod
    def create_interview(
        interviewer_name: str,
        subject_id: str,
        subject_name: str,
        mic_skill: int,
        feud_id: Optional[str] = None
    ) -> 'SegmentTemplate':
        """Create an interview segment"""
        return SegmentTemplate(
            segment_id=f"interview_{subject_id}_{uuid.uuid4().hex[:8]}",
            segment_type=SegmentType.INTERVIEW,
            participants=[
                SegmentParticipant(
                    wrestler_id='interviewer',
                    wrestler_name=interviewer_name,
                    role='interviewer',
                    mic_skill=70  # Interviewers are professionals
                ),
                SegmentParticipant(
                    wrestler_id=subject_id,
                    wrestler_name=subject_name,
                    role='subject',
                    mic_skill=mic_skill
                )
            ],
            location=SegmentLocation.INTERVIEW_AREA,
            tone=SegmentTone.DRAMATIC,
            feud_id=feud_id,
            duration_minutes=4
        )
    
    @staticmethod
    def create_attack(
        attacker_id: str,
        attacker_name: str,
        victim_id: str,
        victim_name: str,
        location: str = 'backstage'
    ) -> 'SegmentTemplate':
        """Create a backstage or in-ring attack"""
        seg_type = SegmentType.BACKSTAGE_ATTACK if location == 'backstage' else SegmentType.IN_RING_ATTACK
        seg_location = SegmentLocation.BACKSTAGE if location == 'backstage' else SegmentLocation.IN_RING
        
        return SegmentTemplate(
            segment_id=f"attack_{attacker_id}_{victim_id}_{uuid.uuid4().hex[:8]}",
            segment_type=seg_type,
            participants=[
                SegmentParticipant(
                    wrestler_id=attacker_id,
                    wrestler_name=attacker_name,
                    role='attacker',
                    mic_skill=50
                ),
                SegmentParticipant(
                    wrestler_id=victim_id,
                    wrestler_name=victim_name,
                    role='victim',
                    mic_skill=50
                )
            ],
            location=seg_location,
            tone=SegmentTone.SHOCKING,
            duration_minutes=3,
            scripted_outcome='attack'
        )
    
    @staticmethod
    def create_confrontation(
        wrestler1_id: str,
        wrestler1_name: str,
        wrestler2_id: str,
        wrestler2_name: str,
        feud_id: Optional[str] = None,
        ends_in_brawl: bool = False
    ) -> 'SegmentTemplate':
        """Create a face-to-face confrontation"""
        return SegmentTemplate(
            segment_id=f"confrontation_{uuid.uuid4().hex[:8]}",
            segment_type=SegmentType.CONFRONTATION,
            participants=[
                SegmentParticipant(
                    wrestler_id=wrestler1_id,
                    wrestler_name=wrestler1_name,
                    role='confronter',
                    mic_skill=50
                ),
                SegmentParticipant(
                    wrestler_id=wrestler2_id,
                    wrestler_name=wrestler2_name,
                    role='confronted',
                    mic_skill=50
                )
            ],
            location=SegmentLocation.IN_RING,
            tone=SegmentTone.INTENSE,
            feud_id=feud_id,
            duration_minutes=6,
            scripted_outcome='brawl' if ends_in_brawl else 'staredown'
        )
    
    @staticmethod
    def create_celebration(
        champion_id: str,
        champion_name: str,
        title_name: str,
        title_id: str
    ) -> 'SegmentTemplate':
        """Create a championship celebration"""
        return SegmentTemplate(
            segment_id=f"celebration_{champion_id}_{uuid.uuid4().hex[:8]}",
            segment_type=SegmentType.CELEBRATION,
            participants=[
                SegmentParticipant(
                    wrestler_id=champion_id,
                    wrestler_name=champion_name,
                    role='champion',
                    mic_skill=50
                )
            ],
            location=SegmentLocation.IN_RING,
            tone=SegmentTone.CELEBRATORY,
            title_id=title_id,
            duration_minutes=5
        )
    
    @staticmethod
    def create_contract_signing(
        wrestler1_id: str,
        wrestler1_name: str,
        wrestler2_id: str,
        wrestler2_name: str,
        match_stipulation: str,
        authority_name: str = "General Manager"
    ) -> 'SegmentTemplate':
        """Create a contract signing segment"""
        return SegmentTemplate(
            segment_id=f"contract_signing_{uuid.uuid4().hex[:8]}",
            segment_type=SegmentType.CONTRACT_SIGNING,
            participants=[
                SegmentParticipant(
                    wrestler_id='authority',
                    wrestler_name=authority_name,
                    role='authority',
                    mic_skill=75
                ),
                SegmentParticipant(
                    wrestler_id=wrestler1_id,
                    wrestler_name=wrestler1_name,
                    role='signee',
                    mic_skill=50
                ),
                SegmentParticipant(
                    wrestler_id=wrestler2_id,
                    wrestler_name=wrestler2_name,
                    role='signee',
                    mic_skill=50
                )
            ],
            location=SegmentLocation.IN_RING,
            tone=SegmentTone.DRAMATIC,
            duration_minutes=10,
            scripted_outcome='table_flip'  # Contract signings always end in chaos
        )
    
    @staticmethod
    def create_return(
        returning_id: str,
        returning_name: str,
        interrupted_id: Optional[str] = None,
        interrupted_name: Optional[str] = None
    ) -> 'SegmentTemplate':
        """Create a surprise return segment"""
        participants = [
            SegmentParticipant(
                wrestler_id=returning_id,
                wrestler_name=returning_name,
                role='returning',
                mic_skill=50
            )
        ]
        
        if interrupted_id:
            participants.append(SegmentParticipant(
                wrestler_id=interrupted_id,
                wrestler_name=interrupted_name,
                role='interrupted',
                mic_skill=50
            ))
        
        return SegmentTemplate(
            segment_id=f"return_{returning_id}_{uuid.uuid4().hex[:8]}",
            segment_type=SegmentType.RETURN,
            participants=participants,
            location=SegmentLocation.ENTRANCE_RAMP,
            tone=SegmentTone.SHOCKING,
            duration_minutes=5
        )
    
    @staticmethod
    def create_betrayal(
        betrayer_id: str,
        betrayer_name: str,
        victim_id: str,
        victim_name: str
    ) -> 'SegmentTemplate':
        """Create a shocking betrayal segment"""
        return SegmentTemplate(
            segment_id=f"betrayal_{betrayer_id}_{uuid.uuid4().hex[:8]}",
            segment_type=SegmentType.BETRAYAL,
            participants=[
                SegmentParticipant(
                    wrestler_id=betrayer_id,
                    wrestler_name=betrayer_name,
                    role='betrayer',
                    mic_skill=50
                ),
                SegmentParticipant(
                    wrestler_id=victim_id,
                    wrestler_name=victim_name,
                    role='victim',
                    mic_skill=50
                )
            ],
            location=SegmentLocation.IN_RING,
            tone=SegmentTone.SHOCKING,
            duration_minutes=4,
            scripted_outcome='attack'
        )


@dataclass
class SegmentHighlight:
    """A notable moment during a segment"""
    timestamp: str
    description: str
    highlight_type: str  # 'quote', 'action', 'reaction', 'interruption'
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp,
            'description': self.description,
            'highlight_type': self.highlight_type
        }


@dataclass
class SegmentResult:
    """
    Post-simulation segment result.
    Contains quality ratings and narrative details.
    """
    segment_id: str
    segment_type: SegmentType
    
    # Participants
    participants: List[SegmentParticipant] = field(default_factory=list)
    
    # Quality
    quality_rating: float = 3.0  # 0.0 - 5.0 stars (like matches)
    crowd_reaction: str = "mixed"  # 'huge_pop', 'good_pop', 'mixed', 'mild_heat', 'nuclear_heat', 'silence'
    crowd_energy_change: int = 0  # How much this affected crowd energy
    
    # Outcome
    outcome: str = ""  # 'promo_success', 'attack_landed', 'brawl_erupted', etc.
    winner_id: Optional[str] = None  # For promo battles
    winner_name: Optional[str] = None
    
    # Narrative
    highlights: List[SegmentHighlight] = field(default_factory=list)
    segment_summary: str = ""
    
    # Post-segment effects
    momentum_changes: Dict[str, int] = field(default_factory=dict)  # wrestler_id -> change
    popularity_changes: Dict[str, int] = field(default_factory=dict)
    feud_intensity_change: int = 0
    injury_caused: Optional[Dict[str, Any]] = None  # If attack caused injury
    
    # Metadata
    duration_minutes: int = 5
    location: str = "in_ring"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'segment_id': self.segment_id,
            'segment_type': self.segment_type.value,
            'participants': [p.to_dict() for p in self.participants],
            'quality_rating': self.quality_rating,
            'crowd_reaction': self.crowd_reaction,
            'crowd_energy_change': self.crowd_energy_change,
            'outcome': self.outcome,
            'winner_id': self.winner_id,
            'winner_name': self.winner_name,
            'highlights': [h.to_dict() for h in self.highlights],
            'segment_summary': self.segment_summary,
            'momentum_changes': self.momentum_changes,
            'popularity_changes': self.popularity_changes,
            'feud_intensity_change': self.feud_intensity_change,
            'injury_caused': self.injury_caused,
            'duration_minutes': self.duration_minutes,
            'location': self.location
        }