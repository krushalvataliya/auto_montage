import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("video_editor")

# Matches strings ending in digits, e.g. "vid10", "gfl_2", "clip-05", "travel3"
NUMERICAL_SUFFIX_PATTERN = re.compile(r"^(.*?)(?:[_\-\s])?(\d+)$")


class VideoMetadata:
    def __init__(self, path: Path):
        self.path = path
        self.stem = path.stem
        match = NUMERICAL_SUFFIX_PATTERN.match(self.stem)
        if match:
            raw_prefix = match.group(1).rstrip("_- ")
            self.prefix = raw_prefix.lower() if raw_prefix else "default"
            self.number: Optional[int] = int(match.group(2))
        else:
            self.prefix = self.stem.lower()
            self.number = None


def natural_sort_key(s: str) -> List:
    """Helper for natural alphanumeric sorting on non-suffixed strings."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", s)]


def sort_videos(video_paths: List[Path]) -> List[Path]:
    """
    Groups videos with the same prefix and sorts each group numerically by their suffix.
    Detects and logs missing sequence numbers.
    Videos without numerical suffixes fallback to natural alphanumeric sorting.
    """
    if not video_paths:
        return []

    # Parse metadata for all video files
    metas = [VideoMetadata(p) for p in video_paths]

    # Group by prefix
    groups: Dict[str, List[VideoMetadata]] = {}
    for meta in metas:
        groups.setdefault(meta.prefix, []).append(meta)

    sorted_result: List[Path] = []

    # Sort prefix groups alphabetically to provide deterministic ordering across different prefixes
    for prefix in sorted(groups.keys(), key=natural_sort_key):
        items = groups[prefix]

        # Separate items with numbers from items without numbers
        numbered = [m for m in items if m.number is not None]
        non_numbered = [m for m in items if m.number is None]

        # Sort numbered items numerically
        numbered.sort(key=lambda m: m.number)  # type: ignore

        # Detect gaps in sequence numbers
        if len(numbered) > 1:
            numbers = [m.number for m in numbered if m.number is not None]
            min_num = numbers[0]
            max_num = numbers[-1]
            expected = set(range(min_num, max_num + 1))
            actual = set(numbers)
            missing = sorted(expected - actual)
            if missing:
                logger.warning(
                    "Sequence gap detected in group '%s': missing indices %s (found %s to %s)",
                    prefix, missing, min_num, max_num
                )

        # Sort non-numbered items by natural filename key
        non_numbered.sort(key=lambda m: natural_sort_key(m.path.stem))

        # Combine: numbered first, followed by non-numbered
        for m in numbered:
            sorted_result.append(m.path)
        for m in non_numbered:
            sorted_result.append(m.path)

    logger.info("Sorted %d video(s):", len(sorted_result))
    for idx, path in enumerate(sorted_result, start=1):
        logger.info("  [%d] %s", idx, path.name)

    return sorted_result
