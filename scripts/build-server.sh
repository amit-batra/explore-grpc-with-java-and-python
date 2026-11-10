#!/usr/bin/env bash
# Build the Java gRPC server into a launchable distribution.
#
# The protobuf-gradle-plugin downloads protoc and the grpc-java plugin itself, so
# no system-wide protoc install is required. The output lives under
# server/build/install/bookstore-server/ (a bin/ launcher plus a lib/ of jars).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$(cd "$SCRIPT_DIR/../server" && pwd)"

cd "$SERVER_DIR"
gradle installDist --console=plain

echo "Server built at server/build/install/bookstore-server/"
