#!/usr/bin/env python3
"""
获取最新的TDX服务器列表
从pytdx GitHub项目中获取最新的服务器配置
"""

import requests
import re
import time
import socket
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed


def fetch_latest_tdx_servers():
    """从GitHub获取最新的TDX服务器列表"""
    try:
        print("🔄 正在从pytdx GitHub项目获取最新服务器列表...")

        url = "https://raw.githubusercontent.com/rainx/pytdx/master/pytdx/config/hosts.py"
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        content = response.text

        # 使用正则表达式提取服务器信息
        pattern = r'\("([^"]*)", "([^"]*)", (\d+)\)'
        matches = re.findall(pattern, content)

        servers = []
        for name, ip, port in matches:
            servers.append({
                'name': name,
                'host': ip,
                'port': int(port),
                'source': 'pytdx_github'
            })

        print(f"✅ 成功获取 {len(servers)} 个服务器配置")
        return servers

    except Exception as e:
        print(f"❌ 获取服务器列表失败: {e}")
        return []


def test_server_connectivity(server, timeout=3):
    """测试单个服务器的连通性"""
    host = server['host']
    port = server['port']

    try:
        start_time = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)

        result = sock.connect_ex((host, port))
        sock.close()

        response_time = time.time() - start_time

        if result == 0:
            server['available'] = True
            server['response_time'] = response_time
            server['status'] = 'available'
            return server
        else:
            server['available'] = False
            server['response_time'] = float('inf')
            server['status'] = 'unavailable'
            server['error'] = f'Connection failed: {result}'
            return server

    except Exception as e:
        server['available'] = False
        server['response_time'] = float('inf')
        server['status'] = 'error'
        server['error'] = str(e)
        return server


def test_servers_concurrent(servers, max_workers=20):
    """并发测试服务器连通性"""
    print(f"🔄 开始并发测试 {len(servers)} 个服务器的连通性...")

    tested_servers = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有测试任务
        future_to_server = {
            executor.submit(test_server_connectivity, server): server
            for server in servers
        }

        # 收集结果
        for future in as_completed(future_to_server):
            try:
                result = future.result(timeout=5)
                tested_servers.append(result)

                if result['available']:
                    print(f"✅ {result['name']:<25} {result['host']:<15} {result['response_time']*1000:.0f}ms")
                else:
                    print(f"❌ {result['name']:<25} {result['host']:<15} {result.get('error', 'Unknown error')}")

            except Exception as e:
                print(f"❌ 测试异常: {e}")

    return tested_servers


def get_best_servers(tested_servers, limit=15):
    """获取最佳服务器列表"""
    # 筛选可用服务器
    available_servers = [s for s in tested_servers if s['available']]

    if not available_servers:
        print("❌ 没有可用的服务器")
        return []

    # 按响应时间排序
    available_servers.sort(key=lambda x: x['response_time'])

    # 返回前N个最快的服务器
    best_servers = available_servers[:limit]

    print(f"\n🎯 最佳服务器列表 (前{len(best_servers)}个):")
    print("-" * 80)
    print(f"{'序号':<4} {'名称':<25} {'IP地址':<15} {'端口':<6} {'响应时间':<10}")
    print("-" * 80)

    for i, server in enumerate(best_servers, 1):
        print(f"{i:<4} {server['name']:<25} {server['host']:<15} {server['port']:<6} {server['response_time']*1000:.0f}ms")

    return best_servers


def update_tdx_database(best_servers):
    """更新TDX数据库中的服务器列表"""
    try:
        print(f"\n🔄 正在更新TDX数据库...")

        from core.database.tdx_server_manager import get_tdx_db_manager

        db_manager = get_tdx_db_manager()

        # 清除旧的GitHub来源的服务器
        # db_manager.clear_servers_by_source('pytdx_github')

        # 添加新的服务器
        added_count = 0
        for server in best_servers:
            success = db_manager.save_tdx_server(
                host=server['host'],
                port=server['port'],
                status='available',
                response_time=server['response_time'],
                location=server['name'],  # 使用name作为location
                source='pytdx_github',
                priority=1,
                last_tested=datetime.now().isoformat(),
                notes=f"Response time: {server['response_time']*1000:.0f}ms"
            )
            if success:
                added_count += 1

        print(f"✅ 成功更新数据库，添加了 {added_count} 个服务器")
        return True

    except Exception as e:
        print(f"❌ 更新数据库失败: {e}")
        return False


def main():
    """主函数"""
    print("🚀 TDX服务器列表更新工具")
    print("=" * 50)

    # 1. 获取最新服务器列表
    servers = fetch_latest_tdx_servers()
    if not servers:
        print("❌ 无法获取服务器列表，退出")
        return

    # 2. 并发测试服务器连通性
    tested_servers = test_servers_concurrent(servers)

    # 3. 获取最佳服务器
    best_servers = get_best_servers(tested_servers, limit=15)
    if not best_servers:
        print("❌ 没有可用的服务器，退出")
        return

    # 4. 更新数据库
    if update_tdx_database(best_servers):
        print("\n🎉 TDX服务器列表更新完成！")

        # 5. 生成Python代码格式
        print("\n📋 Python代码格式的服务器列表:")
        print("server_list = [")
        for server in best_servers[:10]:  # 只显示前10个
            print(f"    ('{server['host']}', {server['port']}),  # {server['name']} - {server['response_time']*1000:.0f}ms")
        print("]")
    else:
        print("❌ 数据库更新失败")


if __name__ == "__main__":
    main()
