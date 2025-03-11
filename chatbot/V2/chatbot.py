from flask import Flask, request, abort
from flask_cors import CORS
from linebot.v3.messaging import MessagingApi, Configuration, TextMessage
from linebot.v3.webhook import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent
import os
import threading

# 先僅導入 chat_with_model 函數
from RAG import chat_with_model  

# 定義一個函數來初始化 RAG
def initialize_rag_in_background():
    print("🔄 開始在背景初始化 RAG 系統...")
    from RAG import initialize_rag
    initialize_rag()
    print("✅ RAG 系統初始化完成！")

# 讀取環境變數
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
LINE_SECRET = os.getenv("LINE_SECRET")

# 確保環境變數存在
if not LINE_ACCESS_TOKEN or not LINE_SECRET:
    raise ValueError("❌ 環境變數 `LINE_ACCESS_TOKEN` 或 `LINE_SECRET` 未設定，請確認 Render 設定！")

# 初始化 Flask 應用
app = Flask(__name__)
CORS(app)

# 初始化 LINE Messaging API 和 Webhook Handler
config = Configuration(access_token=LINE_ACCESS_TOKEN)
line_bot_api = MessagingApi(configuration=config)
handler = WebhookHandler(LINE_SECRET)

# 測試 LINE API 連接
def test_line_api():
    try:
        print(f"✅ LINE 憑證設置: TOKEN={LINE_ACCESS_TOKEN[:5]}..., SECRET={LINE_SECRET[:5]}...")
        return True
    except Exception as e:
        print(f"❌ LINE API 連接測試失敗: {e}")
        return False

@app.route("/callback", methods=["POST"])
def callback():
    try:
        signature = request.headers.get("X-Line-Signature", "")
        body = request.get_data(as_text=True)

        # 🔍 Debug: 確認請求內容
        print(f"📥 Received Webhook Request: {body}")
        print(f"🔑 Signature: {signature}")

        if not body:
            print("❌ 錯誤: 收到空的請求 Body！")
            return "Bad Request - Empty Body", 400

        handler.handle(body, signature)
    except InvalidSignatureError:
        print("❌ Invalid Signature Error!")
        return "Invalid Signature", 400
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return "Internal Server Error", 500

    return "OK"

# 確保 `handler` 在這裡定義後，再使用 `@handler.add`
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    try:
        user_id = event.source.user_id
        user_input = event.message.text
        print(f"📨 收到用戶 {user_id} 的訊息: {user_input}")

        # 先發送等待訊息
        try:
            line_bot_api.reply_message(
                event.reply_token,
                [TextMessage(text="Generating your recipe, please wait...")]
            )
            print("✅ 已發送等待訊息")
        except Exception as e:
            print(f"❌ 發送等待訊息失敗: {e}")

        # 使用 RAG 的 chat_with_model 獲取回應
        try:
            response_text = chat_with_model(user_id, user_input)
            print(f"✅ RAG 生成回應: {response_text[:50]}...")
        except Exception as e:
            print(f"❌ RAG 生成回應失敗: {e}")
            response_text = "Sorry, I encountered an error. Please try again later."

        # 確保回應在 LINE 4000 字元限制內
        max_length = 4000
        response_text = response_text[:max_length]

        # 使用 reply_message 發送最終回應
        try:
            line_bot_api.reply_message(
                event.reply_token,
                [TextMessage(text=response_text)]
            )
            print(f"✅ 已發送回應給用戶 {user_id}")
        except Exception as e:
            print(f"❌ 發送回應失敗: {e}")

    except Exception as e:
        print(f"❌ 處理訊息時發生錯誤: {e}")

# 啟動時在背景線程中初始化 RAG
print("🚀 啟動 Flask 應用並在背景初始化 RAG...")
thread = threading.Thread(target=initialize_rag_in_background)
thread.daemon = True
thread.start()

# 測試 LINE API
test_line_api()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"🌐 開始監聽端口 {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)
