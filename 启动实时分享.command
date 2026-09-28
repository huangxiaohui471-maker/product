#!/bin/zsh
set -e
cd "$(dirname "$0")"
PORT="${1:-8767}"
exec python3 sync_server.py --host 0.0.0.0 --port "$PORT"
