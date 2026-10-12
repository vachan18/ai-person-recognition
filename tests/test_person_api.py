"""Tests for Person registration, profile management, and protected image endpoints."""
import io
import os
import pytest


def test_list_persons_empty_initially(client):
    resp = client.get("/api/persons")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["count"] == 0
    assert data["persons"] == []


def test_create_person_success(client, sample_face_bytes, app):
    resp = client.post(
        "/api/persons",
        data={
            "name": "Grace Hopper",
            "consent": "true",
            "image": (io.BytesIO(sample_face_bytes), "grace.jpg"),
        },
        content_type="multipart/form-data",
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["message"] == "Person registered successfully."
    person = data["person"]
    assert person["name"] == "Grace Hopper"
    assert person["has_image"] is True
    assert person["image_url"] == f"/api/persons/{person['id']}/image"
    # Ensure no internal filesystem paths leak
    assert "data" not in person
    assert "upload" not in person
    assert "file_path" not in person


def test_create_person_rejects_photo_with_no_face(client, sample_image_bytes):
    resp = client.post(
        "/api/persons",
        data={
            "name": "No Face User",
            "consent": "true",
            "image": (io.BytesIO(sample_image_bytes), "blank.jpg"),
        },
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert "no face was detected" in data["error"]["message"].lower()


def test_create_person_requires_name(client, sample_face_bytes):
    resp = client.post(
        "/api/persons",
        data={
            "name": "   ",
            "consent": "true",
            "image": (io.BytesIO(sample_face_bytes), "grace.jpg"),
        },
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert "name is required" in data["error"]["message"].lower()


def test_create_person_requires_consent(client, sample_face_bytes):
    resp = client.post(
        "/api/persons",
        data={
            "name": "Ada Lovelace",
            "image": (io.BytesIO(sample_face_bytes), "ada.jpg"),
        },
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert "consent is required" in data["error"]["message"].lower()


def test_create_person_requires_image(client):
    resp = client.post(
        "/api/persons",
        data={"name": "Ada Lovelace", "consent": "true"},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert "image file is required" in data["error"]["message"].lower()


def test_create_person_rejects_corrupted_image(client):
    resp = client.post(
        "/api/persons",
        data={
            "name": "Corrupt Person",
            "consent": "true",
            "image": (io.BytesIO(b"fake data"), "corrupt.jpg"),
        },
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "corrupt" in data["error"]["message"].lower() or "not a valid" in data["error"]["message"].lower()


def test_get_person_by_id(client, sample_face_bytes):
    create_resp = client.post(
        "/api/persons",
        data={
            "name": "Margaret Hamilton",
            "consent": "true",
            "image": (io.BytesIO(sample_face_bytes), "margaret.jpg"),
        },
        content_type="multipart/form-data",
    )
    person_id = create_resp.get_json()["person"]["id"]

    get_resp = client.get(f"/api/persons/{person_id}")
    assert get_resp.status_code == 200
    data = get_resp.get_json()
    assert data["status"] == "ok"
    assert data["person"]["id"] == person_id
    assert data["person"]["name"] == "Margaret Hamilton"
    assert data["person"]["has_embedding"] is True


def test_get_nonexistent_person_returns_404(client):
    resp = client.get("/api/persons/9999")
    assert resp.status_code == 404
    data = resp.get_json()
    assert data["status"] == "error"
    assert data["error"]["code"] == 404


def test_update_person_name(client, sample_face_bytes):
    create_resp = client.post(
        "/api/persons",
        data={
            "name": "Hedy Lamarr",
            "consent": "true",
            "image": (io.BytesIO(sample_face_bytes), "hedy.jpg"),
        },
        content_type="multipart/form-data",
    )
    person_id = create_resp.get_json()["person"]["id"]

    # Update via JSON
    update_resp = client.put(
        f"/api/persons/{person_id}",
        json={"name": "Hedy Kiesler Lamarr"},
    )
    assert update_resp.status_code == 200
    assert update_resp.get_json()["person"]["name"] == "Hedy Kiesler Lamarr"

    # Verify updated via GET
    get_resp = client.get(f"/api/persons/{person_id}")
    assert get_resp.get_json()["person"]["name"] == "Hedy Kiesler Lamarr"


def test_update_person_name_rejects_empty(client, sample_face_bytes):
    create_resp = client.post(
        "/api/persons",
        data={
            "name": "Katherine Johnson",
            "consent": "true",
            "image": (io.BytesIO(sample_face_bytes), "katherine.jpg"),
        },
        content_type="multipart/form-data",
    )
    person_id = create_resp.get_json()["person"]["id"]

    update_resp = client.put(
        f"/api/persons/{person_id}",
        json={"name": "   "},
    )
    assert update_resp.status_code == 400


def test_update_nonexistent_person_returns_404(client):
    resp = client.put("/api/persons/9999", json={"name": "Ghost"})
    assert resp.status_code == 404


def test_replace_person_image_cleans_up_old_file(client, sample_face_bytes, app):
    create_resp = client.post(
        "/api/persons",
        data={
            "name": "Alan Turing",
            "consent": "true",
            "image": (io.BytesIO(sample_face_bytes), "alan.jpg"),
        },
        content_type="multipart/form-data",
    )
    person_id = create_resp.get_json()["person"]["id"]

    # Check upload directory
    upload_dir = app.config["UPLOAD_DIR"]
    files_before = os.listdir(upload_dir)
    assert len(files_before) == 1
    old_file = files_before[0]

    # Replace with same face under png name
    replace_resp = client.post(
        f"/api/persons/{person_id}/image",
        data={"image": (io.BytesIO(sample_face_bytes), "new_alan.jpg")},
        content_type="multipart/form-data",
    )
    assert replace_resp.status_code == 200

    # Verify old file was deleted and only new file exists
    files_after = os.listdir(upload_dir)
    assert len(files_after) == 1
    assert old_file not in files_after


def test_replace_image_nonexistent_person_returns_404(client, sample_face_bytes):
    resp = client.post(
        "/api/persons/9999/image",
        data={"image": (io.BytesIO(sample_face_bytes), "test.jpg")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 404


def test_delete_person_removes_db_records_and_disk_files(client, sample_face_bytes, app):
    create_resp = client.post(
        "/api/persons",
        data={
            "name": "Claude Shannon",
            "consent": "true",
            "image": (io.BytesIO(sample_face_bytes), "claude.jpg"),
        },
        content_type="multipart/form-data",
    )
    person_id = create_resp.get_json()["person"]["id"]

    upload_dir = app.config["UPLOAD_DIR"]
    assert len(os.listdir(upload_dir)) == 1

    # Delete person
    del_resp = client.delete(f"/api/persons/{person_id}")
    assert del_resp.status_code == 200
    assert del_resp.get_json()["status"] == "ok"

    # Verify 404 on get
    assert client.get(f"/api/persons/{person_id}").status_code == 404

    # Verify file deleted from disk
    assert len(os.listdir(upload_dir)) == 0


def test_delete_nonexistent_person_returns_404(client):
    resp = client.delete("/api/persons/9999")
    assert resp.status_code == 404


def test_serve_image_successfully(client, sample_face_bytes):
    create_resp = client.post(
        "/api/persons",
        data={
            "name": "Radia Perlman",
            "consent": "true",
            "image": (io.BytesIO(sample_face_bytes), "radia.jpg"),
        },
        content_type="multipart/form-data",
    )
    person_id = create_resp.get_json()["person"]["id"]

    img_resp = client.get(f"/api/persons/{person_id}/image")
    assert img_resp.status_code == 200
    assert img_resp.mimetype == "image/jpeg"
    assert "no-store" in img_resp.headers["Cache-Control"]
    assert img_resp.data == sample_face_bytes


def test_serve_image_not_found(client):
    resp = client.get("/api/persons/9999/image")
    assert resp.status_code == 404


def test_search_persons_filtering(client, sample_face_bytes):
    names = ["Alice Smith", "Bob Jones", "Alice Cooper"]
    for n in names:
        client.post(
            "/api/persons",
            data={
                "name": n,
                "consent": "true",
                "image": (io.BytesIO(sample_face_bytes), f"{n}.jpg"),
            },
            content_type="multipart/form-data",
        )

    # Search for alice
    resp_alice = client.get("/api/persons?q=alice")
    data_alice = resp_alice.get_json()
    assert data_alice["count"] == 2
    matched_names = [p["name"] for p in data_alice["persons"]]
    assert "Alice Smith" in matched_names
    assert "Alice Cooper" in matched_names

    # Search for bob
    resp_bob = client.get("/api/persons?q=bob")
    assert resp_bob.get_json()["count"] == 1

    # Search for non-existing
    resp_none = client.get("/api/persons?q=nonexistent")
    assert resp_none.get_json()["count"] == 0
