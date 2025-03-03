from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import json
import os
import time
from functools import wraps
from config import SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD, DB_PATH
from config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD, REDIS_CHANNEL
import redis

app = Flask(__name__)
app.secret_key = SECRET_KEY

# 初始化Redis连接
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD
)

# 按钮更新标志文件路径 (保留向后兼容)
BUTTON_UPDATE_FLAG = os.path.join(os.path.dirname(__file__), 'button_update.flag')

# 更新按钮变更标志和通知Redis
def update_button_change_flag(button_data=None, action="update"):
    # 保留文件标志更新方式 (向后兼容)
    with open(BUTTON_UPDATE_FLAG, 'w') as f:
        f.write(str(time.time()))
    
    # 通过Redis发布按钮更新消息
    update_message = {
        "timestamp": time.time(),
        "action": action,  # "update", "add", "delete"
        "data": button_data
    }
    
    try:
        redis_client.publish(REDIS_CHANNEL, json.dumps(update_message))
        return True
    except Exception as e:
        print(f"Redis发布更新消息失败: {e}")
        return False

# 创建按钮表和回复表
def setup_database():
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
    conn.close()

# 登录验证装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# 路由
@app.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            flash('登录成功！', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('用户名或密码错误！', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('您已退出登录！', 'info')
    return redirect(url_for('login'))

@app.route('/buttons', methods=['GET', 'POST'])
@login_required
def edit_buttons():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if request.method == 'POST':
        button_id = request.form.get('button_id')
        text = request.form.get('text')
        row = request.form.get('row')
        column = request.form.get('column')
        action = request.form.get('action')
        
        button_data = {
            "id": button_id,
            "text": text,
            "row": row,
            "column": column,
            "action": action
        }
        
        if button_id:  # 编辑现有按钮
            cursor.execute(
                "UPDATE buttons SET text = ?, row = ?, column = ?, action = ? WHERE id = ?",
                (text, row, column, action, button_id)
            )
            flash('按钮已更新！', 'success')
            update_action = "update"
        else:  # 添加新按钮
            # 获取最大位置值
            cursor.execute("SELECT MAX(position) FROM buttons")
            max_position = cursor.fetchone()[0] or 0
            
            cursor.execute(
                "INSERT INTO buttons (position, text, row, column, action) VALUES (?, ?, ?, ?, ?)",
                (max_position + 1, text, row, column, action)
            )
            # 获取新插入按钮的ID
            button_data["id"] = cursor.lastrowid
            flash('新按钮已添加！', 'success')
            update_action = "add"
        
        conn.commit()
        # 更新按钮变更标志，包含按钮数据和操作类型
        update_button_change_flag(button_data, update_action)
    
    # 获取所有按钮
    cursor.execute("SELECT * FROM buttons ORDER BY row, column")
    buttons = cursor.fetchall()
    
    conn.close()
    
    return render_template('edit_buttons.html', buttons=buttons)

@app.route('/delete_button/<int:button_id>', methods=['POST'])
@login_required
def delete_button(button_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 先获取要删除的按钮信息
    cursor.execute("SELECT * FROM buttons WHERE id = ?", (button_id,))
    button = cursor.fetchone()
    
    if button:
        # 转换为字典以便JSON序列化
        button_data = {
            "id": button["id"],
            "text": button["text"],
            "row": button["row"],
            "column": button["column"],
            "action": button["action"]
        }
        
        cursor.execute("DELETE FROM buttons WHERE id = ?", (button_id,))
        conn.commit()
        
        # 更新按钮变更标志，传递删除的按钮信息和操作类型
        update_button_change_flag(button_data, "delete")
        
        flash('按钮已删除！', 'success')
    else:
        flash('按钮不存在！', 'error')
    
    conn.close()
    return redirect(url_for('edit_buttons'))

@app.route('/responses', methods=['GET', 'POST'])
@login_required
def edit_responses():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if request.method == 'POST':
        response_id = request.form.get('response_id')
        trigger = request.form.get('trigger')
        response_text = request.form.get('response_text')
        has_image = 1 if request.form.get('has_image') else 0
        image_url = request.form.get('image_url') or ""
        
        if response_id:  # 编辑现有回复
            cursor.execute(
                "UPDATE responses SET trigger = ?, response_text = ?, has_image = ?, image_url = ? WHERE id = ?",
                (trigger, response_text, has_image, image_url, response_id)
            )
            flash('回复已更新！', 'success')
        else:  # 添加新回复
            cursor.execute(
                "INSERT INTO responses (trigger, response_text, has_image, image_url) VALUES (?, ?, ?, ?)",
                (trigger, response_text, has_image, image_url)
            )
            flash('新回复已添加！', 'success')
        
        conn.commit()
    
    # 获取所有回复
    cursor.execute("SELECT * FROM responses ORDER BY trigger")
    responses = cursor.fetchall()
    
    conn.close()
    
    return render_template('edit_responses.html', responses=responses)

@app.route('/delete_response/<int:response_id>', methods=['POST'])
@login_required
def delete_response(response_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM responses WHERE id = ?", (response_id,))
    conn.commit()
    conn.close()
    
    flash('回复已删除！', 'success')
    return redirect(url_for('edit_responses'))

@app.route('/export_config')
@login_required
def export_config():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 获取所有按钮
    cursor.execute("SELECT * FROM buttons ORDER BY position")
    buttons = [dict(row) for row in cursor.fetchall()]
    
    # 获取所有回复
    cursor.execute("SELECT * FROM responses")
    responses = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    config = {
        'buttons': buttons,
        'responses': responses
    }
    
    return json.dumps(config, indent=4)

if __name__ == '__main__':
    # 确保数据库和表存在
    setup_database()
    
    # 启动 Web 服务器
    app.run(host='0.0.0.0', port=5000, debug=True) 