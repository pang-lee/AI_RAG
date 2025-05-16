# '''
# Author: pang-lee
# Date: 2024-07-31 16:51:14
# LastEditTime: 2024-07-31 16:51:14
# LastEditors: LAPTOP-22MC5HRI
# Description: Tools utils
# FilePath: \openai\application\settings\create\tools_template\tools_utils.py
# '''
import os, json

def get_namespace_system_json_embedding(file_path):
    # 拼接得到 "system.json" 文件的路径
    system_json_path = os.path.join(file_path, 'system_setting.json')

    with open(system_json_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    embedding_model = data.get('Embedding', {}).get('model', {})
    
    # 只获取 embedding_model 的dict中value的部分
    embedding_model_values = list(embedding_model.values())

    return embedding_model_values[0]