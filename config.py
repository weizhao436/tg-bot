#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Bot 配置文件
包含机器人运行所需的所有配置参数
"""
import os
import logging
import sys

# ======== 基本配置 ========
# 从原始config.py保留原始的BOT_TOKEN值
BOT_TOKEN = "7988564533:AAFcVl6nUY-jRYhfpBORvRpC_An0WLSa4CY"

# ======== 目录配置 ========
# 基本目录路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 数据目录
DATA_DIR = os.path.join(BASE_DIR, "data")
# 日志目录
LOG_DIR = os.path.join(BASE_DIR, "logs")
# 锁文件路径
LOCK_FILE = os.path.join(BASE_DIR, "bot.lock")

# ======== 数据库配置 ========
# 数据库文件路径
DB_PATH = os.path.join(DATA_DIR, "bot_data.db")

# ======== 日志配置 ========
# 日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = logging.INFO
# 日志文件最大大小 (字节)
LOG_MAX_SIZE = 10 * 1024 * 1024  # 10 MB
# 保留的日志文件数量
LOG_BACKUP_COUNT = 5

# ======== Web管理面板配置 ========
# 管理面板端口范围
ADMIN_PORT_START = 5001
ADMIN_PORT_END = 5100
# 管理员用户名和密码
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "secure_password_here"  # 建议修改为更安全的密码

# ======== API配置 ========
# API 基础URL
API_URL = "https://api.example.com"  # 替换为实际API URL

# ======== 功能配置 ========
# 更新检查间隔 (秒)
UPDATE_CHECK_INTERVAL = 300  # 5分钟
# 自动重启间隔 (秒), 0表示禁用自动重启
AUTO_RESTART_INTERVAL = 86400  # 24小时

# ======== 创建必要的目录 ========
# 这个函数会在导入配置时自动创建必要的目录
def ensure_directories():
    """确保所有必要的目录都存在"""
    directories = [BASE_DIR, DATA_DIR, LOG_DIR]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        # 尝试设置权限
        try:
            os.chmod(directory, 0o755)
        except:
            pass  # 如果没有权限，忽略错误

# 自动创建目录
ensure_directories()

# ======== 按钮配置 ========
# 按钮配置
BUTTON_CHECK_INTERVAL = 60  # 按钮配置检查间隔（秒）
BUTTONS_CACHE_TTL = 300  # 按钮缓存有效期（秒）

# ======== 管理面板配置 ========
# 管理面板端口范围
ADMIN_PORT = 5000  # 管理面板端口
# 管理员用户名和密码
SECRET_KEY = "your_secret_key_here"  # Flask应用密钥，用于session

# ======== API配置 ========
# API 基础URL
API_BASE_URL = "http://localhost:5000/api"

# 确保目录存在
def ensure_dirs():
    """确保必要的目录存在，并设置正确的权限"""
    for directory in [DATA_DIR, LOG_DIR]:
        if not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
                # 设置目录权限
                os.chmod(directory, 0o755)
            except Exception as e:
                print(f"无法创建目录 {directory}: {e}")
                sys.exit(1)

# 自动创建必要的目录
ensure_dirs() 