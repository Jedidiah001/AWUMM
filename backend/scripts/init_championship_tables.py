"""
Initialize Championship Tables
Run this script once to create all championship-related tables.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from persistence.database import Database
from persistence.championship_db import create_championship_tables
from persistence.championship_custom_db import create_custom_championship_tables

def main():
    print("🏆 Championship Tables Initialization")
    print("=" * 60)
    
    # Initialize database
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    db_path = os.path.join(data_dir, 'awum.db')
    
    print(f"📂 Database: {db_path}")
    
    database = Database(db_path)
    
    print("\n📊 Creating championship hierarchy tables...")
    try:
        create_championship_tables(database)
        print("✅ Championship hierarchy tables created")
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    print("\n📊 Creating custom championship tables...")
    try:
        create_custom_championship_tables(database)
        print("✅ Custom championship tables created")
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    print("\n" + "=" * 60)
    print("✅ All championship tables created successfully!")
    print("\nYou can now:")
    print("  - Create custom championships")
    print("  - Track title defenses")
    print("  - Manage vacancies")
    print("  - Grant title shots")
    print("  - Unify/split championships")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())