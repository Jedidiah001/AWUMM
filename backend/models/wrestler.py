"""
Wrestler Model
Represents a professional wrestler with all attributes, stats, and career data.
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
import random

# STEP 122: Import Contract from new dedicated module
from models.contract import Contract


@dataclass
class Injury:
    """Injury information for a wrestler"""
    severity: str  # 'None', 'Minor', 'Moderate', 'Major'
    description: str
    weeks_remaining: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'severity': self.severity,
            'description': self.description,
            'weeks_remaining': self.weeks_remaining
        }
    
    @staticmethod
    def none():
        """Create a no-injury state"""
        return Injury(severity='None', description='Healthy', weeks_remaining=0)


# STEP 122: Remove old Contract dataclass - now in models/contract.py
# Old Contract class deleted - using new enhanced version


class Wrestler:
    """
    Complete wrestler model with all attributes and career tracking.
    
    Attributes are rated 0-100:
    - Brawling: Power moves, strikes, brawling ability
    - Technical: Mat wrestling, submissions, chain wrestling
    - Speed: High-flying, agility, quickness
    - Mic: Promo ability, charisma on the microphone
    - Psychology: In-ring storytelling, selling, match pacing
    - Stamina: Endurance, ability to work long matches
    
    Dynamic Stats (can fluctuate):
    - Popularity: Fan support (0-100)
    - Momentum: Current push status (-100 to 100)
    - Morale: Backstage happiness (-100 to 100)
    - Fatigue: Tiredness level (0-100, higher = more tired)
    """
    
    def __init__(
        self,
        wrestler_id: str,
        name: str,
        age: int,
        gender: str,  # 'Male' or 'Female'
        alignment: str,  # 'Face', 'Heel', 'Tweener'
        role: str,  # 'Main Event', 'Upper Midcard', 'Midcard', 'Lower Midcard', 'Jobber'
        primary_brand: str,  # 'ROC Alpha', 'ROC Velocity', 'ROC Vanguard'
        
        # Core Attributes (0-100)
        brawling: int,
        technical: int,
        speed: int,
        mic: int,
        psychology: int,
        stamina: int,
        
        # Career Data
        years_experience: int,
        is_major_superstar: bool = False,
        
        # Dynamic Stats
        popularity: int = 50,
        momentum: int = 0,
        morale: int = 50,
        fatigue: int = 0,
        
        # Contract
        contract: Optional[Contract] = None,
        
        # Injury
        injury: Optional[Injury] = None,
        
        # Status
        is_retired: bool = False
    ):
        self.id = wrestler_id
        self.name = name
        self.age = age
        self.gender = gender
        self.alignment = alignment
        self.role = role
        self.primary_brand = primary_brand
        
        # Core attributes
        self.brawling = brawling
        self.technical = technical
        self.speed = speed
        self.mic = mic
        self.psychology = psychology
        self.stamina = stamina
        
        # Career
        self.years_experience = years_experience
        self.is_major_superstar = is_major_superstar
        
        # Dynamic stats
        self.popularity = popularity
        self.momentum = momentum
        self.morale = morale
        self.fatigue = fatigue
        
        # Contract
        self.contract = contract or Contract(
            salary_per_show=5000,  # Default $5k per show
            total_length_weeks=52,
            weeks_remaining=52,
            signing_year=1,
            signing_week=1
        )
        
        # Injury
        self.injury = injury or Injury.none()
        
        # Status
        self.is_retired = is_retired
    
    # ========================================================================
    # Computed Properties
    # ========================================================================
    
    @property
    def overall_rating(self) -> int:
        """Calculate overall wrestler rating (0-100)"""
        # Weight attributes differently based on role
        if self.role == 'Main Event':
            weights = {
                'brawling': 0.20,
                'technical': 0.20,
                'speed': 0.15,
                'mic': 0.20,
                'psychology': 0.20,
                'stamina': 0.05
            }
        elif self.role in ['Upper Midcard', 'Midcard']:
            weights = {
                'brawling': 0.20,
                'technical': 0.20,
                'speed': 0.20,
                'mic': 0.10,
                'psychology': 0.20,
                'stamina': 0.10
            }
        else:  # Lower card
            weights = {
                'brawling': 0.25,
                'technical': 0.25,
                'speed': 0.20,
                'mic': 0.05,
                'psychology': 0.15,
                'stamina': 0.10
            }
        
        rating = (
            self.brawling * weights['brawling'] +
            self.technical * weights['technical'] +
            self.speed * weights['speed'] +
            self.mic * weights['mic'] +
            self.psychology * weights['psychology'] +
            self.stamina * weights['stamina']
        )
        
        return int(rating)
    
    @property
    def is_injured(self) -> bool:
        """Check if wrestler is currently injured"""
        return self.injury.severity != 'None' and self.injury.weeks_remaining > 0
    
    @property
    def can_compete(self) -> bool:
        """Check if wrestler can be booked for matches"""
        if self.is_retired:
            return False
        if self.injury.severity in ['Major', 'Moderate']:
            return False
        return True
    
    @property
    def contract_expires_soon(self) -> bool:
        """Check if contract expires within 4 weeks"""
        return self.contract.weeks_remaining <= 4
    
    # ========================================================================
    # Stat Modification Methods
    # ========================================================================
    
    def adjust_popularity(self, delta: int):
        """Adjust popularity, clamped to 0-100"""
        self.popularity = max(0, min(100, self.popularity + delta))
    
    def adjust_momentum(self, delta: int):
        """Adjust momentum, clamped to -100 to 100"""
        self.momentum = max(-100, min(100, self.momentum + delta))
    
    def adjust_morale(self, delta: int):
        """Adjust morale, clamped to -100 to 100"""
        self.morale = max(-100, min(100, self.morale + delta))
    
    def adjust_fatigue(self, delta: int):
        """Adjust fatigue, clamped to 0-100"""
        self.fatigue = max(0, min(100, self.fatigue + delta))
    
    def recover_fatigue(self, amount: int = 20):
        """Recover fatigue (used when wrestler doesn't appear on a show)"""
        self.adjust_fatigue(-amount)
    
    def apply_injury(self, severity: str, description: str, weeks: int):
        """Apply an injury to the wrestler"""
        self.injury = Injury(
            severity=severity,
            description=description,
            weeks_remaining=weeks
        )
    
    def heal_injury(self, weeks_passed: int = 1):
        """Progress injury healing"""
        if self.injury.weeks_remaining > 0:
            self.injury.weeks_remaining -= weeks_passed
            if self.injury.weeks_remaining <= 0:
                self.injury = Injury.none()
    
    def age_one_year(self):
        """
        Age the wrestler by one year and apply attribute degradation.
        Called at year boundaries (Step 10).
        """
        self.age += 1
        
        # Attribute degradation based on age
        if self.age >= 35:
            # Speed and stamina decline first
            self.speed = max(0, self.speed - 1)
            self.stamina = max(0, self.stamina - 1)
        
        if self.age >= 40:
            # More significant decline
            self.speed = max(0, self.speed - 1)
            self.stamina = max(0, self.stamina - 2)
            self.brawling = max(0, self.brawling - 1)
            self.technical = max(0, self.technical - 1)
        
        if self.age >= 45:
            # All attributes decline
            self.speed = max(0, self.speed - 2)
            self.stamina = max(0, self.stamina - 2)
            self.brawling = max(0, self.brawling - 1)
            self.technical = max(0, self.technical - 1)
            self.mic = max(0, self.mic - 1)
            self.psychology = max(0, self.psychology - 1)
    
    def should_retire(self) -> bool:
        """
        Check if wrestler should retire based on age, injuries, and stats.
        """
        # Age threshold
        if self.age < 45:
            return False
        
        # Major injury + old age
        if self.age >= 45 and self.injury.severity == 'Major':
            return random.random() < 0.4  # 40% chance
        
        # Very old with declining stats
        if self.age >= 48:
            avg_attributes = (self.brawling + self.technical + self.speed + 
                            self.mic + self.psychology + self.stamina) / 6
            if avg_attributes < 50:
                return random.random() < 0.6  # 60% chance
        
        # Very low morale + old age
        if self.age >= 45 and self.morale < -50:
            return random.random() < 0.3  # 30% chance
        
        return False
    
    # ========================================================================
    # Serialization
    # ========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert wrestler to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'age': self.age,
            'gender': self.gender,
            'alignment': self.alignment,
            'role': self.role,
            'primary_brand': self.primary_brand,
            
            # Attributes
            'attributes': {
                'brawling': self.brawling,
                'technical': self.technical,
                'speed': self.speed,
                'mic': self.mic,
                'psychology': self.psychology,
                'stamina': self.stamina,
                'overall': self.overall_rating
            },
            
            # Career
            'years_experience': self.years_experience,
            'is_major_superstar': self.is_major_superstar,
            
            # Dynamic stats
            'stats': {
                'popularity': self.popularity,
                'momentum': self.momentum,
                'morale': self.morale,
                'fatigue': self.fatigue
            },
            
            # Contract
            'contract': self.contract.to_dict(),
            
            # Injury
            'injury': self.injury.to_dict(),
            
            # Status
            'is_retired': self.is_retired,
            'is_injured': self.is_injured,
            'can_compete': self.can_compete,
            'contract_expires_soon': self.contract_expires_soon
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Wrestler':
        """Create wrestler from dictionary"""
        attrs = data.get('attributes', {})
        stats = data.get('stats', {})
        contract_data = data.get('contract', {})
        injury_data = data.get('injury', {})
        
        return Wrestler(
            wrestler_id=data['id'],
            name=data['name'],
            age=data['age'],
            gender=data['gender'],
            alignment=data['alignment'],
            role=data['role'],
            primary_brand=data['primary_brand'],
            
            brawling=attrs.get('brawling', 50),
            technical=attrs.get('technical', 50),
            speed=attrs.get('speed', 50),
            mic=attrs.get('mic', 50),
            psychology=attrs.get('psychology', 50),
            stamina=attrs.get('stamina', 50),
            
            years_experience=data.get('years_experience', 5),
            is_major_superstar=data.get('is_major_superstar', False),
            
            popularity=stats.get('popularity', 50),
            momentum=stats.get('momentum', 0),
            morale=stats.get('morale', 50),
            fatigue=stats.get('fatigue', 0),
            
            contract=Contract.from_dict(contract_data) if contract_data else None,
            injury=Injury(
                severity=injury_data.get('severity', 'None'),
                description=injury_data.get('description', 'Healthy'),
                weeks_remaining=injury_data.get('weeks_remaining', 0)
            ) if injury_data else None,
            
            is_retired=data.get('is_retired', False)
        )
    
    def __repr__(self):
        return f"<Wrestler {self.name} ({self.role}, {self.alignment}, {self.primary_brand})>"