# Development tasks for the cli-craft skill.
SKILL := skills/cli-craft
PY    := python3

.PHONY: help test audit demo palette package clean

help:
	@echo "test     run the template unit tests"
	@echo "audit    run the terminal hygiene harness against the demo tool"
	@echo "demo     render the component gallery in this terminal"
	@echo "palette  print the palette and its WCAG contrast table"
	@echo "package  build dist/cli-craft.skill for upload to Claude"
	@echo "clean    remove build artifacts and caches"

test:
	cd $(SKILL)/assets/templates/python && $(PY) -m unittest -v test_ui

audit:
	cd $(SKILL) && $(PY) scripts/check_cli.py --timeout 30 -- $(PY) scripts/demo_gallery.py

demo:
	cd $(SKILL) && $(PY) scripts/demo_gallery.py

palette:
	cd $(SKILL) && $(PY) scripts/palette.py --contrast

package: clean
	mkdir -p dist
	cd $(SKILL) && zip -qr ../../dist/cli-craft.skill . -x '*__pycache__*' '*.pyc'
	@echo "built dist/cli-craft.skill"

clean:
	find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name '*.pyc' -delete
