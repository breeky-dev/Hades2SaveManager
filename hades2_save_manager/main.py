"""Main entry point for Hades II Save Manager."""

import sys
import logging
from pathlib import Path

# Configure logging
log_dir = Path.home() / ".hades2_save_manager"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "app.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main application entry point."""
    try:
        logger.info("Starting Hades II Save Manager")
        
        # Import GUI after logging is configured
        from hades2_save_manager.gui import MainWindow
        
        # Create and run application
        app = MainWindow()
        app.mainloop()
        
        logger.info("Application closed normally")
        
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        
        # Try to show error dialog
        try:
            import tkinter as tk
            from tkinter import messagebox
            
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "Fatal Error",
                f"An error occurred:\n\n{e}\n\nCheck the log file at:\n{log_file}"
            )
        except:
            pass
        
        sys.exit(1)


if __name__ == "__main__":
    main()