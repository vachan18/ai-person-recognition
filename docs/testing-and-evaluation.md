# Testing, Benchmark Evaluation, and Verification Report

This document records the empirical testing, quantitative benchmarks, and evaluation procedures conducted for **Phase 7** of the **AI-Based Person and Facial Expression Recognition** project.

---

## 1. Test Environment Specification

All benchmarks and automated tests were executed locally on the primary development workstation without GPU acceleration or cloud offloading.

| Attribute | Specification |
| :--- | :--- |
| **Operating System** | Windows 11 Enterprise / Pro (Build 10.0.26340) |
| **Processor (CPU)** | Intel64 Family 6 Model 186 (Intel Core CPU, 64-bit architecture) |
| **System Memory (RAM)**| 16 GB |
| **Python Runtime** | Python 3.12.7 (64-bit) |
| **Computer Vision Engine** | OpenCV (`cv2`) version 4.13.0 |
| **Web Framework** | Flask 3.1.3 |
| **Numerical Processing** | NumPy 2.2.6 |
| **Database** | SQLite 3 (embedded, Python standard library) |
| **Test Framework** | Pytest 9.0.3 |

---

## 2. Automated Test Suite Results

The automated test suite covers the complete application across all 7 phases, executing 115 independent tests:

```
============================= test session starts =============================
platform win32 -- Python 3.12.7, pytest-9.0.3, pluggy-1.6.0
rootdir: C:\Users\vacha\Downloads\ai-person-recognition-phase1\ai-person-recognition
configfile: pytest.ini
testpaths: tests
collected 115 items

tests\test_app.py ........................                               [ 20%]
tests\test_database.py ....                                              [ 24%]
tests\test_evaluation_benchmarks.py .....                                [ 28%]
tests\test_expressions.py ...........                                    [ 38%]
tests\test_face_pipeline.py .............                                [ 49%]
tests\test_person_api.py ...................                             [ 66%]
tests\test_phase6_refinements.py ......                                  [ 71%]
tests\test_speech_and_live.py .....                                      [ 75%]
tests\test_validators.py ............................                    [100%]

============================= 115 passed in 5.43s =============================
```

### Breakdown by Test Module:
1. **`test_app.py` (24 tests):** Application factory, security headers (CSP, Permissions-Policy), static asset serving, error handlers, and `/api/health` Phase 7 capabilities.
2. **`test_database.py` (4 tests):** SQLite schema initialization, foreign key enforcement, cascading deletes across images and embeddings, and idempotent reinitialization.
3. **`test_evaluation_benchmarks.py` (5 tests):** Model initialization timings, YuNet & SFace latencies, cosine threshold discrimination, Softmax expression probability calibration, and end-to-end recognition service latency.
4. **`test_expressions.py` (11 tests):** MobileFaceNet FER ONNX initialization, 7 universal expression labels, crop alignment, uncertainty handling (< 0.45 threshold), unusable crop rejection, and structured score outputs.
5. **`test_face_pipeline.py` (13 tests):** YuNet face detection on valid/empty/invalid inputs, SFace embedding properties (shape, L2-norm, finite float32), multi-face composites, and threshold boundary classification.
6. **`test_person_api.py` (19 tests):** Person registration CRUD, validation of names and photos, photo serving with `no-store` headers, search query filtering, and photo replacement cleanup.
7. **`test_phase6_refinements.py` (6 tests):** UI mode badges, processing indicators, multi-face detail breakdown cards, `AbortController` cancellation guards, and `camera.js` hardware isolation invariant.
8. **`test_speech_and_live.py` (5 tests):** Web Speech controls rendering, duplicate announcement suppression policy, repeat button, and cooldown handling.
9. **`test_validators.py` (28 tests):** Person name sanitization, informed consent validation, image file extension validation, corrupt image rejection, and dimension boundaries.

---

## 3. Empirical Performance Measurements

Measurements were collected using high-resolution timers (`time.perf_counter()`) over multiple iterations on local CPU:

### 3.1 Model Initialization Time
| Model Subsystem | ONNX Weight File | File Size | Initialization Latency |
| :--- | :--- | :--- | :--- |
| **YuNet Face Detector** | `face_detection_yunet_2023mar.onnx` | 338 KB | **4.94 ms** |
| **SFace Recognizer** | `face_recognition_sface_2021dec.onnx` | 37.0 MB | **66.08 ms** |
| **MobileFaceNet FER** | `facial_expression_recognition_mobilefacenet_2022july.onnx` | 4.79 MB | **10.15 ms** |
| **Total Cold Startup** | All 3 Models | 42.1 MB | **81.17 ms** |

### 3.2 Single-Component Inference Latencies (Sample Face Frame)
| Processing Stage | Iterations | Mean Latency | Min Latency | Max Latency | Std Dev |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **YuNet Face Detection** | 30 runs | **13.95 ms** | 12.92 ms | 16.16 ms | 0.76 ms |
| **SFace Alignment & Extraction** | 30 runs | **9.00 ms** | 8.44 ms | 10.31 ms | 0.47 ms |
| **Cosine Similarity Match** | 200 runs | **0.028 ms** | 0.021 ms | 0.054 ms | 0.008 ms |
| **MobileFaceNet FER Inference** | 30 runs | **3.71 ms** | 3.26 ms | 4.57 ms | 0.33 ms |
| **Total Pipeline Sum** | Combined | **26.68 ms** | — | — | — |

*Key finding:* A single-face inference pipeline executes in approximately **26.7 ms** on CPU, equivalent to a theoretical maximum throughput of **~37.5 frames per second (FPS)**. This comfortably operates within the live application's 1200 ms polling cadence with zero CPU saturation.

### 3.3 End-to-End API Response Time
- **`/api/recognize` POST (base64 image decode + detection + recognition + FER + JSON serialization):** **31.26 ms** average per frame.

### 3.4 Resource Consumption (Representative 50-Frame Session)
| Metric | Baseline (Pre-Inference) | Post-Inference (50 frames) | Delta |
| :--- | :--- | :--- | :--- |
| **Process Memory (RSS)** | 54.93 MB | 159.48 MB | +104.55 MB |
| **CPU Utilization** | Idle | ~16.6% | Moderate, efficient load |

---

## 4. Face Recognition Evaluation

### 4.1 Evaluation Methodology
- **Matching Metric:** Cosine similarity via `FaceRecognizerSF_FR_COSINE`.
- **Threshold Policy:**
  - $\text{Cosine Similarity} \ge 0.363$: **Recognized** (high-confidence identity match).
  - $0.300 \le \text{Cosine Similarity} < 0.363$: **Uncertain** (boundary match, flagged for re-attempt).
  - $\text{Cosine Similarity} < 0.300$: **Unknown** (no match found).

### 4.2 Measured Separation Characteristics
- **Same Identity (Identical Reference):** Cosine score = **1.0000** (Perfect self-match).
- **Random Orthogonal Face Vectors:** Cosine score = **0.0412** ($\ll 0.300$, cleanly rejected as Unknown).
- **Opposing Vector Test:** Cosine score = **-1.0000** (Full rejection).
- **False Match Risk Mitigation:** The two-stage threshold ($0.300$ and $0.363$) creates a 0.063 buffer zone that prevents borderline detections from being prematurely announced to visually impaired users as confirmed friends or family.

---

## 5. Facial Expression Evaluation

### 5.1 Model Specifications
- **Architecture:** MobileFaceNet (Progressive Teacher framework, Jiang et al., 2021).
- **Training Baseline:** Trained on RAF-DB (Real-world Affective Faces Database) with an 88.27% benchmark accuracy on static images.
- **Classes:** 7 basic universal facial emotion categories (`angry`, `disgust`, `fearful`, `happy`, `neutral`, `sad`, `surprised`).

### 5.2 Confidence Calibration & Uncertainty Handling
- Logits are passed through a numerical Softmax function ($P(c) = \frac{e^{z_c}}{\sum_k e^{z_k}}$).
- The sum of probabilities equals $1.0000 \pm 0.001$.
- Any prediction whose top class confidence is $< 0.45$ is categorized as `"uncertain"`.
- Any face crop smaller than $24 \times 24$ pixels is flagged as `"unusable"` without classification.

---

## 6. Manual Accessibility Audit

| Test Case | Description | Method | Result |
| :--- | :--- | :--- | :--- |
| **A11Y-01** | Full keyboard tab navigation across all buttons, inputs, and links | Manual Tab / Shift+Tab traversal | **Passed:** Clear 3px focus ring visible on every interactive element. |
| **A11Y-02** | Screen-reader live status updates | `aria-live="polite"` on `#recognition-announcement` and `#faces-detail-container` | **Passed:** Non-intrusive announcements rendered without interrupting ongoing speech. |
| **A11Y-03** | Color contrast ratio | WCAG AA / AAA evaluation on background vs text | **Passed:** Dark slate on off-white body satisfies $\ge 4.5:1$ contrast ratio. |
| **A11Y-04** | Camera permission denial handling | Simulate `NotAllowedError` | **Passed:** Clear banner displays instruction to enable camera in browser settings. |
| **A11Y-05** | Fallback without webcam | Use "Test photo upload" | **Passed:** File upload allows complete offline evaluation without physical webcam. |
| **A11Y-06** | Audio speech controls | Mute, repeat, rate selection (0.8x - 1.2x), and cooldown | **Passed:** Instant muting stops speech synthesis; repeat re-announces previous message. |

---

## 7. Known Limitations and Pending Evaluations

1. **Academic Dataset Benchmark Validation:** Full cross-dataset validation across extensive public benchmarks (e.g., LFW, CASIA-WebFace, AffectNet) requires gigabyte-scale licensed datasets and is marked as an extended academic research evaluation beyond the scope of this self-contained local prototype.
2. **Dynamic Lighting & Extreme Angles:** Faces turned beyond 45 degrees or in extreme low light (< 20 lux) may drop detection confidence below the YuNet threshold (0.6), which is reported honestly as "No faces detected" rather than misclassifying.
3. **Single Identity Gallery:** Multi-image gallery averaging per identity (e.g., 3-5 reference photos per person) is a documented future improvement that would increase angular tolerance.
