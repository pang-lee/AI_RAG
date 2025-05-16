# '''
# Author: pang-lee
# Date: 2024-06-27 18:05:47
# LastEditTime: 2024-06-27 18:05:47
# LastEditors: LAPTOP-22MC5HRI
# Description: The openai assistant
# FilePath: \openai\template\system.py
# '''
import os, json, ast, re
from ..tools_template.get_vectorstore import get_vectorstore
from ..helper.token import count_tokens
from .source.openai_assistant_source import CustomAssistant
from langchain_core.agents import AgentFinish
from .source.BaseModel import BaseModel
from ...logger import Logger
from dotenv import load_dotenv
load_dotenv()
openai_model_logger = Logger(name='openai_model_logger')

class Openai(BaseModel):
    def __init__(self):
        self.tools = []
        self.client_assistant = None

    def build_model(self, **kwargs):
        try:
            self.check_namespace_load_tool(**kwargs)

            # 如果沒有assistant_id, 則創建一個
            client = CustomAssistant.create_assistant(
                name=kwargs.get('name'),
                instructions=kwargs.get('instructions'),
                tools=self.tools,
                model=kwargs.get('model'),
                custom_attribute=kwargs.get('custom_attribute', {}),
                as_agent=True
            )

            
            openai_model_logger.get_logger().info(f"Create Openai client successfully, {client}")
            return True, client.assistant_id

        except Exception as e:
            openai_model_logger.get_logger().error(f"An error occurred in Opani class build_model: {e}")
            return False, ''
            
    def modify_assistant(self, **kwargs):
        try:
            self.check_namespace_load_tool(**kwargs)

            # 构建要传递给 CustomAssistant.modify_assistant 的参数字典
            modify_params = {
                'name': kwargs.get('name'),
                'instructions': kwargs.get('instructions'),
                'tools': self.tools,
                'model': kwargs.get('model'),
                'custom_attribute': kwargs.get('custom_attribute'),
                'assistant_id': kwargs.get('assistant_id'),
                'as_agent': True
            }
            
            # 从字典中移除值为 None 的项
            modify_params = {k: v for k, v in modify_params.items() if v is not None}

            if not modify_params['assistant_id']:
                openai_model_logger.get_logger().error("Modify Assistan need to pass assistant_id")
                raise RuntimeError("Modify Assistan need to pass assistant_id")

            client = CustomAssistant.modify_assistant(**modify_params)
            openai_model_logger.get_logger().info(f"Update Openai client successfully, {client}")

            return True

        except Exception as e:
            openai_model_logger.get_logger().error(f'An error occurred in Openai modify_assistant: {e}')
            return False

    def check_namespace_load_tool(self, **kwargs):
        if kwargs.get('namespace') == '':
            openai_model_logger.get_logger().error('Namespace not found or not provided when running the build_model.')
            raise RuntimeError('Namespace not found or not provided when running the build_model.')

        return self.initialize_model_tools(kwargs.get('namespace'))
    
    def initialize_model_tools(self, namespace_path):
        with open(os.path.join(namespace_path, 'system_setting.json'), 'r', encoding='utf-8') as config_file:
            config = json.load(config_file)
        
        # 确定tools目录的路径
        tools_path = os.path.join(namespace_path, 'tools').replace('\\', '/')
        
        # 检查tools目录是否存在
        if not os.path.exists(tools_path):
            openai_model_logger.get_logger().info(f"The directory {tools_path} does not exist.")
            return
        
        # 判斷有哪些tools是需要載入到assistant的
        filtered = [item for item in os.listdir(tools_path) if item in config['Openai']['function_call_active']]

        # 遍历所有子目录和文件
        for sub_dir in os.listdir(tools_path):
            sub_dir_path = os.path.join(tools_path, sub_dir).replace('\\', '/')
            # 确保这是一个目录
            if os.path.isdir(sub_dir_path) and sub_dir in filtered:
                # 构建 'prompt' 子目录路径
                prompt_dir_path = os.path.join(sub_dir_path, 'prompt').replace('\\', '/')

                # 检查 'prompt' 子目录是否存在
                if os.path.isdir(prompt_dir_path):
                    # 讀取寫入的prompt內容
                    with open(os.path.join(prompt_dir_path, 'prompt.py'), 'r', encoding='utf-8') as file:
                        file_content = file.read()
                    
                    tree = ast.parse(file_content)

                    variables = {}
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Assign):
                            for target in node.targets:
                                if isinstance(target, ast.Name):
                                    variable_name = target.id
                                    # Handle different types of values
                                    if isinstance(node.value, ast.Constant):  # For literal values
                                        variable_value = node.value.value
                                    elif isinstance(node.value, ast.Str):  # For string literals
                                        variable_value = node.value.s
                                    elif isinstance(node.value, ast.JoinedStr):  # For formatted strings
                                        variable_value = ''.join(part.s for part in node.value.values)
                                    else:
                                        openai_model_logger.get_logger().error(f"Unsupported node type: {type(node.value).__name__}")
                                        raise ValueError(f"Unsupported node type: {type(node.value).__name__}")

                                    variables[variable_name] = variable_value

                    try:
                        self.tools.append(get_vectorstore(name=variables['chatbot_name'], description=variables['chatbot_description']))
                        openai_model_logger.get_logger().info(f"Loaded All tools from {prompt_dir_path}")
                    except Exception as e:
                        openai_model_logger.get_logger().error(f"Failed to load tools from {prompt_dir_path}: {e}")
                        raise RuntimeError(f"Failed to load tools from {prompt_dir_path}: {e}")

        return True

    def fetch_model(self, assistant=None, **kwargs):
        if assistant:
            self.client_assistant = CustomAssistant(assistant_id=assistant, as_agent=True)
            path = kwargs.get('path', '')
            self.initialize_model_tools(path)

            return self.client_assistant
        
        openai_model_logger.get_logger().error('Assistant_id not found or not provided when instantiating the Openai model.')
        raise RuntimeError('Assistant_id not found or not provided when instantiating the Openai model.')


    # 执行 Agent 并统计 Token, 函數回傳為(AI生成結果, tool, token數)
    def execute_agent(self, agent, tools, input, max_retries=3, **kwargs):
        tool_map = {tool.name: tool for tool in tools}

        # 初始化 Token 计数
        total_prompt_tokens = count_tokens(input['content'], model=kwargs.get('llm'))
        total_completion_tokens = 0
        total_embedding_tokens = 0
         
        retry_count = 0
        while retry_count < max_retries:
            try:
                # 模拟 Agent 的初始调用
                response = agent.invoke(input)

                while not isinstance(response, AgentFinish):
                    tool_outputs = []
                    for action in response:
                        # 获取工具实例
                        tool = tool_map[action.tool]

                        # 统计工具输入的嵌入 Token 数量
                        embedding_tokens = 0
                        if isinstance(action.tool_input, dict):  # 检查是否为字典
                            for key, value in action.tool_input.items():
                                embedding_tokens += count_tokens(value, model=kwargs.get('embed'))
                        else:
                            # 如果 tool_input 不是字典，直接计算 token 数量
                            embedding_tokens = count_tokens(action.tool_input, model=kwargs.get('embed'))

                        total_embedding_tokens += embedding_tokens

                        # 调用工具
                        tool_output = tool.invoke(action.tool_input)

                        tool_outputs.append(
                            {"output": tool_output, "tool_call_id": action.tool_call_id}
                        )

                    # 统计工具输出的 Completion Tokens
                    for output in tool_outputs:
                        total_completion_tokens += count_tokens(output["output"], model=kwargs.get('llm'))

                    # 继续 Agent 的处理
                    response = agent.invoke(
                        {
                            "tool_outputs": tool_outputs,
                            "run_id": action.run_id,
                            "thread_id": action.thread_id,
                        }
                    )

                    total_completion_tokens += count_tokens(response.return_values["output"], model=kwargs.get('llm'))

                # 输出最终 Token 消耗
                total_tokens = total_prompt_tokens + total_completion_tokens + total_embedding_tokens

                # 檢查是否有調用到tool, 如果沒有則回傳None
                if 'action' in locals():
                    return response, action.tool, total_prompt_tokens, total_completion_tokens, total_embedding_tokens, total_tokens

                else:          
                    return response, None, total_prompt_tokens, total_completion_tokens, total_embedding_tokens, total_tokens

            except Exception as e:
                openai_model_logger.get_logger().error(f'When run Openai execute_agent occur Openai rate limit error: {e}')

                error_message = str(e)

                # 提取包含 `last_error` 的 JSON 信息
                json_start = error_message.find("{")
                json_end = error_message.rfind("}")

                if json_start != -1 and json_end != -1:
                    try:
                        error_data = json.loads(error_message[json_start:json_end + 1])  # 提取 JSON 部分
                        
                        openai_model_logger.get_logger().error(f'get error data for error_data: {error_data}')
                        
                        if "last_error" in error_data:
                            last_error = error_data["last_error"]

                            # 获取等待时间
                            wait_time_match = re.search(r"try again in (\d+\.?\d*)s", last_error["message"])
                           
                            # 如果沒有獲得時間, 錯誤可能為超出Token, 重新再測試
                            if wait_time_match:
                                return False, None, float(wait_time_match.group(1)), 0, 0, 0                            
                            else:
                                # 如果沒有找到等待時間，修改輸入並重試
                                openai_model_logger.get_logger().info("No wait time specified. Modifying rebuild the thread and retrying.")
                                if "thread_id" in input:
                                    input.pop("thread_id")
                                    openai_model_logger.get_logger().info(f"Retrying with modified input: {input}")

                                retry_count += 1
                                continue  # 重試循環

                    except json.JSONDecodeError:
                        openai_model_logger.get_logger().error(f"Failed to parse JSON error for more action in execute_agent")
                        return False, None, 0, 0, 0, 0
                
                # 錯誤無法解析出時間(可能是OpenAI問題), 回傳結束              
                return False, None, 0, 0, 0, 0
   
    def chat_with_ai(self, query, session, namespace_path, **kwargs):
        if self.client_assistant is None:
            openai_model_logger.get_logger().error('There is no assistant_id provided when chatting with the Openai model.')
            raise RuntimeError('There is no assistant_id provided when chatting with the Openai model.')
        
        # 构造 session.json 文件的路径
        session_file_path = os.path.join(namespace_path, 'chat_history', f"{session}.json")

        try:                    
            session_data = None  # 初始化
            if os.path.exists(session_file_path):  # 如果文件存在
                try:
                    with open(session_file_path, 'r', encoding='utf-8') as f:
                        session_data = json.load(f)  # 尝试加载 JSON 数据
                        if not session_data:  # 如果内容为空
                            openai_model_logger.get_logger().warning(f"{session_file_path} is empty, resetting session_data.")
                            session_data = None
                except json.JSONDecodeError as e:  # 如果 JSON 无效
                    openai_model_logger.get_logger().error(f"Error parsing {session_file_path}: {e}. Resetting session_data.")
                    session_data = None
            else:
                openai_model_logger.get_logger().info(f"{session_file_path} does not exist. A new session will be created.")


            # 检查是否有過對話紀錄session.json
            if not session_data: # 如果不存在，则创建一个新的 session.json 文件

                result, tool, total_prompt_tokens, total_completion_tokens, total_embedding_tokens, total_tokens = self.execute_agent(self.client_assistant, self.tools, {'content': query}, **kwargs)


                # 如果回傳的不是錯誤訊息False, 則寫入thread_id
                if not isinstance(result, bool):
                    with open(session_file_path, 'w', encoding='utf-8') as f:
                        session_data = {"session_id": session, "thread_id": result.return_values['thread_id'], "cnt": 1}
                        json.dump(session_data, f, ensure_ascii=False, indent=4)
                        openai_model_logger.get_logger().info(f"Created new session file with {session} in {session_file_path}")

                    openai_model_logger.get_logger().info(f"{session_file_path} has chat with ai thread_id: {result.return_values['thread_id']}")

            # 如果存在，则读取對話紀錄 session.json 文件
            else:
                # 當對話紀錄超過次數, 重建Thread_id
                if session_data['cnt'] > 5:                    
                    result, tool, total_prompt_tokens, total_completion_tokens, total_embedding_tokens, total_tokens = self.execute_agent(self.client_assistant, self.tools, {'content': query}, **kwargs)
                 
                    # 如果回傳的不是錯誤訊息, 代表訊息成功生成, 刪除thread
                    if not isinstance(result, bool):
                        del_status = CustomAssistant.del_thread(session_data['thread_id'])
                        openai_model_logger.get_logger().info(f"Delete the original thread {del_status.id}, status {del_status.deleted}, new thread {result.return_values['thread_id']}")

                    with open(session_file_path, 'w', encoding='utf-8') as f:
                        session_data = {"session_id": session, "thread_id": result.return_values['thread_id'], "cnt": 1}
                        json.dump(session_data, f, ensure_ascii=False, indent=4)

                    openai_model_logger.get_logger().info(f"Exceed the limit of chat session, create new thread in path: {session_file_path} with thread {result.return_values['thread_id']}")
                
                # 沒超過詢問次數5次紀錄, 對話使用原先的上下文
                else:
                    result, tool, total_prompt_tokens, total_completion_tokens, total_embedding_tokens, total_tokens = self.execute_agent(self.client_assistant, self.tools, {'content': query, "thread_id": session_data['thread_id']}, **kwargs)

                    # 如果詢問中超出openai的使用上限, 清除當前thread, 並重新建一個
                    if not isinstance(result, bool) and result.return_values['thread_id'] != session_data['thread_id']:
                        del_status = CustomAssistant.del_thread(session_data['thread_id'])
                        openai_model_logger.get_logger().info(f"When calling openai get some error, delete thread {session_data['thread_id']} and re-create new one : {result.return_values['thread_id']}")

                        session_data['cnt'] = 1
                        session_data['thread_id'] = result.return_values['thread_id']
                    else:
                        session_data['cnt'] += 1

                    with open(session_file_path, 'w', encoding='utf-8') as f:
                        json.dump(session_data, f, ensure_ascii=False, indent=4)

                    openai_model_logger.get_logger().info(f"Loaded existing chat session: {session_data['thread_id']}")

            # 如果result是false, 則第一個參數回傳忙碌中
            # 第二個參數調用的funcall為空
            # 第三個參數錯誤為需等待N秒, 那麼total_prompt_token為需要等待多少秒(從agent的except出錯部分調用)
            # 第四個參數為False, 使得此任務可在外部被放入到Queue中, 等帶下一次執行
            if isinstance(result, bool) or result is False:
                wait_time = total_prompt_tokens
                return "AI忙碌中, 請稍等", '', wait_time, False, 0, 0

            # 若成功調用, 則將openai的生成結果, 並會帶tokens數量, 使用哪個tool, 如果沒有則回傳get_vectorstore中所設定的, '查詢不到'
            if tool is None:
                return result.return_values['output'], '', total_prompt_tokens, total_completion_tokens, total_embedding_tokens, total_tokens

            else:
                return result.return_values['output'], tool, total_prompt_tokens, total_completion_tokens, total_embedding_tokens, total_tokens
        
        except Exception as e:
            openai_model_logger.get_logger().error(f'When run Openai chat_with_ai occur error: {e}')



