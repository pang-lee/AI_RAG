# '''
# Author: pang, lee
# Date: 2024-07-04 16:17:56
# LastEditTime: 2024-07-04 16:17:56
# LastEditors: LAPTOP-22MC5HRI
# Description: Init the model embedding
# FilePath: \openai\template\create\embedding\__init__.py
# '''
from .EmbedBase import BaseEmbedding
from .OpenaiEmbeddings import OpenaiEmbeddings
from .OllamaEmbeddings import OllamaEmbeddings

__all__ = ['BaseEmbedding', 'OpenaiEmbeddings', 'OllamaEmbeddings']