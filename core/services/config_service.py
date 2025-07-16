"""
配置服务模块

负责应用配置的管理、持久化和同步。
"""

import logging
import json
import os
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from datetime import datetime
from .base_service import BaseService


logger = logging.getLogger(__name__)


class ConfigService(BaseService):
    """
    配置服务

    负责应用配置的管理、持久化和同步。
    """

    def __init__(self, config_file: str = None, **kwargs):
        """
        初始化配置服务

        Args:
            config_file: 配置文件路径
            **kwargs: 其他参数
        """
        super().__init__(**kwargs)
        self._config_file = config_file or 'config/app_config.json'
        self._config_data = {}
        self._default_config = {}
        self._config_watchers = {}

    def _do_initialize(self) -> None:
        """初始化配置服务"""
        try:
            # 设置默认配置
            self._setup_default_config()

            # 加载配置文件
            self._load_config()

            # 确保配置目录存在
            config_path = Path(self._config_file)
            config_path.parent.mkdir(parents=True, exist_ok=True)

            logger.info(
                f"Config service initialized with file: {self._config_file}")

        except Exception as e:
            logger.error(f"Failed to initialize config service: {e}")
            raise

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值

        Args:
            key: 配置键，支持点分隔的嵌套键如 'ui.theme'
            default: 默认值

        Returns:
            配置值
        """
        self._ensure_initialized()

        try:
            keys = key.split('.')
            value = self._config_data

            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default

            return value

        except Exception as e:
            logger.error(f"Failed to get config '{key}': {e}")
            return default

    def set(self, key: str, value: Any, save: bool = True) -> bool:
        """
        设置配置值

        Args:
            key: 配置键
            value: 配置值
            save: 是否立即保存到文件

        Returns:
            是否成功设置
        """
        self._ensure_initialized()

        try:
            keys = key.split('.')
            config = self._config_data

            # 导航到父级配置
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                elif not isinstance(config[k], dict):
                    config[k] = {}
                config = config[k]

            # 设置值
            old_value = config.get(keys[-1])
            config[keys[-1]] = value

            # 通知观察者
            self._notify_watchers(key, old_value, value)

            # 保存到文件
            if save:
                self._save_config()

            logger.debug(f"Set config '{key}' = {value}")
            return True

        except Exception as e:
            logger.error(f"Failed to set config '{key}': {e}")
            return False

    def update(self, config_dict: Dict[str, Any], save: bool = True) -> bool:
        """
        批量更新配置

        Args:
            config_dict: 配置字典
            save: 是否立即保存到文件

        Returns:
            是否成功更新
        """
        self._ensure_initialized()

        try:
            for key, value in config_dict.items():
                self.set(key, value, save=False)

            if save:
                self._save_config()

            logger.debug(f"Updated {len(config_dict)} config items")
            return True

        except Exception as e:
            logger.error(f"Failed to update config: {e}")
            return False

    def delete(self, key: str, save: bool = True) -> bool:
        """
        删除配置项

        Args:
            key: 配置键
            save: 是否立即保存到文件

        Returns:
            是否成功删除
        """
        self._ensure_initialized()

        try:
            keys = key.split('.')
            config = self._config_data

            # 导航到父级配置
            for k in keys[:-1]:
                if k not in config or not isinstance(config[k], dict):
                    return False
                config = config[k]

            # 删除配置项
            if keys[-1] in config:
                old_value = config.pop(keys[-1])

                # 通知观察者
                self._notify_watchers(key, old_value, None)

                # 保存到文件
                if save:
                    self._save_config()

                logger.debug(f"Deleted config '{key}'")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to delete config '{key}': {e}")
            return False

    def has(self, key: str) -> bool:
        """
        检查配置项是否存在

        Args:
            key: 配置键

        Returns:
            是否存在
        """
        self._ensure_initialized()

        try:
            keys = key.split('.')
            value = self._config_data

            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return False

            return True

        except Exception as e:
            logger.error(f"Failed to check config '{key}': {e}")
            return False

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        获取配置段

        Args:
            section: 配置段名称

        Returns:
            配置段内容
        """
        self._ensure_initialized()

        section_data = self.get(section, {})
        return section_data if isinstance(section_data, dict) else {}

    def reset_to_default(self, key: str = None, save: bool = True) -> bool:
        """
        重置配置为默认值

        Args:
            key: 配置键，如果为None则重置所有配置
            save: 是否立即保存到文件

        Returns:
            是否成功重置
        """
        self._ensure_initialized()

        try:
            if key is None:
                # 重置所有配置
                self._config_data = self._deep_copy(self._default_config)
                logger.info("Reset all config to default")
            else:
                # 重置指定配置
                default_value = self._get_default_value(key)
                if default_value is not None:
                    self.set(key, default_value, save=False)
                    logger.info(f"Reset config '{key}' to default")
                else:
                    logger.warning(f"No default value for config '{key}'")
                    return False

            if save:
                self._save_config()

            return True

        except Exception as e:
            logger.error(f"Failed to reset config: {e}")
            return False

    def export_config(self, export_path: str, keys: List[str] = None) -> bool:
        """
        导出配置

        Args:
            export_path: 导出路径
            keys: 要导出的配置键列表，如果为None则导出所有配置

        Returns:
            是否成功导出
        """
        self._ensure_initialized()

        try:
            if keys is None:
                export_data = self._config_data
            else:
                export_data = {}
                for key in keys:
                    value = self.get(key)
                    if value is not None:
                        self._set_nested_value(export_data, key, value)

            # 添加导出元信息
            export_data['_export_info'] = {
                'export_time': datetime.now().isoformat(),
                'app_version': self.get('app.version', '1.0.0'),
                'exported_keys': keys
            }

            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

            logger.info(f"Config exported to {export_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export config: {e}")
            return False

    def import_config(self, import_path: str, merge: bool = True,
                      keys: List[str] = None) -> bool:
        """
        导入配置

        Args:
            import_path: 导入路径
            merge: 是否合并配置（False表示覆盖）
            keys: 要导入的配置键列表，如果为None则导入所有配置

        Returns:
            是否成功导入
        """
        self._ensure_initialized()

        try:
            if not os.path.exists(import_path):
                logger.error(f"Import file not found: {import_path}")
                return False

            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)

            # 移除导出元信息
            import_data.pop('_export_info', None)

            if not merge:
                # 覆盖模式
                if keys is None:
                    self._config_data = import_data
                else:
                    for key in keys:
                        value = self._get_nested_value(import_data, key)
                        if value is not None:
                            self.set(key, value, save=False)
            else:
                # 合并模式
                if keys is None:
                    self._merge_config(self._config_data, import_data)
                else:
                    for key in keys:
                        value = self._get_nested_value(import_data, key)
                        if value is not None:
                            self.set(key, value, save=False)

            self._save_config()

            logger.info(f"Config imported from {import_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to import config: {e}")
            return False

    def watch(self, key: str, callback: callable) -> str:
        """
        监听配置变化

        Args:
            key: 配置键
            callback: 回调函数，参数为 (key, old_value, new_value)

        Returns:
            监听器ID
        """
        self._ensure_initialized()

        import uuid
        watcher_id = str(uuid.uuid4())

        if key not in self._config_watchers:
            self._config_watchers[key] = {}

        self._config_watchers[key][watcher_id] = callback

        logger.debug(f"Added config watcher for '{key}': {watcher_id}")
        return watcher_id

    def unwatch(self, key: str, watcher_id: str) -> bool:
        """
        取消监听配置变化

        Args:
            key: 配置键
            watcher_id: 监听器ID

        Returns:
            是否成功取消
        """
        try:
            if key in self._config_watchers and watcher_id in self._config_watchers[key]:
                del self._config_watchers[key][watcher_id]

                # 如果该键没有监听器了，删除键
                if not self._config_watchers[key]:
                    del self._config_watchers[key]

                logger.debug(
                    f"Removed config watcher for '{key}': {watcher_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to remove config watcher: {e}")
            return False

    def get_all_config(self) -> Dict[str, Any]:
        """
        获取所有配置

        Returns:
            所有配置
        """
        self._ensure_initialized()
        return self._deep_copy(self._config_data)

    def reload(self) -> bool:
        """
        重新加载配置文件

        Returns:
            是否成功重新加载
        """
        self._ensure_initialized()

        try:
            self._load_config()
            logger.info("Config reloaded successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to reload config: {e}")
            return False

    def _setup_default_config(self) -> None:
        """设置默认配置"""
        self._default_config = {
            'app': {
                'name': 'YS-Quant‌',
                'version': '1.0.0',
                'language': 'zh_CN',
                'auto_save': True,
                'auto_save_interval': 300  # 秒
            },
            'ui': {
                'theme': 'default',
                'window': {
                    'width': 1200,
                    'height': 800,
                    'maximized': False,
                    'remember_size': True
                },
                'layout': {
                    'left_panel_width': 250,
                    'right_panel_width': 300,
                    'bottom_panel_height': 200,
                    'show_left_panel': True,
                    'show_right_panel': True,
                    'show_bottom_panel': True
                }
            },
            'data': {
                'source': 'tdx',
                'cache_enabled': True,
                'cache_size': 1000,  # MB
                'update_interval': 60  # 秒
            },
            'chart': {
                'default_period': 'D',
                'default_indicators': ['MA5', 'MA10', 'MA20'],
                'animation_enabled': True,
                'auto_scale': True
            },
            'analysis': {
                'auto_analysis': True,
                'default_strategies': ['golden_cross', 'rsi_oversold'],
                'alert_enabled': True
            },
            'performance': {
                'max_threads': 4,
                'memory_limit': 2048,  # MB
                'enable_gpu': False
            }
        }

    def _load_config(self) -> None:
        """加载配置文件"""
        try:
            if os.path.exists(self._config_file):
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)

                # 合并默认配置和加载的配置
                self._config_data = self._deep_copy(self._default_config)
                self._merge_config(self._config_data, loaded_config)

                logger.debug(f"Loaded config from {self._config_file}")
            else:
                # 使用默认配置
                self._config_data = self._deep_copy(self._default_config)
                self._save_config()
                logger.info(
                    f"Created default config file: {self._config_file}")

        except Exception as e:
            logger.error(f"Failed to load config file: {e}")
            # 使用默认配置
            self._config_data = self._deep_copy(self._default_config)

    def _save_config(self) -> None:
        """保存配置文件"""
        try:
            # 确保目录存在
            config_path = Path(self._config_file)
            config_path.parent.mkdir(parents=True, exist_ok=True)

            # 添加保存时间戳
            save_data = self._deep_copy(self._config_data)
            save_data['_meta'] = {
                'last_saved': datetime.now().isoformat(),
                'version': '1.0'
            }

            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)

            logger.debug(f"Saved config to {self._config_file}")

        except Exception as e:
            logger.error(f"Failed to save config file: {e}")

    def _notify_watchers(self, key: str, old_value: Any, new_value: Any) -> None:
        """通知配置监听器"""
        try:
            if key in self._config_watchers:
                for watcher_id, callback in self._config_watchers[key].items():
                    try:
                        callback(key, old_value, new_value)
                    except Exception as e:
                        logger.error(f"Config watcher callback error: {e}")

        except Exception as e:
            logger.error(f"Failed to notify config watchers: {e}")

    def _get_default_value(self, key: str) -> Any:
        """获取默认配置值"""
        try:
            keys = key.split('.')
            value = self._default_config

            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return None

            return value

        except Exception:
            return None

    def _deep_copy(self, obj: Any) -> Any:
        """深拷贝对象"""
        if isinstance(obj, dict):
            return {k: self._deep_copy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_copy(item) for item in obj]
        else:
            return obj

    def _merge_config(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """合并配置"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._merge_config(target[key], value)
            else:
                target[key] = self._deep_copy(value)

    def _get_nested_value(self, data: Dict[str, Any], key: str) -> Any:
        """获取嵌套值"""
        try:
            keys = key.split('.')
            value = data

            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return None

            return value

        except Exception:
            return None

    def _set_nested_value(self, data: Dict[str, Any], key: str, value: Any) -> None:
        """设置嵌套值"""
        keys = key.split('.')
        current = data

        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            elif not isinstance(current[k], dict):
                current[k] = {}
            current = current[k]

        current[keys[-1]] = value

    def _do_dispose(self) -> None:
        """清理资源"""
        # 保存配置
        try:
            self._save_config()
        except Exception as e:
            logger.error(f"Failed to save config during disposal: {e}")

        # 清理监听器
        self._config_watchers.clear()
        self._config_data.clear()
        self._default_config.clear()

        super()._do_dispose()
