# Development tasks for the cli-devops-with-ultimate-ui skill.
SKILL := skills/cli-devops-with-ultimate-ui
PY    := python3

CLAUDE_SKILLS := $(HOME)/.claude/skills
INSTALLED     := $(CLAUDE_SKILLS)/cli-devops-with-ultimate-ui

.PHONY: help test audit demo palette package install uninstall verify-install clean

help:
	@echo "test     run the template unit tests"
	@echo "audit    run the terminal hygiene harness against the demo tool"
	@echo "demo     render the component gallery in this terminal"
	@echo "palette  print the palette and its WCAG contrast table"
	@echo "package  build dist/cli-devops-with-ultimate-ui.skill for upload to Claude"
	@echo "install  copy the skill into ~/.claude/skills for Claude Code"
	@echo "uninstall remove it from ~/.claude/skills"
	@echo "verify-install  fail if the installed copy differs from this tree"
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
	# zip updates an existing archive instead of replacing it, so a stale entry
	# survives every rebuild until the file itself is removed.
	rm -f dist/cli-devops-with-ultimate-ui.skill
	mkdir -p dist
	# Zipped from a staging copy on the local disk, so the bundle carries the
	# skill and nothing the working tree accumulated around it.
	stage=$$(mktemp -d) && \
	cp -R $(SKILL)/. $$stage/ && \
	find $$stage \( -name '._*' -o -name '.DS_Store' \) -delete && \
	( cd $$stage && zip -qrX $(CURDIR)/dist/cli-devops-with-ultimate-ui.skill . \
		-x '*__pycache__*' '*.pyc' ) && \
	rm -rf $$stage
	@echo "built dist/cli-devops-with-ultimate-ui.skill"

install:
	mkdir -p $(CLAUDE_SKILLS)
	rm -rf $(INSTALLED)
	cp -R $(SKILL) $(INSTALLED)
	@echo "installed $(INSTALLED)"

uninstall:
	rm -rf $(INSTALLED)
	@echo "removed $(INSTALLED)"

# Drift between the repository and the installed copy is silent otherwise: the
# model lists a skill by name and then cannot load it.
verify-install:
	@test -d $(INSTALLED) || { echo "not installed; run: make install"; exit 1; }
	@diff -r -x '__pycache__' -x '*.pyc' -x '._*' -x '.DS_Store' $(SKILL) $(INSTALLED) >/dev/null \
		&& echo "installed copy matches the repository" \
		|| { echo "installed copy differs; run: make install"; exit 1; }

clean:
	find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name '*.pyc' -delete
	find . -name '._*' -not -path './.git/*' -delete 2>/dev/null || true
