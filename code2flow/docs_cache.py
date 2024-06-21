from code2flow.documentation import Documentation


class DocsCache():
    @staticmethod
    def build_cache(call_graph):
        cache = DocsCache()
        for method_name, _ in call_graph.items():
            cache.add(method_name, Documentation.get_empty())
        return cache

    def __init__(self):
        self.__cache = {}

    def __str__(self) -> str:
        return str(self.__cache)

    def add(self, key: str, value=Documentation.get_empty()):
        assert '::' in key  # Key must contain "::", as per valid call name
        self.__cache[key] = value

    def get(self, key):
        return self.__cache.get(key, None)

    def remove(self, key):
        if key in self.__cache:
            del self.__cache[key]

    def clear(self):
        self.__cache.clear()

    def size(self):
        return len(self.__cache)
    
    def to_dict(self):
        return {key: value.to_dict() for key, value in self.__cache.items()}
