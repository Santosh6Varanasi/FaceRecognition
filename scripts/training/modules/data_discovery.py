"""
Data Discovery Module
=====================
Scans local file system to discover training data organized by person.
"""

import os
from typing import Dict, List, Tuple
from pathlib import Path


class DataDiscoveryError(Exception):
    """Exception raised for data discovery errors"""
    pass


class DataDiscovery:
    """
    Discovers training images organized in person subfolders.
    
    Expected directory structure:
        training_data/
        ├── person_1/
        │   ├── image1.jpg
        │   ├── image2.png
        │   └── image3.jpeg
        ├── person_2/
        │   ├── photo1.jpg
        │   └── photo2.bmp
        └── person_3/
            └── face.webp
    """
    
    # Supported image extensions (case-insensitive)
    VALID_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
    
    def __init__(self):
        """Initialize DataDiscovery"""
        pass
    
    def discover_training_data(self, training_data_dir: str) -> Dict[str, List[str]]:
        """
        Scan directory for person subfolders and discover training images.
        
        Args:
            training_data_dir: Path to training data directory
            
        Returns:
            Dictionary mapping person_name → [image_paths]
            
        Raises:
            DataDiscoveryError: If no person folders found or directory doesn't exist
        """
        # Validate directory exists
        if not os.path.exists(training_data_dir):
            raise DataDiscoveryError(
                f"Training data directory not found: {training_data_dir}\n"
                f"Please create the directory with person subfolders."
            )
        
        if not os.path.isdir(training_data_dir):
            raise DataDiscoveryError(
                f"Path is not a directory: {training_data_dir}"
            )
        
        # Scan for person subdirectories
        person_dirs = self._get_person_directories(training_data_dir)
        
        if len(person_dirs) == 0:
            raise DataDiscoveryError(
                f"No person directories found in {training_data_dir}\n"
                f"Please create subdirectories for each person with their photos."
            )
        
        # Build mapping: person_name → [image_paths]
        person_images: Dict[str, List[str]] = {}
        
        for person_name in person_dirs:
            person_path = os.path.join(training_data_dir, person_name)
            images = self._get_image_files(person_path)
            
            if len(images) == 0:
                # Warn but don't fail - skip this person
                print(f"⚠ WARNING: No images found for {person_name}, skipping")
                continue
            
            person_images[person_name] = images
        
        # Final validation - ensure we have at least one person with images
        if len(person_images) == 0:
            raise DataDiscoveryError(
                f"No valid training images found in any person directory.\n"
                f"Supported formats: {', '.join(self.VALID_EXTENSIONS)}"
            )
        
        return person_images
    
    def _get_person_directories(self, training_data_dir: str) -> List[str]:
        """
        Get list of person subdirectories (immediate children only).
        
        Args:
            training_data_dir: Path to training data directory
            
        Returns:
            List of person directory names
        """
        person_dirs = []
        
        try:
            for item in os.listdir(training_data_dir):
                item_path = os.path.join(training_data_dir, item)
                
                # Only include directories (not files)
                if os.path.isdir(item_path):
                    # Skip hidden directories (starting with .)
                    if not item.startswith('.'):
                        person_dirs.append(item)
        
        except PermissionError as e:
            raise DataDiscoveryError(f"Permission denied accessing directory: {e}")
        
        return sorted(person_dirs)
    
    def _get_image_files(self, person_dir: str) -> List[str]:
        """
        Get list of valid image files in person directory.
        
        Args:
            person_dir: Path to person's image directory
            
        Returns:
            List of absolute paths to image files
        """
        image_files = []
        
        try:
            for item in os.listdir(person_dir):
                item_path = os.path.join(person_dir, item)
                
                # Only include files (not subdirectories)
                if os.path.isfile(item_path):
                    # Check if extension is valid (case-insensitive)
                    ext = Path(item).suffix.lower()
                    if ext in self.VALID_EXTENSIONS:
                        image_files.append(item_path)
        
        except PermissionError as e:
            raise DataDiscoveryError(f"Permission denied accessing directory: {e}")
        
        return sorted(image_files)
    
    def get_discovery_summary(self, person_images: Dict[str, List[str]]) -> Tuple[int, int]:
        """
        Get summary statistics from discovery results.
        
        Args:
            person_images: Dictionary mapping person_name → [image_paths]
            
        Returns:
            Tuple of (num_persons, total_images)
        """
        num_persons = len(person_images)
        total_images = sum(len(images) for images in person_images.values())
        
        return num_persons, total_images
    
    def validate_minimum_requirements(
        self, 
        person_images: Dict[str, List[str]], 
        min_persons: int = 2, 
        min_images_per_person: int = 2
    ) -> Tuple[bool, str]:
        """
        Validate that training data meets minimum requirements.
        
        Args:
            person_images: Dictionary mapping person_name → [image_paths]
            min_persons: Minimum number of persons required
            min_images_per_person: Minimum images per person required
            
        Returns:
            Tuple of (is_valid, error_message)
            - (True, "") if valid
            - (False, error_message) if invalid
        """
        num_persons = len(person_images)
        
        # Check minimum persons
        if num_persons < min_persons:
            return False, (
                f"At least {min_persons} people required for training. "
                f"Found only {num_persons}."
            )
        
        # Check minimum images per person
        for person_name, images in person_images.items():
            if len(images) < min_images_per_person:
                return False, (
                    f"Each person must have at least {min_images_per_person} images. "
                    f"{person_name} has only {len(images)}."
                )
        
        return True, ""
