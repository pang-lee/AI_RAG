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

    def execute_agent(self, query, history=None, **kwargs):
        try:
            # 獲取當前模型名稱
            model_name = self.config['model']
            
            # 如果有歷史對話，將其加入提示模板
            messages = [
                ("system", f"{self.config['system_prompt']}"),
            ]

            # 將歷史對話加入提示（如果存在）
            if history:
                for entry in history:
                    messages.append(("user", entry["user"]))
                    messages.append(("assistant", entry["assistant"]))

            # 加入當前查詢
            messages.append(("user", "{input}"))
            
            # 構造完整的提示文本（用於 token 計數）
            prompt_text = self.config['system_prompt']
            if history:
                for entry in history:
                    prompt_text += f"\nUser: {entry['user']}\nAssistant: {entry['assistant']}"
            prompt_text += f"\nUser: {query}"
        
            # 計算 prompt tokens
            prompt_tokens = count_tokens(prompt_text, model=model_name)
            
            self.log.info(f"Current chat context token: {prompt_tokens}")

            # 定義提示模板
            prompt = ChatPromptTemplate.from_messages(messages)

            # 創建處理鏈
            chain = prompt | self.llm.bind_tools(self.tools) | StrOutputParser()
            response_data = chain.invoke(query)
            
            # 檢查是否調用了工具
            selected_tool = None
            response_text = None
            embed_tokens = 0

            # 假設 response_data 是結構化回應，可能包含工具調用
            if hasattr(response_data, 'tool_calls') and response_data.tool_calls:
                # 如果有工具調用，選擇第一個工具（根據實際結構調整）
                selected_tool = response_data.tool_calls[0]['name']
                tool_name = selected_tool
                tool_args = response_data.tool_calls[0]['args']

                # 執行工具
                tool_instance = next((tool for tool in self.tools if tool.name == tool_name), None)
                if tool_instance:
                    tool_result = tool_instance._run(**tool_args)
                    # 檢查工具回應是否包含 embed_tokens
                    if isinstance(tool_result, dict) and 'response' in tool_result and 'embed_tokens' in tool_result:
                        response_text = tool_result['response']
                        embed_tokens = tool_result['embed_tokens']
                    else:
                        response_text = str(tool_result)
            else:
                # 無工具調用，直接使用回應內容
                response_text = str(response_data)

            # 計算 completion tokens
            completion_tokens = count_tokens(response_text, model=model_name)

            # 計算總 token 數
            total_tokens = prompt_tokens + completion_tokens + embed_tokens

            return response_text, selected_tool or '', prompt_tokens, completion_tokens, embed_tokens, total_tokens

        except Exception as e:
            self.log.error(f"When Running Ollama agent failed: {e}")
            return False, None, 0, 0, 0, 0
    
    def chat_with_ai(self, query, session, namespace_path, max_history=3, **kwargs):
        if self.llm is None:
            self.log.error('There is no ollama llm provided when chatting with the ollama model.')
            raise RuntimeError('There is no ollama llm provided when chatting with the ollama model.')
        
        # 构造 session.json 文件的路径
        session_file_path = os.path.join(namespace_path, 'chat_history', f"{session}.json")

        try:
            session_data = self.check_chat_session(session_file_path)

            # 检查是否有過對話紀錄session.json
            if not session_data: # 如果不存在，则创建一个新的 session.json 文件
                session_data = {
                    "session_id": session,
                    "history": [],  # 用於儲存對話歷史
                    "cnt": 0
                }

            result, tool, total_prompt_tokens, total_completion_tokens, total_embedding_tokens, total_tokens = self.execute_agent({"input": query}, session_data["history"], **kwargs)

            # 如果回傳的不是錯誤訊息False, 則把對話紀錄存下
            if not isinstance(result, bool):
                # 將新對話追加到歷史
                session_data["history"].append({
                    "user": query,
                    "assistant": result
                })
                session_data["cnt"] += 1

                # 保留最近 max_history 次對話
                if len(session_data["history"]) > max_history:
                    session_data["history"] = session_data["history"][-max_history:]
                    self.log.info(f"Trimmed history to last {max_history} conversations for session {session}")

                with open(session_file_path, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, ensure_ascii=False, indent=4)
                    self.log.info(f"Created new session file with {session} in {session_file_path}")

                self.log.info(f"{session_file_path} has chat with ai")

            return result, tool, total_prompt_tokens, total_completion_tokens, total_embedding_tokens, total_tokens 

        except Exception as e:
            self.log.error(f'When run Ollama chat_with_ai occur error: {e}')
            raise RuntimeError(f'When run Ollama chat_with_ai occur error: {e}')
            
    def build_model(self):
        return super().build_model()