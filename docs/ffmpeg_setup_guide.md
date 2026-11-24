# FFmpeg Setup & Environment Guide

The application relies on **FFmpeg** and **FFprobe** for media demuxing, video scaling, audio filtering, and MP4 container encoding.

---

## 1. Automatic Resolution via Python (Recommended)

The project includes `static-ffmpeg` in `requirements.txt`:
```bash
pip install -r requirements.txt
```
When `static-ffmpeg` is installed, the application automatically provisions and detects standalone binaries on first run. No manual PATH configuration is required.

---

## 2. System-Level Installation Options

If you prefer installing FFmpeg as a system binary on your OS, use any of the options below:

### Windows (Winget) - Recommended
Run PowerShell as Administrator or standard user:
```powershell
winget install Gyan.FFmpeg
```
Once installed, restart your terminal to reload system `PATH`.

### Windows (Chocolatey)
```powershell
choco install ffmpeg
```

### Windows (Scoop)
```powershell
scoop install ffmpeg
```

### macOS (Homebrew)
```bash
brew install ffmpeg
```

### Linux (Ubuntu / Debian)
```bash
sudo apt update && sudo apt install -y ffmpeg
```

---

## 3. Manual Installation (Portable Zip)

1. Download an official release build from [Gyan.dev](https://www.gyan.dev/ffmpeg/builds/) (Windows `ffmpeg-release-full.7z` or `.zip`).
2. Extract to a stable directory, e.g. `C:\ffmpeg`.
3. Locate the `bin` directory:
   - `C:\ffmpeg\bin\ffmpeg.exe`
   - `C:\ffmpeg\bin\ffprobe.exe`
4. Either add `C:\ffmpeg\bin` to your Windows System `PATH` or point to it directly in `config.yaml`:
   ```yaml
   paths:
     ffmpeg_path: "C:/ffmpeg/bin/ffmpeg.exe"
     ffprobe_path: "C:/ffmpeg/bin/ffprobe.exe"
   ```

---

## 4. Verifying Installation

Verify that FFmpeg is available and compiled with required codecs:

```bash
ffmpeg -version
ffprobe -version
```

### Required Codecs & Filters
The application requires the following standard FFmpeg components (available in all modern builds):
- **Video Encoder:** `libx264` (H.264)
- **Audio Encoder:** `aac` (Advanced Audio Coding)
- **Demuxers:** `concat`, `mov,mp4,m4a,3gp,3g2,mj2`, `mp3`
- **Video Filters:** `setpts`, `scale`, `pad`, `crop`, `setsar`, `fps`, `overlay`
- **Audio Filters:** `atrim`, `asetpts`, `afade`
