# USPC Supported Media Formats & Streaming Architecture

USPC natively indexes, streams, and processes video, audio, and photo formats with HTTP 206 Partial Content range requests and chunked file reading.

## Supported Formats Matrix

| Category | File Extensions | Streaming Mode | Metadata Extraction | Thumbnail / Cover Art |
|---|---|---|---|---|
| **Video** | `.mp4`, `.webm`, `.m4v` | Native Browser HTML5 (HTTP 206) | FFprobe (Duration, Resolution, Codec) | FFmpeg 10% Frame Grab (WebP) |
| **Video (Non-Native)** | `.mkv`, `.avi`, `.mov`, `.wmv`, `.flv`, `.ts` | Faststart H.264 Transcode / Direct Stream | FFprobe (Stream tags) | FFmpeg Frame Grab / Video Badge |
| **Audio** | `.mp3`, `.aac`, `.m4a`, `.ogg`, `.opus`, `.wav`, `.flac`, `.wma` | Native HTML5 Audio (HTTP 206) | FFprobe (ID3 Title, Artist, Album) | Embedded ID3 Cover Art / Audio Badge |
| **Images** | `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`, `.bmp`, `.svg`, `.tiff` | Direct / Lightbox (WebP/Original) | Pillow (Dimensions, EXIF) | Lanczos 320px WebP Thumbnail |

---

## Streaming Optimization & Performance Rules

1. **Zero Full-Memory Buffering**: Media is read in configurable 64KB - 256KB async chunks without loading 4K/10GB+ files into RAM.
2. **Instant Seeking**: Range requests seek directly to the exact byte position on disk.
3. **In-Flight Deduplication**: Simultaneous requests for the same media generation share a single background processing future.
4. **Original File Protection**: Generated thumbnails and transcoded files are stored separately in `media_cache/` and never modify original source files.
