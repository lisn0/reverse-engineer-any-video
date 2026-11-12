#!/usr/bin/env python3
"""Make audio test files: a generated voice over music beds, and optional human recordings.

    python3 benchmark/make_audio_cases.py VOICE_WAV OUT_DIR [SOURCES_JSON]

SOURCES_JSON (default benchmark/local_sources.json, gitignored) maps an output name to a
video URL, for example {"human-speech": "<url>", "human-with-music": "<url>"}. Seconds
30 to 150 of each are saved as WAV. Without the file only the generated cases are made.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

if len(sys.argv) < 3:
    sys.exit(__doc__)
VOICE, OUT = sys.argv[1], Path(sys.argv[2])
SOURCES = Path(sys.argv[3]) if len(sys.argv) > 3 else Path(__file__).parent / "local_sources.json"
BED = ("sine=frequency=220:sample_rate=24000[a];sine=frequency=277:sample_rate=24000[b];"
       "sine=frequency=330:sample_rate=24000[c];[a][b][c]amix=inputs=3,"
       "tremolo=f=2:d=0.9")
HUMAN = json.loads(SOURCES.read_text()) if SOURCES.is_file() else {}
YT_DLP = (shutil.which("yt-dlp") or sys.exit("yt-dlp not found on PATH")) if HUMAN else None

OUT.mkdir(parents=True, exist_ok=True)
for name, level in (("tts-quiet-bed", 0.06), ("tts-loud-bed", 0.2)):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", VOICE, "-filter_complex",
                    f"{BED},volume={level}[bed];[0:a][bed]amix=inputs=2:duration=first:normalize=0",
                    str(OUT / f"{name}.wav")], check=True)
for name, url in HUMAN.items():
    subprocess.run([YT_DLP,"--no-playlist", "--no-warnings",
                    "--remote-components", "ejs:github", "-f", "ba/b", "--download-sections", "*30-150",
                    "-x", "--audio-format", "wav", "-o", str(OUT / f"{name}.%(ext)s"), url], check=True)
print("MADE", sorted(path.name for path in OUT.iterdir()))
