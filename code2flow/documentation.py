class Documentation():
    @staticmethod
    def get_empty():
        return Documentation()
    
    def __init__(self, version=0, generated_on='', generated_docs=''):
        self.version = version
        self.generated_on = generated_on
        self.generated_docs = generated_docs
    
    def __str__(self) -> str:
        return f'{self.version} - {self.generated_on}'
    
    def to_dict(self):
        return {
            'version': self.version,
            'generated_on': self.generated_on,
            'generated_docs': self.generated_docs
        }