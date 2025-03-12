# from flask import Flask, request, abort
# from flask_cors import CORS
# from linebot import LineBotApi, WebhookHandler
# from linebot.exceptions import InvalidSignatureError
# from linebot.models import MessageEvent, TextMessage, TextSendMessage
# import os
# import threading

# # 導入 RAG 相關函數
# from RAG import chat_with_model, initialize_rag

# # 設定 LINE Channel Token & Secret
# LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
# LINE_SECRET = os.getenv("LINE_SECRET")

# # 初始化 Flask 應用
# app = Flask(__name__)
# CORS(app)

# # 設置 LINE Bot API
# line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
# handler = WebhookHandler(LINE_SECRET)

# def initialize_rag_in_background():
#     print("🔄 開始在背景初始化 RAG 系統...")
#     initialize_rag()
#     print("✅ RAG 系統初始化完成！")

# @app.route("/callback", methods=["POST"])
# def callback():
#     signature = request.headers.get("X-Line-Signature", "")
#     body = request.get_data(as_text=True)
    
#     print(f"📥 Received Webhook Request: {body}")
#     print(f"🔑 Signature: {signature}")
    
#     if not body:
#         print("❌ 錯誤: 收到空的請求 Body！")
#         return "Bad Request - Empty Body", 400
    
#     try:
#         handler.handle(body, signature)
#     except InvalidSignatureError:
#         print("❌ Invalid Signature Error!")
#         return "Invalid Signature", 400
#     except Exception as e:
#         print(f"❌ Unexpected Error: {e}")
#         return "Internal Server Error", 500
    
#     return "OK"

# @handler.add(MessageEvent, message=TextMessage)
# def handle_message(event):
#     try:
#         user_id = event.source.user_id
#         user_input = event.message.text
#         print(f"📨 收到用戶 {user_id} 的訊息: {user_input}")
        
#         # 先發送等待訊息
#         try:
#             line_bot_api.reply_message(
#                 event.reply_token,
#                 TextSendMessage(text="Generating your recipe, please wait...")
#             )
#             print("✅ 已發送等待訊息")
#         except Exception as e:
#             print(f"❌ 發送等待訊息失敗: {e}")
        
#         # 使用 RAG 生成回應
#         try:
#             response_text = chat_with_model(user_id, user_input)
#             print(f"✅ RAG 生成回應: {response_text[:50]}...")
#         except Exception as e:
#             print(f"❌ RAG 生成回應失敗: {e}")
#             response_text = "Sorry, I encountered an error. Please try again later."
        
#         # 限制回應長度 (LINE 限制 4000 字元)
#         response_text = response_text[:4000]
        
#         # 發送回應
#         try:
#             line_bot_api.push_message(
#                 user_id,
#                 TextSendMessage(text=response_text)
#             )
#             print(f"✅ 已發送回應給用戶 {user_id}")
#         except Exception as e:
#             print(f"❌ 發送回應失敗: {e}")
        
#     except Exception as e:
#         print(f"❌ 處理訊息時發生錯誤: {e}")

# # 背景初始化 RAG
# print("🚀 啟動 Flask 應用並在背景初始化 RAG...")
# thread = threading.Thread(target=initialize_rag_in_background)
# thread.daemon = True
# thread.start()

# if __name__ == "__main__":
#     port = int(os.environ.get("PORT", 8080))
#     print(f"🌐 開始監聽端口 {port}...")
#     app.run(host="0.0.0.0", port=port, debug=False)

from flask import Flask, request, abort, jsonify
from flask_cors import CORS
from linebot.v3.messaging import MessagingApi, TextMessage
from linebot.v3.webhook import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent
import os
import threading

from RAG import chat_with_model

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# LINE API Configuration
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
LINE_SECRET = os.getenv("LINE_SECRET")

# Store user preferences (Can be replaced with Firebase)
user_preferences = {}

# Initialize RAG in background
def initialize_rag_in_background():
    print("🔄 Initializing RAG system in the background...")
    from RAG import initialize_rag
    initialize_rag()
    print("✅ RAG system initialized successfully!")

# Test LINE API connection
def test_line_api():
    try:
        print(f"✅ LINE credentials set: TOKEN={LINE_ACCESS_TOKEN[:5]}..., SECRET={LINE_SECRET[:5]}...")
        return True
    except Exception as e:
        print(f"❌ Failed to connect to LINE API: {e}")
        return False

@app.route("/callback", methods=["POST"])
def callback():
    try:
        signature = request.headers.get("X-Line-Signature", "")
        body = request.get_data(as_text=True)

        print(f"📥 Received Webhook Request: {body}")
        print(f"🔑 Signature: {signature}")

        if not body:
            print("❌ Error: Received an empty request body!")
            return "Bad Request - Empty Body", 400

        handler.handle(body, signature)
    except InvalidSignatureError:
        print("❌ Invalid Signature Error!")
        return "Invalid Signature", 400
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return "Internal Server Error", 500

    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    try:
        user_id = event.source.user_id
        user_input = event.message.text.lower().strip()
        print(f"📨 Received message from user {user_id}: {user_input}")

        # **If the user enters "change preference", ask for new dietary preference**
        if user_input in ["change preference", "modify diet", "update preference"]:
            user_preferences[user_id] = None  # Reset preference
            response_text = "Please enter your new dietary preferences (e.g., 'I am vegetarian' or 'I avoid beef and pork')."
        
        # **If the user has no preference stored, ask for their preference**
        elif user_id not in user_preferences or user_preferences[user_id] is None:
            user_preferences[user_id] = user_input  # Store user preference
            response_text = f"Thanks! I've noted your dietary preferences: {user_input}. Now you can ask for recipe recommendations!"
        
        # **If the user has a preference, generate a recipe**
        else:
            preference = user_preferences[user_id]
            response_text = f"Thanks for your message! We will recommend a recipe for you based on your preference: {preference}.\n\nGenerating your recipe, please wait..."
            try:
                recipe = chat_with_model(user_id, user_input)  # Call RAG for recipe generation
                response_text += f"\n\n{recipe}"
            except Exception as e:
                print(f"❌ Failed to generate response using RAG: {e}")
                response_text += "\n\nSorry, I encountered an error while generating your recipe."

        # **Send response to user**
        try:
            line_bot_api.reply_message(event.reply_token, TextMessage(text=response_text))
            print(f"✅ Response sent to user {user_id}")
        except Exception as e:
            print(f"❌ Failed to send response: {e}")
            
    except Exception as e:
        print(f"❌ Error while processing message: {e}")

# Start background RAG initialization
print("🚀 Starting Flask application and initializing RAG in the background...")
thread = threading.Thread(target=initialize_rag_in_background)
thread.daemon = True
thread.start()

# Test LINE API
test_line_api()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"🌐 Listening on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)
