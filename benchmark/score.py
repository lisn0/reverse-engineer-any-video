#!/usr/bin/env python3
"""Score an answers file against a known-truth case.

    python3 benchmark/score.py benchmark/truth/case-a.json answers.json

Answers map each question id to a value or "unknown". A wrong answer is worse than
"unknown", because the point of the method is not to claim what it can't show.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def channels(colour: str) -> list[int]:
    value = colour.strip().lstrip("#")
    return [int(value[i:i + 2], 16) for i in (0, 2, 4)]


def correct(answer: object, truth: object) -> bool:
    if isinstance(truth, dict) and "hex" in truth:
        return all(abs(a - b) <= truth["tolerance"]
                   for a, b in zip(channels(str(answer)), channels(truth["hex"])))
    if isinstance(truth, dict):
        return abs(float(answer) - truth["value"]) <= truth["tolerance"]
    if isinstance(truth, str):
        return str(answer).strip().lower() == truth
    return answer == truth


def main() -> int:
    truth = json.loads(Path(sys.argv[1]).read_text())
    answers = json.loads(Path(sys.argv[2]).read_text())
    missing = sorted(set(truth) - set(answers))
    if missing:
        raise SystemExit(f"answers missing: {missing}")
    results = {"right": [], "wrong": [], "unknown": []}
    for key, expected in truth.items():
        answer = answers[key]
        bucket = "unknown" if answer == "unknown" else "right" if correct(answer, expected) else "wrong"
        results[bucket].append(key)
    answered = len(results["right"]) + len(results["wrong"])
    print(f"right {len(results['right'])}  wrong {len(results['wrong'])}  "
          f"unknown {len(results['unknown'])}  of {len(truth)}")
    print(f"accuracy when answering: {len(results['right']) / answered:.0%}" if answered else "no answers")
    for bucket in ("wrong", "unknown"):
        for key in results[bucket]:
            print(f"{bucket}: {key}: answered {answers[key]!r}, truth {truth[key]!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
