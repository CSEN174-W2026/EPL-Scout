# auth.py
# authentication: login, logout, signup functions

import sqlite3
import bcrypt
from pathlib import Path

DB_PATH = Path("data/users.db")

# create database connection
def get_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    return sqlite3.connect(DB_PATH, check_same_thread=False)

# create users table
def init_user_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash BLOB NOT NULL
        )
    """)

    conn.commit()
    conn.close()

# sign up - create new user
def create_user(username: str, password: str) -> bool:
    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, hashed_password)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

# user login - authenticate user
def auth_user(username: str, password: str) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, password_hash FROM users WHERE username = ?", 
        (username,)
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None
    
    user_id, stored_hash = row
    if bcrypt.checkpw(password.encode(), stored_hash):
        return user_id
    
    return None

