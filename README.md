## Introduction
This is a fork of the original code2flow project. The original project can be found [here](https://github.com/scottrogowski/code2flow/). The original project is licensed under the MIT license. The original project was last updated in 2021. This fork is intended to add new features and improvements to the original project to make useful for a specific Python use case.

Code2flow generates [call graphs](https://en.wikipedia.org/wiki/Call_graph) for dynamic programming language. This fork supports Python only.

The basic algorithm is simple:

1. Translate your source files into ASTs.
1. Find all function definitions.
1. Determine where those functions are called.
1. Connect the dots.

Code2flow is useful for:
- Untangling spaghetti code.
- Identifying orphaned functions.
- Getting new developers up to speed.

Code2flow provides a *pretty good estimate* of your project's structure. No algorithm can generate a perfect call graph for a [dynamic language](https://en.wikipedia.org/wiki/Dynamic_programming_language) – even less so if that language is [duck-typed](https://en.wikipedia.org/wiki/Duck_typing). See the known limitations in the section below.

## How to use

You can work with code2flow as an imported Python library.

```python
from code2flow.engine import code2flow

code2flow(
    raw_source_paths='./projects/users',
    output_dir='output',
    generate_json=True,
    generate_image=True,
    build_cache=True
)
```
This will generate the following files for the `users` project in the `output` directory:
- The call graph in JSON format `output/call_graph.json`
- The call graph in PNG format `output/graph.png`
- The documentation cache in JSON format `output/cache.json` that can be filled with AutoGen documentation.

Examples can be found below.

### Call Graph (JSON)
```json
{
    "EXTERNAL::print": {
        "uid": "external_print",
        "name": "EXTERNAL::print",
        "content": null,
        "callees": []
    },
    "data_processor::DataProcessor.check_emails": {
        "uid": "node_8302933f",
        "name": "data_processor::DataProcessor.check_emails",
        "content": "...",
        "callees": [
            "utils::validate_email"
        ]
    },
    "data_processor::DataProcessor.process_data": {
        "uid": "node_300c8d6d",
        "name": "data_processor::DataProcessor.process_data",
        "content": "...",
        "callees": []
    },
    "main::(global)": {
        "uid": "node_b5519bc4",
        "name": "main::(global)",
        "content": null,
        "callees": [
            "main::main"
        ]
    },
    "main::main": {
        "uid": "node_26daa468",
        "name": "main::main",
        "content": "...",
        "callees": [
            "EXTERNAL::print",
            "EXTERNAL::print",
            "data_processor::DataProcessor.process_data",
            "user::User.__init__"
        ]
    },
    "user::User.__init__": {
        "uid": "node_3ef24613",
        "name": "user::User.__init__",
        "content": "...",
        "callees": []
    },
    "utils::validate_email": {
        "uid": "node_195e73b7",
        "name": "utils::validate_email",
        "content": "...",
        "callees": []
    }
}
```

### Call Graph (PNG)
![graph](output/graph.png)

### Cache 
```json
{
    "EXTERNAL::print": {
        "version": 0,
        "generated_on": "",
        "source_code": "",
        "generated_docs": ""
    },
    "data_processor::DataProcessor.check_emails": {
        "version": 0,
        "generated_on": "",
        "source_code": "",
        "generated_docs": ""
    },
    "data_processor::DataProcessor.process_data": {
        "version": 0,
        "generated_on": "",
        "source_code": "",
        "generated_docs": ""
    },
    "main::(global)": {
        "version": 0,
        "generated_on": "",
        "source_code": "",
        "generated_docs": ""
    },
    "main::main": {
        "version": 0,
        "generated_on": "",
        "source_code": "",
        "generated_docs": ""
    },
    "user::User.__init__": {
        "version": 0,
        "generated_on": "",
        "source_code": "",
        "generated_docs": ""
    },
    "utils::validate_email": {
        "version": 0,
        "generated_on": "",
        "source_code": "",
        "generated_docs": ""
    }
}
```


How code2flow works
------------

Code2flow approximates the structure of projects in dynamic languages. It is *not possible* to generate a perfect callgraph for a dynamic language.

Detailed algorithm:

1. Generate an AST of the source code
2. Recursively separate groups and nodes. Groups are files, modules, or classes. More precisely, groups are namespaces where functions live. Nodes are the functions themselves.
3. For all nodes, identify function calls in those nodes.
4. For all nodes, identify in-scope variables. Attempt to connect those variables to specific nodes and groups. This is where there is some ambiguity in the algorithm because it is impossible to know the types of variables in dynamic languages. So, instead, heuristics must be used.
5. For all calls in all nodes, attempt to find a match from the in-scope variables. This will be an edge.
6. Find all external calls. These are calls to functions that are not defined in the project. These are orphaned nodes.
7. If a definitive match from in-scope variables cannot be found, attempt to find a single match from all other groups and nodes.
8. Trim orphaned nodes and groups.
9. Output results.

Why is it impossible to generate a perfect call graph?
----------------

Consider this toy example in Python
```python
def func_factory(param):
    if param < .5:
        return func_a
    else:
        return func_b

func = func_factory(important_variable)
func()
```

We have no way of knowing whether `func` will point to `func_a` or `func_b` until runtime. In practice, ambiguity like this is common and is present in most non-trivial applications.

Known limitations
-----------------

Code2flow is internally powered by ASTs. Most limitations stem from a token not being named what code2flow expects it to be named.

* All functions without definitions are skipped. This most often happens when a file is not included.
* Functions with identical names in different namespaces are (loudly) skipped. E.g. If you have two classes with identically named methods, code2flow cannot distinguish between these and skips them.
* Imported functions from outside your project directory (including from standard libraries) which share names with your defined functions may not be handled correctly. Instead, when you call the imported function, code2flow will link to your local functions. For example, if you have a function `search()` and call, `import searcher; searcher.search()`, code2flow may link (incorrectly) to your defined function.
* Anonymous or generated functions are skipped. This includes lambdas and factories.
* If a function is renamed, either explicitly or by being passed around as a parameter, it will be skipped.

Original License
-----------------------------
Code2flow is licensed under the MIT license.
Prior to the rewrite in April 2021, code2flow was licensed under LGPL. The last commit under that license was 24b2cb854c6a872ba6e17409fbddb6659bf64d4c.
The April 2021 rewrite was substantial, so it's probably reasonable to treat code2flow as completely MIT-licensed.