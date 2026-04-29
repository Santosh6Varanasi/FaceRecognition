"""
API Client Module
=================
Handles HTTP communication with Flask API endpoints with resilience and error handling.
"""

import time
import requests
from typing import Dict, Any, Optional, Callable
from functools import wraps


class APIClientError(Exception):
    """Exception raised for API client errors"""
    pass


class APIClient:
    """
    HTTP client for Flask API with retry logic and error handling.
    
    Endpoints:
        - POST /api/training/upload-image (multipart/form-data)
        - POST /api/training/label-image (JSON)
        - POST /api/training/retrain (JSON)
        - GET /api/training/retrain-status/<job_id>
    """
    
    # Timeout configurations (seconds)
    TIMEOUT_UPLOAD = 30
    TIMEOUT_LABEL = 30
    TIMEOUT_STATUS = 10
    TIMEOUT_HEALTH = 5
    
    # Retry configuration
    MAX_RETRY_ATTEMPTS = 3
    
    def __init__(self, base_url: str):
        """
        Initialize API client.
        
        Args:
            base_url: Flask API base URL (e.g., http://localhost:5001)
        """
        self.base_url = base_url.rstrip('/')  # Remove trailing slash
        self.session = requests.Session()
    
    def retry_with_backoff(self, func: Callable, max_attempts: int = MAX_RETRY_ATTEMPTS) -> Any:
        """
        Retry function with exponential backoff on network errors.
        
        Args:
            func: Function to retry
            max_attempts: Maximum number of retry attempts
            
        Returns:
            Function result
            
        Raises:
            APIClientError: If all retry attempts fail
        """
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                return func()
            
            except (requests.exceptions.ConnectionError, 
                    requests.exceptions.Timeout,
                    requests.exceptions.RequestException) as e:
                last_exception = e
                
                if attempt == max_attempts - 1:
                    # Last attempt failed
                    raise APIClientError(
                        f"Network error after {max_attempts} attempts: {str(e)}"
                    )
                
                # Exponential backoff: 2^attempt seconds
                wait_time = 2 ** attempt
                print(f"  Network error, retrying in {wait_time}s... (attempt {attempt + 1}/{max_attempts})")
                time.sleep(wait_time)
        
        # Should not reach here, but just in case
        raise APIClientError(f"Failed after {max_attempts} attempts: {str(last_exception)}")
    
    def check_api_availability(self) -> bool:
        """
        Check if Flask API is available and responding.
        
        Returns:
            True if API is available, False otherwise
        """
        try:
            # Try health endpoint first, fall back to root
            health_url = f"{self.base_url}/api/health"
            
            response = self.session.get(
                health_url,
                timeout=self.TIMEOUT_HEALTH
            )
            
            if response.status_code == 200:
                return True
            
            # Try root endpoint as fallback
            root_url = f"{self.base_url}/"
            response = self.session.get(
                root_url,
                timeout=self.TIMEOUT_HEALTH
            )
            
            # Accept any 2xx or 3xx status code
            return 200 <= response.status_code < 400
        
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.RequestException):
            return False
    
    def upload_image(self, image_path: str, person_name: str) -> Optional[str]:
        """
        Upload image to Flask API for validation and embedding generation.
        
        Args:
            image_path: Path to image file
            person_name: Name of person (for logging/tracking)
            
        Returns:
            image_id if successful, None if failed
            
        Raises:
            APIClientError: If all retry attempts fail
        """
        def _upload():
            url = f"{self.base_url}/api/training/upload-image"
            
            # Open and read image file
            with open(image_path, 'rb') as f:
                files = {'image': (image_path.split('/')[-1], f, 'image/jpeg')}
                
                response = self.session.post(
                    url,
                    files=files,
                    timeout=self.TIMEOUT_UPLOAD
                )
            
            # Handle response
            if response.status_code == 200:
                data = response.json()
                image_id = data.get('image_id')
                
                if not image_id:
                    raise APIClientError("No image_id in response")
                
                return image_id
            
            elif response.status_code == 400:
                # Validation error - don't retry
                error_msg = response.json().get('error', 'Validation failed')
                print(f"  ✗ Validation error: {error_msg}")
                return None
            
            elif response.status_code == 500:
                # Server error - don't retry
                error_msg = response.json().get('error', 'Server error')
                print(f"  ✗ Server error: {error_msg}")
                return None
            
            else:
                # Unexpected status code
                raise APIClientError(f"Unexpected status code: {response.status_code}")
        
        try:
            return self.retry_with_backoff(_upload)
        except APIClientError as e:
            print(f"  ✗ Upload failed after retries: {str(e)}")
            return None
    
    def label_image(self, image_id: str, person_name: str) -> bool:
        """
        Assign person name to validated image.
        
        Args:
            image_id: Image ID from upload response
            person_name: Name of person to assign
            
        Returns:
            True if successful, False if failed
            
        Raises:
            APIClientError: If all retry attempts fail
        """
        def _label():
            url = f"{self.base_url}/api/training/label-image"
            
            payload = {
                'image_id': image_id,
                'person_name': person_name
            }
            
            response = self.session.post(
                url,
                json=payload,
                timeout=self.TIMEOUT_LABEL
            )
            
            # Handle response
            if response.status_code == 200:
                return True
            
            elif response.status_code == 400:
                # Validation error - don't retry
                error_msg = response.json().get('error', 'Labeling validation failed')
                print(f"  ✗ Labeling error: {error_msg}")
                return False
            
            elif response.status_code == 500:
                # Server error - don't retry
                error_msg = response.json().get('error', 'Server error')
                print(f"  ✗ Server error: {error_msg}")
                return False
            
            else:
                # Unexpected status code
                raise APIClientError(f"Unexpected status code: {response.status_code}")
        
        try:
            return self.retry_with_backoff(_label)
        except APIClientError as e:
            print(f"  ✗ Labeling failed after retries: {str(e)}")
            return False
    
    def trigger_retrain(self) -> Optional[str]:
        """
        Trigger asynchronous model retraining job.
        
        Returns:
            job_id if successful, None if failed
            
        Raises:
            APIClientError: If request fails (fatal error)
        """
        def _retrain():
            url = f"{self.base_url}/api/training/retrain"
            
            response = self.session.post(
                url,
                json={},  # Empty body
                timeout=self.TIMEOUT_LABEL
            )
            
            # Handle response
            if response.status_code == 202:
                data = response.json()
                job_id = data.get('job_id')
                
                if not job_id:
                    raise APIClientError("No job_id in response")
                
                return job_id
            
            elif response.status_code == 400:
                # Validation error - insufficient data
                error_msg = response.json().get('error', 'Insufficient training data')
                raise APIClientError(f"Retraining validation failed: {error_msg}")
            
            elif response.status_code == 500:
                # Server error
                error_msg = response.json().get('error', 'Server error')
                raise APIClientError(f"Retraining server error: {error_msg}")
            
            else:
                # Unexpected status code
                raise APIClientError(f"Unexpected status code: {response.status_code}")
        
        # Retry on network errors, but propagate API errors
        return self.retry_with_backoff(_retrain)
    
    def poll_retrain_status(self, job_id: str, poll_interval: int = 2) -> Dict[str, Any]:
        """
        Poll retraining job status until completion.
        
        Args:
            job_id: Job ID from trigger_retrain
            poll_interval: Seconds between status checks (default: 2)
            
        Returns:
            Final job status dictionary with metrics
            
        Raises:
            APIClientError: If job fails or status endpoint returns error
        """
        print(f"\n  Polling job status (job_id: {job_id})...")
        
        while True:
            def _check_status():
                url = f"{self.base_url}/api/training/retrain-status/{job_id}"
                
                response = self.session.get(
                    url,
                    timeout=self.TIMEOUT_STATUS
                )
                
                # Handle response
                if response.status_code == 200:
                    return response.json()
                
                elif response.status_code == 404:
                    raise APIClientError(f"Job not found: {job_id}")
                
                else:
                    raise APIClientError(f"Unexpected status code: {response.status_code}")
            
            try:
                status_data = self.retry_with_backoff(_check_status)
            except APIClientError as e:
                # Timeout during polling - retry
                if "Network error" in str(e):
                    print(f"  Network timeout, retrying...")
                    time.sleep(poll_interval)
                    continue
                else:
                    # Fatal error
                    raise
            
            status = status_data.get('status', 'unknown')
            progress = status_data.get('progress_pct', 0)
            message = status_data.get('message', '')
            
            # Display progress
            if status in ('queued', 'in_progress'):
                print(f"  [{progress}%] {message or status.capitalize()}")
                time.sleep(poll_interval)
                continue
            
            elif status == 'completed':
                print(f"  ✓ Training completed successfully!")
                return status_data
            
            elif status == 'failed':
                error_msg = message or 'Training failed'
                raise APIClientError(f"Training job failed: {error_msg}")
            
            else:
                raise APIClientError(f"Unknown job status: {status}")
    
    def close(self):
        """Close the HTTP session"""
        self.session.close()
