"""Regression and end-to-end unit tests for Manage People: Identity Library redesign.

Verifies:
1. Empty directory state.
2. One registered profile.
3. Multiple registered profiles.
4. Searching for a profile.
5. No search results.
6. Editing a profile.
7. Replacing a photo.
8. Deleting a profile.
9. Database persistence across restarts.
10. Template layout, accessibility attributes, and strict CSP compliance.
"""
import io
import os
import pytest
from app import create_app
from app.config import TestingConfig


def test_scenario_1_empty_directory(client):
    """Scenario 1: Directory is empty initially."""
    resp = client.get("/api/persons")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["count"] == 0
    assert data["persons"] == []

    # Check HTML contains Identity Library empty state and controls
    html_resp = client.get("/manage")
    assert html_resp.status_code == 200
    html = html_resp.get_data(as_text=True)
    assert "Your directory starts here." in html
    assert "Biometric Identity Library" in html
    assert 'id="empty-state"' in html
    assert 'id="no-results-state"' in html
    assert 'id="loading-state"' in html
    assert 'id="people-count"' in html


def test_scenario_2_one_registered_profile(client, sample_face_bytes):
    """Scenario 2: Register one profile and verify presence in Identity Library."""
    create_resp = client.post(
        "/api/persons",
        data={
            "name": "Ada Lovelace",
            "consent": "true",
            "image": (io.BytesIO(sample_face_bytes), "ada.jpg"),
        },
        content_type="multipart/form-data",
    )
    assert create_resp.status_code == 201
    person = create_resp.get_json()["person"]
    assert person["name"] == "Ada Lovelace"

    list_resp = client.get("/api/persons")
    data = list_resp.get_json()
    assert data["count"] == 1
    assert data["persons"][0]["name"] == "Ada Lovelace"
    assert data["persons"][0]["has_image"] is True
    assert data["persons"][0]["has_embedding"] is True


def test_scenario_3_multiple_registered_profiles(client, sample_face_bytes):
    """Scenario 3: Multiple profiles registered in Identity Library."""
    for name in ["Ada Lovelace", "Grace Hopper", "Katherine Johnson"]:
        client.post(
            "/api/persons",
            data={
                "name": name,
                "consent": "true",
                "image": (io.BytesIO(sample_face_bytes), f"{name.lower().replace(' ', '_')}.jpg"),
            },
            content_type="multipart/form-data",
        )
    list_resp = client.get("/api/persons")
    data = list_resp.get_json()
    assert data["count"] == 3
    names = [p["name"] for p in data["persons"]]
    assert "Ada Lovelace" in names
    assert "Grace Hopper" in names
    assert "Katherine Johnson" in names


def test_scenario_4_search_for_profile(client, sample_face_bytes):
    """Scenario 4: Search query filters registered profiles."""
    for name in ["Alan Turing", "Alonzo Church", "Claude Shannon"]:
        client.post(
            "/api/persons",
            data={
                "name": name,
                "consent": "true",
                "image": (io.BytesIO(sample_face_bytes), "test.jpg"),
            },
            content_type="multipart/form-data",
        )
    # Search for "Turing"
    resp = client.get("/api/persons?q=turing")
    data = resp.get_json()
    assert data["count"] == 1
    assert data["persons"][0]["name"] == "Alan Turing"

    # Search for "Al" matches Alan and Alonzo
    resp_al = client.get("/api/persons?q=al")
    data_al = resp_al.get_json()
    assert data_al["count"] == 2


def test_scenario_5_no_search_results(client, sample_face_bytes):
    """Scenario 5: Search query with zero matches returns empty list."""
    client.post(
        "/api/persons",
        data={
            "name": "Margaret Hamilton",
            "consent": "true",
            "image": (io.BytesIO(sample_face_bytes), "test.jpg"),
        },
        content_type="multipart/form-data",
    )
    resp = client.get("/api/persons?q=nonexistentpersonxyz")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["count"] == 0
    assert data["persons"] == []


def test_scenario_6_edit_profile(client, sample_face_bytes):
    """Scenario 6: Update person name."""
    create_resp = client.post(
        "/api/persons",
        data={
            "name": "Grace Hopper",
            "consent": "true",
            "image": (io.BytesIO(sample_face_bytes), "test.jpg"),
        },
        content_type="multipart/form-data",
    )
    p_id = create_resp.get_json()["person"]["id"]

    edit_resp = client.put(
        f"/api/persons/{p_id}",
        json={"name": "Rear Admiral Grace Hopper"},
    )
    assert edit_resp.status_code == 200
    updated = edit_resp.get_json()["person"]
    assert updated["name"] == "Rear Admiral Grace Hopper"

    # Verify updated in listing
    get_resp = client.get(f"/api/persons/{p_id}")
    assert get_resp.get_json()["person"]["name"] == "Rear Admiral Grace Hopper"


def test_scenario_7_replace_photo(client, sample_face_bytes):
    """Scenario 7: Replace reference facial photo."""
    create_resp = client.post(
        "/api/persons",
        data={
            "name": "Hedy Lamarr",
            "consent": "true",
            "image": (io.BytesIO(sample_face_bytes), "hedy_initial.jpg"),
        },
        content_type="multipart/form-data",
    )
    p_id = create_resp.get_json()["person"]["id"]

    replace_resp = client.post(
        f"/api/persons/{p_id}/image",
        data={"image": (io.BytesIO(sample_face_bytes), "hedy_updated.jpg")},
        content_type="multipart/form-data",
    )
    assert replace_resp.status_code == 200
    data = replace_resp.get_json()
    assert data["status"] == "ok"
    assert "updated successfully" in data["message"].lower()

    # Image is downloadable
    img_resp = client.get(f"/api/persons/{p_id}/image")
    assert img_resp.status_code == 200
    assert len(img_resp.data) == len(sample_face_bytes)


def test_scenario_8_delete_profile(client, sample_face_bytes):
    """Scenario 8: Delete profile and verify biometric cleanup."""
    create_resp = client.post(
        "/api/persons",
        data={
            "name": "Temporary User",
            "consent": "true",
            "image": (io.BytesIO(sample_face_bytes), "temp.jpg"),
        },
        content_type="multipart/form-data",
    )
    p_id = create_resp.get_json()["person"]["id"]

    del_resp = client.delete(f"/api/persons/{p_id}")
    assert del_resp.status_code == 200
    assert del_resp.get_json()["status"] == "ok"

    # 404 on fetch
    assert client.get(f"/api/persons/{p_id}").status_code == 404
    assert client.get(f"/api/persons/{p_id}/image").status_code == 404

    # Directory count is 0
    assert client.get("/api/persons").get_json()["count"] == 0


def test_scenario_9_database_persistence_across_restart(tmp_path, sample_face_bytes):
    """Scenario 9: Data persists when app reinitializes pointing to same db."""
    db_file = str(tmp_path / "persist" / "app.db")
    upload_dir = str(tmp_path / "persist" / "faces")

    class PersistConfig(TestingConfig):
        DATA_DIR = str(tmp_path / "persist")
        DATABASE_PATH = db_file
        UPLOAD_DIR = upload_dir

    app1 = create_app(PersistConfig)
    with app1.test_client() as c1:
        c1.post(
            "/api/persons",
            data={
                "name": "Persistent Person",
                "consent": "true",
                "image": (io.BytesIO(sample_face_bytes), "persist.jpg"),
            },
            content_type="multipart/form-data",
        )
        assert c1.get("/api/persons").get_json()["count"] == 1

    # Simulate restart with new app instance on same files
    app2 = create_app(PersistConfig)
    with app2.test_client() as c2:
        list_data = c2.get("/api/persons").get_json()
        assert list_data["count"] == 1
        assert list_data["persons"][0]["name"] == "Persistent Person"
        assert list_data["persons"][0]["has_image"] is True


def test_scenario_10_accessibility_and_csp(client):
    """Scenario 10: Manage page accessibility attributes and strict CSP adherence."""
    resp = client.get("/manage")
    html = resp.get_data(as_text=True)

    # Required IDs for interaction & tests
    assert 'id="search-input"' in html
    assert 'id="clear-search-btn"' in html
    assert 'id="people-count"' in html
    assert 'id="loading-state"' in html
    assert 'id="empty-state"' in html
    assert 'id="no-results-state"' in html
    assert 'id="people-grid"' in html
    assert 'id="edit-modal"' in html
    assert 'id="replace-photo-modal"' in html
    assert 'id="delete-modal"' in html

    # Accessibility attributes
    assert 'role="dialog"' in html
    assert 'aria-modal="true"' in html
    assert 'role="status"' in html
    assert 'aria-live="polite"' in html
    assert 'aria-hidden="true"' in html

    # Strict CSP: no inline style or inline script handlers
    assert "style=" not in html
    assert "<script>" not in html
    assert "onclick=" not in html
