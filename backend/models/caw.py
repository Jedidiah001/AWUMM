"""
Create-A-Wrestler (CAW) Utility
Handles validation and creation of custom wrestlers.
"""

from typing import Dict, Any, Optional, List
from models.wrestler import Wrestler, Contract, Injury
from datetime import datetime
import re


class CAWValidator:
    """Validates Create-A-Wrestler input data"""
    
    VALID_GENDERS = ['Male', 'Female']
    VALID_ROLES = ['Main Event', 'Upper Midcard', 'Midcard', 'Lower Midcard', 'Jobber']
    VALID_BRANDS = ['ROC Alpha', 'ROC Velocity', 'ROC Vanguard']
    
    MIN_AGE = 18
    MAX_AGE = 55
    
    MIN_ATTRIBUTE = 0
    MAX_ATTRIBUTE = 100
    
    MIN_SALARY = 1000
    MAX_SALARY = 100000
    
    MIN_CONTRACT_WEEKS = 1
    MAX_CONTRACT_WEEKS = 260  # 5 years max
    
    @staticmethod
    def validate_name(name: str) -> tuple[bool, str]:
        """Validate wrestler name"""
        if not name or not name.strip():
            return False, "Name cannot be empty"
        
        if len(name) < 2:
            return False, "Name must be at least 2 characters"
        
        if len(name) > 50:
            return False, "Name cannot exceed 50 characters"
        
        # Check for valid characters (letters, spaces, hyphens, apostrophes)
        if not re.match(r"^[a-zA-Z\s\-\'\.]+$", name):
            return False, "Name contains invalid characters"
        
        return True, ""
    
    @staticmethod
    def validate_age(age: int) -> tuple[bool, str]:
        """Validate wrestler age"""
        if age < CAWValidator.MIN_AGE:
            return False, f"Age must be at least {CAWValidator.MIN_AGE}"
        
        if age > CAWValidator.MAX_AGE:
            return False, f"Age cannot exceed {CAWValidator.MAX_AGE}"
        
        return True, ""
    
    @staticmethod
    def validate_attribute(value: int, attribute_name: str) -> tuple[bool, str]:
        """Validate attribute value (0-100)"""
        if value < CAWValidator.MIN_ATTRIBUTE:
            return False, f"{attribute_name} cannot be below {CAWValidator.MIN_ATTRIBUTE}"
        
        if value > CAWValidator.MAX_ATTRIBUTE:
            return False, f"{attribute_name} cannot exceed {CAWValidator.MAX_ATTRIBUTE}"
        
        return True, ""
    
    @staticmethod
    def validate_gender(gender: str) -> tuple[bool, str]:
        """Validate gender"""
        if gender not in CAWValidator.VALID_GENDERS:
            return False, f"Gender must be one of: {', '.join(CAWValidator.VALID_GENDERS)}"
        
        return True, ""
    
    @staticmethod
    def validate_role(role: str) -> tuple[bool, str]:
        """Validate role"""
        if role not in CAWValidator.VALID_ROLES:
            return False, f"Role must be one of: {', '.join(CAWValidator.VALID_ROLES)}"
        
        return True, ""
    
    @staticmethod
    def validate_brand(brand: str) -> tuple[bool, str]:
        """Validate brand"""
        if brand not in CAWValidator.VALID_BRANDS:
            return False, f"Brand must be one of: {', '.join(CAWValidator.VALID_BRANDS)}"
        
        return True, ""
    
    @staticmethod
    def validate_salary(salary: int) -> tuple[bool, str]:
        """Validate salary"""
        if salary < CAWValidator.MIN_SALARY:
            return False, f"Salary must be at least ${CAWValidator.MIN_SALARY:,}"
        
        if salary > CAWValidator.MAX_SALARY:
            return False, f"Salary cannot exceed ${CAWValidator.MAX_SALARY:,}"
        
        return True, ""
    
    @staticmethod
    def validate_contract_weeks(weeks: int) -> tuple[bool, str]:
        """Validate contract length"""
        if weeks < CAWValidator.MIN_CONTRACT_WEEKS:
            return False, f"Contract must be at least {CAWValidator.MIN_CONTRACT_WEEKS} week"
        
        if weeks > CAWValidator.MAX_CONTRACT_WEEKS:
            return False, f"Contract cannot exceed {CAWValidator.MAX_CONTRACT_WEEKS} weeks"
        
        return True, ""
    
    @staticmethod
    def validate_all(data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate all CAW data at once.
        Returns (is_valid, list_of_errors)
        """
        errors = []
        
        # Name
        valid, error = CAWValidator.validate_name(data.get('name', ''))
        if not valid:
            errors.append(error)
        
        # Age
        valid, error = CAWValidator.validate_age(data.get('age', 0))
        if not valid:
            errors.append(error)
        
        # Gender
        valid, error = CAWValidator.validate_gender(data.get('gender', ''))
        if not valid:
            errors.append(error)
        
        # Role
        valid, error = CAWValidator.validate_role(data.get('role', ''))
        if not valid:
            errors.append(error)
        
        # Brand
        valid, error = CAWValidator.validate_brand(data.get('primary_brand', ''))
        if not valid:
            errors.append(error)
        
        # Attributes
        attributes = ['brawling', 'technical', 'speed', 'mic', 'psychology', 'stamina']
        for attr in attributes:
            value = data.get(attr, 0)
            valid, error = CAWValidator.validate_attribute(value, attr.capitalize())
            if not valid:
                errors.append(error)
        
        # Salary
        salary = data.get('salary_per_show', 0)
        valid, error = CAWValidator.validate_salary(salary)
        if not valid:
            errors.append(error)
        
        # Contract weeks
        weeks = data.get('contract_weeks', 0)
        valid, error = CAWValidator.validate_contract_weeks(weeks)
        if not valid:
            errors.append(error)
        
        return len(errors) == 0, errors


class CAWFactory:
    """Creates wrestler objects from CAW data"""
    
    @staticmethod
    def generate_wrestler_id(database) -> str:
        """
        Generate next available wrestler ID.
        Scans existing IDs and returns next in sequence.
        """
        cursor = database.conn.cursor()
        cursor.execute("SELECT id FROM wrestlers ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        
        if not row:
            # No wrestlers exist, start at w001
            return 'w001'
        
        last_id = row['id']
        
        # Extract number from ID (e.g., "w045" -> 45)
        try:
            num = int(last_id.replace('w', ''))
            next_num = num + 1
            return f'w{next_num:03d}'
        except ValueError:
            # Fallback if ID format is unexpected
            return f'w{len(database.get_all_wrestlers()) + 1:03d}'
    
    @staticmethod
    def create_wrestler(data: Dict[str, Any], wrestler_id: str, current_year: int, current_week: int) -> Wrestler:
        """
        Create a Wrestler object from validated CAW data.
        
        Args:
            data: Validated CAW data
            wrestler_id: Generated wrestler ID
            current_year: Current game year
            current_week: Current game week
        
        Returns:
            Wrestler object ready to be saved
        """
        # Create contract
        contract = Contract(
            salary_per_show=data['salary_per_show'],
            total_length_weeks=data['contract_weeks'],
            weeks_remaining=data['contract_weeks'],
            signing_year=current_year,
            signing_week=current_week
        )
        
        # Create wrestler
        wrestler = Wrestler(
            wrestler_id=wrestler_id,
            name=data['name'].strip(),
            age=data['age'],
            gender=data['gender'],
            alignment=data.get('alignment', 'Neutral'),
            role=data['role'],
            primary_brand=data['primary_brand'],
            
            # Attributes
            brawling=data['brawling'],
            technical=data['technical'],
            speed=data['speed'],
            mic=data['mic'],
            psychology=data['psychology'],
            stamina=data['stamina'],
            
            # Career
            years_experience=data.get('years_experience', 0),
            is_major_superstar=data.get('is_major_superstar', False),
            
            # Dynamic stats (start at defaults)
            popularity=data.get('popularity', 50),
            momentum=data.get('momentum', 0),
            morale=data.get('morale', 75),  # New wrestlers start happy
            fatigue=data.get('fatigue', 0),
            
            # Contract
            contract=contract,
            
            # Injury (start healthy)
            injury=Injury.none(),
            
            # Status
            is_retired=False
        )
        
        return wrestler
    
    @staticmethod
    def get_suggested_salary(role: str, overall_rating: int) -> int:
        """
        Calculate suggested salary based on role and overall rating.
        
        Args:
            role: Wrestler role
            overall_rating: Calculated overall rating (0-100)
        
        Returns:
            Suggested salary per show
        """
        base_salaries = {
            'Main Event': 20000,
            'Upper Midcard': 12000,
            'Midcard': 7000,
            'Lower Midcard': 4000,
            'Jobber': 2000
        }
        
        base = base_salaries.get(role, 5000)
        
        # Adjust by overall rating
        # 50 rating = base salary
        # 100 rating = 2x base salary
        # 0 rating = 0.5x base salary
        multiplier = 0.5 + (overall_rating / 100)
        
        suggested = int(base * multiplier)
        
        # Round to nearest 500
        suggested = round(suggested / 500) * 500
        
        return suggested
    
    @staticmethod
    def calculate_overall_preview(data: Dict[str, Any]) -> int:
        """
        Calculate overall rating preview for CAW form.
        Uses same logic as Wrestler.overall_rating property.
        """
        role = data.get('role', 'Midcard')
        
        if role == 'Main Event':
            weights = {
                'brawling': 0.20,
                'technical': 0.20,
                'speed': 0.15,
                'mic': 0.20,
                'psychology': 0.20,
                'stamina': 0.05
            }
        elif role in ['Upper Midcard', 'Midcard']:
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
            data.get('brawling', 50) * weights['brawling'] +
            data.get('technical', 50) * weights['technical'] +
            data.get('speed', 50) * weights['speed'] +
            data.get('mic', 50) * weights['mic'] +
            data.get('psychology', 50) * weights['psychology'] +
            data.get('stamina', 50) * weights['stamina']
        )
        
        return int(rating)


class CAWPresets:
    """Pre-defined wrestler templates for quick creation"""
    
    @staticmethod
    def get_preset(preset_name: str) -> Optional[Dict[str, Any]]:
        """Get a preset wrestler template"""
        presets = {
            'powerhouse': {
                'brawling': 85,
                'technical': 50,
                'speed': 40,
                'mic': 55,
                'psychology': 60,
                'stamina': 75,
                'role': 'Upper Midcard',
                'description': 'Strong brawler with high stamina'
            },
            'high_flyer': {
                'brawling': 50,
                'technical': 60,
                'speed': 90,
                'mic': 50,
                'psychology': 65,
                'stamina': 70,
                'role': 'Upper Midcard',
                'description': 'Agile speedster with aerial abilities'
            },
            'technical_master': {
                'brawling': 55,
                'technical': 90,
                'speed': 60,
                'mic': 55,
                'psychology': 80,
                'stamina': 75,
                'role': 'Upper Midcard',
                'description': 'Submission specialist with mat skills'
            },
            'main_eventer': {
                'brawling': 80,
                'technical': 75,
                'speed': 70,
                'mic': 85,
                'psychology': 90,
                'stamina': 80,
                'role': 'Main Event',
                'description': 'Complete package superstar'
            },
            'mic_worker': {
                'brawling': 60,
                'technical': 60,
                'speed': 55,
                'mic': 90,
                'psychology': 75,
                'stamina': 65,
                'role': 'Upper Midcard',
                'description': 'Charismatic talker with solid skills'
            },
            'rookie': {
                'brawling': 45,
                'technical': 45,
                'speed': 55,
                'mic': 40,
                'psychology': 40,
                'stamina': 60,
                'role': 'Lower Midcard',
                'description': 'Green wrestler ready to learn'
            },
            'veteran': {
                'brawling': 70,
                'technical': 75,
                'speed': 50,
                'mic': 80,
                'psychology': 90,
                'stamina': 60,
                'role': 'Upper Midcard',
                'description': 'Experienced ring general'
            },
            'dominant_powerhouse': {
                'brawling': 90,
                'technical': 45,
                'speed': 35,
                'mic': 50,
                'psychology': 70,
                'stamina': 85,
                'role': 'Main Event',
                'description': 'Dominant powerhouse'
            },
            'resilient_underdog': {
                'brawling': 55,
                'technical': 65,
                'speed': 75,
                'mic': 70,
                'psychology': 80,
                'stamina': 70,
                'role': 'Midcard',
                'description': 'Resilient underdog with heart'
            },
            'balanced': {
                'brawling': 65,
                'technical': 65,
                'speed': 65,
                'mic': 65,
                'psychology': 65,
                'stamina': 65,
                'role': 'Midcard',
                'description': 'Well-rounded all-arounder'
            }
        }
        
        return presets.get(preset_name.lower())
    
    @staticmethod
    def get_all_presets() -> Dict[str, Dict[str, Any]]:
        """Get all available presets"""
        return {
            'powerhouse': CAWPresets.get_preset('powerhouse'),
            'high_flyer': CAWPresets.get_preset('high_flyer'),
            'technical_master': CAWPresets.get_preset('technical_master'),
            'main_eventer': CAWPresets.get_preset('main_eventer'),
            'mic_worker': CAWPresets.get_preset('mic_worker'),
            'rookie': CAWPresets.get_preset('rookie'),
            'veteran': CAWPresets.get_preset('veteran'),
            'dominant_powerhouse': CAWPresets.get_preset('dominant_powerhouse'),
            'resilient_underdog': CAWPresets.get_preset('resilient_underdog'),
            'balanced': CAWPresets.get_preset('balanced')
        }
