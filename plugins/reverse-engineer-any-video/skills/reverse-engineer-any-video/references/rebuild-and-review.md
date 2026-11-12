# Rebuild test and blind review

A theory of how a video was made is tested by making a piece of it, then checked by
readers who never saw the theory.

## Contents

- Writing the recipe
- Choosing the riskiest step
- Building the test
- Comparing with the original
- Audio measures
- What a rebuild proves
- Blind review

## Writing the recipe

The shortest list of steps that should reproduce the look, written so a renderer or a
person could follow it without the teardown. The values below are invented and only show
the shape:

```json
{
  "canvas": {"width": 1920, "height": 1080, "fps": 25, "duration_s": 95.0},
  "assets": [{"id": "product", "kind": "photo", "reused": 4}],
  "shots": [{"start": 0.0, "end": 3.2, "layers": ["product"], "motion": "slow push-in", "transition_in": "dissolve"}],
  "captions": {"source": "speech recognition", "max_chars": 32, "position": "bottom third", "animation": "none", "case": "sentence"},
  "sound": {"voice": "recorded", "music": "lowered under the voice", "effects": ["whoosh on transitions"]},
  "unknown": ["editor", "music source"]
}
```

Canvas size, frame rate and duration are measured from `manifest.json`, never assumed.
Shot times come from the confirmed shot table, caption timing from `words.json`, not
from eyeballing the sheets.

## Choosing the riskiest step

The step whose failure would sink the theory. Invented examples: "the camera move can be
faked with a crop on a still", "an off-the-shelf voice reaches the same delivery". The
test targets that step first and stays as small as possible: one shot, ten seconds, a
handful of assets.

## Building the test

- **Recurring subjects:** when the same subject must look the same across shots, that
  consistency is tested first, and the generation or capture settings that worked (seed,
  reference image and its weight, model version) are recorded so a take can be repeated.
- **Preprocessing** the look depends on (masking, colour grading, upscaling) is its own
  recipe step, with the tool and settings noted.
- **Voice timing:** generated speech can carry silence padding at the start and end.
  Padding is trimmed before any fit-to-slot speed change, so the speed change applies to
  the words only.
- **Pace as one setting:** a single time-stretch factor applied to picture and voice
  together makes "slower" or "calmer" a one-line change.
- **Time and effort are evidence.** A rebuild that takes many hours for seconds of video
  suggests the theory is missing an automation step that the original has.

## Comparing with the original

- Paired frames at matching moments, about every 3 seconds across the whole clip, original
  on the left and rebuild on the right.
- A table of what matched, what did not, and what each mismatch says about the theory.
- A person's verdict on the rebuild (an invented example: "sounds flat") is a symptom;
  measurements find the cause.

## Audio measures

The bundled `audio.json` covers levels in gaps and beat strength. A rebuild comparison
also needs integrated loudness and silence, which FFmpeg measures:

```bash
ffmpeg -nostats -i original.mp4 -af ebur128 -f null -
ffmpeg -nostats -i original.mp4 -af silencedetect=noise=-50dB:d=0.15 -f null -
```

| Measure | What it compares |
|---|---|
| Integrated loudness (LUFS) | Overall level of original and rebuild |
| Silent gaps, count and total | Whether one has silence where the other has sound |
| Quietest 10% of levels (noise floor) | Digital silence versus a constant bed or room tone |
| Median voice pitch, from any pitch tracker | Voice register, to narrow a voice choice |

The same measures on both files turn a vague verdict into a specific difference.

## What a rebuild proves

- A rebuild that reaches the look proves the method **can** make it. It does not prove
  the creator used that method; the layout tool, editor or pipeline stays open unless a
  fingerprint pins it.
- A rebuild that cannot reach the look disproves the theory as written. The teardown says
  what changed in the theory and why.
- An untested recipe is labelled untested.

## Blind review

Fresh agents with no memory of the investigation. They never receive the theory, the
title, a summary or the transcript.

| Role | Gets | Answers |
|---|---|---|
| Blind describer | Frames and sheet times only | Copies captions exactly, says what moves and what repeats, guesses the method |
| Claim auditor | One claim plus the frames it cites | measured, seen, inferred or unsupported |
| Blind comparer | Original and rebuild frames | What differs |
| Skeptic | Frames and the claim list | A simpler explanation (one preset, one template) |

Where a reviewer disagrees, the claim is marked weak, not argued away. Two reviewers
disagreeing with each other lowers confidence too. Reviewers can invent details just like
any vision reader, so a reviewer's new detail is checked on the frame before it enters
the teardown.

A reviewer handed a tool's count tends to repeat it. When the question is the count
itself, the reviewer gets frames without the count.
