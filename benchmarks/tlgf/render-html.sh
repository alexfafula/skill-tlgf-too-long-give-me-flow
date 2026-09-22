#!/bin/sh
set -eu

benchmark_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

if [ "$#" -lt 1 ]; then
  echo "Usage: benchmarks/tlgf/render-html.sh RUN_DIRECTORY [--output PATH]" >&2
  exit 2
fi

python3 "$benchmark_dir/../render_html.py" "$@"
