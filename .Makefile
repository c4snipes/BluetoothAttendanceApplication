# Makefile for Bluetooth-Based Attendance Application

# Variables
PYTHON = python3
PIP = pip3
VENV_DIR = venv
SRC_DIR = .
MAIN_SCRIPT = main.py
REQUIREMENTS_FILE = requirements.txt

# Default target
.PHONY: all
all: run

# Create virtual environment
.PHONY: venv
venv:
    $(PYTHON) -m venv $(VENV_DIR)

# Install dependencies
.PHONY: install
install: venv
    $(VENV_DIR)/bin/$(PIP) install -r $(REQUIREMENTS_FILE)

# Run the application
.PHONY: run
run: install
    $(VENV_DIR)/bin/$(PYTHON) $(MAIN_SCRIPT)

# Clean up
.PHONY: clean
clean:
    rm -rf $(VENV_DIR)
    find . -type f -name '*.pyc' -delete
    find . -type d -name '__pycache__' -delete

# Run tests
.PHONY: test
test:
    $(VENV_DIR)/bin/$(PYTHON) -m unittest discover -s tests

# Lint the code
.PHONY: lint
lint:
    $(VENV_DIR)/bin/$(PYTHON) -m flake8 $(SRC_DIR)

# Format the code
.PHONY: format
format:
    $(VENV_DIR)/bin/$(PYTHON) -m black $(SRC_DIR)

# Check for security issues
.PHONY: security
security:
    $(VENV_DIR)/bin/$(PYTHON) -m bandit -r $(SRC_DIR)

# Generate documentation
.PHONY: docs
docs:
    $(VENV_DIR)/bin/$(PYTHON) -m pdoc --html --output-dir docs $(SRC_DIR)