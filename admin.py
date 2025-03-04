#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Telegram Bot 管理面板
提供Web界面管理按钮和菜单配置
"""

import os
import sys
import json
import time
import logging
import secrets
from functools import wraps
from logging.handlers import RotatingFileHandler

try:
    from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
    from flask_wtf import FlaskForm
    from wtforms import StringField, TextAreaField, PasswordField, BooleanField, SelectField, IntegerField, SubmitField
    from wtforms.validators import DataRequired, Length, URL, Optional
except ImportError:
    print("Flask和相关库未安装。请运行: pip install flask flask-wtf")
    sys.exit(1)

try:
    from config import (
        ADMIN_PORT, ADMIN_USERNAME, ADMIN_PASSWORD, SECRET_KEY,
        DATA_DIR, LOG_DIR, DB_PATH, LOG_LEVEL, LOG_FORMAT
    )
except ImportError:
    print("无法导入config.py。请确保该文件存在并包含必要的配置。")
    sys.exit(1)

try:
    import database as db
except ImportError:
    print("无法导入database.py。请确保该文件存在。")
    sys.exit(1)

# 创建日志目录
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR, exist_ok=True)

# 配置日志
logging.basicConfig(
    format=LOG_FORMAT,
    level=LOG_LEVEL
)

# 创建文件处理器
log_file = os.path.join(LOG_DIR, 'admin.log')
file_handler = RotatingFileHandler(
    log_file,
    maxBytes=10 * 1024 * 1024,  # 10 MB
    backupCount=5
)
file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

# 获取根日志记录器并添加文件处理器
logger = logging.getLogger()
logger.addHandler(file_handler)

# 创建Flask应用
app = Flask(__name__)
app.secret_key = SECRET_KEY or secrets.token_hex(16)
app.config['WTF_CSRF_ENABLED'] = True
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

# 表单类
class LoginForm(FlaskForm):
    """登录表单"""
    username = StringField('用户名', validators=[DataRequired()])
    password = PasswordField('密码', validators=[DataRequired()])
    remember = BooleanField('记住我')
    submit = SubmitField('登录')

class ButtonForm(FlaskForm):
    """按钮表单"""
    name = StringField('按钮名称', validators=[DataRequired(), Length(min=3, max=50)])
    text = StringField('按钮文本', validators=[DataRequired(), Length(max=100)])
    callback_data = StringField('回调数据', validators=[Length(max=100), Optional()])
    url = StringField('URL链接', validators=[Length(max=255), Optional(), URL()])
    position = IntegerField('位置', default=0)
    row = IntegerField('行', default=0)
    is_active = BooleanField('启用', default=True)
    submit = SubmitField('保存')

class MenuForm(FlaskForm):
    """菜单表单"""
    name = StringField('菜单名称', validators=[DataRequired(), Length(min=3, max=50)])
    title = StringField('菜单标题', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('菜单描述', validators=[Length(max=500), Optional()])
    is_active = BooleanField('启用', default=True)
    submit = SubmitField('保存')

class MenuButtonForm(FlaskForm):
    """菜单-按钮关联表单"""
    button_id = SelectField('按钮', coerce=int, validators=[DataRequired()])
    position = IntegerField('位置', default=0)
    row = IntegerField('行', default=0)
    submit = SubmitField('添加到菜单')

# 登录验证装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# 添加模板上下文处理器
@app.context_processor
def inject_menu_data():
    """向所有模板注入菜单数据"""
    menus = db.get_all_menus()
    return dict(menus=menus)

# 路由：首页
@app.route('/')
@login_required
def index():
    """管理面板首页"""
    button_count = len(db.get_all_buttons())
    menu_count = len(db.get_all_menus())
    
    # 获取最近添加的按钮和菜单
    buttons = db.get_all_buttons()
    menus = db.get_all_menus()
    
    latest_buttons = sorted(buttons, key=lambda x: x['created_at'], reverse=True)[:5]
    latest_menus = sorted(menus, key=lambda x: x['created_at'], reverse=True)[:5]
    
    return render_template(
        'index.html', 
        button_count=button_count, 
        menu_count=menu_count,
        latest_buttons=latest_buttons,
        latest_menus=latest_menus
    )

# 路由：登录
@app.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    form = LoginForm()
    
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        
        # 简单的身份验证 (生产环境应使用更安全的方法)
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            session['username'] = username
            flash('登录成功！', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('用户名或密码错误！', 'danger')
    
    return render_template('login.html', form=form)

# 路由：退出登录
@app.route('/logout')
def logout():
    """用户退出登录"""
    session.pop('logged_in', None)
    session.pop('username', None)
    flash('您已退出登录！', 'info')
    return redirect(url_for('login'))

# 路由：按钮管理
@app.route('/buttons')
@login_required
def buttons():
    """按钮列表"""
    all_buttons = db.get_all_buttons()
    return render_template('buttons.html', buttons=all_buttons)

# 路由：添加按钮
@app.route('/buttons/add', methods=['GET', 'POST'])
@login_required
def add_button():
    """添加新按钮"""
    form = ButtonForm()
    
    if form.validate_on_submit():
        button_id = db.create_button(
            name=form.name.data,
            text=form.text.data,
            callback_data=form.callback_data.data,
            url=form.url.data,
            position=form.position.data,
            row=form.row.data
        )
        
        if button_id:
            flash(f'按钮 "{form.text.data}" 已成功添加！', 'success')
            return redirect(url_for('buttons'))
        else:
            flash('添加按钮失败！', 'danger')
    
    return render_template('button_form.html', form=form, title='添加按钮')

# 路由：编辑按钮
@app.route('/buttons/edit/<int:button_id>', methods=['GET', 'POST'])
@login_required
def edit_button(button_id):
    """编辑按钮"""
    button = db.get_button_by_id(button_id)
    if not button:
        flash('按钮不存在！', 'danger')
        return redirect(url_for('buttons'))
    
    form = ButtonForm(obj=button)
    
    if form.validate_on_submit():
        success = db.update_button(
            button_id=button_id,
            name=form.name.data,
            text=form.text.data,
            callback_data=form.callback_data.data,
            url=form.url.data,
            position=form.position.data,
            row=form.row.data,
            is_active=form.is_active.data
        )
        
        if success:
            flash(f'按钮 "{form.text.data}" 已成功更新！', 'success')
            return redirect(url_for('buttons'))
        else:
            flash('更新按钮失败！', 'danger')
    
    return render_template('button_form.html', form=form, title='编辑按钮')

# 路由：删除按钮
@app.route('/buttons/delete/<int:button_id>', methods=['POST'])
@login_required
def delete_button(button_id):
    """删除按钮"""
    button = db.get_button_by_id(button_id)
    if not button:
        flash('按钮不存在！', 'danger')
        return redirect(url_for('buttons'))
    
    if db.delete_button(button_id):
        flash(f'按钮 "{button["text"]}" 已成功删除！', 'success')
    else:
        flash('删除按钮失败！', 'danger')
    
    return redirect(url_for('buttons'))

# 路由：菜单管理
@app.route('/menus')
@login_required
def menus():
    """菜单列表"""
    all_menus = db.get_all_menus()
    return render_template('menus.html', menus=all_menus)

# 路由：添加菜单
@app.route('/menus/add', methods=['GET', 'POST'])
@login_required
def add_menu():
    """添加新菜单"""
    form = MenuForm()
    
    if form.validate_on_submit():
        menu_id = db.create_menu(
            name=form.name.data,
            title=form.title.data,
            description=form.description.data
        )
        
        if menu_id:
            flash(f'菜单 "{form.title.data}" 已成功添加！', 'success')
            return redirect(url_for('menus'))
        else:
            flash('添加菜单失败！', 'danger')
    
    return render_template('menu_form.html', form=form, title='添加菜单')

# 路由：编辑菜单
@app.route('/menus/edit/<int:menu_id>', methods=['GET', 'POST'])
@login_required
def edit_menu(menu_id):
    """编辑菜单"""
    menu = db.get_menu_by_id(menu_id)
    if not menu:
        flash('菜单不存在！', 'danger')
        return redirect(url_for('menus'))
    
    form = MenuForm(obj=menu)
    
    if form.validate_on_submit():
        success = db.update_menu(
            menu_id=menu_id,
            name=form.name.data,
            title=form.title.data,
            description=form.description.data,
            is_active=form.is_active.data
        )
        
        if success:
            flash(f'菜单 "{form.title.data}" 已成功更新！', 'success')
            return redirect(url_for('menus'))
        else:
            flash('更新菜单失败！', 'danger')
    
    return render_template('menu_form.html', form=form, title='编辑菜单')

# 路由：删除菜单
@app.route('/menus/delete/<int:menu_id>', methods=['POST'])
@login_required
def delete_menu(menu_id):
    """删除菜单"""
    menu = db.get_menu_by_id(menu_id)
    if not menu:
        flash('菜单不存在！', 'danger')
        return redirect(url_for('menus'))
    
    if db.delete_menu(menu_id):
        flash(f'菜单 "{menu["title"]}" 已成功删除！', 'success')
    else:
        flash('删除菜单失败！', 'danger')
    
    return redirect(url_for('menus'))

# 路由：管理菜单按钮
@app.route('/menus/<int:menu_id>/buttons', methods=['GET', 'POST'])
@login_required
def menu_buttons(menu_id):
    """管理菜单按钮"""
    menu = db.get_menu_by_id(menu_id)
    if not menu:
        flash('菜单不存在！', 'danger')
        return redirect(url_for('menus'))
    
    # 获取菜单中的按钮
    menu_buttons = db.get_menu_buttons(menu_id)
    
    # 获取未添加到此菜单的按钮
    all_buttons = db.get_all_buttons()
    assigned_button_ids = [b['id'] for b in menu_buttons]
    available_buttons = [b for b in all_buttons if b['id'] not in assigned_button_ids]
    
    # 创建表单
    form = MenuButtonForm()
    form.button_id.choices = [(b['id'], f"{b['text']} ({b['name']})") for b in available_buttons]
    
    if form.validate_on_submit() and available_buttons:
        button_id = form.button_id.data
        position = form.position.data
        row = form.row.data
        
        if db.add_button_to_menu(menu_id, button_id, position, row):
            button = db.get_button_by_id(button_id)
            flash(f'按钮 "{button["text"]}" 已添加到 "{menu["title"]}" 菜单！', 'success')
            return redirect(url_for('menu_buttons', menu_id=menu_id))
        else:
            flash('添加按钮到菜单失败！', 'danger')
    
    return render_template(
        'menu_buttons.html', 
        menu=menu, 
        menu_buttons=menu_buttons,
        form=form,
        has_available_buttons=bool(available_buttons)
    )

# 路由：从菜单中移除按钮
@app.route('/menus/<int:menu_id>/buttons/remove/<int:button_id>', methods=['POST'])
@login_required
def remove_button_from_menu(menu_id, button_id):
    """从菜单中移除按钮"""
    menu = db.get_menu_by_id(menu_id)
    button = db.get_button_by_id(button_id)
    
    if not menu or not button:
        flash('菜单或按钮不存在！', 'danger')
        return redirect(url_for('menus'))
    
    if db.remove_button_from_menu(menu_id, button_id):
        flash(f'按钮 "{button["text"]}" 已从 "{menu["title"]}" 菜单中移除！', 'success')
    else:
        flash('从菜单中移除按钮失败！', 'danger')
    
    return redirect(url_for('menu_buttons', menu_id=menu_id))

# 路由：预览菜单
@app.route('/menus/<int:menu_id>/preview')
@login_required
def preview_menu(menu_id):
    """预览菜单布局"""
    menu = db.get_menu_by_id(menu_id)
    if not menu:
        flash('菜单不存在！', 'danger')
        return redirect(url_for('menus'))
    
    # 获取菜单中的按钮并按行和位置排序
    buttons = db.get_menu_buttons(menu_id)
    
    # 按行分组按钮
    rows = {}
    for button in buttons:
        row_num = button['row']
        if row_num not in rows:
            rows[row_num] = []
        rows[row_num].append(button)
    
    # 排序每行中的按钮
    for row_num in rows:
        rows[row_num] = sorted(rows[row_num], key=lambda x: x['position'])
    
    # 获取排序后的行
    sorted_rows = [rows[row_num] for row_num in sorted(rows.keys())]
    
    return render_template('menu_preview.html', menu=menu, rows=sorted_rows)

# 路由：API路由
@app.route('/api/buttons', methods=['GET'])
def api_buttons():
    """获取所有按钮（API）"""
    buttons = db.get_all_buttons()
    return jsonify(buttons)

@app.route('/api/menus', methods=['GET'])
def api_menus():
    """获取所有菜单（API）"""
    menus = db.get_all_menus()
    return jsonify(menus)

@app.route('/api/menus/<string:menu_name>/buttons', methods=['GET'])
def api_menu_buttons(menu_name):
    """获取特定菜单的按钮（API）"""
    menu = db.get_menu_by_name(menu_name)
    if not menu:
        return jsonify({"error": "Menu not found"}), 404
    
    buttons = db.get_menu_buttons(menu['id'])
    return jsonify(buttons)

# 创建必要的静态文件和模板目录
def create_template_dirs():
    """创建模板和静态文件目录"""
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir, exist_ok=True)
    
    if not os.path.exists(static_dir):
        os.makedirs(static_dir, exist_ok=True)
        os.makedirs(os.path.join(static_dir, 'css'), exist_ok=True)
        os.makedirs(os.path.join(static_dir, 'js'), exist_ok=True)
    
    # 创建基本模板文件
    base_template = os.path.join(templates_dir, 'base.html')
    if not os.path.exists(base_template):
        with open(base_template, 'w', encoding='utf-8') as f:
            f.write('''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Telegram Bot 管理面板{% endblock %}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    {% block extra_css %}{% endblock %}
</head>
<body>
    {% if session.logged_in %}
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('index') }}">TG Bot 管理</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav me-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('index') }}">首页</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('buttons') }}">按钮管理</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('menus') }}">菜单管理</a>
                    </li>
                </ul>
                <ul class="navbar-nav">
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('logout') }}">退出登录</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>
    {% endif %}

    <div class="container mt-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
        {% for category, message in messages %}
        <div class="alert alert-{{ category }}">{{ message }}</div>
        {% endfor %}
        {% endif %}
        {% endwith %}

        {% block content %}{% endblock %}
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/jquery@3.6.3/dist/jquery.min.js"></script>
    {% block extra_js %}{% endblock %}
</body>
</html>
            ''')
    
    # 创建样式文件
    css_file = os.path.join(static_dir, 'css', 'style.css')
    if not os.path.exists(css_file):
        with open(css_file, 'w', encoding='utf-8') as f:
            f.write('''
body {
    padding-bottom: 40px;
}
.form-label {
    font-weight: 500;
}
.card-header {
    font-weight: 500;
}
.preview-button {
    margin: 5px;
    min-width: 150px;
}
            ''')
    
    # 创建登录模板
    login_template = os.path.join(templates_dir, 'login.html')
    if not os.path.exists(login_template):
        with open(login_template, 'w', encoding='utf-8') as f:
            f.write('''
{% extends "base.html" %}

{% block title %}登录 - Telegram Bot 管理面板{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header bg-primary text-white">
                <h4 class="mb-0">登录管理面板</h4>
            </div>
            <div class="card-body">
                <form method="POST">
                    {{ form.hidden_tag() }}
                    <div class="mb-3">
                        {{ form.username.label(class="form-label") }}
                        {{ form.username(class="form-control") }}
                    </div>
                    <div class="mb-3">
                        {{ form.password.label(class="form-label") }}
                        {{ form.password(class="form-control") }}
                    </div>
                    <div class="mb-3 form-check">
                        {{ form.remember(class="form-check-input") }}
                        {{ form.remember.label(class="form-check-label") }}
                    </div>
                    <div class="d-grid">
                        {{ form.submit(class="btn btn-primary") }}
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}
            ''')

# 程序入口
if __name__ == '__main__':
    try:
        # 确保数据库已设置
        db.setup_database()
        
        # 创建模板目录
        create_template_dirs()
        
        # 运行应用
        app.run(host='0.0.0.0', port=ADMIN_PORT, debug=True)
    except KeyboardInterrupt:
        print("程序被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"程序启动异常: {e}")
        sys.exit(1) 