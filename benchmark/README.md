# Benchmark

Tests the method on videos whose true construction is known, because the code that made
them is available. A fresh agent gets the skill and the evidence, never the truth files.

```bash
python3 benchmark/score.py benchmark/truth/case-a.json answers.json
```

A wrong answer is reported separately from "unknown", because claiming what the evidence
can't show is the failure this method exists to prevent.

## Results

| Date | Case | Right | Wrong | Unknown | Notes |
|---|---|---|---|---|---|
| 2026-11-01 | case-a run 1 | 14 | 1 | 3 | Coded explainer, easy |
| 2026-11-01 | case-a run 2 | 16 | 0 | 2 | Same video, after the zoom fix |
| 2026-11-01 | case-b, two runs | 7 | 1 | 2 | Code-rendered map |
| 2026-11-01 | case-c, two runs | 6 | 1 | 7 | Real-footage music video edit |
| 2026-11-01 | case-d, two runs | 2 | 3 | 3 | Chess meme |
| 2026-11-01 | case-e, two runs | 0 | 2 | 6 | Gameplay background with narration |
| 2026-11-01 | case-f, two runs | 13 | 0 | 9 | Code-made test video, after the skill fixes |

**Hard cases, b to e, as first scored:** 15 right, 7 wrong, 18 unknown of 40, so 68% of
answers given were right.

**With two flawed questions removed:** 15 right, 4 wrong, 17 unknown of 36, or 79%. Both
were the answer key's fault. Case-e's Minecraft background is both stock footage and a game
render. Case-d has no narrator, but its reaction clips contain speech. The first figure
stands as the headline, because these were found after the agents ran.

Where the unknowns came from: 10 of 18 are voice or music, and 6 of 18 are automation.

**Case-f, a code-made test video:** both agents answered with nothing wrong. It ran after
the skill and question fixes, so its score isn't directly comparable with b to e, and b to e
haven't been rerun. It was built by the skill's author, and its answer key is private. All
nine unknowns are shots, font, music, voice or automation, so shot counting in composited
videos was a clear gap. Both agents chose caution: neither gave a shot count.

- **Case-a's scores don't compare with b to e.** Its questions include plain file facts.
- **The two runs disagreed on 4 scored answers** (case-b captions and voice, case-c
  transitions, case-d voice), so one run isn't reliable on those points.
- **A handful of videos and one agent model** can't support a general accuracy claim.

## Fresh test, 2026-11-01

This is the first test on videos that shaped nothing. Answer keys were committed first
(commit eaa69b6). Only two tool bugs were fixed after that: picture length, and the
missing-file message. Thresholds didn't change, and no skill edits were made.

| Video | Method | Right | Wrong | Unknown |
|---|---|---|---|---|
| fresh-g, two runs | Music video montage from a script | 9 | 3 | 2 |
| fresh-h, two runs | Code-drawn math animation | 10 | 0 | 0 |
| fresh-i, two runs | Godot game capture | 8 | 2 | 0 |
| **Total** | | **27** | **5** | **2** |

**As scored, 27 of 32 answers given were right (84%), and 34 questions produced 2 unknowns.**
This is a lower-bound headline: keys stay unchanged.

Four of the five wrong answers are shot counts where both agents agreed against the key.
These were the suspected causes at the time. See the [follow-up frame audit](#follow-up-frame-audit-2026-11-09).

- fresh-g: the key counts 10 recipe segments, but the source footage has cuts inside them.
  17 changes replace most of the picture.
- fresh-i: the key says 1, but a change at 34.2 s replaces 82% of the picture. The agents
  called it an end card, which the game code reviewed for the key didn't cover.

If those stand, it would be 31 of 32. The other wrong answer is real: fresh-g transitions.

Limits: three videos, one agent model, and all three are code-made, so "code" is an easy
guess here. There's no fresh video by a human editor. Automation was unknown on the music
video.

**AI-image addition (fresh-j):** `make_ai_case.py` built a 43 s video from five recorded AI
images, with a sideways pan, crossfades, a new voice and a quiet real song. Key committed
first. Two blind runs: 9 right, 2 wrong, 7 unknown of 18.

- Both found AI images, bottom captions, 5 shots (correcting the tool's 4) and 12 captions.
- Both wrong answers are the same: they called the pan a slow zoom. The skill's zoom test
  doesn't cover pans.
- Unknowns: music twice, voice twice, automation twice, transitions once. The quiet bed read
  "unclear", so the agents correctly said unknown. Voice can't be established while music
  is unclear.

**All fresh videos:** 36 right, 7 wrong, 9 unknown of 52, or 84% of answers given. The
fresh-j video is built by the same author as the tool, so it isn't independent either.

URL download has been tested on YouTube and TikTok.

## Audio

`evidence.py` writes `audio.json`, using gap level, gap tone and beat strength with no model.
`python3 benchmark/eval_audio.py NAME=VIDEO=MUSIC=VOICE ...` prints readings beside truth.

| Test | Files | Right | Wrong | Unclear |
|---|---|---|---|---|
| Six tuning videos, music and voice readings | see below | used to set the rules | | |
| Held-out: real song mixed under three voices at two levels, music reading | 6 | 2 | 0 | 4 |
| Human speech with no music, music reading | 1 | 0 | 0 | 1 |

The rule set failed its first test: a generated voice over a quiet synthetic bed read as no
music and a recorded voice. That led to the tone test. The test then called a human speech
music, so that overlap now reads "unclear". Those files aren't held out. The song mixes are,
for the music reading, with rules frozen. One later change lets a voice far above the bed
count as a narrator, which wasn't part of that frozen test.

Limits: a quiet bed under a voice usually reads "unclear". The method can't name a voice.
`generated_or_gated` only means digital silence between words, which an edited human
recording or inserted clips can also produce (case-d's clips read this way). No human
narrator recorded with digital silence has been tested, so the false-alarm rate is unknown.

Blind agents with `audio.json`, after the skill fixes:

| Case | Before | After |
|---|---|---|
| c, music video edit | 3 right, 0-1 wrong, 3-4 unknown | 6 right, 0 wrong, 1 unknown |
| e, Reddit story | 0 right, 1 wrong, 3 unknown | 2 right, 1 wrong, 1 unknown |

One agent per case. Both videos were audio tuning videos, so these gains overstate
performance on new videos. Case e's one wrong answer is the flawed stock-or-game question.

## Shot estimates

`python3 benchmark/eval_shots.py NAME=VIDEO:SHOTS ...` compares `evidence.py` with known
shot counts.

| Case | Truth | Estimate | Note |
|---|---|---|---|
| Held-out zoom, seed set 100 | 12 | 12 | All cuts within 0.1 s, none false |
| Held-out zoom, seed set 100 | 16 | 16 | All cuts within 0.1 s, none false |
| Held-out zoom, seed set 100 | 10 | 10 | All cuts within 0.1 s, none false |
| a, real zoom with captions | 20 | 26 | Was 65 raw changes, then 34 |
| c, real footage | 19 | 16 | |
| e, one continuous clip | 1 | 1 | |
| f, code-made test video | 23 | 20 | All 19 cuts are real; 3 added-effect scenes are labelled elements |

**Only the three seed-100 videos are held out.** `make_zoom_cases.py` generates them, and
thresholds were frozen first. The first three generated videos failed at 40, 44 and 37
shots, which led to the final design, so they aren't counted. Cases a, c, e and f all
influenced tuning.

The held-out videos are synthetic: centre zoom only, DejaVu captions and a folder of
generated still images. They don't cover pans, real slideshows or AI-generated motion, so 35 of 35
applies to that kind of video only. Case a remains the honest real-video figure: much
better, still 6 over. Its bottom captions change over moving props.

A blind agent given earlier evidence for case f answered 23 shots, where both earlier
agents said unknown. It used the tool's estimate and checked it against the sheets, so a
wrong estimate could mislead an agent the same way. That evidence came from the previous
version of the detector.

### Follow-up frame audit, 2026-11-09

The original answer keys and scores above are frozen. This audit used the same source
files as the original runs and checked decoder timestamps around disputed events.

| Video | Frame evidence | Audit result |
|---|---|---|
| fresh-g | The performer turns in the same framing around 5.3 s as the stage lights flash. Cuts replace the picture near 7.0 and 21.5 s. An independent frame pass also found a cut around 17.5 s. | The retained run counted the flash and recorded no event near 17.5 or 21.5 s. The full shot count remains unresolved. |
| fresh-i | One game layout persists in the sampled overview. The game darkens through a fade and the full-screen winner card is visible at 34.433 s. | Two picture states when the end card counts as a shot. The detector's 34.2 s event falls during the fade. |

### Independent BBC boundary benchmark

The test uses the first 180 seconds of *Mountains* and *Caves*, from Baraldi,
Grana and Cucchiara's manually annotated BBC Planet Earth dataset. The excerpts and
reference were chosen before scoring. The detector sees only the video, while the
evaluator receives the published shot ranges. [Dataset](https://zenodo.org/records/14865504) · [Paper](https://arxiv.org/abs/1510.08893)

```bash
bash benchmark/run_bbc_sample.sh /tmp/bbc-boundary-sample
```

The runner losslessly encodes each excerpt and checks all 4,500 presentation times
against the expected 25 fps sequence measured from the first decoded picture.
Adjacent shot ranges give a point at the first frame of the new shot. Gaps become
reference intervals. Each reference can match one
prediction, within ±0.15 seconds for cuts or inside the reference interval.
The evaluator reports precision, recall, F1 and unmatched times for the current
`shot` reading and for the broader `shot` plus `element` reading. It also accepts a
list of reference times and intervals in `NAME=VIDEO:BOUNDARIES.json` form. This scores
event detection. Gradual interval length and transition type are outside this test.
[NIST shot boundary measures](https://www-nlpir.nist.gov/projects/t2002v/sbmeasures.html)

| Excerpt | Reading | Matched | False positives | Missed | F1 |
|---|---|---:|---:|---:|---:|
| Mountains | Shot only | 17 | 72 | 0 | 32.1% |
| Caves | Shot only | 16 | 4 | 1 | 86.5% |
| Both | Shot only | 33 | 76 | 1 | 46.2% |
| Both | Shot or element | 33 | 104 | 1 | 38.6% |

Shot-only recall was 97.1% and precision was 30.3% across both excerpts. Counting
elements added 28 false positives and recovered zero boundaries. The miss in *Caves*
was the 25.40–28.72 s interval. The closest shot prediction was at 25.20 s.
In *Mountains*, false positives cluster inside single annotated shots, including
47.6–57.8 s and 93.6–104.8 s. The 89 shot predictions imply 90 shots where the
reference has 18. In *Caves*, the count was 21 versus 18.

This compares two readings of the current detector on six minutes of broadcast
footage. The detector samples at 10 Hz. These figures cover neither frame-exact
timing nor vertical short-form accuracy. The benchmark evaluates visible boundaries
and does not establish the editing workflow or motion type.

### Shot candidates during sustained activity

The baseline (`868afdc`) proposes shots from spikes in the fraction of changed pixels.
To distinguish an isolated spike from repeated motion, the new check uses mean
absolute grayscale difference over the same samples. For each proposed shot, it
compares the boundary pair with the strongest of the three neighboring pairs on
each side. A boundary whose mean change is below 1.4 times both peaks goes into
`uncertain_shots`. The timeline sheets still show these candidates so the reviewer
can resolve them. The check uses temporal context like a rolling threshold.
[PySceneDetect adaptive detector](https://www.scenedetect.com/docs/latest/api/detectors.html)

Development used the published *Mountains* and *Caves* excerpts above. Pooled false
positives fell from 76 to 7 with the same 33 matches. The three synthetic zoom videos
retained all 35 cuts with zero false positives. The fresh-i end-card event stayed at
34.2 s. The detector was frozen before scoring the first 180 seconds of BBC episodes
*From Pole to Pole*, *Jungles* and *Deserts*.

```bash
bash benchmark/run_bbc_sample.sh /tmp/bbc-holdout --baseline 868afdc \
  01_From_Pole_to_Pole 05_Jungles 11_Deserts
```

| Holdout excerpt | Baseline matches | New matches | Baseline false positives | New false positives |
|---|---:|---:|---:|---:|
| From Pole to Pole | 19 | 19 | 46 | 14 |
| Jungles | 18 | 18 | 47 | 22 |
| Deserts | 16 | 16 | 38 | 16 |
| **Total** | **53** | **53** | **131** | **52** |

The frozen candidate reduced holdout false positives by 60.3%, above the 25% target,
and kept all 53 matched references, above the 95% target. Pooled F1 rose from 44.7%
to 67.1%. The normal evidence command kept all 17 uncertain candidates from a
15-second motion excerpt on its review sheets, along with two counted shot events.

The vertical spot checks expose the tradeoff. Fresh-j still gave 31 pan windows and
zero zoom windows. The filter moved its visible 29.6 s dissolve into `uncertain_shots`.
In fresh-g, five candidates became uncertain and the known stage-light false positive
at 5.3 s stayed counted. Fast cuts between two active shots and short dissolves can
land in the uncertain list. The BBC result covers nine minutes of documentary footage.

### Paired comparison with Dissect

Both tools measured identical inputs. We used the three vertical cases with known
disputed moments and all five BBC excerpts above. Dissect ran its visual timeline
at the pinned source revision, with its default shot threshold and depth. This
comparison covers visual output. [Dissect 2.0.0 source](https://github.com/0xpratzyy/dissect/tree/35c1098c0f9d23de9529f471a65fe51bfc90046a)

```bash
DISSECT_PYTHON=python3 bash bench/run_dissect.sh /tmp/dissect-run "$VIDEO"
python3 benchmark/eval_shots.py --dissect-dir /tmp/dissect-run --crosscheck-cuts \
  "case=$VIDEO:$BOUNDARIES"
```

The evaluator compares shot starts with the same one-to-one scoring rule for both
tools. It also reports a second Dissect score that includes events labeled `cut`
inside its shots. The first shot of each clip starts at the beginning and supplies
no boundary to score.

| Reading | BBC matches of 87 | False positives | Missed | F1 |
|---|---:|---:|---:|---:|
| Our shot count | 86 | 59 | 1 | 74.1% |
| Dissect shot starts | 69 | 3 | 18 | 86.8% |
| Dissect starts and internal cuts | 81 | 4 | 6 | 94.2% |
| Our native-frame cut cue | 56 | 0 | 31 | 78.3% |
| Our shot count, confirmed on source frames (2026-11-12, below) | 85 | 5 | 2 | 96.0% |

The three held-out BBC excerpts account for 53 of the 87 reference events. On those
excerpts, our detector matched 53 with 52 false positives. Dissect's shot starts
matched 45 with three false positives. Including internal cuts raised that to 51
matches with four false positives. The native cue matched 33 with zero false positives.
These numbers measure cut candidates on BBC excerpts. The frame checks below cover
the separate question of what actually happened at individual vertical-video events.

| Disagreement | Our automatic reading | Dissect visual timeline | Frame inspection |
|---|---|---|---|
| fresh-g, around 5.3 s | Counted shot | Shot starts at 5.333 s, labeled flash | The stage briefly washes out while the same view continues. |
| fresh-g, around 17.5 s | No shot event | Boundary at 17.45 s, labeled flash | A lighting flare precedes a real cut between the sampled 17.483 and 17.517 s frames. |
| fresh-g, around 21.5 s | No shot event | Cut at 21.5 s | The stage view switches to a tilted close-up between the sampled 21.483 and 21.517 s frames. |
| fresh-j, around 29.6 s | Uncertain candidate | No boundary or internal change | Both images overlap around 29.47–29.53 s before the incoming image takes over. |
| fresh-i, end card | Shot event at 34.2 s | Internal cut at 34.433 s | The game image darkens, then the winner card takes over. |

The evidence CLI now has `--review-at SECONDS` for disagreements. Each request
produces sheets covering up to half a second on either side, plus exact tile
timestamps in `review.json`. We checked the tile timestamps against decoder output
on the three vertical inputs and on a variable-frame-rate control with a delayed
picture start. The comparison uses Dissect as a second opinion. These sheets let
the reviewer adjudicate its labels and ours from the frames.

`--crosscheck-cuts` adds a separate FFmpeg scene-score pass at source cadence and
reports `native_cut_candidates_s`. The cue found the 21.5 s cut and also flagged
the 5.333 s lighting flash. It gave no candidates for the fresh-j montage or the
fresh-i fade. At the time, the automatic shot count used the original detector. Use the separate
cue to choose which moments to review. [FFmpeg select filter](https://ffmpeg.org/ffmpeg-filters.html#select_002c-aselect)

### Shot confirmation on source frames, 2026-11-12

Why Dissect was more precise, from its source at the pinned revision: its shot list
comes from FFmpeg's scene score at the source frame rate, which already discounts
change that continues from the previous frame. Its timeline pass then looks for
hidden cuts with a brightness- and contrast-normalised correlation between
neighbouring frames, which a flash or exposure change barely moves. A candidate must
stand three times above every other change within ten frames. It is then rejected
as a flash, a dip or a reframe, or kept only when few picture blocks survive. Our
detector compared 10 fps samples by the share of pixels that changed, so lighting,
washouts and fast motion inside one view looked like new pictures.

`evidence.py` now decodes every source frame at 96 pixels on the long side and keeps
the 10 fps changes as candidates. Nothing from Dissect runs or is copied.

- **Hard cut:** one frame's structure change (1 − correlation after removing
  brightness and contrast) is at least 0.15 and twice every other change within
  0.4 s, ignoring the frames next to it. The best shift-tolerant match between the
  half second before and the half second after must stay below 0.85. A flash
  passes the first test and fails the second because the old view returns.
- **Gradual change:** a sampled candidate with no hard cut within 1 s must have
  views half a second either side that match below 0.55, and below 0.7 times how
  well each side matches itself over its own half second. Continuous motion
  changes each side as much as the gap, so it stays in review.
- Sampled candidates within 0.25 s of a hard cut take the cut's frame time.
  Everything rejected goes to `uncertain_shots` with a `why`.

Thresholds were set on *Mountains*, *Caves* and the vertical dev clips only, from one
measurement pass and one check. The three holdout excerpts were then scored once with
the settings frozen at `225f65d`, in the same run as the original detector and the
stored Dissect timelines.

| Reading | Dev matches of 34 | FP | Missed | F1 | Holdout matches of 53 | FP | Missed | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Original detector (`5af3a19`) | 33 | 7 | 1 | 89.2% | 53 | 52 | 0 | 67.1% |
| Confirmed on source frames | 33 | 0 | 1 | 98.5% | 52 | 5 | 1 | 94.5% |
| Dissect shot starts | 24 | 0 | 10 | 82.8% | 45 | 3 | 8 | 89.1% |
| Dissect starts and internal cuts | 30 | 0 | 4 | 93.8% | 51 | 4 | 2 | 94.4% |
| FFmpeg scene cue | 23 | 0 | 11 | 80.7% | 33 | 0 | 20 | 76.7% |

Across all five excerpts the confirmed reading matched 85 of 87 with 5 false
positives, an F1 of 96.0%. On the holdout it matches Dissect with internal cuts,
within one event, rather than clearly beating it. The misses are a slow fade to
black in *Mountains* (119.88–122.56 s), where the picture keeps its shape while it
darkens, and the 103.6–107.8 s interval in *From Pole to Pole*. The holdout false
positives were at 131.6 s in *From Pole to Pole*, 82.8 and 165.92 s in *Jungles*,
and 151.2 and 152.6 s in *Deserts*. No setting changed after scoring.

The five holdout false positives were then inspected with `--review-at` sheets and
frames every 0.25 s from 2 s before to 3 s after each one. The scores above stay
as scored against the published reference.

| Time | What the frames show | Verdict |
|---|---|---|
| Pole 131.6 s | Close-up of penguin backs cuts in one frame to a wide view of the huddle. The reference has no boundary between 126.28 and 136.88 s. | Real cut missing from the reference |
| Jungles 82.8 s | A moving camera passes a tree trunk, which covers the sun flare in one frame. The same forest stays in view, and the real cut follows at 83.4 s. | Detector error: occlusion and lighting inside one shot |
| Jungles 165.92 s | A displaying bird snaps its wings shut and turns. Perch, background and the yellow leaf stay put. | Detector error: a large subject changes shape fast |
| Deserts 151.2 and 152.6 s | A low fixed camera watches animal legs walk across the frame for several seconds. The next shot starts at the reference's 155.28 s. | Detector error: foreground passing a fixed camera, read as a gradual change |

So one of the five is a missing reference boundary and four are detector errors.
Each comes from motion or light inside one view that changes most of the picture's
structure: the whole-frame view comparison can't see that the background is the same.
A check on how much of the picture survives in blocks might catch the bird and the
trunk. Nothing was changed for this, because tuning on these five would end the
holdout's blindness. A future fix needs new held-out footage.

### Runtime of the shot pass

Source-frame confirmation decodes every frame of the video at 96 pixels on the long
side. The time below is `find_changes` alone, best of two runs each, on one CPU of
the shared compute host while other jobs ran. Correlation itself takes under 0.6 s;
the extra time is the full-rate decode.

| Video | Size, rate, length | Original (`5af3a19`) | Confirmed | Ratio |
|---|---|---:|---:|---:|
| BBC *Pole* excerpt, lossless benchmark copy | 360×288, 25 fps, 180 s | 8.7 s | 20.8 s | 2.4× |
| Same excerpt re-encoded at CRF 20 | 360×288, 25 fps, 180 s | 5.8 s | 14.4 s | 2.5× |
| Landscape YouTube video | 1280×720, 60 fps, 124 s | 15.5 s | 33.3 s | 2.2× |
| Vertical map animation | 1080×1920, 30 fps, 62 s | 11.2 s | 22.3 s | 2.0× |
| Vertical game capture | 1080×1920, 60 fps, 33 s | 9.8 s | 20.6 s | 2.1× |
| High-bitrate vertical music video edit | 1080×1920, 60 fps, 33 s | 22.1 s | 43.6 s | 2.0× |

The shot pass takes about twice as long, adding 8 to 22 s on these videos. Decoded
frames are held in memory at about 21 KB each for a 16:9 picture (29 KB for the 4:3
BBC excerpts, 131 MB for three minutes at 25 fps). Ten minutes of 16:9 at 60 fps
needs about 0.75 GB, plus the raw decode buffer. No true 4K file was
timed. Decode time grows with the source resolution and frame rate.

Vertical checks: fresh-j now gives 5 shots, matching its key, where the original
gave 3 and Dissect 1. Its 29.6 s dissolve is counted. Fresh-i stays at 2, with the
end-card cut at 34.433 s. The three seed-100 zoom videos still give 12, 16 and 10.
In fresh-g the 5.3 s stage flash moved to review, and the audited cuts at 17.5 and
21.5 s are now counted. Fresh-g has no full key, so its count isn't scored.

`benchmark/shot_candidates.py` prints each decision with its measurements against a
reference. `tests/test_shot_confirmation.py` covers cuts, flashes, exposure changes,
pans, dissolves and clip ends on synthetic frames:
`python3 -m unittest discover -s tests`.

On an input with 1.2 s of picture and 2.4 s of audio, Dissect's frame timeline
reports a 2.4 s video duration despite its last shot ending at 1.2 s. The public
report includes a synthetic reproduction. [Dissect issue #1](https://github.com/0xpratzyy/dissect/issues/1)

## Picture motion

`changes.json` now gives one-second `picture_motion` windows. The tool compares a small
integer translation found by phase correlation with a centred scale fit. A fit needs to
explain the change across at least three quadrants. [Kuglin and Hines, phase correlation](https://jglobal.jst.go.jp/en/detail?JGLOBAL_ID=201002077897196684)

```bash
python3 benchmark/eval_motion.py --baseline 9843ac5 \
  "fresh-j=$FRESH_J=pan" "zoom-1=$ZOOM_1=zoom" "diagonal=$DIAGONAL=pan"
```

The evaluator labels a clip when at least two windows support the leading reading and
it has at least twice the support of the other reading. The baseline emitted no
motion-type cue, so every baseline machine reading was unknown.

| Video | Known motion | Pan windows | Zoom windows | Candidate reading |
|---|---|---:|---:|---|
| fresh-j, captioned AI-image montage with crossfades | Horizontal pan | 31 | 0 | Pan |
| Seed-100 zoom-1 | Centred zoom | 0 | 13 | Zoom |
| Seed-100 zoom-2 | Centred zoom | 0 | 5 | Zoom |
| Seed-100 zoom-3 | Centred zoom | 0 | 11 | Zoom |
| Six-second diagonal crop on a still image | Diagonal pan | 5 | 0 | Pan |
| Four-second still image | Static | 0 | 0 | Unknown |
| fresh-i, game with moving objects and a winner card | Fixed viewpoint | 0 | 0 | Unknown |

The candidate returned the expected label on all five moving clips. In the normal
`evidence.py --no-transcript` run, all five diagonal windows showed the expected
leftward and downward picture displacement. Baseline and candidate returned the same
shot timestamps on each clip. The diagonal and still controls were rendered from two
still images. The diagonal crop used fixed 1.3× scale,
720×1280 input and `x=20+0.8*on:y=150-0.9*on` at 24 fps.

A reviewer given the new cue, with the fresh-j key withheld, checked decoded frames
from 1–6 s. Roof peaks, the tree line and a window moved together without a visible
scale change. The reviewer answered pan. The two earlier runs called it a zoom. This
was a recheck of one shot on a known failure, so it stays separate from the original scores.

Limits include low texture, motion under one sample pixel or beyond eight sample pixels
per second, off-centre or combined motion, parallax, and rapid changes between endpoints.
An empty reading leaves the motion unresolved. A fit describes visible pixels and can
also come from a large moving layer. The three zooms and the diagonal clip are synthetic.
The motion test set still needs a human-edited video with a motion reference.
