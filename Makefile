.DEFAULT_GOAL := help
export OPENSPEC_TELEMETRY := 0

.PHONY: help setup generate interactive test lint fmt openspec status check changelog-check changelog-draft changelog-build release-check build water-benchmark overview-reference regional-reference world-create world-info world-overview world-select region-export

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

regional-reference: ## Export six regional fixtures, check seams and measure resources (fresh OUT)
	uv run python scripts/regional_reference.py $(OUT)/regional-reference

world-create: ## Create a project (PROJECT=path ARGS="--seed 42 --geometry flat ...")
	$(if $(PROJECT),,$(error PROJECT is required))
	uv run python -m pixel_world world-create --project "$(PROJECT)" $(ARGS)

world-info: ## Resume and inspect project settings and coverage (PROJECT=path)
	$(if $(PROJECT),,$(error PROJECT is required))
	uv run python -m pixel_world world-info --project "$(PROJECT)" $(ARGS)

world-overview: ## Export a project's optional overview (PROJECT=path)
	$(if $(PROJECT),,$(error PROJECT is required))
	uv run python -m pixel_world world-overview --project "$(PROJECT)" $(ARGS)

world-select: ## Select an overview position (PROJECT=path ARGS="--overview-x 10.5 --overview-y 20.5")
	$(if $(PROJECT),,$(error PROJECT is required))
	uv run python -m pixel_world world-select --project "$(PROJECT)" $(ARGS)

region-export: ## Export a saved world's region (PROJECT=path ARGS="--x 0 --y 0 --width 512 --height 512")
	$(if $(PROJECT),,$(error PROJECT is required))
	uv run python -m pixel_world region-export --project "$(PROJECT)" $(ARGS)
