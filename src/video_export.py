import logging
from pathlib import Path
from typing import List, Optional

from .audio_processing import AudioProcessor
from .logo_overlay import LogoConfig, LogoOverlayManager
from .utils import MediaProcessingError, get_duration, run_command
from .video_sequence import SequenceItem

logger = logging.getLogger("video_editor")


class VideoExporter:
    """
    Assembles the final video from normalized clips, background music, and optional PNG logo.
    Exports in MP4 container with H.264 and AAC codecs.
    """
    def __init__(
        self,
        ffmpeg_bin: str,
        ffprobe_bin: Optional[str],
        temp_dir: Path,
        output_dir: Path,
        output_filename: str = "final_video.mp4",
        video_codec: str = "libx264",
        crf: int = 18,
        preset: str = "fast",
        target_fps: int = 30
    ):
        self.ffmpeg_bin = ffmpeg_bin
        self.ffprobe_bin = ffprobe_bin
        self.temp_dir = temp_dir
        self.output_dir = output_dir
        self.output_filename = output_filename
        self.video_codec = video_codec
        self.crf = crf
        self.preset = preset
        self.target_fps = target_fps

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def _prepare_concat_list(
        self,
        sequence: List[SequenceItem]
    ) -> Path:
        """
        Creates an FFmpeg concat demuxer text file.
        If the final clip is trimmed, produces an accurate trimmed segment first.
        """
        concat_file = self.temp_dir / "concat_playlist.txt"
        lines: List[str] = []

        for idx, item in enumerate(sequence):
            clip_path = item.clip.processed_path

            if item.is_trimmed:
                # Accurately trim this segment
                trimmed_clip_path = self.temp_dir / f"trimmed_final_seg_{idx}.mp4"
                logger.info(
                    "Trimming final sequence segment #%d '%s' to exact remaining duration: %.3fs",
                    item.order_index, clip_path.name, item.play_duration
                )
                cmd = [
                    self.ffmpeg_bin,
                    "-y",
                    "-ss", "0",
                    "-t", f"{item.play_duration:.6f}",
                    "-i", str(clip_path.resolve()),
                    "-c:v", self.video_codec,
                    "-preset", "ultrafast",
                    "-crf", str(self.crf),
                    "-pix_fmt", "yuv420p",
                    str(trimmed_clip_path.resolve())
                ]
                run_command(cmd, f"Trim final clip #{item.order_index}")
                clip_path = trimmed_clip_path

            # Format path for FFmpeg concat demuxer (forward slashes, escaped single quotes)
            escaped_path = str(clip_path.resolve()).replace("\\", "/").replace("'", "'\\''")
            lines.append(f"file '{escaped_path}'")

        concat_file.write_text("\n".join(lines), encoding="utf-8")
        logger.debug("Wrote concat demuxer list with %d clips to %s", len(lines), concat_file)
        return concat_file

    def export(
        self,
        sequence: List[SequenceItem],
        music_path: Path,
        target_duration: float,
        audio_processor: AudioProcessor,
        logo_manager: Optional[LogoOverlayManager] = None,
        logo_path: Optional[Path] = None
    ) -> Path:
        """
        Executes single-pass final assembly:
          1. Concatenates video segments seamlessly without gaps.
          2. Overlays PNG logo (if enabled) with transparency preservation.
          3. Replaces all audio with background music, applying fade in/out.
          4. Exports to output/final_video.mp4.
        """
        output_file = self.output_dir / self.output_filename
        logger.info("Starting final video assembly export to: %s", output_file)

        # 1. Generate concat playlist
        concat_file = self._prepare_concat_list(sequence)

        # 2. Build FFmpeg inputs and filter complex
        # Input 0: Concat video playlist
        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file.resolve()),
        ]

        filter_chains: List[str] = []
        video_out_label = "[v_concat]"
        audio_out_label = "[a_out]"

        # Check logo overlay
        has_logo = logo_manager is not None and logo_path is not None and logo_path.is_file()
        if has_logo:
            # Input 1: Logo PNG
            cmd.extend(["-i", str(logo_path.resolve())])
            # Input 2: Background Music
            cmd.extend(["-i", str(music_path.resolve())])

            logo_filter, _ = logo_manager.build_overlay_filter(
                logo_path=logo_path,
                video_label="[0:v]",
                logo_label="[1:v]",
                output_label="[v_logo]"
            )
            filter_chains.append(logo_filter)
            video_out_label = "[v_logo]"

            audio_filter = audio_processor.build_audio_filter(
                target_duration=target_duration,
                audio_label="[2:a]",
                output_label=audio_out_label
            )
            filter_chains.append(audio_filter)
        else:
            # Input 1: Background Music
            cmd.extend(["-i", str(music_path.resolve())])
            video_out_label = "0:v"

            audio_filter = audio_processor.build_audio_filter(
                target_duration=target_duration,
                audio_label="[1:a]",
                output_label=audio_out_label
            )
            filter_chains.append(audio_filter)

        filter_complex_str = ";".join(filter_chains)

        cmd.extend([
            "-filter_complex", filter_complex_str,
            "-map", video_out_label,
            "-map", audio_out_label,
            "-c:v", self.video_codec,
            "-preset", self.preset,
            "-crf", str(self.crf),
            "-r", str(self.target_fps),
            "-pix_fmt", "yuv420p",
            "-c:a", audio_processor.config.audio_codec,
            "-b:a", audio_processor.config.audio_bitrate,
            "-t", f"{target_duration:.6f}",
            str(output_file.resolve())
        ])

        run_command(cmd, "Assemble and export final video")

        if not output_file.exists() or output_file.stat().st_size == 0:
            raise MediaProcessingError("Export finished but final video file was not generated or is empty.")

        final_dur = get_duration(output_file, self.ffprobe_bin, self.ffmpeg_bin)
        file_size_mb = output_file.stat().st_size / (1024 * 1024)

        logger.info(
            "Final video exported successfully!\n"
            "  - File: %s\n"
            "  - Size: %.2f MB\n"
            "  - Duration: %.3fs (Target: %.3fs, Delta: %.3fs)\n"
            "  - Format: %s / %s",
            output_file, file_size_mb, final_dur, target_duration, abs(final_dur - target_duration),
            self.video_codec, audio_processor.config.audio_codec
        )

        return output_file
