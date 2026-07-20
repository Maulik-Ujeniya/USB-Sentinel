# 🛡️ USB-Sentinel — Real-Time USB Security & Drive Inspection Suite

[![Python Version](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Web-Flask%203.1-cyan.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-purple.svg)]()

**USB-Sentinel** is a powerful, real-time security inspection and hardware control application for removable USB drives. It monitors USB hardware ports, prompts native desktop popups with audio alerts upon unknown drive insertion, provides instant safe auto-ejection, and delivers a web security dashboard featuring real-time file stream tickers and SHA-256 cryptographic duplicate verification.

---

## ✨ Key Features

- **🚨 Native Windows Audio Popups & Auto-Eject**:
  - Automatically detects when a USB drive is inserted.
  - Plays native Windows sound alerts (`winsound.MessageBeep`).
  - Prompts top-most desktop popup window: **ALLOW** or **BLOCK & EJECT**.
  - Clicking **BLOCK** instantly triggers safe hardware ejection via Windows Shell API.

- **⚡ Instant Native Heuristic Threat Scanner**:
  - Scans drive files in seconds for `autorun.inf` threats, double extensions (e.g. `invoice.pdf.exe`), hidden executables, and malicious scripts.
  - No heavy or slow external virus scanning required!

- **📄 Real-Time File Stream Ticker**:
  - Live animated terminal stream widget on the dashboard showing the **exact file being scanned right now** (`📄 Scanning Maulik.jpg` ➔ `📕 Scanning document.pdf`).

- **🔑 SHA-256 Cryptographic Duplicate Verification**:
  - Groups duplicate files using 2-step verification: byte-size pre-filtering followed by full **SHA-256 cryptographic checksums**.
  - Displays `sha256: a3f8...b12e` proof badges directly in the UI.

- **📊 Storage Telemetry & File Inspection**:
  - Categorizes files into Images, Videos, Documents, Archives, Code, and Executables.
  - Calculates free vs used drive capacity.
  - Inspects `.zip` archive contents and reads `.exe` PE digital signatures.

- **⚙️ Web Security Console**:
  - Cyberpunk dark theme with glassmorphic cards and human-readable explanation badges on every section.
  - Export full scan history to CSV.

---

## 🏗️ Architecture

```
USB-Sentinel Architecture
 ┌─────────────────────────────────────────────────────────────┐
 │                      python main.py                         │
 └──────────────┬──────────────────────────────┬───────────────┘
                │                              │
     [Background Thread]             [Main Process]
    USB Hardware Watcher              Flask Security Console
    (core/detector.py)                (gui/dashboard/app.py)
                │                              │
     ┌──────────┴──────────┐        ┌──────────┴──────────┐
     │  Desktop Popups     │        │  REST API & Live    │
     │  & Audio Alerts     │        │  File Stream Ticker │
     │  (gui/popup.py)     │        │  (http://localhost) │
     └──────────┬──────────┘        └─────────────────────┘
                │
     [ALLOW or BLOCK & EJECT]
```

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.9 or higher

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Maulik-Ujeniya/USB-Sentinel.git
   cd USB-Sentinel
   ```

2. **Set up virtual environment (optional but recommended)**:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Launch USB-Sentinel**:
   ```bash
   python main.py
   ```
   *Your browser will automatically open to `http://localhost:5000` while the USB watcher runs silently in the background.*

---

## ⚙️ Project Structure

```
USB-Sentinel/
├── core/
│   ├── detector.py      # USB insertion watcher & auto-eject controller
│   ├── identifier.py    # Serial number extraction & Windows Shell ejection
│   ├── scanner.py       # Instant native heuristic threat scanner
│   ├── analyzer.py      # Full drive scanning, streaming ticker & SHA-256 deduplication
│   ├── db.py            # SQLite database & activity logger
│   └── manage.py        # CLI drive management utility
├── gui/
│   ├── popup.py         # Native Tkinter popups & winsound audio alerts
│   └── dashboard/
│       ├── app.py       # Flask REST API server
│       └── templates/
│           ├── dashboard.html # Cyberpunk Security Console dashboard
│           └── settings.html  # Security & automation settings page
├── reports/             # Generated JSON scan reports
├── data/                # SQLite database storage (usbsentinel.db)
├── main.py              # Single entry point launcher script
├── requirements.txt     # Dependency list
├── LICENSE              # MIT License
└── README.md            # Documentation
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
