import streamlit as st
from dotenv import load_dotenv
import os
from firecrawl import FirecrawlApp
from tools.db_sqlite import get_latest_version, save_file
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.schema.document import Document
from tools.db_mongo import get_max_version_for_name, insert_documents

load_dotenv()

app = FirecrawlApp(api_key=os.getenv('FIRECRAWL_API_KEY'))
# 主函數
def scrawling_page():
    st.title('網頁爬蟲')

    col1, col2 = st.columns([8, 2])
    with col1:
        url = st.text_input('網頁url')
    with col2:
        page_limit = st.number_input("設定最大頁數", min_value=1, value=1, step=1)
    crawl_result=[]
    includeTags = []
    excludeTags = []
    with st.expander('進階設定'):
        col3, col4 = st.columns([1, 1])
        with col3:
            num_includeTags = st.number_input("includeTags數量:", min_value=0, value=0, step=1)
            for i in range(num_includeTags):
                first_element = st.text_input(f"includeTag {i + 1}:", key=f"first_{i}")
                includeTags.append(first_element)
        with col4:
            num_excludeTags = st.number_input("excludeTags數量:", min_value=0, value=0, step=1)
            for i in range(num_excludeTags):
                first_element = st.text_input(f"excludeTag {i + 1}:", key=f"first_{i}")
                excludeTags.append(first_element)
    if st.button('執行爬蟲') or len(crawl_result)>0:
        crawl_result  = app.crawl_url(
            url,
            params={
                "limit":page_limit,
                "scrapeOptions":{
                    "formats": ["markdown"],
                    "includeTags": includeTags,
                    "excludeTags": excludeTags
                }
            }
        )
        content = st.text_area("網頁內容",key="result_content",value=crawl_result["data"][0]["markdown"],height=680)

        final_chunks = []
        headers_to_split_on = [
            ("#", "H1"),
            ("##", "H2"),
            ("###", "H3"),
        ]
        markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on,return_each_line=True,strip_headers=True)
        splits = markdown_splitter.split_text(crawl_result["data"][0]["markdown"])
        chunk_size = 750
        chunk_overlap = 50
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        final_splits = text_splitter.split_documents(splits)
        latest_version =  get_max_version_for_name('vectorDB_tool','chunks',url)
        new_version = latest_version + 1
        for doc in final_splits:
            doc.metadata['file']=url
            doc.metadata['version'] = new_version
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
            st.success(f"url：『{url}』 版本：{new_version}   {result['msg']}")
        else:
            st.error(f"url：『{url}』 解析失敗： {result['msg']}")
        
    
    
scrawling_page()
