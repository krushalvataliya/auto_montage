import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("video_editor")

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv", ".m4v"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".aac", ".m4a", ".flac", ".ogg", ".wma"}
IMAGE_EXTENSIONS = {".png"}


@dataclass
class DiscoveredMedia:
    """Holds discovered input media files."""
    video_files: List[Path] = field(default_factory=list)
    music_file: Optional[Path] = None
    logo_file: Optional[Path] = None


class FileDiscoveryError(Exception):
    """Raised when file discovery or input validation fails."""
    pass


def discover_files(
    input_dir: Path,
    logo_enabled: bool = True,
    custom_music_path: Optional[str] = None,
    custom_logo_path: Optional[str] = None,
    ignore_filenames: Optional[set] = None
) -> DiscoveredMedia:
    """
    Scans the input directory and identifies video clips, background music,
    and the PNG logo, applying strict validation according to project specs.
    Ignores previously exported final video files.
    """
    if not input_dir.exists():
        raise FileDiscoveryError(f"Input folder does not exist: {input_dir}")

    if not input_dir.is_dir():
        raise FileDiscoveryError(f"Input path is not a directory: {input_dir}")

    # Gather all immediate files (non-recursive to avoid picking up temp/output files)
    all_files = [f for f in input_dir.iterdir() if f.is_file()]

    videos: List[Path] = []
    audios: List[Path] = []
    logos: List[Path] = []

    for f in all_files:
        ext = f.suffix.lower()
        if ext in VIDEO_EXTENSIONS:
            # Skip previously exported final video files in input folder
            if "- final video" in f.stem.lower() or f.stem.lower() == "final_video" or (ignore_filenames and f.name in ignore_filenames):
                logger.debug("Skipping previously generated video in input folder: %s", f.name)
                continue
            videos.append(f)
        elif ext in AUDIO_EXTENSIONS:
            audios.append(f)
        elif ext in IMAGE_EXTENSIONS:
            logos.append(f)
        else:
            logger.debug("Ignoring non-target file: %s", f.name)

    # 1. Validate Video Files
    if not videos:
        raise FileDiscoveryError(
            f"No valid video files found in '{input_dir}'. Supported formats: {', '.join(sorted(VIDEO_EXTENSIONS))}"
        )
    logger.info("Discovered %d video file(s) in '%s'.", len(videos), input_dir)

    # 2. Validate Music File
    selected_music: Optional[Path] = None
    if custom_music_path:
        custom_music = Path(custom_music_path)
        if not custom_music.is_absolute():
            custom_music = (input_dir / custom_music).resolve()
        if not custom_music.is_file():
            raise FileDiscoveryError(f"Specified music file does not exist: {custom_music}")
        selected_music = custom_music
    else:
        if len(audios) == 0:
            raise FileDiscoveryError(
                f"No background music file found in '{input_dir}'. Supported formats: {', '.join(sorted(AUDIO_EXTENSIONS))}"
            )
        if len(audios) > 1:
            audio_names = [a.name for a in audios]
            raise FileDiscoveryError(
                f"Multiple audio files detected: {audio_names}. Exactly one background music file is required. "
                f"Please remove extras or specify 'music_filename' in config.yaml."
            )
        selected_music = audios[0]
    logger.info("Discovered background music: %s", selected_music.name)

    # 3. Validate PNG Logo (if logo enabled)
    selected_logo: Optional[Path] = None
    if logo_enabled:
        if custom_logo_path:
            custom_logo = Path(custom_logo_path)
            if not custom_logo.is_absolute():
                custom_logo = (input_dir / custom_logo).resolve()
            if not custom_logo.is_file():
                raise FileDiscoveryError(f"Specified logo file does not exist: {custom_logo}")
            selected_logo = custom_logo
        else:
            if len(logos) == 0:
                raise FileDiscoveryError(
                    f"Logo overlay is enabled, but no PNG logo was found in '{input_dir}'. "
                    f"Please provide a PNG logo or set 'logo.enabled: false' in config.yaml."
                )
            if len(logos) > 1:
                # If there's an exact match for 'logo.png', pick that; otherwise raise error
                named_logo = next((l for l in logos if l.stem.lower() == "logo"), None)
                if named_logo:
                    selected_logo = named_logo
                else:
                    logo_names = [l.name for l in logos]
                    raise FileDiscoveryError(
                        f"Multiple PNG files detected: {logo_names}. Exactly one PNG logo is required when logo overlay is enabled. "
                        f"Name your logo 'logo.png' or specify 'logo.filename' in config.yaml."
                    )
            else:
                selected_logo = logos[0]
        logger.info("Discovered PNG logo: %s", selected_logo.name)
    else:
        logger.info("Logo overlay is disabled in configuration.")

    return DiscoveredMedia(
        video_files=videos,
        music_file=selected_music,
        logo_file=selected_logo
    )
