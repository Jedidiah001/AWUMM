"""
Save/Load Manager
Handles universe save files with multiple slots.
"""

import os
import json
import shutil
import sqlite3
from typing import List, Optional, Dict, Any
from datetime import datetime
from models.save_file import SaveMetadata, UniverseSnapshot
from persistence.database import Database


class SaveManager:
    """
    Manages save files for AWUM.
    Supports multiple save slots and auto-save.
    """
    
    def __init__(self, saves_dir: str):
        self.saves_dir = saves_dir
        self.ensure_saves_directory()
    
    def ensure_saves_directory(self):
        """Create saves directory if it doesn't exist"""
        os.makedirs(self.saves_dir, exist_ok=True)
        os.makedirs(os.path.join(self.saves_dir, 'backups'), exist_ok=True)
    
    def get_save_path(self, slot: int) -> str:
        """Get file path for a save slot"""
        return os.path.join(self.saves_dir, f'save_slot_{slot}.json')
    
    def get_autosave_path(self) -> str:
        """Get file path for autosave"""
        return os.path.join(self.saves_dir, 'autosave.json')
    
    def list_saves(self) -> List[SaveMetadata]:
        """
        List all available save files.
        Returns metadata for each save slot.
        """
        saves = []
        
        # Check slots 1-10
        for slot in range(1, 11):
            save_path = self.get_save_path(slot)
            
            if os.path.exists(save_path):
                try:
                    with open(save_path, 'r') as f:
                        data = json.load(f)
                        metadata = SaveMetadata.from_dict(data['metadata'])
                        saves.append(metadata)
                except Exception as e:
                    print(f"⚠️ Failed to load save slot {slot}: {e}")
        
        # Check autosave
        autosave_path = self.get_autosave_path()
        if os.path.exists(autosave_path):
            try:
                with open(autosave_path, 'r') as f:
                    data = json.load(f)
                    metadata = SaveMetadata.from_dict(data['metadata'])
                    metadata.save_slot = 0  # 0 = autosave
                    metadata.save_name = f"[AUTO] {metadata.save_name}"
                    saves.append(metadata)
            except Exception as e:
                print(f"⚠️ Failed to load autosave: {e}")
        
        return saves
    
    def save_universe(
        self,
        database: Database,
        slot: int,
        save_name: str,
        include_history: bool = True
    ) -> SaveMetadata:
        """
        Save complete universe state to a slot.
        
        Args:
            database: Database instance
            slot: Save slot number (1-10, or 0 for autosave)
            save_name: Human-readable name for the save
            include_history: Whether to include full match/show history
        
        Returns:
            SaveMetadata for the created save
        """
        print(f"\n💾 Saving universe to slot {slot}...")
        
        # Get game state
        game_state = database.get_game_state()
        
        # Create metadata
        now = datetime.now().isoformat()
        
        # Get statistics
        cursor = database.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM wrestlers WHERE is_retired = 0')
        active_wrestlers = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM feuds WHERE status != "resolved"')
        active_feuds = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM show_history')
        total_shows = cursor.fetchone()[0]
        
        metadata = SaveMetadata(
            save_slot=slot,
            save_name=save_name,
            created_at=now,
            last_modified=now,
            current_year=game_state['current_year'],
            current_week=game_state['current_week'],
            balance=game_state['balance'],
            show_count=game_state['show_count'],
            total_wrestlers=active_wrestlers,
            active_feuds=active_feuds,
            total_shows_run=total_shows
        )
        
        # Create snapshot
        snapshot = UniverseSnapshot(
            metadata=metadata,
            game_state=game_state
        )
        
        # Get all wrestlers
        print("  📊 Saving wrestlers...")
        snapshot.wrestlers = database.get_all_wrestlers(active_only=False)
        
        # Get all championships (with history)
        print("  🏆 Saving championships...")
        champs = database.get_all_championships()
        
        # Get title reigns for each championship
        snapshot.title_reigns = []
        for champ in champs:
            cursor.execute('SELECT * FROM title_reigns WHERE title_id = ?', (champ['id'],))
            reigns = [dict(row) for row in cursor.fetchall()]
            snapshot.title_reigns.extend(reigns)
        
        snapshot.championships = champs
        
        # Get all feuds
        print("  🔥 Saving feuds...")
        snapshot.feuds = database.get_all_feuds(active_only=False)
        
        # Get stats
        print("  📈 Saving wrestler stats...")
        cursor.execute('SELECT * FROM wrestler_stats')
        snapshot.wrestler_stats = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute('SELECT * FROM milestones')
        snapshot.milestones = [dict(row) for row in cursor.fetchall()]
        
        # Save storyline state (STEP 16 ADDITION)
        print("  🎭 Saving storylines...")
        from creative.storylines import storyline_engine
        snapshot.storylines = storyline_engine.save_state()
        
        # Optionally include full history
        if include_history:
            print("  📜 Saving match history...")
            snapshot.match_history = database.get_match_history(limit=10000)
            
            print("  📺 Saving show history...")
            snapshot.show_history = database.get_show_history(limit=10000)
        else:
            print("  ⏭️  Skipping full history (quick save)")
        
        # Write to file
        save_path = self.get_save_path(slot) if slot > 0 else self.get_autosave_path()
        
        # Backup existing save if it exists
        if os.path.exists(save_path):
            backup_path = os.path.join(
                self.saves_dir,
                'backups',
                f'save_slot_{slot}_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            )
            shutil.copy2(save_path, backup_path)
            print(f"  💾 Backed up existing save to {os.path.basename(backup_path)}")
        
        # Write save file
        with open(save_path, 'w') as f:
            json.dump(snapshot.to_dict(), f, indent=2)
        
        file_size = os.path.getsize(save_path) / 1024  # KB
        print(f"✅ Save complete! File size: {file_size:.1f} KB")
        
        return metadata
    
    def load_universe(self, database: Database, slot: int) -> UniverseSnapshot:
        """
        Load universe state from a save slot.
        
        Args:
            database: Database instance
            slot: Save slot number (1-10, or 0 for autosave)
        
        Returns:
            UniverseSnapshot
        """
        save_path = self.get_save_path(slot) if slot > 0 else self.get_autosave_path()
        
        if not os.path.exists(save_path):
            raise FileNotFoundError(f"Save slot {slot} does not exist")
        
        print(f"\n📂 Loading universe from slot {slot}...")
        
        # Read save file
        with open(save_path, 'r') as f:
            data = json.load(f)
        
        snapshot = UniverseSnapshot.from_dict(data)
        
        print(f"  📅 Save Date: {snapshot.metadata.last_modified}")
        print(f"  🎮 Year {snapshot.metadata.current_year}, Week {snapshot.metadata.current_week}")
        print(f"  💰 Balance: ${snapshot.metadata.balance:,}")
        
        # Clear existing database (DANGEROUS - make sure to backup!)
        print("  🗑️  Clearing current universe...")
        self._clear_database(database)
        
        # Restore game state
        print("  🎮 Restoring game state...")
        database.update_game_state(
            current_year=snapshot.game_state['current_year'],
            current_week=snapshot.game_state['current_week'],
            current_show_index=snapshot.game_state['current_show_index'],
            balance=snapshot.game_state['balance'],
            show_count=snapshot.game_state['show_count']
        )
        
        # Restore wrestlers
        print(f"  👥 Restoring {len(snapshot.wrestlers)} wrestlers...")
        for w_dict in snapshot.wrestlers:
            from models.wrestler import Wrestler
            wrestler = Wrestler.from_dict(w_dict)
            database.save_wrestler(wrestler)
        database.conn.commit()
        
        # Restore championships
        print(f"  🏆 Restoring {len(snapshot.championships)} championships...")
        for c_dict in snapshot.championships:
            from models.championship import Championship
            championship = Championship.from_dict(c_dict)
            database.save_championship(championship)
        database.conn.commit()
        
        # Restore title reigns
        print(f"  👑 Restoring {len(snapshot.title_reigns)} title reigns...")
        cursor = database.conn.cursor()
        for reign in snapshot.title_reigns:
            cursor.execute('''
                INSERT INTO title_reigns (
                    title_id, wrestler_id, wrestler_name,
                    won_at_show_id, won_at_show_name,
                    won_date_year, won_date_week,
                    lost_at_show_id, lost_at_show_name,
                    lost_date_year, lost_date_week,
                    days_held, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                reign['title_id'], reign['wrestler_id'], reign['wrestler_name'],
                reign['won_at_show_id'], reign['won_at_show_name'],
                reign['won_date_year'], reign['won_date_week'],
                reign['lost_at_show_id'], reign['lost_at_show_name'],
                reign['lost_date_year'], reign['lost_date_week'],
                reign['days_held'], reign['created_at']
            ))
        database.conn.commit()
        
        # Restore feuds
        print(f"  🔥 Restoring {len(snapshot.feuds)} feuds...")
        for f_dict in snapshot.feuds:
            from models.feud import Feud
            feud = Feud.from_dict(f_dict)
            database.save_feud(feud)
        database.conn.commit()
        
        # Restore stats
        if snapshot.wrestler_stats:
            print(f"  📊 Restoring wrestler stats...")
            cursor = database.conn.cursor()
            for stats in snapshot.wrestler_stats:
                cursor.execute('''
                    INSERT OR REPLACE INTO wrestler_stats (
                        wrestler_id, total_matches, wins, losses, draws,
                        total_star_rating, highest_star_rating,
                        five_star_matches, four_star_plus_matches,
                        total_title_reigns, total_days_as_champion, longest_reign_days,
                        total_main_events, total_ppv_matches,
                        total_upsets, total_upset_losses,
                        clean_wins, cheating_wins, dq_countout_wins, submission_wins,
                        current_win_streak, current_loss_streak,
                        longest_win_streak, longest_loss_streak,
                        last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    stats['wrestler_id'], stats['total_matches'],
                    stats['wins'], stats['losses'], stats['draws'],
                    stats['total_star_rating'], stats['highest_star_rating'],
                    stats['five_star_matches'], stats['four_star_plus_matches'],
                    stats['total_title_reigns'], stats['total_days_as_champion'],
                    stats['longest_reign_days'], stats['total_main_events'],
                    stats['total_ppv_matches'], stats['total_upsets'],
                    stats['total_upset_losses'], stats['clean_wins'],
                    stats['cheating_wins'], stats['dq_countout_wins'],
                    stats['submission_wins'], stats['current_win_streak'],
                    stats['current_loss_streak'], stats['longest_win_streak'],
                    stats['longest_loss_streak'], stats['last_updated']
                ))
            database.conn.commit()
        
        # Restore milestones
        if snapshot.milestones:
            print(f"  🌟 Restoring milestones...")
            cursor = database.conn.cursor()
            for milestone in snapshot.milestones:
                cursor.execute('''
                    INSERT OR IGNORE INTO milestones (
                        id, wrestler_id, milestone_type, description,
                        achieved_at_show_id, achieved_at_show_name,
                        year, week, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    milestone['id'], milestone['wrestler_id'],
                    milestone['milestone_type'], milestone['description'],
                    milestone['achieved_at_show_id'], milestone['achieved_at_show_name'],
                    milestone['year'], milestone['week'], milestone['created_at']
                ))
            database.conn.commit()
        
        # Restore storylines (STEP 16 ADDITION)
        if hasattr(snapshot, 'storylines') and snapshot.storylines:
            print(f"  🎭 Restoring storylines...")
            from creative.storylines import storyline_engine
            storyline_engine.load_state(snapshot.storylines)
        
        # Restore history if present
        if snapshot.match_history:
            print(f"  📜 Restoring {len(snapshot.match_history)} matches...")
            cursor = database.conn.cursor()
            for match in snapshot.match_history:
                cursor.execute('''
                    INSERT INTO match_history (
                        match_id, show_id, show_name, year, week,
                        side_a_ids, side_a_names, side_b_ids, side_b_names,
                        winner, finish_type, duration_minutes, star_rating,
                        is_title_match, title_id, title_changed_hands,
                        is_upset, feud_id, match_summary, highlights, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                ''', (
                    match['match_id'], match['show_id'], match['show_name'],
                    match['year'], match['week'],
                    json.dumps(match['side_a_ids']), json.dumps(match['side_a_names']),
                    json.dumps(match['side_b_ids']), json.dumps(match['side_b_names']),
                    match['winner'], match['finish_type'],
                    match['duration_minutes'], match['star_rating'],
                    match['is_title_match'], match['title_id'],
                    match['title_changed_hands'], match['is_upset'],
                    match['feud_id'], match['match_summary'],
                    json.dumps(match['highlights']), match['created_at']
                ))
            database.conn.commit()
        
        if snapshot.show_history:
            print(f"  📺 Restoring {len(snapshot.show_history)} shows...")
            cursor = database.conn.cursor()
            for show in snapshot.show_history:
                cursor.execute('''
                    INSERT INTO show_history (
                        show_id, show_name, brand, show_type, year, week,
                        match_count, overall_rating,
                        total_attendance, total_revenue, total_payroll, net_profit,
                        events, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    show['show_id'], show['show_name'], show['brand'],
                    show['show_type'], show['year'], show['week'],
                    show['match_count'], show['overall_rating'],
                    show['total_attendance'], show['total_revenue'],
                    show['total_payroll'], show['net_profit'],
                    json.dumps(show['events']), show['created_at']
                ))
            database.conn.commit()
        
        print("✅ Universe loaded successfully!")
        
        return snapshot
    
    def _clear_database(self, database: Database):
        """Clear all data from database (WARNING: DESTRUCTIVE)"""
        cursor = database.conn.cursor()
        
        # Clear all tables (except game_state which we'll update)
        tables = [
            'match_history',
            'show_history',
            'feud_segments',
            'feuds',
            'title_reigns',
            'championships',
            'wrestlers',
            'wrestler_stats',
            'milestones',
            'storylines'  # Added for STEP 16
        ]
        
        for table in tables:
            try:
                cursor.execute(f'DELETE FROM {table}')
            except sqlite3.OperationalError:
                # Table might not exist in older saves
                pass
        
        database.conn.commit()
    
    def delete_save(self, slot: int) -> bool:
        """Delete a save slot"""
        save_path = self.get_save_path(slot) if slot > 0 else self.get_autosave_path()
        
        if os.path.exists(save_path):
            os.remove(save_path)
            print(f"🗑️  Deleted save slot {slot}")
            return True
        
        return False
    
    def export_save(self, slot: int, export_path: str):
        """Export a save file to a specific path"""
        save_path = self.get_save_path(slot) if slot > 0 else self.get_autosave_path()
        
        if not os.path.exists(save_path):
            raise FileNotFoundError(f"Save slot {slot} does not exist")
        
        shutil.copy2(save_path, export_path)
        print(f"📤 Exported save slot {slot} to {export_path}")
    
    def import_save(self, import_path: str, slot: int):
        """Import a save file from a specific path"""
        if not os.path.exists(import_path):
            raise FileNotFoundError(f"Import file not found: {import_path}")
        
        # Validate it's a valid save file
        with open(import_path, 'r') as f:
            data = json.load(f)
            if 'metadata' not in data or 'game_state' not in data:
                raise ValueError("Invalid save file format")
        
        save_path = self.get_save_path(slot) if slot > 0 else self.get_autosave_path()
        shutil.copy2(import_path, save_path)
        print(f"📥 Imported save to slot {slot}")
