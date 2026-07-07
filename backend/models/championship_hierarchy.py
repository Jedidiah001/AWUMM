"""
Championship Hierarchy System
Manages title tiers, defense requirements, prestige tracking, and vacancy situations.

This system handles:
- Title tier classification (World, Secondary, Midcard, Tag, Women's)
- Defense scheduling requirements
- Prestige calculation and tracking
- Vacancy management with detailed reasons
- Title situation handling (injury, contract issues, etc.)
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


class TitleTier(Enum):
    """Championship tier classification"""
    WORLD = "world"              # Top titles (ROC World, ROC United)
    SECONDARY = "secondary"      # Mid-major titles (Intercontinental)
    MIDCARD = "midcard"          # Lower titles (Vanguard Championship)
    TAG_TEAM = "tag_team"        # Tag team titles
    WOMENS = "womens"            # Women's division titles
    DEVELOPMENTAL = "developmental"  # Training/developmental titles


class VacancyReason(Enum):
    """Reasons a title can become vacant"""
    INJURY = "injury"                    # Champion injured, can't defend
    CONTRACT_EXPIRATION = "contract_expiration"  # Champion's contract expired
    RELEASED = "released"                # Champion was released
    RETIRED = "retired"                  # Champion retired
    STRIPPED = "stripped"                # Stripped for misconduct/failure to defend
    SUSPENDED = "suspended"              # Champion suspended
    RELINQUISHED = "relinquished"        # Champion voluntarily gave up title
    BRAND_CHANGE = "brand_change"        # Champion moved to different brand
    TOURNAMENT = "tournament"            # Vacated for tournament
    STORYLINE = "storyline"              # Storyline-driven vacancy


class TitleSituationType(Enum):
    """Types of title situations requiring attention"""
    NORMAL = "normal"                    # No issues
    CHAMPION_INJURED = "champion_injured"
    CHAMPION_CONTRACT_EXPIRING = "champion_contract_expiring"
    CHAMPION_CONTRACT_EXPIRED = "champion_contract_expired"
    DEFENSE_OVERDUE = "defense_overdue"
    VACANT = "vacant"
    INTERIM_CHAMPION = "interim_champion"
    DISPUTED = "disputed"                # Multiple claimants
    LOW_PRESTIGE = "low_prestige"        # Title prestige critically low


@dataclass
class DefenseRequirement:
    """Defense scheduling requirements by tier"""
    tier: TitleTier
    max_days_between_defenses: int
    min_defenses_per_year: int
    ppv_defense_required: bool
    weekly_tv_defense_allowed: bool
    
    @staticmethod
    def get_requirements(tier: TitleTier) -> 'DefenseRequirement':
        """Get defense requirements for a title tier"""
        requirements = {
            TitleTier.WORLD: DefenseRequirement(
                tier=TitleTier.WORLD,
                max_days_between_defenses=30,  # Must defend every 30 days
                min_defenses_per_year=12,
                ppv_defense_required=True,     # Must defend at PPVs
                weekly_tv_defense_allowed=True
            ),
            TitleTier.SECONDARY: DefenseRequirement(
                tier=TitleTier.SECONDARY,
                max_days_between_defenses=35,
                min_defenses_per_year=10,
                ppv_defense_required=True,
                weekly_tv_defense_allowed=True
            ),
            TitleTier.MIDCARD: DefenseRequirement(
                tier=TitleTier.MIDCARD,
                max_days_between_defenses=42,  # 6 weeks
                min_defenses_per_year=8,
                ppv_defense_required=False,
                weekly_tv_defense_allowed=True
            ),
            TitleTier.TAG_TEAM: DefenseRequirement(
                tier=TitleTier.TAG_TEAM,
                max_days_between_defenses=42,
                min_defenses_per_year=8,
                ppv_defense_required=False,
                weekly_tv_defense_allowed=True
            ),
            TitleTier.WOMENS: DefenseRequirement(
                tier=TitleTier.WOMENS,
                max_days_between_defenses=30,
                min_defenses_per_year=12,
                ppv_defense_required=True,
                weekly_tv_defense_allowed=True
            ),
            TitleTier.DEVELOPMENTAL: DefenseRequirement(
                tier=TitleTier.DEVELOPMENTAL,
                max_days_between_defenses=56,  # 8 weeks
                min_defenses_per_year=6,
                ppv_defense_required=False,
                weekly_tv_defense_allowed=True
            )
        }
        return requirements.get(tier, requirements[TitleTier.MIDCARD])


@dataclass
class VacancyRecord:
    """Record of a title vacancy period"""
    vacancy_id: str
    title_id: str
    title_name: str
    reason: VacancyReason
    previous_champion_id: Optional[str]
    previous_champion_name: Optional[str]
    vacated_year: int
    vacated_week: int
    vacated_show_id: Optional[str]
    vacated_show_name: Optional[str]
    filled_year: Optional[int] = None
    filled_week: Optional[int] = None
    filled_show_id: Optional[str] = None
    filled_show_name: Optional[str] = None
    new_champion_id: Optional[str] = None
    new_champion_name: Optional[str] = None
    weeks_vacant: int = 0
    resolution_method: Optional[str] = None  # 'match', 'tournament', 'awarded'
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'vacancy_id': self.vacancy_id,
            'title_id': self.title_id,
            'title_name': self.title_name,
            'reason': self.reason.value,
            'previous_champion_id': self.previous_champion_id,
            'previous_champion_name': self.previous_champion_name,
            'vacated_year': self.vacated_year,
            'vacated_week': self.vacated_week,
            'vacated_show_id': self.vacated_show_id,
            'vacated_show_name': self.vacated_show_name,
            'filled_year': self.filled_year,
            'filled_week': self.filled_week,
            'filled_show_id': self.filled_show_id,
            'filled_show_name': self.filled_show_name,
            'new_champion_id': self.new_champion_id,
            'new_champion_name': self.new_champion_name,
            'weeks_vacant': self.weeks_vacant,
            'resolution_method': self.resolution_method,
            'notes': self.notes,
            'is_active': self.filled_year is None
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'VacancyRecord':
        return VacancyRecord(
            vacancy_id=data['vacancy_id'],
            title_id=data['title_id'],
            title_name=data['title_name'],
            reason=VacancyReason(data['reason']),
            previous_champion_id=data.get('previous_champion_id'),
            previous_champion_name=data.get('previous_champion_name'),
            vacated_year=data['vacated_year'],
            vacated_week=data['vacated_week'],
            vacated_show_id=data.get('vacated_show_id'),
            vacated_show_name=data.get('vacated_show_name'),
            filled_year=data.get('filled_year'),
            filled_week=data.get('filled_week'),
            filled_show_id=data.get('filled_show_id'),
            filled_show_name=data.get('filled_show_name'),
            new_champion_id=data.get('new_champion_id'),
            new_champion_name=data.get('new_champion_name'),
            weeks_vacant=data.get('weeks_vacant', 0),
            resolution_method=data.get('resolution_method'),
            notes=data.get('notes', '')
        )


@dataclass
class TitleDefenseRecord:
    """Record of a title defense"""
    defense_id: str
    title_id: str
    champion_id: str
    champion_name: str
    challenger_id: str
    challenger_name: str
    show_id: str
    show_name: str
    year: int
    week: int
    is_ppv: bool
    result: str  # 'retained', 'lost', 'draw', 'no_contest'
    finish_type: str
    star_rating: float
    duration_minutes: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'defense_id': self.defense_id,
            'title_id': self.title_id,
            'champion_id': self.champion_id,
            'champion_name': self.champion_name,
            'challenger_id': self.challenger_id,
            'challenger_name': self.challenger_name,
            'show_id': self.show_id,
            'show_name': self.show_name,
            'year': self.year,
            'week': self.week,
            'is_ppv': self.is_ppv,
            'result': self.result,
            'finish_type': self.finish_type,
            'star_rating': self.star_rating,
            'duration_minutes': self.duration_minutes
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'TitleDefenseRecord':
        """Create TitleDefenseRecord from dictionary, ignoring extra fields"""
        return TitleDefenseRecord(
            defense_id=data['defense_id'],
            title_id=data['title_id'],
            champion_id=data['champion_id'],
            champion_name=data['champion_name'],
            challenger_id=data['challenger_id'],
            challenger_name=data['challenger_name'],
            show_id=data['show_id'],
            show_name=data['show_name'],
            year=data['year'],
            week=data['week'],
            is_ppv=data.get('is_ppv', False),
            result=data['result'],
            finish_type=data['finish_type'],
            star_rating=data.get('star_rating', 0.0),
            duration_minutes=data.get('duration_minutes', 0)
        )


@dataclass
class GuaranteedTitleShot:
    """Record of a guaranteed future title shot"""
    shot_id: str
    wrestler_id: str
    wrestler_name: str
    title_id: str
    title_name: str
    reason: str  # 'injury_return', 'rematch_clause', 'tournament_winner', 'storyline'
    granted_year: int
    granted_week: int
    expires_year: Optional[int] = None
    expires_week: Optional[int] = None
    used: bool = False
    used_year: Optional[int] = None
    used_week: Optional[int] = None
    used_show_id: Optional[str] = None
    notes: str = ""
    
    @property
    def is_expired(self) -> bool:
        """Check if this title shot has expired (needs current year/week to properly check)"""
        return self.used
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'shot_id': self.shot_id,
            'wrestler_id': self.wrestler_id,
            'wrestler_name': self.wrestler_name,
            'title_id': self.title_id,
            'title_name': self.title_name,
            'reason': self.reason,
            'granted_year': self.granted_year,
            'granted_week': self.granted_week,
            'expires_year': self.expires_year,
            'expires_week': self.expires_week,
            'used': self.used,
            'used_year': self.used_year,
            'used_week': self.used_week,
            'used_show_id': self.used_show_id,
            'notes': self.notes
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'GuaranteedTitleShot':
        return GuaranteedTitleShot(
            shot_id=data['shot_id'],
            wrestler_id=data['wrestler_id'],
            wrestler_name=data['wrestler_name'],
            title_id=data['title_id'],
            title_name=data['title_name'],
            reason=data['reason'],
            granted_year=data['granted_year'],
            granted_week=data['granted_week'],
            expires_year=data.get('expires_year'),
            expires_week=data.get('expires_week'),
            used=data.get('used', False),
            used_year=data.get('used_year'),
            used_week=data.get('used_week'),
            used_show_id=data.get('used_show_id'),
            notes=data.get('notes', '')
        )


@dataclass
class TitleSituation:
    """Current situation/status of a championship"""
    title_id: str
    title_name: str
    tier: TitleTier
    situation_type: TitleSituationType
    current_holder_id: Optional[str]
    current_holder_name: Optional[str]
    interim_holder_id: Optional[str] = None
    interim_holder_name: Optional[str] = None
    days_since_last_defense: int = 0
    next_required_defense_week: Optional[int] = None
    prestige: int = 50
    alerts: List[str] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'title_id': self.title_id,
            'title_name': self.title_name,
            'tier': self.tier.value,
            'situation_type': self.situation_type.value,
            'current_holder_id': self.current_holder_id,
            'current_holder_name': self.current_holder_name,
            'interim_holder_id': self.interim_holder_id,
            'interim_holder_name': self.interim_holder_name,
            'days_since_last_defense': self.days_since_last_defense,
            'next_required_defense_week': self.next_required_defense_week,
            'prestige': self.prestige,
            'alerts': self.alerts,
            'recommended_actions': self.recommended_actions,
            'has_issues': self.situation_type != TitleSituationType.NORMAL
        }


class ChampionshipHierarchy:
    """
    Manages the championship hierarchy system.
    Handles tier classification, prestige calculation, and title situations.
    """
    
    # Map title_type from Championship model to TitleTier
    TYPE_TO_TIER = {
        'World': TitleTier.WORLD,
        'Secondary': TitleTier.SECONDARY,
        'Midcard': TitleTier.MIDCARD,
        'Tag Team': TitleTier.TAG_TEAM,
        'Women': TitleTier.WOMENS,
        'Developmental': TitleTier.DEVELOPMENTAL
    }
    
    def __init__(self):
        self.vacancy_history: List[VacancyRecord] = []
        self.defense_history: List[TitleDefenseRecord] = []
        self.guaranteed_shots: List[GuaranteedTitleShot] = []
        self._next_vacancy_id = 1
        self._next_defense_id = 1
        self._next_shot_id = 1
    
    def get_title_tier(self, championship) -> TitleTier:
        """Get the tier for a championship"""
        return self.TYPE_TO_TIER.get(championship.title_type, TitleTier.MIDCARD)
    
    def get_defense_requirements(self, championship) -> DefenseRequirement:
        """Get defense requirements for a championship"""
        tier = self.get_title_tier(championship)
        return DefenseRequirement.get_requirements(tier)
    
    def calculate_prestige(
        self,
        championship,
        recent_defenses: List[TitleDefenseRecord],
        current_holder_popularity: int = 50,
        current_holder_role: str = 'Midcard'
    ) -> int:
        """
        Calculate current prestige for a championship.
        
        Factors:
        - Base prestige from tier
        - Current holder's popularity and role
        - Quality of recent title defenses
        - Frequency of defenses
        - Vacancy history
        """
        tier = self.get_title_tier(championship)
        
        # Base prestige by tier
        base_prestige = {
            TitleTier.WORLD: 80,
            TitleTier.SECONDARY: 65,
            TitleTier.MIDCARD: 50,
            TitleTier.TAG_TEAM: 55,
            TitleTier.WOMENS: 70,
            TitleTier.DEVELOPMENTAL: 40
        }.get(tier, 50)
        
        prestige = base_prestige
        
        # Holder quality bonus/penalty
        if championship.current_holder_id:
            # Role bonus
            role_modifier = {
                'Main Event': 10,
                'Upper Midcard': 5,
                'Midcard': 0,
                'Lower Midcard': -5,
                'Jobber': -10
            }.get(current_holder_role, 0)
            
            prestige += role_modifier
            
            # Popularity modifier (-10 to +10)
            popularity_modifier = (current_holder_popularity - 50) / 5
            prestige += int(popularity_modifier)
        else:
            # Vacant title loses prestige
            prestige -= 15
        
        # Recent defense quality
        if recent_defenses:
            avg_star_rating = sum(d.star_rating for d in recent_defenses) / len(recent_defenses)
            
            if avg_star_rating >= 4.0:
                prestige += 10
            elif avg_star_rating >= 3.5:
                prestige += 5
            elif avg_star_rating < 2.5:
                prestige -= 5
            
            # PPV defense bonus
            ppv_defenses = [d for d in recent_defenses if d.is_ppv]
            prestige += len(ppv_defenses) * 2
        
        # Clamp to 0-100
        return max(0, min(100, prestige))
    
    def check_defense_status(
        self,
        championship,
        current_year: int,
        current_week: int,
        last_defense_year: int,
        last_defense_week: int
    ) -> Dict[str, Any]:
        """
        Check if a title defense is overdue or upcoming.
        
        Returns status dict with:
        - days_since_defense
        - is_overdue
        - days_until_required
        - urgency_level (0-3)
        """
        requirements = self.get_defense_requirements(championship)
        
        # Calculate weeks since last defense
        weeks_since = (current_year - last_defense_year) * 52 + (current_week - last_defense_week)
        days_since = weeks_since * 7
        
        max_days = requirements.max_days_between_defenses
        days_until_required = max_days - days_since
        
        is_overdue = days_since > max_days
        
        # Calculate urgency
        if is_overdue:
            urgency = 3  # Critical
        elif days_until_required <= 7:
            urgency = 2  # Urgent
        elif days_until_required <= 14:
            urgency = 1  # Warning
        else:
            urgency = 0  # Normal
        
        return {
            'days_since_defense': days_since,
            'weeks_since_defense': weeks_since,
            'max_days_allowed': max_days,
            'days_until_required': max(0, days_until_required),
            'weeks_until_required': max(0, days_until_required // 7),
            'is_overdue': is_overdue,
            'urgency_level': urgency,
            'urgency_label': ['Normal', 'Warning', 'Urgent', 'Critical'][urgency]
        }
    
    def get_title_situation(
        self,
        championship,
        holder_wrestler,
        current_year: int,
        current_week: int,
        last_defense_year: int = None,
        last_defense_week: int = None
    ) -> TitleSituation:
        """
        Analyze the complete situation for a championship.
        Returns alerts and recommended actions.
        """
        tier = self.get_title_tier(championship)
        alerts = []
        recommended_actions = []
        
        # Determine situation type
        situation_type = TitleSituationType.NORMAL
        
        # Check if vacant
        if championship.is_vacant:
            situation_type = TitleSituationType.VACANT
            alerts.append("🚨 Championship is VACANT")
            recommended_actions.append("Schedule tournament or match to crown new champion")
            recommended_actions.append("Consider top contenders from the brand")
        
        # Check champion status
        elif holder_wrestler:
            # Check injury
            if holder_wrestler.is_injured:
                injury_weeks = holder_wrestler.injury.weeks_remaining
                
                if injury_weeks >= 12:
                    situation_type = TitleSituationType.CHAMPION_INJURED
                    alerts.append(f"🏥 Champion injured for {injury_weeks}+ weeks")
                    recommended_actions.append("Consider vacating the title")
                    recommended_actions.append("Create interim championship")
                    recommended_actions.append("Write injury angle with attacker")
                elif injury_weeks >= 4:
                    situation_type = TitleSituationType.CHAMPION_INJURED
                    alerts.append(f"🏥 Champion injured for {injury_weeks} weeks")
                    recommended_actions.append("Monitor recovery progress")
                    recommended_actions.append("Consider interim champion if PPV approaching")
                else:
                    alerts.append(f"⚠️ Champion has minor injury ({injury_weeks} weeks)")
            
            # Check contract
            if holder_wrestler.contract.weeks_remaining <= 0:
                situation_type = TitleSituationType.CHAMPION_CONTRACT_EXPIRED
                alerts.append("🚨 Champion's contract has EXPIRED")
                recommended_actions.append("Negotiate contract extension immediately")
                recommended_actions.append("If no agreement, title must be vacated")
            elif holder_wrestler.contract.weeks_remaining <= 4:
                if situation_type == TitleSituationType.NORMAL:
                    situation_type = TitleSituationType.CHAMPION_CONTRACT_EXPIRING
                alerts.append(f"⚠️ Champion's contract expires in {holder_wrestler.contract.weeks_remaining} weeks")
                recommended_actions.append("Begin contract negotiations")
                recommended_actions.append("Have backup plan for title")
            
            # Check defense schedule
            if last_defense_year is not None and last_defense_week is not None:
                defense_status = self.check_defense_status(
                    championship,
                    current_year,
                    current_week,
                    last_defense_year,
                    last_defense_week
                )
                
                if defense_status['is_overdue']:
                    if situation_type == TitleSituationType.NORMAL:
                        situation_type = TitleSituationType.DEFENSE_OVERDUE
                    alerts.append(f"🚨 Title defense OVERDUE by {defense_status['days_since_defense'] - defense_status['max_days_allowed']} days")
                    recommended_actions.append("Schedule immediate title defense")
                    recommended_actions.append("Consider stripping champion if unable to defend")
                elif defense_status['urgency_level'] >= 2:
                    alerts.append(f"⚠️ Title defense required within {defense_status['days_until_required']} days")
                    recommended_actions.append("Schedule title defense for upcoming show")
        
        # Check prestige
        if championship.prestige < 40:
            alerts.append("📉 Title prestige is critically low")
            recommended_actions.append("Book high-quality title matches")
            recommended_actions.append("Feature title prominently on shows")
            if situation_type == TitleSituationType.NORMAL:
                situation_type = TitleSituationType.LOW_PRESTIGE
        
        # Calculate next required defense week
        next_defense_week = None
        if last_defense_week is not None and not championship.is_vacant:
            requirements = self.get_defense_requirements(championship)
            weeks_allowed = requirements.max_days_between_defenses // 7
            next_defense_week = last_defense_week + weeks_allowed
            if next_defense_week > 52:
                next_defense_week -= 52
        
        # Check for guaranteed title shots
        active_shots = self.get_active_guaranteed_shots(championship.id, current_year, current_week)
        if active_shots:
            for shot in active_shots:
                alerts.append(f"📋 {shot.wrestler_name} has a guaranteed title shot ({shot.reason})")
                recommended_actions.append(f"Book {shot.wrestler_name} vs champion")
        
        return TitleSituation(
            title_id=championship.id,
            title_name=championship.name,
            tier=tier,
            situation_type=situation_type,
            current_holder_id=championship.current_holder_id,
            current_holder_name=championship.current_holder_name,
            days_since_last_defense=0,  # Would be calculated from defense history
            next_required_defense_week=next_defense_week,
            prestige=championship.prestige,
            alerts=alerts,
            recommended_actions=recommended_actions
        )
    
    # ========================================================================
    # Vacancy Management
    # ========================================================================
    
    def create_vacancy(
        self,
        championship,
        reason: VacancyReason,
        year: int,
        week: int,
        show_id: str = None,
        show_name: str = None,
        notes: str = ""
    ) -> VacancyRecord:
        """Create a vacancy record when a title becomes vacant"""
        
        vacancy_id = f"vacancy_{self._next_vacancy_id}"
        self._next_vacancy_id += 1
        
        vacancy = VacancyRecord(
            vacancy_id=vacancy_id,
            title_id=championship.id,
            title_name=championship.name,
            reason=reason,
            previous_champion_id=championship.current_holder_id,
            previous_champion_name=championship.current_holder_name,
            vacated_year=year,
            vacated_week=week,
            vacated_show_id=show_id,
            vacated_show_name=show_name,
            notes=notes
        )
        
        self.vacancy_history.append(vacancy)
        
        return vacancy
    
    def fill_vacancy(
        self,
        vacancy_id: str,
        new_champion_id: str,
        new_champion_name: str,
        year: int,
        week: int,
        show_id: str,
        show_name: str,
        resolution_method: str = 'match'
    ) -> Optional[VacancyRecord]:
        """Record when a vacancy is filled"""
        
        for vacancy in self.vacancy_history:
            if vacancy.vacancy_id == vacancy_id:
                vacancy.filled_year = year
                vacancy.filled_week = week
                vacancy.filled_show_id = show_id
                vacancy.filled_show_name = show_name
                vacancy.new_champion_id = new_champion_id
                vacancy.new_champion_name = new_champion_name
                vacancy.resolution_method = resolution_method
                
                # Calculate weeks vacant
                weeks_vacant = (year - vacancy.vacated_year) * 52 + (week - vacancy.vacated_week)
                vacancy.weeks_vacant = max(0, weeks_vacant)
                
                return vacancy
        
        return None
    
    def get_active_vacancies(self) -> List[VacancyRecord]:
        """Get all currently active (unfilled) vacancies"""
        return [v for v in self.vacancy_history if v.filled_year is None]
    
    def get_vacancy_for_title(self, title_id: str) -> Optional[VacancyRecord]:
        """Get active vacancy for a specific title"""
        for vacancy in self.vacancy_history:
            if vacancy.title_id == title_id and vacancy.filled_year is None:
                return vacancy
        return None
    
    # ========================================================================
    # Defense Tracking
    # ========================================================================
    
    def record_defense(
        self,
        title_id: str,
        champion_id: str,
        champion_name: str,
        challenger_id: str,
        challenger_name: str,
        show_id: str,
        show_name: str,
        year: int,
        week: int,
        is_ppv: bool,
        result: str,
        finish_type: str,
        star_rating: float,
        duration_minutes: int
    ) -> TitleDefenseRecord:
        """Record a title defense"""
        
        defense_id = f"defense_{self._next_defense_id}"
        self._next_defense_id += 1
        
        defense = TitleDefenseRecord(
            defense_id=defense_id,
            title_id=title_id,
            champion_id=champion_id,
            champion_name=champion_name,
            challenger_id=challenger_id,
            challenger_name=challenger_name,
            show_id=show_id,
            show_name=show_name,
            year=year,
            week=week,
            is_ppv=is_ppv,
            result=result,
            finish_type=finish_type,
            star_rating=star_rating,
            duration_minutes=duration_minutes
        )
        
        self.defense_history.append(defense)
        
        return defense
    
    def get_recent_defenses(self, title_id: str, count: int = 5) -> List[TitleDefenseRecord]:
        """Get recent defenses for a title"""
        title_defenses = [d for d in self.defense_history if d.title_id == title_id]
        title_defenses.sort(key=lambda d: (d.year, d.week), reverse=True)
        return title_defenses[:count]
    
    def get_last_defense(self, title_id: str) -> Optional[TitleDefenseRecord]:
        """Get the most recent defense for a title"""
        defenses = self.get_recent_defenses(title_id, 1)
        return defenses[0] if defenses else None
    
    def get_champion_defenses(self, champion_id: str) -> List[TitleDefenseRecord]:
        """Get all defenses by a specific champion"""
        return [d for d in self.defense_history if d.champion_id == champion_id]
    
    # ========================================================================
    # Guaranteed Title Shots
    # ========================================================================
    
    def grant_title_shot(
        self,
        wrestler_id: str,
        wrestler_name: str,
        title_id: str,
        title_name: str,
        reason: str,
        year: int,
        week: int,
        expires_year: int = None,
        expires_week: int = None,
        notes: str = ""
    ) -> GuaranteedTitleShot:
        """Grant a wrestler a guaranteed future title shot"""
        
        shot_id = f"shot_{self._next_shot_id}"
        self._next_shot_id += 1
        
        # Default expiration: 1 year
        if expires_year is None:
            expires_year = year + 1
            expires_week = week
        
        shot = GuaranteedTitleShot(
            shot_id=shot_id,
            wrestler_id=wrestler_id,
            wrestler_name=wrestler_name,
            title_id=title_id,
            title_name=title_name,
            reason=reason,
            granted_year=year,
            granted_week=week,
            expires_year=expires_year,
            expires_week=expires_week,
            notes=notes
        )
        
        self.guaranteed_shots.append(shot)
        
        return shot
    
    def use_title_shot(
        self,
        shot_id: str,
        year: int,
        week: int,
        show_id: str
    ) -> Optional[GuaranteedTitleShot]:
        """Mark a guaranteed title shot as used"""
        
        for shot in self.guaranteed_shots:
            if shot.shot_id == shot_id and not shot.used:
                shot.used = True
                shot.used_year = year
                shot.used_week = week
                shot.used_show_id = show_id
                return shot
        
        return None
    
    def get_active_guaranteed_shots(
        self,
        title_id: str,
        current_year: int,
        current_week: int
    ) -> List[GuaranteedTitleShot]:
        """Get active (unused, unexpired) guaranteed shots for a title"""
        
        active_shots = []
        
        for shot in self.guaranteed_shots:
            if shot.title_id != title_id:
                continue
            
            if shot.used:
                continue
            
            # Check expiration
            if shot.expires_year is not None:
                if shot.expires_year < current_year:
                    continue
                if shot.expires_year == current_year and shot.expires_week < current_week:
                    continue
            
            active_shots.append(shot)
        
        return active_shots
    
    def get_wrestler_guaranteed_shots(
        self,
        wrestler_id: str,
        active_only: bool = True,
        current_year: int = None,
        current_week: int = None
    ) -> List[GuaranteedTitleShot]:
        """Get all guaranteed title shots for a wrestler"""
        
        shots = [s for s in self.guaranteed_shots if s.wrestler_id == wrestler_id]
        
        if active_only and current_year and current_week:
            active_shots = []
            for shot in shots:
                if shot.used:
                    continue
                if shot.expires_year and shot.expires_year < current_year:
                    continue
                if shot.expires_year == current_year and shot.expires_week < current_week:
                    continue
                active_shots.append(shot)
            return active_shots
        
        return shots
    
    # ========================================================================
    # Serialization
    # ========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'vacancy_history': [v.to_dict() for v in self.vacancy_history],
            'defense_history': [d.to_dict() for d in self.defense_history],
            'guaranteed_shots': [s.to_dict() for s in self.guaranteed_shots],
            '_next_vacancy_id': self._next_vacancy_id,
            '_next_defense_id': self._next_defense_id,
            '_next_shot_id': self._next_shot_id
        }
    
    def load_from_dict(self, data: Dict[str, Any]):
        """Load state from dictionary"""
        self.vacancy_history = [
            VacancyRecord.from_dict(v) for v in data.get('vacancy_history', [])
        ]
        self.defense_history = [
            TitleDefenseRecord.from_dict(d) for d in data.get('defense_history', [])
        ]
        self.guaranteed_shots = [
            GuaranteedTitleShot.from_dict(s) for s in data.get('guaranteed_shots', [])
        ]
        self._next_vacancy_id = data.get('_next_vacancy_id', 1)
        self._next_defense_id = data.get('_next_defense_id', 1)
        self._next_shot_id = data.get('_next_shot_id', 1)


# Global championship hierarchy instance
championship_hierarchy = ChampionshipHierarchy()