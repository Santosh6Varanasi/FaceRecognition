#!/usr/bin/env python3
"""
Migration script to run 08-create-timeline-entries-table.sql
"""
import psycopg2
import sys
from pathlib import Path

def run_migration():
    """Execute the migration script."""
    
    # Try multiple credential combinations
    credential_options = [
        {'host': 'localhost', 'database': 'face_recognition', 'user': 'admin', 'password': 'admin'},
        {'host': 'localhost', 'database': 'face_recognition', 'user': 'postgres', 'password': 'postgres'},
    ]
    
    conn_params = None
    conn = None
    
    # Read migration file
    migration_file = Path(__file__).parent / '08-create-timeline-entries-table.sql'
    
    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        sys.exit(1)
    
    with open(migration_file, 'r') as f:
        migration_sql = f.read()
    
    # Try to connect with different credentials
    for params in credential_options:
        try:
            conn = psycopg2.connect(**params)
            conn_params = params
            break
        except psycopg2.Error:
            continue
    
    if conn is None:
        print("❌ Could not connect to database with any known credentials")
        print("   Tried: admin:admin and postgres:postgres")
        print("   Please ensure PostgreSQL is running and credentials are correct")
        sys.exit(1)
    
    # Execute migration
    try:
        cursor = conn.cursor()
        
        print(f"✅ Connected to database: {conn_params['database']}")
        print(f"📄 Executing migration: {migration_file.name}")
        
        # Execute the migration
        cursor.execute(migration_sql)
        conn.commit()
        
        print("✅ Migration completed successfully!")
        
        # Display results
        print("\n" + "=" * 80)
        print("MIGRATION RESULTS")
        print("=" * 80)
        
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()
