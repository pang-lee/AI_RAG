# '''
# Author: pang-lee
# Date: 2024-07-31 16:51:14
# LastEditTime: 2024-07-31 16:51:14
# LastEditors: LAPTOP-22MC5HRI
# Description: Tools utils
# FilePath: \openai\application\settings\create\tools_template\tools_utils.py
# '''
import os, json
import faiss
import torch

def get_namespace_system_json_embedding(file_path):
    # 拼接得到 "system.json" 文件的路径
    system_json_path = os.path.join(file_path, 'system_setting.json')

    with open(system_json_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    embedding_model = data.get('Embedding', {}).get('model', {})
    
    # 直接返回 key 和 value
    for key, value in embedding_model.items():
        return key, value
    
    # 如果 embedding_model 為空，返回默認值
    return None, None

def convert_index_to_gpu(index, log):
    """將 FAISS 索引轉為 GPU 索引（如果有可用 GPU），否則返回原索引"""
    if not torch.cuda.is_available():
        log.info(f"當前torch檢查結果: {torch.cuda.is_available()}, 沒有GPU, 使用CPU 索引")
        return index
    
    if faiss.get_num_gpus() > 0:
        log.info(f"檢測到 {faiss.get_num_gpus()} 個 GPU，轉換為 GPU 索引")
        res = faiss.StandardGpuResources()
        return faiss.index_cpu_to_gpu(res, 0, index)
    else:
        log.info("警告：未檢測到 GPU，使用 CPU 索引")
        return index