#!/usr/bin/env python3
"""Make slideshow videos with steady zoom and exact shot counts, for shot-count tests.

    python3 benchmark/make_zoom_cases.py OUT_DIR IMAGE_DIR [SEED_OFFSET] [ZOOM_STEP]

IMAGE_DIR is any folder of .jpg stills (the published runs used 16 generated images).
Use a new offset for videos the detector hasn't seen. Each shot is one image with a slow zoom. Captions change on their own rhythm, so they
often change mid-shot. Timing comes from a fixed seed, so the truth is known exactly.
"""
import json
import random
import subprocess
import sys
from pathlib import Path

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FPS = 24
CAPTION_SECONDS = 1.3
CASES = {"zoom-1": (11, 12, "cover", "in"), "zoom-2": (22, 16, "fit", "in"), "zoom-3": (33, 10, "cover", "both")}


def fit(mode: str) -> str:
    if mode == "cover":
        return "scale=1440:2560:force_original_aspect_ratio=increase,crop=1440:2560"
    return "scale=1440:2560:force_original_aspect_ratio=decrease,pad=1440:2560:(ow-iw)/2:(oh-ih)/2:white"


def zoom(direction: str, frames: int, rate: float) -> str:
    start, step = (1.0, rate) if direction == "in" else (1.0 + rate * frames, -rate)
    return f"zoompan=z={start}+{step}*on:d={frames}:x=iw/2-iw/zoom/2:y=ih/2-ih/zoom/2:s=720x1280:fps={FPS}"


def main() -> int:
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    out = Path(sys.argv[1])
    images = sorted(Path(sys.argv[2]).glob("*.jpg"))
    if not images:
        raise SystemExit(f"no .jpg images in {sys.argv[2]}")
    offset = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    rate = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0022
    out.mkdir(parents=True, exist_ok=True)
    truth = {}
    for name, (seed, shots, mode, direction) in CASES.items():
        rng = random.Random(seed + offset)
        picked = rng.sample(images, min(shots, len(images)))
        picked += rng.choices(images, k=shots - len(picked))
        lengths = [rng.randint(36, 96) for _ in range(shots)]
        inputs, chains = [], []
        for index, (image, frames) in enumerate(zip(picked, lengths)):
            way = direction if direction != "both" else ("in" if index % 2 == 0 else "out")
            inputs += ["-i", str(image)]
            chains.append(f"[{index}:v]{fit(mode)},{zoom(way, frames, rate)},trim=end_frame={frames},setpts=PTS-STARTPTS[v{index}]")
        total = sum(lengths) / FPS
        captions = []
        for number in range(int(total / CAPTION_SECONDS)):
            begin = number * CAPTION_SECONDS
            captions.append(f"drawtext=fontfile={FONT}:text='caption {number}':fontsize=44:fontcolor=white:"
                            f"borderw=3:bordercolor=black:x=(w-tw)/2:y=h-220:"
                            f"enable='between(t,{begin:.2f},{begin + CAPTION_SECONDS:.2f})'")
        joined = "".join(f"[v{index}]" for index in range(shots))
        graph = ";".join(chains) + f";{joined}concat=n={shots}:v=1:a=0," + ",".join(captions) + "[out]"
        target = out / f"{name}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", graph, "-map", "[out]",
                        "-c:v", "libx264", "-crf", "22", "-pix_fmt", "yuv420p", str(target)], check=True)
        truth[name] = {"video": str(target), "shots": shots, "cut_times": []}
        elapsed = 0
        for frames in lengths[:-1]:
            elapsed += frames
            truth[name]["cut_times"].append(round(elapsed / FPS, 2))
    (out / "truth.json").write_text(json.dumps(truth, indent=1))
    print(json.dumps({key: value["shots"] for key, value in truth.items()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
