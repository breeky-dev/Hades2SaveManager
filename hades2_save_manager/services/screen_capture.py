"""Screen capture service for taking screenshots of the game."""

from pathlib import Path
from typing import Optional
import logging

try:
    from PIL import Image
    import pyautogui
    SCREENSHOT_AVAILABLE = True
except ImportError:
    SCREENSHOT_AVAILABLE = False
    logging.warning("Screenshot libraries not available. Install pillow and pyautogui.")

logger = logging.getLogger(__name__)


class ScreenCapture:
    """Handles screenshot capture functionality."""
    
    def __init__(self):
        """Initialize the screen capture service."""
        self.available = SCREENSHOT_AVAILABLE
        if not self.available:
            logger.warning("Screenshot functionality is not available")
    
    def capture_screenshot(self, output_path: Path) -> bool:
        """
        Capture a screenshot and save it to the specified path.
        
        Args:
            output_path: Path where screenshot should be saved
            
        Returns:
            True if successful, False otherwise
        """
        if not self.available:
            logger.error("Screenshot libraries not available")
            return False
        
        try:
            # Create parent directory if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Capture screenshot
            screenshot = pyautogui.screenshot()
            
            # Save as PNG
            screenshot.save(str(output_path), 'PNG')
            
            logger.info(f"Screenshot saved to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
            return False
    
    def capture_and_resize(self, output_path: Path, max_width: int = 800, 
                          max_height: int = 600) -> bool:
        """
        Capture a screenshot and resize it to fit within max dimensions.
        
        Args:
            output_path: Path where screenshot should be saved
            max_width: Maximum width in pixels
            max_height: Maximum height in pixels
            
        Returns:
            True if successful, False otherwise
        """
        if not self.available:
            logger.error("Screenshot libraries not available")
            return False
        
        try:
            # Create parent directory if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Capture screenshot
            screenshot = pyautogui.screenshot()
            
            # Calculate resize dimensions maintaining aspect ratio
            width, height = screenshot.size
            aspect_ratio = width / height
            
            if width > max_width or height > max_height:
                if width / max_width > height / max_height:
                    # Width is the limiting factor
                    new_width = max_width
                    new_height = int(max_width / aspect_ratio)
                else:
                    # Height is the limiting factor
                    new_height = max_height
                    new_width = int(max_height * aspect_ratio)
                
                screenshot = screenshot.resize((new_width, new_height), Image.LANCZOS)
            
            # Save as PNG
            screenshot.save(str(output_path), 'PNG')
            
            logger.info(f"Resized screenshot saved to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to capture and resize screenshot: {e}")
            return False
    
    def create_thumbnail(self, source_path: Path, output_path: Path,
                        size: tuple = (200, 150)) -> bool:
        """
        Create a thumbnail from an existing screenshot.
        
        Args:
            source_path: Path to source image
            output_path: Path where thumbnail should be saved
            size: Thumbnail size as (width, height) tuple
            
        Returns:
            True if successful, False otherwise
        """
        if not self.available:
            logger.error("Screenshot libraries not available")
            return False
        
        try:
            if not source_path.exists():
                logger.error(f"Source image not found: {source_path}")
                return False
            
            # Create parent directory if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Open and resize image
            with Image.open(source_path) as img:
                img.thumbnail(size, Image.LANCZOS)
                img.save(str(output_path), 'PNG')
            
            logger.info(f"Thumbnail created at {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create thumbnail: {e}")
            return False
    
    def get_screen_size(self) -> Optional[tuple]:
        """
        Get the current screen resolution.
        
        Returns:
            Tuple of (width, height) or None if unavailable
        """
        if not self.available:
            return None
        
        try:
            size = pyautogui.size()
            return (size.width, size.height)
        except Exception as e:
            logger.error(f"Failed to get screen size: {e}")
            return None