import os
import sys
import time
import json

# Ensure core/ is on the import path
sys.path.insert(0, os.path.dirname(__file__))
from db import set_setting

# Dangerous extensions commonly used in USB malware / autoruns
SUSPICIOUS_EXTENSIONS = {
    ".exe", ".scr", ".pif", ".vbs", ".vbe", ".js", ".jse", ".bat", ".cmd",
    ".ps1", ".hta", ".cpl", ".inf", ".reg", ".wsf", ".wsh"
}

# Common double extension disguises (e.g. document.pdf.exe)
FAKE_DOC_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".png", ".jpg", ".jpeg", ".txt", ".mp4", ".zip"}


def _update_scan_status(drive_path, active, files_scanned=0, elapsed=0, current_file=None, result=None, started_at=None):
    status = {
        "type": "virus_scan",
        "drive": drive_path,
        "active": active,
        "files_scanned": files_scanned,
        "elapsed_seconds": elapsed,
        "current_file": current_file,
        "started_at": started_at,
        "result": result
    }
    try:
        set_setting("scan_status", json.dumps(status))
    except Exception:
        pass


def scan_drive_for_viruses(drive_path):
    """
    Instant Native Heuristic Threat Scanner.
    Scans drive files in milliseconds for:
      - autorun.inf files & USB auto-executables
      - Dangerous double extensions (e.g. document.pdf.exe)
      - Hidden executables & malicious script files
      - Suspicious hidden files in drive root
    """
    if not os.path.exists(drive_path):
        return {"error": f"Path not found: {drive_path}"}

    start_time = time.time()
    started_at_iso = time.strftime("%Y-%m-%dT%H:%M:%S")
    _update_scan_status(drive_path, True, 0, 0, None, None, started_at_iso)

    infected_files = []
    files_scanned = 0
    last_update = 0

    try:
        for root, dirs, files in os.walk(drive_path):
            for file in files:
                file_path = os.path.join(root, file)
                files_scanned += 1
                elapsed = time.time() - start_time

                # Live ticker status update
                if elapsed - last_update >= 0.05:
                    _update_scan_status(drive_path, True, files_scanned, round(elapsed, 1), file, None, started_at_iso)
                    last_update = elapsed

                lower_file = file.lower()

                # Rule 1: Check for autorun.inf
                if lower_file == "autorun.inf":
                    infected_files.append({
                        "file": file_path,
                        "threat": "Suspicious AutoRun script (autorun.inf)",
                        "severity": "High"
                    })
                    continue

                # Rule 2: Check for double extensions (e.g. photo.jpg.exe)
                parts = lower_file.rsplit(".", 2)
                if len(parts) == 3:
                    first_ext = "." + parts[1]
                    final_ext = "." + parts[2]
                    if first_ext in FAKE_DOC_EXTENSIONS and final_ext in SUSPICIOUS_EXTENSIONS:
                        infected_files.append({
                            "file": file_path,
                            "threat": f"Double extension disguise ({first_ext}{final_ext})",
                            "severity": "Critical"
                        })
                        continue

                # Rule 3: Hidden executables/scripts in root or system folders
                is_hidden = file.startswith(".") or False
                try:
                    # Windows hidden attribute check
                    import stat
                    st = os.stat(file_path)
                    if hasattr(st, "st_file_attributes"):
                        is_hidden = is_hidden or bool(st.st_file_attributes & 2)
                except Exception:
                    pass

                ext = os.path.splitext(lower_file)[1]
                if is_hidden and ext in SUSPICIOUS_EXTENSIONS:
                    infected_files.append({
                        "file": file_path,
                        "threat": f"Hidden suspicious executable/script ({ext})",
                        "severity": "High"
                    })

    except (OSError, ValueError) as e:
        result = {"error": f"Scan interrupted: {str(e)}"}
        _update_scan_status(drive_path, False, files_scanned, int(time.time() - start_time), None, result, started_at_iso)
        return result

    elapsed_total = round(time.time() - start_time, 2)

    result = {
        "scanned_path": drive_path,
        "files_scanned": files_scanned,
        "infected_count": len(infected_files),
        "infected_files": infected_files,
        "clean": len(infected_files) == 0,
        "time_taken_seconds": elapsed_total
    }
    _update_scan_status(drive_path, False, files_scanned, elapsed_total, None, result, started_at_iso)
    return result


def print_scan_result(result):
    if "error" in result:
        print(f"Scan Error: {result['error']}")
        return
    print(f"\nInstant Heuristic Security Report for: {result['scanned_path']}")
    print("=" * 60)
    print(f"Files Scanned: {result['files_scanned']}")
    print(f"Time Taken: {result['time_taken_seconds']} seconds")
    if result["clean"]:
        print("✅ No threats found. Drive is clean.")
    else:
        print(f"⚠️  {result['infected_count']} suspicious file(s) found!")
        for item in result["infected_files"]:
            print(f"   🦠 {item['file']}")
            print(f"      Threat: {item['threat']} [{item.get('severity','High')}]")
    print("=" * 60)


if __name__ == "__main__":
    path = input("Enter drive/folder path to scan (example: F:\\): ")
    result = scan_drive_for_viruses(path)
    print_scan_result(result)