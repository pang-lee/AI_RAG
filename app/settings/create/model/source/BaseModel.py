# '''
# Author: pang-lee
# Date: 2024-07-26 17:11:08
# LastEditTime: 2024-07-26 17:11:08
# LastEditors: LAPTOP-22MC5HRI
# Description: The BaseModel
# FilePath: \openai\application\settings\create\model\BaseModel.py
# '''
from abc import ABC, abstractmethod

class BaseModel(ABC):
    def __init__(self):
        pass
    
    @abstractmethod
    def build_model(self):
        pass
    
    @abstractmethod
    def fetch_model(self):
        pass
    
    @abstractmethod
    def chat_with_ai(self):
        pass


