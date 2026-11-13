"""Unit tests for Durable Agent CLI entrypoint."""

import pytest

from durable_agent.cli import main


def test_cli_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        # Pass no args to trigger help
        import sys

        sys.argv = ["durable-agent"]
        main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Durable Agentic OS" in captured.out


def test_cli_token_generation(capsys: pytest.CaptureFixture[str]) -> None:
    import sys

    sys.argv = [
        "durable-agent",
        "token",
        "--workflow-id",
        "wf-test-token",
        "--action",
        "BUY",
        "--notional",
        "18000.0",
    ]
    main()
    captured = capsys.readouterr()
    assert "Generated Cryptographic Approval Token:" in captured.out
    assert "wf-test-token:BUY:18000.00:" in captured.out
