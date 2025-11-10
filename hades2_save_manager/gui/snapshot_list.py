"""Snapshot list widget with table view and bulk operations."""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Optional, Callable
import logging

from hades2_save_manager.services import Snapshot
from hades2_save_manager.utils import format_timestamp, format_file_size, get_time_ago

logger = logging.getLogger(__name__)


class SnapshotList(ttk.Frame):
    """Table view for snapshots with sorting and bulk operations."""
    
    def __init__(self, parent, **kwargs):
        """
        Initialize the snapshot list.
        
        Args:
            parent: Parent widget
            **kwargs: Additional frame arguments
        """
        super().__init__(parent, **kwargs)
        
        self.snapshots: List[Snapshot] = []
        self.on_select_callback: Optional[Callable] = None
        self.on_delete_callback: Optional[Callable] = None
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create list widgets."""
        # Title and controls
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(
            header_frame,
            text="All Snapshots",
            font=('TkDefaultFont', 10, 'bold')
        ).pack(side=tk.LEFT)
        
        # Delete button
        self.delete_button = ttk.Button(
            header_frame,
            text="Delete Selected",
            command=self._on_delete_selected,
            state=tk.DISABLED
        )
        self.delete_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Refresh button
        self.refresh_button = ttk.Button(
            header_frame,
            text="Refresh",
            command=self._on_refresh
        )
        self.refresh_button.pack(side=tk.RIGHT)
        
        # Treeview with scrollbars
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Vertical scrollbar
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Horizontal scrollbar
        hsb = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Treeview
        columns = ('profile', 'timestamp', 'time_ago', 'size', 'screenshot')
        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show='headings',
            selectmode='extended',
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set
        )
        
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)
        
        # Configure columns
        self.tree.heading('profile', text='Profile', command=lambda: self._sort_by('profile'))
        self.tree.heading('timestamp', text='Date/Time', command=lambda: self._sort_by('timestamp'))
        self.tree.heading('time_ago', text='Time Ago', command=lambda: self._sort_by('time_ago'))
        self.tree.heading('size', text='Size', command=lambda: self._sort_by('size'))
        self.tree.heading('screenshot', text='Screenshot', command=lambda: self._sort_by('screenshot'))
        
        self.tree.column('profile', width=80, anchor=tk.CENTER)
        self.tree.column('timestamp', width=180)
        self.tree.column('time_ago', width=120)
        self.tree.column('size', width=100, anchor=tk.E)
        self.tree.column('screenshot', width=100, anchor=tk.CENTER)
        
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # Bind events
        self.tree.bind('<<TreeviewSelect>>', self._on_tree_select)
        self.tree.bind('<Double-Button-1>', self._on_double_click)
        
        # Context menu
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Restore", command=self._on_restore_selected)
        self.context_menu.add_command(label="Delete", command=self._on_delete_selected)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Open Folder", command=self._on_open_folder)
        
        self.tree.bind('<Button-3>', self._show_context_menu)
        
        # Sort state
        self.sort_column = 'timestamp'
        self.sort_reverse = True
    
    def set_snapshots(self, snapshots: List[Snapshot]):
        """
        Set the snapshots to display in the list.
        
        Args:
            snapshots: List of Snapshot objects
        """
        self.snapshots = snapshots
        self._refresh_tree()
    
    def _refresh_tree(self):
        """Refresh the tree view."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Sort snapshots
        sorted_snapshots = self._get_sorted_snapshots()
        
        # Add items
        for snapshot in sorted_snapshots:
            values = (
                f"Profile {snapshot.profile}",
                format_timestamp(snapshot.timestamp),
                get_time_ago(snapshot.timestamp),
                format_file_size(snapshot.size),
                "Yes" if snapshot.has_screenshot else "No"
            )
            
            # Store snapshot reference in item
            item_id = self.tree.insert('', tk.END, values=values)
            self.tree.set(item_id, '#0', str(snapshot.path))
    
    def _get_sorted_snapshots(self) -> List[Snapshot]:
        """Get snapshots sorted by current sort column."""
        if self.sort_column == 'profile':
            key_func = lambda s: s.profile
        elif self.sort_column == 'timestamp':
            key_func = lambda s: s.timestamp
        elif self.sort_column == 'time_ago':
            key_func = lambda s: s.timestamp
        elif self.sort_column == 'size':
            key_func = lambda s: s.size
        elif self.sort_column == 'screenshot':
            key_func = lambda s: s.has_screenshot
        else:
            key_func = lambda s: s.timestamp
        
        return sorted(self.snapshots, key=key_func, reverse=self.sort_reverse)
    
    def _sort_by(self, column: str):
        """
        Sort the list by the specified column.
        
        Args:
            column: Column name to sort by
        """
        # Toggle reverse if same column
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = False
        
        self._refresh_tree()
    
    def _on_tree_select(self, event):
        """Handle tree selection change."""
        selected_items = self.tree.selection()
        
        # Enable/disable delete button
        if selected_items:
            self.delete_button.config(state=tk.NORMAL)
        else:
            self.delete_button.config(state=tk.DISABLED)
        
        # Call select callback for single selection
        if len(selected_items) == 1 and self.on_select_callback:
            snapshot = self._get_snapshot_from_item(selected_items[0])
            if snapshot:
                try:
                    self.on_select_callback(snapshot)
                except Exception as e:
                    logger.error(f"Error in select callback: {e}")
    
    def _on_double_click(self, event):
        """Handle double-click on item."""
        selected_items = self.tree.selection()
        if len(selected_items) == 1:
            self._on_restore_selected()
    
    def _show_context_menu(self, event):
        """Show context menu."""
        # Select item under cursor
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)
    
    def _get_snapshot_from_item(self, item_id: str) -> Optional[Snapshot]:
        """
        Get snapshot object from tree item.
        
        Args:
            item_id: Tree item ID
            
        Returns:
            Snapshot object or None
        """
        try:
            path_str = self.tree.set(item_id, '#0')
            for snapshot in self.snapshots:
                if str(snapshot.path) == path_str:
                    return snapshot
        except Exception as e:
            logger.error(f"Failed to get snapshot from item: {e}")
        return None
    
    def get_selected_snapshots(self) -> List[Snapshot]:
        """
        Get currently selected snapshots.
        
        Returns:
            List of selected Snapshot objects
        """
        selected = []
        for item_id in self.tree.selection():
            snapshot = self._get_snapshot_from_item(item_id)
            if snapshot:
                selected.append(snapshot)
        return selected
    
    def _on_delete_selected(self):
        """Handle delete selected button click."""
        selected = self.get_selected_snapshots()
        
        if not selected:
            return
        
        # Confirm deletion
        count = len(selected)
        message = f"Delete {count} snapshot{'s' if count > 1 else ''}?"
        
        if not messagebox.askyesno("Confirm Delete", message, parent=self):
            return
        
        # Call delete callback
        if self.on_delete_callback:
            try:
                self.on_delete_callback(selected)
            except Exception as e:
                logger.error(f"Error in delete callback: {e}")
                messagebox.showerror(
                    "Delete Error",
                    f"Failed to delete snapshots: {e}",
                    parent=self
                )
    
    def _on_restore_selected(self):
        """Handle restore selected snapshot."""
        selected = self.get_selected_snapshots()
        
        if len(selected) != 1:
            messagebox.showwarning(
                "Restore Snapshot",
                "Please select exactly one snapshot to restore.",
                parent=self
            )
            return
        
        # This will be handled by the main window
        # Just trigger the select callback
        if self.on_select_callback:
            try:
                self.on_select_callback(selected[0])
            except Exception as e:
                logger.error(f"Error in select callback: {e}")
    
    def _on_open_folder(self):
        """Open the snapshot folder in file explorer."""
        selected = self.get_selected_snapshots()
        
        if len(selected) != 1:
            return
        
        import subprocess
        import sys
        
        try:
            path = selected[0].path
            if sys.platform == 'win32':
                subprocess.run(['explorer', str(path)])
            elif sys.platform == 'darwin':
                subprocess.run(['open', str(path)])
            else:
                subprocess.run(['xdg-open', str(path)])
        except Exception as e:
            logger.error(f"Failed to open folder: {e}")
            messagebox.showerror(
                "Open Folder Error",
                f"Failed to open folder: {e}",
                parent=self
            )
    
    def _on_refresh(self):
        """Handle refresh button click."""
        self._refresh_tree()
    
    def set_on_select_callback(self, callback: Callable):
        """
        Set callback to be called when a snapshot is selected.
        
        Args:
            callback: Function that takes a Snapshot object as parameter
        """
        self.on_select_callback = callback
    
    def set_on_delete_callback(self, callback: Callable):
        """
        Set callback to be called when snapshots should be deleted.
        
        Args:
            callback: Function that takes a list of Snapshot objects as parameter
        """
        self.on_delete_callback = callback
    
    def clear(self):
        """Clear all snapshots from the list."""
        self.snapshots.clear()
        self._refresh_tree()
    
    def refresh(self):
        """Refresh the list display."""
        self._refresh_tree()