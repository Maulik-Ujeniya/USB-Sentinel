import subprocess
import platform
import os
import time

CLAMSCAN_PATH_WINDOWS = r"C:\Program Files\ClamAV\clamscan.exe"
MAX_SCAN_SECONDS = 3600  # 1 hour safety limit, not a normal expected time

def get_clamscan_path():
    os_name = platform.system()
    if os_name == "Windows":
        return CLAMSCAN_PATH_WINDOWS
    else:
        return "clamscan"

def scan_drive_for_viruses(drive_path):
    clamscan = get_clamscan_path()

    if not os.path.exists(drive_path):
        return {"error": f"Path not found: {drive_path}"}

    cmd = [clamscan, "-r", "-v", drive_path]  # -v = verbose, shows each file live

    try:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1
        )
    except FileNotFoundError:
        return {"error": "ClamAV not found. Please install it first."}

    infected_files = []
    files_scanned = 0
    start_time = time.time()

    for line in process.stdout:
        line = line.strip()
        if not line:
            continue

        if time.time() - start_time > MAX_SCAN_SECONDS:
            process.kill()
            return {"error": "Scan exceeded 1 hour safety limit, stopped."}

        if "FOUND" in line:
            parts = line.rsplit(":", 1)
            if len(parts) == 2:
                file_path = parts[0].strip()
                threat_name = parts[1].replace("FOUND", "").strip()
                infected_files.append({"file": file_path, "threat": threat_name})
                print(f"   🦠 THREAT FOUND: {file_path} -> {threat_name}")
        elif ": OK" in line:
            files_scanned += 1
            if files_scanned % 100 == 0:
                elapsed = int(time.time() - start_time)
                print(f"   ... {files_scanned} files scanned so far ({elapsed}s elapsed)")

    process.wait()
    elapsed_total = int(time.time() - start_time)

    return {
        "scanned_path": drive_path,
        "files_scanned": files_scanned,
        "infected_count": len(infected_files),
        "infected_files": infected_files,
        "clean": len(infected_files) == 0,
        "time_taken_seconds": elapsed_total
    }

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