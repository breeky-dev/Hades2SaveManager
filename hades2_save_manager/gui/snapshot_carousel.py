"""Snapshot carousel widget for browsing snapshots visually."""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import List, Optional, Callable
import logging

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logging.warning("PIL not available. Carousel will not display images.")

from ..services import Snapshot
from ..utils import format_timestamp, get_time_ago

logger = logging.getLogger(__name__)


class SnapshotCarousel(ttk.Frame):
    """Horizontal scrollable carousel for snapshot thumbnails."""
    
    def __init__(self, parent, **kwargs):
        """
        Initialize the snapshot carousel.
        
        Args:
            parent: Parent widget
            **kwargs: Additional frame arguments
        """
        super().__init__(parent, **kwargs)
        
        self.snapshots: List[Snapshot] = []
        self.selected_index: Optional[int] = None
        self.thumbnail_widgets: List[tk.Frame] = []
        self.on_select_callback: Optional[Callable] = None
        
        self.thumbnail_size = (200, 150)
        self.placeholder_image = None
        
        self._create_widgets()
        
        if PIL_AVAILABLE:
            self._create_placeholder_image()
    
    def _create_widgets(self):
        """Create carousel widgets."""
        # Title
        title_label = ttk.Label(
            self,
            text="Recent Snapshots",
            font=('TkDefaultFont', 10, 'bold')
        )
        title_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Scrollable frame
        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        # Canvas for scrolling
        self.canvas = tk.Canvas(
            canvas_frame,
            height=200,
            highlightthickness=0
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(
            canvas_frame,
            orient=tk.HORIZONTAL,
            command=self.canvas.xview
        )
        scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.canvas.configure(xscrollcommand=scrollbar.set)
        
        # Frame inside canvas
        self.thumbnails_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window(
            (0, 0),
            window=self.thumbnails_frame,
            anchor=tk.NW
        )
        
        # Bind resize
        self.thumbnails_frame.bind('<Configure>', self._on_frame_configure)
        
        # Mouse wheel scrolling
        self.canvas.bind('<MouseWheel>', self._on_mousewheel)
        self.canvas.bind('<Button-4>', self._on_mousewheel)
        self.canvas.bind('<Button-5>', self._on_mousewheel)
    
    def _create_placeholder_image(self):
        """Create a placeholder image for snapshots without screenshots."""
        if not PIL_AVAILABLE:
            return
        
        try:
            # Create a simple gray placeholder
            img = Image.new('RGB', self.thumbnail_size, color='#cccccc')
            self.placeholder_image = ImageTk.PhotoImage(img)
        except Exception as e:
            logger.error(f"Failed to create placeholder image: {e}")
    
    def _on_frame_configure(self, event=None):
        """Update scroll region when frame size changes."""
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
    
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling."""
        if event.num == 4 or event.delta > 0:
            self.canvas.xview_scroll(-1, 'units')
        elif event.num == 5 or event.delta < 0:
            self.canvas.xview_scroll(1, 'units')
    
    def set_snapshots(self, snapshots: List[Snapshot]):
        """
        Set the snapshots to display in the carousel.
        
        Args:
            snapshots: List of Snapshot objects
        """
        self.snapshots = snapshots
        self.selected_index = None
        self._refresh_thumbnails()
    
    def _refresh_thumbnails(self):
        """Refresh the thumbnail display."""
        # Clear existing thumbnails
        for widget in self.thumbnail_widgets:
            widget.destroy()
        self.thumbnail_widgets.clear()
        
        # Create new thumbnails
        for i, snapshot in enumerate(self.snapshots):
            thumbnail = self._create_thumbnail(i, snapshot)
            thumbnail.pack(side=tk.LEFT, padx=5, pady=5)
            self.thumbnail_widgets.append(thumbnail)
        
        # Update scroll region
        self.thumbnails_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
    
    def _create_thumbnail(self, index: int, snapshot: Snapshot) -> tk.Frame:
        """
        Create a thumbnail widget for a snapshot.
        
        Args:
            index: Index in snapshots list
            snapshot: Snapshot object
            
        Returns:
            Frame containing the thumbnail
        """
        # Container frame
        frame = tk.Frame(
            self.thumbnails_frame,
            relief=tk.RAISED,
            borderwidth=2,
            cursor='hand2'
        )
        
        # Load and display image
        if PIL_AVAILABLE and snapshot.has_screenshot:
            screenshot_path = snapshot.path / "snapshot.png"
            if screenshot_path.exists():
                try:
                    img = Image.open(screenshot_path)
                    img.thumbnail(self.thumbnail_size, Image.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    
                    img_label = tk.Label(frame, image=photo)
                    img_label.image = photo  # Keep reference
                    img_label.pack()
                except Exception as e:
                    logger.error(f"Failed to load thumbnail: {e}")
                    self._create_placeholder_label(frame)
            else:
                self._create_placeholder_label(frame)
        else:
            self._create_placeholder_label(frame)
        
        # Info label
        time_str = get_time_ago(snapshot.timestamp)
        info_text = f"Profile {snapshot.profile}\n{time_str}"
        
        info_label = tk.Label(
            frame,
            text=info_text,
            font=('TkDefaultFont', 8),
            bg='white',
            pady=5
        )
        info_label.pack(fill=tk.X)
        
        # Bind click event
        frame.bind('<Button-1>', lambda e, idx=index: self._on_thumbnail_click(idx))
        for child in frame.winfo_children():
            child.bind('<Button-1>', lambda e, idx=index: self._on_thumbnail_click(idx))
        
        return frame
    
    def _create_placeholder_label(self, parent):
        """Create a placeholder label when image is not available."""
        if PIL_AVAILABLE and self.placeholder_image:
            label = tk.Label(parent, image=self.placeholder_image)
            label.image = self.placeholder_image
            label.pack()
        else:
            label = tk.Label(
                parent,
                text="No Screenshot",
                width=25,
                height=10,
                bg='#cccccc'
            )
            label.pack()
    
    def _on_thumbnail_click(self, index: int):
        """
        Handle thumbnail click.
        
        Args:
            index: Index of clicked thumbnail
        """
        # Update selection
        old_index = self.selected_index
        self.selected_index = index
        
        # Update visual state
        if old_index is not None and old_index < len(self.thumbnail_widgets):
            self.thumbnail_widgets[old_index].configure(relief=tk.RAISED, borderwidth=2)
        
        if index < len(self.thumbnail_widgets):
            self.thumbnail_widgets[index].configure(relief=tk.SUNKEN, borderwidth=3)
        
        # Call callback
        if self.on_select_callback and index < len(self.snapshots):
            try:
                self.on_select_callback(self.snapshots[index])
            except Exception as e:
                logger.error(f"Error in select callback: {e}")
    
    def get_selected_snapshot(self) -> Optional[Snapshot]:
        """
        Get the currently selected snapshot.
        
        Returns:
            Selected Snapshot or None
        """
        if self.selected_index is not None and self.selected_index < len(self.snapshots):
            return self.snapshots[self.selected_index]
        return None
    
    def set_on_select_callback(self, callback: Callable):
        """
        Set callback to be called when a snapshot is selected.
        
        Args:
            callback: Function that takes a Snapshot object as parameter
        """
        self.on_select_callback = callback
    
    def clear(self):
        """Clear all snapshots from the carousel."""
        self.snapshots.clear()
        self.selected_index = None
        self._refresh_thumbnails()
    
    def refresh(self):
        """Refresh the carousel display."""
        self._refresh_thumbnails()