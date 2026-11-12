#!/usr/bin/env python3
"""Mix a real song quietly under known voices, for held-out music and voice tests.

    python3 benchmark/make_song_cases.py SONG_VIDEO OUT_DIR NAME=VOICE_FILE [...]
"""
import subprocess
import sys
from pathlib import Path

SONG, OUT = sys.argv[1], Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
for item in sys.argv[3:]:
    name, voice = item.split("=")
    for label, level in (("low", 0.04), ("mid", 0.1)):
        graph = (f"[1:a]aloop=loop=-1:size=2e9,volume={level},aformat=sample_rates=24000:channel_layouts=mono[bed];"
                 "[0:a]aformat=sample_rates=24000:channel_layouts=mono[voice];"
                 "[voice][bed]amix=inputs=2:duration=first:normalize=0")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", voice, "-i", SONG, "-filter_complex", graph,
                        str(OUT / f"{name}-{label}.wav")], check=True)
print("MADE", sorted(path.name for path in OUT.iterdir()))
