import os
from .model import Node


class Processor():
    def __init__(self, nodes, edges):
        self.nodes = nodes
        self.edges = edges
        self.calls = self.__get_calls()
        self.__build_edges()

    def __str__(self) -> str:
        return f'{len(self.calls)} calls'

    def __get_calls(self):
        calls = {}
        for node in self.nodes:
            calls[node.uid] = FunctionCall(node)
        return calls

    def __build_edges(self):
        for edge in self.edges:
            caller_id = edge.to_dict()['source']
            callee_id = edge.to_dict()['target']
            directed = edge.to_dict()['directed']

            if not directed:
                raise Exception('Only directed edges are supported')

            caller = self.calls[caller_id]
            callee = self.calls[callee_id]

            # We could add whole FunctionAll object
            # caller.add_callee(callee)

            # But we only want the name
            caller.add_callee(callee.name)

    def get_json(self):
        calls = {}
        for call in self.calls.values():
            calls[call.name] = call.to_dict()
        return calls


class FunctionCall():
    def __init__(self, node: Node):
        self.uid = node.uid
        self.name = node.name()
        self.ownership = node.token_with_ownership()
        self.content = node.content
        self.callees = []
        self.file_name = self.__resolve_filename(node)

    def add_callee(self, callee):
        self.callees.append(callee)

    def __resolve_filename(self, node):
        if node.parent is None:
            return 'EXTERNAL'
        parent = node.parent
        while parent.parent is not None and parent.group_type != 'FILE':
            parent = parent.parent
        return os.path.abspath(parent.file_name)

    def to_dict(self):
        return {
            'uid': self.uid,
            'name': self.name,
            # Could be inferred from the name (b::B.methodB1 -> file b, class B, method methodB1)
            'content': self.content,
            'callees': self.callees,
            'file_name': self.file_name,
        }
