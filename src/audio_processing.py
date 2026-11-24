import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .utils import MediaProcessingError, get_duration

logger = logging.getLogger("video_editor")


@dataclass
class AudioConfig:
    fade_in_duration: float = 1.0
    fade_out_duration: float = 2.0
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"


class AudioProcessor:
    """
    Manages background music processing, audio trimming, and fade-in/fade-out filters.
    """
    def __init__(
        self,
        config: AudioConfig,
        ffmpeg_bin: str,
        ffprobe_bin: Optional[str] = None
    ):
        self.config = config
        self.ffmpeg_bin = ffmpeg_bin
        self.ffprobe_bin = ffprobe_bin

    def build_audio_filter(
        self,
        target_duration: float,
        audio_label: str = "[2:a]",
        output_label: str = "[a_out]"
    ) -> str:
        """
        Builds the FFmpeg audio filtergraph snippet to trim and apply fade-in / fade-out.
        """
        fade_in = max(0.0, float(self.config.fade_in_duration))
        fade_out = max(0.0, float(self.config.fade_out_duration))

        filters = [f"atrim=0:{target_duration:.6f}", "asetpts=PTS-STARTPTS"]

        # Fade in
        if fade_in > 0:
            actual_fade_in = min(fade_in, target_duration / 2.0)
            filters.append(f"afade=t=in:ss=0:d={actual_fade_in:.3f}")

        # Fade out
        if fade_out > 0:
            actual_fade_out = min(fade_out, target_duration / 2.0)
            fade_start = max(0.0, target_duration - actual_fade_out)
            filters.append(f"afade=t=out:st={fade_start:.3f}:d={actual_fade_out:.3f}")

        filter_str = ",".join(filters)
        return f"{audio_label}{filter_str}{output_label}"
