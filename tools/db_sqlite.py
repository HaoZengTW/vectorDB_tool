import sqlite3

# 連接數據庫
def get_connection():
    conn = sqlite3.connect('database/files.db')
    return conn


# 獲取文件的最新版本號
def get_latest_version(filename):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT MAX(version) FROM files WHERE filename = ?', (filename,))
    result = c.fetchone()[0]
    conn.close()
    if result:
        return result
    else:
        return 0

# 保存文件信息到數據庫
def save_file(filename, version, content):
    conn = get_connection()
    c = conn.cursor()
    c.execute('INSERT INTO files (filename, version, content) VALUES (?, ?, ?)', (filename, version, content))
    conn.commit()
    conn.close()
    
# 取得資料庫中已上傳文本名稱清單
def get_distinct_file():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT filename FROM files")
    res = [row[0] for row in cursor.fetchall()]
    conn.close()
    return res

# 取得資料庫中最新版文本
def get_latest_content(fileNwme):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
            SELECT content FROM files
            WHERE filename = ?
            ORDER BY version DESC
            LIMIT 1
        """, (fileNwme,))
    res = cursor.fetchone()
    
    conn.close()
    return res

# Get the document ID for the selected filename
def get_selected_file_id(fileNwme):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM files WHERE filename = ? ORDER BY version DESC LIMIT 1", (fileNwme,))
    document_id_result = cursor.fetchone()
    document_id = document_id_result[0] if document_id_result else None
    conn.close()
    return document_id

# Increment version for the new splits
def get_latest_splits_version(document_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(version) FROM splits WHERE document_id = ?", (document_id,))
    version_result = cursor.fetchone()
    conn.close()
    return version_result

# Save splits to the database
def save_splits(metadata, page_content, new_version,document_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO splits (metadata, page_content, version, document_id)
        VALUES (?, ?, ?, ?)
        """,
        (str(metadata), page_content, new_version, document_id)
    )
    conn.commit()
    conn.close()

# get splits from the database
def get_splits(document_id, version):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT page_content,metadata  FROM splits WHERE document_id = ? and version = ?", (document_id,version))
    result = cursor.fetchall()
    conn.close()
    return result

def del_splits(document_id, version):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM splits WHERE document_id = ? and version = ?", (document_id,version)
    )
    conn.commit()
    conn.close()
