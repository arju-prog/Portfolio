#!/usr/bin/env sh
# Stops every Next.js process (next dev / next start / next build) started from
# this project. Matches on working directory, so other apps and editors are left alone.

cd "$(dirname "$0")/.." || exit 1
root=$(pwd -P)

pids=""
for pid in $(pgrep -f 'next-server|next dev|next start|next build'); do
  cwd=$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p')
  [ "$cwd" = "$root" ] && pids="$pids $pid"
done

if [ -z "$pids" ]; then
  echo "No running Next.js processes for this project."
  exit 0
fi

echo "Stopping:$pids"
kill $pids 2>/dev/null
sleep 1
for pid in $pids; do
  kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null
done
echo "Done."
