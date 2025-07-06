"""
插件配置管理器

负责管理插件的配置文件、权限控制和安全策略
"""

import os
import json
import yaml
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

from core.logger import get_logger

logger = get_logger(__name__)


class PluginPermission(Enum):
    """插件权限枚举"""
    READ_DATA = "read_data"
    WRITE_DATA = "write_data"
    NETWORK_ACCESS = "network_access"
    FILE_SYSTEM_ACCESS = "file_system_access"
    SYSTEM_COMMANDS = "system_commands"
    UI_MODIFICATION = "ui_modification"
    PLUGIN_MANAGEMENT = "plugin_management"


@dataclass
class PluginSecurityPolicy:
    """插件安全策略"""
    allowed_permissions: List[PluginPermission]
    denied_permissions: List[PluginPermission]
    sandbox_enabled: bool = True
    network_whitelist: List[str] = None
    file_access_paths: List[str] = None
    max_memory_usage: int = 100 * 1024 * 1024  # 100MB
    max_cpu_usage: float = 0.5  # 50%
    timeout_seconds: int = 30


@dataclass
class PluginConfig:
    """插件配置"""
    name: str
    version: str
    enabled: bool = True
    config_data: Dict[str, Any] = None
    security_policy: PluginSecurityPolicy = None

    def __post_init__(self):
        if self.config_data is None:
            self.config_data = {}
        if self.security_policy is None:
            self.security_policy = PluginSecurityPolicy(
                allowed_permissions=[],
                denied_permissions=[]
            )


class PluginConfigManager:
    """插件配置管理器"""

    def __init__(self, config_dir: str = "config/plugins"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.plugin_configs: Dict[str, PluginConfig] = {}
        self.global_config_file = self.config_dir / "global_config.yaml"
        self.security_policies_file = self.config_dir / "security_policies.yaml"

        self._load_global_config()
        self._load_security_policies()
        self._load_plugin_configs()

    def _load_global_config(self):
        """加载全局配置"""
        try:
            if self.global_config_file.exists():
                with open(self.global_config_file, 'r', encoding='utf-8') as f:
                    self.global_config = yaml.safe_load(f) or {}
            else:
                self.global_config = {
                    'plugin_directory': 'plugins',
                    'auto_load_plugins': True,
                    'sandbox_enabled': True,
                    'max_plugins': 100,
                    'debug_mode': False
                }
                self._save_global_config()

        except Exception as e:
            logger.error(f"加载全局配置失败: {e}")
            self.global_config = {}

    def _save_global_config(self):
        """保存全局配置"""
        try:
            with open(self.global_config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.global_config, f, default_flow_style=False,
                          allow_unicode=True, indent=2)
        except Exception as e:
            logger.error(f"保存全局配置失败: {e}")

    def _load_security_policies(self):
        """加载安全策略"""
        try:
            if self.security_policies_file.exists():
                with open(self.security_policies_file, 'r', encoding='utf-8') as f:
                    policies_data = yaml.safe_load(f) or {}

                self.security_policies = {}
                for policy_name, policy_data in policies_data.items():
                    self.security_policies[policy_name] = PluginSecurityPolicy(
                        allowed_permissions=[PluginPermission(p) for p in policy_data.get('allowed_permissions', [])],
                        denied_permissions=[PluginPermission(p) for p in policy_data.get('denied_permissions', [])],
                        sandbox_enabled=policy_data.get('sandbox_enabled', True),
                        network_whitelist=policy_data.get('network_whitelist', []),
                        file_access_paths=policy_data.get('file_access_paths', []),
                        max_memory_usage=policy_data.get('max_memory_usage', 100 * 1024 * 1024),
                        max_cpu_usage=policy_data.get('max_cpu_usage', 0.5),
                        timeout_seconds=policy_data.get('timeout_seconds', 30)
                    )
            else:
                self.security_policies = {
                    'default': PluginSecurityPolicy(
                        allowed_permissions=[
                            PluginPermission.READ_DATA,
                            PluginPermission.UI_MODIFICATION
                        ],
                        denied_permissions=[
                            PluginPermission.SYSTEM_COMMANDS,
                            PluginPermission.PLUGIN_MANAGEMENT
                        ]
                    ),
                    'trusted': PluginSecurityPolicy(
                        allowed_permissions=[p for p in PluginPermission],
                        denied_permissions=[]
                    ),
                    'restricted': PluginSecurityPolicy(
                        allowed_permissions=[PluginPermission.READ_DATA],
                        denied_permissions=[
                            PluginPermission.WRITE_DATA,
                            PluginPermission.NETWORK_ACCESS,
                            PluginPermission.FILE_SYSTEM_ACCESS,
                            PluginPermission.SYSTEM_COMMANDS
                        ]
                    )
                }
                self._save_security_policies()

        except Exception as e:
            logger.error(f"加载安全策略失败: {e}")
            self.security_policies = {}

    def _save_security_policies(self):
        """保存安全策略"""
        try:
            policies_data = {}
            for policy_name, policy in self.security_policies.items():
                policies_data[policy_name] = {
                    'allowed_permissions': [p.value for p in policy.allowed_permissions],
                    'denied_permissions': [p.value for p in policy.denied_permissions],
                    'sandbox_enabled': policy.sandbox_enabled,
                    'network_whitelist': policy.network_whitelist or [],
                    'file_access_paths': policy.file_access_paths or [],
                    'max_memory_usage': policy.max_memory_usage,
                    'max_cpu_usage': policy.max_cpu_usage,
                    'timeout_seconds': policy.timeout_seconds
                }

            with open(self.security_policies_file, 'w', encoding='utf-8') as f:
                yaml.dump(policies_data, f, default_flow_style=False,
                          allow_unicode=True, indent=2)

        except Exception as e:
            logger.error(f"保存安全策略失败: {e}")

    def _load_plugin_configs(self):
        """加载所有插件配置"""
        try:
            for config_file in self.config_dir.glob("*.json"):
                if config_file.name in ['global_config.yaml', 'security_policies.yaml']:
                    continue

                plugin_name = config_file.stem
                self._load_plugin_config(plugin_name)

        except Exception as e:
            logger.error(f"加载插件配置失败: {e}")

    def _load_plugin_config(self, plugin_name: str) -> Optional[PluginConfig]:
        """加载单个插件配置"""
        try:
            config_file = self.config_dir / f"{plugin_name}.json"

            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)

                # 创建安全策略
                security_policy_name = config_data.get('security_policy', 'default')
                security_policy = self.security_policies.get(security_policy_name)

                if not security_policy:
                    logger.warning(f"未找到安全策略 {security_policy_name}，使用默认策略")
                    security_policy = self.security_policies.get('default')

                plugin_config = PluginConfig(
                    name=plugin_name,
                    version=config_data.get('version', '1.0.0'),
                    enabled=config_data.get('enabled', True),
                    config_data=config_data.get('config_data', {}),
                    security_policy=security_policy
                )

                self.plugin_configs[plugin_name] = plugin_config
                return plugin_config

            return None

        except Exception as e:
            logger.error(f"加载插件配置失败 {plugin_name}: {e}")
            return None

    def save_plugin_config(self, plugin_name: str, config: PluginConfig) -> bool:
        """保存插件配置"""
        try:
            config_file = self.config_dir / f"{plugin_name}.json"

            # 找到安全策略名称
            security_policy_name = 'default'
            for name, policy in self.security_policies.items():
                if policy == config.security_policy:
                    security_policy_name = name
                    break

            config_data = {
                'name': config.name,
                'version': config.version,
                'enabled': config.enabled,
                'config_data': config.config_data,
                'security_policy': security_policy_name
            }

            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            self.plugin_configs[plugin_name] = config
            logger.info(f"插件配置已保存: {plugin_name}")
            return True

        except Exception as e:
            logger.error(f"保存插件配置失败 {plugin_name}: {e}")
            return False

    def get_plugin_config(self, plugin_name: str) -> Optional[PluginConfig]:
        """获取插件配置"""
        return self.plugin_configs.get(plugin_name)

    def create_plugin_config(self, plugin_name: str, version: str = "1.0.0",
                             security_policy_name: str = "default") -> PluginConfig:
        """创建新的插件配置"""
        security_policy = self.security_policies.get(security_policy_name)
        if not security_policy:
            security_policy = self.security_policies.get('default')

        config = PluginConfig(
            name=plugin_name,
            version=version,
            security_policy=security_policy
        )

        self.plugin_configs[plugin_name] = config
        self.save_plugin_config(plugin_name, config)

        return config

    def update_plugin_config(self, plugin_name: str, config_data: Dict[str, Any]) -> bool:
        """更新插件配置数据"""
        try:
            config = self.plugin_configs.get(plugin_name)
            if not config:
                logger.error(f"插件配置不存在: {plugin_name}")
                return False

            config.config_data.update(config_data)
            return self.save_plugin_config(plugin_name, config)

        except Exception as e:
            logger.error(f"更新插件配置失败 {plugin_name}: {e}")
            return False

    def enable_plugin(self, plugin_name: str) -> bool:
        """启用插件"""
        try:
            config = self.plugin_configs.get(plugin_name)
            if not config:
                logger.error(f"插件配置不存在: {plugin_name}")
                return False

            config.enabled = True
            return self.save_plugin_config(plugin_name, config)

        except Exception as e:
            logger.error(f"启用插件失败 {plugin_name}: {e}")
            return False

    def disable_plugin(self, plugin_name: str) -> bool:
        """禁用插件"""
        try:
            config = self.plugin_configs.get(plugin_name)
            if not config:
                logger.error(f"插件配置不存在: {plugin_name}")
                return False

            config.enabled = False
            return self.save_plugin_config(plugin_name, config)

        except Exception as e:
            logger.error(f"禁用插件失败 {plugin_name}: {e}")
            return False

    def check_permission(self, plugin_name: str, permission: PluginPermission) -> bool:
        """检查插件权限"""
        try:
            config = self.plugin_configs.get(plugin_name)
            if not config:
                logger.warning(f"插件配置不存在，拒绝权限: {plugin_name}")
                return False

            security_policy = config.security_policy

            # 检查是否在拒绝列表中
            if permission in security_policy.denied_permissions:
                return False

            # 检查是否在允许列表中
            if permission in security_policy.allowed_permissions:
                return True

            # 默认拒绝
            return False

        except Exception as e:
            logger.error(f"检查插件权限失败 {plugin_name}: {e}")
            return False

    def get_security_policy(self, plugin_name: str) -> Optional[PluginSecurityPolicy]:
        """获取插件安全策略"""
        config = self.plugin_configs.get(plugin_name)
        return config.security_policy if config else None

    def set_security_policy(self, plugin_name: str, policy_name: str) -> bool:
        """设置插件安全策略"""
        try:
            config = self.plugin_configs.get(plugin_name)
            if not config:
                logger.error(f"插件配置不存在: {plugin_name}")
                return False

            security_policy = self.security_policies.get(policy_name)
            if not security_policy:
                logger.error(f"安全策略不存在: {policy_name}")
                return False

            config.security_policy = security_policy
            return self.save_plugin_config(plugin_name, config)

        except Exception as e:
            logger.error(f"设置插件安全策略失败 {plugin_name}: {e}")
            return False

    def get_all_plugin_configs(self) -> Dict[str, PluginConfig]:
        """获取所有插件配置"""
        return self.plugin_configs.copy()

    def remove_plugin_config(self, plugin_name: str) -> bool:
        """删除插件配置"""
        try:
            config_file = self.config_dir / f"{plugin_name}.json"

            if config_file.exists():
                config_file.unlink()

            if plugin_name in self.plugin_configs:
                del self.plugin_configs[plugin_name]

            logger.info(f"插件配置已删除: {plugin_name}")
            return True

        except Exception as e:
            logger.error(f"删除插件配置失败 {plugin_name}: {e}")
            return False

    def backup_configs(self, backup_dir: str) -> bool:
        """备份配置文件"""
        try:
            backup_path = Path(backup_dir)
            backup_path.mkdir(parents=True, exist_ok=True)

            import shutil
            shutil.copytree(self.config_dir, backup_path / "plugins", dirs_exist_ok=True)

            logger.info(f"配置文件已备份到: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"备份配置文件失败: {e}")
            return False

    def restore_configs(self, backup_dir: str) -> bool:
        """恢复配置文件"""
        try:
            backup_path = Path(backup_dir) / "plugins"

            if not backup_path.exists():
                logger.error(f"备份目录不存在: {backup_path}")
                return False

            import shutil
            shutil.rmtree(self.config_dir)
            shutil.copytree(backup_path, self.config_dir)

            # 重新加载配置
            self._load_global_config()
            self._load_security_policies()
            self._load_plugin_configs()

            logger.info(f"配置文件已从备份恢复: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"恢复配置文件失败: {e}")
            return False


# 全局配置管理器实例
_plugin_config_manager = None


def get_plugin_config_manager() -> PluginConfigManager:
    """获取全局插件配置管理器实例"""
    global _plugin_config_manager
    if _plugin_config_manager is None:
        _plugin_config_manager = PluginConfigManager()
    return _plugin_config_manager
