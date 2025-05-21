# '''
# Author: pang, lee
# Date: 2024-07-04 15:55:08
# LastEditTime: 2024-07-04 15:55:08
# LastEditors: LAPTOP-22MC5HRI
# Description: Qianfan Embedding
# FilePath: \openai\template\create\embeding\QianfanEmbeddings.py
# '''
from .EmbedBase import BaseEmbedding
from langchain_community.embeddings import OllamaEmbeddings
import os
from dotenv import load_dotenv
load_dotenv()

class OllamaEmbeddings(BaseEmbedding):
    def __init__(self, model: str):
        dimension = {'mxbai-embed-large': 1024, 'nomic-embed-text': 768}.get(model, 1024)
        ollam_embed = OllamaEmbeddings(model=model, base_url=os.getenv("OLLAMA_SERVER"), keep_alive=0)
        
        super().__init__(model, dimension, ollam_embed)