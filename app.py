import streamlit as st

pdf_upload_page = st.Page("pdf_upload.py", title="PDF", icon=":material/add_circle:")
chunks_page = st.Page("chunks.py", title="Markdown", icon=":material/add_circle:")
edit_chunks_page = st.Page("edit_chunks.py", title="Chunks編輯", icon=":material/add_circle:")
scrawling_page = st.Page("scrawling.py", title="網路爬蟲", icon=":material/add_circle:")
create_vector_database = st.Page("create_vector_database.py", title="向量資料庫", icon=":material/add_circle:")
st.set_page_config(
    page_title="Markdown to Chunks",
    layout="wide"
)

pages = {
    "資料來源": [
        pdf_upload_page,
        scrawling_page
    ],
    "Chunks": [
        # chunks_page,
        edit_chunks_page
    ],
    "資料庫": [
        create_vector_database
    ]
}
pg = st.navigation(pages)
pg.run()