import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'hikyuu_system.db')


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # 1. 系统配置表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS config (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    # 2. 数据源表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS data_source (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        type TEXT,
        config TEXT,
        is_active INTEGER DEFAULT 0
    )''')
    # 3. 用户收藏表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        fav_type TEXT,
        fav_key TEXT,
        fav_value TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    # 4. 行业表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS industry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        parent_id INTEGER,
        level INTEGER,
        extra TEXT
    )''')
    # 5. 市场表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS market (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        code TEXT UNIQUE,
        region TEXT,
        extra TEXT
    )''')
    # 6. 股票表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE,
        name TEXT,
        market_code TEXT,
        type TEXT,
        valid INTEGER,
        start_date TEXT,
        end_date TEXT,
        industry_id INTEGER,
        extra TEXT
    )''')
    # 7. 概念表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS concept (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE,
        name TEXT,
        extra TEXT
    )''')
    # 8. 指标表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS indicator (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        category TEXT,
        params TEXT,
        extra TEXT
    )''')
    # 9. 用户日志表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        action TEXT,
        detail TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    # 10. 历史记录表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        record_type TEXT,
        record_key TEXT,
        record_value TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()


if __name__ == '__main__':
    init_db()
    print('数据库初始化完成')
