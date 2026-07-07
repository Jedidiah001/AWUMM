"""
Contract Promise Manager
STEP 121: Tracks and enforces contract promises (title shots, brand transfers, etc.)
"""

from typing import Dict, List, Any, Optional
from models.wrestler import Wrestler


class ContractPromiseManager:
    """
    Manages contract promises and their fulfillment.
    
    Promise Types:
    - title_shot: Promised championship opportunity
    - brand_transfer: Promised brand move
    - main_event_push: Promised main event position
    - creative_control: Promised booking input
    """
    
    def __init__(self, database):
        self.database = database
    
    def create_title_shot_promise(
        self,
        wrestler_id: str,
        wrestler_name: str,
        current_year: int,
        current_week: int,
        deadline_weeks: int = 26,
        title_tier: str = 'any'
    ) -> int:
        """
        Create a promise to give wrestler a title opportunity.
        
        Args:
            wrestler_id: Wrestler ID
            wrestler_name: Wrestler name
            current_year: Year promise was made
            current_week: Week promise was made
            deadline_weeks: Weeks until promise must be fulfilled (default 26 = 6 months)
            title_tier: 'world', 'secondary', 'tag', or 'any'
        
        Returns:
            Promise ID
        """
        promise_data = {
            'promise_type': 'title_shot',
            'wrestler_id': wrestler_id,
            'wrestler_name': wrestler_name,
            'promised_year': current_year,
            'promised_week': current_week,
            'deadline_weeks': deadline_weeks,
            'details': {
                'title_tier': title_tier
            }
        }
        
        promise_id = self.database.save_contract_promise(promise_data)
        
        print(f"🏆 Title shot promised to {wrestler_name} (must deliver within {deadline_weeks} weeks)")
        
        return promise_id
    
    def create_brand_transfer_promise(
        self,
        wrestler_id: str,
        wrestler_name: str,
        target_brand: str,
        current_year: int,
        current_week: int,
        immediate: bool = True
    ) -> int:
        """
        Create a promise to transfer wrestler to specific brand.
        
        Args:
            wrestler_id: Wrestler ID
            wrestler_name: Wrestler name
            target_brand: Brand to transfer to
            current_year: Year promise was made
            current_week: Week promise was made
            immediate: If True, transfer happens immediately
        
        Returns:
            Promise ID
        """
        deadline_weeks = 1 if immediate else 4
        
        promise_data = {
            'promise_type': 'brand_transfer',
            'wrestler_id': wrestler_id,
            'wrestler_name': wrestler_name,
            'promised_year': current_year,
            'promised_week': current_week,
            'deadline_weeks': deadline_weeks,
            'details': {
                'target_brand': target_brand,
                'immediate': immediate
            }
        }
        
        promise_id = self.database.save_contract_promise(promise_data)
        
        print(f"🔄 Brand transfer to {target_brand} promised to {wrestler_name}")
        
        return promise_id
    
    def check_title_match_fulfills_promise(
        self,
        wrestler_id: str,
        title_id: str,
        current_year: int,
        current_week: int
    ) -> Optional[int]:
        """
        Check if a title match fulfills an active promise.
        
        Returns promise_id if fulfilled, None otherwise.
        """
        active_promises = self.database.get_active_promises(wrestler_id)
        
        for promise in active_promises:
            if promise['promise_type'] == 'title_shot':
                # Any title match fulfills the promise
                self.database.fulfill_promise(
                    promise['id'],
                    current_year,
                    current_week,
                    f"Title match for {title_id}"
                )
                
                print(f"✅ Title shot promise fulfilled for {promise['wrestler_name']}")
                
                return promise['id']
        
        return None
    
    def check_brand_transfer_fulfills_promise(
        self,
        wrestler_id: str,
        new_brand: str,
        current_year: int,
        current_week: int
    ) -> Optional[int]:
        """
        Check if a brand transfer fulfills an active promise.
        
        Returns promise_id if fulfilled, None otherwise.
        """
        active_promises = self.database.get_active_promises(wrestler_id)
        
        for promise in active_promises:
            if promise['promise_type'] == 'brand_transfer':
                # Check if transferred to promised brand
                details = promise.get('details', {})
                target_brand = details.get('target_brand')
                
                if new_brand == target_brand:
                    self.database.fulfill_promise(
                        promise['id'],
                        current_year,
                        current_week,
                        f"Transferred to {new_brand}"
                    )
                    
                    print(f"✅ Brand transfer promise fulfilled for {promise['wrestler_name']}")
                    
                    return promise['id']
        
        return None
    
    def process_weekly_promise_check(
        self,
        current_year: int,
        current_week: int,
        wrestlers: List[Wrestler]
    ) -> Dict[str, List]:
        """
        Weekly check for overdue promises.
        Applies morale penalties for broken promises.
        
        Returns:
            Dict with 'overdue' and 'warnings' lists
        """
        overdue_promises = self.database.check_overdue_promises(current_year, current_week)
        
        results = {
            'overdue': [],
            'warnings': [],
            'broken': []
        }
        
        for promise in overdue_promises:
            wrestler_id = promise['wrestler_id']
            wrestler_name = promise['wrestler_name']
            promise_type = promise['promise_type']
            
            # Find wrestler
            wrestler = next((w for w in wrestlers if w.id == wrestler_id), None)
            
            if not wrestler:
                continue
            
            # Calculate how overdue
            promised_year = promise['promised_year']
            promised_week = promise['promised_week']
            deadline_weeks = promise['deadline_weeks']
            
            deadline_year = promised_year
            deadline_week = promised_week + deadline_weeks
            
            if deadline_week > 52:
                deadline_year += deadline_week // 52
                deadline_week = deadline_week % 52
            
            weeks_overdue = (current_year - deadline_year) * 52 + (current_week - deadline_week)
            
            if weeks_overdue > 4:
                # Break the promise and apply penalty
                morale_penalty = min(30, weeks_overdue * 2)  # Up to -30 morale
                
                wrestler.adjust_morale(-morale_penalty)
                
                self.database.break_promise(
                    promise['id'],
                    f"Promise not fulfilled after {weeks_overdue} weeks overdue",
                    morale_penalty
                )
                
                results['broken'].append({
                    'wrestler_name': wrestler_name,
                    'promise_type': promise_type,
                    'weeks_overdue': weeks_overdue,
                    'morale_penalty': morale_penalty
                })
                
                print(f"⚠️ BROKEN PROMISE: {wrestler_name} ({promise_type}) - {morale_penalty} morale penalty")
            
            else:
                # Just overdue, not broken yet - warning
                results['overdue'].append({
                    'wrestler_name': wrestler_name,
                    'promise_type': promise_type,
                    'weeks_overdue': weeks_overdue,
                    'deadline_approaching': True
                })
                
                # If 1-2 weeks overdue, give warning
                if weeks_overdue <= 2:
                    results['warnings'].append({
                        'wrestler_name': wrestler_name,
                        'promise_type': promise_type,
                        'weeks_until_broken': 4 - weeks_overdue
                    })
        
        return results
    
    def get_promise_summary(self, wrestler_id: str) -> Dict[str, Any]:
        """Get summary of all promises for a wrestler"""
        promises = self.database.get_wrestler_promises(wrestler_id)
        
        return {
            'total_promises': len(promises['active']) + len(promises['fulfilled']) + len(promises['broken']),
            'active_count': len(promises['active']),
            'fulfilled_count': len(promises['fulfilled']),
            'broken_count': len(promises['broken']),
            'promises': promises,
            'trust_rating': self._calculate_trust_rating(promises)
        }
    
    def _calculate_trust_rating(self, promises: Dict[str, List]) -> str:
        """Calculate trust rating based on promise history"""
        total = len(promises['fulfilled']) + len(promises['broken'])
        
        if total == 0:
            return 'Unknown'
        
        fulfillment_rate = len(promises['fulfilled']) / total
        
        if fulfillment_rate >= 0.9:
            return 'Excellent'
        elif fulfillment_rate >= 0.75:
            return 'Good'
        elif fulfillment_rate >= 0.5:
            return 'Fair'
        else:
            return 'Poor'


# Global promise manager instance (initialized with database)
promise_manager = None

def initialize_promise_manager(database):
    """Initialize the global promise manager"""
    global promise_manager
    promise_manager = ContractPromiseManager(database)
    return promise_manager