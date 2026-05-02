#!/usr/bin/env python3
"""
Complete System Cleanup Script
===============================
WARNING: This script will DELETE ALL DATA and reset the system to initial state.

What it does:
1. Drops all database tables
2. Recreates all tables from scratch
3. Deletes all uploaded video files
4. Deletes all annotated video files
5. Deletes all unknown face images
6. Deletes all training images

Use this to start fresh with a clean system.
"""

import sys
import os
import shutil
import urllib.parse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from flask_api.config import config
from database.db_connection import DatabaseConnection


class SystemCleanup:
    """Complete system cleanup and reset"""
    
    def __init__(self):
        """Initialize cleanup"""
        self.db = None
        self.deleted_files_count = 0
        self.deleted_dirs_count = 0
        
    def confirm_cleanup(self) -> bool:
        """Ask user for confirmation before proceeding"""
        print("=" * 80)
        print("  COMPLETE SYSTEM CLEANUP")
        print("=" * 80)
        print("\nWARNING: This will DELETE ALL DATA including:")
        print("  - All database tables and data")
        print("  - All uploaded videos")
        print("  - All annotated videos")
        print("  - All unknown face images")
        print("  - All training images")
        print("  - All model versions")
        print("\nThis action CANNOT be undone!")
        print("=" * 80)
        
        response = input("\nType 'DELETE EVERYTHING' to confirm: ")
        return response == "DELETE EVERYTHING"
    
    def connect_database(self) -> bool:
        """Connect to database"""
        try:
            print("\n[Step 1] Connecting to database...")
            
            # Parse DATABASE_URL
            parsed = urllib.parse.urlparse(config.DATABASE_URL)
            
            self.db = DatabaseConnection(
                host=parsed.hostname or "localhost",
                port=parsed.port or 5432,
                database=(parsed.path or "/face_recognition").lstrip("/"),
                user=parsed.username or "admin",
                password=parsed.password or "admin",
            )
            
            print("  OK Database connected")
            return True
            
        except Exception as e:
            print(f"  ERROR: Failed to connect to database: {e}")
            return False
    
    def reset_database(self) -> bool:
        """Drop and recreate all database tables"""
        try:
            print("\n[Step 2] Resetting database...")
            
            # Read SQL script
            sql_file = os.path.join(os.path.dirname(__file__), 'reset_all.sql')
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_script = f.read()
            
            # Execute SQL script
            conn = self.db.get_connection()
            try:
                cursor = conn.cursor()
                
                print("  - Dropping all tables...")
                print("  - Recreating all tables...")
                print("  - Creating indexes...")
                
                cursor.execute(sql_script)
                conn.commit()
                
                print("  OK Database reset complete")
                
                # Verify tables
                cursor.execute("""
                    SELECT COUNT(*) FROM pg_tables 
                    WHERE schemaname = 'public'
                """)
                table_count = cursor.fetchone()[0]
                print(f"  OK Created {table_count} tables")
                
                cursor.close()
                return True
                
            except Exception as e:
                conn.rollback()
                print(f"  ERROR: Database reset failed: {e}")
                return False
            finally:
                self.db.return_connection(conn)
                
        except Exception as e:
            print(f"  ERROR: Failed to read SQL script: {e}")
            return False
    
    def delete_directory_contents(self, directory: str, description: str) -> bool:
        """Delete all contents of a directory"""
        try:
            if not os.path.exists(directory):
                print(f"  - {description}: Directory not found, skipping")
                return True
            
            # Count files before deletion
            file_count = sum(len(files) for _, _, files in os.walk(directory))
            
            if file_count == 0:
                print(f"  - {description}: Already empty")
                return True
            
            # Delete all contents
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                
                if os.path.isfile(item_path):
                    os.remove(item_path)
                    self.deleted_files_count += 1
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                    self.deleted_dirs_count += 1
            
            print(f"  - {description}: Deleted {file_count} files")
            return True
            
        except Exception as e:
            print(f"  ERROR: Failed to delete {description}: {e}")
            return False
    
    def cleanup_files(self) -> bool:
        """Delete all uploaded files and images"""
        try:
            print("\n[Step 3] Cleaning up files...")
            
            # Get base directory
            base_dir = os.path.join(os.path.dirname(__file__), '..', '..')
            
            # Define directories to clean
            directories = [
                (os.path.join(base_dir, 'video_uploads'), 'Video uploads'),
                (os.path.join(base_dir, 'unknown_face_images'), 'Unknown face images'),
                (os.path.join(base_dir, 'training_images'), 'Training images'),
                (os.path.join(base_dir, 'face_recognition_app', 'flask_api', 'video_uploads'), 'Flask API video uploads'),
                (os.path.join(base_dir, 'face_recognition_app', 'flask_api', 'video_uploads', 'annotated'), 'Annotated videos'),
            ]
            
            # Clean each directory
            for directory, description in directories:
                self.delete_directory_contents(directory, description)
            
            print(f"  OK Cleanup complete: {self.deleted_files_count} files, {self.deleted_dirs_count} directories")
            return True
            
        except Exception as e:
            print(f"  ERROR: File cleanup failed: {e}")
            return False
    
    def display_summary(self):
        """Display cleanup summary"""
        print("\n" + "=" * 80)
        print("  CLEANUP SUMMARY")
        print("=" * 80)
        print("\nOK System reset complete!")
        print(f"\n  Database:")
        print(f"    - All tables dropped and recreated")
        print(f"    - All data deleted")
        print(f"\n  Files:")
        print(f"    - Deleted {self.deleted_files_count} files")
        print(f"    - Deleted {self.deleted_dirs_count} directories")
        print("\n" + "=" * 80)
        print("\nNext steps:")
        print("  1. Train a new model:")
        print("     cd face_recognition_app/bulk_training_tool")
        print("     python bulk_train.py --training-data-dir ../../training_data/training_data")
        print("\n  2. Start Flask API:")
        print("     cd face_recognition_app/flask_api")
        print("     .\\start_app.bat")
        print("\n  3. Start Angular UI:")
        print("     cd face_recognition_app/angular_frontend")
        print("     npm start")
        print("\n" + "=" * 80 + "\n")
    
    def run(self) -> bool:
        """Execute complete cleanup"""
        try:
            # Step 0: Confirm
            if not self.confirm_cleanup():
                print("\nCleanup cancelled by user.")
                return False
            
            # Step 1: Connect to database
            if not self.connect_database():
                return False
            
            # Step 2: Reset database
            if not self.reset_database():
                return False
            
            # Step 3: Cleanup files
            if not self.cleanup_files():
                return False
            
            # Step 4: Display summary
            self.display_summary()
            
            return True
            
        except KeyboardInterrupt:
            print("\n\nCleanup interrupted by user.")
            return False
        except Exception as e:
            print(f"\nERROR: Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if self.db:
                self.db.close_all()


def main():
    """Main entry point"""
    cleanup = SystemCleanup()
    success = cleanup.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
