import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger("video_editor")

KV_INNOVATION_SYSTEM_INSTRUCTION = """
You are the creative director and metadata strategist for the YouTube channel 'KV Innovation'.
The channel creates high-quality Gujarati/Hindi devotional, folk, Garba/Raas, cultural, and historical music videos.

When given the lyrics and title of a song, you must generate TWO outputs:
1. 'video_prompts': 8 unique, candid, photorealistic AI video prompts formatted for text-to-video tools (e.g. Luma, Runway, Kling, Sora, Veo).
2. 'metadata': Complete YouTube Title, Gujarati Description with lyrics quote and hashtags, and verified YouTube Tags.

---
### RULES FOR VIDEO PROMPTS (8 SCENES):
1. Read the lyrics carefully and identify the song's subject, genre, mood, story, cultural setting, and key visual lines.
2. Create exactly 8 unique AI-video scenes based specifically on the song.
3. Every prompt must be:
   - Candid, realistic, cinematic, documentary-style, reusable as B-roll.
   - 10–12 seconds, photorealistic 4K, seamless/repeat-friendly.
   - Start with: 'Create a video, 10–12 seconds, photorealistic cinematic 4K...'
4. EVERY scene MUST include these negative/restraining conditions:
   'no lip-sync, no singing, no dialogue, no character speaking, no posing, no exaggerated acting, no choreographed performance, no direct camera interaction, no direct eye contact with camera, natural body movement, realistic environmental physics, no modern objects, no text, no watermark.'
5. The 8 scenes must be visually distinct with diverse camera angles (wide landscapes, close-ups, candid movements).
6. Culturally accurate settings:
   - Krishna/Radha: Vraj, Gokul, Vrindavan, Yamuna, Barsana, Dwarka as appropriate.
   - Saurashtra/Kathiyawad songs: Saurashtra landscape, Girnar, Junagadh, etc.
   - Gujarati Garba/Folk: Authentic Gujarati attire, garbo, diyas, dhol, manjira, village chowk.
   - Historical: Period-appropriate clothing and architecture.
7. Provide a practical 'REPEAT ORDER FOR LONGER VIDEO' at the bottom.

---
### RULES FOR YOUTUBE METADATA:
1. YOUTUBE TITLE format:
   Gujarati Song Title | Roman Title | Genre/Theme | Important Keyword | KV Innovation
2. YOUTUBE DESCRIPTION:
   - Engaging Gujarati description explaining the song's meaning and devotional/cultural context.
   - Meaningful lyric quote in Gujarati.
   - Metadata block: Song, Roman Title, Genre, Theme.
   - Call to action: Like, Share, Subscribe, Bell icon.
   - Copyright: © KV Innovation — All Rights Reserved.
   - Ends with a relevant hashtag block.
3. YOUTUBE TAGS:
   - Must include exact Gujarati title, Roman title, genre, deity/theme, related search terms, variations, and 'KV Innovation'.
   - Tags must be comma-separated.
   - Character count of tags string MUST be 500 characters or fewer (ideal: 450-498 characters).

---
### OUTPUT FORMAT (STRICT JSON):
Return a single JSON object with the following structure:
{
  "video_prompts_text": "Complete formatted text for video prompt.txt",
  "metadata_text": "Complete formatted text for title desc tags.txt"
}
"""


class GeminiPromptGenerator:
    """
    Automates the generation of 8 AI video prompts and YouTube metadata
    using Google Gemini API based on song lyrics.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")

    def _call_gemini_api(self, prompt: str) -> str:
        """
        Calls Gemini API using google-genai or requests fallback.
        """
        if not self.api_key:
            raise ValueError(
                "Gemini API key is required. Set 'GEMINI_API_KEY' environment variable "
                "or specify 'gemini_api_key' in config.json."
            )

        # 1. Try google.genai or google.generativeai
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
            return response.text
        except ImportError:
            pass
        except Exception as e:
            logger.warning("google.genai call failed, attempting fallback: %s", e)

        # 2. Direct HTTP REST API fallback (no extra dependencies required!)
        import urllib.request
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"}
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(req) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            return res_json["candidates"][0]["content"]["parts"][0]["text"]

    def generate_for_folder(self, folder_path: Path) -> Tuple[Path, Path]:
        """
        Reads lyrics.txt from folder, calls Gemini to generate prompts and metadata,
        and saves 'video prompt.txt' and 'title desc tags.txt' in the folder.
        """
        lyrics_file = folder_path / "lyrics.txt"
        if not lyrics_file.is_file():
            # Try alternate names
            alt = next(folder_path.glob("*lyrics*.txt"), None)
            if alt and alt.is_file():
                lyrics_file = alt
            else:
                raise FileNotFoundError(f"No 'lyrics.txt' found in: {folder_path}")

        lyrics_text = lyrics_file.read_text(encoding="utf-8").strip()
        folder_name = folder_path.name

        logger.info("Generating prompts for: '%s' (%d chars of lyrics)...", folder_name, len(lyrics_text))

        prompt_request = f"""
{KV_INNOVATION_SYSTEM_INSTRUCTION}

---
Song Folder Title: {folder_name}

Lyrics:
{lyrics_text}
"""

        raw_response = self._call_gemini_api(prompt_request)
        
        # Clean potential markdown fences
        clean_json_str = raw_response.strip()
        if clean_json_str.startswith("```"):
            clean_json_str = re.sub(r"^```(?:json)?\s*", "", clean_json_str)
            clean_json_str = re.sub(r"\s*```$", "", clean_json_str)

        try:
            data = json.loads(clean_json_str)
        except json.JSONDecodeError as e:
            logger.error("Failed to decode JSON response from Gemini: %s", e)
            raise

        video_prompts_path = folder_path / "video prompt.txt"
        metadata_path = folder_path / "title desc tags.txt"

        video_prompts_text = data.get("video_prompts_text", "").strip()
        metadata_text = data.get("metadata_text", "").strip()

        video_prompts_path.write_text(video_prompts_text + "\n", encoding="utf-8")
        metadata_path.write_text(metadata_text + "\n", encoding="utf-8")

        logger.info("Successfully created: %s", video_prompts_path)
        logger.info("Successfully created: %s", metadata_path)

        return video_prompts_path, metadata_path
