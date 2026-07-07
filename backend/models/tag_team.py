"""
Tag Team Model
Represents official tag teams with chemistry, history, and championships.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class TagTeam:
    """
    Official tag team pairing.
    
    Tracks team identity, chemistry, and championship history.
    """
    
    team_id: str
    team_name: str
    member_ids: List[str]  # Wrestler IDs (usually 2, can be 3+ for factions)
    member_names: List[str]
    
    # Team attributes
    primary_brand: str  # 'ROC Alpha', 'ROC Velocity', 'ROC Vanguard'
    formation_date_year: int
    formation_date_week: int
    
    # Chemistry (0-100) - affects match quality
    chemistry: int = 50
    experience_weeks: int = 0
    team_identity: str = ""
    entrance_style: str = "standard"
    signature_double_team: Optional[str] = None
    manager_id: Optional[str] = None
    manager_name: Optional[str] = None
    
    # Team status
    is_active: bool = True
    is_disbanded: bool = False
    
    # Championship history
    total_title_reigns: int = 0
    total_days_as_champions: int = 0
    
    # Win/Loss record as a team
    team_wins: int = 0
    team_losses: int = 0
    team_draws: int = 0
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def win_percentage(self) -> float:
        """Calculate team's win percentage"""
        total_matches = self.team_wins + self.team_losses + self.team_draws
        if total_matches == 0:
            return 0.0
        return (self.team_wins / total_matches) * 100
    
    @property
    def member_count(self) -> int:
        """Number of team members"""
        return len(self.member_ids)
    
    def add_win(self):
        """Record a team victory"""
        self.team_wins += 1
        self.adjust_chemistry(2)  # Winning together improves chemistry
    
    def add_loss(self):
        """Record a team loss"""
        self.team_losses += 1
        self.adjust_chemistry(-1)  # Losing can strain chemistry
    
    def add_draw(self):
        """Record a team draw"""
        self.team_draws += 1
    
    def adjust_chemistry(self, delta: int):
        """Adjust team chemistry (clamped 0-100)"""
        self.chemistry = max(0, min(100, self.chemistry + delta))

    def gain_experience(self, weeks: int = 1):
        """Increase team experience."""
        self.experience_weeks = max(0, self.experience_weeks + weeks)

    def get_experience_bonus(self) -> float:
        """Convert team experience into a small coordination bonus."""
        if self.experience_weeks >= 104:
            return 0.08
        if self.experience_weeks >= 52:
            return 0.05
        if self.experience_weeks >= 26:
            return 0.03
        if self.experience_weeks >= 12:
            return 0.015
        return 0.0

    def get_coordination_multiplier(self) -> float:
        """Combined chemistry + experience multiplier used in tag matches."""
        chemistry_multiplier = 0.8 + (self.chemistry / 100) * 0.4
        return round(chemistry_multiplier * (1.0 + self.get_experience_bonus()), 3)

    def record_match_outcome(self, result: str, match_quality: float = 0.0):
        """Update record, chemistry, and experience after a team match."""
        self.gain_experience(1)

        if result == 'win':
            self.add_win()
        elif result == 'loss':
            self.add_loss()
        elif result == 'draw':
            self.add_draw()

        if match_quality >= 4.0:
            self.adjust_chemistry(1)
        elif match_quality < 2.5:
            self.adjust_chemistry(-1)
    
    def disband(self):
        """Mark team as disbanded"""
        self.is_active = False
        self.is_disbanded = True
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON/API"""
        return {
            'team_id': self.team_id,
            'team_name': self.team_name,
            'member_ids': self.member_ids,
            'member_names': self.member_names,
            'primary_brand': self.primary_brand,
            'formation_date_year': self.formation_date_year,
            'formation_date_week': self.formation_date_week,
            'chemistry': self.chemistry,
            'experience_weeks': self.experience_weeks,
            'team_identity': self.team_identity,
            'entrance_style': self.entrance_style,
            'signature_double_team': self.signature_double_team,
            'manager_id': self.manager_id,
            'manager_name': self.manager_name,
            'is_active': self.is_active,
            'is_disbanded': self.is_disbanded,
            'total_title_reigns': self.total_title_reigns,
            'total_days_as_champions': self.total_days_as_champions,
            'coordination_multiplier': self.get_coordination_multiplier(),
            'team_record': {
                'wins': self.team_wins,
                'losses': self.team_losses,
                'draws': self.team_draws,
                'win_percentage': round(self.win_percentage, 1)
            },
            'member_count': self.member_count,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'TagTeam':
        """Create TagTeam from dictionary"""
        return TagTeam(
            team_id=data['team_id'],
            team_name=data['team_name'],
            member_ids=data['member_ids'],
            member_names=data['member_names'],
            primary_brand=data['primary_brand'],
            formation_date_year=data['formation_date_year'],
            formation_date_week=data['formation_date_week'],
            chemistry=data.get('chemistry', 50),
            experience_weeks=data.get('experience_weeks', 0),
            team_identity=data.get('team_identity', ''),
            entrance_style=data.get('entrance_style', 'standard'),
            signature_double_team=data.get('signature_double_team'),
            manager_id=data.get('manager_id'),
            manager_name=data.get('manager_name'),
            is_active=data.get('is_active', True),
            is_disbanded=data.get('is_disbanded', False),
            total_title_reigns=data.get('total_title_reigns', 0),
            total_days_as_champions=data.get('total_days_as_champions', 0),
            team_wins=data.get('team_record', {}).get('wins', data.get('team_wins', 0)),
            team_losses=data.get('team_record', {}).get('losses', data.get('team_losses', 0)),
            team_draws=data.get('team_record', {}).get('draws', data.get('team_draws', 0)),
            created_at=data.get('created_at', datetime.now().isoformat()),
            updated_at=data.get('updated_at', datetime.now().isoformat())
        )


class TagTeamManager:
    """
    Manages all tag teams in the promotion.
    Handles team creation, chemistry calculation, and automatic team suggestions.
    """
    
    def __init__(self):
        self.teams: List[TagTeam] = []
        self._next_team_id = 1
    
    def create_team(
        self,
        member_ids: List[str],
        member_names: List[str],
        team_name: str,
        primary_brand: str,
        year: int,
        week: int,
        initial_chemistry: int = 50
    ) -> TagTeam:
        """Create a new tag team"""
        
        team_id = f"team_{self._next_team_id:03d}"
        self._next_team_id += 1
        
        team = TagTeam(
            team_id=team_id,
            team_name=team_name,
            member_ids=member_ids,
            member_names=member_names,
            primary_brand=primary_brand,
            formation_date_year=year,
            formation_date_week=week,
            chemistry=initial_chemistry
        )
        
        self.teams.append(team)
        
        return team
    
    def get_team_by_id(self, team_id: str) -> Optional[TagTeam]:
        """Find team by ID"""
        for team in self.teams:
            if team.team_id == team_id:
                return team
        return None
    
    def get_team_by_members(self, wrestler_ids: List[str]) -> Optional[TagTeam]:
        """
        Find team by member IDs.
        Order doesn't matter.
        """
        wrestler_ids_set = set(wrestler_ids)
        
        for team in self.teams:
            if set(team.member_ids) == wrestler_ids_set and team.is_active:
                return team
        
        return None
    
    def get_active_teams(self) -> List[TagTeam]:
        """Get all active tag teams"""
        return [team for team in self.teams if team.is_active and not team.is_disbanded]
    
    def get_teams_by_brand(self, brand: str) -> List[TagTeam]:
        """Get all active teams for a specific brand"""
        return [
            team for team in self.teams 
            if team.primary_brand == brand and team.is_active and not team.is_disbanded
        ]
    
    def get_teams_involving_wrestler(self, wrestler_id: str) -> List[TagTeam]:
        """Get all teams a wrestler is part of"""
        return [
            team for team in self.teams
            if wrestler_id in team.member_ids and team.is_active
        ]
    
    def calculate_chemistry_bonus(self, wrestler_ids: List[str]) -> float:
        """
        Calculate chemistry bonus for a tag team.
        
        Returns:
            Multiplier (0.8 - 1.2) to apply to match quality
        """
        team = self.get_team_by_members(wrestler_ids)
        
        if not team:
            # No established team = random chemistry
            return 1.0
        
        # Chemistry 0-100 → multiplier 0.8-1.2
        return team.get_coordination_multiplier()
    
    def suggest_teams_for_brand(
        self,
        brand: str,
        wrestlers: List,
        max_suggestions: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Suggest potential tag team pairings based on:
        - Similar alignment
        - Complementary styles
        - Similar popularity levels
        
        Returns list of suggested pairings with rationale
        """
        suggestions = []
        
        # Filter to brand wrestlers
        brand_wrestlers = [w for w in wrestlers if w.primary_brand == brand and w.can_compete]
        
        # Don't suggest if already in a team
        existing_team_members = set()
        for team in self.get_teams_by_brand(brand):
            existing_team_members.update(team.member_ids)
        
        available_wrestlers = [w for w in brand_wrestlers if w.id not in existing_team_members]
        
        # Generate pairings
        for i, wrestler_a in enumerate(available_wrestlers):
            for wrestler_b in available_wrestlers[i+1:]:
                score = 0
                reasons = []
                
                # Same alignment bonus
                if wrestler_a.alignment == wrestler_b.alignment:
                    score += 30
                    reasons.append(f"Both {wrestler_a.alignment}s")
                
                # Similar popularity (within 20 points)
                pop_diff = abs(wrestler_a.popularity - wrestler_b.popularity)
                if pop_diff <= 20:
                    score += 20
                    reasons.append("Similar popularity")
                
                # Complementary styles (power + speed, brawler + technical, etc.)
                if (wrestler_a.brawling > 70 and wrestler_b.technical > 70) or \
                   (wrestler_a.technical > 70 and wrestler_b.brawling > 70) or \
                   (wrestler_a.speed > 70 and wrestler_b.brawling > 70):
                    score += 25
                    reasons.append("Complementary styles")
                
                # Same role tier (don't pair main eventers with jobbers)
                role_hierarchy = {
                    'Main Event': 5,
                    'Upper Midcard': 4,
                    'Midcard': 3,
                    'Lower Midcard': 2,
                    'Jobber': 1
                }
                
                role_diff = abs(role_hierarchy.get(wrestler_a.role, 3) - role_hierarchy.get(wrestler_b.role, 3))
                if role_diff <= 1:
                    score += 15
                    reasons.append("Similar experience level")
                
                # Age compatibility (within 10 years)
                age_diff = abs(wrestler_a.age - wrestler_b.age)
                if age_diff <= 10:
                    score += 10
                    reasons.append("Similar age")
                
                # Only suggest if score is decent
                if score >= 50:
                    suggestions.append({
                        'wrestler_a_id': wrestler_a.id,
                        'wrestler_a_name': wrestler_a.name,
                        'wrestler_b_id': wrestler_b.id,
                        'wrestler_b_name': wrestler_b.name,
                        'score': score,
                        'reasons': reasons,
                        'suggested_name': f"{wrestler_a.name.split()[-1]} & {wrestler_b.name.split()[-1]}"
                    })
        
        # Sort by score and return top suggestions
        suggestions.sort(key=lambda x: x['score'], reverse=True)
        
        return suggestions[:max_suggestions]
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize manager state"""
        return {
            'total_teams': len(self.teams),
            'active_teams': len(self.get_active_teams()),
            'teams': [team.to_dict() for team in self.teams],
            'next_team_id': self._next_team_id
        }
