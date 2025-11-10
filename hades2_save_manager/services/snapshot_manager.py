"""Snapshot manager for creating, deleting, and restoring save snapshots."""

from pathlib import Path
from typing import List, Optional, Dict
import logging
import json
from dataclasses import dataclass, asdict

from hades2_save_manager.utils import (
    safe_copy_files,
    safe_delete_directory,
    get_directory_size,
    format_file_size,
    find_profile_files,
    get_timestamp,
    get_snapshot_folder_name,
    parse_snapshot_folder_name,
    format_timestamp
)
from hades2_save_manager.services.screen_capture import ScreenCapture

logger = logging.getLogger(__name__)


@dataclass
class Snapshot:
    """Represents a save snapshot."""
    path: Path
    profile: int
    timestamp: float
    size: int
    has_screenshot: bool
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'path': str(self.path),
            'profile': self.profile,
            'timestamp': self.timestamp,
            'size': self.size,
            'has_screenshot': self.has_screenshot
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Snapshot':
        """Create from dictionary."""
        return cls(
            path=Path(data['path']),
            profile=data['profile'],
            timestamp=data['timestamp'],
            size=data['size'],
            has_screenshot=data['has_screenshot']
        )


class SnapshotManager:
    """Manages save file snapshots."""
    
    def __init__(self, save_dir: Path, snapshot_dir: Path):
        """
        Initialize the snapshot manager.
        
        Args:
            save_dir: Directory containing game save files
            snapshot_dir: Directory where snapshots will be stored
        """
        self.save_dir = Path(save_dir)
        self.snapshot_dir = Path(snapshot_dir)
        self.screen_capture = ScreenCapture()
        self.last_snapshot_time: Dict[int, float] = {}  # Per-profile timestamps
        
        # Create snapshot directory if it doesn't exist
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"SnapshotManager initialized: save_dir={save_dir}, snapshot_dir={snapshot_dir}")
    
    def create_snapshot(self, profile_num: int, take_screenshot: bool = True,
                       overwrite_last: bool = False) -> Optional[Snapshot]:
        """
        Create a new snapshot for the specified profile.
        
        Args:
            profile_num: Profile number (1-4)
            take_screenshot: Whether to capture a screenshot
            overwrite_last: If True, overwrite the last snapshot instead of creating new
            
        Returns:
            Snapshot object if successful, None otherwise
        """
        try:
            # Find all save files for this profile
            save_files = find_profile_files(self.save_dir, profile_num)
            
            if not save_files:
                logger.warning(f"No save files found for profile {profile_num}")
                return None
            
            # Determine snapshot folder
            if overwrite_last:
                # Find the most recent snapshot for this profile
                snapshots = self.list_snapshots(profile_num)
                if snapshots:
                    snapshot_folder = snapshots[0].path
                    logger.info(f"Overwriting last snapshot: {snapshot_folder}")
                else:
                    # No previous snapshot, create new
                    overwrite_last = False
            
            if not overwrite_last:
                # Create new snapshot folder
                folder_name = get_snapshot_folder_name(profile_num)
                snapshot_folder = self.snapshot_dir / f"Profile{profile_num}" / folder_name
                snapshot_folder.mkdir(parents=True, exist_ok=True)
                logger.info(f"Creating new snapshot: {snapshot_folder}")
            
            # Copy save files
            copied_count = safe_copy_files(save_files, snapshot_folder)
            
            if copied_count == 0:
                logger.error("Failed to copy any save files")
                return None
            
            # Capture screenshot
            has_screenshot = False
            if take_screenshot:
                screenshot_path = snapshot_folder / "snapshot.png"
                has_screenshot = self.screen_capture.capture_and_resize(
                    screenshot_path, max_width=1920, max_height=1080
                )
            
            # Create metadata file
            metadata = {
                'profile': profile_num,
                'timestamp': get_timestamp(),
                'files_copied': copied_count,
                'has_screenshot': has_screenshot
            }
            
            metadata_path = snapshot_folder / "metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Update last snapshot time
            self.last_snapshot_time[profile_num] = metadata['timestamp']
            
            # Calculate size
            size = get_directory_size(snapshot_folder)
            
            snapshot = Snapshot(
                path=snapshot_folder,
                profile=profile_num,
                timestamp=metadata['timestamp'],
                size=size,
                has_screenshot=has_screenshot
            )
            
            logger.info(f"Snapshot created successfully: {snapshot_folder}")
            return snapshot
            
        except Exception as e:
            logger.error(f"Failed to create snapshot: {e}")
            return None
    
    def list_snapshots(self, profile_num: Optional[int] = None) -> List[Snapshot]:
        """
        List all snapshots, optionally filtered by profile.
        
        Args:
            profile_num: Profile number to filter by, or None for all profiles
            
        Returns:
            List of Snapshot objects, sorted by timestamp (newest first)
        """
        snapshots = []
        
        try:
            # Determine which profile directories to scan
            if profile_num is not None:
                profile_dirs = [self.snapshot_dir / f"Profile{profile_num}"]
            else:
                profile_dirs = [self.snapshot_dir / f"Profile{i}" for i in range(1, 5)]
            
            for profile_dir in profile_dirs:
                if not profile_dir.exists():
                    continue
                
                # Scan for snapshot folders
                for snapshot_folder in profile_dir.iterdir():
                    if not snapshot_folder.is_dir():
                        continue
                    
                    # Try to load metadata
                    metadata_path = snapshot_folder / "metadata.json"
                    if metadata_path.exists():
                        try:
                            with open(metadata_path, 'r') as f:
                                metadata = json.load(f)
                            
                            snapshot = Snapshot(
                                path=snapshot_folder,
                                profile=metadata['profile'],
                                timestamp=metadata['timestamp'],
                                size=get_directory_size(snapshot_folder),
                                has_screenshot=metadata.get('has_screenshot', False)
                            )
                            snapshots.append(snapshot)
                        except Exception as e:
                            logger.error(f"Failed to load metadata from {metadata_path}: {e}")
                    else:
                        # Try to parse from folder name
                        parsed = parse_snapshot_folder_name(snapshot_folder.name)
                        if parsed:
                            has_screenshot = (snapshot_folder / "snapshot.png").exists()
                            snapshot = Snapshot(
                                path=snapshot_folder,
                                profile=parsed['profile'],
                                timestamp=parsed['timestamp'],
                                size=get_directory_size(snapshot_folder),
                                has_screenshot=has_screenshot
                            )
                            snapshots.append(snapshot)
            
            # Sort by timestamp (newest first)
            snapshots.sort(key=lambda s: s.timestamp, reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to list snapshots: {e}")
        
        return snapshots
    
    def delete_snapshot(self, snapshot: Snapshot) -> bool:
        """
        Delete a snapshot.
        
        Args:
            snapshot: Snapshot to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            return safe_delete_directory(snapshot.path)
        except Exception as e:
            logger.error(f"Failed to delete snapshot {snapshot.path}: {e}")
            return False
    
    def delete_snapshots(self, snapshots: List[Snapshot]) -> int:
        """
        Delete multiple snapshots.
        
        Args:
            snapshots: List of snapshots to delete
            
        Returns:
            Number of snapshots successfully deleted
        """
        deleted_count = 0
        for snapshot in snapshots:
            if self.delete_snapshot(snapshot):
                deleted_count += 1
        return deleted_count
    
    def restore_snapshot(self, snapshot: Snapshot, backup_current: bool = True) -> bool:
        """
        Restore a snapshot by copying its files to the save directory.
        
        Args:
            snapshot: Snapshot to restore
            backup_current: Whether to backup current save files first
            
        Returns:
            True if successful, False otherwise
        """
        try:
            profile_num = snapshot.profile
            
            # Backup current save files if requested
            if backup_current:
                current_files = find_profile_files(self.save_dir, profile_num)
                if current_files:
                    backup_folder = self.snapshot_dir / "live_backup" / f"Profile{profile_num}"
                    backup_folder.mkdir(parents=True, exist_ok=True)
                    
                    # Clear old backup
                    for old_file in backup_folder.iterdir():
                        if old_file.is_file():
                            old_file.unlink()
                    
                    # Copy current files to backup
                    safe_copy_files(current_files, backup_folder)
                    logger.info(f"Backed up current save files to {backup_folder}")
            
            # Find all save files in the snapshot
            snapshot_files = []
            for file_path in snapshot.path.iterdir():
                if file_path.suffix in ['.sav', '.bak'] or file_path.name.endswith('_Temp.sav'):
                    snapshot_files.append(file_path)
            
            if not snapshot_files:
                logger.error(f"No save files found in snapshot {snapshot.path}")
                return False
            
            # Copy snapshot files to save directory
            copied_count = safe_copy_files(snapshot_files, self.save_dir)
            
            if copied_count == 0:
                logger.error("Failed to copy any snapshot files")
                return False
            
            logger.info(f"Restored {copied_count} files from snapshot {snapshot.path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore snapshot: {e}")
            return False
    
    def get_last_snapshot_time(self, profile_num: int) -> Optional[float]:
        """
        Get the timestamp of the last snapshot for a profile.
        
        Args:
            profile_num: Profile number
            
        Returns:
            Timestamp or None if no snapshots exist
        """
        return self.last_snapshot_time.get(profile_num)
    
    def get_snapshot_info(self, snapshot: Snapshot) -> dict:
        """
        Get detailed information about a snapshot.
        
        Args:
            snapshot: Snapshot to get info for
            
        Returns:
            Dictionary with snapshot details
        """
        return {
            'path': str(snapshot.path),
            'profile': snapshot.profile,
            'timestamp': snapshot.timestamp,
            'formatted_time': format_timestamp(snapshot.timestamp),
            'size': snapshot.size,
            'formatted_size': format_file_size(snapshot.size),
            'has_screenshot': snapshot.has_screenshot,
            'screenshot_path': str(snapshot.path / "snapshot.png") if snapshot.has_screenshot else None
        }