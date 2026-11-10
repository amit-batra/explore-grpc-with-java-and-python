#!/usr/bin/env bash
# Regenerate the Python gRPC stubs from the shared proto file.
#
# Uses grpcio-tools (a dev dependency of the client), which bundles its own
# protoc, so no system-wide protoc install is required. The output is the flat
# bookstore_pb2.py / bookstore_pb2_grpc.py pair that the client imports.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROTO_DIR="$REPO_ROOT/proto"
OUT_DIR="$REPO_ROOT/client/src/bookstore_client/stubs"

mkdir -p "$OUT_DIR"

uv run --project "$REPO_ROOT/client" python -m grpc_tools.protoc \
  -I "$PROTO_DIR" \
  --python_out="$OUT_DIR" \
  --grpc_python_out="$OUT_DIR" \
  "$PROTO_DIR/bookstore.proto"

echo "Python stubs generated at client/src/bookstore_client/stubs/"
