#!/bin/bash
set -euo pipefail
umask 077
cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
state="$HOME/Library/Application Support/Montara JM Reel"
export MONTARA_COMPANION_HOME="$state/Companion"
export MONTARA_COMPANION_PORT=47829
export MONTARA_COMPANION_ORIGINS='http://127\.0\.0\.1:8100'
python="$MONTARA_COMPANION_HOME/video/venv/bin/python"
test -x "$python"
if ! /usr/sbin/lsof -nP -iTCP:47829 -sTCP:LISTEN >/dev/null 2>&1; then
  "$python" companion/companion.py >>"$state/companion.log" 2>&1 &
  companion_pid=$!
  trap 'kill "$companion_pid" 2>/dev/null || true' EXIT
fi
"$python" app.py --host 127.0.0.1 --port 8100 --data "$state/Projects" --no-samples
