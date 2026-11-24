import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .utils import MediaProcessingError, get_duration, get_media_info, run_command

logger = logging.getLogger("video_editor")


@dataclass
class ProcessedClip:
    """Holds metadata of a pre-processed and normalized video clip."""
    original_path: Path
    processed_path: Path
    duration: float
    width: int
    height: int
    fps: float


class VideoProcessor:
    def __init__(
        self,
        ffmpeg_bin: str,
        ffprobe_bin: str,
        temp_dir: Path,
        slow_motion_speed: float = 0.66,
        target_width: int = 1920,
        target_height: int = 1080,
        target_fps: int = 30,
        scaling_mode: str = "pad",  # "pad" or "crop"
        video_codec: str = "libx264",
        crf: int = 18,
        preset: str = "fast",
        on_corrupt_file: str = "abort"  # "abort" or "skip"
    ):
        self.ffmpeg_bin = ffmpeg_bin
        self.ffprobe_bin = ffprobe_bin
        self.temp_dir = temp_dir
        self.slow_motion_speed = max(0.05, float(slow_motion_speed))
        self.target_width = target_width
        self.target_height = target_height
        self.target_fps = target_fps
        self.scaling_mode = scaling_mode.lower()
        self.video_codec = video_codec
        self.crf = crf
        self.preset = preset
        self.on_corrupt_file = on_corrupt_file.lower()

        self.clips_dir = self.temp_dir / "normalized_clips"
        self.clips_dir.mkdir(parents=True, exist_ok=True)

    def _file_hash(self, file_path: Path) -> str:
        """Computes short MD5 hash based on path and file size/mtime for cache invalidation."""
        stat = file_path.stat()
        meta_str = f"lossless_v2_{file_path.name}_{stat.st_size}_{stat.st_mtime}_{self.slow_motion_speed}_{self.target_width}_{self.target_height}_{self.target_fps}_{self.scaling_mode}"
        return hashlib.md5(meta_str.encode("utf-8")).hexdigest()[:10]

    def _build_filtergraph(self) -> str:
        """
        Builds the FFmpeg video filtergraph to apply slow motion and format normalization.
        """
        # Slow motion: PTS multiplier = 1 / speed
        # e.g. speed = 0.66 -> multiplier = 1 / 0.66 = 1.5151515...
        pts_factor = 1.0 / self.slow_motion_speed
        filters = [f"setpts={pts_factor:.6f}*PTS"]

        # Scaling and aspect ratio preservation
        if self.scaling_mode == "crop":
            # Scale to cover target box, then crop center
            filters.append(
                f"scale={self.target_width}:{self.target_height}:force_original_aspect_ratio=increase:flags=lanczos+accurate_rnd,"
                f"crop={self.target_width}:{self.target_height}:(iw-ow)/2:(ih-oh)/2"
            )
        else:
            # Default "pad": scale to fit within target box, pad remaining area with black
            filters.append(
                f"scale={self.target_width}:{self.target_height}:force_original_aspect_ratio=decrease:flags=lanczos+accurate_rnd,"
                f"pad={self.target_width}:{self.target_height}:(ow-iw)/2:(oh-ih)/2:black"
            )

        # Enforce square pixels (setsar=1) and fixed target frame rate
        filters.append("setsar=1")
        filters.append(f"fps={self.target_fps}")

        return ",".join(filters)

    def validate_video(self, file_path: Path) -> bool:
        """
        Checks if video file is valid and readable via ffprobe.
        """
        try:
            info = get_media_info(file_path, self.ffprobe_bin, self.ffmpeg_bin)
            video_streams = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]
            if not video_streams:
                logger.error("File '%s' contains no video streams.", file_path.name)
                return False
            return True
        except Exception as e:
            logger.error("Failed to validate video '%s': %s", file_path.name, e)
            return False

    def process_clip(self, input_video: Path, index: int) -> Optional[ProcessedClip]:
        """
        Applies slow-motion, removes audio, normalizes resolution and frame rate.
        Returns a ProcessedClip instance.
        """
        logger.info(
            "Processing clip [%d] '%s' (slow-motion: %.2fx, target: %dx%d @ %dfps)...",
            index, input_video.name, self.slow_motion_speed, self.target_width, self.target_height, self.target_fps
        )

        # Validate file
        if not self.validate_video(input_video):
            if self.on_corrupt_file == "skip":
                logger.warning("Skipping corrupted video '%s' as configured.", input_video.name)
                return None
            else:
                raise MediaProcessingError(f"Corrupted or unreadable video file: {input_video}")

        file_h = self._file_hash(input_video)
        output_filename = f"norm_{index:03d}_{input_video.stem}_{file_h}.mp4"
        output_path = self.clips_dir / output_filename

        # Re-use existing processed clip if valid
        if output_path.exists() and output_path.stat().st_size > 1000:
            try:
                dur = get_duration(output_path, self.ffprobe_bin, self.ffmpeg_bin)
                logger.info("Found cached normalized clip: '%s' (duration: %.2fs)", output_path.name, dur)
                return ProcessedClip(
                    original_path=input_video,
                    processed_path=output_path,
                    duration=dur,
                    width=self.target_width,
                    height=self.target_height,
                    fps=float(self.target_fps)
                )
            except Exception:
                logger.warning("Cached clip corrupted, re-processing: %s", output_path.name)

        vf = self._build_filtergraph()

        # Render intermediate normalized clip with True LOSSLESS H.264 (CRF 0)
        # to ensure zero generation loss before the final assembly pass!
        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-i", str(input_video.resolve()),
            "-vf", vf,
            "-an",  # Completely remove original audio
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "0",
            "-pix_fmt", "yuv420p",
            str(output_path.resolve())
        ]

        run_command(cmd, f"Normalize {input_video.name}")

        duration = get_duration(output_path, self.ffprobe_bin, self.ffmpeg_bin)
        logger.info("Successfully processed '%s' -> duration: %.3fs", output_path.name, duration)

        return ProcessedClip(
            original_path=input_video,
            processed_path=output_path,
            duration=duration,
            width=self.target_width,
            height=self.target_height,
            fps=float(self.target_fps)
        )

    def process_all(self, video_paths: List[Path]) -> List[ProcessedClip]:
        """
        Processes all sorted source videos.
        """
        processed_clips: List[ProcessedClip] = []
        for idx, vpath in enumerate(video_paths, start=1):
            clip = self.process_clip(vpath, idx)
            if clip is not None:
                processed_clips.append(clip)

        if not processed_clips:
            raise MediaProcessingError("No valid video clips could be processed.")

        total_avail_dur = sum(c.duration for c in processed_clips)
        logger.info(
            "All %d video clips processed. Total single-pass footage duration: %.2fs.",
            len(processed_clips), total_avail_dur
        )
        return processed_clips
