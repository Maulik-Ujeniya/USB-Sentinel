from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import json
import os
import sys
import threading
import time
import psutil
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "core"))
from db import (init_db, list_all_drives_detailed, forget_drive, get_setting,
                set_setting, get_all_settings, set_trusted, log_activity,
                get_activity_log, clear_activity_log, save_scan_history,
                update_scan_history, get_scan_history, is_trusted, record_drive_connection)
from identifier import get_drive_serial, eject_drive
from analyzer import (scan_drive_full, find_duplicates, find_largest_files,
                       get_disk_usage, get_snapshot_id, get_snapshot_path,
                       compare_to_previous_scan, save_json_report,
                       save_full_report_json, format_size, set_scan_progress_callback)
from scanner import scan_drive_for_viruses

app = Flask(__name__)
app.secret_key = "usb-sentinel-local-only"
init_db()

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "reports")
FULL_REPORT_PATH = os.path.join(REPORTS_DIR, "last_scan_full.json")

# ---- Shared state for background scans ----
_active_scans = {}  # key -> {"type": ..., "status": ..., etc}
_scans_lock = threading.Lock()


def load_report():
    if not os.path.exists(FULL_REPORT_PATH):
        return None
    try:
        with open(FULL_REPORT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def get_protection_status():
    last = get_setting("last_heartbeat")
    if not last:
        return {"active": False}
    try:
        seconds_ago = (datetime.now() - datetime.fromisoformat(last)).total_seconds()
        return {"active": seconds_ago < 6}
    except Exception:
        return {"active": False}


def get_connected_removable_drives():
    """Get currently connected removable drives with their info."""
    drives = []
    for d in psutil.disk_partitions():
        if 'removable' in d.opts.lower() if isinstance(d.opts, str) else False:
            serial = get_drive_serial(d.device)
            trusted = is_trusted(serial) if serial else False
            try:
                usage = psutil.disk_usage(d.mountpoint)
                usage_info = {
                    "total": format_size(usage.total),
                    "used": format_size(usage.used),
                    "free": format_size(usage.free),
                    "percent": usage.percent
                }
            except (OSError, PermissionError):
                usage_info = None

            drives.append({
                "device": d.device,
                "mountpoint": d.mountpoint,
                "fstype": d.fstype,
                "serial": serial,
                "trusted": trusted,
                "usage": usage_info
            })
    return drives


# ==================== Page Routes ====================

@app.route("/")
def dashboard():
    return render_template("dashboard.html", data=load_report(), status=get_protection_status())

@app.route("/settings")
def settings_page():
    drives = list_all_drives_detailed()
    all_settings = get_all_settings()
    settings = {
        "auto_scan_prompt": all_settings.get("auto_scan_prompt", "1") == "1",
        "eject_on_block": all_settings.get("eject_on_block", "1") == "1",
        "auto_scan_on_insert": all_settings.get("auto_scan_on_insert", "0") == "1",
        "scan_size_limit_mb": all_settings.get("scan_size_limit_mb", "0"),
        "quarantine_threats": all_settings.get("quarantine_threats", "0") == "1",
        "notification_sound": all_settings.get("notification_sound", "1") == "1",
        "theme": all_settings.get("theme", "dark"),
        "start_protection_on_launch": all_settings.get("start_protection_on_launch", "1") == "1",
        "clamav_path": all_settings.get("clamav_path", ""),
    }
    return render_template("settings.html", drives=drives, settings=settings, status=get_protection_status())

@app.route("/settings/forget", methods=["POST"])
def forget_drive_route():
    serial = request.form.get("serial")
    if serial:
        forget_drive(serial)
        log_activity("drive_forgotten", f"Drive {serial} forgotten by user")
        flash(f"Drive {serial} forgotten — it will be treated as unknown next time.")
    return redirect(url_for("settings_page"))

@app.route("/settings/trust", methods=["POST"])
def trust_drive_route():
    serial = request.form.get("serial")
    trust = request.form.get("trust", "1")
    if serial:
        set_trusted(serial, int(trust))
        action = "trusted" if trust == "1" else "untrusted"
        log_activity("drive_trust_changed", f"Drive {serial} {action} by user")
        flash(f"Drive {serial} {action}.")
    return redirect(url_for("settings_page"))

@app.route("/settings/save", methods=["POST"])
def save_settings_route():
    set_setting("auto_scan_prompt", "1" if request.form.get("auto_scan_prompt") else "0")
    set_setting("eject_on_block", "1" if request.form.get("eject_on_block") else "0")
    set_setting("auto_scan_on_insert", "1" if request.form.get("auto_scan_on_insert") else "0")
    set_setting("scan_size_limit_mb", request.form.get("scan_size_limit_mb", "0"))
    set_setting("quarantine_threats", "1" if request.form.get("quarantine_threats") else "0")
    set_setting("notification_sound", "1" if request.form.get("notification_sound") else "0")
    set_setting("start_protection_on_launch", "1" if request.form.get("start_protection_on_launch") else "0")
    set_setting("clamav_path", request.form.get("clamav_path", "").strip())
    log_activity("settings_saved", "Settings updated by user")
    flash("Settings saved.")
    return redirect(url_for("settings_page"))


# ==================== API Routes ====================

@app.route("/api/status")
def api_status():
    scan_raw = get_setting("scan_status")
    scan = json.loads(scan_raw) if scan_raw else None
    return jsonify({"protection": get_protection_status(), "scan": scan})

@app.route("/api/drives/live")
def api_live_drives():
    """Get real-time list of connected removable drives."""
    return jsonify({"drives": get_connected_removable_drives()})

@app.route("/api/drives/trust", methods=["POST"])
def api_trust_drive():
    """Trust or untrust a drive by serial."""
    data = request.get_json() or {}
    serial = data.get("serial")
    trust = data.get("trust", True)
    if not serial:
        return jsonify({"error": "serial required"}), 400
    set_trusted(serial, 1 if trust else 0)
    action = "trusted" if trust else "untrusted"
    log_activity("drive_trust_changed", f"Drive {serial} {action} by user")
    return jsonify({"ok": True, "serial": serial, "trusted": trust})

@app.route("/api/drives/eject", methods=["POST"])
def api_eject_drive():
    """Eject a drive by letter."""
    data = request.get_json() or {}
    drive_letter = data.get("drive_letter")
    if not drive_letter:
        return jsonify({"error": "drive_letter required"}), 400
    success = eject_drive(drive_letter)
    if success:
        log_activity("drive_ejected", f"Drive {drive_letter} ejected by user")
    return jsonify({"ok": success, "drive_letter": drive_letter})

@app.route("/api/scan/drive", methods=["POST"])
def api_scan_drive():
    """Start a file analysis scan of a drive in the background."""
    data = request.get_json() or {}
    drive_path = data.get("drive_path", "").strip()
    if not drive_path or not os.path.isdir(drive_path):
        return jsonify({"error": f"Invalid path: {drive_path}"}), 400

    scan_key = f"file_{drive_path}"
    with _scans_lock:
        if scan_key in _active_scans and _active_scans[scan_key].get("active"):
            return jsonify({"error": "A scan is already running for this drive"}), 409

        scan_state = {
            "active": True, "type": "file_scan", "drive_path": drive_path,
            "files_scanned": 0, "folders_scanned": 0, "current_folder": "",
            "started_at": datetime.now().isoformat(), "result": None
        }
        _active_scans[scan_key] = scan_state

    scan_id = save_scan_history("file_scan", drive_path, scan_state["started_at"])
    log_activity("scan_started", f"File scan started on {drive_path}")

    def run_scan():
        try:
            def progress_cb(files, folders, current):
                with _scans_lock:
                    _active_scans[scan_key]["files_scanned"] = files
                    _active_scans[scan_key]["folders_scanned"] = folders
                    _active_scans[scan_key]["current_folder"] = current

            set_scan_progress_callback(progress_cb)
            scan_data = scan_drive_full(drive_path)
            set_scan_progress_callback(None)

            disk_usage = get_disk_usage(drive_path)
            duplicates = find_duplicates(scan_data)
            largest_files = find_largest_files(scan_data)

            os.makedirs(REPORTS_DIR, exist_ok=True)
            drive_root = os.path.splitdrive(os.path.abspath(drive_path))[0]
            serial = get_drive_serial(drive_root)
            snapshot_id = get_snapshot_id(drive_path, serial)
            snapshot_path = get_snapshot_path(REPORTS_DIR, snapshot_id)
            changes = compare_to_previous_scan(scan_data, snapshot_path)
            save_json_report(scan_data, snapshot_path)
            save_full_report_json(scan_data, duplicates, largest_files, changes, disk_usage, FULL_REPORT_PATH)

            total_dup = sum(d["count"] - 1 for d in duplicates)

            with _scans_lock:
                _active_scans[scan_key]["active"] = False
                _active_scans[scan_key]["result"] = {
                    "total_files": scan_data["total_files"],
                    "total_size_readable": scan_data["total_size_readable"],
                    "duplicate_groups": len(duplicates),
                    "duplicate_copies": total_dup,
                }

            update_scan_history(scan_id, finished_at=datetime.now().isoformat(),
                                files_scanned=scan_data["total_files"],
                                duplicate_groups=len(duplicates),
                                total_size_readable=scan_data["total_size_readable"],
                                status="complete")
            log_activity("scan_complete", f"File scan of {drive_path} complete: {scan_data['total_files']} files")
        except Exception as e:
            with _scans_lock:
                _active_scans[scan_key]["active"] = False
                _active_scans[scan_key]["result"] = {"error": str(e)}
            update_scan_history(scan_id, finished_at=datetime.now().isoformat(),
                                status="error", result_json={"error": str(e)})
            log_activity("scan_error", f"File scan of {drive_path} failed: {e}")

    threading.Thread(target=run_scan, daemon=True).start()
    return jsonify({"ok": True, "scan_key": scan_key, "scan_id": scan_id})

@app.route("/api/scan/virus", methods=["POST"])
def api_scan_virus():
    """Start a ClamAV virus scan of a drive in the background."""
    data = request.get_json() or {}
    drive_path = data.get("drive_path", "").strip()
    if not drive_path or not os.path.exists(drive_path):
        return jsonify({"error": f"Invalid path: {drive_path}"}), 400

    scan_key = f"virus_{drive_path}"
    with _scans_lock:
        if scan_key in _active_scans and _active_scans[scan_key].get("active"):
            return jsonify({"error": "A virus scan is already running for this drive"}), 409

        scan_state = {
            "active": True, "type": "virus_scan", "drive_path": drive_path,
            "started_at": datetime.now().isoformat(), "result": None
        }
        _active_scans[scan_key] = scan_state

    scan_id = save_scan_history("virus_scan", drive_path, scan_state["started_at"])
    log_activity("virus_scan_started", f"Virus scan started on {drive_path}")

    def run_virus_scan():
        try:
            result = scan_drive_for_viruses(drive_path)
            with _scans_lock:
                _active_scans[scan_key]["active"] = False
                _active_scans[scan_key]["result"] = result

            update_scan_history(scan_id, finished_at=datetime.now().isoformat(),
                                files_scanned=result.get("files_scanned", 0),
                                infected_count=result.get("infected_count", 0),
                                status="complete" if "error" not in result else "error",
                                result_json=result)
            if result.get("infected_count", 0) > 0:
                log_activity("threats_found", f"Virus scan of {drive_path}: {result['infected_count']} threats found", result.get("infected_files"))
            else:
                log_activity("virus_scan_complete", f"Virus scan of {drive_path} complete: clean")
        except Exception as e:
            with _scans_lock:
                _active_scans[scan_key]["active"] = False
                _active_scans[scan_key]["result"] = {"error": str(e)}
            update_scan_history(scan_id, finished_at=datetime.now().isoformat(),
                                status="error", result_json={"error": str(e)})
            log_activity("virus_scan_error", f"Virus scan of {drive_path} failed: {e}")

    threading.Thread(target=run_virus_scan, daemon=True).start()
    return jsonify({"ok": True, "scan_key": scan_key, "scan_id": scan_id})

@app.route("/api/scan/progress")
def api_scan_progress():
    """Get live progress of all active scans."""
    with _scans_lock:
        return jsonify({"scans": dict(_active_scans)})

@app.route("/api/scan/history")
def api_scan_history():
    """Get scan history."""
    return jsonify({"history": get_scan_history(50)})

@app.route("/api/activity")
def api_activity():
    """Get activity log."""
    limit = request.args.get("limit", 100, type=int)
    return jsonify({"log": get_activity_log(limit)})

@app.route("/api/activity/clear", methods=["POST"])
def api_clear_activity():
    """Clear all activity log entries."""
    clear_activity_log()
    return jsonify({"ok": True})

@app.route("/api/protection/start", methods=["POST"])
def api_start_protection():
    """Start the USB watcher in a background thread (if not already running)."""
    from detector import start_watching
    prot = get_protection_status()
    if prot["active"]:
        return jsonify({"ok": True, "message": "Already running"})

    def run_watcher():
        try:
            start_watching()
        except Exception:
            pass

    threading.Thread(target=run_watcher, daemon=True).start()
    log_activity("protection_started", "USB protection started from dashboard")
    return jsonify({"ok": True, "message": "Protection started"})

@app.route("/api/report")
def api_report():
    """Get the current full report data."""
    data = load_report()
    if data is None:
        return jsonify({"error": "No scan data available"}), 404
    # Return a lighter version without the full folder listing to avoid huge payloads
    light = {k: v for k, v in data.items() if k != "folders"}
    light["has_folders"] = "folders" in data and len(data.get("folders", [])) > 0
    return jsonify(light)


if __name__ == "__main__":
    app.run(debug=True, port=5000)