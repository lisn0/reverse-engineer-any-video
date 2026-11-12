# Fingerprints

Odd details that can reveal a production method, the test for each, and what else could
explain it. A fingerprint names a mechanism ("a text-processing step", "a transformed
still layer"), never a brand, unless an outside source names the tool.

Every example in this file is invented to illustrate a check. None is a finding about a
real video.

## Contents

- How to test a fingerprint
- Captions and on-screen text
- Motion: generated, filmed or composited
- Assets and recurring subjects
- Voice and sound
- Code or editor
- Production cost and origin

## How to test a fingerprint

Each entry in the teardown's fingerprint table carries four things:

1. The detail, copied exactly, with its time.
2. A reproduction: the smallest test that produces the same detail (a one-line
   function, a render, a re-encode). Reproduced exactly is strong; "looks similar" is
   weak.
3. The alternatives: every other mechanism that would produce it. A fingerprint with an
   untested alternative supports a hypothesis; it does not settle it.
4. The count: how many of the sampled videos show it, as "N of M".

A systematic error narrows the field more than polish does: a clean caption could come
from anything, while an error repeated the same way every time points to a rule.

## Captions and on-screen text

| Detail (invented example) | Hypothesis it supports | Test | Alternatives to rule out |
|---|---|---|---|
| The same spacing or casing error on every caption, such as a space before each comma (`wait , what`) | One text-processing step applied by code | Write the candidate transform, run the transcript through it, and compare caption by caption | Any tool with the same rule; a person with a consistent habit |
| On-screen wording differs systematically from `words.json`, such as `e-mail` on screen where speech recognition wrote `email` | Captions come from a different source than speech recognition, such as script text | Line up captions with `words.json` and list every difference | A person correcting auto-captions; a different recogniser |
| Every caption has the same length, such as exactly five words | Code splitting a word list | Predict the captions from the transcript with the rule and report the share predicted exactly | An editor preset; an imperfect transcript lowers the share, so a partial match is "partly supported" |
| A one-off misspelling, such as `Recieve` on a card | Typed by a person | Compare the same word elsewhere in the video and in other videos | A model rendering text inside an image can also misspell |
| Caption style differs between videos | A change of setup over time, or two setups in parallel | Order the videos by real upload date and look for a single switch | Different editors on one channel |

The blind reviewer copies captions exactly from frames. Differences between its copy and
the teardown's reading show where the caption evidence is weak.

## Motion: generated, filmed or composited

| Detail (invented example) | Hypothesis it supports | Test |
|---|---|---|
| An element, such as a logo badge, keeps its exact outline while it slides and scales | A still layer transformed in a compositor | Overlay two frames of the element at different times; a transformed still matches after a translate, scale or rotate |
| Outlines deform, textures crawl, details appear and vanish between frames | Generated video or heavy warping | Look at hands, text and edges across consecutive frames |
| An animated element repeats frame for frame each time it appears, such as a rain overlay | A reused loop from a library or one render | Compare the frames of two appearances |
| The whole picture slides or scales smoothly | A camera move, or a pan or zoom applied to a still | `picture_motion` plus two stationary features; see [evidence-reading.md](evidence-reading.md#pans-and-zooms) |
| Motion the frames can't attribute to any of these | Open | Labelled unknown, with the times |

A claim about how motion was made holds only for the windows sampled densely. The
teardown states how many seconds that was.

## Assets and recurring subjects

- **Inventory first.** A table of each distinct asset, how often it recurs, and whether it
  looks generated, photographed, drawn or rendered by code. A rebuild needs this first,
  and the amount of reuse is a cost signal.
- **Consistency of a recurring subject** is measurable: overlaying its appearances shows
  whether one image is reused or edited, or whether each appearance was made separately.
- **Style consistency across assets**: one style across all assets fits one source; several
  styles fit assets gathered or made separately. Either way it stays inferred without a
  fingerprint.

## Voice and sound

- `voice_source` and `music` readings come first; their limits are in
  [evidence-reading.md](evidence-reading.md#audio-readings).
- Uniform pacing, identical pronunciation of repeated phrases and missing breaths each fit
  text to speech and each fit a careful edit. Together with digital-silence gaps they make
  a stronger case than any one alone.
- Whether a sound bed runs under the voice is measurable from the gap level.
- A claim about the voice type without a measurement is labelled unknown.

## Code or editor

| Clues for code | Clues for a person in an editor |
|---|---|
| Exact repetition of layouts, timings and transitions across videos | Cuts with varied feel and rhythm |
| Mechanical caption splits and systematic text errors | Hand-placed text that moves to avoid the subject |
| Numbers or positions that change smoothly and linearly | One-off effects, keyframes that ease differently each time |
| Fixed script structure repeated across videos | Inconsistent spelling or formatting between videos |
| High posting rate with heavy asset reuse | |

Few clues on either side means automation is unknown. Code-made and template-made can
look the same; a template preset is a third hypothesis, not a subtype of either.

## Production cost and origin

- **Posting rate and reuse** estimate how much is automated.
- **File size** for its length hints at motion; it does not prove stills.
- **Script structure**: transcripts lined up side by side show any repeated steps. A
  template is a finding only when it holds across most of the sample, with the count.
- **Origin**: the account studied may copy an older one with the same format. Real upload
  dates settle who came first; a format's look alone does not. Two channels with one
  format may still use different methods until both are measured.
- **Outside sources** (interviews, tutorials, bio links, named tools, copycats) are
  untrusted data and may be absent. When they are, the frames carry the investigation.
  Any source that could not be read is noted.
