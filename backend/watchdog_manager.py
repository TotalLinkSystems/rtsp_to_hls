import os
import time
import threading
import logging
import signal
import subprocess
from datetime import datetime

logger = logging.getLogger("stream_api")

# Keep track of active watchdogs
active_watchdogs = {}

# How long to wait before considering the stream "stuck"
WATCHDOG_TIMEOUT = 120  # seconds

def _get_latest_mod_time(folder_path: str) -> float:
    """Return the most recent modification time of any file in folder."""
    latest_time = 0
    for root, _, files in os.walk(folder_path):
        for f in files:
            path = os.path.join(root, f)
            try:
                mtime = os.path.getmtime(path)
                latest_time = max(latest_time, mtime)
            except FileNotFoundError:
                continue
    return latest_time

def _monitor_folder(folder_path: str, pid: int, restart_callback):
    """Monitor a folder and restart stream if stale for too long."""
    logger.info(f"Watchdog started for PID {pid}, folder: {folder_path}")
    last_active = time.time()

    while pid in active_watchdogs:
        try:
            latest_mod = _get_latest_mod_time(folder_path)
            now = time.time()

            # If no updates in 2 minutes → restart stream
            if latest_mod > 0 and (now - latest_mod) > WATCHDOG_TIMEOUT:
                logger.warning(f"No updates in {WATCHDOG_TIMEOUT}s for {folder_path}. Restarting PID {pid}...")
                restart_callback(pid)
                break

            time.sleep(10)  # check every 10 seconds
        except Exception as e:
            logger.error(f"Watchdog error for PID {pid}: {e}")
            time.sleep(10)

    logger.info(f"Watchdog stopped for PID {pid}")

def start_watchdog(pid: int, folder_path: str, restart_callback):
    """Start a watchdog thread for a specific stream."""
    if pid in active_watchdogs:
        logger.warning(f"Watchdog already running for PID {pid}")
        return

    thread = threading.Thread(target=_monitor_folder, args=(folder_path, pid, restart_callback), daemon=True)
    active_watchdogs[pid] = thread
    thread.start()

def stop_watchdog(pid: int):
    """Stop the watchdog for a given PID."""
    if pid in active_watchdogs:
        logger.info(f"Stopping watchdog for PID {pid}")
        del active_watchdogs[pid]
