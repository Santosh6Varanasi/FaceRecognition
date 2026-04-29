#!/usr/bin/env python3
"""
Verification script for migration 07-create-video-detections-table.sql
"""
import psycopg2

def verify_migration():
    """Verify the migration was applied correctly."""
    
    conn_params = {
        'host': 'localhost',
        'database': 'face_recognition',
        'user': 'postgres',
        'password': 'postgres'
    }
    
    try:
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        
        print("=" * 80)
        print("MIGRATION VERIFICATION: 07-create-video-detections-table.sql")
        print("=" * 80)
        
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'video_detections'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            print("✅ Table 'video_detections' exists")
        else:
            print("❌ Table 'video_detections' does NOT exist")
            return
        
        # Check columns
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'video_detections'
            ORDER BY ordinal_position;
        """)
        columns = cursor.fetchall()
        
        print("\n📋 Table Columns:")
        print("-" * 80)
        expected_columns = [
            'id', 'video_id', 'frame_number', 'timestamp', 'person_id',
            'person_name', 'bbox_x1', 'bbox_y1', 'bbox_x2', 'bbox_y2',
            'recognition_confidence', 'detection_confidence', 'is_unknown',
            'created_at'
        ]
        
        found_columns = [col[0] for col in columns]
        for col_name in expected_columns:
            if col_name in found_columns:
                print(f"  ✅ {col_name}")
            else:
                print(f"  ❌ {col_name} - MISSING")
        
        # Check indexes
        cursor.execute("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'video_detections'
            ORDER BY indexname;
        """)
        indexes = cursor.fetchall()
        
        print("\n🔍 Indexes:")
        print("-" * 80)
        expected_indexes = [
            'idx_video_detections_video_timestamp',
            'idx_video_detections_person',
            'idx_video_detections_unknown'
        ]
        
        found_indexes = [idx[0] for idx in indexes]
        for idx_name in expected_indexes:
            if idx_name in found_indexes:
                print(f"  ✅ {idx_name}")
            else:
                print(f"  ❌ {idx_name} - MISSING")
        
        # Check foreign key constraints
        cursor.execute("""
            SELECT
                tc.constraint_name,
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = 'video_detections';
        """)
        foreign_keys = cursor.fetchall()
        
        print("\n🔗 Foreign Key Constraints:")
        print("-" * 80)
        if foreign_keys:
            for fk in foreign_keys:
                print(f"  ✅ {fk[2]} -> {fk[3]}.{fk[4]}")
        else:
            print("  ⚠️  No foreign key constraints found")
        
        # Check CASCADE delete on video_id
        cursor.execute("""
            SELECT
                tc.constraint_name,
                rc.delete_rule
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.referential_constraints AS rc
                ON tc.constraint_name = rc.constraint_name
            WHERE tc.table_name = 'video_detections'
                AND tc.constraint_type = 'FOREIGN KEY'
                AND rc.delete_rule = 'CASCADE';
        """)
        cascade_constraints = cursor.fetchall()
        
        print("\n🗑️  CASCADE Delete Rules:")
        print("-" * 80)
        if cascade_constraints:
            for constraint in cascade_constraints:
                print(f"  ✅ {constraint[0]} - DELETE CASCADE")
        else:
            print("  ⚠️  No CASCADE delete rules found")
        
        print("\n" + "=" * 80)
        print("✅ VERIFICATION COMPLETE")
        print("=" * 80)
        
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    verify_migration()
