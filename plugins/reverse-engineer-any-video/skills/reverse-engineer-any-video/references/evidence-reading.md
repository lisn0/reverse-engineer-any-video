# Reading the evidence

What each file and field from `evidence.py` means, how far it can be trusted, and how to
correct it from frames.

## Contents

- Output files and when they exist
- Shot events and the shot count
- What the shot detector gets wrong
- Adjudicating a boundary
- Cut cross-check
- Pans and zooms
- Audio readings
- Captions, beats and coverage
- Long videos

## Output files and when they exist

| File | Written when | Holds |
|---|---|---|
| `manifest.json` | always | source facts (size, fps, duration, `picture_offset_s`, bytes, kbps, has_audio), change counts, every sheet with `tile_times_s` |
| `changes.json` | always | `events`, `uncertain_shots`, `motion_spans`, `picture_motion`, optional `native_cut_candidates_s` |
| `sheets/*.jpg` | always | overview, hook, middle, ending, one tile per change |
| `transcript.txt`, `words.json` | audio present and transcripts on | timed words from faster-whisper |
| `audio.json` | same as transcripts | sound measures and readings that use the word timings |
| `review.json` | `--review-at` only | review windows instead of the full run |

`--out` must be a new directory; the script refuses to write into an existing one.
`--no-transcript` also drops `audio.json`, because the readings need word timings. A
missing transcript means no transcript, not no speech.

## Shot events and the shot count

`events[].kind` is one of:

- `shot`: the picture was replaced. `cue: cut` is a one-frame structure change after
  which the old view does not come back. `cue: gradual` is a dissolve or fade: the views
  half a second either side differ. Hard cuts carry the first frame of the new shot.
- `element`: something was added to a picture that stays.
- `text`: a caption or label changed.
- `small`: a small pop-in.

`uncertain_shots` holds candidates that failed confirmation, each with a `why` (for
example "the view half a second either side still matches"). Both lists appear on the
change sheets.

`change_counts.estimated_shots` is shots plus one;
`estimated_shots_if_elements_are_cuts` is the upper figure. The working count starts
from the first, adds uncertain candidates the frames confirm, and removes events the
frames reject. The final count states its rule: whether an end card, a title card or a
full-screen effect counts as a shot. Two honest readers can disagree on that rule, and a
recipe's segment count is not the same thing as visible cuts (one recipe segment can hold
several cuts from its source footage).

`structure_change` (one minus brightness-normalised correlation), `view_kept` (how well
the half second after matches the half second before) and `side_steadiness` are the
measurements behind each decision.

## What the shot detector gets wrong

Each item is a measured failure on benchmark footage. When the video has one of these,
the events nearby get a `--review-at` check.

| Situation | Typical error | What the frames show |
|---|---|---|
| Flash, stage light, exposure jump | Usually moved to `uncertain_shots`; a strong one can still count | The same view returns after the flash |
| Large subject changing shape fast (wings, a turn) | False shot | Background and fixed objects stay put |
| Foreground passing a fixed camera | False gradual shot | The edges of the frame keep the same scene |
| Occluder blocking a light source for a frame | False cut | Same place before and after; a real cut may follow shortly |
| Slow fade to black that keeps the picture's shape | Missed boundary | Brightness falls while structure stays |
| Short dissolve between two moving shots | Lands in `uncertain_shots` | Both pictures visible together for a few frames |
| Captions changing over moving props | Extra shots | Layout of the picture holds; only text and props move |
| Fast pan or whip | Occasional extra shot; slow pans go to `picture_motion` | Features slide together |

A real boundary can also be missing from a human reference. On one held-out set, one of
five "false positives" was a real cut the published annotation did not mark. When the
tool and a reference disagree, the frames decide.

## Adjudicating a boundary

```bash
python3 scripts/evidence.py clip.mp4 --review-at 17.5 --review-at 21.5 --out runs/review
```

Up to eight times per run, each inside the picture duration. The same local file is used
for every measurement, so times refer to the same frames; a re-download or re-encode can
shift them. `review.json` lists each tile's picture-relative time in row-major order.

| Pattern in the review sheet | Verdict |
|---|---|
| View changes in one frame and never returns | Cut |
| Picture washes out or darkens, then the same view returns | Flash or dip, not a shot |
| Both pictures visible at once for several frames, then the new one holds | Dissolve |
| Picture darkens to black, new picture rises | Fade through black: one boundary, gradual |
| Flare or flash immediately followed by a new view | Flash next to a real cut: count the cut |
| Same background, subject moves or changes shape | Motion inside one shot |

The verdict, the tile times it rests on and the counting rule go into the teardown's
shot table.

## Cut cross-check

`--crosscheck-cuts` adds `native_cut_candidates_s`: strong abrupt changes from FFmpeg's
scene score at source frame rate. It is precise but misses many cuts and does not see
dissolves; it also fires on flashes. It is a list of moments worth reviewing, not a
second count. A disagreement between it, `events` and `uncertain_shots` is a reason to
run `--review-at`, not a reason to average the counts.

## Pans and zooms

`picture_motion` holds one-second windows where one transform explains the motion across
at least three quadrants:

- `kind: pan` with `dx_sample_px`, `dy_sample_px` in 90×160 sample pixels (positive is
  right and down).
- `kind: zoom` with `scale` (above 1 is zooming in).

The check on frames: two or more stationary features at both times. Sliding together at
fixed spacing is a pan. Spacing growing or shrinking around the centre is a zoom.
Features moving independently suggest layer motion or a real camera with parallax. An
empty list leaves the motion unresolved, not static. A fit can come from one large
layer that fills the picture, so it describes pixels, not how the effect was made.
Agents without this field called a slow pan a zoom on a benchmark clip; the field and a
two-feature check fixed it.

Limits: low texture, motion under one sample pixel or over eight per second, off-centre
or combined motion, parallax.

## Audio readings

`audio.json` measures the sound between words, with no model:

| Field | Meaning |
|---|---|
| `loud_db` | 90th percentile level |
| `gap_level_db` | median level between words |
| `gap_silent_share` | share of gap time below -60 dB (digital silence) |
| `gap_noise_likeness` | 0 tonal (music) to 1 flat hiss (room) |
| `bed_margin_db` | how far the loud parts sit above the gaps |
| `beat_strength`, `beat_bpm` | regular pulse |
| `speech_share`, `words` | how much of the time is speech |
| `music`, `narrator`, `voice_source` | cautious readings; `unclear` is a valid answer |

- `music: unclear` is reported as unknown. A quiet bed under a voice usually reads
  unclear.
- `voice_source: generated_or_gated` only means gaps at digital silence. Text to speech
  does that, and so do an edited human recording, a noise gate and inserted clips. It
  is weighed with the transcript and the pacing. Without it, human versus generated
  stays unknown.
- Voice type cannot be established while music is unclear.
- Sung lyrics in a transcript mean music, not a narrator.
- The scripts do not measure integrated loudness (LUFS) or pitch. When those matter
  (usually in a rebuild), the commands are in
  [rebuild-and-review.md](rebuild-and-review.md#audio-measures).

## Captions, beats and coverage

- A caption follows speech or lyrics. Titles, labels and dashboards are not captions.
- A beat is a change of idea, even inside one continuous shot: on-screen headers, new
  overlays and topic shifts in the transcript mark it.
- For a single continuous shot, near-zero changes are the finding; the study moves to
  what changes inside the frame.
- The overview samples every few seconds and can miss images shorter than its sampling
  interval. The change sheets and dense windows cover that gap; a claim about the whole
  video says which sheets it rests on.
- A very small file for its length (low `kbps`) fits little motion. It does not prove
  stills.

## Long videos

The default sheets cover the hook, middle and ending densely. `--review-at` covers only
about half a second either side of a time, so dense coverage inside each chapter comes
from clips cut from the same file and run through `evidence.py` separately:

```bash
ffmpeg -ss 600 -t 90 -i video.mp4 -c copy chapter-03.mp4
python3 scripts/evidence.py chapter-03.mp4 --out runs/<name>/chapter-03
```

Clip times are offsets from the cut point. A finding from the first minute is labelled
as such until other chapters are checked.
