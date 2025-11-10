"""Screenshot viewer dialog for displaying snapshots in full size."""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
import logging

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logging.warning("PIL not available. Screenshot viewer will not work.")

from hades2_save_manager.services import Snapshot
from hades2_save_manager.utils import format_timestamp, get_time_ago

logger = logging.getLogger(__name__)


class ScreenshotViewer(tk.Toplevel):
    """Dialog for viewing snapshot screenshots in full size."""
    
    def __init__(self, parent, snapshot: Snapshot):
        """
        Initialize the screenshot viewer.
        
        Args:
            parent: Parent window
            snapshot: Snapshot to display
        """
        super().__init__(parent)
        
        self.snapshot = snapshot
        self.photo_image = None
        
        # Configure window
        self.title(f"Snapshot Screenshot - Profile {snapshot.profile}")
        self.geometry("1200x900")
        
        # Make dialog modal
        self.transient(parent)
        self.grab_set()
        
        # Create UI
        self._create_widgets()
        
        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
        
        # Bind escape key to close
        self.bind('<Escape>', lambda e: self.destroy())
    
    def _create_widgets(self):
        """Create viewer widgets."""
        # Info header
        info_frame = ttk.Frame(self, padding="10")
        info_frame.pack(fill=tk.X)
        
        info_text = (
            f"Profile {self.snapshot.profile} • "
            f"{format_timestamp(self.snapshot.timestamp)} • "
            f"{get_time_ago(self.snapshot.timestamp)}"
        )
        
        ttk.Label(
            info_frame,
            text=info_text,
            font=('TkDefaultFont', 10)
        ).pack(side=tk.LEFT)
        
        ttk.Button(
            info_frame,
            text="Close",
            command=self.destroy
        ).pack(side=tk.RIGHT)
        
        # Separator
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X)
        
        # Image display area with scrollbars
        image_frame = ttk.Frame(self)
        image_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Vertical scrollbar
        vsb = ttk.Scrollbar(image_frame, orient=tk.VERTICAL)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Horizontal scrollbar
        hsb = ttk.Scrollbar(image_frame, orient=tk.HORIZONTAL)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Canvas for image
        self.canvas = tk.Canvas(
            image_frame,
            bg='#2b2b2b',
            highlightthickness=0,
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        vsb.config(command=self.canvas.yview)
        hsb.config(command=self.canvas.xview)
        
        # Load and display image
        self._load_image()
        
        # Mouse wheel scrolling
        self.canvas.bind('<MouseWheel>', self._on_mousewheel)
        self.canvas.bind('<Button-4>', self._on_mousewheel)
        self.canvas.bind('<Button-5>', self._on_mousewheel)
    
    def _load_image(self):
        """Load and display the screenshot."""
        if not PIL_AVAILABLE:
            # Show message if PIL not available
            self.canvas.create_text(
                600, 450,
                text="PIL not available\nCannot display screenshot",
                fill='white',
                font=('TkDefaultFont', 14),
                justify=tk.CENTER
            )
            return
        
        screenshot_path = self.snapshot.path / "snapshot.png"
        
        if not screenshot_path.exists():
            # Show message if no screenshot
            self.canvas.create_text(
                600, 450,
                text="No screenshot available\nfor this snapshot",
                fill='white',
                font=('TkDefaultFont', 14),
                justify=tk.CENTER
            )
            return
        
        try:
            # Load image
            img = Image.open(screenshot_path)
            
            # Get image dimensions
            img_width, img_height = img.size
            
            # Resize if too large (max 1920x1080)
            max_width = 1920
            max_height = 1080
            
            if img_width > max_width or img_height > max_height:
                # Calculate scaling factor
                scale = min(max_width / img_width, max_height / img_height)
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)
                img = img.resize((new_width, new_height), Image.LANCZOS)
                img_width, img_height = new_width, new_height
            
            # Convert to PhotoImage
            self.photo_image = ImageTk.PhotoImage(img)
            
            # Display on canvas
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo_image)
            
            # Configure scroll region
            self.canvas.configure(scrollregion=(0, 0, img_width, img_height))
            
            logger.info(f"Loaded screenshot: {screenshot_path} ({img_width}x{img_height})")
            
        except Exception as e:
            logger.error(f"Failed to load screenshot: {e}")
            self.canvas.create_text(
                600, 450,
                text=f"Error loading screenshot:\n{e}",
                fill='white',
                font=('TkDefaultFont', 12),
                justify=tk.CENTER
            )
    
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling."""
        if event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, 'units')
        elif event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, 'units')


def show_screenshot_viewer(parent, snapshot: Snapshot):
    """
    Show the screenshot viewer dialog.
    
    Args:
        parent: Parent window
        snapshot: Snapshot to display
    """
    viewer = ScreenshotViewer(parent, snapshot)
    # Don't wait for window - allow it to be non-modal for better UX
    # parent.wait_window(viewer)