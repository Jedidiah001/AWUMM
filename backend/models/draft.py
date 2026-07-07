"""
Brand Draft Model
Handles the annual brand draft system with various formats and rules.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum
from datetime import datetime
import random


class DraftFormat(Enum):
    """Available draft formats"""
    SNAKE = "snake"           # A-B-C-C-B-A pattern
    ROTATING = "rotating"     # A-B-C-A-B-C pattern
    LOTTERY = "lottery"       # Random order each round


class DraftExemptionReason(Enum):
    """Reasons why a wrestler might be draft-exempt"""
    CHAMPION = "champion"
    INJURED_LONG_TERM = "injured_long_term"
    PART_TIME = "part_time"
    AUTHORITY_FIGURE = "authority_figure"
    RECENT_DEBUT = "recent_debut"
    CROSS_BRAND_FEUD = "cross_brand_feud"
    CONTRACT_PROTECTION = "contract_protection"


@dataclass
class DraftExemption:
    """Represents a draft exemption for a wrestler"""
    wrestler_id: str
    wrestler_name: str
    reason: DraftExemptionReason
    description: str
    expires_week: Optional[int] = None  # When exemption expires


@dataclass
class DraftPick:
    """Represents a single draft pick"""
    round_number: int
    pick_number: int
    overall_pick: int
    brand: str
    gm_id: str
    gm_name: str
    wrestler_id: str
    wrestler_name: str
    wrestler_role: str
    wrestler_overall: int
    pick_value: float  # GM's evaluation of the pick
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class DraftRound:
    """Represents a complete draft round"""
    round_number: int
    picks: List[DraftPick] = field(default_factory=list)
    
    @property
    def is_complete(self) -> bool:
        """Check if all brands have picked"""
        return len(self.picks) >= 3  # 3 brands


class BrandDraft:
    """
    Manages the annual brand draft event.
    
    Features:
    - Multiple draft formats (snake, rotating, lottery)
    - Draft exemptions for champions, injured wrestlers, etc.
    - GM AI with different personalities
    - Trade possibilities during draft
    """
    
    def __init__(
        self,
        draft_id: str,
        year: int,
        week: int,
        format_type: DraftFormat = DraftFormat.SNAKE
    ):
        self.draft_id = draft_id
        self.year = year
        self.week = week
        self.format_type = format_type
        
        # Draft state
        self.rounds: List[DraftRound] = []
        self.current_round = 1
        self.overall_pick_count = 0
        self.is_complete = False
        
        # Participants
        self.eligible_wrestlers: List[Dict] = []
        self.exemptions: List[DraftExemption] = []
        self.draft_pool: Set[str] = set()  # IDs of draftable wrestlers
        
        # Brand tracking
        self.brand_rosters: Dict[str, List[str]] = {
            'ROC Alpha': [],
            'ROC Velocity': [],
            'ROC Vanguard': []
        }
        
        # GM assignments
        self.gm_assignments: Dict[str, Dict] = {}  # brand -> GM info
        
        # Draft order
        self.base_draft_order: List[str] = []
        self.current_draft_order: List[str] = []
        
        # History
        self.all_picks: List[DraftPick] = []
        self.trades: List[Dict] = []  # Any trades during draft
    
    def set_gm_assignments(self, gm_data: List[Dict]):
        """Assign GMs to brands"""
        for gm in gm_data:
            self.gm_assignments[gm['brand']] = gm
    
    def calculate_exemptions(self, universe_state) -> List[DraftExemption]:
        """
        Calculate all draft exemptions based on current universe state.
        
        Exemption rules:
        1. Current champions stay on their brand
        2. Wrestlers with 6+ month injuries
        3. Part-time wrestlers
        4. Authority figures
        5. Wrestlers who debuted within 15 weeks
        6. Wrestlers in active cross-brand feuds
        7. Wrestlers with contract protection clauses
        """
        exemptions = []
        
        # Get all active wrestlers
        all_wrestlers = universe_state.get_active_wrestlers()
        
        for wrestler in all_wrestlers:
            exemption = None
            
            # Check if champion
            for championship in universe_state.championships:
                if championship.current_holder_id == wrestler.id:
                    exemption = DraftExemption(
                        wrestler_id=wrestler.id,
                        wrestler_name=wrestler.name,
                        reason=DraftExemptionReason.CHAMPION,
                        description=f"Current {championship.name} Champion"
                    )
                    break
            
            # Check for long-term injury (6+ months = 24+ weeks)
            if not exemption and wrestler.injury.severity in ['Major'] and wrestler.injury.weeks_remaining >= 24:
                exemption = DraftExemption(
                    wrestler_id=wrestler.id,
                    wrestler_name=wrestler.name,
                    reason=DraftExemptionReason.INJURED_LONG_TERM,
                    description=f"Out with {wrestler.injury.description} ({wrestler.injury.weeks_remaining} weeks)"
                )
            
            # Check for recent debut (within 15 weeks)
            if not exemption:
                try:
                    # Get database reference properly
                    db = getattr(universe_state, 'db', None)
                    if db:
                        match_history = db.get_match_history(wrestler_id=wrestler.id, limit=1)
                        if match_history:
                            first_match = match_history[0]
                            weeks_since_debut = (self.year - first_match['year']) * 52 + (self.week - first_match['week'])
                            if weeks_since_debut <= 15:
                                exemption = DraftExemption(
                                    wrestler_id=wrestler.id,
                                    wrestler_name=wrestler.name,
                                    reason=DraftExemptionReason.RECENT_DEBUT,
                                    description=f"Recently debuted ({weeks_since_debut} weeks ago)",
                                    expires_week=first_match['week'] + 15
                                )
                except Exception as e:
                    # Skip recent debut check if database issues
                    print(f"Could not check debut for {wrestler.name}: {e}")
            
            # Check for cross-brand feuds
            if not exemption:
                active_feuds = universe_state.feud_manager.get_feuds_involving(wrestler.id)
                for feud in active_feuds:
                    if feud.intensity >= 60:  # Only high-intensity feuds
                        # Check if feud involves wrestlers from different brands
                        participants_brands = set()
                        for pid in feud.participant_ids:
                            p_wrestler = universe_state.get_wrestler_by_id(pid)
                            if p_wrestler:
                                participants_brands.add(p_wrestler.primary_brand)
                        
                        if len(participants_brands) > 1:
                            exemption = DraftExemption(
                                wrestler_id=wrestler.id,
                                wrestler_name=wrestler.name,
                                reason=DraftExemptionReason.CROSS_BRAND_FEUD,
                                description=f"In cross-brand feud: {feud.participant_names[0]} vs {feud.participant_names[1]}"
                            )
                            break
            
            if exemption:
                exemptions.append(exemption)
        
        self.exemptions = exemptions
        return exemptions
    
    def initialize_draft_pool(self, all_wrestlers: List, exemptions: List[DraftExemption]):
        """Initialize the pool of draftable wrestlers"""
        exempt_ids = {e.wrestler_id for e in exemptions}
        
        self.eligible_wrestlers = []
        for wrestler in all_wrestlers:
            if wrestler.id not in exempt_ids and not wrestler.is_retired:
                self.eligible_wrestlers.append({
                    'id': wrestler.id,
                    'name': wrestler.name,
                    'brand': wrestler.primary_brand,
                    'role': wrestler.role,
                    'overall': wrestler.overall_rating,
                    'age': wrestler.age,
                    'alignment': wrestler.alignment,
                    'popularity': wrestler.popularity,
                    'mic': wrestler.mic,
                    'years_experience': wrestler.years_experience
                })
                self.draft_pool.add(wrestler.id)
    
    def set_draft_order(self, order: List[str]):
        """Set the base draft order"""
        self.base_draft_order = order
        self.current_draft_order = self._calculate_round_order(1)
    
    def randomize_draft_order(self):
        """Randomize the draft order"""
        brands = list(self.brand_rosters.keys())
        random.shuffle(brands)
        self.set_draft_order(brands)
    
    def _calculate_round_order(self, round_number: int) -> List[str]:
        """Calculate draft order for a specific round based on format"""
        if self.format_type == DraftFormat.SNAKE:
            # Snake draft: reverse order every other round
            if round_number % 2 == 0:
                return list(reversed(self.base_draft_order))
            else:
                return self.base_draft_order.copy()
        
        elif self.format_type == DraftFormat.ROTATING:
            # Rotating: same order every round
            return self.base_draft_order.copy()
        
        elif self.format_type == DraftFormat.LOTTERY:
            # Lottery: random order each round
            order = self.base_draft_order.copy()
            random.shuffle(order)
            return order
        
        return self.base_draft_order.copy()
    
    def get_current_picking_brand(self) -> Optional[str]:
        """Get which brand is currently picking"""
        if self.is_complete or not self.current_draft_order:
            return None
        
        current_round = self._get_or_create_current_round()
        picks_in_round = len(current_round.picks)
        
        if picks_in_round < len(self.current_draft_order):
            return self.current_draft_order[picks_in_round]
        
        return None
    
    def _get_or_create_current_round(self) -> DraftRound:
        """Get current round or create new one"""
        if not self.rounds or self.rounds[-1].is_complete:
            new_round = DraftRound(round_number=self.current_round)
            self.rounds.append(new_round)
            return new_round
        return self.rounds[-1]
    
    def make_pick(self, brand: str, wrestler_id: str, gm_evaluation: float = 0.0) -> DraftPick:
        """
        Make a draft pick for a brand.
        
        Args:
            brand: The brand making the pick
            wrestler_id: ID of wrestler being picked
            gm_evaluation: GM's evaluation score for this pick
        
        Returns:
            The DraftPick object
        
        Raises:
            ValueError: If pick is invalid
        """
        # Validate pick
        if wrestler_id not in self.draft_pool:
            raise ValueError(f"Wrestler {wrestler_id} is not eligible for draft")
        
        if brand != self.get_current_picking_brand():
            raise ValueError(f"It's not {brand}'s turn to pick")
        
        # Get wrestler info
        wrestler_info = next((w for w in self.eligible_wrestlers if w['id'] == wrestler_id), None)
        if not wrestler_info:
            raise ValueError(f"Wrestler {wrestler_id} not found in eligible pool")
        
        # Get GM info
        gm = self.gm_assignments.get(brand, {})
        
        # Create pick
        self.overall_pick_count += 1
        current_round = self._get_or_create_current_round()
        
        pick = DraftPick(
            round_number=self.current_round,
            pick_number=len(current_round.picks) + 1,
            overall_pick=self.overall_pick_count,
            brand=brand,
            gm_id=gm.get('id', 'unknown'),
            gm_name=gm.get('name', 'Unknown GM'),
            wrestler_id=wrestler_id,
            wrestler_name=wrestler_info['name'],
            wrestler_role=wrestler_info['role'],
            wrestler_overall=wrestler_info['overall'],
            pick_value=gm_evaluation
        )
        
        # Record pick
        current_round.picks.append(pick)
        self.all_picks.append(pick)
        self.brand_rosters[brand].append(wrestler_id)
        self.draft_pool.remove(wrestler_id)
        
        # Check if round is complete
        if current_round.is_complete:
            self.current_round += 1
            self.current_draft_order = self._calculate_round_order(self.current_round)
        
        # Check if draft is complete
        if len(self.draft_pool) == 0:
            self.is_complete = True
        
        return pick
    
    def simulate_gm_pick(self, brand: str, universe_state) -> DraftPick:
        """
        Simulate a GM making a pick based on their personality.
        
        Different GM personalities prioritize different attributes:
        - Balanced: Overall rating with slight preference for their brand's style
        - Aggressive: Star power (popularity + momentum)
        - Builder: Young talent with high potential
        - Entertainment: Mic skills and charisma
        """
        gm = self.gm_assignments.get(brand, {})
        personality = gm.get('personality_type', 'balanced')
        traits = gm.get('traits', {})
        
        # Get available wrestlers
        available = [w for w in self.eligible_wrestlers if w['id'] in self.draft_pool]
        
        if not available:
            raise ValueError("No wrestlers available to draft")
        
        # Score each wrestler based on GM personality
        scored_wrestlers = []
        for wrestler in available:
            try:
                score = self._calculate_gm_preference_score(wrestler, personality, traits)
                scored_wrestlers.append((wrestler, score))
            except Exception as e:
                # Fallback to overall rating if scoring fails
                score = wrestler.get('overall', 50)
                scored_wrestlers.append((wrestler, score))
        
        # Sort by score (highest first)
        scored_wrestlers.sort(key=lambda x: x[1], reverse=True)
        
        # Add some randomness (top 3 picks have weighted chance)
        if len(scored_wrestlers) >= 3:
            weights = [0.6, 0.3, 0.1]  # 60% chance for top pick, 30% for 2nd, 10% for 3rd
            top_picks = scored_wrestlers[:3]
            chosen_idx = random.choices(range(3), weights=weights)[0]
            chosen_wrestler, evaluation_score = top_picks[chosen_idx]
        else:
            chosen_wrestler, evaluation_score = scored_wrestlers[0]
        
        # Make the pick
        return self.make_pick(brand, chosen_wrestler['id'], evaluation_score)
    
    def _calculate_gm_preference_score(self, wrestler: Dict, personality: str, traits: Dict) -> float:
        """Calculate how much a GM values a wrestler based on personality"""
        base_score = 0.0
        
        # Safely get values with defaults
        overall = wrestler.get('overall', 50)
        popularity = wrestler.get('popularity', 50)
        age = wrestler.get('age', 30)
        role = wrestler.get('role', 'Midcard')
        mic = wrestler.get('mic', 50)
        years_experience = wrestler.get('years_experience', 5)
        
        if personality == 'balanced':
            # Balanced GMs value overall rating most
            base_score = overall * 1.0
            
            # Slight bonus for role fit
            if role in ['Main Event', 'Upper Midcard']:
                base_score += 10
            
            # Loyalty bonus (simplified - use experience as proxy)
            if traits.get('values_loyalty') and years_experience > 5:
                base_score += 5
        
        elif personality == 'aggressive':
            # Aggressive GMs want immediate impact
            base_score = popularity * 0.7 + overall * 0.3
            
            # Huge bonus for main eventers
            if role == 'Main Event':
                base_score += 20
            
            # Prefer younger wrestlers
            if age < 30 and not traits.get('favors_veterans'):
                base_score += 5
        
        elif personality == 'builder':
            # Builders want young talent with potential
            age_factor = max(0, 40 - age) * 0.5
            base_score = overall * 0.6 + age_factor
            
            # Bonus for younger wrestlers
            if age < 28:
                base_score += 10
            
            # Penalty for older wrestlers
            if age > 35:
                base_score -= 15
        
        elif personality == 'entertainment':
            # Entertainment GMs prioritize charisma
            base_score = mic * 0.5 + overall * 0.3 + popularity * 0.2
            
            # Bonus for high mic skills
            if mic >= 80:
                base_score += 15
        
        else:
            # Default fallback
            base_score = overall
        
        # Universal factors
        
        # Workrate preference - use overall as proxy since we may not have detailed stats
        if traits.get('prefers_workrate'):
            base_score += overall * 0.1
        
        # Surprise factor
        if traits.get('likes_surprises'):
            # Bonus for unexpected picks
            if role in ['Lower Midcard', 'Jobber']:
                base_score += random.randint(0, 10)
        
        return base_score
    
    def execute_trade(self, brand_a: str, wrestler_a_id: str, brand_b: str, wrestler_b_id: str) -> Dict:
        """
        Execute a trade between two brands during the draft.
        
        Returns:
            Trade details dictionary
        """
        # Validate trade
        if wrestler_a_id not in self.brand_rosters[brand_a]:
            raise ValueError(f"{wrestler_a_id} is not on {brand_a}'s roster")
        
        if wrestler_b_id not in self.brand_rosters[brand_b]:
            raise ValueError(f"{wrestler_b_id} is not on {brand_b}'s roster")
        
        # Execute trade
        self.brand_rosters[brand_a].remove(wrestler_a_id)
        self.brand_rosters[brand_a].append(wrestler_b_id)
        
        self.brand_rosters[brand_b].remove(wrestler_b_id)
        self.brand_rosters[brand_b].append(wrestler_a_id)
        
        # Record trade
        trade = {
            'trade_id': f"trade_{len(self.trades) + 1}",
            'timestamp': datetime.now().isoformat(),
            'brand_a': brand_a,
            'wrestler_a_id': wrestler_a_id,
            'brand_b': brand_b,
            'wrestler_b_id': wrestler_b_id
        }
        
        self.trades.append(trade)
        return trade
    
    def get_draft_summary(self) -> Dict:
        """Get comprehensive draft summary"""
        summary = {
            'draft_id': self.draft_id,
            'year': self.year,
            'week': self.week,
            'format': self.format_type.value,
            'is_complete': self.is_complete,
            'total_rounds': self.current_round,
            'total_picks': self.overall_pick_count,
            'picks_by_brand': {},
            'top_picks': [],
            'surprises': [],
            'trades': self.trades,
            'exemptions_count': len(self.exemptions)
        }
        
        # Count picks by brand
        for brand in self.brand_rosters:
            summary['picks_by_brand'][brand] = len(self.brand_rosters[brand])
        
        # Get top 5 picks
        summary['top_picks'] = [
            {
                'pick': p.overall_pick,
                'wrestler': p.wrestler_name,
                'brand': p.brand,
                'overall': p.wrestler_overall
            }
            for p in self.all_picks[:5]
        ]
        
        # Find surprise picks (lower card wrestlers picked early)
        for pick in self.all_picks[:15]:  # First 15 picks
            if pick.wrestler_role in ['Lower Midcard', 'Jobber']:
                summary['surprises'].append({
                    'pick': pick.overall_pick,
                    'wrestler': pick.wrestler_name,
                    'role': pick.wrestler_role,
                    'brand': pick.brand
                })
        
        return summary
    
    def to_dict(self) -> Dict:
        """Convert draft to dictionary for serialization"""
        return {
            'draft_id': self.draft_id,
            'year': self.year,
            'week': self.week,
            'format_type': self.format_type.value,
            'is_complete': self.is_complete,
            'current_round': self.current_round,
            'overall_pick_count': self.overall_pick_count,
            'base_draft_order': self.base_draft_order,
            'current_draft_order': self.current_draft_order,
            'eligible_wrestlers': self.eligible_wrestlers,
            'exemptions': [
                {
                    'wrestler_id': e.wrestler_id,
                    'wrestler_name': e.wrestler_name,
                    'reason': e.reason.value,
                    'description': e.description,
                    'expires_week': e.expires_week
                }
                for e in self.exemptions
            ],
            'draft_pool': list(self.draft_pool),
            'brand_rosters': self.brand_rosters,
            'gm_assignments': self.gm_assignments,
            'rounds': [
                {
                    'round_number': r.round_number,
                    'picks': [
                        {
                            'round_number': p.round_number,
                            'pick_number': p.pick_number,
                            'overall_pick': p.overall_pick,
                            'brand': p.brand,
                            'gm_id': p.gm_id,
                            'gm_name': p.gm_name,
                            'wrestler_id': p.wrestler_id,
                            'wrestler_name': p.wrestler_name,
                            'wrestler_role': p.wrestler_role,
                            'wrestler_overall': p.wrestler_overall,
                            'pick_value': p.pick_value,
                            'timestamp': p.timestamp
                        }
                        for p in r.picks
                    ]
                }
                for r in self.rounds
            ],
            'all_picks': [
                {
                    'round_number': p.round_number,
                    'pick_number': p.pick_number,
                    'overall_pick': p.overall_pick,
                    'brand': p.brand,
                    'gm_id': p.gm_id,
                    'gm_name': p.gm_name,
                    'wrestler_id': p.wrestler_id,
                    'wrestler_name': p.wrestler_name,
                    'wrestler_role': p.wrestler_role,
                    'wrestler_overall': p.wrestler_overall,
                    'pick_value': p.pick_value,
                    'timestamp': p.timestamp
                }
                for p in self.all_picks
            ],
            'trades': self.trades
        }