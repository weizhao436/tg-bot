#!/usr/bin/env python3
"""
最简单的修复脚本 - 直接在if __name__前插入except块
"""
import os

def simple_fix():
    print("执行简单修复...")
    
    bot_file = "bot.py"
    if not os.path.exists(bot_file):
        print(f"错误: 找不到 {bot_file} 文件")
        return False
    
    # 创建备份
    backup_file = f"{bot_file}.simple.bak"
    os.system(f"cp {bot_file} {backup_file}")
    print(f"已创建备份: {backup_file}")
    
    # 读取文件内容
    with open(bot_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 找到 if __name__ 行
    if_name_pos = content.find("if __name__ == '__main__':")
    if if_name_pos == -1:
        print("未找到 if __name__ 行")
        return False
    
    # 在 if __name__ 行前插入缺失的except块
    fixed_content = content[:if_name_pos] + "\nexcept Exception as e:\n    print(f\"未处理的异常: {e}\")\n    import traceback\n    traceback.print_exc()\n\n" + content[if_name_pos:]
    
    # 保存修复后的文件
    with open(bot_file, 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    print("✅ 已插入缺失的except块")
    return True

if __name__ == "__main__":
    if simple_fix():
        print("修复完成，请尝试重新运行bot.py")
    else:
        print("修复失败") 