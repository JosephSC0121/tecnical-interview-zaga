#!/usr/bin/env bash
# PreToolUse: upstream/ belongs to another team and must never be modified.
set -euo pipefail

input=$(cat)
root="${CLAUDE_PROJECT_DIR:-$(jq -r '.cwd // empty' <<<"$input")}"
tool=$(jq -r '.tool_name // empty' <<<"$input")

deny() {
  jq -n --arg reason "$1" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: $reason
    }
  }'
  exit 0
}

case "$tool" in
  Edit | Write | NotebookEdit)
    path=$(jq -r '.tool_input.file_path // .tool_input.notebook_path // empty' <<<"$input")
    [[ "$path" != /* ]] && path="$root/$path"
    if [[ "$path" == "$root/upstream" || "$path" == "$root/upstream/"* ]]; then
      deny "upstream/ is owned by another team and must not be modified (constitution, principle I). Change our backend instead."
    fi
    ;;
  Bash)
    command=$(jq -r '.tool_input.command // empty' <<<"$input")
    # Heuristic: redirections into upstream/ and commands that write or delete there.
    # Reading and running it (cd upstream && uv run ...) stays allowed.
    if grep -Eq '(>>?|\b(tee|rm|mv|touch|sed[[:space:]]+-i[^[:space:]]*|git[[:space:]]+(checkout|restore|apply|rm|mv))\b)[^|;&]*upstream/' <<<"$command"; then
      deny "This command looks like it writes to upstream/, which must not be modified (constitution, principle I)."
    fi
    ;;
esac
