import sys

import pytest

from substitute import substitution


def wrapped(value):
    return {"_content": value, "_type": str(type(value))}


def nest(levels, leaf=1):
    node = leaf
    for _ in range(levels):
        node = {"a": node}
    return node


def test_wraps_each_root_leaf_with_its_python_type():
    assert substitution({"a": 1, "b": "hello"}) == {
        "a": {"_content": 1, "_type": "<class 'int'>"},
        "b": {"_content": "hello", "_type": "<class 'str'>"},
    }


@pytest.mark.parametrize(
    ("data", "depth", "expected"),
    [
        (
            {"a": 1, "b": "Good Luck"},
            None,
            {"a": wrapped(1), "b": wrapped("Good Luck")},
        ),
        ({"a": {"b": {"c": 1}}}, 3, {"a": {"b": {"c": wrapped(1)}}}),
        ({"a": {"b": {"c": 1}}}, 2, {"a": {"b": {"c": 1}}}),
        ({}, None, {}),
        ({"empty": {}}, None, {"empty": {}}),
    ],
)
def test_depth_limits_how_far_down_leaves_are_wrapped(data, depth, expected):
    assert substitution(data, depth) == expected


def test_depth_zero_preserves_dictionary_identity_and_values():
    original = {"nested": {"value": 3}, "value": 1}
    assert substitution(original, 0) is original
    assert original == {"nested": {"value": 3}, "value": 1}


def test_mutates_and_returns_the_same_dictionary():
    record = {"enabled": True, "nested": {"count": 2}}
    result = substitution(record)
    assert result is record
    assert record["nested"]["count"] == wrapped(2)


def test_depth_one_only_wraps_root_leaves():
    assert substitution({"root": 1, "nested": {"value": 2}}, 1) == {
        "root": wrapped(1),
        "nested": {"value": 2},
    }


def test_lists_are_leaves_and_their_objects_are_not_visited():
    result = substitution({"items": [{"value": 1}, [2, {"x": 3}]]})
    assert result == {"items": wrapped([{"value": 1}, [2, {"x": 3}]])}
    assert result["items"]["_type"] == "<class 'list'>"


@pytest.mark.parametrize(
    ("value", "type_name"),
    [
        (True, "<class 'bool'>"),
        (None, "<class 'NoneType'>"),
        (1.5, "<class 'float'>"),
        (10**30, "<class 'int'>"),
    ],
)
def test_type_names_are_python_class_strings(value, type_name):
    assert substitution({"v": value})["v"]["_type"] == type_name


def test_unicode_keys_and_values_are_kept_verbatim():
    result = substitution({"café": "naïve", "日本": {"emoji": "\U0001f600"}})
    assert result == {
        "café": wrapped("naïve"),
        "日本": {"emoji": wrapped("\U0001f600")},
    }


def test_non_string_keys_work_for_python_callers():
    result = substitution({1: "one", (2, 3): {None: 4.0}})
    assert result == {1: wrapped("one"), (2, 3): {None: wrapped(4.0)}}


def test_nesting_deeper_than_the_recursion_limit_raises_recursion_error():
    with pytest.raises(RecursionError):
        substitution(nest(sys.getrecursionlimit() + 100))


def test_a_depth_limit_stops_before_hitting_the_recursion_limit():
    deep = nest(sys.getrecursionlimit() + 100)
    result = substitution(deep, depth=3)
    assert result["a"]["a"]["a"] is not None
    assert "_content" not in result["a"]["a"]


def test_already_annotated_output_is_wrapped_again():
    once = substitution({"a": 1})
    assert substitution(once) == {
        "a": {"_content": wrapped(1), "_type": wrapped("<class 'int'>")}
    }


@pytest.mark.parametrize("value", [[], None, 42, "text"])
def test_root_must_be_an_object(value):
    with pytest.raises(TypeError, match="JSON object"):
        substitution(value)


@pytest.mark.parametrize("depth", [-1, "one", True, 1.0])
def test_invalid_depth_is_rejected(depth):
    with pytest.raises(ValueError, match="depth"):
        substitution({}, depth)
