/**
 * USPC Persistent Audio Dock Player Controller
 */

class AudioDockController {
  constructor() {
    this.dock = document.getElementById('audio-dock-player');
    this.audio = document.getElementById('native-audio-element');
    this.title = document.getElementById('audio-dock-title');
    this.artist = document.getElementById('audio-dock-artist');
    this.playBtn = document.getElementById('audio-play-btn');
    this.prevBtn = document.getElementById('audio-prev-btn');
    this.nextBtn = document.getElementById('audio-next-btn');
    this.seekBar = document.getElementById('audio-seek-bar');
    this.currentTimeLabel = document.getElementById('audio-current-time');
    this.totalTimeLabel = document.getElementById('audio-total-time');
    this.volumeBar = document.getElementById('audio-volume-bar');
    this.muteBtn = document.getElementById('audio-mute-btn');
    this.downloadBtn = document.getElementById('audio-dock-download');
    this.closeBtn = document.getElementById('audio-close-btn');

    this.queue = [];
    this.currentIndex = -1;
    this.isDragging = false;

    this.initEvents();
  }

  initEvents() {
    this.playBtn.addEventListener('click', () => this.togglePlay());
    this.prevBtn.addEventListener('click', () => this.playPrevious());
    this.nextBtn.addEventListener('click', () => this.playNext());
    this.closeBtn.addEventListener('click', () => this.close());

    // Audio time update
    this.audio.addEventListener('timeupdate', () => {
      if (!this.isDragging && this.audio.duration) {
        const percent = (this.audio.currentTime / this.audio.duration) * 100;
        this.seekBar.value = percent;
        this.currentTimeLabel.textContent = this.formatTime(this.audio.currentTime);
      }
    });

    this.audio.addEventListener('loadedmetadata', () => {
      this.totalTimeLabel.textContent = this.formatTime(this.audio.duration);
    });

    this.audio.addEventListener('ended', () => {
      this.playNext();
    });

    this.audio.addEventListener('play', () => {
      this.playBtn.textContent = '⏸';
    });

    this.audio.addEventListener('pause', () => {
      this.playBtn.textContent = '▶';
    });

    // Seeking
    this.seekBar.addEventListener('input', () => {
      this.isDragging = true;
    });

    this.seekBar.addEventListener('change', () => {
      if (this.audio.duration) {
        this.audio.currentTime = (this.seekBar.value / 100) * this.audio.duration;
      }
      this.isDragging = false;
    });

    // Volume
    this.volumeBar.addEventListener('input', () => {
      this.audio.volume = parseFloat(this.volumeBar.value);
      this.muteBtn.textContent = this.audio.volume === 0 ? '🔇' : '🔊';
    });

    this.muteBtn.addEventListener('click', () => {
      this.audio.muted = !this.audio.muted;
      this.muteBtn.textContent = this.audio.muted ? '🔇' : '🔊';
    });
  }

  playItem(item, fullList = []) {
    if (fullList.length > 0) {
      this.queue = fullList.filter(i => i.media_type === 'audio');
      this.currentIndex = this.queue.findIndex(i => i.id === item.id);
    } else {
      this.queue = [item];
      this.currentIndex = 0;
    }

    this.loadCurrentTrack();
  }

  loadCurrentTrack() {
    if (this.currentIndex < 0 || this.currentIndex >= this.queue.length) return;

    const item = this.queue[this.currentIndex];
    this.title.textContent = item.title || item.filename;
    this.artist.textContent = item.artist ? `${item.artist} • ${item.album || ''}` : (item.album || 'Audio Track');
    this.downloadBtn.href = item.download_url || `/api/media/${item.id}/download`;

    const streamUrl = item.stream_url || `/api/media/${item.id}/stream?token=${item.playback_token || ''}`;
    this.audio.src = streamUrl;
    this.dock.classList.remove('hidden');
    this.audio.play().catch(() => {});
  }

  togglePlay() {
    if (this.audio.paused) {
      this.audio.play();
    } else {
      this.audio.pause();
    }
  }

  playNext() {
    if (this.currentIndex < this.queue.length - 1) {
      this.currentIndex++;
      this.loadCurrentTrack();
    }
  }

  playPrevious() {
    if (this.currentIndex > 0) {
      this.currentIndex--;
      this.loadCurrentTrack();
    }
  }

  close() {
    this.audio.pause();
    this.audio.src = '';
    this.dock.classList.add('hidden');
  }

  formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return '0:00';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  }
}
