# '''
# Author: pang-lee
# Date: 2024-07-23 16:20:42
# LastEditTime: 2024-07-23 16:20:43
# LastEditors: LAPTOP-22MC5HRI
# Description: In User Settings Edit
# FilePath: \openai\application\index.py
# '''
import json, time, os, importlib
from dotenv import load_dotenv
load_dotenv()
from apscheduler.schedulers.background import BackgroundScheduler
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from settings import logger, redis as my_redis, generate_template, utils
from queue import Queue
from threading import Thread
from functools import partial

os.environ['OPENAI_API_KEY']=os.getenv('OPENAI_KEY')

class TaskProcessor:
    def __init__(self, redis_cluster=None, log=None):
        if redis_cluster is None or log is None:
            raise RuntimeError('Redis Cluster And Log Must Be Specify When Init The TaskProcessor.')
        
        try:
            self.redis = redis_cluster
            self.log = log
            self.task_queue = Queue()
            self.thread_pool = ThreadPoolExecutor(max_workers=4)
            self.process_pool = ProcessPoolExecutor(max_workers=4)

            # 启动后台线程处理队列
            self.worker_thread = Thread(target=self.process_queue, name="rework")
            self.worker_thread.daemon = True  # 确保后台线程在主线程退出时自动结束
            self.worker_thread.start()

        except Exception as e:
            self.log.get_logger().error(f"Error during TaskProcessor initialization: {e}")

    def fetch_data_from_redis(self):
        """从 Redis 获取数据"""
        msg = self.redis.lpop(os.getenv('MSGLIST_KEY'))
        if not msg:
            return self.log.get_logger().info('Redis Queue is Empty.')

        return json.loads(msg)

    def process_queue(self):
        """后台线程方法：从队列中提取任务并处理, 用於處理失敗服務, 重新調用"""
        while True:
            task = self.task_queue.get()  # 阻塞直到获取任务
            if task is None:  # 停止信号
                continue

            try:
                # 检查任务时间戳
                enqueue_time = task.get('enqueue_time')  # 默认当前时间
                current_time = time.time()              
 
                if current_time < enqueue_time:
                    # 未超过等待时间，将任务重新放回队列
                    self.log.get_logger().info(f"Task waiting: {task}, current time: {current_time}, wait_time: {enqueue_time}")
                    if task['check'] != 1:
                        task['check'] = 1
                        self.task_queue.put(task)

                    continue
                else:
                    # 超过等待时间，处理任务
                    self.log.get_logger().info(f"redo the task {task}")
                    self.process_task(task)

            except Exception as e:
                self.log.get_logger().error(f"Error while redo the processing task in queue: {e}")
            finally:
                self.task_queue.task_done()

    def send_to_redis(self, resp_data, task_data, redis_key):
        resp = json.dumps(resp_data, ensure_ascii=False, indent=4)
        initial_length = self.redis.llen(f"{redis_key}_{task_data['namespace']}")
        self.redis.rpush(f"{redis_key}_{task_data['namespace']}", resp)
        new_length = self.redis.llen(f"{redis_key}_{task_data['namespace']}")

        # 通过长度差判断是否插入成功
        if new_length > initial_length:
            self.log.get_logger().info(f"{task_data['namespace']}_{task_data['ID']}, Send The Response To {redis_key} Redis. {resp}")
        else:
            self.log.get_logger().error(f"{task_data['namespace']}_{task_data['ID']}, Fail To Send The Response To {redis_key} Redis. {resp}")
        return

    @staticmethod
    def file2doc_task(task_data):
        # 1. 解构提取 namespace 和 id
        namespace = task_data.get('namespace')
        id = task_data.get('ID')
        
        if not namespace or not id:
            return {} ,"Both 'namespace' and 'id' must be provided in data."
        
        # 2. 组装 system.json 文件路径
        system_json_path = os.path.join(os.getcwd(), namespace, id)
        
        if not os.path.exists(system_json_path):
            return {}, f"{system_json_path} does not exist."

        try:
            isset, data_docs = utils.do_embedding(task_data)
            
            result = {
                'sn': task_data['sn'],
                'time': int(time.time()),
                'namespace': task_data['namespace'],
                'ID': task_data['ID'],
                'op': task_data['op'],
                'data': {}
            }

            if isset is True: # 表示成功
                result['data'] = {
                    'status': True,
                    'ds_code': task_data['data']['aics_ds_code'],
                    'data_docs': data_docs,
                    'err_msg': ''
                }

            else: # 表示失敗
                result['data'] = {
                    'status': False,
                    'ds_code': task_data['data']['aics_ds_code'],
                    'err_msg': 'Fail to tranfer the file to vector'
                }
            
            return result, ""

        except Exception as e:
            result = {
                 'sn': task_data['sn'],
                 'time': int(time.time()),
                 'namespace': task_data['namespace'],
                 'ID': task_data['ID'],
                 'op': task_data['op'],
                 'data':{
                     'status': False,
                     'ds_code': task_data['data']['aics_ds_code'],
                     'err_msg': 'Failed to transfer file to vector"'
                 }
             },
             
            # 如果是轉換失敗, 第二個參數, 將log紀錄回傳到外部
            return result, f"Failed to execute file2doc_task function in index.py: {e}"
        
    @staticmethod
    def vectordb_task(task_data):
        # 1. 解构提取 namespace 和 id
        namespace = task_data.get('namespace')
        id = task_data.get('ID')
        
        if not namespace or not id:
            raise ValueError("Both 'namespace' and 'id' must be provided in data.")
        
        # 2. 组装 system.json 文件路径
        system_json_path = os.path.join(os.getcwd(), namespace, id)
        
        if not os.path.exists(system_json_path):
            raise FileNotFoundError(f"{system_json_path} does not exist.")
        
        try:
            return utils.do_vectordb(task_data)
        except Exception as e:
            result = {
                'sn': task_data['sn'],
                'time': int(time.time()),
                'namespace': task_data['namespace'],
                'ID': task_data['ID'],
                'op': task_data['op'],
                'data':{
                        'status': False,
                        'code': task_data['data']['aics_vdb_code'],
                        'err_msg': 'Unknow vdb'
                    }
                }

            return result, f"Failed to execute vectordb_task with error: {e}"
        
    def ask_task(self, task_data):
        try:
            namespace, id = task_data['namespace'], task_data['ID']

            # 依照 namespace 和 id 构建 system.json 文件的路径
            json_file_path = os.path.join(namespace, id, 'system_setting.json').replace('\\', '/')
            if not os.path.exists(json_file_path):
                raise RuntimeError('The system_json path is not exist:', json_file_path)
            
            with open(json_file_path, 'r', encoding='utf-8') as f:
                system_data = json.load(f)
            
            # 找到 choosen_ai 為 1 的 key
            chosen_entry = None
            for key, value in system_data.items():
                if isinstance(value, dict) and value.get('choosen_ai') == 1:
                    chosen_entry = key
                    break

            if chosen_entry:
                chosen_value = system_data[chosen_entry]

                # 根据路径 settings/create/ 加载相应的 AI 模块
                module_path = f"settings.create.model.{chosen_entry}"
            
   
                if chosen_entry == 'Openai':
                    # 如果沒有assistant_id, 則會顯示None
                    assistant_id = chosen_value.get('assistant_id')
                    ai_module_class = self.dynamic_load_model(model_entry=chosen_entry, assistant_id=assistant_id, module_path=module_path, namespace=os.path.join(namespace, id))

                else:
                    #如果不是用openai, 則不會有assistnant_id
                    ai_module_class = self.dynamic_load_model(model_entry=chosen_entry, module_path=module_path, namespace=os.path.join(namespace, id))

                # 依照system_setting.json中的設定, 找出embed和當前的LLM, 給後續計算token數使用
                setting_params = {}
                embed_model_data = model_data = system_data.get('Embedding', {}).get('model', {})
                dynamic_key, embedding_model = next(iter(embed_model_data.items()))
                setting_params['embed'] = embedding_model
                setting_params['llm'] = system_data[chosen_entry]['model']

                respond, funcall, total_prompt_tokens, total_completion_tokens, total_embedding_tokens, total_tokens = ai_module_class.chat_with_ai(query=task_data['data']['text'], session=task_data['sid'], namespace_path=os.path.join(namespace, id), **setting_params)

                resp_data = {
                    'sid': task_data['sid'],
                    'sn': task_data['sn'],
                    'op': task_data['op'],
                    'data':{
                        'response': respond,
                        'funcall': funcall,
                        'prompt_token': total_prompt_tokens,
                        'completion_token': total_completion_tokens,
                        'embed_token': total_embedding_tokens,
                        'total_tokens': total_tokens,
                        'cnt': 1 # 統計AI詢問次數
                    },
                    'time': int(time.time()),
                    'namespace': task_data['namespace'],
                    'ID': task_data['ID'],
                    'extParams': task_data['extParams']
                }
                
                # 如果total_completion_tokens是False, 代表調用openai失敗, 放入到queue中等待下次執行, 而total_prompt_tokens是需等待的秒數
                if total_completion_tokens is False:
                    resp_data['data'].pop('cnt', None)
                    self.log.get_logger().warning(f"Task failed. Re-queueing task: {task_data}")
                    task_data['enqueue_time'] = time.time() + total_prompt_tokens # 更新任务时间戳
                    task_data['check'] = 0
                    self.task_queue.put(task_data)

                return self.send_to_redis(resp_data, task_data, os.getenv("MSGANSWER_KEY"))
            else:
                return self.log.get_logger().error("Error: No entry with 'choosen' equal to 1 found.")

        except Exception as e:
            return self.log.get_logger().error(f'There is something went worng in ask_task: {e}')

    def setting_task(self, task_data):
        """处理 setting 任务"""
        check = generate_template.check_path_exist(task_data)
        
        if not check:
            return self.log.get_logger().error("命名空間不存在path.json中")

        # 設定模型參數
        try:
            isset = utils.setting_tools(task_data)
            
            result = {
                'sn': task_data['sn'],
                'time':int(time.time()),
                'namespace': task_data['namespace'],
                'ID': task_data['ID'],
                'op': task_data['op'],
                'data': {}
            }

            if isset is True:
                result['data'] = {
                    'status': True,
                    'funcall': task_data['data']['aics_funcall_code'],
                    'err_msg': ''
                }  # 表示成功
            else:
                result['data'] = {
                    'status': False,
                    'funcall': task_data['data']['aics_funcall_code'],
                    'err_msg': 'Fail to set the funcall'
                }  # 表示失敗

            return self.send_to_redis(result, task_data, os.getenv("MSGNOTIFY_KEY"))
            
        except Exception as e:
            self.log.get_logger().error(f"模块中没有找到 setting_tools 方法: {e}")

            result = {
                'sn': task_data['sn'],
                'time': int(time.time()),
                'namespace': task_data['namespace'],
                'ID': task_data['ID'],
                'op': task_data['op'],
                'data':{
                        'status': False,
                        'funcall': task_data['data']['aics_funcall_code'],
                        'err_msg': 'Unknow funcall'
                    }
                }

            return self.send_to_redis(result, task_data, os.getenv("MSGNOTIFY_KEY"))

    def delete_task(self, task_data):
        """处理 delete 任务"""
        check = generate_template.check_path_exist(task_data)
        
        if not check:
            self.log.get_logger().error("No Namespace in path.json中")
            raise RuntimeError("命名空間不存在path.json中")

        # 設定模型參數
        try:
            isset = utils.delete_tools(task_data)

            result = {
                'sn': task_data['sn'],
                'time':int(time.time()),
                'namespace': task_data['namespace'],
                'ID': task_data['ID'],
                'op': task_data['op'],
                'data': {}
            }

            if isset is True:
                result['data'] = {
                    'status': True,
                    'funcall': task_data['data']['aics_funcall_code'],
                    'err_msg': ''
                }  # 表示成功
            else:
                result['data'] = {
                    'status': False,
                    'funcall': task_data['data']['aics_funcall_code'],
                    'err_msg': 'Fail to Delete Funcall'
                }  # 表示失敗

            return self.send_to_redis(result, task_data, os.getenv("MSGNOTIFY_KEY"))
            
        except Exception as e:
            self.log.get_logger().error(f"模块中没有找到 delete_tools 方法 {e}")
         
            result = {
                'sn': task_data['sn'],
                'time': int(time.time()),
                'namespace': task_data['namespace'],
                'ID': task_data['ID'],
                'op': task_data['op'],
                'data':{
                        'status': False,
                        'funcall': task_data['data']['aics_funcall_code'],
                        'err_msg': 'Unknow funcall'
                    }
                }

            return self.send_to_redis(result, task_data, os.getenv("MSGNOTIFY_KEY"))

    def delete_vdb(self, task_data):
        """处理 delete 任务"""
        check = generate_template.check_path_exist(task_data)

        if not check:
            self.log.get_logger().error("No Namespace in path.json中")
            raise RuntimeError("命名空間不存在path.json中")

        # 設定模型參數
        try:
            isset =  utils.delete_vdb(task_data)

            result = {
                'sn': task_data['sn'],
                'time':int(time.time()),
                'namespace': task_data['namespace'],
                'ID': task_data['ID'],
                'op': task_data['op'],
                'data': {}
            }

            if isset is True:
                result['data'] = {
                    'status': True,
                    'vdb': task_data['data']['aics_vdb_code'],
                    'err_msg': ''
                }  # 表示成功
            else:
                result['data'] = {
                    'status': False,
                    'vdb': task_data['data']['aics_vdb_code'],
                    'err_msg': 'Fail to Delete Funcall'
                }  # 表示失敗

            return self.send_to_redis(result, task_data, os.getenv("MSGNOTIFY_KEY"))

        except Exception as e:
            self.log.get_logger().error(f"模块中没有找到 delete_vdb 方法 {e}")
            
            result = {
                'sn': task_data['sn'],
                'time': int(time.time()),
                'namespace': task_data['namespace'],
                'ID': task_data['ID'],
                'op': task_data['op'],
                'data':{
                        'status': False,
                        'vdb': task_data['data']['aics_vdb_code'],
                        'err_msg': 'Unknow vdb'
                    }
                }

            return self.send_to_redis(result, task_data, os.getenv("MSGNOTIFY_KEY"))

    def initialize_task(self, task_data):
        """初始化文件與模型模板"""
        check = generate_template.check_path_exist(task_data)

        result = {
            'sn': task_data['sn'],
            'time': int(time.time()),
            'namespace': task_data['namespace'],
            'ID': task_data['ID'],
            'op': task_data['op'],
            'data': {}
        }

        # 如果namespae/ID路徑不存在, 則新建路徑與創建機器人
        if not check:
            init_status = generate_template.generate_path_and_template(task_data)            
            result['data']['status'] = init_status
            return self.send_to_redis(result, task_data, os.getenv("MSGNOTIFY_KEY"))
       
        # 如果存在則視為更新參數, 修改機器人
        update_status = generate_template.update_system_setting(task_data)
        result['data']['status'] = update_status
        return self.send_to_redis(result, task_data, os.getenv("MSGNOTIFY_KEY"))

    def dynamic_load_model(self, model_entry=None, assistant_id=None, module_path=None, namespace=None):
        if model_entry and module_path:
            module = importlib.import_module(module_path)
            ai_class = getattr(module, model_entry)()

            #如果模型是openai且assistant_id不為None
            if model_entry == 'Openai' and assistant_id:
                if not assistant_id and not namespace:
                    raise RuntimeError("No assistant_id or namespace for initialize tools, not provided when using Openai model")
                
                self.log.get_logger().info(f"Model entry is Openai with assistant_id: {assistant_id}")
                
                ai_class.fetch_model(assistant=assistant_id, path=namespace)
                return ai_class
            else:
                # 當不是使用Openai模型時，使用別的流程
                self.log.get_logger().info("Model entry is not Openai")
        else:
            self.log.get_logger().error("No model entry, chosen model value, module path provided, for chat with AI")
            raise RuntimeError("No model entry, chosen model value, module path provided, for chat with AI")

    def delete_datasource(self, task_data):
        """处理 delete datasource 任务"""
        check = generate_template.check_path_exist(task_data)

        if not check:
            self.log.get_logger().error("When doing delete datasource from vectordb, No Namespace in path.json中")
            raise RuntimeError("命名空間不存在path.json中")

        # 設定模型參數
        try:
            isset, new_data_docs = utils.delete_datasource(task_data)

            result = {
                'sn': task_data['sn'],
                'time': int(time.time()),
                'namespace': task_data['namespace'],
                'ID': task_data['ID'],
                'op': task_data['op'],
                'data': {}
            }

            if isset is True: # 表示成功
                result['data'] = {
                    'status': True,
                    'file_id': task_data['file_id'],
                    'ds_code': task_data['data']['aics_ds_code'],
                    'data_docs': new_data_docs,
                    'err_msg': ''
                }

            else: # 表示失敗
                result['data'] = {
                    'status': False,
                    'ds_code': task_data['data']['aics_ds_code'],
                    'err_msg': 'Fail to tranfer the file to vector'
                }

            return self.send_to_redis(result, task_data, os.getenv("MSGNOTIFY_KEY"))

        except Exception as e:
           self.log.get_logger().error(f"模块中没有找到 setting_tools 方法: {e}")

           result = {
               'sn': task_data['sn'],
               'time': int(time.time()),
               'namespace': task_data['namespace'],
               'ID': task_data['ID'],
               'op': task_data['op'],
               'data': {
                       'status': False,
                       'data_docs': task_data['data']['aics_ds_code'],
                       'err_msg': 'Unknow datasource'
                   }
               }

           return self.send_to_redis(result, task_data, os.getenv("MSGNOTIFY_KEY"))

    def process_task(self, task_data):
        try:
            if not task_data: 
                self.log.get_logger().info('No any task_data in process_task')
                return
            
            op = task_data.get('op')
            self.log.get_logger().info(f"Processing the op: {op} with {task_data.get('namespace')}/{task_data.get('ID')}")

            future = None

            if op == 'file2doc':
                future = self.process_pool.submit(self.file2doc_task, task_data)
            elif op == 'vectordb':
                future = self.process_pool.submit(self.vectordb_task, task_data)
            elif op == 'ask':
                self.thread_pool.submit(self.ask_task, task_data)
            elif op == 'initialize':
                self.thread_pool.submit(self.initialize_task, task_data)
            elif op == 'setting':
                self.thread_pool.submit(self.setting_task, task_data)
            elif op == 'del_funcall':
                self.thread_pool.submit(self.delete_task, task_data)
            elif op == 'del_vdb':
                self.thread_pool.submit(self.delete_vdb, task_data)
            elif op == 'del_datasource':
                self.thread_pool.submit(self.delete_datasource, task_data)
            else:
                self.log.get_logger().error(f"Unknown operation: {op}")
                return
            
            if future:
                # 使用 partial 绑定 task_data 到 callback, 讓進程池可以有多參數
                callback_with_data = partial(self.task_callback, task_data=task_data)
                future.add_done_callback(callback_with_data)

        except Exception as e:
            self.log.get_logger().error(f"There have something went wrong in process_task:: {e}")

    def task_callback(self, future, task_data):
        """多進程池回調任務"""
        try:
            # 获取任务的返回结果
            result, log_msg = future.result()

            if log_msg: # 如果轉換過程有錯誤, 第二個參數會顯示log錯誤
                return self.log.get_logger().error(log_msg)

            # 使用 task_data 调用 Redis 方法
            self.log.get_logger().info(f"Task completed in process_pool, callback sending result to Redis")
            return self.send_to_redis(resp_data=result, task_data=task_data, redis_key=os.getenv("MSGNOTIFY_KEY"))

        except Exception as e:
            return self.log.get_logger().error(f"Error in task_callback: {e}")

    def fetch_and_process(self):
        """从 Redis 获取数据并处理"""
        task_data = self.fetch_data_from_redis()
        return self.process_task(task_data)

# 启动调度器
scheduler = BackgroundScheduler()
scheduler.start()

if __name__ == '__main__':
    try:

        index_logger = logger.Logger(name='index_logger')
        processor = TaskProcessor(redis_cluster=my_redis.get_redis_client(), log=index_logger)
        scheduler.add_job(processor.fetch_and_process, 'interval', seconds=1, max_instances=100)
        scheduler.add_job(index_logger.move_old_logs, 'interval', days=1)
        
        index_logger.get_logger().info('Start The Scheduler.')

        # 让主线程保持运行
        while True:
            time.sleep(5)

    except Exception as e:
        index_logger.get_logger().error(f'There is something went wrong in index.py: {e}')
    except KeyboardInterrupt:
        index_logger.get_logger().info('Keyboard Interrupt The Scheduler.')
    finally:
        #关闭调度器
        scheduler.shutdown()
        index_logger.get_logger().info('ShutDown The Scheduler.')



# -------------------------- 測試用例 --------------------------

# task_a = {
#  'data':{
#     'model_vendor': 'Openai',
#     'model_val': 'gpt-3.5-turbo',
#     'assistant_name': 'AI銷售店長',
#     'assistant_meta_data': 'AI銷售店是商店小助手',
#     'system_prompt': '抱歉這個問題超出我所了解的範圍',
#     'system_description': '當問到商店之外的問題我想AI回覆上述回答',
#  },
#  'op': 'initialize',
#  'sn': '66bdc5d60c9de',
#  'ts': 1723712982,
#  'namespace': 'TestApplication',
#  'ID': '3'}

# task_b = {
#  'data':{
#     'model_vendor': 'Openai',
#     'model_val': 'gpt-4o',
#     'assistant_name': 'AI超能助手',
#     'assistant_meta_data': 'AI最強小幫手',
#     'system_prompt': '可能要問別人喔我不會!',
#     'system_description': '不知道回答的時候可以回復這個',
#  },
#  'op': 'initialize',
#  'sn': '66bdc5eead0da',
#  'ts': 1723713006,
#  'namespace': 'TestApplication',
#  'ID': '2'}

# #add setting task(後台執行新建的op), 也可以直接update
# task_c = {
#     "data":{
#         "aics_funcall_name":"get_apple", # 只能[a-zA-Z0-9_-]
#         "aics_vdb_code": ['juice_vdb']
#         "aics_funcall_intro":"蘋果汁, 果汁",
#         "aics_funcall_reply":"好喝的蘋果汁價錢是- (數字顯示)查詢結果",
#         "aics_funcall_stat":"2",
#         "aics_funcall_code": "apple_pie"
#     },
#     "op":"setting",
#     "sn":"66c2f4aaaec6a",
#     "ts":1724052650,
#     "namespace":"TestApplication",
#     "ID":"2"}

# task_e = {"op":"file2doc",
#           "data":{
#               'aics_ds_code': "apple_pie", # 未來要將此項設定在task_f中, 使其op單純切割文本
#               'aics_vdb_code': 'juice_vdb'
#               "file_paths":["\/www\/pang\/donate\/data\/public\/24\/08\/eeb18a730dcd3921.txt",
#                             "\/www\/pang\/donate\/data\/public\/24\/08\/abd541cf8ca92db5.txt",
#                             "\/www\/pang\/donate\/data\/public\/24\/08\/842f6c42094868d1.txt",
#                             "\/www\/pang\/donate\/data\/public\/24\/08\/bab6fce6d294d28a.txt",
#                             "\/www\/pang\/donate\/data\/public\/24\/08\/3c9702b588a45243.txt"]
#             },
#           "sn":"66cd3f3ca0ea8",
#           "ts":1724727100,
#           "namespace":"TestApplication",
#           "ID":"2"}

# task_f = {"op":"vectordb_task",
#           "data":{
#               'aics_funcall_code': "apple_pie", # 此項暫時先從file2doc過來, 後續如走op還是必須要帶此參數
#               "files_docs": [{
#                 "file_id": "1d3a2982-7a5c-4491-9d09-d2606fadd078",
#                 "file_split_content": [
#                     {
#                         "doc_id": "ee91ca36-7b4c-4ade-88a1-193fad33621a",
#                         "page_content": "紅燒牛肉麵 - NT$180\n鹽酥雞排 - NT$120\n鮭魚壽司套餐 - NT$350"
#                     },
#                     {
#                         "doc_id": "6e515b25-7d5b-4bd8-8dfd-7921f5b661f4",
#                         "page_content": "鮭魚壽司套餐 - NT$350\n泰式綠咖哩雞飯 - NT$220\n炸蝦天婦羅 - NT$150"
#                     },
#                     {
#                         "doc_id": "b7923767-11fc-4381-87f8-565b8e3568ed",
#                         "page_content": "炸蝦天婦羅 - NT$150\n焗烤海鮮義大利麵 - NT$280\n香烤松阪豬 - NT$320"
#                     },
#                     {
#                         "doc_id": "abac630e-f1d9-4574-9efc-460d94e50b5b",
#                         "page_content": "香烤松阪豬 - NT$320\n麻婆豆腐 - NT$160\n蜂蜜檸檬雞翅 - NT$180"
#                     },
#                     {
#                         "doc_id": "bebb6d4f-2d13-4684-85be-9e1fc0eb4860",
#                         "page_content": "蜂蜜檸檬雞翅 - NT$180\n巧克力熔岩蛋糕 - NT$120"
#                     }
#                 ]}]
#             },
#           "sn":"66cd3f3ca0ea8",
#           "ts":1724727100,
#           "namespace":"TestApplication",
#           "ID":"1"}

#  task_g  =   {  "op":"del_datasource",
#           "data":{
#              'aics_vdb_code': 'juice_vdb',
#                "ids": 
#             [
#                         "ee91ca36-7b4c-4ade-88a1-193fad33621a",
#                         "6e515b25-7d5b-4bd8-8dfd-7921f5b661f4",
#                         "b7923767-11fc-4381-87f8-565b8e3568ed",
#                         "abac630e-f1d9-4574-9efc-460d94e50b5b",
#                         "bebb6d4f-2d13-4684-85be-9e1fc0eb4860",
#             ]
#             },
#           "sn":"66cd3f3ca0ea8",
#           "ts":1724727100,
#           "namespace":"TestApplication",
#           "ID":"1"}


######   如果調用del_datasource或do_vectordb轉向量後, 會回傳整個document的格式, 回傳的代碼例如:
#{
#    "sn": "6811d5458e400",
#    "time": 1745999177,
#    "namespace": "aics",
#    "ID": "8327626",
#    "op": "file2doc",
#    "data": {
#        "status": true,
#        "ds_code": "1745999166606-8615",
#        "data_docs": [
#            {
#                "doc_id": "ed545ca9-36d4-49d9-9648-fd0a9018501c",
#                "page_content": "品名: 招牌熱炒\n價格 (新台幣): \n介紹: ",
#                "metadata": {}
#            },
#            {
#                "doc_id": "fa845cfd-42f3-4b78-85ec-1dccabd05189",
#                "page_content": "品名: 蒜泥白肉\n價格 (新台幣): 180\n介紹: Q彈豬五花搭配濃郁蒜蓉醬，經典下飯！",
#                "metadata": {}
#            },
#            {
#                "doc_id": "36481b05-58c0-4c17-b4a0-5b79da94ab84",
#                "page_content": "品名: 客家小炒\n價格 (新台幣): 220\n介紹: 魷魚、豆干、肉絲、芹菜的完美結合，鹹香夠味，越嚼越香！",
#                "metadata": {}
#            },
#            {
#                "doc_id": "8110499b-bd8e-4899-a8e2-b33ac960314d",
#                "page_content": "品名: 三杯雞\n價格 (新台幣): 280\n介紹: 麻油、醬油、米酒的香氣撲鼻而來，雞肉軟嫩入味，九層塔更添風味！",
#                "metadata": {}
#            },
#          ...
#}


#task_g = {'data': {'text': '蘋果汁多少錢?'},'op': 'ask', 'sid': '8cuwtt7', 'sn': '66bdc5d60c9de','ts': 1723712982, 'namespace': 'TestApplication', 'ID': '2'}

# if __name__ == '__main__':
#     try:
#         TaskProcessor().process_task(task_e)
#     except Exception as e:
#         print(f"Error in main execution: {e}")
