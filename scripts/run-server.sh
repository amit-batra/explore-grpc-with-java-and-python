#!/usr/bin/env bash
# Run the Java gRPC server in the foreground.
#
# Environment variables (all optional):
#   BOOKSTORE_PORT    Port to listen on (default 50051).
#   BOOKS_DATA_FILE   JSON file backing the store (default data/books.json,
#                     resolved relative to the current working directory).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVER_DIR="$REPO_ROOT/server"
DIST_BIN="$SERVER_DIR/build/install/bookstore-server/bin/bookstore-server"

if [ ! -x "$DIST_BIN" ]; then
    echo "Server not built yet. Running build-server.sh first..."
    bash "$SCRIPT_DIR/build-server.sh"
fi

exec "$DIST_BIN"
