.PHONY: test lint prek

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run pyrefly check

prek:
	uv run prek run --all-files

prek-install:
	uv run prek install