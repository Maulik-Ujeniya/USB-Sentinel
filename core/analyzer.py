import os
import sys
import json
import hashlib
import shutil
import time
from datetime import datetime

# Ensure core/ is on the import path regardless of where the script is launched from
sys.path.insert(0, os.path.dirname(__file__))

from identifier import get_drive_serial
import zipfile
try:
    import pefile
    PEFILE_AVAILABLE = True
except ImportError:
    PEFILE_AVAILABLE = False

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


def preview_zip_contents(zip_path, max_entries=50):
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            entries = z.namelist()
            info_list = []
            for name in entries[:max_entries]:
                info = z.getinfo(name)
                info_list.append({
                    "name": name,
                    "size_readable": format_size(info.file_size),
                    "is_folder": name.endswith("/")
                })
            return {
                "total_entries": len(entries),
                "shown_entries": len(info_list),
                "entries": info_list
            }
    except (zipfile.BadZipFile, OSError, FileNotFoundError):
        return {"error": "Could not read this archive (corrupted or unsupported format)."}


def read_exe_metadata(exe_path):
    if not PEFILE_AVAILABLE:
        return {"error": "exe reading not available on this system"}

    try:
        pe = pefile.PE(exe_path, fast_load=True)
        pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_RESOURCE']])

        info = {"publisher": "Unknown", "product_name": "Unknown", "version": "Unknown", "digitally_signed": False}

        if hasattr(pe, "FileInfo"):
            for file_info in pe.FileInfo:
                for entry in file_info:
                    if hasattr(entry, "StringTable"):
                        for st in entry.StringTable:
                            for key, value in st.entries.items():
                                key_str = key.decode(errors="ignore")
                                value_str = value.decode(errors="ignore")
                                if key_str == "CompanyName":
                                    info["publisher"] = value_str
                                elif key_str == "ProductName":
                                    info["product_name"] = value_str
                                elif key_str == "ProductVersion":
                                    info["version"] = value_str

        info["digitally_signed"] = hasattr(pe, "DIRECTORY_ENTRY_SECURITY")

        pe.close()
        return info
    except Exception:
        return {"error": "Could not read exe metadata (file may be corrupted or unusual format)."}


def get_disk_usage(path):
    try:
        usage = shutil.disk_usage(path)
        percent = round((usage.used / usage.total * 100), 1) if usage.total else 0
        return {
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
            "total_readable": format_size(usage.total),
            "used_readable": format_size(usage.used),
            "free_readable": format_size(usage.free),
            "percent_used": percent
        }
    except Exception:
        return None


# ---- Live scan progress callback support ----
_scan_progress_callback = None

def set_scan_progress_callback(callback):
    """Set a callback function(files_scanned, total_folders, current_file, current_folder) for live streaming ticker."""
    global _scan_progress_callback
    _scan_progress_callback = callback


def scan_drive_full(drive_path):
    global _scan_progress_callback
    folders = []
    total_files = 0
    total_folders_scanned = 0
    total_size = 0
    category_summary = {}
    last_callback_time = 0

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

            file_entry = {
                "name": file,
                "extension": extension if extension else "(no extension)",
                "category": category,
                "icon": icon,
                "size_bytes": size,
                "size_readable": format_size(size)
            }

            if extension == ".zip":
                file_entry["zip_preview"] = preview_zip_contents(file_path)

            if extension == ".exe" and PEFILE_AVAILABLE:
                file_entry["exe_metadata"] = read_exe_metadata(file_path)

            folder_entry["files"].append(file_entry)

            total_files += 1
            total_size += size

            # Real-time streaming callback: update current file being scanned
            now = time.time()
            if _scan_progress_callback and (now - last_callback_time >= 0.04):
                last_callback_time = now
                try:
                    _scan_progress_callback(total_files, total_folders_scanned, file, root)
                except Exception:
                    pass

            if category not in category_summary:
                category_summary[category] = {"count": 0, "total_size": 0}
            category_summary[category]["count"] += 1
            category_summary[category]["total_size"] += size

        folders.append(folder_entry)

    for cat in category_summary:
        category_summary[cat]["total_size_readable"] = format_size(category_summary[cat]["total_size"])

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
    """
    Find duplicate files using 2-step verification:
      Step 1: Group files by exact byte size (filtering out unique file sizes).
      Step 2: Calculate full SHA-256 cryptographic hashes for remaining candidates.
      Result includes full SHA-256 hash snippet for proof in UI!
    """

    size_groups = {}
    for folder in data["folders"]:
        for file in folder["files"]:
            size = file["size_bytes"]
            if size == 0:
                continue  # skip empty 0-byte files
            if size not in size_groups:
                size_groups[size] = []
            size_groups[size].append((folder["path"], file))

    hash_map = {}

    for size, file_list in size_groups.items():
        if len(file_list) < 2:
            continue  # Unique size = unique file content

        for folder_path, file in file_list:
            file_path = os.path.join(folder_path, file["name"])
            file_hash = get_file_hash(file_path)

            if file_hash is None:
                continue

            if file_hash not in hash_map:
                hash_map[file_hash] = []
            hash_map[file_hash].append({
                "path": file_path,
                "name": file["name"],
                "folder": folder_path,
                "extension": file["extension"],
                "category": file["category"],
                "icon": file["icon"],
                "size_bytes": file["size_bytes"],
                "size_readable": file["size_readable"]
            })

    duplicates = []
    for file_hash, files in hash_map.items():
        if len(files) > 1:
            wasted = files[0]["size_bytes"] * (len(files) - 1)
            duplicates.append({
                "sha256": file_hash[:16],  # 16-char SHA-256 snippet for UI proof
                "full_sha256": file_hash,
                "count": len(files),
                "size_each_readable": files[0]["size_readable"],
                "wasted_bytes": wasted,
                "wasted_space_readable": format_size(wasted),
                "original": files[0],
                "copies": files[1:]
            })

    duplicates.sort(key=lambda d: d["wasted_bytes"], reverse=True)
    return duplicates


def find_largest_files(data, top_n=50):
    all_files = []
    for folder in data["folders"]:
        for file in folder["files"]:
            all_files.append({
                "path": os.path.join(folder["path"], file["name"]),
                "name": file["name"],
                "folder": folder["path"],
                "category": file["category"],
                "icon": file["icon"],
                "size_bytes": file["size_bytes"],
                "size_readable": file["size_readable"]
            })
    all_files.sort(key=lambda x: x["size_bytes"], reverse=True)
    return all_files[:top_n]


def get_snapshot_id(scanned_path, serial):
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
                files[full_path] = {
                    "name": file["name"],
                    "folder": folder["path"],
                    "extension": file["extension"],
                    "category": file["category"],
                    "icon": file["icon"],
                    "size_bytes": file["size_bytes"],
                    "size_readable": file["size_readable"]
                }
        return files

    old_files = get_file_map(previous_data)
    new_files = get_file_map(current_data)

    added = []
    for path, info in new_files.items():
        if path not in old_files:
            entry = dict(info)
            entry["path"] = path
            added.append(entry)

    removed = []
    for path, info in old_files.items():
        if path not in new_files:
            entry = dict(info)
            entry["path"] = path
            removed.append(entry)

    modified = []
    for path, info in new_files.items():
        if path in old_files and info["size_bytes"] != old_files[path]["size_bytes"]:
            entry = dict(info)
            entry["path"] = path
            entry["old_size_readable"] = old_files[path]["size_readable"]
            entry["new_size_readable"] = info["size_readable"]
            modified.append(entry)

    return {
        "previous_scan_date": previous_data.get("scan_date"),
        "added": added,
        "removed": removed,
        "modified": modified
    }


def save_json_report(data, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def save_full_report_json(data, duplicates, largest_files, changes, disk_usage, output_path):
    total_duplicate_copies = sum(d["count"] - 1 for d in duplicates)
    total_wasted_bytes = sum(d["wasted_bytes"] for d in duplicates)

    full_report = {
        "drive_path": data["drive_path"],
        "scan_date": data["scan_date"],
        "total_folders_scanned": data["total_folders_scanned"],
        "total_files": data["total_files"],
        "total_size": data["total_size"],
        "total_size_readable": data["total_size_readable"],
        "unique_files": data["total_files"] - total_duplicate_copies,
        "duplicate_copies": total_duplicate_copies,
        "wasted_bytes": total_wasted_bytes,
        "wasted_space_readable": format_size(total_wasted_bytes),
        "category_summary": data["category_summary"],
        "duplicates": duplicates,
        "largest_files": largest_files,
        "changes": changes,
        "disk_usage": disk_usage,
        "folders": data["folders"]
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(full_report, f, indent=2)