# AI Person Recognition

An assistive web app, in development, that will tell visually impaired users who is in
front of the camera and what facial expression they show, using spoken announcements.
Everything runs locally on your computer.

**Current status: Phase 3 (AI Face Detection and Person Recognition).**
The Flask backend provides an accessible dashboard, webcam preview, local SQLite database layer,
person registration with image validation, profile management, and a local computer vision pipeline.
Face detection is powered by **OpenCV Zoo YuNet**, and identity recognition feature extraction is powered by **OpenCV Zoo SFace**.
Facial expression analysis and speech feedback are **not implemented yet** (scheduled for Phase 4 and Phase 5).

## AI Models and Recognition Pipeline (Phase 3)

1. **Face Detection (YuNet):**
   - Model: `face_detection_yunet_2023mar.onnx` via OpenCV's `cv2.FaceDetectorYN`.
   - Detects faces in camera frames or uploaded images, returning bounding boxes, detection confidence, and 5 facial landmarks (eyes, nose, mouth corners).
   - Handles multi-face frames and frames with no faces.
2. **Face Alignment & Feature Extraction (SFace):**
   - Model: `face_recognition_sface_2021dec.onnx` via OpenCV's `cv2.FaceRecognizerSF`.
   - Aligns detected face crops using 5 landmarks and extracts 128-dimensional L2-normalized feature vectors.
   - Embeddings are validated for numerical integrity (finite float32 values, no NaNs/Infs).
3. **Database Integration & Persistence:**
   - On person registration (`POST /api/persons`) or photo replacement (`POST /api/persons/<id>/image`), the system verifies that exactly one face is visible, extracts the embedding, and stores it in the `face_embeddings` table.
   - Embeddings are linked via foreign keys to `persons` and cascade-deleted on profile deletion.
4. **Matching & Threshold Calibration:**
   - Feature comparison is performed using cosine similarity via OpenCV (`FaceRecognizerSF_FR_COSINE`).
   - Default matching threshold is **`0.363`** (the official SFace benchmark threshold).
   - Cosine similarity $\ge 0.363$: **Recognized** (reports person ID and name).
   - Cosine similarity between $0.300$ and $0.363$: **Uncertain** (treated conservatively).
   - Cosine similarity $< 0.300$: **Unknown**.
   - *Threshold Calibration:* In real-world environments, optimal thresholds depend on lighting conditions, camera resolution, and angles. You can adjust `RECOGNITION_COSINE_THRESHOLD` in your `.env` file to balance False Acceptance Rate (FAR) and False Rejection Rate (FRR) using known-person and unknown-person evaluation images.

## Privacy and Security in Phase 3

- **100% Local Inference:** Face detection and recognition models execute locally using OpenCV on this computer. Video frames and facial crops are never sent to external AI APIs or cloud servers.
- **Biometric Notice & Consent:** Facial reference images are sensitive biometric data. The Register Person interface requires explicit confirmation of consent before storing reference photos.
- **Protected File Access:** Uploaded facial photos are stored outside `static/` (default `data/faces/`) and served strictly through application routes with `Cache-Control: private, no-store`.
- **Model Storage Safety:** Model ONNX files are placed in `models/` and are excluded from version control via `.gitignore`.
- **Access Control Requirement:** This prototype currently runs without authentication on `127.0.0.1`. Authentication and role-based access control MUST be implemented before deploying beyond a trusted local workstation.



## Requirements

- Windows with Python 3.10 or newer (developed and tested on Python 3.12; later phases may narrow this
  once the AI libraries are chosen).
- A modern browser (Edge, Chrome or Firefox) and a webcam.

## Setup (Windows PowerShell, from the project folder)

```powershell
# 1. Open the project folder (adjust the path)
cd C:\path\to\ai-person-recognition

# 2. See which Python versions are installed
py -0p
py --version

# 3. Create a virtual environment (use the version you want, e.g. 3.12)
py -3.12 -m venv .venv

# 4. Activate it
.\.venv\Scripts\Activate.ps1
```

If PowerShell says scripts are disabled, allow them for this window only, then activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

```powershell
# 5. Install dependencies (includes pytest for the tests)
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt

# 6. (Optional) create a local settings file
Copy-Item .env.example .env
```

In VS Code, choose the interpreter with **Ctrl+Shift+P → Python: Select Interpreter → `.venv`**.

## Run

```powershell
.\.venv\Scripts\Activate.ps1   # if not already active
python run.py
```

Open **http://127.0.0.1:5000** in your browser. Stop the server with **Ctrl+C**.
Health check: http://127.0.0.1:5000/api/health

> Use `127.0.0.1` or `localhost`. Browsers block camera access on other plain-HTTP addresses.

## Test

```powershell
python -m pytest
```

## Manual checks (browser)

These need a real browser and webcam, so they are not covered by the automated tests.

1. **Start/stop:** select *Start camera*, allow access, confirm live video and the status changes to
   "Camera on". Select *Stop camera*: video disappears, status says "Camera off", and the webcam
   light goes out.
2. **Permission denied:** block the camera (address-bar camera icon), select *Start camera*, confirm a
   clear error appears and you can retry after allowing access.
3. **No camera / in use:** unplug the webcam, or open it in another app, and confirm the matching message.
4. **Leaving the page:** with the camera on, close the tab or navigate away; the webcam light should go out.
5. **Keyboard only:** press Tab from the top. The first stop is "Skip to main content", then the
   navigation, then Start/Stop camera. Every focused item must show a visible outline. Start and
   stop the camera with Enter or Space; focus should stay on a usable button.
6. **Screen reader (NVDA or Narrator):** starting and stopping the camera should announce the new
   status; errors should be announced.
7. **Responsive:** resize the window (or use browser device mode) from desktop to ~360 px wide. No
   horizontal scrolling; controls stay readable and tappable.
8. **Zoom/text size:** zoom to 200% and confirm nothing is cut off.

## Project layout

```
app/
  __init__.py        create_app() application factory
  config.py          settings and safe defaults (reads environment / .env)
  db.py              SQLite connection handling and schema initialization
  validators.py      Input validation (names, consent, Pillow image decoding)
  services/
    person_service.py Transactional CRUD for persons and protected facial images
  errors.py          JSON errors for /api/*, HTML error page elsewhere
  security.py        CSP and privacy-related response headers
  routes/
    pages.py         Dashboard, Register Person, Manage People
    api.py           GET /api/health, /api/persons CRUD & protected image serving
  templates/         base, dashboard, register, manage, error
  static/css/        styles.css (high contrast, accessible focus, responsive)
  static/js/         camera.js, register.js, manage.js
tests/               pytest suite (database, validators, API CRUD, integration)
run.py               local entry point
```

## Not committed to Git

`.gitignore` excludes `.venv/`, `.env`, database files, face images/uploads, `instance/`, `data/`
and model weights, so secrets and biometric data are never committed by accident.
