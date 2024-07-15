import collections
import json
import logging
import os
import subprocess
import time

from ordered_set import OrderedSet

from .processor import Processor
from .python import Python
from .model import (TRUNK_COLOR, LEAF_COLOR, NODE_COLOR, GROUP_TYPE, OWNER_CONST, Call,
                    Edge, Group, Node, Variable, is_installed, flatten)

LEGEND = """subgraph legend{
    rank = min;
    label = "legend";
    Legend [shape=none, margin=0, label = <
        <table cellspacing="0" cellpadding="0" border="1"><tr><td>Code2flow Legend</td></tr><tr><td>
        <table cellspacing="0">
        <tr><td>Regular function</td><td width="50px" bgcolor='%s'></td></tr>
        <tr><td>Trunk function (nothing calls this)</td><td bgcolor='%s'></td></tr>
        <tr><td>Leaf function (this calls nothing else)</td><td bgcolor='%s'></td></tr>
        <tr><td>Function call</td><td><font color='black'>&#8594;</font></td></tr>
        </table></td></tr></table>
        >];
}""" % (NODE_COLOR, TRUNK_COLOR, LEAF_COLOR)


def write_dot(outfile, nodes, edges, groups, hide_legend=False,
              no_grouping=False):
    '''
    Write a dot file that can be read by graphviz

    :param outfile File:
    :param nodes list[Node]: functions
    :param edges list[Edge]: function calls
    :param groups list[Group]: classes and files
    :param hide_legend bool:
    :rtype: None
    '''
    splines = "polyline" if len(edges) >= 500 else "ortho"
    content = "digraph G {\n"
    content += "concentrate=true;\n"
    content += f'splines="{splines}";\n'
    content += 'rankdir="LR";\n'
    if not hide_legend:
        content += LEGEND
    for node in nodes:
        content += node.to_dot() + ';\n'
    for edge in edges:
        content += edge.to_dot() + ';\n'
    if not no_grouping:
        for group in groups:
            content += group.to_dot()
    content += '}\n'
    outfile.write(content)


def get_sources(raw_source_paths, language='py'):
    """
    Given a list of files and directories, return just files.
    Filter out files that are not of Python language

    :param list[str] raw_source_paths: file or directory paths
    :rtype: (list, str)
    """

    individual_files = []
    for source in sorted(raw_source_paths):
        if os.path.isfile(source):
            individual_files.append((source, True))
            continue
        for root, _, files in os.walk(source):
            for f in files:
                individual_files.append((os.path.join(root, f), False))

    if not individual_files:
        raise AssertionError("No source files found from %r" %
                             raw_source_paths)
    # logging.info("Found %d files from sources argument.", len(individual_files))

    skipped = 0
    sources = OrderedSet()
    for source, explicity_added in individual_files:
        if explicity_added or source.endswith('.' + language):
            sources.add(source)
        else:
            skipped += 1
    
    logging.info("Skipped %d non-Python files.", skipped)            

    if not sources:
        raise AssertionError("Could not find any source files given {raw_source_paths} "
                             "and language {language}.")

    sources = sorted(list(sources))
    logging.info("Processing %d source file(s)." % (len(sources)))
    # for source in sources:
    #     logging.info("  " + source)

    return sources


def make_file_group(tree, filename):
    """
    Given an AST for the entire file, generate a file group complete with
    subgroups, nodes, etc.

    :param tree ast:
    :param filename str:
    :param extension str:
    """
    language = Python
    subgroup_trees, node_trees, body_trees = language.separate_namespaces(tree)
    group_type = GROUP_TYPE.FILE
    token = os.path.split(filename)[-1].rsplit('.py', 1)[0]
    line_number = 0
    display_name = 'File'
    import_tokens = language.file_import_tokens(filename)

    file_group = Group(token, group_type, display_name, import_tokens,
                       line_number, parent=None, file_name=filename)
    for node_tree in node_trees:
        for new_node in language.make_nodes(node_tree, parent=file_group):
            file_group.add_node(new_node)

    file_group.add_node(language.make_root_node(
        body_trees, parent=file_group), is_root=True)

    for subgroup_tree in subgroup_trees:
        file_group.add_subgroup(language.make_class_group(
            subgroup_tree, parent=file_group))
    return file_group


def _find_link_for_call(call: Call, node_a: Node, all_nodes, external: set[str], all_group_names: set[str], paths : set[str]):
    """
    Given a call that happened on a node (node_a), return the node
    that the call links to and the call itself if >1 node matched.

    :param call Call:
    :param node_a Node:
    :param all_nodes list[Node]:

    :returns: The node it links to and the call if >1 node matched.
    :rtype: (Node|None, Call|None)
    """

    all_vars = node_a.get_variables(call.line_number)

    for var in all_vars:
        var_match = call.matches_variable(var)
        if var_match:
            # Unknown modules (e.g. third party) we don't want to match)
            if var_match == OWNER_CONST.UNKNOWN_MODULE:
                return None, None
            assert isinstance(var_match, Node)
            return var_match, None

    # Save external calls
    method_name = None
    if not call.owner_token and not call.token in all_group_names:
        resolved = _resolve_module_import_(node_a.parent, call)
        method_name = call.token if not resolved else resolved
        
        # Attempt to check if internal
        is_external = True
        normalized = method_name.replace(f'.{call.token}', '')
        if normalized in paths:
            functions = paths[normalized]
            for f in functions:
                if f'{normalized}.{call.token}' == f'{normalized}.{f}':
                    is_external = False
                    break
            
        if is_external:
            external.add(method_name)
        
    else:
        resolved = _resolve_module_import(node_a.parent, call)
        if resolved and resolved not in all_group_names:
            method_name = f'{resolved}.{call.token}'
            external.add(method_name)

    possible_nodes = []
    if method_name and method_name in external:
        possible_nodes.append(Node.external_node(method_name))
    elif call.is_attr():
        for node in all_nodes:
            # checking node.parent != node_a.file_group() prevents self linkage in cases like
            # function a() {b = Obj(); b.a()}
            if call.token == node.token and node.parent != node_a.file_group():
                possible_nodes.append(node)
    else:
        for node in all_nodes:
            if call.token == node.token \
               and isinstance(node.parent, Group)  \
               and node.parent.group_type == GROUP_TYPE.FILE:
                possible_nodes.append(node)
            elif call.token == node.parent.token and node.is_constructor:
                possible_nodes.append(node)

    if len(possible_nodes) == 1:
        return possible_nodes[0], None
    if len(possible_nodes) > 1:
        return None, call
    return None, None


def _resolve_module_import(node, call):
    while node.group_type != GROUP_TYPE.FILE:
        node = node.parent
    for variable in node.get_variables():
        if variable.token == call.owner_token:
            return variable.points_to
    return None


def _resolve_module_import_(node, call):
    while node.group_type != GROUP_TYPE.FILE:
        node = node.parent
    for variable in node.get_variables():
        if variable.token == call.token:
            return variable.points_to
    return None

def _find_links(node_a, all_nodes, external, all_group_names, paths):
    """
    Iterate through the calls on node_a to find everything the node links to.
    This will return a list of tuples of nodes and calls that were ambiguous.

    :param Node node_a:
    :param list[Node] all_nodes:
    :param BaseLanguage language:
    :rtype: list[(Node, Call)]
    """

    links = []
    for call in node_a.calls:
        lfc = _find_link_for_call(
            call, node_a, all_nodes, external, all_group_names, paths)
        assert not isinstance(lfc, Group)
        links.append(lfc)
    return list(filter(None, links))


def map_it(root_path, sources, no_trimming, skip_parse_errors):
    '''
    Given a language implementation and a list of filenames, do these things:
    1. Read/parse source ASTs
    2. Find all groups (classes/modules) and nodes (functions) (a lot happens here)
    3. Trim namespaces / functions that we don't want
    4. Consolidate groups / nodes given all we know so far
    5. Attempt to resolve the variables (point them to a node or group)
    6. Find all calls between all nodes
    7. Loudly complain about duplicate edges that were skipped
    8. Trim nodes that didn't connect to anything

    :param list[str] sources:
    :param str extension:
    :param bool no_trimming:
    :param list exclude_namespaces:
    :param list exclude_functions:
    :param list include_only_namespaces:
    :param list include_only_functions:
    :param bool skip_parse_errors:
    :param LanguageParams lang_params:

    '''
    # 1. Read/parse source ASTs (List of (source : str, ast : Module) tuples)
    file_ast_trees = []
    for source in sources:
        try:
            file_ast_trees.append((source, Python.get_tree(source)))
        except Exception as ex:
            if skip_parse_errors:
                logging.warning(
                    "Could not parse %r. (%r) Skipping...", source, ex)
            else:
                raise ex

    # 2. Find all groups (classes/modules) and nodes (functions) (a lot happens here)
    file_groups = []
    for source, file_ast_tree in file_ast_trees:
        file_group = make_file_group(file_ast_tree, source)
        file_groups.append(file_group)

    # 3. Consolidate structures
    all_subgroups = flatten(g.all_groups()
                            for g in file_groups)  # All modules / classes
    all_nodes = flatten(g.all_nodes() for g in file_groups)  # All functions

    nodes_by_subgroup_token = collections.defaultdict(list)
    for subgroup in all_subgroups:
        if subgroup.token in nodes_by_subgroup_token:
            logging.warning("Duplicate group name %r. Naming collision possible.",
                            subgroup.token)
        nodes_by_subgroup_token[subgroup.token] += subgroup.nodes

    for group in file_groups:
        for subgroup in group.all_groups():
            subgroup.inherits = [nodes_by_subgroup_token.get(
                g) for g in subgroup.inherits]
            subgroup.inherits = list(filter(None, subgroup.inherits))
            for inherit_nodes in subgroup.inherits:
                for node in subgroup.nodes:
                    node.variables += [Variable(n.token, n, n.line_number)
                                       for n in inherit_nodes]

    # 4. Attempt to resolve the variables (point them to a node or group)
    for node in all_nodes:
        node.resolve_variables(file_groups)

    nodes = sorted(n.token_with_ownership() for n in all_nodes)
    all_calls = list(set(c.to_string()
                     for c in flatten(n.calls for n in all_nodes)))
    variables = list(set(v.to_string()
                     for v in flatten(n.variables for n in all_nodes)))

    # Not a step. Just log what we know so far
    # logging.info("Found groups %r." % [g.label() for g in all_subgroups])
    # logging.info("Found nodes %r." % nodes)
    # logging.info("Found calls %r." % sorted(all_calls))
    # logging.info("Found variables %r." % sorted(variables))

    # 5. Find external calls (calls to functions that are not in the source code)
    all_group_names = OrderedSet([g.token for g in all_subgroups])
    external = OrderedSet()

    # 6. Find all calls between all nodes
    paths = __get_paths(root_path, all_nodes)    
    bad_calls = []
    edges = []
    for node_a in list(all_nodes):
        links = _find_links(node_a, all_nodes, external, all_group_names, paths)
        for node_b, bad_call in links:
            if bad_call:
                bad_calls.append(bad_call)
            if not node_b:
                continue
            edges.append(Edge(node_a, node_b))
    # logging.info("Found external calls %r" % sorted(external))

    # 7. Loudly complain about duplicate edges that were skipped
    bad_calls_strings = OrderedSet()
    for bad_call in bad_calls:
        bad_calls_strings.add(bad_call.to_string())
    bad_calls_strings = list(bad_calls_strings)
    if bad_calls_strings:
        logging.info("Skipped processing these calls because the algorithm "
                     "linked them to multiple function definitions: %r." % bad_calls_strings)

    if no_trimming:
        return file_groups, all_nodes, edges

    # 8. Trim nodes that didn't connect to anything
    nodes_with_edges = OrderedSet()
    for edge in edges:
        nodes_with_edges.add(edge.node0)
        nodes_with_edges.add(edge.node1)

    for node in all_nodes:
        if node not in nodes_with_edges:
            node.remove_from_parent()

    for file_group in file_groups:
        for group in file_group.all_groups():
            if not group.all_nodes():
                group.remove_from_parent()

    file_groups = [g for g in file_groups if g.all_nodes()]
    all_nodes = list(nodes_with_edges)

    if not all_nodes:
        logging.warning("No functions found! Most likely, your file(s) do not have "
                        "functions that call each other. Note that to generate a flowchart, "
                        "you need to have both the function calls and the function "
                        "definitions. Or, you might be excluding too many "
                        "with --exclude-* / --include-* / --target-function arguments. ")
        logging.warning("Code2flow will generate an empty output file.")

    return file_groups, all_nodes, edges

def _write_call_graph(output_dir, content):
    json_file_name = os.path.join(output_dir, 'call_graph.json')
    with open(json_file_name, 'w') as f:
        json.dump(content, f, indent=4)
    logging.info("Call Graph with %d nodes stored in: %r",
                 len(content), json_file_name)

def _generate_img(output_dir, all_nodes, edges, file_groups, hide_legend, no_grouping):
    if not is_installed('dot') and not is_installed('dot.exe'):
        raise AssertionError(
            "Can't generate a flowchart image because neither `dot` nor `dot.exe` was found. ")

    # Write dot file
    dot_file_name = os.path.join(output_dir, 'graph.gv')
    with open(dot_file_name, 'w') as f:
        write_dot(f, all_nodes, edges, file_groups,
                  hide_legend=hide_legend, no_grouping=no_grouping)

    # Write image file
    img_file_name = os.path.join(output_dir, 'graph.png')
    _generate_final_img(dot_file_name, 'png', img_file_name)

    # Delete dot file
    os.remove(dot_file_name)
    logging.info("Image file stored in: %r", img_file_name)


def _generate_final_img(output_file, extension, final_img_filename):
    """
    Write the graphviz file
    :param str output_file:
    :param str extension:
    :param str final_img_filename:
    :param int num_edges:
    """
    _generate_graphviz(output_file, extension, final_img_filename)
    # logging.info("Completed flowchart! To see it, open %r.",
    #              final_img_filename)


def _generate_graphviz(output_file, extension, final_img_filename):
    """
    Write the graphviz file
    :param str output_file:
    :param str extension:
    :param str final_img_filename:
    """
    start_time = time.time()
    # logging.info("Running graphviz to make the image...")
    command = ["dot", "-T" + extension, output_file]
    with open(final_img_filename, 'w') as f:
        try:
            subprocess.run(command, stdout=f, check=True)
            # logging.info("Chart created in %.2f seconds." %
            #              (time.time() - start_time))
        except subprocess.CalledProcessError:
            logging.warning("*** Graphviz returned non-zero exit code! "
                            "Try running %r for more detail ***", ' '.join(command + ['-v', '-O']))

def __get_paths(root_path, all_nodes):
    # Turn 'C:\\Coding\\simple-users\\api\\samples\\a.py' into api.samples.a
    paths = {}
    parents = [node.parent for node in all_nodes if node.parent is not None]
    for p in parents:
        if p.group_type == GROUP_TYPE.FILE and p.parent is None:
            path = p.file_name
            path = path.replace(root_path, '')
            path = path.replace('.py', '')
            split = path.split(os.sep)[1:]
            path = '.'.join(split)
            paths[path] = __get_all_calls(p)
    return paths

def __get_all_calls(node):
    calls = OrderedSet()
    # Get all calls from all nodes and subgroups
    for n in node.all_nodes():
        if n.is_leaf and not n.is_constructor and not n.token == '(global)':
            calls.add(n.token)
    return calls

def code2flow(raw_source_paths, output_dir, hide_legend=True,
              exclude_namespaces=None, exclude_functions=None,
              include_only_namespaces=None, include_only_functions=None,
              no_grouping=False, no_trimming=False, skip_parse_errors=False,
              generate_json=True, generate_image=True, level=logging.INFO, silent=False):
    """
    Top-level function. Generate a diagram based on source code.
    Can generate either a dotfile or an image.

    :param list[str] raw_source_paths: file or directory paths
    :param str| output_dir: path to the output dir.
    :param bool hide_legend: Omit the legend from the output
    :param list exclude_namespaces: List of namespaces to exclude
    :param list exclude_functions: List of functions to exclude
    :param list include_only_namespaces: List of namespaces to include
    :param list include_only_functions: List of functions to include
    :param bool no_grouping: Don't group functions into namespaces in the final output
    :param bool no_trimming: Don't trim orphaned functions / namespaces
    :param bool skip_parse_errors: If a language parser fails to parse a file, skip it
    :param lang_params LanguageParams: Object to store lang-specific params
    :param int level: logging level
    """
    start_time = time.time()  # Start timer

    if not isinstance(raw_source_paths, list):
        raw_source_paths = [raw_source_paths]
    exclude_namespaces = exclude_namespaces or []
    assert isinstance(exclude_namespaces, list)
    exclude_functions = exclude_functions or []
    assert isinstance(exclude_functions, list)
    include_only_namespaces = include_only_namespaces or []
    assert isinstance(include_only_namespaces, list)
    include_only_functions = include_only_functions or []
    assert isinstance(include_only_functions, list)

    # Configure logging
    logging.basicConfig(format="Code2Flow: %(message)s", level=level)
    
    if silent:
        logging.disable(logging.CRITICAL + 1)

    sources = get_sources(raw_source_paths)

    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Primary processing
    file_groups, all_nodes, edges = map_it(raw_source_paths[0], sources, 
                                           no_trimming, skip_parse_errors)

    # Remove duplicate nodes (external calls, etc.)
    unique = {}
    for node in all_nodes:
        unique[node.uid] = node
    all_nodes = list(unique.values())

    # Sort for deterministic output
    all_nodes.sort()
    file_groups.sort()
    edges.sort()

    processor = Processor(all_nodes, edges)
    if generate_json:
        _write_call_graph(output_dir, processor.get())

    if generate_image:
        _generate_img(output_dir, all_nodes, edges,
                      file_groups, hide_legend, no_grouping)

    logging.info("Completed in %.2f seconds." %
                 (time.time() - start_time))
