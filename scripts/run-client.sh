#!/usr/bin/env bash
# Run the Python client demo against a running server.
#
# Assumes a server is already listening. Point it elsewhere with:
#   GRPC_TARGET=127.0.0.1:50051 bash scripts/run-client.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CLIENT_DIR="$REPO_ROOT/client"

# The client lives under client/src; put it on the path so `python -m` finds it.
export PYTHONPATH="$CLIENT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"

exec uv run --project "$CLIENT_DIR" python -m bookstore_client
