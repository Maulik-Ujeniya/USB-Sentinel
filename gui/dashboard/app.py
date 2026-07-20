from flask import Flask, render_template
import json
import os

app = Flask(__name__)

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "reports")
FULL_REPORT_PATH = os.path.join(REPORTS_DIR, "last_scan_full.json")

def load_report():
    if not os.path.exists(FULL_REPORT_PATH):
        return None
    with open(FULL_REPORT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

@app.route("/")
def dashboard():
    data = load_report()
    return render_template("dashboard.html", data=data)

if __name__ == "__main__":
    app.run(debug=True, port=5000)