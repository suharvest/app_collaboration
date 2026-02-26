"""
Entry point for PyInstaller bundled executable.
This module avoids relative import issues by using absolute imports.
"""

import os
import sys

# Ensure the package can be found
if getattr(sys, "frozen", False):
    # Running as compiled executable
    # Add the executable directory to path
    app_path = os.path.dirname(sys.executable)
    if app_path not in sys.path:
        sys.path.insert(0, app_path)

# Parse --solutions-dir early, before importing main (which imports settings)
# This ensures the environment variable is set before settings are initialized
if "--solutions-dir" in sys.argv:
    try:
        idx = sys.argv.index("--solutions-dir")
        if idx + 1 < len(sys.argv):
            solutions_dir = sys.argv[idx + 1]
            os.environ["PS_SOLUTIONS_DIR"] = solutions_dir
            print(f"Setting PS_SOLUTIONS_DIR={solutions_dir}")
    except (ValueError, IndexError):
        pass

# Parse --frontend-dir early (same pattern)
if "--frontend-dir" in sys.argv:
    try:
        idx = sys.argv.index("--frontend-dir")
        if idx + 1 < len(sys.argv):
            frontend_dir = sys.argv[idx + 1]
            os.environ["PS_FRONTEND_DIR"] = frontend_dir
            print(f"Setting PS_FRONTEND_DIR={frontend_dir}")
    except (ValueError, IndexError):
        pass

# Now import and run
from provisioning_station.main import main

if __name__ == "__main__":
    main()
