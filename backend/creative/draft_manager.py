"""
Draft Manager
Handles the execution and management of brand drafts.
"""

import json
import os
from typing import List, Dict, Optional, Tuple
from models.draft import BrandDraft, DraftFormat, DraftExemption
import random


class DraftManager:
    """Manages brand draft operations"""
    
    def __init__(self):
        self.current_draft: Optional[BrandDraft] = None
        self.draft_history: List[BrandDraft] = []
        self.gm_data: Dict = {}
    
    def load_gm_data(self, data_dir: str):
        """Load GM data from JSON"""
        gm_path = os.path.join(data_dir, 'authority_figures.json')
        with open(gm_path, 'r') as f:
            self.gm_data = json.load(f)
    
    def check_draft_eligibility(self, current_year: int, current_week: int) -> Tuple[bool, str, int]:
        """
        Check if a draft can be initiated (15 week cooldown).
        
        Returns:
            Tuple of (is_eligible, message, weeks_until_eligible)
        """
        if self.draft_history:
            last_draft = self.draft_history[-1]
            weeks_since = (current_year - last_draft.year) * 52 + (current_week - last_draft.week)
            
            if weeks_since < 15:
                weeks_until = 15 - weeks_since
                return (False, f"Last draft was {weeks_since} weeks ago. Must wait 15 weeks between drafts.", weeks_until)
        
        return (True, "Draft can be initiated", 0)
    
    def initiate_draft(
        self,
        universe_state,
        year: int,
        week: int,
        format_type: DraftFormat = DraftFormat.SNAKE
    ) -> BrandDraft:
        """
        Initiate a new brand draft.
        
        Steps:
        1. Check eligibility (15 week cooldown)
        2. Create draft instance
        3. Calculate exemptions
        4. Initialize draft pool
        5. Set up GMs
        6. Determine draft order
        """
        # Check if draft is allowed
        eligible, message, weeks_until = self.check_draft_eligibility(year, week)
        if not eligible:
            raise ValueError(message)
        
        # Create draft
        draft_id = f"draft_{year}_w{week}"
        draft = BrandDraft(draft_id, year, week, format_type)
        
        # Assign GMs
        gm_list = self.gm_data.get('general_managers', [])
        draft.set_gm_assignments(gm_list)
        
        # Calculate exemptions
        exemptions = draft.calculate_exemptions(universe_state)
        
        # Get all active wrestlers
        all_wrestlers = universe_state.get_active_wrestlers()
        
        # Initialize draft pool
        draft.initialize_draft_pool(all_wrestlers, exemptions)
        
        # Set initial draft order (can be randomized)
        brands = ['ROC Alpha', 'ROC Velocity', 'ROC Vanguard']
        draft.set_draft_order(brands)
        
        self.current_draft = draft
        return draft
    
    def simulate_full_draft(self, universe_state) -> Dict:
        """
        Simulate an entire draft with AI GMs making all picks.
        Optimized for speed - completes in seconds.
        
        Returns:
            Draft summary
        """
        if not self.current_draft:
            raise ValueError("No draft initiated")
        
        draft = self.current_draft
        pick_log = []
        
        print(f"\n{'='*60}")
        print(f"🎯 BRAND DRAFT {draft.year}")
        print(f"Format: {draft.format_type.value.upper()}")
        print(f"Eligible wrestlers: {len(draft.eligible_wrestlers)}")
        print(f"Exempt wrestlers: {len(draft.exemptions)}")
        print(f"{'='*60}\n")
        
        # Fast simulation - no delays
        picks_made = 0
        max_picks = len(draft.eligible_wrestlers)  # Can't pick more than available
        
        while not draft.is_complete and picks_made < max_picks:
            current_brand = draft.get_current_picking_brand()
            if not current_brand:
                break
            
            try:
                # Simulate GM pick
                pick = draft.simulate_gm_pick(current_brand, universe_state)
                pick_log.append(pick)
                picks_made += 1
                
                # Print strategic picks (first 3, last 3, and milestones)
                if picks_made <= 3 or picks_made > max_picks - 3 or picks_made % 10 == 0:
                    print(f"Pick #{pick.overall_pick}: {current_brand} selects {pick.wrestler_name} ({pick.wrestler_role})")
                elif picks_made == 4:
                    print(f"... simulating picks ...")
                
                # Occasional trades (5% chance after round 2, less frequent for speed)
                if draft.current_round > 2 and random.random() < 0.05:
                    self._attempt_trade(draft, universe_state)
                    
            except Exception as e:
                print(f"⚠️ Error making pick {picks_made}: {e}")
                break
        
        if picks_made > 6:
            print(f"\n... {picks_made} total picks completed ...\n")
        
        # Apply draft results to universe
        self._apply_draft_results(draft, universe_state)
        
        # Save to history
        self.draft_history.append(draft)
        self.current_draft = None  # Clear current draft
        
        print(f"{'='*60}")
        print(f"✅ DRAFT COMPLETE")
        print(f"Total Picks: {draft.overall_pick_count}")
        if draft.trades:
            print(f"Total Trades: {len(draft.trades)}")
        print(f"{'='*60}\n")
        
        return draft.get_draft_summary()
    
    def _attempt_trade(self, draft: BrandDraft, universe_state):
        """Attempt to execute a trade between brands"""
        brands = list(draft.brand_rosters.keys())
        
        # Pick two random brands
        if len(brands) < 2:
            return
        
        brand_a, brand_b = random.sample(brands, 2)
        
        # Each brand must have at least 2 picks to trade
        if len(draft.brand_rosters[brand_a]) < 2 or len(draft.brand_rosters[brand_b]) < 2:
            return
        
        # Pick random wrestlers from each roster (not their most recent pick)
        roster_a = draft.brand_rosters[brand_a][:-1]  # Exclude most recent
        roster_b = draft.brand_rosters[brand_b][:-1]
        
        if not roster_a or not roster_b:
            return
        
        wrestler_a_id = random.choice(roster_a)
        wrestler_b_id = random.choice(roster_b)
        
        # Get wrestler info
        wrestler_a = universe_state.get_wrestler_by_id(wrestler_a_id)
        wrestler_b = universe_state.get_wrestler_by_id(wrestler_b_id)
        
        if not wrestler_a or not wrestler_b:
            return
        
        # Simple trade logic: only trade if overall ratings are within 10 points
        if abs(wrestler_a.overall_rating - wrestler_b.overall_rating) <= 10:
            try:
                trade = draft.execute_trade(brand_a, wrestler_a_id, brand_b, wrestler_b_id)
                print(f"🔄 TRADE: {brand_a} trades {wrestler_a.name} to {brand_b} for {wrestler_b.name}")
            except Exception as e:
                # Silently fail trades to not interrupt simulation
                pass
    
    def _apply_draft_results(self, draft: BrandDraft, universe_state):
        """Apply draft results to universe state"""
        print("\n📝 Applying draft results...")
        
        # Update wrestler brands
        changes_made = 0
        changes_log = []
        
        for brand, roster in draft.brand_rosters.items():
            for wrestler_id in roster:
                wrestler = universe_state.get_wrestler_by_id(wrestler_id)
                if wrestler and wrestler.primary_brand != brand:
                    old_brand = wrestler.primary_brand
                    wrestler.primary_brand = brand
                    universe_state.save_wrestler(wrestler)
                    changes_made += 1
                    
                    # Log first 5 changes for display
                    if changes_made <= 5:
                        changes_log.append(f"   {wrestler.name}: {old_brand} → {brand}")
        
        # Print change summary
        for change in changes_log:
            print(change)
        
        if changes_made > 5:
            print(f"   ... and {changes_made - 5} more brand changes")
        
        # Commit all changes
        if hasattr(universe_state, 'db'):
            universe_state.db.conn.commit()
        else:
            # Fallback if structure is different
            try:
                import backend.app as app
                app.database.conn.commit()
            except:
                pass
        
        print(f"✅ {changes_made} wrestlers changed brands")
    
    def get_draft_report(self, draft: BrandDraft) -> Dict:
        """Generate detailed draft report"""
        report = {
            'summary': draft.get_draft_summary(),
            'brand_analysis': {},
            'best_picks': [],
            'worst_picks': [],
            'steals': [],
            'reaches': []
        }
        
        # Analyze each brand's draft
        for brand in draft.brand_rosters:
            roster_ids = draft.brand_rosters[brand]
            picks = [p for p in draft.all_picks if p.brand == brand]
            
            if not picks:
                continue
            
            # Calculate average overall
            avg_overall = sum(p.wrestler_overall for p in picks) / len(picks) if picks else 0
            
            # Find best and worst picks
            picks_sorted = sorted(picks, key=lambda p: p.wrestler_overall, reverse=True)
            
            report['brand_analysis'][brand] = {
                'total_picks': len(picks),
                'average_overall': round(avg_overall, 1),
                'best_pick': {
                    'wrestler': picks_sorted[0].wrestler_name,
                    'overall': picks_sorted[0].wrestler_overall,
                    'round': picks_sorted[0].round_number
                } if picks_sorted else None,
                'worst_pick': {
                    'wrestler': picks_sorted[-1].wrestler_name,
                    'overall': picks_sorted[-1].wrestler_overall,
                    'round': picks_sorted[-1].round_number
                } if len(picks_sorted) > 1 else None
            }
        
        # Find best value picks (steals) - only if we have enough picks
        if len(draft.all_picks) > 5:
            for pick in draft.all_picks:
                # Adjust expectation calculation for small draft pools
                if len(draft.all_picks) < 20:
                    expected_pick = (pick.wrestler_overall - 40) / 5  # Adjusted for smaller pools
                else:
                    expected_pick = pick.wrestler_overall / 10
                
                if pick.overall_pick > expected_pick + 3:  # Lowered threshold for small drafts
                    report['steals'].append({
                        'wrestler': pick.wrestler_name,
                        'overall': pick.wrestler_overall,
                        'picked_at': pick.overall_pick,
                        'brand': pick.brand
                    })
        
        # Find reaches (picked too early) - only if we have enough picks
        if len(draft.all_picks) > 5:
            for pick in draft.all_picks[:min(10, len(draft.all_picks))]:  # Only check early picks
                if len(draft.all_picks) < 20:
                    expected_pick = (pick.wrestler_overall - 40) / 5
                else:
                    expected_pick = pick.wrestler_overall / 10
                
                if pick.overall_pick < expected_pick - 3:
                    report['reaches'].append({
                        'wrestler': pick.wrestler_name,
                        'overall': pick.wrestler_overall,
                        'picked_at': pick.overall_pick,
                        'brand': pick.brand
                    })
        
        # Sort steals and reaches
        report['steals'].sort(key=lambda x: x['overall'], reverse=True)
        report['reaches'].sort(key=lambda x: x['picked_at'])
        
        # Limit to top 5 each
        report['steals'] = report['steals'][:5]
        report['reaches'] = report['reaches'][:5]
        
        return report
    
    def save_draft_to_history(self, draft: BrandDraft, database):
        """Save draft to database for historical tracking"""
        # This would save to a draft_history table
        # For now, we'll just track in memory
        if draft not in self.draft_history:
            self.draft_history.append(draft)
    
    def get_last_draft(self) -> Optional[BrandDraft]:
        """Get the most recent draft"""
        return self.draft_history[-1] if self.draft_history else None
    
    def clear_current_draft(self):
        """Clear the current draft (used after completion or cancellation)"""
        self.current_draft = None


# Global instance
draft_manager = DraftManager()