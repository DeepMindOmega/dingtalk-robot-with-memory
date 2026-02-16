import sqlite3
from pathlib import Path
from typing import Generator

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "src" / "data"
DB_PATH = DATA_DIR / "memory_system.db"


def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def get_db_path() -> Path:
    return DB_PATH


def get_memories_dir() -> Path:
    return BASE_DIR / "memories"


def get_reports_dir() -> Path:
    return BASE_DIR / "reports"
