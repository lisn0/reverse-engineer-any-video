# Roadmap

The goal is a public skill that reverse-engineers any video or channel.

## v0.1: public skill (this release)

- Install on a clean machine with Python, ffmpeg and yt-dlp
- No private hosts or paths in the tree
- README with install steps and examples

## v0.2: use it anywhere

- MCP server and registry listing, so clients other than Claude Code can call it

## Better answers

These can run alongside v0.1 and v0.2.

- Tell code-driven edits from templates and manual editing
- Quiet music and voice type from measured audio
- Rebuild comparison: paired original and rebuild frames with a score
- Machine-readable recipe output (assets, shots, timing, captions, sound), so a teardown
  can feed a renderer without retyping
- Asset inventory: each distinct asset, how often it is reused, and whether it looks
  generated, photographed or drawn by code
- Caption extraction from frames with timings, to compare on-screen text with speech
- Separate shot changes from new captions and added elements in the change list
- Standard audio measures in every teardown: loudness, silent gaps, noise floor and
  median pitch

## Later

- Website, once people are using it

## Known limits

- Shot boundaries have been tested on independently annotated broadcast footage.
  A full teardown of a manual edit with a known workflow is still untested.
- Accuracy so far comes from a small set of videos: see
  [the benchmark](../benchmark/README.md).
