"""Tests for SQLite database schema, initialization, and foreign key enforcement."""
import sqlite3
import pytest

from app.db import get_db, init_db


def test_tables_created_on_initialization(app):
    with app.app_context():
        db = get_db()
        tables = {
            row["name"]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "persons" in tables
        assert "facial_images" in tables


def test_foreign_keys_are_enforced(app):
    with app.app_context():
        db = get_db()
        fk_status = db.execute("PRAGMA foreign_keys;").fetchone()[0]
        assert fk_status == 1

        # Inserting a facial_image for a non-existent person must fail
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO facial_images (person_id, file_path, created_at) VALUES (?, ?, ?)",
                (9999, "fake.jpg", "2026-10-12T00:00:00Z"),
            )
            db.commit()


def test_cascading_delete(app):
    with app.app_context():
        db = get_db()
        # Insert a person
        cursor = db.execute(
            "INSERT INTO persons (name, created_at, updated_at) VALUES (?, ?, ?)",
            ("Test Person", "2026-10-12T00:00:00Z", "2026-10-12T00:00:00Z"),
        )
        person_id = cursor.lastrowid

        # Insert associated image
        db.execute(
            "INSERT INTO facial_images (person_id, file_path, created_at) VALUES (?, ?, ?)",
            (person_id, "test_pic.jpg", "2026-10-12T00:00:00Z"),
        )
        db.commit()

        # Confirm image exists
        img_before = db.execute(
            "SELECT id FROM facial_images WHERE person_id = ?", (person_id,)
        ).fetchone()
        assert img_before is not None

        # Delete person
        db.execute("DELETE FROM persons WHERE id = ?", (person_id,))
        db.commit()

        # Image should be cascade-deleted by SQLite foreign key ON DELETE CASCADE
        img_after = db.execute(
            "SELECT id FROM facial_images WHERE person_id = ?", (person_id,)
        ).fetchone()
        assert img_after is None


def test_safe_reinitialization(app):
    # Calling init_db multiple times must not raise errors or duplicate tables
    with app.app_context():
        init_db(app)
        init_db(app)
        db = get_db()
        assert db.execute("SELECT COUNT(*) FROM persons").fetchone()[0] == 0
