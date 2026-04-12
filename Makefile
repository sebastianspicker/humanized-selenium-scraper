SHELL := /bin/bash

.PHONY: ci format-check lint type test security dependency-audit

ci: format-check lint type test

format-check:
	ruff format --check .

lint:
	ruff check .

type:
	mypy humanized_selenium_scraper

test:
	python -m pytest -q

security:
	bandit -r humanized_selenium_scraper -x tests --severity-level medium

dependency-audit:
	pip-audit -r requirements.txt
