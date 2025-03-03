#!/usr/bin/env python3
"""
这个脚本用于修复config.py中的循环导入问题
"""
import os
import sys

def fix_config_file(config_path):
    print(f"正在修复配置文件: {config_path}")
    if not os.path.exists(config_path):
        print(f"错误: 配置文件不存在: {config_path}")
        return False
    
    # 读取原始配置文件
    with open(config_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 寻找并移除循环导入
    found_import = False
    fixed_lines = []
    for line in lines:
        if "from config import DB_PATH" in line:
            found_import = True
            fixed_lines.append("# 已移除循环导入: from config import DB_PATH\n")
        else:
            fixed_lines.append(line)
    
    if not found_import:
        print("未发现循环导入问题，无需修复")
        return False
    
    # 创建备份
    backup_path = f"{config_path}.bak"
    print(f"创建备份文件: {backup_path}")
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    # 写入修复后的文件
    with open(config_path, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    
    print("配置文件已成功修复")
    return True

if __name__ == "__main__":
    # 默认路径
    default_paths = [
        "./config.py",
        "/opt/tg-bot/config.py"
    ]
    
    if len(sys.argv) > 1:
        # 使用用户提供的路径
        success = fix_config_file(sys.argv[1])
    else:
        # 尝试所有默认路径
        success = False
        for path in default_paths:
            if os.path.exists(path):
                if fix_config_file(path):
                    success = True
                    break
        
        if not success:
            print(f"错误: 未能找到配置文件。请提供正确的配置文件路径作为参数。")
            print(f"用法: {sys.argv[0]} [配置文件路径]")
            sys.exit(1) 