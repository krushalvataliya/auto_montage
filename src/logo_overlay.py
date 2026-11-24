import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger("video_editor")


@dataclass
class LogoConfig:
    enabled: bool = True
    filename: Optional[str] = None
    position: str = "bottom-right"  # "top-left", "top-right", "bottom-left", "bottom-right", "center"
    width_percent: float = 12.0
    max_width_px: Optional[int] = 300
    max_height_px: Optional[int] = None
    margin_x: int = 30
    margin_y: int = 30
    opacity: float = 1.0


class LogoOverlayManager:
    """
    Builds FFmpeg filter definitions to scale and overlay a PNG logo with alpha transparency.
    """
    def __init__(
        self,
        config: LogoConfig,
        target_width: int,
        target_height: int,
        ffmpeg_bin: Optional[str] = None,
        ffprobe_bin: Optional[str] = None
    ):
        self.config = config
        self.target_width = target_width
        self.target_height = target_height
        self.ffmpeg_bin = ffmpeg_bin
        self.ffprobe_bin = ffprobe_bin

    def compute_scaled_dimensions(self, original_w: int, original_h: int) -> Tuple[int, int]:
        """
        Computes final pixel dimensions for the logo, preserving aspect ratio and respecting
        width_percent, max_width_px, and max_height_px limits.
        """
        # Calculate width from percentage
        calc_w = self.target_width * (self.config.width_percent / 100.0)

        # Apply max width limit if specified
        if self.config.max_width_px:
            calc_w = min(calc_w, float(self.config.max_width_px))

        aspect_ratio = original_w / max(1, original_h)
        calc_h = calc_w / aspect_ratio

        # Apply max height limit if specified
        if self.config.max_height_px and calc_h > self.config.max_height_px:
            calc_h = float(self.config.max_height_px)
            calc_w = calc_h * aspect_ratio

        # Ensure dimensions are positive integers and even numbers for codec compatibility
        w = max(2, int(round(calc_w)))
        h = max(2, int(round(calc_h)))
        if w % 2 != 0:
            w += 1
        if h % 2 != 0:
            h += 1

        return w, h

    def get_position_expressions(self, logo_w: int, logo_h: int) -> Tuple[str, str]:
        """
        Returns (x_expr, y_expr) for the FFmpeg overlay filter, clamping to video boundaries.
        """
        pos = self.config.position.lower().strip()
        mx = max(0, self.config.margin_x)
        my = max(0, self.config.margin_y)

        if pos == "top-left":
            x_val = mx
            y_val = my
        elif pos == "top-right":
            x_val = self.target_width - logo_w - mx
            y_val = my
        elif pos == "bottom-left":
            x_val = mx
            y_val = self.target_height - logo_h - my
        elif pos == "center":
            x_val = (self.target_width - logo_w) // 2
            y_val = (self.target_height - logo_h) // 2
        else:
            # Default: bottom-right
            x_val = self.target_width - logo_w - mx
            y_val = self.target_height - logo_h - my

        # Ensure within bounds
        clamped_x = max(0, min(self.target_width - logo_w, x_val))
        clamped_y = max(0, min(self.target_height - logo_h, y_val))

        return str(clamped_x), str(clamped_y)

    def build_overlay_filter(
        self,
        logo_path: Path,
        video_label: str = "[0:v]",
        logo_label: str = "[1:v]",
        output_label: str = "[v_out]"
    ) -> Tuple[str, Tuple[int, int]]:
        """
        Generates the complete FFmpeg filtergraph snippet for scaling and overlaying the logo.
        """
        from .utils import get_media_info
        orig_w, orig_h = 400, 400
        try:
            info = get_media_info(logo_path, self.ffprobe_bin, self.ffmpeg_bin)
            for s in info.get("streams", []):
                if s.get("codec_type") == "video":
                    orig_w = int(s.get("width", 400))
                    orig_h = int(s.get("height", 400))
                    break
        except Exception as e:
            logger.debug("Could not probe logo dimensions directly, using fallback defaults: %s", e)

        final_w, final_h = self.compute_scaled_dimensions(orig_w, orig_h)
        x_expr, y_expr = self.get_position_expressions(final_w, final_h)

        logger.info(
            "Logo config: position=%s, size=%dx%d (%.1f%% width), coords=(x=%s, y=%s)",
            self.config.position, final_w, final_h, self.config.width_percent, x_expr, y_expr
        )

        # Scale logo and adjust opacity if needed
        logo_filter_chain = [f"scale={final_w}:{final_h}:force_original_aspect_ratio=decrease"]
        if self.config.opacity < 0.999:
            logo_filter_chain.append(f"format=rgba,colorchannelmixer=aa={self.config.opacity:.2f}")

        logo_filters_str = ",".join(logo_filter_chain)

        filtergraph = (
            f"{logo_label}{logo_filters_str}[scaled_logo];"
            f"{video_label}[scaled_logo]overlay=x={x_expr}:y={y_expr}:format=auto{output_label}"
        )

        return filtergraph, (final_w, final_h)
