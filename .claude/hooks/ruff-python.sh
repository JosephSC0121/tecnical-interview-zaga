#!/usr/bin/env bash
# PostToolUse: format and lint every edited .py file. Remaining lint errors go back to Claude.
set -uo pipefail

input=$(cat)
root="${CLAUDE_PROJECT_DIR:-$(jq -r '.cwd // empty' <<<"$input")}"
path=$(jq -r '.tool_response.filePath // .tool_input.file_path // empty' <<<"$input")

[[ "$path" == *.py && -f "$path" ]] || exit 0
[[ "$path" == "$root/upstream/"* ]] && exit 0

uvx ruff format --quiet "$path" >&2 || exit 2
if ! output=$(uvx ruff check --fix --unfixable F401 --quiet "$path" 2>&1); then
  printf 'ruff check found problems it could not fix in %s:\n%s\n' "$path" "$output" >&2
  exit 2
fi
