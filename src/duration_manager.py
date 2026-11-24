import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .utils import get_duration

logger = logging.getLogger("video_editor")


@dataclass
class DurationPlan:
    music_duration: float
    sequential_footage_duration: float
    additional_duration_needed: float
    reuse_required: bool


class DurationManager:
    """
    Manages and calculates exact durations for video clips and music.
    """
    def __init__(self, ffprobe_bin: Optional[str], ffmpeg_bin: Optional[str] = None):
        self.ffprobe_bin = ffprobe_bin
        self.ffmpeg_bin = ffmpeg_bin

    def get_music_duration(self, music_file: Path) -> float:
        """
        Determines the exact duration of the background music.
        """
        dur = get_duration(music_file, self.ffprobe_bin, self.ffmpeg_bin)
        logger.info("Background music '%s' duration: %.3f seconds (%s)", music_file.name, dur, self.format_time(dur))
        return dur

    def evaluate_durations(self, music_duration: float, single_pass_duration: float) -> DurationPlan:
        """
        Evaluates footage requirements based on music and single-pass video durations.
        """
        diff = music_duration - single_pass_duration
        reuse_required = diff > 0.001
        add_needed = max(0.0, diff)

        logger.info(
            "Duration Analysis:\n"
            "  - Music duration: %.3fs (%s)\n"
            "  - Available single-pass video: %.3fs (%s)\n"
            "  - Additional footage needed: %.3fs\n"
            "  - Random reuse required: %s",
            music_duration, self.format_time(music_duration),
            single_pass_duration, self.format_time(single_pass_duration),
            add_needed,
            "YES" if reuse_required else "NO (Sequential clips cover full music)"
        )

        return DurationPlan(
            music_duration=music_duration,
            sequential_footage_duration=single_pass_duration,
            additional_duration_needed=add_needed,
            reuse_required=reuse_required
        )

    @staticmethod
    def format_time(seconds: float) -> str:
        """Formats seconds into MM:SS.mmm format."""
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"{mins:02d}:{secs:06.3f}"
