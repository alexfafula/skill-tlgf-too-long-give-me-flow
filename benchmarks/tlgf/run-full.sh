#!/bin/sh
set -eu

benchmark_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

python3 "$benchmark_dir/run.py" doctor
python3 "$benchmark_dir/run.py" run \
  --agents claude,codex,agy \
  --claude-model opus \
  --agy-model gemini-3.7-flash-high \
  --manage-agy-settings \
  --repetitions 3 \
  "$@"
