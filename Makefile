SOURCE_FILES := src/frico/*.py tests/*.py
BLUE := \033[1;34m
GREEN := \033[1;32m
NOCOLOR := \033[0m
FRAME_TOP := ┏━┅┉
FRAME_BOTTOM := ┗━┅┉
STEP_TOP := @echo "$(BLUE)$(FRAME_TOP)$(NOCOLOR)"
STEP_BOTTOM := @echo "$(BLUE)$(FRAME_BOTTOM)$(NOCOLOR)"
SUCCESS := @echo "$(GREEN)$(FRAME_TOP)\n┋ All tests complete: success! \n$(FRAME_BOTTOM)"

# update venv if requirements have changed
# note that make doesnt understand `source` so using .venv/bin/<bin>
.venv/bin/activate: requirements.in
	$(STEP_TOP)
	@echo "$(BLUE)┋ Development environment not found, setting it up.$(NOCOLOR)"
	@echo "$(BLUE)┋ Creating venv...$(NOCOLOR)"
	@python3 -m venv .venv
	@echo "$(BLUE)┋ Installing pip-tools...$(NOCOLOR)"
	@.venv/bin/python3 -m pip install pip-tools
	@echo "$(BLUE)┋ Compiling pinned dependencies...$(NOCOLOR)"
	@CUSTOM_COMPILE_COMMAND="make" .venv/bin/python3 -m piptools compile requirements.in
	@echo "$(BLUE)┋ Installing all requirements...$(NOCOLOR)"
	@.venv/bin/python3 -m pip install -r requirements.txt
	$(STEP_BOTTOM)

.PHONY: clean
clean:
	@rm -rf .venv


.PHONY: check-requirements
check-requirements: requirements.txt requirements.in
	@git diff-files --quiet requirements.txt
	TXT_CHANGED=$$?
	@git diff-files --quiet requirements.in
	IN_CHANGED=$$?
	@expr($IN_CHANGED=$OUT_CHANGED) || echo "requirements.in and requirements.txt out of sync" exit 1;

# TODO: make this less repetitive
.PHONY: format
format:
	$(STEP_TOP)
	@echo "$(BLUE)┋ Formatting...$(NOCOLOR)"
	@echo "isort `.venv/bin/isort --version-number)`"
	@.venv/bin/isort $(SOURCE_FILES)
	@.venv/bin/black --version
	@.venv/bin/black $(SOURCE_FILES)
	$(STEP_BOTTOM)

.PHONY: format-check
# for CI use, bail out of anything needs to be reformatted
format-check:
	$(STEP_TOP)
	@echo "$(BLUE)┋ Checking format...$(NOCOLOR)"
	@echo "isort `.venv/bin/isort --version-number)`"
	@.venv/bin/isort --diff $(SOURCE_FILES)
	@.venv/bin/isort --check-only $(SOURCE_FILES)
	@.venv/bin/black --version
	@.venv/bin/black --check $(SOURCE_FILES)
	$(STEP_BOTTOM)

.PHONY: lint
lint:
	$(STEP_TOP)
	@echo "$(BLUE)┋ Linting...$(NOCOLOR)"
	@echo "flake8 `.venv/bin/flake8 --version)`"
	@.venv/bin/flake8 $(SOURCE_FILES)
	@echo "$(GREEN)No complaints."
	$(STEP_BOTTOM)

.PHONY: typecheck
typecheck:
	$(STEP_TOP)
	@echo "$(BLUE)┋ Type checking...$(NOCOLOR)"
	@.venv/bin/mypy --version
	@.venv/bin/mypy $(SOURCE_FILES)
	$(STEP_BOTTOM)

.PHONY: unit
unit:
	$(STEP_TOP)
	@echo "$(BLUE)┋ Running unit and doc tests...$(NOCOLOR)"
	@.venv/bin/pytest
	$(STEP_BOTTOM)
	$(SUCCESS)

.PHONY: test
# will install venv if needed
test: .venv/bin/activate format lint typecheck unit

.PHONY: test-ci
test-ci: .venv/bin/activate format-check lint typecheck unit
