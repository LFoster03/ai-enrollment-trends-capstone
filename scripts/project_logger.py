"""
project_logger.py

A tiny logging utility for this capstone project. Import this in any
script and call log_event() to automatically append a timestamped
entry to project.log at the repo root.

Usage:
    from project_logger import log_event

    log_event("Cleaned ISU Fall 2025 file: 8 programs matched")
"""

import datetime
import os

# project.log will live at the repo root, one level up from /scripts/
LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "project.log")


def log_event(message: str, level: str = "INFO"):
    """Append a timestamped entry to project.log.

    Args:
        message: what happened (e.g. "Cleaned ISU Fall 2025 file")
        level: INFO, WARNING, or ERROR -- just a visual tag, not
               enforced, so use whatever makes sense.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] [{level}] {message}\n"

    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(entry)

    # Also print to console so you see it in real time while running scripts
    print(entry.strip())