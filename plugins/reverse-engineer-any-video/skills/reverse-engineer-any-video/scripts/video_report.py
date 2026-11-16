"""Build local playback reports and compare measured properties of indexed videos."""

from __future__ import annotations

import json
import os
import re
import statistics
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import quote

if __package__:
    from . import evidence
else:
    import evidence

TEMPLATE = Path(__file__).resolve().parents[1] / "assets/video-report.html"


def relative_url(target: Path, base: Path) -> str:
    try:
        return quote(Path(os.path.relpath(target, base)).as_posix())
    except ValueError:
        # Different drives on Windows need an absolute file URL.
        return target.resolve().as_uri()


def loudness(media: Path, duration: float, offset: float) -> float | None:
    command = [
        "ffmpeg", "-nostdin", "-hide_banner", "-nostats", "-loglevel", "info",
        "-ss", str(max(0.0, offset)), "-i", str(media), "-t", str(duration),
        "-map", "0:a:0", "-vn", "-af", "ebur128=framelog=verbose", "-f", "null", "-",
    ]
    reading = subprocess.run(command, capture_output=True, text=True)
    if reading.returncode:
        raise SystemExit(f"Loudness measurement failed: {reading.stderr.strip()[-800:]}")
    final = reading.stderr.rsplit("Integrated loudness:", 1)[-1]
    match = re.search(r"\bI:\s*(-?\d+(?:\.\d+)?)\s+LUFS", final)
    if not match:
        return None
    measured = float(match.group(1))
    # FFmpeg emits its floor value when no program material clears the loudness gate.
    return measured if measured > -70 else None


def measurements(index: dict, events: list[dict], integrated: float | None) -> dict:
    facts = index["facts"]
    duration = facts["duration_s"]
    coverage = index["coverage"]
    boundaries = sorted({event["t"] for event in events if 0 < event["t"] < duration})
    edges = [0, *boundaries, duration]
    shot_lengths = [after - before for before, after in zip(edges, edges[1:])]
    frames = index["frames"]
    with_text = [frame for frame in frames if frame.get("text", "").strip()]
    return {
        "Duration (s)": duration,
        "Resolution": f"{facts['width']} × {facts['height']}",
        "Frame rate (fps)": facts["fps"],
        "Hard-cut calls": sum(event["cue"] == "cut" for event in events),
        "Gradual boundary calls": sum(event["cue"] == "gradual" for event in events),
        "Boundary calls in first 3 s": sum(t < 3 for t in boundaries),
        "Boundary calls per minute": len(boundaries) * 60 / duration,
        "Median estimated shot (s)": statistics.median(shot_lengths),
        "Estimated shots under 1 s (%)": 100 * sum(length < 1 for length in shot_lengths) / len(shot_lengths),
        "Spoken words per video minute": (
            len(index["words"]) * 60 / duration
            if coverage["speech"] == "indexed" and not index.get("captions") else None
        ),
        "Samples with visible text (%)": (
            100 * len(with_text) / len(frames) if frames and coverage["screen"] == "sampled" else None
        ),
        "Integrated loudness (LUFS)": integrated,
    }


def metric_rows(readings: list[dict]) -> list[dict]:
    def format_value(value):
        if value is None:
            return "Unavailable"
        return str(value) if not isinstance(value, float) else f"{value:.2f}".rstrip("0").rstrip(".")

    rows = []
    for label in readings[0]:
        values = [reading[label] for reading in readings]
        delta = None
        if len(values) == 2 and all(isinstance(value, (int, float)) for value in values):
            difference = values[1] - values[0]
            delta = format_value(difference)
            if float(delta) == 0:
                delta = "0"
            elif difference > 0:
                delta = f"+{delta}"
        rows.append({"label": label, "values": [format_value(value) for value in values], "delta": delta})
    return rows


def report_video(path: Path, index: dict, report_dir: Path, *, detect_dissolves: bool) -> tuple[dict, dict]:
    media = (path.parent / index["video"]).resolve()
    if not media.is_file():
        raise SystemExit(f"Indexed media is missing: {media}")
    facts = index["facts"]
    duration = facts["duration_s"]
    with tempfile.TemporaryDirectory(prefix="video-report-") as work:
        changes = evidence.find_changes(media, duration, Path(work), detect_dissolves=detect_dissolves)
    events = [event for event in changes["events"] if event["kind"] in {"shot", "text"}]
    shots = [event for event in events if event["kind"] == "shot"]
    integrated = loudness(media, duration, facts["picture_offset_s"]) if facts["has_audio"] else None
    readings = measurements(index, shots, integrated)
    view = {
        "label": index["source"].get("untrusted_source_text", {}).get("title") or media.name,
        "media": relative_url(media, report_dir),
        "duration": duration,
        "pictureOffset": facts["picture_offset_s"],
        "coverage": index["coverage"],
        "words": index["words"],
        "captions": index.get("captions", []),
        "frames": [
            {**frame, "image": relative_url(path.parent / frame["image"], report_dir)}
            for frame in index["frames"]
        ],
        "events": events,
    }
    return view, readings


def render_report(sources: list[tuple[Path, dict]], out: Path, *, detect_dissolves: bool = False) -> dict:
    if out.suffix.lower() != ".html":
        raise SystemExit("Report output needs an .html extension")
    if out.exists() or out.is_symlink():
        raise SystemExit(f"Choose a new report file: {out}")
    videos, readings = zip(*[
        report_video(path, index, out.parent.resolve(), detect_dissolves=detect_dissolves)
        for path, index in sources
    ])
    metrics = metric_rows(list(readings))
    payload = json.dumps({"videos": videos, "metrics": metrics}, ensure_ascii=True).replace("<", "\\u003c")
    template = TEMPLATE.read_text(encoding="utf-8")
    marker = "__VIDEO_REPORT_DATA__"
    if template.count(marker) != 1:
        raise SystemExit("Report template needs exactly one data marker")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8") as report:
        report.write(template.replace(marker, payload))
    return {"report": str(out.resolve()), "metrics": metrics}
