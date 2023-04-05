from substitute import substitution


def test_substitution_simple():
    input_dict = {'a': 1, 'b': 'hello'}
    expected_output = {'a': {'_content': 1, '_type': "<class 'int'>"}, 'b': {'_content': 'hello', '_type': "<class 'str'>"}}
    actual_output = substitution(input_dict)
    assert actual_output == expected_output
