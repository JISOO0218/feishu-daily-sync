import os
import json
import requests
from datetime import datetime, timedelta, timezone

APP_ID = os.environ["FEISHU_APP_ID"]
APP_SECRET = os.environ["FEISHU_APP_SECRET"]
CHAT_ID = "oc_8986e681faa16d91676aaff14a9ecd61"
SHEET_TOKEN = "KQfwsq9FwhCpxBtvLNWcJOhnn3e"
SHEET_ID = "e373f2"
DOC_URL = "https://iairnznqr8.feishu.cn/wiki/TgsTwqh4ZiP3qFkxhqWcx2uCnN2"

tz = timezone(timedelta(hours=8))
now = datetime.now(tz)
yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")

r = requests.post(
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    json={"app_id": APP_ID, "app_secret": APP_SECRET}
)
token = r.json()["tenant_access_token"]
headers = {"Authorization": f"Bearer {token}"}

resp = requests.get(
    f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{SHEET_TOKEN}/values/{SHEET_ID}!A2:C1000",
    headers=headers
)
rows = resp.json()["data"]["valueRange"]["values"]
records = [r for r in rows if r and r[0] and str(r[0]).startswith(yesterday)]

lines = [[
    {"tag": "text", "text": f"{'封禁时间':^25}{'用户名':^20}{'用户主页地址':^30}
"}
]]
if records:
    for rec in records:
        t = str(rec[0]) if len(rec) > 0 and rec[0] else ""
        u = str(rec[1]) if len(rec) > 1 and rec[1] else ""
        link = str(rec[2]) if len(rec) > 2 and rec[2] else ""
        lines.append([
            {"tag": "text", "text": f"{t:^25}{u:^20}"},
            {"tag": "a", "text": f"{link:^30}", "href": link}
        ])
else:
    lines.append([{"tag": "text", "text": "昨日暂无永封记录"}])

content_body = {
    "zh_cn": {
        "title": f"✅ {yesterday} 广告永封同步完成",
        "content": lines
    }
}

requests.post(
    "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
    headers=headers,
    json={
        "receive_id": CHAT_ID,
        "msg_type": "post",
        "content": json.dumps({"post": content_body})
    }
)
print(f"发送成功，共 {len(records)} 条记录")
