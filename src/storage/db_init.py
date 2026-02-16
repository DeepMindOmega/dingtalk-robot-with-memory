"""
Database initialization script for Intelligent Memory System
Creates SQLite database with required tables: memories, config_history, agent_metrics
"""

import sqlite3
import os
from datetime import datetime


def init_database(db_path: str = None) -> sqlite3.Connection:
    """
    Initialize SQLite database with required tables.

    Args:
        db_path: Path to database file. If None, uses default path.

    Returns:
        SQLite connection object
    """
    if db_path is None:
        db_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "memory_system.db"
        )
        db_path = os.path.abspath(db_path)

    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT,
            source TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            expires_at TEXT,
            score REAL DEFAULT 0.0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS config_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            config_data TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            accuracy REAL DEFAULT 0.0,
            response_time REAL DEFAULT 0.0,
            tasks_completed INTEGER DEFAULT 0,
            timestamp TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_type TEXT NOT NULL,
            priority TEXT NOT NULL,
            schedule TEXT,
            retry_count INTEGER DEFAULT 3,
            max_retries INTEGER DEFAULT 3,
            status TEXT NOT NULL,
            last_run_at TEXT,
            next_run_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            error_message TEXT,
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_type TEXT NOT NULL,
            start_date TEXT,
            end_date TEXT,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_source ON memories(source)")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at)"
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_tasks_next_run_at ON tasks(next_run_at)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_task_logs_task_id ON task_logs(task_id)"
    )

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_reports_type ON reports(report_type)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports(created_at)"
    )

    conn.commit()
    print(f"✓ Database initialized at: {db_path}")
    return conn


def get_connection(db_path: str = None) -> sqlite3.Connection:
    """
    Get a database connection.

    Args:
        db_path: Path to database file. If None, uses default path.

    Returns:
        SQLite connection object
    """
    if db_path is None:
        db_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "memory_system.db"
        )
        db_path = os.path.abspath(db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


if __name__ == "__main__":
    conn = init_database()
    print("✓ All tables created successfully")

    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"✓ Tables: {[t[0] for t in tables]}")

    conn.close()
