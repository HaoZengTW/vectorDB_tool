import streamlit as st
from tools.db_sqlite import get_distinct_file, get_latest_content, save_splits, get_latest_splits_version, get_selected_file_id, get_splits,del_splits
from langchain.schema.document import Document
from langchain.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
from langchain_huggingface.embeddings import HuggingFaceEmbeddings

import json
import os
import zipfile


filenames = get_distinct_file()
# embeddings = OllamaEmbeddings(model="hf.co/lagoon999/Chuxin-Embedding-Q8_0-GGUF",)
embeddings = HuggingFaceEmbeddings(model_name="chuxin-llm/Chuxin-Embedding")

def get_databases():
    res = []
    for name in os.listdir("./database"):
        if os.path.isdir(os.path.join("./database", name)):
            res.append(name)
    return res
databases = get_databases()

st.title("向量資料庫")
with st.expander('產生新資料庫'):
    db_name = st.text_input('資料庫名稱')
    selected_filename = st.selectbox("文檔名稱:", filenames)
    document_id = get_selected_file_id(selected_filename)
    latest_splits_version = get_latest_splits_version(document_id)
    if latest_splits_version and latest_splits_version[0]  is not None:
        if st.button("生成資料庫"):
            docs = []
            splits_version = latest_splits_version[0]
            splits = get_splits(document_id, splits_version)
            
            for split in splits:
                docs.append(
                    Document(
                        page_content = split[0],
                        
                        metadata = json.loads(split[1].replace("'","\""))
                    )
                )
            vectorstore = FAISS.from_documents(documents=docs, embedding=embeddings)
            vectorstore.save_local(f"./database/{db_name}")
            folder_path = f"./database/{db_name}"
            zipfile_path = f'./zip/{db_name}.zip'
            zipf = zipfile.ZipFile(zipfile_path, 'w', zipfile.ZIP_DEFLATED)
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    # 写入文件到.zip 文件中
                    zipf.write(os.path.join(root, file), 
                            os.path.relpath(os.path.join(root, file), 
                            os.path.join(folder_path, '..')))
                    
            # 关闭 ZipFile 对象
            zipf.close()
            databases = get_databases()
            st.success(f"{db_name} 已保存")
    else:
        st.write('尚未建立chunks')
with st.expander('合併資料庫'):
    c_db_name = st.text_input('新資料庫名稱')
    selected_dbs = st.multiselect("向量資料庫:", databases)
    if st.button("合併"):
        if len(selected_dbs) > 1:
            for i in range(len(selected_dbs)):
                if i == 0:
                    db_base = FAISS.load_local(
                        folder_path=f"./database/{selected_dbs[i]}", 
                        embeddings=embeddings,
                        allow_dangerous_deserialization=True
                    )
                else:
                    db_unit = FAISS.load_local(
                        folder_path=f"./database/{selected_dbs[i]}", 
                        embeddings=embeddings,
                        allow_dangerous_deserialization=True
                    )
                    db_base.merge_from(db_unit)
            db_base.save_local(f"./database/{c_db_name}")
            folder_path = f"./database/{c_db_name}"
            zipfile_path = f'./zip/{c_db_name}.zip'
            zipf = zipfile.ZipFile(zipfile_path, 'w', zipfile.ZIP_DEFLATED)
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    # 写入文件到.zip 文件中
                    zipf.write(os.path.join(root, file), 
                            os.path.relpath(os.path.join(root, file), 
                            os.path.join(folder_path, '..')))
                    
            # 关闭 ZipFile 对象
            zipf.close()
            databases = get_databases()
            st.success(f"{db_name} 已保存")
        else:
            st.write('請選擇要合併的資料庫')
        
if databases:
    selected_db = st.selectbox("資料庫名稱:", databases)
    with open(f'./zip/{selected_db}.zip', 'rb') as f:
        st.download_button('Download', f, file_name=f'{selected_db}.zip')