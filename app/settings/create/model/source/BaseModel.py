# '''
# Author: pang-lee
# Date: 2024-07-26 17:11:08
# LastEditTime: 2024-07-26 17:11:08
# LastEditors: LAPTOP-22MC5HRI
# Description: The BaseModel
# FilePath: \settings\create\model\BaseModel.py
# '''
from abc import ABC, abstractmethod
import os, json, ast
from ...tools_template.get_vectorstore import get_vectorstore

class BaseModel(ABC):
    def __init__(self, log):
        self.tools = []
        self.log = log.get_logger()
    
    def check_namespace_load_tool(self, **kwargs):
        if kwargs.get('namespace') == '':
            self.log.error('Namespace not found or not provided when running the build_model.')
            raise RuntimeError('Namespace not found or not provided when running the build_model.')

        return self.initialize_model_tools(kwargs.get('namespace'))
    
    def read_setting_file(self, namespace_path):
        with open(os.path.join(namespace_path, 'system_setting.json'), 'r', encoding='utf-8') as config_file:
            config = json.load(config_file)
        
        filtered_data = {key: value for key, value in config.items() if value.get("choosen_ai") == 1}
        
        return filtered_data

    def initialize_model_tools(self, namespace_path):
        config = self.read_setting_file(namespace_path)

        # 确定tools目录的路径
        tools_path = os.path.join(namespace_path, 'tools').replace('\\', '/')
        
        # 检查tools目录是否存在
        if not os.path.exists(tools_path):
            self.log.info(f"The directory {tools_path} does not exist.")
            return
        
        # 判斷有哪些tools是需要載入到assistant的
        filtered = [item for item in os.listdir(tools_path) if item in config['function_call_active']]

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
                                        self.log.error(f"Unsupported node type: {type(node.value).__name__}")
                                        raise ValueError(f"Unsupported node type: {type(node.value).__name__}")

                                    variables[variable_name] = variable_value

                    try:
                        self.tools.append(get_vectorstore(name=variables['chatbot_name'], description=variables['chatbot_description']))
                        self.log.info(f"Loaded All tools from {prompt_dir_path}")
                    except Exception as e:
                        self.log.error(f"Failed to load tools from {prompt_dir_path}: {e}")
                        raise RuntimeError(f"Failed to load tools from {prompt_dir_path}: {e}")

        return True

    def check_chat_session(self, session_file_path):
        session_data = None  # 初始化
        if os.path.exists(session_file_path):  # 如果文件存在
            try:
                with open(session_file_path, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)  # 尝试加载 JSON 数据
                    if not session_data:  # 如果内容为空
                        self.log.warning(f"{session_file_path} is empty, resetting session_data.")
                        session_data = None
            except json.JSONDecodeError as e:  # 如果 JSON 无效
                self.log.error(f"Error parsing {session_file_path}: {e}. Resetting session_data.")
                session_data = None
        else:
            self.log.info(f"{session_file_path} does not exist. A new session will be created.")
        
        return session_data

    @abstractmethod
    def execute_agent(self):
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
