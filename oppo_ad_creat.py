import importlib
import importlib.util
import sys
import os
import ast

def get_imported_modules(file_path):
    """解析Python文件，获取所有import的库"""
    with open(file_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=file_path)

    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split('.')[0])  # 只取最外层库名
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.add(node.module.split('.')[0])
    return modules

def modules_check():
    # 当前脚本路径
    script_path = os.path.abspath(__file__)

    # 获取当前脚本中引用的库
    imported_modules = get_imported_modules(script_path)

    # 检查这些库是否安装
    missing_libs = []
    for lib in imported_modules:
        if importlib.util.find_spec(lib) is None:
            missing_libs.append(lib)

    if missing_libs:
        print("运行失败！以下库未安装：", ", ".join(missing_libs))
        sys.exit(1)

modules_check()

import requests # type: ignore
import json
import time
import hmac
import hashlib
import random
from urllib.parse import urlencode
from rich import print
from rich.panel import Panel
from rich.console import Console
from rich.highlighter import NullHighlighter
from oppo_ad_config import APP_LIST #从外部文件读取应用列表信息

console = Console(highlighter=NullHighlighter())

API_DOMAIN = "https://openapi.heytapmobi.com"


# 广告位配置模板
AD_SLOT_TEMPLATES = {
    1: {
        'name': '原生-固定价',
        'type':'原生',
        'config': {
            'posScene': 4, #4原生、
            'devCrtType': '19', #固定数字
            'adMultiDevCrtTypes': '100,6,7,8,11,47,46', #选自渲染原生就固定这些
            'renderMode': 3, #自渲染2.0选择3
            'targetPriceOpen': 1, #1表示要设置目标价，0时关闭
            # 'biddingPattern': 0 #0标准竞价，1实时竞价
        }
    },
    2: {
        'name': '原生-bidding',
        'type':'原生',
        'config': {
            'posScene': 4, #4原生、
            'devCrtType': '19', #固定数字
            'adMultiDevCrtTypes': '100,6,7,8,11,47,46', #选自渲染原生就固定这些
            'renderMode': 3, #自渲染2.0选择3
            'targetPriceOpen': 0, #1表示要设置目标价，0时关闭
            'biddingPattern': 1 #0标准竞价，1实时竞价
        }
    },
    3: {
        'name': '激励-固定价',
        'type':'激励',
        'config': {
            'posScene': 5, #5激励视频
            'devCrtType': '45', #固定数字
            'videoPlayDirection':2, #1横屏，2竖屏
            'openVoiceStyle':0, #0关闭声音，1开启声音
            'multiEndPageStyles':3, #触发类型，3指全部都勾选
            'targetPriceOpen':1, #1表示要设置目标价。0时关闭
            # 'biddingPattern': 0 #0标准竞价，1实时竞价
        }
    },
    4: {
        'name': '激励-bidding',
        'type':'激励',
        'config': {
            'posScene': 5, #5激励视频
            'devCrtType': '45', #固定数字
            'videoPlayDirection':2, #1横屏，2竖屏
            'openVoiceStyle':0, #0关闭声音，1开启声音
            'multiEndPageStyles':3, #触发类型，3指全部都勾选
            'targetPriceOpen':0, #1表示要设置目标价。0时关闭
            'biddingPattern': 1 #0标准竞价，1实时竞价
        }
    }
}




class OppoAdAPI:
    def __init__(self, client_id, client_secret, media_id):
        self.client_id = client_id
        self.client_secret = client_secret
        self.media_id = media_id
        self.access_token = None
        self.token_expire_time = 0

    def _generate_signature(self, access_token, timestamp, nonce, params):
        """签名生成算法"""
        sorted_params = sorted((k, v) for k, v in params.items() if v is not None)
        param_str = '&'.join(f"{k}={v}" for k, v in sorted_params)
        base_str = f"access_token={access_token}&timestamp={timestamp}&nonce={nonce}"
        if param_str:
            base_str += f"&{param_str}"
        signature = hmac.new(
            self.client_secret.encode('utf-8'),
            base_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def get_access_token(self):
        """获取access_token"""
        if self.access_token and time.time() < self.token_expire_time:
            return self.access_token

        url = f"{API_DOMAIN}/oauth2/v1/token"
        params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") == 0:
                self.access_token = result["data"]["access_token"]
                self.token_expire_time = time.time() + result["data"]["expire_in"] - 300
                return self.access_token
            else:
                raise Exception(f"获取token失败: {result.get('message')}")
        except Exception as e:
            print(f"[red bold]获取access_token出错: {str(e)}")
            return None

    def create_ad_slot(self, slot_data):
        """创建广告位"""
        if not self.get_access_token():
            return {"code": -1, "message": "获取access_token失败"}

        url = f"{API_DOMAIN}/union/v1/order/create"
        timestamp = str(int(time.time() * 1000))
        nonce = str(random.randint(0, 20000))

        params = {
            #特殊情况处理：如果获取不到那么为“”，然后再删掉为空的项目
            k: v for k, v in {
            "appId": self.media_id,
            "devCrtType": slot_data["devCrtType"],
            "posName": slot_data["posName"],
            "posScene": slot_data["posScene"],
            "renderMode": slot_data.get("renderMode", ""),
            "biddingPattern": slot_data.get("biddingPattern", ""),
            "targetPriceOpen": slot_data.get("targetPriceOpen", ""),
            "adMultiDevCrtTypes": slot_data.get("adMultiDevCrtTypes", ""),
            "videoPlayDirection":slot_data.get("videoPlayDirection", ""),
            "openVoiceStyle":slot_data.get("openVoiceStyle", ""),
            "multiEndPageStyles":slot_data.get("multiEndPageStyles", ""),
            "targetPrice": slot_data.get("targetPrice", 0)
            }.items() if v != ""
        }

        sign = self._generate_signature(
            access_token=self.access_token,
            timestamp=timestamp,
            nonce=nonce,
            params=params
        )

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"{self.access_token}",
            "X-Client-Send-Utc-Ms": timestamp,
            "X-Nonce": nonce,
            "X-Api-Sign": sign
        }

        sorted_params = sorted(params.items(), key=lambda x: x[0])
        form_data = urlencode(sorted_params)

        try:
            response = requests.post(
                url,
                headers=headers,
                data=form_data,
                timeout=15
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"code": -1, "message": str(e)}

def select_template():
    """选择广告位模板"""
    print("[bold]请选择广告位模板：")
    for k, v in AD_SLOT_TEMPLATES.items():
        print(f"[blue bold]{k}.[/] {v['name']}")
    
    while True:
        try:
            choice = int(input("请输入模板编号: "))
            if choice in AD_SLOT_TEMPLATES:
                return AD_SLOT_TEMPLATES[choice]
            print("[red]无效的选择，请重新输入")
        except ValueError:
            print("[red]请输入有效的数字")

def select_app():
    """选择应用"""
    print("[bold]请选择应用：")
    for k, v in APP_LIST.items():
        print(f"[blue bold]{k}.[/] {v['APP_NAME']}")
    
    while True:
        try:
            choice = int(input("请输入应用编号: "))
            if choice in APP_LIST:
                return APP_LIST[choice]
            print("[red]无效的选择，请重新输入")
        except ValueError:
            print("[red]请输入有效的数字")

def generate_ad_name(app_name, base_name, target_price_title, ad_type, index):
    """生成广告位名称，规则是【应用名】-【基础名称】-【类型（原生时不展示）】-【保价】-【序号】"""
    if ad_type!="原生":
        return f"{app_name}-{base_name}-{ad_type}-{target_price_title}-{index}"
    else:
        return f"{app_name}-{base_name}-{target_price_title}-{index}"
    
def creat_ads(template, app_name, base_name, api):
    
    #初始化
    all_output=[] 
    target_price = '' 

    #当非bidding才需要输入目标价
    if "bidding" not in template['name']:

        target_price = input("请输入目标价格(元): ")
        if target_price == 't': #从价格输入接收t的结果，并接直接返回，并告知400
            return 400
        target_price=int(target_price)

    
    count = input("请输入要创建的广告位数量: ")
    if count == 't': #从数量输入接收t的结果，并接直接返回，并告知400；因bidding广告只需输入数量，所以在数量这里也做收口
        return 400
    count = int(count)
    
    start_index=1 #开始的序号

    success_count = 0
    for i in range(start_index, count + start_index):
        # 生成广告位配置
        ad_slot = template['config'].copy()

        #当为bidding广告时，target_price输入为空，那么就将命名中的目标价改为bidding
        target_price_title  = target_price
        if target_price=="":
            target_price_title = 'bidding'
            # print("[red]变量为空或假值")

        ad_slot['posName'] = generate_ad_name(app_name, base_name, target_price_title, template['type'], i)

        if target_price!="":
            ad_slot['targetPriceOpen'] = 1 if target_price > 0 else 0
        ad_slot['targetPrice'] = target_price

        # print(f"\n正在创建广告位 {i}/{count}...")
        result = api.create_ad_slot(ad_slot)
        # print(result)
        
        if result and result.get("code") == 0:
            output = f"[blue]{result.get('data', {}).get('posId')}[/],{ad_slot['posName']},[green]{target_price_title}[/]"
            all_output.append(output)
            print(output) #打印结果格式：广告位id、名称、保价
            success_count += 1
        else:
            print(f"[red]创建失败：{ad_slot['posName']}")
            print(f"[red]{result}") #打印错误信息

    print(f"\n成功创建 {success_count}/{count} 个广告位\n")
    
    return all_output    

    

def main():

    print(Panel("[red]* 依次选择或输入“应用-广告类型-名称-保价-数量”创建广告\n* 广告位名称规则：应用名称-基础名称-保价-序号\n* 保价或数量输入“t”可退出创建，并输出本次所有创建的广告信息", title="欢迎使用oppo广告创建脚本"))

    #选择应用配置
    app_info=select_app()
    print(f'【已选择{app_info["APP_NAME"]}】')
    
    api = OppoAdAPI(app_info["CLIENT_ID"],app_info["CLIENT_SECRET"], app_info["MEDIA_ID"])
    
    # 选择广告位模板
    template = select_template()
    console.print(f'【已选择{template["name"]}】')
    # template= AD_SLOT_TEMPLATES[1]

    base_name = input("请输入广告位基础名称: ")

    all_output=[]

    for _ in range(100):
       
       ads_output=creat_ads(template, app_info["APP_NAME"], base_name, api)
       
       #如果输入了t，那么函数会收到400的消息，那么就打印所有收到的结果，退出循环；否则就加入列表，继续循环
       if ads_output == 400:
           print("")
           print("所有广告位：")
           for item in all_output:
               print(item)
           break
       else:
        all_output.extend(ads_output) #ads_output返回的是列表，extend方法将其接在all_output后面，而不是append。append是将ads_output整个作为元素塞到all_output里
        

if __name__ == "__main__":
    main()