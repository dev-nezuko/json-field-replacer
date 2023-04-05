"""Wrap dictionary leaf values with their original value and Python type name."""

import argparse
import json
import os
import tempfile


def substitution(dictionary, depth=None, current_depth=0):
    """Mutate a dictionary; lists remain leaf values and depth zero is a no-op."""
    if not isinstance(dictionary, dict):
        raise TypeError("The input must be a JSON object.")
    if depth is not None and (type(depth) is not int or depth < 0):
        raise ValueError("depth must be a nonnegative integer or None.")

    def visit(node, level):
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


def _reject_constant(name):
    raise ValueError(f"{name} is not valid JSON")


def read_json(path):
    """Parse strict JSON; a UTF-8 byte-order mark is accepted, NaN/Infinity are not."""
    with open(path, encoding="utf-8-sig") as source:
        try:
            return json.load(source, parse_constant=_reject_constant)
        except ValueError as error:
            raise ValueError(f"{path}: {error}") from error


def write_atomically(path, text):
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


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, usage="%(prog)s input.json [depth] output.json"
    )
    parser.add_argument("input", help="Input JSON object file")
    parser.add_argument(
        "depth_or_output",
        help="Output file, or the maximum depth when a third argument follows",
    )
    parser.add_argument("output", nargs="?", help="Output file when depth is provided")
    args = parser.parse_args(argv)
    depth = None
    output = args.depth_or_output
    if args.output is not None:
        try:
            depth = int(args.depth_or_output)
            if depth < 0:
                raise ValueError()
        except ValueError:
            parser.error("depth must be a nonnegative integer")
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
