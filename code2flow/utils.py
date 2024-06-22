
import json

from code2flow.engine import code2flow


def generate_graph(root_folder, output_dir):
    """
    Writes call graph to output_dir/call_graph.json
    Writes image to output_dir/call_graph.png
    """
    code2flow(
        raw_source_paths=root_folder,
        output_dir=output_dir,
        generate_json=True,
        generate_image=True,
        build_cache=True
    )


def get_cache(output_dir) -> dict:
    try:
        return __load_json(f'{output_dir}/cache.json')
    except FileNotFoundError:
        raise Exception('Cache not found. Please run generate_graph first.')


def get_call_graph(output_dir) -> dict:
    try:
        return __load_json(f'{output_dir}/call_graph.json')
    except FileNotFoundError:
        raise Exception(
            'Call graph not found. Please run generate_graph first.')


def get_file_to_functions() -> dict:
    """
    Converts call graph to a file to functions mapping of the form:
    {
        'file1.py': ['func1', 'func2'],
        'file2.py': ['func3', 'func4'],
        'EXTERNAL': ['EXTERNAL::dict', 'EXTERNAL::list'], 
        ...
    }
    """
    file_to_calls = {}
    for method_name, call in get_call_graph().items():
        file_name = call['file_name']
        items = file_to_calls.get(file_name, [])
        file_to_calls[file_name] = items + [method_name]
    return file_to_calls


def __load_json(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)


def __write_json(file_path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)
