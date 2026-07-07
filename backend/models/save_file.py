"""
Save File Models
Handles save file metadata and universe snapshots.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
import json


@dataclass
class SaveMetadata:
    """Metadata about a save file"""
    save_slot: int
    save_name: str
    created_at: str
    last_modified: str
    
    # Universe state at save time
    current_year: int
    current_week: int
    balance: int
    show_count: int
    
    # Statistics
    total_wrestlers: int
    active_feuds: int
    total_shows_run: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'save_slot': self.save_slot,
            'save_name': self.save_name,
            'created_at': self.created_at,
            'last_modified': self.last_modified,
            'current_year': self.current_year,
            'current_week': self.current_week,
            'balance': self.balance,
            'show_count': self.show_count,
            'total_wrestlers': self.total_wrestlers,
            'active_feuds': self.active_feuds,
            'total_shows_run': self.total_shows_run
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'SaveMetadata':
        return SaveMetadata(
            save_slot=data['save_slot'],
            save_name=data['save_name'],
            created_at=data['created_at'],
            last_modified=data['last_modified'],
            current_year=data['current_year'],
            current_week=data['current_week'],
            balance=data['balance'],
            show_count=data['show_count'],
            total_wrestlers=data['total_wrestlers'],
            active_feuds=data['active_feuds'],
            total_shows_run=data['total_shows_run']
        )


@dataclass
class UniverseSnapshot:
    """
    Complete snapshot of universe state for saving.
    Contains everything needed to restore a game.
    """
    metadata: SaveMetadata
    
    # Game state
    game_state: Dict[str, Any]
    
    # Core data
    wrestlers: List[Dict[str, Any]] = field(default_factory=list)
    championships: List[Dict[str, Any]] = field(default_factory=list)
    feuds: List[Dict[str, Any]] = field(default_factory=list)
    
    # History (optional - can be large)
    match_history: List[Dict[str, Any]] = field(default_factory=list)
    show_history: List[Dict[str, Any]] = field(default_factory=list)
    title_reigns: List[Dict[str, Any]] = field(default_factory=list)
    
    # Stats (optional)
    wrestler_stats: List[Dict[str, Any]] = field(default_factory=list)
    milestones: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'metadata': self.metadata.to_dict(),
            'game_state': self.game_state,
            'wrestlers': self.wrestlers,
            'championships': self.championships,
            'feuds': self.feuds,
            'match_history': self.match_history,
            'show_history': self.show_history,
            'title_reigns': self.title_reigns,
            'wrestler_stats': self.wrestler_stats,
            'milestones': self.milestones
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'UniverseSnapshot':
        return UniverseSnapshot(
            metadata=SaveMetadata.from_dict(data['metadata']),
            game_state=data['game_state'],
            wrestlers=data.get('wrestlers', []),
            championships=data.get('championships', []),
            feuds=data.get('feuds', []),
            match_history=data.get('match_history', []),
            show_history=data.get('show_history', []),
            title_reigns=data.get('title_reigns', []),
            wrestler_stats=data.get('wrestler_stats', []),
            milestones=data.get('milestones', [])
        )