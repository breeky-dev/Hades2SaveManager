"""Main application window."""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import json
import logging
from typing import Optional, Dict

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logging.warning("psutil not available. Game process checking will be disabled.")

from ..services import SnapshotManager, SnapshotWatcher, Snapshot
from .snapshot_carousel import SnapshotCarousel
from .snapshot_list import SnapshotList
from .settings_dialog import show_settings_dialog

logger = logging.getLogger(__name__)


class MainWindow(tk.Tk):
    """Main application window."""
    
    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        
        self.title("Hades II Save Manager")
        self.geometry("1200x800")
        
        # Settings
        self.settings = self._load_settings()
        
        # Services
        self.snapshot_manager: Optional[SnapshotManager] = None
        self.snapshot_watcher: Optional[SnapshotWatcher] = None
        
        # Current state
        self.current_profile = 1
        self.selected_snapshot: Optional[Snapshot] = None
        
        # Create UI
        self._create_menu()
        self._create_widgets()
        self._create_status_bar()
        
        # Initialize services
        self._initialize_services()
        
        # Load initial data
        self._refresh_snapshots()
        
        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _load_settings(self) -> Dict:
        """Load settings from file."""
        settings_file = Path.home() / ".hades2_save_manager" / "settings.json"
        
        # Default settings
        default_settings = {
            'save_dir': str(Path.home() / "Saved Games" / "Hades II"),
            'snapshot_dir': str(Path.home() / "Documents" / "Hades2SaveManager" / "Snapshots"),
            'auto_snapshot_enabled': True,
            'snapshot_threshold': 5.0,
            'check_game_running': True
        }
        
        try:
            if settings_file.exists():
                with open(settings_file, 'r') as f:
                    loaded_settings = json.load(f)
                    # Merge with defaults
                    default_settings.update(loaded_settings)
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
        
        return default_settings
    
    def _save_settings(self):
        """Save settings to file."""
        settings_file = Path.home() / ".hades2_save_manager" / "settings.json"
        
        try:
            settings_file.parent.mkdir(parents=True, exist_ok=True)
            with open(settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
    
    def _create_menu(self):
        """Create menu bar."""
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Settings", command=self._show_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close)
        
        # Snapshot menu
        snapshot_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Snapshot", menu=snapshot_menu)
        snapshot_menu.add_command(label="Take Snapshot Now", command=self._take_manual_snapshot)
        snapshot_menu.add_separator()
        snapshot_menu.add_command(label="Refresh List", command=self._refresh_snapshots)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)
    
    def _create_widgets(self):
        """Create main window widgets."""
        # Toolbar
        toolbar = ttk.Frame(self, padding="5")
        toolbar.pack(fill=tk.X)
        
        # Profile selector
        ttk.Label(toolbar, text="Profile:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.profile_var = tk.IntVar(value=self.current_profile)
        profile_combo = ttk.Combobox(
            toolbar,
            textvariable=self.profile_var,
            values=[1, 2, 3, 4],
            state='readonly',
            width=5
        )
        profile_combo.pack(side=tk.LEFT, padx=(0, 10))
        profile_combo.bind('<<ComboboxSelected>>', self._on_profile_changed)
        
        # Auto-snapshot toggle
        self.auto_var = tk.BooleanVar(value=self.settings.get('auto_snapshot_enabled', True))
        auto_check = ttk.Checkbutton(
            toolbar,
            text="Auto-Snapshot",
            variable=self.auto_var,
            command=self._on_auto_toggle
        )
        auto_check.pack(side=tk.LEFT, padx=(0, 10))
        
        # Manual snapshot button
        ttk.Button(
            toolbar,
            text="Take Snapshot",
            command=self._take_manual_snapshot
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        # Restore button
        self.restore_button = ttk.Button(
            toolbar,
            text="Restore Selected",
            command=self._restore_snapshot,
            state=tk.DISABLED
        )
        self.restore_button.pack(side=tk.LEFT)
        
        # Settings button
        ttk.Button(
            toolbar,
            text="Settings",
            command=self._show_settings
        ).pack(side=tk.RIGHT)
        
        # Main content area
        content = ttk.Frame(self, padding="10")
        content.pack(fill=tk.BOTH, expand=True)
        
        # Carousel
        self.carousel = SnapshotCarousel(content)
        self.carousel.pack(fill=tk.X, pady=(0, 10))
        self.carousel.set_on_select_callback(self._on_snapshot_selected)
        
        # Separator
        ttk.Separator(content, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 10))
        
        # Snapshot list
        self.snapshot_list = SnapshotList(content)
        self.snapshot_list.pack(fill=tk.BOTH, expand=True)
        self.snapshot_list.set_on_select_callback(self._on_snapshot_selected)
        self.snapshot_list.set_on_delete_callback(self._delete_snapshots)
    
    def _create_status_bar(self):
        """Create status bar."""
        self.status_bar = ttk.Frame(self, relief=tk.SUNKEN)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_label = ttk.Label(
            self.status_bar,
            text="Ready",
            padding="2"
        )
        self.status_label.pack(side=tk.LEFT)
        
        self.watcher_status_label = ttk.Label(
            self.status_bar,
            text="Watcher: Stopped",
            padding="2"
        )
        self.watcher_status_label.pack(side=tk.RIGHT)
    
    def _initialize_services(self):
        """Initialize snapshot manager and watcher."""
        try:
            save_dir = Path(self.settings['save_dir'])
            snapshot_dir = Path(self.settings['snapshot_dir'])
            
            # Create snapshot manager
            self.snapshot_manager = SnapshotManager(save_dir, snapshot_dir)
            
            # Create and start watcher
            self.snapshot_watcher = SnapshotWatcher(
                self.snapshot_manager,
                self.settings['snapshot_threshold']
            )
            
            # Set callbacks
            self.snapshot_watcher.set_snapshot_created_callback(self._on_auto_snapshot_created)
            self.snapshot_watcher.set_error_callback(self._on_watcher_error)
            
            # Start watcher
            if self.snapshot_watcher.start():
                if self.auto_var.get():
                    self.snapshot_watcher.enable()
                self._update_watcher_status()
            else:
                messagebox.showwarning(
                    "Watcher Error",
                    "Failed to start file watcher. Auto-snapshot will not work."
                )
        
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            messagebox.showerror(
                "Initialization Error",
                f"Failed to initialize services: {e}"
            )
    
    def _refresh_snapshots(self):
        """Refresh snapshot list."""
        if not self.snapshot_manager:
            return
        
        try:
            snapshots = self.snapshot_manager.list_snapshots(self.current_profile)
            
            # Update carousel (show recent 10)
            self.carousel.set_snapshots(snapshots[:10])
            
            # Update list (show all)
            self.snapshot_list.set_snapshots(snapshots)
            
            self._set_status(f"Loaded {len(snapshots)} snapshots for Profile {self.current_profile}")
        
        except Exception as e:
            logger.error(f"Failed to refresh snapshots: {e}")
            self._set_status(f"Error loading snapshots: {e}")
    
    def _on_profile_changed(self, event=None):
        """Handle profile selection change."""
        self.current_profile = self.profile_var.get()
        self._refresh_snapshots()
    
    def _on_auto_toggle(self):
        """Handle auto-snapshot toggle."""
        if not self.snapshot_watcher:
            return
        
        if self.auto_var.get():
            self.snapshot_watcher.enable()
            self._set_status("Auto-snapshot enabled")
        else:
            self.snapshot_watcher.disable()
            self._set_status("Auto-snapshot disabled")
        
        self._update_watcher_status()
        
        # Save setting
        self.settings['auto_snapshot_enabled'] = self.auto_var.get()
        self._save_settings()
    
    def _take_manual_snapshot(self):
        """Take a manual snapshot."""
        if not self.snapshot_manager:
            return
        
        try:
            self._set_status("Taking snapshot...")
            snapshot = self.snapshot_manager.create_snapshot(
                self.current_profile,
                take_screenshot=True,
                overwrite_last=False
            )
            
            if snapshot:
                self._set_status("Snapshot created successfully")
                self._refresh_snapshots()
            else:
                self._set_status("Failed to create snapshot")
                messagebox.showerror(
                    "Snapshot Error",
                    "Failed to create snapshot. Check logs for details."
                )
        
        except Exception as e:
            logger.error(f"Failed to take manual snapshot: {e}")
            self._set_status(f"Error: {e}")
            messagebox.showerror("Snapshot Error", str(e))
    
    def _on_snapshot_selected(self, snapshot: Snapshot):
        """Handle snapshot selection."""
        self.selected_snapshot = snapshot
        self.restore_button.config(state=tk.NORMAL)
        self._set_status(f"Selected: {snapshot.path.name}")
    
    def _restore_snapshot(self):
        """Restore the selected snapshot."""
        if not self.selected_snapshot or not self.snapshot_manager:
            return
        
        # Check if game is running
        if self.settings.get('check_game_running', True) and PSUTIL_AVAILABLE:
            if self._is_game_running():
                messagebox.showwarning(
                    "Game Running",
                    "Hades II is currently running. Please close the game before restoring a snapshot.",
                    parent=self
                )
                return
        
        # Confirm restore
        if not messagebox.askyesno(
            "Restore Snapshot",
            f"Restore snapshot from {self.selected_snapshot.path.name}?\n\n"
            "This will overwrite your current save files.\n"
            "A backup will be created automatically.",
            parent=self
        ):
            return
        
        try:
            self._set_status("Restoring snapshot...")
            
            if self.snapshot_manager.restore_snapshot(self.selected_snapshot):
                self._set_status("Snapshot restored successfully")
                messagebox.showinfo(
                    "Restore Complete",
                    "Snapshot restored successfully!\n\n"
                    "You can now start Hades II.",
                    parent=self
                )
            else:
                self._set_status("Failed to restore snapshot")
                messagebox.showerror(
                    "Restore Error",
                    "Failed to restore snapshot. Check logs for details.",
                    parent=self
                )
        
        except Exception as e:
            logger.error(f"Failed to restore snapshot: {e}")
            self._set_status(f"Error: {e}")
            messagebox.showerror("Restore Error", str(e), parent=self)
    
    def _delete_snapshots(self, snapshots: list):
        """Delete snapshots."""
        if not self.snapshot_manager:
            return
        
        try:
            deleted = self.snapshot_manager.delete_snapshots(snapshots)
            self._set_status(f"Deleted {deleted} snapshot(s)")
            self._refresh_snapshots()
        
        except Exception as e:
            logger.error(f"Failed to delete snapshots: {e}")
            self._set_status(f"Error: {e}")
    
    def _on_auto_snapshot_created(self, snapshot: Snapshot):
        """Handle auto-snapshot creation."""
        # Update UI from main thread
        self.after(0, lambda: self._refresh_snapshots())
        self.after(0, lambda: self._set_status(f"Auto-snapshot created: {snapshot.path.name}"))
    
    def _on_watcher_error(self, error: str):
        """Handle watcher error."""
        logger.error(f"Watcher error: {error}")
        self.after(0, lambda: self._set_status(f"Watcher error: {error}"))
    
    def _is_game_running(self) -> bool:
        """Check if Hades II is running."""
        if not PSUTIL_AVAILABLE:
            return False
        
        try:
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] and 'hades' in proc.info['name'].lower():
                    return True
        except Exception as e:
            logger.error(f"Failed to check if game is running: {e}")
        
        return False
    
    def _show_settings(self):
        """Show settings dialog."""
        result = show_settings_dialog(self, self.settings)
        
        if result:
            self.settings = result
            self._save_settings()
            
            # Reinitialize services if paths changed
            if self.snapshot_watcher:
                self.snapshot_watcher.stop()
            
            self._initialize_services()
            self._refresh_snapshots()
    
    def _show_about(self):
        """Show about dialog."""
        messagebox.showinfo(
            "About",
            "Hades II Save Manager\n\n"
            "A tool for managing Hades II save file snapshots.\n\n"
            "Features:\n"
            "• Automatic snapshots when entering new rooms\n"
            "• Manual snapshot creation\n"
            "• Snapshot browsing and restoration\n"
            "• Screenshot capture\n\n"
            "Version 1.0",
            parent=self
        )
    
    def _set_status(self, message: str):
        """Set status bar message."""
        self.status_label.config(text=message)
    
    def _update_watcher_status(self):
        """Update watcher status in status bar."""
        if not self.snapshot_watcher:
            status = "Watcher: Not initialized"
        elif not self.snapshot_watcher.is_running():
            status = "Watcher: Stopped"
        elif self.snapshot_watcher.is_enabled():
            status = "Watcher: Active"
        else:
            status = "Watcher: Paused"
        
        self.watcher_status_label.config(text=status)
    
    def _on_close(self):
        """Handle window close."""
        # Stop watcher
        if self.snapshot_watcher:
            self.snapshot_watcher.stop()
        
        # Save settings
        self._save_settings()
        
        # Destroy window
        self.destroy()