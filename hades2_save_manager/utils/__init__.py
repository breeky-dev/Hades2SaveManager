"""Utility modules for Hades II Save Manager."""

from .file_ops import (
    safe_copy_file,
    safe_copy_files,
    safe_delete_file,
    safe_delete_directory,
    get_file_size,
    get_directory_size,
    format_file_size,
    find_profile_files,
    extract_profile_number
)

from .time_helpers import (
    get_timestamp,
    format_timestamp,
    get_snapshot_folder_name,
    parse_snapshot_folder_name,
    get_time_ago,
    should_create_new_snapshot
)

__all__ = [
    'safe_copy_file',
    'safe_copy_files',
    'safe_delete_file',
    'safe_delete_directory',
    'get_file_size',
    'get_directory_size',
    'format_file_size',
    'find_profile_files',
    'extract_profile_number',
    'get_timestamp',
    'format_timestamp',
    'get_snapshot_folder_name',
    'parse_snapshot_folder_name',
    'get_time_ago',
    'should_create_new_snapshot'
]