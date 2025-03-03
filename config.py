import os

# 基本配置
SECRET_KEY = 'your-secret-key-change-this'  # 用于 Flask 会话
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'password'  # 建议使用更强的密码并加密存储

# 数据库配置
DB_PATH = os.path.join(os.path.dirname(__file__), 'bot_data.db')

# 机器人配置
BOT_TOKEN = "7988564533:AAFcVl6nUY-jRYhfpBORvRpC_An0WLSa4CY" 