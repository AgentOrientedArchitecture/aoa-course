#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
case "$(uname -s)" in Linux) platform=linux;; Darwin) platform=darwin;; *) echo 'Use WSL2 for the course Directory lab.' >&2; exit 1;; esac
case "$(uname -m)" in aarch64|arm64) architecture=arm64;; x86_64) architecture=amd64;; *) echo 'Unsupported architecture' >&2; exit 1;; esac
mkdir -p .course-tools
binary=.course-tools/dirctl-1.8.0
if [[ ! -x "$binary" ]]; then
  curl --fail --location --silent --show-error "https://github.com/agntcy/dir/releases/download/v1.8.0/dirctl-$platform-$architecture" -o "$binary.download"
  chmod +x "$binary.download"
  mv "$binary.download" "$binary"
fi
"$binary" version
# Record the installed artefact hash for the run. This is provenance, not signature verification.
if command -v sha256sum >/dev/null; then sha256sum "$binary" > .course-tools/dirctl.sha256; else shasum -a 256 "$binary" > .course-tools/dirctl.sha256; fi
