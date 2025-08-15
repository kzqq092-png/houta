#!/usr/bin/env python3
"""
确保所有插件都有正确的默认配置
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def ensure_plugin_configs():
    """确保所有插件都有正确的默认配置"""
    print("🔧 确保所有插件都有正确的默认配置...")

    try:
        from db.models.plugin_models import get_data_source_config_manager
        config_manager = get_data_source_config_manager()

        # 需要配置的插件及其默认配置
        plugin_configs = {
            "examples.wind_data_plugin": {
                "connection": {
                    "host": "localhost",
                    "port": 9001,
                    "use_ssl": False,
                    "timeout": 30
                },
                "auth": {
                    "type": "用户名密码",
                    "username": "",
                    "password": "",
                    "api_key": "",
                    "token": ""
                },
                "routing": {
                    "weight": 50,
                    "priority": 5,
                    "strategy": "优先级",
                    "max_retries": 3
                },
                "monitoring": {
                    "health_interval": 30,
                    "health_timeout": 10,
                    "enable_auto_check": True
                },
                "advanced": {
                    "enable_cache": True,
                    "cache_ttl": 300,
                    "max_cache_size": 100,
                    "enable_rate_limit": False,
                    "requests_per_second": 10,
                    "burst_size": 20,
                    "custom_params": {
                        "wind_terminal_path": "C:\\Wind\\Wind.NET.Client\\WindNET.exe",
                        "auto_login": True
                    }
                }
            },

            "examples.ctp_futures_plugin": {
                "connection": {
                    "host": "180.168.146.187",
                    "port": 10131,
                    "use_ssl": False,
                    "timeout": 30
                },
                "auth": {
                    "type": "用户名密码",
                    "username": "",
                    "password": "",
                    "api_key": "",
                    "token": ""
                },
                "advanced": {
                    "custom_params": {
                        "broker_id": "",
                        "app_id": "",
                        "auth_code": ""
                    }
                }
            },

            "examples.mysteel_data_plugin": {
                "connection": {
                    "host": "api.mysteel.com",
                    "port": 443,
                    "use_ssl": True,
                    "timeout": 30
                },
                "auth": {
                    "type": "API密钥",
                    "username": "",
                    "password": "",
                    "api_key": "",
                    "token": ""
                }
            },

            "examples.wenhua_data_plugin": {
                "connection": {
                    "host": "api.wenhua.com.cn",
                    "port": 443,
                    "use_ssl": True,
                    "timeout": 30
                },
                "auth": {
                    "type": "API密钥",
                    "username": "",
                    "password": "",
                    "api_key": "",
                    "token": ""
                }
            },

            "examples.bond_data_plugin": {
                "connection": {
                    "host": "api.bond-data.com",
                    "port": 443,
                    "use_ssl": True,
                    "timeout": 30
                },
                "auth": {
                    "type": "API密钥",
                    "username": "",
                    "password": "",
                    "api_key": "",
                    "token": ""
                }
            }
        }

        updated_count = 0

        for plugin_id, default_config in plugin_configs.items():
            print(f"\n检查插件: {plugin_id}")

            # 检查现有配置
            existing_config = config_manager.get_plugin_config(plugin_id)

            if existing_config:
                existing_host = existing_config['config_data'].get('connection', {}).get('host', '')
                print(f"   现有配置主机: {existing_host}")

                # 如果主机地址为空或者是测试地址，更新为正确的默认配置
                if not existing_host or existing_host.startswith('api.') and 'plugin' in existing_host:
                    print(f"   更新配置...")
                    success = config_manager.save_plugin_config(
                        plugin_id=plugin_id,
                        config_data=default_config,
                        priority=5,
                        weight=1.0,
                        enabled=True
                    )
                    if success:
                        print(f"   ✅ 配置更新成功")
                        updated_count += 1
                    else:
                        print(f"   ❌ 配置更新失败")
                else:
                    print(f"   ✅ 配置正常，无需更新")
            else:
                print(f"   创建新配置...")
                success = config_manager.save_plugin_config(
                    plugin_id=plugin_id,
                    config_data=default_config,
                    priority=5,
                    weight=1.0,
                    enabled=True
                )
                if success:
                    print(f"   ✅ 配置创建成功")
                    updated_count += 1
                else:
                    print(f"   ❌ 配置创建失败")

        print(f"\n📊 处理完成: 更新了 {updated_count} 个插件配置")

        # 验证所有配置
        print(f"\n🔍 验证所有插件配置:")
        for plugin_id in plugin_configs.keys():
            config = config_manager.get_plugin_config(plugin_id)
            if config:
                host = config['config_data'].get('connection', {}).get('host', '未设置')
                auth_type = config['config_data'].get('auth', {}).get('type', '未设置')
                print(f"   {plugin_id}: 主机={host}, 认证={auth_type}")
            else:
                print(f"   {plugin_id}: ❌ 配置不存在")

        return True

    except Exception as e:
        print(f"❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = ensure_plugin_configs()
    if success:
        print("\n🎉 所有插件配置已确保正确！")
        print("💡 用户现在打开插件配置对话框应该能看到:")
        print("   - Wind插件: localhost:9001, 用户名密码认证")
        print("   - CTP期货: 180.168.146.187:10131, 用户名密码认证")
        print("   - 我的钢铁网: api.mysteel.com:443, API密钥认证")
        print("   - 文华财经: api.wenhua.com.cn:443, API密钥认证")
        print("   - 债券数据: api.bond-data.com:443, API密钥认证")
    else:
        print("\n❌ 配置处理失败")
