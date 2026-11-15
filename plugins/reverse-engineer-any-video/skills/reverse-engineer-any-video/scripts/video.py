#!/usr/bin/env python3
"""Index a video for timestamped visual questions, speech search and on-screen text search."""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import re
import shutil
import subprocess
import tempfile
import unicodedata
from itertools import groupby
from pathlib import Path

import evidence


def run_ffmpeg(*arguments: str) -> str:
    command = ["ffmpeg", "-nostdin", "-hide_banner", "-nostats", *arguments]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise SystemExit(f"Could not read video frames: {result.stderr.strip()[-1400:]}")
    return result.stderr


def sample_frames(video: Path, out: Path, interval: float) -> list[dict]:
    folder = out / "frames"
    folder.mkdir()
    log = run_ffmpeg(
        "-loglevel", "info", "-i", str(video), "-map", "0:v:0", "-an",
        "-vf", f"setpts=PTS-STARTPTS,select='isnan(prev_selected_t)+gte(t-prev_selected_t,{interval})',"
        "scale=w='min(1280,iw)':h='min(1280,ih)':force_original_aspect_ratio=decrease,showinfo",
        "-fps_mode", "passthrough", "-threads", "1", "-q:v", "2", str(folder / "%06d.jpg"),
    )
    times = evidence.frame_times(log, 0.0, str(video))
    images = sorted(folder.glob("*.jpg"))
    if not images or len(images) != len(times):
        raise SystemExit("Decoded frame timestamps and image count disagree")
    return [{"t": t, "image": str(image.relative_to(out))} for t, image in zip(times, images)]


def overview(out: Path, frames: list[dict]) -> list[dict]:
    """Build an overview covering the whole video, using the exact sampled images."""
    count = min(len(frames), 48)
    indexes = [round(i * (len(frames) - 1) / max(count - 1, 1)) for i in range(count)]
    pages = []
    for start in range(0, count, 24):
        selected = indexes[start:start + 24]
        rows = math.ceil(len(selected) / 4)
        name = f"overview-{len(pages) + 1}.jpg"
        expression = "+".join(f"eq(n,{i})" for i in selected)
        run_ffmpeg(
            "-loglevel", "error", "-framerate", "1", "-i", str(out / "frames/%06d.jpg"),
            "-vf", f"select='{expression}',scale=280:180:force_original_aspect_ratio=decrease,"
            f"pad=280:180:(ow-iw)/2:(oh-ih)/2,tile=4x{rows}:nb_frames={len(selected)}",
            "-frames:v", "1", "-threads", "1", "-q:v", "3", str(out / name),
        )
        if not (out / name).is_file():
            raise SystemExit(f"Could not make {name}")
        pages.append({"image": name, "columns": 4, "tile_times_s": [frames[i]["t"] for i in selected]})
    return pages


def read_screen(image: Path, language: str) -> str:
    result = subprocess.run(
        ["tesseract", str(image), "stdout", "-l", language, "tsv"],
        capture_output=True, text=True,
    )
    if result.returncode:
        raise SystemExit(f"OCR failed for {image.name}: {result.stderr.strip()}")
    words = [row for row in csv.DictReader(io.StringIO(result.stdout), delimiter="\t")
             if row["level"] == "5" and row["text"] and row["text"].strip()]
    return "\n".join(
        " ".join(row["text"].strip() for row in line)
        for _, line in groupby(words, key=lambda row: (row["block_num"], row["par_num"], row["line_num"]))
    )


def audio_offset(video: Path, picture_offset: float) -> float:
    command = ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
               "stream=start_time:format=start_time", "-of", "json", str(video)]
    metadata = json.loads(evidence.run(command))
    container_start = float(metadata["format"].get("start_time", 0))
    audio_start = float(metadata["streams"][0].get("start_time", container_start))
    return audio_start - container_start - picture_offset


def embedded_captions(video: Path, language: str | None, duration: float,
                      picture_offset: float) -> tuple[list[dict], str | None]:
    """Read a matching-language text subtitle stream, preserving cue-level timing."""
    probe = ["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(video)]
    streams = json.loads(evidence.run(probe)).get("streams", [])
    if language:
        wanted = language.casefold().split("-")[0]
    else:
        audio = [stream for stream in streams if stream.get("codec_type") == "audio"]
        audio_language = str(audio[0].get("tags", {}).get("language", "")).casefold() if audio else ""
        if not audio_language:
            return [], None
        wanted = audio_language.split("-")[0]
    aliases = {
        "en": {"en", "eng"}, "eng": {"en", "eng"},
        "fr": {"fr", "fra", "fre"}, "fra": {"fr", "fra", "fre"}, "fre": {"fr", "fra", "fre"},
        "de": {"de", "deu", "ger"}, "deu": {"de", "deu", "ger"}, "ger": {"de", "deu", "ger"},
        "es": {"es", "spa"}, "spa": {"es", "spa"},
        "it": {"it", "ita"}, "ita": {"it", "ita"},
        "pt": {"pt", "por"}, "por": {"pt", "por"},
        "ja": {"ja", "jpn"}, "jpn": {"ja", "jpn"},
        "zh": {"zh", "zho", "chi"}, "zho": {"zh", "zho", "chi"}, "chi": {"zh", "zho", "chi"},
    }
    accepted = aliases.get(wanted, {wanted})
    candidates = []
    bitmap = {"hdmv_pgs_subtitle", "dvd_subtitle", "dvb_subtitle", "xsub"}
    for stream in streams:
        if (stream.get("codec_type") != "subtitle" or stream.get("codec_name") in bitmap
                or stream.get("disposition", {}).get("forced", 0)):
            continue
        tag = str(stream.get("tags", {}).get("language", "")).casefold()
        if tag.split("-")[0] in accepted:
            candidates.append(stream)
    if not candidates:
        return [], None
    candidates.sort(key=lambda item: -int(item.get("disposition", {}).get("default", 0)))
    stream = candidates[0]
    result = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-i", str(video), "-map", f"0:{stream['index']}",
         "-f", "srt", "pipe:1"], capture_output=True, text=True,
    )
    if result.returncode:
        return [], None
    pattern = re.compile(
        r"(?m)^\s*\d+\s*\n(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*"
        r"(\d{2}:\d{2}:\d{2}[,.]\d{3})[^\n]*\n(.*?)(?=\n\s*\n|\Z)", re.S,
    )
    def seconds(value: str) -> float:
        hours, minutes, rest = value.replace(",", ".").split(":")
        return int(hours) * 3600 + int(minutes) * 60 + float(rest)
    cues = []
    for match in pattern.finditer(result.stdout):
        start = seconds(match.group(1)) - picture_offset
        end = seconds(match.group(2)) - picture_offset
        text = re.sub(r"<[^>]*>", "", match.group(3)).replace(r"\N", " ").strip()
        text = re.sub(r"\s+", " ", text)
        if text and end > 0 and start < duration:
            cues.append({"text": text, "start": round(max(0, start), 3),
                         "end": round(min(duration, end), 3)})
    return cues, str(stream.get("tags", {}).get("language", wanted))


def index_video(args: argparse.Namespace) -> dict:
    if not args.no_ocr and shutil.which("tesseract") is None:
        raise SystemExit("On-screen text requires Tesseract. Install it or pass --no-ocr.")
    local = Path(args.source).expanduser()
    if not local.is_file() and not args.source.startswith(("http://", "https://")):
        raise SystemExit(f"Expected a local video or HTTP(S) URL: {args.source}")
    if args.out.exists() or args.out.is_symlink():
        raise SystemExit(f"Choose a new index directory: {args.out}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{args.out.name}-", dir=args.out.parent))
    try:
        index = build_index(args, local, stage)
        if args.out.exists() or args.out.is_symlink():
            raise FileExistsError(f"Index path was created during processing: {args.out}")
        stage.rename(args.out)
    except (SystemExit, OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"{exc}\nPartial index retained at {stage}.") from exc
    return {"index": str(args.out / "index.json"), "facts": index["facts"], "coverage": index["coverage"],
            "sampled_frames": len(index["frames"]), "speech_words": len(index["words"]),
            "overview": index["overview"]}


def build_index(args: argparse.Namespace, local: Path, stage: Path) -> dict:
    if local.is_file():
        video, source = local.resolve(), {"type": "local file"}
    else:
        video, metadata = evidence.fetch(args.source, stage)
        source = {"type": "url", **evidence.source_facts(metadata, include_description=False)}
    facts = evidence.probe(video)
    words = []
    captions = []
    speech_source = None
    speech = "skipped" if args.no_transcript else "no audio"
    if facts["has_audio"] and not args.no_transcript:
        captions, caption_language = embedded_captions(
            video, args.language, facts["duration_s"], facts["picture_offset_s"]
        )
        if captions:
            speech_source = f"embedded captions ({caption_language})"
        else:
            try:
                evidence.transcribe(video, stage, args.language, args.whisper_model)
            except ModuleNotFoundError as exc:
                if exc.name != "faster_whisper":
                    raise
                raise SystemExit("Speech needs faster-whisper. Install it or pass --no-transcript.") from exc
            offset = audio_offset(video, facts["picture_offset_s"])
            for word in json.loads((stage / "words.json").read_text(encoding="utf-8")):
                start, end = word["start"] + offset, word["end"] + offset
                if end > 0 and start < facts["duration_s"]:
                    words.append({"word": word["word"], "start": round(max(0, start), 3),
                                  "end": round(min(facts["duration_s"], end), 3)})
            speech_source = "faster-whisper"
        speech = "indexed"
    frames = sample_frames(video, stage, args.sample_every)
    if not args.no_ocr:
        for frame in frames:
            frame["text"] = read_screen(stage / frame["image"], args.ocr_language)
    sheets = overview(stage, frames)
    index = {
        "source": source,
        "video": str(video) if local.is_file() else video.name,
        "facts": facts,
        "coverage": {"speech": speech, "speech_source": speech_source,
                     "screen": "skipped" if args.no_ocr else "sampled",
                     "minimum_sample_spacing_s": args.sample_every},
        "overview": sheets,
        "words": words,
        "captions": captions,
        "frames": frames,
    }
    (stage / "index.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return index


# Split CJK and Japanese ideographs/syllabaries so a phrase can match inside unspaced text.
TOKEN = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]|(?:(?![\u3040-\u30ff\u3400-\u9fff])[^\W_])+")


def tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    result = []
    for token in TOKEN.findall(normalized):
        if all("LATIN" in unicodedata.name(char, "") or char.isdigit() for char in token):
            token = "".join(char for char in unicodedata.normalize("NFKD", token)
                            if not unicodedata.combining(char))
        result.append(token)
    return result


def speech_hits(words: list[dict], query: list[str]) -> list[dict]:
    terms = [(token, i) for i, word in enumerate(words) for token in tokens(word["word"])]
    hits = []
    for i in range(len(terms) - len(query) + 1):
        window = terms[i:i + len(query)]
        if [token for token, _ in window] != query:
            continue
        first, last = window[0][1], window[-1][1]
        if any(b["start"] - a["end"] > 1.5 for a, b in zip(words[first:last], words[first + 1:last + 1])):
            continue
        hits.append({"track": "said", "start": words[first]["start"], "end": words[last]["end"],
                     "text": " ".join(word["word"] for word in words[first:last + 1])})
    return hits


def caption_hits(captions: list[dict], query: list[str]) -> list[dict]:
    hits = []
    for cue in captions:
        terms = tokens(cue["text"])
        if any(terms[i:i + len(query)] == query for i in range(len(terms) - len(query) + 1)):
            hits.append({"track": "said", "start": cue["start"], "end": cue["end"],
                         "text": cue["text"], "source": "embedded captions"})
    return hits


def screen_hits(frames: list[dict], query: list[str]) -> list[dict]:
    hits = []
    previous = None
    for frame in frames:
        text = frame.get("text", "")
        terms = tokens(text)
        found = any(terms[i:i + len(query)] == query for i in range(len(terms) - len(query) + 1))
        if not found:
            previous = None
            continue
        if previous is not None:
            previous["last_seen"] = frame["t"]
            continue
        previous = {"track": "shown", "first_seen": frame["t"], "last_seen": frame["t"],
                    "text": text, "image": frame["image"]}
        hits.append(previous)
    return hits


def load_index(path: Path) -> tuple[Path, dict]:
    path = (path / "index.json" if path.is_dir() else path).resolve()
    try:
        index = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Could not read index {path}: {exc}") from exc
    if not isinstance(index, dict) or not all(
        isinstance(index.get(key), kind)
        for key, kind in (("words", list), ("frames", list), ("coverage", dict))
    ):
        raise SystemExit(f"Expected a video.py index at {path}")
    return path, index


def search(indexes: list[Path], query: str, track: str) -> dict:
    query_tokens = tokens(query)
    if not query_tokens:
        raise SystemExit("Search needs at least one letter or number")
    results = []
    for path in indexes:
        path, index = load_index(path)
        hits = []
        if track in ("all", "said"):
            hits.extend(speech_hits(index["words"], query_tokens))
            hits.extend(caption_hits(index.get("captions", []), query_tokens))
        if track in ("all", "shown"):
            hits.extend(screen_hits(index["frames"], query_tokens))
        for hit in hits:
            if hit["track"] == "shown":
                hit["image"] = str(path.parent / hit["image"])
        hits.sort(key=lambda hit: hit["start"] if hit["track"] == "said" else hit["first_seen"])
        results.append({"index": str(path), "coverage": index["coverage"], "hits": hits})
    return {"query": query, "results": results}


def timestamp(value: str) -> float:
    """Accept seconds, minutes:seconds or hours:minutes:seconds."""
    try:
        parts = [float(part) for part in value.split(":")]
        if (len(parts) > 3 or not all(math.isfinite(part) and part >= 0 for part in parts)
                or (len(parts) > 1 and (any(not part.is_integer() for part in parts[:-1])
                    or any(part >= 60 for part in parts[1:])))):
            raise ValueError
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected a timestamp such as 24.5 or 01:24.5") from exc
    return sum(part * 60 ** i for i, part in enumerate(reversed(parts)))


def crop_box(value: str) -> tuple[float, float, float, float]:
    try:
        x, y, width, height = (float(part) for part in value.split(","))
        if not (0 <= x < 1 and 0 <= y < 1 and 0 < width <= 1 - x and 0 < height <= 1 - y):
            raise ValueError
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected normalized x,y,width,height inside the frame") from exc
    return x, y, width, height


def extract_frame(index_path: Path, at: float, box, out: Path) -> dict:
    path, index = load_index(index_path)
    media = (path.parent / index["video"]).resolve()
    if not media.is_file():
        raise SystemExit(f"Indexed media is missing: {media}")
    if not 0 <= at < index["facts"]["duration_s"]:
        raise SystemExit("Frame timestamp must fall within the indexed video")
    if out.suffix.lower() != ".png" or out.exists() or out.is_symlink():
        raise SystemExit("Choose a new PNG output path")
    filters = f"setpts=PTS-STARTPTS,select='gte(t,{at:.9f})'"
    if box is not None:
        x, y, width, height = box
        filters += f",crop=w=max(1\\,iw*{width}):h=max(1\\,ih*{height}):x=iw*{x}:y=ih*{y}:exact=1"
    out.parent.mkdir(parents=True, exist_ok=True)
    log = run_ffmpeg(
        "-n", "-loglevel", "info", "-i", str(media), "-map", "0:v:0", "-an",
        "-vf", filters + ",showinfo", "-frames:v", "1", "-c:v", "png", "-threads", "1",
        "-update", "1", "-atomic_writing", "1", str(out),
    )
    times = evidence.frame_times(log, 0.0, str(media))
    if not times or not out.is_file():
        raise SystemExit("No decoded frame at or after the requested time")
    return {"image": str(out.resolve()), "requested_s": at, "frame_s": times[0], "box": box}


def positive_interval(value: str) -> float:
    seconds = float(value)
    if not math.isfinite(seconds) or seconds <= 0:
        raise argparse.ArgumentTypeError("sampling interval must be finite and positive")
    return seconds


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("index", help="create a reusable video index")
    build.add_argument("source", help="local video file or a URL supported by yt-dlp")
    build.add_argument("--out", type=Path, required=True, help="new directory for the index and images")
    build.add_argument("--sample-every", type=positive_interval, default=1.0,
                       help="minimum seconds between sampled frames (default: 1)")
    build.add_argument("--no-transcript", action="store_true")
    build.add_argument("--language", help="speech language for faster-whisper")
    build.add_argument("--whisper-model", default="small")
    build.add_argument("--no-ocr", action="store_true")
    build.add_argument("--ocr-language", default="eng", help="installed Tesseract language(s), e.g. eng+fra")
    find = commands.add_parser("search", help="search indexed speech and visible text")
    find.add_argument("query", help="literal phrase, ignoring case and punctuation")
    find.add_argument("indexes", type=Path, nargs="+", help="one or more index directories or index.json files")
    find.add_argument("--track", choices=("all", "said", "shown"), default="all")
    view = commands.add_parser("view", help="write a searchable HTML player for an indexed video")
    view.add_argument("index", type=Path)
    compare = commands.add_parser("compare", help="write a side-by-side playback and metrics report")
    compare.add_argument("reference", type=Path)
    compare.add_argument("candidate", type=Path)
    for report in (view, compare):
        report.add_argument("--out", type=Path, required=True, help="new HTML report")
        report.add_argument("--detect-dissolves", action="store_true",
                            help="include additional dissolve calls that need visual review")
    frame = commands.add_parser("frame", help="extract a timestamped, source-resolution frame or crop")
    frame.add_argument("index", type=Path)
    frame.add_argument("--at", type=timestamp, required=True)
    frame.add_argument("--box", type=crop_box, metavar="X,Y,W,H")
    frame.add_argument("--out", type=Path, required=True, help="new PNG output")
    args = parser.parse_args()
    if args.command == "index":
        result = index_video(args)
    elif args.command == "search":
        result = search(args.indexes, args.query, args.track)
    elif args.command == "frame":
        result = extract_frame(args.index, args.at, args.box, args.out)
    else:
        from video_report import render_report

        indexes = (args.index,) if args.command == "view" else (args.reference, args.candidate)
        result = render_report([load_index(path) for path in indexes], args.out,
                               detect_dissolves=args.detect_dissolves)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
