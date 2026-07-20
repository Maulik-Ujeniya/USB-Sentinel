import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "usbsentinel.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

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
    conn.commit()
    conn.close()
    _set_default_settings()

def _set_default_settings():
    defaults = {"auto_scan_prompt": "1", "eject_on_block": "1"}
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

if __name__ == "__main__":
    init_db()
    print("Database created at:", DB_PATH)