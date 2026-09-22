#!/bin/sh
set -eu

benchmark_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repository_url=https://github.com/pallets/flask.git
repository_commit=d318b683471101618febed18996405ad26462110
cache_root=${TLGF_REAL_REPO_CACHE:-/tmp/tlgf-real-repos}
source_dir="$cache_root/flask-source"
fixture_dir="$benchmark_dir/fixtures/.real-repos/flask-error-handlers-d318b683"
overlay_dir="$benchmark_dir/real-repo-overlays/flask-error-handlers"

if [ -d "$fixture_dir" ]; then
    test -f "$fixture_dir/LICENSE.txt"
    test -f "$fixture_dir/.tlgf/PROVENANCE.md"
    test -f "$fixture_dir/src/flask/sansio/app.py"
    test -f "$fixture_dir/tests/test_user_error_handler.py"
    echo "Prepared fixture already exists: $fixture_dir"
    exit 0
fi

mkdir -p "$cache_root"
if [ ! -d "$source_dir/.git" ]; then
    git clone --filter=blob:none --no-checkout "$repository_url" "$source_dir"
fi

if ! git -C "$source_dir" cat-file -e "$repository_commit^{commit}" 2>/dev/null; then
    git -C "$source_dir" fetch --depth 1 origin "$repository_commit"
fi

mkdir -p "$fixture_dir"
git -C "$source_dir" archive "$repository_commit" | tar -x -C "$fixture_dir"
cp -R "$overlay_dir/." "$fixture_dir/"

test -f "$fixture_dir/LICENSE.txt"
test -f "$fixture_dir/.tlgf/PROVENANCE.md"
test -f "$fixture_dir/src/flask/app.py"
test -f "$fixture_dir/src/flask/wrappers.py"
test -f "$fixture_dir/src/flask/sansio/app.py"
test -f "$fixture_dir/tests/test_user_error_handler.py"

echo "Prepared Flask $repository_commit at $fixture_dir"
