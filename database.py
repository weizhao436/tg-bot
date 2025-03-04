#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import json
import time
import logging
import os
from config import DB_PATH, DATA_DIR

# 确保数据目录存在
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)

# 设置日志记录器
logger = logging.getLogger(__name__)

def dict_factory(cursor, row):
    """将SQLite查询结果转换为字典"""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = dict_factory
    return conn

def setup_database():
    """初始化数据库结构"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 创建用户表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            username TEXT,
            language_code TEXT,
            is_bot INTEGER DEFAULT 0,
            created_at INTEGER,
            last_activity INTEGER
        )
        ''')
        
        # 创建按钮表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS buttons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            text TEXT NOT NULL,
            callback_data TEXT,
            url TEXT,
            position INTEGER,
            row INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at INTEGER,
            updated_at INTEGER
        )
        ''')
        
        # 创建菜单表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS menus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            description TEXT,
            is_active INTEGER DEFAULT 1,
            created_at INTEGER,
            updated_at INTEGER
        )
        ''')
        
        # 创建菜单-按钮关联表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS menu_buttons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            menu_id INTEGER,
            button_id INTEGER,
            position INTEGER,
            row INTEGER DEFAULT 0,
            FOREIGN KEY (menu_id) REFERENCES menus (id) ON DELETE CASCADE,
            FOREIGN KEY (button_id) REFERENCES buttons (id) ON DELETE CASCADE
        )
        ''')
        
        # 创建按钮更新跟踪表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS button_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            last_update INTEGER
        )
        ''')
        
        # 插入初始按钮更新记录
        cursor.execute('''
        INSERT OR IGNORE INTO button_updates (id, last_update) VALUES (1, ?)
        ''', (int(time.time()),))
        
        # 如果没有默认菜单，创建一个
        cursor.execute('SELECT COUNT(*) as count FROM menus')
        result = cursor.fetchone()
        if result['count'] == 0:
            current_time = int(time.time())
            cursor.execute('''
            INSERT INTO menus (name, title, description, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', ('main_menu', '主菜单', '机器人的主菜单', 1, current_time, current_time))
            
            # 添加一些默认按钮
            cursor.execute('''
            INSERT INTO buttons (name, text, callback_data, position, row, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', ('help_button', '帮助', 'help', 0, 0, 1, current_time, current_time))
            
            cursor.execute('''
            INSERT INTO buttons (name, text, callback_data, position, row, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', ('about_button', '关于', 'about', 1, 0, 1, current_time, current_time))
            
            # 获取插入的按钮ID
            cursor.execute('SELECT id FROM buttons WHERE name = ?', ('help_button',))
            help_button_id = cursor.fetchone()['id']
            
            cursor.execute('SELECT id FROM buttons WHERE name = ?', ('about_button',))
            about_button_id = cursor.fetchone()['id']
            
            # 获取主菜单ID
            cursor.execute('SELECT id FROM menus WHERE name = ?', ('main_menu',))
            main_menu_id = cursor.fetchone()['id']
            
            # 关联按钮到主菜单
            cursor.execute('''
            INSERT INTO menu_buttons (menu_id, button_id, position, row)
            VALUES (?, ?, ?, ?)
            ''', (main_menu_id, help_button_id, 0, 0))
            
            cursor.execute('''
            INSERT INTO menu_buttons (menu_id, button_id, position, row)
            VALUES (?, ?, ?, ?)
            ''', (main_menu_id, about_button_id, 1, 0))
        
        conn.commit()
        logger.info("数据库结构设置完成")
        return True
    except Exception as e:
        logger.error(f"设置数据库时出错: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

# 用户相关函数
def save_user(user_id, first_name, last_name, username, language_code):
    """保存用户信息到数据库"""
    try:
        current_time = int(time.time())
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT OR REPLACE INTO users 
        (user_id, first_name, last_name, username, language_code, created_at, last_activity)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, first_name, last_name, username, language_code, current_time, current_time))
        
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"保存用户信息时出错: {e}")
        return False
    finally:
        if conn:
            conn.close()

def update_user_activity(user_id):
    """更新用户的最后活动时间"""
    try:
        current_time = int(time.time())
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE users SET last_activity = ? WHERE user_id = ?
        ''', (current_time, user_id))
        
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"更新用户活动时间出错: {e}")
        return False
    finally:
        if conn:
            conn.close()

def get_user_by_id(user_id):
    """通过ID获取用户信息"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        return user
    except Exception as e:
        logger.error(f"获取用户信息时出错: {e}")
        return None
    finally:
        if conn:
            conn.close()

# 按钮相关函数
def get_all_buttons():
    """获取所有按钮"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM buttons ORDER BY row, position')
        buttons = cursor.fetchall()
        return buttons
    except Exception as e:
        logger.error(f"获取所有按钮时出错: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_button_by_id(button_id):
    """通过ID获取按钮"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM buttons WHERE id = ?', (button_id,))
        button = cursor.fetchone()
        return button
    except Exception as e:
        logger.error(f"获取按钮信息时出错: {e}")
        return None
    finally:
        if conn:
            conn.close()

def create_button(name, text, callback_data=None, url=None, position=0, row=0):
    """创建新按钮"""
    try:
        current_time = int(time.time())
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO buttons 
        (name, text, callback_data, url, position, row, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, text, callback_data, url, position, row, 1, current_time, current_time))
        
        # 更新按钮更新时间
        cursor.execute('UPDATE button_updates SET last_update = ? WHERE id = 1', (current_time,))
        
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"创建按钮时出错: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            conn.close()

def update_button(button_id, name=None, text=None, callback_data=None, url=None, position=None, row=None, is_active=None):
    """更新按钮信息"""
    try:
        current_time = int(time.time())
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取当前按钮信息
        cursor.execute('SELECT * FROM buttons WHERE id = ?', (button_id,))
        button = cursor.fetchone()
        
        if not button:
            return False
        
        # 更新有提供的字段
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        
        if text is not None:
            updates.append("text = ?")
            params.append(text)
        
        if callback_data is not None:
            updates.append("callback_data = ?")
            params.append(callback_data)
        
        if url is not None:
            updates.append("url = ?")
            params.append(url)
        
        if position is not None:
            updates.append("position = ?")
            params.append(position)
        
        if row is not None:
            updates.append("row = ?")
            params.append(row)
        
        if is_active is not None:
            updates.append("is_active = ?")
            params.append(is_active)
        
        updates.append("updated_at = ?")
        params.append(current_time)
        
        # 构建和执行更新查询
        query = f"UPDATE buttons SET {', '.join(updates)} WHERE id = ?"
        params.append(button_id)
        
        cursor.execute(query, params)
        
        # 更新按钮更新时间
        cursor.execute('UPDATE button_updates SET last_update = ? WHERE id = 1', (current_time,))
        
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"更新按钮信息时出错: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def delete_button(button_id):
    """删除按钮"""
    try:
        current_time = int(time.time())
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 删除按钮
        cursor.execute('DELETE FROM buttons WHERE id = ?', (button_id,))
        
        # 同时删除菜单-按钮关联
        cursor.execute('DELETE FROM menu_buttons WHERE button_id = ?', (button_id,))
        
        # 更新按钮更新时间
        cursor.execute('UPDATE button_updates SET last_update = ? WHERE id = 1', (current_time,))
        
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"删除按钮时出错: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

# 菜单相关函数
def get_all_menus():
    """获取所有菜单"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM menus ORDER BY id')
        menus = cursor.fetchall()
        return menus
    except Exception as e:
        logger.error(f"获取所有菜单时出错: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_menu_by_id(menu_id):
    """通过ID获取菜单"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM menus WHERE id = ?', (menu_id,))
        menu = cursor.fetchone()
        return menu
    except Exception as e:
        logger.error(f"获取菜单信息时出错: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_menu_by_name(name):
    """通过名称获取菜单"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM menus WHERE name = ?', (name,))
        menu = cursor.fetchone()
        return menu
    except Exception as e:
        logger.error(f"通过名称获取菜单时出错: {e}")
        return None
    finally:
        if conn:
            conn.close()

def create_menu(name, title, description=""):
    """创建新菜单"""
    try:
        current_time = int(time.time())
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO menus 
        (name, title, description, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, title, description, 1, current_time, current_time))
        
        # 更新按钮更新时间
        cursor.execute('UPDATE button_updates SET last_update = ? WHERE id = 1', (current_time,))
        
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"创建菜单时出错: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            conn.close()

def update_menu(menu_id, name=None, title=None, description=None, is_active=None):
    """更新菜单信息"""
    try:
        current_time = int(time.time())
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取当前菜单信息
        cursor.execute('SELECT * FROM menus WHERE id = ?', (menu_id,))
        menu = cursor.fetchone()
        
        if not menu:
            return False
        
        # 更新有提供的字段
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        
        if is_active is not None:
            updates.append("is_active = ?")
            params.append(is_active)
        
        updates.append("updated_at = ?")
        params.append(current_time)
        
        # 构建和执行更新查询
        query = f"UPDATE menus SET {', '.join(updates)} WHERE id = ?"
        params.append(menu_id)
        
        cursor.execute(query, params)
        
        # 更新按钮更新时间
        cursor.execute('UPDATE button_updates SET last_update = ? WHERE id = 1', (current_time,))
        
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"更新菜单信息时出错: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def delete_menu(menu_id):
    """删除菜单"""
    try:
        current_time = int(time.time())
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 删除菜单
        cursor.execute('DELETE FROM menus WHERE id = ?', (menu_id,))
        
        # 同时删除菜单-按钮关联
        cursor.execute('DELETE FROM menu_buttons WHERE menu_id = ?', (menu_id,))
        
        # 更新按钮更新时间
        cursor.execute('UPDATE button_updates SET last_update = ? WHERE id = 1', (current_time,))
        
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"删除菜单时出错: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

# 菜单-按钮关联函数
def add_button_to_menu(menu_id, button_id, position=0, row=0):
    """将按钮添加到菜单"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查是否已存在此关联
        cursor.execute('''
        SELECT * FROM menu_buttons WHERE menu_id = ? AND button_id = ?
        ''', (menu_id, button_id))
        
        if cursor.fetchone():
            # 更新现有关联
            cursor.execute('''
            UPDATE menu_buttons SET position = ?, row = ? 
            WHERE menu_id = ? AND button_id = ?
            ''', (position, row, menu_id, button_id))
        else:
            # 创建新关联
            cursor.execute('''
            INSERT INTO menu_buttons (menu_id, button_id, position, row)
            VALUES (?, ?, ?, ?)
            ''', (menu_id, button_id, position, row))
        
        # 更新按钮更新时间
        current_time = int(time.time())
        cursor.execute('UPDATE button_updates SET last_update = ? WHERE id = 1', (current_time,))
        
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"将按钮添加到菜单时出错: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def remove_button_from_menu(menu_id, button_id):
    """从菜单中移除按钮"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        DELETE FROM menu_buttons WHERE menu_id = ? AND button_id = ?
        ''', (menu_id, button_id))
        
        # 更新按钮更新时间
        current_time = int(time.time())
        cursor.execute('UPDATE button_updates SET last_update = ? WHERE id = 1', (current_time,))
        
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"从菜单移除按钮时出错: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def get_menu_buttons(menu_id):
    """获取菜单中的所有按钮"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT b.*, mb.position, mb.row 
        FROM buttons b
        JOIN menu_buttons mb ON b.id = mb.button_id
        WHERE mb.menu_id = ? AND b.is_active = 1
        ORDER BY mb.row, mb.position
        ''', (menu_id,))
        
        buttons = cursor.fetchall()
        return buttons
    except Exception as e:
        logger.error(f"获取菜单按钮时出错: {e}")
        return []
    finally:
        if conn:
            conn.close()

# 按钮更新状态函数
def get_last_button_update_time():
    """获取按钮的最后更新时间"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT last_update FROM button_updates WHERE id = 1')
        result = cursor.fetchone()
        
        if result:
            return result['last_update']
        return 0
    except Exception as e:
        logger.error(f"获取按钮更新时间时出错: {e}")
        return 0
    finally:
        if conn:
            conn.close()

# 初始化数据库
setup_database() 