"""
Free Agency Declaration System
STEP 123: Wrestlers can publicly announce intention to test free agency
"""

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime
from enum import Enum


class DeclarationType(Enum):
    """Types of free agency declarations"""
    TESTING_MARKET = "testing_market"          # Exploring all options
    OPEN_TO_OFFERS = "open_to_offers"          # Willing to negotiate
    SEEKING_CHANGE = "seeking_change"          # Unhappy, wants out
    LEVERAGING = "leveraging"                  # Using to get better deal
    RETIREMENT_CONSIDERATION = "retirement"     # Might retire instead


class DeclarationStatus(Enum):
    """Status of free agency declaration"""
    ACTIVE = "active"              # Currently testing market
    WITHDRAWN = "withdrawn"        # Changed mind, staying
    SIGNED_ELSEWHERE = "signed"    # Left for another promotion
    RE_SIGNED = "re_signed"        # Re-signed with current promotion
    RETIRED = "retired"            # Retired instead


@dataclass
class FreeAgencyDeclaration:
    """
    Represents a wrestler's public declaration of free agency intent.
    
    Creates media attention, fan speculation, and negotiation pressure.
    """
    
    declaration_id: str
    wrestler_id: str
    wrestler_name: str
    
    # When and how declared
    declared_year: int
    declared_week: int
    declaration_type: DeclarationType
    
    # Current status
    status: DeclarationStatus
    
    # Contract details at time of declaration
    weeks_remaining_at_declaration: int
    current_salary: int
    years_with_promotion: int
    
    # Wrestler's stated reasons
    reasons: List[str]  # ["seeking_title_opportunities", "wants_creative_control", "salary_concerns"]
    public_statement: str
    
    # Leverage and positioning
    leverage_level: int  # 0-100 (how strong is their position?)
    media_attention: int  # 0-100 (how much buzz has this generated?)
    
    # Offers and interest
    rival_offers_count: int = 0
    highest_rival_offer: int = 0
    current_promotion_counter_offer: Optional[int] = None
    
    # Resolution
    resolved_year: Optional[int] = None
    resolved_week: Optional[int] = None
    resolution_details: Optional[str] = None
    
    # Metadata
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
    
    @property
    def is_active(self) -> bool:
        """Check if declaration is still active"""
        return self.status == DeclarationStatus.ACTIVE
    
    @property
    def days_since_declaration(self) -> int:
        """Calculate how long declaration has been active"""
        # Simplified - would calculate from declared_year/week to current
        return 0  # Placeholder
    
    def to_dict(self) -> dict:
        """Serialize to dictionary"""
        return {
            'declaration_id': self.declaration_id,
            'wrestler_id': self.wrestler_id,
            'wrestler_name': self.wrestler_name,
            'declared_year': self.declared_year,
            'declared_week': self.declared_week,
            'declaration_type': self.declaration_type.value,
            'status': self.status.value,
            'weeks_remaining_at_declaration': self.weeks_remaining_at_declaration,
            'current_salary': self.current_salary,
            'years_with_promotion': self.years_with_promotion,
            'reasons': self.reasons,
            'public_statement': self.public_statement,
            'leverage_level': self.leverage_level,
            'media_attention': self.media_attention,
            'rival_offers_count': self.rival_offers_count,
            'highest_rival_offer': self.highest_rival_offer,
            'current_promotion_counter_offer': self.current_promotion_counter_offer,
            'resolved_year': self.resolved_year,
            'resolved_week': self.resolved_week,
            'resolution_details': self.resolution_details,
            'is_active': self.is_active
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'FreeAgencyDeclaration':
        """Create from dictionary"""
        return FreeAgencyDeclaration(
            declaration_id=data['declaration_id'],
            wrestler_id=data['wrestler_id'],
            wrestler_name=data['wrestler_name'],
            declared_year=data['declared_year'],
            declared_week=data['declared_week'],
            declaration_type=DeclarationType(data['declaration_type']),
            status=DeclarationStatus(data['status']),
            weeks_remaining_at_declaration=data['weeks_remaining_at_declaration'],
            current_salary=data['current_salary'],
            years_with_promotion=data['years_with_promotion'],
            reasons=data['reasons'],
            public_statement=data['public_statement'],
            leverage_level=data['leverage_level'],
            media_attention=data['media_attention'],
            rival_offers_count=data.get('rival_offers_count', 0),
            highest_rival_offer=data.get('highest_rival_offer', 0),
            current_promotion_counter_offer=data.get('current_promotion_counter_offer'),
            resolved_year=data.get('resolved_year'),
            resolved_week=data.get('resolved_week'),
            resolution_details=data.get('resolution_details'),
            created_at=data.get('created_at')
        )


class FreeAgencyDeclarationManager:
    """
    Manages all free agency declarations.
    
    Handles:
    - Creating declarations
    - Tracking active declarations
    - Simulating rival interest
    - Resolving declarations
    """
    
    def __init__(self):
        self.declarations: List[FreeAgencyDeclaration] = []
        self._next_declaration_id = 1
    
    def create_declaration(
        self,
        wrestler,
        declaration_type: DeclarationType,
        reasons: List[str],
        current_year: int,
        current_week: int
    ) -> FreeAgencyDeclaration:
        """
        Create a new free agency declaration.
        
        Args:
            wrestler: Wrestler object
            declaration_type: Type of declaration
            reasons: List of reasons for declaration
            current_year: Current game year
            current_week: Current game week
        
        Returns:
            FreeAgencyDeclaration object
        """
        declaration_id = f"fa_decl_{self._next_declaration_id:05d}"
        self._next_declaration_id += 1
        
        # Generate public statement
        public_statement = self._generate_public_statement(
            wrestler.name,
            declaration_type,
            reasons
        )
        
        # Calculate leverage level
        leverage_level = self._calculate_leverage(wrestler)
        
        # Calculate media attention
        media_attention = self._calculate_media_attention(wrestler)
        
        declaration = FreeAgencyDeclaration(
            declaration_id=declaration_id,
            wrestler_id=wrestler.id,
            wrestler_name=wrestler.name,
            declared_year=current_year,
            declared_week=current_week,
            declaration_type=declaration_type,
            status=DeclarationStatus.ACTIVE,
            weeks_remaining_at_declaration=wrestler.contract.weeks_remaining,
            current_salary=wrestler.contract.salary_per_show,
            years_with_promotion=wrestler.years_experience,
            reasons=reasons,
            public_statement=public_statement,
            leverage_level=leverage_level,
            media_attention=media_attention
        )
        
        self.declarations.append(declaration)
        
        return declaration
    
    def _generate_public_statement(
        self,
        wrestler_name: str,
        declaration_type: DeclarationType,
        reasons: List[str]
    ) -> str:
        """Generate public statement based on declaration type"""
        statements = {
            DeclarationType.TESTING_MARKET: [
                f"{wrestler_name}: 'I've been loyal for years, but it's time to see what's out there. I owe it to myself and my family to explore all options.'",
                f"{wrestler_name}: 'My contract is ending, and I want to make sure I'm making the best decision for my career. I'm open to hearing from everyone.'",
                f"{wrestler_name}: 'I love what we've built here, but I need to know my worth. Testing the market will show me that.'"
            ],
            DeclarationType.OPEN_TO_OFFERS: [
                f"{wrestler_name}: 'I'm listening. If you want me on your roster, make me an offer I can't refuse.'",
                f"{wrestler_name}: 'My phone is ringing off the hook. Let's see who really wants me.'",
                f"{wrestler_name}: 'I'm ready for the next chapter. Show me what you've got.'"
            ],
            DeclarationType.SEEKING_CHANGE: [
                f"{wrestler_name}: 'I'm not happy with how things have gone. I need a fresh start somewhere that values what I bring.'",
                f"{wrestler_name}: 'The promises made to me haven't been kept. I deserve better, and I'm going to find it.'",
                f"{wrestler_name}: 'It's time for change. I've given everything here, and it's not being reciprocated.'"
            ],
            DeclarationType.LEVERAGING: [
                f"{wrestler_name}: 'I have offers on the table. If they want to keep me, they know what they need to do.'",
                f"{wrestler_name}: 'Other companies see my value. I hope my current employer does too before it's too late.'",
                f"{wrestler_name}: 'The ball is in their court. I know what I'm worth.'"
            ],
            DeclarationType.RETIREMENT_CONSIDERATION: [
                f"{wrestler_name}: 'I might be done. Unless someone gives me a reason to keep going, this could be it.'",
                f"{wrestler_name}: 'I'm considering hanging up the boots. It would take something special to change my mind.'",
                f"{wrestler_name}: 'My body's telling me one thing, but if the right opportunity comes along... we'll see.'"
            ]
        }
        
        import random
        return random.choice(statements.get(declaration_type, [f"{wrestler_name} has declared free agency."]))
    
    def _calculate_leverage(self, wrestler) -> int:
        """Calculate wrestler's leverage in negotiations"""
        leverage = 50  # Base
        
        # Popularity boost
        leverage += (wrestler.popularity - 50) * 0.5
        
        # Role boost
        role_modifiers = {
            'Main Event': 30,
            'Upper Midcard': 20,
            'Midcard': 10,
            'Lower Midcard': 0,
            'Jobber': -20
        }
        leverage += role_modifiers.get(wrestler.role, 0)
        
        # Major superstar boost
        if wrestler.is_major_superstar:
            leverage += 20
        
        # Age penalty
        if wrestler.age >= 40:
            leverage -= 15
        elif wrestler.age >= 35:
            leverage -= 5
        
        # Morale affects leverage
        if wrestler.morale < 30:
            leverage += 10  # Desperation adds urgency
        
        return max(0, min(100, int(leverage)))
    
    def _calculate_media_attention(self, wrestler) -> int:
        """Calculate media buzz around declaration"""
        attention = 30  # Base
        
        # Popularity drives media
        attention += wrestler.popularity * 0.5
        
        # Major stars get more coverage
        if wrestler.is_major_superstar:
            attention += 30
        
        # Role matters
        if wrestler.role == 'Main Event':
            attention += 20
        elif wrestler.role == 'Upper Midcard':
            attention += 10
        
        return max(0, min(100, int(attention)))
    
    def get_active_declarations(self) -> List[FreeAgencyDeclaration]:
        """Get all active free agency declarations"""
        return [d for d in self.declarations if d.is_active]
    
    def get_declaration_by_wrestler(self, wrestler_id: str) -> Optional[FreeAgencyDeclaration]:
        """Get active declaration for specific wrestler"""
        for declaration in self.declarations:
            if declaration.wrestler_id == wrestler_id and declaration.is_active:
                return declaration
        return None
    
    def simulate_rival_interest(self, declaration: FreeAgencyDeclaration, wrestler):
        """
        Simulate rival promotions making offers.
        
        Called each week while declaration is active.
        """
        from economy.contracts import contract_manager
        
        # Probability of new offer based on leverage and media attention
        offer_probability = (declaration.leverage_level + declaration.media_attention) / 200
        
        import random
        if random.random() < offer_probability:
            # Generate rival offer
            market_value = contract_manager.calculate_market_value(wrestler)
            
            # Rival offers are typically 10-30% above market
            offer_multiplier = 1.1 + (random.random() * 0.2)
            rival_offer = int(market_value * offer_multiplier)
            
            declaration.rival_offers_count += 1
            if rival_offer > declaration.highest_rival_offer:
                declaration.highest_rival_offer = rival_offer
    
    def withdraw_declaration(
        self,
        declaration: FreeAgencyDeclaration,
        reason: str,
        current_year: int,
        current_week: int
    ):
        """Wrestler withdraws free agency declaration"""
        declaration.status = DeclarationStatus.WITHDRAWN
        declaration.resolved_year = current_year
        declaration.resolved_week = current_week
        declaration.resolution_details = reason
    
    def resolve_declaration(
        self,
        declaration: FreeAgencyDeclaration,
        resolution_type: DeclarationStatus,
        details: str,
        current_year: int,
        current_week: int
    ):
        """Resolve free agency declaration with outcome"""
        declaration.status = resolution_type
        declaration.resolved_year = current_year
        declaration.resolved_week = current_week
        declaration.resolution_details = details
    
    def to_dict(self) -> dict:
        """Serialize manager state"""
        return {
            'total_declarations': len(self.declarations),
            'active_declarations': len(self.get_active_declarations()),
            'declarations': [d.to_dict() for d in self.declarations]
        }
    
    def load_from_dict(self, data: dict):
        """Load manager state from dictionary"""
        self.declarations = [
            FreeAgencyDeclaration.from_dict(d) 
            for d in data.get('declarations', [])
        ]
        
        if self.declarations:
            max_id = max(
                int(d.declaration_id.replace('fa_decl_', '')) 
                for d in self.declarations
            )
            self._next_declaration_id = max_id + 1


# Global declaration manager instance
free_agency_declaration_manager = FreeAgencyDeclarationManager()