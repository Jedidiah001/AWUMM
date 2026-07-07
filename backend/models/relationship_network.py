"""
Locker-room relationship graph.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


RELATIONSHIP_FRIENDSHIP = "friendship"
RELATIONSHIP_HEAT = "heat"
RELATIONSHIP_MENTORSHIP = "mentorship"
RELATIONSHIP_ROMANTIC = "romantic"
RELATIONSHIP_MANAGER_CLIENT = "manager_client"


@dataclass
class LockerRoomRelationship:
    """Relationship edge between two roster members."""

    relationship_id: str
    wrestler_a_id: str
    wrestler_a_name: str
    wrestler_b_id: str
    wrestler_b_name: str
    relationship_type: str
    strength: int = 50
    metadata: Dict[str, Any] = field(default_factory=dict)
    history: List[str] = field(default_factory=list)
    is_active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def involves(self, wrestler_id: str) -> bool:
        return wrestler_id in {self.wrestler_a_id, self.wrestler_b_id}

    def other_party_id(self, wrestler_id: str) -> Optional[str]:
        if wrestler_id == self.wrestler_a_id:
            return self.wrestler_b_id
        if wrestler_id == self.wrestler_b_id:
            return self.wrestler_a_id
        return None

    def adjust_strength(self, delta: int, note: Optional[str] = None):
        self.strength = max(0, min(100, self.strength + delta))
        if note:
            self.history.append(note)
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'relationship_id': self.relationship_id,
            'wrestler_a_id': self.wrestler_a_id,
            'wrestler_a_name': self.wrestler_a_name,
            'wrestler_b_id': self.wrestler_b_id,
            'wrestler_b_name': self.wrestler_b_name,
            'relationship_type': self.relationship_type,
            'strength': self.strength,
            'metadata': self.metadata,
            'history': self.history,
            'is_active': self.is_active,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "LockerRoomRelationship":
        return LockerRoomRelationship(
            relationship_id=data['relationship_id'],
            wrestler_a_id=data['wrestler_a_id'],
            wrestler_a_name=data.get('wrestler_a_name', data['wrestler_a_id']),
            wrestler_b_id=data['wrestler_b_id'],
            wrestler_b_name=data.get('wrestler_b_name', data['wrestler_b_id']),
            relationship_type=data['relationship_type'],
            strength=data.get('strength', 50),
            metadata=data.get('metadata', {}),
            history=data.get('history', []),
            is_active=data.get('is_active', True),
            created_at=data.get('created_at', datetime.now().isoformat()),
            updated_at=data.get('updated_at', datetime.now().isoformat()),
        )


class RelationshipNetwork:
    """Simple relationship manager with helper methods for simulation hooks."""

    def __init__(self):
        self.relationships: List[LockerRoomRelationship] = []
        self._next_relationship_id = 1

    def _normalize_pair(self, wrestler_a_id: str, wrestler_a_name: str, wrestler_b_id: str, wrestler_b_name: str):
        if wrestler_a_id <= wrestler_b_id:
            return wrestler_a_id, wrestler_a_name, wrestler_b_id, wrestler_b_name
        return wrestler_b_id, wrestler_b_name, wrestler_a_id, wrestler_a_name

    def create_or_update_relationship(
        self,
        wrestler_a_id: str,
        wrestler_a_name: str,
        wrestler_b_id: str,
        wrestler_b_name: str,
        relationship_type: str,
        strength_delta: int = 0,
        base_strength: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        note: Optional[str] = None,
    ) -> LockerRoomRelationship:
        wrestler_a_id, wrestler_a_name, wrestler_b_id, wrestler_b_name = self._normalize_pair(
            wrestler_a_id, wrestler_a_name, wrestler_b_id, wrestler_b_name
        )

        existing = self.get_relationship(wrestler_a_id, wrestler_b_id, relationship_type)
        if existing:
            existing.metadata.update(metadata or {})
            if base_strength is not None and existing.strength == 50 and strength_delta == 0:
                existing.strength = base_strength
            existing.adjust_strength(strength_delta, note)
            return existing

        relationship = LockerRoomRelationship(
            relationship_id=f"rel_{self._next_relationship_id:04d}",
            wrestler_a_id=wrestler_a_id,
            wrestler_a_name=wrestler_a_name,
            wrestler_b_id=wrestler_b_id,
            wrestler_b_name=wrestler_b_name,
            relationship_type=relationship_type,
            strength=base_strength if base_strength is not None else max(0, min(100, 50 + strength_delta)),
            metadata=metadata or {},
            history=[note] if note else [],
        )
        self.relationships.append(relationship)
        self._next_relationship_id += 1
        return relationship

    def get_relationship(self, wrestler_a_id: str, wrestler_b_id: str, relationship_type: str) -> Optional[LockerRoomRelationship]:
        wrestler_a_id, _, wrestler_b_id, _ = self._normalize_pair(wrestler_a_id, wrestler_a_id, wrestler_b_id, wrestler_b_id)
        return next((
            rel for rel in self.relationships
            if rel.is_active
            and rel.relationship_type == relationship_type
            and rel.wrestler_a_id == wrestler_a_id
            and rel.wrestler_b_id == wrestler_b_id
        ), None)

    def get_relationship_by_id(self, relationship_id: str) -> Optional[LockerRoomRelationship]:
        return next((rel for rel in self.relationships if rel.relationship_id == relationship_id), None)

    def get_relationships_for_wrestler(self, wrestler_id: str, relationship_type: Optional[str] = None) -> List[LockerRoomRelationship]:
        return [
            rel for rel in self.relationships
            if rel.is_active
            and rel.involves(wrestler_id)
            and (relationship_type is None or rel.relationship_type == relationship_type)
        ]

    def get_manager_bonus(self, wrestler_ids: List[str], context: str = "match") -> float:
        """Translate manager-client relationships into a small match/promo bonus."""
        best_bonus = 0.0
        for wrestler_id in wrestler_ids:
            for rel in self.get_relationships_for_wrestler(wrestler_id, RELATIONSHIP_MANAGER_CLIENT):
                effectiveness = rel.metadata.get('effectiveness', rel.strength)
                fit = rel.metadata.get('fit', 60)
                if context == "promo":
                    bonus = ((effectiveness * 0.6) + (fit * 0.4)) / 1000
                else:
                    bonus = ((effectiveness * 0.5) + (fit * 0.3)) / 1200
                best_bonus = max(best_bonus, round(bonus, 3))
        return best_bonus

    def seed_natural_relationships(self, wrestlers: List[Any], brand: Optional[str] = None, max_new_relationships: int = 20) -> List[LockerRoomRelationship]:
        """Auto-create friendships, heat, and mentor links from roster traits."""
        seeded: List[LockerRoomRelationship] = []
        pool = [w for w in wrestlers if not brand or getattr(w, 'primary_brand', None) == brand]

        for idx, wrestler_a in enumerate(pool):
            for wrestler_b in pool[idx + 1:]:
                if len(seeded) >= max_new_relationships:
                    return seeded

                if wrestler_a.alignment == wrestler_b.alignment and abs(wrestler_a.age - wrestler_b.age) <= 6:
                    seeded.append(self.create_or_update_relationship(
                        wrestler_a.id, wrestler_a.name,
                        wrestler_b.id, wrestler_b.name,
                        RELATIONSHIP_FRIENDSHIP,
                        base_strength=62,
                        note="Backstage friendship formed from similar alignment and shared locker-room circles."
                    ))

                if wrestler_a.alignment != wrestler_b.alignment and abs(wrestler_a.popularity - wrestler_b.popularity) <= 12:
                    seeded.append(self.create_or_update_relationship(
                        wrestler_a.id, wrestler_a.name,
                        wrestler_b.id, wrestler_b.name,
                        RELATIONSHIP_HEAT,
                        base_strength=55,
                        note="Competitive backstage heat simmering between similarly-positioned rivals."
                    ))

                veteran = wrestler_a if wrestler_a.years_experience >= wrestler_b.years_experience else wrestler_b
                younger = wrestler_b if veteran is wrestler_a else wrestler_a
                if veteran.years_experience - younger.years_experience >= 7 and younger.age <= 30:
                    seeded.append(self.create_or_update_relationship(
                        veteran.id, veteran.name,
                        younger.id, younger.name,
                        RELATIONSHIP_MENTORSHIP,
                        base_strength=60,
                        metadata={'mentor_id': veteran.id, 'protege_id': younger.id},
                        note="Veteran/protege relationship formed through shared travel and ring guidance."
                    ))

        return seeded[:max_new_relationships]
