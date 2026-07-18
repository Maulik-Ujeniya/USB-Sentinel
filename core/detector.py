import psutil
import time
from identifier import get_drive_serial
from db import init_db, record_drive_connection, is_trusted, set_trusted

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "gui"))
from popup import ask_allow_or_block

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
    else:
        set_trusted(serial, 0)
        print(f"    User BLOCKED this drive.")

def start_watching():
    init_db()
    print("USB-Sentinel watching for drives... (Ctrl+C to stop)")
    old_drives = get_connected_drives()

    while True:
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