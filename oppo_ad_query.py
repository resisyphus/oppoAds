import requests # type: ignore
import json
import time
import hmac
import hashlib
import random
from urllib.parse import urlencode
from playsound import playsound
import time
from datetime import datetime
import os
import sys
import random
from rich import print
from oppo_ad_config import APP_LIST #从外部文件读取应用列表信息

API_DOMAIN = "https://openapi.heytapmobi.com"


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
            print(f"获取access_token出错: {str(e)}")
            return None


    def media_query(self, app_name):
        """创建广告位"""
        if not self.get_access_token():
            return {"code": -1, "message": "获取access_token失败"}

        url = "https://openapi.heytapmobi.com/union/v1/app/list"
        timestamp = str(int(time.time() * 1000))
        nonce = str(random.randint(0, 20000))

        params = {
            "page": 1,
            "rows":10,
            "searchingWord":app_name
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
            # print(response.json())

            result_json = response.json().get('data', {}).get('items', [])
            # print(result_json)
            if result_json != []:
                for item in result_json:
                    name = item.get('mediaName')
                    status = item.get('unionStatus')
                    if status == 4:
                        status = '【冻结】'
                    elif status == 2:
                        status = '正常'
                    else:
                        status = '没找到'
                    result=f"{name}:{status}"
                    if "冻结" in result:
                        print(f"[red bold]result[/]")
                    else:
                        print(result)
                    return(result)
            else:
                print(f'{app_name}:没找到')

        except requests.exceptions.RequestException as e:
            return {"code": -1, "message": str(e)}

def play_sound(file_path):
    
    try:
        playsound(file_path)
    except Exception as e:
        print(f"播放失败: {e}")

def main():

    text=[]
    

    for t in range(100000): 

        new=[] #初始化本轮的结果

        now = datetime.now()
        print("当前时间是：", now.strftime("%Y-%m-%d %H:%M:%S"))

        for i in APP_LIST:
            app_info=APP_LIST[i]
            
            api = OppoAdAPI(app_info["CLIENT_ID"],app_info["CLIENT_SECRET"], app_info["MEDIA_ID"])
            new.append(api.media_query(app_info["APP_NAME"]))

            time.sleep(random.uniform(0.1,0.6)) 
        
        # print(f"这是text：{text}")
        # print(f"这是new：{new}")

        # if new != text: #比较本轮的结果和上一轮的结果，如果有变化，那么提示
        #     print("【有新变化，请注意！】")
        #     play_sound("asasd/y2080.mp3") #提醒声音的地址

        # text = new #将本轮的结果存下来


        duration=15 #下次查询的分钟数

        for ti in range(duration*60):
            time.sleep(1)
            print(f'距离下次查询还有{duration*60 - ti-1}秒', end="\r")
            sys.stdout.flush()

        print("\n")


    
if __name__ == "__main__":
    main()