import os

from ordered_set import OrderedSet
from .model import Node


class Processor():
    def __init__(self, nodes, edges):
        self.nodes = nodes
        self.edges = edges
        self.calls = self._get_calls()
        self._build_edges()
        self.json = self._to_json()
        self._resolve_callers()

    def __str__(self) -> str:
        return f'{len(self.calls)} calls'

    def _get_calls(self):
        calls = {}
        for node in self.nodes:
            calls[node.uid] = FunctionCall(node)
        return calls

    def _build_edges(self):
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

    def _resolve_callers(self):
        for uid, call in self.json.items():
            for callee in call['callees']:
                self.json[callee]['callers'].append(uid)
        
        # Remove duplicates
        for uid, call in self.json.items():
            call['callers'] = list(OrderedSet(call['callers']))

    def _to_json(self):
        calls = {}
        for call in self.calls.values():
            calls[call.name] = call.to_dict()
        return calls
    
    def get(self):
        return self.json


class FunctionCall():
    def __init__(self, node: Node):
        self.uid = node.uid
        self.name = node.name()
        self.ownership = node.token_with_ownership()
        self.content = node.content if node.content else ''
        self.callers = []
        self.callees = []
        self.file_name = self._resolve_filename(node)

    def __str__(self):
        return f'{self.name}'

    def add_callee(self, callee):
        self.callees.append(callee)

    def _resolve_filename(self, node):
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
            'content': self.content,
            'callers': self.callers,
            'callees': self.callees,
            'file_name': self.file_name,
        }
