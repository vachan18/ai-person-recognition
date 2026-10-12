"""Service layer for Person profiles and facial image storage."""
import json
import logging
import mimetypes
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from flask import current_app

from app.db import get_db

log = logging.getLogger(__name__)


def _get_upload_dir() -> str:
    """Return the absolute path to the protected upload directory."""
    upload_dir = current_app.config.get("UPLOAD_DIR")
    if not upload_dir:
        upload_dir = os.path.join(current_app.config["DATA_DIR"], "faces")
    abs_dir = os.path.abspath(upload_dir)
    os.makedirs(abs_dir, exist_ok=True)
    return abs_dir


def _safe_remove_file(file_path: str) -> None:
    """Safely delete a file from disk, logging warnings if missing or error occurs."""
    if not file_path:
        return
    try:
        if os.path.isfile(file_path):
            os.remove(file_path)
            log.info("Safely removed file: %s", os.path.basename(file_path))
    except OSError as exc:
        log.warning("Could not delete file %s: %s", file_path, exc)


def _resolve_safe_file_path(filename: str) -> Optional[str]:
    """Verify that a filename resolves strictly within the protected upload directory."""
    if not filename:
        return None
    upload_dir = _get_upload_dir()
    # Strip any directory path components to avoid path traversal
    base_name = os.path.basename(filename)
    full_path = os.path.abspath(os.path.join(upload_dir, base_name))
    
    # Path traversal protection check
    if not full_path.startswith(upload_dir + os.sep) and full_path != upload_dir:
        log.warning("Path traversal attempt detected with filename: %s", filename)
        return None
    return full_path


class PersonService:
    """Manages Person profiles and their associated facial images."""

    @staticmethod
    def list_persons(search_query: Optional[str] = None) -> List[Dict[str, Any]]:
        """List registered persons with optional case-insensitive name filtering."""
        db = get_db()
        sql = """
            SELECT 
                p.id, 
                p.name, 
                p.created_at, 
                p.updated_at,
                i.id AS image_id
            FROM persons p
            LEFT JOIN facial_images i ON p.id = i.person_id
        """
        params: List[Any] = []

        if search_query and search_query.strip():
            sql += " WHERE LOWER(p.name) LIKE ? ORDER BY p.name COLLATE NOCASE ASC"
            params.append(f"%{search_query.strip().lower()}%")
        else:
            sql += " ORDER BY p.created_at DESC"

        rows = db.execute(sql, params).fetchall()
        result = []
        for row in rows:
            has_image = row["image_id"] is not None
            result.append(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "has_image": has_image,
                    "image_url": f"/api/persons/{row['id']}/image" if has_image else None,
                }
            )
        return result

    @staticmethod
    def get_person(person_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a person's profile and image metadata by ID."""
        db = get_db()
        row = db.execute(
            """
            SELECT 
                p.id, 
                p.name, 
                p.created_at, 
                p.updated_at,
                i.id AS image_id,
                i.metadata AS image_metadata
            FROM persons p
            LEFT JOIN facial_images i ON p.id = i.person_id
            WHERE p.id = ?
            """,
            (person_id,),
        ).fetchone()

        if not row:
            return None

        metadata = None
        if row["image_metadata"]:
            try:
                metadata = json.loads(row["image_metadata"])
            except (json.JSONDecodeError, TypeError):
                metadata = None

        has_image = row["image_id"] is not None
        return {
            "id": row["id"],
            "name": row["name"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "has_image": has_image,
            "image_url": f"/api/persons/{row['id']}/image" if has_image else None,
            "image_metadata": metadata,
        }

    @staticmethod
    def create_person(
        name: str,
        image_bytes: bytes,
        extension: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new person record and store their facial image transactionally."""
        upload_dir = _get_upload_dir()
        safe_filename = f"{uuid.uuid4().hex}.{extension}"
        file_path = os.path.join(upload_dir, safe_filename)

        # Write file to disk first
        with open(file_path, "wb") as f:
            f.write(image_bytes)

        db = get_db()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        try:
            cursor = db.execute(
                "INSERT INTO persons (name, created_at, updated_at) VALUES (?, ?, ?)",
                (name, now, now),
            )
            person_id = cursor.lastrowid

            db.execute(
                """
                INSERT INTO facial_images (person_id, file_path, created_at, metadata)
                VALUES (?, ?, ?, ?)
                """,
                (person_id, safe_filename, now, json.dumps(metadata)),
            )
            db.commit()
        except Exception:
            db.rollback()
            _safe_remove_file(file_path)
            log.exception("Failed to insert person into database, rolled back and removed file.")
            raise

        person = PersonService.get_person(person_id)
        if not person:
            raise RuntimeError("Person was inserted but could not be retrieved.")
        return person

    @staticmethod
    def update_person_name(person_id: int, new_name: str) -> Optional[Dict[str, Any]]:
        """Update a person's name."""
        db = get_db()
        # Verify existence
        exists = db.execute("SELECT id FROM persons WHERE id = ?", (person_id,)).fetchone()
        if not exists:
            return None

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        db.execute(
            "UPDATE persons SET name = ?, updated_at = ? WHERE id = ?",
            (new_name, now, person_id),
        )
        db.commit()
        return PersonService.get_person(person_id)

    @staticmethod
    def replace_person_image(
        person_id: int,
        image_bytes: bytes,
        extension: str,
        metadata: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Replace an existing person's facial image and remove the obsolete file."""
        db = get_db()
        person_row = db.execute("SELECT id FROM persons WHERE id = ?", (person_id,)).fetchone()
        if not person_row:
            return None

        existing_img_row = db.execute(
            "SELECT id, file_path FROM facial_images WHERE person_id = ?",
            (person_id,),
        ).fetchone()

        old_file_path = None
        if existing_img_row and existing_img_row["file_path"]:
            old_file_path = _resolve_safe_file_path(existing_img_row["file_path"])

        upload_dir = _get_upload_dir()
        new_filename = f"{uuid.uuid4().hex}.{extension}"
        new_file_path = os.path.join(upload_dir, new_filename)

        # Write new image to disk
        with open(new_file_path, "wb") as f:
            f.write(image_bytes)

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        try:
            if existing_img_row:
                db.execute(
                    """
                    UPDATE facial_images 
                    SET file_path = ?, created_at = ?, metadata = ?
                    WHERE person_id = ?
                    """,
                    (new_filename, now, json.dumps(metadata), person_id),
                )
            else:
                db.execute(
                    """
                    INSERT INTO facial_images (person_id, file_path, created_at, metadata)
                    VALUES (?, ?, ?, ?)
                    """,
                    (person_id, new_filename, now, json.dumps(metadata)),
                )

            db.execute("UPDATE persons SET updated_at = ? WHERE id = ?", (now, person_id))
            db.commit()
        except Exception:
            db.rollback()
            _safe_remove_file(new_file_path)
            log.exception("Failed to update facial image in database, rolled back.")
            raise

        # Clean up old file after successful transaction commit
        if old_file_path:
            _safe_remove_file(old_file_path)

        return PersonService.get_person(person_id)

    @staticmethod
    def delete_person(person_id: int) -> bool:
        """Delete a person and clean up their associated facial image files."""
        db = get_db()
        person_row = db.execute("SELECT id FROM persons WHERE id = ?", (person_id,)).fetchone()
        if not person_row:
            return False

        # Gather files to delete before cascade removes the DB records
        img_rows = db.execute(
            "SELECT file_path FROM facial_images WHERE person_id = ?",
            (person_id,),
        ).fetchall()
        files_to_delete = []
        for img in img_rows:
            path = _resolve_safe_file_path(img["file_path"])
            if path:
                files_to_delete.append(path)

        try:
            db.execute("DELETE FROM persons WHERE id = ?", (person_id,))
            db.commit()
        except Exception:
            db.rollback()
            log.exception("Failed to delete person with ID %s from database.", person_id)
            raise

        # Clean up files on disk after DB commit
        for path in files_to_delete:
            _safe_remove_file(path)

        return True

    @staticmethod
    def get_person_image_file(person_id: int) -> Optional[Tuple[str, str]]:
        """Return the absolute path and MIME type of a person's facial image."""
        db = get_db()
        img_row = db.execute(
            "SELECT file_path, metadata FROM facial_images WHERE person_id = ?",
            (person_id,),
        ).fetchone()

        if not img_row or not img_row["file_path"]:
            return None

        full_path = _resolve_safe_file_path(img_row["file_path"])
        if not full_path or not os.path.isfile(full_path):
            log.warning("Image file for person %s not found on disk: %s", person_id, full_path)
            return None

        # Determine mime type
        mime_type, _ = mimetypes.guess_type(full_path)
        if not mime_type:
            # Fallback based on extension
            ext = os.path.splitext(full_path)[1].lower()
            if ext in {".jpg", ".jpeg"}:
                mime_type = "image/jpeg"
            elif ext == ".png":
                mime_type = "image/png"
            elif ext == ".webp":
                mime_type = "image/webp"
            else:
                mime_type = "application/octet-stream"

        return full_path, mime_type
