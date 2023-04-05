from json import dump, load
from sys import argv

def substitution(dictionary, depth=None, current_depth=0):
    if depth is not None and current_depth >= depth:
        return dictionary
    for key, value in dictionary.items():
        dictionary[key] = substitution(value, depth, current_depth + 1) if isinstance(value, dict) else {'_content': value, '_type': str(type(value))}     
    return dictionary


if __name__ == '__main__':
    input_filename = argv[1]
    if len(argv) == 4:
        depth = int(argv[2])
        output_filename = argv[3]
    else:
        depth = None
        output_filename = argv[2]
    modified_dictionary = substitution(load(open(f"{input_filename}", "r")), depth)
    dump(modified_dictionary, open(f"{output_filename}", "w"))
