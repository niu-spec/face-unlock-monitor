#!/usr/bin/env bash
# Shared frontend CI entry — used by Jenkins and GitHub Actions.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/frontend"

npm ci
npm run build
