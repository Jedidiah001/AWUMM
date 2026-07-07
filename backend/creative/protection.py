"""
Wrestler Protection System
Tracks win/loss streaks and prevents booking that damages wrestler value.

Protection Rules:
1. Main eventers shouldn't lose more than 2 in a row
2. Rising stars (high momentum) get win streak protection
3. Champions get protected from clean losses
4. Jobbers can lose streaks (but not infinite)
5. 50/50 booking detection (alternating wins/losses is bad)
"""

from typing import List, Dict, Optional, Tuple
from models.wrestler import Wrestler
from dataclasses import dataclass
from enum import Enum


class ProtectionLevel(Enum):
    """How protected a wrestler should be"""
    NONE = "none"              # Jobbers, can lose frequently
    LOW = "low"                # Lower card, some protection
    MEDIUM = "medium"          # Midcard, moderate protection
    HIGH = "high"              # Upper card, strong protection
    ABSOLUTE = "absolute"      # Champions, top stars


@dataclass
class WrestlerRecord:
    """Tracks a wrestler's recent booking record"""
    wrestler_id: str
    
    # Last 10 matches
    last_10_results: List[str] = None  # ['W', 'L', 'W', 'W', 'L', ...]
    
    # Streaks
    current_win_streak: int = 0
    current_loss_streak: int = 0
    longest_win_streak: int = 0
    longest_loss_streak: int = 0
    
    # Overall record (career)
    total_wins: int = 0
    total_losses: int = 0
    total_draws: int = 0
    
    # 50/50 booking detection
    alternating_count: int = 0  # How many alternating W/L in a row
    
    def __post_init__(self):
        if self.last_10_results is None:
            self.last_10_results = []
    
    def add_result(self, result: str):
        """
        Add a match result.
        
        Args:
            result: 'W' (win), 'L' (loss), or 'D' (draw)
        """
        
        # Update last 10
        self.last_10_results.append(result)
        if len(self.last_10_results) > 10:
            self.last_10_results.pop(0)
        
        # Update totals
        if result == 'W':
            self.total_wins += 1
            self.current_win_streak += 1
            self.current_loss_streak = 0
            
            if self.current_win_streak > self.longest_win_streak:
                self.longest_win_streak = self.current_win_streak
        
        elif result == 'L':
            self.total_losses += 1
            self.current_loss_streak += 1
            self.current_win_streak = 0
            
            if self.current_loss_streak > self.longest_loss_streak:
                self.longest_loss_streak = self.current_loss_streak
        
        elif result == 'D':
            self.total_draws += 1
            self.current_win_streak = 0
            self.current_loss_streak = 0
        
        # Check for 50/50 booking pattern
        self._check_alternating_pattern()
    
    def _check_alternating_pattern(self):
        """Detect if wrestler is stuck in 50/50 booking"""
        
        if len(self.last_10_results) < 4:
            self.alternating_count = 0
            return
        
        # Check last 6 results for alternating pattern
        recent = self.last_10_results[-6:]
        
        is_alternating = True
        for i in range(1, len(recent)):
            if recent[i] == recent[i-1]:
                is_alternating = False
                break
        
        if is_alternating:
            self.alternating_count = len(recent)
        else:
            self.alternating_count = 0
    
    def get_win_percentage(self) -> float:
        """Calculate win percentage"""
        total = self.total_wins + self.total_losses + self.total_draws
        if total == 0:
            return 0.5
        return self.total_wins / total
    
    def is_in_50_50_booking(self) -> bool:
        """Check if stuck in 50/50 booking pattern"""
        return self.alternating_count >= 4
    
    def needs_protection(self, wrestler: Wrestler) -> bool:
        """
        Check if wrestler needs booking protection.
        
        Returns True if:
        - Main eventer on 2+ loss streak
        - Rising star (momentum > 20) on loss streak
        - Anyone on 4+ loss streak
        - In 50/50 booking pattern
        """
        
        # 50/50 booking is always bad
        if self.is_in_50_50_booking():
            return True
        
        # Main eventers can't lose more than 2 in a row
        if wrestler.role == 'Main Event' and self.current_loss_streak >= 2:
            return True
        
        # Rising stars (high momentum) need protection
        if wrestler.momentum > 20 and self.current_loss_streak >= 2:
            return True
        
        # Upper midcard can't lose 3+ in a row
        if wrestler.role == 'Upper Midcard' and self.current_loss_streak >= 3:
            return True
        
        # Anyone losing 4+ in a row needs help
        if self.current_loss_streak >= 4:
            return True
        
        return False
    
    def to_dict(self):
        return {
            'wrestler_id': self.wrestler_id,
            'last_10_results': self.last_10_results,
            'current_win_streak': self.current_win_streak,
            'current_loss_streak': self.current_loss_streak,
            'longest_win_streak': self.longest_win_streak,
            'longest_loss_streak': self.longest_loss_streak,
            'total_wins': self.total_wins,
            'total_losses': self.total_losses,
            'total_draws': self.total_draws,
            'win_percentage': self.get_win_percentage(),
            'in_50_50_booking': self.is_in_50_50_booking()
        }


class ProtectionManager:
    """Manages wrestler protection across the roster"""
    
    def __init__(self):
        self.records: Dict[str, WrestlerRecord] = {}
    
    def get_or_create_record(self, wrestler_id: str) -> WrestlerRecord:
        """Get existing record or create new one"""
        if wrestler_id not in self.records:
            self.records[wrestler_id] = WrestlerRecord(wrestler_id=wrestler_id)
        return self.records[wrestler_id]
    
    def record_match_result(self, wrestler_id: str, won: bool, was_draw: bool = False):
        """
        Record a match result for a wrestler.
        
        Args:
            wrestler_id: ID of the wrestler
            won: True if they won
            was_draw: True if match was a draw
        """
        
        record = self.get_or_create_record(wrestler_id)
        
        if was_draw:
            record.add_result('D')
        elif won:
            record.add_result('W')
        else:
            record.add_result('L')
    
    def get_protection_level(self, wrestler: Wrestler) -> ProtectionLevel:
        """
        Determine protection level for a wrestler.
        
        Based on:
        - Role in card
        - Championship status
        - Momentum
        - Popularity
        """
        
        # Champions get absolute protection
        # (This would check if they hold a title - simplified for now)
        
        # Main eventers
        if wrestler.role == 'Main Event':
            return ProtectionLevel.HIGH
        
        # Rising stars
        if wrestler.momentum > 30:
            return ProtectionLevel.HIGH
        
        # Upper midcard
        if wrestler.role == 'Upper Midcard':
            return ProtectionLevel.MEDIUM
        
        # Midcard
        if wrestler.role == 'Midcard':
            return ProtectionLevel.LOW
        
        # Lower card
        return ProtectionLevel.NONE
    
    def should_wrestler_win(
        self,
        wrestler: Wrestler,
        opponent: Wrestler,
        booking_bias: str = 'even'
    ) -> Tuple[bool, str]:
        """
        Determine if a wrestler should win based on protection needs.
        
        Args:
            wrestler: The wrestler in question
            opponent: Their opponent
            booking_bias: Current booking bias
        
        Returns:
            (should_force_win, reason)
        """
        
        wrestler_record = self.get_or_create_record(wrestler.id)
        opponent_record = self.get_or_create_record(opponent.id)
        
        wrestler_protection = self.get_protection_level(wrestler)
        opponent_protection = self.get_protection_level(opponent)
        
        # Check if wrestler desperately needs a win
        if wrestler_record.needs_protection(wrestler):
            
            # But don't sacrifice a more protected opponent
            if opponent_protection.value > wrestler_protection.value:
                return (False, "Opponent has higher protection level")
            
            # If opponent also needs protection, it's a problem
            if opponent_record.needs_protection(opponent):
                return (False, "Both wrestlers need protection - book carefully")
            
            return (True, f"Wrestler on {wrestler_record.current_loss_streak} loss streak - needs win")
        
        # Check if opponent desperately needs a loss
        if opponent_record.current_win_streak >= 5 and wrestler_protection != ProtectionLevel.NONE:
            return (True, f"Opponent on {opponent_record.current_win_streak} win streak - time to lose")
        
        # Check for 50/50 booking pattern
        if wrestler_record.is_in_50_50_booking():
            # Break the pattern - if last result was L, give them W
            if wrestler_record.last_10_results[-1] == 'L':
                return (True, "Breaking 50/50 booking pattern")
            else:
                return (False, "Breaking 50/50 booking pattern")
        
        return (False, "No protection override needed")
    
    def get_wrestlers_needing_protection(
        self,
        wrestlers: List[Wrestler]
    ) -> List[Tuple[Wrestler, WrestlerRecord]]:
        """
        Get list of wrestlers who need booking protection.
        
        Returns:
            List of (wrestler, record) tuples
        """
        
        needs_protection = []
        
        for wrestler in wrestlers:
            record = self.get_or_create_record(wrestler.id)
            
            if record.needs_protection(wrestler):
                needs_protection.append((wrestler, record))
        
        return needs_protection
    
    def get_roster_protection_summary(
        self,
        wrestlers: List[Wrestler]
    ) -> Dict[str, any]:
        """Get summary of protection status across roster"""
        
        needs_protection = self.get_wrestlers_needing_protection(wrestlers)
        in_50_50 = []
        long_streaks = []
        
        for wrestler in wrestlers:
            record = self.get_or_create_record(wrestler.id)
            
            if record.is_in_50_50_booking():
                in_50_50.append((wrestler, record))
            
            if record.current_win_streak >= 5 or record.current_loss_streak >= 5:
                long_streaks.append((wrestler, record))
        
        return {
            'total_wrestlers': len(wrestlers),
            'needs_protection': len(needs_protection),
            'in_50_50_booking': len(in_50_50),
            'long_streaks': len(long_streaks),
            'details': {
                'needs_protection': [
                    {
                        'name': w.name,
                        'role': w.role,
                        'current_loss_streak': r.current_loss_streak,
                        'last_10': ''.join(r.last_10_results)
                    }
                    for w, r in needs_protection
                ],
                'in_50_50_booking': [
                    {
                        'name': w.name,
                        'last_10': ''.join(r.last_10_results)
                    }
                    for w, r in in_50_50
                ],
                'long_streaks': [
                    {
                        'name': w.name,
                        'win_streak': r.current_win_streak,
                        'loss_streak': r.current_loss_streak
                    }
                    for w, r in long_streaks
                ]
            }
        }


# Global protection manager instance
protection_manager = ProtectionManager()