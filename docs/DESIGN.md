# Design

Goal: given any video or channel, work out how it was made and why it works, then
prove it by rebuilding it. Shorts, TikTok, long-form and documentaries are all in
scope.

## Where the field stands

Initial source review on 2026-11-01. See the [benchmark](../benchmark/README.md) for
the later paired visual comparison with Dissect.

| Tool | Strong at | Missing |
|---|---|---|
| [dissect](https://github.com/0xpratzyy/dissect) | Frame measurement, measured blocks the model can't retype, timing lint | No research, no stack inference, score is timing only, VFR mishandled, frame-level timeline stops at 10 minutes, no tests |
| [zuverse](https://github.com/zutrue/zuverse) | Measured cuts fed to Gemini as constraints, generative remake | Nothing compares the remake with the original |
| [head-of-content](https://github.com/bradautomates/head-of-content) | Closed taxonomy, runs only on outliers | No measurement, trusts the model |
| OutlierKit | Outlier ranking, data over MCP and API | Public data and transcripts; homepage shows no frame analysis |

None of these identifies the production stack, researches the web, or tests its own
claims. That is the gap.

## What makes this different

1. **Investigation:** competing hypotheses for each part of the stack, backed by
   fingerprints and web research.
2. **Channel evidence:** winners compared with flops from the same channel, with
   sample sizes and video-clustered statistics.
3. **Adversarial verification (Elephant-Goldfish):** the agent holding the theory
   never grades its own work. Fresh reviewers with no memory check it:
   - blind describer: frames and cuts only, no blueprint. Blueprint details it
     doesn't see get flagged as possibly invented.
   - claim auditor: one claim plus its frames, answers measured, inferred or
     unsupported.
   - blind comparer: original and rebuild only, says what differs.
   - blueprint-only rebuilder: the blueprint only, says what can't be built.
   - skeptic: looks for a simpler explanation, such as one preset.
   They never receive the theory or a summary of it. Two blind readers disagreeing
   lowers the claim's confidence.
4. **Honest rebuild scoring:** timing, content, style and sound are scored
   separately, so a hollow rebuild can't score high. Each scorer is checked against
   deliberately bad rebuilds.
5. **Any length:** long videos are measured in full by chapter, not just the opening.
6. **Tested accuracy:** a committed benchmark of hand-labelled videos, so accuracy is
   a number anyone can reproduce.

## Pipeline

1. **Scan** (built): score videos against the channel baseline, per format.
2. **Measure** (partly built): `evidence.py` gives facts, transcript, sheets and visible
   changes, shot estimates and audio readings, and fails on partial decode. Still to come:
   native timestamps, OCR, voice identification.
3. **Compare** (not built): classify every video against a closed taxonomy and count
   what separates outliers from flops.
4. **Investigate** (skill instructions written): fingerprints, web research and
   competing hypotheses.
5. **Reconstruct** (not built): recipe, then a small test of the riskiest step.
6. **Verify** (not built): the Goldfish reviewers above, then the rebuild score. A
   failed theory returns to step 4.
7. **Blueprint** (not built): every claim labelled measured, found, inferred or
   unknown, with measured values inserted by code so the model can't retype them.

## Ideas to take from others

dissect is MIT, so credit it. Measured placeholders, the prose-against-data lint,
transition strips around each change, a confidence on every heuristic, fixes stated
in frames. From zuverse: measured cuts as model constraints. From head-of-content:
the closed taxonomy.

## Build our own core

Use Dissect as an optional comparison input in the benchmark. The evidence command
uses FFmpeg to build its own timestamped review sheets for disputed boundaries.

## Products

One Python engine; every surface is a thin layer over it.

| Order | Surface | Notes |
|---|---|---|
| 1 | Python package and CLI | The engine, on PyPI |
| 2 | Skill and plugin | Claude Code first; Codex reads the same instructions through AGENTS.md |
| 3 | MCP server | Works in Claude, Codex, Cursor and other clients; MCP Registry through `server.json` |
| 4 | Hosted API | Only when people need it without local compute |
| 5 | Website | Docs, example teardowns, the benchmark |

Each new surface should wait until the layer below works on real videos. Release
PyPI first, then the MCP Registry, and confirm each step for real.

An SDK is the Python package itself until someone needs another language.

## Public from day one

Nothing may depend on a private host or path. Setup for one machine stays outside the
repo. Users bring their own API keys.

## Lessons this design carries

- Vision agents invent details. Spot-check and keep unverified claims labelled.
- Detector cut lists are lower bounds.
- Sampling coarser than the cut rate misses events.
- Don't derive laws from small samples.
- Generate totals from one ledger per channel, never by hand.
- Gemini timestamps drift, so snap them to detected boundaries.
- Human reference annotations miss real boundaries too, so disagreements are settled on
  frames. Tune on development footage only and score held-out footage once.
- Flashes, lighting changes, occlusion and large motion inside one view are the main
  sources of false shots; slow fades that keep the picture's shape are the main misses.
- Systematic errors narrow the field more than polish does, and a fingerprint names a
  mechanism, not a brand.
- A rebuild that reaches the look shows a method can make it, not that the creator used it.
- The skill keeps a lean `SKILL.md` and moves detail into one-level reference files
  (evidence reading, fingerprints, channel comparison, rebuild and review, pitfalls).

## Open questions

- Ingestion: flat listings lack dates and engagement, and TikTok access is fragile.
- Thresholds: 3x and 0.5x are starting values.
- Which cues distinguish a dissolve from movement across the same shot.
- Name: "any video" undersells channels, but the repo handles both.
