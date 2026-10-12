# AI Person and Facial Expression Recognition

An intelligent, accessible assistive web application designed to help blind and visually impaired individuals recognize familiar people, identify unfamiliar individuals, and perceive visible facial cues in real time through spoken audio feedback.

Everything runs **100% locally on your computer** using lightweight deep learning models on CPU. No camera frames, facial embeddings, or voice outputs are ever transmitted to external cloud services or third-party APIs.

**Current status: Phase 7 (Final Testing, Evaluation, and Project Documentation Complete).**
Academic project developed in accordance with the specifications in `MINI PROJECT HCB.pdf`.

---

## 1. Problem Statement & Objectives

### Problem Statement
Visual impairment creates significant barriers in recognizing acquaintances, identifying unknown persons, and interpreting non-verbal facial expressions during everyday social interactions. While commercial cloud solutions exist, they frequently suffer from network latency, ongoing subscription costs, and severe biometric privacy risks.

### Project Objectives
1. **Real-time Face Detection:** Locate human faces in camera frames using a lightweight, locally executed deep learning model.
2. **Identity Recognition:** Compare detected facial representations against registered identities using cosine similarity.
3. **Unknown-Person Handling:** Accurately flag and announce un-registered individuals when matching is below threshold.
4. **Facial Expression Estimation:** Classify visible facial expressions into 7 universal categories using an independent classifier.
5. **Spoken Audio Feedback:** Convert recognition and expression results into natural spoken announcements via browser speech synthesis.
6. **Accessible Profile Management:** Provide accessible web interfaces to register consented individuals, upload/validate photos, and manage profiles.
7. **Accessibility-First Design:** Full keyboard accessibility (visible 3px focus rings), high contrast, polite screen-reader announcements, and graceful hardware error handling.
8. **Rigorous Local Evaluation:** Quantitatively evaluate latency, matching thresholds, memory/CPU footprint, and reliability on CPU.

---

## 2. System Architecture & Model Pipeline

The application combines three pre-trained, open-source computer vision models in ONNX format via OpenCV:

```
[Camera WebRTC Stream]
         │
         ▼ (1200ms cadence)
[YuNet Face Detector] ──────► Bounding box + 5 Facial Landmarks
         │                               │
         ├───────────────────────────────┤
         ▼                               ▼
[SFace Feature Extractor]      [MobileFaceNet Expression Classifier]
  • 128-d L2-normalized vector    • 5-point Affine Warping to 112x112
  • Cosine Match vs SQLite        • Softmax Probabilities (7 Classes)
  • Threshold: ≥ 0.363 Match      • Confidence Threshold: ≥ 0.45
         │                               │
         └───────────────┬───────────────┘
                         ▼
        [Structured Recognition Result]
                         │
                         ▼
        [Web Speech Synthesis Engine]
  "Recognized Alice. Estimated visible expression: smiling."
```

### Models Used
1. **Face Detection (YuNet):**
   - File: `models/face_detection_yunet_2023mar.onnx` (338 KB)
   - Source: OpenCV Zoo (`cv2.FaceDetectorYN`)
   - Latency: **~14.0 ms** on CPU
2. **Face Feature Extraction & Recognition (SFace):**
   - File: `models/face_recognition_sface_2021dec.onnx` (37.0 MB)
   - Source: OpenCV Zoo (`cv2.FaceRecognizerSF`)
   - Output: 128-dimensional L2-normalized float32 embedding
   - Latency: **~9.0 ms** on CPU
   - Cosine threshold: $\ge 0.363$ = Recognized, $0.300 \dots 0.363$ = Uncertain, $< 0.300$ = Unknown
3. **Facial Expression Classification (MobileFaceNet):**
   - File: `models/facial_expression_recognition_mobilefacenet_2022july.onnx` (4.79 MB)
   - Source: OpenCV Zoo Progressive Teacher (Jiang et al., 2021; trained on RAF-DB)
   - Classes: `angry`, `disgust`, `fearful`, `happy`, `neutral`, `sad`, `surprised`
   - Latency: **~3.7 ms** on CPU
   - Minimum face crop: 24 px; Uncertainty threshold: $< 0.45$ top confidence

---

## 3. Technology Stack

- **Backend:** Python 3.12, Flask 3.1.3, SQLite 3
- **Computer Vision & ML:** OpenCV 4.13.0 (`cv2.FaceDetectorYN`, `cv2.FaceRecognizerSF`, `cv2.dnn`), NumPy 2.2.6, Pillow 11.1.0
- **Frontend:** Vanilla HTML5, Accessible CSS3 (custom design system, no bloated frameworks), Vanilla JavaScript (strict CSP, no inline handlers)
- **Audio Feedback:** Web Speech Synthesis API (`window.speechSynthesis`, `SpeechSynthesisUtterance`)
- **Testing:** Pytest 9.0.3 (115 automated tests)

---

## 4. Hardware and System Requirements

| Component | Minimum Specification | Recommended Specification |
| :--- | :--- | :--- |
| **Processor** | Intel Core i3 / AMD Ryzen 3 or equivalent | Intel Core i5 / i7 / Ryzen 5 or equivalent |
| **RAM** | 4 GB | 8 GB or 16 GB |
| **Storage** | 500 MB free disk space | 2 GB free disk space |
| **Camera** | Built-in or USB webcam | 720p or 1080p webcam |
| **Audio** | Internal speaker or headphones | Internal speaker or headphones |
| **Operating System** | Windows 10/11, macOS, or Linux | Windows 11 / Ubuntu 22.04+ |

---

## 5. Installation and Setup Guide

### 1. Clone the Repository
```powershell
git clone https://github.com/vachan18/ai-person-recognition.git
cd ai-person-recognition
```

### 2. Set Up Python Virtual Environment
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```
*(If PowerShell restricts execution scripts, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first).*

### 3. Install Dependencies
```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

### 4. Verify Model Weights
Model weights are stored locally in `models/` (and excluded from Git by `.gitignore`):
- `models/face_detection_yunet_2023mar.onnx`
- `models/face_recognition_sface_2021dec.onnx`
- `models/facial_expression_recognition_mobilefacenet_2022july.onnx`

If weights are missing, download them from the official OpenCV Zoo repository:
- [YuNet 2023mar](https://github.com/opencv/opencv_zoo/tree/master/models/face_detection_yunet)
- [SFace 2021dec](https://github.com/opencv/opencv_zoo/tree/master/models/face_recognition_sface)
- [MobileFaceNet FER 2022july](https://github.com/opencv/opencv_zoo/tree/master/models/facial_expression_recognition)

---

## 6. Running the Application

Start the local Flask development server:
```powershell
python run.py
```

- **Dashboard:** Open [http://127.0.0.1:5000](http://127.0.0.1:5000)
- **Register Person:** [http://127.0.0.1:5000/register](http://127.0.0.1:5000/register)
- **Manage People:** [http://127.0.0.1:5000/manage](http://127.0.0.1:5000/manage)
- **System Health:** [http://127.0.0.1:5000/api/health](http://127.0.0.1:5000/api/health)

> **Important:** Always access via `http://127.0.0.1:5000` or `http://localhost:5000`. Browsers block webcam access on unencrypted non-localhost IP addresses.

---

## 7. How to Use the System

### 1. Register a Person
1. Navigate to **Register Person** (`/register`).
2. Enter the person's name (e.g., "Alice").
3. Upload a clear, front-facing reference photo (JPEG, PNG, or WebP).
4. Review and check the **Informed Biometric Consent** checkbox.
5. Select **Save Person**. The system computes and stores the 128-dimensional embedding in the local SQLite database.

### 2. Live Face Recognition & Spoken Feedback
1. On the **Dashboard** (`/`), select **Start Camera**.
2. Allow camera permissions when prompted by your browser.
3. Click **Recognize Face** for single-frame recognition, or toggle **Continuous mode (1.2s)** for live automated announcements.
4. Spoken audio feedback will announce:
   - Recognized person: *"Recognized Alice. Estimated visible expression: smiling."*
   - Unknown person: *"An unrecognized person is in front of you. Estimated visible expression: neutral."*
   - Uncertain match: *"Person not identified with confidence. Please try again."*
   - Multi-face scenes: *"Detected 2 people: Recognized Alice, 1 unrecognized person."*
5. Use the **Voice Controls** to mute, change speech speed (0.8x to 1.2x), adjust repeat cooldown (4s, 6s, 10s), or manually replay the announcement.

### 3. Testing Without a Physical Webcam
If no webcam is attached or camera access is blocked in your environment, use the **"Test photo upload"** button on the dashboard. Select any photo with faces to test the full pipeline offline.

---

## 8. Reproducible Final Demonstration Sequence

Follow this 10-step sequence for a complete college or project demonstration:
1. **Start Application:** Execute `python run.py` and open `http://127.0.0.1:5000/api/health` to confirm Phase 7 status.
2. **Open Dashboard:** Navigate to `http://127.0.0.1:5000`.
3. **Register Consenting Participant:** Go to `/register`, enter name "Test Participant", upload a clear reference photo, check the consent box, and submit.
4. **Verify Database Record:** Go to `/manage` to confirm the profile is listed, its thumbnail is visible, and the embedding count is updated.
5. **Start Camera Preview:** Return to the Dashboard and select "Start camera".
6. **Demonstrate Registered Recognition:** Stand in front of the camera (or upload the participant photo). Select "Recognize Face". The system displays a green badge and speaks: *"Recognized Test Participant."*
7. **Demonstrate Expression Analysis:** Smile or show an expression; confirm the audio announcements updates: *"Estimated visible expression: smiling."*
8. **Demonstrate Unknown Person:** Have an unregistered person face the camera. The system draws a red bounding box and announces: *"An unrecognized person is in front of you."*
9. **Demonstrate Voice Controls & Duplicate Suppression:** Enable continuous mode (1.2s). Show that identical frames are suppressed during the cooldown window. Click **Mute voice** to immediately cancel audio; click **Repeat announcement** to replay.
10. **Demonstrate Profile Management & Deletion:** Return to `/manage`, delete the test profile, and confirm cascade deletion cleans up disk images and SQLite embeddings.

---

## 9. Automated Testing and Benchmarks

Run the full automated test suite:
```powershell
pytest -v
```

**Results:** **115 passed tests in 5.43s** (100% pass rate).

### Measured Latency & Footprint on Local CPU:
- **YuNet Face Detection:** 13.95 ms
- **SFace Embedding Extraction:** 9.00 ms
- **MobileFaceNet Expression Analysis:** 3.71 ms
- **Cosine Gallery Matching:** 0.028 ms
- **Total Pipeline Inference:** **26.68 ms (~37.5 FPS potential on CPU)**
- **Process Memory Footprint:** 159.48 MB RSS post-inference
- **Process CPU Load:** ~16.6% during active recognition

---

## 10. Privacy, Ethics, and Security Architecture

- **100% Local Execution:** No video frames, face embeddings, or speech synthesis are sent outside the local machine.
- **Biometric Data Protection:** Reference photos are stored outside the public web root (`data/faces/`) and served only via protected endpoints with `Cache-Control: private, no-store`.
- **Informed Consent Enforcement:** The database enforces consent logging; profiles cannot be created without explicit consent affirmation.
- **Cascade Deletion:** Deleting a person profile deletes all associated database rows, binary embeddings, and disk photo files.
- **Probabilistic Assistance Guardrail:** The system explicitly frames expression predictions as probabilistic visual cues, not definitive psychological or emotional truth.
- **Non-Surveillance Designation:** The system does not attempt to catalog, identify, or track un-registered individuals.

---

## 11. Documentation Index

- [docs/architecture.md](docs/architecture.md): Complete system architecture, component breakdown, data flow, API endpoints, and Mermaid diagrams.
- [docs/testing-and-evaluation.md](docs/testing-and-evaluation.md): Quantitative benchmark data, test environment, threshold analysis, and accessibility audit.
- [docs/project-report-outline.md](docs/project-report-outline.md): Comprehensive academic project report outline structured according to `MINI PROJECT HCB.pdf`.

---

## 12. License & Academic Attribution

This project is developed for educational and academic research purposes as part of the College Mini-Project curriculum.
- Models: SFace, YuNet, and MobileFaceNet are provided by OpenCV Zoo under Apache 2.0 / BSD licensing.
