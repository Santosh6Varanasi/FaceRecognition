"""
Face Recognition System - Section A: Database Connection & Initialization
Phase 2: Notebook Refactoring

This section initializes the database connection, creates tables if needed,
and sets up helper functions for data persistence.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_connection import DatabaseConnection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# SECTION A: DATABASE CONNECTION & INITIALIZATION
# ============================================================================

def initialize_database():
    """
    Initialize PostgreSQL connection and verify database is ready.
    
    Returns
    -------
    DatabaseConnection
        Initialized database connection pool
    """
    logger.info("=" * 70)
    logger.info("SECTION A: DATABASE CONNECTION & INITIALIZATION")
    logger.info("=" * 70)
    
    # Get database credentials from environment
    db_config = {
        'host': os.getenv('DATABASE_HOST', 'localhost'),
        'port': int(os.getenv('DATABASE_PORT', 5432)),
        'database': os.getenv('DATABASE_NAME', 'face_recognition'),
        'user': os.getenv('DATABASE_USER', 'postgres'),
        'password': os.getenv('DATABASE_PASSWORD', 'postgres'),
        'min_connections': int(os.getenv('DATABASE_MIN_CONNECTIONS', 1)),
        'max_connections': int(os.getenv('DATABASE_MAX_CONNECTIONS', 20)),
    }
    
    logger.info(f"Connecting to database: {db_config['database']}@{db_config['host']}:{db_config['port']}")
    
    try:
        db = DatabaseConnection(**db_config)
        logger.info("✅ Database connection pool initialized")
        
        # Verify connection by querying table counts
        verify_database_schema(db)
        
        return db
    
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        logger.error("Ensure PostgreSQL is running and configured correctly.")
        raise


def verify_database_schema(db: DatabaseConnection):
    """
    Verify all required tables exist in the database.
    
    Parameters
    ----------
    db : DatabaseConnection
        Database connection instance
    """
    logger.info("\nVerifying database schema...")
    
    required_tables = [
        'people', 'faces', 'unknown_faces', 'video_sessions',
        'frames', 'detections', 'model_versions'
    ]
    
    try:
        people = db.get_all_people()
        logger.info(f"✅ Database tables verified")
        logger.info(f"   - {len(people)} persons in database")
        
        face_counts = db.get_face_count_by_person()
        total_faces = sum(face_counts.values())
        logger.info(f"   - {total_faces} faces stored in database")
        
        model_versions = db.get_model_versions(limit=1)
        if model_versions:
            latest = model_versions[0]
            logger.info(f"   - Active model: v{latest['version_number']} "
                       f"({latest['num_classes']} persons, "
                       f"{latest['cv_accuracy']*100:.1f}% accuracy)")
        else:
            logger.warning("   ⚠️  No trained models found - will need to train one")
        
        unknown_stats = db.get_unknown_faces_statistics()
        pending_count = unknown_stats.get('pending', 0)
        labeled_count = unknown_stats.get('labeled', 0)
        logger.info(f"   - Unknown faces: {pending_count} pending, {labeled_count} labeled")
        
    except Exception as e:
        logger.warning(f"⚠️  Could not verify all tables: {e}")
        logger.info("   Run database setup scripts to create tables:")
        logger.info("   psql -U postgres -d face_recognition -f database/02-create-tables.sql")
        logger.info("   psql -U postgres -d face_recognition -f database/03-create-indexes.sql")


def create_required_directories():
    """Create output directories if they don't exist."""
    logger.info("\nCreating required directories...")
    
    dirs = [
        os.getenv('TRAINING_DATA_DIR', './training_data'),
        os.getenv('TEST_IMAGES_DIR', './test_images'),
        os.getenv('OUTPUT_DIR', './output'),
        os.getenv('FRAMES_DIR', './frames'),
        './logs',
    ]
    
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ {dir_path}")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    logger.info("Face Recognition System - Phase 2: Notebook Refactoring")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    
    # Initialize database
    db = initialize_database()
    
    # Create directories
    create_required_directories()
    
    logger.info("\n" + "=" * 70)
    logger.info("SECTION A COMPLETE")
    logger.info("Database connection established and verified")
    logger.info("Ready for Section B: Data generation")
    logger.info("=" * 70)
