#!/usr/bin/env python3
"""
检查所有插件的配置UI - 验证修复是否适用于所有插件
"""

import sys
import os
import glob
import importlib.util
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def discover_all_plugins():
    """自动发现系统中的所有插件"""
    plugins = []
    print("🔍 自动发现插件...")

    # 搜索插件目录
    plugin_directories = [
        "plugins/sentiment_data_sources",
        "plugins/examples",
        "plugins",
    ]

    for plugin_dir in plugin_directories:
        if os.path.exists(plugin_dir):
            print(f"📂 搜索目录: {plugin_dir}")

            # 查找Python文件
            pattern = os.path.join(plugin_dir, "*.py")
            for file_path in glob.glob(pattern):
                filename = os.path.basename(file_path)

                # 跳过特殊文件
                if filename.startswith('__') or filename in ['base.py', 'config_base.py', 'plugin_interface.py']:
                    continue

                plugin_name = filename.replace('.py', '')

                # 构造插件信息
                if plugin_dir == "plugins/sentiment_data_sources":
                    display_name = format_plugin_display_name(plugin_name, "情绪数据")
                    full_name = f"sentiment_data_sources.{plugin_name}"
                elif plugin_dir == "plugins/examples":
                    display_name = format_plugin_display_name(plugin_name, "示例")
                    full_name = f"examples.{plugin_name}"
                else:
                    display_name = format_plugin_display_name(plugin_name, "插件")
                    full_name = plugin_name

                plugin_info = {
                    "name": full_name,
                    "display_name": display_name,
                    "file_path": file_path,
                    "category": plugin_dir.split('/')[-1]
                }

                plugins.append(plugin_info)
                print(f"  ✅ 发现: {display_name}")

    print(f"🎯 总共发现 {len(plugins)} 个插件")
    return plugins


def format_plugin_display_name(plugin_name, category):
    """格式化插件显示名称"""
    # 移除常见后缀
    clean_name = plugin_name.replace('_plugin', '').replace('_', ' ')

    # 首字母大写
    formatted_name = ' '.join(word.capitalize() for word in clean_name.split())

    return f"{formatted_name} ({category}插件)"


def get_predefined_plugins():
    """获取预定义的插件列表"""
    return [
        {
            "name": "sentiment_data_sources.fmp_sentiment_plugin",
            "display_name": "FMP社交情绪插件",
            "category": "sentiment_data_sources"
        },
        {
            "name": "sentiment_data_sources.vix_sentiment_plugin",
            "display_name": "VIX恐慌指数插件",
            "category": "sentiment_data_sources"
        },
        {
            "name": "sentiment_data_sources.akshare_sentiment_plugin",
            "display_name": "AkShare情绪插件",
            "category": "sentiment_data_sources"
        },
        {
            "name": "examples.macd_indicator",
            "display_name": "MACD指标插件",
            "category": "examples"
        },
        {
            "name": "examples.moving_average_strategy",
            "display_name": "移动平均策略插件",
            "category": "examples"
        }
    ]


def get_plugin_instance_adaptive(plugin_info):
    """自适应获取插件实例"""
    plugin_name = plugin_info['name']

    # 策略1: 尝试推断策略
    inference_strategies = [
        # 情绪数据源插件
        {
            'condition': lambda name: 'sentiment_data_sources' in name,
            'module_prefix': 'plugins.sentiment_data_sources',
            'class_suffix': 'SentimentPlugin'
        },
        # 示例插件
        {
            'condition': lambda name: 'examples' in name,
            'module_prefix': 'plugins.examples',
            'class_suffix': 'Plugin'
        },
        # 通用插件
        {
            'condition': lambda name: True,
            'module_prefix': 'plugins',
            'class_suffix': 'Plugin'
        }
    ]

    for strategy in inference_strategies:
        if strategy['condition'](plugin_name):
            try:
                # 提取实际插件名
                if '.' in plugin_name:
                    actual_name = plugin_name.split('.')[-1]
                else:
                    actual_name = plugin_name

                # 构造模块路径
                if '.' in plugin_name and plugin_name.count('.') == 1:
                    # "category.plugin_name" 格式
                    module_path = f"plugins.{plugin_name}"
                else:
                    # 使用策略前缀
                    module_path = f"{strategy['module_prefix']}.{actual_name}"

                # 推断类名
                clean_name = actual_name.replace('_plugin', '')
                class_name_parts = clean_name.split('_')
                class_name = ''.join(word.capitalize() for word in class_name_parts) + strategy['class_suffix']

                print(f"🔧 尝试导入: {module_path}.{class_name}")

                module = __import__(module_path, fromlist=[class_name])
                plugin_class = getattr(module, class_name)
                return plugin_class()

            except Exception as e:
                print(f"⚠️ 策略失败: {e}")
                continue

    return None


def check_all_plugins():
    """检查所有插件的配置 - 自动发现和自适应"""
    print("🔍 检查所有插件的配置...")

    # 尝试获取系统中的所有插件
    discovered_plugins = discover_all_plugins()

    # 如果自动发现失败，使用预定义列表
    if not discovered_plugins:
        print("⚠️ 自动发现插件失败，使用预定义插件列表")
        discovered_plugins = get_predefined_plugins()

    plugins_to_check = discovered_plugins

    results = []

    for plugin_info in plugins_to_check:
        print(f"\n=== 检查插件: {plugin_info['display_name']} ===")
        print(f"📋 插件名称: {plugin_info['name']}")

        try:
            # 尝试使用自适应的方式获取插件实例
            plugin_instance = get_plugin_instance_adaptive(plugin_info)

            if plugin_instance:
                print(f"✅ 插件实例创建成功: {type(plugin_instance)}")

                # 检查是否是ConfigurablePlugin
                from plugins.sentiment_data_sources.config_base import ConfigurablePlugin

                if isinstance(plugin_instance, ConfigurablePlugin):
                    print(f"✅ 是ConfigurablePlugin类型")

                    # 获取配置模式
                    try:
                        schema = plugin_instance.get_config_schema()
                        config_count = len(schema)
                        print(f"✅ 配置字段数量: {config_count}")

                        if config_count > 0:
                            print(f"📝 配置字段详情:")
                            for field in schema:
                                required_mark = " *" if field.required else ""
                                print(f"  - {field.name}{required_mark}: {field.field_type} ({field.display_name})")
                        else:
                            print(f"⚠️ 没有配置字段")

                        # 检查配置状态
                        if hasattr(plugin_instance, 'is_properly_configured'):
                            is_configured = plugin_instance.is_properly_configured()
                            status_msg = plugin_instance.get_config_status_message() if hasattr(plugin_instance, 'get_config_status_message') else "未知"
                            print(f"🔧 配置状态: {'✅ 正常' if is_configured else '⚠️ 需要配置'} - {status_msg}")

                        results.append({
                            "name": plugin_info['name'],
                            "display_name": plugin_info['display_name'],
                            "status": "✅ ConfigurablePlugin",
                            "config_count": config_count,
                            "configurable": True
                        })

                    except Exception as e:
                        print(f"❌ 获取配置模式失败: {e}")
                        results.append({
                            "name": plugin_info['name'],
                            "display_name": plugin_info['display_name'],
                            "status": "❌ 配置模式错误",
                            "config_count": 0,
                            "configurable": False
                        })
                else:
                    print(f"⚠️ 不是ConfigurablePlugin类型，将使用传统配置")
                    results.append({
                        "name": plugin_info['name'],
                        "display_name": plugin_info['display_name'],
                        "status": "⚠️ 传统配置",
                        "config_count": 0,
                        "configurable": False
                    })
            else:
                print(f"❌ 无法创建插件实例")
                results.append({
                    "name": plugin_info['name'],
                    "display_name": plugin_info['display_name'],
                    "status": "❌ 实例化失败",
                    "config_count": 0,
                    "configurable": False
                })

        except ImportError as e:
            print(f"❌ 插件导入失败: {e}")
            results.append({
                "name": plugin_info['name'],
                "display_name": plugin_info['display_name'],
                "status": "❌ 导入失败",
                "config_count": 0,
                "configurable": False
            })
        except Exception as e:
            print(f"❌ 插件检查失败: {e}")
            results.append({
                "name": plugin_info['name'],
                "display_name": plugin_info['display_name'],
                "status": f"❌ 错误: {e}",
                "config_count": 0,
                "configurable": False
            })

    # 汇总报告
    print(f"\n" + "="*80)
    print(f"📊 插件配置检查汇总报告")
    print(f"="*80)

    configurable_plugins = [r for r in results if r['configurable']]
    traditional_plugins = [r for r in results if not r['configurable'] and '导入失败' not in r['status'] and '错误' not in r['status']]
    failed_plugins = [r for r in results if '导入失败' in r['status'] or '错误' in r['status']]

    print(f"\n✅ 支持ConfigurablePlugin的插件 ({len(configurable_plugins)}个):")
    for plugin in configurable_plugins:
        print(f"  - {plugin['display_name']}: {plugin['config_count']}个配置字段")

    if traditional_plugins:
        print(f"\n⚠️ 使用传统配置的插件 ({len(traditional_plugins)}个):")
        for plugin in traditional_plugins:
            print(f"  - {plugin['display_name']}")

    if failed_plugins:
        print(f"\n❌ 有问题的插件 ({len(failed_plugins)}个):")
        for plugin in failed_plugins:
            print(f"  - {plugin['display_name']}: {plugin['status']}")

    print(f"\n🎉 总计: {len(results)}个插件检查完成")
    print(f"💡 支持配置UI的插件应该能正常显示配置参数")

    return results


if __name__ == "__main__":
    print("🚀 开始检查所有插件...")
    results = check_all_plugins()

    print(f"\n✅ 检查完成！用户可以在HIkyuu插件管理器中测试这些插件的配置功能。")
    input("\n按回车键退出...")
