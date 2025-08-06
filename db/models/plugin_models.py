"""
HIkyuu 插件管理数据库模型

专业级插件管理系统，支持：
- 插件注册与生命周期管理
- 状态持久化存储
- 依赖关系管理
- 配置版本控制
- 远程管理支持
- 性能监控数据
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


class PluginStatus(Enum):
    """插件状态枚举"""
    UNLOADED = "unloaded"
    LOADED = "loaded"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"
    INSTALLING = "installing"
    UPDATING = "updating"
    UNINSTALLING = "uninstalling"


class PluginType(Enum):
    """插件类型枚举"""
    INDICATOR = "indicator"
    STRATEGY = "strategy"
    DATA_SOURCE = "data_source"
    ANALYSIS = "analysis"
    UI_COMPONENT = "ui_component"
    EXPORT = "export"
    NOTIFICATION = "notification"
    CHART_TOOL = "chart_tool"


@dataclass
class PluginRecord:
    """插件记录数据类"""
    id: Optional[int] = None
    name: str = ""
    display_name: str = ""
    version: str = "1.0.0"
    plugin_type: str = PluginType.ANALYSIS.value
    status: str = PluginStatus.UNLOADED.value
    description: str = ""
    author: str = ""
    email: str = ""
    homepage: str = ""
    repository: str = ""
    license: str = "MIT"
    tags: str = ""  # JSON array
    install_path: str = ""
    entry_point: str = ""
    config_schema: str = "{}"  # JSON schema
    dependencies: str = "[]"  # JSON array
    compatibility: str = "{}"  # JSON object
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_enabled_at: Optional[str] = None
    install_size: int = 0
    checksum: str = ""
    remote_url: str = ""
    auto_update: bool = False
    priority: int = 100


class PluginDatabaseManager:
    """插件数据库管理器"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """初始化插件相关数据库表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 1. 插件注册表 - 核心插件信息
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS plugins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,  -- 插件唯一标识符
                display_name TEXT NOT NULL,  -- 显示名称
                version TEXT NOT NULL DEFAULT '1.0.0',
                plugin_type TEXT NOT NULL DEFAULT 'analysis',
                status TEXT NOT NULL DEFAULT 'unloaded',
                description TEXT DEFAULT '',
                author TEXT DEFAULT '',
                email TEXT DEFAULT '',
                homepage TEXT DEFAULT '',
                repository TEXT DEFAULT '',
                license TEXT DEFAULT 'MIT',
                tags TEXT DEFAULT '[]',  -- JSON数组: ["AI", "量化", "技术分析"]
                install_path TEXT DEFAULT '',
                entry_point TEXT DEFAULT '',  -- 入口点: module.class
                config_schema TEXT DEFAULT '{}',  -- JSON配置模式
                dependencies TEXT DEFAULT '[]',  -- JSON依赖数组
                compatibility TEXT DEFAULT '{}',  -- 兼容性信息
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_enabled_at TIMESTAMP,
                install_size INTEGER DEFAULT 0,
                checksum TEXT DEFAULT '',  -- 文件校验和
                remote_url TEXT DEFAULT '',  -- 远程更新URL
                auto_update BOOLEAN DEFAULT 0,
                priority INTEGER DEFAULT 100  -- 加载优先级
            )''')

            # 2. 插件状态历史表 - 状态变更记录
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS plugin_status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plugin_id INTEGER NOT NULL,
                old_status TEXT,
                new_status TEXT NOT NULL,
                reason TEXT DEFAULT '',  -- 状态变更原因
                error_message TEXT DEFAULT '',  -- 错误信息
                changed_by TEXT DEFAULT 'system',  -- 操作者
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (plugin_id) REFERENCES plugins (id) ON DELETE CASCADE
            )''')

            # 3. 插件配置表 - 动态配置存储
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS plugin_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plugin_id INTEGER NOT NULL,
                config_key TEXT NOT NULL,
                config_value TEXT NOT NULL,  -- JSON值
                config_type TEXT DEFAULT 'user',  -- user/system/default
                version INTEGER DEFAULT 1,
                description TEXT DEFAULT '',
                is_encrypted BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (plugin_id) REFERENCES plugins (id) ON DELETE CASCADE,
                UNIQUE(plugin_id, config_key, config_type)
            )''')

            # 4. 插件依赖关系表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS plugin_dependencies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plugin_id INTEGER NOT NULL,
                dependency_name TEXT NOT NULL,  -- 依赖名称
                dependency_version TEXT DEFAULT '*',  -- 版本约束
                dependency_type TEXT DEFAULT 'required',  -- required/optional
                resolved_version TEXT DEFAULT '',  -- 实际解析版本
                is_satisfied BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (plugin_id) REFERENCES plugins (id) ON DELETE CASCADE
            )''')

            # 5. 插件性能监控表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS plugin_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plugin_id INTEGER NOT NULL,
                metric_name TEXT NOT NULL,  -- load_time/memory_usage/cpu_usage/error_count
                metric_value REAL NOT NULL,
                metric_unit TEXT DEFAULT '',  -- ms/MB/%/count
                measurement_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_id TEXT DEFAULT '',  -- 会话标识
                additional_data TEXT DEFAULT '{}',  -- 额外数据JSON
                FOREIGN KEY (plugin_id) REFERENCES plugins (id) ON DELETE CASCADE
            )''')

            # 6. 插件事件日志表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS plugin_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plugin_id INTEGER,
                event_type TEXT NOT NULL,  -- load/enable/disable/error/config_change
                event_level TEXT DEFAULT 'INFO',  -- DEBUG/INFO/WARNING/ERROR
                event_message TEXT NOT NULL,
                event_data TEXT DEFAULT '{}',  -- 事件详细数据JSON
                user_agent TEXT DEFAULT '',  -- 客户端标识
                session_id TEXT DEFAULT '',
                ip_address TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (plugin_id) REFERENCES plugins (id) ON DELETE SET NULL
            )''')

            # 7. 插件权限表 - 远程管理支持
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS plugin_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plugin_id INTEGER NOT NULL,
                permission_name TEXT NOT NULL,  -- file_access/network_access/system_access
                permission_level TEXT DEFAULT 'read',  -- read/write/execute
                granted_by TEXT DEFAULT 'system',
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (plugin_id) REFERENCES plugins (id) ON DELETE CASCADE,
                UNIQUE(plugin_id, permission_name)
            )''')

            # 8. 插件市场缓存表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS plugin_market_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plugin_name TEXT NOT NULL,
                market_data TEXT NOT NULL,  -- JSON市场信息
                downloads_count INTEGER DEFAULT 0,
                rating REAL DEFAULT 0.0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                cache_expires_at TIMESTAMP,
                UNIQUE(plugin_name)
            )''')

            # 创建索引优化查询性能
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_plugins_status ON plugins(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_plugins_type ON plugins(plugin_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_plugins_priority ON plugins(priority)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_plugin_events_type ON plugin_events(event_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_plugin_performance_metric ON plugin_performance(metric_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_plugin_configs_type ON plugin_configs(config_type)')

            conn.commit()
            conn.close()

            logger.info("插件数据库表初始化完成")

        except Exception as e:
            logger.error(f"初始化插件数据库失败: {e}")
            raise

    def register_plugin(self, plugin_record: PluginRecord) -> int:
        """注册插件到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO plugins (
                    name, display_name, version, plugin_type, status, description,
                    author, email, homepage, repository, license, tags,
                    install_path, entry_point, config_schema, dependencies,
                    compatibility, install_size, checksum, remote_url,
                    auto_update, priority, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                plugin_record.name, plugin_record.display_name, plugin_record.version,
                plugin_record.plugin_type, plugin_record.status, plugin_record.description,
                plugin_record.author, plugin_record.email, plugin_record.homepage,
                plugin_record.repository, plugin_record.license, plugin_record.tags,
                plugin_record.install_path, plugin_record.entry_point,
                plugin_record.config_schema, plugin_record.dependencies,
                plugin_record.compatibility, plugin_record.install_size,
                plugin_record.checksum, plugin_record.remote_url,
                plugin_record.auto_update, plugin_record.priority,
                datetime.now().isoformat()
            ))

            plugin_id = cursor.lastrowid
            conn.commit()
            conn.close()

            logger.info(f"插件注册成功: {plugin_record.name} (ID: {plugin_id})")
            return plugin_id

        except Exception as e:
            logger.error(f"注册插件失败: {e}")
            raise

    def update_plugin_status(self, plugin_name: str, new_status: PluginStatus,
                             reason: str = "", error_message: str = "") -> bool:
        """更新插件状态"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 获取当前状态
            cursor.execute('SELECT id, status FROM plugins WHERE name = ?', (plugin_name,))
            result = cursor.fetchone()

            if not result:
                logger.warning(f"插件不存在: {plugin_name}")
                return False

            plugin_id, old_status = result
            new_status_str = new_status.value

            # 更新插件状态
            update_fields = ['status = ?', 'updated_at = ?']
            update_values = [new_status_str, datetime.now().isoformat()]

            if new_status == PluginStatus.ENABLED:
                update_fields.append('last_enabled_at = ?')
                update_values.append(datetime.now().isoformat())

            cursor.execute(f'''
                UPDATE plugins 
                SET {', '.join(update_fields)}
                WHERE name = ?
            ''', update_values + [plugin_name])

            # 记录状态变更历史
            cursor.execute('''
                INSERT INTO plugin_status_history (
                    plugin_id, old_status, new_status, reason, error_message
                ) VALUES (?, ?, ?, ?, ?)
            ''', (plugin_id, old_status, new_status_str, reason, error_message))

            # 记录事件日志
            cursor.execute('''
                INSERT INTO plugin_events (
                    plugin_id, event_type, event_level, event_message, event_data
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                plugin_id, 'status_change', 'INFO',
                f"状态从 {old_status} 变更为 {new_status_str}",
                json.dumps({"old_status": old_status, "new_status": new_status_str, "reason": reason})
            ))

            conn.commit()
            conn.close()

            logger.info(f"插件状态更新成功: {plugin_name} -> {new_status_str}")
            return True

        except Exception as e:
            logger.error(f"更新插件状态失败: {e}")
            return False

    def get_plugin_status(self, plugin_name: str) -> Optional[PluginStatus]:
        """获取插件状态"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('SELECT status FROM plugins WHERE name = ?', (plugin_name,))
            result = cursor.fetchone()
            conn.close()

            if result:
                return PluginStatus(result[0])
            return None

        except Exception as e:
            logger.error(f"获取插件状态失败: {e}")
            return None

    def get_all_plugins(self) -> List[Dict[str, Any]]:
        """获取所有插件信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, name, display_name, version, plugin_type, status, description,
                       author, email, homepage, repository, license, tags, install_path,
                       entry_point, created_at, updated_at, last_enabled_at, priority
                FROM plugins 
                ORDER BY priority ASC, name ASC
            ''')

            columns = [desc[0] for desc in cursor.description]
            plugins = []

            for row in cursor.fetchall():
                plugin_dict = dict(zip(columns, row))
                # 解析JSON字段
                try:
                    plugin_dict['tags'] = json.loads(plugin_dict['tags'] or '[]')
                except:
                    plugin_dict['tags'] = []

                plugins.append(plugin_dict)

            conn.close()
            return plugins

        except Exception as e:
            logger.error(f"获取所有插件信息失败: {e}")
            return []

    def get_plugins_by_status(self, status: PluginStatus) -> List[Dict[str, Any]]:
        """根据状态获取插件列表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT name, display_name, version, plugin_type, status, description, author
                FROM plugins 
                WHERE status = ?
                ORDER BY priority ASC, name ASC
            ''', (status.value,))

            columns = [desc[0] for desc in cursor.description]
            plugins = [dict(zip(columns, row)) for row in cursor.fetchall()]

            conn.close()
            return plugins

        except Exception as e:
            logger.error(f"根据状态获取插件失败: {e}")
            return []

    def get_plugin_performance_metrics(self, plugin_name: str,
                                       metric_name: str = None,
                                       limit: int = 100) -> List[Dict[str, Any]]:
        """获取插件性能指标"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            base_query = '''
                SELECT pm.metric_name, pm.metric_value, pm.metric_unit, 
                       pm.measurement_time, pm.additional_data
                FROM plugin_performance pm
                JOIN plugins p ON pm.plugin_id = p.id
                WHERE p.name = ?
            '''

            params = [plugin_name]

            if metric_name:
                base_query += ' AND pm.metric_name = ?'
                params.append(metric_name)

            base_query += ' ORDER BY pm.measurement_time DESC LIMIT ?'
            params.append(limit)

            cursor.execute(base_query, params)

            columns = [desc[0] for desc in cursor.description]
            metrics = [dict(zip(columns, row)) for row in cursor.fetchall()]

            conn.close()
            return metrics

        except Exception as e:
            logger.error(f"获取插件性能指标失败: {e}")
            return []

    def record_plugin_performance(self, plugin_name: str, metric_name: str,
                                  metric_value: float, metric_unit: str = "",
                                  additional_data: Dict[str, Any] = None) -> bool:
        """记录插件性能指标"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 获取插件ID
            cursor.execute('SELECT id FROM plugins WHERE name = ?', (plugin_name,))
            result = cursor.fetchone()

            if not result:
                return False

            plugin_id = result[0]

            cursor.execute('''
                INSERT INTO plugin_performance (
                    plugin_id, metric_name, metric_value, metric_unit, additional_data
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                plugin_id, metric_name, metric_value, metric_unit,
                json.dumps(additional_data or {})
            ))

            conn.commit()
            conn.close()

            return True

        except Exception as e:
            logger.error(f"记录插件性能指标失败: {e}")
            return False

    def delete_plugin(self, plugin_name: str) -> bool:
        """
        删除插件及其相关记录

        Args:
            plugin_name: 插件名称

        Returns:
            bool: 是否删除成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 先获取插件ID
            cursor.execute('SELECT id FROM plugins WHERE name = ?', (plugin_name,))
            row = cursor.fetchone()

            if not row:
                logger.warning(f"插件 {plugin_name} 不存在于数据库中")
                conn.close()
                return True  # 不存在也算成功

            plugin_id = row[0]

            # 删除相关的性能记录
            cursor.execute('DELETE FROM plugin_performance WHERE plugin_id = ?', (plugin_id,))
            performance_deleted = cursor.rowcount

            # 删除相关的事件日志
            cursor.execute('DELETE FROM plugin_events WHERE plugin_id = ?', (plugin_id,))
            events_deleted = cursor.rowcount

            # 删除插件状态历史
            cursor.execute('DELETE FROM plugin_status_history WHERE plugin_id = ?', (plugin_id,))
            history_deleted = cursor.rowcount

            # 最后删除插件记录
            cursor.execute('DELETE FROM plugins WHERE id = ?', (plugin_id,))

            if cursor.rowcount == 0:
                logger.error(f"删除插件记录失败: {plugin_name}")
                conn.rollback()
                conn.close()
                return False

            conn.commit()
            conn.close()

            logger.info(f"插件 {plugin_name} 已完全删除: "
                        f"性能记录 {performance_deleted} 条, "
                        f"事件日志 {events_deleted} 条, "
                        f"状态历史 {history_deleted} 条")
            return True

        except Exception as e:
            logger.error(f"删除插件失败: {plugin_name}, 错误: {e}")
            return False

    def cleanup_old_records(self, days: int = 30) -> bool:
        """清理旧记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cutoff_date = datetime.now().replace(day=datetime.now().day - days).isoformat()

            # 清理旧的性能记录
            cursor.execute('''
                DELETE FROM plugin_performance 
                WHERE measurement_time < ?
            ''', (cutoff_date,))

            # 清理旧的事件日志
            cursor.execute('''
                DELETE FROM plugin_events 
                WHERE created_at < ? AND event_level != 'ERROR'
            ''', (cutoff_date,))

            deleted_performance = cursor.rowcount

            conn.commit()
            conn.close()

            logger.info(f"清理旧记录完成，删除 {deleted_performance} 条性能记录")
            return True

        except Exception as e:
            logger.error(f"清理旧记录失败: {e}")
            return False
