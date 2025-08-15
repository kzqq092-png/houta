#!/usr/bin/env python3
from db.models.plugin_models import get_data_source_config_manager

# 测试配置保存和加载
config_manager = get_data_source_config_manager()

# 保存Wind插件配置
wind_config = {
    'connection': {
        'host': 'localhost',
        'port': 9001,
        'use_ssl': False,
        'timeout': 30
    },
    'auth': {
        'type': '用户名密码',
        'username': 'wind_user',
        'password': 'wind_pass'
    }
}

print('保存Wind插件配置...')
result = config_manager.save_plugin_config('examples.wind_data_plugin', wind_config)
print(f'保存结果: {result}')

print('\n加载Wind插件配置...')
loaded = config_manager.get_plugin_config('examples.wind_data_plugin')
if loaded:
    print('✅ 配置加载成功')
    config_data = loaded['config_data']
    print(f'主机: {config_data["connection"]["host"]}')
    print(f'端口: {config_data["connection"]["port"]}')
    print(f'认证类型: {config_data["auth"]["type"]}')
    print(f'用户名: {config_data["auth"]["username"]}')
else:
    print('❌ 配置加载失败')

# 测试其他插件
plugins_to_test = [
    'examples.ctp_futures_plugin',
    'examples.mysteel_data_plugin',
    'examples.wenhua_data_plugin',
    'examples.bond_data_plugin'
]

for plugin_id in plugins_to_test:
    test_config = {
        'connection': {'host': f'api.{plugin_id.split(".")[-1]}.com', 'port': 443},
        'auth': {'type': 'API密钥', 'api_key': f'test_key_{plugin_id}'}
    }

    print(f'\n测试 {plugin_id}...')
    save_result = config_manager.save_plugin_config(plugin_id, test_config)
    print(f'保存: {save_result}')

    load_result = config_manager.get_plugin_config(plugin_id)
    if load_result:
        host = load_result['config_data']['connection']['host']
        api_key = load_result['config_data']['auth']['api_key']
        print(f'加载: ✅ host={host}, api_key={api_key}')
    else:
        print('加载: ❌ 失败')
