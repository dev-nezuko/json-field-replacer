"""Wrap dictionary leaf values with their original value and Python type name."""

import argparse
import json
import os
import tempfile
from collections.abc import Sequence
from typing import Any

EPILOG = """\
examples:
  %(prog)s input.json result.json            wrap every leaf, at any depth
  %(prog)s --depth 1 input.json result.json  wrap only the root's leaves
  %(prog)s input.json 1 result.json          same, original argument order

Depth 0 leaves the object unchanged. Lists are leaves: their items are
not visited. The output file is replaced only after the whole result has
been built, so invalid input never truncates it.
"""


def substitution(
    dictionary: dict[Any, Any], depth: int | None = None, current_depth: int = 0
) -> dict[Any, Any]:
    """Mutate a dictionary; lists remain leaf values and depth zero is a no-op."""
    if not isinstance(dictionary, dict):
        raise TypeError("The input must be a JSON object.")
    if depth is not None and (type(depth) is not int or depth < 0):
        raise ValueError("depth must be a nonnegative integer or None.")

    def visit(node: dict[Any, Any], level: int) -> dict[Any, Any]:
        if depth is not None and level >= depth:
            return node
        for key, value in node.items():
            node[key] = (
                visit(value, level + 1)
                if isinstance(value, dict)
                else {"_content": value, "_type": str(type(value))}
            )
        return node

    return visit(dictionary, current_depth)


def _reject_constant(name: str) -> None:
    raise ValueError(f"{name} is not valid JSON")


def read_json(path: str) -> Any:
    """Parse strict JSON; a UTF-8 byte-order mark is accepted, NaN/Infinity are not."""
    with open(path, encoding="utf-8-sig") as source:
        try:
            return json.load(source, parse_constant=_reject_constant)
        except ValueError as error:
            raise ValueError(f"{path}: {error}") from error


def write_atomically(path: str, text: str) -> None:
    """Replace path in one step, so readers never see a half-written file."""
    target = os.path.realpath(path)
    directory = os.path.dirname(target)
    try:
        mode = os.stat(target).st_mode & 0o777
    except FileNotFoundError:
        umask = os.umask(0)
        os.umask(umask)
        mode = 0o666 & ~umask
    try:
        fd, temp_path = tempfile.mkstemp(dir=directory, prefix=".substitute-")
    except OSError as error:
        raise OSError(error.errno, error.strerror, path) from error
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as destination:
            destination.write(text)
        os.chmod(temp_path, mode)
        os.replace(temp_path, target)
    except BaseException:
        os.unlink(temp_path)
        raise


def _depth(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        value = -1
    if value < 0:
        raise argparse.ArgumentTypeError(f"must be a nonnegative integer, not {text!r}")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        usage="%(prog)s [-h] [--depth N] input.json [N] output.json",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "input", metavar="input.json", help="JSON file whose root is an object"
    )
    parser.add_argument(
        "depth_or_output",
        metavar="[N] output.json",
        help="output file; a leading N is the legacy way to give --depth",
    )
    parser.add_argument("output", nargs="?", help=argparse.SUPPRESS)
    parser.add_argument(
        "-d",
        "--depth",
        type=_depth,
        metavar="N",
        help="only wrap leaves in the first N levels of objects (default: all)",
    )
    args = parser.parse_args(argv)
    depth = args.depth
    output = args.depth_or_output
    if args.output is not None:
        if depth is not None:
            parser.error("give the depth either as --depth or positionally, not both")
        try:
            depth = _depth(args.depth_or_output)
        except argparse.ArgumentTypeError as error:
            parser.error(f"depth {error}")
        output = args.output
    try:
        result = substitution(read_json(args.input), depth)
        # Serialize fully before touching the output so bad input never truncates it.
        rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        write_atomically(output, rendered)
    except RecursionError:
        parser.exit(2, f"{parser.prog}: {args.input}: JSON is nested too deeply\n")
    except (OSError, ValueError, TypeError) as error:
        parser.exit(2, f"{parser.prog}: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
