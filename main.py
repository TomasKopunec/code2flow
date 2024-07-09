from code2flow.utils import *

root_folder = '../simple-users'
output_dir = 'output'

# 1. Generate graph
generate_graph(root_folder, output_dir)
graph = get_call_graph(output_dir)
                             
# 2. Build mapping of a file to the functions called within them
file_to_calls = get_file_to_functions(graph)

bfs_result = explore_call_graph(graph=graph, depth=5)
# write_json(f'{output_dir}/bfs_result.json', bfs_result)