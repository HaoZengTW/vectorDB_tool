import sqlite3

# 連接數據庫（如果不存在則創建）
conn = sqlite3.connect('database/files.db')
c = conn.cursor()

# 創建表格
c.execute('''
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        version INTEGER,
        content TEXT
    )
''')

conn.commit()

# 創建表格
c.execute('''
    CREATE TABLE IF NOT EXISTS splits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        metadata TEXT, 
        page_content TEXT, 
        version INTEGER, 
        document_id INTEGER
    )
''')

conn.commit()


conn.close()
