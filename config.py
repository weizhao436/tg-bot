import sqlite3
import os
from config import DB_PATH

# 基本配置
SECRET_KEY = 'your-secret-key-change-this'  # 用于 Flask 会话
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'password'  # 建议使用更强的密码并加密存储

# 数据库配置
DB_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(DB_DIR, exist_ok=True)  # 确保数据目录存在
DB_PATH = os.path.join(DB_DIR, 'bot_data.db')

# 机器人配置
BOT_TOKEN = "7988564533:AAFcVl6nUY-jRYhfpBORvRpC_An0WLSa4CY" 

# Redis配置
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_PASSWORD = None  # 如果有密码则设置
REDIS_CHANNEL = 'button_updates'  # Redis发布/订阅通道

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def setup_database():
    # 从admin_web.py移动到这里的数据库初始化代码
    conn = get_db_connection()
    # ...创建表等操作...
    conn.close()

def get_all_buttons():
    conn = get_db_connection()
    buttons = conn.execute("SELECT * FROM buttons ORDER BY row, column").fetchall()
    conn.close()
    return buttons

# ...其他数据库操作函数...