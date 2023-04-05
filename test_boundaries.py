import json
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from substitute import main, substitution


def test_depth_zero_preserves_dictionary_identity_and_values():
    original = {"nested": {"value": 3}, "value": 1}
    assert substitution(original, 0) is original
    assert original == {"nested": {"value": 3}, "value": 1}


def test_depth_one_only_wraps_root_leaves():
    assert substitution({"root": 1, "nested": {"value": 2}}, 1) == {
        "root": {"_content": 1, "_type": "<class 'int'>"},
        "nested": {"value": 2},
    }


def test_lists_are_whole_leaf_values_and_types_are_python_names():
    result = substitution({"items": [{"value": 1}], "ready": True, "empty": None})
    assert result["items"] == {"_content": [{"value": 1}], "_type": "<class 'list'>"}
    assert result["ready"]["_type"] == "<class 'bool'>"
    assert result["empty"]["_type"] == "<class 'NoneType'>"


@pytest.mark.parametrize("value", [[], None, 42])
def test_root_must_be_an_object(value):
    with pytest.raises(TypeError):
        substitution(value)


@pytest.mark.parametrize("depth", [-1, "one", True])
def test_invalid_depth_is_rejected(depth):
    with pytest.raises(ValueError, match="depth"):
        substitution({}, depth)


def test_invalid_input_does_not_truncate_existing_output(tmp_path):
    source = tmp_path / "input.json"
    source.write_text("{broken")
    output = tmp_path / "output.json"
    output.write_text("keep-existing-output")
    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).with_name("substitute.py")),
            str(source),
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert output.read_text() == "keep-existing-output"


def test_cli_preserves_legacy_depth_argument_and_unicode(tmp_path):
    source = tmp_path / "input.json"
    source.write_text(json.dumps({"name": "café", "nested": {"value": 1}}))
    output = tmp_path / "output.json"
    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).with_name("substitute.py")),
            str(source),
            "1",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert json.loads(output.read_text()) == {
        "name": {"_content": "café", "_type": "<class 'str'>"},
        "nested": {"value": 1},
    }


def run_cli(*args):
    with pytest.raises(SystemExit) as stopped:
        main([str(arg) for arg in args])
    return stopped.value.code


def test_nan_and_infinity_are_rejected_instead_of_echoed(tmp_path, capsys):
    source = tmp_path / "input.json"
    source.write_text('{"a": NaN, "b": Infinity}')
    output = tmp_path / "output.json"
    assert run_cli(source, output) == 2
    assert "NaN is not valid JSON" in capsys.readouterr().err
    assert not output.exists()


def test_utf8_byte_order_mark_is_accepted(tmp_path):
    source = tmp_path / "input.json"
    source.write_bytes(b'\xef\xbb\xbf{"a": 1}')
    output = tmp_path / "output.json"
    assert main([str(source), str(output)]) == 0
    assert json.loads(output.read_text()) == {
        "a": {"_content": 1, "_type": "<class 'int'>"}
    }


def test_parse_errors_name_the_input_file(tmp_path, capsys):
    source = tmp_path / "broken.json"
    source.write_text("{broken")
    assert run_cli(source, tmp_path / "out.json") == 2
    assert "broken.json: Expecting property name" in capsys.readouterr().err


def test_too_deep_input_reports_nesting_not_a_traceback(tmp_path, capsys):
    source = tmp_path / "deep.json"
    source.write_text('{"a":' * 100_000 + "1" + "}" * 100_000)
    assert run_cli(source, tmp_path / "out.json") == 2
    assert "nested too deeply" in capsys.readouterr().err


def test_overwrite_keeps_permissions_and_leaves_no_temp_files(tmp_path):
    source = tmp_path / "input.json"
    source.write_text('{"a": 1}')
    output = tmp_path / "output.json"
    output.write_text("old")
    output.chmod(0o640)
    assert main([str(source), str(output)]) == 0
    assert stat.S_IMODE(output.stat().st_mode) == 0o640
    assert sorted(p.name for p in tmp_path.iterdir()) == ["input.json", "output.json"]


def test_symlinked_output_updates_the_link_target(tmp_path):
    source = tmp_path / "input.json"
    source.write_text('{"a": 1}')
    real = tmp_path / "real.json"
    real.write_text("old")
    link = tmp_path / "link.json"
    link.symlink_to(real)
    assert main([str(source), str(link)]) == 0
    assert link.is_symlink()
    assert json.loads(real.read_text())["a"]["_content"] == 1


def test_missing_output_directory_names_the_output_path(tmp_path, capsys):
    source = tmp_path / "input.json"
    source.write_text('{"a": 1}')
    assert run_cli(source, tmp_path / "nowhere" / "out.json") == 2
    assert "nowhere/out.json" in capsys.readouterr().err
