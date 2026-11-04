#!/usr/bin/env bash
# Resolve this plugin's user data directory (the private overlay).
#
#   scripts/paths.sh           -> data dir and which rule picked it
#   scripts/paths.sh dir       -> data dir only
#   scripts/paths.sh defaults  -> path of the user's defaults.md, exit 1 if there is none
#   scripts/paths.sh notebook  -> research notebook dir: the `notebook:` line of defaults.md, else <data dir>/notebook
#
# Data dir, first match wins:
#   1. $BATCH_INFERENCE_HOME
#   2. $CLAUDE_USER_DATA/batch-inference
#   3. ~/.claude-user-data/batch-inference                          if ~/.claude-user-data exists
#   4. ${XDG_DATA_HOME:-~/.local/share}/claude-plugins/batch-inference  if that root exists
#   5. ~/.claude-user-data/batch-inference
set -euo pipefail
NAME=batch-inference
XDG_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/claude-plugins"
if [[ -n "${BATCH_INFERENCE_HOME:-}" ]]; then DIR="$BATCH_INFERENCE_HOME"; RULE="BATCH_INFERENCE_HOME"
elif [[ -n "${CLAUDE_USER_DATA:-}" ]]; then DIR="$CLAUDE_USER_DATA/$NAME"; RULE="CLAUDE_USER_DATA"
elif [[ -d "$HOME/.claude-user-data" ]]; then DIR="$HOME/.claude-user-data/$NAME"; RULE="existing ~/.claude-user-data"
elif [[ -d "$XDG_ROOT" ]]; then DIR="$XDG_ROOT/$NAME"; RULE="existing $XDG_ROOT"
else DIR="$HOME/.claude-user-data/$NAME"; RULE="default"; fi

case "${1:-}" in
  dir) echo "$DIR" ;;
  defaults) [[ -f "$DIR/defaults.md" ]] && echo "$DIR/defaults.md" || exit 1 ;;
  notebook)
    NB=""
    [[ -f "$DIR/defaults.md" ]] && NB=$(sed -nE 's/^notebook:[[:space:]]*//p' "$DIR/defaults.md" | head -1)
    NB="${NB/#\~/$HOME}"
    echo "${NB:-$DIR/notebook}" ;;
  "") echo "$DIR ($RULE)" ;;
  *) echo "usage: paths.sh [dir|defaults|notebook]" >&2; exit 2 ;;
esac
