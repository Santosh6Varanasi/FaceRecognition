"""
Training Orchestrator Module
============================
Coordinates the end-to-end training workflow from data discovery through model retraining.
"""

import time
from typing import Dict, List, Tuple
from datetime import datetime

from modules.api_client import APIClient, APIClientError
from modules.data_discovery import DataDiscovery, DataDiscoveryError


class TrainingOrchestrator:
    """
    Orchestrates the complete training workflow:
    1. Validate API availability
    2. Discover training data
    3. Upload images
    4. Label images
    5. Trigger retraining
    6. Poll status until completion
    7. Display summary
    """
    
    def __init__(self, api_client: APIClient, data_discovery: DataDiscovery):
        """
        Initialize orchestrator with dependencies.
        
        Args:
            api_client: Configured API client instance
            data_discovery: Data discovery instance
        """
        self.api_client = api_client
        self.data_discovery = data_discovery
        
        # State tracking
        self.person_images: Dict[str, List[str]] = {}
        self.image_to_id: Dict[str, str] = {}  # image_path → image_id
        self.upload_results: Dict[str, bool] = {}  # image_path → success
        self.label_results: Dict[str, bool] = {}  # image_id → success
        self.failed_images: List[Tuple[str, str, str]] = []  # (person, image, reason)
        
        # Metrics
        self.total_images = 0
        self.successful_uploads = 0
        self.successful_labels = 0
        self.start_time = None
        self.end_time = None

    def run_training(self, training_data_dir: str) -> bool:
        """
        Execute the complete training workflow.
        
        Args:
            training_data_dir: Path to training data directory
            
        Returns:
            True if training completed successfully, False otherwise
        """
        self.start_time = datetime.now()
        
        try:
            # Step 1: Check API availability
            print("\n" + "=" * 80)
            print("  API-BASED MODEL TRAINING")
            print("=" * 80)
            
            print("\n[Step 1] Checking API availability...")
            if not self.api_client.check_api_availability():
                print("✗ ERROR: Flask API is not available")
                print(f"  Please ensure the API is running at: {self.api_client.base_url}")
                return False
            print("✓ API is available")
            
            # Step 2: Discover training data
            print("\n[Step 2] Discovering training data...")
            try:
                self.person_images = self.data_discovery.discover_training_data(training_data_dir)
            except DataDiscoveryError as e:
                print(f"✗ ERROR: {str(e)}")
                return False
            
            num_persons, self.total_images = self.data_discovery.get_discovery_summary(self.person_images)
            print(f"✓ Found {num_persons} persons with {self.total_images} total images")
            
            for person_name, images in self.person_images.items():
                print(f"  - {person_name}: {len(images)} images")
            
            # Step 3: Validate minimum requirements
            print("\n[Step 3] Validating minimum requirements...")
            is_valid, error_msg = self.data_discovery.validate_minimum_requirements(
                self.person_images,
                min_persons=2,
                min_images_per_person=2
            )
            
            if not is_valid:
                print(f"✗ ERROR: {error_msg}")
                return False
            print("✓ Minimum requirements met")
            
            # Step 4: Upload all images
            print("\n[Step 4] Uploading images...")
            self._upload_all_images()
            
            if self.successful_uploads == 0:
                print("✗ ERROR: No images were successfully uploaded")
                return False
            
            print(f"✓ Successfully uploaded {self.successful_uploads}/{self.total_images} images")
            
            # Step 5: Label all successfully uploaded images
            print("\n[Step 5] Labeling images...")
            self._label_all_images()
            
            if self.successful_labels == 0:
                print("✗ ERROR: No images were successfully labeled")
                return False
            
            print(f"✓ Successfully labeled {self.successful_labels}/{self.successful_uploads} images")
            
            # Step 6: Trigger retraining
            print("\n[Step 6] Triggering model retraining...")
            try:
                job_id = self.api_client.trigger_retrain()
                if not job_id:
                    print("✗ ERROR: Failed to trigger retraining")
                    return False
                print(f"✓ Retraining job started (job_id: {job_id})")
            except APIClientError as e:
                print(f"✗ ERROR: {str(e)}")
                return False
            
            # Step 7: Poll status until completion
            print("\n[Step 7] Waiting for training to complete...")
            try:
                final_status = self.api_client.poll_retrain_status(job_id)
            except APIClientError as e:
                print(f"✗ ERROR: {str(e)}")
                return False
            
            # Step 8: Display summary
            self.end_time = datetime.now()
            self._display_summary(final_status)
            
            return True
        
        except Exception as e:
            print(f"\n✗ ERROR: Unexpected error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _upload_all_images(self):
        """Upload all discovered images through API"""
        image_count = 0
        
        for person_name, images in self.person_images.items():
            print(f"\n  Processing {person_name}...")
            
            for image_path in images:
                image_count += 1
                image_filename = image_path.split('/')[-1].split('\\')[-1]
                
                print(f"  [{image_count}/{self.total_images}] Uploading {image_filename}...", end=' ')
                
                try:
                    image_id = self.api_client.upload_image(image_path, person_name)
                    
                    if image_id:
                        self.image_to_id[image_path] = image_id
                        self.upload_results[image_path] = True
                        self.successful_uploads += 1
                        print("✓")
                    else:
                        self.upload_results[image_path] = False
                        self.failed_images.append((person_name, image_filename, "Upload failed"))
                        print("✗")
                
                except Exception as e:
                    self.upload_results[image_path] = False
                    self.failed_images.append((person_name, image_filename, str(e)))
                    print(f"✗ {str(e)}")
    
    def _label_all_images(self):
        """Label all successfully uploaded images"""
        label_count = 0
        total_to_label = len(self.image_to_id)
        
        for person_name, images in self.person_images.items():
            for image_path in images:
                # Skip if upload failed
                if image_path not in self.image_to_id:
                    continue
                
                label_count += 1
                image_id = self.image_to_id[image_path]
                image_filename = image_path.split('/')[-1].split('\\')[-1]
                
                print(f"  [{label_count}/{total_to_label}] Labeling {image_filename} as {person_name}...", end=' ')
                
                try:
                    success = self.api_client.label_image(image_id, person_name)
                    
                    if success:
                        self.label_results[image_id] = True
                        self.successful_labels += 1
                        print("✓")
                    else:
                        self.label_results[image_id] = False
                        self.failed_images.append((person_name, image_filename, "Labeling failed"))
                        print("✗")
                
                except Exception as e:
                    self.label_results[image_id] = False
                    self.failed_images.append((person_name, image_filename, str(e)))
                    print(f"✗ {str(e)}")

    def _display_summary(self, final_status: Dict):
        """
        Display comprehensive training summary.
        
        Args:
            final_status: Final job status from API
        """
        print("\n" + "=" * 80)
        print("  TRAINING SUMMARY")
        print("=" * 80)
        
        # Execution time
        if self.start_time and self.end_time:
            duration = self.end_time - self.start_time
            minutes = int(duration.total_seconds() // 60)
            seconds = int(duration.total_seconds() % 60)
            print(f"\n✓ Training completed successfully!")
            print(f"  Execution time: {minutes}m {seconds}s")
        
        # Image processing stats
        print(f"\n  Image Processing:")
        print(f"    - Total images processed: {self.total_images}")
        print(f"    - Successful uploads: {self.successful_uploads}")
        print(f"    - Successful labels: {self.successful_labels}")
        print(f"    - Failed images: {len(self.failed_images)}")
        
        # Persons trained
        print(f"\n  Persons Trained: {len(self.person_images)}")
        for person_name, images in self.person_images.items():
            successful_count = sum(
                1 for img in images 
                if img in self.image_to_id and self.image_to_id[img] in self.label_results and self.label_results[self.image_to_id[img]]
            )
            print(f"    - {person_name}: {successful_count}/{len(images)} images")
        
        # Model metrics
        print(f"\n  Model Metrics:")
        cv_accuracy = final_status.get('cv_accuracy')
        num_classes = final_status.get('num_classes')
        version_number = final_status.get('version_number')
        
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
        print("  1. The new model is now active in the Flask API")
        print("  2. Test face recognition with your images/videos")
        print("  3. Use --export-model to create a migration package")
