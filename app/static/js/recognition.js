/**
 * recognition.js - Frontend client for live face detection, person recognition,
 * facial expression classification, and accessible voice feedback (Phase 5).
 * Strictly adheres to CSP: self-hosted, no inline handlers, full keyboard & screen-reader support.
 */
(function () {
  'use strict';

  // Camera & canvas elements
  const video = document.getElementById('camera-video');
  const overlay = document.getElementById('camera-overlay');
  const cameraStatus = document.getElementById('camera-status');
  const recognizeBtn = document.getElementById('recognize-btn');
  const liveToggle = document.getElementById('live-recognition-toggle');
  const uploadInput = document.getElementById('upload-image-input');

  // Recognition Results panel elements
  const resultPerson = document.getElementById('result-person');
  const resultSimilarity = document.getElementById('result-similarity');
  const resultFacesCount = document.getElementById('result-faces-count');
  const resultLatency = document.getElementById('result-latency');
  const resultExpression = document.getElementById('result-expression');
  const announcement = document.getElementById('recognition-announcement');

  // Phase 6 Status & Breakdown elements
  const recognitionModeBadge = document.getElementById('recognition-mode-badge');
  const processingIndicator = document.getElementById('processing-indicator');
  const facesDetailContainer = document.getElementById('faces-detail-container');
  const facesDetailList = document.getElementById('faces-detail-list');

  // Voice Feedback elements (Phase 5)
  const speechStatusBadge = document.getElementById('speech-status-badge');
  const latestAnnouncementText = document.getElementById('latest-announcement-text');
  const muteBtn = document.getElementById('mute-speech-btn');
  const muteBtnText = document.getElementById('mute-btn-text');
  const repeatBtn = document.getElementById('repeat-speech-btn');
  const speechRateSelect = document.getElementById('speech-rate-select');
  const speechCooldownSelect = document.getElementById('speech-cooldown-select');

  if (!recognizeBtn || !overlay) {
    return;
  }

  // State variables
  let isProcessing = false;
  let activeRequestId = 0;
  let activeAbortController = null;
  let liveInterval = null;
  let isSpeechMuted = false;
  let lastSpokenMessage = '';
  let lastSpokenTime = 0;
  let previousPeopleInScene = [];
  const hasSupportedSpeech = 'speechSynthesis' in window && typeof window.SpeechSynthesisUtterance !== 'undefined';

  const offscreenCanvas = document.createElement('canvas');
  const offscreenCtx = offscreenCanvas.getContext('2d');
  const overlayCtx = overlay.getContext('2d');

  // Initial speech synthesis check
  if (!hasSupportedSpeech) {
    if (speechStatusBadge) {
      speechStatusBadge.className = 'badge badge--warning';
      speechStatusBadge.textContent = 'Voice unsupported';
    }
    if (muteBtn) muteBtn.disabled = true;
    if (repeatBtn) repeatBtn.disabled = true;
  }

  function clearOverlay() {
    overlayCtx.clearRect(0, 0, overlay.width, overlay.height);
  }

  function resetResults() {
    clearOverlay();
    if (resultPerson) resultPerson.innerHTML = '<span class="badge badge--neutral">No faces detected</span>';
    if (resultSimilarity) resultSimilarity.textContent = '—';
    if (resultFacesCount) resultFacesCount.textContent = '0';
    if (resultLatency) resultLatency.textContent = '—';
    if (resultExpression) resultExpression.innerHTML = '<span class="badge badge--neutral">—</span>';
    if (facesDetailContainer) facesDetailContainer.hidden = true;
    if (facesDetailList) facesDetailList.innerHTML = '';
    if (announcement) announcement.textContent = 'Ready for face recognition.';
    previousPeopleInScene = [];
  }

  function setCameraControlsState(isOn) {
    recognizeBtn.disabled = !isOn || isProcessing;
    liveToggle.disabled = !isOn;
    if (!isOn) {
      if (liveToggle.checked) {
        liveToggle.checked = false;
      }
      stopLiveRecognition();
      resetResults();
      overlay.hidden = true;
      cancelSpeech();
      if (recognitionModeBadge) {
        recognitionModeBadge.className = 'badge badge--neutral';
        recognitionModeBadge.textContent = 'Camera off';
      }
    } else {
      overlay.hidden = false;
      if (recognitionModeBadge && !liveToggle.checked) {
        recognitionModeBadge.className = 'badge badge--neutral';
        recognitionModeBadge.textContent = 'Recognition idle';
      }
    }
  }

  // Observe camera status changes from camera.js
  if (cameraStatus) {
    const observer = new MutationObserver(function (mutations) {
      mutations.forEach(function (mutation) {
        if (mutation.type === 'attributes' && mutation.attributeName === 'data-state') {
          const state = cameraStatus.getAttribute('data-state');
          setCameraControlsState(state === 'on');
        }
      });
    });
    observer.observe(cameraStatus, { attributes: true });
  }

  function captureVideoFrame() {
    if (!video || video.videoWidth === 0 || video.videoHeight === 0) {
      return null;
    }
    offscreenCanvas.width = video.videoWidth;
    offscreenCanvas.height = video.videoHeight;
    offscreenCtx.drawImage(video, 0, 0, video.videoWidth, video.videoHeight);
    return offscreenCanvas.toDataURL('image/jpeg', 0.85);
  }

  // Natural language mapping for visible facial expressions
  function formatExpressionText(exprObj) {
    if (!exprObj || exprObj.status !== 'classified' || !exprObj.label) {
      return null;
    }
    const map = {
      happy: 'smiling',
      neutral: 'neutral',
      sad: 'sad',
      surprised: 'surprised',
      angry: 'frowning or angry',
      disgust: 'disgusted',
      fearful: 'fearful',
    };
    return map[exprObj.label.toLowerCase()] || exprObj.label;
  }

  // Generate accessible, honest announcement message
  function generateAnnouncement(data) {
    if (!data || data.faces_count === 0) {
      if (previousPeopleInScene.length > 0) {
        return 'No faces detected in view.';
      }
      return null;
    }

    const faces = data.faces || [];
    const recognized = faces.filter(f => f.status === 'recognized');
    const uncertain = faces.filter(f => f.status === 'uncertain');
    const unknown = faces.filter(f => f.status === 'unknown');

    // 1. Single face scene
    if (faces.length === 1) {
      const f = faces[0];
      const exprText = formatExpressionText(f.expression);

      if (f.status === 'recognized') {
        if (exprText) {
          return `Recognized ${f.name}. Estimated visible expression: ${exprText}.`;
        }
        return `Recognized ${f.name}.`;
      }

      if (f.status === 'uncertain') {
        return 'Person not identified with confidence. Please try again.';
      }

      // Unknown face
      if (exprText) {
        return `An unrecognized person is in front of you. Estimated visible expression: ${exprText}.`;
      }
      return 'An unrecognized person is in front of you.';
    }

    // 2. Multiple faces scene
    const parts = [];
    if (recognized.length > 0) {
      const names = recognized.map(f => f.name).join(' and ');
      parts.push(`Recognized ${names}`);
    }
    if (unknown.length > 0) {
      parts.push(`${unknown.length} unrecognized person${unknown.length > 1 ? 's' : ''}`);
    }
    if (uncertain.length > 0) {
      parts.push(`${uncertain.length} person with uncertain identity`);
    }

    return `Detected ${faces.length} people: ${parts.join(', ')}.`;
  }

  // Voice synthesis executor with queue cancellation
  function speakAnnouncement(text, forceRepeat = false) {
    if (!text) return;

    if (latestAnnouncementText) {
      latestAnnouncementText.textContent = text;
    }
    if (repeatBtn) {
      repeatBtn.disabled = false;
    }
    if (announcement) {
      announcement.textContent = text;
    }

    if (!hasSupportedSpeech || isSpeechMuted) {
      lastSpokenMessage = text;
      lastSpokenTime = Date.now();
      return;
    }

    try {
      window.speechSynthesis.cancel(); // Single utterance only: cancel any pending queue

      const utterance = new SpeechSynthesisUtterance(text);
      const rate = speechRateSelect ? parseFloat(speechRateSelect.value) : 1.0;
      utterance.rate = isNaN(rate) ? 1.0 : Math.max(0.5, Math.min(2.0, rate));
      utterance.pitch = 1.0;
      utterance.lang = 'en-US';

      window.speechSynthesis.speak(utterance);
      lastSpokenMessage = text;
      lastSpokenTime = Date.now();
    } catch (err) {
      console.warn('SpeechSynthesis error:', err);
    }
  }

  function cancelSpeech() {
    if (hasSupportedSpeech) {
      try {
        window.speechSynthesis.cancel();
      } catch (e) {
        // ignore
      }
    }
  }

  // Duplicate suppression and cooldown decision logic
  function processSpeechPolicy(data) {
    const newAnnouncement = generateAnnouncement(data);
    if (!newAnnouncement) {
      previousPeopleInScene = [];
      return;
    }

    const currentPeople = (data.faces || []).map(f => {
      if (f.status === 'recognized') return `person_${f.person_id}`;
      if (f.status === 'uncertain') return 'uncertain';
      return 'unknown';
    });

    // Check if new person entered the scene
    const hasNewPerson = currentPeople.some(p => !previousPeopleInScene.includes(p));
    previousPeopleInScene = currentPeople;

    const now = Date.now();
    const cooldownMs = speechCooldownSelect ? parseInt(speechCooldownSelect.value, 10) : 6000;
    const elapsed = now - lastSpokenTime;

    // Policy:
    // 1. If a new person entered: announce immediately
    // 2. If message changed and at least 3s passed: announce change
    // 3. If exact same message: announce only if cooldown has expired
    if (hasNewPerson) {
      speakAnnouncement(newAnnouncement);
    } else if (newAnnouncement !== lastSpokenMessage) {
      if (elapsed >= 3000) {
        speakAnnouncement(newAnnouncement);
      }
    } else if (elapsed >= cooldownMs) {
      speakAnnouncement(newAnnouncement);
    }
  }

  // Draw overlay annotations
  function drawDetections(faces, imageWidth, imageHeight) {
    overlay.width = imageWidth;
    overlay.height = imageHeight;
    clearOverlay();

    faces.forEach(function (face) {
      const box = face.box;
      const status = face.status;
      const name = face.name || 'Unknown';
      const sim = face.similarity ? (face.similarity * 100).toFixed(0) + '%' : '';

      let exprSnippet = '';
      if (face.expression && face.expression.status === 'classified' && face.expression.label) {
        const exprName = face.expression.label.charAt(0).toUpperCase() + face.expression.label.slice(1);
        const exprConf = (face.expression.confidence * 100).toFixed(0);
        exprSnippet = ` | ${exprName} (${exprConf}%)`;
      } else if (face.expression && face.expression.status === 'uncertain') {
        exprSnippet = ' | Expr: Uncertain';
      }

      let color = '#d13438'; // red for unknown
      let label = `Unknown${exprSnippet}`;
      if (status === 'recognized') {
        color = '#107c41'; // green for recognized
        label = `${name} (${sim})${exprSnippet}`;
      } else if (status === 'uncertain') {
        color = '#d87a00'; // amber for uncertain
        label = `Uncertain (${sim})${exprSnippet}`;
      }

      // 1. Draw Bounding Box
      overlayCtx.lineWidth = Math.max(3, Math.round(imageWidth / 250));
      overlayCtx.strokeStyle = color;
      overlayCtx.beginPath();
      overlayCtx.rect(box.x, box.y, box.width, box.height);
      overlayCtx.stroke();

      // 2. Draw Label Badge
      const fontSize = Math.max(13, Math.round(imageWidth / 38));
      overlayCtx.font = `bold ${fontSize}px "Segoe UI", system-ui, sans-serif`;
      const textWidth = overlayCtx.measureText(label).width;
      const pad = 6;
      const labelX = box.x;
      const labelY = Math.max(fontSize + pad * 2, box.y - 6);

      overlayCtx.fillStyle = color;
      overlayCtx.fillRect(labelX, labelY - fontSize - pad, textWidth + pad * 2, fontSize + pad * 1.5);

      overlayCtx.fillStyle = '#ffffff';
      overlayCtx.fillText(label, labelX + pad, labelY - pad / 2);
    });
  }

  // Update UI stats and results
  function updateResultsUI(data) {
    if (resultFacesCount) {
      resultFacesCount.textContent = data.faces_count;
    }
    if (resultLatency) {
      resultLatency.textContent = `${data.processing_time_ms} ms`;
    }

    if (data.faces_count === 0) {
      clearOverlay();
      if (resultPerson) resultPerson.innerHTML = '<span class="badge badge--neutral">No faces detected</span>';
      if (resultSimilarity) resultSimilarity.textContent = '—';
      if (resultExpression) resultExpression.innerHTML = '<span class="badge badge--neutral">—</span>';
      if (facesDetailContainer) facesDetailContainer.hidden = true;
      if (facesDetailList) facesDetailList.innerHTML = '';
      processSpeechPolicy(data);
      return;
    }

    const faces = data.faces || [];
    const recognizedList = faces.filter(f => f.status === 'recognized');
    const uncertainList = faces.filter(f => f.status === 'uncertain');
    const unknownList = faces.filter(f => f.status === 'unknown');

    let personHtml = '';
    if (recognizedList.length > 0) {
      personHtml = recognizedList
        .map(f => `<span class="badge badge--success">${f.name} (${(f.similarity * 100).toFixed(0)}%)</span>`)
        .join(' ');
      if (resultSimilarity) {
        resultSimilarity.textContent = `${(recognizedList[0].similarity * 100).toFixed(1)}%`;
      }
    } else if (uncertainList.length > 0) {
      personHtml = `<span class="badge badge--warning">Uncertain match</span>`;
      if (resultSimilarity) {
        resultSimilarity.textContent = `${(uncertainList[0].similarity * 100).toFixed(1)}%`;
      }
    } else {
      personHtml = `<span class="badge badge--danger">Unknown person</span>`;
      if (resultSimilarity) {
        resultSimilarity.textContent = unknownList[0].similarity > 0 ? `${(unknownList[0].similarity * 100).toFixed(1)}%` : '—';
      }
    }

    // Expression UI update
    if (resultExpression && faces.length > 0) {
      const primaryExpr = faces[0].expression;
      if (primaryExpr && primaryExpr.status === 'classified' && primaryExpr.label) {
        const exprName = primaryExpr.label.charAt(0).toUpperCase() + primaryExpr.label.slice(1);
        const exprPct = (primaryExpr.confidence * 100).toFixed(0);
        resultExpression.innerHTML = `<span class="badge badge--success">${exprName} (${exprPct}%)</span>`;
      } else if (primaryExpr && primaryExpr.status === 'uncertain') {
        const candidate = primaryExpr.candidate ? ` (${primaryExpr.candidate})` : '';
        resultExpression.innerHTML = `<span class="badge badge--warning">Uncertain${candidate}</span>`;
      } else {
        resultExpression.innerHTML = '<span class="badge badge--neutral">Unusable crop</span>';
      }
    }

    if (resultPerson) {
      resultPerson.innerHTML = personHtml;
    }

    // Phase 6: Multi-face detailed breakdown cards
    if (facesDetailContainer && facesDetailList) {
      facesDetailContainer.hidden = false;
      facesDetailList.innerHTML = faces.map(function (face, idx) {
        let statusBadge = '';
        if (face.status === 'recognized') {
          const sim = face.similarity ? ` (${(face.similarity * 100).toFixed(1)}%)` : '';
          statusBadge = `<span class="badge badge--success">Recognized: ${face.name || 'Person'}${sim}</span>`;
        } else if (face.status === 'uncertain') {
          const sim = face.similarity ? ` (${(face.similarity * 100).toFixed(1)}%)` : '';
          statusBadge = `<span class="badge badge--warning">Uncertain match${sim}</span>`;
        } else {
          statusBadge = `<span class="badge badge--danger">Unknown person</span>`;
        }

        let exprBadge = '';
        if (face.expression && face.expression.status === 'classified' && face.expression.label) {
          const exprName = face.expression.label.charAt(0).toUpperCase() + face.expression.label.slice(1);
          const exprPct = (face.expression.confidence * 100).toFixed(0);
          exprBadge = `<span class="badge badge--success">${exprName} (${exprPct}%)</span>`;
        } else if (face.expression && face.expression.status === 'uncertain') {
          exprBadge = `<span class="badge badge--warning">Expression uncertain</span>`;
        } else {
          exprBadge = `<span class="badge badge--neutral">Expression unclassified</span>`;
        }

        const box = face.box || {};
        const boxLabel = box.width ? `<span class="text-muted" style="margin-left: 0.5rem; font-size: 0.8125rem;">${box.width}×${box.height}px</span>` : '';

        return `<div class="face-detail-card">
          <div class="face-detail-card__identity">
            <span>Face #${idx + 1}: </span>
            ${statusBadge}
            ${boxLabel}
          </div>
          <div class="face-detail-card__expression">
            ${exprBadge}
          </div>
        </div>`;
      }).join('');
    }

    // Dispatch announcement policy
    processSpeechPolicy(data);
  }

  // Single-flight network request with backpressure and stale cancellation
  async function performRecognition(imageDataUrl, originalWidth, originalHeight) {
    if (isProcessing) return;
    isProcessing = true;
    recognizeBtn.disabled = true;

    if (processingIndicator) {
      processingIndicator.hidden = false;
    }

    // Abort previous in-flight request if any
    if (activeAbortController) {
      try {
        activeAbortController.abort();
      } catch (e) {}
    }
    const abortController = new AbortController();
    activeAbortController = abortController;
    const reqId = ++activeRequestId;

    try {
      const resp = await fetch('/api/recognize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: imageDataUrl }),
        signal: abortController.signal,
      });

      const data = await resp.json();

      // Guard against stale response if another request was triggered
      if (reqId !== activeRequestId) {
        return;
      }

      if (resp.status === 200 && data.status === 'ok') {
        updateResultsUI(data);
        drawDetections(data.faces, originalWidth, originalHeight);
      } else {
        const errorMsg = data.error && data.error.message ? data.error.message : 'Recognition failed.';
        if (announcement) announcement.textContent = `Error: ${errorMsg}`;
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        return; // Normal cancellation
      }
      if (reqId === activeRequestId) {
        if (announcement) announcement.textContent = 'Network or server error during recognition.';
      }
    } finally {
      if (reqId === activeRequestId) {
        isProcessing = false;
        if (processingIndicator) {
          processingIndicator.hidden = true;
        }
        const isCameraOn = cameraStatus && cameraStatus.getAttribute('data-state') === 'on';
        recognizeBtn.disabled = !isCameraOn;
      }
    }
  }

  function onRecognizeClick() {
    const dataUrl = captureVideoFrame();
    if (!dataUrl) {
      alert('Camera is not active or no frame available.');
      return;
    }
    performRecognition(dataUrl, video.videoWidth, video.videoHeight);
  }

  function startLiveRecognition() {
    if (liveInterval) clearInterval(liveInterval);
    if (recognitionModeBadge) {
      recognitionModeBadge.className = 'badge badge--success';
      recognitionModeBadge.textContent = 'Continuous active (1.2s)';
    }
    onRecognizeClick();
    // Controlled, measured 1200ms processing loop with single-flight backpressure
    liveInterval = setInterval(function () {
      if (!isProcessing) {
        const dataUrl = captureVideoFrame();
        if (dataUrl) {
          performRecognition(dataUrl, video.videoWidth, video.videoHeight);
        }
      }
    }, 1200);
  }

  function stopLiveRecognition() {
    if (liveInterval) {
      clearInterval(liveInterval);
      liveInterval = null;
    }
    if (activeAbortController) {
      try {
        activeAbortController.abort();
      } catch (e) {}
      activeAbortController = null;
    }
    activeRequestId++;
    isProcessing = false;
    if (processingIndicator) {
      processingIndicator.hidden = true;
    }
    const isCameraOn = cameraStatus && cameraStatus.getAttribute('data-state') === 'on';
    if (recognitionModeBadge) {
      recognitionModeBadge.className = 'badge badge--neutral';
      recognitionModeBadge.textContent = isCameraOn ? 'Recognition idle' : 'Camera off';
    }
    cancelSpeech();
  }

  // Event Listeners
  recognizeBtn.addEventListener('click', onRecognizeClick);

  liveToggle.addEventListener('change', function () {
    if (liveToggle.checked) {
      startLiveRecognition();
    } else {
      stopLiveRecognition();
    }
  });

  // Mute / Unmute speech toggle
  if (muteBtn) {
    muteBtn.addEventListener('click', function () {
      isSpeechMuted = !isSpeechMuted;
      muteBtn.setAttribute('aria-pressed', isSpeechMuted ? 'true' : 'false');

      if (isSpeechMuted) {
        cancelSpeech();
        if (muteBtnText) muteBtnText.textContent = 'Unmute voice';
        if (speechStatusBadge) {
          speechStatusBadge.className = 'badge badge--neutral';
          speechStatusBadge.textContent = 'Muted';
        }
      } else {
        if (muteBtnText) muteBtnText.textContent = 'Mute voice';
        if (speechStatusBadge) {
          speechStatusBadge.className = 'badge badge--success';
          speechStatusBadge.textContent = 'Voice active';
        }
        if (lastSpokenMessage) {
          speakAnnouncement(lastSpokenMessage);
        }
      }
    });
  }

  // Manual repeat announcement button
  if (repeatBtn) {
    repeatBtn.addEventListener('click', function () {
      if (lastSpokenMessage) {
        speakAnnouncement(lastSpokenMessage, true);
      }
    });
  }

  // Static image testing support
  if (uploadInput) {
    uploadInput.addEventListener('change', function () {
      const file = uploadInput.files && uploadInput.files[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = function (e) {
        const dataUrl = e.target.result;
        const img = new Image();
        img.onload = function () {
          performRecognition(dataUrl, img.naturalWidth, img.naturalHeight);
        };
        img.src = dataUrl;
      };
      reader.readAsDataURL(file);
    });
  }

  // Clean cancellation on unload
  window.addEventListener('beforeunload', cancelSpeech);
})();
