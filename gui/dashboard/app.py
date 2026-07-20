from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import json
import os
import sys
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "core"))
from db import init_db, list_all_drives_detailed, forget_drive, get_setting, set_setting

app = Flask(__name__)
app.secret_key = "usb-sentinel-local-only"
init_db()

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "reports")
FULL_REPORT_PATH = os.path.join(REPORTS_DIR, "last_scan_full.json")

def load_report():
    if not os.path.exists(FULL_REPORT_PATH):
        return None
    with open(FULL_REPORT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def get_protection_status():
    last = get_setting("last_heartbeat")
    if not last:
        return {"active": False}
    try:
        seconds_ago = (datetime.now() - datetime.fromisoformat(last)).total_seconds()
        return {"active": seconds_ago < 6}
    except Exception:
        return {"active": False}

@app.route("/")
def dashboard():
    return render_template("dashboard.html", data=load_report(), status=get_protection_status())

@app.route("/settings")
def settings_page():
    drives = list_all_drives_detailed()
    settings = {
        "auto_scan_prompt": get_setting("auto_scan_prompt", "1") == "1",
        "eject_on_block": get_setting("eject_on_block", "1") == "1"
    }
    return render_template("settings.html", drives=drives, settings=settings, status=get_protection_status())

@app.route("/settings/forget", methods=["POST"])
def forget_drive_route():
    serial = request.form.get("serial")
    if serial:
        forget_drive(serial)
        flash(f"Drive {serial} forgotten — it will be treated as unknown next time.")
    return redirect(url_for("settings_page"))

@app.route("/settings/save", methods=["POST"])
def save_settings_route():
    set_setting("auto_scan_prompt", "1" if request.form.get("auto_scan_prompt") else "0")
    set_setting("eject_on_block", "1" if request.form.get("eject_on_block") else "0")
    flash("Settings saved.")
    return redirect(url_for("settings_page"))

@app.route("/api/status")
def api_status():
    scan_raw = get_setting("scan_status")
    scan = json.loads(scan_raw) if scan_raw else None
    return jsonify({"protection": get_protection_status(), "scan": scan})

if __name__ == "__main__":
    app.run(debug=True, port=5000)