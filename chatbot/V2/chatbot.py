# from flask import Flask, request, abort
# from flask_cors import CORS
# from linebot import LineBotApi, WebhookHandler
# from linebot.exceptions import InvalidSignatureError
# from linebot.models import MessageEvent, TextMessage, TextSendMessage
# import os
# import threading
# import firebase_admin
# from firebase_admin import credentials, firestore
# import json
# import ast  # ✅ 確保 JSON 解析不出錯

# # 🔥 導入 RAG 相關函數
# from RAG import chat_with_model, initialize_rag

# # ✅ 設定 LINE Channel Token & Secret
# LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
# LINE_SECRET = os.getenv("LINE_SECRET")

# # ✅ 讀取 Firebase 憑證
# # 讀取 Firebase 憑證
# firebase_credentials_json = os.getenv("FIREBASE_CREDENTIALS")

# if firebase_credentials_json:
#     try:
#         if isinstance(firebase_credentials_json, str):
#             cred_dict = json.loads(firebase_credentials_json)  # 只有當它是字串時才解析
#         else:
#             cred_dict = firebase_credentials_json  # 如果已經是字典，直接使用
        
#         cred = credentials.Certificate(cred_dict)

#         # 🔍 **先檢查 Firebase 是否已初始化**
#         if not firebase_admin._apps:
#             firebase_admin.initialize_app(cred)
#             print("✅ Firestore database initialized successfully!")
#         else:
#             print("⚠️ Firebase app already initialized, skipping re-initialization.")

#     except Exception as e:
#         print(f"❌ Firebase Initialization Error: {e}")
#         raise ValueError("Failed to load Firebase credentials.")
# else:
#     raise ValueError("❌ Firebase credentials not found! Please set FIREBASE_CREDENTIALS in the environment variables.")


# # ✅ 初始化 Firestore
# db = firestore.client()

# # ✅ 初始化 Flask 應用
# app = Flask(__name__)
# CORS(app)

# # ✅ 設置 LINE Bot API
# line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
# handler = WebhookHandler(LINE_SECRET)

# # ✅ 背景初始化 RAG
# def initialize_rag_in_background():
#     print("🔄 Initializing RAG system in the background...")
#     initialize_rag()
#     print("✅ RAG system initialized successfully!")

# @app.route("/callback", methods=["POST"])
# def callback():
#     """接收 LINE Webhook 回傳的訊息"""
#     signature = request.headers.get("X-Line-Signature", "")
#     body = request.get_data(as_text=True)
    
#     print(f"📥 Received Webhook Request: {body}")
#     print(f"🔑 Signature: {signature}")
    
#     if not body:
#         print("❌ Error: Received an empty request body!")
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
#     """處理用戶發送的訊息"""
#     try:
#         user_id = event.source.user_id
#         user_input = event.message.text.lower().strip()
#         print(f"📨 Received message from user {user_id}: {user_input}")

#         # 🔥 取得用戶在 Firebase 的記錄
#         user_ref = db.collection("users").document(user_id)
#         user_data = user_ref.get()
#         stored_preferences = user_data.to_dict().get("preferences") if user_data.exists else None

#         # **1️⃣ 用戶輸入 "change preference"，讓他重新輸入偏好**
#         if user_input in ["change preference", "modify diet", "update preference"]:
#             user_ref.update({"preferences": firestore.DELETE_FIELD})  # 🔥 刪除偏好欄位
#             response_text = "Please enter your new dietary preferences (e.g., 'I am vegetarian' or 'I avoid beef and pork')."

#         # **2️⃣ 如果用戶沒有設定偏好，要求他輸入**
#         elif stored_preferences is None:
#             user_ref.set({"preferences": user_input})  # ✅ 記錄新偏好
#             response_text = f"Thanks! I've noted your dietary preferences: {user_input}. Now you can ask for recipe recommendations!"

#         # **3️⃣ 用戶已經有偏好，根據偏好推薦食譜**
#         else:
#             response_text = f"Thanks for your message! We will recommend a recipe for you based on your preference: {stored_preferences}."
#             try:
#                 recipe = chat_with_model(user_id, user_input)  # 調用 RAG 生成食譜
#                 response_text += f"\n\n{recipe}"
#             except Exception as e:
#                 print(f"❌ RAG generation failed: {e}")
#                 response_text += "\n\nSorry, I encountered an error while generating your recipe."

#         # ✅ **發送回應**
#         line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response_text))
#         print(f"✅ Response sent to user {user_id}")

#     except Exception as e:
#         print(f"❌ Error while processing message: {e}")

# # ✅ 背景初始化 RAG
# thread = threading.Thread(target=initialize_rag_in_background)
# thread.daemon = True
# thread.start()

# # ✅ 啟動 Flask 服務
# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=False)


from flask import Flask, request, abort
from flask_cors import CORS
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import threading
import firebase_admin
from firebase_admin import credentials, firestore
import json
import ast

# 🔥 導入 RAG 相關函數
from RAG import chat_with_model, initialize_rag

# ✅ 設定 LINE Channel Token & Secret
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
LINE_SECRET = os.getenv("LINE_SECRET")

# ✅ 讀取 Firebase 憑證
firebase_credentials_json = os.getenv("FIREBASE_CREDENTIALS")

if firebase_credentials_json:
    try:
        if isinstance(firebase_credentials_json, str):
            cred_dict = json.loads(firebase_credentials_json)  # 解析 JSON 字串
        else:
            cred_dict = firebase_credentials_json  # 如果已經是字典，直接使用
        
        cred = credentials.Certificate(cred_dict)

        # 🔍 **先檢查 Firebase 是否已初始化**
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
            print("✅ Firestore database initialized successfully!")
        else:
            print("⚠️ Firebase app already initialized, skipping re-initialization.")

    except Exception as e:
        print(f"❌ Firebase Initialization Error: {e}")
        raise ValueError("Failed to load Firebase credentials.")
else:
    raise ValueError("❌ Firebase credentials not found! Please set FIREBASE_CREDENTIALS in the environment variables.")

# ✅ 初始化 Firestore
db = firestore.client()

# ✅ 初始化 Flask 應用
app = Flask(__name__)
CORS(app)

# ✅ 設置 LINE Bot API
line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
handler = WebhookHandler(LINE_SECRET)

# ✅ 背景初始化 RAG
def initialize_rag_in_background():
    print("🔄 Initializing RAG system in the background...")
    initialize_rag()
    print("✅ RAG system initialized successfully!")

@app.route("/callback", methods=["POST"])
def callback():
    """接收 LINE Webhook 回傳的訊息"""
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    
    print(f"📥 Received Webhook Request: {body}")
    print(f"🔑 Signature: {signature}")
    
    if not body:
        print("❌ Error: Received an empty request body!")
        return "Bad Request - Empty Body", 400
    
    try:
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
    """處理用戶發送的訊息"""
    try:
        user_id = event.source.user_id
        user_input = event.message.text.lower().strip()
        print(f"📨 Received message from user {user_id}: {user_input}")

        # 🔥 **強制從 Firebase 獲取最新的用戶偏好**
        user_ref = db.collection("users").document(user_id)
        user_data = user_ref.get()
        stored_preferences = None

        if user_data.exists:
            stored_preferences = user_data.to_dict().get("preferences")  # 確保取的是最新數據

        # **1️⃣ 用戶輸入 "change preference"，讓他重新輸入偏好**
        if user_input in ["change preference", "modify diet", "update preference"]:
            user_ref.update({"preferences": firestore.DELETE_FIELD})  # 🔥 刪除偏好欄位
            response_text = "Please enter your new dietary preferences (e.g., 'I am vegetarian' or 'I avoid beef and pork')."

        # **2️⃣ 如果用戶沒有設定偏好，要求他輸入**
        elif stored_preferences is None:
            user_ref.set({"preferences": user_input})  # ✅ 記錄新偏好
            response_text = f"Thanks! I've noted your dietary preferences: {user_input}. Now you can ask for recipe recommendations!"

        # **3️⃣ 用戶已經有偏好，根據偏好推薦食譜**
        else:
            # ✅ **每次都重新獲取最新的偏好**
            user_data = user_ref.get()  # **再次強制查詢最新數據**
            stored_preferences = user_data.to_dict().get("preferences")

            response_text = f"Thanks for your message! We will recommend a recipe for you based on your preference: {stored_preferences}."
            try:
                recipe = chat_with_model(user_id, user_input)  # 調用 RAG 生成食譜
                response_text += f"\n\n{recipe}"
            except Exception as e:
                print(f"❌ RAG generation failed: {e}")
                response_text += "\n\nSorry, I encountered an error while generating your recipe."

        # ✅ **發送回應**
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response_text))
        print(f"✅ Response sent to user {user_id}")

    except Exception as e:
        print(f"❌ Error while processing message: {e}")

# ✅ 背景初始化 RAG
thread = threading.Thread(target=initialize_rag_in_background)
thread.daemon = True
thread.start()

# ✅ 啟動 Flask 服務
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=False)
