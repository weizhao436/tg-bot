import logging
import time
import os
import sys
import json
import urllib.request
import urllib.error
import urllib.parse
import sqlite3
from datetime import datetime
from telegram import ReplyKeyboardMarkup, KeyboardButton, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram import InputMediaPhoto, InputMediaVideo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, Defaults, ContextTypes
from telegram.ext import CallbackQueryHandler, ConversationHandler, JobQueue
import fcntl
import redis
import threading
from config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD, REDIS_CHANNEL, DB_PATH

# 设置更详细的日志记录
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # 改为 DEBUG 级别以获取更多信息
)
logger = logging.getLogger(__name__)

# 确保数据库目录存在
def ensure_db_directory():
    """确保数据库目录存在"""
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        try:
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"创建数据库目录: {db_dir}")
        except Exception as e:
            logger.error(f"创建数据库目录失败: {e}")
            raise

# 数据库设置
def setup_database():
    """创建数据库表结构"""
    # 确保数据库目录存在
    ensure_db_directory()
    
    # 连接数据库
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 创建按钮表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS buttons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            position INTEGER,
            text TEXT NOT NULL,
            row INTEGER,
            column INTEGER,
            action TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建回复表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trigger TEXT NOT NULL,
            response_text TEXT NOT NULL,
            has_image INTEGER DEFAULT 0,
            image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 检查是否需要插入默认按钮
        cursor.execute("SELECT COUNT(*) FROM buttons")
        if cursor.fetchone()[0] == 0:
            buttons = [
                (1, "🔍 搜索", 0, 0, "search"),
                (2, "📢 最新活动", 0, 1, "latest_activities"),
                (3, "🏠 主页", 1, 0, "homepage"),
                (4, "👤 个人中心", 1, 1, "profile"),
                (5, "📸 图片展示", 2, 0, "photo_gallery"),
                (6, "📞 联系我们", 2, 1, "contact"),
                (7, "❓ 帮助", 3, 0, "help")
            ]
            cursor.executemany("INSERT INTO buttons (position, text, row, column, action) VALUES (?, ?, ?, ?, ?)", buttons)
        
        # 检查是否需要插入默认回复
        cursor.execute("SELECT COUNT(*) FROM responses")
        if cursor.fetchone()[0] == 0:
            responses = [
                ("🔍 搜索", "请输入您要搜索的内容：", 0, ""),
                ("🏠 主页", "🏠 欢迎访问西安娱乐导航主页\n\n我们提供西安地区最全面的娱乐信息和服务。\n请使用键盘按钮浏览不同功能。", 0, ""),
                ("📞 联系我们", "📞 联系我们\n\n客服电话: 029-XXXXXXXX\n电子邮件: support@example.com\n工作时间: 周一至周日 9:00-21:00", 0, ""),
                ("❓ 帮助", "可用命令:\n/start - 启动机器人\n/help - 显示此帮助消息\n/photo - 发送图片示例\n/video - 发送视频示例\n/admin - 管理员功能\n\n您也可以使用下方的键盘按钮快速访问功能。", 0, "")
            ]
            cursor.executemany("INSERT INTO responses (trigger, response_text, has_image, image_url) VALUES (?, ?, ?, ?)", responses)
        
        conn.commit()
        logger.info("数据库初始化成功")
    except sqlite3.Error as e:
        logger.error(f"数据库初始化失败: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

# 数据库客户端
redis_client = None

# 活跃用户字典，用于实时通知
active_users = {}

# 按钮更新标志文件路径
BUTTON_UPDATE_FLAG = os.path.join(os.path.dirname(__file__), 'button_update.flag')
# 上次检查按钮更新的时间
last_button_check = 0
# 按钮缓存
button_cache = None
# 按钮更新锁，防止多线程冲突
button_cache_lock = threading.Lock()

# 初始化Redis
def init_redis():
    global redis_client
    try:
        redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD
        )
        logger.info("Redis客户端初始化成功")
        return True
    except Exception as e:
        logger.error(f"Redis客户端初始化失败: {e}")
        return False

# Redis订阅线程
def redis_subscriber():
    """监听Redis中的按钮更新消息"""
    global redis_client
    
    if not redis_client:
        logger.error("Redis客户端未初始化，无法启动订阅")
        return
    
    pubsub = redis_client.pubsub()
    pubsub.subscribe(REDIS_CHANNEL)
    
    logger.info(f"开始监听Redis频道 {REDIS_CHANNEL} 的更新")
    
    for message in pubsub.listen():
        if message['type'] == 'message':
            try:
                data = json.loads(message['data'])
                logger.info(f"收到按钮更新消息: {data}")
                
                # 根据更新类型处理
                action = data.get('action', 'update')
                
                # 无论什么操作，都清除按钮缓存，强制重新加载
                with button_cache_lock:
                    global button_cache
                    button_cache = None
                    logger.info("按钮缓存已清除，将在下次请求时重新加载")
                
                # 通知活跃用户
                notify_active_users_about_update(data)
                
            except Exception as e:
                logger.error(f"处理Redis消息时出错: {e}")

# 通知活跃用户关于按钮更新
async def notify_active_users_about_update(update_data=None):
    """向活跃用户发送按钮更新通知"""
    global active_users
    
    # 只通知最近10分钟活跃的用户
    current_time = time.time()
    active_threshold = current_time - 600  # 10分钟
    
    users_to_notify = []
    for user_id, last_active in active_users.items():
        if last_active > active_threshold:
            users_to_notify.append(user_id)
    
    if not users_to_notify:
        logger.info("没有活跃用户需要通知")
        return
    
    try:
        # 从main函数获取application实例
        application = get_application_instance()
        if not application:
            logger.error("无法获取Application实例，无法发送通知")
            return
        
        # 确定更新类型，自定义消息
        action = update_data.get('action', 'update') if update_data else 'update'
        button_data = update_data.get('data', {}) if update_data else {}
        
        if action == 'add':
            message = f"📢 新按钮已添加: {button_data.get('text', '未知按钮')}"
        elif action == 'delete':
            message = f"📢 按钮已删除: {button_data.get('text', '未知按钮')}"
        else:
            message = "📢 按钮配置已更新，您将看到最新的键盘布局"
        
        # 向活跃用户发送通知
        for user_id in users_to_notify:
            try:
                await application.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    reply_markup=get_main_keyboard()
                )
                logger.info(f"成功向用户 {user_id} 发送按钮更新通知")
            except Exception as e:
                logger.error(f"向用户 {user_id} 发送通知时出错: {e}")
                
    except Exception as e:
        logger.error(f"通知活跃用户时出错: {e}")

# 全局Application实例
_application_instance = None

def set_application_instance(app):
    """设置全局Application实例，用于在非处理函数中发送消息"""
    global _application_instance
    _application_instance = app

def get_application_instance():
    """获取全局Application实例"""
    global _application_instance
    return _application_instance

# 检查按钮是否有更新
def check_button_updates():
    global last_button_check, button_cache
    
    with button_cache_lock:
        # 强制清除缓存，始终重新加载按钮数据
        button_cache = None
        last_button_check = time.time()
        logger.info("重新加载按钮配置")
    return True

# 从数据库加载按钮
def load_buttons_from_db():
    global button_cache
    
    # 如果缓存存在且没有检测到更新，直接返回缓存
    if button_cache is not None and not check_button_updates():
        return button_cache
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 获取所有按钮并按行和列排序
        cursor.execute("SELECT * FROM buttons ORDER BY row, column")
        buttons_data = cursor.fetchall()
        
        # 将按钮组织成行和列
        keyboard = []
        current_row = -1
        
        for button in buttons_data:
            row = button['row']
            column = button['column']
            text = button['text']
            
            # 如果是新的一行，添加一个新的行列表
            if row > current_row:
                keyboard.append([])
                current_row = row
            
            # 添加按钮到当前行
            if current_row < len(keyboard):
                keyboard[current_row].append(KeyboardButton(text))
        
        conn.close()
        
        # 如果没有按钮，使用默认键盘
        if not keyboard:
            keyboard = [
                [KeyboardButton("🔍 搜索"), KeyboardButton("📢 最新活动")],
                [KeyboardButton("🏠 主页"), KeyboardButton("👤 个人中心")],
                [KeyboardButton("📸 图片展示"), KeyboardButton("📞 联系我们")],
                [KeyboardButton("❓ 帮助")]
            ]
        
        # 更新缓存
        button_cache = keyboard
        return keyboard
    
    except Exception as e:
        logger.error(f"从数据库加载按钮时出错: {e}")
        # 出错时返回默认键盘
        return [
            [KeyboardButton("🔍 搜索"), KeyboardButton("📢 最新活动")],
            [KeyboardButton("🏠 主页"), KeyboardButton("👤 个人中心")],
            [KeyboardButton("📸 图片展示"), KeyboardButton("📞 联系我们")],
            [KeyboardButton("❓ 帮助")]
        ]

# 创建常驻键盘
def get_main_keyboard():
    keyboard = load_buttons_from_db()
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# 定义命令处理程序
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """当发出 /start 命令时发送消息。"""
    user = update.effective_user
    logger.info(f"收到来自用户 {user.id} ({user.username}) 的 /start 命令")
    
    # 保存用户信息到数据库
    save_user(user)
    
    # 确保获取最新的按钮配置
    check_button_updates()
    
    try:
        await update.message.reply_text(
            f'你好 {user.first_name}！我是西安娱乐导航机器人🤖。\n'
            f'使用下方键盘按钮或 /help 查看可用命令。',
            reply_markup=get_main_keyboard()
        )
        logger.info("成功发送 /start 响应")
    except Exception as e:
        logger.error(f"发送 /start 响应时出错: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """当发出 /help 命令时发送消息。"""
    user = update.effective_user
    logger.info(f"收到来自用户 {user.id} ({user.username}) 的 /help 命令")
    
    # 确保获取最新的按钮配置
    check_button_updates()
    
    try:
        await update.message.reply_text(
            '可用命令:\n'
            '/start - 启动机器人\n'
            '/help - 显示此帮助消息\n'
            '/photo - 发送图片示例\n'
            '/video - 发送视频示例\n'
            '/admin - 管理员功能\n\n'
            '您也可以使用下方的键盘按钮快速访问功能。',
            reply_markup=get_main_keyboard()
        )
        logger.info("成功发送 /help 响应")
    except Exception as e:
        logger.error(f"发送 /help 响应时出错: {e}")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理搜索按钮"""
    response_data = get_response_for_trigger("🔍 搜索")
    
    if response_data:
        response_text = response_data['response_text']
    else:
        response_text = "请输入您要搜索的内容："
    
    await update.message.reply_text(response_text)

async def latest_activities(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理最新活动按钮"""
    # 从数据库获取活动
    activities = get_activities()
    
    if not activities:
        await update.message.reply_text("目前没有活动信息。")
        return
    
    # 创建活动列表消息
    message = "📢 最新活动：\n\n"
    for i, activity in enumerate(activities, 1):
        message += f"{i}. {activity['title']} - {activity['date']}\n"
        message += f"   {activity['description']}\n\n"
    
    # 创建内联键盘，用于查看活动详情
    keyboard = []
    for activity in activities:
        keyboard.append([InlineKeyboardButton(f"查看: {activity['title']}", callback_data=f"activity_{activity['id']}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, reply_markup=reply_markup)

async def activity_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理活动详情按钮回调"""
    query = update.callback_query
    await query.answer()
    
    activity_id = query.data.split('_')[1]
    activity = get_activity_by_id(activity_id)
    
    if not activity:
        await query.edit_message_text("活动信息不存在或已被删除。")
        return
    
    message = f"🎉 <b>{activity['title']}</b>\n\n"
    message += f"📅 日期: {activity['date']}\n\n"
    message += f"📝 描述: {activity['description']}\n\n"
    
    # 如果有图片，发送图片
    if activity['image_url'] and activity['image_url'].startswith('http'):
        try:
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=activity['image_url'],
                caption=message,
                parse_mode='HTML'
            )
            await query.delete_message()
        except Exception as e:
            logger.error(f"发送活动图片时出错: {e}")
            # 如果发送图片失败，只发送文本
            await query.edit_message_text(message, parse_mode='HTML')
    else:
        await query.edit_message_text(message, parse_mode='HTML')

async def homepage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理主页按钮"""
    response_data = get_response_for_trigger("🏠 主页")
    
    if response_data:
        response_text = response_data['response_text']
    else:
        response_text = ("🏠 欢迎访问西安娱乐导航主页\n\n"
                        "我们提供西安地区最全面的娱乐信息和服务。\n"
                        "请使用键盘按钮浏览不同功能。")
    
    await update.message.reply_text(response_text, reply_markup=get_main_keyboard())

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理个人中心按钮"""
    user = update.effective_user
    
    # 获取用户信息
    user_info = get_user_by_id(user.id)
    
    if user_info:
        created_at = datetime.strptime(user_info['created_at'], '%Y-%m-%d %H:%M:%S')
        days_since_joined = (datetime.now() - created_at).days
        
        await update.message.reply_text(
            f"👤 <b>{user.first_name}</b> 的个人中心\n\n"
            f"用户ID: {user.id}\n"
            f"用户名: @{user.username}\n"
            f"加入时间: {user_info['created_at']}\n"
            f"使用天数: {days_since_joined} 天\n\n"
            "您目前没有待处理的订单。",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            f"👤 {user.first_name} 的个人中心\n\n"
            f"用户ID: {user.id}\n"
            f"用户名: @{user.username}\n\n"
            "您目前没有待处理的订单。"
        )

async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理联系我们按钮"""
    await update.message.reply_text(
        "📞 联系我们\n\n"
        "客服电话: 029-XXXXXXXX\n"
        "电子邮件: support@example.com\n"
        "工作时间: 周一至周日 9:00-21:00"
    )

async def photo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """发送图片示例"""
    # 发送单张图片
    await update.message.reply_photo(
        photo="https://upload.wikimedia.org/wikipedia/commons/thumb/e/e6/Xi%27an_-_Big_Wild_Goose_Pagoda.jpg/1200px-Xi%27an_-_Big_Wild_Goose_Pagoda.jpg",
        caption="大雁塔 - 西安著名景点"
    )
    
    # 发送多张图片
    media_group = [
        InputMediaPhoto("https://upload.wikimedia.org/wikipedia/commons/thumb/1/1b/Xi%27an_City_Wall.jpg/1200px-Xi%27an_City_Wall.jpg", caption="西安城墙"),
        InputMediaPhoto("https://upload.wikimedia.org/wikipedia/commons/thumb/6/6e/Bell_Tower_of_Xi%27an.jpg/1200px-Bell_Tower_of_Xi%27an.jpg"),
        InputMediaPhoto("https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Terracotta_Army%2C_View_of_Pit_1.jpg/1200px-Terracotta_Army%2C_View_of_Pit_1.jpg")
    ]
    
    await update.message.reply_media_group(media=media_group)

async def video_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """发送视频示例"""
    # 发送视频
    await update.message.reply_video(
        video="https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4",
        caption="视频示例 - 大雁塔灯光秀",
        supports_streaming=True
    )

async def photo_gallery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示图片画廊"""
    # 创建内联键盘，用于浏览不同类别的图片
    keyboard = [
        [InlineKeyboardButton("景点", callback_data="gallery_attractions")],
        [InlineKeyboardButton("美食", callback_data="gallery_food")],
        [InlineKeyboardButton("活动", callback_data="gallery_events")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📸 图片展示\n\n"
        "请选择您想浏览的图片类别：",
        reply_markup=reply_markup
    )

async def gallery_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理图片画廊回调"""
    query = update.callback_query
    await query.answer()
    
    category = query.data.split('_')[1]
    
    if category == "attractions":
        # 发送景点图片
        media_group = [
            InputMediaPhoto("https://upload.wikimedia.org/wikipedia/commons/thumb/e/e6/Xi%27an_-_Big_Wild_Goose_Pagoda.jpg/1200px-Xi%27an_-_Big_Wild_Goose_Pagoda.jpg", caption="大雁塔"),
            InputMediaPhoto("https://upload.wikimedia.org/wikipedia/commons/thumb/1/1b/Xi%27an_City_Wall.jpg/1200px-Xi%27an_City_Wall.jpg", caption="西安城墙"),
            InputMediaPhoto("https://upload.wikimedia.org/wikipedia/commons/thumb/6/6e/Bell_Tower_of_Xi%27an.jpg/1200px-Bell_Tower_of_Xi%27an.jpg", caption="钟楼")
        ]
        await query.delete_message()
        await context.bot.send_media_group(chat_id=query.message.chat_id, media=media_group)
    
    elif category == "food":
        # 发送美食图片
        media_group = [
            InputMediaPhoto("https://upload.wikimedia.org/wikipedia/commons/a/a5/Roujiamo.jpg", caption="肉夹馍"),
            InputMediaPhoto("https://upload.wikimedia.org/wikipedia/commons/2/28/Liangpi.jpg", caption="凉皮"),
            InputMediaPhoto("https://upload.wikimedia.org/wikipedia/commons/d/d8/Biangbiang_noodles.jpg", caption="Biangbiang面")
        ]
        await query.delete_message()
        await context.bot.send_media_group(chat_id=query.message.chat_id, media=media_group)
    
    elif category == "events":
        # 发送活动图片
        media_group = [
            InputMediaPhoto("https://example.com/event1.jpg", caption="音乐节"),
            InputMediaPhoto("https://example.com/event2.jpg", caption="美食节"),
            InputMediaPhoto("https://example.com/event3.jpg", caption="文化展览")
        ]
        try:
            await query.delete_message()
            await context.bot.send_media_group(chat_id=query.message.chat_id, media=media_group)
        except Exception as e:
            logger.error(f"发送活动图片时出错: {e}")
            await query.edit_message_text("抱歉，无法加载活动图片。请稍后再试。")

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """管理员功能"""
    user = update.effective_user
    
    # 检查是否是管理员（这里简单示例，实际应用中应该有更安全的验证）
    admin_ids = [123456789]  # 替换为实际管理员的用户ID
    
    if user.id not in admin_ids:
        await update.message.reply_text("抱歉，您没有管理员权限。")
        return
    
    # 创建管理员菜单
    keyboard = [
        [InlineKeyboardButton("添加活动", callback_data="admin_add_activity")],
        [InlineKeyboardButton("查看用户统计", callback_data="admin_user_stats")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👨‍💼 管理员面板\n\n"
        "请选择您要执行的操作：",
        reply_markup=reply_markup
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理文本消息"""
    text = update.message.text
    user = update.effective_user
    
    # 更新用户最后活动时间
    update_user_activity(user.id)
    
    # 记录活跃用户，用于实时推送
    global active_users
    active_users[user.id] = time.time()
    
    logger.info(f"收到来自用户 {user.id} ({user.username}) 的消息: {text}")
    
    # 检查按钮是否有更新 - 由于没有使用 JobQueue，在每次消息处理时检查
    button_updated = check_button_updates()
    
    # 从数据库获取回复
    response_data = get_response_for_trigger(text)
    
    if response_data:
        # 如果数据库中有匹配的回复
        response_text = response_data['response_text']
        has_image = response_data['has_image']
        image_url = response_data['image_url']
        
        if has_image and image_url:
            try:
                await update.message.reply_photo(
                    photo=image_url,
                    caption=response_text
                )
                
                # 如果按钮有更新，发送提示消息
                if button_updated:
                    await update.message.reply_text(
                        "界面按钮已更新，请使用最新的键盘按钮。",
                        reply_markup=get_main_keyboard()
                    )
                return
            except Exception as e:
                logger.error(f"发送图片回复时出错: {e}")
                # 如果图片发送失败，回退到纯文本回复
        
        await update.message.reply_text(response_text, reply_markup=get_main_keyboard())
        
        # 如果按钮有更新，发送提示消息
        if button_updated:
            await update.message.reply_text(
                "界面按钮已更新，请使用最新的键盘按钮。",
                reply_markup=get_main_keyboard()
            )
        return
    
    # 如果没有匹配的回复，根据按钮文本执行相应的函数
    if text == "🔍 搜索":
        await search(update, context)
    elif text == "📢 最新活动":
        await latest_activities(update, context)
    elif text == "🏠 主页":
        await homepage(update, context)
    elif text == "👤 个人中心":
        await profile(update, context)
    elif text == "📞 联系我们":
        await contact(update, context)
    elif text == "❓ 帮助":
        await help_command(update, context)
    elif text == "📸 图片展示":
        await photo_gallery(update, context)
    else:
        await update.message.reply_text(f"您发送了: {text}\n\n请使用键盘按钮选择功能。", reply_markup=get_main_keyboard())
    
    # 如果按钮有更新，发送提示消息
    if button_updated and text not in ["🔍 搜索", "📢 最新活动", "🏠 主页", "👤 个人中心", "📞 联系我们", "❓ 帮助", "📸 图片展示"]:
        await update.message.reply_text(
            "界面按钮已更新，请使用最新的键盘按钮。",
            reply_markup=get_main_keyboard()
        )

# 添加一个处理所有更新的函数，用于调试
async def debug_updates(update, context):
    """记录所有收到的更新，用于调试"""
    logger.debug(f"收到更新: {update.to_dict()}")
    # 不阻止其他处理程序处理此更新
    return False

# 错误处理函数
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理错误"""
    logger.error(f"更新 {update} 导致错误 {context.error}")
    
    # 获取完整的错误跟踪
    import traceback
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = ''.join(tb_list)
    
    # 记录详细错误信息
    logger.error(f"异常详情:\n{tb_string}")
    
    # 如果可能，向用户发送错误消息
    if update and hasattr(update, 'effective_message') and update.effective_message:
        await update.effective_message.reply_text(
            "抱歉，处理您的请求时出现了错误。请稍后再试。"
        )

# 使用 urllib 发送 HTTP 请求
def make_request(url):
    try:
        with urllib.request.urlopen(url) as response:
            return response.read().decode('utf-8'), response.getcode()
    except urllib.error.HTTPError as e:
        return e.read().decode('utf-8'), e.code
    except Exception as e:
        logger.error(f"请求错误: {e}")
        return str(e), 0

# 数据库操作函数
def save_user(user):
    """保存用户信息到数据库"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 检查用户是否已存在
        cursor.execute("SELECT id FROM users WHERE id = ?", (user.id,))
        if cursor.fetchone() is None:
            # 插入新用户
            cursor.execute(
                "INSERT INTO users (id, username, first_name, last_name, language_code, last_activity, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user.id, user.username, user.first_name, user.last_name, user.language_code, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )
        else:
            # 更新用户活动时间
            cursor.execute(
                "UPDATE users SET last_activity = ? WHERE id = ?",
                (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user.id)
            )
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"保存用户信息时出错: {e}")

def get_user_by_id(user_id):
    """根据ID获取用户信息"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        conn.close()
        
        if user:
            return dict(user)
        return None
    except Exception as e:
        logger.error(f"获取用户信息时出错: {e}")
        return None

def get_activities():
    """获取所有活动"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM activities ORDER BY date DESC")
        activities = cursor.fetchall()
        
        conn.close()
        
        return [dict(activity) for activity in activities]
    except Exception as e:
        logger.error(f"获取活动列表时出错: {e}")
        return []

def get_activity_by_id(activity_id):
    """根据ID获取活动详情"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM activities WHERE id = ?", (activity_id,))
        activity = cursor.fetchone()
        
        conn.close()
        
        if activity:
            return dict(activity)
        return None
    except Exception as e:
        logger.error(f"获取活动详情时出错: {e}")
        return None

def update_user_activity(user_id):
    """更新用户最后活动时间"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE users SET last_activity = datetime('now') WHERE id = ?",
            (user_id,)
        )
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"更新用户活动时间时出错: {e}")

# 定期检查按钮更新
async def check_updates(context: ContextTypes.DEFAULT_TYPE = None):
    """定期检查按钮更新，如有更新则通知活跃用户"""
    if check_button_updates():
        logger.info("检测到按钮更新，将重新加载按钮配置")
        # 这里可以添加通知活跃用户的逻辑，例如发送消息告知用户界面已更新
        # 或者在用户下次交互时自动更新界面

# 从数据库获取按钮触发的响应
def get_response_for_trigger(trigger_text):
    """根据触发文本从数据库获取对应的响应"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM responses WHERE trigger_text = ?", (trigger_text,))
        response = cursor.fetchone()
        
        conn.close()
        
        if response:
            return dict(response)
        return None
    except Exception as e:
        logger.error(f"获取响应数据时出错: {e}")
        return None

async def refresh_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """刷新机器人配置"""
    user = update.effective_user
    
    # 清除按钮缓存
    global button_cache
    button_cache = None
    
    await update.message.reply_text(
        "配置已刷新，按钮和响应数据已重新加载。",
        reply_markup=get_main_keyboard()
    )

def main():
    # 创建锁文件
    lock_file = open("/tmp/telegram_bot.lock", "w")
    
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        logger.error("另一个机器人实例已经在运行")
        sys.exit(1)
    
    # 初始化Redis
    redis_success = init_redis()
    if redis_success:
        # 启动Redis订阅线程
        subscriber_thread = threading.Thread(target=redis_subscriber, daemon=True)
        subscriber_thread.start()
        logger.info("已启动Redis订阅线程")
    else:
        logger.warning("Redis初始化失败，将使用文件监控方式检查按钮更新")
    
    # 从配置文件读取token
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            token = config.get('token')
    except Exception as e:
        logger.error(f"读取配置文件时出错: {e}")
        token = None
    
    if not token:
        logger.error("未找到有效的机器人token")
        sys.exit(1)
    
    try:
        # 设置数据库
        setup_database()
        
        # 检查机器人 token 是否有效
        response_text, status_code = make_request(f"https://api.telegram.org/bot{token}/getMe")
        if status_code != 200:
            logger.error(f"机器人 token 无效: {response_text}")
            return
        
        bot_info = json.loads(response_text)["result"]
        logger.info(f"机器人信息: {bot_info['first_name']} (@{bot_info['username']})")
        
        # 删除任何现有的 webhook
        response_text, _ = make_request(f"https://api.telegram.org/bot{token}/deleteWebhook")
        logger.info(f"删除 webhook 结果: {response_text}")
        
        # 创建 Application
        defaults = Defaults(parse_mode='HTML')  # 使用 HTML 解析模式
        application = Application.builder().token(token).defaults(defaults).build()
        logger.info("成功创建 Application 实例")
        
        # 保存全局应用实例，用于Redis通知
        set_application_instance(application)

        # 使用 JobQueue 定期检查按钮更新
        job_queue = application.job_queue
        job_queue.run_repeating(check_updates, interval=10, first=5)  # 每10秒检查一次
        logger.info("已设置定期检查按钮更新的任务")
        
        # 添加调试处理程序（必须放在第一位）
        application.add_handler(MessageHandler(filters.ALL, debug_updates), group=-1)
        
        # 添加常规处理程序
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("photo", photo_command))
        application.add_handler(CommandHandler("video", video_command))
        application.add_handler(CommandHandler("admin", admin_command))
        application.add_handler(CommandHandler("refresh", refresh_command))
        
        # 添加回调查询处理程序
        application.add_handler(CallbackQueryHandler(activity_details, pattern="^activity_"))
        application.add_handler(CallbackQueryHandler(gallery_callback, pattern="^gallery_"))
        
        # 添加消息处理程序
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # 添加错误处理程序
        application.add_error_handler(error_handler)
        
        logger.info("成功添加所有处理程序")

        # 确保没有其他实例在运行
        logger.info("检查是否有其他机器人实例在运行...")
        pid = os.getpid()
        logger.info(f"当前进程 PID: {pid}")
        
        # 添加重试逻辑和更好的错误处理
        max_retries = 5
        retry_delay = 10  # 秒
        
        logger.info("开始运行机器人...")
        for attempt in range(max_retries):
            try:
                # 启动机器人
                logger.info(f"尝试启动机器人 (尝试 {attempt+1}/{max_retries})")
                application.run_polling(
                    poll_interval=1.0,
                    timeout=30,
                    read_timeout=30,
                    write_timeout=30,
                    connect_timeout=30,
                    pool_timeout=30,
                    drop_pending_updates=True,
                    allowed_updates=None  # 允许所有类型的更新
                )
                logger.info("机器人成功运行")
                break  # 如果成功，退出重试循环
                
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"连接错误: {e}. {retry_delay} 秒后重试... (尝试 {attempt+1}/{max_retries})")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"{max_retries} 次尝试后连接失败。退出。")
                    raise
    except Exception as e:
        logger.error(f"初始化机器人时发生错误: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise

if __name__ == '__main__':
    logger.info("启动 Telegram 机器人程序")
    # 设置数据库
    setup_database()
    # 初始化按钮检查时间
    if os.path.exists(BUTTON_UPDATE_FLAG):
        last_button_check = os.path.getmtime(BUTTON_UPDATE_FLAG)
    else:
        with open(BUTTON_UPDATE_FLAG, 'w') as f:
            last_button_check = time.time()
            f.write(str(last_button_check))
    main() 