"""
Championship Management Service
STEP 22: Comprehensive championship lifecycle management

Handles:
- Unification (merge two+ titles)
- Splitting (one title becomes two)
- Restart/Reboot (same name, new lineage)
- Deactivation (inactive but not retired)
- Transfer (brand/division changes)
- Brand exclusivity enforcement
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json


class ChampionshipStatus(Enum):
    """Championship lifecycle status"""
    ACTIVE = "active"
    INACTIVE = "inactive"  # Not defended, but not retired
    RETIRED = "retired"    # Officially ended
    UNIFIED = "unified"    # Merged into another title
    SPLIT = "split"        # Split into multiple titles


class UnificationType(Enum):
    """How titles are unified"""
    UNDISPUTED = "undisputed"      # Both lineages continue as one
    ABSORBED = "absorbed"          # One title absorbed into another
    NEW_TITLE = "new_title"        # Both retired, new title created


class TransferType(Enum):
    """Types of championship transfers"""
    BRAND_CHANGE = "brand_change"
    DIVISION_CHANGE = "division_change"
    PROMOTION_LOAN = "promotion_loan"
    BRAND_EXCLUSIVE_TOGGLE = "brand_exclusive_toggle"


@dataclass
class UnificationRecord:
    """Record of a title unification"""
    unification_id: str
    primary_title_id: str
    primary_title_name: str
    secondary_title_id: str
    secondary_title_name: str
    resulting_title_id: str
    resulting_title_name: str
    unification_type: UnificationType
    unified_by_wrestler_id: str
    unified_by_wrestler_name: str
    year: int
    week: int
    show_id: str
    show_name: str
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'unification_id': self.unification_id,
            'primary_title_id': self.primary_title_id,
            'primary_title_name': self.primary_title_name,
            'secondary_title_id': self.secondary_title_id,
            'secondary_title_name': self.secondary_title_name,
            'resulting_title_id': self.resulting_title_id,
            'resulting_title_name': self.resulting_title_name,
            'unification_type': self.unification_type.value,
            'unified_by_wrestler_id': self.unified_by_wrestler_id,
            'unified_by_wrestler_name': self.unified_by_wrestler_name,
            'year': self.year,
            'week': self.week,
            'show_id': self.show_id,
            'show_name': self.show_name,
            'notes': self.notes
        }


@dataclass
class SplitRecord:
    """Record of a title split"""
    split_id: str
    original_title_id: str
    original_title_name: str
    new_title_ids: List[str]
    new_title_names: List[str]
    reason: str  # brand_split, division_split, storyline
    year: int
    week: int
    show_id: str
    show_name: str
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'split_id': self.split_id,
            'original_title_id': self.original_title_id,
            'original_title_name': self.original_title_name,
            'new_title_ids': self.new_title_ids,
            'new_title_names': self.new_title_names,
            'reason': self.reason,
            'year': self.year,
            'week': self.week,
            'show_id': self.show_id,
            'show_name': self.show_name,
            'notes': self.notes
        }


@dataclass
class TransferRecord:
    """Record of a championship transfer"""
    transfer_id: str
    title_id: str
    title_name: str
    transfer_type: TransferType
    from_value: str  # Previous brand/division
    to_value: str    # New brand/division
    year: int
    week: int
    reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'transfer_id': self.transfer_id,
            'title_id': self.title_id,
            'title_name': self.title_name,
            'transfer_type': self.transfer_type.value,
            'from_value': self.from_value,
            'to_value': self.to_value,
            'year': self.year,
            'week': self.week,
            'reason': self.reason
        }


@dataclass
class LineageRecord:
    """Complete lineage tracking for a championship"""
    lineage_id: str
    title_id: str
    title_name: str
    lineage_number: int  # 1 = original, 2+ = reboots
    start_year: int
    start_week: int
    end_year: Optional[int] = None
    end_week: Optional[int] = None
    end_reason: Optional[str] = None  # retired, unified, rebooted
    total_reigns: int = 0
    total_defenses: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'lineage_id': self.lineage_id,
            'title_id': self.title_id,
            'title_name': self.title_name,
            'lineage_number': self.lineage_number,
            'start_year': self.start_year,
            'start_week': self.start_week,
            'end_year': self.end_year,
            'end_week': self.end_week,
            'end_reason': self.end_reason,
            'total_reigns': self.total_reigns,
            'total_defenses': self.total_defenses,
            'is_active': self.end_year is None
        }


class ChampionshipManager:
    """
    Comprehensive championship lifecycle manager.
    Handles all championship operations beyond basic CRUD.
    """
    
    def __init__(self, database):
        self.db = database
        self.unification_history: List[UnificationRecord] = []
        self.split_history: List[SplitRecord] = []
        self.transfer_history: List[TransferRecord] = []
        self.lineages: Dict[str, List[LineageRecord]] = {}  # title_id -> lineages
        
        self._next_unification_id = 1
        self._next_split_id = 1
        self._next_transfer_id = 1
        self._next_lineage_id = 1
    
    # ========================================================================
    # UNIFICATION
    # ========================================================================
    
    def can_unify_titles(
        self,
        title1_id: str,
        title2_id: str,
        championships: List[Any]
    ) -> Tuple[bool, str]:
        """Check if two titles can be unified"""
        
        title1 = next((c for c in championships if c.id == title1_id), None)
        title2 = next((c for c in championships if c.id == title2_id), None)
        
        if not title1 or not title2:
            return False, "One or both championships not found"
        
        if title1_id == title2_id:
            return False, "Cannot unify a title with itself"
        
        # Both must have champions (or one must be vacant for absorption)
        if title1.is_vacant and title2.is_vacant:
            return False, "At least one title must have a champion"
        
        # Check type compatibility
        if title1.title_type != title2.title_type:
            # Allow some cross-type unifications
            allowed_cross = [
                ('World', 'Secondary'),
                ('Secondary', 'World'),
                ('Midcard', 'Secondary'),
                ('Secondary', 'Midcard'),
            ]
            if (title1.title_type, title2.title_type) not in allowed_cross:
                return False, f"Cannot unify {title1.title_type} and {title2.title_type} titles"
        
        return True, "Titles can be unified"
    
    def unify_championships(
        self,
        primary_title_id: str,
        secondary_title_id: str,
        winner_id: str,
        winner_name: str,
        year: int,
        week: int,
        show_id: str,
        show_name: str,
        unification_type: UnificationType,
        resulting_title_name: Optional[str] = None,
        championships: List[Any] = None,
        notes: str = ""
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Unify two championships into one.
        
        Returns:
            (success, result_dict)
        """
        if not championships:
            return False, {'error': 'Championships list required'}
        
        primary = next((c for c in championships if c.id == primary_title_id), None)
        secondary = next((c for c in championships if c.id == secondary_title_id), None)
        
        if not primary or not secondary:
            return False, {'error': 'One or both championships not found'}
        
        # Determine resulting title
        if unification_type == UnificationType.UNDISPUTED:
            # Primary title continues with "Undisputed" prefix
            resulting_title_id = primary_title_id
            resulting_name = resulting_title_name or f"Undisputed {primary.name}"
            
            # Update primary title name
            primary.name = resulting_name
            
            # Mark secondary as unified
            self._mark_title_unified(secondary, primary_title_id, year, week)
            
        elif unification_type == UnificationType.ABSORBED:
            # Secondary absorbed into primary, primary continues unchanged
            resulting_title_id = primary_title_id
            resulting_name = primary.name
            
            # Mark secondary as unified
            self._mark_title_unified(secondary, primary_title_id, year, week)
            
        elif unification_type == UnificationType.NEW_TITLE:
            # Both retired, new title created
            if not resulting_title_name:
                return False, {'error': 'New title name required for NEW_TITLE unification'}
            
            # Create new championship
            from models.championship_factory import ChampionshipFactory
            
            new_id = ChampionshipFactory.generate_championship_id(self.db)
            
            # Use higher prestige of the two
            new_prestige = max(primary.prestige, secondary.prestige)
            
            resulting_title_id = new_id
            resulting_name = resulting_title_name
            
            # Mark both as unified
            self._mark_title_unified(primary, new_id, year, week)
            self._mark_title_unified(secondary, new_id, year, week)
            
            # Return info to create new title
            return True, {
                'requires_new_title': True,
                'new_title_data': {
                    'id': new_id,
                    'name': resulting_name,
                    'assigned_brand': primary.assigned_brand,
                    'title_type': primary.title_type,
                    'prestige': new_prestige
                },
                'primary_title': primary,
                'secondary_title': secondary,
                'winner_id': winner_id,
                'winner_name': winner_name
            }
        
        # Award title to winner
        primary.award_title(
            wrestler_id=winner_id,
            wrestler_name=winner_name,
            show_id=show_id,
            show_name=show_name,
            year=year,
            week=week
        )
        
        # Boost prestige for historic moment
        primary.adjust_prestige(10)
        
        # Record unification
        unification_id = f"unify_{self._next_unification_id}"
        self._next_unification_id += 1
        
        record = UnificationRecord(
            unification_id=unification_id,
            primary_title_id=primary_title_id,
            primary_title_name=primary.name,
            secondary_title_id=secondary_title_id,
            secondary_title_name=secondary.name,
            resulting_title_id=resulting_title_id,
            resulting_title_name=resulting_name,
            unification_type=unification_type,
            unified_by_wrestler_id=winner_id,
            unified_by_wrestler_name=winner_name,
            year=year,
            week=week,
            show_id=show_id,
            show_name=show_name,
            notes=notes
        )
        
        self.unification_history.append(record)
        
        return True, {
            'unification_id': unification_id,
            'resulting_title_id': resulting_title_id,
            'resulting_title_name': resulting_name,
            'primary_title': primary,
            'secondary_title': secondary,
            'message': f'{winner_name} unified the {primary.name} and {secondary.name}!'
        }
    
    def _mark_title_unified(self, championship, unified_into_id: str, year: int, week: int):
        """Mark a championship as unified into another"""
        # End current lineage
        if championship.id in self.lineages:
            for lineage in self.lineages[championship.id]:
                if lineage.end_year is None:
                    lineage.end_year = year
                    lineage.end_week = week
                    lineage.end_reason = f"unified_into_{unified_into_id}"
        
        # Vacate the title
        championship.vacate_title(
            show_id=f"unification_{year}_{week}",
            show_name="Title Unification",
            year=year,
            week=week,
            reason=f"Unified into {unified_into_id}"
        )
    
    # ========================================================================
    # SPLITTING
    # ========================================================================
    
    def split_championship(
        self,
        original_title_id: str,
        new_titles_data: List[Dict[str, Any]],
        year: int,
        week: int,
        show_id: str,
        show_name: str,
        reason: str,
        championships: List[Any],
        notes: str = ""
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Split one championship into multiple titles.
        
        new_titles_data: List of dicts with name, assigned_brand, etc.
        """
        original = next((c for c in championships if c.id == original_title_id), None)
        
        if not original:
            return False, {'error': 'Original championship not found'}
        
        if len(new_titles_data) < 2:
            return False, {'error': 'Split requires at least 2 new titles'}
        
        # End original title's lineage
        if original_title_id in self.lineages:
            for lineage in self.lineages[original_title_id]:
                if lineage.end_year is None:
                    lineage.end_year = year
                    lineage.end_week = week
                    lineage.end_reason = "split"
        
        # Vacate original if held
        if not original.is_vacant:
            original.vacate_title(
                show_id=show_id,
                show_name=show_name,
                year=year,
                week=week,
                reason="Title split"
            )
        
        # Record split
        split_id = f"split_{self._next_split_id}"
        self._next_split_id += 1
        
        new_title_ids = []
        new_title_names = []
        
        for title_data in new_titles_data:
            new_title_ids.append(title_data.get('id', f"new_{len(new_title_ids)}"))
            new_title_names.append(title_data.get('name', 'New Championship'))
        
        record = SplitRecord(
            split_id=split_id,
            original_title_id=original_title_id,
            original_title_name=original.name,
            new_title_ids=new_title_ids,
            new_title_names=new_title_names,
            reason=reason,
            year=year,
            week=week,
            show_id=show_id,
            show_name=show_name,
            notes=notes
        )
        
        self.split_history.append(record)
        
        return True, {
            'split_id': split_id,
            'original_title': original,
            'new_titles_to_create': new_titles_data,
            'message': f'{original.name} has been split into {len(new_titles_data)} new championships!'
        }
    
    # ========================================================================
    # REBOOT/RESTART
    # ========================================================================
    
    def reboot_championship(
        self,
        title_id: str,
        year: int,
        week: int,
        championships: List[Any],
        keep_name: bool = True,
        new_name: Optional[str] = None,
        reset_prestige: bool = False,
        notes: str = ""
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Reboot a championship with a fresh lineage.
        History is preserved but a new lineage begins.
        """
        championship = next((c for c in championships if c.id == title_id), None)
        
        if not championship:
            return False, {'error': 'Championship not found'}
        
        # End current lineage
        current_lineage_num = 1
        if title_id in self.lineages:
            for lineage in self.lineages[title_id]:
                if lineage.end_year is None:
                    lineage.end_year = year
                    lineage.end_week = week
                    lineage.end_reason = "rebooted"
                current_lineage_num = max(current_lineage_num, lineage.lineage_number + 1)
        
        # Create new lineage
        lineage_id = f"lineage_{self._next_lineage_id}"
        self._next_lineage_id += 1
        
        new_lineage = LineageRecord(
            lineage_id=lineage_id,
            title_id=title_id,
            title_name=new_name or championship.name,
            lineage_number=current_lineage_num,
            start_year=year,
            start_week=week
        )
        
        if title_id not in self.lineages:
            self.lineages[title_id] = []
        self.lineages[title_id].append(new_lineage)
        
        # Update championship
        if new_name:
            championship.name = new_name
        
        if reset_prestige:
            # Reset to base prestige for title type
            base_prestige = {
                'World': 80,
                'Secondary': 65,
                'Midcard': 50,
                'Tag Team': 55,
                'Women': 70,
                'Developmental': 40
            }.get(championship.title_type, 50)
            championship.prestige = base_prestige
        
        # Vacate if held
        if not championship.is_vacant:
            championship.vacate_title(
                show_id=f"reboot_{year}_{week}",
                show_name="Championship Reboot",
                year=year,
                week=week,
                reason="Lineage reboot"
            )
        
        return True, {
            'lineage_id': lineage_id,
            'lineage_number': current_lineage_num,
            'championship': championship,
            'message': f'{championship.name} has been rebooted! Beginning lineage #{current_lineage_num}'
        }
    
    # ========================================================================
    # DEACTIVATION
    # ========================================================================
    
    def deactivate_championship(
        self,
        title_id: str,
        year: int,
        week: int,
        championships: List[Any],
        reason: str = "Not currently active"
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Deactivate a championship (inactive but not retired).
        Can be reactivated later without a full reboot.
        """
        championship = next((c for c in championships if c.id == title_id), None)
        
        if not championship:
            return False, {'error': 'Championship not found'}
        
        # Must be vacant to deactivate
        if not championship.is_vacant:
            return False, {'error': 'Championship must be vacated before deactivation'}
        
        # Update extended data
        from persistence.championship_custom_db import save_championship_extended, get_championship_extended
        
        extended = get_championship_extended(self.db, title_id) or {}
        extended['status'] = ChampionshipStatus.INACTIVE.value
        extended['deactivated_year'] = year
        extended['deactivated_week'] = week
        extended['deactivation_reason'] = reason
        
        save_championship_extended(self.db, title_id, extended)
        
        # Log action
        from persistence.championship_custom_db import log_championship_action
        log_championship_action(
            self.db,
            title_id,
            'deactivated',
            year,
            week,
            reason
        )
        
        return True, {
            'title_id': title_id,
            'status': 'inactive',
            'message': f'{championship.name} has been deactivated'
        }
    
    def reactivate_championship(
        self,
        title_id: str,
        year: int,
        week: int,
        championships: List[Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Reactivate an inactive championship"""
        championship = next((c for c in championships if c.id == title_id), None)
        
        if not championship:
            return False, {'error': 'Championship not found'}
        
        from persistence.championship_custom_db import save_championship_extended, get_championship_extended
        
        extended = get_championship_extended(self.db, title_id) or {}
        
        if extended.get('status') != ChampionshipStatus.INACTIVE.value:
            return False, {'error': 'Championship is not inactive'}
        
        extended['status'] = ChampionshipStatus.ACTIVE.value
        extended['reactivated_year'] = year
        extended['reactivated_week'] = week
        extended.pop('deactivated_year', None)
        extended.pop('deactivated_week', None)
        extended.pop('deactivation_reason', None)
        
        save_championship_extended(self.db, title_id, extended)
        
        from persistence.championship_custom_db import log_championship_action
        log_championship_action(
            self.db,
            title_id,
            'reactivated',
            year,
            week,
            'Championship reactivated'
        )
        
        return True, {
            'title_id': title_id,
            'status': 'active',
            'message': f'{championship.name} has been reactivated!'
        }
    
    # ========================================================================
    # TRANSFERS
    # ========================================================================
    
    def transfer_championship(
        self,
        title_id: str,
        transfer_type: TransferType,
        new_value: str,
        year: int,
        week: int,
        championships: List[Any],
        reason: str = ""
    ) -> Tuple[bool, Dict[str, Any]]:
        """Transfer a championship between brands/divisions"""
        championship = next((c for c in championships if c.id == title_id), None)
        
        if not championship:
            return False, {'error': 'Championship not found'}
        
        old_value = ""
        
        if transfer_type == TransferType.BRAND_CHANGE:
            old_value = championship.assigned_brand
            
            # Validate new brand
            valid_brands = ['ROC Alpha', 'ROC Velocity', 'ROC Vanguard', 'Cross-Brand']
            if new_value not in valid_brands:
                return False, {'error': f'Invalid brand. Must be one of: {", ".join(valid_brands)}'}
            
            championship.assigned_brand = new_value
            
        elif transfer_type == TransferType.DIVISION_CHANGE:
            from persistence.championship_custom_db import get_championship_extended, save_championship_extended
            
            extended = get_championship_extended(self.db, title_id) or {}
            old_value = extended.get('division', 'open')
            
            valid_divisions = ['mens', 'womens', 'tag_team', 'open', 'intergender']
            if new_value not in valid_divisions:
                return False, {'error': f'Invalid division. Must be one of: {", ".join(valid_divisions)}'}
            
            extended['division'] = new_value
            save_championship_extended(self.db, title_id, extended)
            
        elif transfer_type == TransferType.BRAND_EXCLUSIVE_TOGGLE:
            from persistence.championship_custom_db import get_championship_extended, save_championship_extended
            
            extended = get_championship_extended(self.db, title_id) or {}
            old_value = str(extended.get('brand_exclusive', False))
            new_value_bool = new_value.lower() == 'true'
            
            extended['brand_exclusive'] = new_value_bool
            save_championship_extended(self.db, title_id, extended)
            new_value = str(new_value_bool)
        
        # Record transfer
        transfer_id = f"transfer_{self._next_transfer_id}"
        self._next_transfer_id += 1
        
        record = TransferRecord(
            transfer_id=transfer_id,
            title_id=title_id,
            title_name=championship.name,
            transfer_type=transfer_type,
            from_value=old_value,
            to_value=new_value,
            year=year,
            week=week,
            reason=reason
        )
        
        self.transfer_history.append(record)
        
        # Log action
        from persistence.championship_custom_db import log_championship_action
        log_championship_action(
            self.db,
            title_id,
            f'transfer_{transfer_type.value}',
            year,
            week,
            f'Transferred from {old_value} to {new_value}. {reason}'
        )
        
        return True, {
            'transfer_id': transfer_id,
            'from': old_value,
            'to': new_value,
            'message': f'{championship.name} transferred: {old_value} → {new_value}'
        }
    
    # ========================================================================
    # LINEAGE MANAGEMENT
    # ========================================================================
    
    def get_championship_lineages(self, title_id: str) -> List[LineageRecord]:
        """Get all lineages for a championship"""
        return self.lineages.get(title_id, [])
    
    def get_current_lineage(self, title_id: str) -> Optional[LineageRecord]:
        """Get the current active lineage for a championship"""
        lineages = self.lineages.get(title_id, [])
        for lineage in lineages:
            if lineage.end_year is None:
                return lineage
        return None
    
    def initialize_lineage(self, title_id: str, title_name: str, year: int, week: int):
        """Initialize lineage tracking for a new championship"""
        lineage_id = f"lineage_{self._next_lineage_id}"
        self._next_lineage_id += 1
        
        lineage = LineageRecord(
            lineage_id=lineage_id,
            title_id=title_id,
            title_name=title_name,
            lineage_number=1,
            start_year=year,
            start_week=week
        )
        
        if title_id not in self.lineages:
            self.lineages[title_id] = []
        self.lineages[title_id].append(lineage)
        
        return lineage
    
    # ========================================================================
    # BRAND EXCLUSIVITY
    # ========================================================================
    
    def check_brand_eligibility(
        self,
        title_id: str,
        wrestler_brand: str,
        championships: List[Any]
    ) -> Tuple[bool, str]:
        """Check if a wrestler's brand allows them to compete for a title"""
        championship = next((c for c in championships if c.id == title_id), None)
        
        if not championship:
            return False, "Championship not found"
        
        # Cross-brand titles are available to all
        if championship.assigned_brand == 'Cross-Brand':
            return True, "Cross-brand championship - all brands eligible"
        
        # Check brand exclusivity
        from persistence.championship_custom_db import get_championship_extended
        extended = get_championship_extended(self.db, title_id) or {}
        
        if extended.get('brand_exclusive', True):
            # Brand-exclusive: must match
            if wrestler_brand != championship.assigned_brand:
                return False, f"This championship is exclusive to {championship.assigned_brand}"
        
        return True, "Wrestler is eligible"
    
    # ========================================================================
    # HISTORY & REPORTING
    # ========================================================================
    
    def get_unification_history(self, title_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get unification history, optionally filtered by title"""
        history = self.unification_history
        
        if title_id:
            history = [
                u for u in history 
                if u.primary_title_id == title_id 
                or u.secondary_title_id == title_id
                or u.resulting_title_id == title_id
            ]
        
        return [u.to_dict() for u in history]
    
    def get_split_history(self, title_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get split history, optionally filtered by title"""
        history = self.split_history
        
        if title_id:
            history = [
                s for s in history 
                if s.original_title_id == title_id 
                or title_id in s.new_title_ids
            ]
        
        return [s.to_dict() for s in history]
    
    def get_transfer_history(self, title_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get transfer history, optionally filtered by title"""
        history = self.transfer_history
        
        if title_id:
            history = [t for t in history if t.title_id == title_id]
        
        return [t.to_dict() for t in history]
    
    def get_full_title_history(self, title_id: str) -> Dict[str, Any]:
        """Get complete history for a championship including all events"""
        return {
            'lineages': [l.to_dict() for l in self.get_championship_lineages(title_id)],
            'unifications': self.get_unification_history(title_id),
            'splits': self.get_split_history(title_id),
            'transfers': self.get_transfer_history(title_id)
        }
    
    # ========================================================================
    # SERIALIZATION
    # ========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize manager state"""
        return {
            'unification_history': [u.to_dict() for u in self.unification_history],
            'split_history': [s.to_dict() for s in self.split_history],
            'transfer_history': [t.to_dict() for t in self.transfer_history],
            'lineages': {
                title_id: [l.to_dict() for l in lineages]
                for title_id, lineages in self.lineages.items()
            },
            '_next_unification_id': self._next_unification_id,
            '_next_split_id': self._next_split_id,
            '_next_transfer_id': self._next_transfer_id,
            '_next_lineage_id': self._next_lineage_id
        }
    
    def load_from_dict(self, data: Dict[str, Any]):
        """Load manager state from dict"""
        # Load unification history
        self.unification_history = []
        for u in data.get('unification_history', []):
            record = UnificationRecord(
                unification_id=u['unification_id'],
                primary_title_id=u['primary_title_id'],
                primary_title_name=u['primary_title_name'],
                secondary_title_id=u['secondary_title_id'],
                secondary_title_name=u['secondary_title_name'],
                resulting_title_id=u['resulting_title_id'],
                resulting_title_name=u['resulting_title_name'],
                unification_type=UnificationType(u['unification_type']),
                unified_by_wrestler_id=u['unified_by_wrestler_id'],
                unified_by_wrestler_name=u['unified_by_wrestler_name'],
                year=u['year'],
                week=u['week'],
                show_id=u['show_id'],
                show_name=u['show_name'],
                notes=u.get('notes', '')
            )
            self.unification_history.append(record)
        
        # Load split history
        self.split_history = []
        for s in data.get('split_history', []):
            record = SplitRecord(
                split_id=s['split_id'],
                original_title_id=s['original_title_id'],
                original_title_name=s['original_title_name'],
                new_title_ids=s['new_title_ids'],
                new_title_names=s['new_title_names'],
                reason=s['reason'],
                year=s['year'],
                week=s['week'],
                show_id=s['show_id'],
                show_name=s['show_name'],
                notes=s.get('notes', '')
            )
            self.split_history.append(record)
        
        # Load transfer history
        self.transfer_history = []
        for t in data.get('transfer_history', []):
            record = TransferRecord(
                transfer_id=t['transfer_id'],
                title_id=t['title_id'],
                title_name=t['title_name'],
                transfer_type=TransferType(t['transfer_type']),
                from_value=t['from_value'],
                to_value=t['to_value'],
                year=t['year'],
                week=t['week'],
                reason=t.get('reason', '')
            )
            self.transfer_history.append(record)
        
        # Load lineages
        self.lineages = {}
        for title_id, lineage_list in data.get('lineages', {}).items():
            self.lineages[title_id] = []
            for l in lineage_list:
                lineage = LineageRecord(
                    lineage_id=l['lineage_id'],
                    title_id=l['title_id'],
                    title_name=l['title_name'],
                    lineage_number=l['lineage_number'],
                    start_year=l['start_year'],
                    start_week=l['start_week'],
                    end_year=l.get('end_year'),
                    end_week=l.get('end_week'),
                    end_reason=l.get('end_reason'),
                    total_reigns=l.get('total_reigns', 0),
                    total_defenses=l.get('total_defenses', 0)
                )
                self.lineages[title_id].append(lineage)
        
        # Load counters
        self._next_unification_id = data.get('_next_unification_id', 1)
        self._next_split_id = data.get('_next_split_id', 1)
        self._next_transfer_id = data.get('_next_transfer_id', 1)
        self._next_lineage_id = data.get('_next_lineage_id', 1)


# Global instance
championship_manager = None


def get_championship_manager(database) -> ChampionshipManager:
    """Get or create the championship manager instance"""
    global championship_manager
    if championship_manager is None:
        championship_manager = ChampionshipManager(database)
    return championship_manager