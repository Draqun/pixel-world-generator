.DEFAULT_GOAL := help
export OPENSPEC_TELEMETRY := 0

.PHONY: help setup generate interactive test lint fmt openspec status check changelog-check changelog-draft changelog-build release-check build water-benchmark overview-reference

SIZE ?= 1024
OUT ?= out
TARGET_BRANCH ?= main
VERSION = $(shell uv run python -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')
export TARGET_BRANCH

help: ## List targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-10s %s\n", $$1, $$2}'

setup: ## Install dependencies into .venv
	uv sync

generate: ## Generate a world (make generate SEED=42 [SIZE=1024] [OUT=out])
	$(if $(SEED),,$(error SEED is required, e.g. make generate SEED=42))
	uv run python -m pixel_world generate --seed $(SEED) --size $(SIZE) --out $(OUT) $(ARGS)

interactive: ## Configure, generate and preview a world in the terminal
	uv run python -m pixel_world interactive

test: ## Run tests (scope: make test ARGS="tests/test_x.py -k name")
	uv run pytest $(ARGS)

lint: ## Lint and check formatting
	uv run ruff check .
	uv run ruff format --check .

fmt: ## Format code
	uv run ruff format .

openspec: ## Validate all OpenSpec changes and specs
	openspec validate --all --strict

status: ## List active OpenSpec changes
	openspec list

check: lint test openspec ## Everything to run before a push

changelog-check: ## Require a fragment compared with TARGET_BRANCH (default main)
	uv run towncrier check --compare-with "origin/$$TARGET_BRANCH"

changelog-draft: ## Preview pending release notes without changing files
	uv run towncrier build --draft --version "$(VERSION)"

changelog-build: ## Consume fragments into CHANGELOG.md for the project version
	uv run towncrier build --yes --version "$(VERSION)"

release-check: ## Validate version agreement, unused tag and pending fragments
	@uv run python scripts/release_version.py

build: ## Build wheel and source distribution in dist/
	uv build

water-benchmark: ## Benchmark seed 42 water at 1024 and 2048; save diagnostic previews
	uv run python scripts/benchmark_water.py 1024 --preview $(OUT)/water-preview-1024.png
	uv run python scripts/benchmark_water.py 2048 --preview $(OUT)/water-preview-2048.png

overview-reference: ## Generate new seed-42 overview reference projects (choose a fresh OUT)
	uv run python scripts/overview_reference.py $(OUT)/overview-reference
