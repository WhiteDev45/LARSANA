#!/bin/bash
# Download/extract build tools without installing packages on the host.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .build/cache .build/rootfs dist
: > .build/empty-status
mapfile -t build_packages < packaging/build-dependencies.txt
apt-get --download-only --yes --no-install-recommends \
  -o "Dir::State::status=$PWD/.build/empty-status" \
  -o "Dir::Cache::archives=$PWD/.build/cache" -o Debug::NoLocking=true \
  install "${build_packages[@]}"
python3 tools/bootstrap_builder.py
python3 tools/builder_database.py
