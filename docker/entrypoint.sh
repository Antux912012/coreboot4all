#!/usr/bin/env bash
# Entry point for the cb4a builder image.
set -euo pipefail

# Make the build reproducible.
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1700000000}"
export LANG=C
export LC_ALL=C
export TZ=UTC0

# Give a clear error when the host did not mount the work tree.
if [ ! -d /work ]; then
  echo "E-01: /work is not mounted. Start the container with docker compose." >&2
  exit 25
fi

# When the user gives no command, show the help text.
if [ "$#" -eq 0 ]; then
  set -- cb4a --help
fi

exec "$@"
