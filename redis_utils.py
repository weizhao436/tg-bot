import json
import logging
import time
import redis
from redis import ConnectionPool
from config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD, REDIS_CHANNEL

logger = logging.getLogger(__name__)

# 创建Redis连接池
REDIS_POOL = None
try:
    REDIS_POOL = ConnectionPool(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD,
        socket_timeout=5,
        socket_connect_timeout=5
    )
    logger.info("Redis连接池初始化成功")
except Exception as e:
    logger.error(f"Redis连接池初始化失败: {e}")

def get_redis_client():
    """获取Redis客户端实例"""
    if not REDIS_POOL:
        logger.warning("Redis连接池未初始化，返回None")
        return None
        
    try:
        client = redis.Redis(connection_pool=REDIS_POOL)
        # 测试连接
        client.ping()
        return client
    except redis.RedisError as e:
        logger.error(f"Redis客户端初始化失败: {e}")
        return None

def is_redis_available():
    """检查Redis是否可用"""
    client = get_redis_client()
    if not client:
        return False
        
    try:
        return client.ping()
    except:
        return False

def publish_update(data, channel=REDIS_CHANNEL):
    """发布更新消息到Redis频道"""
    client = get_redis_client()
    if not client:
        logger.warning("Redis客户端未初始化，无法发布更新")
        return False
        
    try:
        if isinstance(data, dict):
            data = json.dumps(data)
        client.publish(channel, data)
        return True
    except Exception as e:
        logger.error(f"发布Redis更新失败: {e}")
        return False

def start_subscriber(callback, channel=REDIS_CHANNEL):
    """启动Redis订阅监听
    
    Args:
        callback: 收到消息时的回调函数，接收一个参数(message)
        channel: 要订阅的频道名称
    """
    client = get_redis_client()
    if not client:
        logger.error("Redis客户端未初始化，无法启动订阅")
        return False
        
    pubsub = client.pubsub()
    pubsub.subscribe(channel)
    
    logger.info(f"开始监听Redis频道: {channel}")
    
    for message in pubsub.listen():
        if message['type'] == 'message':
            try:
                # 尝试解析JSON
                data = message['data'].decode('utf-8')
                try:
                    data = json.loads(data)
                except:
                    pass  # 如果不是JSON，保持原样
                    
                # 调用回调处理消息
                callback(data)
                
            except Exception as e:
                logger.error(f"处理Redis消息时出错: {e}")

def set_cache(key, value, ttl=300):
    """设置带过期时间的缓存
    
    Args:
        key: 缓存键名
        value: 缓存值(将自动序列化)
        ttl: 过期时间(秒)
    """
    client = get_redis_client()
    if not client:
        return False
        
    try:
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        return client.setex(key, ttl, value)
    except Exception as e:
        logger.error(f"设置缓存失败: {e}")
        return False
        
def get_cache(key):
    """获取缓存值
    
    Args:
        key: 缓存键名
    
    Returns:
        缓存的值，如果是JSON将自动反序列化；如果不存在或错误，返回None
    """
    client = get_redis_client()
    if not client:
        return None
        
    try:
        value = client.get(key)
        if value is None:
            return None
            
        # 尝试JSON反序列化
        try:
            return json.loads(value)
        except:
            return value.decode('utf-8')
    except Exception as e:
        logger.error(f"获取缓存失败: {e}")
        return None

def delete_cache(key):
    """删除缓存
    
    Args:
        key: 缓存键名
    """
    client = get_redis_client()
    if not client:
        return False
        
    try:
        return client.delete(key) > 0
    except Exception as e:
        logger.error(f"删除缓存失败: {e}")
        return False 