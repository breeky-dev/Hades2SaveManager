# Hades II Save Manager

A Python desktop tool that captures, browses, and restores snapshots of Hades II save files.

## Features

- **Auto-snapshot** - Automatically captures save snapshots when entering new rooms
- **Screenshot capture** - Takes screenshots alongside each snapshot for visual reference
- **Snapshot browser** - Browse snapshots with a carousel widget and detailed list view
- **Manual controls** - Toggle auto-snapshot on/off and take manual snapshots
- **Profile awareness** - Supports all 4 Hades II profiles with separate snapshot storage
- **Safe restore** - Checks if game is running and creates backups before restoring

## Installation

### Prerequisites

- Python 3.8 or higher
- Windows (tested), macOS, or Linux

### Setup

1. Clone or download this repository

2. Create a virtual environment:
```bash
python -m venv .venv
```

3. Activate the virtual environment:
   - Windows: `.venv\Scripts\activate`
   - macOS/Linux: `source .venv/bin/activate`

4. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Running the Application

```bash
python -m hades2_save_manager.main
```

Or from the project root:
```bash
python -m hades2_save_manager
```

### First-Time Setup

1. Launch the application
2. Go to **File → Settings**
3. Configure:
   - **Game Save Folder**: Location of Hades II save files (usually `%USERPROFILE%/Saved Games/Hades II`)
   - **Snapshot Storage Folder**: Where snapshots will be stored
   - **Auto-Snapshot**: Enable/disable automatic snapshots
   - **Snapshot Threshold**: Minimum seconds between snapshots (default: 5)

### Using the Application

#### Auto-Snapshot Mode
- Enable "Auto-Snapshot" in the toolbar
- The application will automatically create snapshots when save files change
- Snapshots within the threshold time are merged (same room)

#### Manual Snapshots
- Click "Take Snapshot" button to create a snapshot immediately
- Or use **Snapshot → Take Snapshot Now** menu

#### Browsing Snapshots
- Use the carousel at the top to quickly browse recent snapshots
- Use the list view below for detailed information and sorting
- Select a profile from the dropdown to filter snapshots

#### Restoring Snapshots
1. Select a snapshot from the carousel or list
2. Click "Restore Selected" button
3. Confirm the restore operation
4. The application will:
   - Check if Hades II is running (warns if it is)
   - Create a backup of current save files
   - Restore the selected snapshot
   - Notify when complete

#### Deleting Snapshots
- Select one or more snapshots in the list view
- Click "Delete Selected" button
- Or right-click and select "Delete" from context menu

## Building Executable

To create a standalone executable:

```bash
pip install pyinstaller
pyinstaller --onefile --noconsole --name "Hades2SaveManager" hades2_save_manager/main.py
```

The executable will be in the `dist/` folder.

## Project Structure

```
hades2_save_manager/
├── gui/                    # Tkinter windows & widgets
│   ├── main_window.py      # Main application window
│   ├── snapshot_carousel.py # Carousel widget for thumbnails
│   ├── snapshot_list.py    # List view with sorting
│   └── settings_dialog.py  # Settings configuration dialog
├── services/
│   ├── snapshot_watcher.py # File system watcher
│   ├── snapshot_manager.py # Snapshot creation/deletion/restore
│   └── screen_capture.py   # Screenshot functionality
├── utils/
│   ├── file_ops.py         # File operation helpers
│   └── time_helpers.py     # Time/date utilities
└── main.py                 # Application entry point
```

## Configuration

Settings are stored in `%USERPROFILE%/.hades2_save_manager/settings.json`

Default settings:
```json
{
  "save_dir": "%USERPROFILE%/Saved Games/Hades II",
  "snapshot_dir": "%USERPROFILE%/Documents/Hades2SaveManager/Snapshots",
  "auto_snapshot_enabled": true,
  "snapshot_threshold": 5.0,
  "check_game_running": true
}
```

## Logs

Application logs are stored in `%USERPROFILE%/.hades2_save_manager/app.log`

## Troubleshooting

### Auto-snapshot not working
- Ensure the game save folder path is correct in settings
- Check that the watchdog library is installed
- Review logs for errors

### Screenshots not captured
- Ensure Pillow and pyautogui are installed
- Check that you have screen capture permissions (macOS)

### Cannot restore snapshot
- Make sure Hades II is closed before restoring
- Check that you have write permissions to the save folder
- Review logs for specific errors

## Dependencies

- **watchdog** - File system monitoring
- **Pillow** - Image processing
- **pyautogui** - Screenshot capture
- **psutil** - Process detection

## License

This project is provided as-is for personal use.

## Disclaimer

This tool modifies game save files. Always keep backups of your important saves. The authors are not responsible for any data loss.