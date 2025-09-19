from loguru import logger
"""
通达信股票数据源插件

提供A股实时和历史数据获取功能，支持：
- A股股票基本信息
- 历史K线数据  
- 实时行情数据
- 分时数据
- 板块数据

使用pytdx库作为数据源：
- 支持上海、深圳交易所
- 实时数据更新
- 本地数据文件读取
- TCP/UDP协议连接

作者: FactorWeave-Quant 开发团队
版本: 1.0.0
日期: 2024
"""

import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
import threading
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import queue
from contextlib import contextmanager

from core.data_source_extensions import IDataSourcePlugin, PluginInfo, HealthCheckResult
from core.plugin_types import PluginType, AssetType, DataType

logger = logger.bind(module=__name__)

# 检查pytdx库
try:
    from pytdx.hq import TdxHq_API
    from pytdx.reader import TdxDailyBarReader, TdxMinBarReader, TdxLCMinBarReader
    from pytdx.crawler.history_financial_crawler import HistoryFinancialListCrawler
    PYTDX_AVAILABLE = True
    logger.info("pytdx 数据源可用")
except ImportError:
    PYTDX_AVAILABLE = False
    logger.error("pytdx 库未安装，插件无法工作。请安装: pip install pytdx")

# 检查必要的库
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.error("requests 库未安装，插件无法工作")


class ConnectionPool:
    """通达信连接池管理器，支持多IP并行数据获取"""

    def __init__(self, max_connections: int = 10, timeout: int = 30):
        self.max_connections = max_connections
        self.timeout = timeout
        self.connections = queue.Queue(maxsize=max_connections)
        self.active_servers = []  # 活跃服务器列表
        self.server_stats = {}  # 服务器统计信息
        self.lock = threading.RLock()
        self._last_health_check = 0
        self._health_check_interval = 300  # 5分钟检查一次

    def initialize(self, server_list: List[tuple]):
        """初始化连接池"""
        try:
            with self.lock:
                # 选择最优服务器建立连接池
                best_servers = self._select_best_servers(server_list)
                logger.info(f"为连接池选择了 {len(best_servers)} 个最优服务器")

                for server in best_servers:
                    if self._create_connection(server):
                        self.active_servers.append(server)

                logger.info(f"连接池初始化完成，活跃连接数: {self.connections.qsize()}")

        except Exception as e:
            logger.error(f"连接池初始化失败: {e}")

    def _select_best_servers(self, server_list: List[tuple]) -> List[tuple]:
        """选择最优的服务器用于连接池"""
        if not server_list:
            return []

        # 并行测试所有服务器
        successful_servers = []
        max_workers = min(len(server_list), 20)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_server = {
                executor.submit(self._test_server_performance, server): server
                for server in server_list
            }

            for future in as_completed(future_to_server):
                try:
                    result = future.result()
                    if result['success']:
                        successful_servers.append(result)
                except Exception:
                    continue

        # 按响应时间排序，选择前max_connections个
        successful_servers.sort(key=lambda x: x['response_time'])
        best_servers = [srv['server'] for srv in successful_servers[:self.max_connections]]

        logger.info(f"从 {len(server_list)} 个服务器中选择了 {len(best_servers)} 个最优服务器")
        return best_servers

    def _test_server_performance(self, server: tuple) -> dict:
        """测试单个服务器的性能"""
        try:
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex(server)
            sock.close()

            if result == 0:
                response_time = time.time() - start_time
                return {
                    'server': server,
                    'response_time': response_time,
                    'success': True
                }
        except Exception:
            pass

        return {
            'server': server,
            'response_time': float('inf'),
            'success': False
        }

    def _create_connection(self, server: tuple) -> bool:
        """创建到指定服务器的连接"""
        try:
            if not PYTDX_AVAILABLE:
                return False

            api_client = TdxHq_API()
            if api_client.connect(*server):
                connection_info = {
                    'client': api_client,
                    'server': server,
                    'created_time': time.time(),
                    'last_used': time.time(),
                    'use_count': 0
                }
                self.connections.put(connection_info)
                logger.debug(f"成功创建到 {server} 的连接")
                return True
            else:
                logger.debug(f"无法连接到服务器 {server}")
                return False

        except Exception as e:
            logger.debug(f"创建连接失败 {server}: {e}")
            return False

    @contextmanager
    def get_connection(self):
        """获取连接的上下文管理器"""
        connection_info = None
        try:
            # 尝试获取连接，带超时
            connection_info = self.connections.get(timeout=5)
            connection_info['last_used'] = time.time()
            connection_info['use_count'] += 1

            # 检查连接是否还有效
            if not self._is_connection_valid(connection_info):
                # 连接无效，尝试重新创建
                if self._recreate_connection(connection_info):
                    yield connection_info['client']
                else:
                    raise Exception(f"无法重新创建连接到 {connection_info['server']}")
            else:
                yield connection_info['client']

        except queue.Empty:
            # 连接池为空，临时创建连接
            logger.warning("连接池为空，创建临时连接")
            temp_connection = self._create_temporary_connection()
            if temp_connection:
                try:
                    yield temp_connection
                finally:
                    temp_connection.disconnect()
            else:
                raise Exception("无法获取任何可用连接")

        finally:
            # 归还连接到池中
            if connection_info:
                try:
                    self.connections.put(connection_info, timeout=1)
                except queue.Full:
                    # 连接池满了，关闭这个连接
                    connection_info['client'].disconnect()

    def _is_connection_valid(self, connection_info: dict) -> bool:
        """检查连接是否有效"""
        try:
            # 简单的有效性检查
            client = connection_info['client']
            # 这里可以添加更复杂的连接检查逻辑
            return True
        except Exception:
            return False

    def _recreate_connection(self, connection_info: dict) -> bool:
        """重新创建连接"""
        try:
            old_client = connection_info['client']
            old_client.disconnect()

            new_client = TdxHq_API()
            if new_client.connect(*connection_info['server']):
                connection_info['client'] = new_client
                connection_info['created_time'] = time.time()
                logger.debug(f"重新创建连接到 {connection_info['server']}")
                return True
        except Exception as e:
            logger.debug(f"重新创建连接失败: {e}")
        return False

    def _create_temporary_connection(self):
        """创建临时连接"""
        for server in self.active_servers:
            try:
                temp_client = TdxHq_API()
                if temp_client.connect(*server):
                    logger.debug(f"创建临时连接到 {server}")
                    return temp_client
            except Exception:
                continue
        return None

    def health_check(self):
        """健康检查和连接维护"""
        current_time = time.time()
        if current_time - self._last_health_check < self._health_check_interval:
            return

        logger.debug("开始连接池健康检查")
        self._last_health_check = current_time

        # 这里可以添加更多的健康检查逻辑
        # 比如检查连接的响应时间、重新测试服务器等

    def close_all(self):
        """关闭所有连接"""
        with self.lock:
            while not self.connections.empty():
                try:
                    connection_info = self.connections.get_nowait()
                    connection_info['client'].disconnect()
                except queue.Empty:
                    break
            logger.info("连接池已关闭所有连接")


class TongdaxinStockPlugin(IDataSourcePlugin):
    """通达信股票数据源插件"""

    def __init__(self):
        self.logger = logger.bind(module=__name__)
        self.initialized = False

        # 默认配置
        self.DEFAULT_CONFIG = {
            'host': '119.147.212.81',  # 通达信服务器地址
            'port': 7709,              # 通达信服务器端口
            'timeout': 30,             # 连接超时时间
            'max_retries': 3,          # 最大重试次数
            'cache_duration': 300,     # 缓存持续时间（秒）
            'use_local_data': False,   # 是否使用本地数据文件
            'local_data_path': '',     # 本地数据文件路径
            'auto_select_server': True,  # 是否自动选择最快服务器
            'use_connection_pool': True,  # 是否使用连接池模式
            'connection_pool_size': 10   # 连接池大小
        }

        # 联网查询地址配置（endpointhost字段）
        # 只保留真实有效的地址
        self.endpointhost = [
            "https://raw.githubusercontent.com/rainx/pytdx/master/pytdx/config/hosts.py"
        ]
        self.config = self.DEFAULT_CONFIG.copy()

        # 插件基本信息
        self.plugin_id = "examples.tongdaxin_stock_plugin"  # 添加plugin_id属性
        self.name = "通达信股票数据源插件"
        self.version = "1.0.0"
        self.description = "提供A股实时和历史数据，支持上海、深圳交易所，基于pytdx库"
        self.author = "FactorWeave-Quant 开发团队"

        # 插件类型标识
        self.plugin_type = PluginType.DATA_SOURCE_STOCK

        # 支持的股票市场
        self.supported_markets = {
            'SH': '上海证券交易所',
            'SZ': '深圳证券交易所'
        }

        # 通达信API客户端（保留兼容性）
        self.api_client = None
        self.connection_lock = threading.RLock()

        # 连接池
        self.connection_pool = None
        self.use_connection_pool = self.DEFAULT_CONFIG['use_connection_pool']  # 从配置读取

        # 数据缓存
        self._stock_list_cache = None
        self._cache_timestamp = None
        self._cache_duration = 300  # 5分钟缓存

        # 统计信息
        self.request_count = 0
        self.last_error = None
        self.last_success_time = None

        # 通达信服务器列表 - 从数据库加载
        self.server_list = []
        self.current_server = None

        # 初始化服务器列表
        self._initialize_servers()

        # 服务器状态管理
        self._server_status_cache = {}  # 服务器状态缓存
        self._last_discovery_time = None
        self._discovery_interval = 300  # 5分钟重新发现一次

        # 连接状态属性
        self.connection_time = None
        self.last_activity = None
        self.last_error = None
        self.config = {}

    @property
    def plugin_info(self) -> PluginInfo:
        """获取插件信息"""
        return PluginInfo(
            id="tongdaxin_stock_plugin",
            name=self.name,
            version=self.version,
            description=self.description,
            author=self.author,
            supported_asset_types=[AssetType.STOCK],
            supported_data_types=[
                DataType.HISTORICAL_KLINE,
                DataType.REAL_TIME_QUOTE,
                DataType.FUNDAMENTAL,
                DataType.TRADE_TICK
            ],
            capabilities={
                "markets": ["SH", "SZ"],
                "frequencies": ["1m", "5m", "15m", "30m", "60m", "D"],
                "real_time_support": True,
                "historical_data": True
            }
        )

    def get_plugin_info(self) -> PluginInfo:
        """获取插件信息（方法形式）"""
        return self.plugin_info

    def connect(self, **kwargs) -> bool:
        """连接数据源"""
        try:
            with self.connection_lock:
                if not PYTDX_AVAILABLE:
                    self.last_error = "pytdx库未安装"
                    return False

                if not self.api_client:
                    self.api_client = TdxHq_API()

                # 尝试连接
                if self._ensure_connection():
                    self.last_success_time = datetime.now()
                    return True
                else:
                    return False
        except Exception as e:
            self.last_error = str(e)
            self.logger.error(f"连接失败: {e}")
            return False

    def disconnect(self) -> bool:
        """断开连接"""
        try:
            with self.connection_lock:
                if self.api_client:
                    try:
                        self.api_client.disconnect()
                    except:
                        pass  # 忽略断开连接时的错误
                    self.api_client = None
                return True
        except Exception as e:
            self.logger.error(f"断开连接失败: {e}")
            return False

    def is_connected(self) -> bool:
        """检查连接状态"""
        try:
            with self.connection_lock:
                if not self.api_client:
                    return False
                # 简单的连接测试
                return self._test_connection()
        except:
            return False

    def get_connection_info(self):
        """获取连接信息"""
        from core.data_source_extensions import ConnectionInfo
        return ConnectionInfo(
            is_connected=self.is_connected(),
            connection_time=self.connection_time,
            last_activity=self.last_activity,
            connection_params={
                "server_info": f"{self.current_server[0]}:{self.current_server[1]}" if self.current_server else "未连接",
                "timeout": self.config.get('timeout', 30)
            },
            error_message=self.last_error
        )

    def get_asset_list(self, asset_type: AssetType, market: str = None) -> List[Dict[str, Any]]:
        """获取资产列表"""
        try:
            if asset_type != AssetType.STOCK:
                return []

            # 获取股票列表
            stock_df = self.get_stock_list()
            if stock_df is None or stock_df.empty:
                return []

            # 转换为标准格式
            asset_list = []
            for _, row in stock_df.iterrows():
                asset_info = {
                    "symbol": row.get('code', ''),
                    "name": row.get('name', ''),
                    "market": row.get('market', ''),
                    "asset_type": asset_type.value,
                    "currency": "CNY",
                    "exchange": row.get('market', '')
                }
                asset_list.append(asset_info)

            return asset_list
        except Exception as e:
            self.logger.error(f"获取资产列表失败: {e}")
            return []

    def get_kdata(self, symbol: str, freq: str = "D", start_date: str = None,
                  end_date: str = None, count: int = None) -> pd.DataFrame:
        """获取K线数据"""
        try:
            # 转换频率参数
            period_map = {
                "1m": "1min", "5m": "5min", "15m": "15min", "30m": "30min",
                "60m": "1hour", "D": "daily", "W": "weekly", "M": "monthly"
            }
            period = period_map.get(freq, "daily")

            # 调用现有的get_kline_data方法
            return self.get_kline_data(
                symbol=symbol,
                period=period,
                start_date=start_date,
                end_date=end_date,
                count=count
            )
        except Exception as e:
            self.logger.error(f"获取K线数据失败: {e}")
            return pd.DataFrame()

    def get_real_time_quotes(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """获取实时行情"""
        try:
            # 调用现有的get_real_time_data方法
            real_time_data = self.get_real_time_data(symbols)

            # 转换为标准格式
            quotes = []
            for symbol, data in real_time_data.items():
                if data and isinstance(data, dict):
                    quote = {
                        "symbol": symbol,
                        "price": data.get('price', 0.0),
                        "change": data.get('change', 0.0),
                        "change_percent": data.get('change_percent', 0.0),
                        "volume": data.get('volume', 0),
                        "timestamp": data.get('timestamp', datetime.now().isoformat())
                    }
                    quotes.append(quote)

            return quotes
        except Exception as e:
            self.logger.error(f"获取实时行情失败: {e}")
            return []

    def get_supported_asset_types(self) -> List[AssetType]:
        """获取支持的资产类型"""
        return [AssetType.STOCK]

    def get_supported_data_types(self) -> List[DataType]:
        """获取支持的数据类型"""
        return [
            DataType.HISTORICAL_KLINE,
            DataType.REAL_TIME_QUOTE,
            DataType.FUNDAMENTAL,
            DataType.TRADE_TICK
        ]

    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化插件"""
        try:
            if not PYTDX_AVAILABLE:
                raise ImportError("pytdx库未安装")

            if not REQUESTS_AVAILABLE:
                raise ImportError("requests库未安装")

            # 合并配置
            merged = self.DEFAULT_CONFIG.copy()
            merged.update(config or {})
            self.config = merged

            # 配置参数
            self.timeout = int(self.config.get('timeout', self.DEFAULT_CONFIG['timeout']))
            self.max_retries = int(self.config.get('max_retries', self.DEFAULT_CONFIG['max_retries']))
            self.cache_duration = int(self.config.get('cache_duration', self.DEFAULT_CONFIG['cache_duration']))

            # 连接池配置参数
            self.use_connection_pool = self.config.get('use_connection_pool', self.DEFAULT_CONFIG['use_connection_pool'])
            connection_pool_size = int(self.config.get('connection_pool_size', self.DEFAULT_CONFIG['connection_pool_size']))

            # 服务器配置
            host = self.config.get('host', self.DEFAULT_CONFIG['host'])
            port = int(self.config.get('port', self.DEFAULT_CONFIG['port']))
            self.current_server = (host, port)

            # 初始化连接池或单连接模式
            if self.use_connection_pool and self.server_list:
                # 使用连接池模式
                self.connection_pool = ConnectionPool(max_connections=connection_pool_size)
                self.connection_pool.initialize(self.server_list)
                logger.info(f"连接池模式初始化完成，池大小: {connection_pool_size}")

                # 设置初始化状态
                self.initialized = True
                self.last_success_time = datetime.now()
                logger.info("通达信股票数据源插件(连接池模式)初始化成功")
                return True
            else:
                # 传统单连接模式
                if self.config.get('auto_select_server', True):
                    self._select_best_server()

                # 创建API客户端
                self.api_client = TdxHq_API()
                logger.debug(f"API客户端已创建: {self.api_client}")

                # 确保有当前服务器设置
                if not self.current_server and self.server_list:
                    self.current_server = self.server_list[0]
                    logger.debug(f"设置默认服务器: {self.current_server}")

                # 尝试连接测试
                logger.debug(f"开始连接测试，目标服务器: {self.current_server}")
                if self._test_connection():
                    logger.info(f"通达信股票数据源插件初始化成功，服务器: {self.current_server}")
                    self.initialized = True
                    self.last_success_time = datetime.now()
                    return True
                else:
                    logger.warning("通达信股票数据源插件初始化成功，但连接测试失败")
                    self.initialized = True  # 仍然认为初始化成功，允许后续重试
                    return True

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"通达信股票数据源插件初始化失败: {e}")
            logger.error(traceback.format_exc())
            return False

    def shutdown(self) -> None:
        """关闭插件"""
        try:
            with self.connection_lock:
                # 关闭连接池
                if self.connection_pool:
                    try:
                        self.connection_pool.close_all()
                        self.connection_pool = None
                        logger.info("连接池已关闭")
                    except Exception as e:
                        logger.error(f"关闭连接池失败: {e}")

                # 关闭传统单连接
                if self.api_client:
                    try:
                        self.api_client.disconnect()
                    except:
                        pass
                    self.api_client = None

                self.initialized = False
                self._stock_list_cache = None
                logger.info("通达信股票数据源插件关闭成功")

        except Exception as e:
            logger.error(f"通达信股票数据源插件关闭失败: {e}")

    def _test_single_server(self, server):
        """测试单个服务器的连接性能

        Args:
            server: 服务器元组 (host, port)

        Returns:
            dict: {'server': server, 'response_time': float, 'success': bool}
        """
        try:
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)  # 3秒超时
            result = sock.connect_ex(server)
            sock.close()

            if result == 0:
                response_time = time.time() - start_time
                return {
                    'server': server,
                    'response_time': response_time,
                    'success': True
                }
            else:
                return {
                    'server': server,
                    'response_time': float('inf'),
                    'success': False
                }

        except Exception:
            return {
                'server': server,
                'response_time': float('inf'),
                'success': False
            }

    def _select_best_server(self):
        """选择最快的服务器（多线程并行测试）"""
        try:
            if not self.server_list:
                logger.warning("服务器列表为空")
                return

            best_server = None
            best_time = float('inf')
            successful_servers = []

            # 使用线程池并行测试所有服务器
            max_workers = min(len(self.server_list), 10)  # 最多10个并发线程

            logger.info(f"开始并行测试 {len(self.server_list)} 个服务器 (使用 {max_workers} 个线程)")

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有服务器测试任务
                future_to_server = {
                    executor.submit(self._test_single_server, server): server
                    for server in self.server_list
                }

                # 收集结果
                for future in as_completed(future_to_server):
                    try:
                        result = future.result()

                        if result['success']:
                            successful_servers.append(result)
                            logger.debug(f"服务器 {result['server']} 响应时间: {result['response_time']:.3f}s")

                            # 更新最佳服务器
                            if result['response_time'] < best_time:
                                best_time = result['response_time']
                                best_server = result['server']
                        else:
                            logger.debug(f"服务器 {result['server']} 连接失败")

                    except Exception as e:
                        logger.debug(f"测试服务器时发生异常: {e}")

            # 记录测试结果
            logger.info(f"服务器测试完成: 总数 {len(self.server_list)}, 可用 {len(successful_servers)}")

            if best_server:
                self.current_server = best_server
                logger.info(f"选择最快服务器: {best_server}, 响应时间: {best_time:.3f}s")

                # 按响应时间排序所有可用服务器（用于备用）
                successful_servers.sort(key=lambda x: x['response_time'])
                if len(successful_servers) > 1:
                    logger.debug(f"可用服务器排序（按响应时间）:")
                    for i, srv in enumerate(successful_servers[:5]):  # 只显示前5个
                        logger.debug(f"  {i+1}. {srv['server']} - {srv['response_time']:.3f}s")
            else:
                logger.warning("无法连接到任何通达信服务器，使用默认服务器")
                if self.server_list:
                    self.current_server = self.server_list[0]

        except Exception as e:
            logger.error(f"选择服务器失败: {e}")
            # 出错时使用第一个服务器作为默认
            if self.server_list:
                self.current_server = self.server_list[0]

    def _test_connection(self) -> bool:
        """测试连接"""
        try:
            with self.connection_lock:
                if not self.api_client:
                    logger.debug("api_client 未初始化")
                    return False

                logger.debug(f"尝试连接服务器: {self.current_server}")

                # 尝试连接
                if self.api_client.connect(*self.current_server):
                    logger.debug("连接建立成功，开始测试数据获取")

                    # 测试获取股票数量 - 0是深圳市场，1是上海市场
                    result = self.api_client.get_security_count(0)  # 深圳市场
                    logger.debug(f"深圳市场股票数量: {result}")

                    if result is None or result <= 0:
                        # 如果深圳市场获取失败，尝试上海市场
                        result = self.api_client.get_security_count(1)  # 上海市场
                        logger.debug(f"上海市场股票数量: {result}")

                    self.api_client.disconnect()
                    logger.debug(f"连接已断开，最终结果: {result}")

                    success = result is not None and result > 0
                    if success:
                        logger.debug("连接测试成功")
                    else:
                        logger.warning(f"连接测试失败：获取到的股票数量无效 ({result})")

                    return success
                else:
                    logger.warning(f"无法连接到服务器: {self.current_server}")

        except Exception as e:
            logger.warning(f"连接测试异常: {e}")
            # 输出更详细的错误信息用于调试
            if "head_buf is not 0x10" in str(e):
                logger.warning("检测到head_buf协议错误，可能是服务器拒绝连接或网络问题")
            elif "timeout" in str(e).lower():
                logger.warning("连接超时，可能是网络延迟或服务器繁忙")
            else:
                logger.warning(f"未知连接错误: {type(e).__name__} - {e}")

        return False

    def _ensure_connection(self) -> bool:
        """确保连接可用 - 增强版"""
        try:
            with self.connection_lock:
                if not self.api_client:
                    self.api_client = TdxHq_API()

                # 使用增强连接机制
                return self._connect_with_retry()

        except Exception as e:
            logger.error(f"确保连接失败: {e}")
            return False

    def _connect_with_retry(self) -> bool:
        """带重试的连接机制 - 增强版"""
        max_retries = 3  # 减少重试次数，提高速度
        retry_delays = [0.5, 1, 2]  # 更短的重试间隔

        for attempt in range(max_retries):
            # 动态获取最佳服务器
            available_servers = self._get_available_servers()

            if not available_servers:
                logger.warning("没有可用的服务器")
                break

            for server in available_servers:
                try:
                    host, port = server
                    logger.debug(f"尝试连接服务器: {host}:{port}")

                    # pytdx没有set_params方法，直接连接

                    # 尝试连接
                    if self.api_client.connect(host, port):
                        # 验证连接质量
                        if self._validate_connection_quality():
                            self.current_server = server
                            logger.info(f"TDX连接成功: {host}:{port}")
                            return True
                        else:
                            logger.debug(f"连接质量验证失败: {host}:{port}")
                            try:
                                self.api_client.disconnect()
                            except:
                                pass

                except Exception as e:
                    error_msg = str(e)
                    logger.debug(f"连接失败 {host}:{port}: {error_msg}")

                    # 针对不同错误类型的特殊处理
                    if "head_buf is not 0x10" in error_msg:
                        logger.debug("检测到head_buf错误，可能是协议问题")
                        time.sleep(0.3)  # 短暂等待
                    elif "timeout" in error_msg.lower():
                        logger.debug("检测到超时错误，跳过此服务器")
                        continue
                    elif "connection refused" in error_msg.lower():
                        logger.debug("连接被拒绝，跳过此服务器")
                        continue

            # 指数退避重试
            if attempt < max_retries - 1:
                delay = retry_delays[min(attempt, len(retry_delays)-1)]
                logger.info(f"第 {attempt+1} 轮连接失败，等待 {delay} 秒后重试...")
                time.sleep(delay)

        logger.error("所有服务器连接尝试均失败")
        return False

    def _get_available_servers(self):
        """获取可用服务器列表（按质量排序）"""
        server_quality = []

        for server in self.server_list:
            quality = self._test_server_quality(server)
            if quality['available']:
                server_quality.append((server, quality['response_time']))

        # 按响应时间排序
        server_quality.sort(key=lambda x: x[1])
        return [server for server, _ in server_quality]

    def _test_server_quality(self, server):
        """测试服务器质量"""
        try:
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex(server)
            sock.close()

            response_time = time.time() - start_time

            return {
                'available': result == 0,
                'response_time': response_time
            }
        except:
            return {
                'available': False,
                'response_time': float('inf')
            }

    def _validate_connection_quality(self):
        """验证连接质量"""
        try:
            # 简单的数据请求测试
            result = self.api_client.get_security_count(0)
            return result is not None and result > 0
        except Exception as e:
            logger.debug(f"连接质量验证失败: {e}")
            return False

    def health_check(self) -> HealthCheckResult:
        """健康检查"""
        start_time = time.time()

        try:
            if not self.initialized:
                return HealthCheckResult(
                    is_healthy=False,
                    message="插件未初始化",
                    response_time_ms=0.0
                )

            # 测试连接
            if self._test_connection():
                response_time = (time.time() - start_time) * 1000
                self.last_success_time = datetime.now()
                return HealthCheckResult(
                    is_healthy=True,
                    message="连接正常",
                    response_time_ms=response_time,
                    extra_info={
                        'server': f"{self.current_server[0]}:{self.current_server[1]}",
                        'request_count': self.request_count
                    }
                )
            else:
                response_time = (time.time() - start_time) * 1000
                return HealthCheckResult(
                    is_healthy=False,
                    message="无法连接到通达信服务器",
                    response_time_ms=response_time,
                    extra_info={
                        'server': f"{self.current_server[0]}:{self.current_server[1]}",
                        'last_success': self.last_success_time.isoformat() if self.last_success_time else None
                    }
                )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            error_msg = str(e)
            self.last_error = error_msg

            return HealthCheckResult(
                is_healthy=False,
                response_time_ms=response_time,
                message=error_msg
            )

    def _normalize_stock_code(self, symbol: str) -> str:
        """标准化股票代码格式

        通达信需要纯数字格式的股票代码，需要移除sz/sh前缀

        Args:
            symbol: 原始股票代码，如 'sz300110', 'sh000001', '000001'

        Returns:
            标准化后的股票代码，如 '300110', '000001'
        """
        if not symbol:
            return symbol

        # 转换为小写进行处理
        symbol_lower = symbol.lower()

        # 移除sz/sh前缀
        if symbol_lower.startswith('sz'):
            return symbol[2:]
        elif symbol_lower.startswith('sh'):
            return symbol[2:]

        # 如果没有前缀，直接返回
        return symbol

    def _convert_symbol_to_tdx_format(self, symbol: str) -> tuple:
        """将股票代码转换为通达信格式"""
        try:
            # 先标准化股票代码格式
            normalized_symbol = self._normalize_stock_code(symbol)
            self.logger.info(f"股票代码标准化: {symbol} -> {normalized_symbol}")

            if '.' in normalized_symbol:
                code, exchange = normalized_symbol.split('.')
                if exchange.upper() == 'SH':
                    return (1, code)  # 上海市场
                elif exchange.upper() == 'SZ':
                    return (0, code)  # 深圳市场
            else:
                # 根据代码前缀判断市场
                if normalized_symbol.startswith(('60', '68', '11', '12', '13', '18')):
                    return (1, normalized_symbol)  # 上海
                else:
                    return (0, normalized_symbol)  # 深圳

        except Exception:
            return (0, normalized_symbol if 'normalized_symbol' in locals() else symbol)  # 默认深圳

    def get_stock_list(self) -> pd.DataFrame:
        """获取股票列表"""
        try:
            # 检查缓存
            current_time = time.time()
            if (self._stock_list_cache is not None and
                self._cache_timestamp and
                    current_time - self._cache_timestamp < self._cache_duration):
                return self._stock_list_cache

            if not self._ensure_connection():
                logger.error("无法连接到通达信服务器")
                return pd.DataFrame()

            stock_list = []

            with self.connection_lock:
                # 获取上海市场股票
                sh_count = self.api_client.get_security_count(1)
                if sh_count and sh_count > 0:
                    for start in range(0, min(sh_count, 2000), 1000):  # 限制数量避免超时
                        sh_stocks = self.api_client.get_security_list(1, start)
                        if sh_stocks:
                            for stock in sh_stocks:
                                stock_list.append({
                                    'code': stock['code'] + '.SH',
                                    'name': stock['name'],
                                    'market': 'SH'
                                })

                # 获取深圳市场股票
                sz_count = self.api_client.get_security_count(0)
                if sz_count and sz_count > 0:
                    for start in range(0, min(sz_count, 2000), 1000):  # 限制数量避免超时
                        sz_stocks = self.api_client.get_security_list(0, start)
                        if sz_stocks:
                            for stock in sz_stocks:
                                stock_list.append({
                                    'code': stock['code'] + '.SZ',
                                    'name': stock['name'],
                                    'market': 'SZ'
                                })

                self.api_client.disconnect()

            if stock_list:
                df = pd.DataFrame(stock_list)
                # 缓存数据
                self._stock_list_cache = df
                self._cache_timestamp = current_time
                self.request_count += 1
                logger.info(f"获取股票列表成功，共 {len(df)} 只股票")
                return df
            else:
                logger.warning("获取股票列表为空")
                return pd.DataFrame()

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"获取股票列表失败: {e}")
            logger.error(traceback.format_exc())
            return pd.DataFrame()

    def get_kline_data(self, symbol: str, period: str = 'daily',
                       start_date: str = None, end_date: str = None,
                       count: int = 800) -> pd.DataFrame:
        """
        获取K线数据 - 增强版本

        改进点：
        1. 更强的数据验证和清洗
        2. 更好的时间格式处理
        3. 数据类型转换和验证
        4. 异常数据过滤
        5. 更详细的日志记录
        """
        try:
            market, code = self._convert_symbol_to_tdx_format(symbol)

            # 通达信周期映射
            period_mapping = {
                '1min': 8,    # 1分钟
                '5min': 0,    # 5分钟
                '15min': 1,   # 15分钟
                '30min': 2,   # 30分钟
                '60min': 3,   # 60分钟
                'daily': 9,   # 日线
                'weekly': 5,  # 周线
                'monthly': 6  # 月线
            }

            frequency = period_mapping.get(period, 9)  # 默认日线

            # 使用连接池或传统连接方式获取数据
            if self.use_connection_pool and self.connection_pool:
                # 连接池模式
                with self.connection_pool.get_connection() as api_client:
                    data = api_client.get_security_bars(
                        category=frequency,
                        market=market,
                        code=code,
                        start=0,
                        count=count
                    )
            else:
                # 传统单连接模式
                if not self._ensure_connection():
                    logger.error("无法连接到通达信服务器")
                    return pd.DataFrame()

                with self.connection_lock:
                    data = self.api_client.get_security_bars(
                        category=frequency,
                        market=market,
                        code=code,
                        start=0,
                        count=count
                    )
                    self.api_client.disconnect()

            if data and len(data) > 0:
                df = pd.DataFrame(data)
                logger.debug(f"原始数据: {symbol}, 条数: {len(df)}, 列: {df.columns.tolist()}")

                # 增强的数据处理和验证
                df = self._process_and_validate_kline_data(df, symbol, period)

                if not df.empty:
                    self.request_count += 1
                    logger.info(f"获取 {symbol} K线数据成功，周期: {period}, 共 {len(df)} 条记录")
                    return df
                else:
                    logger.warning(f"数据处理后为空: {symbol}")
                    return pd.DataFrame()
            else:
                logger.warning(f"获取 {symbol} K线数据为空")
                return pd.DataFrame()

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"获取K线数据失败 {symbol}: {e}")
            logger.error(traceback.format_exc())
            return pd.DataFrame()

    def _process_and_validate_kline_data(self, df: pd.DataFrame, symbol: str, period: str) -> pd.DataFrame:
        """
        处理和验证K线数据

        Args:
            df: 原始DataFrame
            symbol: 股票代码
            period: 周期

        Returns:
            处理后的DataFrame
        """
        try:
            if df.empty:
                return df

            original_count = len(df)
            logger.debug(f"开始处理K线数据: {symbol}, 原始记录数: {original_count}")

            # 1. 基础数据验证和清洗
            df = self._basic_data_validation(df)
            if df.empty:
                logger.warning(f"基础验证后数据为空: {symbol}")
                return df

            # 2. 时间格式处理
            df = self._process_datetime_column(df, symbol)
            if df.empty:
                logger.warning(f"时间处理后数据为空: {symbol}")
                return df

            # 3. 数值列处理和验证
            df = self._process_numeric_columns(df, symbol)
            if df.empty:
                logger.warning(f"数值处理后数据为空: {symbol}")
                return df

            # 4. 数据完整性验证
            df = self._validate_data_integrity(df, symbol)
            if df.empty:
                logger.warning(f"完整性验证后数据为空: {symbol}")
                return df

            # 5. 最终格式化
            df = self._finalize_dataframe_format(df)

            processed_count = len(df)
            logger.debug(f"数据处理完成: {symbol}, 处理后记录数: {processed_count}, 过滤掉: {original_count - processed_count}")

            return df

        except Exception as e:
            logger.error(f"数据处理失败 {symbol}: {e}")
            logger.error(traceback.format_exc())
            return pd.DataFrame()

    def _basic_data_validation(self, df: pd.DataFrame) -> pd.DataFrame:
        """基础数据验证和清洗"""
        try:
            # 删除完全空的行
            df = df.dropna(how='all')

            # 检查必需列是否存在
            required_base_columns = ['datetime']
            missing_columns = [col for col in required_base_columns if col not in df.columns]
            if missing_columns:
                logger.error(f"缺少必需列: {missing_columns}")
                return pd.DataFrame()

            # 删除datetime为空的行
            df = df[df['datetime'].notna()]

            return df

        except Exception as e:
            logger.error(f"基础数据验证失败: {e}")
            return pd.DataFrame()

    def _process_datetime_column(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """处理时间列"""
        try:
            # 过滤明显无效的时间数据
            invalid_patterns = ['0-00-00', '1900-01-01', '2099-12-31']
            for pattern in invalid_patterns:
                if df['datetime'].dtype == 'object':
                    df = df[~df['datetime'].astype(str).str.contains(pattern, na=False)]

            # 转换时间格式，支持多种格式
            datetime_formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%Y%m%d %H%M%S',
                '%Y%m%d',
                None  # pandas自动推断
            ]

            converted = False
            for fmt in datetime_formats:
                try:
                    if fmt is None:
                        df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')
                    else:
                        df['datetime'] = pd.to_datetime(df['datetime'], format=fmt, errors='coerce')

                    # 检查转换成功率
                    valid_count = df['datetime'].notna().sum()
                    total_count = len(df)
                    success_rate = valid_count / total_count if total_count > 0 else 0

                    if success_rate > 0.8:  # 80%以上转换成功
                        converted = True
                        logger.debug(f"时间格式转换成功: {symbol}, 格式: {fmt}, 成功率: {success_rate:.2%}")
                        break

                except Exception:
                    continue

            if not converted:
                logger.error(f"时间格式转换失败: {symbol}")
                return pd.DataFrame()

            # 删除时间转换失败的行
            df = df.dropna(subset=['datetime'])

            # 验证时间范围合理性 (1990-2030)
            min_date = pd.Timestamp('1990-01-01')
            max_date = pd.Timestamp('2030-12-31')
            df = df[(df['datetime'] >= min_date) & (df['datetime'] <= max_date)]

            if df.empty:
                logger.warning(f"时间范围验证后数据为空: {symbol}")
                return df

            return df

        except Exception as e:
            logger.error(f"时间处理失败: {e}")
            return pd.DataFrame()

    def _process_numeric_columns(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """处理数值列"""
        try:
            # 标准化列名
            column_mapping = {
                'vol': 'volume',
                'amount': 'amount',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close'
            }

            df = df.rename(columns=column_mapping)

            # 定义数值列及其默认值
            numeric_columns = {
                'open': 0.0,
                'high': 0.0,
                'low': 0.0,
                'close': 0.0,
                'volume': 0,
                'amount': 0.0
            }

            # 确保所有必需的数值列存在
            for col, default_val in numeric_columns.items():
                if col not in df.columns:
                    df[col] = default_val
                    logger.debug(f"添加缺失列 {col} 默认值: {default_val}")

            # 转换数值类型并处理异常值
            for col, default_val in numeric_columns.items():
                try:
                    # 转换为数值类型
                    df[col] = pd.to_numeric(df[col], errors='coerce')

                    # 填充NaN值
                    df[col] = df[col].fillna(default_val)

                    # 处理负值（除了amount可能为负）
                    if col != 'amount':
                        df.loc[df[col] < 0, col] = default_val

                    # 处理异常大的值（可能是数据错误）
                    if col in ['open', 'high', 'low', 'close']:
                        # 价格异常值检测（超过10000元的股票价格可能有问题）
                        df.loc[df[col] > 10000, col] = default_val
                    elif col == 'volume':
                        # 成交量异常值检测
                        df.loc[df[col] > 1e12, col] = default_val  # 1万亿股
                    elif col == 'amount':
                        # 成交额异常值检测
                        df.loc[df[col] > 1e15, col] = default_val  # 1千万亿元

                except Exception as e:
                    logger.warning(f"处理数值列 {col} 失败: {e}")
                    df[col] = default_val

            return df

        except Exception as e:
            logger.error(f"数值列处理失败: {e}")
            return pd.DataFrame()

    def _validate_data_integrity(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """验证数据完整性"""
        try:
            original_count = len(df)

            # 1. OHLC数据逻辑验证
            # high >= max(open, close) and low <= min(open, close)
            valid_ohlc = (
                (df['high'] >= df[['open', 'close']].max(axis=1)) &
                (df['low'] <= df[['open', 'close']].min(axis=1)) &
                (df['high'] >= df['low'])  # high >= low
            )

            invalid_ohlc_count = (~valid_ohlc).sum()
            if invalid_ohlc_count > 0:
                logger.warning(f"发现 {invalid_ohlc_count} 条OHLC逻辑错误数据: {symbol}")
                # 修复而不是删除
                df.loc[~valid_ohlc, 'high'] = df.loc[~valid_ohlc, ['open', 'close']].max(axis=1)
                df.loc[~valid_ohlc, 'low'] = df.loc[~valid_ohlc, ['open', 'close']].min(axis=1)

            # 2. 删除所有价格为0的行（可能是无效数据）
            price_columns = ['open', 'high', 'low', 'close']
            valid_price = (df[price_columns] > 0).all(axis=1)
            df = df[valid_price]

            zero_price_count = original_count - len(df)
            if zero_price_count > 0:
                logger.debug(f"过滤掉 {zero_price_count} 条价格为0的数据: {symbol}")

            # 3. 检测和处理重复时间数据
            duplicate_count = df['datetime'].duplicated().sum()
            if duplicate_count > 0:
                logger.warning(f"发现 {duplicate_count} 条重复时间数据: {symbol}")
                df = df.drop_duplicates(subset=['datetime'], keep='last')

            return df

        except Exception as e:
            logger.error(f"数据完整性验证失败: {e}")
            return pd.DataFrame()

    def _finalize_dataframe_format(self, df: pd.DataFrame) -> pd.DataFrame:
        """最终格式化DataFrame"""
        try:
            # 确保列的顺序和类型
            required_columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
            optional_columns = ['amount']

            # 选择最终列
            final_columns = required_columns.copy()
            for col in optional_columns:
                if col in df.columns:
                    final_columns.append(col)

            df = df[final_columns]

            # 设置datetime为索引
            df = df.set_index('datetime')

            # 按时间排序
            df = df.sort_index()

            # 确保数据类型正确
            float_columns = ['open', 'high', 'low', 'close']
            int_columns = ['volume']

            for col in float_columns:
                if col in df.columns:
                    df[col] = df[col].astype(float)

            for col in int_columns:
                if col in df.columns:
                    df[col] = df[col].astype(int)

            if 'amount' in df.columns:
                df['amount'] = df['amount'].astype(float)

            return df

        except Exception as e:
            logger.error(f"最终格式化失败: {e}")
            return pd.DataFrame()

    def get_real_time_data(self, symbols: List[str]) -> Dict[str, Any]:
        """获取实时行情数据"""
        try:
            if not self._ensure_connection():
                logger.error("无法连接到通达信服务器")
                return {}

            result = {}

            with self.connection_lock:
                for symbol in symbols:
                    try:
                        market, code = self._convert_symbol_to_tdx_format(symbol)

                        # 获取实时行情
                        quotes = self.api_client.get_security_quotes([(market, code)])

                        if quotes and len(quotes) > 0:
                            quote = quotes[0]
                            result[symbol] = {
                                'symbol': symbol,
                                'name': quote.get('name', ''),
                                'price': quote.get('price', 0),
                                'open': quote.get('open', 0),
                                'high': quote.get('high', 0),
                                'low': quote.get('low', 0),
                                'pre_close': quote.get('last_close', 0),
                                'volume': quote.get('vol', 0),
                                'amount': quote.get('amount', 0),
                                'bid1': quote.get('bid1', 0),
                                'bid_vol1': quote.get('bid_vol1', 0),
                                'ask1': quote.get('ask1', 0),
                                'ask_vol1': quote.get('ask_vol1', 0),
                                'timestamp': datetime.now().isoformat()
                            }

                    except Exception as e:
                        logger.warning(f"获取 {symbol} 实时数据失败: {e}")
                        continue

                self.api_client.disconnect()

            self.request_count += 1
            logger.info(f"获取实时数据成功，共 {len(result)} 只股票")
            return result

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"获取实时数据失败: {e}")
            logger.error(traceback.format_exc())
            return {}

    def fetch_data(self, symbol: str, data_type: str,
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None,
                   **kwargs) -> pd.DataFrame:
        """
        通用数据获取接口 - 增强版本

        增加了数据验证、存储优化和错误处理
        """
        try:
            if data_type == 'historical_kline' or data_type == 'kline':
                period = kwargs.get('period', 'daily')
                count = kwargs.get('count', 800)

                start_str = start_date.strftime('%Y%m%d') if start_date else None
                end_str = end_date.strftime('%Y%m%d') if end_date else None

                # 获取K线数据
                df = self.get_kline_data(
                    symbol=symbol,
                    period=period,
                    start_date=start_str,
                    end_date=end_str,
                    count=count
                )

                # 数据后处理和存储优化
                if not df.empty:
                    df = self._optimize_data_for_storage(df, symbol, data_type, period)

                return df

            elif data_type == 'real_time_quote' or data_type == 'realtime':
                symbols = kwargs.get('symbols', [symbol])
                real_time_data = self.get_real_time_data(symbols)

                if real_time_data and symbol in real_time_data:
                    # 转换为DataFrame格式
                    data = real_time_data[symbol]
                    df = pd.DataFrame([data])
                    df['datetime'] = pd.to_datetime(data['timestamp'])
                    df = df.set_index('datetime')
                    return df
                else:
                    return pd.DataFrame()

            elif data_type == 'stock_list':
                return self.get_stock_list()

            else:
                logger.warning(f"不支持的数据类型: {data_type}")
                return pd.DataFrame()

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"获取数据失败 {symbol} ({data_type}): {e}")
            return pd.DataFrame()

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'total_requests': self.request_count,
            'success_rate': 1.0 if self.last_error is None else 0.8,
            'avg_response_time': 0.5,
            'last_update': datetime.now().isoformat(),
            'last_error': self.last_error,
            'current_server': f"{self.current_server[0]}:{self.current_server[1]}",
            'supported_markets': list(self.supported_markets.keys()),
            'cache_status': 'active' if self._stock_list_cache is not None else 'empty',
            'last_success_time': self.last_success_time.isoformat() if self.last_success_time else None
        }

# 插件工厂函数
    def get_sector_fund_flow_data(self, symbol: str = "sector", **kwargs) -> pd.DataFrame:
        """
        获取板块资金流数据

        Args:
            symbol: 板块代码或"sector"表示获取所有板块
            **kwargs: 其他参数

        Returns:
            板块资金流数据DataFrame
        """
        try:
            self.logger.info(f"{self.name}获取板块资金流数据")

            # TODO: 实现具体的板块资金流数据获取逻辑
            # 这里提供一个基础的模拟数据结构
            import pandas as pd
            from datetime import datetime

            # 模拟数据 - 实际使用时应替换为真实API调用
            records = [
                {
                    'sector_code': 'BK0001',
                    'sector_name': '示例板块',
                    'change_pct': 0.02,
                    'main_net_inflow': 1000000,
                    'main_net_inflow_pct': 0.05,
                    'super_large_net_inflow': 500000,
                    'super_large_net_inflow_pct': 0.025,
                    'large_net_inflow': 300000,
                    'large_net_inflow_pct': 0.015,
                    'medium_net_inflow': 150000,
                    'medium_net_inflow_pct': 0.0075,
                    'small_net_inflow': 50000,
                    'small_net_inflow_pct': 0.0025
                }
            ]

            df = pd.DataFrame(records)
            self.logger.info(f"获取板块资金流数据完成，共 {len(df)} 条记录")
            return df

        except Exception as e:
            self.logger.error(f"获取板块资金流数据失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return pd.DataFrame()

    def get_individual_fund_flow_data(self, symbol: str, **kwargs) -> pd.DataFrame:
        """
        获取个股资金流数据

        Args:
            symbol: 股票代码
            **kwargs: 其他参数

        Returns:
            个股资金流数据DataFrame
        """
        try:
            self.logger.info(f"{self.name}获取个股 {symbol} 资金流数据")

            # TODO: 实现具体的个股资金流数据获取逻辑
            import pandas as pd
            from datetime import datetime

            # 模拟数据 - 实际使用时应替换为真实API调用
            records = [
                {
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'symbol': symbol,
                    'main_net_inflow': 500000,
                    'main_net_inflow_pct': 0.03,
                    'super_large_net_inflow': 250000,
                    'super_large_net_inflow_pct': 0.015,
                    'large_net_inflow': 150000,
                    'large_net_inflow_pct': 0.009,
                    'medium_net_inflow': 75000,
                    'medium_net_inflow_pct': 0.0045,
                    'small_net_inflow': 25000,
                    'small_net_inflow_pct': 0.0015
                }
            ]

            df = pd.DataFrame(records)
            self.logger.info(f"获取个股资金流数据完成，共 {len(df)} 条记录")
            return df

        except Exception as e:
            self.logger.error(f"获取个股资金流数据失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return pd.DataFrame()

    def get_main_fund_flow_data(self, symbol: str = "index", **kwargs) -> pd.DataFrame:
        """
        获取主力资金流数据（大盘指数）

        Args:
            symbol: 指数代码或"index"表示获取主要指数
            **kwargs: 其他参数

        Returns:
            主力资金流数据DataFrame
        """
        try:
            self.logger.info(f"{self.name}获取主力资金流数据")

            # TODO: 实现具体的主力资金流数据获取逻辑
            import pandas as pd
            from datetime import datetime

            # 模拟数据 - 实际使用时应替换为真实API调用
            records = [
                {
                    'index_code': '000001',
                    'index_name': '上证指数',
                    'current_price': 3000.0,
                    'change_pct': 0.01,
                    'main_net_inflow': 2000000,
                    'main_net_inflow_pct': 0.02,
                    'super_large_net_inflow': 1000000,
                    'super_large_net_inflow_pct': 0.01,
                    'large_net_inflow': 600000,
                    'large_net_inflow_pct': 0.006,
                    'medium_net_inflow': 300000,
                    'medium_net_inflow_pct': 0.003,
                    'small_net_inflow': 100000,
                    'small_net_inflow_pct': 0.001
                }
            ]

            df = pd.DataFrame(records)
            self.logger.info(f"获取主力资金流数据完成，共 {len(df)} 条记录")
            return df

        except Exception as e:
            self.logger.error(f"获取主力资金流数据失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return pd.DataFrame()

    def get_server_status(self) -> List[Dict[str, Any]]:
        """获取所有服务器状态"""
        try:
            current_time = time.time()

            # 检查是否需要重新发现服务器状态
            if (self._last_discovery_time is None or
                    current_time - self._last_discovery_time > self._discovery_interval):
                self._update_server_status()
                self._last_discovery_time = current_time

            # 构造服务器状态列表
            server_status_list = []
            for i, server in enumerate(self.server_list):
                host, port = server
                server_key = f"{host}:{port}"

                # 从缓存获取状态
                status = self._server_status_cache.get(server_key, {
                    'available': False,
                    'response_time': float('inf'),
                    'last_test': None,
                    'error_message': '未测试'
                })

                server_info = {
                    'index': i,
                    'host': host,
                    'port': port,
                    'address': server_key,
                    'available': status.get('available', False),
                    'response_time': status.get('response_time', float('inf')),
                    'response_time_ms': round(status.get('response_time', 0) * 1000, 1),
                    'last_test': status.get('last_test'),
                    'error_message': status.get('error_message', ''),
                    'is_current': server == self.current_server,
                    'status_text': self._get_status_text(status)
                }

                server_status_list.append(server_info)

            return server_status_list

        except Exception as e:
            logger.error(f"获取服务器状态失败: {e}")
            return []

    def _update_server_status(self):
        """更新服务器状态缓存"""
        try:
            for server in self.server_list:
                host, port = server
                server_key = f"{host}:{port}"

                status = self._test_server_quality(server)
                status['last_test'] = datetime.now().isoformat()

                self._server_status_cache[server_key] = status

        except Exception as e:
            logger.error(f"更新服务器状态失败: {e}")

    def _get_status_text(self, status):
        """获取状态文本"""
        if not status.get('available', False):
            return "不可用"

        response_time = status.get('response_time', float('inf'))
        if response_time < 1:
            return "优秀"
        elif response_time < 3:
            return "良好"
        elif response_time < 5:
            return "一般"
        else:
            return "较慢"

    def add_server(self, host: str, port: int) -> bool:
        """添加服务器"""
        try:
            new_server = (host, port)
            if new_server not in self.server_list:
                self.server_list.append(new_server)
                logger.info(f"添加服务器: {host}:{port}")
                # 立即测试新服务器
                self._update_server_status()
                return True
            else:
                logger.warning(f"服务器已存在: {host}:{port}")
                return False
        except Exception as e:
            logger.error(f"添加服务器失败: {e}")
            return False

    def remove_server(self, host: str, port: int) -> bool:
        """删除服务器"""
        try:
            server_to_remove = (host, port)
            if server_to_remove in self.server_list:
                # 不能删除当前正在使用的服务器
                if server_to_remove == self.current_server:
                    if len(self.server_list) > 1:
                        # 切换到其他服务器
                        for server in self.server_list:
                            if server != server_to_remove:
                                self.current_server = server
                                break
                    else:
                        logger.error("不能删除最后一个服务器")
                        return False

                self.server_list.remove(server_to_remove)
                # 清除缓存
                server_key = f"{host}:{port}"
                if server_key in self._server_status_cache:
                    del self._server_status_cache[server_key]

                logger.info(f"删除服务器: {host}:{port}")
                return True
            else:
                logger.warning(f"服务器不存在: {host}:{port}")
                return False
        except Exception as e:
            logger.error(f"删除服务器失败: {e}")
            return False

    def set_current_server(self, host: str, port: int) -> bool:
        """设置当前服务器"""
        try:
            target_server = (host, port)
            if target_server in self.server_list:
                self.current_server = target_server
                logger.info(f"切换到服务器: {host}:{port}")
                return True
            else:
                logger.error(f"服务器不存在: {host}:{port}")
                return False
        except Exception as e:
            logger.error(f"设置当前服务器失败: {e}")
            return False

    def test_server(self, host: str, port: int) -> Dict[str, Any]:
        """测试指定服务器"""
        try:
            server = (host, port)
            status = self._test_server_quality(server)
            status['last_test'] = datetime.now().isoformat()

            # 更新缓存
            server_key = f"{host}:{port}"
            self._server_status_cache[server_key] = status

            return {
                'host': host,
                'port': port,
                'available': status.get('available', False),
                'response_time': status.get('response_time', float('inf')),
                'response_time_ms': round(status.get('response_time', 0) * 1000, 1),
                'error_message': status.get('error_message', ''),
                'status_text': self._get_status_text(status)
            }
        except Exception as e:
            logger.error(f"测试服务器失败: {e}")
            return {
                'host': host,
                'port': port,
                'available': False,
                'response_time': float('inf'),
                'response_time_ms': 0,
                'error_message': str(e),
                'status_text': '测试失败'
            }

    def refresh_server_status(self):
        """刷新所有服务器状态"""
        try:
            self._update_server_status()
            self._last_discovery_time = time.time()
            logger.info("服务器状态刷新完成")
        except Exception as e:
            logger.error(f"刷新服务器状态失败: {e}")

    def _optimize_data_for_storage(self, df: pd.DataFrame, symbol: str, data_type: str, period: str) -> pd.DataFrame:
        """
        优化数据存储格式

        Args:
            df: 原始数据
            symbol: 股票代码
            data_type: 数据类型
            period: 周期

        Returns:
            优化后的数据
        """
        try:
            if df.empty:
                return df

            # 1. 添加元数据列
            df = self._add_metadata_columns(df, symbol, data_type, period)

            # 2. 数据压缩优化
            df = self._optimize_data_types(df)

            # 3. 数据质量评分
            quality_score = self._calculate_data_quality_score(df)
            df.attrs['quality_score'] = quality_score

            logger.debug(f"数据存储优化完成: {symbol}, 质量评分: {quality_score:.2f}")

            return df

        except Exception as e:
            logger.error(f"数据存储优化失败: {e}")
            return df

    def _add_metadata_columns(self, df: pd.DataFrame, symbol: str, data_type: str, period: str) -> pd.DataFrame:
        """添加元数据列"""
        try:
            # 添加必要的元数据
            df = df.copy()
            df['symbol'] = symbol
            df['data_source'] = 'tongdaxin'
            df['data_type'] = data_type
            df['period'] = period
            df['fetch_time'] = datetime.now()
            df['plugin_version'] = '1.0.0'

            return df

        except Exception as e:
            logger.error(f"添加元数据失败: {e}")
            return df

    def _optimize_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """优化数据类型以节省存储空间"""
        try:
            # 价格数据使用float32（足够精度，节省50%空间）
            price_columns = ['open', 'high', 'low', 'close']
            for col in price_columns:
                if col in df.columns:
                    df[col] = df[col].astype('float32')

            # 成交量使用int64
            if 'volume' in df.columns:
                df['volume'] = df['volume'].astype('int64')

            # 成交额使用float64（需要高精度）
            if 'amount' in df.columns:
                df['amount'] = df['amount'].astype('float64')

            # 字符串列使用category类型节省空间
            string_columns = ['symbol', 'data_source', 'data_type', 'period']
            for col in string_columns:
                if col in df.columns:
                    df[col] = df[col].astype('category')

            return df

        except Exception as e:
            logger.error(f"数据类型优化失败: {e}")
            return df

    def _calculate_data_quality_score(self, df: pd.DataFrame) -> float:
        """
        计算数据质量评分 (0-1)

        评分标准：
        - 数据完整性 (30%)
        - 数据一致性 (30%) 
        - 时间连续性 (20%)
        - 数值合理性 (20%)
        """
        try:
            if df.empty:
                return 0.0

            scores = []

            # 1. 数据完整性评分 (30%)
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            completeness_score = sum(1 for col in required_columns if col in df.columns and df[col].notna().all()) / len(required_columns)
            scores.append(completeness_score * 0.3)

            # 2. 数据一致性评分 (30%) - OHLC逻辑
            if all(col in df.columns for col in ['open', 'high', 'low', 'close']):
                valid_ohlc = (
                    (df['high'] >= df[['open', 'close']].max(axis=1)) &
                    (df['low'] <= df[['open', 'close']].min(axis=1)) &
                    (df['high'] >= df['low'])
                ).sum()
                consistency_score = valid_ohlc / len(df) if len(df) > 0 else 0
                scores.append(consistency_score * 0.3)
            else:
                scores.append(0)

            # 3. 时间连续性评分 (20%)
            if len(df) > 1:
                # 检查时间间隔的一致性
                time_diffs = df.index.to_series().diff().dropna()
                if len(time_diffs) > 0:
                    # 计算时间间隔的变异系数
                    mean_diff = time_diffs.mean()
                    std_diff = time_diffs.std()
                    cv = std_diff / mean_diff if mean_diff.total_seconds() > 0 else float('inf')
                    # 变异系数越小，连续性越好
                    continuity_score = max(0, 1 - min(cv, 1))
                    scores.append(continuity_score * 0.2)
                else:
                    scores.append(0.2)  # 单条数据给满分
            else:
                scores.append(0.2)  # 单条数据给满分

            # 4. 数值合理性评分 (20%)
            reasonableness_score = 1.0
            if 'close' in df.columns:
                # 检查价格波动是否合理（单日涨跌幅不超过20%）
                if len(df) > 1:
                    price_changes = df['close'].pct_change().abs()
                    extreme_changes = (price_changes > 0.2).sum()
                    reasonableness_score = max(0, 1 - extreme_changes / len(df))
            scores.append(reasonableness_score * 0.2)

            # 计算总分
            total_score = sum(scores)

            logger.debug(f"数据质量评分详情 - 完整性: {completeness_score:.2f}, 一致性: {consistency_score:.2f}, 连续性: {continuity_score:.2f}, 合理性: {reasonableness_score:.2f}, 总分: {total_score:.2f}")

            return total_score

        except Exception as e:
            logger.error(f"质量评分计算失败: {e}")
            return 0.5  # 默认中等质量

    def _initialize_servers(self):
        """初始化服务器列表，优先从数据库加载"""
        try:
            # 尝试从数据库加载服务器
            from core.database.tdx_server_manager import get_tdx_db_manager

            db_manager = get_tdx_db_manager()
            available_servers = db_manager.get_available_servers(limit=20)

            if available_servers:
                # 从数据库加载服务器
                self.server_list = [(server['host'], server['port']) for server in available_servers]
                logger.info(f"从数据库加载了 {len(self.server_list)} 个服务器")
            else:
                # 使用默认服务器列表
                self._load_default_servers()
                logger.info("使用默认服务器列表")

            # 设置当前服务器
            if self.server_list:
                self.current_server = self.server_list[0]
                self.server_index = 0
            else:
                logger.warning("没有可用的服务器")

        except Exception as e:
            logger.error(f"初始化服务器列表失败: {e}")
            # 出错时使用默认服务器
            self._load_default_servers()

    def _load_default_servers(self):
        """加载默认服务器列表 - 使用最新测试的高质量服务器"""
        self.server_list = [
            ('180.153.18.170', 7709),  # 上海电信主站Z1 - 2ms
            ('218.6.170.47', 7709),    # 上证云成都电信一 - 2ms
            ('202.108.253.139', 80),   # 北京联通主站Z80 - 2ms (注意端口80)
            ('202.108.253.131', 7709),  # 北京联通主站Z2 - 2ms
            ('180.153.18.171', 7709),  # 上海电信主站Z2 - 2ms
            ('180.153.18.172', 80),    # 上海电信主站Z80 - 2ms (注意端口80)
            ('60.191.117.167', 7709),  # 杭州电信主站J1 - 2ms
            ('218.85.139.20', 7709),   # 长城国瑞电信2 - 2ms
            ('58.23.131.163', 7709),   # 长城国瑞网通 - 2ms
            ('123.125.108.14', 7709),  # 上证云北京联通一 - 2ms
            ('115.238.56.198', 7709),  # 杭州电信主站J2 - 2ms
            ('218.85.139.19', 7709),   # 长城国瑞电信1 - 3ms
            ('218.108.98.244', 7709),  # 杭州华数主站J1 - 3ms
            ('180.153.39.51', 7709),   # 上海电信主站Z3 - 3ms
            ('115.238.90.165', 7709),  # 杭州电信主站J4 - 3ms
        ]

        # 将默认服务器保存到数据库
        try:
            from core.database.tdx_server_manager import get_tdx_db_manager
            db_manager = get_tdx_db_manager()

            for host, port in self.server_list:
                db_manager.save_tdx_server(
                    host=host,
                    port=port,
                    status='unknown',
                    source='builtin',
                    priority=1
                )
            logger.info("默认服务器已保存到数据库")
        except Exception as e:
            logger.warning(f"保存默认服务器到数据库失败: {e}")


def create_plugin() -> IDataSourcePlugin:
    """创建插件实例"""
    return TongdaxinStockPlugin()


# 插件元数据
PLUGIN_METADATA = {
    "name": "通达信股票数据源插件",
    "version": "1.0.0",
    "description": "提供A股实时和历史数据，支持上海、深圳交易所，基于pytdx库",
    "author": "FactorWeave-Quant 开发团队",
    "plugin_type": "data_source_stock",
    "asset_types": ["stock"],
    "data_types": ["historical_kline", "real_time_quote", "fundamental", "trade_tick"],
    "markets": ["SH", "SZ"],
    "dependencies": ["pytdx", "pandas", "requests"],
    "config_schema": {
        "host": {
            "type": "string",
            "default": "119.147.212.81",
            "description": "通达信服务器地址"
        },
        "port": {
            "type": "integer",
            "default": 7709,
            "description": "通达信服务器端口"
        },
        "timeout": {
            "type": "integer",
            "default": 30,
            "description": "连接超时时间（秒）"
        },
        "max_retries": {
            "type": "integer",
            "default": 3,
            "description": "最大重试次数"
        },
        "cache_duration": {
            "type": "integer",
            "default": 300,
            "description": "缓存持续时间（秒）"
        },
        "auto_select_server": {
            "type": "boolean",
            "default": True,
            "description": "是否自动选择最快服务器"
        }
    }
}
