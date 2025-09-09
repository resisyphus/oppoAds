#oppo广告相关脚本的选择器

import subprocess
import sys
from rich import print

# 定义字典
fun_list = {
    "广告创建": "oppo_ad_creat.py",
    "媒体状态查询": "oppo_ad_query.py",
    "收入查询": "oppo_incomes_query.py"
}

file_path='xxx/oppo_Ad/' #脚本的目录

def run_script():
    while True:
        # 显示功能列表
        print("\n请选择你要执行的脚本：")
        for index, key in enumerate(fun_list.keys(), start=1):
            print(f"[blue]{index}. {key}")
        print(f"[blue]{len(fun_list) + 1}. 退出")

        # 获取用户选择
        try:
            choice = int(input("请输入对应数字选择："))
            if 1 <= choice <= len(fun_list):
                selected_function = list(fun_list.values())[choice - 1]
                print(f"你选择了：{list(fun_list.keys())[choice - 1]}")
                # 执行选中的脚本
                subprocess.run([sys.executable, file_path+selected_function])
            elif choice == len(fun_list) + 1:
                print("退出程序")
                break
            else:
                print("无效的选择，请输入有效数字！")
        except ValueError:
            print("请输入一个有效的数字！")

# 调用函数
run_script()