"""Compare the standard detector commands on new edits with frame-authored truth."""

import argparse
import json
import os
from pathlib import Path
import random
import subprocess
import sys

from PIL import Image, ImageDraw


FPS = 30
SIZE = (480, 270)
LENGTH = 450
EYES_COMMIT = "a5409613b2bfba96147efbebb6c92b400fe305c8"
EVIDENCE = (
    Path(__file__).resolve().parents[1]
    / "plugins/reverse-engineer-any-video/skills/reverse-engineer-any-video/scripts/evidence.py"
)
KINDS = ("cut", "dissolve", "fast wipe", "fast dip")


def backgrounds(seed):
    rng = random.Random(seed)
    images = []
    for _ in range(8):
        top, bottom = [tuple(rng.randrange(20, 236) for _ in range(3)) for _ in range(2)]
        base = Image.new("RGB", (640, 320))
        draw = ImageDraw.Draw(base)
        for y in range(base.height):
            shade = tuple(round(a + (b - a) * y / base.height) for a, b in zip(top, bottom))
            draw.line((0, y, base.width, y), fill=shade)
        for _ in range(34):
            x, y = rng.randrange(-50, 640), rng.randrange(-50, 320)
            width, height = rng.randrange(16, 125), rng.randrange(16, 110)
            color = tuple(rng.randrange(18, 238) for _ in range(3))
            shape = rng.choice((draw.rectangle, draw.ellipse))
            shape((x, y, x + width, y + height), fill=color)
        images.append(base)
    return images


def render_video(root, name, seed, edits, *, mostly_static):
    images = backgrounds(seed)
    controls = {"flash": 58, "whip pan": 401, "overlay": 423}
    truth = [
        {"kind": kind, "start": start / FPS, "end": (start + duration) / FPS}
        for kind, start, duration in edits
    ]

    def picture(shot, frame, x_offset=0):
        x = 10 + x_offset + (0 if mostly_static else (150 - abs(frame % 300 - 150)) // 3)
        y = 15 + (0 if mostly_static else (90 - abs(frame % 180 - 90)) // 6)
        frame_image = images[shot].crop((x, y, x + SIZE[0], y + SIZE[1]))
        if mostly_static:
            return frame_image
        actor = ImageDraw.Draw(frame_image)
        x = 30 + (165 - abs((frame * 3) % 330 - 165))
        actor.ellipse((x, 170, x + 42, 212), fill=(221, 118, 88))
        return frame_image

    video = root / f"{name}.mp4"
    command = [
        "ffmpeg", "-nostdin", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{SIZE[0]}x{SIZE[1]}", "-r", str(FPS), "-i", "pipe:0",
        "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", "-threads", "2", str(video),
    ]
    shot = 0
    with subprocess.Popen(command, stdin=subprocess.PIPE) as encoder:
        for frame in range(LENGTH):
            if shot < len(edits) and frame >= sum(edits[shot][1:]):
                shot += 1
            pan = min(60, max(0, frame - controls["whip pan"]) * 15)
            image = picture(shot, frame, pan)
            if shot < len(edits):
                kind, start, duration = edits[shot]
                if frame >= start and duration:
                    alpha = (frame - start + 1) / (duration + 1)
                    incoming = picture(shot + 1, frame)
                    if kind == "dissolve":
                        image = Image.blend(image, incoming, alpha)
                    elif kind == "fast wipe":
                        edge = round(SIZE[0] * alpha)
                        image.paste(incoming.crop((0, 0, edge, SIZE[1])), (0, 0))
                    elif kind == "fast dip":
                        black = Image.new("RGB", SIZE)
                        image = Image.blend(image if alpha < 0.5 else incoming, black,
                                            1 - abs(2 * alpha - 1))
            if controls["flash"] <= frame < controls["flash"] + 2:
                image = Image.blend(image, Image.new("RGB", SIZE, "white"), 0.88)
            if controls["overlay"] <= frame < controls["overlay"] + 12:
                ImageDraw.Draw(image).rectangle((140, 80, 350, 180), fill="white")
            encoder.stdin.write(image.tobytes())
        encoder.stdin.close()
        if encoder.wait():
            raise RuntimeError(f"FFmpeg failed to render {name}")

    control_seconds = {kind: frame / FPS for kind, frame in controls.items()}
    (root / f"{name}.truth.json").write_text(
        json.dumps({"events": truth, "controls": control_seconds}, indent=2)
    )
    return video, truth, control_seconds


def score(truth, guesses):
    """Each detection can match one edit, within its interval plus two frames."""
    matched = set()
    results = []
    for edit in truth:
        center = (edit["start"] + edit["end"]) / 2
        candidates = [
            i for i, event in enumerate(guesses)
            if i not in matched and edit["start"] - 2 / FPS <= event["t"] <= edit["end"] + 2 / FPS
        ]
        best = min(candidates, key=lambda i: abs(guesses[i]["t"] - center), default=None)
        if best is not None:
            matched.add(best)
        results.append({**edit, "detection": guesses[best] if best is not None else None})
    return {"edits": results, "extra_boundaries": [
        event for i, event in enumerate(guesses) if i not in matched
    ]}


def run_detector(script, arguments, log, env=None):
    with log.open("w") as output:
        subprocess.run([sys.executable, "-B", str(script), *arguments], env=env,
                       stdout=output, stderr=subprocess.STDOUT, check=True)


def index_eyes(root, env, video, name):
    with (root / f"{name}-eyes.log").open("w") as output:
        subprocess.run(
            [sys.executable, "-B", "-c", "from eyes.cli import main; raise SystemExit(main())",
             "index", str(video), "--no-ocr", "--title", name],
            env=env, stdout=output, stderr=subprocess.STDOUT, check=True,
        )
    shot_files = [
        path for path in (root / "eyes").glob("*/shots.json")
        if json.loads((path.parent / "index.json").read_text())["title"] == name
    ]
    if len(shot_files) != 1:
        raise RuntimeError(f"Expected one Claude Eyes shot index for {name}: {shot_files}")
    return [{"t": shot["start"], "cue": "cut"}
            for shot in json.loads(shot_files[0].read_text())["shots"][1:]]


def compare(root, eyes_source, evidence, annotated, detect_dissolves):
    env = {**os.environ, "PYTHONPATH": str(eyes_source / "src"), "EYES_HOME": str(root / "eyes")}
    actual = subprocess.check_output(["git", "-C", str(eyes_source), "rev-parse", "HEAD"], text=True)
    if actual.strip() != EYES_COMMIT:
        raise ValueError(f"Expected Claude Eyes commit {EYES_COMMIT}, received {actual.strip()}")
    if annotated is not None:
        video, annotations = annotated
        from eval_shots import read_boundaries, score_boundaries

        eyes = index_eyes(root, env, video, "annotated")
        result = score_boundaries([shot["t"] for shot in eyes], read_boundaries(annotations), 0.15)
        print("Claude Eyes independent excerpt:", json.dumps(result), flush=True)
        return

    cases = [
        ("steady", 44201, [("cut", 91, 0), ("dissolve", 137, 9), ("cut", 181, 0),
                           ("fast wipe", 231, 4), ("dissolve", 279, 24), ("fast dip", 344, 5)]),
        ("moving", 81907, [("dissolve", 93, 13), ("cut", 151, 0), ("fast dip", 198, 4),
                           ("cut", 224, 0), ("dissolve", 268, 33), ("fast wipe", 350, 6)]),
        ("validation", 57033, [("fast wipe", 93, 3), ("dissolve", 137, 10), ("cut", 186, 0),
                               ("dissolve", 232, 28), ("fast dip", 298, 6), ("cut", 351, 0)]),
    ]
    reports = {}
    for name, seed, edits in cases:
        video, truth, controls = render_video(root, name, seed, edits, mostly_static=name == "steady")
        ours_dir = root / f"{name}-ours"
        arguments = [str(video), "--out", str(ours_dir), "--no-transcript"]
        if detect_dissolves:
            arguments.append("--detect-dissolves")
        run_detector(evidence, arguments, root / f"{name}-ours.log")
        eyes = index_eyes(root, env, video, name)
        ours = json.loads((ours_dir / "changes.json").read_text())
        reports[name] = {
            "eyes": score(truth, eyes),
            "ours": score(truth, [event for event in ours["events"] if event["kind"] == "shot"]),
            "ours_uncertain": score(truth, ours["uncertain_shots"]),
            "controls": controls,
        }
        print(name, json.dumps(reports[name]), flush=True)
    (root / "report.json").write_text(json.dumps(reports, indent=2))
    for tool in ("eyes", "ours"):
        results = [result for case in reports.values() for result in case[tool]["edits"]]
        counts = {
            kind: [sum(result["detection"] is not None for result in results if result["kind"] == kind),
                   sum(result["kind"] == kind for result in results)] for kind in KINDS
        }
        extras = sum(len(case[tool]["extra_boundaries"]) for case in reports.values())
        print(f"{tool}: {counts}, extra boundaries: {extras}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="New output directory")
    parser.add_argument("eyes_source", type=Path, help="Pinned Claude Eyes git checkout")
    parser.add_argument("--evidence", type=Path, default=EVIDENCE)
    parser.add_argument("--annotated", nargs=2, type=Path, metavar=("VIDEO", "BOUNDARIES"),
                        help="Only score Eyes on the independent excerpt using the existing BBC scorer")
    parser.add_argument("--detect-dissolves", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    root.mkdir()
    print(f"Results: {root}", flush=True)
    compare(root, args.eyes_source.resolve(), args.evidence.resolve(), args.annotated, args.detect_dissolves)


if __name__ == "__main__":
    main()
