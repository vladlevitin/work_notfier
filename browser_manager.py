"""Edge browser profile and process management."""

from __future__ import annotations

import os
import re
import stat
import subprocess
import time
from pathlib import Path


def get_edge_pids_for_user_data_dir(user_data_dir: Path) -> list[int]:
    """Get all Edge process IDs using a specific user data directory."""
    safe_user_data = re.escape(str(user_data_dir)).replace("'", "''")
    ps_command = (
        "Get-CimInstance Win32_Process -Filter \"Name = 'msedge.exe'\" | "
        f"Where-Object {{ $_.CommandLine -match '--user-data-dir=\"?{safe_user_data}\"?' }} | "
        "Select-Object -ExpandProperty ProcessId"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_command],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return []

    pids: list[int] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.isdigit():
            pids.append(int(line))
    return pids


def cleanup_profile_lock_files(user_data_dir: Path) -> bool:
    """Remove lock files that prevent Edge from launching."""
    lock_names = {"DevToolsActivePort", "SingletonLock", "SingletonCookie", "SingletonSocket"}
    removed = 0
    failed = False

    for root, _, files in os.walk(user_data_dir):
        for name in files:
            if name not in lock_names:
                continue
            path = Path(root) / name
            try:
                try:
                    os.chmod(path, stat.S_IWRITE)
                except OSError:
                    pass
                path.unlink()
                removed += 1
            except OSError:
                print("Could not remove lock file:", path)
                failed = True

    if removed:
        print(f"Removed {removed} lock files.")
    return not failed


def prepare_browser_profile(user_data_dir: Path) -> bool:
    """
    Prepare browser profile by cleaning up processes and lock files.
    Returns True if successful, False otherwise.
    """
    user_data_dir.mkdir(parents=True, exist_ok=True)
    print("Using Edge profile folder:", user_data_dir)

    # Kill any Edge processes using this profile
    for pid in get_edge_pids_for_user_data_dir(user_data_dir):
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], check=False)

    # Wait for processes to exit
    for _ in range(10):
        if not get_edge_pids_for_user_data_dir(user_data_dir):
            break
        time.sleep(0.5)

    # Clean up lock files
    if not cleanup_profile_lock_files(user_data_dir):
        print("Close all Edge windows and try again.")
        return False

    # Verify no processes are still running
    if get_edge_pids_for_user_data_dir(user_data_dir):
        print("Edge is still running with this profile folder.")
        print("Close all Edge windows and try again.")
        return False

    # Final cleanup attempt
    for _ in range(5):
        if cleanup_profile_lock_files(user_data_dir):
            break
        time.sleep(0.5)

    return True


def get_edge_binary_path() -> Path:
    """Get the path to the Edge browser executable."""
    candidates = [
        Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
    ]
    return next((path for path in candidates if path.exists()), candidates[-1])
