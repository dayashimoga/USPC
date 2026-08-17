/**
 * USPC Media API Client
 */

const API = {
  baseUrl: '',

  async getHealth() {
    const res = await fetch(`${this.baseUrl}/api/health`);
    if (!res.ok) throw new Error('Health check failed');
    return res.json();
  },

  async listMedia({ type = '', search = '', sort = 'mtime', order = 'DESC', limit = 100, offset = 0 } = {}) {
    const params = new URLSearchParams();
    if (type) params.append('type', type);
    if (search) params.append('search', search);
    if (sort) params.append('sort', sort);
    if (order) params.append('order', order);
    params.append('limit', limit);
    params.append('offset', offset);

    const res = await fetch(`${this.baseUrl}/api/media?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to fetch media list');
    return res.json();
  },

  async getMediaItem(id) {
    const res = await fetch(`${this.baseUrl}/api/media/${id}`);
    if (!res.ok) throw new Error('Failed to get media item details');
    return res.json();
  },

  async triggerScan() {
    const res = await fetch(`${this.baseUrl}/api/scan`, { method: 'POST' });
    return res.json();
  },

  uploadFile(file, onProgress) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const formData = new FormData();
      formData.append('file', file);

      xhr.open('POST', `${this.baseUrl}/api/upload`);

      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable && onProgress) {
          const percent = Math.round((e.loaded / e.total) * 100);
          onProgress(percent);
        }
      };

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(JSON.parse(xhr.responseText));
        } else {
          reject(new Error(`Upload failed with status ${xhr.status}`));
        }
      };

      xhr.onerror = () => reject(new Error('Network upload error'));
      xhr.send(formData);
    });
  }
};
