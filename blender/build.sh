#!/usr/bin/env sh
# Rebuilds every figure: blender/characters/<id>.py -> public/models/<id>.glb + <id>.png
# Usage: pnpm models            (all)
#        pnpm models luffy asta (some)
# Set BLENDER=/path/to/blender if Blender isn't in the default macOS location.

cd "$(dirname "$0")/.." || exit 1
BLENDER=${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}
command -v "$BLENDER" >/dev/null 2>&1 || [ -x "$BLENDER" ] || { echo "Blender not found. Set BLENDER=/path/to/blender"; exit 1; }

if [ $# -gt 0 ]; then
  scripts=$(for id in "$@"; do echo "blender/characters/$id.py"; done)
else
  scripts=$(ls blender/characters/*.py | grep -v '/_')
fi

status=0
for script in $scripts; do
  echo "→ $(basename "$script" .py)"
  out=$("$BLENDER" -b --factory-startup -P "$script" 2>&1)
  echo "$out" | grep '\[kit\]' || { echo "$out" | grep -E 'Error|Traceback' -A3; status=1; }
done
exit $status
