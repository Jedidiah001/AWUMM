"""
Special Events System
Handles injury returns, contract signings, and other special moments.
"""

from typing import List, Optional, Dict
from models.wrestler import Wrestler, Injury, Contract
import random


class EventsManager:
    """
    Manages special events like:
    - Injury returns (wrestlers cleared to compete after long-term injury)
    - Contract signings (wrestlers returning to the promotion)
    - Surprise debuts
    - Special announcements
    """
    
    def __init__(self):
        self.signings_this_year = 0
        self.MAX_SIGNINGS_PER_YEAR = 3
        self.recently_signed_ids = []  # Track who signed recently
        self.departed_wrestlers = []  # Wrestlers who left the promotion
    
    def attempt_injury_return(
        self,
        show_name: str,
        show_type: str,
        injured_wrestlers: List[Wrestler],
        current_year: int,
        current_week: int
    ) -> Optional[Wrestler]:
        """
        Attempt to trigger a dramatic injury return announcement.
        
        Only for wrestlers who:
        - Have been out 8+ weeks (major injury)
        - Are NOW healed (injury_severity == 'None')
        - Are popular (60+ popularity)
        
        This creates a "return from injury" announcement at major shows.
        
        Returns:
            Wrestler object if return announced, None otherwise
        """
        # Only trigger at PPVs
        if show_type not in ['minor_ppv', 'major_ppv']:
            return None
        
        # 30% chance at any PPV
        if random.random() > 0.30:
            return None
        
        # Find wrestlers who JUST healed from major injuries
        # (In a full implementation, track injury_start_week)
        # For now, filter by wrestlers who are healthy but have high fatigue (recovering)
        
        eligible = [
            w for w in injured_wrestlers
            if not w.is_injured  # NOW healthy
            and w.popularity >= 60  # Popular enough to warrant announcement
            and w.can_compete  # Able to return
            and not w.is_retired
        ]
        
        if not eligible:
            return None
        
        # Weight by popularity
        weights = [w.popularity for w in eligible]
        returning_wrestler = random.choices(eligible, weights=weights)[0]
        
        # Boost stats for return
        returning_wrestler.adjust_momentum(20)
        returning_wrestler.adjust_morale(15)
        returning_wrestler.fatigue = 0  # Fully rested
        
        return returning_wrestler
    
    def attempt_contract_signing(
        self,
        show_name: str,
        show_type: str,
        current_year: int,
        current_week: int,
        current_balance: int
    ) -> Optional[Wrestler]:
        """
        Attempt to trigger a surprise contract signing (wrestler returning to promotion).
        
        This simulates:
        - Wrestlers who were released/left returning
        - "Free agents" being signed
        - Former stars making comebacks
        
        Args:
            show_name: Name of the show
            show_type: Type of show (for probability calculation)
            current_year: Current game year
            current_week: Current game week
            current_balance: Promotion's current balance
        
        Returns:
            Wrestler object if signing occurs, None otherwise
        """
        # Check if we've hit the yearly limit
        if self.signings_this_year >= self.MAX_SIGNINGS_PER_YEAR:
            return None
        
        # Signing probabilities by show type
        signing_probabilities = {
            'Rumble Royale': 0.25,     # 25% chance - big surprise entrant potential
            'Victory Dome': 0.20,      # 20% chance - year-end blockbuster
            'Summer Slamfest': 0.15,   # 15% chance - summer signing
            'Night of Glory': 0.15,    # 15% chance - big event
            'Clash of Titans': 0.10,   # 10% chance - solid PPV
            'Overdrive': 0.10,         # 10% chance
            'Champions\' Ascent': 0.10, # 10% chance
            'Autumn Annihilation': 0.10, # 10% chance
        }
        
        chance = signing_probabilities.get(show_name, 0.0)
        
        # Only major/minor PPVs trigger signings
        if chance == 0.0:
            return None
        
        # Roll the dice
        if random.random() > chance:
            return None
        
        # Get eligible signings (departed wrestlers or generate new one)
        if self.departed_wrestlers:
            # Re-sign a departed wrestler
            available = [
                w for w in self.departed_wrestlers
                if w.id not in self.recently_signed_ids
            ]
            
            if available:
                # Weight by popularity (more popular = more likely to return)
                weights = [w.popularity for w in available]
                signing = random.choices(available, weights=weights)[0]
                
                # Remove from departed list
                self.departed_wrestlers.remove(signing)
            else:
                # No one available
                return None
        else:
            # Generate a new signing (returning veteran or new talent)
            signing = self._generate_new_signing(current_year, current_week)
        
        # Check if promotion can afford them
        from economy.contracts import contract_manager
        market_value = contract_manager.calculate_market_value(signing)
        
        # Don't sign if too expensive (would exceed 10% of balance per year)
        annual_cost = market_value * 52 * 3  # Rough estimate
        if annual_cost > current_balance * 0.1:
            return None
        
        # EXECUTE THE SIGNING
        self.execute_signing(signing, current_year, current_week)
        
        # Track signing
        self.signings_this_year += 1
        self.recently_signed_ids.append(signing.id)
        
        return signing
    
    def execute_signing(self, wrestler: Wrestler, current_year: int, current_week: int):
        """
        Execute a contract signing.
        
        Effects:
        - Set is_retired to False (make active)
        - Reset injury to healthy
        - Moderate popularity/momentum boost (not as dramatic as injury return)
        - Reset fatigue
        - Grant new 1-year contract
        """
        wrestler.is_retired = False
        
        # Full health
        wrestler.injury = Injury.none()
        wrestler.fatigue = 0
        
        # Moderate stat boosts (not as extreme as surprise return)
        wrestler.adjust_popularity(25)
        wrestler.adjust_momentum(30)
        wrestler.adjust_morale(20)
        
        # New 1-year contract at market rate
        from economy.contracts import contract_manager
        market_value = contract_manager.calculate_market_value(wrestler)
        
        wrestler.contract = Contract(
            salary_per_show=market_value,
            total_length_weeks=52,
            weeks_remaining=52,
            signing_year=current_year,
            signing_week=current_week
        )
    
    def add_departed_wrestler(self, wrestler: Wrestler):
        """
        Add a wrestler to the departed pool (when released/contract expires).
        These wrestlers can potentially return later via contract signing.
        """
        if wrestler.is_major_superstar or wrestler.popularity >= 60:
            # Only track notable wrestlers
            self.departed_wrestlers.append(wrestler)
    
    def _generate_new_signing(self, current_year: int, current_week: int) -> Wrestler:
        """
        Generate a brand new wrestler signing (returning veteran or new talent).
        This simulates signing someone from outside the promotion.
        """
        import random
        from models.wrestler import Wrestler, Contract, Injury
        
        # Determine wrestler type
        is_veteran = random.random() < 0.6  # 60% chance of veteran, 40% new talent
        
        if is_veteran:
            # Returning veteran (35-45 years old)
            age = random.randint(35, 45)
            years_exp = random.randint(12, 25)
            role_choices = ['Upper Midcard', 'Midcard', 'Main Event']
            role_weights = [50, 30, 20]
        else:
            # New talent (22-30 years old)
            age = random.randint(22, 30)
            years_exp = random.randint(2, 8)
            role_choices = ['Midcard', 'Lower Midcard', 'Upper Midcard']
            role_weights = [40, 40, 20]
        
        role = random.choices(role_choices, weights=role_weights)[0]
        gender = random.choice(['Male', 'Female'])
        alignment = random.choice(['Face', 'Heel', 'Tweener'])
        brand = random.choice(['ROC Alpha', 'ROC Velocity', 'ROC Vanguard'])
        
        # Generate name
        first_names_m = ['Rex', 'Ace', 'Blaze', 'Storm', 'Thunder', 'Viper', 'Hawk', 'Wolf', 'Titan', 'Dragon']
        last_names_m = ['Knight', 'Steele', 'Savage', 'Rage', 'Justice', 'Fury', 'Storm', 'Blaze', 'King', 'Phoenix']
        first_names_f = ['Raven', 'Phoenix', 'Storm', 'Jade', 'Luna', 'Scarlett', 'Ivy', 'Ember', 'Aurora', 'Violet']
        last_names_f = ['Blaze', 'Storm', 'Eclipse', 'Frost', 'Phoenix', 'Tempest', 'Fury', 'Chaos', 'Venom', 'Sky']
        
        if gender == 'Male':
            name = f"{random.choice(first_names_m)} {random.choice(last_names_m)}"
        else:
            name = f"{random.choice(first_names_f)} {random.choice(last_names_f)}"
        
        # Generate attributes based on role
        if role == 'Main Event':
            attr_range = (75, 90)
            popularity = random.randint(70, 85)
        elif role == 'Upper Midcard':
            attr_range = (70, 82)
            popularity = random.randint(60, 75)
        elif role == 'Midcard':
            attr_range = (65, 75)
            popularity = random.randint(50, 65)
        else:  # Lower Midcard
            attr_range = (60, 70)
            popularity = random.randint(40, 55)
        
        # Apply age degradation for veterans
        if age >= 40:
            attr_range = (attr_range[0] - 10, attr_range[1] - 5)
        elif age >= 35:
            attr_range = (attr_range[0] - 5, attr_range[1] - 2)
        
        wrestler = Wrestler(
            wrestler_id=f"w_signed_{current_year}_{current_week}_{random.randint(1000, 9999)}",
            name=name,
            age=age,
            gender=gender,
            alignment=alignment,
            role=role,
            primary_brand=brand,
            brawling=random.randint(*attr_range),
            technical=random.randint(*attr_range),
            speed=random.randint(*attr_range),
            mic=random.randint(*attr_range),
            psychology=random.randint(*attr_range),
            stamina=random.randint(*attr_range),
            years_experience=years_exp,
            is_major_superstar=False,  # New signings aren't major superstars yet
            popularity=popularity,
            momentum=random.randint(10, 30),
            morale=random.randint(60, 80),
            fatigue=0
        )
        
        return wrestler
    
    def create_injury_return_announcement(self, wrestler: Wrestler) -> Dict:
        """
        Create an injury return announcement event.
        
        Returns:
            Event details dictionary
        """
        return {
            'event_type': 'injury_return',
            'wrestler_id': wrestler.id,
            'wrestler_name': wrestler.name,
            'message': f"🎉 {wrestler.name} has been CLEARED TO COMPETE and is returning to action!"
        }
    
    def create_signing_announcement(self, wrestler: Wrestler) -> Dict:
        """
        Create a contract signing announcement event.
        
        Returns:
            Event details dictionary
        """
        return {
            'event_type': 'contract_signing',
            'wrestler_id': wrestler.id,
            'wrestler_name': wrestler.name,
            'brand': wrestler.primary_brand,
            'message': f"📝 BREAKING: Ring of Champions has signed {wrestler.name} to a contract! Welcome to {wrestler.primary_brand}!"
        }
    
    def reset_yearly_limits(self):
        """Reset yearly counters (call at year-end)"""
        self.signings_this_year = 0
        # Keep recently_signed_ids for 2 years - could implement tracking if needed
    
    def to_dict(self) -> Dict:
        """Serialize events manager state"""
        return {
            'signings_this_year': self.signings_this_year,
            'max_signings_per_year': self.MAX_SIGNINGS_PER_YEAR,
            'departed_wrestlers_count': len(self.departed_wrestlers),
            'recently_signed_count': len(self.recently_signed_ids)
        }


# Global events manager instance
events_manager = EventsManager()