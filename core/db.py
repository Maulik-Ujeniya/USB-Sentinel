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

if __name__ == "__main__":
    init_db()
    print("Database created at:", DB_PATH)