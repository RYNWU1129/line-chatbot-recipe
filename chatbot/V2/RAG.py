# # RAG.py
# import os
# import json
# import pandas as pd
# import faiss
# import numpy as np
# from sentence_transformers import SentenceTransformer
# import openai
# from dotenv import load_dotenv
# import firebase_admin
# from firebase_admin import credentials, firestore

# # ----------------------------------------- 
# # 🔹 初始化全局變數
# # ----------------------------------------- 
# FIREBASE_CRED_PATH = "C:/Users/user/anaconda3/line-chatbot-recipe/chatbot/api1.env.txt"
# CSV_PATH = "C:/Users/user/anaconda3/line-chatbot-recipe/chatbot/RecipeNLG_dataset.csv"
# FAISS_INDEX_PATH = "recipe_faiss.index"
# METADATA_PATH = "recipe_metadata.csv"

# # Load environment variables
# load_dotenv(FIREBASE_CRED_PATH)
# openai_api_key = os.getenv("OPENAI_API_KEY")
# firebase_cred_path = "C:/Users/user/anaconda3/line-chatbot-recipe/chatbot/ai-recipe-87c0b-firebase-adminsdk-fbsvc-1abcfa88d1.json"

# if not openai_api_key:
#     raise ValueError("❌ OPENAI_API_KEY not found! Check your .env file.")

# # Initialize Firebase
# if not firebase_admin._apps:
#     cred = credentials.Certificate(firebase_cred_path)
#     firebase_admin.initialize_app(cred)
# db = firestore.client()

# # Load embedding model
# model = SentenceTransformer("all-MiniLM-L6-v2")

# # Load recipe dataset and FAISS index
# if os.path.exists(FAISS_INDEX_PATH) and os.path.exists(METADATA_PATH):
#     index = faiss.read_index(FAISS_INDEX_PATH)
#     df = pd.read_csv(METADATA_PATH)
# else:
#     df = pd.read_csv(CSV_PATH, nrows=10000)
#     df["text"] = df.apply(lambda row: f"Title: {row['title']}\nIngredients: {row['ingredients']}\nInstructions: {row['directions']}", axis=1)
#     df["embedding"] = df["text"].apply(lambda x: model.encode(x, convert_to_numpy=True))
#     embeddings = np.vstack(df["embedding"].values)
#     embedding_dim = embeddings.shape[1]
#     index = faiss.IndexFlatL2(embedding_dim)
#     index.add(embeddings)
#     faiss.write_index(index, FAISS_INDEX_PATH)
#     df.to_csv(METADATA_PATH, index=False)

# # ----------------------------------------- 
# # 🔹 Firestore 函數
# # ----------------------------------------- 
# def get_user_data(user_id):
#     user_ref = db.collection("users").document(user_id)
#     user_doc = user_ref.get()
#     return user_doc.to_dict() if user_doc.exists else None

# def set_user_data(user_id, data):
#     user_ref = db.collection("users").document(user_id)
#     user_ref.set(data, merge=True)

# def get_user_conversation(user_id):
#     user_ref = db.collection("conversations").document(user_id)
#     user_doc = user_ref.get()
#     return user_doc.to_dict().get("messages", []) if user_doc.exists else []

# def save_user_conversation(user_id, messages):
#     user_ref = db.collection("conversations").document(user_id)
#     user_ref.set({"messages": messages}, merge=True)

# # ----------------------------------------- 
# # 🔹 FAISS 檢索
# # ----------------------------------------- 
# def search_recipe(query, k=3):
#     query_embedding = model.encode(query, convert_to_numpy=True).reshape(1, -1)
#     distances, indices = index.search(query_embedding, k)
#     return df.iloc[indices[0]]

# # ----------------------------------------- 
# # 🔹 GPT 整合
# # ----------------------------------------- 
# def chat_with_model(user_id, user_input):
#     user_data = get_user_data(user_id)
#     preferences = user_data.get("preferences", None) if user_data else None

#     if not preferences:
#         return "Please enter your dietary preferences (e.g., vegetarian, no beef, low-carb)."

#     best_recipes = search_recipe(user_input, k=3)
#     formatted_recipes = "\n\n".join([
#         f"**Title:** {row['title']}\n**Ingredients:** {row['ingredients']}\n**Instructions:** {row['directions']}"
#         for _, row in best_recipes.iterrows()
#     ])

#     system_prompt = f"""
#     You are a professional chef assistant. The user follows these dietary preferences: {preferences}.
#     Here are recommended recipes based on their preferences:
#     {formatted_recipes}
#     Provide a response considering these preferences strictly.
#     """

#     conversation = get_user_conversation(user_id)
#     if not conversation:
#         conversation.append({"role": "system", "content": system_prompt})
#     conversation.append({"role": "user", "content": user_input})

#     client = openai.OpenAI(api_key=openai_api_key)
#     response = client.chat.completions.create(
#         model="gpt-3.5-turbo",
#         messages=conversation,
#         max_tokens=200
#     )

#     reply = response.choices[0].message.content
#     conversation.append({"role": "assistant", "content": reply})

#     if len(conversation) > 20:
#         conversation = conversation[-20:]
#     save_user_conversation(user_id, conversation)

#     return reply

import os
import json
import gdown
import pandas as pd
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import openai
import firebase_admin
from firebase_admin import credentials, firestore
import gc

# ----------------------------------------- 
# 🔹 初始化全局變數
# ----------------------------------------- 
FAISS_INDEX_PATH = "recipe_faiss.index"
METADATA_PATH = "recipe_metadata.csv"
CSV_PATH = "https://drive.google.com/file/d/1IuGWrM_YwnYQwtp06SvWji695NJ7d_wS/view?usp=sharing"

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

# ✅ 加載 embedding 模型
model = SentenceTransformer("all-MiniLM-L6-v2")

# ✅ 分批處理函數 - 減少記憶體使用
def process_csv_in_chunks():
    print("⚠️ 未找到現有的 FAISS 索引和元數據，開始分批處理資料...")
    
    # 從 Google Drive 下載檔案
    file_id = '1IuGWrM_YwnYQwtp06SvWji695NJ7d_wS'  # 從 URL 中提取 ID
    temp_csv_path = 'RecipeNLG_dataset.csv'
    gdown.download(f'https://drive.google.com/uc?id={file_id}', temp_csv_path, quiet=False)
    
    print("✅ 檔案下載完成，開始分批處理...")
    
    # 創建空的 FAISS 索引
    # all-MiniLM-L6-v2 的嵌入維度是 384
    embedding_dim = 384
    index = faiss.IndexFlatL2(embedding_dim)
    
    # 創建空的元數據 DataFrame
    metadata_df = pd.DataFrame()
    
    # 分批處理 CSV
    chunk_size = 500  # 每次處理 500 行
    max_rows = 2000   # 減少總行數以符合記憶體限制
    rows_processed = 0
    
    # 使用 chunksize 參數分批讀取 CSV
    for chunk in pd.read_csv(temp_csv_path, chunksize=chunk_size):
        if rows_processed >= max_rows:
            break
            
        # 限制此批次的大小
        current_chunk = chunk.iloc[:min(chunk_size, max_rows - rows_processed)]
        rows_processed += len(current_chunk)
        
        print(f"🔄 處理第 {rows_processed-len(current_chunk)+1} 至 {rows_processed} 行，計劃處理 {max_rows} 行")
        
        # 創建文本字段
        current_chunk["text"] = current_chunk.apply(
            lambda row: f"Title: {row['title']}\nIngredients: {row['ingredients']}\nInstructions: {row['directions']}", 
            axis=1
        )
        
        # 保存元數據（不包含嵌入）
        metadata_chunk = current_chunk[['title', 'ingredients', 'directions', 'text']]
        
        if metadata_df.empty:
            metadata_df = metadata_chunk.copy()
        else:
            metadata_df = pd.concat([metadata_df, metadata_chunk])
        
        print(f"✅ 開始為第 {rows_processed-len(current_chunk)+1} 至 {rows_processed} 行創建嵌入...")
        
        # 分批處理嵌入以減少記憶體使用
        batch_embeddings = []
        for i, row in current_chunk.iterrows():
            # 主動進行垃圾回收
            gc.collect()
            
            embedding = model.encode(row["text"], convert_to_numpy=True)
            batch_embeddings.append(embedding)
            
            # 每處理 100 個嵌入就清理一次記憶體
            if (i % 100 == 0) and (i > 0):
                gc.collect()
        
        # 添加到 FAISS 索引
        print(f"✅ 添加第 {rows_processed-len(current_chunk)+1} 至 {rows_processed} 行的嵌入到 FAISS 索引...")
        batch_embeddings_array = np.vstack(batch_embeddings)
        index.add(batch_embeddings_array)
        
        # 釋放記憶體
        del batch_embeddings, batch_embeddings_array, current_chunk, metadata_chunk
        gc.collect()
        print(f"✅ 第 {rows_processed} 行處理完成，釋放記憶體")
    
    # 保存索引和元數據
    print("✅ 保存 FAISS 索引和元數據...")
    faiss.write_index(index, FAISS_INDEX_PATH)
    metadata_df.to_csv(METADATA_PATH, index=False)
    
    # 清理
    if os.path.exists(temp_csv_path):
        os.remove(temp_csv_path)
    print("✅ 分批處理完成！")
    
    return index, metadata_df

# ✅ 加載 FAISS index 和食譜數據
if os.path.exists(FAISS_INDEX_PATH) and os.path.exists(METADATA_PATH):
    print("✅ 找到現有的 FAISS 索引和元數據，直接載入")
    index = faiss.read_index(FAISS_INDEX_PATH)
    df = pd.read_csv(METADATA_PATH)
else:
    # 使用分批處理代替原始處理方法
    index, df = process_csv_in_chunks()

# ----------------------------------------- 
# 🔹 Firestore 函數
# ----------------------------------------- 
def get_user_data(user_id):
    """ 從 Firestore 獲取使用者數據 """
    user_ref = db.collection("users").document(user_id)
    user_doc = user_ref.get()
    return user_doc.to_dict() if user_doc.exists else None

def set_user_data(user_id, data):
    """ 更新 Firestore 中的使用者數據 """
    user_ref = db.collection("users").document(user_id)
    user_ref.set(data, merge=True)

def get_user_conversation(user_id):
    """ 獲取使用者的聊天記錄 """
    user_ref = db.collection("conversations").document(user_id)
    user_doc = user_ref.get()
    return user_doc.to_dict().get("messages", []) if user_doc.exists else []

def save_user_conversation(user_id, messages):
    """ 存儲使用者的聊天記錄 """
    user_ref = db.collection("conversations").document(user_id)
    user_ref.set({"messages": messages}, merge=True)

# ----------------------------------------- 
# 🔹 FAISS 檢索
# ----------------------------------------- 
def search_recipe(query, k=3):
    """ 透過 FAISS 搜尋相似食譜 """
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
    user_data = get_user_data(user_id)
    preferences = user_data.get("preferences", None) if user_data else None

    if not preferences:
        return "Please enter your dietary preferences (e.g., vegetarian, no beef, low-carb)."

    best_recipes = search_recipe(user_input, k=3)
    if best_recipes is None or best_recipes.empty:
        return "Sorry, I couldn't find any relevant recipes for your request."

    formatted_recipes = "\n\n".join([
        f"**Title:** {row['title']}\n**Ingredients:** {row['ingredients']}\n**Instructions:** {row['directions']}"
        for _, row in best_recipes.iterrows()
    ])

    system_prompt = f"""
    You are a professional chef assistant. The user follows these dietary preferences: {preferences}.
    Here are recommended recipes based on their preferences:
    {formatted_recipes}
    Provide a response considering these preferences strictly.
    """

    conversation = get_user_conversation(user_id)
    if not conversation:
        conversation.append({"role": "system", "content": system_prompt})
    conversation.append({"role": "user", "content": user_input})

    client = openai.OpenAI(api_key=openai_api_key)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=conversation,
        max_tokens=200
    )

    reply = response.choices[0].message.content
    conversation.append({"role": "assistant", "content": reply})

    if len(conversation) > 20:
        conversation = conversation[-20:]
    save_user_conversation(user_id, conversation)

    return reply