#!/usr/bin/env python3
"""Make a narrated AI-image test video with a known recipe.

    python3 benchmark/make_ai_case.py OUT_DIR IMAGE_DIR MUSIC_VIDEO

Each scene is one AI image with a sideways pan and a crossfade. Every sentence has its own
burned-in caption. The voice comes from Kokoro, and a real song sits quietly under it.
"""
import subprocess
import sys
import textwrap
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro import KPipeline

OUT, IMAGES, MUSIC = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
VOICE, RATE, FPS, FADE, PAUSE = "bf_emma", 24000, 30, 0.4, 0.4
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
SCENES = [
    ("01-shiyan-night.png", ["Winter had reached the poorest county in the empire.",
                             "Only one window still burned past midnight."]),
    ("02-tao-writing.png", ["Inside, a thin young scholar wrote until his fingers bled.",
                            "He owed more than his whole family could ever earn.",
                            "The exam was his only way out."]),
    ("03-decree-mist.png", ["Then the fog came through the walls.",
                            "A voice without a body read him his fate.",
                            "He would fail, it said, for the third and final time."]),
    ("04-tao-refuses.png", ["He wept, and then he raised his brush.",
                            "If heaven had written his life, he would write it again."]),
    ("05-qiu-arrives.png", ["At dawn someone knocked at the broken door.",
                            "Nobody had ever come looking for him before."]),
]


def speak() -> list[list[np.ndarray]]:
    pipeline = KPipeline(lang_code="b", repo_id="hexgrad/Kokoro-82M", device="cpu")
    return [[np.concatenate([np.asarray(part.audio) for part in pipeline(line, voice=VOICE)]) for line in lines]
            for _, lines in SCENES]


def clip(number: int, picture: Path, lines: list[str], spoken: list[np.ndarray]) -> tuple[Path, float]:
    seconds = sum(len(line) / RATE + PAUSE for line in spoken)
    frames = int((seconds + FADE) * FPS)
    start, end = ("0", "1") if number % 2 == 0 else ("1", "0")
    travel = f"({start}+({end}-{start})*on/{frames})"
    parts = ["scale=1296:1620:force_original_aspect_ratio=increase,crop=1296:1620",
             f"zoompan=z=1.2:x='(iw-iw/zoom)*{travel}':y='(ih-ih/zoom)/2':d={frames}:s=720x1280:fps={FPS}"]
    begin = 0.0
    for index, (line, audio) in enumerate(zip(lines, spoken)):
        caption = OUT / f"caption-{number}-{index}.txt"
        caption.write_text("\n".join(textwrap.wrap(line, 26)))
        finish = begin + len(audio) / RATE + PAUSE
        parts.append(f"drawtext=fontfile={FONT}:textfile={caption}:fontsize=40:fontcolor=white:borderw=3:"
                     f"bordercolor=black:x=(w-tw)/2:y=h-270:line_spacing=8:enable='between(t,{begin:.2f},{finish:.2f})'")
        begin = finish
    target = OUT / f"clip-{number}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(picture), "-vf", ",".join(parts + ["format=yuv420p"]),
                    "-frames:v", str(frames), "-c:v", "libx264", "-crf", "20", str(target)], check=True)
    return target, seconds


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=False)
    voices = speak()
    gap = np.zeros(int(PAUSE * RATE))
    sf.write(OUT / "voice.wav", np.concatenate([part for scene in voices for line in scene for part in (line, gap)]), RATE)
    made = [clip(i, IMAGES / name, lines, voices[i]) for i, (name, lines) in enumerate(SCENES)]
    inputs = [arg for path, _ in made for arg in ("-i", str(path))]
    chain, last, offset = [], "[0:v]", 0.0
    for index in range(1, len(made)):
        offset += made[index - 1][1]
        chain.append(f"{last}[{index}:v]xfade=transition=fade:duration={FADE}:offset={offset:.3f}[v{index}]")
        last = f"[v{index}]"
    silent = OUT / "silent.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(chain), "-map", last,
                    "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", str(silent)], check=True)
    final = OUT / "final.mp4"
    graph = ("[2:a]aloop=loop=-1:size=2e9,volume=0.05,aformat=sample_rates=24000:channel_layouts=mono[bed];"
             "[1:a]aformat=sample_rates=24000:channel_layouts=mono[voice];"
             "[voice][bed]amix=inputs=2:duration=first:normalize=0[mix]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(silent), "-i", str(OUT / "voice.wav"), "-i", MUSIC,
                    "-filter_complex", graph, "-map", "0:v", "-map", "[mix]", "-c:v", "copy", "-c:a", "aac",
                    "-shortest", str(final)], check=True)
    print("MADE", final, final.stat().st_size, "seconds", round(sum(seconds for _, seconds in made), 1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
