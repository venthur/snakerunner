.PHONY: all
all: lint test

.PHONY: test
test:
	pytest

.PHONY: lint
lint:
	flake8

.PHONY: clean
clean:
	find . -type f -name *.pyc -delete
	find . -type d -name __pycache__ -delete
	rm -rf htmlcov
