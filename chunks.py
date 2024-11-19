import streamlit as st
from tools.db_sqlite import get_distinct_file, get_latest_content, save_splits, get_latest_splits_version, get_selected_file_id, get_splits,del_splits
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_text_splitters import RecursiveCharacterTextSplitter
import json
import base64
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import os
from langchain.schema.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

os.environ["GROQ_API_KEY"] = os.getenv('GROQ_API_KEY')

llm = ChatGroq(
     model="llama-3.2-90b-vision-preview",
     temperature=0,
     max_tokens=None,
     timeout=None,
     max_retries=2,
 )

summary_prompt = """
請用繁體中文幫我總結下列markdown表格內容 :
{element}
"""


table_llm = ChatGroq(
     model="llama-3.1-70b-versatile",
     temperature=0,
     max_tokens=None,
     timeout=None,
     max_retries=2,
 )

table_prompt=ChatPromptTemplate.from_template(summary_prompt)

summary_chain = table_prompt | table_llm | StrOutputParser()

filenames = get_distinct_file()

# Helper function to encode image
def encode_image(file_path):
    """
    讀取圖片並進行 Base64 編碼
    :param file_path: 圖片檔案路徑
    :return: Base64 編碼後的字符串
    """
    with open(file_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
    return encoded_string

def summarize_image(encoded_image):
    prompt = [
        HumanMessage(content=[
            {
                "type": "text",
                "text": "你是一個善於分圖像的專家.請用繁體中文詳細解釋這圖片的內容."
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{encoded_image}"
                },
            },
        ])
    ]
    response = llm.invoke(prompt)
    return response.content

def summarize_table(context):
    return summary_chain.invoke(context)

# Streamlit UI for selecting a filename
st.title("選擇檔案")
if filenames:
    selected_filename = st.selectbox("文檔名稱:", filenames)
    select_chunks_source = st.selectbox("",["讀取Chunks","重建Chunks"])
    if select_chunks_source == "重建Chunks":
        result = get_latest_content(selected_filename)

        if result:
            file_content = result[0]
            with st.expander('文本預覽'):
                # Display the content
                markdown_content = st.text_area("Markdown文本：", file_content, height=300)
        else:
            st.warning("No content found for the selected filename.")
        st.title("設定斷詞參數")
        user_defined_tuples = []
        num_tuples = st.number_input("斷詞符號設定數量:", min_value=0, value=1, step=1)

        for i in range(num_tuples):
            col1, col2 = st.columns(2)
            with col1:
                first_element = st.text_input(f"段詞符號 {i + 1}:", key=f"first_{i}")
            with col2:   
                second_element = st.text_input(f"metadata顯示 {i + 1}:", key=f"second_{i}")
            user_defined_tuples.append((first_element, second_element))

        st.write("預覽:", user_defined_tuples)
        col1, col2 = st.columns(2)
        with col1:
            chunk_max_size = st.number_input("chunk_max_size", min_value=10, value=250, step=50)
        with col2:
            chunk_overlap = st.number_input("chunk_overlap", min_value=5, value=30, step=5)
        if st.button('執行斷詞'):
            markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=user_defined_tuples,return_each_line=False,strip_headers=True)
            md_header_splits = markdown_splitter.split_text(file_content)
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_max_size, chunk_overlap=chunk_overlap)
            splits = text_splitter.split_documents(md_header_splits)
            
            document_id = get_selected_file_id(selected_filename)
            latest_splits_version = get_latest_splits_version(document_id)
            print('latest_splits_version',latest_splits_version)
            new_version = (latest_splits_version[0] + 1) if latest_splits_version and latest_splits_version[0]  is not None else 1
            
            for split in splits:
                save_splits(split.metadata,split.page_content, new_version, document_id)
            st.success(f'{selected_filename} 已儲存chunks version:{new_version}')
    
    if select_chunks_source == "讀取Chunks": 
        
        document_id = get_selected_file_id(selected_filename)
        latest_splits_version = get_latest_splits_version(document_id)
        splits_version = (latest_splits_version[0]) if latest_splits_version and latest_splits_version[0]  is not None else 0
        splits = get_splits(document_id, splits_version)
        if st.button('保存更新'):
            del_splits(document_id, splits_version)
            for i in range(len(splits)):
                page_content = st.session_state.get(f"page_content_{i}", splits[i][0])
                metadata = st.session_state.get(f"metadata_{i}", splits[i][1])
                save_splits(metadata, page_content, splits_version, document_id)
            st.success("已保存更新")
            st.rerun()
        st.divider()
        if st.button("摘要全影像內容", type="primary"):
            for i in range(len(splits)):
                if "image" in splits[i][1]:
                    # 執行摘要
                    summary = summarize_image(json.loads(splits[i][1].replace("'","\""))['original_content'])
                    # 更新 splits 的 page_content
                    splits[i] = (summary, splits[i][1])
        if st.button("摘要全表格內容", type="primary"):
            for i in range(len(splits)):
                if "table" in splits[i][1]:
                    # 執行摘要
                    table_summary = summarize_table(splits[i][0])
                    metadata = json.loads(splits[i][1].replace("'", "\""))
            
                    # 將原始內容寫入 metadata 中，變數名為 "original_content"
                    metadata["original_content"] = splits[i][0]
                    
                    # 更新 splits[i] 的內容
                    splits[i] = (table_summary, json.dumps(metadata))
        i = 0
        while i < len(splits):
            col1, col2 ,col3= st.columns([2, 1,1])
            with col1:
                page_content = st.text_area(f"content {i }:", key=f"page_content_{i}", value=splits[i][0], height = 300)
            with col2:  
                if "image" not in splits[i][1]:
                    metadata = st.text_area(f"metadata {i }:", key=f"metadata_{i}", value=splits[i][1].replace("'","\"").replace(",\"",",\n\" ").replace("{\"","{\n\"").replace("\"}","\" \n }"), height = 300)
                else:
                    st.image(base64.b64decode(json.loads(splits[i][1].replace("'","\""))['original_content']))
                    # st.text_area(f"metadata {i }:", key=f"metadata_{i}", value=json.loads(splits[i][1].replace("'","\""))['original_content'])
            with col3:
                if i>0:
                    if st.button('向上合併',key=f"combine_{i}"):
                        splits[i-1]= list(splits[i-1])
                        splits[i-1][0] = splits[i-1][0]+ " " + splits[i][0]
                        splits[i-1] = tuple(splits[i-1])
                        splits.pop(i)
                        del_splits(document_id, splits_version)
                        for split in splits:
                            save_splits(split[1],split[0], splits_version, document_id)
                        st.rerun()
                if st.button('刪除',key=f"del_{i}"):
                    splits.pop(i)
                    del_splits(document_id, splits_version)
                    for split in splits:
                        save_splits(split[1],split[0], splits_version, document_id)
                    st.rerun()
                if st.button('拆分',key=f"splits_{i}"):
                    splits.insert(i+1,("",splits[i][1]))
                    del_splits(document_id, splits_version)
                    for split in splits:
                        save_splits(split[1],split[0], splits_version, document_id)
                    st.rerun()
                if "image" in splits[i][1]:
                    if st.button("摘要影像內容",key=f"sum_img_{i}"):
                        # 執行摘要
                        summary = summarize_image(json.loads(splits[i][1].replace("'","\""))['original_content'])
                        # 更新 splits 的 page_content
                        splits[i] = (summary, splits[i][1])
                        del_splits(document_id, splits_version)
                        for split in splits:
                            save_splits(split[1],split[0], splits_version, document_id)
                        st.rerun()
                if "table" in splits[i][1]:
                    if st.button("摘要表格內容",key=f"sum_table_{i}"):
                        table_summary = summarize_table(splits[i][0])
                        metadata = json.loads(splits[i][1].replace("'", "\""))
                
                        # 將原始內容寫入 metadata 中，變數名為 "original_content"
                        metadata["original_content"] = splits[i][0]
                        
                        # 更新 splits[i] 的內容
                        splits[i] = (table_summary, json.dumps(metadata))
                        del_splits(document_id, splits_version)
                        for split in splits:
                            save_splits(split[1],split[0], splits_version, document_id)
                        st.rerun()
            st.divider()
            i += 1
else:
    st.warning("No filenames found in the database.")

# Close the connection
