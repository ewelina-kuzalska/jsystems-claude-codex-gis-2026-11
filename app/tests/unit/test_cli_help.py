from typer.testing import CliRunner

from map_qa.cli import app


def test_help_exits_zero_and_is_polish():
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "run" in result.output


def test_run_help_lists_options():
    result = CliRunner().invoke(app, ["run", "--help"])
    assert result.exit_code == 0
    for opt in ("--input", "--output", "--with-signs", "--max-requests", "--threshold", "--yes"):
        assert opt in result.output
