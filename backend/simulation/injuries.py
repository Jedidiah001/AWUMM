"""
Injury System
Handles injury generation, severity, recovery tracking, and medical management.
Based on realistic wrestling injury patterns and recovery times.
Fully integrated with SQLite database persistence.
"""

import random
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from models.wrestler import Wrestler, Injury
from persistence.injury_db import (
    save_injury_details, get_injury_details, update_injury_progress,
    delete_injury_details, save_to_injury_history, save_injury_angle,
    save_return_angle, get_medical_staff_config, save_rehab_session,
    update_injury_stats, get_injury_history, update_medical_staff_tier,
    get_all_injured_wrestlers
)


class InjurySeverity(Enum):
    """Injury severity levels with recovery time ranges"""
    MINOR = "Minor"  # 1-3 weeks (bruises, minor sprains)
    MODERATE = "Moderate"  # 4-8 weeks (muscle tears, minor fractures)
    SEVERE = "Severe"  # 12-24 weeks (major tears, surgeries needed)
    CAREER_THREATENING = "Career Threatening"  # 24-52 weeks (major surgeries, potential retirement)


class BodyPart(Enum):
    """Body parts that can be injured"""
    HEAD = "Head"
    NECK = "Neck"
    SHOULDER = "Shoulder"
    ARM = "Arm"
    BACK = "Back"
    RIBS = "Ribs"
    KNEE = "Knee"
    LEG = "Leg"
    ANKLE = "Ankle"
    HAND = "Hand"


@dataclass
class InjuryDetails:
    """Detailed injury information"""
    severity: InjurySeverity
    body_part: BodyPart
    description: str
    weeks_out: int
    requires_surgery: bool = False
    can_appear_limited: bool = False  # Can do promos/segments but not wrestle
    rehab_milestones: List[Dict[str, Any]] = field(default_factory=list)
    occurred_date: Dict[str, int] = field(default_factory=dict)  # year, week
    return_date: Dict[str, int] = field(default_factory=dict)  # estimated return
    medical_costs: int = 0
    rehab_progress: float = 0.0  # 0.0 to 100.0


class InjuryType:
    """Specific injury types with descriptions"""
    
    # Minor injuries (1-3 weeks)
    MINOR_INJURIES = {
        BodyPart.HEAD: ["minor concussion", "cut requiring stitches", "black eye"],
        BodyPart.RIBS: ["bruised ribs", "chest contusion"],
        BodyPart.BACK: ["lower back strain", "muscle spasms"],
        BodyPart.ARM: ["bruised bicep", "minor elbow sprain"],
        BodyPart.LEG: ["hamstring tightness", "quad contusion", "shin splints"],
        BodyPart.ANKLE: ["twisted ankle", "minor sprain"],
        BodyPart.HAND: ["jammed finger", "bruised hand"],
        BodyPart.NECK: ["neck stiffness", "minor whiplash"],
        BodyPart.SHOULDER: ["shoulder bruise", "minor strain"],
        BodyPart.KNEE: ["knee contusion", "minor swelling"]
    }
    
    # Moderate injuries (4-8 weeks)
    MODERATE_INJURIES = {
        BodyPart.HEAD: ["moderate concussion", "orbital bone fracture"],
        BodyPart.NECK: ["neck strain", "cervical sprain"],
        BodyPart.SHOULDER: ["shoulder impingement", "AC joint sprain", "rotator cuff strain"],
        BodyPart.ARM: ["hyperextended elbow", "bicep strain", "tricep tear"],
        BodyPart.BACK: ["herniated disc (minor)", "severe back spasms"],
        BodyPart.RIBS: ["cracked rib", "intercostal strain"],
        BodyPart.KNEE: ["MCL sprain", "knee contusion", "meniscus irritation"],
        BodyPart.LEG: ["hamstring pull", "calf strain", "quad tear (grade 1)"],
        BodyPart.ANKLE: ["high ankle sprain", "ligament damage"],
        BodyPart.HAND: ["fractured finger", "sprained wrist"]
    }
    
    # Severe injuries (12-24 weeks)
    SEVERE_INJURIES = {
        BodyPart.HEAD: ["severe concussion syndrome", "fractured skull"],
        BodyPart.NECK: ["herniated disc (neck)", "cervical fracture"],
        BodyPart.SHOULDER: ["torn labrum", "separated shoulder", "rotator cuff tear"],
        BodyPart.ARM: ["broken arm", "torn bicep", "dislocated elbow"],
        BodyPart.BACK: ["herniated disc (severe)", "compression fracture"],
        BodyPart.RIBS: ["multiple broken ribs", "punctured lung"],
        BodyPart.KNEE: ["torn ACL", "torn meniscus", "PCL tear"],
        BodyPart.LEG: ["broken leg", "complete hamstring tear", "torn quadricep"],
        BodyPart.ANKLE: ["broken ankle", "complete ligament tear"],
        BodyPart.HAND: ["broken hand", "torn ligaments in wrist"]
    }
    
    # Career-threatening injuries (24-52 weeks)
    CAREER_THREATENING_INJURIES = {
        BodyPart.NECK: ["spinal fusion needed", "multiple herniated discs"],
        BodyPart.SHOULDER: ["complete rotator cuff destruction", "chronic labrum tears"],
        BodyPart.BACK: ["spinal stenosis", "multiple compression fractures"],
        BodyPart.KNEE: ["complete knee reconstruction", "multiple ligament tears"],
        BodyPart.HEAD: ["post-concussion syndrome", "neurological damage"]
    }


class MedicalStaff:
    """Medical staff that affects recovery times"""
    
    STAFF_TIERS = {
        "Basic": {
            "recovery_modifier": 1.0,
            "cost_per_week": 5000,
            "injury_prevention": 0.0,
            "misdiagnosis_chance": 0.10
        },
        "Standard": {
            "recovery_modifier": 0.95,
            "cost_per_week": 10000,
            "injury_prevention": 0.02,
            "misdiagnosis_chance": 0.05
        },
        "Premium": {
            "recovery_modifier": 0.90,
            "cost_per_week": 20000,
            "injury_prevention": 0.05,
            "misdiagnosis_chance": 0.02
        },
        "Elite": {
            "recovery_modifier": 0.85,
            "cost_per_week": 35000,
            "injury_prevention": 0.08,
            "misdiagnosis_chance": 0.01
        },
        "World Class": {
            "recovery_modifier": 0.75,
            "cost_per_week": 50000,
            "injury_prevention": 0.12,
            "misdiagnosis_chance": 0.0
        }
    }


class InjurySimulator:
    """Main injury simulation engine"""
    
    def __init__(self, medical_staff_tier: str = "Standard"):
        self.medical_staff_tier = medical_staff_tier
        self.staff_config = MedicalStaff.STAFF_TIERS.get(medical_staff_tier, MedicalStaff.STAFF_TIERS["Standard"])
        
    def check_for_injury(
        self,
        wrestler: Wrestler,
        match_duration: int,
        match_type: str,
        took_big_bump: bool = False,
        is_ppv: bool = False
    ) -> Optional[InjuryDetails]:
        """
        Check if a wrestler gets injured during a match.
        
        Returns InjuryDetails if injured, None otherwise.
        """
        
        # Base injury chance
        base_chance = 0.02  # 2% base chance
        
        # Modifiers
        if match_duration > 20:
            base_chance += 0.02  # Longer matches more dangerous
        if match_duration > 30:
            base_chance += 0.03
            
        # High-risk styles
        if wrestler.speed > 80:  # High flyers
            base_chance += 0.015
        if wrestler.brawling > 80:  # Brawlers
            base_chance += 0.01
            
        # Match type modifiers
        match_type_modifiers = {
            "ladder": 0.05,
            "cage": 0.03,
            "no_dq": 0.02,
            "tables": 0.03,
            "tlc": 0.06,
            "hell_in_cell": 0.04,
            "elimination_chamber": 0.05,
            "rumble": 0.02,
            "battle_royal": 0.015,
            "hardcore": 0.04
        }
        base_chance += match_type_modifiers.get(match_type, 0)
        
        # Special circumstances
        if took_big_bump:
            base_chance += 0.04
        if is_ppv:
            base_chance += 0.01  # Wrestlers go harder at PPVs
            
        # Age factor
        if wrestler.age >= 35:
            base_chance += 0.01
        if wrestler.age >= 40:
            base_chance += 0.02
        if wrestler.age >= 45:
            base_chance += 0.03
            
        # Fatigue factor
        if wrestler.fatigue > 70:
            base_chance += 0.02
        if wrestler.fatigue > 90:
            base_chance += 0.03
            
        # Previous injury history (reinjury risk)
        if wrestler.is_injured:
            base_chance += 0.05  # Shouldn't be wrestling injured, but if they are...
            
        # Medical staff prevention
        base_chance -= self.staff_config["injury_prevention"]
        base_chance = max(0.005, base_chance)  # Minimum 0.5% chance
        
        # Roll for injury
        if random.random() < base_chance:
            return self._generate_injury(wrestler, match_type, match_duration)
        
        return None
    
    def _generate_injury(
        self,
        wrestler: Wrestler,
        match_type: str,
        match_duration: int
    ) -> InjuryDetails:
        """Generate injury details when an injury occurs"""
        
        # Determine severity (weighted probabilities)
        severity_weights = [65, 25, 8, 2]  # Minor, Moderate, Severe, Career-threatening
        
        # Modify weights based on circumstances
        if match_type in ["ladder", "tlc", "hell_in_cell", "elimination_chamber"]:
            severity_weights = [45, 35, 15, 5]  # More severe in dangerous matches
        if wrestler.age >= 40:
            severity_weights = [50, 30, 15, 5]  # Older wrestlers get hurt worse
        if match_duration > 30:
            severity_weights = [55, 30, 12, 3]
            
        severity = random.choices(
            list(InjurySeverity),
            weights=severity_weights
        )[0]
        
        # Determine body part (weighted by match type)
        body_part = self._determine_body_part(match_type)
        
        # Get specific injury description
        injury_description = self._get_injury_description(severity, body_part)
        
        # Calculate time out
        weeks_out = self._calculate_recovery_time(severity, wrestler.age)
        
        # Determine if surgery required
        requires_surgery = self._requires_surgery(severity, body_part)
        
        # Can they do limited appearances?
        can_appear = severity == InjurySeverity.MINOR or (
            severity == InjurySeverity.MODERATE and body_part not in [BodyPart.HEAD, BodyPart.NECK]
        )
        
        # Calculate medical costs
        medical_costs = self._calculate_medical_costs(severity, requires_surgery)
        
        # Create rehab milestones
        rehab_milestones = self._create_rehab_milestones(severity, weeks_out)
        
        return InjuryDetails(
            severity=severity,
            body_part=body_part,
            description=injury_description,
            weeks_out=weeks_out,
            requires_surgery=requires_surgery,
            can_appear_limited=can_appear,
            rehab_milestones=rehab_milestones,
            medical_costs=medical_costs,
            rehab_progress=0.0
        )
    
    def _determine_body_part(self, match_type: str) -> BodyPart:
        """Determine which body part gets injured based on match type"""
        
        # Default weights
        weights = {
            BodyPart.HEAD: 10,
            BodyPart.NECK: 8,
            BodyPart.SHOULDER: 15,
            BodyPart.ARM: 10,
            BodyPart.BACK: 15,
            BodyPart.RIBS: 10,
            BodyPart.KNEE: 15,
            BodyPart.LEG: 10,
            BodyPart.ANKLE: 5,
            BodyPart.HAND: 2
        }
        
        # Modify by match type
        if match_type in ["ladder", "tlc"]:
            weights[BodyPart.BACK] += 10
            weights[BodyPart.RIBS] += 5
            weights[BodyPart.LEG] += 5
        elif match_type == "submission":
            weights[BodyPart.KNEE] += 10
            weights[BodyPart.SHOULDER] += 5
            weights[BodyPart.ARM] += 5
        elif match_type in ["no_dq", "hardcore", "cage"]:
            weights[BodyPart.HEAD] += 5
            weights[BodyPart.BACK] += 5
        elif match_type == "rumble":
            weights[BodyPart.SHOULDER] += 5
            weights[BodyPart.BACK] += 5
            
        return random.choices(
            list(weights.keys()),
            weights=list(weights.values())
        )[0]
    
    def _get_injury_description(self, severity: InjurySeverity, body_part: BodyPart) -> str:
        """Get specific injury description"""
        
        injury_map = {
            InjurySeverity.MINOR: InjuryType.MINOR_INJURIES,
            InjurySeverity.MODERATE: InjuryType.MODERATE_INJURIES,
            InjurySeverity.SEVERE: InjuryType.SEVERE_INJURIES,
            InjurySeverity.CAREER_THREATENING: InjuryType.CAREER_THREATENING_INJURIES
        }
        
        injuries_dict = injury_map[severity]
        injuries = injuries_dict.get(body_part, ["unspecified injury"])
        
        # Handle career-threatening which doesn't cover all body parts
        if not injuries and severity == InjurySeverity.CAREER_THREATENING:
            # Fall back to severe injury for that body part
            injuries = InjuryType.SEVERE_INJURIES.get(body_part, ["severe injury"])
            
        return random.choice(injuries)
    
    def _calculate_recovery_time(self, severity: InjurySeverity, age: int) -> int:
        """Calculate recovery time in weeks"""
        
        base_times = {
            InjurySeverity.MINOR: (1, 3),
            InjurySeverity.MODERATE: (4, 8),
            InjurySeverity.SEVERE: (12, 24),
            InjurySeverity.CAREER_THREATENING: (24, 52)
        }
        
        min_weeks, max_weeks = base_times[severity]
        weeks = random.randint(min_weeks, max_weeks)
        
        # Age modifier
        if age >= 35:
            weeks = int(weeks * 1.1)
        if age >= 40:
            weeks = int(weeks * 1.2)
        if age >= 45:
            weeks = int(weeks * 1.3)
            
        # Medical staff modifier
        weeks = int(weeks * self.staff_config["recovery_modifier"])
        
        return max(1, weeks)  # Minimum 1 week
    
    def _requires_surgery(self, severity: InjurySeverity, body_part: BodyPart) -> bool:
        """Determine if injury requires surgery"""
        
        if severity == InjurySeverity.MINOR:
            return False
        elif severity == InjurySeverity.MODERATE:
            return random.random() < 0.2  # 20% chance
        elif severity == InjurySeverity.SEVERE:
            # High chance for certain body parts
            if body_part in [BodyPart.SHOULDER, BodyPart.KNEE, BodyPart.NECK]:
                return random.random() < 0.8
            return random.random() < 0.6
        else:  # Career threatening
            return random.random() < 0.9  # 90% chance
    
    def _calculate_medical_costs(self, severity: InjurySeverity, surgery: bool) -> int:
        """Calculate medical costs for the injury"""
        
        base_costs = {
            InjurySeverity.MINOR: 5000,
            InjurySeverity.MODERATE: 15000,
            InjurySeverity.SEVERE: 50000,
            InjurySeverity.CAREER_THREATENING: 100000
        }
        
        cost = base_costs[severity]
        
        if surgery:
            surgery_costs = {
                InjurySeverity.MODERATE: 20000,
                InjurySeverity.SEVERE: 75000,
                InjurySeverity.CAREER_THREATENING: 150000
            }
            cost += surgery_costs.get(severity, 0)
            
        # Add random variance
        cost = int(cost * random.uniform(0.8, 1.2))
            
        return cost
    
    def _create_rehab_milestones(self, severity: InjurySeverity, weeks_out: int) -> List[Dict[str, Any]]:
        """Create rehabilitation milestones"""
        
        milestones = []
        
        if severity == InjurySeverity.MINOR:
            milestones = [
                {"week": 1, "description": "Rest and recovery", "progress": 50},
                {"week": weeks_out, "description": "Cleared to compete", "progress": 100}
            ]
        elif severity == InjurySeverity.MODERATE:
            milestones = [
                {"week": 2, "description": "Begin physical therapy", "progress": 20},
                {"week": weeks_out // 2, "description": "Light training", "progress": 50},
                {"week": weeks_out - 1, "description": "Full training", "progress": 90},
                {"week": weeks_out, "description": "Cleared to compete", "progress": 100}
            ]
        elif severity == InjurySeverity.SEVERE:
            if weeks_out >= 12:
                milestones = [
                    {"week": 2, "description": "Surgery completed", "progress": 10},
                    {"week": 4, "description": "Begin rehab", "progress": 20},
                    {"week": 8, "description": "Range of motion restored", "progress": 35},
                    {"week": 12, "description": "Strength training begins", "progress": 50},
                    {"week": weeks_out - 4, "description": "Ring training", "progress": 80},
                    {"week": weeks_out - 1, "description": "Final evaluation", "progress": 95},
                    {"week": weeks_out, "description": "Cleared to compete", "progress": 100}
                ]
        else:  # Career threatening
            milestones = [
                {"week": 1, "description": "Initial surgery", "progress": 5},
                {"week": 4, "description": "Post-op recovery", "progress": 10},
                {"week": 8, "description": "Begin basic rehab", "progress": 15},
                {"week": 16, "description": "Intensive therapy", "progress": 30},
                {"week": 24, "description": "Strength rebuilding", "progress": 50},
                {"week": 32, "description": "Athletic training", "progress": 70},
                {"week": weeks_out - 4, "description": "Return to ring training", "progress": 85},
                {"week": weeks_out - 1, "description": "Final medical clearance", "progress": 95},
                {"week": weeks_out, "description": "Cleared to compete", "progress": 100}
            ]
            
        return milestones
    
    def attempt_rushed_return(self, wrestler: Wrestler, injury_details: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Attempt to return early from injury.
        High risk of reinjury.
        """
        
        rehab_progress = injury_details.get('rehab_progress', 0)
        
        if rehab_progress < 75:
            return False, "Medical staff refuses to clear - too risky"
            
        # Calculate risk
        risk_factor = (100 - rehab_progress) / 100
        reinjury_chance = 0.3 + (risk_factor * 0.4)  # 30-70% chance
        
        # Account for misdiagnosis chance
        if random.random() < self.staff_config["misdiagnosis_chance"]:
            # Medical staff misdiagnosed - higher reinjury risk
            reinjury_chance += 0.2
        
        if random.random() < reinjury_chance:
            # Reinjured - make it worse
            additional_weeks = random.randint(4, 12)
            return False, f"REINJURED during evaluation - {additional_weeks} more weeks added to recovery!"
            
        # Successful early return
        return True, "Miraculously cleared for early return!"


class InjuryAngleGenerator:
    """Generate creative angles for injury write-offs"""
    
    ATTACK_SCENARIOS = [
        {
            "type": "backstage_attack",
            "description": "{attacker} brutally attacked {victim} backstage with a steel chair",
            "heat_generated": 30
        },
        {
            "type": "parking_lot_ambush", 
            "description": "{attacker} ambushed {victim} in the parking lot",
            "heat_generated": 25
        },
        {
            "type": "post_match_assault",
            "description": "{attacker} assaulted {victim} after their match",
            "heat_generated": 20
        },
        {
            "type": "injury_during_match",
            "description": "{victim} suffered the injury during a match with {attacker}",
            "heat_generated": 15
        },
        {
            "type": "contract_signing_attack",
            "description": "{attacker} attacked {victim} during a contract signing",
            "heat_generated": 35
        },
        {
            "type": "sneak_attack",
            "description": "{attacker} blindsided {victim} during their entrance",
            "heat_generated": 25
        }
    ]
    
    @classmethod
    def generate_injury_angle(
        cls,
        injured_wrestler: Wrestler,
        attacker: Optional[Wrestler] = None,
        existing_feud: bool = False
    ) -> Dict[str, Any]:
        """Generate a creative angle to write off an injured wrestler"""
        
        scenario = random.choice(cls.ATTACK_SCENARIOS)
        
        if not attacker:
            # Need to choose an attacker - prefer heels
            attacker_name = "a masked attacker"
        else:
            attacker_name = attacker.name
            
        description = scenario["description"].format(
            attacker=attacker_name,
            victim=injured_wrestler.name
        )
        
        angle = {
            "type": scenario["type"],
            "description": description,
            "injured_wrestler_id": injured_wrestler.id,
            "injured_wrestler_name": injured_wrestler.name,
            "attacker_id": attacker.id if attacker else None,
            "attacker_name": attacker_name,
            "heat_generated": scenario["heat_generated"],
            "creates_feud": not existing_feud,
            "feud_intensity": 50 if not existing_feud else 20
        }
        
        return angle
    
    @classmethod
    def generate_return_angle(
        cls,
        returning_wrestler: Wrestler,
        is_surprise: bool = True,
        target: Optional[Wrestler] = None,
        weeks_out: int = 0
    ) -> Dict[str, Any]:
        """Generate a return angle for a wrestler coming back from injury"""
        
        if is_surprise:
            scenarios = [
                "{wrestler} makes a SHOCKING return during the main event!",
                "{wrestler}'s music hits! They're BACK!",
                "{wrestler} returns through the crowd to confront {target}!",
                "The lights go out... {wrestler} IS HERE!",
                "{wrestler} emerges from under the ring to attack {target}!"
            ]
        else:
            scenarios = [
                "{wrestler} returns after {weeks} weeks to reclaim their spot",
                "{wrestler} is finally cleared and ready for revenge",
                "{wrestler} makes their triumphant return to action",
                "{wrestler} is back and looking for {target}"
            ]
            
        description = random.choice(scenarios).format(
            wrestler=returning_wrestler.name,
            target=target.name if target else "the champion",
            weeks=weeks_out
        )
        
        return {
            "type": "return_angle",
            "description": description,
            "wrestler_id": returning_wrestler.id,
            "wrestler_name": returning_wrestler.name,
            "is_surprise": is_surprise,
            "target_id": target.id if target else None,
            "target_name": target.name if target else None,
            "momentum_boost": 40 if is_surprise else 20,
            "popularity_boost": 20 if is_surprise else 10
        }


class InjuryManager:
    """Main injury management system with database integration"""
    
    def __init__(self, database, medical_staff_tier: str = "Standard"):
        self.database = database
        self.simulator = InjurySimulator(medical_staff_tier)
        self.angle_generator = InjuryAngleGenerator
        
        # Load medical staff config from database
        config = get_medical_staff_config(database)
        if config:
            self.simulator.medical_staff_tier = config['tier']
            self.simulator.staff_config = {
                'recovery_modifier': config['recovery_modifier'],
                'cost_per_week': config['cost_per_week'],
                'injury_prevention': config['injury_prevention'],
                'misdiagnosis_chance': config['misdiagnosis_chance']
            }
    
    def apply_injury_to_wrestler(
        self,
        wrestler: Wrestler,
        injury_details: InjuryDetails,
        year: int,
        week: int,
        show_id: str = None,
        show_name: str = None
    ) -> InjuryDetails:
        """Apply injury to wrestler and save to database"""
        
        # Apply to wrestler model
        wrestler.apply_injury(
            severity=injury_details.severity.value,
            description=injury_details.description,
            weeks=injury_details.weeks_out
        )
        
        # Set occurred date
        injury_details.occurred_date = {'year': year, 'week': week}
        
        # Calculate estimated return
        estimated_year = year
        estimated_week = week + injury_details.weeks_out
        
        # Adjust for year overflow
        while estimated_week > 52:
            estimated_week -= 52
            estimated_year += 1
            
        injury_details.return_date = {'year': estimated_year, 'week': estimated_week}
        
        # Save detailed injury info to database
        save_injury_details(self.database, wrestler.id, {
            'severity': injury_details.severity.value,
            'body_part': injury_details.body_part.value,
            'description': injury_details.description,
            'weeks_out': injury_details.weeks_out,
            'weeks_remaining': injury_details.weeks_out,
            'requires_surgery': injury_details.requires_surgery,
            'surgery_completed': False,
            'can_appear_limited': injury_details.can_appear_limited,
            'medical_costs': injury_details.medical_costs,
            'rehab_progress': 0.0,
            'rehab_milestones': injury_details.rehab_milestones,
            'occurred_year': year,
            'occurred_week': week,
            'occurred_show_id': show_id,
            'occurred_show_name': show_name,
            'estimated_return_year': estimated_year,
            'estimated_return_week': estimated_week
        })
        
        return injury_details
    
    def process_match_injuries(
        self,
        match_result,
        wrestlers: List[Wrestler],
        match_type: str,
        year: int,
        week: int,
        show_id: str = None,
        show_name: str = None,
        is_ppv: bool = False
    ) -> List[Dict[str, Any]]:
        """Check for injuries after a match"""
        
        injuries = []
        
        for wrestler in wrestlers:
            # Skip if already injured (shouldn't be wrestling)
            if wrestler.is_injured:
                continue
                
            # Check for injury
            injury = self.simulator.check_for_injury(
                wrestler=wrestler,
                match_duration=match_result.duration_minutes,
                match_type=match_type,
                took_big_bump=match_result.star_rating >= 4.5,
                is_ppv=is_ppv
            )
            
            if injury:
                # Apply injury to wrestler and database
                self.apply_injury_to_wrestler(
                    wrestler=wrestler,
                    injury_details=injury,
                    year=year,
                    week=week,
                    show_id=show_id,
                    show_name=show_name
                )
                
                # Add to injuries list
                injuries.append({
                    'wrestler_id': wrestler.id,
                    'wrestler_name': wrestler.name,
                    'severity': injury.severity.value,
                    'body_part': injury.body_part.value,
                    'description': injury.description,
                    'weeks_out': injury.weeks_out,
                    'requires_surgery': injury.requires_surgery,
                    'medical_costs': injury.medical_costs
                })
                
        return injuries
    
    def create_injury_writeoff(
        self,
        injured_wrestler: Wrestler,
        roster: List[Wrestler],
        existing_feuds: List,
        year: int,
        week: int,
        show_id: str = None,
        show_name: str = None
    ) -> Dict[str, Any]:
        """Create an angle to write off an injured wrestler"""
        
        # Find suitable attacker (prefer existing feud partner)
        attacker = None
        existing_feud = False
        
        for feud in existing_feuds:
            if injured_wrestler.id in feud.participant_ids:
                other_id = [pid for pid in feud.participant_ids if pid != injured_wrestler.id][0]
                attacker = next((w for w in roster if w.id == other_id), None)
                if attacker:
                    existing_feud = True
                    break
                    
        # If no feud partner, pick a heel
        if not attacker:
            heels = [w for w in roster if w.alignment == "Heel" and not w.is_injured and w.id != injured_wrestler.id]
            if heels:
                attacker = random.choice(heels)
                
        angle = self.angle_generator.generate_injury_angle(
            injured_wrestler=injured_wrestler,
            attacker=attacker,
            existing_feud=existing_feud
        )
        
        # Add show details
        angle['show_id'] = show_id
        angle['show_name'] = show_name or f'Week {week} Show'
        angle['year'] = year
        angle['week'] = week
        
        # Save to database
        save_injury_angle(self.database, angle)
        
        return angle
    
    def process_weekly_recovery(self, roster: List[Wrestler], year: int, week: int) -> List[Dict[str, Any]]:
        """Process recovery for all injured wrestlers with database tracking"""
        
        recovery_updates = []
        
        for wrestler in roster:
            if not wrestler.is_injured:
                continue
            
            # Get detailed injury info from database
            injury_info = get_injury_details(self.database, wrestler.id)
            
            if not injury_info:
                # Simple recovery without detailed tracking
                wrestler.heal_injury(1)
                if not wrestler.is_injured:
                    recovery_updates.append({
                        'wrestler_id': wrestler.id,
                        'wrestler_name': wrestler.name,
                        'status': 'recovered',
                        'message': f"{wrestler.name} has recovered from injury!"
                    })
            else:
                # Detailed recovery with milestones
                old_weeks = injury_info['weeks_remaining']
                injury_info['weeks_remaining'] -= 1
                
                # Update progress
                total_weeks = injury_info['weeks_out']
                weeks_completed = total_weeks - injury_info['weeks_remaining']
                progress = (weeks_completed / total_weeks) * 100
                
                # Update in database
                update_injury_progress(
                    self.database,
                    wrestler.id,
                    1,
                    progress
                )
                
                # Update wrestler model
                wrestler.heal_injury(1)
                
                # Check for milestones
                milestones = injury_info.get('rehab_milestones', [])
                milestone_message = None
                
                for milestone in milestones:
                    if milestone['week'] == weeks_completed:
                        milestone_message = milestone['description']
                        
                        # Save rehab session
                        save_rehab_session(self.database, {
                            'wrestler_id': wrestler.id,
                            'session_week': weeks_completed,
                            'session_type': 'milestone',
                            'progress_made': milestone['progress'],
                            'milestone_achieved': milestone_message,
                            'therapist_notes': f"Achieved: {milestone_message}",
                            'year': year,
                            'week': week
                        })
                        break
                
                # Check if fully recovered
                if injury_info['weeks_remaining'] <= 0:
                    # Save to history
                    save_to_injury_history(self.database, wrestler.id, {
                        'wrestler_name': wrestler.name,
                        'severity': injury_info['severity'],
                        'body_part': injury_info['body_part'],
                        'description': injury_info['description'],
                        'occurred_year': injury_info['occurred_year'],
                        'occurred_week': injury_info['occurred_week'],
                        'occurred_show_id': injury_info.get('occurred_show_id'),
                        'occurred_show_name': injury_info.get('occurred_show_name', 'Unknown'),
                        'weeks_missed': injury_info['weeks_out'],
                        'required_surgery': injury_info['requires_surgery'],
                        'medical_costs': injury_info['medical_costs'],
                        'return_year': year,
                        'return_week': week
                    })
                    
                    # Update stats
                    update_injury_stats(
                        self.database,
                        wrestler.id,
                        injury_info['severity'],
                        injury_info['weeks_out'],
                        injury_info['medical_costs'],
                        injury_info['requires_surgery']
                    )
                    
                    # Delete detailed injury
                    delete_injury_details(self.database, wrestler.id)
                    
                    recovery_updates.append({
                        'wrestler_id': wrestler.id,
                        'wrestler_name': wrestler.name,
                        'status': 'recovered',
                        'message': f"{wrestler.name} has fully recovered and is cleared to compete!",
                        'weeks_missed': injury_info['weeks_out']
                    })
                elif milestone_message:
                    recovery_updates.append({
                        'wrestler_id': wrestler.id,
                        'wrestler_name': wrestler.name,
                        'status': 'milestone',
                        'message': f"{wrestler.name}: {milestone_message}",
                        'weeks_remaining': injury_info['weeks_remaining'],
                        'progress': progress
                    })
        
        return recovery_updates
    
    def get_injury_report(self, roster: List[Wrestler]) -> Dict[str, Any]:
        """Get comprehensive injury report"""
        
        injured = [w for w in roster if w.is_injured]
        
        by_severity = {
            'Minor': [],
            'Moderate': [],
            'Severe': [],
            'Career Threatening': []
        }
        
        total_costs = 0
        
        for wrestler in injured:
            # Get detailed info from database
            injury_info = get_injury_details(self.database, wrestler.id)
            
            wrestler_info = {
                'wrestler_id': wrestler.id,
                'wrestler_name': wrestler.name,
                'severity': wrestler.injury.severity,
                'description': wrestler.injury.description,
                'weeks_remaining': wrestler.injury.weeks_remaining
            }
            
            if injury_info:
                wrestler_info.update({
                    'body_part': injury_info['body_part'],
                    'requires_surgery': injury_info['requires_surgery'],
                    'can_appear_limited': injury_info['can_appear_limited'],
                    'rehab_progress': injury_info['rehab_progress'],
                    'medical_costs': injury_info['medical_costs']
                })
                total_costs += injury_info['medical_costs']
            
            by_severity[wrestler.injury.severity].append(wrestler_info)
                
        return {
            'total_injured': len(injured),
            'by_severity': by_severity,
            'total_medical_costs': total_costs,
            'injured_list': [w.to_dict() for w in injured],
            'medical_staff_tier': self.simulator.medical_staff_tier,
            'medical_staff_cost_per_week': self.simulator.staff_config['cost_per_week']
        }
    
    def upgrade_medical_staff(self, new_tier: str) -> bool:
        """Upgrade medical staff tier"""
        
        if new_tier not in MedicalStaff.STAFF_TIERS:
            return False
        
        # Update in simulator
        self.simulator.medical_staff_tier = new_tier
        self.simulator.staff_config = MedicalStaff.STAFF_TIERS[new_tier]
        
        # Save to database
        update_medical_staff_tier(self.database, new_tier, self.simulator.staff_config)
        
        return True


# Global injury manager instance (will be initialized in app.py with database)
injury_manager = None