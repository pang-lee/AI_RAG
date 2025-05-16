# '''
# Author: pang, lee
# Date: 2024-07-04 15:55:08
# LastEditTime: 2024-07-04 15:55:08
# LastEditors: LAPTOP-22MC5HRI
# Description: Qianfan Embedding
# FilePath: \openai\template\create\embeding\QianfanEmbeddings.py
# '''
from .EmbedBase import BaseEmbedding

class QianfanEmbeddings(BaseEmbedding):
    def __init__(self, model: str):
        dimension = 1536 if model in ['text-embedding-ada-002', 'text-embedding-3-small'] else 3072
        super().__init__(model, dimension)

    def embed(self, text):
        # 模拟嵌入操作
        print(self.dimension)
        return f"Qianfan embedding for {text} using model {self.model}"
