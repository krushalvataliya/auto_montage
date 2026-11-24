# Configuration Guide & Presets

All behavior in the Automated Video Generator is controlled via [`config.yaml`](file:///c:/Users/Krushal%20Vataliya/Downloads/yt%20retune/video%20generator/config.yaml) without modifying source code.

---

## 1. Configuration Parameter Reference

### `paths` Block
Configures file locations and binary paths.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `input_dir` | `string` | `"./input"` | Path to input directory containing videos, music, and logo. |
| `output_dir` | `string` | `""` | Destination directory for exported final video. Leave empty (`""`) to save directly inside `input_dir` by default. |
| `temp_dir` | `string` | `"./temp"` | Directory for intermediate normalized clips and concat lists. |
| `log_dir` | `string` | `"./logs"` | Directory for persistent log files (`video_editor.log`). |
| `output_filename` | `string` | `""` | File name of the exported video. Leave empty (`""`) to automatically use `"<folder_name> - final video.mp4"`. |
| `ffmpeg_path` | `string` | `""` | Optional explicit path to `ffmpeg.exe` (leave empty for auto-discovery). |
| `ffprobe_path` | `string` | `""` | Optional explicit path to `ffprobe.exe` (leave empty for auto-discovery). |

---

### `video` Block
Controls slow motion, format normalization, and encoding quality.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `slow_motion_speed` | `float` | `0.66` | Playback speed factor. `0.66` = 66% speed (slow motion). `1.0` = normal speed. |
| `target_width` | `int` | `1920` | Output video canvas width in pixels. |
| `target_height` | `int` | `1080` | Output video canvas height in pixels. |
| `target_fps` | `int` | `30` | Output frame rate in frames per second. |
| `scaling_mode` | `string` | `"pad"` | Aspect ratio strategy: `"pad"` (letterbox/pillarbox) or `"crop"` (fill canvas). |
| `video_codec` | `string` | `"libx264"` | Video codec (H.264 standard for universal compatibility). |
| `crf` | `int` | `18` | Constant Rate Factor (0-51). Lower = higher quality. 17-20 is visually lossless. |
| `preset` | `string` | `"fast"` | x264 preset (`ultrafast`, `faster`, `fast`, `medium`, `slow`). |

---

### `audio` Block
Controls background music, audio transitions, and codec settings.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `music_filename` | `string` | `""` | Optional explicit music filename. If empty, auto-detects single audio file. |
| `fade_in_duration` | `float` | `1.0` | Music fade-in duration in seconds at start of video. |
| `fade_out_duration`| `float` | `2.0` | Music fade-out duration in seconds at end of video. |
| `audio_codec` | `string` | `"aac"` | Audio codec. Recommended: `"aac"`. |
| `audio_bitrate` | `string` | `"192k"` | Audio encoding bitrate (e.g., `"192k"`, `"256k"`, `"320k"`). |

---

### `logo` Block
Controls logo overlay visibility, geometry, and placement.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `enabled` | `bool` | `true` | Set `false` to disable logo overlay entirely. |
| `filename` | `string` | `""` | Optional explicit PNG filename. If empty, auto-detects single PNG file. |
| `position` | `string` | `"bottom-right"` | Position: `"top-left"`, `"top-right"`, `"bottom-left"`, `"bottom-right"`, `"center"`. |
| `width_percent` | `float` | `12.0` | Logo width as percentage of canvas width (12% of 1920 = 230px). |
| `max_width_px` | `int` | `250` | Maximum cap on logo width in pixels. |
| `max_height_px`| `int/null` | `null` | Optional max height cap in pixels (null preserves aspect ratio). |
| `margin_x` | `int` | `30` | Horizontal margin from canvas border in pixels. |
| `margin_y` | `int` | `30` | Vertical margin from canvas border in pixels. |
| `opacity` | `float` | `1.0` | Transparency multiplier (0.0 = invisible, 1.0 = fully opaque). |

---

### `sequence` Block
Controls video playlist arrangement.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `random_seed` | `int/null` | `null` | Set an integer (e.g. `42`) for deterministic, reproducible reuse sequences. |

---

### `execution` Block
Controls logging and error tolerance.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `log_level` | `string` | `"INFO"` | Console and logfile verbosity: `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`. |
| `on_corrupt_file`| `string`| `"abort"` | Error policy: `"abort"` terminates on unreadable files; `"skip"` excludes them. |
| `keep_temp` | `bool` | `true` | Retain cached clips in `temp/` to accelerate subsequent runs. |

---

## 2. Practical Configuration Presets

### Recipe A: Standard YouTube Video (16:9 Landscape 1080p)
```yaml
video:
  slow_motion_speed: 0.66
  target_width: 1920
  target_height: 1080
  target_fps: 30
  scaling_mode: "pad"
  crf: 18
  preset: "fast"
logo:
  enabled: true
  position: "bottom-right"
  width_percent: 12.0
  max_width_px: 250
  margin_x: 30
  margin_y: 30
```

### Recipe B: YouTube Shorts / Instagram Reels (9:16 Vertical)
```yaml
video:
  slow_motion_speed: 0.66
  target_width: 1080
  target_height: 1920
  target_fps: 30
  scaling_mode: "crop"    # Crops landscape videos to fill vertical frame
  crf: 18
  preset: "fast"
logo:
  enabled: true
  position: "top-right"
  width_percent: 20.0
  max_width_px: 200
  margin_x: 40
  margin_y: 120           # Extra vertical margin to avoid platform UI overlays
```

### Recipe C: 4K Ultra-HD Master (3840x2160 @ 60 FPS)
```yaml
video:
  slow_motion_speed: 0.50 # 2x slow motion
  target_width: 3840
  target_height: 2160
  target_fps: 60
  scaling_mode: "pad"
  crf: 16                 # Near lossless master
  preset: "medium"
audio:
  audio_bitrate: "320k"
logo:
  width_percent: 10.0
  max_width_px: 400
  margin_x: 60
  margin_y: 60
```

### Recipe D: Fast Draft / Low-Res Preview
```yaml
video:
  slow_motion_speed: 0.66
  target_width: 1280
  target_height: 720
  target_fps: 24
  crf: 26                 # Smaller file, much faster render
  preset: "ultrafast"
```
