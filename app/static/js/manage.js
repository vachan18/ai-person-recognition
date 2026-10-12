/**
 * manage.js - Directory management, search, edit, photo replace, and delete operations.
 * Strictly adheres to CSP: self-hosted, no inline handlers, full keyboard accessibility.
 */
(function () {
  'use strict';

  // State
  let persons = [];
  let activeModal = null;
  let lastFocusedElement = null;
  let searchDebounceTimer = null;

  // DOM elements
  const searchInput = document.getElementById('search-input');
  const clearSearchBtn = document.getElementById('clear-search-btn');
  const peopleCount = document.getElementById('people-count');
  const loadingState = document.getElementById('loading-state');
  const emptyState = document.getElementById('empty-state');
  const noResultsState = document.getElementById('no-results-state');
  const noResultsText = document.getElementById('no-results-text');
  const resetSearchBtn = document.getElementById('reset-search-btn');
  const peopleGrid = document.getElementById('people-grid');

  const manageError = document.getElementById('manage-error');
  const manageErrorText = document.getElementById('manage-error-text');
  const manageSuccess = document.getElementById('manage-success');
  const manageSuccessText = document.getElementById('manage-success-text');

  // Modals
  const editModal = document.getElementById('edit-modal');
  const editForm = document.getElementById('edit-name-form');
  const editPersonId = document.getElementById('edit-person-id');
  const editPersonName = document.getElementById('edit-person-name');

  const replaceModal = document.getElementById('replace-photo-modal');
  const replaceForm = document.getElementById('replace-photo-form');
  const replacePersonId = document.getElementById('replace-person-id');
  const replacePersonNameDisplay = document.getElementById('replace-person-name-display');
  const replaceFileInput = document.getElementById('replace-image-file');
  const replaceFilename = document.getElementById('replace-filename');
  const replacePreviewContainer = document.getElementById('replace-preview-container');
  const replaceImagePreview = document.getElementById('replace-image-preview');
  const replacePreviewMeta = document.getElementById('replace-preview-meta');

  const deleteModal = document.getElementById('delete-modal');
  const deletePersonName = document.getElementById('delete-person-name');
  const confirmDeleteBtn = document.getElementById('confirm-delete-btn');
  let personIdToDelete = null;

  let replacePreviewUrl = null;

  // Feedback banners
  function clearFeedback() {
    manageError.hidden = true;
    manageErrorText.textContent = '';
    manageSuccess.hidden = true;
    manageSuccessText.textContent = '';
  }

  function showError(msg) {
    manageSuccess.hidden = true;
    manageErrorText.textContent = msg;
    manageError.hidden = false;
    manageError.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function showSuccess(msg) {
    manageError.hidden = true;
    manageSuccessText.textContent = msg;
    manageSuccess.hidden = false;
    manageSuccess.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function formatDate(isoString) {
    if (!isoString) return 'Unknown';
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return isoString;
    }
  }

  // Accessible Modal helpers
  function openModal(modalElement, focusTarget) {
    lastFocusedElement = document.activeElement;
    modalElement.hidden = false;
    modalElement.classList.add('is-open');
    activeModal = modalElement;
    if (focusTarget) {
      focusTarget.focus();
    } else {
      const focusable = modalElement.querySelector('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
      if (focusable) focusable.focus();
    }
    document.body.style.overflow = 'hidden';
  }

  function closeModal() {
    if (!activeModal) return;
    activeModal.hidden = true;
    activeModal.classList.remove('is-open');
    activeModal = null;
    document.body.style.overflow = '';
    if (lastFocusedElement && typeof lastFocusedElement.focus === 'function') {
      lastFocusedElement.focus();
    }
  }

  // Trap focus & Escape key inside modal
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && activeModal) {
      closeModal();
      return;
    }

    if (e.key === 'Tab' && activeModal) {
      const focusables = activeModal.querySelectorAll(
        'button:not([disabled]), [href], input:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      );
      if (focusables.length === 0) return;
      const first = focusables[0];
      const last = focusables[focusables.length - 1];

      if (e.shiftKey) {
        if (document.activeElement === first) {
          last.focus();
          e.preventDefault();
        }
      } else {
        if (document.activeElement === last) {
          first.focus();
          e.preventDefault();
        }
      }
    }
  });

  // Modal close buttons
  document.querySelectorAll('[data-close-modal]').forEach(function (btn) {
    btn.addEventListener('click', closeModal);
  });

  // Fetch people list
  async function loadPeople(query = '') {
    loadingState.hidden = false;
    emptyState.hidden = true;
    noResultsState.hidden = true;
    peopleGrid.hidden = true;

    try {
      const url = query ? `/api/persons?q=${encodeURIComponent(query)}` : '/api/persons';
      const resp = await fetch(url);
      const data = await resp.json();

      loadingState.hidden = true;

      if (data.status !== 'ok') {
        showError(data.error && data.error.message ? data.error.message : 'Failed to load people.');
        return;
      }

      persons = data.persons || [];
      renderDirectory(query);
    } catch (err) {
      loadingState.hidden = true;
      showError('Could not connect to the local server.');
    }
  }

  function renderDirectory(query = '') {
    const count = persons.length;

    if (query) {
      clearSearchBtn.hidden = false;
      peopleCount.textContent = `Found ${count} ${count === 1 ? 'person' : 'people'} matching "${query}"`;
    } else {
      clearSearchBtn.hidden = true;
      peopleCount.textContent = `${count} ${count === 1 ? 'person' : 'people'} registered`;
    }

    if (count === 0) {
      peopleGrid.hidden = true;
      if (query) {
        noResultsText.textContent = `No people match "${query}".`;
        noResultsState.hidden = false;
      } else {
        emptyState.hidden = false;
      }
      return;
    }

    noResultsState.hidden = true;
    emptyState.hidden = true;
    peopleGrid.innerHTML = '';
    peopleGrid.hidden = false;

    persons.forEach(function (person) {
      const card = createPersonCard(person);
      peopleGrid.appendChild(card);
    });
  }

  function createPersonCard(person) {
    const card = document.createElement('article');
    card.className = 'card person-card';
    card.id = `person-card-${person.id}`;
    card.setAttribute('aria-labelledby', `person-name-${person.id}`);

    const media = document.createElement('div');
    media.className = 'person-card__media';

    const img = document.createElement('img');
    img.id = `person-img-${person.id}`;
    img.className = 'person-card__img';
    img.src = `${person.image_url}?t=${encodeURIComponent(person.updated_at)}`;
    img.alt = `Facial portrait of ${person.name}`;
    img.loading = 'lazy';
    img.addEventListener('error', function () {
      img.alt = 'Photo unavailable';
    });
    media.appendChild(img);

    const body = document.createElement('div');
    body.className = 'person-card__body';

    const title = document.createElement('h3');
    title.id = `person-name-${person.id}`;
    title.className = 'person-card__title';
    title.textContent = person.name;

    const meta = document.createElement('div');
    meta.className = 'person-card__meta';
    meta.innerHTML = `
      <p><span>Registered:</span> ${formatDate(person.created_at)}</p>
      <p><span>Updated:</span> ${formatDate(person.updated_at)}</p>
    `;

    const actions = document.createElement('div');
    actions.className = 'person-card__actions';

    const editBtn = document.createElement('button');
    editBtn.type = 'button';
    editBtn.className = 'btn btn--small';
    editBtn.textContent = 'Edit Name';
    editBtn.setAttribute('aria-label', `Edit name for ${person.name}`);
    editBtn.addEventListener('click', function () {
      editPersonId.value = person.id;
      editPersonName.value = person.name;
      openModal(editModal, editPersonName);
    });

    const photoBtn = document.createElement('button');
    photoBtn.type = 'button';
    photoBtn.className = 'btn btn--small';
    photoBtn.textContent = 'Change Photo';
    photoBtn.setAttribute('aria-label', `Change reference photo for ${person.name}`);
    photoBtn.addEventListener('click', function () {
      replacePersonId.value = person.id;
      replacePersonNameDisplay.textContent = `For: ${person.name}`;
      resetReplaceFileInput();
      openModal(replaceModal, replaceFileInput);
    });

    const delBtn = document.createElement('button');
    delBtn.type = 'button';
    delBtn.className = 'btn btn--small btn--danger';
    delBtn.textContent = 'Delete';
    delBtn.setAttribute('aria-label', `Delete ${person.name}`);
    delBtn.addEventListener('click', function () {
      personIdToDelete = person.id;
      deletePersonName.textContent = person.name;
      openModal(deleteModal, confirmDeleteBtn);
    });

    actions.appendChild(editBtn);
    actions.appendChild(photoBtn);
    actions.appendChild(delBtn);

    body.appendChild(title);
    body.appendChild(meta);
    body.appendChild(actions);

    card.appendChild(media);
    card.appendChild(body);
    return card;
  }

  // Search Handling
  searchInput.addEventListener('input', function () {
    clearTimeout(searchDebounceTimer);
    const q = searchInput.value.trim();
    searchDebounceTimer = setTimeout(function () {
      loadPeople(q);
    }, 250);
  });

  clearSearchBtn.addEventListener('click', function () {
    searchInput.value = '';
    clearSearchBtn.hidden = true;
    searchInput.focus();
    loadPeople('');
  });

  resetSearchBtn.addEventListener('click', function () {
    searchInput.value = '';
    clearSearchBtn.hidden = true;
    searchInput.focus();
    loadPeople('');
  });

  // Edit Name Submit
  editForm.addEventListener('submit', async function (e) {
    e.preventDefault();
    const id = editPersonId.value;
    const name = editPersonName.value.trim();

    if (!name) {
      alert('Please enter a valid name.');
      editPersonName.focus();
      return;
    }

    try {
      const resp = await fetch(`/api/persons/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      const data = await resp.json();

      if (resp.status === 200 && data.status === 'ok') {
        closeModal();
        showSuccess(`Updated name to "${data.person.name}".`);
        loadPeople(searchInput.value.trim());
      } else {
        alert(data.error && data.error.message ? data.error.message : 'Failed to update name.');
      }
    } catch {
      alert('Network error. Could not update name.');
    }
  });

  // Replace Photo Handlers
  function resetReplaceFileInput() {
    if (replacePreviewUrl) {
      URL.revokeObjectURL(replacePreviewUrl);
      replacePreviewUrl = null;
    }
    replaceFileInput.value = '';
    replaceFilename.textContent = 'No file selected';
    replaceImagePreview.src = '';
    replacePreviewMeta.textContent = '';
    replacePreviewContainer.hidden = true;
  }

  replaceFileInput.addEventListener('change', function () {
    const file = replaceFileInput.files && replaceFileInput.files[0];
    if (!file) {
      resetReplaceFileInput();
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      alert('File size exceeds the 5 MB limit.');
      resetReplaceFileInput();
      return;
    }

    replaceFilename.textContent = file.name;
    replacePreviewMeta.textContent = `Size: ${(file.size / 1024).toFixed(1)} KB`;

    if (replacePreviewUrl) URL.revokeObjectURL(replacePreviewUrl);
    replacePreviewUrl = URL.createObjectURL(file);
    replaceImagePreview.src = replacePreviewUrl;
    replacePreviewContainer.hidden = false;
  });

  replaceForm.addEventListener('submit', async function (e) {
    e.preventDefault();
    const id = replacePersonId.value;
    const file = replaceFileInput.files && replaceFileInput.files[0];

    if (!file) {
      alert('Please choose an image file first.');
      replaceFileInput.focus();
      return;
    }

    const formData = new FormData();
    formData.append('image', file);

    const submitBtn = replaceForm.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Uploading...';

    try {
      const resp = await fetch(`/api/persons/${id}/image`, {
        method: 'POST',
        body: formData,
      });
      const data = await resp.json();

      if (resp.status === 200 && data.status === 'ok') {
        closeModal();
        showSuccess(`Facial photo for "${data.person.name}" was replaced successfully.`);
        loadPeople(searchInput.value.trim());
      } else {
        alert(data.error && data.error.message ? data.error.message : 'Photo upload failed.');
      }
    } catch {
      alert('Network error. Could not replace photo.');
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Update Photo';
    }
  });

  // Delete Confirm
  confirmDeleteBtn.addEventListener('click', async function () {
    if (!personIdToDelete) return;

    confirmDeleteBtn.disabled = true;
    confirmDeleteBtn.textContent = 'Deleting...';

    try {
      const resp = await fetch(`/api/persons/${personIdToDelete}`, {
        method: 'DELETE',
      });
      const data = await resp.json();

      if (resp.status === 200 && data.status === 'ok') {
        closeModal();
        showSuccess('Person profile and associated reference photos deleted.');
        loadPeople(searchInput.value.trim());
      } else {
        alert(data.error && data.error.message ? data.error.message : 'Deletion failed.');
      }
    } catch {
      alert('Network error. Could not delete person.');
    } finally {
      confirmDeleteBtn.disabled = false;
      confirmDeleteBtn.textContent = 'Delete Permanently';
      personIdToDelete = null;
    }
  });

  // Initial load
  loadPeople();
})();
