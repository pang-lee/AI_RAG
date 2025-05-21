# '''
# Author: pang, lee
# Date: 2024-07-04 15:54:26
# LastEditTime: 2024-07-04 15:54:26
# LastEditors: LAPTOP-22MC5HRI
# Description: Openai Embedding
# FilePath: \openai\template\create\embeding\openai_embed.py
# '''
from .EmbedBase import BaseEmbedding
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
load_dotenv()

class OpenaiEmbeddings(BaseEmbedding):
    def __init__(self, model: str):
        dimension = 1536 if model in ['text-embedding-ada-002', 'text-embedding-3-small'] else 3072
        super().__init__(model, dimension, OpenAIEmbeddings(model=model))
    