# '''
# Author: pang-lee
# Date: 2024-06-28 13:56:50
# LastEditTime: 2024-06-28 13:56:51
# LastEditors: LAPTOP-22MC5HRI
# Description: create function calling tool
# FilePath: \openai\template\create\tool.py
# '''
import re, os
from langchain.tools import BaseTool
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv
load_dotenv()
from langchain_openai import OpenAIEmbeddings
from langchain_ollama import OllamaEmbeddings
from .tools_utils import get_namespace_system_json_embedding, convert_index_to_gpu
from ...logger import Logger
vc_logger = Logger(name='get_vectorstore_logger')

class get_vectorstore(BaseTool):
    def _run(self, query=None):
        if query is None:
            return vc_logger.get_logger().error("In get vectorstore tool, query cannot be None")

        try:
            vc_logger.get_logger().info(f'The Question of your: {query}')

            # 使用正則表達式提取 db 和 reply
            db_pattern = re.compile(r'db=(.*?)[\s)]')
            reply_pattern = re.compile(r'reply:\s*(.*)', re.DOTALL)

            db_match = db_pattern.search(self.description)
            reply_match = reply_pattern.search(self.description)

            db_value = db_match.group(1).strip() if db_match else None
            reply_value = reply_match.group(1).strip() if reply_match else None
            
            vc_logger.get_logger().info(f'Succefully Find the vector DB: {db_value}')
            
            # 獲取設定檔中的Embedding供應商和模型
            vendor, model = get_namespace_system_json_embedding('/'.join(db_value.split('/')[:2]))
            
            if not vendor or not model: # 如果沒有供應商或模型, 跳出查詢
                return vc_logger.get_logger().error(f"In get vectorstore tool, embdding vendor: {vendor} or Model: {model} is None")
            
            if vendor is 'OpenaiEmbeddings':
                embed = OpenAIEmbeddings(model=model)
                
            elif vendor is 'OllamaEmbeddings':
                embed = OllamaEmbeddings(model=model, base_url=os.getenv("OLLAMA_SERVER"), keep_alive=0)
            
            # 獲取當前目錄的向量庫路徑
            local_vc = FAISS.load_local(db_value, index_name=db_value.split('/')[-1], embeddings=embed, allow_dangerous_deserialization=True)
            
            # 將 FAISS 索引轉換為 GPU 索引
            local_vc.index = convert_index_to_gpu(local_vc.index, vc_logger.get_logger())            

            # 使用 similarity_search 執行查詢
            result = local_vc.similarity_search(query, k=3)
            vc_logger.get_logger().info(f'Check the vectorDB search result: {result}')

            if not result:
                respond = "回覆:「抱歉我剛查過了,我有些不太確定你的問題,可以再說的詳細點嗎?」"
            else:
                contents = "\n".join([f"- {doc.page_content}" for doc in result])
                respond = f"[結果] {contents} | \
                            [規則] 嚴格遵守{reply_value} | \
                            [限制] 僅處理當前查詢"

            return respond

        except Exception as e:
            return vc_logger.get_logger().error(f"An error occurred in get vectorstore vector similarity search: {e}")
                
    def _arun(self):
        raise NotImplementedError("Tools does not support async")
    
    
