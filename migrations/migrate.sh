#!/usr/bin/env bash
#
# Applies the pending schema migrations. Same arguments as migrate.py:
#
#     ./migrations/migrate.sh --dry-run
#     ./migrations/migrate.sh
#
# Changes into the project root first, so .streamlit/secrets.toml is found
# relative to the working directory, the same way Streamlit finds it.

set -euo pipefail
cd "$(dirname "$0")/.."
exec "${PYTHON:-python3}" migrations/migrate.py "$@"
