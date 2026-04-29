"""
Verification script for migration 06-enhance-videos-table.sql
"""
import psycopg2

def verify_migration():
    """Verify the migration was applied correctly."""
    conn_params = {
        'host': 'localhost',
        'port': 5432,
        'database': 'face_recognition',
        'user': 'admin',
        'password': 'admin'
    }
    
    try:
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        
        print("=" * 80)
        print("MIGRATION VERIFICATION: 06-enhance-videos-table.sql")
        print("=" * 80)
        
        # Check columns
        print("\n📋 Checking new columns in 'videos' table:")
        cursor.execute("""
            SELECT 
                column_name, 
                data_type, 
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = 'videos'
              AND column_name IN ('frame_count', 'uploaded_by', 'processed_at', 'reprocessed_at', 'model_version')
            ORDER BY column_name
        """)
        
        columns = cursor.fetchall()
        if columns:
            print(f"{'Column Name':<20} {'Data Type':<15} {'Nullable':<10} {'Default':<20}")
            print("-" * 70)
            for col in columns:
                print(f"{col[0]:<20} {col[1]:<15} {col[2]:<10} {str(col[3] or ''):<20}")
            print(f"\n✅ Found {len(columns)} new columns")
        else:
            print("❌ No new columns found!")
        
        # Check indexes
        print("\n📊 Checking indexes on 'videos' table:")
        cursor.execute("""
            SELECT 
                indexname,
                indexdef
            FROM pg_indexes
            WHERE tablename = 'videos'
              AND indexname IN ('idx_videos_status', 'idx_videos_uploaded_at', 
                               'idx_videos_model_version', 'idx_videos_uploaded_by')
            ORDER BY indexname
        """)
        
        indexes = cursor.fetchall()
        if indexes:
            for idx_name, idx_def in indexes:
                print(f"  ✅ {idx_name}")
                print(f"     {idx_def}")
            print(f"\n✅ Found {len(indexes)} indexes")
        else:
            print("❌ No indexes found!")
        
        # Show all columns in videos table
        print("\n📋 All columns in 'videos' table:")
        cursor.execute("""
            SELECT 
                column_name, 
                data_type
            FROM information_schema.columns
            WHERE table_name = 'videos'
            ORDER BY ordinal_position
        """)
        
        all_columns = cursor.fetchall()
        print(f"{'Column Name':<30} {'Data Type':<20}")
        print("-" * 50)
        for col in all_columns:
            print(f"{col[0]:<30} {col[1]:<20}")
        
        print("\n" + "=" * 80)
        print("✅ VERIFICATION COMPLETE")
        print("=" * 80)
        
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    verify_migration()
