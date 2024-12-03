from pymongo import MongoClient
from bson.objectid import ObjectId

def get_max_version_for_name(database_name, collection_name, file):
    """
    查詢指定 file 的最大 version 值
    
    :param database_name: 資料庫名稱
    :param collection_name: 集合名稱
    :param file: 要查詢的 file
    :return: 最大 version 值，若無對應資料，返回 None
    """
    # 連接 MongoDB
    client = MongoClient("mongodb://localhost:27017/")
    db = client[database_name]
    collection = db[collection_name]
    
    # 查詢 file 相同的最大 version
    result = collection.find({"metadata.file": file}, {"metadata.version": 1}).sort("metadata.version", -1).limit(1)
    
    # 提取結果
    max_version = 0
    for doc in result:
        max_version = doc.get("metadata")['version']
    
    client.close()
    return max_version

def insert_documents(database_name, collection_name, documents):
    """
    將一組 Document 寫入指定的資料庫集合中

    :param database_name: 資料庫名稱
    :param collection_name: 集合名稱
    :param documents: 要插入的 Document 陣列 (list of dict)
    :return: 插入結果，包括插入的 document ID 列表
    """

    # 連接 MongoDB
    client = MongoClient("mongodb://localhost:27017/")
    db = client[database_name]
    collection = db[collection_name]
    # 插入 Document 陣列
    try:
        result = collection.insert_many(documents)
        print(f"成功寫入 {len(result.inserted_ids)} 筆文件")
        return {'code':200,'msg':f"成功寫入 {len(result.inserted_ids)} 筆Chunks"}
    except Exception as e:
        print(f"插入過程中發生錯誤: {e}")
        return {'code':999,'msg':f"插入過程中發生錯誤: {e}"}
    finally:
        client.close()

def query_chunks_by_name_and_version(database_name, collection_name, file, version):
    """
    根據 file 和 version 查詢資料庫集合中的資料

    :param database_name: 資料庫名稱
    :param collection_name: 集合名稱
    :param file: 要查詢的文件名 (file)
    :param version: 要查詢的版本號 (version)
    :return: 查詢結果的文檔 (dict)，若無匹配資料返回 None
    """
    # 連接 MongoDB
    client = MongoClient("mongodb://localhost:27017/")
    db = client[database_name]
    collection = db[collection_name]
    
    try:
        # 查詢條件
        # query = {"file": file, "version": version}
        query = {"metadata.file": file, "metadata.version": version}
        
        # 查詢所有符合條件的文檔
        results = list(collection.find(query))
        
        if results:
            print(f"找到符合條件的文檔: {len(results)}")
            return {'code':200, 'msg':f"找到符合條件的文檔: {len(results)}", 'data':results}
        else:
            print(f"未找到符合條件的文檔: file={file}, version={version}")
            return {'code':201, 'msg':f"未找到符合條件的文檔: file={file}, version={version}"}
    except Exception as e:
        print(f"查詢過程中發生錯誤: {e}")
        return {'code':999, 'msg':f"查詢過程中發生錯誤: {e}"}
    finally:
        client.close()
        
def get_distinct_files(database_name, collection_name, column):
    """
    查詢集合中 metadata.file 欄位的所有唯一值

    :param database_name: 資料庫名稱
    :param collection_name: 集合名稱
    :param column: metadata 欄位名稱
    :return: 包含唯一 metadata.{column} 值的列表，若無結果返回空列表
    """
    # 連接 MongoDB
    client = MongoClient("mongodb://localhost:27017/")
    db = client[database_name]
    collection = db[collection_name]
    
    try:
        # 查詢 distinct 值
        distinct_files = collection.distinct(f"metadata.{column}")
        
        if distinct_files:
            print(f"找到 {len(distinct_files)} 個唯一的文件名")
            return {'code':200, 'data':distinct_files,'msg':f"找到 {len(distinct_files)} 個唯一的文件名"}
        else:
            print("未找到任何唯一的文件名")
            return {'code':200, 'data':[],'msg':"資料庫中沒有已上傳文件"}
    except Exception as e:
        print(f"查詢過程中發生錯誤: {e}")
        return {'code':999, 'msg':f"查詢過程中發生錯誤: {e}"}
    finally:
        client.close()

def delete_documents_by_ids(database_name, collection_name, id_list):
    """
    根據提供的 _id 列表刪除 MongoDB 集合中的數據

    :param database_name: 資料庫名稱
    :param collection_name: 集合名稱
    :param id_list: 要刪除的 _id 列表
    :return: 成功刪除的文檔數量
    """
    if not isinstance(id_list, list):
        raise ValueError("id_list 必須是列表")
    # 確保 id_list 中的元素是有效的 ObjectId
    try:
        object_ids = [ObjectId(id) for id in id_list]
    except Exception as e:
        raise ValueError(f"無效的 _id 格式: {e}")

    # 連接 MongoDB
    client = MongoClient("mongodb://localhost:27017/")
    db = client[database_name]
    collection = db[collection_name]

    try:
        # 刪除符合條件的文檔
        delete_result = collection.delete_many({"_id": {"$in": object_ids}})
        print(f"成功刪除 {delete_result.deleted_count} 筆文檔")
        return {'code':200, 'msg':f"成功刪除{delete_result.deleted_count} 筆文檔"}
    except Exception as e:
        print(f"刪除過程中發生錯誤: {e}")
        return {'code':999, 'msg':f"刪除過程中發生錯誤: {e}"}
    finally:
        client.close()

def batch_update_documents(database_name, collection_name, documents):
    """
    批次保存修改後的文檔到 MongoDB

    :param database_name: 資料庫名稱
    :param collection_name: 集合名稱
    :param documents: 包含修改後文檔的列表，每個文檔需包含 `_id` 字段
    :return: 成功更新的文檔數量
    """
    if not isinstance(documents, list):
        raise ValueError("documents 必須是列表")
    
    # 檢查每個文檔是否包含 _id 並且格式正確
    for doc in documents:
        if "_id" not in doc:
            raise ValueError("每個文檔必須包含 '_id'")
        if not ObjectId.is_valid(doc["_id"]):
            raise ValueError(f"無效的 _id 格式: {doc['_id']}")

    # 連接 MongoDB
    client = MongoClient("mongodb://localhost:27017/")
    db = client[database_name]
    collection = db[collection_name]

    updated_count = 0

    try:
        # 批量更新文檔
        for doc in documents:
            # 確保 _id 是 ObjectId 類型
            doc_id = ObjectId(doc["_id"])
            # 從文檔中移除 _id，因為 MongoDB 不允許更新 _id 本身
            updated_doc = {k: v for k, v in doc.items() if k != "_id"}
            # 更新文檔
            result = collection.update_one({"_id": doc_id}, {"$set": updated_doc})
            if result.modified_count > 0:
                updated_count += 1

        print(f"成功更新 {updated_count} 筆文檔")
        return {'code':200, 'msg':f"成功更新 {updated_count} 筆文檔"}
    except Exception as e:
        print(f"更新過程中發生錯誤: {e}")
        return {'code':999, 'msg':"更新過程中發生錯誤: {e}"}
    finally:
        client.close()