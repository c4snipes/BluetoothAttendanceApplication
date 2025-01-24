# Define the Python virtual environment directory
VENV := .venv

# Default target
all: install run

install:
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install -r requirements.txt

run:
	$(VENV)/bin/python attendance_app/main.py

clean:
	rm -rf $(VENV)
	find . -name "__pycache__" -exec rm -rf {} +
