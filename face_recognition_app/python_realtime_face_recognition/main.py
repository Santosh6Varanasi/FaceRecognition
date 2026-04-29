"""
Face Recognition Application - Main Entry Point

This is the main entry point for the Python real-time face recognition application.
It integrates with the existing Flask API backend for face detection and recognition.
"""

import sys
import logging
import time
from datetime import datetime
from typing import Optional

from src.config import AppConfig, load_config
from src.camera_handler import CameraHandler
from src.api_client import APIClient
from src.display_renderer import DisplayRenderer
from src.models import VideoSession

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


class FaceRecognitionApp:
    """
    Main application controller for the Python real-time face recognition system.
    
    This class orchestrates all components (camera, API client, display) and manages
    the application lifecycle. It initializes components in the correct order with
    proper error handling and logging.
    
    Attributes:
        config: Application configuration
        camera: Camera handler for frame capture
        api_client: API client for Flask backend communication
        display: Display renderer for visualization
        session: Current video session information
    """
    
    def __init__(self, config: AppConfig):
        """
        Initialize the FaceRecognitionApp with all required components.
        
        Initializes components in the following order:
        1. Display renderer (lightweight, no external dependencies)
        2. Camera handler (hardware initialization)
        3. API client (network communication)
        
        Each component initialization includes error handling and logging.
        If any critical component fails to initialize, the application will
        not be in a runnable state.
        
        Args:
            config: AppConfig instance with application settings
        """
        self.config = config
        self.camera: Optional[CameraHandler] = None
        self.api_client: Optional[APIClient] = None
        self.display: Optional[DisplayRenderer] = None
        self.session: Optional[VideoSession] = None
        
        logger.info("Application starting...")
        logger.info(f"Configuration: API={config.api_base_url}, Camera={config.camera_index}, "
                   f"Resolution={config.camera_width}x{config.camera_height}, "
                   f"Max FPS={config.max_fps}, JPEG Quality={config.jpeg_quality}")
        
        # Initialize components in order
        self._initialize_display()
        self._initialize_camera()
        self._initialize_api_client()
        
        # Log initialization summary
        if self._is_ready():
            logger.info("All components initialized successfully")
        else:
            logger.error("Component initialization incomplete - application not ready")
    
    def _initialize_display(self) -> None:
        """
        Initialize the display renderer component.
        
        Creates the display window for showing the video feed with detection overlays.
        This is initialized first as it has no external dependencies.
        """
        try:
            logger.info("Initializing display renderer...")
            self.display = DisplayRenderer(window_name=self.config.display_window_name)
            logger.info(f"Display renderer initialized: window='{self.config.display_window_name}'")
        except Exception as e:
            logger.error(f"Failed to initialize display renderer: {e}")
            self.display = None
    
    def _initialize_camera(self) -> None:
        """
        Initialize the camera handler component.
        
        Opens the camera device and configures the frame resolution.
        Logs detailed error messages with troubleshooting tips if initialization fails.
        """
        try:
            logger.info(f"Initializing camera (index={self.config.camera_index})...")
            self.camera = CameraHandler(
                camera_index=self.config.camera_index,
                width=self.config.camera_width,
                height=self.config.camera_height
            )
            
            # Attempt to initialize the camera hardware
            if self.camera.initialize():
                logger.info(f"Camera initialized successfully: "
                           f"device={self.config.camera_index}, "
                           f"resolution={self.config.camera_width}x{self.config.camera_height}")
            else:
                logger.error("Camera initialization failed - check logs for troubleshooting tips")
                self.camera = None
                
        except Exception as e:
            logger.error(f"Exception during camera initialization: {e}")
            self.camera = None
    
    def _initialize_api_client(self) -> None:
        """
        Initialize the API client component.
        
        Creates the HTTP client for communicating with the Flask API backend.
        This component does not perform any network calls during initialization.
        """
        try:
            logger.info(f"Initializing API client (base_url={self.config.api_base_url})...")
            self.api_client = APIClient(
                base_url=self.config.api_base_url,
                timeout=self.config.api_timeout
            )
            logger.info(f"API client initialized: "
                       f"base_url={self.config.api_base_url}, "
                       f"timeout={self.config.api_timeout}s")
        except Exception as e:
            logger.error(f"Failed to initialize API client: {e}")
            self.api_client = None
    
    def _is_ready(self) -> bool:
        """
        Check if all components are initialized and ready.
        
        Returns:
            True if all components (camera, API client, display) are initialized,
            False if any component is missing
        """
        return (
            self.camera is not None and
            self.api_client is not None and
            self.display is not None
        )
    
    def run(self) -> None:
        """
        Main processing loop for the face recognition application.
        
        This method:
        1. Starts an API session
        2. Captures frames in a loop
        3. Processes frames via API
        4. Draws detections and FPS overlay
        5. Displays frames
        6. Checks for quit condition
        7. Ends session on exit
        
        The loop continues until the user presses 'q' or closes the window.
        """
        if not self._is_ready():
            logger.error("Cannot run: components not initialized")
            return
        
        # Start API session
        session_id = self.api_client.start_session()
        if session_id is None:
            logger.error("Failed to start API session - cannot proceed")
            return
        
        # Create session object
        self.session = VideoSession(
            session_id=session_id,
            start_time=datetime.now(),
            frame_count=0
        )
        logger.info(f"Session started: {session_id}")
        
        # FPS calculation variables
        fps_frame_times = []
        fps_window_size = 30  # Calculate FPS over last 30 frames
        current_fps = 0.0
        
        # Frame rate limiting
        min_frame_interval = 1.0 / self.config.max_fps
        last_process_time = 0.0
        
        # Performance metrics
        frames_processed = 0
        frames_skipped = 0
        api_errors = 0
        total_api_latency = 0.0
        last_metrics_log = time.time()
        
        logger.info("Entering main processing loop (press 'q' to quit)")
        
        try:
            while True:
                loop_start_time = time.time()
                
                # Check if we should process this frame (rate limiting)
                if loop_start_time - last_process_time < min_frame_interval:
                    # Skip frame to maintain target FPS
                    frames_skipped += 1
                    
                    # Still need to display the last frame and check for quit
                    if self.display.should_quit():
                        logger.info("Quit signal received")
                        break
                    
                    continue
                
                last_process_time = loop_start_time
                
                # Capture frame from camera
                frame = self.camera.read_frame()
                if frame is None:
                    logger.warning("Failed to capture frame, skipping")
                    frames_skipped += 1
                    continue
                
                # Process frame via API
                api_start_time = time.time()
                detections = self.api_client.process_frame(self.session.session_id, frame)
                api_latency = (time.time() - api_start_time) * 1000  # Convert to ms
                
                if detections is None:
                    # API error - display frame without detections
                    api_errors += 1
                    detections = []
                else:
                    # Successful processing
                    frames_processed += 1
                    self.session.frame_count += 1
                    total_api_latency += api_latency
                    
                    # Log detection info
                    if detections:
                        logger.info(f"Frame {self.session.frame_count}: {len(detections)} face(s) detected "
                                   f"({api_latency:.0f}ms)")
                
                # Draw detections on frame
                frame_with_detections = self.display.draw_detections(frame, detections)
                
                # Calculate FPS
                frame_time = time.time()
                fps_frame_times.append(frame_time)
                
                # Keep only last N frame times for rolling average
                if len(fps_frame_times) > fps_window_size:
                    fps_frame_times.pop(0)
                
                # Calculate FPS from frame times
                if len(fps_frame_times) >= 2:
                    time_span = fps_frame_times[-1] - fps_frame_times[0]
                    if time_span > 0:
                        current_fps = (len(fps_frame_times) - 1) / time_span
                
                # Add FPS overlay
                frame_with_overlay = self.display.add_fps_overlay(frame_with_detections, current_fps)
                
                # Display frame
                self.display.show_frame(frame_with_overlay)
                
                # Check for quit condition
                if self.display.should_quit():
                    logger.info("Quit signal received")
                    break
                
                # Log performance metrics every 30 seconds
                if time.time() - last_metrics_log >= 30.0:
                    self._log_performance_metrics(
                        current_fps,
                        frames_processed,
                        frames_skipped,
                        api_errors,
                        total_api_latency
                    )
                    last_metrics_log = time.time()
        
        except KeyboardInterrupt:
            logger.info("Interrupted by user (Ctrl+C)")
        except Exception as e:
            logger.error(f"Error in main processing loop: {e}", exc_info=True)
        finally:
            # End API session
            if self.session:
                logger.info(f"Session ending: {self.session.frame_count} frames processed")
                self.api_client.end_session(self.session.session_id, self.session.frame_count)
                
                # Log final performance metrics
                if frames_processed > 0:
                    avg_api_latency = total_api_latency / frames_processed
                    logger.info(f"Final metrics: FPS={current_fps:.1f}, "
                               f"Processed={frames_processed}, Skipped={frames_skipped}, "
                               f"Errors={api_errors}, Avg API Latency={avg_api_latency:.0f}ms")
    
    def _log_performance_metrics(
        self,
        fps: float,
        frames_processed: int,
        frames_skipped: int,
        api_errors: int,
        total_api_latency: float
    ) -> None:
        """
        Log performance metrics summary.
        
        Args:
            fps: Current frames per second
            frames_processed: Total frames successfully processed
            frames_skipped: Total frames skipped
            api_errors: Total API errors encountered
            total_api_latency: Cumulative API latency in milliseconds
        """
        avg_api_latency = total_api_latency / frames_processed if frames_processed > 0 else 0
        logger.info(f"Performance: FPS={fps:.1f} | "
                   f"API Latency={avg_api_latency:.0f}ms | "
                   f"Processed={frames_processed} | "
                   f"Skipped={frames_skipped} | "
                   f"Errors={api_errors}")
    
    def shutdown(self) -> None:
        """
        Gracefully shutdown the application and release all resources.
        
        Releases resources in reverse order of initialization:
        1. End API session (if active)
        2. Camera (release hardware)
        3. Display (destroy windows)
        """
        logger.info("Shutting down application...")
        
        # End API session if active
        if self.session and self.api_client:
            try:
                logger.info(f"Ending session: {self.session.session_id}")
                self.api_client.end_session(self.session.session_id, self.session.frame_count)
            except Exception as e:
                logger.error(f"Error ending session: {e}")
        
        # Release camera resources
        if self.camera is not None:
            try:
                self.camera.release()
            except Exception as e:
                logger.error(f"Error releasing camera: {e}")
        
        # Destroy display windows
        if self.display is not None:
            try:
                import cv2
                cv2.destroyAllWindows()
                logger.info("Display windows closed")
            except Exception as e:
                logger.error(f"Error closing display windows: {e}")
        
        logger.info("Shutdown complete")


def main():
    """Main application entry point."""
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = load_config()
        
        # Create application instance
        app = FaceRecognitionApp(config)
        
        # Run the main processing loop
        app.run()
        
        # Cleanup
        app.shutdown()
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
