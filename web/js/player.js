/**
 * USPC Video Player Modal Controller
 */

class VideoPlayerController {
  constructor() {
    this.modal = document.getElementById('video-modal');
    this.video = document.getElementById('native-video-element');
    this.title = document.getElementById('video-modal-title');
    this.downloadBtn = document.getElementById('video-modal-download');
    this.closeBtn = document.getElementById('video-modal-close');

    this.initEvents();
  }

  initEvents() {
    this.closeBtn.addEventListener('click', () => this.close());
    this.modal.addEventListener('click', (e) => {
      if (e.target === this.modal) this.close();
    });

    document.addEventListener('keydown', (e) => {
      if (this.modal.classList.contains('hidden')) return;

      if (e.key === 'Escape') {
        this.close();
      } else if (e.code === 'Space' && e.target.tagName !== 'INPUT') {
        e.preventDefault();
        this.togglePlay();
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        this.video.currentTime += 5;
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        this.video.currentTime -= 5;
      } else if (e.key === 'f' || e.key === 'F') {
        this.toggleFullscreen();
      } else if (e.key === 'm' || e.key === 'M') {
        this.video.muted = !this.video.muted;
      }
    });
  }

  open(item) {
    this.title.textContent = item.title || item.filename;
    this.downloadBtn.href = item.download_url || `/api/media/${item.id}/download`;
    this.downloadBtn.download = item.filename;

    const streamUrl = item.stream_url || `/api/media/${item.id}/stream?token=${item.playback_token || ''}`;
    this.video.src = streamUrl;
    this.modal.classList.remove('hidden');
    this.video.play().catch(() => {});
  }

  close() {
    this.video.pause();
    this.video.src = '';
    this.modal.classList.add('hidden');
  }

  togglePlay() {
    if (this.video.paused) {
      this.video.play();
    } else {
      this.video.pause();
    }
  }

  toggleFullscreen() {
    if (!document.fullscreenElement) {
      this.video.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen().catch(() => {});
    }
  }
}
