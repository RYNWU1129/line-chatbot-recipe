import os
import json
import gdown
import pandas as pd
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import gc

# 設置檔案路徑
FAISS_INDEX_PATH = "recipe_faiss.index"
METADATA_PATH = "recipe_metadata.csv"
CSV_PATH = "https://drive.google.com/file/d/1IuGWrM_YwnYQwtp06SvWji695NJ7d_wS/view?usp=sharing"

# 加載 embedding 模型
print("載入 embedding 模型...")
model = SentenceTransformer("all-MiniLM-L6-v2")

def process_csv_in_chunks():
    print("開始下載資料...")
    # 從 Google Drive 下載檔案
    file_id = '1IuGWrM_YwnYQwtp06SvWji695NJ7d_wS'
    temp_csv_path = 'RecipeNLG_dataset.csv'
    gdown.download(f'https://drive.google.com/uc?id={file_id}', temp_csv_path, quiet=False)
    
    print("檔案下載完成，開始處理...")
    
    # 創建空的 FAISS 索引 (all-MiniLM-L6-v2 的嵌入維度是 384)
    embedding_dim = 384
    index = faiss.IndexFlatL2(embedding_dim)
    
    # 創建空的元數據 DataFrame
    metadata_df = pd.DataFrame()
    
    # 分批處理 CSV
    chunk_size = 500
    max_rows = 2000  # 可以設定更大，因為在本地機器上不受 512MB 限制
    rows_processed = 0
    
    # 使用 chunksize 參數分批讀取 CSV
    for chunk in pd.read_csv(temp_csv_path, chunksize=chunk_size):
        if rows_processed >= max_rows:
            break
            
        # 處理當前批次
        current_chunk = chunk.iloc[:min(chunk_size, max_rows - rows_processed)]
        rows_processed += len(current_chunk)
        
        print(f"處理第 {rows_processed-len(current_chunk)+1} 至 {rows_processed} 行，計劃處理 {max_rows} 行")
        
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
        
        print(f"為第 {rows_processed-len(current_chunk)+1} 至 {rows_processed} 行創建嵌入...")
        
        # 處理嵌入
        batch_embeddings = []
        for _, row in current_chunk.iterrows():
            embedding = model.encode(row["text"], convert_to_numpy=True)
            batch_embeddings.append(embedding)
        
        # 添加到 FAISS 索引
        batch_embeddings_array = np.vstack(batch_embeddings)
        index.add(batch_embeddings_array)
        
        # 釋放記憶體
        del batch_embeddings, batch_embeddings_array, current_chunk, metadata_chunk
        gc.collect()
        
    # 保存索引和元數據
    print("保存 FAISS 索引和元數據...")
    faiss.write_index(index, FAISS_INDEX_PATH)
    metadata_df.to_csv(METADATA_PATH, index=False)
    
    # 清理臨時檔案
    if os.path.exists(temp_csv_path):
        os.remove(temp_csv_path)
        
    print("處理完成！檔案已保存為:")
    print(f"- {FAISS_INDEX_PATH}")
    print(f"- {METADATA_PATH}")
    
if __name__ == "__main__":
    process_csv_in_chunks()