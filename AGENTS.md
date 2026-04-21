# Repository Guidelines

## Project Structure & Module Organization

`mcp_toolkit/` contains the Python package. The main server entry point is `mcp_toolkit/server.py`, with CLI startup exposed through `mcp_toolkit/__main__.py`. Tool implementations live in `mcp_toolkit/tools/` (`web_search.py`, `run_python.py`, `run_js.py`, `memory.py`). Shared helpers live in `mcp_toolkit/utils/`, including sandboxing, logging, and browser utilities. Tests are in `tests/` and mirror tool or server behavior with files such as `test_server.py` and `test_web_search.py`.

## Build, Test, and Development Commands

Use `uv` for dependency and environment management.

- `uv sync`: install runtime and development dependencies from `pyproject.toml` and `uv.lock`.
- `uv run python -m playwright install chromium`: install the browser required by Playwright-backed web extraction.
- `uv run mcp-toolkit`: run the MCP server locally using the project script.
- `uv run mcp-toolkit --transport http --host 0.0.0.0 --port 8080`: run the streamable HTTP transport at `/mcp`.
- `uv run pytest`: run the full test suite.
- `uv build`: build distributable artifacts with Hatchling.

## Coding Style & Naming Conventions

Target Python 3.13. Use 4-space indentation, type hints for public functions, and concise async functions for MCP tools. Name modules and functions with `snake_case`; use descriptive tool names that match their exported MCP function names. Keep tool modules focused on one capability and put reusable cross-cutting behavior in `mcp_toolkit/utils/`.

## Testing Guidelines

The test suite uses `pytest` with `pytest-asyncio`; async tests are enabled automatically through `asyncio_mode = "auto"` in `pyproject.toml`. Add tests under `tests/` using the `test_*.py` naming pattern. Prefer focused tests for each tool plus integration coverage in `test_server.py` when registration, transport, or MCP behavior changes. Run `uv run pytest` before submitting changes.

## Commit & Pull Request Guidelines

Recent history uses Conventional Commit-style subjects, for example `feat: add centralized logging module` and `refactor(web_search): use httpx + trafilatura, Playwright as SPA fallback`. Keep commits small and use prefixes such as `feat:`, `fix:`, `refactor:`, or `test:`.

Pull requests should include a short description, the reason for the change, test results, and any setup impact such as new dependencies, Playwright requirements, or transport changes. Link related issues when available and include logs or screenshots only when they clarify user-visible behavior.

## Security & Configuration Tips

Sandboxed execution tools should keep strict timeout, memory, and network restrictions intact. Do not commit local virtual environments, caches, or memory databases. Persistent memory is stored outside the repo in the user data directory, so tests should isolate state with fixtures rather than relying on local data.
