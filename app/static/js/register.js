/**
 * register.js - Person registration handling with image preview and validation.
 * Adheres to CSP: strictly self-hosted, no inline handlers.
 */
(function () {
  'use strict';

  const form = document.getElementById('register-form');
  const nameInput = document.getElementById('person-name');
  const imageInput = document.getElementById('person-image');
  const consentCheckbox = document.getElementById('consent-checkbox');
  const chosenFilename = document.getElementById('chosen-filename');
  const previewContainer = document.getElementById('preview-container');
  const imagePreview = document.getElementById('image-preview');
  const previewFilename = document.getElementById('preview-filename');
  const previewMeta = document.getElementById('preview-meta');
  const removePreviewBtn = document.getElementById('remove-preview-btn');
  const submitBtn = document.getElementById('submit-btn');
  const submitBtnText = document.getElementById('submit-btn-text');
  const feedbackError = document.getElementById('feedback-error');
  const feedbackErrorText = document.getElementById('feedback-error-text');
  const feedbackSuccess = document.getElementById('feedback-success');
  const feedbackSuccessText = document.getElementById('feedback-success-text');
  const registerAnotherBtn = document.getElementById('register-another-btn');

  let currentPreviewUrl = null;

  function clearFeedback() {
    feedbackError.hidden = true;
    feedbackErrorText.textContent = '';
    feedbackSuccess.hidden = true;
  }

  function showError(message) {
    feedbackSuccess.hidden = true;
    feedbackErrorText.textContent = message;
    feedbackError.hidden = false;
    feedbackError.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function showSuccess(message) {
    feedbackError.hidden = true;
    feedbackSuccessText.textContent = message;
    feedbackSuccess.hidden = false;
    feedbackSuccess.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
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
    imageInput.value = '';
    chosenFilename.textContent = 'No file selected';
    imagePreview.src = '';
    previewFilename.textContent = '';
    previewMeta.textContent = '';
    previewContainer.hidden = true;
  }

  imageInput.addEventListener('change', function () {
    clearFeedback();
    const file = imageInput.files && imageInput.files[0];
    if (!file) {
      clearImagePreview();
      return;
    }

    const validExtensions = ['image/jpeg', 'image/png', 'image/webp'];
    const lowerName = file.name.toLowerCase();
    const hasValidExt = lowerName.endsWith('.jpg') || lowerName.endsWith('.jpeg') || lowerName.endsWith('.png') || lowerName.endsWith('.webp');

    if (!hasValidExt && !validExtensions.includes(file.type)) {
      showError('Please select a valid JPEG, PNG, or WEBP image file.');
      clearImagePreview();
      return;
    }

    // 5 MB max
    const maxBytes = 5 * 1024 * 1024;
    if (file.size > maxBytes) {
      showError('The selected file is too large. Maximum allowed size is 5 MB.');
      clearImagePreview();
      return;
    }

    if (file.size === 0) {
      showError('The selected image file is empty.');
      clearImagePreview();
      return;
    }

    chosenFilename.textContent = file.name;
    previewFilename.textContent = file.name;
    previewMeta.textContent = 'Size: ' + formatBytes(file.size);

    if (currentPreviewUrl) {
      URL.revokeObjectURL(currentPreviewUrl);
    }
    currentPreviewUrl = URL.createObjectURL(file);
    imagePreview.src = currentPreviewUrl;
    previewContainer.hidden = false;
  });

  removePreviewBtn.addEventListener('click', function () {
    clearImagePreview();
  });

  registerAnotherBtn.addEventListener('click', function () {
    form.reset();
    clearImagePreview();
    clearFeedback();
    nameInput.focus();
  });

  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    clearFeedback();

    const name = nameInput.value.trim();
    if (!name) {
      showError('Please enter the person\'s name.');
      nameInput.focus();
      return;
    }

    const file = imageInput.files && imageInput.files[0];
    if (!file) {
      showError('Please select a facial reference image file.');
      imageInput.focus();
      return;
    }

    if (!consentCheckbox.checked) {
      showError('You must confirm consent before registering biometric facial data.');
      consentCheckbox.focus();
      return;
    }

    const formData = new FormData();
    formData.append('name', name);
    formData.append('image', file);
    formData.append('consent', 'true');

    submitBtn.disabled = true;
    submitBtnText.textContent = 'Registering...';

    try {
      const resp = await fetch('/api/persons', {
        method: 'POST',
        body: formData,
      });

      const data = await resp.json();

      if (resp.status === 201 && data.status === 'ok') {
        showSuccess(`"${data.person.name}" registered successfully!`);
        form.reset();
        clearImagePreview();
      } else {
        const errorMsg = data.error && data.error.message ? data.error.message : 'Registration failed.';
        showError(errorMsg);
      }
    } catch (err) {
      showError('Network error or server unavailable. Please try again.');
    } finally {
      submitBtn.disabled = false;
      submitBtnText.textContent = 'Register Person';
    }
  });
})();
