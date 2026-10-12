/**
 * recognition.js - Frontend client for face detection and identity recognition.
 * Strictly adheres to CSP: self-hosted, no inline handlers, full keyboard & screen-reader support.
 */
(function () {
  'use strict';

  const video = document.getElementById('camera-video');
  const overlay = document.getElementById('camera-overlay');
  const cameraStatus = document.getElementById('camera-status');
  const recognizeBtn = document.getElementById('recognize-btn');
  const liveToggle = document.getElementById('live-recognition-toggle');
  const uploadInput = document.getElementById('upload-image-input');

  const resultPerson = document.getElementById('result-person');
  const resultSimilarity = document.getElementById('result-similarity');
  const resultFacesCount = document.getElementById('result-faces-count');
  const resultLatency = document.getElementById('result-latency');
  const announcement = document.getElementById('recognition-announcement');

  if (!recognizeBtn || !overlay) {
    return;
  }

  let isProcessing = false;
  let liveInterval = null;
  const offscreenCanvas = document.createElement('canvas');
  const offscreenCtx = offscreenCanvas.getContext('2d');
  const overlayCtx = overlay.getContext('2d');

  function clearOverlay() {
    overlayCtx.clearRect(0, 0, overlay.width, overlay.height);
  }

  function resetResults() {
    clearOverlay();
    if (resultPerson) resultPerson.innerHTML = '<span class="badge badge--neutral">No face detected</span>';
    if (resultSimilarity) resultSimilarity.textContent = '—';
    if (resultFacesCount) resultFacesCount.textContent = '0';
    if (resultLatency) resultLatency.textContent = '—';
    if (announcement) announcement.textContent = 'Ready for face recognition.';
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
    } else {
      overlay.hidden = false;
    }
  }

  // Observe camera status changes
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

  function drawDetections(faces, imageWidth, imageHeight) {
    overlay.width = imageWidth;
    overlay.height = imageHeight;
    clearOverlay();

    faces.forEach(function (face) {
      const box = face.box;
      const status = face.status;
      const name = face.name || 'Unknown';
      const sim = face.similarity ? (face.similarity * 100).toFixed(1) + '%' : '';

      let color = '#d13438'; // red for unknown
      let label = 'Unknown';
      if (status === 'recognized') {
        color = '#107c41'; // green for recognized
        label = `${name} (${sim})`;
      } else if (status === 'uncertain') {
        color = '#d87a00'; // amber for uncertain
        label = `Uncertain (${sim})`;
      }

      // 1. Draw Bounding Box
      overlayCtx.lineWidth = Math.max(3, Math.round(imageWidth / 250));
      overlayCtx.strokeStyle = color;
      overlayCtx.beginPath();
      overlayCtx.rect(box.x, box.y, box.width, box.height);
      overlayCtx.stroke();

      // 2. Draw Label Badge
      const fontSize = Math.max(14, Math.round(imageWidth / 35));
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
      if (announcement) announcement.textContent = 'No faces detected in view.';
      return;
    }

    const faces = data.faces;
    const recognizedList = faces.filter(f => f.status === 'recognized');
    const uncertainList = faces.filter(f => f.status === 'uncertain');
    const unknownList = faces.filter(f => f.status === 'unknown');

    let personHtml = '';
    let announcementText = '';

    if (recognizedList.length > 0) {
      personHtml = recognizedList
        .map(f => `<span class="badge badge--success">${f.name} (${(f.similarity * 100).toFixed(0)}%)</span>`)
        .join(' ');
      announcementText = `Recognized ${recognizedList.map(f => f.name).join(', ')}.`;
      if (resultSimilarity) {
        resultSimilarity.textContent = `${(recognizedList[0].similarity * 100).toFixed(1)}%`;
      }
    } else if (uncertainList.length > 0) {
      personHtml = `<span class="badge badge--warning">Uncertain match</span>`;
      announcementText = 'Detected person with uncertain identity.';
      if (resultSimilarity) {
        resultSimilarity.textContent = `${(uncertainList[0].similarity * 100).toFixed(1)}%`;
      }
    } else {
      personHtml = `<span class="badge badge--danger">Unknown person</span>`;
      announcementText = `Detected ${unknownList.length} unknown face(s).`;
      if (resultSimilarity) {
        resultSimilarity.textContent = unknownList[0].similarity > 0 ? `${(unknownList[0].similarity * 100).toFixed(1)}%` : '—';
      }
    }

    if (resultPerson) {
      resultPerson.innerHTML = personHtml;
    }
    if (announcement) {
      announcement.textContent = announcementText;
    }
  }

  async function performRecognition(imageDataUrl, originalWidth, originalHeight) {
    if (isProcessing) return;
    isProcessing = true;
    recognizeBtn.disabled = true;

    try {
      const resp = await fetch('/api/recognize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: imageDataUrl }),
      });

      const data = await resp.json();

      if (resp.status === 200 && data.status === 'ok') {
        updateResultsUI(data);
        drawDetections(data.faces, originalWidth, originalHeight);
      } else {
        const errorMsg = data.error && data.error.message ? data.error.message : 'Recognition failed.';
        if (announcement) announcement.textContent = `Error: ${errorMsg}`;
      }
    } catch (err) {
      if (announcement) announcement.textContent = 'Network or server error during recognition.';
    } finally {
      isProcessing = false;
      const isCameraOn = cameraStatus && cameraStatus.getAttribute('data-state') === 'on';
      recognizeBtn.disabled = !isCameraOn;
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
    onRecognizeClick();
    liveInterval = setInterval(function () {
      if (!isProcessing) {
        const dataUrl = captureVideoFrame();
        if (dataUrl) {
          performRecognition(dataUrl, video.videoWidth, video.videoHeight);
        }
      }
    }, 1000);
  }

  function stopLiveRecognition() {
    if (liveInterval) {
      clearInterval(liveInterval);
      liveInterval = null;
    }
  }

  recognizeBtn.addEventListener('click', onRecognizeClick);

  liveToggle.addEventListener('change', function () {
    if (liveToggle.checked) {
      startLiveRecognition();
    } else {
      stopLiveRecognition();
    }
  });

  // Support testing recognition via static uploaded photo
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
})();
