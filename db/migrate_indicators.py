#!/usr/bin/env python3
"""
指标数据迁移脚本
从 indicators.db 迁移所有数据到 hikyuu_system.db 的统一表结构中
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional


SOURCE_DB_PATH = os.path.join(os.path.dirname(__file__), 'indicators.db')
TARGET_DB_PATH = os.path.join(os.path.dirname(__file__), 'hikyuu_system.db')


def log_migration_status(target_conn, migration_name: str, status: str, error: str = None, data: Dict = None):
    """记录迁移状态"""
    cursor = target_conn.cursor()

    current_time = datetime.now().isoformat()
    migration_data = json.dumps(data) if data else None

    if status == 'running':
        cursor.execute('''
            INSERT OR REPLACE INTO migration_status 
            (migration_name, status, started_at, migration_data) 
            VALUES (?, ?, ?, ?)
        ''', (migration_name, status, current_time, migration_data))
    elif status == 'completed':
        cursor.execute('''
            UPDATE migration_status 
            SET status = ?, completed_at = ?, migration_data = ?
            WHERE migration_name = ?
        ''', (status, current_time, migration_data, migration_name))
    elif status == 'failed':
        cursor.execute('''
            UPDATE migration_status 
            SET status = ?, completed_at = ?, error_message = ?, migration_data = ?
            WHERE migration_name = ?
        ''', (status, current_time, error, migration_data, migration_name))

    target_conn.commit()


def check_source_database():
    """检查源数据库是否存在和可访问"""
    if not os.path.exists(SOURCE_DB_PATH):
        print(f"❌ 源数据库不存在: {SOURCE_DB_PATH}")
        return False

    try:
        conn = sqlite3.connect(SOURCE_DB_PATH)
        cursor = conn.cursor()

        # 检查必要的表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        required_tables = ['indicator_categories', 'indicators', 'indicator_parameters', 'indicator_implementations']
        missing_tables = [table for table in required_tables if table not in tables]

        if missing_tables:
            print(f"❌ 源数据库缺少必要的表: {missing_tables}")
            conn.close()
            return False

        conn.close()
        print("✅ 源数据库检查通过")
        return True

    except Exception as e:
        print(f"❌ 源数据库检查失败: {str(e)}")
        return False


def migrate_categories(source_conn, target_conn):
    """迁移指标分类数据"""
    print("📂 迁移指标分类数据...")

    log_migration_status(target_conn, 'categories', 'running')

    try:
        source_cursor = source_conn.cursor()
        target_cursor = target_conn.cursor()

        # 获取源数据
        source_cursor.execute('SELECT * FROM indicator_categories')
        categories = source_cursor.fetchall()

        migrated_count = 0
        for category in categories:
            try:
                # 检查是否已存在
                target_cursor.execute(
                    'SELECT id FROM indicator_categories WHERE id = ?', (category[0],)
                )
                existing = target_cursor.fetchone()

                if existing:
                    # 更新现有记录
                    target_cursor.execute('''
                        UPDATE indicator_categories 
                        SET name = ?, display_name = ?, description = ?, parent_id = ?
                        WHERE id = ?
                    ''', (category[1], category[2], category[3], category[4], category[0]))
                else:
                    # 插入新记录
                    target_cursor.execute('''
                        INSERT INTO indicator_categories 
                        (id, name, display_name, description, parent_id) 
                        VALUES (?, ?, ?, ?, ?)
                    ''', category[:5])

                migrated_count += 1

            except Exception as e:
                print(f"⚠️ 迁移分类 {category[0]} 失败: {str(e)}")

        target_conn.commit()

        migration_data = {
            'total_categories': len(categories),
            'migrated_count': migrated_count
        }

        log_migration_status(target_conn, 'categories', 'completed', data=migration_data)
        print(f"✅ 分类迁移完成: {migrated_count}/{len(categories)}")

        return True

    except Exception as e:
        error_msg = f"分类迁移失败: {str(e)}"
        log_migration_status(target_conn, 'categories', 'failed', error=error_msg)
        print(f"❌ {error_msg}")
        return False


def migrate_indicators(source_conn, target_conn):
    """迁移指标数据"""
    print("📈 迁移指标数据...")

    log_migration_status(target_conn, 'indicators', 'running')

    try:
        source_cursor = source_conn.cursor()
        target_cursor = target_conn.cursor()

        # 获取源数据
        source_cursor.execute('SELECT * FROM indicators')
        indicators = source_cursor.fetchall()

        migrated_count = 0
        for indicator in indicators:
            try:
                # 检查是否已存在
                target_cursor.execute(
                    'SELECT id FROM indicator WHERE name = ?', (indicator[1],)
                )
                existing = target_cursor.fetchone()

                if existing:
                    # 更新现有记录
                    target_cursor.execute('''
                        UPDATE indicator 
                        SET display_name = ?, category_id = ?, description = ?, 
                            formula = ?, output_names = ?, version = ?, is_builtin = ?
                        WHERE name = ?
                    ''', (indicator[2], indicator[3], indicator[4], indicator[5],
                          indicator[6], indicator[9], indicator[10], indicator[1]))

                    indicator_id = existing[0]
                else:
                    # 插入新记录
                    target_cursor.execute('''
                        INSERT INTO indicator 
                        (name, display_name, category_id, description, formula, output_names, version, is_builtin) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (indicator[1], indicator[2], indicator[3], indicator[4],
                          indicator[5], indicator[6], indicator[9], indicator[10]))

                    indicator_id = target_cursor.lastrowid

                # 记录指标ID映射，用于后续迁移参数和实现
                if not hasattr(migrate_indicators, 'id_mapping'):
                    migrate_indicators.id_mapping = {}
                migrate_indicators.id_mapping[indicator[0]] = indicator_id

                migrated_count += 1

            except Exception as e:
                print(f"⚠️ 迁移指标 {indicator[1]} 失败: {str(e)}")

        target_conn.commit()

        migration_data = {
            'total_indicators': len(indicators),
            'migrated_count': migrated_count,
            'id_mapping': migrate_indicators.id_mapping
        }

        log_migration_status(target_conn, 'indicators', 'completed', data=migration_data)
        print(f"✅ 指标迁移完成: {migrated_count}/{len(indicators)}")

        return True

    except Exception as e:
        error_msg = f"指标迁移失败: {str(e)}"
        log_migration_status(target_conn, 'indicators', 'failed', error=error_msg)
        print(f"❌ {error_msg}")
        return False


def migrate_parameters(source_conn, target_conn):
    """迁移指标参数数据"""
    print("⚙️ 迁移指标参数数据...")

    log_migration_status(target_conn, 'parameters', 'running')

    try:
        source_cursor = source_conn.cursor()
        target_cursor = target_conn.cursor()

        # 获取ID映射
        id_mapping = getattr(migrate_indicators, 'id_mapping', {})
        if not id_mapping:
            print("❌ 缺少指标ID映射，无法迁移参数")
            return False

        # 获取源数据
        source_cursor.execute('SELECT * FROM indicator_parameters')
        parameters = source_cursor.fetchall()

        migrated_count = 0
        for param in parameters:
            try:
                old_indicator_id = param[1]
                new_indicator_id = id_mapping.get(old_indicator_id)

                if not new_indicator_id:
                    print(f"⚠️ 找不到指标ID {old_indicator_id} 的映射")
                    continue

                # 检查参数是否已存在
                target_cursor.execute(
                    'SELECT id FROM indicator_parameters WHERE indicator_id = ? AND name = ?',
                    (new_indicator_id, param[2])
                )
                existing = target_cursor.fetchone()

                if existing:
                    # 更新现有记录
                    target_cursor.execute('''
                        UPDATE indicator_parameters 
                        SET description = ?, param_type = ?, default_value = ?, 
                            min_value = ?, max_value = ?, step_value = ?, choices = ?
                        WHERE indicator_id = ? AND name = ?
                    ''', (param[3], param[4], param[5], param[6], param[7],
                          param[8], param[9], new_indicator_id, param[2]))
                else:
                    # 插入新记录
                    target_cursor.execute('''
                        INSERT INTO indicator_parameters 
                        (indicator_id, name, description, param_type, default_value, 
                         min_value, max_value, step_value, choices) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (new_indicator_id, param[2], param[3], param[4], param[5],
                          param[6], param[7], param[8], param[9]))

                migrated_count += 1

            except Exception as e:
                print(f"⚠️ 迁移参数 {param[2]} 失败: {str(e)}")

        target_conn.commit()

        migration_data = {
            'total_parameters': len(parameters),
            'migrated_count': migrated_count
        }

        log_migration_status(target_conn, 'parameters', 'completed', data=migration_data)
        print(f"✅ 参数迁移完成: {migrated_count}/{len(parameters)}")

        return True

    except Exception as e:
        error_msg = f"参数迁移失败: {str(e)}"
        log_migration_status(target_conn, 'parameters', 'failed', error=error_msg)
        print(f"❌ {error_msg}")
        return False


def migrate_implementations(source_conn, target_conn):
    """迁移指标实现数据"""
    print("🔧 迁移指标实现数据...")

    log_migration_status(target_conn, 'implementations', 'running')

    try:
        source_cursor = source_conn.cursor()
        target_cursor = target_conn.cursor()

        # 获取ID映射
        id_mapping = getattr(migrate_indicators, 'id_mapping', {})
        if not id_mapping:
            print("❌ 缺少指标ID映射，无法迁移实现")
            return False

        # 获取源数据
        source_cursor.execute('SELECT * FROM indicator_implementations')
        implementations = source_cursor.fetchall()

        migrated_count = 0
        for impl in implementations:
            try:
                old_indicator_id = impl[1]
                new_indicator_id = id_mapping.get(old_indicator_id)

                if not new_indicator_id:
                    print(f"⚠️ 找不到指标ID {old_indicator_id} 的映射")
                    continue

                # 检查实现是否已存在
                target_cursor.execute(
                    'SELECT id FROM indicator_implementations WHERE indicator_id = ? AND engine = ?',
                    (new_indicator_id, impl[2])
                )
                existing = target_cursor.fetchone()

                if existing:
                    # 更新现有记录
                    target_cursor.execute('''
                        UPDATE indicator_implementations 
                        SET function_name = ?, implementation_code = ?, is_default = ?
                        WHERE indicator_id = ? AND engine = ?
                    ''', (impl[3], impl[4], impl[5], new_indicator_id, impl[2]))
                else:
                    # 插入新记录
                    target_cursor.execute('''
                        INSERT INTO indicator_implementations 
                        (indicator_id, engine, function_name, implementation_code, is_default) 
                        VALUES (?, ?, ?, ?, ?)
                    ''', (new_indicator_id, impl[2], impl[3], impl[4], impl[5]))

                migrated_count += 1

            except Exception as e:
                print(f"⚠️ 迁移实现 {impl[2]}.{impl[3]} 失败: {str(e)}")

        target_conn.commit()

        migration_data = {
            'total_implementations': len(implementations),
            'migrated_count': migrated_count
        }

        log_migration_status(target_conn, 'implementations', 'completed', data=migration_data)
        print(f"✅ 实现迁移完成: {migrated_count}/{len(implementations)}")

        return True

    except Exception as e:
        error_msg = f"实现迁移失败: {str(e)}"
        log_migration_status(target_conn, 'implementations', 'failed', error=error_msg)
        print(f"❌ {error_msg}")
        return False


def verify_migration(target_conn):
    """验证迁移结果"""
    print("🔍 验证迁移结果...")

    try:
        cursor = target_conn.cursor()

        # 检查各表的记录数
        tables_info = {}

        for table in ['indicator_categories', 'indicator', 'indicator_parameters', 'indicator_implementations']:
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            count = cursor.fetchone()[0]
            tables_info[table] = count

        print("📊 迁移统计:")
        for table, count in tables_info.items():
            print(f"  {table}: {count} 条记录")

        # 检查数据完整性
        cursor.execute('''
            SELECT i.name, i.display_name, c.display_name as category_name,
                   COUNT(DISTINCT p.id) as param_count,
                   COUNT(DISTINCT impl.id) as impl_count
            FROM indicator i
            LEFT JOIN indicator_categories c ON i.category_id = c.id
            LEFT JOIN indicator_parameters p ON i.id = p.indicator_id
            LEFT JOIN indicator_implementations impl ON i.id = impl.indicator_id
            GROUP BY i.id
            ORDER BY i.name
        ''')

        indicators_summary = cursor.fetchall()

        print("\n📈 指标完整性检查:")
        for ind in indicators_summary:
            print(f"  {ind[0]} ({ind[1]}) - 分类: {ind[2]}, 参数: {ind[3]}, 实现: {ind[4]}")

        # 检查是否有孤立的记录
        cursor.execute('''
            SELECT COUNT(*) FROM indicator_parameters p
            LEFT JOIN indicator i ON p.indicator_id = i.id
            WHERE i.id IS NULL
        ''')
        orphan_params = cursor.fetchone()[0]

        cursor.execute('''
            SELECT COUNT(*) FROM indicator_implementations impl
            LEFT JOIN indicator i ON impl.indicator_id = i.id
            WHERE i.id IS NULL
        ''')
        orphan_impls = cursor.fetchone()[0]

        if orphan_params > 0 or orphan_impls > 0:
            print(f"⚠️ 发现孤立记录: 参数 {orphan_params}, 实现 {orphan_impls}")
            return False

        print("✅ 数据完整性检查通过")
        return True

    except Exception as e:
        print(f"❌ 验证失败: {str(e)}")
        return False


def backup_old_database():
    """备份旧的indicators.db"""
    if os.path.exists(SOURCE_DB_PATH):
        backup_dir = os.path.join(os.path.dirname(__file__), 'backup')
        os.makedirs(backup_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(backup_dir, f'indicators_{timestamp}.db')

        import shutil
        shutil.copy2(SOURCE_DB_PATH, backup_path)
        print(f"✅ 旧数据库已备份到: {backup_path}")
        return backup_path
    return None


def main():
    """主函数"""
    print("🚀 开始指标数据迁移...")
    print("=" * 60)

    try:
        # 1. 检查源数据库
        if not check_source_database():
            return False

        # 2. 备份旧数据库
        old_backup = backup_old_database()

        # 3. 连接数据库
        source_conn = sqlite3.connect(SOURCE_DB_PATH)
        target_conn = sqlite3.connect(TARGET_DB_PATH)

        # 4. 执行迁移
        migration_steps = [
            ('分类数据', migrate_categories),
            ('指标数据', migrate_indicators),
            ('参数数据', migrate_parameters),
            ('实现数据', migrate_implementations),
        ]

        all_success = True
        for step_name, step_func in migration_steps:
            print(f"\n📋 执行: {step_name}")
            if not step_func(source_conn, target_conn):
                print(f"❌ {step_name} 迁移失败")
                all_success = False
                break

        # 5. 验证迁移结果
        if all_success:
            print(f"\n🔍 验证迁移结果...")
            if verify_migration(target_conn):
                print("\n🎉 所有数据迁移成功！")

                # 记录整体迁移完成状态
                log_migration_status(target_conn, 'full_migration', 'completed',
                                     data={'backup_path': old_backup})

                result = True
            else:
                print("\n❌ 迁移验证失败")
                result = False
        else:
            result = False

        # 6. 关闭连接
        source_conn.close()
        target_conn.close()

        return result

    except Exception as e:
        print(f"\n❌ 迁移过程发生错误: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False


if __name__ == '__main__':
    success = main()
    if success:
        print("\n✅ 阶段二：数据迁移完成")
        print("💡 下一步：更新服务层使用新的统一数据库")
    else:
        print("\n❌ 阶段二：数据迁移失败")
        print("💡 请检查错误信息并修复后重试")
