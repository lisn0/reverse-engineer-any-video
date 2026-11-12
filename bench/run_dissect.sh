#!/usr/bin/env bash
# Run the upstream visual measurement CLI with an existing Linux environment.
# usage: DISSECT_PYTHON=python3 bash bench/run_dissect.sh NEW_OUT_DIR VIDEO [VIDEO...]
set -euo pipefail

out=${1:?Provide a new output directory and one or more videos.}
shift
if [[ $(uname -s) != Linux || $# == 0 ]]; then
    printf 'Run this benchmark on a Linux machine with one or more videos.\n' >&2
    exit 2
fi
python=${DISSECT_PYTHON:-python3}
"$python" -B -c 'import cv2, numpy, PIL; print("Visual dependencies:", cv2.__version__, numpy.__version__, PIL.__version__)'

mkdir -- "$out"
repo="$out/dissect-source"
revision=35c1098c0f9d23de9529f471a65fe51bfc90046a
git init -q "$repo"
git -C "$repo" fetch -q --depth 1 https://github.com/0xpratzyy/dissect "$revision"
git -C "$repo" checkout --quiet --detach FETCH_HEAD
test "$(git -C "$repo" rev-parse HEAD)" = "$revision"
printf '%s\n' "$revision" > "$out/dissect-commit.txt"

script="$repo/plugins/dissect/skills/dissect/scripts/dissect.py"
"$python" -B "$script" --version
for video in "$@"; do
    "$python" -B "$script" "$video" --out "$out" --max-minutes 25 --no-comments --threads 2
done
