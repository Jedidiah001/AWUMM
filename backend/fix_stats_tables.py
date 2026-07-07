"""
One-time script to add stats tables to existing database
"""

import sqlite3
import os
from datetime import datetime

# Get database path
db_path = os.path.join(os.path.dirname(__file__), 'data', 'awum.db')

print(f"Connecting to database: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Creating wrestler_stats table...")

cursor.execute('''
    CREATE TABLE IF NOT EXISTS wrestler_stats (
        wrestler_id TEXT PRIMARY KEY,
        
        -- Win/Loss
        total_matches INTEGER NOT NULL DEFAULT 0,
        wins INTEGER NOT NULL DEFAULT 0,
        losses INTEGER NOT NULL DEFAULT 0,
        draws INTEGER NOT NULL DEFAULT 0,
        
        -- Quality
        total_star_rating REAL NOT NULL DEFAULT 0,
        highest_star_rating REAL NOT NULL DEFAULT 0,
        five_star_matches INTEGER NOT NULL DEFAULT 0,
        four_star_plus_matches INTEGER NOT NULL DEFAULT 0,
        
        -- Titles
        total_title_reigns INTEGER NOT NULL DEFAULT 0,
        total_days_as_champion INTEGER NOT NULL DEFAULT 0,
        longest_reign_days INTEGER NOT NULL DEFAULT 0,
        
        -- Achievements
        total_main_events INTEGER NOT NULL DEFAULT 0,
        total_ppv_matches INTEGER NOT NULL DEFAULT 0,
        total_upsets INTEGER NOT NULL DEFAULT 0,
        total_upset_losses INTEGER NOT NULL DEFAULT 0,
        
        -- Finishes
        clean_wins INTEGER NOT NULL DEFAULT 0,
        cheating_wins INTEGER NOT NULL DEFAULT 0,
        dq_countout_wins INTEGER NOT NULL DEFAULT 0,
        submission_wins INTEGER NOT NULL DEFAULT 0,
        
        -- Streaks
        current_win_streak INTEGER NOT NULL DEFAULT 0,
        current_loss_streak INTEGER NOT NULL DEFAULT 0,
        longest_win_streak INTEGER NOT NULL DEFAULT 0,
        longest_loss_streak INTEGER NOT NULL DEFAULT 0,
        
        last_updated TEXT NOT NULL,
        
        FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
    )
''')

print("✅ wrestler_stats table created")

print("Creating milestones table...")

cursor.execute('''
    CREATE TABLE IF NOT EXISTS milestones (
        id TEXT PRIMARY KEY,
        wrestler_id TEXT NOT NULL,
        milestone_type TEXT NOT NULL,
        description TEXT NOT NULL,
        achieved_at_show_id TEXT NOT NULL,
        achieved_at_show_name TEXT NOT NULL,
        year INTEGER NOT NULL,
        week INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
    )
''')

print("✅ milestones table created")

print("Creating indexes...")

cursor.execute('CREATE INDEX IF NOT EXISTS idx_milestones_wrestler ON milestones(wrestler_id)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_milestones_type ON milestones(milestone_type)')

print("✅ Indexes created")

conn.commit()

# Verify tables exist
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name='wrestler_stats' OR name='milestones')")
tables = cursor.fetchall()

print("\n📊 Verification:")
for table in tables:
    print(f"  ✅ Table exists: {table[0]}")

# Count wrestlers
cursor.execute("SELECT COUNT(*) FROM wrestlers")
wrestler_count = cursor.fetchone()[0]
print(f"\n👥 Total wrestlers in database: {wrestler_count}")

# Count existing stats
cursor.execute("SELECT COUNT(*) FROM wrestler_stats")
stats_count = cursor.fetchone()[0]
print(f"📊 Stats records: {stats_count}")

if stats_count == 0:
    print("\n⚠️  Stats cache is empty. Run the update command next.")

conn.close()

print("\n✅ Database schema updated successfully!")
print("\nNext step: Run this command to populate stats:")
print("  curl -X POST http://localhost:8080/api/stats/update-all")