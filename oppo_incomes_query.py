import requests # type: ignore
import json
import time
import hmac
import hashlib
import random
from urllib.parse import urlencode
import time
from datetime import datetime, timedelta
import random
import sys
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

    def app_query(self,day):

        if not self.get_access_token():
            return {"code": -1, "message": "获取access_token失败"}

        url = "https://openapi.heytapmobi.com/union/api/report/appQuery"
        timestamp = str(int(time.time() * 1000))
        nonce = str(random.randint(0, 20000))

        yesterday = datetime.now() - timedelta(days=day) #计算日期，1是昨天，2就是前天

        params = {
            "startTime": yesterday.strftime('%Y%m%d'),
            "endTime": yesterday.strftime('%Y%m%d'),
            "timeGranularity":"day"
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
            return response.json(), yesterday.strftime('%Y-%m-%d')
        
        except requests.exceptions.RequestException as e:
            return {"code": -1, "message": str(e)}, yesterday.strftime('%Y-%m-%d')
        
def income(day):
    all_income=0
    unique_company_apps = {}
    seen_companies = set()

    # APP_LIST是以应用为维度维护的，在这里按公司去重
    for app_id, app_info in APP_LIST.items():
        company = app_info['COMPANY']
        if company not in seen_companies:
            unique_company_apps[app_id] = app_info
            seen_companies.add(company)
    # print(unique_company_apps)
    
    # 这里获取所有应用的名称
    app_lsit = [app_info['APP_NAME'] for app_info in APP_LIST.values()]
    # print(app_lsit)

    for i in unique_company_apps:

        # 先按每个公司来查询数据
        app_info=unique_company_apps[i]
        api = OppoAdAPI(app_info["CLIENT_ID"],app_info["CLIENT_SECRET"], app_info["MEDIA_ID"])
        json_data,day_date = api.app_query(day)#调取查询接口，同时传入是查最近几天的
        # print(json_data)

        #从返回的信息中筛选出在APP_LIST中的应用的收入
        for item in json_data['data']:
            # print(item)
            if item.get('biddingType') in [2, None]: #当有bidding和标准时只获取标准竞价的收入，当两种不分的时候就不算
                if item.get('appName') in app_lsit:
                    app_name = item.get('appName')
                    income = item.get('income')
                    all_income+=float(income)
                    ecpm = item.get('ecpm')
                    print(f'{app_name}: 收入={income:,}, ecpm={ecpm}')
    return all_income, day_date

def progress_bar(duration, steps=60):
    #自定义样式的进度条
    step_duration = duration / steps
    
    for i in range(steps + 1):
        # 计算百分比
        percent = (i / steps) * 100
        # 创建进度条字符串
        bar = "[" + "█" * i + " " * (steps - i) + "]"
        # 打印进度条和百分比
        sys.stdout.write(f"\r{bar} {percent:.1f}%")
        sys.stdout.flush()
        if i < steps:
            time.sleep(step_duration)

def main():

    day=1 #获取最近几天的，1就是昨天，3就是之前3天的

    for i in range(100): #尝试多次获取数据

        for d in range(day):
            incomes, day_date=income(day-d)
            print(f'\n{day_date} 总收入为：{incomes:,}\n') 

        if int(incomes) > 0: #如果已经获取到收入则直接退出循环
                break
          
        progress_bar(300) 

if __name__ == "__main__":
    main()