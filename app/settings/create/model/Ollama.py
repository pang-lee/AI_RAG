# '''
# Author: pang-lee
# Date: 2024-05-21 16:05:47
# LastEditTime: 2024-06-27 16:05:47
# LastEditors: LAPTOP-22MC5HRI
# Description: The ollama model for service
# '''
import os, json
from ..helper.token import count_tokens
from .source.BaseModel import BaseModel
from ...logger import Logger
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
load_dotenv()
ollama_model_logger = Logger(name='ollama_model_logger')

class Ollama(BaseModel):
    def __init__(self):
        super.__init__(ollama_model_logger)
        self.llm = None
        self.config = None

    def fetch_model(self, **kwargs):
        path = kwargs.get('path', '')
        self.initialize_model_tools(path)
        self.config = self.read_setting_file(path)
        
        self.llm = ChatOllama(
            model=self.config['model'],
            base_url=os.getenv('OLLAMA_SERVER'),
            temperature=self.config['temperature'],
            max_tokens=self.config['max_tokens'],
            keep_alive=self.config['keep_alive'],
            top_p=self.config['top_p'],
            top_k=self.config['top_k'],
            num_ctx=self.config['num_ctx'],
            num_gpu=self.config['num_gpu']
        )
        
        return self.llm

    def execute_agent(self, query, **kwargs):
        # 定義提示模板
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"{self.config['system_prompt']}"),
            ("user", "{input}")
        ])

        # 創建處理鏈
        chain = prompt | self.llm.bind_tools(self.tools) | StrOutputParser()
        response = chain.invoke(query)

    
    def chat_with_ai(self, query, session, namespace_path, **kwargs):
        if self.llm is None:
            self.log.error('There is no ollama llm provided when chatting with the ollama model.')
            raise RuntimeError('There is no ollama llm provided when chatting with the ollama model.')
        
        # 构造 session.json 文件的路径
        session_file_path = os.path.join(namespace_path, 'chat_history', f"{session}.json")

        try:
            session_data = self.check_chat_session(session_file_path)

            # 检查是否有過對話紀錄session.json
            if not session_data: # 如果不存在，则创建一个新的 session.json 文件
                result, tool, total_prompt_tokens, total_completion_tokens, total_embedding_tokens, total_tokens = self.execute_agent({"input": query}, **kwargs)
                
                # 如果回傳的不是錯誤訊息False, 則把對話紀錄存下
                if not isinstance(result, bool):
                    with open(session_file_path, 'w', encoding='utf-8') as f:
                        session_data = {"session_id": session, "thread_id": result.return_values['thread_id'], "cnt": 1}
                        json.dump(session_data, f, ensure_ascii=False, indent=4)
                        self.log.info(f"Created new session file with {session} in {session_file_path}")

                    self.log.info(f"{session_file_path} has chat with ai thread_id: {result.return_values['thread_id']}")

            else: # 如果存在，则读取對話紀錄 session.json 文件
                pass
            
        except Exception as e:
            self.log.error(f'When run Ollama chat_with_ai occur error: {e}')
            raise RuntimeError(f'When run Ollama chat_with_ai occur error: {e}')
            
    def build_model(self):
        return super().build_model()