#!/usr/bin/env bash
# Claude Code statusline — Andromeda theme. Portable (Linux + macOS).
# Reads session JSON on stdin, emits a single ANSI-colored line.

input=$(cat)

# --- Andromeda palette (24-bit ANSI) ---
CYAN=$'\033[38;2;0;232;198m'      # #00E8C6 — active / model
MUTED=$'\033[38;2;103;118;145m'   # #677691 — secondary
PURPLE=$'\033[38;2;176;132;235m'  # #B084EB — branch (clean)
GREEN=$'\033[38;2;168;255;96m'    # #A8FF60 — good
YELLOW=$'\033[38;2;255;230;109m'  # #FFE66D — warn
RED=$'\033[38;2;238;93;67m'       # #EE5D43 — critical / dirty
RESET=$'\033[0m'

# --- Parse stdin ---
model=$(echo "$input" | jq -r '.model.display_name // .model.id // "claude"' | sed -E 's/ *\(1M context\)//')
cwd=$(echo "$input"  | jq -r '.workspace.current_dir // .cwd // empty')
transcript=$(echo "$input" | jq -r '.transcript_path // empty')

# --- CWD: replace $HOME with ~ ---
display_cwd="${cwd/#$HOME/\~}"

# --- Git branch + dirty state ---
git_segment=""
if [[ -n "$cwd" ]] && git -C "$cwd" rev-parse --git-dir >/dev/null 2>&1; then
  branch=$(git -C "$cwd" branch --show-current 2>/dev/null)
  [[ -z "$branch" ]] && branch=$(git -C "$cwd" rev-parse --short HEAD 2>/dev/null)
  if [[ -n "$(git -C "$cwd" status --porcelain 2>/dev/null)" ]]; then
    git_segment="${RED} ${branch}*${RESET}"
  else
    git_segment="${PURPLE} ${branch}${RESET}"
  fi
fi

# --- Portable reverse-cat: GNU `tac` or BSD `tail -r` ---
reverse_lines() {
  if command -v tac >/dev/null 2>&1; then
    tac "$1"
  else
    tail -r "$1"
  fi
}

# --- Token usage from latest assistant message in transcript ---
token_segment=""
if [[ -n "$transcript" && -f "$transcript" ]]; then
  usage=$(reverse_lines "$transcript" 2>/dev/null | while IFS= read -r line; do
    u=$(echo "$line" | jq -r '
      .message.usage // empty
      | (.input_tokens // 0)
        + (.cache_read_input_tokens // 0)
        + (.cache_creation_input_tokens // 0)
        + (.output_tokens // 0)
    ' 2>/dev/null)
    if [[ -n "$u" && "$u" != "0" ]]; then
      echo "$u"
      break
    fi
  done)

  if [[ -n "$usage" ]]; then
    limit=200000
    pct=$(( usage * 100 / limit ))
    if   (( pct >= 80 )); then color="$RED"
    elif (( pct >= 50 )); then color="$YELLOW"
    else                       color="$GREEN"
    fi
    k=$(( usage / 1000 ))
    token_segment="${color}󰍛 ${k}k/200k${RESET}"
  fi
fi

# --- Compose ---
printf "%s󰚩 %s%s  %s%s%s%s%s" \
  "$CYAN" "$model" "$RESET" \
  "$MUTED" "$display_cwd" "$RESET" \
  "$git_segment" \
  "${token_segment:+  $token_segment}"
