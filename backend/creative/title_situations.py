"""
Title Situation Manager
Handles championship situations including injuries, vacancies, and transitions.

Based on the Tyler Cross scenario:
- Champion gets injured during match
- Company must decide: vacate, interim champion, or wait
- Attacker angle creates feud for return
- Guaranteed title shot upon return
- Full storyline integration

This module manages all title-related creative decisions.

STEP 25 ENHANCEMENTS:
✅ Added check_defense_frequency method to detect overdue defenses
✅ Creates TitleSituation when defense is overdue or urgent
"""

import random
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from models.championship_hierarchy import (
    ChampionshipHierarchy,
    TitleTier,
    VacancyReason,
    TitleSituationType,
    TitleSituation,
    VacancyRecord,
    GuaranteedTitleShot,
    championship_hierarchy
)
from models.championship import Championship
from models.wrestler import Wrestler


class TitleDecision(Enum):
    """Possible decisions when champion is unavailable"""
    WAIT = "wait"                        # Wait for champion to recover
    VACATE = "vacate"                    # Vacate the title immediately
    INTERIM_CHAMPION = "interim_champion" # Create interim championship
    DEFEND_INJURED = "defend_injured"     # Champion defends while injured (risky)
    STRIP = "strip"                       # Strip champion of title
    TOURNAMENT = "tournament"             # Vacate and hold tournament
    NUMBER_ONE_CONTENDER = "number_one_contender"  # #1 contender match, winner faces champ when ready


class ResolutionMethod(Enum):
    """How a vacant title can be filled"""
    SINGLE_MATCH = "single_match"        # One match between top contenders
    TOURNAMENT = "tournament"            # Multi-person tournament
    BATTLE_ROYAL = "battle_royal"        # Battle royal/rumble
    LADDER_MATCH = "ladder_match"        # Multi-person ladder match
    AWARDED = "awarded"                  # Title awarded by authority
    CHAMPION_RETURNS = "champion_returns" # Original champion returns and reclaims


@dataclass
class TitleDecisionResult:
    """Result of a title situation decision"""
    decision: TitleDecision
    success: bool
    message: str
    title_id: str
    title_name: str
    affected_wrestler_id: Optional[str] = None
    affected_wrestler_name: Optional[str] = None
    new_champion_id: Optional[str] = None
    new_champion_name: Optional[str] = None
    vacancy_created: bool = False
    vacancy_id: Optional[str] = None
    interim_created: bool = False
    guaranteed_shot_granted: bool = False
    guaranteed_shot_id: Optional[str] = None
    feud_created: bool = False
    feud_id: Optional[str] = None
    segment_suggestion: Optional[Dict[str, Any]] = None
    follow_up_actions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'decision': self.decision.value,
            'success': self.success,
            'message': self.message,
            'title_id': self.title_id,
            'title_name': self.title_name,
            'affected_wrestler_id': self.affected_wrestler_id,
            'affected_wrestler_name': self.affected_wrestler_name,
            'new_champion_id': self.new_champion_id,
            'new_champion_name': self.new_champion_name,
            'vacancy_created': self.vacancy_created,
            'vacancy_id': self.vacancy_id,
            'interim_created': self.interim_created,
            'guaranteed_shot_granted': self.guaranteed_shot_granted,
            'guaranteed_shot_id': self.guaranteed_shot_id,
            'feud_created': self.feud_created,
            'feud_id': self.feud_id,
            'segment_suggestion': self.segment_suggestion,
            'follow_up_actions': self.follow_up_actions
        }


@dataclass
class InjuryAngleTemplate:
    """Template for an injury write-off angle"""
    angle_type: str  # 'backstage_attack', 'in_ring_assault', 'parking_lot', etc.
    description: str
    attacker_id: Optional[str]
    attacker_name: Optional[str]
    victim_id: str
    victim_name: str
    heat_generated: int  # 0-100
    creates_feud: bool
    feud_intensity: int
    promo_text: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'angle_type': self.angle_type,
            'description': self.description,
            'attacker_id': self.attacker_id,
            'attacker_name': self.attacker_name,
            'victim_id': self.victim_id,
            'victim_name': self.victim_name,
            'heat_generated': self.heat_generated,
            'creates_feud': self.creates_feud,
            'feud_intensity': self.feud_intensity,
            'promo_text': self.promo_text
        }


@dataclass
class ReturnAngleTemplate:
    """Template for a return from injury angle"""
    angle_type: str  # 'surprise_return', 'announced_return', 'attack_from_crowd', etc.
    description: str
    returning_wrestler_id: str
    returning_wrestler_name: str
    target_id: Optional[str]
    target_name: Optional[str]
    is_surprise: bool
    pop_level: int  # 0-100 expected crowd reaction
    momentum_boost: int
    popularity_boost: int
    promo_text: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'angle_type': self.angle_type,
            'description': self.description,
            'returning_wrestler_id': self.returning_wrestler_id,
            'returning_wrestler_name': self.returning_wrestler_name,
            'target_id': self.target_id,
            'target_name': self.target_name,
            'is_surprise': self.is_surprise,
            'pop_level': self.pop_level,
            'momentum_boost': self.momentum_boost,
            'popularity_boost': self.popularity_boost,
            'promo_text': self.promo_text
        }


class TitleSituationManager:
    """
    Manages title situations and creative decisions.
    
    Handles:
    - Champion injury scenarios
    - Vacancy management
    - Interim championship creation
    - Return angles and guaranteed title shots
    - Integration with feud system
    - Defense frequency tracking (STEP 25)
    """
    
    # Attack angle templates
    ATTACK_TEMPLATES = [
        {
            'type': 'backstage_attack',
            'description': "{attacker} brutally attacked {victim} backstage with a steel chair, targeting the injured {body_part}",
            'heat': 35,
            'feud_intensity': 60
        },
        {
            'type': 'parking_lot_ambush',
            'description': "{attacker} ambushed {victim} in the parking lot, repeatedly slamming them into a car",
            'heat': 40,
            'feud_intensity': 70
        },
        {
            'type': 'post_match_assault',
            'description': "After {victim}'s match, {attacker} attacked from behind and destroyed them with their finisher",
            'heat': 30,
            'feud_intensity': 55
        },
        {
            'type': 'contract_signing_attack',
            'description': "During a contract signing, {attacker} flipped the table and put {victim} through it",
            'heat': 45,
            'feud_intensity': 75
        },
        {
            'type': 'stretcher_attack',
            'description': "As {victim} was being stretchered out, {attacker} attacked the medical team and continued the assault",
            'heat': 50,
            'feud_intensity': 80
        },
        {
            'type': 'championship_celebration_attack',
            'description': "During {victim}'s championship celebration, {attacker} emerged and laid them out, standing over them with the title",
            'heat': 45,
            'feud_intensity': 70
        }
    ]
    
    # Return angle templates
    RETURN_TEMPLATES = [
        {
            'type': 'surprise_music_hit',
            'description': "{wrestler}'s music hits! The arena EXPLODES as they make their return!",
            'is_surprise': True,
            'pop': 90,
            'momentum': 50,
            'popularity': 25
        },
        {
            'type': 'lights_out_return',
            'description': "The lights go out... when they come back on, {wrestler} is standing in the ring!",
            'is_surprise': True,
            'pop': 95,
            'momentum': 55,
            'popularity': 30
        },
        {
            'type': 'attack_from_crowd',
            'description': "{wrestler} emerges from the crowd and attacks {target}! They're BACK!",
            'is_surprise': True,
            'pop': 85,
            'momentum': 45,
            'popularity': 20
        },
        {
            'type': 'announced_return_promo',
            'description': "{wrestler} returns to a hero's welcome, cutting an emotional promo about their journey back",
            'is_surprise': False,
            'pop': 75,
            'momentum': 35,
            'popularity': 15
        },
        {
            'type': 'save_the_day',
            'description': "Just as {target} is about to be destroyed, {wrestler}'s music hits! They sprint to the ring and clear house!",
            'is_surprise': True,
            'pop': 92,
            'momentum': 50,
            'popularity': 25
        },
        {
            'type': 'ppv_surprise_entrant',
            'description': "The countdown ends... IT'S {wrestler}! They've returned at the PPV!",
            'is_surprise': True,
            'pop': 88,
            'momentum': 45,
            'popularity': 22
        }
    ]
    
    # Authority announcement templates for vacating titles
    VACANCY_ANNOUNCEMENT_TEMPLATES = [
        "Due to {reason}, {champion} has been forced to relinquish the {title}.",
        "It is with regret that we announce {champion} must vacate the {title} due to {reason}.",
        "After consultation with medical staff, {champion} has made the difficult decision to surrender the {title}.",
        "The {title} is now vacant. {champion} will receive an immediate title shot upon their return.",
        "Tonight, {champion} has relinquished the {title}. A tournament will be held to crown a new champion."
    ]
    
    def __init__(self, hierarchy: ChampionshipHierarchy = None):
        self.hierarchy = hierarchy or championship_hierarchy
    
    def check_defense_frequency(
        self,
        championship: Championship,
        current_year: int,
        current_week: int
    ) -> Optional[TitleSituation]:
        """
        Check if a championship has an overdue defense and create situation if needed.
        
        STEP 25: Defense frequency tracking.
        
        Args:
            championship: The championship to check
            current_year: Current game year
            current_week: Current game week
        
        Returns:
            TitleSituation if defense is overdue, None otherwise
        """
        if championship.is_vacant:
            return None
        
        # Get defense status from championship
        status = championship.get_defense_status(current_year, current_week)
        
        # Only create situation if overdue or urgency is high (level 2+)
        if not status['is_overdue'] and status['urgency_level'] < 2:
            return None
        
        # Determine severity based on status
        if status['is_overdue']:
            severity = 'high'
        elif status['urgency_level'] >= 3:
            severity = 'high'
        elif status['urgency_level'] >= 2:
            severity = 'medium'
        else:
            severity = 'low'
        
        # Build description
        days_since = status['days_since_defense']
        if status['is_overdue']:
            description = f"{championship.name} has not been defended in {days_since} days - OVERDUE!"
        else:
            description = f"{championship.name} needs to be defended soon ({days_since} days since last defense)"
        
        # Create the situation
        situation = TitleSituation(
            title_id=championship.id,
            title_name=championship.name,
            situation_type=TitleSituationType.DEFENSE_OVERDUE,
            severity=severity,
            description=description,
            recommended_actions=[
                'Schedule immediate title defense',
                'Create storyline explaining absence',
                'Consider interim champion if injury'
            ]
        )
        
        # Add champion to involved wrestlers
        if championship.current_holder_id:
            situation.involved_wrestlers.append(championship.current_holder_id)
        
        # Store metadata for detailed tracking
        days_overdue = 0
        if status['is_overdue']:
            days_overdue = days_since - championship.defense_frequency_days
        
        situation.metadata = {
            'days_since_defense': days_since,
            'days_overdue': days_overdue,
            'urgency_level': status['urgency_level'],
            'max_days_allowed': championship.defense_frequency_days,
            'champion_id': championship.current_holder_id,
            'champion_name': championship.current_holder_name,
            'last_defense_year': championship.last_defense_year,
            'last_defense_week': championship.last_defense_week,
            'next_defense_deadline': status.get('next_defense_deadline')
        }
        
        return situation
    
    def check_all_defense_frequencies(
        self,
        championships: List[Championship],
        current_year: int,
        current_week: int
    ) -> List[TitleSituation]:
        """
        Check all championships for overdue or urgent defenses.
        
        STEP 25: Batch defense frequency checking.
        
        Args:
            championships: List of all championships to check
            current_year: Current game year
            current_week: Current game week
        
        Returns:
            List of TitleSituation objects for championships needing attention
        """
        situations = []
        
        for championship in championships:
            situation = self.check_defense_frequency(
                championship,
                current_year,
                current_week
            )
            
            if situation:
                situations.append(situation)
        
        # Sort by severity (high first) and days overdue
        severity_order = {'high': 0, 'medium': 1, 'low': 2}
        situations.sort(
            key=lambda s: (
                severity_order.get(s.severity, 3),
                -(s.metadata.get('days_overdue', 0) if s.metadata else 0)
            )
        )
        
        return situations
    
    def analyze_champion_injury(
        self,
        championship: Championship,
        champion: Wrestler,
        current_year: int,
        current_week: int,
        upcoming_ppv_weeks: int = None
    ) -> Dict[str, Any]:
        """
        Analyze an injured champion situation and provide recommendations.
        
        Returns analysis with:
        - Severity assessment
        - Available options
        - Recommended decision
        - Timeline considerations
        """
        injury_weeks = champion.injury.weeks_remaining
        injury_severity = champion.injury.severity
        injury_description = champion.injury.description
        
        tier = self.hierarchy.get_title_tier(championship)
        requirements = self.hierarchy.get_defense_requirements(championship)
        
        # Calculate defense timeline
        days_until_defense_required = requirements.max_days_between_defenses
        if championship.last_defense_week:
            weeks_since_defense = (current_year - (championship.last_defense_year or current_year)) * 52
            weeks_since_defense += current_week - (championship.last_defense_week or current_week)
            days_since_defense = weeks_since_defense * 7
            days_until_defense_required = requirements.max_days_between_defenses - days_since_defense
        
        weeks_until_defense_required = max(0, days_until_defense_required // 7)
        
        # Determine available options
        available_options = []
        recommended_decision = None
        
        # Option: Wait (only if injury is short enough)
        if injury_weeks <= weeks_until_defense_required:
            available_options.append({
                'decision': TitleDecision.WAIT.value,
                'description': f"Wait {injury_weeks} weeks for {champion.name} to recover",
                'risk_level': 'low',
                'pros': ['Champion retains title', 'No storyline disruption', 'Maintains prestige'],
                'cons': ['Delays title defenses', 'May bore fans if too long']
            })
            recommended_decision = TitleDecision.WAIT
        
        # Option: Interim Champion
        if injury_weeks >= 4 and tier in [TitleTier.WORLD, TitleTier.WOMENS]:
            risk = 'medium' if injury_weeks < 12 else 'low'
            available_options.append({
                'decision': TitleDecision.INTERIM_CHAMPION.value,
                'description': f"Crown an interim champion until {champion.name} returns",
                'risk_level': risk,
                'pros': ['Title stays active', 'Creates new storylines', 'Builds to unification'],
                'cons': ['Dilutes title prestige slightly', 'Complex booking required']
            })
            if injury_weeks >= 8 and not recommended_decision:
                recommended_decision = TitleDecision.INTERIM_CHAMPION
        
        # Option: Vacate
        available_options.append({
            'decision': TitleDecision.VACATE.value,
            'description': f"Vacate the title and hold a tournament",
            'risk_level': 'medium',
            'pros': ['Clean break', 'Tournament creates excitement', 'Fresh champion story'],
            'cons': ['Champion loses reign', 'Prestige hit', 'May feel anticlimactic']
        })
        
        # Option: #1 Contender
        if injury_weeks >= 4:
            available_options.append({
                'decision': TitleDecision.NUMBER_ONE_CONTENDER.value,
                'description': "Determine #1 contender who will face champion upon return",
                'risk_level': 'low',
                'pros': ['Builds anticipation', 'Champion keeps title', 'Creates storyline'],
                'cons': ['Delays title match', 'Contender may get injured too']
            })
        
        # Special case: Very long injury
        if injury_weeks >= 24:
            recommended_decision = TitleDecision.VACATE
            for opt in available_options:
                if opt['decision'] == TitleDecision.VACATE.value:
                    opt['recommended'] = True
        elif injury_weeks >= 12 and recommended_decision is None:
            recommended_decision = TitleDecision.INTERIM_CHAMPION
        elif recommended_decision is None:
            recommended_decision = TitleDecision.WAIT
        
        # PPV consideration
        ppv_urgency = None
        if upcoming_ppv_weeks is not None:
            if upcoming_ppv_weeks <= 2:
                ppv_urgency = "CRITICAL - PPV in {upcoming_ppv_weeks} weeks!"
                if injury_weeks > upcoming_ppv_weeks:
                    # Must decide before PPV
                    recommended_decision = TitleDecision.INTERIM_CHAMPION if tier == TitleTier.WORLD else TitleDecision.VACATE
        
        return {
            'champion_id': champion.id,
            'champion_name': champion.name,
            'title_id': championship.id,
            'title_name': championship.name,
            'title_tier': tier.value,
            'injury': {
                'severity': injury_severity,
                'description': injury_description,
                'weeks_remaining': injury_weeks,
                'estimated_return_week': current_week + injury_weeks
            },
            'defense_timeline': {
                'days_until_required': days_until_defense_required,
                'weeks_until_required': weeks_until_defense_required,
                'is_overdue': days_until_defense_required < 0
            },
            'ppv_urgency': ppv_urgency,
            'available_options': available_options,
            'recommended_decision': recommended_decision.value if recommended_decision else None,
            'analysis_summary': self._generate_analysis_summary(
                champion, championship, injury_weeks, recommended_decision
            )
        }
    
    def _generate_analysis_summary(
        self,
        champion: Wrestler,
        championship: Championship,
        injury_weeks: int,
        recommended: TitleDecision
    ) -> str:
        """Generate human-readable analysis summary"""
        
        if injury_weeks <= 2:
            return f"{champion.name} has a minor injury. Recommend waiting for recovery."
        elif injury_weeks <= 4:
            return f"{champion.name} will miss approximately one month. Consider waiting or building a #1 contender storyline."
        elif injury_weeks <= 8:
            return f"{champion.name} faces 1-2 months on the shelf. An interim champion may be warranted for the {championship.name}."
        elif injury_weeks <= 16:
            return f"{champion.name} is looking at 2-4 months out. Strongly recommend interim champion or vacating the {championship.name}."
        else:
            return f"{champion.name} faces an extended absence of {injury_weeks} weeks. The {championship.name} should be vacated to maintain prestige."
    
    def execute_title_decision(
        self,
        decision: TitleDecision,
        championship: Championship,
        champion: Wrestler,
        year: int,
        week: int,
        show_id: str = None,
        show_name: str = None,
        new_champion: Wrestler = None,
        attacker: Wrestler = None,
        vacancy_reason: VacancyReason = None,
        notes: str = ""
    ) -> TitleDecisionResult:
        """
        Execute a title situation decision.
        
        Handles all the logistics of vacating, creating interim champions,
        granting title shots, and creating angles.
        """
        
        result = TitleDecisionResult(
            decision=decision,
            success=False,
            message="",
            title_id=championship.id,
            title_name=championship.name,
            affected_wrestler_id=champion.id if champion else None,
            affected_wrestler_name=champion.name if champion else None
        )
        
        if decision == TitleDecision.VACATE:
            result = self._execute_vacate(
                championship, champion, year, week, show_id, show_name,
                vacancy_reason or VacancyReason.INJURY, notes, result
            )
        
        elif decision == TitleDecision.INTERIM_CHAMPION:
            if not new_champion:
                result.message = "No interim champion specified"
                return result
            result = self._execute_interim_champion(
                championship, champion, new_champion, year, week,
                show_id, show_name, result
            )
        
        elif decision == TitleDecision.STRIP:
            result = self._execute_strip(
                championship, champion, year, week, show_id, show_name,
                vacancy_reason or VacancyReason.STRIPPED, notes, result
            )
        
        elif decision == TitleDecision.WAIT:
            result.success = True
            result.message = f"Waiting for {champion.name} to recover. No action taken on {championship.name}."
            result.follow_up_actions = [
                "Monitor injury recovery progress",
                "Prepare backup plan if recovery delayed",
                "Build storylines that don't require title"
            ]
        
        elif decision == TitleDecision.NUMBER_ONE_CONTENDER:
            result.success = True
            result.message = f"Will determine #1 contender for {championship.name} while {champion.name} recovers."
            result.follow_up_actions = [
                "Book #1 contender match or tournament",
                "Build contender vs champion anticipation",
                "Schedule title match for champion's return"
            ]
        
        elif decision == TitleDecision.TOURNAMENT:
            result = self._execute_vacate(
                championship, champion, year, week, show_id, show_name,
                vacancy_reason or VacancyReason.INJURY, notes, result
            )
            if result.success:
                result.follow_up_actions.insert(0, "Book multi-person tournament")
                result.message += " A tournament will determine the new champion."
        
        # Generate attack angle if attacker specified
        if attacker and result.success and decision in [TitleDecision.VACATE, TitleDecision.INTERIM_CHAMPION]:
            angle = self.generate_injury_angle(
                champion, attacker, champion.injury.description if champion.injury else "injury"
            )
            result.segment_suggestion = angle.to_dict()
            result.follow_up_actions.append(
                f"Execute injury angle with {attacker.name} as attacker"
            )
        
        return result
    
    def _execute_vacate(
        self,
        championship: Championship,
        champion: Wrestler,
        year: int,
        week: int,
        show_id: str,
        show_name: str,
        reason: VacancyReason,
        notes: str,
        result: TitleDecisionResult
    ) -> TitleDecisionResult:
        """Execute title vacancy"""
        
        # Create vacancy record
        vacancy = self.hierarchy.create_vacancy(
            championship=championship,
            reason=reason,
            year=year,
            week=week,
            show_id=show_id,
            show_name=show_name,
            notes=notes
        )
        
        # Grant guaranteed title shot to outgoing champion
        shot = self.hierarchy.grant_title_shot(
            wrestler_id=champion.id,
            wrestler_name=champion.name,
            title_id=championship.id,
            title_name=championship.name,
            reason='injury_return' if reason == VacancyReason.INJURY else 'former_champion',
            year=year,
            week=week,
            notes=f"Guaranteed shot after relinquishing title due to {reason.value}"
        )
        
        # Vacate the title
        championship.vacate_title(
            show_id=show_id,
            show_name=show_name,
            year=year,
            week=week,
            reason=reason.value
        )
        
        result.success = True
        result.message = f"{champion.name} has vacated the {championship.name} due to {reason.value}."
        result.vacancy_created = True
        result.vacancy_id = vacancy.vacancy_id
        result.guaranteed_shot_granted = True
        result.guaranteed_shot_id = shot.shot_id
        result.follow_up_actions = [
            "Announce vacancy on next show",
            "Determine method to crown new champion",
            f"{champion.name} has guaranteed title shot upon return"
        ]
        
        return result
    
    def _execute_interim_champion(
        self,
        championship: Championship,
        original_champion: Wrestler,
        interim_champion: Wrestler,
        year: int,
        week: int,
        show_id: str,
        show_name: str,
        result: TitleDecisionResult
    ) -> TitleDecisionResult:
        """Create an interim champion"""
        
        # Award interim title
        championship.award_title(
            wrestler_id=interim_champion.id,
            wrestler_name=interim_champion.name,
            show_id=show_id,
            show_name=show_name,
            year=year,
            week=week,
            is_interim=True
        )
        
        result.success = True
        result.message = f"{interim_champion.name} has been crowned Interim {championship.name}!"
        result.new_champion_id = interim_champion.id
        result.new_champion_name = interim_champion.name
        result.interim_created = True
        result.follow_up_actions = [
            f"Book {interim_champion.name} in interim title defenses",
            f"Build toward unification match when {original_champion.name} returns",
            "Consider who interim champion should feud with"
        ]
        
        return result
    
    def _execute_strip(
        self,
        championship: Championship,
        champion: Wrestler,
        year: int,
        week: int,
        show_id: str,
        show_name: str,
        reason: VacancyReason,
        notes: str,
        result: TitleDecisionResult
    ) -> TitleDecisionResult:
        """Strip a champion of their title (no guaranteed rematch)"""
        
        vacancy = self.hierarchy.create_vacancy(
            championship=championship,
            reason=reason,
            year=year,
            week=week,
            show_id=show_id,
            show_name=show_name,
            notes=notes
        )
        
        championship.vacate_title(
            show_id=show_id,
            show_name=show_name,
            year=year,
            week=week,
            reason=reason.value
        )
        
        result.success = True
        result.message = f"{champion.name} has been STRIPPED of the {championship.name}!"
        result.vacancy_created = True
        result.vacancy_id = vacancy.vacancy_id
        result.guaranteed_shot_granted = False  # No guaranteed shot when stripped
        result.follow_up_actions = [
            "Address stripping on next show",
            "Determine new champion via match/tournament",
            f"{champion.name} must earn future title opportunities"
        ]
        
        return result
    
    def generate_injury_angle(
        self,
        victim: Wrestler,
        attacker: Wrestler,
        injury_description: str = "injury",
        body_part: str = "shoulder"
    ) -> InjuryAngleTemplate:
        """
        Generate an injury write-off angle.
        
        Based on Tyler Cross scenario - attacker injures champion,
        creating a ready-made feud for the return.
        """
        
        template = random.choice(self.ATTACK_TEMPLATES)
        
        description = template['description'].format(
            attacker=attacker.name,
            victim=victim.name,
            body_part=body_part
        )
        
        # Generate promo text for attacker
        promo_options = [
            f"THIS IS MY TITLE! MINE! {victim.name} was weak, and I did what had to be done!",
            f"You want to blame someone? Blame {victim.name} for standing in my way!",
            f"I'm not sorry. {victim.name} had this coming. Now, I take what's mine!",
            f"That was just the beginning. When {victim.name} comes back, I'll finish the job!",
            f"Everyone saw what I did to {victim.name}. Anyone who crosses me will end up the same way!"
        ]
        
        return InjuryAngleTemplate(
            angle_type=template['type'],
            description=description,
            attacker_id=attacker.id,
            attacker_name=attacker.name,
            victim_id=victim.id,
            victim_name=victim.name,
            heat_generated=template['heat'],
            creates_feud=True,
            feud_intensity=template['feud_intensity'],
            promo_text=random.choice(promo_options)
        )
    
    def generate_return_angle(
        self,
        returning_wrestler: Wrestler,
        target: Wrestler = None,
        is_ppv: bool = False,
        prefer_surprise: bool = True
    ) -> ReturnAngleTemplate:
        """
        Generate a return from injury angle.
        
        Based on Tyler Cross scenario - dramatic return,
        confrontation with the one who put them out.
        """
        
        # Filter templates based on preferences
        templates = [t for t in self.RETURN_TEMPLATES 
                    if t['is_surprise'] == prefer_surprise or not prefer_surprise]
        
        if not templates:
            templates = self.RETURN_TEMPLATES
        
        # PPV returns get better templates
        if is_ppv:
            templates = sorted(templates, key=lambda t: t['pop'], reverse=True)[:3]
        
        template = random.choice(templates)
        
        description = template['description'].format(
            wrestler=returning_wrestler.name,
            target=target.name if target else "their rival"
        )
        
        # Generate promo text
        promo_options = [
            f"Did you miss me? I told you I'd be back, and now it's time for payback!",
            f"Five months. Five months I've been watching, waiting, healing. Now I'm back, and I want what's MINE!",
            f"You thought you ended my career? You only made me STRONGER!",
            f"The champion is BACK! And I'm coming for whoever has MY title!",
            f"I never forgot what happened. Every single day in rehab, I thought about this moment. Now it's time!"
        ]
        
        return ReturnAngleTemplate(
            angle_type=template['type'],
            description=description,
            returning_wrestler_id=returning_wrestler.id,
            returning_wrestler_name=returning_wrestler.name,
            target_id=target.id if target else None,
            target_name=target.name if target else None,
            is_surprise=template['is_surprise'],
            pop_level=template['pop'],
            momentum_boost=template['momentum'],
            popularity_boost=template['popularity'],
            promo_text=random.choice(promo_options)
        )
    
    def generate_vacancy_announcement(
        self,
        championship: Championship,
        champion: Wrestler,
        reason: str
    ) -> str:
        """Generate authority announcement text for vacating a title"""
        
        template = random.choice(self.VACANCY_ANNOUNCEMENT_TEMPLATES)
        
        return template.format(
            champion=champion.name,
            title=championship.name,
            reason=reason
        )
    
    def get_interim_champion_candidates(
        self,
        championship: Championship,
        roster: List[Wrestler],
        excluded_ids: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get ranked candidates for interim championship.
        
        Considers:
        - Role/position
        - Popularity
        - Momentum
        - Brand alignment
        - Current injury status
        """
        
        excluded = set(excluded_ids or [])
        
        # Add current champion to exclusions
        if championship.current_holder_id:
            excluded.add(championship.current_holder_id)
        
        # Filter eligible candidates
        candidates = []
        
        for wrestler in roster:
            # Skip excluded
            if wrestler.id in excluded:
                continue
            
            # Must be able to compete
            if not wrestler.can_compete:
                continue
            
            # Must be on the right brand (or cross-brand title)
            if championship.assigned_brand != 'Cross-Brand':
                if wrestler.primary_brand != championship.assigned_brand:
                    continue
            
            # Calculate candidate score
            score = 0
            
            # Role weight
            role_scores = {
                'Main Event': 100,
                'Upper Midcard': 75,
                'Midcard': 50,
                'Lower Midcard': 25,
                'Jobber': 10
            }
            score += role_scores.get(wrestler.role, 25)
            
            # Popularity weight
            score += wrestler.popularity * 0.5
            
            # Momentum weight
            score += (wrestler.momentum + 100) * 0.25  # Normalize -100 to 100 -> 0 to 50
            
            # Major superstar bonus
            if wrestler.is_major_superstar:
                score += 30
            
            candidates.append({
                'wrestler_id': wrestler.id,
                'wrestler_name': wrestler.name,
                'role': wrestler.role,
                'popularity': wrestler.popularity,
                'momentum': wrestler.momentum,
                'brand': wrestler.primary_brand,
                'is_major_superstar': wrestler.is_major_superstar,
                'score': round(score, 1)
            })
        
        # Sort by score
        candidates.sort(key=lambda c: c['score'], reverse=True)
        
        return candidates[:10]  # Top 10 candidates
    
    def check_all_title_situations(
        self,
        championships: List[Championship],
        roster: List[Wrestler],
        current_year: int,
        current_week: int
    ) -> List[TitleSituation]:
        """
        Check all championships for situations requiring attention.
        
        Returns list of title situations sorted by urgency.
        """
        
        situations = []
        
        for championship in championships:
            # Get holder
            holder = None
            if championship.current_holder_id:
                holder = next(
                    (w for w in roster if w.id == championship.current_holder_id),
                    None
                )
            
            situation = self.hierarchy.get_title_situation(
                championship=championship,
                holder_wrestler=holder,
                current_year=current_year,
                current_week=current_week,
                last_defense_year=championship.last_defense_year,
                last_defense_week=championship.last_defense_week
            )
            
            situations.append(situation)
        
        # Also check defense frequencies (STEP 25)
        defense_situations = self.check_all_defense_frequencies(
            championships,
            current_year,
            current_week
        )
        
        # Merge defense situations (avoid duplicates by title_id)
        existing_title_ids = {s.title_id for s in situations}
        for defense_sit in defense_situations:
            if defense_sit.title_id not in existing_title_ids:
                situations.append(defense_sit)
            else:
                # Update existing situation with defense info if it's more urgent
                for i, sit in enumerate(situations):
                    if sit.title_id == defense_sit.title_id:
                        if defense_sit.severity == 'high' and sit.severity != 'high':
                            # Add defense overdue alert to existing situation
                            sit.alerts.append(defense_sit.description)
                            if defense_sit.metadata:
                                if not sit.metadata:
                                    sit.metadata = {}
                                sit.metadata.update(defense_sit.metadata)
                        break
        
        # Sort by urgency (issues first)
        situations.sort(
            key=lambda s: (
                s.situation_type != TitleSituationType.NORMAL,
                s.severity == 'high',
                len(s.alerts)
            ),
            reverse=True
        )
        
        return situations
    
    def process_champion_return(
        self,
        championship: Championship,
        returning_champion: Wrestler,
        year: int,
        week: int,
        show_id: str,
        show_name: str,
        current_champion: Wrestler = None,
        unify_immediately: bool = False
    ) -> Dict[str, Any]:
        """
        Process a champion returning from injury.
        
        Handles:
        - Stripping interim champion
        - Scheduling unification match
        - Using guaranteed title shot
        - Applying return boosts
        """
        
        result = {
            'success': True,
            'returning_champion': returning_champion.name,
            'title': championship.name,
            'actions_taken': [],
            'follow_up': []
        }
        
        # Check for active guaranteed shot
        active_shots = self.hierarchy.get_active_guaranteed_shots(
            championship.id, year, week
        )
        
        wrestler_shot = next(
            (s for s in active_shots if s.wrestler_id == returning_champion.id),
            None
        )
        
        if wrestler_shot:
            result['actions_taken'].append(
                f"Guaranteed title shot activated for {returning_champion.name}"
            )
        
        # Handle interim champion situation
        if championship.has_interim_champion:
            if unify_immediately:
                # Returning champ immediately becomes undisputed
                championship.strip_interim_champion(show_id, show_name, year, week)
                result['actions_taken'].append(
                    f"Interim champion stripped. {returning_champion.name} is undisputed champion."
                )
            else:
                # Schedule unification match
                result['follow_up'].append(
                    f"Book {returning_champion.name} vs {championship.interim_holder_name} unification match"
                )
                result['actions_taken'].append("Unification match to be scheduled")
        
        # If title is vacant and they have a shot, they can claim it
        elif championship.is_vacant and wrestler_shot:
            result['follow_up'].append(
                f"{returning_champion.name} has guaranteed shot at vacant title"
            )
        
        # Use the guaranteed shot
        if wrestler_shot:
            self.hierarchy.use_title_shot(wrestler_shot.shot_id, year, week, show_id)
            result['actions_taken'].append("Guaranteed title shot used")
        
        # Apply return boosts to wrestler
        returning_champion.adjust_momentum(40)
        returning_champion.adjust_popularity(15)
        
        result['stat_changes'] = {
            'momentum': '+40',
            'popularity': '+15'
        }
        
        return result
    
    def get_defense_urgency_report(
        self,
        championships: List[Championship],
        current_year: int,
        current_week: int
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive report on defense urgency for all titles.
        
        STEP 25: Summary report for booking decisions.
        
        Returns:
            Dict with summary and detailed breakdown
        """
        report = {
            'summary': {
                'total_titles': len(championships),
                'overdue': 0,
                'urgent': 0,
                'upcoming': 0,
                'healthy': 0
            },
            'overdue_titles': [],
            'urgent_titles': [],
            'upcoming_titles': [],
            'healthy_titles': []
        }
        
        for championship in championships:
            if championship.is_vacant:
                report['summary']['healthy'] += 1
                report['healthy_titles'].append({
                    'title_id': championship.id,
                    'title_name': championship.name,
                    'status': 'vacant'
                })
                continue
            
            status = championship.get_defense_status(current_year, current_week)
            
            title_info = {
                'title_id': championship.id,
                'title_name': championship.name,
                'champion_id': championship.current_holder_id,
                'champion_name': championship.current_holder_name,
                'days_since_defense': status['days_since_defense'],
                'urgency_level': status['urgency_level'],
                'max_days_allowed': championship.defense_frequency_days
            }
            
            if status['is_overdue']:
                report['summary']['overdue'] += 1
                title_info['days_overdue'] = status['days_since_defense'] - championship.defense_frequency_days
                report['overdue_titles'].append(title_info)
            elif status['urgency_level'] >= 3:
                report['summary']['urgent'] += 1
                report['urgent_titles'].append(title_info)
            elif status['urgency_level'] >= 2:
                report['summary']['upcoming'] += 1
                report['upcoming_titles'].append(title_info)
            else:
                report['summary']['healthy'] += 1
                report['healthy_titles'].append(title_info)
        
        return report


# Global title situation manager instance
title_situation_manager = TitleSituationManager()