import os
import json
import requests
from datetime import datetime, timedelta, timezone

APP_ID = os.environ["FEISHU_APP_ID"]
APP_SECRET = os.environ["FEISHU_APP_SECRET"]
CHAT_IDS = [
    "oc_8986e681faa16d91676aaff14a9ecd61",
    "oc_6522503b874f4ec811241613e24f06b0",
]
SOURCE_CHAT_ID = "oc_770b3e4347e43cabd389f545a7980f4b"
SHEET_TOKEN = "KQfwsq9FwhCpxBtvLNWcJOhnn3e"
SHEET_ID = "e373f2"
DOC_URL = "https://iairnznqr8.feishu.cn/wiki/TgsTwqh4ZiP3qFkxhqWcx2uCnN2"

tz = timezone(timedelta(hours=8))
now = datetime.now(tz)
yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
print(f"[INFO] 目标日期: {yesterday}")

r = requests.post(
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    json={"app_id": APP_ID, "app_secret": APP_SECRET}
)
token_data = r.json()
if "tenant_access_token" not in token_data:
    print(f"[ERROR] 获取token失败: {token_data}")
    exit(1)
access_token = token_data["tenant_access_token"]
headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
print("[INFO] token获取成功")

all_items = []
page_token = ""
page_count = 0
while True:
    url = (
        f"https://open.feishu.cn/open-apis/im/v1/messages"
        f"?container_id_type=chat&container_id={SOURCE_CHAT_ID}"
        f"&page_size=50&sort_type=ByCreateTimeDesc"
    )
    if page_token:
        url += f"&page_token={page_token}"
    resp = requests.get(url, headers=headers).json()

    if resp.get("code", 0) != 0:
        print(f"[ERROR] 读取消息失败: code={resp.get('code')}, msg={resp.get('msg')}")
        break

    items = resp.get("data", {}).get("items", [])
    page_count += 1
    print(f"[INFO] 第{page_count}页: {len(items)} 条消息")
    all_items.extend(items)

    if items:
        last_ts = int(items[-1]["create_time"]) / 1000
        last_dt = datetime.fromtimestamp(last_ts, tz)
        if last_dt.strftime("%Y-%m-%d") < yesterday:
            break
    if not resp.get("data", {}).get("has_more"):
        break
    page_token = resp["data"]["page_token"]

print(f"[INFO] 共读取 {len(all_items)} 条消息")

records = []
for item in all_items:
    ts = int(item["create_time"]) / 1000
    dt = datetime.fromtimestamp(ts, tz)
    if dt.strftime("%Y-%m-%d") != yesterday:
        continue
    content = json.loads(item.get("body", {}).get("content", "{}"))
    text = content.get("text", "")
    if "永封报警" in text and "命中策略：发布广告" in text:
        username = ""
        user_url = ""
        for line in text.split("\n"):
            if line.startswith("用户名："):
                username = line.replace("用户名：", "")
            if line.startswith("用户主页地址："):
                user_url = line.replace("用户主页地址：", "")
        records.append([dt.strftime("%Y-%m-%d %H:%M:%S"), username, user_url])

records.sort(key=lambda x: x[0])
print(f"[INFO] 昨日({yesterday})因广告永封: {len(records)} 条")

if records:
    write_resp = requests.post(
        f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{SHEET_TOKEN}/values_append?insertDataOption=INSERT_ROWS",
        headers=headers,
        json={"valueRange": {"range": f"{SHEET_ID}!A:C", "values": records}}
    )
    write_data = write_resp.json()
    if write_data.get("code", 0) != 0:
        print(f"[ERROR] 写入表格失败: {write_data}")
        exit(1)
    print(f"[INFO] 写入表格成功: {len(records)} 条")

finish_time = now.strftime("%Y-%m-%d %H:%M:%S")
post_content = {
    "zh_cn": {
        "title": "✅ 广告永封同步任务完成",
        "content": [
            [{"tag": "text", "text": f"数据日期：{yesterday}\n"}],
            [{"tag": "text", "text": f"同步条数：{len(records)} 条\n"}],
            [{"tag": "text", "text": f"完成时间：{finish_time}\n"}],
            [{"tag": "text", "text": "查看文档："}, {"tag": "a", "text": "点击跳转飞书文档", "href": DOC_URL}]
        ]
    }
}

for chat_id in CHAT_IDS:
    resp = requests.post(
        "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
        headers=headers,
        json={"receive_id": chat_id, "msg_type": "post", "content": json.dumps(post_content)}
    )
    print(f"[INFO] 通知发送({chat_id[:20]}...): {resp.json().get('msg')}")
