import psutil
import time
import sys
import os
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "gui"))

from identifier import get_drive_serial, eject_drive
from db import init_db, record_drive_connection, is_trusted, set_trusted, get_setting, set_setting
from popup import ask_allow_or_block, ask_scan_now, show_scan_result
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
        print(f"    Trusted drive — allowed silently.")
        return

    print(f"    Unknown drive — asking user...")
    allowed = ask_allow_or_block(drive_letter, serial)

    if allowed:
        set_trusted(serial, 1)
        print(f"    User ALLOWED this drive. Marked as trusted.")

        if get_setting("auto_scan_prompt", "1") == "1":
            wants_scan = ask_scan_now(drive_letter)
            if wants_scan:
                print(f"    Scanning {drive_letter} for viruses...")
                scan_result = scan_drive_for_viruses(drive_letter)
                show_scan_result(scan_result)
                print(f"    Scan finished.")
            else:
                print(f"    User skipped scanning.")
        else:
            print(f"    Scan prompt disabled in Settings.")
    else:
        set_trusted(serial, 0)
        if get_setting("eject_on_block", "1") == "1":
            print(f"    User BLOCKED this drive. Ejecting...")
            eject_drive(drive_letter)
            print(f"    Drive ejected.")
        else:
            print(f"    User BLOCKED this drive. (Auto-eject disabled in Settings)")

def start_watching():
    init_db()
    print("USB-Sentinel watching for drives... (Ctrl+C to stop)")
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

        for drive in removed:
            print(f"[-] Drive removed: {drive}")

        old_drives = new_drives

if __name__ == "__main__":
    start_watching()