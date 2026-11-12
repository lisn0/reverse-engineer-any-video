#!/usr/bin/env python3
"""Print audio measurements beside the known truth.

    python3 benchmark/eval_audio.py NAME=VIDEO=MUSIC=VOICE [...]

Word timings come from faster-whisper, the same as evidence.py.
"""
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

SCRIPT = (Path(__file__).parent.parent / "plugins/reverse-engineer-any-video/skills"
          / "reverse-engineer-any-video/scripts/evidence.py")
spec = importlib.util.spec_from_file_location("evidence", SCRIPT)
evidence = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evidence)

for item in sys.argv[1:]:
    name, video, music, voice = item.split("=")
    with tempfile.TemporaryDirectory() as work:
        evidence.transcribe(Path(video), Path(work), None, "small")
        words = json.loads((Path(work) / "words.json").read_text())
    measured = evidence.measure_audio(Path(video), words)
    print(json.dumps({"case": name, "truth_music": music, "truth_voice": voice, **measured}), flush=True)
