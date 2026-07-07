"""
Faction and stable models.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Faction:
    """Represents a stable or faction with internal dynamics."""

    faction_id: str
    faction_name: str
    member_ids: List[str]
    member_names: List[str]
    leader_id: str
    leader_name: str
    primary_brand: str
    identity: str = ""
    goals: List[str] = field(default_factory=list)
    hierarchy: List[Dict[str, Any]] = field(default_factory=list)
    dynamics: Dict[str, Dict[str, int]] = field(default_factory=dict)
    entrance_style: str = "standard"
    manager_id: Optional[str] = None
    manager_name: Optional[str] = None
    is_active: bool = True
    is_disbanded: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def _default_member_dynamics(self, wrestler_id: str) -> Dict[str, int]:
        return self.dynamics.get(wrestler_id, {
            'loyalty': 60,
            'jealousy': 20,
            'power': 50,
        })

    def ensure_member_tracking(self):
        """Ensure every member has hierarchy and dynamic tracking."""
        if not self.hierarchy:
            self.hierarchy = [
                {'wrestler_id': wrestler_id, 'wrestler_name': wrestler_name, 'role': 'member', 'rank': idx + 1}
                for idx, (wrestler_id, wrestler_name) in enumerate(zip(self.member_ids, self.member_names))
            ]

        for wrestler_id in self.member_ids:
            self.dynamics.setdefault(wrestler_id, self._default_member_dynamics(wrestler_id))

        for entry in self.hierarchy:
            if entry['wrestler_id'] == self.leader_id:
                entry['role'] = 'leader'
                entry['rank'] = 1

    def add_member(self, wrestler_id: str, wrestler_name: str, role: str = "member"):
        if wrestler_id in self.member_ids:
            return
        self.member_ids.append(wrestler_id)
        self.member_names.append(wrestler_name)
        self.hierarchy.append({
            'wrestler_id': wrestler_id,
            'wrestler_name': wrestler_name,
            'role': role,
            'rank': len(self.hierarchy) + 1,
        })
        self.dynamics[wrestler_id] = self._default_member_dynamics(wrestler_id)
        self.updated_at = datetime.now().isoformat()

    def remove_member(self, wrestler_id: str):
        if wrestler_id not in self.member_ids:
            return
        index = self.member_ids.index(wrestler_id)
        del self.member_ids[index]
        del self.member_names[index]
        self.hierarchy = [entry for entry in self.hierarchy if entry['wrestler_id'] != wrestler_id]
        self.dynamics.pop(wrestler_id, None)
        self._recalculate_hierarchy()
        self.updated_at = datetime.now().isoformat()

    def _recalculate_hierarchy(self):
        for idx, entry in enumerate(sorted(self.hierarchy, key=lambda item: item.get('rank', 999))):
            entry['rank'] = idx + 1
            if entry['wrestler_id'] == self.leader_id:
                entry['rank'] = 1
                entry['role'] = 'leader'
        self.hierarchy.sort(key=lambda item: item.get('rank', 999))

    def update_member_dynamics(self, wrestler_id: str, loyalty_delta: int = 0, jealousy_delta: int = 0, power_delta: int = 0):
        self.ensure_member_tracking()
        metrics = self.dynamics.setdefault(wrestler_id, self._default_member_dynamics(wrestler_id))
        metrics['loyalty'] = max(0, min(100, metrics['loyalty'] + loyalty_delta))
        metrics['jealousy'] = max(0, min(100, metrics['jealousy'] + jealousy_delta))
        metrics['power'] = max(0, min(100, metrics['power'] + power_delta))
        self.updated_at = datetime.now().isoformat()

    def record_member_spotlight(self, wrestler_id: str, success: bool):
        if wrestler_id not in self.member_ids:
            return

        for member_id in self.member_ids:
            if member_id == wrestler_id:
                self.update_member_dynamics(member_id, loyalty_delta=3 if success else -2, jealousy_delta=-1, power_delta=4 if success else -2)
            else:
                self.update_member_dynamics(member_id, loyalty_delta=1 if success else -2, jealousy_delta=2 if success else 1, power_delta=-1 if success else 0)

    def to_dict(self) -> Dict[str, Any]:
        self.ensure_member_tracking()
        return {
            'faction_id': self.faction_id,
            'faction_name': self.faction_name,
            'member_ids': self.member_ids,
            'member_names': self.member_names,
            'leader_id': self.leader_id,
            'leader_name': self.leader_name,
            'primary_brand': self.primary_brand,
            'identity': self.identity,
            'goals': self.goals,
            'hierarchy': self.hierarchy,
            'dynamics': self.dynamics,
            'entrance_style': self.entrance_style,
            'manager_id': self.manager_id,
            'manager_name': self.manager_name,
            'is_active': self.is_active,
            'is_disbanded': self.is_disbanded,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Faction":
        faction = Faction(
            faction_id=data['faction_id'],
            faction_name=data['faction_name'],
            member_ids=data.get('member_ids', []),
            member_names=data.get('member_names', []),
            leader_id=data['leader_id'],
            leader_name=data['leader_name'],
            primary_brand=data['primary_brand'],
            identity=data.get('identity', ''),
            goals=data.get('goals', []),
            hierarchy=data.get('hierarchy', []),
            dynamics=data.get('dynamics', {}),
            entrance_style=data.get('entrance_style', 'standard'),
            manager_id=data.get('manager_id'),
            manager_name=data.get('manager_name'),
            is_active=data.get('is_active', True),
            is_disbanded=data.get('is_disbanded', False),
            created_at=data.get('created_at', datetime.now().isoformat()),
            updated_at=data.get('updated_at', datetime.now().isoformat()),
        )
        faction.ensure_member_tracking()
        return faction


class FactionManager:
    """In-memory manager backed by database persistence in the universe layer."""

    def __init__(self):
        self.factions: List[Faction] = []
        self._next_faction_id = 1

    def create_faction(
        self,
        faction_name: str,
        member_ids: List[str],
        member_names: List[str],
        leader_id: str,
        leader_name: str,
        primary_brand: str,
        identity: str = "",
        goals: Optional[List[str]] = None,
        entrance_style: str = "standard",
        manager_id: Optional[str] = None,
        manager_name: Optional[str] = None,
    ) -> Faction:
        faction = Faction(
            faction_id=f"faction_{self._next_faction_id:03d}",
            faction_name=faction_name,
            member_ids=member_ids,
            member_names=member_names,
            leader_id=leader_id,
            leader_name=leader_name,
            primary_brand=primary_brand,
            identity=identity,
            goals=goals or [],
            entrance_style=entrance_style,
            manager_id=manager_id,
            manager_name=manager_name,
        )
        faction.ensure_member_tracking()
        self.factions.append(faction)
        self._next_faction_id += 1
        return faction

    def get_faction_by_id(self, faction_id: str) -> Optional[Faction]:
        return next((faction for faction in self.factions if faction.faction_id == faction_id), None)

    def get_faction_by_member(self, wrestler_id: str) -> Optional[Faction]:
        return next((faction for faction in self.factions if faction.is_active and wrestler_id in faction.member_ids), None)

    def get_active_factions(self) -> List[Faction]:
        return [faction for faction in self.factions if faction.is_active and not faction.is_disbanded]
