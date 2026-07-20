import psutil
import time
import sys
import os
from datetime import datetime

# Ensure core/ is on the import path
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "gui"))

from identifier import get_drive_serial, eject_drive
from db import init_db, record_drive_connection, is_trusted, set_trusted, get_setting, set_setting, log_activity
from popup import ask_allow_or_block, ask_scan_now, show_scan_result, show_eject_notification
from scanner import scan_drive_for_viruses

def get_connected_drives():
    drives = []
    for d in psutil.disk_partitions():
        if 'removable' in d.opts or d.fstype != '':
            drives.append(d.device)
    return set(drives)

def handle_new_drive(drive_letter, serial):
    already_known = is_trusted(serial)
    record_drive_connection(serial, drive_letter)

    if already_known:
        print(f"    [OK] Trusted drive {drive_letter} ({serial}) allowed silently.")
        log_activity("drive_connected", f"Trusted drive {drive_letter} (serial: {serial}) connected")
        return

    print(f"    [ALERT] Unknown drive {drive_letter} ({serial}) detected — prompting user popup...")
    log_activity("drive_connected", f"Unknown drive {drive_letter} (serial: {serial}) detected")

    # Show top-most desktop popup window with audio sound alert
    allowed = ask_allow_or_block(drive_letter, serial)

    if allowed:
        set_trusted(serial, 1)
        print(f"    [ALLOW] User ALLOWED drive {drive_letter}. Marked as trusted.")
        log_activity("drive_allowed", f"User allowed drive {drive_letter} (serial: {serial})")

        if get_setting("auto_scan_prompt", "1") == "1":
            wants_scan = ask_scan_now(drive_letter)
            if wants_scan:
                print(f"    Scanning {drive_letter} for threats...")
                log_activity("virus_scan_started", f"Heuristic scan started on {drive_letter}")
                scan_result = scan_drive_for_viruses(drive_letter)
                show_scan_result(scan_result)
                print(f"    Scan finished.")
                if scan_result.get("infected_count", 0) > 0:
                    log_activity("threats_found", f"Scan of {drive_letter}: {scan_result['infected_count']} threats found")
                else:
                    log_activity("virus_scan_complete", f"Scan of {drive_letter} complete: clean")
            else:
                print(f"    User skipped prompt scan.")
    else:
        set_trusted(serial, 0)
        log_activity("drive_blocked", f"User BLOCKED drive {drive_letter} (serial: {serial})")
        print(f"    [BLOCK] User BLOCKED drive {drive_letter}. Triggering safe auto-eject...")
        eject_drive(drive_letter)
        print(f"    [EJECT] Drive {drive_letter} ejected.")
        log_activity("drive_ejected", f"Blocked drive {drive_letter} auto-ejected")
        show_eject_notification(drive_letter)

def start_watching():
    init_db()
    print("USB-Sentinel watching for drives... (Ctrl+C to stop)")
    log_activity("protection_started", "USB protection watcher service running")
    old_drives = get_connected_drives()

    while True:
        set_setting("last_heartbeat", datetime.now().isoformat())
        time.sleep(2)
        new_drives = get_connected_drives()
        added = new_drives - old_drives
        removed = old_drives - new_drives

        for drive in added:
            print(f"[+] Drive inserted: {drive}")
            serial = get_drive_serial(drive)
            if serial:
                handle_new_drive(drive, serial)
            else:
                print("    Could not read serial number")
                log_activity("drive_connected", f"Drive {drive} connected (serial unreadable)")

        for drive in removed:
            print(f"[-] Drive removed: {drive}")
            log_activity("drive_removed", f"Drive {drive} disconnected")

        old_drives = new_drives

if __name__ == "__main__":
    start_watching()