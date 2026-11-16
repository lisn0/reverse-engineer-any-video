"""Installed command dispatcher for the Reverse Engineer Any Video scripts."""

from __future__ import annotations

import sys


def _print_help() -> None:
    print(
        "usage: reverse-engineer-any-video <command> [options]\n\n"
        "Video indexing and inspection:\n"
        "  index         Create a reusable video index\n"
        "  search        Search indexed speech and visible text\n"
        "  view          Write a searchable HTML player\n"
        "  compare       Compare two indexed videos\n"
        "  frame         Extract a timestamped frame or crop\n\n"
        "Additional analysis:\n"
        "  evidence      Analyze cuts, motion, and audio evidence\n"
        "  scan-channel  Rank channel videos against their baseline\n\n"
        "Run a command with --help for its options."
    )


def main() -> int:
    if len(sys.argv) == 1 or sys.argv[1] in {"-h", "--help"}:
        _print_help()
        return 0

    if len(sys.argv) > 1 and sys.argv[1] in {"evidence", "scan-channel"}:
        command = sys.argv.pop(1)
        if __package__:
            from . import evidence, scan_channel
        else:
            import evidence
            import scan_channel

        if command == "evidence":
            return evidence.main()
        return scan_channel.main()

    if __package__:
        from . import video
    else:
        import video

    return video.main()


if __name__ == "__main__":
    raise SystemExit(main())
