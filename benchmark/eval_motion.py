#!/usr/bin/env python3
"""Compare whole-picture motion evidence on videos with known dominant motion.

    python3 benchmark/eval_motion.py --baseline REV NAME=VIDEO=pan NAME=VIDEO=zoom

Use 'none' for a stationary control. Sparse or mixed evidence reads 'unknown'.
"""
import argparse
import json
import runpy
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = Path("plugins/reverse-engineer-any-video/skills/reverse-engineer-any-video/scripts/evidence.py")


def score(evidence: dict, video: Path) -> dict:
    facts = evidence["probe"](video)
    with tempfile.TemporaryDirectory() as work:
        changes = evidence["find_changes"](video, facts["duration_s"], Path(work))
    motion = Counter(reading["kind"] for reading in changes.get("picture_motion", []))
    pan, zoom = motion["pan"], motion["zoom"]
    reading = "unknown"
    if max(pan, zoom) >= 2 and max(pan, zoom) >= 2 * min(pan, zoom):
        reading = "pan" if pan > zoom else "zoom"
    return {"reading": reading, "pan_windows": pan, "zoom_windows": zoom,
            "shot_times": [event["t"] for event in changes["events"] if event["kind"] == "shot"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--baseline", help="Git revision to run on the same inputs")
    parser.add_argument("cases", nargs="+", metavar="NAME=VIDEO=KIND")
    args = parser.parse_args()
    baseline = None
    if args.baseline:
        source = subprocess.check_output(["git", "-C", str(ROOT), "show", f"{args.baseline}:{SCRIPT}"])
        baseline = {"__name__": "baseline"}
        exec(compile(source, f"{args.baseline}:{SCRIPT}", "exec"), baseline)
    candidate = runpy.run_path(str(ROOT / SCRIPT))
    for item in args.cases:
        name, rest = item.split("=", 1)
        video, truth = rest.rsplit("=", 1)
        if truth not in {"pan", "zoom", "none"}:
            parser.error(f"{name}: expected pan, zoom or none, got {truth!r}")
        row = {"case": name, "truth": truth, "candidate": score(candidate, Path(video))}
        if baseline is not None:
            row["baseline"] = score(baseline, Path(video))
        print(json.dumps(row), flush=True)


if __name__ == "__main__":
    main()
