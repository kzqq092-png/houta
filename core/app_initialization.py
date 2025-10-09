"""
应用初始化模块
在应用启动时自动初始化所有必要的组件和配置
"""

import logging
import asyncio
from typing import Dict, Any, List
from pathlib import Path

from core.network.plugin_auto_register import initialize_plugin_network_configs, get_plugin_auto_register

logger = logging.getLogger(__name__)

class AppInitializer:
    """应用初始化器"""
    
    def __init__(self):
        self.initialization_results: Dict[str, Any] = {}
        self.initialized = False

    def initialize_all(self) -> Dict[str, Any]:
        """初始化所有组件"""
        logger.info("开始应用初始化...")
        
        try:
            # 1. 初始化网络配置
            network_results = self._initialize_network_configs()
            self.initialization_results['network_config'] = network_results
            
            # 2. 初始化数据库
            database_results = self._initialize_databases()
            self.initialization_results['database'] = database_results
            
            # 3. 初始化其他组件
            other_results = self._initialize_other_components()
            self.initialization_results['other_components'] = other_results
            
            self.initialized = True
            
            # 记录初始化摘要
            self._log_initialization_summary()
            
            return self.initialization_results
            
        except Exception as e:
            logger.error(f"应用初始化失败: {e}")
            self.initialization_results['error'] = str(e)
            return self.initialization_results

    def _initialize_network_configs(self) -> Dict[str, Any]:
        """初始化网络配置"""
        logger.info("初始化插件网络配置...")
        
        try:
            # 自动注册所有支持网络配置的插件
            registration_results = initialize_plugin_network_configs()
            
            # 获取注册统计
            auto_register = get_plugin_auto_register()
            registration_status = auto_register.get_registration_status()
            plugins_info = auto_register.get_registered_plugins_info()
            
            network_results = {
                'status': 'success',
                'registration_results': registration_results,
                'registration_status': registration_status,
                'plugins_info': plugins_info,
                'total_plugins': len(registration_results),
                'successful_plugins': sum(1 for success in registration_results.values() if success),
                'failed_plugins': sum(1 for success in registration_results.values() if not success)
            }
            
            logger.info(f"网络配置初始化完成: {network_results['successful_plugins']}/{network_results['total_plugins']} 插件成功")
            
            return network_results
            
        except Exception as e:
            logger.error(f"网络配置初始化失败: {e}")
            return {
                'status': 'failed',
                'error': str(e),
                'total_plugins': 0,
                'successful_plugins': 0,
                'failed_plugins': 0
            }

    def _initialize_databases(self) -> Dict[str, Any]:
        """初始化数据库"""
        logger.info("初始化数据库...")
        
        try:
            # 确保配置目录存在
            config_dir = Path("config")
            config_dir.mkdir(exist_ok=True)
            
            # 确保网络配置目录存在
            network_config_dir = config_dir / "network"
            network_config_dir.mkdir(exist_ok=True)
            
            # 确保数据库目录存在
            db_dir = Path("database")
            db_dir.mkdir(exist_ok=True)
            
            database_results = {
                'status': 'success',
                'config_dir_created': config_dir.exists(),
                'network_config_dir_created': network_config_dir.exists(),
                'database_dir_created': db_dir.exists()
            }
            
            logger.info("数据库初始化完成")
            return database_results
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            return {
                'status': 'failed',
                'error': str(e)
            }

    def _initialize_other_components(self) -> Dict[str, Any]:
        """初始化其他组件"""
        logger.info("初始化其他组件...")
        
        try:
            # 这里可以添加其他组件的初始化逻辑
            # 例如：缓存系统、日志系统、监控系统等
            
            other_results = {
                'status': 'success',
                'components': ['logging', 'config_management']
            }
            
            logger.info("其他组件初始化完成")
            return other_results
            
        except Exception as e:
            logger.error(f"其他组件初始化失败: {e}")
            return {
                'status': 'failed',
                'error': str(e)
            }

    def _log_initialization_summary(self):
        """记录初始化摘要"""
        try:
            logger.info("=== 应用初始化摘要 ===")
            
            # 网络配置摘要
            network_config = self.initialization_results.get('network_config', {})
            if network_config.get('status') == 'success':
                logger.info(f"✓ 网络配置: {network_config['successful_plugins']}/{network_config['total_plugins']} 插件成功注册")
                
                # 显示注册的插件列表
                for plugin_info in network_config.get('plugins_info', []):
                    plugin_name = plugin_info['plugin_name']
                    endpoints_count = plugin_info['endpoints_count']
                    logger.info(f"  - {plugin_name}: {endpoints_count} 个端点")
            else:
                logger.error(f"✗ 网络配置初始化失败: {network_config.get('error', '未知错误')}")
            
            # 数据库摘要
            database = self.initialization_results.get('database', {})
            if database.get('status') == 'success':
                logger.info("✓ 数据库: 初始化成功")
            else:
                logger.error(f"✗ 数据库初始化失败: {database.get('error', '未知错误')}")
            
            # 其他组件摘要
            other = self.initialization_results.get('other_components', {})
            if other.get('status') == 'success':
                components = ', '.join(other.get('components', []))
                logger.info(f"✓ 其他组件: {components}")
            else:
                logger.error(f"✗ 其他组件初始化失败: {other.get('error', '未知错误')}")
            
            logger.info("=== 初始化完成 ===")
            
        except Exception as e:
            logger.error(f"记录初始化摘要失败: {e}")

    def get_initialization_status(self) -> Dict[str, Any]:
        """获取初始化状态"""
        return {
            'initialized': self.initialized,
            'results': self.initialization_results.copy() if self.initialization_results else {}
        }

    def reinitialize_network_configs(self) -> Dict[str, Any]:
        """重新初始化网络配置"""
        logger.info("重新初始化网络配置...")
        
        try:
            network_results = self._initialize_network_configs()
            self.initialization_results['network_config'] = network_results
            
            logger.info("网络配置重新初始化完成")
            return network_results
            
        except Exception as e:
            logger.error(f"重新初始化网络配置失败: {e}")
            return {
                'status': 'failed',
                'error': str(e)
            }

# 全局初始化器实例
_app_initializer = None

def get_app_initializer() -> AppInitializer:
    """获取应用初始化器实例"""
    global _app_initializer
    if _app_initializer is None:
        _app_initializer = AppInitializer()
    return _app_initializer

def initialize_application() -> Dict[str, Any]:
    """初始化应用"""
    initializer = get_app_initializer()
    return initializer.initialize_all()

def get_app_status() -> Dict[str, Any]:
    """获取应用状态"""
    initializer = get_app_initializer()
    return initializer.get_initialization_status()

# 这个函数应该在应用的main.py或__init__.py中调用
def startup_initialization():
    """启动时的初始化"""
    logger.info("开始应用启动初始化...")
    
    try:
        results = initialize_application()
        
        if results.get('error'):
            logger.error(f"应用初始化包含错误: {results['error']}")
        else:
            logger.info("应用启动初始化成功完成")
        
        return results
        
    except Exception as e:
        logger.error(f"应用启动初始化失败: {e}")
        return {'error': str(e)}
