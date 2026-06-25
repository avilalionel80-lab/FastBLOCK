import sqlite3
import os
from contextlib import contextmanager
from app.config import get_settings


def get_db_path() -> str:
    url = get_settings().database_url
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "")
    return "netshield.db"


def get_connection() -> sqlite3.Connection:
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                public_key TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'alumno',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS data_records (
                id TEXT PRIMARY KEY,
                encrypted_data TEXT NOT NULL,
                iv TEXT NOT NULL,
                tag TEXT NOT NULL,
                fragment1_hash TEXT,
                fragment2_hash TEXT,
                fragment3_hash TEXT,
                owner TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    finally:
        conn.close()
