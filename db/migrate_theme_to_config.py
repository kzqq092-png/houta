import sqlite3
import os

themes_db = os.path.join(os.path.dirname(__file__), 'themes.db')
config_db = os.path.join(os.path.dirname(__file__), 'hikyuu_system.db')

conn1 = sqlite3.connect(themes_db)
conn2 = sqlite3.connect(config_db)
c1 = conn1.cursor()
c2 = conn2.cursor()

# 清空目标表
c2.execute('DELETE FROM themes')

# 迁移主题内容表
theme_rows = c1.execute('SELECT * FROM themes').fetchall()
for row in theme_rows:
    c2.execute('INSERT INTO themes (id, name, type, content, origin, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)', row)

# 迁移主题配置表
try:
    c1.execute('SELECT key, value FROM config')
    for row in c1.fetchall():
        c2.execute('INSERT OR REPLACE INTO theme_config (key, value) VALUES (?, ?)', row)
except Exception as e:
    print('config表迁移异常:', e)

conn2.commit()
conn1.close()
conn2.close()
print('主题数据迁移完成')
