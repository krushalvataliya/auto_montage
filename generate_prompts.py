#!/usr/bin/env python3
"""
Automated AI Video Prompt & YouTube Metadata Generator for KV Innovation
Reads lyrics.txt from a song folder and uses Google Gemini to generate:
  - video prompt.txt (8 unique 10-12s cinematic prompts with negative constraints)
  - title desc tags.txt (Searchable Title, Gujarati Description, and exact 500-char Tags)
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from src.prompt_generator import GeminiPromptGenerator
from src.utils import setup_logger

logger = logging.getLogger("video_editor")


def load_config() -> dict:
    """Loads config.json or returns empty dict."""
    config_file = Path(__file__).resolve().parent / "config.json"
    if config_file.is_file():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate 8 AI video prompts & YouTube metadata from lyrics.txt using Gemini."
    )
    parser.add_argument(
        "-f", "--folder",
        dest="folder_path",
        default=None,
        help="Path to song directory containing lyrics.txt (default: input folder from config.json)"
    )
    parser.add_argument(
        "--api-key",
        dest="api_key",
        default=None,
        help="Google Gemini API key (or set GEMINI_API_KEY environment variable / config.json)"
    )
    parser.add_argument(
        "--all",
        dest="process_all",
        action="store_true",
        help="Scan parent directory and generate prompts for all folders containing lyrics.txt"
    )

    args = parser.parse_args()
    setup_logger(log_level="INFO")

    config = load_config()

    # Determine API key
    api_key = args.api_key or os.environ.get("GEMINI_API_KEY") or config.get("gemini_api_key")
    if not api_key:
        print("\n" + "=" * 65, file=sys.stderr)
        print("[ERROR] Gemini API Key is required to run the automated script.", file=sys.stderr)
        print("You can supply your key in any of these ways:", file=sys.stderr)
        print("  1. In config.json:  \"gemini_api_key\": \"AIzaSy...\"", file=sys.stderr)
        print("  2. In environment:  $env:GEMINI_API_KEY=\"AIzaSy...\"", file=sys.stderr)
        print("  3. Via CLI option:  python generate_prompts.py --api-key \"AIzaSy...\"", file=sys.stderr)
        print("\nNOTE: You can also simply ask Antigravity in this chat to generate", file=sys.stderr)
        print("prompts for any song folder directly!", file=sys.stderr)
        print("=" * 65 + "\n", file=sys.stderr)
        return 1

    generator = GeminiPromptGenerator(api_key=api_key)

    # Process all folders
    if args.process_all:
        base_dir = Path("..").resolve()
        logger.info("Scanning for folders with lyrics.txt in: %s", base_dir)
        folders = [d for d in base_dir.iterdir() if d.is_dir() and (d / "lyrics.txt").is_file()]
        logger.info("Found %d folder(s) with lyrics.txt", len(folders))
        for f in folders:
            try:
                generator.generate_for_folder(f)
            except Exception as e:
                logger.error("Failed for folder '%s': %s", f.name, e)
        return 0

    # Process single folder
    target_folder = args.folder_path
    if not target_folder:
        target_folder = config.get("input") or config.get("input_dir")

    if not target_folder:
        logger.error("No folder specified and no 'input' found in config.json. Use --folder 'path/to/song'")
        return 1

    folder = Path(target_folder).resolve()
    if not folder.is_dir():
        logger.error("Specified path is not a directory: %s", folder)
        return 1

    try:
        vp_path, meta_path = generator.generate_for_folder(folder)
        print("\n" + "=" * 60)
        print(f"SUCCESS! Generated files in '{folder.name}':")
        print(f"  1. {vp_path.name}  -> 8 Cinematic AI Video Prompts")
        print(f"  2. {meta_path.name} -> Title, Gujarati Desc & Tags")
        print("=" * 60 + "\n")
        return 0
    except Exception as e:
        logger.error("Prompt generation failed: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
