import subprocess
import platform
import os
import time
import json
from db import set_setting

CLAMSCAN_PATH_WINDOWS = r"C:\Program Files\ClamAV\clamscan.exe"
MAX_SCAN_SECONDS = 3600

def get_clamscan_path():
    os_name = platform.system()
    if os_name == "Windows":
        return CLAMSCAN_PATH_WINDOWS
    else:
        return "clamscan"

def _update_scan_status(drive_path, active, files_scanned=0, elapsed=0, current_file=None, result=None, started_at=None):
    status = {
        "type": "virus_scan", "drive": drive_path, "active": active,
        "files_scanned": files_scanned, "elapsed_seconds": elapsed,
        "current_file": current_file, "started_at": started_at, "result": result
    }
    try:
        set_setting("scan_status", json.dumps(status))
    except Exception:
        pass  # never let status reporting crash the actual scan

def scan_drive_for_viruses(drive_path):
    clamscan = get_clamscan_path()

    if not os.path.exists(drive_path):
        return {"error": f"Path not found: {drive_path}"}

    cmd = [clamscan, "-r", "-v", drive_path]
    start_time = time.time()
    started_at_iso = time.strftime("%Y-%m-%dT%H:%M:%S")
    _update_scan_status(drive_path, True, 0, 0, None, None, started_at_iso)

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    except FileNotFoundError:
        result = {"error": "ClamAV not found. Please install it first."}
        _update_scan_status(drive_path, False, 0, 0, None, result, started_at_iso)
        return result

    infected_files = []
    files_scanned = 0
    last_update = 0

    try:
        for line in process.stdout:
            line = line.strip()
            if not line:
                continue

            elapsed = time.time() - start_time
            if elapsed > MAX_SCAN_SECONDS:
                process.kill()
                result = {"error": "Scan exceeded 1 hour safety limit, stopped."}
                _update_scan_status(drive_path, False, files_scanned, int(elapsed), None, result, started_at_iso)
                return result

            if "FOUND" in line:
                parts = line.rsplit(":", 1)
                if len(parts) == 2:
                    file_path = parts[0].strip()
                    threat_name = parts[1].replace("FOUND", "").strip()
                    infected_files.append({"file": file_path, "threat": threat_name})
                    print(f"   🦠 THREAT FOUND: {file_path} -> {threat_name}")
            elif ": OK" in line:
                files_scanned += 1
                current_file = line.rsplit(":", 1)[0].strip()

                if files_scanned % 100 == 0:
                    print(f"   ... {files_scanned} files scanned so far ({int(elapsed)}s elapsed)")

                if elapsed - last_update >= 1:
                    _update_scan_status(drive_path, True, files_scanned, int(elapsed), current_file, None, started_at_iso)
                    last_update = elapsed
    except (OSError, ValueError):
        process.kill()
        result = {"error": "Scan interrupted — the drive may have been removed."}
        _update_scan_status(drive_path, False, files_scanned, int(time.time() - start_time), None, result, started_at_iso)
        return result

    process.wait()
    elapsed_total = int(time.time() - start_time)

    result = {
        "scanned_path": drive_path, "files_scanned": files_scanned,
        "infected_count": len(infected_files), "infected_files": infected_files,
        "clean": len(infected_files) == 0, "time_taken_seconds": elapsed_total
    }
    _update_scan_status(drive_path, False, files_scanned, elapsed_total, None, result, started_at_iso)
    return result

def print_scan_result(result):
    if "error" in result:
        print(f"Scan Error: {result['error']}")
        return
    print(f"\nVirus Scan Report for: {result['scanned_path']}")
    print("=" * 60)
    print(f"Files Scanned: {result['files_scanned']}")
    print(f"Time Taken: {result['time_taken_seconds']} seconds")
    if result["clean"]:
        print("✅ No threats found. Drive is clean.")
    else:
        print(f"⚠️  {result['infected_count']} infected file(s) found!")
        for item in result["infected_files"]:
            print(f"   🦠 {item['file']}")
            print(f"      Threat: {item['threat']}")
    print("=" * 60)

if __name__ == "__main__":
    path = input("Enter drive/folder path to scan (example: F:\\): ")
    print("Scanning... progress will print every 100 files.\n")
    result = scan_drive_for_viruses(path)
    print_scan_result(result)