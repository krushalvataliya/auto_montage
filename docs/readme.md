Project: Automated Video Editing Application Using Python
1. Project Objective

Create a Python application that automatically generates a final edited video using video clips, a background music file, and a PNG logo.

The application should automatically:

Discover and sort video files.
Apply slow motion to all video clips.
Remove original audio from all video clips.
Arrange clips in a predefined order.
Randomly reuse clips when additional footage is required.
Match the final video duration exactly to the background music duration.
Overlay a configurable PNG logo.
Export the final video in MP4 format.

The application should be modular, configurable, and easy to use.

2. Input Folder Structure

All input files will be located in a single folder.

Example:

text
input/
├── vid1.mp4
├── vid2.mp4
├── vid3.mp4
├── vid4.mp4
├── vid5.mp4
├── vid6.mp4
├── vid7.mp4
├── background_music.mp3
└── logo.png


The number of video files is dynamic. There may be 3, 7, 8, 15, or any other number of videos.

The application must automatically identify:

Video files (MP4, MOV, AVI, etc.).
One background music file.
One PNG logo.

Do not hardcode video filenames.

3. Video Filename Detection and Sorting

Video filenames may follow different naming conventions.

Examples:

text
vid1.mp4
vid2.mp4
vid3.mp4
vid10.mp4


Or:

text
smb1.mp4
smb2.mp4
smb3.mp4


Or:

text
travel1.mp4
travel2.mp4
travel3.mp4


Requirements:

Extract the numerical suffix from each filename.
Sort videos using natural numerical ordering.
Videos with the same common filename prefix should be grouped together.
Do not assume the prefix is always 'vid' or 'smb'.
Detect missing sequence numbers without crashing.
Ignore non-video files during video discovery.
Handle filenames without numerical suffixes using a clearly defined fallback sorting rule.

Example:

Input: vid1.mp4, vid10.mp4, vid2.mp4, vid3.mp4

Expected order: vid1.mp4, vid2.mp4, vid3.mp4, vid10.mp4

4. Video Processing

Before assembling the final video, process every source video.

For each video:

Remove original audio completely.
Apply slow motion at 0.66x playback speed (66% of original speed).
Preserve the original visual quality as much as possible.
Maintain the correct aspect ratio.
Handle different source resolutions and frame rates.
Make processed videos available for final assembly.

The application must not include original audio in the final video.

Only the background music should be audible.

5. Automatic Video Arrangement

The video arrangement must follow two stages.

Stage 1: Sequential Playback

First, arrange every detected video in numerical order.

Example:

text
vid1 → vid2 → vid3 → vid4 → vid5 → vid6 → vid7


Every source video must be included once before random reuse begins.

Stage 2: Random Video Reuse

Calculate whether the available processed video footage is sufficient to cover the entire background music duration.

If additional footage is required:

Randomly select videos from the available collection.
Append them until the required duration is reached.
Avoid selecting the same video twice consecutively.
Avoid reusing a video until every other available video has had a chance to be reused, if possible.
Random selection should not disrupt the initial sequential arrangement.
Support an optional random seed for reproducible editing.

Example:

text
Initial sequence:
vid1 → vid2 → vid3 → vid4

Additional sequence:
vid2 → vid4 → vid1 → vid3 → vid2


The final sequence must cover the background music duration.

6. Final Video Duration

The background music determines the final video duration.

Requirements:

Read the exact duration of the background music.
Calculate the total duration of the processed video clips.
Append additional randomly selected clips when necessary.
Trim the final video to exactly match the music duration.
If the final clip exceeds the remaining required duration, trim only that final clip.
Do not leave black frames, blank frames, or gaps between clips.
Ensure smooth concatenation.
Avoid extending the video with frozen frames.

The exported video duration must match the music duration as closely as technically possible.

7. Background Music
Automatically identify the music file in the input folder.
Use it as the only audio track.
Preserve the music's original playback speed and duration.
Trim music only if necessary to match the final video duration.
Do not add original video audio.
Optionally support configurable audio fade-in and fade-out.
8. PNG Logo Overlay

Automatically identify the PNG logo.

The logo must support transparency.

Provide configurable logo settings:

Logo Position

Support these positions:

Top-left
Top-right
Bottom-left
Bottom-right
Center (optional)
Logo Size

Allow logo size to be configured using:

Percentage of video width.
Maximum width in pixels.
Optional maximum height.
Aspect ratio preservation.
Logo Margin

Allow configurable horizontal and vertical margins.

Example configuration:

yaml
logo:
  enabled: true
  position: bottom-right
  width_percent: 12
  margin_x: 30
  margin_y: 30


The logo must:

Preserve transparency.
Maintain its original aspect ratio.
Never stretch or distort.
Stay within the video boundaries.
9. Output

Save the final video in an output folder.

Example:

text
project/
├── input/
│   ├── vid1.mp4
│   ├── vid2.mp4
│   ├── background_music.mp3
│   └── logo.png
├── output/
│   └── final_video.mp4
├── temp/
└── config.yaml


Output requirements:

MP4 container.
H.264 video codec.
AAC audio codec.
Configurable resolution.
Configurable frame rate.
High-quality encoding.
Correct audio-video synchronization.
10. Configuration

All important settings should be configurable without modifying Python source code.

Provide a config.yaml file with settings for:

Input folder.
Output folder.
Temporary folder.
Slow-motion speed.
Logo visibility.
Logo position.
Logo size.
Logo margins.
Output resolution.
Output frame rate.
Video codec.
Audio codec.
Random seed.
Audio fade duration.
11. Error Handling and Validation

The application should validate:

Input folder exists.
At least one valid video exists.
Exactly one music file is available.
Exactly one PNG logo is available when logo overlay is enabled.
All video files can be opened.
Music duration can be detected.
Output folder is writable.
Required processing dependencies are installed.

Provide clear error messages.

Do not silently skip corrupted files. Report which files failed and allow configurable skip-or-abort behavior.

12. Technical Requirements

Use Python 3.11 or newer.

Recommended libraries:

FFmpeg for video and audio processing.
FFprobe for media metadata extraction.
Python subprocess for FFmpeg execution.
PyYAML for configuration.
pathlib for file management.
logging for execution logs.

Use FFmpeg-based processing for performance and reliability.

Avoid loading entire video files into memory.

13. Project Architecture

Organize the application into separate modules:

text
video_editor/
├── main.py
├── config.yaml
├── requirements.txt
├── README.md
├── src/
│   ├── file_discovery.py
│   ├── video_sorting.py
│   ├── video_processing.py
│   ├── video_sequence.py
│   ├── duration_manager.py
│   ├── logo_overlay.py
│   ├── audio_processing.py
│   ├── video_export.py
│   └── utils.py
├── input/
├── output/
├── temp/
└── logs/


Each module should have a single responsibility.

14. Execution

The application should be executable using:

bash
python main.py


The application should:

Load configuration.
Scan the input folder.
Identify videos, music, and logo.
Sort videos numerically.
Process all videos at 0.66x speed without original audio.
Calculate the required total video duration.
Generate the initial sequential video playlist.
Randomly append videos when additional duration is needed.
Trim the final sequence to music duration.
Add background music.
Overlay the PNG logo.
Export final_video.mp4.
Display processing progress and a final summary.
15. Expected Deliverables

Provide:

Complete working Python project.
All source code.
requirements.txt.
config.yaml.
README.md with installation and execution instructions.
FFmpeg installation instructions.
Error handling and logging.
Example input and output folder structure.
Clear explanation of how video selection and duration calculations work.

Do not provide pseudocode or incomplete placeholder functions. Generate a complete, runnable implementation.