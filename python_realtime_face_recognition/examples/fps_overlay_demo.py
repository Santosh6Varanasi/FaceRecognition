"""
Demo script showing how to use the FPS overlay feature.

This script demonstrates the add_fps_overlay method of DisplayRenderer
by creating a simple animation with an FPS counter.
"""

import sys
import os
import time
import numpy as np

# Add parent directory to path to import src modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.display_renderer import DisplayRenderer


def main():
    """Run FPS overlay demonstration."""
    print("FPS Overlay Demo")
    print("Press 'q' to quit")
    print("-" * 40)
    
    # Create display renderer
    renderer = DisplayRenderer("FPS Overlay Demo")
    
    # Create a sample frame (640x480 with gradient)
    height, width = 480, 640
    
    # Track FPS
    frame_times = []
    frame_count = 0
    
    try:
        while True:
            start_time = time.time()
            
            # Create a dynamic frame with changing colors
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            
            # Add some visual interest - moving gradient
            offset = (frame_count * 2) % 255
            for y in range(height):
                for x in range(width):
                    frame[y, x] = [
                        (x + offset) % 255,
                        (y + offset) % 255,
                        (x + y + offset) % 255
                    ]
            
            # Calculate FPS
            if len(frame_times) > 0:
                avg_frame_time = sum(frame_times[-30:]) / len(frame_times[-30:])
                fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0.0
            else:
                fps = 0.0
            
            # Add FPS overlay
            frame_with_fps = renderer.add_fps_overlay(frame, fps)
            
            # Display the frame
            renderer.show_frame(frame_with_fps)
            
            # Check for quit
            if renderer.should_quit():
                break
            
            # Track frame time
            frame_time = time.time() - start_time
            frame_times.append(frame_time)
            frame_count += 1
            
            # Limit to ~30 FPS
            time.sleep(max(0, 1/30 - frame_time))
    
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
    
    finally:
        print(f"\nProcessed {frame_count} frames")
        if len(frame_times) > 0:
            avg_fps = 1.0 / (sum(frame_times) / len(frame_times))
            print(f"Average FPS: {avg_fps:.1f}")


if __name__ == "__main__":
    main()
