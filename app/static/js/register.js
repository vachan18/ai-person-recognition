/**
 * register.js - Biometric Enrollment Studio frontend controller.
 * Drag-and-drop reference portrait upload, live validation, preview lifecycle,
 * and accessible error handling. Strictly adheres to CSP (no inline scripts/handlers).
 */
(function () {
  'use strict';

  // Form & Input Elements
  const form = document.getElementById('register-form');
  const nameInput = document.getElementById('person-name');
  const imageInput = document.getElementById('person-image');
  const consentCheckbox = document.getElementById('consent-checkbox');
  const dropzone = document.getElementById('upload-dropzone');
  const dropzonePrompt = document.getElementById('dropzone-prompt');
  const chosenFilename = document.getElementById('chosen-filename');

  // Preview Card Elements
  const previewContainer = document.getElementById('preview-container');
  const imagePreview = document.getElementById('image-preview');
  const previewFilename = document.getElementById('preview-filename');
  const previewMeta = document.getElementById('preview-meta');
  const removePreviewBtn = document.getElementById('remove-preview-btn');

  // Action Buttons & Live Announcements
  const submitBtn = document.getElementById('submit-btn');
  const submitBtnText = document.getElementById('submit-btn-text');
  const feedbackError = document.getElementById('feedback-error');
  const feedbackErrorText = document.getElementById('feedback-error-text');
  const feedbackSuccess = document.getElementById('feedback-success');
  const feedbackSuccessText = document.getElementById('feedback-success-text');
  const registerAnotherBtn = document.getElementById('register-another-btn');

  let currentPreviewUrl = null;

  // Validation & Live Button State Helper
  function updateSubmitState() {
    if (!submitBtn) return;
    const hasName = nameInput && nameInput.value.trim().length > 0;
    const hasImage = imageInput && imageInput.files && imageInput.files.length > 0;
    const hasConsent = consentCheckbox && consentCheckbox.checked;

    const isValid = hasName && hasImage && hasConsent;
    submitBtn.disabled = !isValid;
  }

  function clearFeedback() {
    if (feedbackError) {
      feedbackError.hidden = true;
      feedbackErrorText.textContent = '';
    }
    if (feedbackSuccess) {
      feedbackSuccess.hidden = true;
    }
  }

  function showError(message) {
    if (feedbackSuccess) feedbackSuccess.hidden = true;
    if (feedbackError && feedbackErrorText) {
      feedbackErrorText.textContent = message;
      feedbackError.hidden = false;
      feedbackError.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  function showSuccess(message) {
    if (feedbackError) feedbackError.hidden = true;
    if (feedbackSuccess && feedbackSuccessText) {
      feedbackSuccessText.textContent = message;
      feedbackSuccess.hidden = false;
      feedbackSuccess.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  function clearImagePreview() {
    if (currentPreviewUrl) {
      URL.revokeObjectURL(currentPreviewUrl);
      currentPreviewUrl = null;
    }
    if (imageInput) imageInput.value = '';
    if (chosenFilename) chosenFilename.textContent = 'No file selected';
    if (imagePreview) imagePreview.src = '';
    if (previewFilename) previewFilename.textContent = '';
    if (previewMeta) previewMeta.textContent = '';
    if (previewContainer) previewContainer.hidden = true;
    if (dropzonePrompt) dropzonePrompt.hidden = false;
    updateSubmitState();
  }

  function handleFileSelected(file) {
    clearFeedback();
    if (!file) {
      clearImagePreview();
      return;
    }

    const validExtensions = ['image/jpeg', 'image/png', 'image/webp'];
    const lowerName = file.name.toLowerCase();
    const hasValidExt = lowerName.endsWith('.jpg') || lowerName.endsWith('.jpeg') || lowerName.endsWith('.png') || lowerName.endsWith('.webp');

    if (!hasValidExt && !validExtensions.includes(file.type)) {
      showError('Unsupported file format. Please upload a JPEG, PNG, or WEBP facial photo.');
      clearImagePreview();
      return;
    }

    // 5 MB max
    const maxBytes = 5 * 1024 * 1024;
    if (file.size > maxBytes) {
      showError('The selected image exceeds the maximum allowed size of 5 MB.');
      clearImagePreview();
      return;
    }

    if (file.size === 0) {
      showError('The selected image file is empty (0 bytes).');
      clearImagePreview();
      return;
    }

    if (chosenFilename) chosenFilename.textContent = file.name;
    if (previewFilename) previewFilename.textContent = file.name;
    if (previewMeta) previewMeta.textContent = 'Size: ' + formatBytes(file.size);

    if (currentPreviewUrl) {
      URL.revokeObjectURL(currentPreviewUrl);
    }
    currentPreviewUrl = URL.createObjectURL(file);
    if (imagePreview) imagePreview.src = currentPreviewUrl;

    if (dropzonePrompt) dropzonePrompt.hidden = true;
    if (previewContainer) previewContainer.hidden = false;

    updateSubmitState();
  }

  // File Input Change
  if (imageInput) {
    imageInput.addEventListener('change', function () {
      const file = imageInput.files && imageInput.files[0];
      handleFileSelected(file);
    });
  }

  // Drag and Drop support
  if (dropzone) {
    ['dragenter', 'dragover'].forEach(function (eventName) {
      dropzone.addEventListener(eventName, function (e) {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add('is-dragover');
      });
    });

    ['dragleave', 'drop'].forEach(function (eventName) {
      dropzone.addEventListener(eventName, function (e) {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove('is-dragover');
      });
    });

    dropzone.addEventListener('drop', function (e) {
      const dt = e.dataTransfer;
      if (!dt || !dt.files || dt.files.length === 0) return;
      const file = dt.files[0];

      // Assign to input files list via DataTransfer where supported
      try {
        const transfer = new DataTransfer();
        transfer.items.add(file);
        imageInput.files = transfer.files;
      } catch (err) {
        // Fallback for environments where DataTransfer is restricted
      }

      handleFileSelected(file);
    });
  }

  // Remove Preview Button
  if (removePreviewBtn) {
    removePreviewBtn.addEventListener('click', function () {
      clearImagePreview();
      if (imageInput) imageInput.focus();
    });
  }

  // Input & Consent Listeners for Real-Time Validation
  if (nameInput) {
    nameInput.addEventListener('input', updateSubmitState);
  }

  if (consentCheckbox) {
    consentCheckbox.addEventListener('change', updateSubmitState);
  }

  // Register Another Button
  if (registerAnotherBtn) {
    registerAnotherBtn.addEventListener('click', function () {
      if (form) form.reset();
      clearImagePreview();
      clearFeedback();
      updateSubmitState();
      if (nameInput) nameInput.focus();
    });
  }

  // Form Submit Handler
  if (form) {
    form.addEventListener('submit', async function (e) {
      e.preventDefault();
      clearFeedback();

      const name = nameInput ? nameInput.value.trim() : '';
      if (!name) {
        showError('Please enter the person\'s full name.');
        if (nameInput) nameInput.focus();
        return;
      }

      const file = imageInput && imageInput.files ? imageInput.files[0] : null;
      if (!file) {
        showError('Please select a facial reference image file.');
        if (imageInput) imageInput.focus();
        return;
      }

      if (!consentCheckbox || !consentCheckbox.checked) {
        showError('Biometric consent is required before registering facial reference data.');
        if (consentCheckbox) consentCheckbox.focus();
        return;
      }

      const formData = new FormData();
      formData.append('name', name);
      formData.append('image', file);
      formData.append('consent', 'true');

      if (submitBtn) submitBtn.disabled = true;
      if (submitBtnText) submitBtnText.textContent = 'Enrolling...';

      try {
        const resp = await fetch('/api/persons', {
          method: 'POST',
          body: formData,
        });

        const data = await resp.json();

        if (resp.status === 201 && data.status === 'ok') {
          showSuccess(`"${data.person.name}" registered successfully into local directory!`);
          form.reset();
          clearImagePreview();
        } else {
          // Keep the person's name and selected image on error!
          const errorMsg = data.error && data.error.message ? data.error.message : 'Registration failed.';
          showError(errorMsg);
        }
      } catch (err) {
        showError('Network error or server unavailable. Please try again.');
      } finally {
        if (submitBtnText) submitBtnText.textContent = 'Register Person';
        updateSubmitState();
      }
    });
  }

  // Initial validation check
  updateSubmitState();
})();
