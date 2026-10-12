/*
 * Camera preview (Phase 1).
 *
 * Shows the webcam in a <video> element and nothing else. Frames are never
 * drawn to a canvas, stored, or sent over the network in this phase.
 * The camera is requested only when the user clicks "Start camera".
 */
(function () {
  'use strict';

  var els = {
    video: document.getElementById('camera-video'),
    placeholder: document.getElementById('camera-placeholder'),
    status: document.getElementById('camera-status'),
    statusText: document.getElementById('camera-status-text'),
    error: document.getElementById('camera-error'),
    start: document.getElementById('start-camera'),
    stop: document.getElementById('stop-camera')
  };

  // Nothing to do on pages without the camera UI.
  if (!els.video || !els.start || !els.stop) { return; }

  var stream = null;
  // Incremented on every start/stop so a late getUserMedia result can be discarded.
  var requestId = 0;

  var STATE_TEXT = {
    off: 'Camera off',
    starting: 'Starting camera. Waiting for permission.',
    on: 'Camera on. Live preview is showing.',
    error: 'Camera error'
  };

  function setState(state, errorMessage) {
    els.status.setAttribute('data-state', state);
    els.statusText.textContent = STATE_TEXT[state];

    var showVideo = state === 'on';
    els.video.hidden = !showVideo;
    els.placeholder.hidden = showVideo;

    // Start is available when idle or after an error; Stop whenever a camera
    // is running or a permission request is pending (so the user can cancel).
    els.start.disabled = state === 'starting' || state === 'on';
    els.stop.disabled = state === 'off' || state === 'error';

    if (state === 'error' && errorMessage) {
      els.error.textContent = errorMessage;
      els.error.hidden = false;
    } else {
      els.error.textContent = '';
      els.error.hidden = true;
    }
  }

  function releaseStream() {
    if (stream) {
      stream.getTracks().forEach(function (track) {
        track.onended = null;
        track.stop();
      });
      stream = null;
    }
    els.video.srcObject = null;
  }

  function describeError(err) {
    var name = err && err.name;
    switch (name) {
      case 'NotAllowedError':
      case 'SecurityError':
      case 'PermissionDeniedError':
        return 'Camera access was blocked. Allow camera access for this site in your browser ' +
               'settings (the camera icon in the address bar), then select Start camera again.';
      case 'NotFoundError':
      case 'DevicesNotFoundError':
      case 'OverconstrainedError':
        return 'No camera was found. Connect a webcam, check that it is enabled in Windows ' +
               'privacy settings, then select Start camera again.';
      case 'NotReadableError':
      case 'TrackStartError':
      case 'AbortError':
        return 'The camera could not be started. It may be in use by another app, such as a ' +
               'video call. Close that app and select Start camera again.';
      default:
        return 'The camera could not be started because of an unexpected problem. ' +
               'Reload the page and try again.';
    }
  }

  function unsupportedMessage() {
    if (window.isSecureContext === false) {
      return 'This browser blocks camera access on this address. Open the app at ' +
             'http://127.0.0.1:5000 or http://localhost:5000 on this computer.';
    }
    return 'This browser does not support camera access. Use a recent version of ' +
           'Edge, Chrome, Firefox or Safari.';
  }

  function startCamera() {
    if (!navigator.mediaDevices || typeof navigator.mediaDevices.getUserMedia !== 'function') {
      setState('error', unsupportedMessage());
      els.start.focus();
      return;
    }

    var myRequest = ++requestId;
    setState('starting');
    // The Start button is now disabled; move focus so keyboard users keep their place.
    els.stop.focus();

    navigator.mediaDevices
      .getUserMedia({ video: { width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false })
      .then(function (newStream) {
        // User pressed Stop (or started again) while the prompt was open: discard.
        if (myRequest !== requestId) {
          newStream.getTracks().forEach(function (t) { t.stop(); });
          return;
        }
        stream = newStream;
        stream.getVideoTracks().forEach(function (track) {
          track.onended = function () {
            // Camera unplugged or taken by the system.
            releaseStream();
            requestId++;
            setState('error', 'The camera was disconnected or stopped unexpectedly. ' +
                              'Reconnect it, then select Start camera.');
            els.start.focus();
          };
        });
        els.video.srcObject = stream;
        setState('on');
        var playing = els.video.play();
        if (playing && typeof playing.catch === 'function') {
          playing.catch(function () { /* muted autoplay; ignore benign interruptions */ });
        }
      })
      .catch(function (err) {
        if (myRequest !== requestId) { return; }
        releaseStream();
        setState('error', describeError(err));
        els.start.focus();
      });
  }

  function stopCamera() {
    requestId++;
    releaseStream();
    setState('off');
    els.start.focus();
  }

  // Release the camera when the page is left, without touching the UI.
  function releaseOnUnload() {
    requestId++;
    releaseStream();
  }

  els.start.addEventListener('click', startCamera);
  els.stop.addEventListener('click', stopCamera);
  window.addEventListener('pagehide', releaseOnUnload);
  window.addEventListener('beforeunload', releaseOnUnload);

  setState('off');
})();
