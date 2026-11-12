---
name: reverse-engineer-any-video
description: Reverse-engineer any video of any length (a local file or a URL yt-dlp can download) or a channel. Measures how the video was made from its frames and audio, finds which videos beat their channel's own baseline, tests the theory with a rebuild, and checks it with a blind reviewer. Use when asked "how was this video made", "reverse engineer this channel", "how was this made", "what makes this channel work", "analyze this creator".
---

# reverse-engineer-any-video

You are an investigator, not a describer. The question is always: how was this
made, why does it work, and could we make it? Describing what is on screen is not
the answer.

Work through the steps in order. Write the result with
`assets/teardown-template.md`. Steps 1 and 2 have scripts; the rest is your own work.

Answer "unknown" whenever the evidence doesn't support a claim. A wrong claim is worse.

## 1. Scan the channel

```bash
python3 scripts/scan_channel.py "<url>" --out runs/<name>
```

Pass the `/videos` or `/shorts` tab for YouTube, or the profile URL for TikTok. Other
sites yt-dlp lists may work but are untested. For a single video, scan its channel when
it has one, so you know whether it's unusual. A local file has no channel: skip to step 2.

Read `outliers.md`, then:

- Look for format changes in the titles. Baselines near a change are distorted, so
  compare videos within one format.
- Choose at least 2 winners and 2 flops **from the same format**. Avoid flops that
  differ for an obvious reason, such as adverts.

## 2. Get the evidence

```bash
python3 scripts/evidence.py "<video url or file>" --out runs/<name>/<id>
```

This writes `manifest.json`, `changes.json`, `transcript.txt`, `words.json` and sheets:
an overview across the whole video, dense hook, middle and ending windows, and one
frame per visible change. The manifest gives the time of every tile.

- `changes.json` labels events `shot`, `element` (added to the picture), `text` or
  `small`. Every shot is checked on the source frames. `cue: cut` is a one-frame
  change in picture structure after which the old view doesn't come back.
  `cue: gradual` is a dissolve or fade: the views half a second either side differ.
  A candidate that fails, such as a flash, a lighting change or motion inside one
  view, goes into `uncertain_shots` with a `why`. Both lists appear on the change
  sheets. The manifest gives `estimated_shots` and a higher figure that counts
  elements as cuts. Start there, then review uncertain times and correct the count
  from the frames. A slow fade that keeps the picture's shape can land in review.
  Fast motion or a foreground object crossing one view can still count as a shot.
  The source-frame check decodes every frame, so the shot pass takes about twice as
  long as before: roughly 15 to 45 s for a one- to three-minute video.
- Those labels are estimates, so check a few against the frames. They handle a centred
  zoom well. Pans, and captions over moving items, can still add false shots. Effects
  added to a scene usually count as `element`, not `shot`.
- A caption follows speech or lyrics. Titles, labels and dashboards aren't captions.
- A beat is a change of idea, even inside one continuous shot. Count beats from
  on-screen headers, new overlays and the transcript.
- For a single continuous shot, near-zero changes are the finding. Then study what
  changes inside the frame instead.
- Sung lyrics in a transcript mean music. They don't mean a narrator.
- `--crosscheck-cuts` adds `native_cut_candidates_s`, a separate list of strong
  abrupt changes at the source frame rate. Compare it with `events` and
  `uncertain_shots` to find moments worth reviewing. A candidate can be a flash
  or a cut, and a dissolve may appear only in the original evidence.
- When a boundary is uncertain or two timelines disagree, generate a focused review.
  Use the clip's local source so both measurements refer to the same frames.

  ```bash
  python3 scripts/evidence.py clip.mp4 --review-at 5.3 --review-at 29.6 --out runs/review
  ```

  `review.json` gives the picture-relative presentation time of each tile in row-major
  order. Check the lead-in, the change, and the recovery. A flash can leave the camera
  view continuous or occur next to a real cut. A dissolve briefly shows both shots
  before settling into the next one. Use the visible frames to resolve the report.
- For long videos, add dense windows inside each chapter.

Read the frames yourself. If you use sub-agents, spot-check their claims, because
they invent details.

## 3. Investigate how it was made

For each part (script, visuals, motion, voice, captions, sound, edit, automation)
keep competing hypotheses and try to break each one.

- **Hunt for mistakes first:** odd capitalisation, typos, spellings that differ from
  the speech, repeated assets and glitches reveal the process.
- **Test every fingerprint:** reproduce the exact mistake if you can, then say what
  else could also explain it. A match proves a mechanism, not a brand.
- **Check what moves:** do shapes deform as in generated video, or do rigid layers
  move, rotate, swap and fade?
- **Tell pans from zooms:** `changes.json` includes `picture_motion`, one-second windows
  where a translation or centred scale explained the motion across the picture. Pan
  offsets are in 90×160 sample pixels, with positive values pointing right and down.
  Check two or more stationary features in the frames at both times. If they slide together
  and keep their spacing, report a pan. If their spacing changes together around the
  centre, report a zoom. Features that move independently suggest layer motion. An
  empty list leaves the motion unresolved. The fit can also come from a moving layer
  that fills the picture, so it cannot establish how the effect was made.
- **Hearing:** you can't listen, so use `audio.json`. It reads `music`, `narrator` and
  `voice_source` from the sound between words. "unclear" means the evidence is split, so
  answer unknown. `no` means digital silence or room noise in the gaps. `yes` means a
  beat, or tones under the voice.
- **Voice source:** `generated_or_gated` means gaps at digital silence. That fits text to
  speech, but also an edited human recording or inserted clips, so check it against the
  transcript and pacing. Without it, don't guess between human and generated.
- **Clues for code:** exact repetition across videos, mechanical caption splits, casing
  bugs and numbers that change smoothly. **Clues for an editor:** cuts with varied
  feel, hand-placed text, one-off effects. Few clues means "unknown".
- **Check the file size:** a very small file for its length suggests little motion.
- **Separate the script's parts:** line up transcripts and name the repeated steps.
- **Don't trust a change count alone:** check it against the frames, and check any
  strange frame too, because your tool may have made it.
- **Search the web:** interviews, tutorials, bio links, tools mentioned, and people
  who tried to copy the format. Expect little, and record what you couldn't read.
- **Find the origin:** search the format's name across platforms. The account you
  were given may copy a bigger one. Compare real dates before saying who came first.
- **Estimate the cost:** posting rate and asset reuse show how much is automated.

Name the evidence for each claim. A plausible tool with no evidence stays a hypothesis.

## 4. Compare winners with flops

Compare script type, length, topic breadth, hook and look. Say how many videos each
pattern rests on. Prefer a closed list of categories so videos can be counted. With
fewer than about 10 videos per side, call it a lead.

Rule out the obvious first: age, posting date and format changes. TikTok video IDs
contain the upload time (`id >> 32` is Unix seconds), so check it. The strongest
evidence is a matched pair: same week, length and style, very different views. Whatever
they share can't explain the gap.

Compare across channels too. What holds on two unrelated channels is a stronger lead.

## 5. Reconstruct to test the theory

Write the shortest recipe you believe reproduces the look. Find its riskiest step,
make the cheapest test of it, and compare the result with the original at matching
moments. If it can't produce the look, the theory is wrong: update it and say what
changed. If you can't run a test, say so and label the recipe untested.

## 6. Review blind

Give a fresh agent frames only: no theory, title, summary or transcript. Ask it to
copy the captions exactly, say what moves, say what repeats, and guess the method.
Where it disagrees with you, mark the evidence as weak instead of arguing it away.

## 7. Write the teardown

Fill in the template. End with what's unknown and the next test.

## Rules

- Compare videos with their own channel, never with raw view counts.
- Label every claim: measured, seen, blind, found, inferred or unknown.
- Exit 0 isn't proof. Check the output exists and reads correctly.
- Correct your own earlier claims in the open.
- Study the format. Don't reproduce a script, footage or a likeness.
