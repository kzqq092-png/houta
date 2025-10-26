#!/usr/bin/env python3
"""
分布式节点启动脚本

提供简单的启动方式
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from distributed_node.node_server import start_server
from distributed_node.node_config import NodeConfig


def main():
    """主函数"""
    print("="*80)
    print("FactorWeave-Quant 分布式计算节点")
    print("="*80)
    print()
    
    # 配置选择
    print("请选择配置方式:")
    print("1. 使用默认配置")
    print("2. 从文件加载配置")
    print("3. 自定义配置")
    
    choice = input("\n请输入选择 (1-3): ").strip()
    
    config = None
    
    if choice == "1":
        print("\n使用默认配置...")
        config = NodeConfig()
    
    elif choice == "2":
        config_file = input("请输入配置文件路径: ").strip()
        try:
            config = NodeConfig.load_from_file(config_file)
            print(f"\n已加载配置: {config_file}")
        except Exception as e:
            print(f"\n加载配置失败: {e}")
            print("使用默认配置...")
            config = NodeConfig()
    
    elif choice == "3":
        print("\n自定义配置:")
        node_name = input("节点名称 [Distributed Node]: ").strip() or "Distributed Node"
        port = input("监听端口 [8900]: ").strip()
        port = int(port) if port else 8900
        max_workers = input("最大工作线程 [4]: ").strip()
        max_workers = int(max_workers) if max_workers else 4
        
        config = NodeConfig(
            node_name=node_name,
            port=port,
            max_workers=max_workers
        )
    
    else:
        print("\n无效的选择，使用默认配置")
        config = NodeConfig()
    
    # 保存配置
    save = input("\n是否保存此配置？ (y/n): ").strip().lower()
    if save == 'y':
        config_file = "distributed_node/node_config.json"
        config.save_to_file(config_file)
        print(f"配置已保存到: {config_file}")
    
    print("\n正在启动节点服务器...")
    print(f"节点名称: {config.node_name}")
    print(f"监听端口: {config.port}")
    print(f"访问地址: http://localhost:{config.port}")
    print("\n按 Ctrl+C 停止服务器")
    print("="*80)
    print()
    
    # 启动服务器
    try:
        start_server(config)
    except KeyboardInterrupt:
        print("\n\n服务器已停止")
    except Exception as e:
        print(f"\n启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

