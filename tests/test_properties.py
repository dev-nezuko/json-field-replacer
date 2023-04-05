import copy
import json

from hypothesis import given
from hypothesis import strategies as st

from substitute import substitution

RESERVED = {"_content", "_type"}

keys = st.text(max_size=8).filter(lambda key: key not in RESERVED)
scalars = st.none() | st.booleans() | st.integers() | st.text(max_size=8)
scalars |= st.floats(allow_nan=False, allow_infinity=False)
json_values = st.recursive(
    scalars,
    lambda children: (
        st.lists(children, max_size=4) | st.dictionaries(keys, children, max_size=4)
    ),
    max_leaves=20,
)
json_objects = st.dictionaries(keys, json_values, max_size=5)


def unwrap(node):
    if set(node) == RESERVED:
        return node["_content"]
    return {key: unwrap(value) for key, value in node.items()}


def object_depth(node):
    children = [value for value in node.values() if isinstance(value, dict)]
    return 1 + max((object_depth(child) for child in children), default=0)


@given(json_objects)
def test_unwrapping_the_result_gives_back_the_original(data):
    assert unwrap(substitution(copy.deepcopy(data))) == data


@given(json_objects)
def test_every_wrapper_records_the_type_of_its_content(data):
    def check(node):
        for value in node.values():
            if set(value) == RESERVED:
                assert value["_type"] == str(type(value["_content"]))
            else:
                check(value)

    check(substitution(data))


@given(json_objects)
def test_result_survives_a_json_round_trip(data):
    result = substitution(data)
    assert json.loads(json.dumps(result, allow_nan=False)) == result


@given(json_objects)
def test_depth_zero_is_a_no_op(data):
    before = copy.deepcopy(data)
    assert substitution(data, 0) == before


@given(json_objects)
def test_a_depth_at_least_as_deep_as_the_data_equals_no_limit(data):
    limited = substitution(copy.deepcopy(data), object_depth(data))
    assert limited == substitution(data)
