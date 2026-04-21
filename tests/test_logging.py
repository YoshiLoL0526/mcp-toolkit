import importlib
import logging


def test_logging_uses_env_level_and_file(tmp_path, monkeypatch):
    log_path = tmp_path / "mcp-toolkit.log"
    monkeypatch.setenv("MCP_LOG_LEVEL", "INFO")
    monkeypatch.setenv("MCP_LOG_FILE", str(log_path))

    import mcp_toolkit.utils.logging as logging_utils

    root = logging.getLogger("mcp_toolkit")
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()

    logging_utils = importlib.reload(logging_utils)
    logger = logging_utils.get_logger("mcp_toolkit.tests")

    logger.info("integration log message")

    assert root.level == logging.INFO
    assert log_path.exists()
    assert "integration log message" in log_path.read_text(encoding="utf-8")

    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()
