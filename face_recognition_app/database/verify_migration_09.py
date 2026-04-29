"""
Verification script for migration 09-extend-unknown-faces-table.sql
Displays the schema changes and confirms successful migration.
"""
import psycopg2

# Database connection parameters
DB_PARAMS = {
    'host': 'localhost',
    'port': 5432,
    'database': 'face_recognition',
    'user': 'admin',
    'password': 'admin'
}

def verify_migration():
    """Verify the migration was successful."""
    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()
    
    print("=" * 80)
    print("MIGRATION 09 VERIFICATION")
    print("=" * 80)
    print()
    
    # Check new columns
    print("1. NEW COLUMNS IN unknown_faces TABLE")
    print("-" * 80)
    cursor.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = 'unknown_faces'
          AND column_name IN ('source_video_id', 'frame_timestamp', 'frame_number')
        ORDER BY column_name
    """)
    
    columns = cursor.fetchall()
    if columns:
        print(f"{'Column Name':<20} {'Data Type':<25} {'Nullable':<10} {'Default':<15}")
        print("-" * 80)
        for col in columns:
            print(f"{col[0]:<20} {col[1]:<25} {col[2]:<10} {str(col[3]):<15}")
        print(f"\n✅ Found {len(columns)} new columns")
    else:
        print("❌ No new columns found!")
    print()
    
    # Check foreign key constraint
    print("2. FOREIGN KEY CONSTRAINT")
    print("-" * 80)
    cursor.execute("""
        SELECT 
            tc.constraint_name,
            tc.constraint_type,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
          ON ccu.constraint_name = tc.constraint_name
        WHERE tc.table_name = 'unknown_faces'
          AND tc.constraint_name = 'fk_unknown_faces_source_video'
    """)
    
    fk = cursor.fetchone()
    if fk:
        print(f"Constraint Name: {fk[0]}")
        print(f"Type: {fk[1]}")
        print(f"Column: {fk[2]}")
        print(f"References: {fk[3]}.{fk[4]}")
        print("✅ Foreign key constraint exists")
    else:
        print("❌ Foreign key constraint not found!")
    print()
    
    # Check indexes
    print("3. INDEXES")
    print("-" * 80)
    cursor.execute("""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE tablename = 'unknown_faces'
          AND indexname IN ('idx_unknown_faces_source_video', 'idx_unknown_faces_status')
        ORDER BY indexname
    """)
    
    indexes = cursor.fetchall()
    if indexes:
        for idx in indexes:
            print(f"Index: {idx[0]}")
            print(f"  Definition: {idx[1]}")
            print()
        print(f"✅ Found {len(indexes)} indexes")
    else:
        print("❌ No indexes found!")
    print()
    
    # Check sample data (if any)
    print("4. SAMPLE DATA")
    print("-" * 80)
    cursor.execute("""
        SELECT COUNT(*) as total_unknown_faces,
               COUNT(source_video_id) as with_video_source,
               COUNT(frame_timestamp) as with_timestamp,
               COUNT(frame_number) as with_frame_number
        FROM unknown_faces
    """)
    
    stats = cursor.fetchone()
    print(f"Total unknown faces: {stats[0]}")
    print(f"With video source: {stats[1]}")
    print(f"With timestamp: {stats[2]}")
    print(f"With frame number: {stats[3]}")
    print()
    
    # Summary
    print("=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)
    
    success = True
    if len(columns) == 3:
        print("✅ All 3 new columns added successfully")
    else:
        print(f"❌ Expected 3 columns, found {len(columns)}")
        success = False
    
    if fk:
        print("✅ Foreign key constraint created successfully")
    else:
        print("❌ Foreign key constraint missing")
        success = False
    
    if len(indexes) >= 2:
        print("✅ Required indexes created successfully")
    else:
        print(f"❌ Expected at least 2 indexes, found {len(indexes)}")
        success = False
    
    print()
    if success:
        print("🎉 MIGRATION 09 COMPLETED SUCCESSFULLY!")
    else:
        print("⚠️  MIGRATION 09 HAS ISSUES - PLEASE REVIEW")
    print("=" * 80)
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    try:
        verify_migration()
    except Exception as e:
        print(f"❌ Error during verification: {e}")
