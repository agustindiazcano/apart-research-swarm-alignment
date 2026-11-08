#!/usr/bin/env bash
# Launch Antigravity (agy) on one task in a worktree and wait until it exits.
# Usage: scripts/agy_launch.sh <worktree-dir> <prompt-file> <log-file> [model]
# Run it in the background (for example with the Bash tool option run_in_background).
set -u

if [ "$#" -lt 3 ]; then
  echo "usage: $0 <worktree-dir> <prompt-file> <log-file> [model]" >&2
  exit 2
fi

worktree="$1"
prompt="$2"
log="$3"
model="${4:-gemini-3.8-flash-high}"

cd "$worktree" || exit 2
echo "start $(date -u +%Y-%m-%dT%H:%M:%SZ) branch=$(git branch --show-current) model=$model" > "$log.start"

agy --dangerously-skip-permissions --model "$model" --print "$(cat "$prompt")" > "$log" 2>&1
code=$?
echo "agy exit code: $code" >> "$log"
exit "$code"
