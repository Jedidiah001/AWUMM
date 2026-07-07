"""
Championship Model
Represents a wrestling championship title with history tracking.

STEP 21: Enhanced with hierarchy integration, interim champions, and situation tracking.
STEP 25: Added defense frequency tracking and overdue detection.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class TitleReign:
    """Single title reign record"""
    wrestler_id: str
    wrestler_name: str
    won_at_show_id: Optional[str]
    won_at_show_name: str
    won_date_year: int
    won_date_week: int
    lost_at_show_id: Optional[str] = None
    lost_at_show_name: Optional[str] = None
    lost_date_year: Optional[int] = None
    lost_date_week: Optional[int] = None
    days_held: int = 0  # Calculated when reign ends
    is_interim: bool = False  # STEP 21: Track interim reigns
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'wrestler_id': self.wrestler_id,
            'wrestler_name': self.wrestler_name,
            'won_at_show_id': self.won_at_show_id,
            'won_at_show_name': self.won_at_show_name,
            'won_date_year': self.won_date_year,
            'won_date_week': self.won_date_week,
            'lost_at_show_id': self.lost_at_show_id,
            'lost_at_show_name': self.lost_at_show_name,
            'lost_date_year': self.lost_date_year,
            'lost_date_week': self.lost_date_week,
            'days_held': self.days_held,
            'is_interim': self.is_interim
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'TitleReign':
        return TitleReign(
            wrestler_id=data['wrestler_id'],
            wrestler_name=data['wrestler_name'],
            won_at_show_id=data.get('won_at_show_id'),
            won_at_show_name=data['won_at_show_name'],
            won_date_year=data['won_date_year'],
            won_date_week=data['won_date_week'],
            lost_at_show_id=data.get('lost_at_show_id'),
            lost_at_show_name=data.get('lost_at_show_name'),
            lost_date_year=data.get('lost_date_year'),
            lost_date_week=data.get('lost_date_week'),
            days_held=data.get('days_held', 0),
            is_interim=data.get('is_interim', False)
        )


class Championship:
    """
    Wrestling championship title.
    
    Tracks current holder, prestige, and complete reign history.
    
    STEP 21 ENHANCEMENTS:
    - Interim champion support
    - Last defense tracking
    - Vacancy reason tracking
    - Situation status integration
    
    STEP 25 ENHANCEMENTS:
    - Defense frequency requirements
    - Overdue detection
    - Urgency level calculation
    """
    
    def __init__(
        self,
        title_id: str,
        name: str,
        assigned_brand: str,  # 'ROC Alpha', 'ROC Velocity', 'ROC Vanguard', 'Cross-Brand'
        title_type: str,  # 'World', 'Secondary', 'Midcard', 'Tag Team', 'Women'
        prestige: int = 50,  # 0-100, grows with quality title matches
        current_holder_id: Optional[str] = None,
        current_holder_name: Optional[str] = None
    ):
        self.id = title_id
        self.name = name
        self.assigned_brand = assigned_brand
        self.title_type = title_type
        self.prestige = prestige
        self.current_holder_id = current_holder_id
        self.current_holder_name = current_holder_name
        self.history: List[TitleReign] = []
        
        # STEP 21: New fields
        self.interim_holder_id: Optional[str] = None
        self.interim_holder_name: Optional[str] = None
        self.last_defense_year: Optional[int] = None
        self.last_defense_week: Optional[int] = None
        self.last_defense_show_id: Optional[str] = None
        self.vacancy_reason: Optional[str] = None  # Set when title becomes vacant
        self.total_defenses: int = 0
        
        # STEP 25: Defense frequency tracking
        self.defense_frequency_days: int = 30  # Max days between defenses
        self.min_annual_defenses: int = 12     # Minimum defenses per year
    
    @property
    def is_vacant(self) -> bool:
        """Check if title has no current holder"""
        return self.current_holder_id is None
    
    @property
    def has_interim_champion(self) -> bool:
        """Check if title has an interim champion"""
        return self.interim_holder_id is not None
    
    @property
    def effective_champion_id(self) -> Optional[str]:
        """Get the effective champion (interim if main champion unavailable)"""
        if self.interim_holder_id:
            return self.interim_holder_id
        return self.current_holder_id
    
    @property
    def effective_champion_name(self) -> Optional[str]:
        """Get the effective champion name"""
        if self.interim_holder_name:
            return self.interim_holder_name
        return self.current_holder_name
    
    def get_defense_status(self, current_year: int, current_week: int) -> dict:
        """
        Get detailed defense status for this championship.
        
        STEP 25: Calculate if defense is overdue and urgency level.
        
        Returns:
            dict with keys:
            - days_since_defense: int
            - is_overdue: bool
            - urgency_level: int (0=Normal, 1=Medium, 2=High, 3=CRITICAL)
            - urgency_label: str
            - days_until_required: int
        """
        if not self.last_defense_year or not self.last_defense_week:
            # No defense recorded - check current reign length
            if not self.history or self.is_vacant:
                return {
                    'days_since_defense': 0,
                    'is_overdue': False,
                    'urgency_level': 0,
                    'urgency_label': 'Normal',
                    'days_until_required': self.defense_frequency_days
                }
            
            # Use current reign start
            current_reign = self.history[-1]
            weeks_since = (current_year - current_reign.won_date_year) * 52 + (current_week - current_reign.won_date_week)
        else:
            # Calculate from last defense
            weeks_since = (current_year - self.last_defense_year) * 52 + (current_week - self.last_defense_week)
        
        days_since = max(0, weeks_since * 7)
        days_until = self.defense_frequency_days - days_since
        
        # Determine urgency
        if days_since >= self.defense_frequency_days:
            urgency_level = 3  # CRITICAL
            urgency_label = 'CRITICAL'
            is_overdue = True
        elif days_since >= self.defense_frequency_days * 0.85:
            urgency_level = 2  # High
            urgency_label = 'High'
            is_overdue = False
        elif days_since >= self.defense_frequency_days * 0.70:
            urgency_level = 1  # Medium
            urgency_label = 'Medium'
            is_overdue = False
        else:
            urgency_level = 0  # Normal
            urgency_label = 'Normal'
            is_overdue = False
        
        return {
            'days_since_defense': days_since,
            'is_overdue': is_overdue,
            'urgency_level': urgency_level,
            'urgency_label': urgency_label,
            'days_until_required': max(0, days_until)
        }
    
    def set_defense_requirements(self, max_days: int = None, min_annual: int = None):
        """
        Set defense frequency requirements for this championship.
        
        STEP 25: Allow customization of defense requirements per title.
        """
        if max_days is not None:
            if max_days < 14 or max_days > 90:
                raise ValueError("Max days between defenses must be 14-90")
            self.defense_frequency_days = max_days
        
        if min_annual is not None:
            if min_annual < 4 or min_annual > 52:
                raise ValueError("Min annual defenses must be 4-52")
            self.min_annual_defenses = min_annual
    
    def award_title(
        self,
        wrestler_id: str,
        wrestler_name: str,
        show_id: Optional[str],
        show_name: str,
        year: int,
        week: int,
        is_interim: bool = False
    ):
        """
        Award the title to a new champion.
        Ends the previous reign if one exists.
        
        STEP 21: Now supports interim championship
        """
        if is_interim:
            # Don't end the main champion's reign, just add interim
            self.interim_holder_id = wrestler_id
            self.interim_holder_name = wrestler_name
            
            # Create interim reign record
            interim_reign = TitleReign(
                wrestler_id=wrestler_id,
                wrestler_name=wrestler_name,
                won_at_show_id=show_id,
                won_at_show_name=show_name,
                won_date_year=year,
                won_date_week=week,
                is_interim=True
            )
            self.history.append(interim_reign)
        else:
            # End current reign if exists
            if not self.is_vacant and self.history:
                current_reign = self.history[-1]
                if current_reign.lost_at_show_id is None:  # Reign is ongoing
                    current_reign.lost_at_show_id = show_id
                    current_reign.lost_at_show_name = show_name
                    current_reign.lost_date_year = year
                    current_reign.lost_date_week = week
                    
                    # Calculate days held (approximate: 7 days per week)
                    weeks_held = (year - current_reign.won_date_year) * 52 + (week - current_reign.won_date_week)
                    current_reign.days_held = weeks_held * 7
            
            # Clear interim if any
            if self.has_interim_champion:
                # End interim reign
                for reign in reversed(self.history):
                    if reign.is_interim and reign.lost_at_show_id is None:
                        reign.lost_at_show_id = show_id
                        reign.lost_at_show_name = show_name
                        reign.lost_date_year = year
                        reign.lost_date_week = week
                        weeks_held = (year - reign.won_date_year) * 52 + (week - reign.won_date_week)
                        reign.days_held = weeks_held * 7
                        break
                
                self.interim_holder_id = None
                self.interim_holder_name = None
            
            # Create new reign
            new_reign = TitleReign(
                wrestler_id=wrestler_id,
                wrestler_name=wrestler_name,
                won_at_show_id=show_id,
                won_at_show_name=show_name,
                won_date_year=year,
                won_date_week=week,
                is_interim=False
            )
            self.history.append(new_reign)
            
            # Update current holder
            self.current_holder_id = wrestler_id
            self.current_holder_name = wrestler_name
            
            # Clear vacancy reason
            self.vacancy_reason = None
        
        # Record defense date
        self.last_defense_year = year
        self.last_defense_week = week
        self.last_defense_show_id = show_id
    
    def record_successful_defense(
        self,
        year: int,
        week: int,
        show_id: str = None
    ):
        """Record a successful title defense (champion retained)"""
        self.last_defense_year = year
        self.last_defense_week = week
        self.last_defense_show_id = show_id
        self.total_defenses += 1
    
    def vacate_title(
        self,
        show_id: str,
        show_name: str,
        year: int,
        week: int,
        reason: str = None
    ):
        """
        Vacate the title (injury, firing, etc.)
        
        STEP 21: Now tracks vacancy reason
        """
        if not self.is_vacant and self.history:
            current_reign = self.history[-1]
            current_reign.lost_at_show_id = show_id
            current_reign.lost_at_show_name = show_name
            current_reign.lost_date_year = year
            current_reign.lost_date_week = week
            
            weeks_held = (year - current_reign.won_date_year) * 52 + (week - current_reign.won_date_week)
            current_reign.days_held = weeks_held * 7
        
        # Also end interim reign if any
        if self.has_interim_champion:
            for reign in reversed(self.history):
                if reign.is_interim and reign.lost_at_show_id is None:
                    reign.lost_at_show_id = show_id
                    reign.lost_at_show_name = show_name
                    reign.lost_date_year = year
                    reign.lost_date_week = week
                    weeks_held = (year - reign.won_date_year) * 52 + (week - reign.won_date_week)
                    reign.days_held = weeks_held * 7
                    break
            
            self.interim_holder_id = None
            self.interim_holder_name = None
        
        self.current_holder_id = None
        self.current_holder_name = None
        self.vacancy_reason = reason
    
    def strip_interim_champion(
        self,
        show_id: str,
        show_name: str,
        year: int,
        week: int
    ):
        """Remove interim champion (original champion returns)"""
        if not self.has_interim_champion:
            return
        
        # End interim reign
        for reign in reversed(self.history):
            if reign.is_interim and reign.lost_at_show_id is None:
                reign.lost_at_show_id = show_id
                reign.lost_at_show_name = show_name
                reign.lost_date_year = year
                reign.lost_date_week = week
                weeks_held = (year - reign.won_date_year) * 52 + (week - reign.won_date_week)
                reign.days_held = weeks_held * 7
                break
        
        self.interim_holder_id = None
        self.interim_holder_name = None
    
    def unify_titles(
        self,
        winner_id: str,
        show_id: str,
        show_name: str,
        year: int,
        week: int
    ):
        """
        Called when interim and main champion unify titles.
        Winner becomes undisputed champion.
        """
        # End interim reign
        self.strip_interim_champion(show_id, show_name, year, week)
        
        # If winner wasn't already the main champion, transfer title
        if self.current_holder_id != winner_id:
            self.award_title(
                wrestler_id=winner_id,
                wrestler_name=self.interim_holder_name or "Unknown",  # Should be passed in
                show_id=show_id,
                show_name=show_name,
                year=year,
                week=week,
                is_interim=False
            )
    
    def adjust_prestige(self, delta: int):
        """Adjust title prestige, clamped to 0-100"""
        self.prestige = max(0, min(100, self.prestige + delta))
    
    def get_current_reign_length(self, current_year: int, current_week: int) -> int:
        """Get the current reign length in days"""
        if self.is_vacant or not self.history:
            return 0
        
        current_reign = None
        for reign in reversed(self.history):
            if reign.lost_at_show_id is None and not reign.is_interim:
                current_reign = reign
                break
        
        if not current_reign:
            return 0
        
        weeks_held = (current_year - current_reign.won_date_year) * 52 + (current_week - current_reign.won_date_week)
        return weeks_held * 7
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON"""
        return {
            'id': self.id,
            'name': self.name,
            'assigned_brand': self.assigned_brand,
            'title_type': self.title_type,
            'prestige': self.prestige,
            'current_holder_id': self.current_holder_id,
            'current_holder_name': self.current_holder_name,
            'is_vacant': self.is_vacant,
            'history': [reign.to_dict() for reign in self.history],
            'total_reigns': len([r for r in self.history if not r.is_interim]),
            # STEP 21 fields
            'interim_holder_id': self.interim_holder_id,
            'interim_holder_name': self.interim_holder_name,
            'has_interim_champion': self.has_interim_champion,
            'effective_champion_id': self.effective_champion_id,
            'effective_champion_name': self.effective_champion_name,
            'last_defense_year': self.last_defense_year,
            'last_defense_week': self.last_defense_week,
            'last_defense_show_id': self.last_defense_show_id,
            'vacancy_reason': self.vacancy_reason,
            'total_defenses': self.total_defenses,
            # STEP 25 fields
            'defense_frequency_days': self.defense_frequency_days,
            'min_annual_defenses': self.min_annual_defenses
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Championship':
        """Create championship from dictionary"""
        title = Championship(
            title_id=data['id'],
            name=data['name'],
            assigned_brand=data['assigned_brand'],
            title_type=data['title_type'],
            prestige=data.get('prestige', 50),
            current_holder_id=data.get('current_holder_id'),
            current_holder_name=data.get('current_holder_name')
        )
        
        # Load history
        for reign_data in data.get('history', []):
            title.history.append(TitleReign.from_dict(reign_data))
        
        # STEP 21: Load fields
        title.interim_holder_id = data.get('interim_holder_id')
        title.interim_holder_name = data.get('interim_holder_name')
        title.last_defense_year = data.get('last_defense_year')
        title.last_defense_week = data.get('last_defense_week')
        title.last_defense_show_id = data.get('last_defense_show_id')
        title.vacancy_reason = data.get('vacancy_reason')
        title.total_defenses = data.get('total_defenses', 0)
        
        # STEP 25: Load defense frequency fields
        title.defense_frequency_days = data.get('defense_frequency_days', 30)
        title.min_annual_defenses = data.get('min_annual_defenses', 12)
        
        return title
    
    def __repr__(self):
        holder = self.current_holder_name or "VACANT"
        interim = f" (Interim: {self.interim_holder_name})" if self.has_interim_champion else ""
        return f"<Championship {self.name} - {holder}{interim}>"