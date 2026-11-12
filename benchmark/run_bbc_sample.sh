#!/usr/bin/env bash
# Run the shot benchmark on selected three-minute public BBC annotations.
set -euo pipefail

root=$(cd -- "$(dirname -- "$0")/.." && pwd)
work=${1:?Usage: bash benchmark/run_bbc_sample.sh NEW_OUTPUT_DIRECTORY [--baseline REV] [EPISODE ...]}
shift
baseline=
episodes=()
while (($#)); do
    case "$1" in
        --baseline)
            (($# >= 2)) || { printf '%s\n' '--baseline requires a revision.' >&2; exit 2; }
            baseline=$2
            shift 2
            ;;
        *) episodes+=("$1"); shift ;;
    esac
done
if ((${#episodes[@]} == 0)); then
    episodes=(02_Mountains 10_Caves)
fi
for name in "${episodes[@]}"; do
    case "$name" in
        02_Mountains|10_Caves|01_From_Pole_to_Pole|05_Jungles|11_Deserts) ;;
        *) printf 'Unsupported episode: %s\n' "$name" >&2; exit 2 ;;
    esac
done
if [[ -n $baseline ]]; then
    # Keep option parsing in the runner; pass the revision before positional cases.
    eval_args=(--baseline "$baseline")
else
    eval_args=()
fi
mkdir -- "$work"
export TMPDIR="$work"
scratch_mib=$((320 * ${#episodes[@]} + 64))
if [[ $(df -B1 --output=avail -- "$work" | tail -n1) -lt $((scratch_mib * 1048576)) ]]; then
    printf 'Need at least %s MiB available for excerpts and detector scratch.\n' "$scratch_mib" >&2
    exit 1
fi
ulimit -f 327680  # 320 MiB per output file in Bash's 1024-byte units

base=https://zenodo.org/records/14865504/files
api=https://zenodo.org/api/records/14865504/files
encode_excerpt() {
    timeout 180s ffmpeg -nostdin -v error -y -rw_timeout 15000000 \
        -reconnect 1 -reconnect_on_network_error 1 -reconnect_on_http_error '429,5xx' \
        -reconnect_max_retries 2 -reconnect_delay_max 4 \
        -i "$1" -map 0:v:0 -an -frames:v 4500 \
        -vf 'setpts=PTS-STARTPTS' -fps_mode passthrough \
        -c:v libx264 -preset ultrafast -qp 0 -threads 2 "$2"
}

cases=()
for name in "${episodes[@]}"; do
    video="$work/$name.mp4"
    labels="$work/$name.txt"
    boundaries="$work/$name.json"
    frames="$work/$name.frames"
    curl -fsSL --retry 2 --retry-delay 2 --max-time 30 --max-filesize 16384 \
        "$base/$name.txt?download=1" -o "$labels"
    # Decode the presentation frames before trimming. H.264 packet order can leave
    # a hole at the end of a stream-copy excerpt, even when its frame count is right.
    if ! encode_excerpt "$base/bbc_${name:0:2}.mp4?download=1" "$video"; then
        printf 'Retrying %s through the Zenodo file API.\n' "$name" >&2
        encode_excerpt "$api/bbc_${name:0:2}.mp4/content" "$video"
    fi
    ffprobe -v error -select_streams v:0 -show_entries frame=best_effort_timestamp_time \
        -of json "$video" > "$frames"
    python3 -B - "$labels" "$boundaries" "$frames" <<'PY'
import json
import sys
from pathlib import Path

labels, output, frames = sys.argv[1:]
timestamps = [float(frame["best_effort_timestamp_time"]) for frame in json.loads(Path(frames).read_text())["frames"]]
if timestamps != [i / 25 for i in range(4500)]:
    raise SystemExit(f"{frames}: expected 4,500 consecutive presentation frames at 25 fps from time zero")
shots = [tuple(map(int, row.split())) for row in Path(labels).read_text().splitlines() if row.strip()]
if shots[0][0] != 0 or shots[-1][1] < 4499:
    raise SystemExit(f"{labels}: annotations do not cover the excerpt")
references = []
for (_, previous_end), (start, _) in zip(shots, shots[1:]):
    if start >= 4500:
        if previous_end < 4499:
            raise SystemExit(f"{labels}: excerpt ends inside an annotation gap")
        break
    if start <= previous_end:
        raise SystemExit(f"{labels}: overlapping reference shots near frame {start}")
    if start == previous_end + 1:
        references.append(start / 25)
    else:
        references.append([(previous_end + 1) / 25, start / 25])
Path(output).write_text(json.dumps(references) + "\n")
PY
    printf '%s reference boundaries: ' "$name"
    cat "$boundaries"
    cases+=("$name=$video:$boundaries")
done

python3 -B "$root/benchmark/eval_shots.py" "${eval_args[@]}" "${cases[@]}" | tee "$work/results.txt"
du -sh -- "$work"
