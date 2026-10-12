"""SQLite database layer with foreign key enforcement and safe initialization."""
import os
import sqlite3
from typing import Optional
from flask import Flask, current_app, g


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS persons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS facial_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    created_at TEXT NOT NULL,
    metadata TEXT,
    FOREIGN KEY (person_id) REFERENCES persons (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_facial_images_person_id ON facial_images (person_id);
CREATE INDEX IF NOT EXISTS idx_persons_name ON persons (name);
"""


def get_db() -> sqlite3.Connection:
    """Return a database connection for the current request context."""
    if "db" not in g:
        db_path = current_app.config["DATABASE_PATH"]
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        g.db = conn
    return g.db


def close_db(e: Optional[BaseException] = None) -> None:
    """Close the database connection at the end of the request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app: Flask) -> None:
    """Initialize database directories and create tables safely on startup."""
    data_dir = app.config.get("DATA_DIR")
    if data_dir:
        os.makedirs(data_dir, exist_ok=True)

    upload_dir = app.config.get("UPLOAD_DIR")
    if upload_dir:
        os.makedirs(upload_dir, exist_ok=True)

    db_path = app.config["DATABASE_PATH"]
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.executescript(SCHEMA_SQL)
        conn.commit()


def init_app(app: Flask) -> None:
    """Register database teardown and run safe schema initialization."""
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db(app)
