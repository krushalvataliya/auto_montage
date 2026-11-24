import logging
import random
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .video_processing import ProcessedClip

logger = logging.getLogger("video_editor")


@dataclass
class SequenceItem:
    """Represents a clip in the assembly sequence."""
    order_index: int
    clip: ProcessedClip
    play_duration: float
    is_trimmed: bool
    is_reused: bool


class SequenceBuilder:
    """
    Builds the video playback sequence following:
      Stage 1: Sequential playback of every video clip.
      Stage 2: Fair random reuse if additional footage is needed.
      Trims strictly the final clip to match music duration.
    """
    def __init__(self, random_seed: Optional[int] = None):
        self.random_seed = random_seed
        self.rng = random.Random(random_seed)

    def build_sequence(
        self,
        clips: List[ProcessedClip],
        target_duration: float
    ) -> List[SequenceItem]:
        """
        Assembles the sequence of video clips to exactly reach target_duration.
        """
        if not clips:
            raise ValueError("No processed clips provided to sequence builder.")

        if target_duration <= 0:
            raise ValueError(f"Invalid target duration: {target_duration}")

        sequence: List[SequenceItem] = []
        accumulated_duration = 0.0

        # -------------------------------------------------------------
        # Stage 1: Sequential Playback
        # Include every clip once in order
        # -------------------------------------------------------------
        logger.info("Stage 1: Building initial sequential playlist (%d clips)...", len(clips))
        for clip in clips:
            remaining = target_duration - accumulated_duration
            if remaining <= 0:
                break

            if clip.duration <= remaining:
                sequence.append(
                    SequenceItem(
                        order_index=len(sequence) + 1,
                        clip=clip,
                        play_duration=clip.duration,
                        is_trimmed=False,
                        is_reused=False
                    )
                )
                accumulated_duration += clip.duration
            else:
                # Target duration reached during Stage 1: trim this final clip
                sequence.append(
                    SequenceItem(
                        order_index=len(sequence) + 1,
                        clip=clip,
                        play_duration=remaining,
                        is_trimmed=True,
                        is_reused=False
                    )
                )
                accumulated_duration += remaining
                break

        # Check if target duration is already satisfied
        if accumulated_duration >= target_duration - 1e-4:
            logger.info(
                "Stage 1 fully covered target duration (%.3fs). No reuse required.",
                accumulated_duration
            )
            return sequence

        # -------------------------------------------------------------
        # Stage 2: Random Video Reuse
        # Rules:
        #  - Do not pick same video twice consecutively.
        #  - Shuffle bag / round-robin so every clip gets a chance before repeating.
        #  - Optional random seed supported.
        # -------------------------------------------------------------
        logger.info(
            "Stage 2: Sequential duration (%.3fs) < music duration (%.3fs). Beginning fair random reuse...",
            accumulated_duration, target_duration
        )

        last_used_clip = clips[-1]

        while accumulated_duration < target_duration - 1e-4:
            # Create a full fair pool permutation of available clips
            bag = list(clips)
            self.rng.shuffle(bag)

            # Avoid consecutive repeat at the boundary between rounds
            if len(bag) > 1 and bag[0].original_path == last_used_clip.original_path:
                # Swap first item with another item in bag
                swap_idx = self.rng.randint(1, len(bag) - 1)
                bag[0], bag[swap_idx] = bag[swap_idx], bag[0]

            for candidate in bag:
                remaining = target_duration - accumulated_duration
                if remaining <= 0:
                    break

                # Ensure non-consecutive even if single clip edge case handled
                if len(clips) > 1 and candidate.original_path == last_used_clip.original_path:
                    continue

                if candidate.duration <= remaining:
                    sequence.append(
                        SequenceItem(
                            order_index=len(sequence) + 1,
                            clip=candidate,
                            play_duration=candidate.duration,
                            is_trimmed=False,
                            is_reused=True
                        )
                    )
                    accumulated_duration += candidate.duration
                    last_used_clip = candidate
                else:
                    # Final clip of reuse: trim to remaining duration
                    sequence.append(
                        SequenceItem(
                            order_index=len(sequence) + 1,
                            clip=candidate,
                            play_duration=remaining,
                            is_trimmed=True,
                            is_reused=True
                        )
                    )
                    accumulated_duration += remaining
                    last_used_clip = candidate
                    break

        logger.info("Sequence generated with %d segments. Total assembled duration: %.3fs", len(sequence), accumulated_duration)
        for item in sequence:
            tag = "reused" if item.is_reused else "initial"
            trimmed_str = f" [trimmed to {item.play_duration:.3f}s]" if item.is_trimmed else ""
            logger.debug(
                "  Segment #%d: %s (%s, play: %.3fs)%s",
                item.order_index, item.clip.original_path.name, tag, item.play_duration, trimmed_str
            )

        return sequence
