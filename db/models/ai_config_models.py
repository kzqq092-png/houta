from loguru import logger
#!/usr/bin/env python3
"""
AI预测配置数据库模型

用于在数据库中存储和管理AI预测系统的配置参数
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

logger = logger

class AIPredictionConfigManager:
    """AI预测配置管理器"""

    def __init__(self, db_path: str = "db/factorweave_system.sqlite"):
        """
        初始化配置管理器

        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """初始化数据库表"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 创建AI预测配置表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS ai_prediction_config (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        config_key TEXT UNIQUE NOT NULL,
                        config_value TEXT NOT NULL,
                        config_type TEXT NOT NULL DEFAULT 'json',
                        description TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        is_active BOOLEAN DEFAULT 1
                    )
                """)

                # 创建配置历史表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS ai_config_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        config_key TEXT NOT NULL,
                        old_value TEXT,
                        new_value TEXT,
                        changed_by TEXT DEFAULT 'system',
                        changed_at TEXT NOT NULL
                    )
                """)

                conn.commit()
                logger.info("AI预测配置数据库表初始化完成")

        except Exception as e:
            logger.error(f"初始化AI配置数据库失败: {e}")
            logger.warning("🗄️ AI配置数据库文件缺失或无法访问，这是正常的初次运行状态")
            logger.info("💡 系统将使用默认配置运行，功能完全正常")
            logger.info("📁 数据库文件将在首次使用时自动创建")
            raise

    def load_default_config(self):
        """加载默认配置到数据库"""
        try:
            default_config_path = Path("config/ai_prediction_config.json")
            if default_config_path.exists():
                with open(default_config_path, 'r', encoding='utf-8') as f:
                    default_config = json.load(f)

                # 将配置分组存储
                for section_key, section_value in default_config.items():
                    self._save_config_section(section_key, section_value,
                                              f"AI预测{section_key}配置")

                logger.info("默认AI预测配置已加载到数据库")
            else:
                logger.warning("默认配置文件不存在，跳过加载")

        except Exception as e:
            logger.error(f"加载默认配置失败: {e}")

    def _save_config_section(self, key: str, value: Dict[str, Any], description: str = ""):
        """保存配置段到数据库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 检查是否存在
                cursor.execute("SELECT config_value FROM ai_prediction_config WHERE config_key = ?", (key,))
                existing = cursor.fetchone()

                current_time = datetime.now().isoformat()
                value_json = json.dumps(value, ensure_ascii=False, indent=2)

                if existing:
                    # 记录历史
                    cursor.execute("""
                        INSERT INTO ai_config_history (config_key, old_value, new_value, changed_at)
                        VALUES (?, ?, ?, ?)
                    """, (key, existing[0], value_json, current_time))

                    # 更新配置
                    cursor.execute("""
                        UPDATE ai_prediction_config 
                        SET config_value = ?, updated_at = ?
                        WHERE config_key = ?
                    """, (value_json, current_time, key))
                else:
                    # 插入新配置
                    cursor.execute("""
                        INSERT INTO ai_prediction_config 
                        (config_key, config_value, description, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (key, value_json, description, current_time, current_time))

                conn.commit()

        except Exception as e:
            logger.error(f"保存配置段失败: {e}")
            raise

    def get_config(self, key: str) -> Optional[Dict[str, Any]]:
        """
        获取配置

        Args:
            key: 配置键

        Returns:
            配置值字典，如果不存在返回None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT config_value FROM ai_prediction_config 
                    WHERE config_key = ? AND is_active = 1
                """, (key,))

                result = cursor.fetchone()
                if result:
                    return json.loads(result[0])
                return None

        except Exception as e:
            logger.error(f"获取配置失败: {e}")
            return None

    def update_config(self, key: str, value: Dict[str, Any], changed_by: str = "user"):
        """
        更新配置

        Args:
            key: 配置键
            value: 新配置值
            changed_by: 修改者
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 获取旧值
                cursor.execute("SELECT config_value FROM ai_prediction_config WHERE config_key = ?", (key,))
                old_result = cursor.fetchone()
                old_value = old_result[0] if old_result else None

                current_time = datetime.now().isoformat()
                value_json = json.dumps(value, ensure_ascii=False, indent=2)

                # 检查值是否真的发生了变化
                if old_value is not None:
                    try:
                        old_value_dict = json.loads(old_value)
                        # 比较新值和旧值，如果相同则不记录变更
                        if old_value_dict == value:
                            logger.debug(f"配置 {key} 值未发生变化，跳过历史记录")
                            return  # 值没有变化，直接返回
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"解析旧配置值失败，继续更新: {e}")

                # 记录历史（只有在值真正变化时才记录）
                cursor.execute("""
                    INSERT INTO ai_config_history (config_key, old_value, new_value, changed_by, changed_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (key, old_value, value_json, changed_by, current_time))

                # 更新配置
                if old_value is not None:
                    cursor.execute("""
                        UPDATE ai_prediction_config 
                        SET config_value = ?, updated_at = ?
                        WHERE config_key = ?
                    """, (value_json, current_time, key))
                else:
                    # 插入新配置
                    cursor.execute("""
                        INSERT INTO ai_prediction_config 
                        (config_key, config_value, description, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (key, value_json, "", current_time, current_time))

                conn.commit()
                logger.info(f"配置 {key} 已更新")

        except Exception as e:
            logger.error(f"更新配置失败: {e}")
            raise

    def get_all_configs(self) -> Dict[str, Any]:
        """获取所有活跃配置"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT config_key, config_value FROM ai_prediction_config 
                    WHERE is_active = 1
                """)

                configs = {}
                for row in cursor.fetchall():
                    key, value_json = row
                    configs[key] = json.loads(value_json)

                return configs

        except Exception as e:
            logger.error(f"获取所有配置失败: {e}")
            return {}

    def get_config_history(self, key: str = None, limit: int = 50) -> list:
        """
        获取配置历史

        Args:
            key: 配置键，None表示获取所有配置的历史
            limit: 限制返回数量

        Returns:
            历史记录列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                if key:
                    cursor.execute("""
                        SELECT config_key, old_value, new_value, changed_by, changed_at
                        FROM ai_config_history 
                        WHERE config_key = ?
                        ORDER BY changed_at DESC
                        LIMIT ?
                    """, (key, limit))
                else:
                    cursor.execute("""
                        SELECT config_key, old_value, new_value, changed_by, changed_at
                        FROM ai_config_history 
                        ORDER BY changed_at DESC
                        LIMIT ?
                    """, (limit,))

                return cursor.fetchall()

        except Exception as e:
            logger.error(f"获取配置历史失败: {e}")
            return []

    def export_config(self, file_path: str):
        """导出配置到文件"""
        try:
            configs = self.get_all_configs()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(configs, f, ensure_ascii=False, indent=2)
            logger.info(f"配置已导出到: {file_path}")

        except Exception as e:
            logger.error(f"导出配置失败: {e}")
            raise

    def import_config(self, file_path: str, changed_by: str = "import"):
        """从文件导入配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                configs = json.load(f)

            for key, value in configs.items():
                self.update_config(key, value, changed_by)

            logger.info(f"配置已从 {file_path} 导入")

        except Exception as e:
            logger.error(f"导入配置失败: {e}")
            raise

    def reset_to_defaults(self, changed_by: str = "reset"):
        """重置为默认配置"""
        try:
            # 先备份当前配置
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"config/ai_config_backup_{current_time}.json"
            self.export_config(backup_file)

            # 重新加载默认配置
            self.load_default_config()

            logger.info(f"配置已重置为默认值，备份保存在: {backup_file}")

        except Exception as e:
            logger.error(f"重置配置失败: {e}")
            raise

# 全局配置管理器实例
_config_manager = None

def get_ai_config_manager() -> AIPredictionConfigManager:
    """获取全局AI配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = AIPredictionConfigManager()
        # 确保默认配置已加载
        _config_manager.load_default_config()
    return _config_manager
