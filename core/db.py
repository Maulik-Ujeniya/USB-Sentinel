import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "usbsentinel.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS drives (
            serial_number TEXT PRIMARY KEY,
            drive_letter TEXT,
            manufacturer TEXT,
            first_seen TEXT,
            last_seen TEXT,
            connection_count INTEGER DEFAULT 0,
            trusted INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scan_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_type TEXT,
            drive_path TEXT,
            started_at TEXT,
            finished_at TEXT,
            files_scanned INTEGER DEFAULT 0,
            infected_count INTEGER DEFAULT 0,
            duplicate_groups INTEGER DEFAULT 0,
            total_size_readable TEXT,
            status TEXT DEFAULT 'running',
            result_json TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            event_type TEXT,
            message TEXT,
            details TEXT
        )
    """)
    conn.commit()
    conn.close()
    _set_default_settings()

def _set_default_settings():
    defaults = {
        "auto_scan_prompt": "1",
        "eject_on_block": "1",
        "auto_scan_on_insert": "0",
        "scan_size_limit_mb": "0",
        "quarantine_threats": "0",
        "notification_sound": "1",
        "theme": "dark",
        "start_protection_on_launch": "1",
        "clamav_path": "",
    }
    for key, value in defaults.items():
        if get_setting(key) is None:
            set_setting(key, value)

def get_setting(key, default=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else default

def set_setting(key, value):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """, (key, str(value)))
    conn.commit()
    conn.close()

def get_all_settings():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    rows = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}

def record_drive_connection(serial_number, drive_letter):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    cursor.execute("SELECT serial_number FROM drives WHERE serial_number = ?", (serial_number,))
    existing = cursor.fetchone()

    if existing:
        cursor.execute("""
            UPDATE drives
            SET last_seen = ?, drive_letter = ?, connection_count = connection_count + 1
            WHERE serial_number = ?
        """, (now, drive_letter, serial_number))
    else:
        cursor.execute("""
            INSERT INTO drives (serial_number, drive_letter, first_seen, last_seen, connection_count, trusted)
            VALUES (?, ?, ?, ?, 1, 0)
        """, (serial_number, drive_letter, now, now))

    conn.commit()
    conn.close()

def is_trusted(serial_number):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT trusted FROM drives WHERE serial_number = ?", (serial_number,))
    result = cursor.fetchone()
    conn.close()
    return result is not None and result[0] == 1

def set_trusted(serial_number, trusted_value):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE drives SET trusted = ? WHERE serial_number = ?", (trusted_value, serial_number))
    conn.commit()
    conn.close()

def list_all_drives():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT serial_number, drive_letter, connection_count, trusted FROM drives")
    rows = cursor.fetchall()
    conn.close()
    return rows

def list_all_drives_detailed():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT serial_number, drive_letter, connection_count, trusted, first_seen, last_seen
        FROM drives ORDER BY last_seen DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

def forget_drive(serial_number):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM drives WHERE serial_number = ?", (serial_number,))
    conn.commit()
    conn.close()

# --------------- Activity Log ---------------

def log_activity(event_type, message, details=None):
    """Log an event to the activity_log table."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    details_str = json.dumps(details) if details else None
    cursor.execute(
        "INSERT INTO activity_log (timestamp, event_type, message, details) VALUES (?, ?, ?, ?)",
        (now, event_type, message, details_str)
    )
    conn.commit()
    conn.close()

def get_activity_log(limit=100):
    """Get recent activity log entries."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, timestamp, event_type, message, details FROM activity_log ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {"id": r[0], "timestamp": r[1], "event_type": r[2], "message": r[3],
         "details": json.loads(r[4]) if r[4] else None}
        for r in rows
    ]

def clear_activity_log():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM activity_log")
    conn.commit()
    conn.close()

# --------------- Scan History ---------------

def save_scan_history(scan_type, drive_path, started_at, finished_at=None,
                      files_scanned=0, infected_count=0, duplicate_groups=0,
                      total_size_readable="", status="running", result_json=None):
    """Save a scan record and return its id."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO scan_history
            (scan_type, drive_path, started_at, finished_at, files_scanned,
             infected_count, duplicate_groups, total_size_readable, status, result_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (scan_type, drive_path, started_at, finished_at, files_scanned,
          infected_count, duplicate_groups, total_size_readable, status,
          json.dumps(result_json) if result_json else None))
    scan_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return scan_id

def update_scan_history(scan_id, **kwargs):
    """Update fields of an existing scan_history row."""
    conn = get_connection()
    cursor = conn.cursor()
    allowed = {"finished_at", "files_scanned", "infected_count", "duplicate_groups",
               "total_size_readable", "status", "result_json"}
    sets = []
    vals = []
    for k, v in kwargs.items():
        if k in allowed:
            if k == "result_json":
                v = json.dumps(v) if v is not None else None
            sets.append(f"{k} = ?")
            vals.append(v)
    if sets:
        vals.append(scan_id)
        cursor.execute(f"UPDATE scan_history SET {', '.join(sets)} WHERE id = ?", vals)
        conn.commit()
    conn.close()

def get_scan_history(limit=50):
    """Get recent scan history entries."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, scan_type, drive_path, started_at, finished_at,
               files_scanned, infected_count, duplicate_groups,
               total_size_readable, status
        FROM scan_history ORDER BY id DESC LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [
        {"id": r[0], "scan_type": r[1], "drive_path": r[2], "started_at": r[3],
         "finished_at": r[4], "files_scanned": r[5], "infected_count": r[6],
         "duplicate_groups": r[7], "total_size_readable": r[8], "status": r[9]}
        for r in rows
    ]


if __name__ == "__main__":
    init_db()
    print("Database created at:", DB_PATH)