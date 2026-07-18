import os
import json
from datetime import datetime

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

def save_json_report(data, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def save_text_report(data, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("USB-Sentinel Scan Report\n")
        f.write(f"Drive: {data['drive_path']}\n")
        f.write(f"Scan Date: {data['scan_date']}\n")
        f.write("=" * 70 + "\n")
        f.write(f"Total Folders Scanned: {data['total_folders_scanned']}\n")
        f.write(f"Total Files: {data['total_files']}\n")
        f.write(f"Total Size: {data['total_size_readable']}\n")
        f.write("-" * 70 + "\n\n")

        f.write("Summary by Category:\n")
        for cat, info in data["category_summary"].items():
            icon = CATEGORY_ICONS.get(cat, "❓")
            f.write(f"  {icon} {cat:15} | Files: {info['count']:5} | Size: {format_size(info['total_size'])}\n")

        f.write("\n" + "=" * 70 + "\n")
        f.write("Full Folder & File Listing:\n")
        f.write("=" * 70 + "\n\n")

        for folder in data["folders"]:
            f.write(f"{FOLDER_ICON} {folder['path']}\n")
            for file in folder["files"]:
                f.write(f"    {file['icon']} {file['name']:40} | {file['category']} ({file['extension']}) | {file['size_readable']}\n")
            f.write("\n")

if __name__ == "__main__":
    path = input("Enter drive path (example: F:\\): ")
    data = scan_drive_full(path)

    reports_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
    os.makedirs(reports_dir, exist_ok=True)

    json_path = os.path.join(reports_dir, "last_scan.json")
    text_path = os.path.join(reports_dir, "last_scan.txt")

    save_json_report(data, json_path)
    save_text_report(data, text_path)

    print(f"\nScan complete.")
    print(f"Total Folders Scanned: {data['total_folders_scanned']}")
    print(f"Total Files Found: {data['total_files']}")
    print(f"Total Size: {data['total_size_readable']}")
    print(f"\nFull report saved to:\n  {text_path}\n  {json_path}")
    print(f"\nOpen the .txt file in VS Code to see everything — no scroll limit there.")