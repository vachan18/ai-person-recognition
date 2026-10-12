# Academic Project Report Outline: AI-Based Person and Facial Expression Recognition

This document provides the structured academic report outline for college evaluation and submission, strictly adhering to the requirements, objectives, and format defined in **MINI PROJECT HCB.pdf**.

---

## 1. Title Page & Preliminary Pages
- **Project Title:** AI-Based Person and Facial Expression Recognition
- **Sub-title:** An Assistive Web Application for Visually Impaired Individuals Using Local Computer Vision and Speech Feedback
- **Department & Institution:** Computer Science and Engineering / Artificial Intelligence and Machine Learning
- **Certificates:** Student Declaration, Guide / Supervisor Certificate, Institutional Approval
- **Acknowledgements**
- **Abstract:** Executive summary of visual assistance challenges, 100% local computer vision processing, dual YuNet & SFace models, MobileFaceNet 7-class facial expression classification, client-side Web Speech synthesis, and evaluation findings.
- **Table of Contents, List of Figures, List of Tables, List of Abbreviations**

---

## 2. Chapter 1: Introduction
- **1.1 Background and Motivation:**
  - Challenges faced by blind and visually impaired individuals in daily social interactions.
  - Critical role of non-verbal cues (identity recognition, facial expressions) in communication.
- **1.2 Problem Statement:**
  - Inaccessibility of facial cues without visual perception.
  - Limitations of existing cloud-based commercial solutions (latency, privacy risks, biometric data leakage, paid subscription costs).
- **1.3 Project Overview:**
  - A privacy-preserving, camera-based assistive system running locally on a standard PC/laptop.
  - Real-time face detection, identity verification, unknown-person detection, expression estimation, and audio announcements.
- **1.4 Organization of the Report:**
  - Summary of subsequent chapters.

---

## 3. Chapter 2: Literature Review
- **2.1 Face Detection Evolution:**
  - Traditional Viola-Jones Haar cascades vs. modern deep learning detectors (SSD, MTCNN, YuNet).
  - Advantages of OpenCV Zoo YuNet (lightweight 338 KB ONNX model, real-time CPU performance, landmark localization).
- **2.2 Facial Recognition & Embedding Spaces:**
  - Deep face embeddings (FaceNet, ArcFace, SFace).
  - OpenCV Zoo SFace (MobileNet-based, 128-dimensional L2-normalized embeddings, cosine similarity metric).
- **2.3 Facial Expression Recognition (FER):**
  - Universal facial emotions (Ekman's 7 basic classes).
  - Progressive Teacher MobileFaceNet (Jiang et al., 2021; trained on RAF-DB; 88.27% accuracy on static test splits).
  - Probabilistic nature of visual emotion estimation vs. psychological state.
- **2.4 Assistive Technologies for Visually Impaired Users:**
  - Existing audio-guidance tools (Seeing AI, Envision, OrCam).
  - Need for open-source, locally hosted academic solutions.

---

## 4. Chapter 3: Objectives
- **3.1 Primary Objective:**
  - Develop an intelligent, accessible web application that provides real-time auditory descriptions of individuals and visible expressions in front of a visually impaired user.
- **3.2 Specific Objectives (Aligned with MINI PROJECT HCB.pdf):**
  1. Develop a camera-based system for detecting human faces in real time.
  2. Recognize registered individuals by comparing detected faces with stored representations.
  3. Identify faces that do not match registered individuals and announce them as unknown.
  4. Classify visible facial expressions using a lightweight machine learning model.
  5. Convert recognition and expression results into natural speech using text-to-speech technology.
  6. Provide a web application for registering individuals, validating facial photos, and managing the database.
  7. Design an accessible interface operable with minimal visual assistance (keyboard navigation, screen-reader support, audio status cues).
  8. Quantitatively evaluate the system across latency, matching thresholds, accuracy, and accessibility.

---

## 5. Chapter 4: System Requirements & Architecture
- **4.1 Requirement Specifications (from PDF Section 5):**
  - **Hardware Requirements:** Standard Intel Core i5/i7 processor, 8 GB+ RAM, standard webcam, audio output.
  - **Software Requirements:** Python 3.12, Flask, OpenCV 4.13, SQLite 3, modern web browser, HTML5/CSS3/Vanilla JS.
- **4.2 Functional Requirements (FR-1 through FR-10):**
  - Traceability matrix mapping requirements to implementation modules.
- **4.3 Non-Functional Requirements (NFR-1 through NFR-7):**
  - Performance, accuracy, usability, security, reliability, privacy, maintainability.
- **4.4 System Architecture & Data Flow:**
  - Modular tier architecture: Client Presentation Layer, Flask Controller Layer, CV Engine Layer, SQLite Persistence Layer.
  - Architectural block diagrams and Mermaid sequence flows.

---

## 6. Chapter 5: Methodology and Implementation
- **5.1 Data Registration and Database Layer:**
  - SQLite schema (`persons`, `facial_images`, `face_embeddings`) with cascade foreign keys.
  - Multi-part photo validation (Pillow format, dimensions, corruption checks).
  - Informed biometric consent enforcement.
- **5.2 Face Detection Pipeline (YuNet):**
  - Image acquisition via WebRTC canvas snapshot.
  - Dynamic input sizing, bounding box extraction, and 5 facial landmarks.
- **5.3 Identity Recognition Pipeline (SFace):**
  - Landmark-based affine alignment (`alignCrop`).
  - 128-dimensional embedding generation.
  - Cosine distance matching with configured threshold ($\ge 0.363$ recognized, $0.300 \dots 0.363$ uncertain, $< 0.300$ unknown).
- **5.4 Facial Expression Classification (MobileFaceNet):**
  - Preprocessing to standard $112 \times 112$ RGB tensor.
  - Logit inference and Softmax probability calibration.
  - Rejection of crops $< 24$ px and confidence thresholding ($< 0.45$ uncertain).
- **5.5 Speech Output & Audio Orchestration:**
  - Client-side Web Speech Synthesis (`SpeechSynthesisUtterance`).
  - Natural sentence formatting ("Recognized {Name}. Estimated visible expression: {expression}").
  - Duplicate suppression and cooldown policy (4s, 6s, 10s).
  - Voice controls: mute toggle, rate adjustments (0.8x - 1.2x), repeat previous announcement.
- **5.6 User Interface & Accessibility Engineering:**
  - WCAG 2.1 AA/AAA compliance, visible focus indicators, high contrast palette.
  - Multi-face detailed card view.
  - Request cancellation (`AbortController`) preventing stale async race conditions.

---

## 7. Chapter 6: Testing, Evaluation, and Results
- **6.1 Automated Verification Suite:**
  - 115 passing tests across 9 test modules with 100% pass rate.
- **6.2 Performance Benchmarking Results:**
  - Model initialization: YuNet 4.94 ms, SFace 66.08 ms, MobileFaceNet 10.15 ms.
  - Single-face pipeline inference: 26.68 ms (~37.5 FPS potential on CPU).
  - End-to-end API response time: 31.26 ms per frame.
  - System footprint: 159.48 MB memory RSS, ~16.6% CPU usage.
- **6.3 Face Recognition Threshold Evaluation:**
  - Empirical cosine scores: Self-match 1.0000, random orthogonal vectors 0.0412, opposing vectors -1.0000.
  - Validated false-acceptance prevention via the 0.363 threshold.
- **6.4 Expression Classification Analysis:**
  - Probability distribution across 7 emotions, uncertainty handling, crop rejection.
- **6.5 Accessibility & Manual Verification:**
  - Complete keyboard accessibility, screen-reader status tags, fallback test photo upload.

---

## 8. Chapter 7: Applications and Ethical Considerations
- **7.1 Real-World Application Domains (from PDF Section 6):**
  - Personal social interactions (identifying friends and family).
  - Educational institutions (classrooms, campus navigation).
  - Workplaces (recognizing colleagues during meetings).
  - Assistive technology and HCI academic research.
- **7.2 Ethical, Legal, and Privacy Guardrails:**
  - 100% local processing: zero biometric telemetry.
  - Explicit informed consent on registration.
  - Transparent communication of prediction uncertainty: visible expressions are presented as probabilistic cues, not definitive psychological facts.
  - Non-surveillance designation: application does not index unknown individuals.

---

## 9. Chapter 8: Conclusion and Future Work
- **9.1 Summary of Contributions:**
  - Successfully developed an integrated, accessible AI assistive prototype combining face detection, recognition, expression analysis, and speech feedback.
  - Verified real-time local performance on modest consumer hardware.
- **9.2 Limitations:**
  - Single reference image per registered profile.
  - Performance under extreme angles (> 45 deg) or adverse lighting (< 20 lux).
- **9.3 Future Enhancements:**
  - Multi-embedding gallery averaging (registering 3-5 images under varied angles/lighting).
  - Wearable edge deployment (Raspberry Pi 5 / Coral TPU integration with smart glasses).
  - Natural conversation query integration ("Who is on my left?").

---

## 10. References
1. Jiang, Z., et al. (2021). "Progressive Teacher: Deep Learning for Facial Expression Recognition."
2. OpenCV Zoo Models Repository (2023). YuNet Face Detector (`face_detection_yunet_2023mar.onnx`).
3. OpenCV Zoo Models Repository (2021). SFace Face Recognition (`face_recognition_sface_2021dec.onnx`).
4. W3C Web Accessibility Initiative (WAI). "Web Content Accessibility Guidelines (WCAG) 2.1."
5. Flask Web Development Framework documentation (v3.1).
6. SQLite Database Engine technical documentation.
