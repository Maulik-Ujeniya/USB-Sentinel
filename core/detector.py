import psutil
import time

def get_connected_drives():
    drives = []
    for d in psutil.disk_partitions():
        if 'removable' in d.opts or d.fstype != '':
            drives.append(d.device)
    return set(drives)

def start_watching():
    print("USB-Sentinel watching for drives... (Ctrl+C to stop)")
    old_drives = get_connected_drives()

    while True:
        time.sleep(2)
        new_drives = get_connected_drives()

        added = new_drives - old_drives
        removed = old_drives - new_drives

        for drive in added:
            print(f"[+] Drive inserted: {drive}")

        for drive in removed:
            print(f"[-] Drive removed: {drive}")

        old_drives = new_drives

if __name__ == "__main__":
    start_watching()