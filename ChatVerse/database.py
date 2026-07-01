"""
ChatVerse V2 - database.py

SQLite wrapper for user registration and authentication.
"""

import sqlite3
from sqlite3 import Connection, Cursor
from pathlib import Path
from datetime import datetime
import hashlib
import os
from typing import Optional, Tuple
import config

DB_PATH = config.DB_PATH

def get_connection() -> Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def initialize_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            registered_at TEXT NOT NULL
        );
        """
    )
    conn.commit()
    conn.close()

def hash_password(password: str, salt: Optional[str] = None) -> str:
    """
    Hash password using SHA-256 with a salt.
    """
    if salt is None:
        salt = os.urandom(16).hex()
    hashed = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"{salt}${hashed}"

def verify_password(stored: str, provided: str) -> bool:
    try:
        salt, hashed = stored.split("$", 1)
    except ValueError:
        return False
    return hash_password(provided, salt) == stored

def register_user(username: str, password: str) -> Tuple[bool, str]:
    """
    Register a new user. Returns (success, message).
    """
    if not username or not password:
        return False, "Username and password cannot be empty."
    username = username.strip()
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM users WHERE username = ?;", (username,))
        if cur.fetchone():
            return False, "Username already exists."
        pw_hash = hash_password(password)
        cur.execute(
            "INSERT INTO users (username, password_hash, registered_at) VALUES (?, ?, ?);",
            (username, pw_hash, datetime.utcnow().isoformat()),
        )
        conn.commit()
        return True, "Registration successful."
    except sqlite3.Error as e:
        return False, f"Database error: {e}"
    finally:
        conn.close()

def authenticate_user(username: str, password: str) -> Tuple[bool, str]:
    """
    Authenticate user. Returns (success, message).
    """
    if not username or not password:
        return False, "Username and password cannot be empty."
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT password_hash FROM users WHERE username = ?;", (username,))
        row = cur.fetchone()
        if not row:
            return False, "Invalid username or password."
        stored_hash = row[0]
        if verify_password(stored_hash, password):
            return True, "Login successful."
        return False, "Invalid username or password."
    except sqlite3.Error as e:
        return False, f"Database error: {e}"
    finally:
        conn.close()

# Initialize DB on import
initialize_db()
