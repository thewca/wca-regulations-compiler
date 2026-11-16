.PHONY: check
check: lint test

.PHONY: test
test: test-regulations test-states

.PHONY: test-regulations
test-regulations:
	uv run wrc --target html -- ./test/samples/plus_n/wca-regulations.md
	uv run wrc --target html -- ./test/samples/multiplus/wca-regulations.md
	uv run -- ./test/mixed_guidelines.py

.PHONY: test-states
test-states:
	echo "from wrc.wrc import states; states()" | uv run -- - ./test/samples/states/wca-states.md --target=json

.PHONY: lint
lint:
	uv run ruff check

.PHONY: format
format:
	uv run ruff check
