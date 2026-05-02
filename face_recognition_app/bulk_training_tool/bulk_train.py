#!/usr/bin/env python3
"""
Bulk Training Tool
==================
Direct training from training_data folder using Flask API modules.
No HTTP calls - imports modules directly for better performance and reliability.

Usage:
    python bulk_train.py --training-data-dir ../../training_data/training_data
    python bulk_train.py --training-data-dir ../../training_data/training_data --verbose
"""

import sys
import os
import time
import click
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import Flask API modules directly
from flask_api.db import queries
from flask_api.services.image_validator import ImageValidator
from flask_api.services.model_retrainer import ModelRetrainerService
from flask_api.config import config

# Import local utilities
from utils.logger import init_logger, get_logger
from utils.validators import validate_path
from modules.data_discovery import DataDiscovery


class BulkTrainingTool:
    """
    Bulk training tool that directly uses Flask API modules.
    
    Workflow:
    1. Discover training data from folder
    2. Validate and process images using ImageValidator
    3. Store faces in database
    4. Trigger model retraining using ModelRetrainer
    5. Display results
    """
    
    def __init__(self, verbose: bool = False):
        """
        Initialize bulk training tool.
        
        Args:
            verbose: Enable verbose logging
        """
        self.logger = get_logger(__name__)
        self.verbose = verbose
        
        # Initialize components
        self.data_discovery = DataDiscovery()
        self.db = None
        
        # State tracking
        self.person_images: Dict[str, List[str]] = {}
        self.successful_images = 0
        self.failed_images: List[Tuple[str, str, str]] = []  # (person, image, reason)
        self.start_time = None
        self.end_time = None
    
    def run(self, training_data_dir: str) -> bool:
        """
        Execute bulk training workflow.
        
        Args:
            training_data_dir: Path to training data directory
            
        Returns:
            True if successful, False otherwise
        """
        self.start_time = datetime.now()
        
        try:
            self._print_header("BULK TRAINING TOOL")
            self.logger.info(f"Training data directory: {training_data_dir}")
            
            # Step 1: Initialize database connection
            self._print_step(1, "Initializing database connection")
            self.db = queries.get_db_connection()
            self.logger.info("✓ Database connected")
            
            # Step 2: Discover training data
            self._print_step(2, "Discovering training data")
            try:
                self.person_images = self.data_discovery.discover_training_data(training_data_dir)
            except Exception as e:
                self.logger.error(f"✗ Data discovery failed: {str(e)}")
                return False
            
            num_persons, total_images = self.data_discovery.get_discovery_summary(self.person_images)
            self.logger.info(f"✓ Found {num_persons} persons with {total_images} total images")
            
            for person_name, images in self.person_images.items():
                self.logger.info(f"  - {person_name}: {len(images)} images")
            
            # Step 3: Validate minimum requirements
            self._print_step(3, "Validating minimum requirements")
            is_valid, error_msg = self.data_discovery.validate_minimum_requirements(
                self.person_images,
                min_persons=2,
                min_images_per_person=2
            )
            
            if not is_valid:
                self.logger.error(f"✗ {error_msg}")
                return False
            self.logger.info("✓ Minimum requirements met")
            
            # Step 4: Process all images
            self._print_step(4, "Processing and storing images")
            self._process_all_images()
            
            if self.successful_images == 0:
                self.logger.error("✗ No images were successfully processed")
                return False
            
            self.logger.info(f"✓ Successfully processed {self.successful_images}/{total_images} images")
            
            # Step 5: Trigger model retraining
            self._print_step(5, "Training model")
            try:
                model_metrics = self._train_model()
                self.logger.info("✓ Model training completed")
            except Exception as e:
                self.logger.error(f"✗ Model training failed: {str(e)}")
                return False
            
            # Step 6: Display summary
            self.end_time = datetime.now()
            self._display_summary(model_metrics)
            
            return True
            
        except Exception as e:
            self.logger.error(f"✗ Unexpected error: {str(e)}")
            if self.verbose:
                import traceback
                traceback.print_exc()
            return False
    
    def _process_all_images(self):
        """Process all discovered images and store in database"""
        import cv2
        from deepface import DeepFace
        from sklearn.preprocessing import normalize
        import numpy as np
        
        image_validator = ImageValidator()
        image_count = 0
        total_images = sum(len(images) for images in self.person_images.values())
        
        for person_name, images in self.person_images.items():
            self.logger.info(f"\n  Processing {person_name}...")
            
            # Ensure person exists in database
            person_id = queries.upsert_person(self.db, person_name)
            
            for image_path in images:
                image_count += 1
                image_filename = os.path.basename(image_path)
                
                if self.verbose:
                    self.logger.info(f"  [{image_count}/{total_images}] Processing {image_filename}...")
                else:
                    print(f"  [{image_count}/{total_images}] Processing {image_filename}...", end=' ', flush=True)
                
                try:
                    # Read image
                    frame_bgr = cv2.imread(image_path)
                    if frame_bgr is None:
                        raise Exception("Failed to read image")
                    
                    # Validate single face - this raises ValueError if validation fails
                    validation_result = image_validator.validate_single_face(frame_bgr)
                    
                    # Extract embedding from validation result
                    embedding_norm = validation_result['embedding']
                    
                    # Store in database with the actual image path
                    queries.insert_face_from_unknown(
                        self.db,
                        person_id=person_id,
                        embedding=embedding_norm,
                        source_type="training",
                        image_path=image_path
                    )
                    
                    self.successful_images += 1
                    if not self.verbose:
                        print("OK")
                
                except ValueError as e:
                    # Validation error (no face, multiple faces, etc.)
                    error_msg = str(e)
                    self.failed_images.append((person_name, image_filename, error_msg))
                    if not self.verbose:
                        print(f"X {error_msg}")
                    else:
                        self.logger.warning(f"  X {error_msg}")
                
                except Exception as e:
                    # Other errors
                    error_msg = str(e)
                    self.failed_images.append((person_name, image_filename, error_msg))
                    if not self.verbose:
                        print(f"X {error_msg}")
                    else:
                        self.logger.error(f"  X {error_msg}")
    
    def _train_model(self) -> Dict:
        """Train model using ModelRetrainerService"""
        self.logger.info("\n  Initializing model retrainer...")
        
        retrainer = ModelRetrainerService(self.db)
        
        self.logger.info("  Loading training data from database...")
        self.logger.info("  Training SVM classifier...")
        self.logger.info("  Evaluating model with cross-validation...")
        self.logger.info("  Saving model to database...")
        
        # Create a job ID for tracking
        import uuid
        job_id = str(uuid.uuid4())
        
        # Train the model directly (synchronous)
        result = retrainer.train_model(job_id)
        
        return result
    
    def _display_summary(self, model_metrics: Dict):
        """Display comprehensive training summary"""
        print("\n" + "=" * 80)
        print("  TRAINING SUMMARY")
        print("=" * 80)
        
        # Execution time
        if self.start_time and self.end_time:
            duration = self.end_time - self.start_time
            minutes = int(duration.total_seconds() // 60)
            seconds = int(duration.total_seconds() % 60)
            print(f"OK Training completed successfully!")
            print(f"  Execution time: {minutes}m {seconds}s")
        
        # Image processing stats
        total_images = sum(len(images) for images in self.person_images.values())
        print(f"\n  Image Processing:")
        print(f"    - Total images: {total_images}")
        print(f"    - Successful: {self.successful_images}")
        print(f"    - Failed: {len(self.failed_images)}")
        
        # Persons trained
        print(f"\n  Persons Trained: {len(self.person_images)}")
        for person_name, images in self.person_images.items():
            successful_count = len(images) - sum(
                1 for p, _, _ in self.failed_images if p == person_name
            )
            print(f"    - {person_name}: {successful_count}/{len(images)} images")
        
        # Model metrics
        print(f"\n  Model Metrics:")
        cv_accuracy = model_metrics.get('cv_accuracy')
        num_classes = model_metrics.get('num_classes')
        version_number = model_metrics.get('version_number')
        
        if cv_accuracy is not None:
            print(f"    - Cross-Validation Accuracy: {cv_accuracy:.2%}")
        if num_classes is not None:
            print(f"    - Number of Classes: {num_classes}")
        if version_number is not None:
            print(f"    - Model Version: v{version_number}")
        
        # Failed images (show first 10)
        if self.failed_images:
            print(f"\n  ⚠ Failed Images ({len(self.failed_images)}):")
            for person, image, reason in self.failed_images[:10]:
                print(f"    - {person}/{image}: {reason}")
            if len(self.failed_images) > 10:
                print(f"    ... and {len(self.failed_images) - 10} more")
        
        print("\n" + "=" * 80)
        print("\nNext steps:")
        print("  1. The new model is now active")
        print("  2. Test with webcam: python_realtime_face_recognition/main.py")
        print("  3. Test with videos via Web UI")
        print("=" * 80 + "\n")
    
    def _print_header(self, text: str):
        """Print formatted header"""
        print("\n" + "=" * 80)
        print(f"  {text}")
        print("=" * 80)
    
    def _print_step(self, step_num: int, text: str):
        """Print formatted step"""
        print(f"\n[Step {step_num}] {text}")


@click.command()
@click.option(
    '--training-data-dir',
    default='../../training_data/training_data',
    help='Path to training data directory'
)
@click.option(
    '--verbose',
    is_flag=True,
    help='Enable verbose logging'
)
def main(training_data_dir, verbose):
    """
    Bulk Training Tool - Train model from training_data folder.
    
    This tool directly imports Flask API modules for better performance
    and reliability compared to HTTP API calls.
    """
    # Initialize logger
    init_logger(verbose=verbose)
    logger = get_logger(__name__)
    
    # Validate training data directory
    is_valid, error_msg = validate_path(training_data_dir, must_exist=True, must_be_dir=True)
    if not is_valid:
        logger.error(f"Invalid training data directory: {error_msg}")
        sys.exit(1)
    
    # Run bulk training
    tool = BulkTrainingTool(verbose=verbose)
    success = tool.run(training_data_dir)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
