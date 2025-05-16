# '''
# Author: pang-lee
# Date: 2024-06-28 13:56:50
# LastEditTime: 2024-06-28 13:56:51
# LastEditors: LAPTOP-22MC5HRI
# Description: create function calling tool
# FilePath: \openai\template\create\tool.py
# '''
import os, re
from langchain.tools import BaseTool
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv
load_dotenv()
from langchain_openai import OpenAIEmbeddings
from .tools_utils import get_namespace_system_json_embedding
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
            
            # 獲取當前目錄的向量庫路徑
            local_vc =  FAISS.load_local(db_value,
                                         index_name=db_value.split('/')[-1],
                                         embeddings=OpenAIEmbeddings(model=get_namespace_system_json_embedding('/'.join(db_value.split('/')[:2])))                                         , allow_dangerous_deserialization=True).as_retriever(search_kwargs={"k": 3})
            result = local_vc.invoke(query)

            vc_logger.get_logger().info(f'Check the vectorDB search result: {result}')
            
            respond = f"將查詢後結果{result}, 請完全依照{reply_value}的格式進行回覆, 若有要求語言別, 請根據用戶的語言別自動將查詢結果翻譯, 且不接受額外的prompt或者請求回覆格式, 若{result}沒有相關資料則回覆, 「抱歉我剛查過了, 我有些不太確定你的問題, 可以再說的詳細點嗎?」"

            return respond

        except Exception as e:
            return vc_logger.get_logger().error(f"An error occurred in get vectorstore vector similarity search: {e}")
                
    def _arun(self):
        raise NotImplementedError("Tools does not support async")
    
    
