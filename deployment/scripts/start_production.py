#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Production Startup Script
生产环境启动脚本

本脚本负责在生产环境中启动FactorWeave-Quant应用，包括配置验证、
服务初始化、健康检查、监控设置等。

启动流程：
1. 环境检查和配置验证
2. 数据库初始化
3. 缓存系统初始化
4. 插件系统初始化
5. 监控系统启动
6. 主应用启动
7. 健康检查服务
"""

import sys
import os
import asyncio
import signal
import time
from pathlib import Path
from typing import Optional, Dict, Any
import threading

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from loguru import logger
    import uvicorn
    import psutil
except ImportError as e:
    print(f"依赖导入失败: {e}")
    print("请确保已安装生产环境依赖")
    sys.exit(1)

try:
    from deployment.production_config import create_production_config, Environment
    from core.performance.enhanced_cache_system import init_global_cache_system
    from core.plugin_center import PluginCenter
    from core.services.service_bootstrap import ServiceBootstrap
    from core.database.duckdb_manager import DuckDBManager
except ImportError as e:
    print(f"核心模块导入失败: {e}")
    sys.exit(1)


class ProductionServer:
    """生产环境服务器"""

    def __init__(self):
        self.config = None
        self.services = {}
        self.shutdown_event = threading.Event()
        self.health_check_thread = None
        self.monitoring_thread = None

        # 信号处理
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        logger.info("生产环境服务器初始化完成")

    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"接收到信号 {signum}，开始优雅关闭...")
        self.shutdown_event.set()

    async def start(self):
        """启动生产环境服务器"""
        try:
            # 1. 环境检查和配置验证
            await self._check_environment()

            # 2. 加载和验证配置
            await self._load_configuration()

            # 3. 设置日志
            self._setup_logging()

            # 4. 初始化数据库
            await self._initialize_database()

            # 5. 初始化缓存系统
            await self._initialize_cache()

            # 6. 初始化插件系统
            await self._initialize_plugins()

            # 7. 初始化核心服务
            await self._initialize_services()

            # 8. 启动监控系统
            await self._start_monitoring()

            # 9. 启动健康检查
            await self._start_health_check()

            # 10. 启动主应用
            await self._start_main_application()

        except Exception as e:
            logger.error(f"生产环境启动失败: {e}")
            await self._cleanup()
            sys.exit(1)

    async def _check_environment(self):
        """检查环境"""
        logger.info("🔍 检查生产环境...")

        # 检查Python版本
        python_version = sys.version_info
        if python_version < (3, 8):
            raise RuntimeError(f"Python版本过低: {python_version}, 需要3.8+")

        # 检查系统资源
        memory_gb = psutil.virtual_memory().total / (1024**3)
        if memory_gb < 2:
            logger.warning(f"系统内存较低: {memory_gb:.1f}GB，建议至少4GB")

        cpu_count = psutil.cpu_count()
        if cpu_count < 2:
            logger.warning(f"CPU核心数较少: {cpu_count}，建议至少2核")

        # 检查磁盘空间
        disk_usage = psutil.disk_usage('/')
        free_gb = disk_usage.free / (1024**3)
        if free_gb < 5:
            logger.warning(f"磁盘空间不足: {free_gb:.1f}GB，建议至少10GB")

        logger.info("✅ 环境检查完成")

    async def _load_configuration(self):
        """加载配置"""
        logger.info("📋 加载生产环境配置...")

        # 创建配置
        environment = os.getenv('ENVIRONMENT', 'production')
        self.config = create_production_config(environment)

        # 验证配置
        errors = self.config.validate_config()
        if errors:
            logger.error("配置验证失败:")
            for error in errors:
                logger.error(f"  - {error}")
            raise RuntimeError("配置验证失败")

        # 保存配置到文件
        config_file = project_root / 'deployment' / 'current_config.json'
        self.config.save_config(str(config_file))

        logger.info("✅ 配置加载完成")

    def _setup_logging(self):
        """设置日志"""
        logger.info("📝 设置生产环境日志...")

        try:
            self.config.setup_logging()
            logger.info("✅ 日志设置完成")
        except Exception as e:
            logger.error(f"日志设置失败: {e}")
            raise

    async def _initialize_database(self):
        """初始化数据库"""
        logger.info("🗄️ 初始化数据库...")

        try:
            # 创建DuckDB管理器
            db_config = self.config.database.get_duckdb_config()
            db_manager = DuckDBManager(
                db_path=self.config.database.duckdb_path,
                config=db_config
            )

            # 连接数据库
            await db_manager.connect()

            # 初始化表结构
            await db_manager.initialize_schema()

            # 执行数据库优化
            await db_manager.optimize_performance()

            self.services['database'] = db_manager

            logger.info("✅ 数据库初始化完成")

        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise

    async def _initialize_cache(self):
        """初始化缓存系统"""
        logger.info("💾 初始化缓存系统...")

        try:
            # 获取缓存配置
            cache_config = self.config.cache.get_cache_config()

            # 初始化全局缓存系统
            init_global_cache_system(cache_config)

            # 缓存预热
            if self.config.performance.cache_warmup_enabled:
                await self._warmup_cache()

            logger.info("✅ 缓存系统初始化完成")

        except Exception as e:
            logger.error(f"缓存系统初始化失败: {e}")
            raise

    async def _warmup_cache(self):
        """缓存预热"""
        logger.info("🔥 开始缓存预热...")

        try:
            from core.performance.enhanced_cache_system import get_global_cache_system

            cache_system = get_global_cache_system()

            # 预热常用数据
            def preload_data():
                # 这里可以添加预热数据的逻辑
                return {
                    'system_info': {
                        'version': '1.0.0',
                        'startup_time': time.time()
                    }
                }

            await cache_system.preload(preload_data, ttl=3600)

            logger.info("✅ 缓存预热完成")

        except Exception as e:
            logger.warning(f"缓存预热失败: {e}")

    async def _initialize_plugins(self):
        """初始化插件系统"""
        logger.info("🔌 初始化插件系统...")

        try:
            # 创建插件中心
            plugin_center = PluginCenter()

            # 加载插件配置
            plugin_config = self.config.plugin.__dict__

            # 发现和加载插件
            if self.config.plugin.auto_load:
                for plugin_dir in self.config.plugin.plugin_dirs:
                    plugin_path = Path(plugin_dir)
                    if plugin_path.exists():
                        await plugin_center.discover_plugins(str(plugin_path))

            # 初始化插件
            await plugin_center.initialize_plugins()

            self.services['plugin_center'] = plugin_center

            logger.info("✅ 插件系统初始化完成")

        except Exception as e:
            logger.error(f"插件系统初始化失败: {e}")
            raise

    async def _initialize_services(self):
        """初始化核心服务"""
        logger.info("初始化核心服务...")

        try:
            # 创建服务引导器
            service_bootstrap = ServiceBootstrap()

            # 注册数据库服务
            if 'database' in self.services:
                service_bootstrap.register_service('database', self.services['database'])

            # 注册插件中心
            if 'plugin_center' in self.services:
                service_bootstrap.register_service('plugin_center', self.services['plugin_center'])

            # 初始化所有服务
            await service_bootstrap.initialize_all_services()

            self.services['service_bootstrap'] = service_bootstrap

            logger.info("✅ 核心服务初始化完成")

        except Exception as e:
            logger.error(f"核心服务初始化失败: {e}")
            raise

    async def _start_monitoring(self):
        """启动监控系统"""
        if not self.config.monitoring.metrics_enabled:
            return

        logger.info("📊 启动监控系统...")

        try:
            # 启动监控线程
            self.monitoring_thread = threading.Thread(
                target=self._monitoring_worker,
                daemon=True
            )
            self.monitoring_thread.start()

            logger.info("✅ 监控系统启动完成")

        except Exception as e:
            logger.error(f"监控系统启动失败: {e}")
            raise

    def _monitoring_worker(self):
        """监控工作线程"""
        logger.info("监控工作线程启动")

        while not self.shutdown_event.is_set():
            try:
                # 收集系统指标
                cpu_percent = psutil.cpu_percent(interval=1)
                memory_percent = psutil.virtual_memory().percent
                disk_percent = psutil.disk_usage('/').percent

                # 检查阈值
                if cpu_percent > self.config.monitoring.cpu_threshold:
                    logger.warning(f"CPU使用率过高: {cpu_percent:.1f}%")

                if memory_percent > self.config.monitoring.memory_threshold:
                    logger.warning(f"内存使用率过高: {memory_percent:.1f}%")

                if disk_percent > self.config.monitoring.disk_threshold:
                    logger.warning(f"磁盘使用率过高: {disk_percent:.1f}%")

                # 等待下次检查
                self.shutdown_event.wait(self.config.monitoring.health_check_interval)

            except Exception as e:
                logger.error(f"监控工作线程异常: {e}")
                time.sleep(60)  # 异常时等待1分钟

    async def _start_health_check(self):
        """启动健康检查"""
        if not self.config.monitoring.health_check_enabled:
            return

        logger.info("🏥 启动健康检查...")

        try:
            # 启动健康检查线程
            self.health_check_thread = threading.Thread(
                target=self._health_check_worker,
                daemon=True
            )
            self.health_check_thread.start()

            logger.info("✅ 健康检查启动完成")

        except Exception as e:
            logger.error(f"健康检查启动失败: {e}")
            raise

    def _health_check_worker(self):
        """健康检查工作线程"""
        logger.info("健康检查工作线程启动")

        while not self.shutdown_event.is_set():
            try:
                # 检查数据库连接
                if 'database' in self.services:
                    db_healthy = self.services['database'].is_connected()
                    if not db_healthy:
                        logger.error("数据库连接异常")

                # 检查缓存系统
                try:
                    from core.performance.enhanced_cache_system import get_global_cache_system
                    cache_system = get_global_cache_system()
                    cache_stats = cache_system.get_stats()
                    logger.debug(f"缓存状态: {len(cache_stats)} 个缓存层级")
                except Exception as e:
                    logger.error(f"缓存系统检查失败: {e}")

                # 检查插件系统
                if 'plugin_center' in self.services:
                    plugin_center = self.services['plugin_center']
                    plugin_count = len(plugin_center.data_source_plugins)
                    logger.debug(f"插件状态: {plugin_count} 个数据源插件")

                # 等待下次检查
                self.shutdown_event.wait(self.config.monitoring.health_check_interval)

            except Exception as e:
                logger.error(f"健康检查异常: {e}")
                time.sleep(60)

    async def _start_main_application(self):
        """启动主应用"""
        logger.info("🚀 启动主应用...")

        try:
            # 导入主应用
            from main import create_app

            # 创建应用实例
            app = create_app(self.config)

            # 配置uvicorn
            uvicorn_config = uvicorn.Config(
                app=app,
                host=self.config.ui.host,
                port=self.config.ui.port,
                log_level=self.config.logging.level.lower(),
                access_log=True,
                use_colors=False,
                loop="asyncio"
            )

            # 启动服务器
            server = uvicorn.Server(uvicorn_config)

            logger.info(f"🌟 FactorWeave-Quant 生产环境启动成功")
            logger.info(f"📍 访问地址: http://{self.config.ui.host}:{self.config.ui.port}")
            logger.info(f"📊 监控地址: http://{self.config.ui.host}:{self.config.monitoring.metrics_port}/metrics")

            # 运行服务器
            await server.serve()

        except Exception as e:
            logger.error(f"主应用启动失败: {e}")
            raise

    async def _cleanup(self):
        """清理资源"""
        logger.info("🧹 清理资源...")

        try:
            # 设置关闭事件
            self.shutdown_event.set()

            # 等待线程结束
            if self.health_check_thread and self.health_check_thread.is_alive():
                self.health_check_thread.join(timeout=5)

            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=5)

            # 关闭服务
            for service_name, service in self.services.items():
                try:
                    if hasattr(service, 'close'):
                        await service.close()
                    elif hasattr(service, 'disconnect'):
                        await service.disconnect()
                    logger.info(f"服务 {service_name} 已关闭")
                except Exception as e:
                    logger.error(f"关闭服务 {service_name} 失败: {e}")

            logger.info("✅ 资源清理完成")

        except Exception as e:
            logger.error(f"资源清理失败: {e}")


async def main():
    """主函数"""
    print("=" * 60)
    print("FactorWeave-Quant 专业量化平台 - 生产环境")
    print("=" * 60)

    server = ProductionServer()

    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("接收到中断信号，正在关闭...")
    except Exception as e:
        logger.error(f"服务器运行异常: {e}")
        return 1
    finally:
        await server._cleanup()

    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
