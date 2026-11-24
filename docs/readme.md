# Documentation Overview

Welcome to the documentation for the **Automated Video Editing Application** (`auto_montage`).

---

## Available Documentation

| Document | Description |
|---|---|
| [**Architecture & System Design**](file:///c:/Users/Krushal%20Vataliya/Downloads/yt%20retune/video%20generator/docs/architecture.md) | Pipeline data flow, module responsibilities, and FFmpeg filtergraph architecture. |
| [**Configuration Guide & Presets**](file:///c:/Users/Krushal%20Vataliya/Downloads/yt%20retune/video%20generator/docs/configuration_guide.md) | Complete reference for `config.yaml` with ready-to-use recipes (Landscape, Shorts, 4K, Draft). |
| [**Sequence & Duration Logic**](file:///c:/Users/Krushal%20Vataliya/Downloads/yt%20retune/video%20generator/docs/sequence_and_duration_logic.md) | Mathematical timing models, slow-motion PTS math, fair shuffle-bag reuse, and trimming formulas. |
| [**FFmpeg Setup Guide**](file:///c:/Users/Krushal%20Vataliya/Downloads/yt%20retune/video%20generator/docs/ffmpeg_setup_guide.md) | Cross-platform FFmpeg/FFprobe installation, binary path options, and codec verification. |
| [**Troubleshooting & FAQ**](file:///c:/Users/Krushal%20Vataliya/Downloads/yt%20retune/video%20generator/docs/troubleshooting_and_faq.md) | Root cause resolutions for common errors, performance tips, and frequently asked questions. |
| [**Original Functional Specification**](file:///c:/Users/Krushal%20Vataliya/Downloads/yt%20retune/video%20generator/docs/specification.md) | Complete baseline product requirement specification for the video generator. |

---

## Quick Start Reference

```bash
# 1. Install dependencies
cd "video generator"
pip install -r requirements.txt

# 2. Run with default config
python main.py

# 3. Run with CLI overrides
python main.py --input "path/to/clips" --output "./output" --speed 0.66 --seed 42
```
