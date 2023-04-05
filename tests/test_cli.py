import json
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from substitute import main

SCRIPT = Path(__file__).resolve().parents[1] / "substitute.py"


@pytest.fixture
def source(tmp_path):
    path = tmp_path / "input.json"
    path.write_text('{"name": "Sample", "nested": {"value": 1}}', encoding="utf-8")
    return path


def run_cli(*args):
    """Run main() and return its exit status, whether it returns or exits."""
    try:
        return main([str(arg) for arg in args])
    except SystemExit as stopped:
        return stopped.code


def test_script_runs_as_a_standalone_file(source, tmp_path):
    output = tmp_path / "output.json"
    finished = subprocess.run(
        [sys.executable, str(SCRIPT), str(source), str(output)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert finished.returncode == 0, finished.stderr
    assert json.loads(output.read_text())["nested"]["value"]["_content"] == 1


def test_output_is_indented_utf8_with_a_final_newline(tmp_path):
    source = tmp_path / "input.json"
    source.write_text(json.dumps({"name": "café"}), encoding="utf-8")
    output = tmp_path / "output.json"
    assert run_cli(source, output) == 0
    text = output.read_bytes().decode("utf-8")
    assert '"_content": "café"' in text
    assert text.startswith('{\n  "name"')
    assert text.endswith("}\n")


def test_depth_option_matches_the_legacy_positional_depth(source, tmp_path):
    by_option = tmp_path / "option.json"
    by_position = tmp_path / "position.json"
    assert run_cli("--depth", "1", source, by_option) == 0
    assert run_cli(source, "1", by_position) == 0
    assert by_option.read_text() == by_position.read_text()
    assert json.loads(by_option.read_text())["nested"] == {"value": 1}


def test_lists_pass_through_the_cli_as_leaves(tmp_path):
    source = tmp_path / "input.json"
    source.write_text('{"items": [{"id": 1}]}')
    output = tmp_path / "output.json"
    assert run_cli(source, output) == 0
    assert json.loads(output.read_text()) == {
        "items": {"_content": [{"id": 1}], "_type": "<class 'list'>"}
    }


def test_output_may_overwrite_the_input_file(source):
    assert run_cli(source, source) == 0
    assert json.loads(source.read_text())["name"]["_content"] == "Sample"


@pytest.mark.parametrize(
    "args",
    [
        ["--depth", "1", "in.json", "2", "out.json"],
        ["--depth", "-1", "in.json", "out.json"],
        ["in.json", "x", "out.json"],
    ],
)
def test_bad_depth_arguments_are_usage_errors(args, capsys):
    assert run_cli(*args) == 2
    assert "depth" in capsys.readouterr().err


def test_help_explains_depth_and_shows_examples(capsys):
    assert run_cli("--help") == 0
    text = capsys.readouterr().out
    assert "--depth N" in text
    assert "examples:" in text


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("{broken", "Expecting property name"),
        ("", "Expecting value"),
        ('{"a": 1} trailing', "Extra data"),
        ('{"a": NaN}', "NaN is not valid JSON"),
        ('{"a": -Infinity}', "-Infinity is not valid JSON"),
        ("[1, 2]", "must be a JSON object"),
    ],
)
def test_invalid_json_exits_2_and_leaves_existing_output_alone(
    tmp_path, capsys, content, message
):
    source = tmp_path / "input.json"
    source.write_text(content)
    output = tmp_path / "output.json"
    output.write_text("keep-existing-output")
    assert run_cli(source, output) == 2
    assert message in capsys.readouterr().err
    assert output.read_text() == "keep-existing-output"


def test_parse_errors_name_the_input_file(tmp_path, capsys):
    source = tmp_path / "broken.json"
    source.write_text("{broken")
    assert run_cli(source, tmp_path / "out.json") == 2
    assert "broken.json: Expecting property name" in capsys.readouterr().err


def test_invalid_utf8_is_reported(tmp_path, capsys):
    source = tmp_path / "input.json"
    source.write_bytes(b'{"a": "\xff"}')
    assert run_cli(source, tmp_path / "out.json") == 2
    assert "utf-8" in capsys.readouterr().err


def test_utf8_byte_order_mark_is_accepted(tmp_path):
    source = tmp_path / "input.json"
    source.write_bytes(b'\xef\xbb\xbf{"a": 1}')
    output = tmp_path / "output.json"
    assert run_cli(source, output) == 0
    assert json.loads(output.read_text())["a"]["_content"] == 1


def test_missing_input_file_exits_2_without_creating_output(tmp_path, capsys):
    output = tmp_path / "output.json"
    assert run_cli(tmp_path / "missing.json", output) == 2
    assert "missing.json" in capsys.readouterr().err
    assert not output.exists()


def test_too_deep_input_reports_nesting_not_a_traceback(tmp_path, capsys):
    source = tmp_path / "deep.json"
    source.write_text('{"a":' * 100_000 + "1" + "}" * 100_000)
    assert run_cli(source, tmp_path / "out.json") == 2
    assert "nested too deeply" in capsys.readouterr().err


def test_overwrite_keeps_permissions_and_leaves_no_temp_files(source, tmp_path):
    output = tmp_path / "output.json"
    output.write_text("old")
    output.chmod(0o640)
    assert run_cli(source, output) == 0
    assert stat.S_IMODE(output.stat().st_mode) == 0o640
    assert sorted(p.name for p in tmp_path.iterdir()) == ["input.json", "output.json"]


def test_failed_replace_keeps_the_old_output_and_cleans_up(source, tmp_path, capsys):
    output = tmp_path / "output"
    output.mkdir()
    assert run_cli(source, output) == 2
    assert "output" in capsys.readouterr().err
    assert sorted(p.name for p in tmp_path.iterdir()) == ["input.json", "output"]


def test_symlinked_output_updates_the_link_target(source, tmp_path):
    real = tmp_path / "real.json"
    real.write_text("old")
    link = tmp_path / "link.json"
    link.symlink_to(real)
    assert run_cli(source, link) == 0
    assert link.is_symlink()
    assert json.loads(real.read_text())["name"]["_content"] == "Sample"


def test_missing_output_directory_names_the_output_path(source, tmp_path, capsys):
    assert run_cli(source, tmp_path / "nowhere" / "out.json") == 2
    assert "nowhere/out.json" in capsys.readouterr().err
