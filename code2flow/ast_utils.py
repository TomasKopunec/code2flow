import difflib
import os
import enum
import shutil
from .utils import generate_graph, get_call_graph


class FunctionChangeType(enum.Enum):
    EQUAL = 0
    UPDATED = 1
    REMOVED = 2
    ADDED = 3
    RENAMED = 4


class FunctionChange:
    def __init__(self, name, type, similarity):
        self.name = name
        self.type = type
        self.similarity = similarity

    def __str__(self):
        match self.type:
            case FunctionChangeType.EQUAL:
                return f'Function {self.name} has no changes.'
            case FunctionChangeType.UPDATED:
                percent = round(self.similarity * 100, 2)
                return f'Function {self.name} has been updated with similarity of {percent}%.'
            case FunctionChangeType.REMOVED:
                return f'Function {self.name} has been removed.'
            case FunctionChangeType.ADDED:
                return f'Function {self.name} has been added.'
            case FunctionChangeType.RENAMED:
                percent = round(self.similarity * 100, 2)
                return f'Function {self.name} has been renamed with similarity of {percent}%'
            case _:
                raise ValueError(f'Invalid FunctionChangeType: {self.type}')
            
def filter_changes(changes: list):
    """
    Filter changes to only retrieve relevant parent dependencies.
    Only include the UPDATED functions.
    """
    filtered_changes = []
    print(f"Changes: {changes}")
    for change in changes:
        # Check if each 'change' is a dictionary and has the required keys
        print(f"Change: {change.type}")
        if change.type == FunctionChangeType.UPDATED:
            filtered_changes.append(change.name)
        else:
            print(f"Invalid change format: {change}")
    return filtered_changes


def get_function_changes(file_path, old_file, new_file) -> list[FunctionChange]:
    """
    Given two Python function dictionaries (name -> content), this function calculates (using difflib)
    the similarity between the functions in the files.

    Returns:
        list[FunctionChange]: A list of FunctionChange objects representing the changes between the old and new functions.
        [{name: 'func1', change_type: 'UPDATED', similarity: 0.887}, ...]
    """
    old_functions = _get_all_functions_from_content(file_path, old_file)
    new_functions = _get_all_functions_from_content(file_path, new_file)

    similarity = []
    old_func_names = set(old_functions.keys())
    new_func_names = set(new_functions.keys())

    for new_name, new_func in new_functions.items():
        # Updated
        if new_name in old_func_names:
            old_func = old_functions[new_name]
            ratio = _get_similarity(old_func, new_func)
            type = FunctionChangeType.EQUAL if ratio == 1 else FunctionChangeType.UPDATED
            similarity.append(FunctionChange(new_name, type, ratio))
            continue

        # Added or Renamed
        max_similarity = 0
        most_similar_old_func = None
        for old_name, old_func in old_functions.items():
            if old_name not in new_func_names:
                sim = _get_similarity(old_func, new_func)
                if sim > max_similarity:
                    max_similarity = sim
                    most_similar_old_func = old_name

        if max_similarity > 0.8:  # Threshold for considering a function renamed
            similarity.append(FunctionChange(
                new_name, FunctionChangeType.RENAMED, max_similarity))
            old_func_names.remove(most_similar_old_func)
        else:
            similarity.append(FunctionChange(
                new_name, FunctionChangeType.ADDED, 0))

    # Removed
    for old_name in old_func_names:
        if old_name not in new_func_names:
            similarity.append(FunctionChange(
                old_name, FunctionChangeType.REMOVED, 0))

    for simi in similarity:
        print(f"Function: {simi.name}")
        print(f"Type: {simi.type}")
    return similarity


def _get_all_functions_from_content(path, content):
    os.makedirs('./tmp', exist_ok=True)
    file_path = f'./tmp/{os.path.basename(path)}'
    with open(file_path, 'w') as f:
        f.write(content)
    return _get_all_functions_from_file(file_path)


def _get_all_functions_from_file(file_path) -> dict:
    generate_graph(file_path, './tmp', generate_image=False, silent=True)
    graph = get_call_graph('./tmp')

    # Only pick the functions from graph that are in functions
    map = {}
    for _, entry in graph.items():
        name = entry['name']
        if 'EXTERNAL' not in name:
            map[name] = entry['content']
    shutil.rmtree('./tmp')
    return map


def _get_similarity(a, b):
    assert isinstance(a, str) and isinstance(b, str)    
    return difflib.SequenceMatcher(None, a, b).ratio()
