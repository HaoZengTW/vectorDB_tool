import streamlit as st
from tools.db_mongo import get_distinct_files, query_chunks_by_name_and_version, get_max_version_for_name, delete_documents_by_ids, batch_update_documents
from langchain.schema.document import Document
from langchain.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
from langchain_huggingface.embeddings import HuggingFaceEmbeddings

import json
import os
import zipfile


get_fileName_result = get_distinct_files('vectorDB_tool','chunks','file')
if get_fileName_result['code'] == 200:
    file_list = get_fileName_result['data']
else:
    st.error(get_fileName_result['msg'])
embeddings = OllamaEmbeddings(model="hf.co/lagoon999/Chuxin-Embedding-Q8_0-GGUF",)
# embeddings = HuggingFaceEmbeddings(model_name="chuxin-llm/Chuxin-Embedding")

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
    selected_filename = st.selectbox("文檔名稱:", file_list)
    latest_splits_version = get_max_version_for_name('vectorDB_tool','chunks',selected_filename)
    
    if latest_splits_version and len(db_name)>0:
        if st.button("生成資料庫"):
            docs = []
            splits_version = latest_splits_version
            splits = query_chunks_by_name_and_version('vectorDB_tool','chunks', selected_filename, latest_splits_version)
            
            for split in splits['data']:
                docs.append(
                    Document(
                        page_content = split['page_content'],
                        
                        metadata = split['metadata']
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
            st.success(f"{c_db_name} 已保存")
        else:
            st.write('請選擇要合併的資料庫')
        
if databases:
    selected_db = st.selectbox("資料庫名稱:", databases)
    with open(f'./zip/{selected_db}.zip', 'rb') as f:
        st.download_button('Download', f, file_name=f'{selected_db}.zip')