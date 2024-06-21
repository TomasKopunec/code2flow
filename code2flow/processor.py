
from code2flow.model import Node


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
        # self.namespace = node.namespace_ownership()
        # self.first_group = 'EXTERNAL' if not node.first_group() else node.first_group().label()
        # self.file_group = 'EXTERNAL' if not node.file_group() else node.file_group().label()
        # self.token_with_ownership = node.token_with_ownership()
        self.callees = []

    # def __str__(self) -> str:
    #     return f'{self.namespace}::{self.first_group}::{self.file_group}::{self.token_with_ownership}'

    def add_callee(self, callee):
        self.callees.append(callee)

    def to_dict(self):
        return {
            'uid' : self.uid,
            'name' : self.name,
            # 'namespace' : self.namespace,
            # 'first_group' : self.first_group,
            # 'file_group' : self.file_group,
            # 'token_with_ownership' : self.token_with_ownership,
            'callees' : self.callees
        }