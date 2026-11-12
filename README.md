# reverse-engineer-any-video

Break down any video to work out how it was made, and scan a channel to see which of
its videos beat the channel's own baseline.

- **Any video:** a local file, or a URL from any site [yt-dlp](https://github.com/yt-dlp/yt-dlp)
  can download. The evidence comes from the frames and the audio, so the source doesn't
  matter once the file is on disk.
- **Channels:** the outlier scan has been tested on TikTok and YouTube channels. Other
  sites that yt-dlp can list may work but are untested.

It ships as an agent skill plus two standalone Python scripts:

- `evidence.py` measures one video: facts, transcript, contact sheets, visible changes,
  shot estimates, picture motion and audio readings, so the model works from
  measurements instead of guessing.
- `scan_channel.py` ranks a channel's videos against the channel's own baseline, so the
  winners and flops you compare come from the same channel and format.

The skill then guides the agent through investigating how the video was made: competing
hypotheses for each part, fingerprints, web research, a comparison of winners with
flops, a small rebuild test and a blind review. Every claim is labelled measured, seen,
found, inferred or unknown.

Status: v0.1. The channel scan, the evidence command and a first benchmark work. See
[the design](docs/DESIGN.md) for what is planned and [the roadmap](docs/ROADMAP.md).

## Requirements

- Python 3.10 or newer
- [ffmpeg](https://ffmpeg.org/) with `ffprobe`, on your `PATH`
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for URLs and channel scans
- numpy
- Optional: [faster-whisper](https://github.com/SYSTRAN/faster-whisper) for transcripts
  (runs on CPU; skip it with `--no-transcript`)

## Install

```bash
git clone https://github.com/lisn0/reverse-engineer-any-video.git
cd reverse-engineer-any-video
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pip install faster-whisper   # optional, for transcripts
```

Install ffmpeg with your package manager, for example `brew install ffmpeg` or
`sudo apt install ffmpeg`.

## Install in any agent

The skill is a standard [Agent Skills](https://agentskills.io) `SKILL.md` folder:
[`plugins/reverse-engineer-any-video/skills/reverse-engineer-any-video/`](plugins/reverse-engineer-any-video/skills/reverse-engineer-any-video/).
It has been tested with Claude Code. Other agents that read Agent Skills should load
it the same way, but haven't been tested.

**With the Skills CLI** ([vercel-labs/skills](https://github.com/vercel-labs/skills)),
which finds the skill through the repo's `.claude-plugin/marketplace.json`:

```bash
npx skills add lisn0/reverse-engineer-any-video                # asks which agents
npx skills add lisn0/reverse-engineer-any-video -a claude-code  # one agent
npx skills add lisn0/reverse-engineer-any-video --all           # all agents, no prompts
npx skills add lisn0/reverse-engineer-any-video --list          # show it without installing
```

**By hand:** copy that folder into your agent's skills directory, for example
`.agents/skills/` for Codex or `.claude/skills/` for Claude Code.

**As a Claude Code plugin:** the repo is also a plugin marketplace
([`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json)). In Claude Code:

```
/plugin marketplace add lisn0/reverse-engineer-any-video
/plugin install reverse-engineer-any-video@reverse-engineer-any-video
```

Then ask, for example, "how was this video made: ./clip.mp4" or "reverse engineer this
channel: https://www.youtube.com/@<handle>/shorts". The skill runs the scripts for you;
they still need the requirements above on the machine the agent runs on.

## Examples

The scripts live in
`plugins/reverse-engineer-any-video/skills/reverse-engineer-any-video/scripts/`.

### Evidence for one video

```bash
python3 plugins/reverse-engineer-any-video/skills/reverse-engineer-any-video/scripts/evidence.py \
  ./clip.mp4 --out runs/clip
python3 plugins/reverse-engineer-any-video/skills/reverse-engineer-any-video/scripts/evidence.py \
  "<video URL>" --out runs/<name>
```

The source can be a local file or a URL. This writes `manifest.json`, `changes.json`,
`audio.json`, the transcript, word timings and contact sheets.

For a disputed cut, flash or dissolve, pass `--review-at SECONDS` with a new output
directory. This writes dense contact sheets and a `review.json` index with each tile's
time relative to the first picture. Repeat the flag to review several moments. For an
independent abrupt-change cue in a full evidence run, add `--crosscheck-cuts`.

### Scan a channel

```bash
python3 plugins/reverse-engineer-any-video/skills/reverse-engineer-any-video/scripts/scan_channel.py \
  "https://www.youtube.com/@<handle>/shorts" --out runs/<name>
```

This writes `outliers.md` and `channel.json`. Each video is scored as its views divided
by the median of its neighbours in upload order, separately for short and long videos.
For YouTube, pass the `/videos` or `/shorts` tab; for TikTok, the profile URL.

Run either script with `--help` for all options.

## Benchmark

Shot boundaries were scored against the manually annotated BBC Planet Earth dataset
(Baraldi, Grana and Cucchiara), on the first 180 seconds of five episodes, 87 reference
boundaries in all. Settings were tuned on two excerpts (*Mountains*, *Caves*) and then
frozen before the other three were scored once.

| Reading | All 5 excerpts (87) | Held-out 3 excerpts (53) |
|---|---:|---:|
| This tool, shots confirmed on source frames | F1 96.0% (85 matched, 5 false, 2 missed) | F1 94.5% |
| [Dissect](https://github.com/0xpratzyy/dissect), shot starts and internal cuts | | F1 94.4% |
| Dissect, shot starts only | | F1 89.1% |
| This tool's previous detector | | F1 67.1% |

On the held-out excerpts this ties Dissect with internal cuts, within one event; it
doesn't clearly beat it. The five held-out false positives were checked frame by frame:
one was a real cut missing from the reference, and four were motion or light changes
inside one view.

[benchmark/README.md](benchmark/README.md) has the full method, the hand-labelled
method questions, audio and motion tests, the runtime table and the scoring scripts.
Some benchmark scripts need extra packages (soundfile and kokoro for
`make_ai_case.py`; opencv and pillow for the Dissect comparison).

## Known limits

- Large motion or lighting changes inside one view (a subject passing a fixed camera, a
  flare blocked for a frame) can still be counted as a new shot.
- A slow fade to black can be missed, because the picture keeps its shape as it darkens.
- The shot pass decodes every frame, so it takes about 2 to 2.5 times as long as before:
  for example 8.7 s to 20.8 s on a 3-minute clip. No true 4K file has been timed.
- The benchmark covers a handful of videos and one agent model, and most test videos
  were made by code. It doesn't support a general accuracy claim.
- Channel scans are tested on TikTok and YouTube only.
- Scanning is built and measuring is partly built. The compare, reconstruct, verify and
  blueprint steps are designed but not built yet ([design](docs/DESIGN.md)).

## Credits

[Dissect](https://github.com/0xpratzyy/dissect) (MIT) is the comparison baseline in the
benchmark; `bench/run_dissect.sh` runs a pinned revision of it. Several ideas here,
such as measured placeholders and transition strips, come from it. Nothing from Dissect
runs inside this tool or is copied into it.

## License

[MIT](LICENSE)
