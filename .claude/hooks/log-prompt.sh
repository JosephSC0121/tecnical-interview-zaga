#!/usr/bin/env bash
# UserPromptSubmit: append every prompt to the AI trail. Prints nothing, so no context is added.
set -euo pipefail

input=$(cat)
root="${CLAUDE_PROJECT_DIR:-$(jq -r '.cwd // empty' <<<"$input")}"
log="$root/ai-trail/prompts.md"

mkdir -p "$(dirname "$log")"
if [[ ! -f "$log" ]]; then
  printf '# Prompt log\n\nEvery prompt sent to Claude Code in this repository, appended by `.claude/hooks/log-prompt.sh`.\n' >"$log"
fi

session=$(jq -r '(.session_id // "unknown")[0:8]' <<<"$input")
{
  printf '\n## %s · session %s\n\n`````text\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')" "$session"
  jq -r '.prompt // ""' <<<"$input"
  printf '`````\n'
} >>"$log"
