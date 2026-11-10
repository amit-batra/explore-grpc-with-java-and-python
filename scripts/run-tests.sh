#!/usr/bin/env bash
# End-to-end test flow, fully self-contained:
#   1. Restore the seed data so the run is deterministic.
#   2. Build the Java server.
#   3. Start the server (in the background) against a data copy.
#   4. Wait until the gRPC port accepts connections.
#   5. Run the pytest suite.
#   6. Stop the server (always, even on failure).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CLIENT_DIR="$REPO_ROOT/client"

PORT="${BOOKSTORE_PORT:-50051}"
export BOOKSTORE_PORT="$PORT"
# Back the store with the live data file; the test restores the seed first.
export BOOKS_DATA_FILE="$REPO_ROOT/data/books.json"
export GRPC_TARGET="127.0.0.1:$PORT"
export PYTHONPATH="$CLIENT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"

SERVER_PID=""
cleanup() {
    if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

# 1. Deterministic starting state.
cp "$REPO_ROOT/data/books.json.seed" "$REPO_ROOT/data/books.json"

# 1b. Ensure the client venv exists and the stubs are generated (idempotent), so
#     the flow works even after `make clean`.
uv sync --project "$CLIENT_DIR" >/dev/null
bash "$SCRIPT_DIR/generate-proto.sh" >/dev/null

# 2. Build (build-server.sh builds the distribution if needed).
bash "$SCRIPT_DIR/build-server.sh"

# 3. Start the server in the background.
bash "$SCRIPT_DIR/run-server.sh" &
SERVER_PID=$!
echo "Started server (pid $SERVER_PID) on port $PORT"

# 4. Wait for the port to accept connections.
wait_for_port() {
    local py="$CLIENT_DIR/.venv/bin/python"
    for _ in $(seq 1 60); do
        if "$py" -c "
import socket, sys
s = socket.socket(); s.settimeout(1)
try:
    s.connect(('127.0.0.1', int(sys.argv[1]))); s.close(); sys.exit(0)
except OSError:
    sys.exit(1)
" "$PORT" 2>/dev/null; then
            return 0
        fi
        sleep 1
    done
    echo "Timed out waiting for port $PORT" >&2
    return 1
}
wait_for_port

# 5. Run the tests.
uv run --project "$CLIENT_DIR" pytest "$CLIENT_DIR/tests" -v
