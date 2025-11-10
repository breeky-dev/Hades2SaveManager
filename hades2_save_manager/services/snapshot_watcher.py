"""File system watcher for automatic snapshot creation."""

from pathlib import Path
from typing import Optional, Callable
import logging
import queue
import threading

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    logging.warning("Watchdog not available. Install watchdog for auto-snapshot functionality.")

from ..utils import extract_profile_number, should_create_new_snapshot, get_timestamp
from .snapshot_manager import SnapshotManager

logger = logging.getLogger(__name__)


class SaveFileEventHandler(FileSystemEventHandler):
    """Handles file system events for save files."""
    
    def __init__(self, event_queue: queue.Queue, snapshot_threshold: float = 5.0):
        """
        Initialize the event handler.
        
        Args:
            event_queue: Queue to push events to
            snapshot_threshold: Minimum seconds between snapshots
        """
        super().__init__()
        self.event_queue = event_queue
        self.snapshot_threshold = snapshot_threshold
        self.last_event_time = {}  # Per-profile timestamps
    
    def on_modified(self, event: FileSystemEvent):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        # Check if it's a save file
        if not self._is_save_file(file_path):
            return
        
        # Extract profile number
        profile_num = extract_profile_number(file_path)
        if profile_num is None:
            return
        
        # Check if we should create a snapshot (debounce)
        current_time = get_timestamp()
        last_time = self.last_event_time.get(profile_num)
        
        if should_create_new_snapshot(last_time, self.snapshot_threshold):
            # Push event to queue
            self.event_queue.put({
                'type': 'file_modified',
                'profile': profile_num,
                'file_path': file_path,
                'timestamp': current_time
            })
            
            self.last_event_time[profile_num] = current_time
            logger.info(f"Save file modified: {file_path} (Profile {profile_num})")
    
    def on_created(self, event: FileSystemEvent):
        """Handle file creation events."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        # Check if it's a save file
        if not self._is_save_file(file_path):
            return
        
        # Extract profile number
        profile_num = extract_profile_number(file_path)
        if profile_num is None:
            return
        
        # Push event to queue
        current_time = get_timestamp()
        self.event_queue.put({
            'type': 'file_created',
            'profile': profile_num,
            'file_path': file_path,
            'timestamp': current_time
        })
        
        logger.info(f"Save file created: {file_path} (Profile {profile_num})")
    
    def _is_save_file(self, file_path: Path) -> bool:
        """
        Check if a file is a save file.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if it's a save file
        """
        name = file_path.name
        return (
            name.endswith('.sav') or
            name.endswith('_Temp.sav') or
            name.endswith('.sav.bak')
        )


class SnapshotWatcher:
    """Watches for save file changes and triggers automatic snapshots."""
    
    def __init__(self, snapshot_manager: SnapshotManager, 
                 snapshot_threshold: float = 5.0):
        """
        Initialize the snapshot watcher.
        
        Args:
            snapshot_manager: SnapshotManager instance
            snapshot_threshold: Minimum seconds between snapshots
        """
        self.snapshot_manager = snapshot_manager
        self.snapshot_threshold = snapshot_threshold
        self.event_queue = queue.Queue()
        self.observer: Optional[Observer] = None
        self.event_handler: Optional[SaveFileEventHandler] = None
        self.running = False
        self.enabled = False
        self.processing_thread: Optional[threading.Thread] = None
        
        # Callbacks
        self.on_snapshot_created: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        if not WATCHDOG_AVAILABLE:
            logger.error("Watchdog library not available. Auto-snapshot will not work.")
    
    def start(self) -> bool:
        """
        Start watching for file changes.
        
        Returns:
            True if started successfully, False otherwise
        """
        if not WATCHDOG_AVAILABLE:
            logger.error("Cannot start watcher: watchdog not available")
            return False
        
        if self.running:
            logger.warning("Watcher is already running")
            return True
        
        try:
            # Create event handler
            self.event_handler = SaveFileEventHandler(
                self.event_queue,
                self.snapshot_threshold
            )
            
            # Create observer
            self.observer = Observer()
            self.observer.schedule(
                self.event_handler,
                str(self.snapshot_manager.save_dir),
                recursive=True
            )
            
            # Start observer
            self.observer.start()
            
            # Start event processing thread
            self.running = True
            self.processing_thread = threading.Thread(
                target=self._process_events,
                daemon=True
            )
            self.processing_thread.start()
            
            logger.info(f"Watcher started for {self.snapshot_manager.save_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start watcher: {e}")
            self.running = False
            return False
    
    def stop(self):
        """Stop watching for file changes."""
        if not self.running:
            return
        
        self.running = False
        
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=5)
            self.observer = None
        
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
            self.processing_thread = None
        
        logger.info("Watcher stopped")
    
    def enable(self):
        """Enable automatic snapshot creation."""
        self.enabled = True
        logger.info("Auto-snapshot enabled")
    
    def disable(self):
        """Disable automatic snapshot creation."""
        self.enabled = False
        logger.info("Auto-snapshot disabled")
    
    def is_enabled(self) -> bool:
        """Check if auto-snapshot is enabled."""
        return self.enabled
    
    def is_running(self) -> bool:
        """Check if watcher is running."""
        return self.running
    
    def _process_events(self):
        """Process events from the queue (runs in separate thread)."""
        logger.info("Event processing thread started")
        
        while self.running:
            try:
                # Get event from queue with timeout
                event = self.event_queue.get(timeout=1)
                
                # Only process if auto-snapshot is enabled
                if not self.enabled:
                    continue
                
                # Create snapshot
                profile_num = event['profile']
                logger.info(f"Creating auto-snapshot for profile {profile_num}")
                
                # Determine if we should overwrite the last snapshot
                last_time = self.snapshot_manager.get_last_snapshot_time(profile_num)
                overwrite = False
                
                if last_time is not None:
                    time_diff = event['timestamp'] - last_time
                    # If less than threshold, overwrite (same room)
                    if time_diff <= self.snapshot_threshold:
                        overwrite = True
                
                snapshot = self.snapshot_manager.create_snapshot(
                    profile_num,
                    take_screenshot=True,
                    overwrite_last=overwrite
                )
                
                if snapshot:
                    logger.info(f"Auto-snapshot created: {snapshot.path}")
                    
                    # Call callback if set
                    if self.on_snapshot_created:
                        try:
                            self.on_snapshot_created(snapshot)
                        except Exception as e:
                            logger.error(f"Error in snapshot_created callback: {e}")
                else:
                    logger.error("Failed to create auto-snapshot")
                    
                    # Call error callback if set
                    if self.on_error:
                        try:
                            self.on_error("Failed to create snapshot")
                        except Exception as e:
                            logger.error(f"Error in error callback: {e}")
                
            except queue.Empty:
                # Timeout, continue loop
                continue
            except Exception as e:
                logger.error(f"Error processing event: {e}")
                
                if self.on_error:
                    try:
                        self.on_error(str(e))
                    except Exception as callback_error:
                        logger.error(f"Error in error callback: {callback_error}")
        
        logger.info("Event processing thread stopped")
    
    def set_snapshot_created_callback(self, callback: Callable):
        """
        Set callback to be called when a snapshot is created.
        
        Args:
            callback: Function that takes a Snapshot object as parameter
        """
        self.on_snapshot_created = callback
    
    def set_error_callback(self, callback: Callable):
        """
        Set callback to be called when an error occurs.
        
        Args:
            callback: Function that takes an error message string as parameter
        """
        self.on_error = callback