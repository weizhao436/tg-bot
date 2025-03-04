#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Bot - 主程序
"""
import os
import sys
import json
import time
import fcntl
import logging
import sqlite3
import socket
import threading
import signal
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler

# 尝试导入Telegram相关库
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, Defaults
    from telegram.error import TelegramError
except ImportError:
    print("错误: 未安装python-telegram-bot库。请运行: pip install python-telegram-bot")
    sys.exit(1)

# 尝试导入配置
try:
    from config import (BOT_TOKEN, BASE_DIR, DATA_DIR, LOG_DIR, 
                        LOCK_FILE, DB_PATH, LOG_LEVEL, LOG_MAX_SIZE, 
                        LOG_BACKUP_COUNT, ADMIN_PORT_START, ADMIN_PORT_END,
                        API_URL, UPDATE_CHECK_INTERVAL)
    print("✅ 已成功导入配置")
except ImportError:
    print("错误: 未找到config.py文件")
    sys.exit(1)
except Exception as e:
    print(f"导入配置时出错: {e}")
    sys.exit(1)

# ======== 设置日志 ========
# 确保日志目录存在
os.makedirs(LOG_DIR, exist_ok=True)

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, LOG_LEVEL)
)

# 添加文件处理器
log_file = os.path.join(LOG_DIR, 'bot.log')
file_handler = RotatingFileHandler(
    log_file,
    maxBytes=LOG_MAX_SIZE,
    backupCount=LOG_BACKUP_COUNT
)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# 获取根日志记录器并添加文件处理器
root_logger = logging.getLogger()
root_logger.addHandler(file_handler)

# 创建日志记录器
logger = logging.getLogger(__name__)
logger.info(f"启动Telegram Bot - 日志文件: {log_file}")

# ======== 确保数据目录存在 ========
os.makedirs(DATA_DIR, exist_ok=True)
logger.info(f"数据目录: {DATA_DIR}")

# ======== 全局变量 ========
# 按钮更新标志
BUTTON_UPDATE_FLAG = False

# ======== 数据库函数 ========
def setup_database():
    """设置数据库"""
    logger.info(f"设置数据库: {DB_PATH}")
    
    # 记录当前环境信息
    logger.info(f"当前用户: {os.getuid()}:{os.getgid()}")
    logger.info(f"数据库路径: {os.path.abspath(DB_PATH)}")
    
    # 确保数据目录存在并有正确权限
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        try:
            os.makedirs(db_dir, exist_ok=True)
            os.chmod(db_dir, 0o755)  # 设置目录权限
            logger.info(f"已创建数据库目录: {db_dir}")
        except Exception as e:
            logger.error(f"创建数据库目录失败: {e}")
            try:
                # 尝试以更宽松的权限创建
                os.system(f"mkdir -p {db_dir}")
                os.system(f"chmod 777 {db_dir}")
                logger.info("使用系统命令创建了数据库目录")
            except Exception as e2:
                logger.error(f"使用系统命令创建目录也失败: {e2}")
                raise RuntimeError(f"无法创建数据库目录: {e2}")
    
    # 记录目录权限
    try:
        dir_stat = os.stat(db_dir)
        logger.info(f"目录权限: {oct(dir_stat.st_mode)}, 所有者: {dir_stat.st_uid}:{dir_stat.st_gid}")
        logger.info(f"当前用户对目录的写权限: {os.access(db_dir, os.W_OK)}")
    except Exception as e:
        logger.error(f"获取目录信息失败: {e}")
    
    # 连接数据库并创建表
    try:
        # 如果数据库文件不存在，尝试创建空文件
        if not os.path.exists(DB_PATH):
            try:
                with open(DB_PATH, 'w') as f:
                    pass
                os.chmod(DB_PATH, 0o644)  # 设置文件权限
                logger.info(f"已创建空数据库文件: {DB_PATH}")
            except Exception as e:
                logger.error(f"创建数据库文件失败: {e}")
                # 尝试使用系统命令
                os.system(f"touch {DB_PATH}")
                os.system(f"chmod 666 {DB_PATH}")
                logger.info("使用系统命令创建了数据库文件")
        
        # 记录文件权限
        if os.path.exists(DB_PATH):
            file_stat = os.stat(DB_PATH)
            logger.info(f"文件权限: {oct(file_stat.st_mode)}, 所有者: {file_stat.st_uid}:{file_stat.st_gid}")
            logger.info(f"当前用户对文件的写权限: {os.access(DB_PATH, os.W_OK)}")
        
        # 尝试连接数据库
        conn = sqlite3.connect(DB_PATH, timeout=30)  # 增加超时时间
        cursor = conn.cursor()
        logger.info("成功连接到数据库")
        
        # 创建用户表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            language_code TEXT,
            last_activity TEXT,
            join_date TEXT
        )
        ''')
        
        # 创建功能使用统计表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS usage_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            feature TEXT,
            use_time TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
        
        # 创建定制按钮表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS custom_buttons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            button_text TEXT,
            button_url TEXT,
            created_at TEXT
        )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("数据库表创建/更新成功")
        return True
        
    except sqlite3.Error as e:
        logger.error(f"数据库错误: {e}")
        # 尝试异常恢复
        try:
            backup_path = f"{DB_PATH}.bak.{int(time.time())}"
            if os.path.exists(DB_PATH):
                logger.info(f"备份当前数据库到 {backup_path}")
                os.rename(DB_PATH, backup_path)
            logger.info("创建新的数据库文件")
            with open(DB_PATH, 'w') as f:
                pass
            os.chmod(DB_PATH, 0o644)
            logger.info("已创建新的数据库文件，请重新启动机器人")
        except Exception as recovery_e:
            logger.error(f"恢复过程中出错: {recovery_e}")
        return False
    except Exception as e:
        logger.error(f"设置数据库时出现未知错误: {e}")
        return False

def save_user(user):
    """保存用户信息到数据库"""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        cursor = conn.cursor()
        
        # 检查用户是否已存在
        cursor.execute("SELECT id FROM users WHERE id = ?", (user.id,))
        if cursor.fetchone():
            # 用户已存在，更新信息
            cursor.execute("""
            UPDATE users SET
                username = ?,
                first_name = ?,
                last_name = ?,
                language_code = ?,
                last_activity = ?
            WHERE id = ?
            """, (
                user.username,
                user.first_name,
                user.last_name,
                user.language_code,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                user.id
            ))
        else:
            # 用户不存在，创建新记录
            cursor.execute("""
            INSERT INTO users (id, username, first_name, last_name, language_code, last_activity, join_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user.id,
                user.username,
                user.first_name,
                user.last_name,
                user.language_code,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
        
        conn.commit()
        conn.close()
        logger.info(f"已保存/更新用户 {user.id} ({user.username}) 的信息")
        return True
    except sqlite3.Error as e:
        logger.error(f"保存用户时出现数据库错误: {e}")
        return False
    except Exception as e:
        logger.error(f"保存用户时出现未知错误: {e}")
        return False

def get_user_by_id(user_id):
    """根据ID获取用户信息"""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user_data = cursor.fetchone()
        
        conn.close()
        
        if user_data:
            # 创建用户字典
            user = {
                'id': user_data[0],
                'username': user_data[1],
                'first_name': user_data[2],
                'last_name': user_data[3],
                'language_code': user_data[4],
                'last_activity': user_data[5],
                'join_date': user_data[6]
            }
            return user
        else:
            return None
    except sqlite3.Error as e:
        logger.error(f"获取用户时出现数据库错误: {e}")
        return None
    except Exception as e:
        logger.error(f"获取用户时出现未知错误: {e}")
        return None

def update_user_activity(user_id):
    """更新用户活动时间"""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        cursor = conn.cursor()
        
        cursor.execute("""
        UPDATE users SET last_activity = ? WHERE id = ?
        """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_id))
        
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        logger.error(f"更新用户活动时出现数据库错误: {e}")
        return False
    except Exception as e:
        logger.error(f"更新用户活动时出现未知错误: {e}")
        return False

# ======== 工具函数 ========
def check_button_updates():
    """检查按钮更新"""
    global BUTTON_UPDATE_FLAG
    try:
        # 检查按钮是否需要更新的逻辑
        # 这里是示例代码，请根据实际需求修改
        logger.info("检查按钮更新")
        BUTTON_UPDATE_FLAG = True
        return True
    except Exception as e:
        logger.error(f"检查按钮更新时出错: {str(e)}")
        return False

def get_main_keyboard():
    """获取主键盘"""
    try:
        keyboard = [
            ["🔍 搜索", "🆕 最新活动"],
            ["🏠 首页", "👤 个人中心"],
            ["📞 联系我们", "📸 照片"],
            ["🎥 视频", "🎞 图库"]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    except Exception as e:
        logger.error(f"获取主键盘时出错: {str(e)}")
        # 返回一个基本键盘作为后备
        return ReplyKeyboardMarkup([["🏠 首页"]], resize_keyboard=True)

def find_available_port(start_port, end_port):
    """查找可用端口"""
    for port in range(start_port, end_port+1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', port)) != 0:
                logger.info(f"找到可用端口: {port}")
                return port
    logger.error(f"在范围 {start_port}-{end_port} 内没有可用端口")
    return start_port  # 如果没有找到，返回起始端口

def make_request(url):
    """发送HTTP请求并返回响应文本和状态码"""
    try:
        import requests
        response = requests.get(url, timeout=30)
        return response.text, response.status_code
    except Exception as e:
        logger.error(f"发送请求时出错: {e}")
        return str(e), 500

# ======== 示例功能 ========
def get_activities():
    """获取活动列表"""
    # 示例活动数据，实际应用中应从数据库或API获取
    activities = [
        {
            'id': '1',
            'title': '社区清洁日',
            'date': '2023-06-15',
            'location': '中央公园',
            'description': '一起来参与社区清洁活动，让我们的环境更美好！我们将提供清洁工具和饮料。'
        },
        {
            'id': '2',
            'title': '编程工作坊',
            'date': '2023-06-20',
            'location': '科技中心',
            'description': '学习基础Python编程，适合初学者。请自带笔记本电脑。'
        },
        {
            'id': '3',
            'title': '艺术展览',
            'date': '2023-06-25',
            'location': '市立美术馆',
            'description': '当地艺术家作品展示，包括绘画、雕塑和摄影作品。'
        }
    ]
    return activities

def get_activity_by_id(activity_id):
    """根据ID获取活动详情"""
    activities = get_activities()
    for activity in activities:
        if activity['id'] == activity_id:
            return activity
    return None

def get_response_for_trigger(trigger_text):
    """根据触发文本获取响应"""
    try:
        # 触发词和响应的映射
        triggers = {
            "你好": "👋 你好！有什么我可以帮助你的吗？",
            "早上好": "🌞 早上好！祝你有一个美好的一天！",
            "下午好": "🌤 下午好！今天过得如何？",
            "晚上好": "🌙 晚上好！今天过得愉快吗？",
            "谢谢": "🙏 不客气！随时为你服务。",
            "再见": "👋 再见！期待下次再与你聊天。"
        }
        
        # 查找匹配的触发词
        for trigger, response in triggers.items():
            if trigger in trigger_text:
                logger.info(f"找到触发词 '{trigger}'，返回相应响应")
                return response
        
        # 如果没有匹配的触发词
        return None
    except Exception as e:
        logger.error(f"获取触发响应时出错: {e}")
        return None

# ======== 命令处理程序 ========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理/start命令"""
    try:
        user = update.effective_user
        logger.info(f"用户 {user.id} ({user.username}) 发送了 /start 命令")
        
        # 保存用户信息
        save_user(user)
        
        # 准备欢迎消息
        welcome_message = f"👋 你好，{user.first_name}！\n\n"
        welcome_message += "欢迎使用我们的机器人。这是一个功能强大的机器人，可以帮助你:\n"
        welcome_message += "• 🔍 搜索信息\n"
        welcome_message += "• 📰 查看最新活动\n"
        welcome_message += "• 📸 分享照片和视频\n"
        welcome_message += "• 🎮 玩有趣的小游戏\n\n"
        welcome_message += "使用底部的按钮菜单开始探索，或者输入 /help 查看更多命令。"
        
        # 发送欢迎消息并显示主键盘
        await update.message.reply_html(
            welcome_message,
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        logger.error(f"处理 /start 命令时出错: {e}")
        await update.message.reply_text("抱歉，启动过程中出现了一个错误。请稍后再试。")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理/help命令"""
    try:
        user = update.effective_user
        logger.info(f"用户 {user.id} ({user.username}) 发送了 /help 命令")
        
        # 记录用户活动
        update_user_activity(user.id)
        
        help_text = "📚 <b>可用命令列表</b>\n\n"
        help_text += "/start - 启动机器人并显示欢迎信息\n"
        help_text += "/help - 显示此帮助信息\n"
        help_text += "/search - 搜索功能\n"
        help_text += "/latest - 查看最新活动\n"
        help_text += "/refresh - 刷新机器人状态\n\n"
        help_text += "你还可以使用底部的键盘菜单访问更多功能。"
        
        await update.message.reply_html(help_text)
    except Exception as e:
        logger.error(f"处理 /help 命令时出错: {e}")
        await update.message.reply_text("抱歉，获取帮助信息时出现了一个错误。请稍后再试。")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理搜索功能"""
    try:
        user = update.effective_user
        logger.info(f"用户 {user.id} ({user.username}) 使用了搜索功能")
        
        # 记录用户活动
        update_user_activity(user.id)
        
        await update.message.reply_text(
            "🔍 请输入你想搜索的内容:",
            reply_markup=ReplyKeyboardRemove()
        )
        
        # 在用户上下文中设置状态
        context.user_data['state'] = 'waiting_for_search_query'
    except Exception as e:
        logger.error(f"处理搜索时出错: {e}")
        await update.message.reply_text("抱歉，搜索功能暂时不可用。请稍后再试。")

async def latest_activities(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示最新活动"""
    try:
        user = update.effective_user
        logger.info(f"用户 {user.id} ({user.username}) 请求了最新活动")
        
        # 记录用户活动
        update_user_activity(user.id)
        
        # 获取活动数据
        activities = get_activities()
        
        if not activities:
            await update.message.reply_text("目前没有可用的活动信息。请稍后再试。", reply_markup=get_main_keyboard())
            return
        
        # 创建活动列表消息
        message = "🆕 <b>最新活动</b>\n\n"
        
        keyboard = []
        
        for activity in activities[:5]:  # 只显示前5个活动
            message += f"<b>{activity['title']}</b>\n"
            message += f"日期: {activity['date']}\n"
            message += f"简介: {activity['description'][:100]}...\n\n"
            
            # 为每个活动添加一个查看详情按钮
            keyboard.append([
                InlineKeyboardButton(f"查看详情: {activity['title'][:20]}", callback_data=f"activity_{activity['id']}")
            ])
        
        # 添加一个查看全部按钮
        keyboard.append([InlineKeyboardButton("查看全部活动", callback_data="view_all_activities")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_html(message, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"显示最新活动时出错: {e}")
        await update.message.reply_text("抱歉，获取最新活动时出现了一个错误。请稍后再试。", reply_markup=get_main_keyboard())

async def activity_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示活动详情"""
    try:
        query = update.callback_query
        await query.answer()
        
        # 从回调数据中获取活动ID
        activity_id = query.data.split('_')[1]
        
        user = query.from_user
        logger.info(f"用户 {user.id} ({user.username}) 查看了活动 {activity_id} 的详情")
        
        # 记录用户活动
        update_user_activity(user.id)
        
        # 获取活动详情
        activity = get_activity_by_id(activity_id)
        
        if not activity:
            await query.edit_message_text("抱歉，找不到该活动的详情。它可能已被删除。")
            return
        
        # 创建详情消息
        message = f"🎯 <b>{activity['title']}</b>\n\n"
        message += f"📅 日期: {activity['date']}\n"
        message += f"📍 地点: {activity['location']}\n\n"
        message += f"📝 详情:\n{activity['description']}\n\n"
        
        # 返回按钮
        keyboard = [[InlineKeyboardButton("返回活动列表", callback_data="view_all_activities")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')
    except Exception as e:
        logger.error(f"显示活动详情时出错: {e}")
        try:
            await query.edit_message_text("抱歉，获取活动详情时出现了一个错误。请稍后再试。")
        except:
            pass

async def refresh_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """刷新机器人状态"""
    try:
        user = update.effective_user
        logger.info(f"用户 {user.id} ({user.username}) 发送了 /refresh 命令")
        
        # 可以在这里添加任何需要刷新的状态或数据
        global BUTTON_UPDATE_FLAG
        BUTTON_UPDATE_FLAG = True
        
        await update.message.reply_text("✅ 机器人状态已刷新！", reply_markup=get_main_keyboard())
    except Exception as e:
        logger.error(f"刷新机器人状态时出错: {e}")
        await update.message.reply_text("抱歉，刷新操作失败。请稍后再试。")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理错误"""
    logger.error(f"更新 {update} 导致错误 {context.error}")
    try:
        if update and hasattr(update, 'effective_message'):
            await update.effective_message.reply_text("抱歉，发生了一个错误。我们的技术团队已收到通知。")
    except:
        pass

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理普通消息"""
    try:
        user = update.effective_user
        message_text = update.message.text
        logger.info(f"用户 {user.id} ({user.username}) 发送了消息: {message_text}")
        
        # 记录用户活动
        update_user_activity(user.id)
        
        # 检查用户状态
        if 'state' in context.user_data:
            state = context.user_data['state']
            
            # 处理搜索查询
            if state == 'waiting_for_search_query':
                logger.info(f"处理搜索查询: {message_text}")
                await update.message.reply_text(
                    f"🔍 正在搜索: {message_text}\n\n"
                    "搜索结果将很快显示...",
                    reply_markup=get_main_keyboard()
                )
                # 清除状态
                del context.user_data['state']
                return
        
        # 检查是否有匹配的触发响应
        response = get_response_for_trigger(message_text)
        if response:
            await update.message.reply_text(response, reply_markup=get_main_keyboard())
            return
        
        # 如果是主键盘按钮
        if message_text == "🔍 搜索":
            await search(update, context)
        elif message_text == "🆕 最新活动":
            await latest_activities(update, context)
        else:
            # 默认响应
            await update.message.reply_text(
                "👋 我收到了你的消息。你可以使用键盘菜单选择功能，或者输入 /help 查看可用命令。",
                reply_markup=get_main_keyboard()
            )
    except Exception as e:
        logger.error(f"处理消息时出错: {e}")
        try:
            await update.message.reply_text("抱歉，处理你的消息时出现了一个错误。请稍后再试。")
        except:
            pass

# ======== 主函数 ========
def main():
    """主函数"""
    # 创建锁文件并检查是否已经有实例在运行
    try:
        # 确保锁文件目录存在
        lock_dir = os.path.dirname(LOCK_FILE)
        os.makedirs(lock_dir, exist_ok=True)
        
        # 尝试创建和锁定文件
        lock_file = open(LOCK_FILE, "w")
        try:
            # 尝试获取独占锁
            fcntl.lockf(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            logger.info("成功获取锁，确保只有一个实例在运行")
        except IOError:
            logger.error("另一个实例已在运行。退出。")
            sys.exit(1)
    except Exception as e:
        logger.error(f"创建锁文件时出错: {e}")
        # 继续执行，即使锁定失败
    
    logger.info("初始化机器人...")
    
    # 获取bot token
    token = None
    
    # 1. 尝试使用配置中的BOT_TOKEN
    token = BOT_TOKEN
    if token:
        logger.info("使用配置文件中的BOT_TOKEN")
    
    # 2. 尝试从环境变量获取
    if not token:
        token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if token:
            logger.info("使用环境变量TELEGRAM_BOT_TOKEN")
    
    # 3. 尝试从config.json获取
    if not token:
        try:
            config_path = os.path.join(os.path.dirname(__file__), 'config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    token = config.get('token') or config.get('telegram_bot_token')
                    if token:
                        logger.info("使用config.json中的token")
        except Exception as e:
            logger.warning(f"从config.json读取token时出错: {e}")
    
    # 检查是否有有效的token
    if not token:
        logger.error("未找到有效的Telegram Bot Token")
        logger.error("请在config.py中设置BOT_TOKEN，或设置环境变量TELEGRAM_BOT_TOKEN，或在config.json中配置")
        sys.exit(1)
    
    # 设置数据库
    try:
        db_setup_result = setup_database()
        if db_setup_result:
            logger.info("数据库设置成功")
        else:
            logger.warning("数据库设置不完整，某些功能可能不可用")
    except Exception as e:
        logger.error(f"数据库设置失败: {e}")
        logger.warning("继续运行，但某些功能可能不可用")
    
    # 检查机器人 token 是否有效
    try:
        response_text, status_code = make_request(f"https://api.telegram.org/bot{token}/getMe")
        if status_code != 200:
            logger.error(f"机器人 token 无效: {response_text}")
            sys.exit(1)
        
        bot_info = json.loads(response_text)["result"]
        logger.info(f"机器人信息: {bot_info['first_name']} (@{bot_info['username']})")
    except Exception as e:
        logger.error(f"检查机器人 token 时出错: {e}")
        sys.exit(1)
    
    # 删除任何现有的 webhook
    try:
        response_text, _ = make_request(f"https://api.telegram.org/bot{token}/deleteWebhook")
        logger.info(f"删除 webhook 结果: {response_text}")
    except Exception as e:
        logger.error(f"删除 webhook 时出错: {e}")
    
    try:
        # 创建 Application
        defaults = Defaults(parse_mode='HTML')
        application = Application.builder().token(token).defaults(defaults).build()
        logger.info("成功创建 Application 实例")
        
        # 添加命令处理程序
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("search", search))
        application.add_handler(CommandHandler("latest", latest_activities))
        application.add_handler(CommandHandler("refresh", refresh_command))
        
        # 添加回调查询处理程序
        application.add_handler(CallbackQueryHandler(activity_details, pattern="^activity_"))
        
        # 添加消息处理程序
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # 添加错误处理程序
        application.add_error_handler(error_handler)
        
        # 启动机器人
        logger.info("机器人已启动并正在轮询更新...")
        application.run_polling()
    except KeyboardInterrupt:
        logger.info("收到键盘中断，正在退出...")
    except Exception as e:
        logger.critical(f"启动机器人时出错: {e}", exc_info=True)
    finally:
        # 清理锁文件
        try:
            if os.path.exists(LOCK_FILE):
                os.remove(LOCK_FILE)
                logger.info("已移除锁文件")
        except:
            pass

# ======== 启动程序 ========
if __name__ == "__main__":
    main() 