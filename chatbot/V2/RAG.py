import os
import json
import pandas as pd
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import openai
import firebase_admin
from firebase_admin import credentials, firestore

# ----------------------------------------- 
# 🔹 初始化全局變數
# ----------------------------------------- 
FAISS_INDEX_PATH = "recipe_faiss.index"
METADATA_PATH = "recipe_metadata.csv"

# 全局變數
index = None
df = None

# ✅ 從環境變數讀取 API Keys
openai_api_key = os.getenv("OPENAI_API_KEY")
firebase_json = os.getenv("FIREBASE_CREDENTIALS")

if not openai_api_key:
    raise ValueError("❌ OPENAI_API_KEY not found! Please set it in Render environment variables.")

# ✅ 初始化 Firebase（從環境變數讀取）
if firebase_json:
    firebase_cred = json.loads(firebase_json)  # 解析 JSON 字串
    if not firebase_admin._apps:  # 確保 Firebase 只初始化一次
        cred = credentials.Certificate(firebase_cred)
        firebase_admin.initialize_app(cred)
else:
    raise ValueError("❌ FIREBASE_CREDENTIALS not found! Please set it in Render environment variables.")

db = firestore.client()

# 測試 Firebase 連接
def test_firebase_connection():
    try:
        # 創建一個測試文檔
        test_ref = db.collection("test").document("connection_test")
        test_ref.set({"timestamp": firestore.SERVER_TIMESTAMP})
        print("✅ Firebase 連接成功")
        return True
    except Exception as e:
        print(f"❌ Firebase 連接失敗: {e}")
        return False
        
# 啟動時測試 Firebase 連接
test_firebase_connection()

# ✅ 加載 embedding 模型
model = SentenceTransformer("all-MiniLM-L6-v2")

# ----------------------------------------- 
# 🔹 RAG 初始化函數 (用於背景執行)
# ----------------------------------------- 
def initialize_rag():
    """初始化 RAG 系統，加載預處理的 FAISS 索引和元數據"""
    global index, df
    
    print("🔍 開始初始化 RAG 系統...")
    
    if os.path.exists(FAISS_INDEX_PATH) and os.path.exists(METADATA_PATH):
        try:
            print(f"✅ 找到預處理的文件，正在載入 {FAISS_INDEX_PATH} 和 {METADATA_PATH}")
            index = faiss.read_index(FAISS_INDEX_PATH)
            df = pd.read_csv(METADATA_PATH)
            print(f"✅ 成功載入索引 (向量數: {index.ntotal}) 和元數據 (行數: {len(df)})")
            return index, df
        except Exception as e:
            print(f"❌ 載入索引或元數據失敗: {e}")
            raise
    else:
        files_found = os.listdir(".")
        error_msg = f"❌ 找不到預處理文件! 目錄內容: {files_found}"
        print(error_msg)
        raise FileNotFoundError(error_msg)

# ----------------------------------------- 
# 🔹 Firestore 函數
# ----------------------------------------- 
def get_user_data(user_id):
    """ 從 Firestore 獲取使用者數據 """
    try:
        user_ref = db.collection("users").document(user_id)
        user_doc = user_ref.get()
        return user_doc.to_dict() if user_doc.exists else None
    except Exception as e:
        print(f"❌ Firestore 獲取用戶數據錯誤: {e}")
        return None

def set_user_data(user_id, data):
    """ 更新 Firestore 中的使用者數據 """
    try:
        user_ref = db.collection("users").document(user_id)
        user_ref.set(data, merge=True)
        return True
    except Exception as e:
        print(f"❌ Firestore 設置用戶數據錯誤: {e}")
        return False

def get_user_conversation(user_id):
    """ 獲取使用者的聊天記錄 """
    try:
        user_ref = db.collection("conversations").document(user_id)
        user_doc = user_ref.get()
        return user_doc.to_dict().get("messages", []) if user_doc.exists else []
    except Exception as e:
        print(f"❌ Firestore 獲取對話記錄錯誤: {e}")
        return []

def save_user_conversation(user_id, messages):
    """ 存儲使用者的聊天記錄 """
    try:
        user_ref = db.collection("conversations").document(user_id)
        user_ref.set({"messages": messages}, merge=True)
        return True
    except Exception as e:
        print(f"❌ Firestore 保存對話記錄錯誤: {e}")
        return False

# ----------------------------------------- 
# 🔹 FAISS 檢索
# ----------------------------------------- 
def search_recipe(query, k=3):
    """ 透過 FAISS 搜尋相似食譜 """
    global index, df
    
    # 確保 index 和 df 已初始化
    if index is None or df is None:
        print("⚠️ FAISS 索引和元數據未初始化，嘗試初始化...")
        initialize_rag()
    
    try:
        query_embedding = model.encode(query, convert_to_numpy=True).reshape(1, -1)
        distances, indices = index.search(query_embedding, k)
        return df.iloc[indices[0]]
    except Exception as e:
        print(f"❌ FAISS 檢索錯誤: {e}")
        return None

# ----------------------------------------- 
# 🔹 GPT 整合
# ----------------------------------------- 
def chat_with_model(user_id, user_input):
    """ GPT 生成回應並整合 FAISS 搜尋結果 """
    global index, df
    
    print(f"📝 處理用戶 {user_id} 的輸入: {user_input}")
    
    # 確保 RAG 系統已初始化
    retry_count = 0
    while (index is None or df is None) and retry_count < 3:
        print(f"⚠️ RAG 未初始化，嘗試初始化 (嘗試 {retry_count+1}/3)")
        try:
            initialize_rag()
            break
        except Exception as e:
            print(f"❌ RAG 初始化失敗: {e}")
            retry_count += 1
            import time
            time.sleep(1)  # 等待1秒再重試
    
    # 如果仍未初始化成功
    if index is None or df is None:
        print("❌ RAG 初始化失敗，無法繼續")
        return "Sorry, I'm currently experiencing technical difficulties. Please try again later."
    
    # 獲取用戶數據
    try:
        user_data = get_user_data(user_id)
        print(f"📊 用戶數據: {user_data}")
        preferences = user_data.get("preferences", None) if user_data else None
    except Exception as e:
        print(f"❌ 獲取用戶數據失敗: {e}")
        preferences = None

    # 檢查是否是設置偏好的訊息
    if not preferences:
        print(f"🆕 新用戶 {user_id}，設置飲食偏好: {user_input}")
        try:
            set_user_data(user_id, {"preferences": user_input})
            return f"Thanks! I've noted your dietary preferences: {user_input}. Now you can ask for recipe recommendations!"
        except Exception as e:
            print(f"❌ 設置用戶偏好失敗: {e}")
            return "I couldn't save your preferences. Please try again."
    
    # 搜尋相關食譜
    print(f"🔍 為查詢 '{user_input}' 搜尋食譜...")
    best_recipes = search_recipe(user_input, k=3)
    if best_recipes is None or len(best_recipes) == 0:
        return "Sorry, I couldn't find any relevant recipes for your request."
    
    # 格式化食譜結果
    formatted_recipes = "\n\n".join([
        f"**Title:** {row['title']}\n**Ingredients:** {row['ingredients']}\n**Instructions:** {row['directions']}"
        for _, row in best_recipes.iterrows()
    ])
    
    # 組織系統提示
    system_prompt = f"""
    You are a professional chef assistant. The user follows these dietary preferences: {preferences}.
    Here are recommended recipes based on their preferences:
    {formatted_recipes}
    Provide a response considering these preferences strictly.
    """
    
    # 獲取對話歷史
    conversation = get_user_conversation(user_id)
    if not conversation:
        conversation.append({"role": "system", "content": system_prompt})
    conversation.append({"role": "user", "content": user_input})
    
    # 調用 OpenAI API
    try:
        client = openai.OpenAI(api_key=openai_api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=conversation,
            max_tokens=200
        )
        
        reply = response.choices[0].message.content
        
        # 保存對話
        conversation.append({"role": "assistant", "content": reply})
        if len(conversation) > 20:
            conversation = conversation[-20:]
        save_user_conversation(user_id, conversation)
        
        return reply
    except Exception as e:
        print(f"❌ OpenAI API 調用錯誤: {e}")
        return "Sorry, I'm having trouble connecting to my recipe brain. Please try again later."