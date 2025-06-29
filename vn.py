from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    ReplyMessageRequest, TextMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from dotenv import load_dotenv
import os
import requests

# 載入 .env 環境變數
load_dotenv()
app = Flask(__name__)

# LINE Bot 設定
configuration = Configuration(access_token=os.getenv('CHANNEL_ACCESS_TOKEN'))
line_handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# 翻譯函數
def translate_text(text, target_lang):
    url = "https://translation.googleapis.com/language/translate/v2"
    params = {
        'q': text,
        'target': target_lang,
        'format': 'text',
        'key': GOOGLE_API_KEY
    }
    res = requests.post(url, data=params)
    return res.json()['data']['translations'][0]['translatedText']

# 語言偵測函數
def detect_language(text):
    url = "https://translation.googleapis.com/language/translate/v2/detect"
    params = {
        'q': text,
        'key': GOOGLE_API_KEY
    }
    res = requests.post(url, data=params)
    return res.json()['data']['detections'][0][0]['language']

# 處理 LINE 訊息事件
@line_handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_text = event.message.text
    source_lang = detect_language(user_text)

    # 只處理中文與泰文的互譯
    if source_lang.startswith("zh"):
        target_langs = ['vi']
    elif source_lang == 'vi':
        target_langs = ['zh-TW']
    else:
        return  # 其他語言不回應

    # 執行翻譯並準備回覆訊息
    reply_lines = []
    for tgt in target_langs:
        translated = translate_text(user_text, tgt)
        flag = {
            'zh-TW': "🇹🇼",
            'zh-CN': "🇹🇼",
            'vi': "vn"
        }.get(tgt, "")
        reply_lines.append(f"{flag} : {translated}")
    reply = "\n".join(reply_lines)

    # 使用 quote_token 回覆引用訊息
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TextMessage(
                        text=reply,
                        quote_token=event.message.quote_token
                    )
                ]
            )
        )

# LINE webhook 路由
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

if __name__ == "__main__":
    app.run()
