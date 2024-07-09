
from collections import deque
import json

from .engine import code2flow


def generate_graph(root_folder, output_dir, generate_image=True, generate_json=True):
    """
    Writes call graph to output_dir/call_graph.json
    Writes image to output_dir/call_graph.png
    """
    code2flow(
        raw_source_paths=root_folder,
        output_dir=output_dir,
        generate_json=generate_json,
        generate_image=generate_image
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


def get_file_to_functions(graph) -> dict:
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
    for method_name, call in graph.items():
        file_name = call['file_name']
        items = file_to_calls.get(file_name, [])
        file_to_calls[file_name] = items + [method_name]
    return file_to_calls


def explore_call_graph(graph, depth=5) -> dict:
    """
    Converts call graph to a function to list of callees mapping of the form:
    {
        'func1': {'func2': {'func3': {}}}
        'func2': {'func3': {}, 'func4': {
            'func5': {'func6': {}, 'func7': {}},
            'func8': {'func9': {}}
        }}' 
        ...
    }
    """
    print(f'Exploring the Call Graph with depth up to {depth}')
    visited = {}
    for method in graph:
        if 'EXTERNAL' not in method:  # Skip external methods
            visited.update(__explore_call_graph(
                graph, method, visited, depth))
    return visited

def get_parent_dependencies(graph, matched_functions) -> list[tuple]:
    """
    Returns a list of tuples containing the parent dependencies of the matched functions.
    [
        ('func1', 'file1.py'),
        ('func2', 'file2.py'),
        ...
    ]
    """
    parent_dependencies = []
    visited = set()
    queue = deque(matched_functions)
    
    while queue:
        current_function = queue.popleft()
        if current_function not in visited:
            visited.add(current_function)
            graph_entry = graph.get(current_function)
                
            file_name = graph_entry['file_name']
            if file_name != 'EXTERNAL':
                parent_dependencies.append((current_function, graph_entry['file_name']))
                
            # Add callers (parents) to the queue
            for caller in graph_entry['callers']:
                if caller not in visited:
                    queue.append(caller)
    return parent_dependencies

def __explore_call_graph(graph, start_method, visited, depth) -> dict:
    result = {}
    queue = deque([(start_method, 0, result)])

    while queue:
        curr, curr_depth, curr_dict = queue.popleft()
        if curr_depth < depth:
            # Check if we already visited this method, if so use the cached result
            if curr in visited:
                curr_dict[curr] = visited[curr]
            else:
                curr_dict[curr] = {}
                for callee in graph.get(curr, {}).get('callees', []):
                    queue.append((callee, curr_depth + 1, curr_dict[curr]))
    return result


def __load_json(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)