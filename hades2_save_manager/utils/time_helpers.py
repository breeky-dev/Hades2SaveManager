"""Time and date utilities for snapshot management."""

from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def get_timestamp() -> float:
    """
    Get current timestamp in seconds.
    
    Returns:
        Current time as float (seconds since epoch)
    """
    return datetime.now().timestamp()


def format_timestamp(timestamp: float, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format a timestamp to a readable string.
    
    Args:
        timestamp: Unix timestamp in seconds
        format_str: strftime format string
        
    Returns:
        Formatted date/time string
    """
    try:
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime(format_str)
    except Exception as e:
        logger.error(f"Failed to format timestamp {timestamp}: {e}")
        return "Unknown"


def get_snapshot_folder_name(profile_num: int) -> str:
    """
    Generate a snapshot folder name with current timestamp and profile.
    
    Args:
        profile_num: Profile number (1-4)
        
    Returns:
        Folder name in format: YYYY-MM-DD_HH-MM-SS_profileN
    """
    now = datetime.now()
    return now.strftime(f"%Y-%m-%d_%H-%M-%S_profile{profile_num}")


def parse_snapshot_folder_name(folder_name: str) -> Optional[dict]:
    """
    Parse a snapshot folder name to extract timestamp and profile.
    
    Args:
        folder_name: Folder name in format YYYY-MM-DD_HH-MM-SS_profileN
        
    Returns:
        Dict with 'timestamp' (float) and 'profile' (int), or None if invalid
    """
    try:
        # Expected format: YYYY-MM-DD_HH-MM-SS_profileN
        parts = folder_name.split('_')
        if len(parts) < 4:
            return None
        
        # Extract date and time
        date_str = parts[0]  # YYYY-MM-DD
        time_str = parts[1]  # HH-MM-SS
        
        # Extract profile number
        profile_str = parts[2]  # profileN
        if not profile_str.startswith('profile'):
            return None
        
        profile_num = int(profile_str[7:])
        
        # Parse datetime
        datetime_str = f"{date_str} {time_str.replace('-', ':')}"
        dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        
        return {
            'timestamp': dt.timestamp(),
            'profile': profile_num,
            'datetime': dt
        }
    except Exception as e:
        logger.error(f"Failed to parse snapshot folder name '{folder_name}': {e}")
        return None


def get_time_ago(timestamp: float) -> str:
    """
    Get human-readable time difference from now.
    
    Args:
        timestamp: Unix timestamp in seconds
        
    Returns:
        String like "5 minutes ago", "2 hours ago", etc.
    """
    try:
        now = datetime.now()
        dt = datetime.fromtimestamp(timestamp)
        diff = now - dt
        
        seconds = diff.total_seconds()
        
        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif seconds < 604800:
            days = int(seconds / 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"
        else:
            weeks = int(seconds / 604800)
            return f"{weeks} week{'s' if weeks != 1 else ''} ago"
    except Exception as e:
        logger.error(f"Failed to calculate time ago for {timestamp}: {e}")
        return "unknown"


def should_create_new_snapshot(last_snapshot_time: Optional[float], 
                               threshold_seconds: float = 5.0) -> bool:
    """
    Determine if a new snapshot should be created based on time threshold.
    
    Args:
        last_snapshot_time: Timestamp of last snapshot, or None
        threshold_seconds: Minimum seconds between snapshots
        
    Returns:
        True if new snapshot should be created
    """
    if last_snapshot_time is None:
        return True
    
    current_time = get_timestamp()
    time_diff = current_time - last_snapshot_time
    
    return time_diff > threshold_seconds