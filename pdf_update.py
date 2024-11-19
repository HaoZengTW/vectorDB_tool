import streamlit as st
import pymupdf4llm
from tools.db_sqlite import get_latest_version, save_file,save_splits, get_latest_splits_version, get_selected_file_id
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
        latest_version = get_latest_version(filename)
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
            file_content = ''
            for i in st.session_state['file_content']:
                file_content += i['text']
                
            save_file(filename, new_version, file_content)
            st.success(f'文件已保存為版本 {new_version}')
            document_id = get_selected_file_id(filename)
            latest_splits_version = get_latest_splits_version(document_id)
            new_version = (latest_splits_version[0] + 1) if latest_splits_version and latest_splits_version[0]  is not None else 1
            final_chunks = []
            headers_to_split_on = [
                ("#", "H1"),
                ("##", "H2"),
                ("###", "H3"),
                ("####", "H4"),
                ("#####", "H5"),
            ]
            markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on,return_each_line=True,strip_headers=True)

            for split in st.session_state['file_content']:
                for key in ['format','title','producer','page_count','file_path','encryption','modDate','trapped','creationDate','creator','keywords','subject','author']:
                    split['metadata'].pop(key,None)
                if len(split['tables']) >0 :
                    split['metadata']['type']= 'table'
                else:
                    split['metadata']['type']= 'text'
                md_splits = markdown_splitter.split_text(split['text'])
                for md_split in md_splits:
                    md_split.metadata.update(split['metadata'])
                    # print(md_split)
                    final_chunks.append(md_split)
                # save_splits(md_split['metadata'],md_split['text'], new_version, document_id)
            # print(final_chunks)
            chunk_size = 500
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
                                'type': 'image',
                                'original_content': encode_image(f"{folder_path}/{file}")
                            }
                        )
                    )
            for split in final_splits:
                save_splits(split.metadata,split.page_content, new_version, document_id)
pdf_handler()
