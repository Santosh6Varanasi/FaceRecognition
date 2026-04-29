#!/usr/bin/env python3
"""
API-Based Training Script
=========================
Orchestrates face recognition model training through Flask API endpoints.
Supports model and database migration for cross-environment deployment.

Usage:
    python api_training_script.py --training-data-dir path/to/data
    python api_training_script.py --export-model
    python api_training_script.py --import-model path/to/export.zip
"""

import sys
import os
import click
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.logger import init_logger, get_logger
from utils.validators import validate_url, validate_path
from modules.api_client import APIClient
from modules.data_discovery import DataDiscovery
from modules.training_orchestrator import TrainingOrchestrator
from modules.migration_manager import MigrationManager, MigrationError

# Load environment variables from .env file
load_dotenv()

# Default configuration
DEFAULT_TRAINING_DATA_DIR = "training_data/training_data"
DEFAULT_FLASK_API_URL = "http://localhost:5001"


@click.command()
@click.option(
    '--training-data-dir',
    default=DEFAULT_TRAINING_DATA_DIR,
    help='Path to training data directory (default: training_data/training_data)'
)
@click.option(
    '--verbose',
    is_flag=True,
    help='Enable verbose logging'
)
@click.option(
    '--export-model',
    is_flag=True,
    help='Export trained model after training (coming in Task 6)'
)
@click.option(
    '--export-database',
    is_flag=True,
    help='Export database training data (coming in Task 6)'
)
@click.option(
    '--create-migration-package',
    is_flag=True,
    help='Create complete migration package (coming in Task 6)'
)
@click.option(
    '--import-model',
    type=click.Path(exists=True),
    help='Import model from export package (coming in Task 7)'
)
@click.option(
    '--import-database',
    type=click.Path(exists=True),
    help='Import database from export file (coming in Task 7)'
)
def main(training_data_dir, verbose, export_model, export_database, 
         create_migration_package, import_model, import_database):
    """
    API-Based Training Script
    
    Train face recognition model by uploading images through Flask API endpoints.
    Supports model and database migration for cross-environment deployment.
    """
    # Initialize logger
    logger = init_logger(verbose=verbose)
    
    # Get Flask API URL from environment
    flask_api_url = os.getenv('FLASK_API_URL', DEFAULT_FLASK_API_URL)
    
    # Validate API URL
    is_valid, error_msg = validate_url(flask_api_url)
    if not is_valid:
        logger.error(f"Invalid FLASK_API_URL: {error_msg}")
        logger.info(f"Please set FLASK_API_URL environment variable or use default: {DEFAULT_FLASK_API_URL}")
        sys.exit(1)
    
    logger.info(f"Flask API URL: {flask_api_url}")
    
    # Initialize migration manager
    migration_manager = MigrationManager()
    
    # Handle import operations (Task 7)
    if import_model:
        try:
            logger.info("\n" + "=" * 80)
            logger.info("  IMPORTING MODEL")
            logger.info("=" * 80)
            
            result = migration_manager.import_model(import_model)
            
            if result["success"]:
                logger.success("Model imported successfully!")
                logger.info("\nNext steps:")
                logger.info("  1. Restart Flask API to load the new model")
                logger.info("  2. Test face recognition with your images/videos")
            
            sys.exit(0)
        
        except MigrationError as e:
            logger.error(f"Model import failed: {str(e)}")
            sys.exit(1)
    
    if import_database:
        try:
            logger.info("\n" + "=" * 80)
            logger.info("  IMPORTING DATABASE")
            logger.info("=" * 80)
            
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                logger.error("DATABASE_URL environment variable not set")
                logger.info("Please set DATABASE_URL to import database")
                sys.exit(1)
            
            result = migration_manager.import_database(import_database, database_url)
            
            if result["success"]:
                logger.success("Database imported successfully!")
            
            sys.exit(0)
        
        except MigrationError as e:
            logger.error(f"Database import failed: {str(e)}")
            sys.exit(1)
    
    # Validate training data directory
    is_valid, error_msg = validate_path(training_data_dir, must_exist=True, must_be_dir=True)
    if not is_valid:
        logger.error(f"Invalid training data directory: {error_msg}")
        sys.exit(1)
    
    # Initialize components
    api_client = APIClient(base_url=flask_api_url)
    data_discovery = DataDiscovery()
    orchestrator = TrainingOrchestrator(api_client, data_discovery)
    
    try:
        # Run training workflow
        success = orchestrator.run_training(training_data_dir)
        
        if not success:
            logger.error("Training failed")
            sys.exit(1)
        
        # Get training metadata for export
        training_metadata = None
        
        # Handle export operations
        model_export_path = None
        database_export_path = None
        
        if export_model:
            try:
                logger.info("\n" + "=" * 80)
                logger.info("  EXPORTING MODEL")
                logger.info("=" * 80)
                model_export_path = migration_manager.export_model(training_metadata)
            except MigrationError as e:
                logger.error(f"Model export failed: {str(e)}")
                sys.exit(1)
        
        if export_database:
            try:
                logger.info("\n" + "=" * 80)
                logger.info("  EXPORTING DATABASE")
                logger.info("=" * 80)
                
                database_url = os.getenv('DATABASE_URL')
                if not database_url:
                    logger.error("DATABASE_URL environment variable not set")
                    logger.info("Please set DATABASE_URL to export database")
                    sys.exit(1)
                
                database_export_path = migration_manager.export_database(database_url)
            except MigrationError as e:
                logger.error(f"Database export failed: {str(e)}")
                sys.exit(1)
        
        if create_migration_package:
            try:
                logger.info("\n" + "=" * 80)
                logger.info("  CREATING MIGRATION PACKAGE")
                logger.info("=" * 80)
                
                # Export model if not already done
                if not model_export_path:
                    model_export_path = migration_manager.export_model(training_metadata)
                
                # Export database if not already done
                if not database_export_path:
                    database_url = os.getenv('DATABASE_URL')
                    if database_url:
                        database_export_path = migration_manager.export_database(database_url)
                    else:
                        logger.warning("DATABASE_URL not set, creating package without database export")
                
                package_path = migration_manager.create_migration_package(
                    model_export_path,
                    database_export_path
                )
            except MigrationError as e:
                logger.error(f"Migration package creation failed: {str(e)}")
                sys.exit(1)
        
        logger.success("Training completed successfully!")
        sys.exit(0)
    
    except KeyboardInterrupt:
        logger.warning("\nTraining interrupted by user")
        sys.exit(1)
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    
    finally:
        # Clean up
        api_client.close()


if __name__ == "__main__":
    main()

