# '''
# Author: pang-lee
# Date: 2024-07-11 09:47:51
# LastEditTime: 2024-07-11 09:47:51
# LastEditors: LAPTOP-22MC5HRI
# Description: redis settings
# FilePath: \openai\template\redis.py
# '''
from rediscluster import RedisCluster
from redis import Redis
import os
from .logger import Logger
redis_logger = Logger(name='redis_logger')
from dotenv import load_dotenv
load_dotenv()

def get_redis_client():
    if os.getenv("DOCKER_HOST"): # 單機 Redis 模式（Docker）
        host = os.getenv("DOCKER_HOST", "redis")
        port = int(os.getenv("DOCKER_PORT", "6379"))
        redis_logger.get_logger().info(f"Redis docker host: {host}:{port}")
        return Redis(
            host=host,
            port=port,
            decode_responses=True
        )

    else: # 从环境变量中获取 Redis Cluster 节点信息
        redis_nodes = []
        i = 1

        while True:
            host = os.getenv(f"REDIS_CLUSTER_HOST_{i}")
            port = os.getenv(f"REDIS_CLUSTER_PORT_{i}")

            if host and port:
                redis_nodes.append({"host": host, "port": port})
                i += 1
            else:
                break
            
        redis_logger.get_logger().info(f"Redis Cluster Nodes: {redis_nodes}")
        return RedisCluster(startup_nodes=redis_nodes, decode_responses=True, skip_full_coverage_check=True)


