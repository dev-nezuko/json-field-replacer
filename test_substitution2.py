import pytest
from substitute import substitution

@pytest.mark.parametrize("input_dict, depth, expected_output", [
    ({'a': 1, 'b': 'Good Luck'}, None, {'a': {'_content': 1, '_type': "<class 'int'>"}, 'b': {'_content': 'Good Luck', '_type': "<class 'str'>"}}),
    ({'a': {'b': {'c': 1}}}, 3, {'a': {'b': {'c': {'_content': 1, '_type': "<class 'int'>"}}}}),
    ({}, None, {}),
])

def test_substitution(input_dict, depth, expected_output):
    actual_output = substitution(input_dict, depth)
    print(actual_output)
    print(expected_output)
    assert actual_output == expected_output
