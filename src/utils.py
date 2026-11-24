import json
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("video_editor")


class FFmpegNotFoundError(Exception):
    """Raised when FFmpeg executables are not found."""
    pass


class MediaProcessingError(Exception):
    """Raised when media analysis or processing fails."""
    pass


def find_ffmpeg(
    config_ffmpeg: Optional[str] = None,
    config_ffprobe: Optional[str] = None
) -> Tuple[str, Optional[str]]:
    """
    Locates FFmpeg and FFprobe executables.
    Checks:
      1. Explicit config paths.
      2. static-ffmpeg package (auto-adds to PATH).
      3. System PATH.
      4. Known default Windows directories (WinGet, Cypress, Scoop, C:\ffmpeg, etc.).
    Returns (ffmpeg_bin, ffprobe_bin). ffprobe_bin may be None if ffmpeg fallback is used.
    """
    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
    except Exception:
        pass

    ffmpeg_bin: Optional[str] = None
    ffprobe_bin: Optional[str] = None

    # 1. Config paths
    if config_ffmpeg and Path(config_ffmpeg).is_file():
        ffmpeg_bin = str(Path(config_ffmpeg).resolve())
    if config_ffprobe and Path(config_ffprobe).is_file():
        ffprobe_bin = str(Path(config_ffprobe).resolve())

    # 2. System PATH
    if not ffmpeg_bin:
        ffmpeg_bin = shutil.which("ffmpeg")
    if not ffprobe_bin:
        ffprobe_bin = shutil.which("ffprobe")

    # 3. Known Windows candidate locations
    candidate_roots = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Links",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages",
        Path("C:/ffmpeg/bin"),
        Path("C:/Program Files/ffmpeg/bin"),
        Path(os.environ.get("USERPROFILE", "")) / "scoop" / "shims",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Cypress" / "Cache",
    ]

    for root in candidate_roots:
        if not root.exists():
            continue
        if not ffmpeg_bin:
            match = next(root.rglob("ffmpeg.exe"), None)
            if match and match.is_file():
                ffmpeg_bin = str(match.resolve())
        if not ffprobe_bin:
            match = next(root.rglob("ffprobe.exe"), None)
            if match and match.is_file():
                ffprobe_bin = str(match.resolve())

    if not ffmpeg_bin:
        raise FFmpegNotFoundError(
            "FFmpeg executable not found.\n"
            "Please install FFmpeg using 'winget install Gyan.FFmpeg' or specify 'ffmpeg_path' in config.yaml."
        )

    logger.debug("Selected ffmpeg: %s", ffmpeg_bin)
    logger.debug("Selected ffprobe: %s", ffprobe_bin or "None (using ffmpeg fallback)")
    return ffmpeg_bin, ffprobe_bin


def run_command(cmd: List[str], desc: str = "") -> subprocess.CompletedProcess:
    """
    Executes a shell/subprocess command safely and logs output.
    Raises MediaProcessingError on nonzero exit codes.
    """
    logger.debug("Running [%s]: %s", desc, " ".join(f'"{c}"' if " " in c else c for c in cmd))
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
    except Exception as e:
        logger.error("Failed to spawn process '%s': %s", desc, e)
        raise MediaProcessingError(f"Failed to spawn process '{desc}': {e}") from e

    if proc.returncode != 0:
        err_msg = (
            f"Command failed [{desc}] with exit code {proc.returncode}.\n"
            f"Command: {' '.join(cmd)}\n"
            f"Error details:\n{proc.stderr.strip()}"
        )
        logger.error(err_msg)
        raise MediaProcessingError(err_msg)

    return proc


def _probe_with_ffmpeg(file_path: Path, ffmpeg_bin: str) -> Dict[str, Any]:
    """
    Fallback probe using 'ffmpeg -i <file>' stderr parsing when ffprobe is unavailable.
    """
    cmd = [ffmpeg_bin, "-i", str(file_path.resolve())]
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    output = proc.stderr

    duration: Optional[float] = None
    dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", output)
    if dur_match:
        h, m, s = dur_match.groups()
        duration = int(h) * 3600 + int(m) * 60 + float(s)

    streams = []
    # Video stream regex
    vid_match = re.search(r"Stream #\d+:\d+.*?: Video:.*?(\d{2,5})x(\d{2,5})", output)
    if vid_match:
        w, h = vid_match.groups()
        streams.append({
            "codec_type": "video",
            "width": int(w),
            "height": int(h),
            "duration": str(duration) if duration else None
        })

    # Audio stream regex
    aud_match = re.search(r"Stream #\d+:\d+.*?: Audio:", output)
    if aud_match:
        streams.append({
            "codec_type": "audio",
            "duration": str(duration) if duration else None
        })

    return {
        "format": {"duration": str(duration) if duration else None},
        "streams": streams
    }


def get_media_info(file_path: Path, probe_bin: Optional[str], ffmpeg_bin: Optional[str] = None) -> Dict[str, Any]:
    """
    Extracts complete media metadata using FFprobe or FFmpeg fallback.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Media file not found: {file_path}")

    if probe_bin and Path(probe_bin).is_file():
        cmd = [
            probe_bin,
            "-v", "error",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(file_path.resolve())
        ]
        result = run_command(cmd, f"Probe {file_path.name}")
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            logger.warning("ffprobe JSON parsing failed, attempting fallback: %s", e)

    if ffmpeg_bin:
        return _probe_with_ffmpeg(file_path, ffmpeg_bin)

    raise MediaProcessingError(f"No probe tool available to inspect {file_path.name}")


def get_duration(file_path: Path, probe_bin: Optional[str], ffmpeg_bin: Optional[str] = None) -> float:
    """
    Returns exact duration of media file in seconds (as float).
    """
    info = get_media_info(file_path, probe_bin, ffmpeg_bin)

    # 1. format.duration
    format_info = info.get("format", {})
    if format_info and "duration" in format_info and format_info["duration"] is not None:
        try:
            return float(format_info["duration"])
        except (ValueError, TypeError):
            pass

    # 2. streams duration
    streams = info.get("streams", [])
    for stream in streams:
        if "duration" in stream and stream["duration"] is not None:
            try:
                return float(stream["duration"])
            except (ValueError, TypeError):
                pass

    raise MediaProcessingError(f"Unable to determine duration for: {file_path.name}")


def setup_logger(
    log_file: Optional[Path] = None,
    log_level: str = "INFO"
) -> logging.Logger:
    """
    Sets up application logger with console and optional file handler.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)

    if not logger.handlers:
        console_fmt = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S"
        )
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(console_fmt)
        logger.addHandler(console_handler)

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_fmt = logging.Formatter(
            "%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(file_fmt)
        logger.addHandler(file_handler)

    return logger
