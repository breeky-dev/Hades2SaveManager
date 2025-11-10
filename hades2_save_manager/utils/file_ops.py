"""File operation utilities for safe copying and deletion."""

import os
import shutil
from pathlib import Path
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


def safe_copy_file(src: Path, dst: Path) -> bool:
    """
    Safely copy a file from src to dst, creating parent directories if needed.
    
    Args:
        src: Source file path
        dst: Destination file path
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create parent directory if it doesn't exist
        dst.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy the file
        shutil.copy2(src, dst)
        logger.info(f"Copied {src} to {dst}")
        return True
    except Exception as e:
        logger.error(f"Failed to copy {src} to {dst}: {e}")
        return False


def safe_copy_files(src_files: List[Path], dst_dir: Path) -> int:
    """
    Copy multiple files to a destination directory.
    
    Args:
        src_files: List of source file paths
        dst_dir: Destination directory
        
    Returns:
        Number of files successfully copied
    """
    dst_dir.mkdir(parents=True, exist_ok=True)
    success_count = 0
    
    for src_file in src_files:
        if src_file.exists():
            dst_file = dst_dir / src_file.name
            if safe_copy_file(src_file, dst_file):
                success_count += 1
    
    return success_count


def safe_delete_file(file_path: Path) -> bool:
    """
    Safely delete a file.
    
    Args:
        file_path: Path to file to delete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted {file_path}")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to delete {file_path}: {e}")
        return False


def safe_delete_directory(dir_path: Path) -> bool:
    """
    Safely delete a directory and all its contents.
    
    Args:
        dir_path: Path to directory to delete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if dir_path.exists() and dir_path.is_dir():
            shutil.rmtree(dir_path)
            logger.info(f"Deleted directory {dir_path}")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to delete directory {dir_path}: {e}")
        return False


def get_file_size(file_path: Path) -> int:
    """
    Get file size in bytes.
    
    Args:
        file_path: Path to file
        
    Returns:
        File size in bytes, or 0 if file doesn't exist
    """
    try:
        if file_path.exists():
            return file_path.stat().st_size
        return 0
    except Exception as e:
        logger.error(f"Failed to get size of {file_path}: {e}")
        return 0


def get_directory_size(dir_path: Path) -> int:
    """
    Get total size of all files in a directory.
    
    Args:
        dir_path: Path to directory
        
    Returns:
        Total size in bytes
    """
    total_size = 0
    try:
        for file_path in dir_path.rglob('*'):
            if file_path.is_file():
                total_size += get_file_size(file_path)
    except Exception as e:
        logger.error(f"Failed to calculate directory size for {dir_path}: {e}")
    
    return total_size


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def find_profile_files(save_dir: Path, profile_num: int) -> List[Path]:
    """
    Find all save files for a specific profile.
    
    Args:
        save_dir: Game save directory
        profile_num: Profile number (1-4)
        
    Returns:
        List of file paths for the profile
    """
    files = []
    try:
        if not save_dir.exists():
            return files
        
        # Main save file
        main_save = save_dir / f"Profile{profile_num}.sav"
        if main_save.exists():
            files.append(main_save)
        
        # Temp save file
        temp_save = save_dir / f"Profile{profile_num}_Temp.sav"
        if temp_save.exists():
            files.append(temp_save)
        
        # Backup files
        for backup_file in save_dir.glob(f"Profile{profile_num}.sav.bak*"):
            files.append(backup_file)
    
    except Exception as e:
        logger.error(f"Failed to find profile files: {e}")
    
    return files


def extract_profile_number(file_path: Path) -> Optional[int]:
    """
    Extract profile number from a save file path.
    
    Args:
        file_path: Path to save file
        
    Returns:
        Profile number (1-4) or None if not found
    """
    try:
        filename = file_path.name
        # Look for Profile{N} pattern
        if filename.startswith("Profile"):
            # Extract number after "Profile"
            num_str = ""
            for char in filename[7:]:
                if char.isdigit():
                    num_str += char
                else:
                    break
            
            if num_str:
                profile_num = int(num_str)
                if 1 <= profile_num <= 4:
                    return profile_num
    except Exception as e:
        logger.error(f"Failed to extract profile number from {file_path}: {e}")
    
    return None