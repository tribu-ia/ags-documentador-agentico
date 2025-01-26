# Variables
PYTHON = python3.11
POETRY = poetry
UVICORN = uvicorn
APP = main:app
PORT = 8098
HOST = 0.0.0.0
WORKERS = 2

# Install dependencies
install:
	$(POETRY) install

# Run application
run:
	$(UVICORN) $(APP) --host $(HOST) --port $(PORT)

run-reload:
	$(UVICORN) $(APP) --host $(HOST) --port $(PORT) --reload

# Run tests
test:
	$(POETRY) run pytest

# Lint and format code
lint:
	$(POETRY) run flake8 .
format:
	$(POETRY) run black .

# Check type hints
type-check:
	$(POETRY) run mypy .

# Generate requirements.txt
gen-req:
	$(POETRY) export --without-hashes --output requirements.txt

# Clean up files
clean:
	find . -name "__pycache__" -exec rm -rf {} +
	find . -name "*.pyc" -exec rm -f {} +

# Run additional tasks
run-agent:
	langgraph dev

# Help
default:
	@echo "Available targets:"
	@echo "  install       Install dependencies"
	@echo "  run           Run the application"
	@echo "  test          Run tests"
	@echo "  lint          Lint the code"
	@echo "  format        Format the code"
	@echo "  type-check    Check type hints"
	@echo "  gen-req       Generate requirements.txt"
	@echo "  clean         Clean up temporary files"
	@echo "  run-agent     Run the langgraph agent"
	@echo "  run-api       Run the fastapi application"
