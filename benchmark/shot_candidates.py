#!/usr/bin/env python3
"""Print every shot decision with its measurements, labelled against a reference.

    python3 benchmark/shot_candidates.py NAME=VIDEO[:BOUNDARIES.json] ...

Use it on development footage to see why a candidate was counted or left for review.
Labels: "cut" or "gradual" when the time matches a reference boundary, "none" when it
matches nothing, "?" without a reference.
"""
import json
import runpy
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = (ROOT / "plugins/reverse-engineer-any-video/skills"
          / "reverse-engineer-any-video/scripts/evidence.py")


def label(t: float, references: list[tuple[float, float]] | None, tolerance: float = 0.15) -> str:
    if references is None:
        return "?"
    for start, end in references:
        if start == end and abs(t - start) <= tolerance:
            return "cut"
        if start != end and start <= t <= end:
            return "gradual"
    return "none"


def main() -> None:
    evidence = runpy.run_path(str(SCRIPT))
    for item in sys.argv[1:]:
        name, rest = item.split("=", 1)
        video, _, reference = rest.partition(":")
        references = None
        if reference:
            references = [tuple(v) if isinstance(v, list) else (v, v)
                          for v in json.loads(Path(reference).read_text())]
        facts = evidence["probe"](Path(video))
        with tempfile.TemporaryDirectory() as work:
            changes = evidence["find_changes"](Path(video), facts["duration_s"], Path(work))
        decided = [{"decision": "shot", **e} for e in changes["events"] if e["kind"] == "shot"]
        decided += [{"decision": "review", **e} for e in changes["uncertain_shots"]]
        for row in sorted(decided, key=lambda e: e["t"]):
            print(json.dumps({"case": name, "label": label(row["t"], references), **row}))
        for start, end in references or []:
            hits = [e["t"] for e in changes["events"]
                    if e["kind"] == "shot" and start - 0.15 <= e["t"] <= end + 0.15]
            if not hits:
                print(json.dumps({"case": name, "missed": [start, end]}))
        sys.stdout.flush()


if __name__ == "__main__":
    main()
