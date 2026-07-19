import os
import json
import hashlib
from datetime import datetime
from identifier import get_drive_serial

FILE_CATEGORIES = {
    "Image": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".heic"],
    "Video": [".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv"],
    "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg"],
    "Document": [".doc", ".docx", ".txt", ".rtf", ".odt"],
    "PDF": [".pdf"],
    "Spreadsheet": [".xls", ".xlsx", ".csv"],
    "Presentation": [".ppt", ".pptx"],
    "Code": [".py", ".js", ".java", ".c", ".cpp", ".html", ".css", ".php", ".json", ".xml"],
    "Archive": [".zip", ".rar", ".7z", ".tar", ".gz"],
    "Executable": [".exe", ".msi", ".bat", ".sh"],
}

CATEGORY_ICONS = {
    "Image": "🖼️", "Video": "🎬", "Audio": "🎵", "Document": "📄",
    "PDF": "📕", "Spreadsheet": "📊", "Presentation": "📽️",
    "Code": "💻", "Archive": "🗜️", "Executable": "⚙️", "Other": "❓",
}
FOLDER_ICON = "📁"

def get_category(extension):
    extension = extension.lower()
    for category, extensions in FILE_CATEGORIES.items():
        if extension in extensions:
            return category
    return "Other"

def format_size(size_bytes):
    if size_bytes >= 1024 ** 3:
        return f"{size_bytes / (1024 ** 3):.2f} GB"
    elif size_bytes >= 1024 ** 2:
        return f"{size_bytes / (1024 ** 2):.2f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes} B"

def scan_drive_full(drive_path):
    folders = []
    total_files = 0
    total_folders_scanned = 0
    total_size = 0
    category_summary = {}

    for root, dirs, files in os.walk(drive_path):
        total_folders_scanned += 1
        if not files:
            continue

        folder_entry = {"path": root, "files": []}

        for file in files:
            file_path = os.path.join(root, file)
            try:
                size = os.path.getsize(file_path)
            except (OSError, FileNotFoundError):
                continue

            extension = os.path.splitext(file)[1].lower()
            category = get_category(extension)
            icon = CATEGORY_ICONS.get(category, "❓")

            folder_entry["files"].append({
                "name": file,
                "extension": extension if extension else "(no extension)",
                "category": category,
                "icon": icon,
                "size_bytes": size,
                "size_readable": format_size(size)
            })

            total_files += 1
            total_size += size

            if category not in category_summary:
                category_summary[category] = {"count": 0, "total_size": 0}
            category_summary[category]["count"] += 1
            category_summary[category]["total_size"] += size

        folders.append(folder_entry)

    return {
        "drive_path": drive_path,
        "scan_date": datetime.now().isoformat(),
        "total_folders_scanned": total_folders_scanned,
        "total_files": total_files,
        "total_size": total_size,
        "total_size_readable": format_size(total_size),
        "category_summary": category_summary,
        "folders": folders
    }

def get_file_hash(file_path, block_size=65536):
    hasher = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while True:
                block = f.read(block_size)
                if not block:
                    break
                hasher.update(block)
        return hasher.hexdigest()
    except (OSError, FileNotFoundError, PermissionError):
        return None

def find_duplicates(data):
    hash_map = {}
    files_hashed = 0

    for folder in data["folders"]:
        for file in folder["files"]:
            file_path = os.path.join(folder["path"], file["name"])
            file_hash = get_file_hash(file_path)
            files_hashed += 1

            if files_hashed % 200 == 0:
                print(f"   ... hashed {files_hashed} files so far (checking duplicates)")

            if file_hash is None:
                continue

            if file_hash not in hash_map:
                hash_map[file_hash] = []
            hash_map[file_hash].append({"path": file_path, "size": file["size_bytes"]})

    duplicates = []
    for file_hash, files in hash_map.items():
        if len(files) > 1:
            duplicates.append({
                "count": len(files),
                "size_each_bytes": files[0]["size"],
                "size_each_readable": format_size(files[0]["size"]),
                "wasted_bytes": files[0]["size"] * (len(files) - 1),
                "wasted_space_readable": format_size(files[0]["size"] * (len(files) - 1)),
                "files": [f["path"] for f in files]
            })

    return duplicates

def find_largest_files(data, top_n=10):
    all_files = []
    for folder in data["folders"]:
        for file in folder["files"]:
            all_files.append({
                "path": os.path.join(folder["path"], file["name"]),
                "size_bytes": file["size_bytes"],
                "size_readable": file["size_readable"]
            })
    all_files.sort(key=lambda x: x["size_bytes"], reverse=True)
    return all_files[:top_n]

def get_snapshot_id(scanned_path, serial):
    """
    Builds a unique ID per (physical drive + exact folder scanned),
    so different folders on the same drive never share a snapshot,
    and different physical drives never collide either.
    """
    drive_root, tail = os.path.splitdrive(os.path.abspath(scanned_path))
    normalized_tail = tail.replace("\\", "/").strip("/").lower()
    base_id = serial if serial else "unknownserial"

    if normalized_tail:
        tail_hash = hashlib.md5(normalized_tail.encode()).hexdigest()[:8]
        return f"{base_id}_{tail_hash}"
    return base_id

def get_snapshot_path(reports_dir, snapshot_id):
    return os.path.join(reports_dir, f"{snapshot_id}_snapshot.json")

def compare_to_previous_scan(current_data, snapshot_path):
    if not os.path.exists(snapshot_path):
        return None

    with open(snapshot_path, "r", encoding="utf-8") as f:
        previous_data = json.load(f)

    def get_file_map(data):
        files = {}
        for folder in data["folders"]:
            for file in folder["files"]:
                full_path = os.path.join(folder["path"], file["name"])
                files[full_path] = file["size_bytes"]
        return files

    old_files = get_file_map(previous_data)
    new_files = get_file_map(current_data)

    added = [f for f in new_files if f not in old_files]
    removed = [f for f in old_files if f not in new_files]
    modified = [f for f in new_files if f in old_files and new_files[f] != old_files[f]]

    return {
        "previous_scan_date": previous_data.get("scan_date"),
        "added": added,
        "removed": removed,
        "modified": modified
    }

def save_json_report(data, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def save_text_report(data, duplicates, largest_files, changes, output_path):
    total_duplicate_copies = sum(d["count"] - 1 for d in duplicates)
    total_wasted_bytes = sum(d["wasted_bytes"] for d in duplicates)
    unique_files = data["total_files"] - total_duplicate_copies

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("USB-Sentinel Scan Report\n")
        f.write(f"Drive/Folder Scanned: {data['drive_path']}\n")
        f.write(f"Scan Date: {data['scan_date']}\n")
        f.write("=" * 70 + "\n")
        f.write(f"Total Folders Scanned: {data['total_folders_scanned']}\n")
        f.write(f"Total Files: {data['total_files']}\n")
        f.write(f"  - Unique files: {unique_files}\n")
        f.write(f"  - Duplicate copies: {total_duplicate_copies}\n")
        f.write(f"Total Size: {data['total_size_readable']}\n")
        f.write(f"Space wasted by duplicates: {format_size(total_wasted_bytes)}\n")
        f.write("-" * 70 + "\n\n")

        f.write("Summary by Category:\n")
        for cat, info in data["category_summary"].items():
            icon = CATEGORY_ICONS.get(cat, "❓")
            f.write(f"  {icon} {cat:15} | Files: {info['count']:5} | Size: {format_size(info['total_size'])}\n")

        f.write("\n" + "=" * 70 + "\n")
        f.write("Top 10 Largest Files:\n")
        f.write("=" * 70 + "\n")
        for i, file in enumerate(largest_files, 1):
            f.write(f"  {i}. {file['path']} - {file['size_readable']}\n")

        f.write("\n" + "=" * 70 + "\n")
        f.write(f"Duplicate Files Found: {len(duplicates)} group(s), {total_duplicate_copies} extra copies, {format_size(total_wasted_bytes)} wasted\n")
        f.write("=" * 70 + "\n")
        for dup in duplicates:
            f.write(f"  {dup['count']}x copies, {dup['size_each_readable']} each, wasting {dup['wasted_space_readable']}\n")
            for path in dup["files"]:
                f.write(f"      - {path}\n")

        f.write("\n" + "=" * 70 + "\n")
        f.write("Changes Since Last Scan (of this exact drive+folder):\n")
        f.write("=" * 70 + "\n")
        if changes is None:
            f.write("  No previous scan found for this drive+folder — this is the first scan.\n")
        else:
            f.write(f"  Compared to scan on: {changes['previous_scan_date']}\n")
            f.write(f"  Added ({len(changes['added'])}):\n")
            for p in changes["added"]:
                f.write(f"      + {p}\n")
            f.write(f"  Removed ({len(changes['removed'])}):\n")
            for p in changes["removed"]:
                f.write(f"      - {p}\n")
            f.write(f"  Modified ({len(changes['modified'])}):\n")
            for p in changes["modified"]:
                f.write(f"      ~ {p}\n")

        f.write("\n" + "=" * 70 + "\n")
        f.write("Full Folder & File Listing:\n")
        f.write("=" * 70 + "\n\n")

        for folder in data["folders"]:
            f.write(f"{FOLDER_ICON} {folder['path']}\n")
            for file in folder["files"]:
                f.write(f"    {file['icon']} {file['name']:40} | {file['category']} ({file['extension']}) | {file['size_readable']}\n")
            f.write("\n")

def print_duplicate_details(duplicates):
    if not duplicates:
        print("\nNo duplicate files found.")
        return

    print(f"\nDuplicate File Details ({len(duplicates)} group(s)):")
    print("-" * 70)
    for i, dup in enumerate(duplicates, 1):
        print(f"  Group {i}: {dup['count']}x copies, {dup['size_each_readable']} each, wasting {dup['wasted_space_readable']}")
        for path in dup["files"]:
            print(f"      - {path}")
    print("-" * 70)


if __name__ == "__main__":
    raw_path = input("Enter drive/folder path (example: F:\\ or F:\\WebS): ")
    path = raw_path.strip()

    if not os.path.isdir(path):
        print(f"\n❌ Error: '{path}' is not a valid folder/drive path, or the drive isn't connected.")
        print("Check for typos or extra spaces, make sure the drive is plugged in, then try again.")
    else:
        print("Step 1/3: Scanning files and folders...")
        data = scan_drive_full(path)

        print("Step 2/3: Checking for duplicate files (this reads every file, may take a while)...")
        duplicates = find_duplicates(data)
        largest_files = find_largest_files(data)

        reports_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
        os.makedirs(reports_dir, exist_ok=True)

        drive_root = os.path.splitdrive(os.path.abspath(path))[0]
        serial = get_drive_serial(drive_root)
        snapshot_id = get_snapshot_id(path, serial)
        snapshot_path = get_snapshot_path(reports_dir, snapshot_id)

        print(f"    Identity for this scan -> Drive Serial: {serial or 'Unknown'} | Snapshot ID: {snapshot_id}")

        print("Step 3/3: Comparing to last scan of this exact drive+folder...")
        changes = compare_to_previous_scan(data, snapshot_path)

        save_json_report(data, snapshot_path)

        text_path = os.path.join(reports_dir, "last_scan.txt")
        save_text_report(data, duplicates, largest_files, changes, text_path)

        total_duplicate_copies = sum(d["count"] - 1 for d in duplicates)
        unique_files = data["total_files"] - total_duplicate_copies

        print(f"\nScan complete.")
        print(f"Total Files: {data['total_files']} (Unique: {unique_files}, Duplicate copies: {total_duplicate_copies})")
        print(f"Total Size: {data['total_size_readable']}")

        print_duplicate_details(duplicates)

        if changes is None:
            print("\nFirst scan of this drive+folder — no comparison available yet.")
        else:
            print(f"\nChanges since last scan: +{len(changes['added'])} added, -{len(changes['removed'])} removed, ~{len(changes['modified'])} modified")

        print(f"\nFull report saved to: {text_path}")