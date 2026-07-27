import os
import json
import requests
from datetime import datetime, timedelta, timezone

APP_ID = os.environ["FEISHU_APP_ID"]
APP_SECRET = os.environ["FEISHU_APP_SECRET"]
SOURCE_CHAT_ID = "oc_770b3e4347e43cabd389f545a7980f4b"
SHEET_TOKEN = "KQfwsq9FwhCpxBtvLNWcJOhnn3e"
SHEET_ID = "e373f2"

START_DATE = "2026-07-23"
END_DATE = "2026-07-25"

tz = timezone(timedelta(hours=8))
print(f"[INFO] 回填日期范围: {START_DATE} 至 {END_DATE}")

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
        if last_dt.strftime("%Y-%m-%d") < START_DATE:
            break
    if not resp.get("data", {}).get("has_more"):
        break
    page_token = resp["data"]["page_token"]

print(f"[INFO] 共读取 {len(all_items)} 条消息")

records_by_date = {}
for item in all_items:
    ts = int(item["create_time"]) / 1000
    dt = datetime.fromtimestamp(ts, tz)
    date_str = dt.strftime("%Y-%m-%d")
    if date_str < START_DATE or date_str > END_DATE:
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
        if date_str not in records_by_date:
            records_by_date[date_str] = []
        records_by_date[date_str].append([dt.strftime("%Y-%m-%d %H:%M:%S"), username, user_url])

for date_str in sorted(records_by_date.keys()):
    records = sorted(records_by_date[date_str], key=lambda x: x[0])
    print(f"[INFO] {date_str}: {len(records)} 条记录")
    if not records:
        continue
    resp = requests.get(
        f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{SHEET_TOKEN}/values/{SHEET_ID}!A2:A9999",
        headers=headers
    )
    sheet_data = resp.json()
    if sheet_data.get("code", 0) != 0:
        print(f"[ERROR] {date_str}: 读取表格失败: {sheet_data}")
        continue
    rows = sheet_data.get("data", {}).get("valueRange", {}).get("values") or []
    last_row = 1
    for i, row in enumerate(rows):
        if row and row[0]:
            last_row = i + 2
    next_row = last_row + 1
    print(f"[INFO] {date_str}: 当前最后行={last_row}, 写入起始行={next_row}")
    range_str = f"{SHEET_ID}!A{next_row}:C{next_row + len(records) - 1}"
    write_resp = requests.put(
        f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{SHEET_TOKEN}/values",
        headers=headers,
        json={"valueRange": {"range": range_str, "values": records}}
    )
    write_data = write_resp.json()
    if write_data.get("code", 0) != 0:
        print(f"[ERROR] {date_str}: 写入失败: {write_data}")
    else:
        print(f"[INFO] {date_str}: 写入成功 {len(records)} 条，范围: {range_str}")

print("[INFO] 回填完成")
