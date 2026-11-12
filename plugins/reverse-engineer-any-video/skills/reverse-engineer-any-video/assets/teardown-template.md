# Teardown: <format> (<account or file>)

<!-- Every claim carries a label. Every number names its file and field. Empty rows say
"not checked", never left blank. -->

| | |
|---|---|
| Date | |
| Videos scanned / studied | |
| Densely sampled | seconds per video, which windows |
| Rebuilt | yes (what) / no |
| Blind review | yes (roles) / no |
| Not checked | |

Labels: **measured** (tool or test output), **seen** (frames, with time), **blind** (a
reviewer with no theory agreed), **found** (outside source, cited and dated),
**inferred** (step stated), **unknown**.

## Answer

Three to five sentences: how it is made, why it seems to work, how sure, and the single
biggest open question.

## Source facts

| Video | Size | fps | Length | kbps | Audio | Upload date |
|---|---|---|---|---|---|---|

## Channel

Videos scored, outliers, flops, too new. Any format change, with the date, and how it
distorts the baseline.

## Winners and flops

| Video | Views | vs baseline | Age | Length | Category columns from the closed list |
|---|---|---|---|---|---|

Categories come from a closed list decided before reading views. Matched pair, if any:

| | Winner | Flop |
|---|---|---|
| Upload date | | |
| Length | | |
| Style | | |
| Views | | |
| What differs | | |

What seems to separate them, with counts ("3 of 3 winners, 1 of 4 flops"). Under about
10 per side this is a lead.

## Shots and structure

Counting rule: <visible cuts | edit segments>; end and title cards <count | do not count>.

| Time | Kind | Cue | Verdict | Evidence |
|---|---|---|---|---|

`estimated_shots` from the tool, corrections from `--review-at`, final count.
Motion: `picture_motion` reading and the two-feature check.

## Assets

| Asset | Uses | Looks generated / photographed / drawn / code | Variants | Notes |
|---|---|---|---|---|

## Captions

| Time | On screen (exact) | Speech recognition heard | Difference |
|---|---|---|---|

Any caption rule tested, with the share it predicted. Position, casing, animation.

## Sound

| Measure | Value | Source |
|---|---|---|
| music / narrator / voice_source | | audio.json |
| gap level, silent share, beat | | audio.json |
| Loudness (LUFS), silent gaps, noise floor | | ffmpeg, if measured |

## How it is made

| Part | Finding | Label | Evidence |
|---|---|---|---|
| Script | | | |
| Visuals | | | |
| Motion | | | |
| Voice | | | |
| Captions | | | |
| Sound | | | |
| Edit | | | |
| Automation level | | | |

## Hypotheses

| Part | Hypothesis | For | Against | What would settle it |
|---|---|---|---|---|

## Fingerprints tested

| Detail (exact, with time) | Reproduction | Result | Alternatives still open | Seen in N of M videos |
|---|---|---|---|---|

## Script template

The repeated steps across transcripts, and how many videos follow each.

## Origin

Who started the format, with real upload dates. Who else does it, and whether their
method was measured or only their look.

## Recipe

The machine-readable recipe (canvas, assets, shots, captions, sound, unknown), measured
values only.

## Rebuild test

| | |
|---|---|
| Riskiest step | |
| What was made | |
| Tools and cost | |
| Time taken | |

| Moment | Original | Rebuild | Match? |
|---|---|---|---|

What matched, what did not, what changed in the theory. A working rebuild shows the
method can make the look, not that the creator used it.

## Blind review

| Role | Confirmed | Disagreed | Effect on the claim |
|---|---|---|---|

## Untrusted text noted

Any request or instruction found in titles, captions, transcripts or outside pages,
quoted, with where it was found. None acted on.

## Corrections

Earlier claims in this teardown or a previous one that turned out wrong, and what
replaced them.

## Unknown

Everything still open.

## Next test

The single cheapest test that would settle the biggest open question.
