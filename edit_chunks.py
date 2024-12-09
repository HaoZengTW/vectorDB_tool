import os
import base64
import json
import streamlit as st
import pandas as pd
from tools.llm_chains import summarize_image, summarize_table
from tools.db_mongo import get_distinct_files, query_chunks_by_name_and_version, get_max_version_for_name, delete_documents_by_ids, batch_update_documents, insert_documents
import time
from bson import ObjectId


st.session_state.chunks = []
st.session_state.editMode = False
if "importMode" not in st.session_state:
    st.session_state.importMode = False
def handle_imported_json(json_data,version):
    imported_data = []
    for item in json_data:
        item["_id"] = str(ObjectId())  # Assign a new ObjectId if _id is missing
        if not item.get("page_content"):
            item["page_content"] = ""  # Default to empty string if page_content is missing
        item["metadata"]['version'] = version
        imported_data.append(item)
    return imported_data

def json_serializable(data):
    if isinstance(data, ObjectId):
        return str(data)
    raise TypeError("Type not serializable")

get_fileName_result = get_distinct_files('vectorDB_tool','chunks','file')
if get_fileName_result['code'] == 200:
    file_list = get_fileName_result['data']
else:
    st.error(get_fileName_result['msg'])

if file_list:
    selected_filename = st.selectbox("文檔名稱:", file_list)
    version = get_max_version_for_name('vectorDB_tool','chunks',selected_filename)
    query_chunks = query_chunks_by_name_and_version('vectorDB_tool','chunks', selected_filename, version)
    if query_chunks['code'] == 200:
        st.session_state.chunks = query_chunks['data']
    st.write(f'Chunks數量：{len(st.session_state.chunks)}')
    with st.expander('匯出/匯入'):
        st.download_button(label="下載JSON", data=json.dumps(st.session_state.chunks, indent=4, default=json_serializable), file_name=f"{selected_filename}_v{version}.json")
        uploaded_file = st.file_uploader("匯入JSON文件", type=["json"], on_change=lambda: st.session_state.update({"importMode": True}))
        if st.session_state.importMode and uploaded_file:
            try:
                uploaded_data = json.load(uploaded_file)
                processed_data = handle_imported_json(uploaded_data,version+1)
                insert_documents('vectorDB_tool', 'chunks', processed_data)
                st.success("匯入成功！")
                st.session_state.importMode = False
                st.rerun()
            except json.JSONDecodeError:
                st.error("JSON文件格式錯誤！")
                st.session_state.importMode = False
            except Exception as e:
                st.error(f"匯入過程中發生錯誤：{str(e)}")
                st.session_state.importMode = False
    df = pd.DataFrame(st.session_state.chunks)
    df['img'] = df['metadata'].apply(lambda x: f"data:image/png;base64,{x.get('original_content', '')}"  if isinstance(x, dict) else '')
    df['metadata'] =  df['metadata'].apply(lambda x: json.dumps(x, indent=4) if isinstance(x, dict) else str(x))
    df['selected'] = False
    
    # 删除逻辑
    if "confirm_delete" not in st.session_state:
        st.session_state.confirm_delete = False
    
    
          
    edited_df = st.data_editor(
        df, 
        use_container_width=True,
        column_order=('selected','page_content','img','metadata'),
        column_config={
            '_id': None,
            'img': st.column_config.ImageColumn("Image"
                ),
            'page_content': st.column_config.TextColumn(
                "內文",
                width='large'
            ),
            'metadata': st.column_config.TextColumn(
                "metadata",
                width='large'
            ),
            'selected': st.column_config.CheckboxColumn(
                "選擇",
                 width='small'
            )
        }
    )
    selected_rows = edited_df[edited_df['selected'] == True]
    col1, col2 = st.columns(2)
    with col1:
        # 新增数据
        if st.button("新增"):
            new_data = {
                "page_content": "",
                "metadata": {"version": version, "file": selected_filename, "type": "text"}
            }
            insert_documents('vectorDB_tool', 'chunks',[new_data])
            
            st.rerun()
        uploaded_file = st.file_uploader("新增圖片", type=["jpg", "jpeg", "png"])
        # 上传图片
        if uploaded_file and st.button("插入圖片"):
            try:
                encoded_image = base64.b64encode(uploaded_file.read()).decode('utf-8')
                new_image_data = {
                    "page_content": "",
                    "metadata":{
                        "version": version,
                        "file": selected_filename,
                        "type": "image",
                        "original_content": encoded_image
                    }
                }
                insert_documents('vectorDB_tool', 'chunks',[new_image_data])
            
                st.rerun()
            except Exception as e:
                st.error(f"圖片處理失敗：{str(e)}")
        # 保存功能
        if st.button("保存"):
            try:
                # 准备保存的数据
                save_data = []
                for _, row in edited_df.iterrows():
                    metadata_dict = json.loads(row['metadata'])  # 将 metadata 转回字典格式
                    save_data.append({
                        "_id": row['_id'],  # 保持原始 _id
                        "page_content": row['page_content'],
                        "metadata": metadata_dict  # 更新后的 metadata
                    })
                update_result = batch_update_documents('vectorDB_tool', 'chunks', save_data)
                if update_result['code'] == 200:
                    st.success("保存成功！")
                    st.rerun()
                else:
                    st.error(f"保存失敗：{update_result['msg']}")
            except json.JSONDecodeError:
                st.error("Metadata 格式錯誤，請確保為有效的 JSON 格式！")
            except Exception as e:
                st.error(f"保存過程中發生錯誤：{str(e)}")
        
        # 摘要全圖片
        if st.button("摘要全圖片"):
            for idx, row in edited_df.iterrows():
                metadata = json.loads(row['metadata'])
                if metadata.get('type') == 'image' and 'original_content' in metadata:
                    encoded_image = metadata['original_content']
                    summary = summarize_image(encoded_image)
                    edited_df.at[idx, 'page_content'] = summary
                    time.sleep(1)
            save_data = []
            for _, row in edited_df.iterrows():
                metadata_dict = json.loads(row['metadata'])  # 将 metadata 转回字典格式
                save_data.append({
                    "_id": row['_id'],  # 保持原始 _id
                    "page_content": row['page_content'],
                    "metadata": metadata_dict  # 更新后的 metadata
                })
            update_result = batch_update_documents('vectorDB_tool', 'chunks', save_data)
            if update_result['code'] == 200:
                st.success("保存成功！")
                st.rerun()
            else:
                st.error(f"保存失敗：{update_result['msg']}")
        # 摘要全表格
        if st.button("摘要全表格"):
            for idx, row in edited_df.iterrows():
                metadata = json.loads(row['metadata'])
                if metadata.get('type') == 'table' and 'page_content' in row:
                    metadata['original_data'] = row['page_content']
                    summary = summarize_table(metadata['original_data'])
                    edited_df.at[idx, 'page_content'] = summary
                    edited_df.at[idx, 'metadata'] = json.dumps(metadata, indent=4)
                    time.sleep(1)
            save_data = []
            for _, row in edited_df.iterrows():
                metadata_dict = json.loads(row['metadata'])  # 将 metadata 转回字典格式
                save_data.append({
                    "_id": row['_id'],  # 保持原始 _id
                    "page_content": row['page_content'],
                    "metadata": metadata_dict  # 更新后的 metadata
                })
            update_result = batch_update_documents('vectorDB_tool', 'chunks', save_data)
            if update_result['code'] == 200:
                st.success("保存成功！")
                st.rerun()
            else:
                st.error(f"保存失敗：{update_result['msg']}")
    with col2:
        
        if len(selected_rows) >0:
            # 刪除功能
            if st.button("刪除"):
                if not selected_rows.empty:
                    selected_ids = selected_rows['_id'].tolist()
                    del_res = delete_documents_by_ids('vectorDB_tool','chunks',selected_ids)
                    if del_res['code'] == 200:
                        st.success(del_res['msg'])
                        st.rerun()
                    else:
                        st.error(del_res['msg'])
                else:
                    st.warning("未選擇任何資料進行刪除！")
            
            # 摘要选取图片
            if st.button("摘要選取圖片"):
                for idx, row in edited_df.iterrows():
                    if row['selected'] == True:
                        metadata = json.loads(row['metadata'])
                        if metadata.get('type') == 'image' and 'original_content' in metadata:
                            encoded_image = metadata['original_content']
                            summary = summarize_image(encoded_image)
                            edited_df.at[idx, 'page_content'] = summary
                            time.sleep(1)
                save_data = []
                for _, row in edited_df.iterrows():
                    metadata_dict = json.loads(row['metadata'])  # 将 metadata 转回字典格式
                    save_data.append({
                        "_id": row['_id'],  # 保持原始 _id
                        "page_content": row['page_content'],
                        "metadata": metadata_dict  # 更新后的 metadata
                    })
                update_result = batch_update_documents('vectorDB_tool', 'chunks', save_data)
                if update_result['code'] == 200:
                    st.success("保存成功！")
                    st.rerun()
                else:
                    st.error(f"保存失敗：{update_result['msg']}")
                    
            # 摘要所选表格
            if st.button("摘要所選表格"):
                for idx, row in edited_df.iterrows():
                    if row['selected'] == True:
                        metadata = json.loads(row['metadata'])
                        if metadata.get('type') == 'table' and 'page_content' in row:
                            metadata['original_data'] = row['page_content']
                            summary = summarize_table(metadata['original_data'])
                            edited_df.at[idx, 'page_content'] = summary
                            edited_df.at[idx, 'metadata'] = json.dumps(metadata, indent=4)
                save_data = []
                for _, row in edited_df.iterrows():
                    metadata_dict = json.loads(row['metadata'])  # 将 metadata 转回字典格式
                    save_data.append({
                        "_id": row['_id'],  # 保持原始 _id
                        "page_content": row['page_content'],
                        "metadata": metadata_dict  # 更新后的 metadata
                    })
                update_result = batch_update_documents('vectorDB_tool', 'chunks', save_data)
                if update_result['code'] == 200:
                    st.success("保存成功！")
                    st.rerun()
                else:
                    st.error(f"保存失敗：{update_result['msg']}")
            # 合併功能
            if st.button("合併"):
                if not selected_rows.empty:
                    # 找到選取行中 index 最小的行
                    min_index = selected_rows.index.min()
                    merged_content = "\n ".join(selected_rows['page_content'])
                    edited_df.at[min_index, 'page_content'] = merged_content
                    # 移除除 index 最小外的其他選取行
                    selected_ids = selected_rows.loc[selected_rows.index != min_index, '_id'].tolist()
                    del_res = delete_documents_by_ids('vectorDB_tool','chunks',selected_ids)
                    if del_res['code'] == 200:
                        # 保存合併後的變更
                        save_data = []
                        for _, row in edited_df.iterrows():
                            metadata_dict = json.loads(row['metadata'])  # 将 metadata 转回字典格式
                            save_data.append({
                                "_id": row['_id'],  # 保持原始 _id
                                "page_content": row['page_content'],
                                "metadata": metadata_dict  # 更新后的 metadata
                            })
                        update_result = batch_update_documents('vectorDB_tool', 'chunks', save_data)
                        if update_result['code'] == 200:
                            st.success("合併成功並保存！")
                            st.rerun()
                        else:
                            st.error(f"保存失敗：{update_result['msg']}")
                    else:
                        st.error(del_res['msg'])
                else:
                    st.warning("未選擇任何資料進行合併！")

