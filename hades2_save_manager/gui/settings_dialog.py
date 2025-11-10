"""Settings dialog for configuring the application."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import json
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class SettingsDialog(tk.Toplevel):
    """Dialog for application settings."""
    
    def __init__(self, parent, settings: Dict):
        """
        Initialize the settings dialog.
        
        Args:
            parent: Parent window
            settings: Current settings dictionary
        """
        super().__init__(parent)
        
        self.title("Settings")
        self.geometry("600x400")
        self.resizable(False, False)
        
        # Make dialog modal
        self.transient(parent)
        self.grab_set()
        
        # Store settings
        self.settings = settings.copy()
        self.result = None
        
        # Create UI
        self._create_widgets()
        
        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
    
    def _create_widgets(self):
        """Create dialog widgets."""
        # Main frame with padding
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Save folder section
        save_frame = ttk.LabelFrame(main_frame, text="Game Save Folder", padding="10")
        save_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.save_dir_var = tk.StringVar(value=self.settings.get('save_dir', ''))
        
        save_entry_frame = ttk.Frame(save_frame)
        save_entry_frame.pack(fill=tk.X)
        
        ttk.Entry(
            save_entry_frame,
            textvariable=self.save_dir_var,
            state='readonly'
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Button(
            save_entry_frame,
            text="Browse...",
            command=self._browse_save_dir
        ).pack(side=tk.RIGHT)
        
        ttk.Label(
            save_frame,
            text="Location of Hades II save files (usually %USERPROFILE%/Saved Games/Hades II)",
            font=('TkDefaultFont', 8),
            foreground='gray'
        ).pack(anchor=tk.W, pady=(5, 0))
        
        # Snapshot folder section
        snapshot_frame = ttk.LabelFrame(main_frame, text="Snapshot Storage Folder", padding="10")
        snapshot_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.snapshot_dir_var = tk.StringVar(value=self.settings.get('snapshot_dir', ''))
        
        snapshot_entry_frame = ttk.Frame(snapshot_frame)
        snapshot_entry_frame.pack(fill=tk.X)
        
        ttk.Entry(
            snapshot_entry_frame,
            textvariable=self.snapshot_dir_var,
            state='readonly'
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Button(
            snapshot_entry_frame,
            text="Browse...",
            command=self._browse_snapshot_dir
        ).pack(side=tk.RIGHT)
        
        ttk.Label(
            snapshot_frame,
            text="Where snapshots will be stored",
            font=('TkDefaultFont', 8),
            foreground='gray'
        ).pack(anchor=tk.W, pady=(5, 0))
        
        # Auto-snapshot section
        auto_frame = ttk.LabelFrame(main_frame, text="Auto-Snapshot", padding="10")
        auto_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.auto_snapshot_var = tk.BooleanVar(
            value=self.settings.get('auto_snapshot_enabled', True)
        )
        
        ttk.Checkbutton(
            auto_frame,
            text="Enable automatic snapshots when entering new rooms",
            variable=self.auto_snapshot_var
        ).pack(anchor=tk.W)
        
        # Snapshot threshold
        threshold_frame = ttk.Frame(auto_frame)
        threshold_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(
            threshold_frame,
            text="Snapshot threshold (seconds):"
        ).pack(side=tk.LEFT)
        
        self.threshold_var = tk.StringVar(
            value=str(self.settings.get('snapshot_threshold', 5.0))
        )
        
        threshold_spinbox = ttk.Spinbox(
            threshold_frame,
            from_=1.0,
            to=60.0,
            increment=1.0,
            textvariable=self.threshold_var,
            width=10
        )
        threshold_spinbox.pack(side=tk.LEFT, padx=(5, 0))
        
        ttk.Label(
            auto_frame,
            text="Minimum time between snapshots (prevents duplicate snapshots for same room)",
            font=('TkDefaultFont', 8),
            foreground='gray'
        ).pack(anchor=tk.W, pady=(5, 0))
        
        # Process check section
        process_frame = ttk.LabelFrame(main_frame, text="Safety", padding="10")
        process_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.check_process_var = tk.BooleanVar(
            value=self.settings.get('check_game_running', True)
        )
        
        ttk.Checkbutton(
            process_frame,
            text="Check if game is running before restoring snapshots",
            variable=self.check_process_var
        ).pack(anchor=tk.W)
        
        ttk.Label(
            process_frame,
            text="Prevents data corruption by ensuring the game is closed",
            font=('TkDefaultFont', 8),
            foreground='gray'
        ).pack(anchor=tk.W, pady=(5, 0))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(
            button_frame,
            text="Cancel",
            command=self._cancel
        ).pack(side=tk.RIGHT, padx=(5, 0))
        
        ttk.Button(
            button_frame,
            text="Save",
            command=self._save
        ).pack(side=tk.RIGHT)
        
        ttk.Button(
            button_frame,
            text="Reset to Defaults",
            command=self._reset_defaults
        ).pack(side=tk.LEFT)
    
    def _browse_save_dir(self):
        """Browse for save directory."""
        initial_dir = self.save_dir_var.get() or str(Path.home())
        
        directory = filedialog.askdirectory(
            parent=self,
            title="Select Game Save Folder",
            initialdir=initial_dir
        )
        
        if directory:
            self.save_dir_var.set(directory)
    
    def _browse_snapshot_dir(self):
        """Browse for snapshot directory."""
        initial_dir = self.snapshot_dir_var.get() or str(Path.home())
        
        directory = filedialog.askdirectory(
            parent=self,
            title="Select Snapshot Storage Folder",
            initialdir=initial_dir
        )
        
        if directory:
            self.snapshot_dir_var.set(directory)
    
    def _reset_defaults(self):
        """Reset settings to defaults."""
        if messagebox.askyesno(
            "Reset Settings",
            "Reset all settings to default values?",
            parent=self
        ):
            # Default save directory
            default_save_dir = Path.home() / "Saved Games" / "Hades II"
            self.save_dir_var.set(str(default_save_dir))
            
            # Default snapshot directory
            default_snapshot_dir = Path.home() / "Documents" / "Hades2SaveManager" / "Snapshots"
            self.snapshot_dir_var.set(str(default_snapshot_dir))
            
            # Default settings
            self.auto_snapshot_var.set(True)
            self.threshold_var.set("5.0")
            self.check_process_var.set(True)
    
    def _validate_settings(self) -> bool:
        """
        Validate settings before saving.
        
        Returns:
            True if valid, False otherwise
        """
        # Check save directory
        save_dir = self.save_dir_var.get().strip()
        if not save_dir:
            messagebox.showerror(
                "Invalid Settings",
                "Please select a game save folder.",
                parent=self
            )
            return False
        
        # Check snapshot directory
        snapshot_dir = self.snapshot_dir_var.get().strip()
        if not snapshot_dir:
            messagebox.showerror(
                "Invalid Settings",
                "Please select a snapshot storage folder.",
                parent=self
            )
            return False
        
        # Validate threshold
        try:
            threshold = float(self.threshold_var.get())
            if threshold < 1.0 or threshold > 60.0:
                raise ValueError()
        except ValueError:
            messagebox.showerror(
                "Invalid Settings",
                "Snapshot threshold must be between 1 and 60 seconds.",
                parent=self
            )
            return False
        
        return True
    
    def _save(self):
        """Save settings and close dialog."""
        if not self._validate_settings():
            return
        
        # Update settings
        self.settings['save_dir'] = self.save_dir_var.get().strip()
        self.settings['snapshot_dir'] = self.snapshot_dir_var.get().strip()
        self.settings['auto_snapshot_enabled'] = self.auto_snapshot_var.get()
        self.settings['snapshot_threshold'] = float(self.threshold_var.get())
        self.settings['check_game_running'] = self.check_process_var.get()
        
        self.result = self.settings
        self.destroy()
    
    def _cancel(self):
        """Cancel and close dialog."""
        self.result = None
        self.destroy()
    
    def get_result(self) -> Optional[Dict]:
        """
        Get the dialog result.
        
        Returns:
            Updated settings dictionary or None if cancelled
        """
        return self.result


def show_settings_dialog(parent, settings: Dict) -> Optional[Dict]:
    """
    Show the settings dialog and return the result.
    
    Args:
        parent: Parent window
        settings: Current settings dictionary
        
    Returns:
        Updated settings dictionary or None if cancelled
    """
    dialog = SettingsDialog(parent, settings)
    parent.wait_window(dialog)
    return dialog.get_result()