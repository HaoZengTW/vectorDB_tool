import streamlit as st
from dotenv import load_dotenv
import os
from firecrawl import FirecrawlApp
from tools.db_sqlite import get_latest_version, save_file

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
    if st.button('執行爬蟲') or len(crawl_result)>0:
        crawl_result  = app.crawl_url(
            url,
            params={
                "limit":page_limit,
                "scrapeOptions":{
                    "formats": ["markdown"]
                }
            }
        )
        content = st.text_area("網頁內容",key="result_content",value=crawl_result["data"][0]["markdown"],height=680)

        latest_version = get_latest_version(url)
        new_version = latest_version + 1
        save_file("網頁爬蟲_"+url, new_version, content)
        st.success(f'{url} 已保存為版本 {new_version}')
        
    
    
scrawling_page()
