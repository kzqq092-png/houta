#!/usr/bin/env python3
"""
统一数据库初始化脚本
在 hikyuu_system.db 中创建完整的指标系统表结构，支持技术指标和形态识别
"""

import sqlite3
import os
import json
from datetime import datetime


DB_PATH = os.path.join(os.path.dirname(__file__), 'hikyuu_system.db')


def backup_database():
    """备份现有数据库"""
    if os.path.exists(DB_PATH):
        backup_dir = os.path.join(os.path.dirname(__file__), 'backup')
        os.makedirs(backup_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(backup_dir, f'hikyuu_system_{timestamp}.db')

        import shutil
        shutil.copy2(DB_PATH, backup_path)
        print(f"✅ 数据库已备份到: {backup_path}")
        return backup_path
    return None


def create_unified_indicator_tables(conn):
    """创建统一的指标系统表结构"""
    cursor = conn.cursor()

    print("📊 创建指标分类表...")
    # 1. 指标分类表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS indicator_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,              -- 分类英文名 (trend, oscillator)
        display_name TEXT NOT NULL,             -- 分类显示名 (趋势类, 震荡类)
        description TEXT,                       -- 分类描述
        parent_id INTEGER,                      -- 父分类ID（支持层级）
        sort_order INTEGER DEFAULT 0,          -- 排序顺序
        is_active BOOLEAN DEFAULT 1,           -- 是否启用
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (parent_id) REFERENCES indicator_categories (id)
    )''')

    print("📈 创建统一指标表...")
    # 2. 备份并重建指标表
    cursor.execute('ALTER TABLE indicator RENAME TO indicator_old')

    cursor.execute('''
    CREATE TABLE indicator (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,              -- 指标英文名 (MA, MACD)
        display_name TEXT NOT NULL,             -- 指标显示名 (移动平均线)
        category_id INTEGER NOT NULL,           -- 分类ID，关联indicator_categories
        description TEXT NOT NULL,              -- 指标描述
        formula TEXT,                           -- 计算公式
        output_names TEXT NOT NULL,             -- JSON格式的输出列名
        version TEXT DEFAULT '1.0.0',          -- 版本号
        is_builtin BOOLEAN DEFAULT 1,          -- 是否内置指标
        is_active BOOLEAN DEFAULT 1,           -- 是否启用
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (category_id) REFERENCES indicator_categories (id)
    )''')

    print("⚙️ 创建指标参数表...")
    # 3. 指标参数表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS indicator_parameters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        indicator_id INTEGER NOT NULL,
        name TEXT NOT NULL,                     -- 参数名 (timeperiod, fastperiod)
        description TEXT NOT NULL,              -- 参数描述
        param_type TEXT NOT NULL,               -- 参数类型 (int, float, string)
        default_value TEXT NOT NULL,            -- JSON格式的默认值
        min_value TEXT,                         -- JSON格式的最小值
        max_value TEXT,                         -- JSON格式的最大值
        step_value TEXT,                        -- JSON格式的步长
        choices TEXT,                           -- JSON格式的选择项
        is_required BOOLEAN DEFAULT 1,         -- 是否必需
        sort_order INTEGER DEFAULT 0,          -- 排序顺序
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (indicator_id) REFERENCES indicator (id) ON DELETE CASCADE,
        UNIQUE (indicator_id, name)
    )''')

    print("🔧 创建指标实现表...")
    # 4. 指标实现表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS indicator_implementations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        indicator_id INTEGER NOT NULL,
        engine TEXT NOT NULL,                   -- 计算引擎 (talib, pandas, custom)
        function_name TEXT NOT NULL,            -- 函数名
        implementation_code TEXT,               -- 实现代码（自定义引擎）
        is_default BOOLEAN DEFAULT 0,          -- 是否默认实现
        priority INTEGER DEFAULT 0,            -- 优先级（数字越大越优先）
        performance_score REAL DEFAULT 0.0,    -- 性能评分
        is_active BOOLEAN DEFAULT 1,           -- 是否启用
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (indicator_id) REFERENCES indicator (id) ON DELETE CASCADE,
        UNIQUE (indicator_id, engine)
    )''')

    print("📊 扩展形态类型表...")
    # 5. 扩展现有 pattern_types 表
    try:
        cursor.execute('ALTER TABLE pattern_types ADD COLUMN algorithm_code TEXT')
    except sqlite3.OperationalError:
        pass  # 字段已存在

    try:
        cursor.execute('ALTER TABLE pattern_types ADD COLUMN parameters TEXT')
    except sqlite3.OperationalError:
        pass  # 字段已存在

    try:
        cursor.execute('ALTER TABLE pattern_types ADD COLUMN category_id INTEGER DEFAULT 5')
    except sqlite3.OperationalError:
        pass  # 字段已存在

    # 6. 创建指标组合表增强版
    cursor.execute('DROP TABLE IF EXISTS indicator_combination')
    cursor.execute('''
    CREATE TABLE indicator_combination (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,                     -- 组合名称
        user_id TEXT,                           -- 用户ID
        combination_type TEXT DEFAULT 'custom', -- 组合类型 (builtin, custom, strategy)
        indicators TEXT NOT NULL,               -- JSON格式的指标配置
        patterns TEXT,                          -- JSON格式的形态配置
        description TEXT,                       -- 组合描述
        is_active BOOLEAN DEFAULT 1,           -- 是否启用
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        extra TEXT                              -- 扩展字段
    )''')

    print("📋 创建视图和索引...")
    # 7. 创建便于查询的视图
    cursor.execute('''
    CREATE VIEW IF NOT EXISTS v_indicators_full AS
    SELECT 
        i.id,
        i.name,
        i.display_name,
        i.description,
        i.formula,
        i.output_names,
        i.version,
        i.is_builtin,
        i.is_active,
        c.name AS category_name,
        c.display_name AS category_display_name,
        COUNT(ip.id) AS param_count,
        COUNT(ii.id) AS implementation_count
    FROM indicator i
    LEFT JOIN indicator_categories c ON i.category_id = c.id
    LEFT JOIN indicator_parameters ip ON i.id = ip.indicator_id
    LEFT JOIN indicator_implementations ii ON i.id = ii.indicator_id
    GROUP BY i.id
    ''')

    # 8. 创建性能索引
    indexes = [
        'CREATE INDEX IF NOT EXISTS idx_indicator_name ON indicator(name)',
        'CREATE INDEX IF NOT EXISTS idx_indicator_category ON indicator(category_id)',
        'CREATE INDEX IF NOT EXISTS idx_indicator_active ON indicator(is_active)',
        'CREATE INDEX IF NOT EXISTS idx_indicator_params_indicator ON indicator_parameters(indicator_id)',
        'CREATE INDEX IF NOT EXISTS idx_indicator_impl_indicator ON indicator_implementations(indicator_id)',
        'CREATE INDEX IF NOT EXISTS idx_indicator_impl_engine ON indicator_implementations(engine)',
        'CREATE INDEX IF NOT EXISTS idx_pattern_types_category ON pattern_types(category_id)',
        'CREATE INDEX IF NOT EXISTS idx_pattern_types_active ON pattern_types(is_active)'
    ]

    for index_sql in indexes:
        cursor.execute(index_sql)

    conn.commit()
    print("✅ 统一指标表结构创建完成")


def insert_default_categories(conn):
    """插入默认的指标分类数据"""
    cursor = conn.cursor()

    print("📂 插入默认指标分类...")
    categories = [
        (1, 'trend', '趋势类', '用于判断市场趋势方向的指标', None, 1),
        (2, 'oscillator', '震荡类', '用于判断市场超买超卖状态的指标', None, 2),
        (3, 'volume', '成交量类', '基于成交量分析的指标', None, 3),
        (4, 'volatility', '波动性类', '用于衡量市场波动程度的指标', None, 4),
        (5, 'pattern', '形态类', 'K线形态和图表形态识别', None, 5),
        (6, 'momentum', '动量类', '价格动量和变化率指标', None, 6),
        (7, 'other', '其他', '其他类型的技术指标', None, 99)
    ]

    cursor.executemany('''
        INSERT OR REPLACE INTO indicator_categories 
        (id, name, display_name, description, parent_id, sort_order) 
        VALUES (?, ?, ?, ?, ?, ?)
    ''', categories)

    # 更新 pattern_types 表的 category_id
    cursor.execute('''
        UPDATE pattern_types 
        SET category_id = 5 
        WHERE category_id IS NULL OR category_id = 0
    ''')

    conn.commit()
    print(f"✅ 插入了 {len(categories)} 个默认分类")


def create_migration_functions(conn):
    """创建数据迁移辅助函数"""
    cursor = conn.cursor()

    print("🔧 创建迁移辅助表...")
    # 创建迁移状态表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS migration_status (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        migration_name TEXT NOT NULL UNIQUE,
        status TEXT NOT NULL,                   -- pending, running, completed, failed
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        error_message TEXT,
        migration_data TEXT                     -- JSON格式的迁移数据
    )''')

    conn.commit()
    print("✅ 迁移辅助表创建完成")


def verify_table_structure(conn):
    """验证表结构是否正确创建"""
    cursor = conn.cursor()

    print("🔍 验证表结构...")

    # 检查必要的表是否存在
    required_tables = [
        'indicator_categories',
        'indicator',
        'indicator_parameters',
        'indicator_implementations',
        'pattern_types',
        'migration_status'
    ]

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = [row[0] for row in cursor.fetchall()]

    missing_tables = []
    for table in required_tables:
        if table not in existing_tables:
            missing_tables.append(table)

    if missing_tables:
        print(f"❌ 缺少表: {missing_tables}")
        return False

    # 检查关键字段是否存在
    cursor.execute("PRAGMA table_info(indicator)")
    indicator_columns = [col[1] for col in cursor.fetchall()]
    required_columns = ['id', 'name', 'display_name', 'category_id', 'description']

    missing_columns = []
    for col in required_columns:
        if col not in indicator_columns:
            missing_columns.append(col)

    if missing_columns:
        print(f"❌ indicator表缺少字段: {missing_columns}")
        return False

    print("✅ 表结构验证通过")
    return True


def main():
    """主函数"""
    print("🚀 开始统一数据库初始化...")
    print("=" * 60)

    try:
        # 1. 备份现有数据库
        backup_path = backup_database()

        # 2. 连接数据库
        conn = sqlite3.connect(DB_PATH)

        # 3. 创建统一指标表结构
        create_unified_indicator_tables(conn)

        # 4. 插入默认分类数据
        insert_default_categories(conn)

        # 5. 创建迁移辅助功能
        create_migration_functions(conn)

        # 6. 验证表结构
        if verify_table_structure(conn):
            print("\n🎉 统一数据库初始化成功！")
            print(f"📍 数据库位置: {DB_PATH}")
            if backup_path:
                print(f"🔒 备份位置: {backup_path}")
        else:
            print("\n❌ 表结构验证失败")
            return False

        conn.close()
        return True

    except Exception as e:
        print(f"\n❌ 初始化失败: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False


if __name__ == '__main__':
    success = main()
    if success:
        print("\n✅ 阶段一：数据库表结构升级完成")
    else:
        print("\n❌ 阶段一：数据库表结构升级失败")
