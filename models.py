import sqlite3
from datetime import datetime
from config import DATABASE_PATH

def get_db_connection():
    """Returns a SQLite connection with Row factory enabled."""
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """Initializes database schema with required tables and indexes."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('student', 'faculty', 'admin')),
            department TEXT NOT NULL,
            roll_or_emp_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL,
            department TEXT NOT NULL,
            location TEXT NOT NULL,
            specs TEXT,
            instructions TEXT,
            status TEXT DEFAULT 'available' CHECK(status IN ('available', 'maintenance', 'in_use', 'reserved')),
            image_icon TEXT DEFAULT 'chip',
            requires_approval INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            equipment_id INTEGER NOT NULL,
            booking_date TEXT NOT NULL,
            time_slot TEXT NOT NULL,
            purpose TEXT NOT NULL,
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected', 'completed', 'cancelled', 'rescheduled')),
            reviewed_by INTEGER,
            review_comments TEXT,
            conflict_group_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (equipment_id) REFERENCES equipment(id),
            FOREIGN KEY (reviewed_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS project_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            equipment_id INTEGER NOT NULL,
            project_title TEXT NOT NULL,
            project_description TEXT NOT NULL,
            department TEXT NOT NULL,
            project_deadline TEXT NOT NULL,
            preferred_date TEXT NOT NULL,
            preferred_slot TEXT NOT NULL,
            duration_hours INTEGER DEFAULT 2,
            reason TEXT NOT NULL,
            urgency TEXT DEFAULT 'medium' CHECK(urgency IN ('low', 'medium', 'high', 'critical')),
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected', 'resolved')),
            faculty_comments TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (equipment_id) REFERENCES equipment(id)
        );

        CREATE TABLE IF NOT EXISTS conflict_resolutions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conflict_key TEXT NOT NULL,
            equipment_id INTEGER NOT NULL,
            conflict_date TEXT NOT NULL,
            time_slot TEXT NOT NULL,
            winning_id INTEGER,
            winning_user_name TEXT,
            competing_id INTEGER,
            competing_user_name TEXT,
            scores_json TEXT,
            reasoning TEXT,
            alternative_recommendation TEXT,
            status TEXT DEFAULT 'recommended' CHECK(status IN ('recommended', 'approved', 'dismissed')),
            resolved_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (equipment_id) REFERENCES equipment(id),
            FOREIGN KEY (resolved_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            type TEXT DEFAULT 'info' CHECK(type IN ('info', 'success', 'warning', 'conflict')),
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE INDEX IF NOT EXISTS idx_bookings_lookup ON bookings(equipment_id, booking_date, time_slot, status);
        CREATE INDEX IF NOT EXISTS idx_project_requests_lookup ON project_requests(equipment_id, preferred_date, preferred_slot, status);
        CREATE INDEX IF NOT EXISTS idx_equipment_dept ON equipment(department, category, status);
        CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read);
        """)
        conn.commit()
    finally:
        conn.close()

def query_db(query, args=(), one=False):
    """Executes a parameterized query safely and returns results as dictionaries."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(query, args)
        rv = cur.fetchall()
        if rv:
            return (dict(rv[0])) if one else [dict(r) for r in rv]
        return None if one else []
    finally:
        conn.close()

def execute_db(query, args=()):
    """Executes an INSERT, UPDATE, or DELETE query safely with automatic commit and close."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(query, args)
        conn.commit()
        last_id = cur.lastrowid
        return last_id
    finally:
        conn.close()

def create_notification(user_id, title, message, notif_type='info'):
    """Helper to dispatch notification to user."""
    return execute_db(
        "INSERT INTO notifications (user_id, title, message, type) VALUES (?, ?, ?, ?)",
        (user_id, title, message, notif_type)
    )
