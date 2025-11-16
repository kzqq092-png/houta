#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试GitHub端点数据解析和IP池填充验证

验证：
1. 能否从GitHub端点获取数据
2. 能否正确解析数据
3. 能否正确验证IP地址格式
4. 能否正确填充到连接池
"""

import sys
import os
import time
import socket
from typing import List, Tuple

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from loguru import logger
    logger.add("test_github_endpoint_parsing.log", rotation="10 MB", level="DEBUG")
except ImportError:
    import logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)

def validate_ip_address(ip: str) -> bool:
    """验证IP地址格式是否正确"""
    try:
        # 使用socket.inet_aton验证IPv4地址格式
        socket.inet_aton(ip)
        # 进一步验证IP地址范围（排除0.0.0.0和255.255.255.255等特殊地址）
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        for part in parts:
            num = int(part)
            if num < 0 or num > 255:
                return False
        # 排除一些明显无效的地址
        if ip == '0.0.0.0' or ip == '255.255.255.255':
            return False
        return True
    except (socket.error, ValueError):
        return False

def test_github_endpoint_fetch():
    """测试从GitHub端点获取数据"""
    logger.info("=" * 60)
    logger.info("测试1: 从GitHub端点获取数据")
    logger.info("=" * 60)
    
    try:
        import requests
        import re
        import json
        
        url = "https://raw.githubusercontent.com/rainx/pytdx/master/pytdx/config/hosts.py"
        logger.info(f"正在从 {url} 获取数据...")
        
        resp = requests.get(url, timeout=30)
        logger.info(f"HTTP状态码: {resp.status_code}")
        
        if resp.status_code != 200:
            logger.error(f"获取失败: HTTP {resp.status_code}")
            return False
        
        text = resp.text
        logger.info(f"获取到的数据长度: {len(text)} 字符")
        logger.info(f"数据前500字符:\n{text[:500]}")
        
        # 解析数据
        servers = []
        
        # 1) 尝试作为JSON解析
        parsed_json = None
        try:
            parsed_json = json.loads(text)
            logger.info("数据格式: JSON")
        except Exception:
            logger.info("数据格式: 非JSON，尝试其他格式")
        
        if isinstance(parsed_json, list):
            logger.info(f"JSON数组长度: {len(parsed_json)}")
            for item in parsed_json:
                try:
                    if isinstance(item, dict):
                        if 'ip' in item and 'port' in item:
                            host = str(item['ip']).strip()
                            port = int(item['port'])
                            if 0 < port <= 65535:
                                servers.append((host, port))
                        elif 'host' in item and 'port' in item:
                            host = str(item['host']).strip()
                            port = int(item['port'])
                            if 0 < port <= 65535:
                                servers.append((host, port))
                    elif isinstance(item, (list, tuple)) and len(item) >= 2:
                        host = str(item[0]).strip()
                        port = int(item[1])
                        if 0 < port <= 65535:
                            servers.append((host, port))
                except Exception as e:
                    logger.debug(f"解析JSON项失败: {e}")
                    continue
        
        # 2) 解析Python hosts.py风格的('ip', port)元组
        tuple_pattern = re.compile(r"\(\s*['\"](\d{1,3}(?:\.\d{1,3}){3})['\"]\s*,\s*(\d{2,5})\s*\)")
        for m in tuple_pattern.finditer(text):
            host = m.group(1)
            port = int(m.group(2))
            if 0 < port <= 65535:
                servers.append((host, port))
        
        # 3) 再用通用 ip:port 模式兜底
        ip_port_pattern = re.compile(r"(?:^|[^0-9])(\d{1,3}(?:\.\d{1,3}){3})[:：]\s*(\d{2,5})")
        for m in ip_port_pattern.finditer(text):
            host = m.group(1)
            port = int(m.group(2))
            if 0 < port <= 65535:
                servers.append((host, port))
        
        logger.info(f"解析到的服务器数量: {len(servers)}")
        
        # 去重
        seen = set()
        deduped = []
        for host, port in servers:
            key = f"{host}:{port}"
            if key in seen:
                continue
            seen.add(key)
            deduped.append((host, port))
        
        logger.info(f"去重后的服务器数量: {len(deduped)}")
        
        # 验证IP地址格式
        validated_servers = []
        invalid_servers = []
        for host, port in deduped:
            if validate_ip_address(host):
                validated_servers.append((host, port))
            else:
                invalid_servers.append((host, port))
        
        logger.info(f"有效IP地址数量: {len(validated_servers)}")
        logger.info(f"无效IP地址数量: {len(invalid_servers)}")
        
        if invalid_servers:
            logger.warning(f"无效IP地址列表: {invalid_servers[:10]}")
        
        if validated_servers:
            logger.info(f"前10个有效IP地址:")
            for i, (host, port) in enumerate(validated_servers[:10], 1):
                logger.info(f"  {i}. {host}:{port}")
        
        return len(validated_servers) > 0
        
    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
        return False

def test_connection_pool_initialization():
    """测试连接池初始化"""
    logger.info("=" * 60)
    logger.info("测试2: 连接池初始化")
    logger.info("=" * 60)
    
    try:
        from plugins.data_sources.stock.tongdaxin_plugin import TongdaxinStockPlugin
        
        plugin = TongdaxinStockPlugin()
        logger.info("插件实例创建成功")
        
        # 初始化服务器列表
        plugin._initialize_servers()
        logger.info(f"服务器列表长度: {len(plugin.server_list)}")
        
        if plugin.server_list:
            logger.info(f"前10个服务器:")
            for i, (host, port) in enumerate(plugin.server_list[:10], 1):
                logger.info(f"  {i}. {host}:{port}")
        
        # 测试连接池初始化
        if plugin.use_connection_pool and plugin.server_list:
            logger.info("开始初始化连接池...")
            from plugins.data_sources.stock.tongdaxin_plugin import ConnectionPool
            
            pool = ConnectionPool(max_connections=5, timeout=10)
            pool.initialize(plugin.server_list[:20])  # 只测试前20个服务器
            
            logger.info(f"连接池初始化完成")
            logger.info(f"活跃连接数: {len(pool.connections_list)}")
            logger.info(f"活跃服务器数: {len(pool.active_servers)}")
            
            # 获取连接池信息
            pool_info = pool.get_connection_pool_info()
            logger.info(f"连接池信息:")
            logger.info(f"  总连接数: {pool_info.get('total_connections', 0)}")
            logger.info(f"  活跃服务器数: {pool_info.get('active_servers', 0)}")
            logger.info(f"  健康IP数: {pool_info.get('healthy_ips', 0)}")
            logger.info(f"  限流IP数: {pool_info.get('limited_ips', 0)}")
            logger.info(f"  故障IP数: {pool_info.get('failed_ips', 0)}")
            
            ip_stats = pool_info.get('ip_stats', {})
            if ip_stats:
                logger.info(f"IP统计信息（前5个）:")
                for i, (server_key, stats) in enumerate(list(ip_stats.items())[:5], 1):
                    logger.info(f"  {i}. {server_key}: {stats}")
            
            return len(pool.connections_list) > 0
        else:
            logger.warning("连接池模式未启用或服务器列表为空")
            return False
        
    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
        return False

def main():
    """主函数"""
    logger.info("开始测试GitHub端点数据解析和IP池填充")
    logger.info(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # 测试1: GitHub端点获取
    result1 = test_github_endpoint_fetch()
    results.append(("GitHub端点获取", result1))
    
    # 测试2: 连接池初始化
    result2 = test_connection_pool_initialization()
    results.append(("连接池初始化", result2))
    
    # 汇总结果
    logger.info("=" * 60)
    logger.info("测试结果汇总")
    logger.info("=" * 60)
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    logger.info(f"\n总体结果: {'✅ 所有测试通过' if all_passed else '❌ 部分测试失败'}")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())

