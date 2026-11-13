# Contributing to Durable Agentic OS

Thank you for your interest in contributing to **Durable Agentic OS**!

## Code Standards
- **Python:** 3.11+ (Targeted at 3.12).
- **Code Style:** Formatted with `ruff format` and linted with `ruff check`.
- **Type Checking:** Strict `mypy` without untyped definitions.
- **Testing:** Comprehensive test suite run via `pytest`. All new features must include unit/integration tests with $\ge 80\%$ branch coverage.

## Development Workflow
1. Clone the repository.
2. Install development dependencies:
   ```bash
   uv sync --extra dev
   ```
3. Run test suite:
   ```bash
   uv run pytest
   ```
4. Run lint and type-checks:
   ```bash
   uv run ruff check .
   uv run mypy src
   ```

## Commit Conventions
We use [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` A new feature
- `fix:` A bug fix
- `docs:` Documentation updates
- `test:` Adding or updating tests
- `refactor:` Code change that neither fixes a bug nor adds a feature
