.PHONY: check
check: lint test build check-package

.PHONY: build
build:
	uv run pyproject-build

.PHONY: test
test: test-regulations test-states test-languages

.PHONY: test-regulations
test-regulations:
	uv run -- wrc --target html -- ./test/samples/plus_n/wca-regulations.md
	uv run -- wrc --target html -- ./test/samples/multiplus/wca-regulations.md
	uv run -- ./test/mixed_guidelines.py

.PHONY: test-states
test-states:
	uv run -- wrc-states ./test/samples/states/wca-states.md --target=json

.PHONY: test-languages
test-languages:
	uv run -- wrc-languages

.PHONY: lint
lint:
	uv lock --check
	uv run ruff check

.PHONY: format
format:
	uv run ruff check

.PHONY: setup
setup:
	uv sync

.PHONY: clean
clean:
	rm -rf ./build/ ./dist/

.PHONY: reset
reset: clean
	rm -rf ./.ruff-cahe/ ./.venv/

.PHONY: check-package
check-package: build
	uv run twine check dist/*

.PHONY: publish
publish: build check-package
	uv run -- twine upload dist/*

.PHONY: version-bump-patch
version-bump-patch:
	uv version --bump patch

.PHONY: version-bump-minor
version-bump-minor:
	uv version --bump minor
