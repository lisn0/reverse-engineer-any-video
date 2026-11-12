#!/usr/bin/env python3
"""Compare estimated shot counts or boundary times with a reference.

    python3 benchmark/eval_shots.py NAME=VIDEO:SHOTS [NAME=VIDEO:BOUNDARIES.json ...]

Boundary JSON contains a list of cut times and optional gradual intervals in seconds.
Example: [0.75, [2.4, 2.9], 3.5]
"""
import argparse
from bisect import bisect_left
import json
import math
import runpy
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = (ROOT / "plugins/reverse-engineer-any-video/skills"
          / "reverse-engineer-any-video/scripts/evidence.py")


def read_boundaries(path: Path) -> list[tuple[float, float]]:
    data = json.loads(path.read_text())
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected a list of boundaries")
    boundaries = []
    previous_end = 0.0
    for value in data:
        pair = value if isinstance(value, list) else [value, value]
        if len(pair) != 2 or any(type(t) not in (int, float) or not math.isfinite(t) for t in pair):
            raise ValueError(f"{path}: invalid boundary {value!r}")
        start, end = pair
        if not previous_end < start <= end:
            raise ValueError(f"{path}: boundaries must be positive, ordered and disjoint")
        boundaries.append((start, end))
        previous_end = end
    return boundaries


def score_boundaries(times: list[float], truth: list[tuple[float, float]], tolerance: float) -> dict:
    """Match one prediction per reference, maximizing the number of matches."""
    intervals = [(start - tolerance, end + tolerance, (start, end)) if start == end
                 else (start, end, (start, end)) for start, end in truth]
    unmatched = sorted(times)
    missed = []
    # Use the earliest available prediction for the reference that expires first.
    # A nearest-time match can consume the only prediction available to a later cut.
    for start, end, reference in sorted(intervals, key=lambda interval: interval[1]):
        index = bisect_left(unmatched, round(start, 9))
        if index < len(unmatched) and unmatched[index] <= round(end, 9):
            unmatched.pop(index)
        else:
            missed.append(reference)
    tp = len(times) - len(unmatched)
    return {"tp": tp, "fp": len(unmatched), "fn": len(missed),
            "precision": round(tp / len(times), 4) if times else None,
            "recall": round(tp / len(truth), 4) if truth else None,
            "f1": round(2 * tp / (len(times) + len(truth)), 4) if times or truth else None,
            "false_positive_times": unmatched, "missed_boundaries": sorted(missed)}


def evaluate(evidence: dict, video: Path, duration: float,
             boundaries: list[tuple[float, float]] | None, tolerance: float) -> tuple[dict, list[float]]:
    with tempfile.TemporaryDirectory() as work:
        changes = evidence["find_changes"](video, duration, Path(work))
    events = changes["events"]
    shots = [e["t"] for e in events if e["kind"] == "shot"]
    counts = {kind: sum(e["kind"] == kind for e in events) for kind in ("shot", "element", "text", "small")}
    result = {"estimated_shots": len(shots) + 1, **counts}
    if boundaries is not None:
        shots_and_elements = [e["t"] for e in events if e["kind"] in {"shot", "element"}]
        result.update(cut_tolerance_s=tolerance,
                      shot_only=score_boundaries(shots, boundaries, tolerance),
                      shot_or_element=score_boundaries(shots_and_elements, boundaries, tolerance))
    return result, shots


def read_dissect_timelines(folder: Path) -> dict[Path, dict]:
    timelines = {}
    for path in folder.glob("*/data/timeline.json"):
        timeline = json.loads(path.read_text())
        source = Path(timeline["source"]).resolve()
        if source in timelines:
            raise ValueError(f"multiple Dissect timelines for {source}")
        timelines[source] = timeline
    if not timelines:
        raise ValueError(f"no Dissect timelines in {folder}")
    return timelines


def compare_dissect(timeline: dict, boundaries: list[tuple[float, float]] | None, tolerance: float) -> dict:
    shots = timeline["shots"]
    starts = [{"t": shot["start"], **shot["transition_in"]} for shot in shots[1:]]
    internal = [change for shot in shots for change in shot["internal_changes"]]
    result = {"estimated_shots": len(shots), "transitions": starts, "internal_changes": internal}
    if boundaries is not None:
        times = [event["t"] for event in starts]
        internal_cuts = [event["t"] for event in internal if event["type"] == "cut"]
        result["shot_only"] = score_boundaries(times, boundaries, tolerance)
        result["shot_with_internal_cuts"] = score_boundaries(times + internal_cuts, boundaries, tolerance)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tolerance", type=float, default=0.15, help="seconds on either side of a cut")
    parser.add_argument("--baseline", metavar="REV", help="also score the detector from this Git revision")
    parser.add_argument("--dissect-dir", type=Path, metavar="DIR", help="also score local inputs' Dissect timelines")
    parser.add_argument("--crosscheck-cuts", action="store_true", help="also score the native-frame cue")
    parser.add_argument("cases", nargs="+", metavar="NAME=VIDEO:SHOTS_OR_BOUNDARIES_JSON")
    args = parser.parse_args()
    if not math.isfinite(args.tolerance) or args.tolerance < 0:
        parser.error("--tolerance must be finite and nonnegative")
    try:
        timelines = read_dissect_timelines(args.dissect_dir) if args.dissect_dir else {}
    except ValueError as exc:
        parser.error(str(exc))
    evidence = runpy.run_path(str(SCRIPT))
    baseline = None
    if args.baseline:
        try:
            source = subprocess.run(["git", "-C", str(ROOT), "show", "--end-of-options",
                                     f"{args.baseline}:{SCRIPT.relative_to(ROOT).as_posix()}"],
                                    check=True, capture_output=True, text=True).stdout
        except subprocess.CalledProcessError as exc:
            parser.error(f"cannot read detector at Git revision {args.baseline!r}: {exc.stderr.strip()}")
        with tempfile.TemporaryDirectory() as work:
            path = Path(work) / "evidence.py"
            path.write_text(source)
            baseline = runpy.run_path(str(path))
    for item in args.cases:
        name, rest = item.split("=", 1)
        video, reference = rest.rsplit(":", 1)
        facts = evidence["probe"](Path(video))
        boundaries = read_boundaries(Path(reference)) if reference.endswith(".json") else None
        if boundaries and boundaries[-1][1] >= facts["duration_s"]:
            parser.error(f"{name}: a boundary falls beyond the picture")
        truth_shots = len(boundaries) + 1 if boundaries is not None else int(reference)
        reading, shots = evaluate(evidence, Path(video), facts["duration_s"], boundaries, args.tolerance)
        result = {"case": name, "truth_shots": truth_shots, **reading}
        if args.crosscheck_cuts:
            times = evidence["native_cut_candidates"](Path(video), facts["duration_s"])
            result["native_cut_candidates_s"] = times
            if boundaries is not None:
                result["native_cut_score"] = score_boundaries(times, boundaries, args.tolerance)
        if args.dissect_dir:
            timeline = timelines.get(Path(video).resolve())
            if timeline is None:
                parser.error(f"no Dissect timeline for {video}")
            result["dissect"] = compare_dissect(timeline, boundaries, args.tolerance)
        if baseline is not None:
            old, old_shots = evaluate(baseline, Path(video), facts["duration_s"], boundaries, args.tolerance)
            result["baseline"] = {"revision": args.baseline, **old}
            result["baseline_shot_times"] = old_shots
        print(json.dumps(result))
        print("  shot times:", shots, flush=True)


if __name__ == "__main__":
    main()
