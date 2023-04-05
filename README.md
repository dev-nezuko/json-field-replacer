# Annotate JSON object values with their Python types

A small Python command-line exercise that walks nested dictionaries and replaces each non-dictionary value with its original content and Python type name. It does not rename JSON fields, infer a database schema or flatten nested data.

Input:

```json
{"name":"Sample","age":30,"address":{"city":"Example"}}
```

Output:

```json
{
  "name": {"_content": "Sample", "_type": "<class 'str'>"},
  "age": {"_content": 30, "_type": "<class 'int'>"},
  "address": {
    "city": {"_content": "Example", "_type": "<class 'str'>"}
  }
}
```

Those are **Python type strings**, not JSON Schema type names.

## Run it

The program uses only Python's standard library. From the repository root:

```sh
python3 substitute.py input.json result.json
python3 substitute.py input.json 1 shallow-result.json
python3 substitute.py --help
```

The optional depth remains a positional argument **between** input and output. Output uses UTF-8, indentation and a final newline. The supplied `input.json` and `output.json` show the original full-depth example; use a separate output filename when exploring it.

| Depth | Effect |
| --- | --- |
| Omitted | Visit all nested dictionaries |
| `0` | Leave the object unchanged |
| `1` | Wrap only non-dictionary values at the root |
| `2` | Also wrap leaves in directly nested dictionaries |

Lists are treated as whole leaf values. For example, `{"items":[{"id":1}]}` becomes `{"items":{"_content":[{"id":1}],"_type":"<class 'list'>"}}`; objects inside the list are not traversed. Boolean and null values receive `<class 'bool'>` and `<class 'NoneType'>` respectively. Empty dictionaries stay empty.

## Use the function

```python
from substitute import substitution

record = {"enabled": True, "nested": {"count": 2}}
result = substitution(record, depth=1)
assert result is record  # The function mutates and returns the same dictionary.
```

The root must be an object, and depth must be a nonnegative integer or `None`. Invalid input, malformed JSON and CLI errors exit nonzero with an explanation. Input is parsed and the complete result serialized before the output is opened, so a validation error does not truncate an existing output file. Successful runs overwrite the explicitly named output.

## Checks and limits

```sh
python3 -m pip install pytest
python3 -m pytest -q
```

Fifteen tests cover the original examples, depth-zero identity, shallow traversal, lists, booleans/nulls, invalid roots and depths, Unicode, the legacy CLI argument order, and preservation of an existing output after malformed input.

The full object and rendered output are held in memory, and dictionary traversal is recursive. This is a small-document exercise, not a streaming transformer for large or deeply nested datasets. Running it repeatedly on already annotated output will wrap the annotation fields again; it is not idempotent. Standard-library JSON behavior is used rather than a separate strict-schema validator.

The unused copied font directory was removed because this command-line program has no rendering or font requirement. No license file is included.
