import os
  import json
  import requests
  from datetime import datetime, timedelta, timezone

  APP_ID = os.environ["FEISHU_APP_ID"]
  APP_SECRET = os.environ["FEISHU_APP_SECRET"]
  CHAT_ID = "oc_84d26d69383c3822d4be403c673653a2"
  DOC_URL = "https://iairnznqr8.feishu.cn/wiki/TgsTwqh4ZiP3qFkxhqWcx2uCnN2"

  tz = timezone(timedelta(hours=8))
  now = datetime.now(tz)
  yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")

  r = requests.post(
      "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
      json={"app_id": APP_ID, "app_secret": APP_SECRET}
  )
  token = r.json()["tenant_access_token"]

  content = {
      "post": {
          "zh_cn": {
              "title": "✅ 广告永封同步任务完成",
              "content": [[
                  {"tag": "text", "text": f"数据日期：{yesterday}\n"},
                  {"tag": "text", "text": f"完成时间：{now.strftime('%Y-%m-%d %H:%M:%S')}\n"},
                  {"tag": "text", "text": "查看文档："},
                  {"tag": "a", "text": "点击跳转飞书文档", "href": DOC_URL}
              ]]
          }
      }
  }

  requests.post(
      "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
      headers={"Authorization": f"Bearer {token}"},
      json={"receive_id": CHAT_ID, "msg_type": "post", "content": json.dumps(content["post"])}
  )
  print("发送成功")
