import streamlit as st
import pymupdf4llm
from tools.db_mongo import get_max_version_for_name, insert_documents

import os
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.schema.document import Document
import base64

def encode_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

# 主函數
def pdf_handler():
    st.title('PDF 文件上傳')
    
    # 文件上傳
    uploaded_file = st.file_uploader('上傳您的 PDF 文件', type=['pdf'])
    if uploaded_file is not None:
        filename = uploaded_file.name
        latest_version =  get_max_version_for_name('vectorDB_tool','chunks',filename)
        new_version = latest_version + 1
        file_folder = filename.split('.')[0]
        folder_path = f'uploads/{file_folder}'

        # 確認路徑是否存在，如果不存在則創建路徑
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        # 保存上傳的文件到本地（可選）
        with open(f'{folder_path}/{filename}', 'wb') as f:
            f.write(uploaded_file.getbuffer())

        # 初始化 session_state 中的內容
        if 'uploaded_filename' not in st.session_state or st.session_state['uploaded_filename'] != filename:
            st.session_state['uploaded_filename'] = filename
            st.session_state['file_content'] = pymupdf4llm.to_markdown(f'{folder_path}/{filename}',write_images=True,image_path=f'{folder_path}',page_chunks=True)

            final_chunks = []
            headers_to_split_on = [
                ("#", "H1"),
                ("##", "H2"),
                ("###", "H3"),
            ]
            markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on,return_each_line=False,strip_headers=True)

            for split in st.session_state['file_content']:
                split['metadata']['file'] = uploaded_file.name
                split['metadata']['version'] = new_version
                for key in ['format','title','producer','page_count','file_path','encryption','modDate','trapped','creationDate','creator','keywords','subject','author']:
                    split['metadata'].pop(key,None)
                if len(split['tables']) >0 :
                    split['metadata']['type']= 'table'
                else:
                    split['metadata']['type']= 'text'
                md_splits = markdown_splitter.split_text(split['text'])
                for md_split in md_splits:
                    md_split.metadata.update(split['metadata'])
                    final_chunks.append(md_split)
            chunk_size = 750
            chunk_overlap = 50
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size, chunk_overlap=chunk_overlap
            )
            final_splits = text_splitter.split_documents(final_chunks)
            file_list = os.listdir(folder_path)
            for file in file_list:
                if file.endswith(".png"):
                    final_splits.insert(0,
                        Document(
                            page_content = "",
                            metadata = {
                                'version': new_version,
                                'file':filename,
                                'type': 'image',
                                'original_content': encode_image(f"{folder_path}/{file}"),
                                'imgname': file
                            }
                        )
                    )
            save_list = []
            for doc in final_splits:
                save_list.append(
                    {
                        'page_content':doc.page_content,
                        'metadata': doc.metadata
                    }
                )
            result = insert_documents('vectorDB_tool','chunks',save_list)
            if result['code'] == 200:
                st.success(f"檔案：『{filename}』 版本：{new_version}   {result['msg']}")
            else:
                st.error(f"檔案：『{filename}』 解析失敗： {result['msg']}")
pdf_handler()
