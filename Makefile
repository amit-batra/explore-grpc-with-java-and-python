# Top-level automation for the gRPC Book Store demo.
#
# Each target delegates to the matching script under scripts/ (or an inline
# command). Scripts remain usable on their own.
.DEFAULT_GOAL := help

REPO_ROOT := $(shell pwd)

.PHONY: help proto setup build server client test clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

proto: ## Regenerate the Python gRPC stubs from proto/bookstore.proto
	bash scripts/generate-proto.sh

setup: proto ## Sync the client venv and regenerate the stubs
	@uv sync --project client

build: ## Build the Java server distribution
	bash scripts/build-server.sh

server: build ## Run the Java gRPC server in the foreground
	bash scripts/run-server.sh

client: proto ## Run the Python client demo (regenerates stubs; assumes a running server)
	bash scripts/run-client.sh

test: ## Self-contained: seed, build, run server, run pytest, stop server
	bash scripts/run-tests.sh

clean: ## Remove build artifacts and generated stubs
	rm -rf server/build server/.gradle
	rm -rf client/src/bookstore_client/stubs/bookstore_pb2.py \
	       client/src/bookstore_client/stubs/bookstore_pb2_grpc.py
	@echo "cleaned"
