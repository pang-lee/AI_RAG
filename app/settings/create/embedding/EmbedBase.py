# '''
# Author: pang, lee
# Date: 2024-07-04 15:58:20
# LastEditTime: 2024-07-04 15:58:20
# LastEditors: LAPTOP-22MC5HRI
# Description: The base of Embedding
# FilePath: \openai\template\create\embeding\EmbedBase.py
# '''
from abc import ABC, abstractmethod
from ..file2doc.file2doc import file2doc

class BaseEmbedding(ABC):
    def __init__(self, model: str, dimension: int = 0):
        self.model = model
        self.dimension = dimension
        
    def compute_dimension(self, text: str) -> int:
        # 假设这里是根据文本计算维度的逻辑，这里简单地返回文本长度作为示例
        return len(text)
    
    def transfer_file2doc(self, docs):
        return file2doc(docs).process_docs()
    
    @abstractmethod
    def embed_vector_db(self):
        pass