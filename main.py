#!/usr/bin/env python3
"""
Automated Video Editing Application
Main CLI entry point orchestrating discovery, sorting, processing, sequencing, and export.
"""

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict

import yaml

from src.audio_processing import AudioConfig, AudioProcessor
from src.duration_manager import DurationManager
from src.file_discovery import FileDiscoveryError, discover_files
from src.logo_overlay import LogoConfig, LogoOverlayManager
from src.utils import FFmpegNotFoundError, MediaProcessingError, find_ffmpeg, setup_logger
from src.video_export import VideoExporter
from src.video_processing import VideoProcessor
from src.video_sequence import SequenceBuilder
from src.video_sorting import sort_videos

logger = logging.getLogger("video_editor")


def load_config(config_path: Path) -> Dict[str, Any]:
    """Loads and validates YAML configuration file."""
    if not config_path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        try:
            config = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse config file '{config_path}': {e}") from e

    return config


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Automated Video Editing Application - Generate edited video from clips, music, and logo."
    )
    parser.add_argument(
        "-c", "--config",
        default="config.yaml",
        help="Path to YAML configuration file (default: config.yaml)"
    )
    parser.add_argument(
        "-i", "--input",
        dest="input_dir",
        default=None,
        help="Override input directory containing video clips, music, and logo"
    )
    parser.add_argument(
        "-o", "--output",
        dest="output_dir",
        default=None,
        help="Override output directory for final video (default: saves directly in input folder)"
    )
    parser.add_argument(
        "--output-name",
        dest="output_filename",
        default=None,
        help="Override output filename (default: '{folder_name} - final video.mp4')"
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=None,
        help="Override slow-motion playback speed factor (e.g. 0.66)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Override random seed for video reuse reproducibility"
    )

    args = parser.parse_args()

    # 1. Load Configuration
    config_file = Path(args.config)
    if not config_file.is_file():
        # Fallback to script directory config.yaml
        script_dir = Path(__file__).resolve().parent
        config_file = script_dir / "config.yaml"

    try:
        config = load_config(config_file)
    except Exception as e:
        print(f"[ERROR] Failed to load configuration: {e}", file=sys.stderr)
        return 1

    # Extract configuration blocks
    paths_cfg = config.get("paths", {})
    video_cfg = config.get("video", {})
    audio_cfg = config.get("audio", {})
    logo_cfg = config.get("logo", {})
    seq_cfg = config.get("sequence", {})
    exec_cfg = config.get("execution", {})

    # CLI Overrides
    if args.input_dir:
        paths_cfg["input_dir"] = args.input_dir
    if args.output_dir is not None:
        paths_cfg["output_dir"] = args.output_dir
    if args.output_filename is not None:
        paths_cfg["output_filename"] = args.output_filename
    if args.speed is not None:
        video_cfg["slow_motion_speed"] = args.speed
    if args.seed is not None:
        seq_cfg["random_seed"] = args.seed

    # Setup Paths
    input_dir = Path(paths_cfg.get("input_dir", "./input")).resolve()

    # Default output directory: input folder (unless explicitly configured otherwise)
    raw_output_dir = paths_cfg.get("output_dir")
    if not raw_output_dir or str(raw_output_dir).strip().lower() in ("", "input", "none", "null"):
        output_dir = input_dir
    else:
        output_dir = Path(raw_output_dir).resolve()

    # Default output filename: '{folder_name} - final video.mp4'
    raw_output_filename = paths_cfg.get("output_filename")
    if not raw_output_filename or str(raw_output_filename).strip().lower() in ("", "default", "none", "null"):
        output_filename = f"{input_dir.name} - final video.mp4"
    else:
        output_filename = str(raw_output_filename)

    temp_dir = Path(paths_cfg.get("temp_dir", "./temp")).resolve()
    log_dir = Path(paths_cfg.get("log_dir", "./logs")).resolve()

    # 2. Setup Logging
    log_level = exec_cfg.get("log_level", "INFO")
    log_file = log_dir / "video_editor.log"
    setup_logger(log_file=log_file, log_level=log_level)

    logger.info("==================================================")
    logger.info("Starting Automated Video Generator Application")
    logger.info("==================================================")
    logger.info("Loaded config from: %s", config_file)
    logger.info("Input directory:    %s", input_dir)
    logger.info("Output directory:   %s", output_dir)
    logger.info("Temporary dir:      %s", temp_dir)

    start_time = time.time()

    # 3. Locate FFmpeg and FFprobe
    try:
        ffmpeg_bin, ffprobe_bin = find_ffmpeg(
            config_ffmpeg=paths_cfg.get("ffmpeg_path"),
            config_ffprobe=paths_cfg.get("ffprobe_path")
        )
        logger.info("Using FFmpeg binary:  %s", ffmpeg_bin)
        if ffprobe_bin:
            logger.info("Using FFprobe binary: %s", ffprobe_bin)
        else:
            logger.info("Using FFmpeg built-in fallback parser for media probing.")
    except FFmpegNotFoundError as e:
        logger.error(str(e))
        return 1

    # 4. File Discovery & Input Validation
    try:
        discovered = discover_files(
            input_dir=input_dir,
            logo_enabled=logo_cfg.get("enabled", True),
            custom_music_path=audio_cfg.get("music_filename") or None,
            custom_logo_path=logo_cfg.get("filename") or None,
            ignore_filenames={output_filename, f"{input_dir.name} - final video.mp4"}
        )
    except FileDiscoveryError as e:
        logger.error("Input validation failed: %s", e)
        return 1

    # 5. Video Sorting
    sorted_video_paths = sort_videos(discovered.video_files)
    if not sorted_video_paths:
        logger.error("No valid video files available for processing.")
        return 1

    # 6. Video Processing & Normalization
    video_proc = VideoProcessor(
        ffmpeg_bin=ffmpeg_bin,
        ffprobe_bin=ffprobe_bin,
        temp_dir=temp_dir,
        slow_motion_speed=video_cfg.get("slow_motion_speed", 0.66),
        target_width=video_cfg.get("target_width", 1920),
        target_height=video_cfg.get("target_height", 1080),
        target_fps=video_cfg.get("target_fps", 30),
        scaling_mode=video_cfg.get("scaling_mode", "pad"),
        video_codec=video_cfg.get("video_codec", "libx264"),
        crf=video_cfg.get("crf", 18),
        preset=video_cfg.get("preset", "fast"),
        on_corrupt_file=exec_cfg.get("on_corrupt_file", "abort")
    )

    try:
        processed_clips = video_proc.process_all(sorted_video_paths)
    except MediaProcessingError as e:
        logger.error("Error during video processing: %s", e)
        return 1

    # 7. Duration Evaluation
    dur_manager = DurationManager(ffprobe_bin=ffprobe_bin, ffmpeg_bin=ffmpeg_bin)
    try:
        music_duration = dur_manager.get_music_duration(discovered.music_file)
    except MediaProcessingError as e:
        logger.error("Failed to determine music duration: %s", e)
        return 1

    single_pass_duration = sum(c.duration for c in processed_clips)
    dur_plan = dur_manager.evaluate_durations(
        music_duration=music_duration,
        single_pass_duration=single_pass_duration
    )

    # 8. Video Sequence Generation
    seq_builder = SequenceBuilder(random_seed=seq_cfg.get("random_seed"))
    sequence = seq_builder.build_sequence(
        clips=processed_clips,
        target_duration=music_duration
    )

    # 9. Audio & Logo Setup
    audio_obj = AudioConfig(
        fade_in_duration=audio_cfg.get("fade_in_duration", 1.0),
        fade_out_duration=audio_cfg.get("fade_out_duration", 2.0),
        audio_codec=audio_cfg.get("audio_codec", "aac"),
        audio_bitrate=audio_cfg.get("audio_bitrate", "192k")
    )
    audio_proc = AudioProcessor(
        config=audio_obj,
        ffmpeg_bin=ffmpeg_bin,
        ffprobe_bin=ffprobe_bin
    )

    logo_manager: Optional[LogoOverlayManager] = None
    if logo_cfg.get("enabled", True) and discovered.logo_file:
        logo_obj = LogoConfig(
            enabled=True,
            filename=logo_cfg.get("filename"),
            position=logo_cfg.get("position", "bottom-right"),
            width_percent=float(logo_cfg.get("width_percent", 12.0)),
            max_width_px=logo_cfg.get("max_width_px", 250),
            max_height_px=logo_cfg.get("max_height_px"),
            margin_x=int(logo_cfg.get("margin_x", 30)),
            margin_y=int(logo_cfg.get("margin_y", 30)),
            opacity=float(logo_cfg.get("opacity", 1.0))
        )
        logo_manager = LogoOverlayManager(
            config=logo_obj,
            target_width=video_cfg.get("target_width", 1920),
            target_height=video_cfg.get("target_height", 1080),
            ffmpeg_bin=ffmpeg_bin,
            ffprobe_bin=ffprobe_bin
        )

    # 10. Final Assembly & Export
    exporter = VideoExporter(
        ffmpeg_bin=ffmpeg_bin,
        ffprobe_bin=ffprobe_bin,
        temp_dir=temp_dir,
        output_dir=output_dir,
        output_filename=output_filename,
        video_codec=video_cfg.get("video_codec", "libx264"),
        crf=video_cfg.get("crf", 18),
        preset=video_cfg.get("preset", "fast"),
        target_fps=video_cfg.get("target_fps", 30)
    )

    try:
        final_video_path = exporter.export(
            sequence=sequence,
            music_path=discovered.music_file,
            target_duration=music_duration,
            audio_processor=audio_proc,
            logo_manager=logo_manager,
            logo_path=discovered.logo_file
        )
    except MediaProcessingError as e:
        logger.error("Final export failed: %s", e)
        return 1

    elapsed = time.time() - start_time
    logger.info("==================================================")
    logger.info("PROCESS COMPLETE")
    logger.info("Final video:      %s", final_video_path)
    logger.info("Music duration:   %.3fs", music_duration)
    logger.info("Clips in sequence: %d", len(sequence))
    logger.info("Elapsed time:     %.2fs", elapsed)
    logger.info("==================================================")

    return 0


if __name__ == "__main__":
    sys.exit(main())
