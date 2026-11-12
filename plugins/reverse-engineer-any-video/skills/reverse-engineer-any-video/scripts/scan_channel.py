#!/usr/bin/env python3
"""Rank a channel's videos against the channel's own baseline.

    python3 scan_channel.py "<TikTok profile URL>" --out ./runs/<name>
    python3 scan_channel.py "https://www.youtube.com/@<handle>/shorts" --limit 300

Each video is scored as views / median views of its neighbours in upload order,
inside its own format (short or long). Outliers and flops from the same channel
are the comparison set for the deep analysis step.

Stdlib plus the `yt-dlp` command. Writes channel.json and outliers.md. Exits
non-zero when the listing has no usable view counts.
"""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SHORT_MAX_SECONDS = 180
WINDOW = 15  # neighbours on each side
MIN_NEIGHBOURS = 5
OUTLIER_RATIO = 3.0
FLOP_RATIO = 0.5
SETTLE_DAYS = 14  # newer videos are still gaining views, so they stay unlabelled


def list_channel(url: str, limit: int) -> list[dict]:
    argv = ["yt-dlp", "-J", "--flat-playlist", "--playlist-end", str(limit), url]
    proc = subprocess.run(argv, capture_output=True, text=True, check=True)
    entries = json.loads(proc.stdout).get("entries")
    if not entries:
        raise SystemExit(f"yt-dlp returned no entries for {url}")
    # A channel root lists its tabs as nested playlists.
    if any(e.get("_type") == "playlist" for e in entries):
        raise SystemExit("URL lists tabs, not videos: pass the /videos or /shorts tab")
    return entries


def age_days(entry: dict, now: datetime) -> int | None:
    timestamp = entry.get("timestamp")
    if timestamp is None:
        return None
    return (now - datetime.fromtimestamp(timestamp, timezone.utc)).days


def video_format(entry: dict) -> str | None:
    # YouTube's Shorts tab omits duration, but the URL itself proves the format.
    if "/shorts/" in (entry.get("url") or ""):
        return "short"
    duration = entry.get("duration")
    if duration is None:
        return None
    return "short" if duration <= SHORT_MAX_SECONDS else "long"


def score_group(videos: list[dict]) -> None:
    """Score one format group. `videos` stays in listing order (newest first)."""
    for index, video in enumerate(videos):
        low, high = max(0, index - WINDOW), index + WINDOW + 1
        neighbours = [v["views"] for i, v in enumerate(videos[low:high], low) if i != index]
        if len(neighbours) < MIN_NEIGHBOURS:
            video["baseline"], video["ratio"], video["label"] = None, None, "unscored"
            continue
        baseline = statistics.median(neighbours)
        video["baseline"] = baseline
        video["ratio"] = round(video["views"] / baseline, 2) if baseline else None
        video["label"] = label(video)


def fill_missing_dates(videos: list[dict]) -> None:
    """Fetch real dates for undated outliers and flops, then re-judge them.

    Flat YouTube listings have no dates, so a new video can look like a flop.
    """
    undated = {v["id"]: v for v in videos
               if v["age_days"] is None and v["label"] in ("outlier", "flop")}
    if not undated:
        return
    argv = ["yt-dlp", "--skip-download", "--ignore-errors", "--print", "%(id)s %(timestamp)s",
            *(v["url"] for v in undated.values())]
    proc = subprocess.run(argv, capture_output=True, text=True, check=False)
    now = datetime.now(timezone.utc)
    for line in proc.stdout.splitlines():
        video_id, _, timestamp = line.partition(" ")
        if video_id in undated and timestamp.isdigit():
            video = undated[video_id]
            video["age_days"] = age_days({"timestamp": int(timestamp)}, now)
            video["label"] = label(video)


def label(video: dict) -> str:
    if video["ratio"] is None:
        return "unscored"
    if video["age_days"] is not None and video["age_days"] < SETTLE_DAYS:
        return "too-new"
    if video["ratio"] >= OUTLIER_RATIO:
        return "outlier"
    if video["ratio"] <= FLOP_RATIO:
        return "flop"
    return "normal"


def build_videos(entries: list[dict]) -> tuple[list[dict], int]:
    now = datetime.now(timezone.utc)
    videos, skipped = [], 0
    for entry in entries:
        fmt = video_format(entry)
        views = entry.get("view_count")
        if views is None or fmt is None:
            skipped += 1
            continue
        videos.append({
            "id": entry.get("id"),
            "title": entry.get("title") or entry.get("description") or "",
            "url": entry.get("url") or entry.get("webpage_url"),
            "views": views,
            "duration": entry.get("duration"),
            "format": fmt,
            "age_days": age_days(entry, now),
            "likes": entry.get("like_count"),
            "comments": entry.get("comment_count"),
        })
    if not videos:
        raise SystemExit("no entry had both view_count and a known format")
    for fmt in ("short", "long"):
        score_group([v for v in videos if v["format"] == fmt])
    fill_missing_dates(videos)
    return videos, skipped


def render_row(video: dict) -> str:
    title = " ".join(video["title"].split())[:70].replace("|", "/")
    return f"| {video['ratio']}x | {video['views']:,} | {video['format']} | [{title or video['id']}]({video['url']}) |"


def render_report(url: str, videos: list[dict], skipped: int, top: int) -> str:
    counts = {name: sum(v["label"] == name for v in videos)
              for name in ("outlier", "normal", "flop", "too-new", "unscored")}
    undated = sum(v["age_days"] is None and v["label"] in ("outlier", "flop") for v in videos)
    lines = [f"# Channel scan: {url}", "",
             f"{len(videos)} videos scored, {skipped} skipped (no views or known format). "
             + ", ".join(f"{k}: {n}" for k, n in counts.items()) + ".", ""]
    if undated:
        lines += [f"{undated} outliers or flops still have no upload date, "
                  "so the too-new check could not apply to them.", ""]
    scored = [v for v in videos if v["ratio"] is not None]
    groups = (("Outliers", "outlier", True), ("Flops", "flop", False))
    for heading, name, reverse in groups:
        rows = sorted((v for v in scored if v["label"] == name),
                      key=lambda v: v["ratio"], reverse=reverse)[:top]
        lines += [f"## {heading}", "", "| vs baseline | views | format | video |",
                  "|---|---|---|---|", *map(render_row, rows), ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("url")
    parser.add_argument("--limit", type=int, default=300)
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--out", type=Path, default=Path("runs/scan"))
    args = parser.parse_args()

    videos, skipped = build_videos(list_channel(args.url, args.limit))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "channel.json").write_text(json.dumps(
        {"url": args.url, "skipped": skipped, "videos": videos}, indent=2, ensure_ascii=False))
    report = render_report(args.url, videos, skipped, args.top)
    (args.out / "outliers.md").write_text(report)
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
