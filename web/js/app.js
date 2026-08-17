/**
 * USPC Main Application Controller
 */

document.addEventListener('DOMContentLoaded', () => {
  const state = {
    items: [],
    total: 0,
    currentType: '',
    searchQuery: '',
    sortBy: 'mtime',
    sortOrder: 'DESC',
    isListView: false,
  };

  const videoPlayer = new VideoPlayerController();
  const audioPlayer = new AudioDockController();

  // Elements
  const grid = document.getElementById('media-grid');
  const searchInput = document.getElementById('search-input');
  const clearSearchBtn = document.getElementById('clear-search-btn');
  const filterPills = document.querySelectorAll('.filter-pills .pill');
  const sortSelect = document.getElementById('sort-select');
  const refreshBtn = document.getElementById('refresh-btn');
  const viewToggleBtn = document.getElementById('view-toggle-btn');
  const fileUploadInput = document.getElementById('file-upload-input');
  const uploadCard = document.getElementById('upload-progress-card');
  const uploadFilename = document.getElementById('upload-filename');
  const uploadPercent = document.getElementById('upload-percent');
  const uploadProgressBar = document.getElementById('upload-progress-bar');
  const emptyState = document.getElementById('empty-state');
  const loadingSpinner = document.getElementById('loading-spinner');
  const statsLabel = document.getElementById('library-stats');

  // Image Lightbox Elements
  const imageModal = document.getElementById('image-modal');
  const imageModalImg = document.getElementById('image-modal-img');
  const imageModalTitle = document.getElementById('image-modal-title');
  const imageModalDownload = document.getElementById('image-modal-download');
  const imageModalClose = document.getElementById('image-modal-close');

  imageModalClose.addEventListener('click', () => imageModal.classList.add('hidden'));
  imageModal.addEventListener('click', (e) => {
    if (e.target === imageModal) imageModal.classList.add('hidden');
  });

  // Load Library Data
  async function loadLibrary() {
    loadingSpinner.classList.remove('hidden');
    emptyState.classList.add('hidden');

    try {
      const data = await API.listMedia({
        type: state.currentType,
        search: state.searchQuery,
        sort: state.sortBy,
        order: state.sortOrder,
      });

      state.items = data.items;
      state.total = data.total;

      renderGrid();
      updateStats();
    } catch (err) {
      console.error('Failed to load media:', err);
    } finally {
      loadingSpinner.classList.add('hidden');
    }
  }

  function updateStats() {
    statsLabel.textContent = `${state.total} item${state.total === 1 ? '' : 's'} in library`;
  }

  function renderGrid() {
    grid.innerHTML = '';

    if (state.items.length === 0) {
      emptyState.classList.remove('hidden');
      return;
    }

    emptyState.classList.add('hidden');

    state.items.forEach((item) => {
      const card = document.createElement('div');
      card.className = 'media-card';
      card.dataset.id = item.id;
      card.dataset.type = item.media_type;

      const durationStr = item.duration_seconds ? formatDuration(item.duration_seconds) : '';
      const sizeStr = formatFileSize(item.size_bytes);

      const badgeType = item.media_type.toUpperCase();
      const badgeClass = `badge-${item.media_type}`;

      card.innerHTML = `
        <div class="card-thumb-wrapper">
          <img class="card-thumb-img" src="/api/media/${item.id}/thumbnail" alt="${escapeHtml(item.filename)}" loading="lazy" onerror="this.src='data:image/svg+xml;utf8,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'100\\' height=\\'100\\'><rect width=\\'100\\' height=\\'100\\' fill=\\'%231e293b\\'/></svg>'">
          <span class="badge ${badgeClass}">${badgeType}</span>
          ${durationStr ? `<span class="duration-pill">${durationStr}</span>` : ''}
          <div class="play-hover-overlay">
            <div class="play-icon-circle">
              ${item.media_type === 'image' ? '🔍' : '▶'}
            </div>
          </div>
        </div>
        <div class="card-body">
          <div class="card-title" title="${escapeHtml(item.title || item.filename)}">
            ${escapeHtml(item.title || item.filename)}
          </div>
          <div class="card-meta">
            <span>${item.artist ? escapeHtml(item.artist) : sizeStr}</span>
            <span>${durationStr || sizeStr}</span>
          </div>
        </div>
      `;

      card.addEventListener('click', () => handleItemClick(item));
      grid.appendChild(card);
    });
  }

  // 1-Click Interaction Handler
  async function handleItemClick(item) {
    // Get fresh token & URLs
    const fullItem = await API.getMediaItem(item.id);

    if (item.media_type === 'video') {
      videoPlayer.open(fullItem);
    } else if (item.media_type === 'audio') {
      audioPlayer.playItem(fullItem, state.items);
    } else if (item.media_type === 'image') {
      openImageLightbox(fullItem);
    }
  }

  function openImageLightbox(item) {
    imageModalTitle.textContent = item.filename;
    imageModalImg.src = item.download_url || `/api/media/${item.id}/download`;
    imageModalDownload.href = item.download_url || `/api/media/${item.id}/download`;
    imageModalDownload.download = item.filename;
    imageModal.classList.remove('hidden');
  }

  // Filter Pills
  filterPills.forEach((pill) => {
    pill.addEventListener('click', () => {
      filterPills.forEach((p) => p.classList.remove('active'));
      pill.classList.add('active');
      state.currentType = pill.dataset.type;
      loadLibrary();
    });
  });

  // Search Input with Debounce
  let searchTimeout;
  searchInput.addEventListener('input', () => {
    clearTimeout(searchTimeout);
    const val = searchInput.value.trim();
    clearSearchBtn.classList.toggle('hidden', val.length === 0);

    searchTimeout = setTimeout(() => {
      state.searchQuery = val;
      loadLibrary();
    }, 250);
  });

  clearSearchBtn.addEventListener('click', () => {
    searchInput.value = '';
    clearSearchBtn.classList.add('hidden');
    state.searchQuery = '';
    loadLibrary();
  });

  // Sort Controls
  sortSelect.addEventListener('change', () => {
    const [field, dir] = sortSelect.value.split(':');
    state.sortBy = field;
    state.sortOrder = dir;
    loadLibrary();
  });

  // View Switcher (Grid / List)
  viewToggleBtn.addEventListener('click', () => {
    state.isListView = !state.isListView;
    grid.classList.toggle('list-view', state.isListView);
  });

  // Refresh Sync Button
  refreshBtn.addEventListener('click', async () => {
    refreshBtn.style.transform = 'rotate(180deg)';
    await API.triggerScan();
    await loadLibrary();
    setTimeout(() => {
      refreshBtn.style.transform = 'none';
    }, 400);
  });

  // File Upload Handlers
  fileUploadInput.addEventListener('change', () => {
    if (fileUploadInput.files.length > 0) {
      handleUploadQueue(Array.from(fileUploadInput.files));
      fileUploadInput.value = '';
    }
  });

  // Window Drag and Drop
  window.addEventListener('dragover', (e) => e.preventDefault());
  window.addEventListener('drop', (e) => {
    e.preventDefault();
    if (e.dataTransfer.files.length > 0) {
      handleUploadQueue(Array.from(e.dataTransfer.files));
    }
  });

  async function handleUploadQueue(files) {
    uploadCard.classList.remove('hidden');

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      uploadFilename.textContent = `Uploading ${file.name} (${i + 1}/${files.length})...`;
      uploadProgressBar.style.width = '0%';
      uploadPercent.textContent = '0%';

      try {
        await API.uploadFile(file, (percent) => {
          uploadProgressBar.style.width = `${percent}%`;
          uploadPercent.textContent = `${percent}%`;
        });
      } catch (err) {
        console.error(`Upload error on ${file.name}:`, err);
      }
    }

    uploadFilename.textContent = 'All uploads complete!';
    setTimeout(() => {
      uploadCard.classList.add('hidden');
    }, 1500);

    loadLibrary();
  }

  // Helpers
  function formatDuration(sec) {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  }

  function formatFileSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // Initial Load
  loadLibrary();
});
