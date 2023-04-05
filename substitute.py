"""Wrap dictionary leaf values with their original value and Python type name."""
import argparse
import json


def substitution(dictionary, depth=None, current_depth=0):
    """Mutate a dictionary; lists remain leaf values and depth zero is a no-op."""
    if not isinstance(dictionary, dict):
        raise TypeError('The input must be a JSON object.')
    if depth is not None and (type(depth) is not int or depth < 0):
        raise ValueError('depth must be a nonnegative integer or None.')

    def visit(node, level):
        if depth is not None and level >= depth:
            return node
        for key, value in node.items():
            node[key] = visit(value, level + 1) if isinstance(value, dict) else {'_content': value, '_type': str(type(value))}
        return node

    return visit(dictionary, current_depth)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, usage='%(prog)s input.json [depth] output.json')
    parser.add_argument('input', help='Input JSON object file')
    parser.add_argument('depth_or_output', help='Output file, or maximum dictionary depth when a third argument is present')
    parser.add_argument('output', nargs='?', help='Output file when depth is provided')
    args = parser.parse_args(argv)
    depth = None
    output = args.depth_or_output
    if args.output is not None:
        try:
            depth = int(args.depth_or_output)
            if depth < 0:
                raise ValueError()
        except ValueError:
            parser.error('depth must be a nonnegative integer')
        output = args.output
    try:
        with open(args.input, encoding='utf-8') as source:
            result = substitution(json.load(source), depth)
        # Serialize fully before opening the output, so invalid input never truncates it.
        rendered = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
        with open(output, 'w', encoding='utf-8') as destination:
            destination.write(rendered)
    except (OSError, ValueError, TypeError, RecursionError) as error:
        parser.exit(2, f'{parser.prog}: {error}\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
