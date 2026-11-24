# Troubleshooting Guide & FAQ

This document covers common operational questions, error codes, and troubleshooting steps.

---

## 1. Common Error Messages & Solutions

### Error: `FFmpegNotFoundError: Missing required executables: ffmpeg`
- **Cause:** FFmpeg is not found in system `PATH` or `config.yaml`.
- **Solution:**
  1. Install via pip: `pip install static-ffmpeg`.
  2. Or install via Windows Package Manager: `winget install Gyan.FFmpeg`.
  3. Or set explicit executable paths in `config.yaml`:
     ```yaml
     paths:
       ffmpeg_path: "C:/ffmpeg/bin/ffmpeg.exe"
       ffprobe_path: "C:/ffmpeg/bin/ffprobe.exe"
     ```

---

### Error: `FileDiscoveryError: No valid video files found in '...'`
- **Cause:** Input folder contains no recognized video files.
- **Solution:** Ensure input clips have supported extensions: `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`, `.flv`, `.wmv`, `.m4v`. Check that `paths.input_dir` points to the correct folder.

---

### Error: `FileDiscoveryError: Multiple audio files detected: [...]`
- **Cause:** The input folder contains more than one background audio file, and the application cannot guess which one to use.
- **Solution:**
  - Remove extraneous audio files so only one remains, OR
  - Specify the exact music file in `config.yaml`:
    ```yaml
    audio:
      music_filename: "my_song.mp3"
    ```

---

### Error: `FileDiscoveryError: Logo overlay is enabled, but no PNG logo was found`
- **Cause:** `logo.enabled` is `true`, but no `.png` file exists in the input directory.
- **Solution:**
  - Place your transparent `.png` logo in the input folder, OR
  - If you do not want a logo, set `logo.enabled: false` in `config.yaml`, OR
  - Specify an absolute path to the logo:
    ```yaml
    logo:
      filename: "C:/path/to/my_logo.png"
    ```

---

### Error: `MediaProcessingError: Corrupted or unreadable video file`
- **Cause:** A video file in the input directory has corrupted moov atoms or truncated headers.
- **Solution:**
  - Inspect the specific file identified in `logs/video_editor.log`.
  - If you wish the application to automatically skip corrupted files and continue rendering with healthy videos, set:
    ```yaml
    execution:
      on_corrupt_file: "skip"
    ```

---

## 2. Frequently Asked Questions (FAQ)

### Q: Why is there a slight gap between videos or black frames?
**A:** There are zero black frames in this architecture. All clips are pre-normalized to matching dimensions (1920x1080), square pixels (`setsar=1`), identical frame rate (30 FPS), and pixel format (`yuv420p`). This allows the FFmpeg concat demuxer to transition between clips with continuous frame continuity.

### Q: How do I change the slow motion speed?
**A:** In `config.yaml`, modify `video.slow_motion_speed`:
- `0.50` = Half speed (2x slow motion)
- `0.66` = 66% speed (standard slow motion)
- `1.00` = Normal original speed
You can also override this on the command line:
```bash
python main.py --speed 0.5
```

### Q: Can I render vertical videos for YouTube Shorts or Instagram Reels?
**A:** Yes. In `config.yaml`, change the dimensions and scaling mode:
```yaml
video:
  target_width: 1080
  target_height: 1920
  scaling_mode: "crop"   # Fills 9:16 vertical canvas without black bars
```

### Q: Does the application re-encode every video from scratch on each run?
**A:** No. Pre-processed normalized clips are cached in `temp/normalized_clips/`. If the source video file, target resolution, and speed factor have not changed, the cache is reused automatically, reducing rendering time to seconds.

### Q: How do I clean up temporary files?
**A:** You can safely delete the contents of `temp/` at any time, or set `execution.keep_temp: false` in `config.yaml`.
