# Automated Video Editing Application

A modular, production-ready Python application that automatically generates an edited video using dynamic video clips, background music, and an optional PNG logo overlay.

---

## Key Features

- **Dynamic File Discovery:**
  - Automatically identifies video files (`.mp4`, `.mov`, `.avi`, `.mkv`, etc.).
  - Detects background music track (`.mp3`, `.wav`, `.aac`, etc.).
  - Detects PNG logo file with transparency (`.png`).
  - Ignores non-media files (`.txt`, `.json`, lyrics, prompt files, etc.).
- **Natural Numerical Sorting & Prefix Grouping:**
  - Natural numerical sorting (e.g. `vid1`, `vid2`, `vid3`, ..., `vid10`).
  - Groups files by prefix (e.g. `gfl1`, `gfl2`, `smb1`, `travel1`).
  - Sequence gap detection: detects missing sequence numbers and logs a warning without crashing.
  - Fallback natural alphabetical sort for non-numerical filenames.
- **Slow Motion & Format Normalization:**
  - User-configurable slow-motion playback speed (default: `0.66x` / 66% speed).
  - Completely strips original audio from all video clips (`-an`).
  - Automatically normalizes all clips to standard output resolution (e.g., `1920x1080` @ `30 FPS`).
  - Configurable aspect ratio handling (`pad` for letterbox/pillarbox or `crop` to fill).
  - High visual quality encoding using H.264 with configurable CRF.
- **Two-Stage Video Arrangement & Fair Reuse:**
  - **Stage 1 (Sequential Playback):** Plays every detected video once in numerical sequence.
  - **Stage 2 (Fair Random Reuse):** If music duration exceeds available footage, randomly appends clips using a fair shuffle-bag algorithm:
    - Never picks the same clip consecutively.
    - Ensures every clip has a chance to be reused before repeating.
    - Supports an optional random seed for reproducible edits.
- **Millisecond-Accurate Duration Matching:**
  - Matches final video duration strictly to background music duration.
  - Trims only the final segment if it exceeds the remaining music duration.
  - No black frames, blank gaps, or frozen frames.
- **Configurable PNG Logo Overlay:**
  - Positions: `top-left`, `top-right`, `bottom-left`, `bottom-right`, `center`.
  - Configurable sizing via percentage of video width, max width in pixels, and optional max height.
  - Strict aspect ratio preservation (never stretched or distorted).
  - Preserves alpha transparency and respects margin boundaries.
- **Background Music Handling:**
  - Single audio track sourced from background music file.
  - Configurable audio fade-in and fade-out durations.
  - High quality AAC audio encoding.

---

## Project Structure

```text
video generator/
├── main.py                     # Main CLI entry point
├── config.yaml                 # Central configuration file
├── requirements.txt            # Python dependencies
├── README.md                   # Full documentation & guide
├── src/
│   ├── __init__.py
│   ├── file_discovery.py       # Scans input folder and validates media files
│   ├── video_sorting.py        # Natural numerical sorting and gap detection
│   ├── video_processing.py     # Slow-motion, audio removal, format normalization
│   ├── video_sequence.py       # Two-stage sequence planner & fair reuse logic
│   ├── duration_manager.py     # Duration calculations & analysis
│   ├── logo_overlay.py         # Logo overlay filter building & positioning
│   ├── audio_processing.py     # Background music filter & fade-in/out
│   ├── video_export.py         # FFmpeg concat demuxer & final MP4 export
│   └── utils.py                # FFmpeg detection, media probing, logging
├── input/                      # Default input directory (or configure custom path)
├── output/                     # Exported final video directory
├── temp/                       # Intermediate normalized clips & playlists
└── logs/                       # Application execution log files
```

---

## Installation & Prerequisites

### 1. Python Environment
Requires **Python 3.11** or newer.

```bash
cd "video generator"
pip install -r requirements.txt
```

### 2. FFmpeg Installation

The application requires FFmpeg. You can install it using any of the methods below:

#### Method A: Windows Package Manager (Winget) - Recommended
```powershell
winget install Gyan.FFmpeg
```

#### Method B: Python Static-FFmpeg Package
The application includes `static-ffmpeg` in `requirements.txt`. It will automatically add FFmpeg to the environment:
```bash
pip install static-ffmpeg
```

#### Method C: Manual Installation
1. Download FFmpeg from [Gyan.dev](https://www.gyan.dev/ffmpeg/builds/) or [FFmpeg.org](https://ffmpeg.org/download.html).
2. Extract the archive (e.g. to `C:\ffmpeg`).
3. Add `C:\ffmpeg\bin` to your system `PATH` environment variable, or configure `ffmpeg_path` in `config.yaml`:
   ```yaml
   paths:
     ffmpeg_path: "C:/ffmpeg/bin/ffmpeg.exe"
     ffprobe_path: "C:/ffmpeg/bin/ffprobe.exe"
   ```

---

## Configuration (`config.json` & `config.yaml`)

You can run the application with **zero command-line arguments**:
```bash
python main.py
```
It automatically loads [`config.json`](file:///c:/Users/Krushal%20Vataliya/Downloads/yt%20retune/video%20generator/config.json) (or falls back to `config.yaml`).

### Example `config.json`:
```json
{
  "input": "c:/Users/Krushal Vataliya/Downloads/yt retune/Girnaar Farte Lili Parikramaa",
  "output": "",
  "speed": 0.66,
  "seed": 42,
  "logo_path": "",
  "logo": {
    "enabled": true,
    "position": "bottom-right",
    "width_percent": 12.0,
    "max_width_px": 250,
    "max_height_px": null,
    "margin_x": 30,
    "margin_y": 30,
    "opacity": 1.0
  },
  "video": {
    "target_width": 1920,
    "target_height": 1080,
    "target_fps": 30,
    "scaling_mode": "pad",
    "video_codec": "libx264",
    "crf": 18,
    "preset": "fast"
  },
  "audio": {
    "music_filename": "",
    "fade_in_duration": 1.0,
    "fade_out_duration": 2.0,
    "audio_codec": "aac",
    "audio_bitrate": "192k"
  },
  "paths": {
    "temp_dir": "./temp",
    "log_dir": "./logs",
    "ffmpeg_path": "",
    "ffprobe_path": ""
  },
  "execution": {
    "log_level": "INFO",
    "on_corrupt_file": "abort",
    "keep_temp": true
  }
}
```

---

## How Video Selection & Duration Calculation Work

### 1. Slow Motion Calculation
For every input video:
$$\text{Output Duration} = \frac{\text{Original Duration}}{\text{slow\_motion\_speed}}$$
For example, a 10.0-second video at `0.66x` speed results in:
$$\frac{10.0}{0.66} \approx 15.15\text{ seconds}$$
FFmpeg video filter: `setpts=(1/0.66)*PTS` with fixed target frame rate (`fps=30`).

### 2. Stage 1: Sequential Playback
- Files are sorted naturally by their numerical suffix (`gfl1`, `gfl2`, ..., `gfl7`).
- All clips are placed sequentially into the playlist.
- If the cumulative duration of Stage 1 reaches or exceeds the music duration $T_{\text{music}}$, the final clip is trimmed to exact remaining duration and Stage 2 is skipped.

### 3. Stage 2: Fair Random Reuse
- If cumulative duration $T_{\text{seq}} < T_{\text{music}}$, additional footage is needed.
- A shuffle-bag algorithm generates random permutations of available clips.
- Rules:
  1. **No consecutive duplicates:** The first clip of a new round never matches the last clip of the previous round.
  2. **Fair distribution:** Every source clip has an opportunity to be used once before any clip can be used a third time.
  3. **Exact trimming:** When cumulative duration reaches $T_{\text{music}}$, the final clip is trimmed to:
     $$\Delta t = T_{\text{music}} - \sum_{i=1}^{k-1} t_i$$
     This guarantees zero black frames and an exact duration match down to the millisecond.

---

## Execution

### Run with default configuration:
```bash
python main.py
```

### Run with CLI overrides:
```bash
python main.py --input "path/to/my_folder" --output "path/to/my_output" --speed 0.5 --seed 42
```

---

## Verification & Error Handling

- **Input Folder Validation:** Verifies folder exists and contains valid media.
- **Corrupt Media Handling:** Checks videos with ffprobe before processing; configurable to `abort` or `skip`.
- **Media Format Normalization:** Automatically conforms mixed resolutions, aspect ratios, and frame rates to standard canvas.
- **Logs:** Real-time detailed console output and persistent file logging in `logs/video_editor.log`.
