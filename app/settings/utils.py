# '''
# Author: pang-lee
# Date: 2024-07-01 17:10:16
# LastEditTime: 2024-07-01 17:10:16
# LastEditors: LAPTOP-22MC5HRI
# Description: read system json file
# FilePath: \openai\template\create\read_system_json.py
# '''
import json, traceback, importlib, os, shutil
from .create.embedding.EmbedBase import BaseEmbedding
from .logger import Logger
utils_logger = Logger(name='utils_logger')

def config_path(namespace, id):
    return os.path.join(namespace, id, 'system_setting.json')

def load_config(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as config_file:
            config = json.load(config_file)
            utils_logger.get_logger().info(f"Successfully loaded the config file {file_path}.")
        return config
    except FileNotFoundError:
        utils_logger.get_logger().error(f"Error: The file {file_path} was not found. The Exception: {traceback.print_exc()}")
    except json.JSONDecodeError:
        utils_logger.get_logger().error(f"Error: Failed to decode JSON from the file {file_path}. The Exception: {traceback.print_exc()}")
    except Exception as e:
        utils_logger.get_logger().error(f"An unexpected error occurred: {e}. The Exception: {traceback.print_exc()}")

def get_model_by_path(namespace, id):
    config = load_config(config_path(namespace, id))
    
    embed_config = config.get('Embedding', {}).get('model', {})
    embed_type, model = next(iter(embed_config.items()))

    module_name = f"settings.create.embedding.{embed_type}"
    class_name = embed_type
    
    # 动态导入模块
    module = importlib.import_module(module_name)
    # 获取类
    EmbeddingClass = getattr(module, class_name)

    # 确保EmbeddingClass继承自BaseEmbedding
    if not issubclass(EmbeddingClass, BaseEmbedding):
        utils_logger.get_logger().info(f"{class_name} must inherit from BaseEmbedding")
        raise TypeError(f"{class_name} must inherit from BaseEmbedding")

    # 初始化类
    return EmbeddingClass(model=model)

def do_embedding(task_data):
    try:
        vector_path = os.path.join(task_data['namespace'], task_data['ID'], 'vectorstore', task_data['data']['aics_vdb_code'])
    
        # 检查 vector_path 是否存在, 如果不存在，则创建该路径  
        if not os.path.exists(vector_path):
            os.makedirs(vector_path)
            utils_logger.get_logger().info(f"Current vectordb is not exist, created vector path: {vector_path}")

        model = get_model_by_path(task_data['namespace'], task_data['ID'])
        utils_logger.get_logger().info(f"Embedding model is init, start file2doc with: {task_data['namespace']}{task_data['ID']}")
       
        transfer_result = model.transfer_file2doc([doc.replace('\\/', '/') for doc in task_data['data']['file_paths']])
       
        if transfer_result is None:
            utils_logger.get_logger().error(f"transfer_file2doc failed with errors: {transfer_result['errors']}")
            return False, ''

        task_data['data']['files_docs'] = transfer_result
        task_data["data"].pop("file_paths")
        serialize_result, docs = do_vectordb(task_data)

        # 回傳serialize_result為bool代表是否成功轉向量, 第二個是切割完畢的document組合array of dict
        return serialize_result, docs
    except:
        # 回傳第一個參數為bool代表是否成功, 第二個參數為array of dict的document
        utils_logger.get_logger().error(f"Failed to do_embedding in utils.py with error: {e}")
        return False, []

def do_vectordb(task_data):
    model = get_model_by_path(task_data['namespace'], task_data['ID'])
    utils_logger.get_logger().info(f"Embedding model is init, start doc to vectorstore with: {task_data['namespace']}/{task_data['ID']}")

    return model.embed_vector_db(task_data)

def setting_tools(task_data):
    try:
        config = load_config(config_path(task_data['namespace'], task_data['ID']))

        # 找到 choosen_ai 為 1 的 key
        chosen_entry = None
        for key, value in config.items():
            if isinstance(value, dict) and value.get('choosen_ai') == 1:
                chosen_entry = key
                break
        
        if not chosen_entry:
            utils_logger.get_logger().info("Cannot find which model vendor choosen in setting_tools")
            raise RuntimeError("Cannot find which model vendor choosen in ")

        # 如果後台的狀態為啟用, 那會將function call的名字寫入system_setting的function_call_active中
        tool_path = os.path.join(task_data['namespace'], task_data['ID'], 'tools', task_data['data']['aics_funcall_code'])
        prompt_file_path = os.path.join(tool_path, 'prompt', 'prompt.py').replace('\\', '/')

        if not os.path.isdir(tool_path):
            os.makedirs(tool_path)
            os.makedirs(os.path.join(tool_path, 'prompt'))

        chatbot_description = f"""
            當詢問到和{task_data['data']['aics_funcall_intro'].strip()}有關的內容關鍵字或相似描述時, 解析出想詢問的內容做為query.
            並使用此Tools來查詢指定的向量庫(db={task_data['namespace']}/{task_data['ID']}/vectorstore/{task_data['data']['aics_vdb_code'][0]})資料.
            reply:
            {task_data['data']['aics_funcall_reply'].strip()}
        """

        # 将变量写入 prompt.py 文件, 若已經有prompt的話, 則視為更新prompt
        with open(prompt_file_path, 'w', encoding='utf-8') as f:
            f.write(f"chatbot_name = '{task_data['data']['aics_funcall_name']}'\n")
            f.write(f'chatbot_description = """{chatbot_description}"""\n')

        utils_logger.get_logger().info(f"Successfully wrote or update prompt.py to {prompt_file_path}")

        # 如果後台不啟用某Tools, 更新system_setting的function_call_active並行assistant的修改
        if task_data['data']['aics_funcall_stat'] == '0':
            # 如果function_call_active中沒有此function_calling_code則直接跳過
            if task_data['data']['aics_funcall_code'] in config[chosen_entry]['function_call_active']:
                config[chosen_entry]['function_call_active'] = [item for item in config[chosen_entry]['function_call_active'] if item != task_data['data']['aics_funcall_code']]
            
                # 将更新后的function_call_active写回文件
                with open(os.path.join(task_data['namespace'], task_data['ID'], 'system_setting.json'), 'w', encoding='utf-8') as file:
                    json.dump(config, file, ensure_ascii=False, indent=4)


                utils_logger.get_logger().info(f"Funcall {config[chosen_entry]['function_call_active']} current state is 0, shold not in function_call_active_array")

        else:
   
            # 若資料不存在則添加入function_call_active中
            if task_data['data']['aics_funcall_code'] not in config[chosen_entry]['function_call_active']:
                config[chosen_entry]['function_call_active'].append(task_data['data']['aics_funcall_code'])

                # 将更新后的function_call_active写回文件
                with open(os.path.join(task_data['namespace'], task_data['ID'], 'system_setting.json'), 'w', encoding='utf-8') as file:
                    json.dump(config, file, ensure_ascii=False, indent=4)

                utils_logger.get_logger().info(f"Successfule change the which funcall is active {config[chosen_entry]['function_call_active']}")


        # 根据路径 settings/create/ 加载相应的 AI 模块
        module_path = f"settings.create.model.{chosen_entry}"
        
        if chosen_entry == 'Openai':
            module = importlib.import_module(module_path)
            ai_class = getattr(module, chosen_entry)()
            ai_class.modify_assistant(assistant_id=config[chosen_entry].get('assistant_id'), namespace=f"{task_data['namespace']}/{task_data['ID']}")

        return True
    
    except Exception as e:
        utils_logger.get_logger().error(f"An error occurred when setting tools: {e}")
        return False

            
def delete_tools(task_data):
    try:
        config = load_config(config_path(task_data['namespace'], task_data['ID']))
        
        # 找到 choosen_ai 為 1 的 key
        chosen_entry = None
        for key, value in config.items():
            if isinstance(value, dict) and value.get('choosen_ai') == 1:
                chosen_entry = key
                break
        
        if not chosen_entry:
            err_msg = 'Cannot find which model vendor choosen in delete_tool'
            utils_logger.get_logger().info(f"{err_msg}")
            return False
        
        # 如果後台的狀態為啟用, 那會將function call的名字寫入system_setting的function_call_active中
        tool_path = os.path.join(task_data['namespace'], task_data['ID'], 'tools', task_data['data']['aics_funcall_code'])
        
        # 檢查aics_funcall_code是否有在function_call_active的陣列中, 如果有需要先關閉才能刪除
        if task_data['data']['aics_funcall_code'] in config[chosen_entry]['function_call_active']:
            err_msg = "Cannot delete because {task_data['data']['aics_funcall_code']} in function_call_active"
            utils_logger.get_logger().error(f"{err_msg}")
            return False
        else:
            # 刪除掉tools的資料夾
            if os.path.exists(tool_path):
                shutil.rmtree(tool_path)
                utils_logger.get_logger().info(f"Directory '{tool_path}' has been removed")

        # 根据路径 settings/create/ 加载相应的 AI 模块
        module_path = f"settings.create.model.{chosen_entry}"
        
        if chosen_entry == 'Openai':
            module = importlib.import_module(module_path)
            ai_class = getattr(module, chosen_entry)()
            ai_class.modify_assistant(assistant_id=config[chosen_entry].get('assistant_id'), namespace=f"{task_data['namespace']}/{task_data['ID']}")

        return True
    
    except Exception as e:
        utils_logger.get_logger().error(f"An error occurred when delete tools: {e}")

def delete_vdb(task_data):
    try:
        vdb_path = os.path.join('./', task_data['namespace'], task_data['ID'], 'vectorstore', task_data['data']['aics_vdb_code'])
        
        if os.path.exists(vdb_path):
            shutil.rmtree(vdb_path)
            utils_logger.get_logger().info(f"VectorStore '{vdb_path}' has been removed")
        utils_logger.get_logger().info(f"VectorStore '{vdb_path}' is not init, no need to delete anything")
     
        return True

    except Exception as e:
        utils_logger.get_logger().error(f"An error occurred when delete vdb: {e}")
        return False


def delete_datasource(task_data):
    try:
        model = get_model_by_path(task_data['namespace'], task_data['ID'])
        utils_logger.get_logger().info(f"Embedding model is init, start to delete datasource from vectordb with: {task_data['namespace']}/{task_data['ID']}")

        return model.delete_datasource(task_data)

    except Exception as e:
        utils_logger.get_logger().error(f"An error occurred when delete datasource from vectordb: {e}")




